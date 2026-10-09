"""Approve, reject, ERP sync and pending-list routes for Scope 1 emissions.

Split out of routes/emissions.py unchanged (hardening plan, task 5.3). The routes are
registered on the same ``emissions_bp`` blueprint, so URLs and endpoint names are the same.
"""
from extensions import db
from flask import jsonify, request
from models import Emission, Scope2Emission, Scope3Emission
from routes.auth import login_required
from utils import get_allowed_facility_ids, get_current_user, internal_error
from . import emissions_bp


@emissions_bp.route("/approve/<int:emission_id>", methods=["POST"])
@login_required
def approve_emission(emission_id):
    """Approve a single record awaiting review (Scope 1, 2, 3 or CAP) — RC-2 state machine."""
    from services.maker_checker import DecisionError, decide_single

    req_data = request.get_json(silent=True) or {}
    scope = str(req_data.get("scope") or request.args.get("scope") or "1")
    try:
        decide_single(get_current_user(), scope, emission_id, "approve", request=request)
        db.session.commit()
    except DecisionError as err:
        db.session.rollback()
        return jsonify({"error": err.message}), err.status
    except Exception as err:
        db.session.rollback()
        return internal_error(err)
    from routes.dashboard import clear_dashboard_cache

    clear_dashboard_cache()
    return jsonify({"success": True, "id": emission_id, "scope": scope, "status": "Verified"})


@emissions_bp.route("/reject/<int:emission_id>", methods=["POST"])
@login_required
def reject_emission(emission_id):
    """Reject a single record awaiting review; decided records cannot be flipped (BUG-070)."""
    from services.maker_checker import DecisionError, decide_single

    req_data = request.get_json(silent=True) or {}
    scope = str(req_data.get("scope") or request.args.get("scope") or "1")
    reason = str(req_data.get("reason") or "Rejected by reviewer")
    try:
        decide_single(get_current_user(), scope, emission_id, "reject", reason=reason, request=request)
        db.session.commit()
    except DecisionError as err:
        db.session.rollback()
        return jsonify({"error": err.message}), err.status
    except Exception as err:
        db.session.rollback()
        return internal_error(err)
    from routes.dashboard import clear_dashboard_cache

    clear_dashboard_cache()
    return jsonify({"success": True, "id": emission_id, "scope": scope, "status": "Rejected", "reason": reason})


def _batch_decide(decision):
    """(decided ids, skipped records with the reason) of a batch call, or an error response."""
    from services.maker_checker import DecisionError
    from services.review_batch import run_batch

    try:
        done, skipped = run_batch(get_current_user(), request.get_json(silent=True) or {}, decision, request)
        db.session.commit()
    except DecisionError as err:
        db.session.rollback()
        return jsonify({"error": err.message}), err.status
    except Exception as err:
        db.session.rollback()
        return internal_error(err)
    from routes.dashboard import clear_dashboard_cache

    clear_dashboard_cache()
    return done, skipped


@emissions_bp.route("/approve/batch", methods=["POST"])
@login_required
def approve_batch_emissions():
    """Approve records awaiting review. Body: {by_scope: {"1": [...], ...}} or {scope, ids} or {scope: "all", approve_all: true}.
    Records the caller created or last modified are skipped (segregation of duties)."""
    result = _batch_decide("approve")
    if not (isinstance(result, tuple) and isinstance(result[0], list)):
        return result  # an error response (body, status)
    done, skipped = result
    return jsonify({"success": True, "approved_count": len(done), "approved_ids": done,
                    "skipped_count": len(skipped), "skipped": skipped})


@emissions_bp.route("/reject/batch", methods=["POST"])
@login_required
def reject_batch_emissions():
    """Reject records awaiting review (soft: status Rejected, excluded from totals)."""
    result = _batch_decide("reject")
    if not (isinstance(result, tuple) and isinstance(result[0], list)):
        return result  # an error response (body, status)
    done, skipped = result
    return jsonify({"success": True, "deleted_count": len(done), "rejected_count": len(done), "rejected_ids": done,
                    "skipped_count": len(skipped), "skipped": skipped})


@emissions_bp.route("/erp/sync", methods=["POST"])
@login_required
def trigger_erp_sync():
    """ERP integration endpoint. No ERP connector is implemented: the former "mock" sync inserted three
    invented Scope 3 records (fixed spend, factors and co2e, "SAP Ariba Inv #9921") into the inventory
    when ENABLE_MOCK_ERP was set; it is removed and the endpoint says so."""
    user = get_current_user()
    if not user or user.role not in ["admin", "superuser"]:
        return jsonify({"error": "Admin privileges required for ERP sync"}), 403
    return jsonify({"error": "No ERP connector is configured. Import ERP spend or activity data with the "
                             "Scope 3 file upload."}), 501


@emissions_bp.route("/pending", methods=["GET"])
@login_required
def get_pending_emissions():
    """Get all pending emissions across Scope 1, 2, 3 for the reviewer dashboard.
    Query params: ?all=true (unlimited) or ?limit=200
    """
    user = get_current_user()
    if not user or user.role not in ["admin", "superuser"]:
        return jsonify({"error": "Insufficient permissions"}), 403

    allowed_fids = get_allowed_facility_ids(user)
    # drafts are the maker's unsubmitted work: they enter review only when submitted (browser test)
    pending_statuses = ["Pending", "Pending Approval", "Pending Review"]
    fetch_all = request.args.get("all", "").lower() == "true"
    if fetch_all:
        limit_val = None
    else:
        try:
            limit_val = max(1, min(1000, int(request.args.get("limit", 200))))
        except (ValueError, TypeError):
            limit_val = 200

    def q_scope1():
        q = Emission.query.filter(Emission.status.in_(pending_statuses))
        if allowed_fids is not None:
            q = q.filter(Emission.facility_id.in_(allowed_fids))
        q = q.order_by(Emission.timestamp.desc())
        if limit_val:
            q = q.limit(limit_val)
        return [
            {
                "id": e.id, "scope": "1", "facility_id": e.facility_id,
                "facility_name": e.facility.name if getattr(e, "facility", None) else None,
                "year": e.year, "month": e.month, "process_type": e.process_type,
                "fuel_type": e.fuel_type, "quantity": e.quantity, "unit": e.unit,
                "co2e_total": e.co2e_total, "status": e.status, 
                "qa_flag": getattr(e, "qa_flag", None),
                "emission_factor": getattr(e, "emission_factor", None),
                "created_by": getattr(e, "created_by", None),
                "created_at": e.timestamp.isoformat() if e.timestamp else None,
            }
            for e in q.all()
        ]

    def q_scope2():
        q = Scope2Emission.query.filter(Scope2Emission.status.in_(pending_statuses))
        if allowed_fids is not None:
            q = q.filter(Scope2Emission.facility_id.in_(allowed_fids))
        q = q.order_by(Scope2Emission.created_at.desc())
        if limit_val:
            q = q.limit(limit_val)
        return [
            {
                "id": e.id, "scope": "2", "facility_id": e.facility_id,
                "facility_name": e.facility.name if getattr(e, "facility", None) else None,
                "year": e.year, "month": e.month, "source_type": e.source_type,
                "electricity_kwh": e.electricity_kwh, "heat_mmbtu": getattr(e, "heat_mmbtu", None),
                "co2e": e.co2e, "status": e.status,
                "qa_flag": getattr(e, "qa_flag", None),
                "emission_factor": getattr(e, "emission_factor", None),
                "created_by": getattr(e, "created_by", None),
                "created_at": e.created_at.isoformat() if e.created_at else None,
            }
            for e in q.all()
        ]

    def q_scope3():
        q = Scope3Emission.query.filter(Scope3Emission.status.in_(pending_statuses))
        if allowed_fids is not None:
            q = q.filter(Scope3Emission.facility_id.in_(allowed_fids))
        q = q.order_by(Scope3Emission.created_at.desc())
        if limit_val:
            q = q.limit(limit_val)
        return [
            {
                "id": e.id, "scope": "3", "facility_id": e.facility_id,
                "facility_name": e.facility.name if getattr(e, "facility", None) else None,
                "year": e.year, "month": e.month, "category": e.category,
                "sub_category": getattr(e, "sub_category", None),
                "activity_data": getattr(e, "activity_data", None),
                "unit": getattr(e, "unit", None),
                "co2e": e.co2e, "status": e.status,
                "qa_flag": getattr(e, "qa_flag", None),
                "emission_factor": getattr(e, "emission_factor", None),
                "created_by": getattr(e, "created_by", None),
                "created_at": e.created_at.isoformat() if e.created_at else None,
            }
            for e in q.all()
        ]

    def count_pending(model):
        q = model.query.filter(model.status.in_(pending_statuses))
        if allowed_fids is not None:
            q = q.filter(model.facility_id.in_(allowed_fids))
        return q.count()

    counts = {"1": count_pending(Emission), "2": count_pending(Scope2Emission), "3": count_pending(Scope3Emission)}

    def sum_pending(model, col):
        q = db.session.query(db.func.coalesce(db.func.sum(col), 0.0)).filter(model.status.in_(pending_statuses))
        if allowed_fids is not None:
            q = q.filter(model.facility_id.in_(allowed_fids))
        return float(q.scalar() or 0.0)

    pending_co2e = (sum_pending(Emission, Emission.co2e_total) + sum_pending(Scope2Emission, Scope2Emission.co2e)
                    + sum_pending(Scope3Emission, Scope3Emission.co2e))
    return jsonify({
        "scope1": q_scope1(),
        "scope2": q_scope2(),
        "scope3": q_scope3(),
        # the lists hold at most `limit` rows per scope; the counts are the whole queue
        "pending_counts": counts,
        "pending_co2e": pending_co2e,
        "limit": limit_val,
        "total_pending": sum(counts.values()),
    })
