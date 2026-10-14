"""Synchronous bulk-upload route for Scope 1 emissions (JSON rows, preview then confirm).

Every row goes through ``background_processor._process_row``, the same validation, factor
resolution, calculation and storage as the file upload and the manual form, so the three
entry points cannot drift apart. The routes are registered on ``emissions_bp``.
"""
from datetime import datetime, timezone

from calculations import compute_emissions
from emission_factors import API_FACTORS
from extensions import db, limiter
from flask import jsonify, request
from models import CustomFactor, Emission, Facility, Notification, User
from routes.auth import login_required
from utils import (
    build_name_map, get_allowed_facility_ids, get_current_user, internal_error, log_activity_and_notify,
)
from . import emissions_bp
from routes.emissions import resolve_gwp_dict, resolve_gwp_standard

_DATE_FORMATS = {
    "YYYY-MM-DD": "%Y-%m-%d", "MM/DD/YYYY": "%m/%d/%Y", "DD/MM/YYYY": "%d/%m/%Y",
    "YYYY-MM": "%Y-%m", "MM/YYYY": "%m/%Y", "YYYY": "%Y",
}


def _row_for_processor(rec, py_fmt, date_format):
    """A JSON record in the shape of a file row; returns (row, error)."""
    row = {str(k): v for k, v in rec.items() if v is not None and str(v).strip() != ""}
    row["facility_name"] = str(row.get("facility_name") or row.get("facility_id") or "").strip()
    if "process" not in row and "process_type" not in row and row.get("type"):
        row["process"] = row["type"]
    if row.get("equipment") and not row.get("equipment_id"):
        row["equipment_id"] = row["equipment"]
    date = row.get("date")
    if date:
        try:
            dt = datetime.strptime(str(date).strip(), py_fmt)
        except ValueError:
            return row, f"Invalid date format: {date} does not match {date_format}."
        row["date"] = f"{dt.year}-{dt.month:02d}"
    return row, None


@emissions_bp.route("/bulk-upload", methods=["POST"])
@limiter.limit("20 per minute")
@login_required
def add_bulk_upload():
    from background_processor import _scope1_key, _process_row

    user = get_current_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    if user.role in ["auditor", "it_admin", "it_manager", "it"]:
        return jsonify({"error": "Read-only auditor and IT personnel do not have access to upload emission data"}), 403

    data = request.get_json() or {}
    records = data.get("records", [])
    date_format = data.get("date_format", "YYYY-MM-DD")
    global_factor_type = data.get("global_factor_type", "auto")
    confirm = bool(data.get("confirm", False))
    py_fmt = _DATE_FORMATS.get(date_format, "%Y-%m-%d")

    allowed = get_allowed_facility_ids(user)
    facilities = Facility.query.all() if allowed is None else Facility.query.filter(Facility.id.in_(allowed)).all()
    fac_name_map = build_name_map(facilities)
    for fac in facilities:
        fac_name_map.add(fac.region, fac, overwrite=False)
    fac_id_map = {str(f.id): f for f in facilities}
    cf_name_map = build_name_map(CustomFactor.query.filter(CustomFactor.is_archived.is_(False)).all())

    # existing live records, keyed as the file upload keys them (duplicates are found the same way)
    batch_keys = {}
    for e in Emission.query.filter(Emission.status.in_(("Pending", "Verified", "Pending Approval"))).with_entities(
        Emission.id, Emission.facility_id, Emission.year, Emission.month, Emission.process_type,
        Emission.fuel_type, Emission.equipment_id, Emission.data_source_ref,
    ).all():
        batch_keys[_scope1_key(e.facility_id, e.year, e.month, e.process_type, e.fuel_type,
                               e.equipment_id, e.data_source_ref)] = e.id

    gwp_dict, gwp_std = resolve_gwp_dict(user), resolve_gwp_standard(user)
    valid_records, errors, duplicates, new_emissions = [], [], [], []
    db.session.autoflush = False
    for idx, rec in enumerate(records):
        row_num = idx + 1
        row, date_err = _row_for_processor(rec if isinstance(rec, dict) else {}, py_fmt, date_format)
        if date_err:
            errors.append({"row": row_num, "reasons": [date_err], "original": rec})
            continue
        obj, errs = _process_row(
            row, user.id, fac_name_map, fac_id_map, cf_name_map, compute_emissions, API_FACTORS,
            global_factor_type, gwp_dict=gwp_dict, gwp_std=gwp_std, row_idx=row_num,
            batch_keys=batch_keys, overwrite_duplicates=confirm,
        )
        if errs:
            if str(errs[0]).startswith("Duplicate record"):
                duplicates.append({"row": row_num, "reason": errs[0]})
            else:
                errors.append({"row": row_num, "reasons": errs, "original": rec})
            continue
        if obj is None:
            continue  # an existing record was overwritten through the maker-checker
        facility = fac_id_map.get(str(obj.facility_id))
        valid_records.append({
            "row": row_num, "year": obj.year, "month": obj.month, "facility": facility.name if facility else None,
            "process": obj.process_type, "fuel": obj.fuel_type, "amount": obj.quantity, "unit": obj.unit,
            "co2e": round(obj.co2e_total, 2),
        })
        new_emissions.append(obj)

    if not confirm:
        db.session.rollback()  # the preview saves nothing
        return jsonify({"status": "preview", "valid_count": len(valid_records), "valid_records": valid_records,
                        "duplicate_count": len(duplicates), "duplicates": duplicates, "errors": errors})

    if new_emissions:
        db.session.add_all(new_emissions)
    try:
        status = new_emissions[0].status if new_emissions else None
        if status in ("Pending", "Pending Approval"):
            for admin in User.query.filter_by(role="admin", status="active").all():
                Notification.create(
                    user_id=admin.id, type="audit", title="Scope 1 Bulk Upload Pending Review",
                    message=f"{len(new_emissions):,} new Scope 1 emission records were uploaded by {user.fullName} "
                            "and are awaiting your approval.",
                )
        log_activity_and_notify(
            action="BULK_IMPORT", record_id=f"count:{len(new_emissions)}", user=user, request=request,
            entity="Emission", details=f"Bulk uploaded {len(new_emissions)} Scope 1 records (Status: {status})",
        )
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return internal_error(e, "Failed to save to database")
    return jsonify({"status": "success", "imported": len(new_emissions), "errors": errors})
