"""Background upload jobs and JSON import routes for emissions.

Split out of routes/emissions.py unchanged (hardening plan, task 5.3). The routes are
registered on the same ``emissions_bp`` blueprint, so URLs and endpoint names are the same.
"""
import os
import tempfile
import uuid
from background_processor import active_job_count, get_job_status, start_background_upload
from calculations import compute_emissions
from extensions import db
from flask import current_app, jsonify, request, send_file
from input_validation import decimal_mark_from, xlsx_signature_error
from models import Emission, Facility, Notification, User
from routes.auth import login_required
from services.ogmp import ogmp_level_for
from sqlalchemy import func
from utils import get_allowed_facility_ids, get_current_user, log_activity_and_notify
from . import emissions_bp
from routes.emissions import resolve_gwp_dict, resolve_gwp_standard


def _read_upload_request():
    """The validated upload form (file saved to a temp path), or an error response. Shared by the import
    and by the "Check file" step so both refuse the same files."""
    user = get_current_user()
    if not user:
        return None, (jsonify({"error": "Unauthorized"}), 401)

    if "file" not in request.files:
        return None, (jsonify({"error": "No file part"}), 400)
    file = request.files["file"]
    if file.filename == "":
        return None, (jsonify({"error": "No selected file"}), 400)

    ext = os.path.splitext(file.filename)[1].lower()
    if ext == ".xls":
        # the reader handles Excel 2007+ workbooks only (a .xls file was read as text)
        return None, (jsonify({"error": "Excel 97-2003 (.xls) files are not supported: save the file as .xlsx or .csv"}), 400)
    if ext not in [".csv", ".xlsx"]:
        return None, (jsonify({"error": "Invalid file type. Only .csv and .xlsx files are allowed."}), 400)

    global_factor_type = request.form.get("global_factor_type", "auto")
    mapping_str = request.form.get("column_mapping") or request.form.get("mapping")
    scope = request.form.get("scope", "1")
    overwrite_duplicates = request.form.get("overwrite_duplicates") == "true"
    decimal_mark = decimal_mark_from(request.form)  # chosen per file in the wizard (F6)

    # BUG-001: the bulk job must enforce the same roles as the dedicated endpoints.
    if user.role in ["it_admin", "it_manager", "it"]:
        return None, (jsonify({"error": "IT accounts cannot upload business data"}), 403)
    if user.role == "auditor":
        return None, (jsonify({"error": "Read-only role cannot upload data"}), 403)
    if scope not in ("1", "2", "3", "3_eeio", "sources", "production", "mitigation", "custom_factors", "facilities"):
        return None, (jsonify({"error": f"Unknown import type '{scope}'"}), 400)
    if scope in ("facilities", "custom_factors") and user.role not in ["admin", "superuser"]:
        return None, (jsonify({"error": "Only admins and superusers can import facilities or custom factors"}), 403)

    import json

    provided_mapping = None
    if mapping_str:
        try:
            provided_mapping = json.loads(mapping_str)
        except json.JSONDecodeError:
            return None, (jsonify({"error": "column_mapping is not valid JSON"}), 400)
        if not isinstance(provided_mapping, dict):
            return None, (jsonify({"error": "column_mapping must be an object of field -> column"}), 400)

    fd, path = tempfile.mkstemp(suffix=ext)
    os.close(fd)  # H6: Close descriptor immediately to prevent leak
    file.save(path)

    # Content sniffing check for Excel
    if ext == ".xlsx" and (bad := xlsx_signature_error(path)):
        try:
            os.remove(path)
        except OSError:
            pass
        return None, (jsonify({"error": bad}), 400)

    return {"user": user, "path": path, "filename": file.filename, "global_factor_type": global_factor_type,
            "mapping": provided_mapping, "scope": scope, "overwrite": overwrite_duplicates,
            "decimal_mark": decimal_mark}, None


@emissions_bp.route("/upload/start", methods=["POST"])
@login_required
def upload_start():
    # Audit A-09: each job is a thread holding its parsed rows until its single commit;
    # unbounded parallel uploads by one account could exhaust the worker's memory
    user = get_current_user()
    max_jobs = int(os.environ.get("MAX_CONCURRENT_UPLOADS_PER_USER", "3"))
    if user and active_job_count(user.id) >= max_jobs:
        return jsonify({"error": f"You already have {max_jobs} uploads in progress. Wait for one to finish."}), 429

    req, err = _read_upload_request()
    if err:
        return err
    from flask import current_app

    job_id = start_background_upload(
        current_app._get_current_object(),
        req["path"],
        req["filename"],
        req["user"].id,
        req["global_factor_type"],
        provided_mapping=req["mapping"],
        scope=req["scope"],
        overwrite_duplicates=req["overwrite"],
        decimal_mark=req["decimal_mark"],
    )

    try:
        log_activity_and_notify(
            action="UPLOAD_START",
            record_id=str(job_id),
            user=req["user"],
            request=request,
            entity="BulkJob",
            details=f"Queued bulk upload job '{req['filename']}' for scope {req['scope']}",
        )
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.warning(f"Failed to log upload_start activity: {e}")

    return jsonify({"job_id": job_id})


@emissions_bp.route("/upload/check", methods=["POST"])
@login_required
def upload_check():
    """Check a file before importing it: the first `sample_rows` rows are calculated exactly as the import
    would, every row is counted (period, facilities, processes), and nothing is saved."""
    req, err = _read_upload_request()
    if err:
        return err
    from flask import current_app
    from background_processor import run_file_check

    try:
        sample = max(100, min(int(request.form.get("sample_rows") or 2000), 20000))
    except ValueError:
        sample = 2000
    status = run_file_check(current_app._get_current_object(), req["path"], req["filename"], req["user"].id,
                            req["global_factor_type"], provided_mapping=req["mapping"], scope=req["scope"],
                            overwrite_duplicates=req["overwrite"], sample_rows=sample,
                            decimal_mark=req["decimal_mark"])
    if not status or status.get("status") != "completed":
        errors = (status or {}).get("errors") or ["The file could not be checked."]
        return jsonify({"error": errors[0], "errors": errors}), 400
    return jsonify({"preview": status.get("preview"), "skipped_groups": status.get("skipped_groups", [])})


@emissions_bp.route("/upload/limits", methods=["GET"])
@login_required
def upload_limits():
    """Upload limits the wizard checks when a file is picked (no row limit; the request size is capped)."""
    from flask import current_app

    return jsonify({"max_bytes": current_app.config.get("MAX_CONTENT_LENGTH")})


def _job_visible(job_id):
    """BUG-076: a bulk job is readable by its uploader, or by an admin; others get 404."""
    from background_processor import get_job_owner

    user = get_current_user()
    owner = get_job_owner(job_id)
    return user is not None and owner is not None and (owner == user.id or user.role == "admin")


@emissions_bp.route("/upload/status/<job_id>", methods=["GET"])
@login_required
def upload_status(job_id):
    status = get_job_status(job_id) if _job_visible(job_id) else None
    if not status:
        return jsonify({"error": "Job not found"}), 404
    return jsonify(status)


@emissions_bp.route("/upload/errors/<job_id>", methods=["GET"])
@login_required
def upload_errors(job_id):
    from background_processor import get_job_error_csv_path

    path = get_job_error_csv_path(job_id) if _job_visible(job_id) else None
    if not path:
        return jsonify({"error": "No errors file found"}), 404
    return send_file(
        path,
        as_attachment=True,
        download_name=f"errors_{job_id}.csv",
        mimetype="text/csv",
    )


@emissions_bp.route("/import", methods=["POST"])
@login_required  # SEC-01 FIX: was missing
def import_emissions():
    user = get_current_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    if user.role in ["it_admin", "it_manager", "it"]:
        return (
            jsonify(
                {"error": "Forbidden: IT personnel cannot access operational emission data"}
            ),
            403,
        )

    data = request.get_json()
    records_data = data.get("records", [])

    if not records_data:
        return jsonify({"error": "No records provided"}), 400

    imported_count = 0
    errors = []

    allowed_ids = get_allowed_facility_ids(user)

    # Cache for facility lookups to avoid redundant queries
    facility_cache = {}

    for i, rec_data in enumerate(records_data):
        try:
            # 1. Resolve facility_id (could be a name string from CSV)
            f_val = rec_data.get("facility_id")
            facility = None

            if isinstance(f_val, str) and not f_val.isdigit():
                # Provided value is a facility name - make it case insensitive and strip whitespace
                f_name_clean = f_val.strip()
                if f_name_clean.lower() in facility_cache:
                    facility = facility_cache[f_name_clean.lower()]
                else:
                    facility = Facility.query.filter(
                        func.lower(Facility.name) == f_name_clean.lower()
                    ).first()
                    facility_cache[f_name_clean.lower()] = facility
            else:
                # Provided value is potentially an ID
                try:
                    fid = int(f_val) if f_val else None
                    if fid is not None:
                        if fid in facility_cache:
                            facility = facility_cache[fid]
                        else:
                            facility = db.session.get(Facility, fid)
                            facility_cache[fid] = facility
                    else:
                        facility = None
                except (ValueError, TypeError):
                    facility = None

            if not facility:
                errors.append(f"Row {i}: Facility/Region '{f_val}' not found")
                continue
            elif allowed_ids is not None and facility.id not in allowed_ids:
                errors.append(f"Row {i}: Unauthorized for facility '{f_val}'")
                continue

            # Update rec_data with resolved ID and ensure group_name is set for calculation context
            rec_data["facility_id"] = facility.id
            if not rec_data.get("group_name"):
                rec_data["group_name"] = facility.name

            # Fill in hierarchy if missing
            rec_data["activity"] = rec_data.get("activity") or facility.activity
            rec_data["division"] = rec_data.get("division") or facility.division
            rec_data["field"] = rec_data.get("field") or facility.field

            # CSV templates use '-' for empty optional fields
            for key in list(rec_data.keys()):
                if rec_data.get(key) == "-":
                    rec_data[key] = None

            # RC-6: same validation, factor resolution and persistence as the manual form
            from calculations.anomaly import plausibility_check
            from input_validation import ValidationError, parse_month, parse_year
            from services.scope1_calc import apply_result, canonicalize, resolve_factor, validate_activity
            from utils import user_label

            FUEL_ALIASES = {
                "Diesel": "Diesel (No. 2 Fuel Oil)",
                "No. 2 Diesel": "Diesel (No. 2 Fuel Oil)",
                "Gasoline": "Motor Gasoline",
                "Petrol": "Motor Gasoline",
            }
            try:
                rec_data["year"] = parse_year(rec_data.get("year"))
                rec_data["month"] = parse_month(rec_data.get("month"), required=True)
                rec_data["process_type"] = rec_data.get("process_type") or rec_data.get("type")
                fuel_key = rec_data.get("fuel") or rec_data.get("fuel_type")
                if fuel_key in FUEL_ALIASES:
                    rec_data["fuel"] = rec_data["fuel_type"] = FUEL_ALIASES[fuel_key]
                rec_data = canonicalize(rec_data)
                validate_activity(rec_data, require_unit=str(rec_data.get("factor_source") or "default").lower() in ("default", "custom"))
                factor_data = resolve_factor(rec_data)
                if factor_data.get("hhv") and not rec_data.get("hhv"):
                    rec_data["hhv"] = factor_data["hhv"]
                gwp_dict = resolve_gwp_dict(user)
                gwp_std = resolve_gwp_standard(user)
                em_result, method = compute_emissions(rec_data, factor_data, gwp_dict=gwp_dict)
            except ValueError as err:
                errors.append(f"Row {i}: {getattr(err, 'message', None) or err}")
                continue
            verdict, qa_msg = plausibility_check(em_result["totalCo2e"])
            if verdict == "reject":
                errors.append(f"Row {i}: {qa_msg}")
                continue

            record = Emission(
                record_id=f"IMP-{uuid.uuid4().hex[:8]}-{i}",
                year=rec_data["year"],
                month=rec_data["month"],
                facility_id=facility.id,
                group_name=rec_data["group_name"],
                activity=rec_data["activity"],
                division=rec_data["division"],
                field=rec_data["field"],
                equipment_id=rec_data.get("equipment_id"),
                created_by=user.id,
                created_by_name=user_label(user),
                factor_source=rec_data.get("factor_source") or "default",
                qa_flag=qa_msg[:255] if qa_msg else None,
                status="Pending",  # D-04: all bulk imports queue as Pending
                approved_by=None,
                approved_at=None,
            )
            apply_result(record, rec_data, em_result, method, factor_data, gwp_std)
            record.ogmp_level = ogmp_level_for(record)
            db.session.add(record)
            imported_count += 1
        except Exception:
            current_app.logger.exception("Import row %s failed", i)
            errors.append(f"Row {i}: could not be processed")  # BUG-087: no raw exception text

    current_app.logger.info(
        f"Import summary: imported={imported_count}, errors={len(errors)}"
    )
    if errors and imported_count == 0:
        db.session.rollback()
        return jsonify({"error": "Import failed", "details": errors}), 400

    if imported_count > 0:
        # audit entry + reviewer notifications commit atomically with the data (project convention)
        log_activity_and_notify(
            action="IMPORT",
            record_id=f"BATCH-{imported_count}",
            user=user,
            request=request,
            entity="Emission",
            details=f"Bulk imported {imported_count} emission records (status: Pending)",
        )
        for admin in User.query.filter_by(role="admin", status="active").all():
            if admin.id == user.id:
                continue
            Notification.create(
                user_id=admin.id,
                type="warning",
                title="Bulk Emission Records Awaiting Approval",
                message=f"{user.fullName or user.email} imported {imported_count} emission records that require verification.",
                metadata={"imported_count": imported_count, "uploader_id": user.id},
            )
    db.session.commit()
    from routes.dashboard import clear_dashboard_cache

    clear_dashboard_cache()

    return jsonify(
        {
            "message": f"{imported_count} records imported",
            "imported": imported_count,
            "status": "Pending",
            "errors": errors,
        }
    )
