"""SBTi trajectory route.

Split out of routes/dashboard.py unchanged (hardening plan, task 5.3). The routes are
registered on the same ``dashboard_bp`` blueprint, so URLs and endpoint names are the same.
"""
from flask import jsonify, request
from routes.auth import login_required
from sqlalchemy import func
from utils import get_allowed_facility_ids, get_current_user
from routes.dashboard import dashboard_bp, is_it_role


@dashboard_bp.route("/sbti-trajectory", methods=["GET"])
@login_required
def get_sbti_trajectory():
    from models import SbtiTarget, Emission, Scope2Emission, Scope3Emission, Facility
    from datetime import datetime

    user = get_current_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    if is_it_role(user):
        return (
            jsonify(
                {"error": "Forbidden: IT Administrators cannot access operational dashboard data"}
            ),
            403,
        )

    allowed_fids = get_allowed_facility_ids(user)
    facility_id = request.args.get("facility_id") or request.args.get("facilityId")
    scope = (request.args.get("scope") or "all").lower().strip()
    
    target = SbtiTarget.query.order_by(SbtiTarget.created_at.desc()).first()
    if not target:
        return jsonify({"has_target": False})
        
    # Get actuals per year (Scope 1+2+3 verified only)
    actuals = {}
    scope1_actuals = {}
    scope2_actuals = {}
    scope3_actuals = {}
    
    q_s1 = Emission.query.filter_by(status="Verified")
    q_s2 = Scope2Emission.query.filter_by(status="Verified")
    q_s3 = Scope3Emission.query.filter_by(status="Verified")
    
    if facility_id and facility_id != "all":
        try:
            fid = int(facility_id)
            if allowed_fids is not None and fid not in allowed_fids:
                return jsonify({"error": "Unauthorized facility"}), 403
            q_s1 = q_s1.filter_by(facility_id=fid)
            q_s2 = q_s2.filter_by(facility_id=fid)
            q_s3 = q_s3.filter_by(facility_id=fid)
        except ValueError:
            pass
    elif allowed_fids is not None:
        q_s1 = q_s1.filter(Emission.facility_id.in_(allowed_fids))
        q_s2 = q_s2.filter(Scope2Emission.facility_id.in_(allowed_fids))
        q_s3 = q_s3.filter(Scope3Emission.facility_id.in_(allowed_fids))
            
    s1_rows = (
        q_s1.with_entities(
            Emission.year,
            func.sum(func.coalesce(Emission.co2e_total, Emission.co2_emissions, 0)),
        )
        .group_by(Emission.year)
        .all()
    )
    for yr, val in s1_rows:
        if yr is not None:
            v = float(val or 0)
            actuals[yr] = actuals.get(yr, 0) + v
            scope1_actuals[yr] = scope1_actuals.get(yr, 0) + v

    s2_rows = (
        q_s2.with_entities(
            Scope2Emission.year,
            func.sum(func.coalesce(Scope2Emission.co2e, 0)),
        )
        .group_by(Scope2Emission.year)
        .all()
    )
    for yr, val in s2_rows:
        if yr is not None:
            v = float(val or 0)
            actuals[yr] = actuals.get(yr, 0) + v
            scope2_actuals[yr] = scope2_actuals.get(yr, 0) + v

    s3_rows = (
        q_s3.with_entities(
            Scope3Emission.year,
            func.sum(func.coalesce(Scope3Emission.co2e, 0)),
        )
        .group_by(Scope3Emission.year)
        .all()
    )
    for yr, val in s3_rows:
        if yr is not None:
            v = float(val or 0)
            actuals[yr] = actuals.get(yr, 0) + v
            scope3_actuals[yr] = scope3_actuals.get(yr, 0) + v
        
    base_year = target.base_year
    target_year = target.target_year
    rate = (target.reduction_rate_pct or 0.0) / 100.0
    rate_15c = 0.042  # SBTi 1.5C-aligned minimum linear annual reduction
    rate_wb2c = 0.025  # SBTi well-below-2C minimum
    current_year = datetime.now().year
    last_complete_year = current_year - 1

    # Which series does this view compare, and does it match what the target covers? (BUG-019)
    coverage = (target.scope_coverage or "S1S2S3").upper()
    view = {"s1_s2": "S1S2", "s3": "S3"}.get(scope, coverage)

    def series(yr):
        if view == "S1S2":
            return (scope1_actuals.get(yr, 0.0) + scope2_actuals.get(yr, 0.0)) if (yr in scope1_actuals or yr in scope2_actuals) else None
        if view == "S3":
            return scope3_actuals.get(yr) if yr in scope3_actuals else None
        return actuals.get(yr) if yr in actuals else None

    restricted = allowed_fids is not None or bool(facility_id and facility_id != "all")
    if view == coverage and not restricted:
        baseline = float(target.base_year_emissions)
        baseline_source = "target"
    else:
        # scope subset or a regional / facility view: its own base-year actual is the baseline
        baseline = series(base_year)
        baseline_source = "base-year actual for this view"
    residual_floor = baseline * 0.10 if baseline else None

    def line(r, yrs):
        if not baseline:
            return None
        return round(max(residual_floor, baseline * (1 - r * yrs)), 2)

    end_year = max(target_year, current_year)
    trajectory = []
    for yr in range(base_year, end_year + 1):
        d = yr - base_year
        s1 = round(scope1_actuals.get(yr, 0), 2)
        s2 = round(scope2_actuals.get(yr, 0), 2)
        s3 = round(scope3_actuals.get(yr, 0), 2)
        has = yr in actuals
        val = series(yr)
        trajectory.append({
            "year": str(yr),
            "sbti_target": line(rate, d),
            "sbti_15c": line(rate_15c, d),
            "sbti_wb2c": line(rate_wb2c, d),
            "bau_projection": round(baseline * (1.015 ** d), 2) if baseline else None,
            "actual": round(val, 2) if (val is not None and yr <= current_year) else None,
            "is_partial_year": yr == current_year,
            "scope1": s1 if has else 0,
            "scope2": s2 if has else 0,
            "scope3": s3 if has else 0,
            "scope12": round(s1 + s2, 2) if has else 0,
            "total_emissions": round(s1 + s2 + s3, 2) if has else 0,
        })

    # BUG-014: progress on the latest COMPLETE year (never the running year or a future-dated one)
    candidates = [y for y in range(base_year, last_complete_year + 1) if series(y) is not None]
    progress_year = max(candidates) if candidates else None
    ytd = series(current_year)
    if progress_year is None or not baseline:
        # BUG-028: no data is "not available", never "ON TRACK / 100 %"
        current_actual = current_target = reduction = on_track = None
    else:
        current_actual = series(progress_year)
        current_target = line(rate, progress_year - base_year)
        reduction = (baseline - current_actual) / baseline * 100.0
        on_track = current_actual <= current_target

    def r2(v):
        return round(v, 2) if v is not None else None

    labels = {"1.5C": "SBTi 1.5\u00b0C Linear Target", "WB2C": "SBTi Well-Below 2\u00b0C Linear Target",
              "custom": "Custom Linear Target"}
    return jsonify({
        "has_target": True,
        "base_year": base_year,
        "base_year_emissions": r2(baseline),
        "target_base_year_emissions": round(target.base_year_emissions, 2),
        "baseline_source": baseline_source,
        "scope_coverage": coverage,
        "view_scope": view,
        "target_year": target_year,
        "target_emissions_final": line(rate, target_year - base_year),
        "reduction_rate_pct": target.reduction_rate_pct,
        "pathway_type": target.pathway_type,
        "pathway_label": labels.get(target.pathway_type, "Custom Linear Target"),
        "current_year": progress_year,
        "latest_actual_year": progress_year,
        "ytd_year": current_year,
        "ytd_actual": r2(ytd),
        "current_actual_emissions": r2(current_actual),
        "current_target_emissions": r2(current_target),
        "current_actual": r2(current_actual),
        "current_target": r2(current_target),
        "reduction_achieved_pct": r2(reduction),
        "on_track": on_track,
        "residual_floor": r2(residual_floor),
        "scope": scope,
        "trajectory": trajectory,
    })
