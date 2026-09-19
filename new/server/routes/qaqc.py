from flask import Blueprint, jsonify, request, Response
from sqlalchemy import func, distinct, or_, and_
from datetime import datetime, timezone, timedelta
from extensions import db
from models import Emission, Scope2Emission, Scope3Emission, ActivityLog, Facility, CustomFactor
from routes.auth import login_required, superuser_required
from utils import get_current_user, get_allowed_facility_ids
import csv
import io
from process_categories import NON_COMBUSTION_PROCESSES

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
        try:
            limit = max(1, min(int(request.args.get("limit", 100)), _MAX_FLAGGED_RECORDS))
        except (ValueError, TypeError):
            limit = 100
        try:
            offset = max(0, int(request.args.get("offset", 0)))
        except (ValueError, TypeError):
            offset = 0

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
        all_flagged = []
        total_flagged = 0

        if scope_arg in [None, "all", "1"]:
            q1 = Emission.query.filter(Emission.qa_flag.isnot(None))
            q1 = _fac_filter(q1, Emission)
            total_flagged += q1.count()
            if scope_arg == "1":
                q1 = q1.order_by(Emission.timestamp.desc()).offset(offset).limit(limit)
            else:
                q1 = q1.order_by(Emission.timestamp.desc()).limit(_MAX_FLAGGED_RECORDS)
            for r in q1:
                all_flagged.append({
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
            if scope_arg == "2":
                q2 = q2.order_by(Scope2Emission.created_at.desc()).offset(offset).limit(limit)
            else:
                q2 = q2.order_by(Scope2Emission.created_at.desc()).limit(_MAX_FLAGGED_RECORDS)
            for r in q2:
                all_flagged.append({
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
            if scope_arg == "3":
                q3 = q3.order_by(Scope3Emission.created_at.desc()).offset(offset).limit(limit)
            else:
                q3 = q3.order_by(Scope3Emission.created_at.desc()).limit(_MAX_FLAGGED_RECORDS)
            for r in q3:
                all_flagged.append({
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

        # When querying all scopes together, sort uniformly and slice [offset:offset+limit]
        if scope_arg in [None, "all"]:
            all_flagged.sort(key=lambda x: (x["co2e"] or 0), reverse=True)
            flagged_records = all_flagged[offset : offset + limit]
        else:
            all_flagged.sort(key=lambda x: (x["co2e"] or 0), reverse=True)
            flagged_records = all_flagged

        # ── Uncertainty aggregation (IPCC SRSS — scoped to allowed facilities) ──
        def _norm_unc(pct_val, frac_val, default_val=0.05):
            if pct_val is not None:
                try:
                    return float(pct_val) / 100.0
                except (ValueError, TypeError):
                    pass
            if frac_val is not None:
                try:
                    fval = float(frac_val)
                    return (fval / 100.0) if fval > 1.0 else fval
                except (ValueError, TypeError):
                    pass
            return default_val

        # Scope 1
        s1_q = _fac_filter(Emission.query, Emission)
        s1_rows = s1_q.with_entities(
            Emission.co2e_total,
            Emission.uncertainty_pct,
            Emission.uncertainty,
        ).all()
        s1_total = sum((r[0] or 0) for r in s1_rows)
        s1_unc_var = sum(
            ((_norm_unc(r[1], r[2], 0.05) * (r[0] or 0)) ** 2) for r in s1_rows
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
            ((_norm_unc(r[1], r[2], 0.05) * (r[0] or 0)) ** 2) for r in s2_rows
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
            ((_norm_unc(r[1], r[2], 0.10) * (r[0] or 0)) ** 2) for r in s3_rows
        )

        total_inventory = s1_total + s2_total + s3_total
        total_unc_var = s1_unc_var + s2_unc_var + s3_unc_var

        overall_uncertainty = (
            (total_unc_var ** 0.5) / total_inventory if total_inventory > 0 else 0
        )

        # ── Diagnostic & Data Health Analysis (SQL-speed) ───────────────────
        cutoff_30d = datetime.now(timezone.utc) - timedelta(days=30)

        # Scoped queries for counts
        q_s1_all = _fac_filter(Emission.query, Emission)
        q_s2_all = _fac_filter(Scope2Emission.query, Scope2Emission)
        q_s3_all = _fac_filter(Scope3Emission.query, Scope3Emission)

        s1_count = q_s1_all.count()
        s2_count = q_s2_all.count()
        s3_count = q_s3_all.count()
        total_records_count = s1_count + s2_count + s3_count

        # Recent activity (last 30 days)
        try:
            recent_s1 = q_s1_all.filter(Emission.timestamp >= cutoff_30d).count()
        except Exception:
            recent_s1 = 0
        try:
            recent_s2 = q_s2_all.filter(Scope2Emission.created_at >= cutoff_30d).count()
        except Exception:
            recent_s2 = 0
        try:
            recent_s3 = q_s3_all.filter(Scope3Emission.created_at >= cutoff_30d).count()
        except Exception:
            recent_s3 = 0
        recent_records_count = recent_s1 + recent_s2 + recent_s3

        # Field-level gap checks on Scope 1
        if allowed_fids is not None:
            missing_facility_count = 0
        else:
            missing_fac_q = Emission.query.filter(Emission.facility_id.is_(None))
            if year_arg and year_arg not in ["all", ""]:
                try:
                    missing_fac_q = missing_fac_q.filter(Emission.year == int(year_arg))
                except ValueError:
                    pass
            missing_facility_count = missing_fac_q.count()

        # Fuel check applies strictly to combustion processes or unspecified process types
        comb_q = q_s1_all.filter(
            or_(
                Emission.process_type.is_(None),
                ~Emission.process_type.in_(NON_COMBUSTION_PROCESSES),
            )
        )
        comb_count = comb_q.count()
        missing_fuel_count = comb_q.filter(
            or_(
                Emission.fuel_type.is_(None),
                Emission.fuel_type == "",
            )
        ).count()
        missing_amount_count = q_s1_all.filter(
            or_(Emission.quantity.is_(None), Emission.quantity <= 0)
        ).count()
        missing_co2e_count = q_s1_all.filter(
            or_(Emission.co2e_total.is_(None), Emission.co2e_total < 0)
        ).count()

        # Facilities coverage (scoped to allowed facilities and reporting year)
        if allowed_fids is not None:
            total_facilities = len(allowed_fids)
        else:
            total_facilities = Facility.query.count()

        # Check active facilities across Scope 1, Scope 2, and Scope 3
        def _get_active_fids(model):
            q = db.session.query(distinct(model.facility_id)).filter(model.facility_id.isnot(None))
            if allowed_fids is not None:
                q = q.filter(model.facility_id.in_(allowed_fids))
            if year_arg and year_arg not in ["all", ""]:
                try:
                    q = q.filter(model.year == int(year_arg))
                except ValueError:
                    pass
            return set(r[0] for r in q.all())

        active_fids = _get_active_fids(Emission) | _get_active_fids(Scope2Emission) | _get_active_fids(Scope3Emission)
        unused_facilities = max(0, total_facilities - len(active_fids))

        # Custom factors
        try:
            total_custom_factors = CustomFactor.query.count()
        except Exception:
            total_custom_factors = 0

        # Status counts for flagged records
        pending_anomalies = 0
        verified_anomalies = 0
        rejected_anomalies = 0

        q1_flags = Emission.query.filter(Emission.qa_flag.isnot(None))
        q1_flags = _fac_filter(q1_flags, Emission)
        pending_anomalies += q1_flags.filter(
            or_(Emission.status.ilike("%pending%"), Emission.status.is_(None))
        ).count()
        verified_anomalies += q1_flags.filter(Emission.status.ilike("%verified%")).count()
        rejected_anomalies += q1_flags.filter(Emission.status.ilike("%rejected%")).count()

        q2_flags = Scope2Emission.query.filter(Scope2Emission.qa_flag.isnot(None))
        q2_flags = _fac_filter(q2_flags, Scope2Emission)
        pending_anomalies += q2_flags.filter(
            or_(Scope2Emission.status.ilike("%pending%"), Scope2Emission.status.is_(None))
        ).count()
        verified_anomalies += q2_flags.filter(Scope2Emission.status.ilike("%verified%")).count()
        rejected_anomalies += q2_flags.filter(Scope2Emission.status.ilike("%rejected%")).count()

        q3_flags = Scope3Emission.query.filter(Scope3Emission.qa_flag.isnot(None))
        q3_flags = _fac_filter(q3_flags, Scope3Emission)
        pending_anomalies += q3_flags.filter(
            or_(Scope3Emission.status.ilike("%pending%"), Scope3Emission.status.is_(None))
        ).count()
        verified_anomalies += q3_flags.filter(Scope3Emission.status.ilike("%verified%")).count()
        rejected_anomalies += q3_flags.filter(Scope3Emission.status.ilike("%rejected%")).count()

        # Completeness rates per dimension
        if s1_count > 0:
            fac_completeness = round(max(0.0, (s1_count - missing_facility_count) / s1_count * 100), 1)
            fuel_completeness = round(max(0.0, (comb_count - missing_fuel_count) / comb_count * 100), 1) if comb_count > 0 else 100.0
            amount_completeness = round(max(0.0, (s1_count - missing_amount_count) / s1_count * 100), 1)
            calc_completeness = round(max(0.0, (s1_count - missing_co2e_count) / s1_count * 100), 1)
            overall_completeness = round(
                (fac_completeness + fuel_completeness + amount_completeness + calc_completeness) / 4, 1
            )
        else:
            fac_completeness = 100.0
            fuel_completeness = 100.0
            amount_completeness = 100.0
            calc_completeness = 100.0
            overall_completeness = 100.0

        # Structured diagnostic findings
        issues = []
        warnings = []
        suggestions = []

        if missing_facility_count > 0:
            issues.append({
                "id": "missing_facility",
                "type": "critical",
                "title": "Unassigned Facility Boundary",
                "description": f"{missing_facility_count} emission record(s) lack facility assignment, breaking GHG Protocol organizational boundary requirements.",
                "affected_count": missing_facility_count,
                "impact": "High",
                "action": "Assign Facilities",
                "action_tab": "queue",
            })

        if missing_co2e_count > 0:
            issues.append({
                "id": "missing_co2e",
                "type": "critical",
                "title": "Uncalculated Emission Values",
                "description": f"{missing_co2e_count} record(s) have uncalculated or negative CO₂e totals.",
                "affected_count": missing_co2e_count,
                "impact": "High",
                "action": "Recalculate",
                "action_tab": "queue",
            })

        if missing_fuel_count > 0:
            warnings.append({
                "id": "missing_fuel",
                "type": "warning",
                "title": "Missing Fuel or Source Classification",
                "description": f"{missing_fuel_count} Scope 1 combustion record(s) are missing explicit fuel or process types, using generic defaults.",
                "affected_count": missing_fuel_count,
                "impact": "Medium",
                "action": "Classify Sources",
                "action_tab": "queue",
            })

        if missing_amount_count > 0:
            warnings.append({
                "id": "missing_amount",
                "type": "warning",
                "title": "Zero or Null Activity Quantities",
                "description": f"{missing_amount_count} record(s) contain zero or unrecorded activity amounts.",
                "affected_count": missing_amount_count,
                "impact": "Medium",
                "action": "Review Activity",
                "action_tab": "queue",
            })

        if total_records_count > 0 and recent_records_count == 0:
            warnings.append({
                "id": "stale_data",
                "type": "warning",
                "title": "Data Freshness Advisory",
                "description": "No emissions or activity records ingested during the last 30 days.",
                "affected_count": 0,
                "impact": "Low",
                "action": "Check Ingestion",
                "action_tab": "diagnostics",
            })

        if unused_facilities > 0:
            suggestions.append({
                "id": "unused_facilities",
                "type": "info",
                "title": "Inactive Facilities In Scope",
                "description": f"{unused_facilities} facility boundary(ies) are registered in master data but have no emissions reported for this period.",
                "affected_count": unused_facilities,
                "impact": "Low",
                "action": "View Facilities",
                "action_url": "/reference-data",
            })

        if total_custom_factors == 0:
            suggestions.append({
                "id": "no_custom_factors",
                "type": "info",
                "title": "Tier 1 Default Factor Reliance",
                "description": "No custom or site-specific emission factors registered. Adding facility-calibrated factors reduces Tier 1 uncertainty.",
                "affected_count": 0,
                "impact": "Low",
                "action": "Manage Factors",
                "action_url": "/reference-data",
            })

        # Calculate composite health score
        penalty = (len(issues) * 10) + (len(warnings) * 5) + min(15, pending_anomalies * 2)
        health_score = max(0, min(100, int(round(overall_completeness - penalty))))

        diagnostics_data = {
            "health_score": health_score,
            "completeness": overall_completeness,
            "dimension_completeness": {
                "facility": fac_completeness,
                "fuel_source": fuel_completeness,
                "activity_amount": amount_completeness,
                "calculation": calc_completeness,
            },
            "total_records": total_records_count,
            "records_by_scope": {
                "scope1": s1_count,
                "scope2": s2_count,
                "scope3": s3_count,
            },
            "recent_records_30d": recent_records_count,
            "total_facilities": total_facilities,
            "active_facilities": len(active_fids),
            "unused_facilities": unused_facilities,
            "total_custom_factors": total_custom_factors,
            "anomalies_summary": {
                "total": total_flagged,
                "pending": pending_anomalies,
                "verified": verified_anomalies,
                "rejected": rejected_anomalies,
            },
            "issues": issues,
            "warnings": warnings,
            "suggestions": suggestions,
        }

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
            "diagnostics": diagnostics_data,
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

        q1 = []
        q2 = []
        q3 = []
        if scope_arg in [None, "all", "1"]:
            q1 = _fac_filter(
                Emission.query.filter(Emission.qa_flag.isnot(None)), Emission
            ).limit(_MAX_FLAGGED_RECORDS).all()
        if scope_arg in [None, "all", "2"]:
            q2 = _fac_filter(
                Scope2Emission.query.filter(Scope2Emission.qa_flag.isnot(None)), Scope2Emission
            ).limit(_MAX_FLAGGED_RECORDS).all()
        if scope_arg in [None, "all", "3"]:
            q3 = _fac_filter(
                Scope3Emission.query.filter(Scope3Emission.qa_flag.isnot(None)), Scope3Emission
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
        return jsonify({"status": "error", "message": str(e)}), 500


@qaqc_bp.route("/resolve/<int:record_id>", methods=["POST"])
@login_required
def resolve_flagged_record(record_id):
    """
    Marks a flagged record as reviewed by updating status to 'Verified' or 'Rejected'.
    """
    user = get_current_user()
    if not _is_admin_or_superuser(user):
        return jsonify({"error": "Admin or Superuser privileges required"}), 403

    data = request.get_json() or {}
    try:
        scope = int(data.get("scope", 1))
    except (ValueError, TypeError):
        scope = 1
    resolution = data.get("resolution", "Verified")  # "Verified" or "Rejected"

    try:
        allowed_fids = get_allowed_facility_ids(user)

        if scope == 1:
            record = db.session.get(Emission, record_id)
        elif scope == 2:
            record = db.session.get(Scope2Emission, record_id)
        else:
            record = db.session.get(Scope3Emission, record_id)

        if not record:
            return jsonify({"error": "Record not found"}), 404

        # RBAC: verify this record belongs to an allowed facility
        if allowed_fids is not None and record.facility_id not in allowed_fids:
            return jsonify({"error": "Access denied to this record"}), 403

        # Maker-Checker segregation of duties: user cannot verify records they created
        if resolution == "Verified" and getattr(record, "created_by", None) and record.created_by == user.id:
            return jsonify({"error": "Maker-checker violation: users cannot verify records they created"}), 403

        # Update status and tag QA flag for audit preservation
        record.status = resolution
        if record.qa_flag and not record.qa_flag.startswith(f"[{resolution}]"):
            record.qa_flag = f"[{resolution}] {record.qa_flag}"[:255]
        elif not record.qa_flag:
            record.qa_flag = f"[{resolution}] Manually reviewed"

        if hasattr(record, "approved_by"):
            record.approved_by = user.id
        if hasattr(record, "approved_at"):
            record.approved_at = datetime.now(timezone.utc)

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

        try:
            from routes.dashboard import clear_dashboard_cache
            clear_dashboard_cache()
        except Exception:
            pass

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
            try:
                scope = int(item.get("scope", 1))
            except (ValueError, TypeError):
                scope = 1

            if scope == 1:
                record = db.session.get(Emission, rid)
            elif scope == 2:
                record = db.session.get(Scope2Emission, rid)
            else:
                record = db.session.get(Scope3Emission, rid)

            if not record:
                skipped.append({"id": rid, "reason": "not_found"})
                continue

            if allowed_fids is not None and record.facility_id not in allowed_fids:
                skipped.append({"id": rid, "reason": "access_denied"})
                continue

            # Maker-Checker segregation of duties
            if resolution == "Verified" and getattr(record, "created_by", None) and record.created_by == user.id:
                skipped.append({"id": rid, "reason": "maker_checker_violation"})
                continue

            record.status = resolution
            if record.qa_flag and not record.qa_flag.startswith(f"[{resolution}]"):
                record.qa_flag = f"[{resolution}] {record.qa_flag}"[:255]
            elif not record.qa_flag:
                record.qa_flag = f"[{resolution}] Manually reviewed"

            if hasattr(record, "approved_by"):
                record.approved_by = user.id
            if hasattr(record, "approved_at"):
                record.approved_at = datetime.now(timezone.utc)

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

        try:
            from routes.dashboard import clear_dashboard_cache
            clear_dashboard_cache()
        except Exception:
            pass

        return jsonify({
            "message": f"Resolved {resolved_count} records.",
            "resolved_count": resolved_count,
            "skipped": skipped,
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500
