from flask import Blueprint, jsonify, request, Response
from sqlalchemy import func
from extensions import db
from models import Emission, Scope2Emission, Scope3Emission, ActivityLog, Facility
from routes.auth import login_required, superuser_required
from utils import get_current_user, get_allowed_facility_ids
import csv
import io

qaqc_bp = Blueprint("qaqc_bp", __name__)

# Maximum number of flagged records returned per request (prevents OOM on large DBs)
_MAX_FLAGGED_RECORDS = 500


def _is_admin_or_superuser(user):
    """Returns True if the user has QA/QC viewing rights (admin or superuser roles)."""
    return user and user.role in ["admin", "superuser", "it_admin"]


@qaqc_bp.route("/dashboard", methods=["GET"])
@login_required
def get_qaqc_dashboard():
    """
    Returns aggregated uncertainty (IPCC SRSS) and flagged anomaly records.
    Scoped to the requesting user's allowed facilities.
    Access: admin, superuser, it_admin only.
    """
    user = get_current_user()
    if not _is_admin_or_superuser(user):
        return jsonify({"error": "Admin or Superuser privileges required"}), 403

    try:
        # --- Resolve allowed facility IDs for RBAC scoping ---
        allowed_fids = get_allowed_facility_ids(user)  # None = all, [] = none

        # Optional filter params
        year_arg = request.args.get("year")
        scope_arg = request.args.get("scope")  # "1", "2", "3", or "all"
        limit = min(int(request.args.get("limit", _MAX_FLAGGED_RECORDS)), _MAX_FLAGGED_RECORDS)
        offset = int(request.args.get("offset", 0))

        # ── Helper: apply facility filter ──────────────────────────────────
        def _fac_filter(q, model):
            if allowed_fids is not None:
                q = q.filter(model.facility_id.in_(allowed_fids))
            if year_arg and year_arg not in ["all", ""]:
                try:
                    q = q.filter(model.year == int(year_arg))
                except ValueError:
                    pass
            return q

        # ── Flagged anomaly queries ──────────────────────────────────────────
        flagged_records = []
        total_flagged = 0

        if scope_arg in [None, "all", "1"]:
            q1 = Emission.query.filter(Emission.qa_flag.isnot(None))
            q1 = _fac_filter(q1, Emission)
            total_flagged += q1.count()
            for r in q1.order_by(Emission.timestamp.desc()).offset(offset).limit(limit):
                flagged_records.append({
                    "id": r.id,
                    "record_id": r.record_id,
                    "scope": 1,
                    "facility_id": r.facility_id,
                    "year": r.year,
                    "month": r.month,
                    "process_type": r.process_type,
                    "qa_flag": r.qa_flag,
                    "status": r.status,
                    "co2e": r.co2e_total,
                })

        if scope_arg in [None, "all", "2"]:
            q2 = Scope2Emission.query.filter(Scope2Emission.qa_flag.isnot(None))
            q2 = _fac_filter(q2, Scope2Emission)
            total_flagged += q2.count()
            for r in q2.order_by(Scope2Emission.created_at.desc()).offset(offset).limit(limit):
                flagged_records.append({
                    "id": r.id,
                    "record_id": None,
                    "scope": 2,
                    "facility_id": r.facility_id,
                    "year": r.year,
                    "month": r.month,
                    "process_type": r.source_type,
                    "qa_flag": r.qa_flag,
                    "status": r.status,
                    "co2e": r.co2e,
                })

        if scope_arg in [None, "all", "3"]:
            q3 = Scope3Emission.query.filter(Scope3Emission.qa_flag.isnot(None))
            q3 = _fac_filter(q3, Scope3Emission)
            total_flagged += q3.count()
            for r in q3.order_by(Scope3Emission.created_at.desc()).offset(offset).limit(limit):
                flagged_records.append({
                    "id": r.id,
                    "record_id": None,
                    "scope": 3,
                    "facility_id": r.facility_id,
                    "year": r.year,
                    "month": r.month,
                    "process_type": r.category,
                    "qa_flag": r.qa_flag,
                    "status": r.status,
                    "co2e": r.co2e,
                })

        # Sort combined list by co2e descending so highest-impact anomalies appear first
        flagged_records.sort(key=lambda x: (x["co2e"] or 0), reverse=True)

        # ── Uncertainty aggregation (IPCC SRSS — scoped to allowed facilities) ──
        # Scope 1
        s1_q = _fac_filter(Emission.query, Emission)
        s1_rows = s1_q.with_entities(
            Emission.co2e_total,
            Emission.uncertainty_pct,
            Emission.uncertainty,
        ).all()
        s1_total = sum((r[0] or 0) for r in s1_rows)
        s1_unc_var = sum(
            (((r[1] or r[2] or 0.05) * (r[0] or 0)) ** 2) for r in s1_rows
        )

        # Scope 2
        s2_q = _fac_filter(Scope2Emission.query, Scope2Emission)
        s2_rows = s2_q.with_entities(
            Scope2Emission.co2e,
            Scope2Emission.uncertainty_pct,
            Scope2Emission.uncertainty,
        ).all()
        s2_total = sum((r[0] or 0) for r in s2_rows)
        s2_unc_var = sum(
            (((r[1] or r[2] or 0.05) * (r[0] or 0)) ** 2) for r in s2_rows
        )

        # Scope 3
        s3_q = _fac_filter(Scope3Emission.query, Scope3Emission)
        s3_rows = s3_q.with_entities(
            Scope3Emission.co2e,
            Scope3Emission.uncertainty_pct,
            Scope3Emission.uncertainty,
        ).all()
        s3_total = sum((r[0] or 0) for r in s3_rows)
        s3_unc_var = sum(
            (((r[1] or r[2] or 0.10) * (r[0] or 0)) ** 2) for r in s3_rows
        )

        total_inventory = s1_total + s2_total + s3_total
        total_unc_var = s1_unc_var + s2_unc_var + s3_unc_var

        overall_uncertainty = (
            (total_unc_var ** 0.5) / total_inventory if total_inventory > 0 else 0
        )

        return jsonify({
            "status": "success",
            "total_flagged_count": total_flagged,
            "returned_count": len(flagged_records),
            "limit": limit,
            "offset": offset,
            "tier1_uncertainty": {
                "overall": overall_uncertainty,
                "scope1": (s1_unc_var ** 0.5) / s1_total if s1_total > 0 else 0,
                "scope2": (s2_unc_var ** 0.5) / s2_total if s2_total > 0 else 0,
                "scope3": (s3_unc_var ** 0.5) / s3_total if s3_total > 0 else 0,
                "s1_total_tco2e": s1_total,
                "s2_total_tco2e": s2_total,
                "s3_total_tco2e": s3_total,
            },
            "flagged_records": flagged_records,
        })

    except Exception as e:
        import traceback
        from flask import current_app
        current_app.logger.error(f"[QAQC] Dashboard error: {e}\n{traceback.format_exc()}")
        return jsonify({"status": "error", "message": str(e)}), 500


@qaqc_bp.route("/export", methods=["GET"])
@login_required
def export_qaqc_report():
    """
    Exports QA/QC anomaly data as a CSV file.
    Access: admin, superuser, it_admin only.
    Uses standard GET with session cookie — must be called via Axios with
    responseType='blob', not window.open (which doesn't carry session).
    """
    user = get_current_user()
    if not _is_admin_or_superuser(user):
        return jsonify({"error": "Admin or Superuser privileges required"}), 403

    try:
        allowed_fids = get_allowed_facility_ids(user)

        def _fac_filter(q, model):
            if allowed_fids is not None:
                q = q.filter(model.facility_id.in_(allowed_fids))
            return q

        q1 = _fac_filter(
            Emission.query.filter(Emission.qa_flag.isnot(None)), Emission
        ).limit(_MAX_FLAGGED_RECORDS).all()
        q2 = _fac_filter(
            Scope2Emission.query.filter(Scope2Emission.qa_flag.isnot(None)), Scope2Emission
        ).limit(_MAX_FLAGGED_RECORDS).all()
        q3 = _fac_filter(
            Scope3Emission.query.filter(Scope3Emission.qa_flag.isnot(None)), Scope3Emission
        ).limit(_MAX_FLAGGED_RECORDS).all()

        si = io.StringIO()
        cw = csv.writer(si)

        cw.writerow([
            "Record ID", "Scope", "Facility ID", "Year", "Month",
            "Process / Source Type", "Issue (QA Flag)", "Emissions (tCO2e)", "Status"
        ])

        for r in q1:
            cw.writerow([
                r.id, 1, r.facility_id, r.year, r.month,
                r.process_type, r.qa_flag, r.co2e_total, r.status,
            ])
        for r in q2:
            cw.writerow([
                r.id, 2, r.facility_id, r.year, r.month,
                r.source_type, r.qa_flag, r.co2e, r.status,
            ])
        for r in q3:
            cw.writerow([
                r.id, 3, r.facility_id, r.year, r.month,
                r.category, r.qa_flag, r.co2e, r.status,
            ])

        output = si.getvalue()
        return Response(
            output,
            mimetype="text/csv",
            headers={"Content-Disposition": "attachment;filename=qa_qc_report.csv"},
        )
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@qaqc_bp.route("/resolve/<int:record_id>", methods=["POST"])
@login_required
def resolve_flagged_record(record_id):
    """
    Marks a flagged Scope 1 record as reviewed by clearing its qa_flag
    and updating its status. Called from the QA dashboard 'Resolve' action.
    """
    user = get_current_user()
    if not _is_admin_or_superuser(user):
        return jsonify({"error": "Admin or Superuser privileges required"}), 403

    data = request.get_json() or {}
    scope = data.get("scope", 1)
    resolution = data.get("resolution", "Verified")  # "Verified" or "Rejected"

    try:
        allowed_fids = get_allowed_facility_ids(user)

        if scope == 1:
            record = Emission.query.get(record_id)
            co2e_field = record.co2e_total if record else None
        elif scope == 2:
            record = Scope2Emission.query.get(record_id)
            co2e_field = record.co2e if record else None
        else:
            record = Scope3Emission.query.get(record_id)
            co2e_field = record.co2e if record else None

        if not record:
            return jsonify({"error": "Record not found"}), 404

        # RBAC: verify this record belongs to an allowed facility
        if allowed_fids is not None and record.facility_id not in allowed_fids:
            return jsonify({"error": "Access denied to this record"}), 403

        # Clear the anomaly flag and update status
        record.qa_flag = None
        record.status = resolution

        from utils import log_activity_and_notify
        log_activity_and_notify(
            action="UPDATE",
            record_id=str(record_id),
            user=user,
            request=request,
            entity=f"Scope{scope}Emission",
            details=f"QA flag resolved by {user.fullName}. Resolution: {resolution}",
        )
        db.session.commit()

        return jsonify({"message": f"Record {record_id} resolved as '{resolution}'."})

    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500


@qaqc_bp.route("/bulk-resolve", methods=["POST"])
@login_required
def bulk_resolve():
    """
    Bulk approve or reject a list of flagged records.
    Payload: { "records": [{"id": 1, "scope": 1}, ...], "resolution": "Verified" | "Rejected" }
    """
    user = get_current_user()
    if not _is_admin_or_superuser(user):
        return jsonify({"error": "Admin or Superuser privileges required"}), 403

    data = request.get_json() or {}
    records_to_resolve = data.get("records", [])
    resolution = data.get("resolution", "Verified")

    if resolution not in ["Verified", "Rejected"]:
        return jsonify({"error": "Invalid resolution. Use 'Verified' or 'Rejected'."}), 400

    if not records_to_resolve:
        return jsonify({"error": "No records provided."}), 400

    allowed_fids = get_allowed_facility_ids(user)
    resolved_count = 0
    skipped = []

    try:
        for item in records_to_resolve:
            rid = item.get("id")
            scope = item.get("scope", 1)

            if scope == 1:
                record = Emission.query.get(rid)
            elif scope == 2:
                record = Scope2Emission.query.get(rid)
            else:
                record = Scope3Emission.query.get(rid)

            if not record:
                skipped.append({"id": rid, "reason": "not_found"})
                continue

            if allowed_fids is not None and record.facility_id not in allowed_fids:
                skipped.append({"id": rid, "reason": "access_denied"})
                continue

            record.qa_flag = None
            record.status = resolution
            resolved_count += 1

        from utils import log_activity_and_notify
        log_activity_and_notify(
            action="UPDATE",
            record_id="bulk",
            user=user,
            request=request,
            entity="QABulkResolve",
            details=f"Bulk resolved {resolved_count} records as '{resolution}' by {user.fullName}.",
        )
        db.session.commit()

        return jsonify({
            "message": f"Resolved {resolved_count} records.",
            "resolved_count": resolved_count,
            "skipped": skipped,
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500
