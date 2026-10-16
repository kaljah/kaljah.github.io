from flask import Blueprint, jsonify, request, Response
from sqlalchemy import or_, and_
from extensions import db
from models import Emission, Scope2Emission, Scope3Emission
from routes.auth import login_required
from utils import get_current_user, get_allowed_facility_ids
import csv
import io
from utils import internal_error

qaqc_bp = Blueprint("qaqc_bp", __name__)

# Maximum number of flagged records returned per request (prevents OOM on large DBs)
_MAX_FLAGGED_RECORDS = 500


def _is_admin_or_superuser(user):
    """Returns True if the user has QA/QC viewing rights (admin or superuser roles)."""
    return user and user.role in ["admin", "superuser"]


@qaqc_bp.route("/dashboard", methods=["GET"])
@login_required
def get_qaqc_dashboard():
    """
    Returns aggregated uncertainty (IPCC SRSS) and flagged anomaly records.
    Scoped to the requesting user's allowed facilities.
    Access: admin, superuser only. The data is built by services.qaqc_dashboard.
    """
    from services.qaqc_dashboard import build_dashboard

    user = get_current_user()
    if not _is_admin_or_superuser(user):
        return jsonify({"error": "Admin or Superuser privileges required"}), 403
    try:
        return jsonify(build_dashboard(get_allowed_facility_ids(user), request.args))
    except Exception as e:
        import traceback
        from flask import current_app
        current_app.logger.error(f"[QAQC] Dashboard error: {e}\n{traceback.format_exc()}")
        return internal_error(e, status_text="error", message="Internal server error")


@qaqc_bp.route("/export", methods=["GET"])
@login_required
def export_qaqc_report():
    """
    Exports QA/QC anomaly data as a CSV file with scope and year filtering.
    Access: admin, superuser, it_admin only.
    """
    user = get_current_user()
    if not _is_admin_or_superuser(user):
        return jsonify({"error": "Admin or Superuser privileges required"}), 403

    try:
        allowed_fids = get_allowed_facility_ids(user)
        year_arg = request.args.get("year")
        scope_arg = request.args.get("scope")

        def _fac_filter(q, model):
            if allowed_fids is not None:
                q = q.filter(model.facility_id.in_(allowed_fids))
            if year_arg and year_arg not in ["all", ""]:
                try:
                    q = q.filter(model.year == int(year_arg))
                except ValueError:
                    pass
            return q

        status_arg = (request.args.get("status") or "").lower().strip()

        def _apply_export_status_filter(q, model):
            if status_arg == "rejected":
                return q.filter(model.status.ilike("%rejected%"))
            elif status_arg == "verified":
                return q.filter(model.status.ilike("%verified%"))
            elif status_arg == "pending":
                return q.filter(or_(model.status.ilike("%pending%"), model.status.is_(None)))
            elif status_arg == "active":
                return q.filter(or_(model.status.is_(None), and_(~model.status.ilike("%rejected%"), ~model.status.ilike("%verified%"))))
            elif status_arg in ["all", ""]:
                return q.filter(or_(model.status.is_(None), ~model.status.ilike("%rejected%")))
            return q

        q1 = []
        q2 = []
        q3 = []
        if scope_arg in [None, "all", "1"]:
            q1 = _apply_export_status_filter(
                _fac_filter(Emission.query.filter(Emission.qa_flag.isnot(None)), Emission),
                Emission
            ).limit(_MAX_FLAGGED_RECORDS).all()
        if scope_arg in [None, "all", "2"]:
            q2 = _apply_export_status_filter(
                _fac_filter(Scope2Emission.query.filter(Scope2Emission.qa_flag.isnot(None)), Scope2Emission),
                Scope2Emission
            ).limit(_MAX_FLAGGED_RECORDS).all()
        if scope_arg in [None, "all", "3"]:
            q3 = _apply_export_status_filter(
                _fac_filter(Scope3Emission.query.filter(Scope3Emission.qa_flag.isnot(None)), Scope3Emission),
                Scope3Emission
            ).limit(_MAX_FLAGGED_RECORDS).all()

        si = io.StringIO()
        cw = csv.writer(si)

        cw.writerow([
            "Record ID", "Scope", "Facility ID", "Year", "Month",
            "Process / Source Type", "Issue (QA Flag)", "Emissions (tCO2e)", "Status"
        ])

        def _sanitize_csv(val):
            if val is None:
                return ""
            s = str(val)
            stripped = s.lstrip()
            if stripped and stripped.startswith(("=", "+", "-", "@", "\t", "\r", "%")):
                return f"'{s}"
            return s

        for r in q1:
            cw.writerow([
                _sanitize_csv(r.record_id or r.id),
                1,
                r.facility_id,
                r.year,
                r.month,
                _sanitize_csv(r.process_type),
                _sanitize_csv(r.qa_flag),
                r.co2e_total if r.co2e_total is not None else 0.0,
                _sanitize_csv(r.status),
            ])
        for r in q2:
            cw.writerow([
                _sanitize_csv(f"S2-{r.id}"),
                2,
                r.facility_id,
                r.year,
                r.month,
                _sanitize_csv(r.source_type),
                _sanitize_csv(r.qa_flag),
                r.co2e if r.co2e is not None else 0.0,
                _sanitize_csv(r.status),
            ])
        for r in q3:
            cw.writerow([
                _sanitize_csv(f"S3-{r.id}"),
                3,
                r.facility_id,
                r.year,
                r.month,
                _sanitize_csv(r.category),
                _sanitize_csv(r.qa_flag),
                r.co2e if r.co2e is not None else 0.0,
                _sanitize_csv(r.status),
            ])

        output = si.getvalue()
        return Response(
            output,
            mimetype="text/csv",
            headers={"Content-Disposition": "attachment;filename=qa_qc_report.csv"},
        )
    except Exception as e:
        return internal_error(e, status_text="error", message="Internal server error")


_RESOLUTIONS = {"Verified": "approve", "Rejected": "reject"}
_DEFAULT_REJECT_REASON = "Rejected in QA/QC review"


def _scope_of(value):
    """"1", "2" or "3"; None for anything else (an unknown scope used to be read as Scope 3)."""
    s = str(value if value is not None else 1).strip()
    return s if s in ("1", "2", "3") else None


def _tag_qa_flags(model, flags, resolution, reason):
    """Keep each decided record's QA flag text, marked with the decision (`flags`: id -> flag before)."""
    for rid, flag in flags.items():
        rec = db.session.get(model, rid)
        if rec is None:
            continue
        flag = flag or "Manually reviewed"
        rec.qa_flag = (f"[Verified] {flag}" if resolution == "Verified" else f"Rejected: {reason} ({flag})")[:255]


def _skip_reason(model, rid, user, allowed):
    from services.maker_checker import REVIEWABLE_STATUSES

    rec = db.session.get(model, rid)
    if rec is None:
        return "not_found"
    if allowed is not None and rec.facility_id not in allowed:
        return "access_denied"
    if rec.status not in REVIEWABLE_STATUSES:
        return "not_awaiting_review"
    return "maker_checker_violation"


@qaqc_bp.route("/resolve/<int:record_id>", methods=["POST"])
@login_required
def resolve_flagged_record(record_id):
    """Approve ("Verified") or reject ("Rejected") one flagged record under the review queue's rules
    (services.maker_checker): only records awaiting review, never your own, decided atomically. This route
    used to set the status directly: it verified drafts and flipped decided records (review 2026-10-15)."""
    from services.maker_checker import RECORD_TYPES, DecisionError, decide_single

    user = get_current_user()
    if not _is_admin_or_superuser(user):
        return jsonify({"error": "Admin or Superuser privileges required"}), 403

    data = request.get_json() or {}
    resolution = data.get("resolution", "Verified")
    if resolution not in _RESOLUTIONS:
        return jsonify({"error": "Invalid resolution. Must be 'Verified' or 'Rejected'"}), 400
    scope = _scope_of(data.get("scope", 1))
    if scope is None:
        return jsonify({"error": "Invalid scope. Must be 1, 2 or 3", "field": "scope"}), 400
    reason = str(data.get("reason") or _DEFAULT_REJECT_REASON).strip()
    model = RECORD_TYPES[scope][0]

    record = db.session.get(model, record_id)
    allowed = get_allowed_facility_ids(user)
    if (record is not None and resolution == "Verified" and (allowed is None or record.facility_id in allowed)
            and user.id in {record.created_by, getattr(record, "updated_by", None)}):
        return jsonify({"error": "Maker-checker violation: users cannot verify records they created or updated"}), 403
    flag = record.qa_flag if record is not None else None

    try:
        decide_single(user, scope, record_id, _RESOLUTIONS[resolution], reason, request)
        db.session.expire_all()  # the decision is a bulk UPDATE: reload before tagging the flag
        _tag_qa_flags(model, {record_id: flag}, resolution, reason)
        db.session.commit()
    except DecisionError as err:
        db.session.rollback()
        return jsonify({"error": err.message}), err.status
    except Exception as e:
        db.session.rollback()
        return internal_error(e, status_text="error", message="Internal server error")

    try:
        from routes.dashboard import clear_dashboard_cache
        clear_dashboard_cache()
    except Exception:
        pass
    return jsonify({"message": f"Record {record_id} resolved as '{resolution}'."})


@qaqc_bp.route("/bulk-resolve", methods=["POST"])
@login_required
def bulk_resolve():
    """
    Bulk approve or reject a list of flagged records, under the same rules as /resolve.
    Payload: { "records": [{"id": 1, "scope": 1}, ...], "resolution": "Verified" | "Rejected", "reason": "..." }
    Records that cannot be decided are listed in "skipped" with the reason.
    """
    from services.maker_checker import RECORD_TYPES, DecisionError, decide

    user = get_current_user()
    if not _is_admin_or_superuser(user):
        return jsonify({"error": "Admin or Superuser privileges required"}), 403

    data = request.get_json() or {}
    items = data.get("records", [])
    resolution = data.get("resolution", "Verified")
    if resolution not in _RESOLUTIONS:
        return jsonify({"error": "Invalid resolution. Use 'Verified' or 'Rejected'."}), 400
    if not isinstance(items, list) or not items:
        return jsonify({"error": "No records provided."}), 400

    by_scope = {}
    for i, item in enumerate(items):
        if not isinstance(item, dict):
            return jsonify({"error": f"records[{i}] must be an object with id and scope", "field": "records"}), 400
        scope = _scope_of(item.get("scope", 1))
        try:
            rid = int(item.get("id"))
        except (TypeError, ValueError):
            rid = None
        if scope is None or rid is None:
            return jsonify({"error": f"records[{i}] needs a numeric id and a scope of 1, 2 or 3",
                            "field": "records"}), 400
        by_scope.setdefault(scope, []).append(rid)

    reason = str(data.get("reason") or _DEFAULT_REJECT_REASON).strip()
    allowed = get_allowed_facility_ids(user)
    resolved_count = 0
    skipped = []
    try:
        for scope, ids in by_scope.items():
            model = RECORD_TYPES[scope][0]
            flags = dict(model.query.filter(model.id.in_(ids)).with_entities(model.id, model.qa_flag).all())
            done = set(decide(user, scope, ids, _RESOLUTIONS[resolution], reason, request))
            db.session.expire_all()
            _tag_qa_flags(model, {rid: flags.get(rid) for rid in done}, resolution, reason)
            resolved_count += len(done)
            skipped += [{"id": rid, "scope": int(scope), "reason": _skip_reason(model, rid, user, allowed)}
                        for rid in dict.fromkeys(ids) if rid not in done]
        db.session.commit()
    except DecisionError as err:
        db.session.rollback()
        return jsonify({"error": err.message}), err.status
    except Exception as e:
        db.session.rollback()
        return internal_error(e, status_text="error", message="Internal server error")

    try:
        from routes.dashboard import clear_dashboard_cache
        clear_dashboard_cache()
    except Exception:
        pass

    message = f"Resolved {resolved_count} records."
    if skipped:
        message += f" {len(skipped)} could not be decided (not awaiting review, outside your scope or your own)."
    return jsonify({"message": message, "resolved_count": resolved_count, "skipped": skipped})
