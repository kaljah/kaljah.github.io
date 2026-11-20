"""
Recalculation Action & Base-Year Workflow (Part 2.2)
===================================================
Provides:
1. Impact preview (records affected, tCO2e before/after, delta) by year, facility, scope, factor version, or GWP.
2. Maker-checker approval workflow with GHG Protocol base-year triggers:
   - methodology_change
   - structural_change
   - error_correction
3. Audit logging and record-level provenance snapshot in RecalculationHistory.
"""
import datetime
from flask import Blueprint, request, jsonify, session, current_app
from extensions import db
from models import (
    Emission, Scope2Emission, Scope3Emission, Facility, CustomFactor,
    RecalculationRequest, RecalculationHistory, BaseYearRecalculation, User
)
from routes.auth import login_required, admin_required
from utils import (
    facility_access_error,
    get_allowed_facility_ids,
    get_current_tenant_id,
    get_current_user,
    log_activity_and_notify,
    normalize_tenant_id,
    tenant_matches,
)
from calculations.constants import invalidate_gwp_cache
from services.gwp_recalculation import known_gwp_dict, reweighted_co2e
from services.custom_factor_policy import second_approver_required

recalculate_bp = Blueprint("recalculate", __name__, url_prefix="/api/recalculate")

ALLOWED_TRIGGERS = {
    "methodology_change": "Methodology Change (e.g. updated emission factor, new GWP standard)",
    "structural_change": "Structural Change (e.g. merger, acquisition, divestment, operational control)",
    "error_correction": "Error Correction (e.g. discovery of significant metering or calculation errors)",
}


def _engine_recalc(e, cf, gwp_dict=None):
    """(co2, ch4, n2o, co2e) in tonnes of a Scope 1 record recalculated with a custom factor by the Scope 1 engine.

    Blind audit BA-043: the recalculation multiplied the stored quantity by the kg/MMBtu factor (no unit, no
    heating value; 980x on a scf record) and left the gas masses as they were. The record's saved inputs, unit
    and period go through compute_emissions with the new factor, as an edit would. None when it cannot be re-run.
    """
    import json

    from calculations import compute_emissions
    from calculations.constants import get_active_gwp
    from services.scope1_calc import canonicalize, custom_factor_data

    try:
        stored = json.loads(e.source_payload or "{}")
    except (TypeError, ValueError):
        stored = {}
    if not isinstance(stored, dict):
        stored = {}
    base = {"process_type": e.process_type, "process": e.process_type, "fuel_type": e.fuel_type, "fuel": e.fuel_type,
            "unit": e.unit, "quantity": e.quantity, "amount": e.quantity}
    payload = canonicalize({**base, **{k: v for k, v in stored.items() if v is not None}})
    payload.update(year=e.year, month=e.month, facility_id=e.facility_id, factor_source="custom",
                   custom_factor_id=cf.id)
    try:
        em, _method = compute_emissions(payload, custom_factor_data(cf), gwp_dict=gwp_dict or get_active_gwp())
    except Exception as exc:  # the engine's refusal: the record is left as it is and reported
        current_app.logger.warning("Recalculation of record %s with factor %s refused: %s", e.id, cf.id, exc)
        return None
    return (float(em.get("co2") or 0.0), float(em.get("ch4") or 0.0), float(em.get("n2o") or 0.0),
            float(em.get("totalCo2e") or 0.0))


def _simulate_recalculation(target_year=None, target_facility_id=None, target_scope="all",
                            target_factor_id=None, target_factor_version=None,
                            target_gwp_standard=None, allowed_fids=None, caller_tenant=None):
    """
    Simulates the recalculation across Scope 1, 2, and 3 without persisting changes.
    Returns preview metrics and sample before/after rows scoped to `allowed_fids`.
    """
    gwp_dict = known_gwp_dict(target_gwp_standard) if target_gwp_standard else None  # unknown refused (F-CORE-08)

    # Custom factor lookup if factor_id is specified
    cf = db.session.get(CustomFactor, target_factor_id) if target_factor_id else None

    # Resolve tenant & authorized facilities
    fac_q = Facility.query.with_entities(Facility.id)
    if caller_tenant is not None:
        fac_q = fac_q.filter(tenant_matches(Facility.tenant_id, caller_tenant))
    if allowed_fids is not None:
        fac_q = fac_q.filter(Facility.id.in_(allowed_fids or [-1]))
    scoped_fids = [fid for (fid,) in fac_q.all()]

    total_before = 0.0
    total_after = 0.0
    affected_count = 0
    scope_breakdown = {
        "scope1": {"records": 0, "before": 0.0, "after": 0.0},
        "scope2": {"records": 0, "before": 0.0, "after": 0.0},
        "scope3": {"records": 0, "before": 0.0, "after": 0.0},
    }
    sample_records = []

    # 1. Scope 1
    if target_scope in ("all", "1", 1):
        q1 = Emission.query.filter(Emission.is_test == False)
        q1 = q1.filter(Emission.facility_id.in_(scoped_fids or [-1]))
        if target_year is not None:
            q1 = q1.filter(Emission.year == int(target_year))
        if target_facility_id is not None:
            q1 = q1.filter(Emission.facility_id == int(target_facility_id))
        if target_factor_id is not None:
            q1 = q1.filter(Emission.custom_factor_id == int(target_factor_id))
        elif target_factor_version:
            q1 = q1.filter(Emission.factor_version == target_factor_version)

        for e in q1.all():
            curr_co2e = float(e.co2e_total or 0.0)
            proj_co2e = curr_co2e

            if cf is not None:
                # the Scope 1 engine with the new factor (units, heating value, period), never quantity x factor
                res = _engine_recalc(e, cf, gwp_dict)
                proj_co2e = res[3] if res is not None else curr_co2e
            elif target_gwp_standard:
                # stored gas masses re-weighted; HFC / SF6 re-run, rows without gases kept (F-CORE-01 / F-AGG-07)
                proj = reweighted_co2e(e, gwp_dict)
                proj_co2e = curr_co2e if proj is None else proj

            total_before += curr_co2e
            total_after += proj_co2e
            affected_count += 1
            scope_breakdown["scope1"]["records"] += 1
            scope_breakdown["scope1"]["before"] += curr_co2e
            scope_breakdown["scope1"]["after"] += proj_co2e

            if len(sample_records) < 10:
                sample_records.append({
                    "record_id": e.record_id or f"S1-{e.id}",
                    "scope": 1,
                    "process_type": e.process_type,
                    "old_co2e": round(curr_co2e, 2),
                    "new_co2e": round(proj_co2e, 2),
                    "delta": round(proj_co2e - curr_co2e, 2),
                })

    # 2. Scope 2
    if target_scope in ("all", "2", 2) and target_factor_id is None:
        q2 = Scope2Emission.query
        q2 = q2.filter(Scope2Emission.facility_id.in_(scoped_fids or [-1]))
        if target_year is not None:
            q2 = q2.filter(Scope2Emission.year == int(target_year))
        if target_facility_id is not None:
            q2 = q2.filter(Scope2Emission.facility_id == int(target_facility_id))

        for e in q2.all():
            curr_co2e = float(e.co2e or 0.0)
            proj_co2e = curr_co2e  # GWP change affects steam/fuel if applicable
            total_before += curr_co2e
            total_after += proj_co2e
            affected_count += 1
            scope_breakdown["scope2"]["records"] += 1
            scope_breakdown["scope2"]["before"] += curr_co2e
            scope_breakdown["scope2"]["after"] += proj_co2e

    # 3. Scope 3
    if target_scope in ("all", "3", 3) and target_factor_id is None:
        q3 = Scope3Emission.query
        q3 = q3.filter(Scope3Emission.facility_id.in_(scoped_fids or [-1]))
        if target_year is not None:
            q3 = q3.filter(Scope3Emission.year == int(target_year))
        if target_facility_id is not None:
            q3 = q3.filter(Scope3Emission.facility_id == int(target_facility_id))

        for e in q3.all():
            curr_co2e = float(e.co2e or 0.0)
            proj_co2e = curr_co2e
            total_before += curr_co2e
            total_after += proj_co2e
            affected_count += 1
            scope_breakdown["scope3"]["records"] += 1
            scope_breakdown["scope3"]["before"] += curr_co2e
            scope_breakdown["scope3"]["after"] += proj_co2e

    delta_tco2e = total_after - total_before
    delta_pct = (delta_tco2e / total_before * 100.0) if total_before > 0 else 0.0

    return {
        "records_affected": affected_count,
        "tco2e_before": round(total_before, 2),
        "tco2e_after": round(total_after, 2),
        "delta_tco2e": round(delta_tco2e, 2),
        "delta_pct": round(delta_pct, 2),
        "scope_breakdown": {
            k: {
                "records": v["records"],
                "before": round(v["before"], 2),
                "after": round(v["after"], 2),
                "delta": round(v["after"] - v["before"], 2),
            }
            for k, v in scope_breakdown.items()
        },
        "sample_records": sample_records,
    }


@recalculate_bp.route("/preview", methods=["POST"])
@login_required
def recalculate_preview():
    """Part 2.2: Impact preview for proposed recalculation without writing to DB."""
    user = get_current_user()
    if user and user.role in ["it_admin", "it_manager", "it"]:
        return jsonify({"error": "IT administrators are not authorized to access recalculation previews."}), 403
    caller_tenant = get_current_tenant_id(user)
    allowed_fids = get_allowed_facility_ids(user)

    data = request.get_json() or {}
    target_year = data.get("year")
    target_facility_id = data.get("facility_id")
    target_scope = str(data.get("scope") or "all")
    target_factor_id = data.get("target_factor_id")
    target_factor_version = data.get("target_factor_version")
    target_gwp_standard = data.get("target_gwp_standard")

    if target_facility_id is not None:
        if (denied := facility_access_error(user, target_facility_id)):
            return denied
    if target_factor_id is not None:
        cf = db.session.get(CustomFactor, int(target_factor_id))
        if cf and normalize_tenant_id(getattr(cf, "tenant_id", None)) != caller_tenant:
            return jsonify({"error": "Unauthorized custom factor"}), 403

    preview = _simulate_recalculation(
        target_year=target_year,
        target_facility_id=target_facility_id,
        target_scope=target_scope,
        target_factor_id=target_factor_id,
        target_factor_version=target_factor_version,
        target_gwp_standard=target_gwp_standard,
        allowed_fids=allowed_fids,
        caller_tenant=caller_tenant,
    )
    return jsonify(preview), 200


@recalculate_bp.route("/request", methods=["POST"])
@login_required
def submit_recalculation_request():
    """Part 2.2: Submit a recalculation request with GHG Protocol base-year triggers & maker-checker."""
    user = get_current_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    if user.role in ["auditor", "it_admin", "it_manager", "it"]:
        return jsonify({"error": "Read-only or IT roles cannot request recalculations"}), 403
    caller_tenant = get_current_tenant_id(user)
    allowed_fids = get_allowed_facility_ids(user)

    data = request.get_json() or {}
    trigger_type = str(data.get("trigger_type") or "").strip().lower()
    if trigger_type not in ALLOWED_TRIGGERS:
        return jsonify({
            "error": f"Invalid trigger_type '{trigger_type}'. Must be one of: {', '.join(ALLOWED_TRIGGERS.keys())}",
            "allowed_triggers": ALLOWED_TRIGGERS,
        }), 400

    justification = str(data.get("justification") or "").strip()
    if len(justification) < 10:
        return jsonify({
            "error": "A detailed justification is required per GHG Protocol (minimum 10 characters)",
            "field": "justification",
        }), 400

    target_year = data.get("year")
    target_facility_id = data.get("facility_id")
    target_scope = str(data.get("scope") or "all")
    target_factor_id = data.get("target_factor_id")
    target_factor_version = data.get("target_factor_version")
    target_gwp_standard = data.get("target_gwp_standard")

    if target_facility_id is not None:
        if (denied := facility_access_error(user, target_facility_id)):
            return denied
    if target_factor_id is not None:
        cf = db.session.get(CustomFactor, int(target_factor_id))
        if cf and normalize_tenant_id(getattr(cf, "tenant_id", None)) != caller_tenant:
            return jsonify({"error": "Unauthorized custom factor"}), 403

    # Run preview simulation scoped to caller's facilities/tenant
    preview = _simulate_recalculation(
        target_year=target_year,
        target_facility_id=target_facility_id,
        target_scope=target_scope,
        target_factor_id=target_factor_id,
        target_factor_version=target_factor_version,
        target_gwp_standard=target_gwp_standard,
        allowed_fids=allowed_fids,
        caller_tenant=caller_tenant,
    )

    req = RecalculationRequest(
        tenant_id=caller_tenant,
        target_year=int(target_year) if target_year is not None else None,
        target_facility_id=int(target_facility_id) if target_facility_id is not None else None,
        target_scope=target_scope,
        target_factor_id=int(target_factor_id) if target_factor_id is not None else None,
        target_factor_version=target_factor_version,
        target_gwp_standard=target_gwp_standard,
        trigger_type=trigger_type,
        justification=justification,
        status="pending_approval",
        records_affected=preview["records_affected"],
        tco2e_before=preview["tco2e_before"],
        tco2e_after=preview["tco2e_after"],
        delta_tco2e=preview["delta_tco2e"],
        delta_pct=preview["delta_pct"],
        requested_by=user.id,
        requested_at=datetime.datetime.now(datetime.timezone.utc),
    )
    db.session.add(req)
    db.session.commit()

    log_activity_and_notify(
        action="RECALCULATION_REQUESTED",
        record_id=str(req.id),
        user=user,
        request=request,
        entity="RecalculationRequest",
        details=f"Recalculation requested for trigger '{trigger_type}': {justification} ({preview['records_affected']} records, delta {preview['delta_tco2e']} tCO2e)",
    )

    return jsonify({
        "message": "Recalculation request submitted for maker-checker approval",
        "request": req.to_dict(),
        "preview": preview,
    }), 201


@recalculate_bp.route("/<int:request_id>/approve", methods=["POST"])
@admin_required
def approve_and_execute_recalculation(request_id):
    """Part 2.2: Admin maker-checker approval and execution of recalculation."""
    user = get_current_user()
    caller_tenant = get_current_tenant_id(user)
    allowed_fids = get_allowed_facility_ids(user)
    req = db.session.get(RecalculationRequest, request_id)
    if not req:
        return jsonify({"error": "Recalculation request not found"}), 404
    if normalize_tenant_id(getattr(req, "tenant_id", None)) != caller_tenant:
        return jsonify({"error": "Forbidden"}), 403

    if req.status != "pending_approval":
        return jsonify({"error": f"Request cannot be approved: current status is '{req.status}'"}), 400

    # Maker-checker enforcement
    if req.requested_by == user.id and second_approver_required():
        return jsonify({"error": "Maker-checker policy violation: Request creator cannot approve their own recalculation"}), 403

    # Execute recalculation
    gwp_dict = known_gwp_dict(req.target_gwp_standard) if req.target_gwp_standard else None
    cf = db.session.get(CustomFactor, req.target_factor_id) if req.target_factor_id else None

    # Resolve tenant & authorized facilities
    fac_q = Facility.query.with_entities(Facility.id)
    if caller_tenant is not None:
        fac_q = fac_q.filter(tenant_matches(Facility.tenant_id, caller_tenant))
    if allowed_fids is not None:
        fac_q = fac_q.filter(Facility.id.in_(allowed_fids or [-1]))
    scoped_fids = [fid for (fid,) in fac_q.all()]

    refused = []  # Scope 1 records the new factor cannot calculate (left unchanged)
    # Scope 1 Execution (tenant-scoped)
    if req.target_scope in ("all", "1", "Scope 1", 1):
        q1 = Emission.query.filter(Emission.is_test == False)
        q1 = q1.filter(Emission.facility_id.in_(scoped_fids or [-1]))
        if req.target_year is not None:
            q1 = q1.filter(Emission.year == req.target_year)
        if req.target_facility_id is not None:
            q1 = q1.filter(Emission.facility_id == req.target_facility_id)
        if req.target_factor_id is not None:
            q1 = q1.filter(Emission.custom_factor_id == req.target_factor_id)
        elif req.target_factor_version:
            q1 = q1.filter(Emission.factor_version == req.target_factor_version)

        for e in q1.all():
            old_val = float(e.co2e_total or 0.0)
            old_factor_ver = e.factor_version
            old_gwp_ver = e.gwp_version
            new_val = old_val
            new_factor_ver = cf.version if cf else e.factor_version
            new_gwp_ver = req.target_gwp_standard or e.gwp_version

            if cf is not None:
                res = _engine_recalc(e, cf, gwp_dict)
                if res is None:  # refused by the engine: the record keeps its values and is named to the approver
                    refused.append(e.record_id or f"S1-{e.id}")
                    continue
                e.co2_emissions, e.ch4_emissions, e.n2o_emissions, new_val = res
                e.factor_version = cf.version
            elif req.target_gwp_standard:
                proj = reweighted_co2e(e, gwp_dict)  # HFC / SF6 re-run, rows without gases kept (F-CORE-01)
                if proj is None:
                    refused.append(e.record_id or f"S1-{e.id}")
                    continue
                new_val = proj
                e.gwp_version = req.target_gwp_standard.upper()

            # Save snapshot in history
            hist = RecalculationHistory(
                request_id=req.id,
                record_id=e.record_id or f"S1-{e.id}",
                scope=1,
                facility_id=e.facility_id,
                year=e.year,
                old_co2e=old_val,
                new_co2e=new_val,
                old_factor_version=old_factor_ver,
                new_factor_version=new_factor_ver,
                old_gwp_version=old_gwp_ver,
                new_gwp_version=new_gwp_ver,
            )
            db.session.add(hist)

            e.co2e_total = new_val
            e.updated_at = datetime.datetime.now(datetime.timezone.utc)
            e.updated_by = user.id

    # Scope 2 / 3 store only their CO2e (no per-gas masses), so a GWP change cannot re-weight them
    # here: they are left as they are and named in the response, never logged as recalculated
    skipped_scopes = []
    if req.target_factor_id is None and req.target_gwp_standard:
        if req.target_scope in ("all", "2", "Scope 2", 2):
            skipped_scopes.append("Scope 2")
        if req.target_scope in ("all", "3", "Scope 3", 3):
            skipped_scopes.append("Scope 3")

    # If base year was targeted, register in BaseYearRecalculation table
    if req.target_year:
        by_rec = BaseYearRecalculation(
            tenant_id=caller_tenant,
            year=req.target_year,
            reason=f"[{req.trigger_type}: {ALLOWED_TRIGGERS.get(req.trigger_type, req.trigger_type)}] {req.justification}",
            previous_emissions=req.tco2e_before,
            adjusted_emissions=req.tco2e_after,
            approved_by=user.id,
            created_by=req.requested_by,
        )
        db.session.add(by_rec)

    req.status = "executed"
    req.approved_by = user.id
    req.approved_at = datetime.datetime.now(datetime.timezone.utc)
    req.executed_at = datetime.datetime.now(datetime.timezone.utc)

    skipped_note = f"; not re-weighted (no stored gas split): {', '.join(skipped_scopes)}" if skipped_scopes else ""
    if refused:
        skipped_note += f"; left unchanged, they cannot be recalculated: {', '.join(refused)}"
    # the audit entry commits with the data change (one transaction)
    log_activity_and_notify(
        action="RECALCULATION_EXECUTED",
        record_id=str(req.id),
        user=user,
        request=request,
        entity="RecalculationRequest",
        details=f"Recalculation #{req.id} executed by {user.fullName}: {req.records_affected} records updated ({req.tco2e_before} -> {req.tco2e_after} tCO2e){skipped_note}",
    )
    db.session.commit()
    invalidate_gwp_cache()

    return jsonify({
        "message": "Recalculation executed successfully",
        "request": req.to_dict(),
        "skipped_scopes": skipped_scopes,
        "refused_records": refused,
    }), 200


@recalculate_bp.route("/<int:request_id>/reject", methods=["POST"])
@admin_required
def reject_recalculation(request_id):
    """Part 2.2: Reject a recalculation request."""
    user = get_current_user()
    caller_tenant = get_current_tenant_id(user)
    req = db.session.get(RecalculationRequest, request_id)
    if not req:
        return jsonify({"error": "Recalculation request not found"}), 404
    if normalize_tenant_id(getattr(req, "tenant_id", None)) != caller_tenant:
        return jsonify({"error": "Forbidden"}), 403

    data = request.get_json() or {}
    reason = str(data.get("reason") or "Rejected by administrator").strip()

    req.status = "rejected"
    req.rejection_reason = reason
    req.approved_by = user.id
    req.approved_at = datetime.datetime.now(datetime.timezone.utc)
    db.session.commit()

    log_activity_and_notify(
        action="RECALCULATION_REJECTED",
        record_id=str(req.id),
        user=user,
        request=request,
        entity="RecalculationRequest",
        details=f"Recalculation #{req.id} rejected by {user.fullName}. Reason: {reason}",
    )

    return jsonify({
        "message": "Recalculation request rejected",
        "request": req.to_dict(),
    }), 200


@recalculate_bp.route("/requests", methods=["GET"])
@login_required
def list_recalculation_requests():
    """Part 2.2: List recalculation requests for the caller's tenant."""
    user = get_current_user()
    caller_tenant = get_current_tenant_id(user)
    q = RecalculationRequest.query.filter(
        tenant_matches(RecalculationRequest.tenant_id, caller_tenant)
    ).order_by(RecalculationRequest.requested_at.desc())
    status = request.args.get("status")
    if status:
        q = q.filter_by(status=status)
    return jsonify([r.to_dict() for r in q.all()])


@recalculate_bp.route("/history", methods=["GET"])
@login_required
def list_recalculation_history():
    """Part 2.2: List granular record-level recalculation history for the caller's tenant."""
    user = get_current_user()
    caller_tenant = get_current_tenant_id(user)
    allowed_fids = get_allowed_facility_ids(user)
    q = (
        RecalculationHistory.query
        .join(RecalculationRequest, RecalculationHistory.request_id == RecalculationRequest.id)
        .filter(tenant_matches(RecalculationRequest.tenant_id, caller_tenant))
    )
    if allowed_fids is not None:
        q = q.filter(RecalculationHistory.facility_id.in_(allowed_fids or [-1]))
    q = q.order_by(RecalculationHistory.timestamp.desc())
    request_id = request.args.get("request_id")
    if request_id:
        q = q.filter(RecalculationHistory.request_id == int(request_id))
    limit = min(int(request.args.get("limit") or 100), 500)
    return jsonify([h.to_dict() for h in q.limit(limit).all()])
