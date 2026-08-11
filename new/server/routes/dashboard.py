from routes.auth import login_required
from flask import Blueprint, request, jsonify, current_app
from models import (
    Emission,
    Facility,
    Scope2Emission,
    Scope3Emission,
    MitigationProject,
    MitigationRecord,
    Goal,
    BaseYearRecalculation,
    ProductionData,
    OgmpSurvey,
)
from extensions import db
from utils import get_current_user, get_allowed_facility_ids
from sqlalchemy import func
from datetime import datetime
from cachetools import TTLCache, cached, keys
from calculations.constants import get_active_gwp
import threading
import concurrent.futures

# Global cache for dashboard queries (5 minutes TTL)
DASHBOARD_CACHE = TTLCache(maxsize=100, ttl=300)
CACHE_LOCK = threading.Lock()


def clear_dashboard_cache():
    with CACHE_LOCK:
        DASHBOARD_CACHE.clear()


def make_cache_key(namespace):
    def cache_key_builder(*args, **kwargs):
        # Convert any list values to tuples so they are hashable for the cache key
        hashable_kwargs = {
            k: tuple(v) if isinstance(v, list) else v for k, v in kwargs.items()
        }
        return keys.hashkey(namespace, *args, **hashable_kwargs)

    return cache_key_builder


def _run_in_app_ctx(app, fn, *args, **kwargs):
    """
    Helper: push the Flask application context in a background thread
    before calling fn, so db.session works correctly.
    Flask-SQLAlchemy scopes sessions to the app context; worker threads
    spawned by ThreadPoolExecutor don't inherit it automatically.
    """
    with app.app_context():
        return fn(*args, **kwargs)


dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/batch-all", methods=["GET"])
@login_required
def get_batch_dashboard_data():
    """Consolidated dashboard API — all sub-queries run in parallel threads."""
    facility_id = request.args.get("facilityId")
    year = request.args.get("year")
    request.args.get("month")
    activity = request.args.get("activity")
    division = request.args.get("division")
    segment = request.args.get("segment")
    group_by = request.args.get("groupBy")

    user = get_current_user()
    allowed_fids = get_allowed_facility_ids(user)

    # Capture app reference NOW (inside the request context) so worker
    # threads can push their own app context independently.
    app = current_app._get_current_object()

    try:
        goal_year = int(year) if year and year != "all" else datetime.utcnow().year
        uncertainty_year = int(year) if year and year != "all" else None

        # Run all independent queries in parallel — eliminates sequential wait time.
        # Each future wraps the call in _run_in_app_ctx to supply the app context.
        with concurrent.futures.ThreadPoolExecutor(max_workers=7) as executor:
            f_summary = executor.submit(
                _run_in_app_ctx,
                app,
                _query_summary,
                facility_id=facility_id,
                year=year,
                activity=activity,
                division=division,
                group_by=group_by,
                allowed_fids=allowed_fids,
                segment=segment,
            )
            f_mitigation = executor.submit(
                _run_in_app_ctx,
                app,
                _query_mitigation,
                facility_id=facility_id,
                year=year,
                allowed_fids=allowed_fids,
                segment=segment,
            )
            f_scope3 = executor.submit(
                _run_in_app_ctx,
                app,
                _query_scope3_summary,
                facility_id=facility_id,
                year=year,
                activity=activity,
                division=division,
                allowed_fids=allowed_fids,
                segment=segment,
            )
            f_categorical = executor.submit(
                _run_in_app_ctx,
                app,
                _query_categorical_breakdown,
                facility_id=facility_id,
                year=year,
                activity=activity,
                division=division,
                allowed_fids=allowed_fids,
                segment=segment,
            )
            f_intensity = executor.submit(
                _run_in_app_ctx,
                app,
                _query_intensity_stats,
                facility_id=facility_id,
                year=year,
                activity=activity,
                division=division,
                allowed_fids=allowed_fids,
                segment=segment,
            )
            f_uncertainty = executor.submit(
                _run_in_app_ctx,
                app,
                _query_uncertainty,
                year=uncertainty_year,
                allowed_fids=allowed_fids,
            )
            f_years = executor.submit(_run_in_app_ctx, app, _query_available_years)

        # Static / cheap lookups (sequential is fine — they're single-row queries)
        goal = Goal.query.filter_by(year=goal_year).first()
        goal_obj = (
            {
                "year": goal.year,
                "target_amount": float(goal.target_amount),
                "created_at": goal.created_at.isoformat() if goal.created_at else None,
            }
            if goal
            else None
        )
        base_year_rec = BaseYearRecalculation.query.order_by(
            BaseYearRecalculation.recalc_date.desc()
        ).first()
        base_year_obj = (
            {
                "id": base_year_rec.id,
                "year": base_year_rec.year,
                "reason": base_year_rec.reason,
                "recalc_date": (
                    base_year_rec.recalc_date.isoformat()
                    if base_year_rec.recalc_date
                    else None
                ),
            }
            if base_year_rec
            else None
        )

        return jsonify(
            {
                "summary": f_summary.result(),
                "mitigation": f_mitigation.result(),
                "scope3_summary": f_scope3.result(),
                "categorical_breakdown": f_categorical.result(),
                "intensity_stats": f_intensity.result(),
                "uncertainty": f_uncertainty.result(),
                "years": f_years.result(),
                "goal": goal_obj,
                "base_year": base_year_obj,
            }
        )
    except Exception as e:
        import traceback

        print(traceback.format_exc())
        return jsonify({"error": str(e)}), 500


# ─────────────────────────────────────────────────────────────────────────────
# PRIVATE QUERY HELPERS
# Each helper contains the pure DB logic extracted from the matching route.
# Routes delegate to them; get_batch_dashboard_data() calls them directly.
# This eliminates the need to mutate request.args (BUG-10 fix).
# ─────────────────────────────────────────────────────────────────────────────


@cached(
    cache=DASHBOARD_CACHE, key=make_cache_key("get_intensity_trend"), lock=CACHE_LOCK
)
@dashboard_bp.route("/intensity-trend", methods=["GET"])
@login_required
def get_intensity_trend():
    facility_id = request.args.get("facilityId")
    activity = request.args.get("activity")
    division = request.args.get("division")
    segment = request.args.get("segment")
    years_str = request.args.get("years", "")

    allowed_fids = get_allowed_facility_ids(get_current_user())

    if years_str:
        years = [int(y.strip()) for y in years_str.split(",") if y.strip()]
    else:
        years = list(range(2019, 2031))

    # PERF: Single bulk query instead of 12 individual calls (eliminates N+1)
    bulk = _query_intensity_trend_bulk(
        facility_id=facility_id,
        years=tuple(years),
        activity=activity,
        division=division,
        allowed_fids=allowed_fids,
        segment=segment,
    )
    return jsonify(bulk)


@cached(cache=DASHBOARD_CACHE, key=make_cache_key("_query_summary"), lock=CACHE_LOCK)
def _query_summary(
    facility_id=None,
    year=None,
    activity=None,
    division=None,
    group_by=None,
    allowed_fids=None,
    segment=None,
):
    """Pure query logic for /summary — returns a plain Python list."""
    sel = [
        Emission.year.label("year"),
        func.sum(Emission.co2_emissions).label("co2_total"),
        func.sum(Emission.ch4_emissions).label("ch4_total"),
        func.sum(Emission.n2o_emissions).label("n2o_total"),
        func.sum(Emission.co2e_total).label("scope1_total"),
    ]
    if group_by == "facility":
        sel.insert(1, Emission.facility_id)

    scope1_query = db.session.query(*sel)
    if allowed_fids is not None:
        scope1_query = scope1_query.filter(Emission.facility_id.in_(allowed_fids))
    if facility_id and facility_id != "all":
        scope1_query = scope1_query.filter(Emission.facility_id == int(facility_id))
    if segment and segment != "all":
        scope1_query = scope1_query.join(
            Facility, Emission.facility_id == Facility.id
        ).filter(Facility.segment == segment)
    if activity and activity != "all":
        scope1_query = scope1_query.filter(Emission.activity == activity)
    if division and division != "all":
        scope1_query = scope1_query.filter(Emission.division == division)
    if year and year != "all":
        scope1_query = scope1_query.filter(Emission.year == int(year))
    scope1_query = scope1_query.filter(Emission.status != "Draft")
    groups = [Emission.year]
    if group_by == "facility":
        groups.append(Emission.facility_id)
    scope1_data = scope1_query.group_by(*groups).all()

    sel2 = [
        Scope2Emission.year,
        func.sum(Scope2Emission.co2e).label("scope2_total"),
        func.sum(Scope2Emission.electricity_kwh).label("scope2_energy"),
    ]
    if group_by == "facility":
        sel2.insert(1, Scope2Emission.facility_id)
    scope2_query = db.session.query(*sel2)
    if allowed_fids is not None:
        scope2_query = scope2_query.filter(Scope2Emission.facility_id.in_(allowed_fids))
    if facility_id and facility_id != "all":
        scope2_query = scope2_query.filter(
            Scope2Emission.facility_id == int(facility_id)
        )
    if segment and segment != "all":
        scope2_query = scope2_query.join(
            Facility, Scope2Emission.facility_id == Facility.id
        ).filter(Facility.segment == segment)
    if activity and activity != "all":
        scope2_query = scope2_query.filter(Scope2Emission.activity == activity)
    if division and division != "all":
        scope2_query = scope2_query.filter(Scope2Emission.division == division)
    if year and year != "all":
        scope2_query = scope2_query.filter(Scope2Emission.year == int(year))
    scope2_query = scope2_query.filter(Scope2Emission.status != "Draft")
    groups2 = [Scope2Emission.year]
    if group_by == "facility":
        groups2.append(Scope2Emission.facility_id)
    scope2_data = scope2_query.group_by(*groups2).all()

    yearly_data = {}
    for row in scope1_data:
        yr = int(row.year)
        fid = getattr(row, "facility_id", "total")
        key = (yr, fid)
        yearly_data[key] = {
            "year": yr,
            "facility_id": fid,
            "scope1_total": float(row.scope1_total or 0),
            "co2_total": float(row.co2_total or 0),
            "ch4_total": float(row.ch4_total or 0),
            "n2o_total": float(row.n2o_total or 0),
            "scope2_total": 0,
            "scope2_energy": 0,
            "combustion": 0,
            "flaring": 0,
            "venting": 0,
            "other": 0,
        }
    for row in scope2_data:
        yr = int(row.year)
        fid = getattr(row, "facility_id", "total")
        key = (yr, fid)
        if key not in yearly_data:
            yearly_data[key] = {
                "year": yr,
                "facility_id": fid,
                "scope1_total": 0,
                "co2_total": 0,
                "ch4_total": 0,
                "n2o_total": 0,
                "scope2_total": 0,
                "scope2_energy": 0,
                "combustion": 0,
                "flaring": 0,
                "venting": 0,
                "other": 0,
            }
        yearly_data[key]["scope2_total"] = float(row.scope2_total or 0)
        yearly_data[key]["scope2_energy"] = float(row.scope2_energy or 0)

    act_sel = [
        Emission.year.label("year"),
        Emission.process_type,
        func.sum(Emission.co2e_total).label("total"),
    ]
    if group_by == "facility":
        act_sel.insert(1, Emission.facility_id)
    activity_query = db.session.query(*act_sel)
    if allowed_fids is not None:
        activity_query = activity_query.filter(Emission.facility_id.in_(allowed_fids))
    if facility_id and facility_id != "all":
        activity_query = activity_query.filter(Emission.facility_id == int(facility_id))
    if activity and activity != "all":
        activity_query = activity_query.filter(Emission.activity == activity)
    if division and division != "all":
        activity_query = activity_query.filter(Emission.division == division)
    if year and year != "all":
        activity_query = activity_query.filter(Emission.year == int(year))
    activity_query = activity_query.filter(Emission.status != "Draft")
    activity_groups = [Emission.year, Emission.process_type]
    if group_by == "facility":
        activity_groups.append(Emission.facility_id)
    activity_data = activity_query.group_by(*activity_groups).all()

    SOURCE_MAP = {
        "combustion": "combustion",
        "stationary combustion": "combustion",
        "flaring": "flaring",
        "flare": "flaring",
        "venting": "venting",
        "vent": "venting",
        "fugitive": "venting",
        "fugitives": "venting",
    }
    for row in activity_data:
        yr = int(row.year)
        fid = getattr(row, "facility_id", "total")
        key = (yr, fid)
        if key in yearly_data:
            source_raw = (row.process_type or "").lower().strip()
            mapped = False
            for pattern, category in SOURCE_MAP.items():
                if pattern in source_raw:
                    yearly_data[key][category] += float(row.total or 0)
                    mapped = True
                    break
            if not mapped:
                yearly_data[key]["other"] += float(row.total or 0)

    return list(yearly_data.values())


@cached(cache=DASHBOARD_CACHE, key=make_cache_key("_query_mitigation"), lock=CACHE_LOCK)
def _query_mitigation(facility_id=None, year=None, allowed_fids=None, segment=None):
    """Pure query logic for /mitigation — returns a plain Python list."""
    proj_query = MitigationProject.query
    if allowed_fids is not None:
        proj_query = proj_query.filter(MitigationProject.facility_id.in_(allowed_fids))
    if facility_id and facility_id != "all":
        proj_query = proj_query.filter(
            MitigationProject.facility_id == int(facility_id)
        )
    if segment and segment != "all":
        proj_query = proj_query.join(
            Facility, MitigationProject.facility_id == Facility.id
        ).filter(Facility.segment == segment)
    if year and year != "all":
        proj_query = proj_query.filter(MitigationProject.year == int(year))
    projects = proj_query.all()

    rec_query = MitigationRecord.query
    if year and year != "all":
        rec_query = rec_query.filter(MitigationRecord.year == int(year))
    records = rec_query.all()

    results = []
    for p in projects:
        results.append(
            {
                "id": f"proj_{p.id}",
                "name": p.name,
                "type": p.project_type,
                "quantity_tco2e": float(p.quantity_tco2e or 0),
                "year": p.year,
                "status": p.status,
                "activity": p.facility.activity if p.facility else "-",
                "division": p.facility.division if p.facility else "-",
                "region": p.facility.name if p.facility else "-",
            }
        )
    for m in records:
        results.append(
            {
                "id": f"rec_{m.id}",
                "name": f"{m.type} - {m.subtype}" if m.subtype else m.type,
                "type": m.type,
                "quantity_tco2e": float(m.quantity_tco2e or 0),
                "year": m.year,
                "status": "Active",
            }
        )
    return results


@cached(
    cache=DASHBOARD_CACHE, key=make_cache_key("_query_scope3_summary"), lock=CACHE_LOCK
)
def _query_scope3_summary(
    facility_id=None,
    year=None,
    activity=None,
    division=None,
    allowed_fids=None,
    segment=None,
):
    """Pure query logic for /scope3/summary — returns a plain Python dict."""
    query = db.session.query(func.sum(Scope3Emission.co2e))
    if allowed_fids is not None:
        query = query.filter(Scope3Emission.facility_id.in_(allowed_fids))
    if year and year != "all":
        query = query.filter(Scope3Emission.year == int(year))
    if facility_id and facility_id != "all":
        query = query.filter(Scope3Emission.facility_id == int(facility_id))
    need_join = (
        (activity and activity != "all")
        or (division and division != "all")
        or (segment and segment != "all")
    )
    if need_join:
        query = query.join(Facility, Facility.id == Scope3Emission.facility_id)
        if activity and activity != "all":
            query = query.filter(Facility.activity == activity)
        if division and division != "all":
            query = query.filter(Facility.division == division)
        if segment and segment != "all":
            query = query.filter(Facility.segment == segment)
    query = query.filter(Scope3Emission.status != "Draft")
    total = query.scalar() or 0
    return {"total": float(total)}


@cached(
    cache=DASHBOARD_CACHE,
    key=make_cache_key("_query_categorical_breakdown"),
    lock=CACHE_LOCK,
)
def _query_categorical_breakdown(
    facility_id=None,
    year=None,
    activity=None,
    division=None,
    allowed_fids=None,
    segment=None,
):
    """Pure query logic for /categorical-breakdown — returns a plain Python list."""
    query = db.session.query(
        Facility.activity,
        Facility.division,
        Facility.name.label("region"),
        Facility.field,
        func.sum(Emission.co2e_total).label("total_emissions"),
    ).join(Facility, Emission.facility_id == Facility.id)
    if allowed_fids is not None:
        query = query.filter(Emission.facility_id.in_(allowed_fids))
    if year and year != "all":
        query = query.filter(Emission.year == int(year))
    if facility_id and facility_id != "all":
        query = query.filter(Emission.facility_id == int(facility_id))
    if segment and segment != "all":
        query = query.filter(Facility.segment == segment)
    if activity and activity != "all":
        query = query.filter(Emission.activity == activity)
    if division and division != "all":
        query = query.filter(Emission.division == division)
    query = query.filter(Emission.status != "Draft")
    results = query.group_by(
        Facility.activity, Facility.division, Facility.name, Facility.field
    ).all()

    scope2_q = db.session.query(
        Facility.activity,
        Facility.division,
        Facility.name.label("region"),
        Facility.field,
        func.sum(Scope2Emission.co2e).label("total_emissions"),
    ).join(Facility, Scope2Emission.facility_id == Facility.id)
    if allowed_fids is not None:
        scope2_q = scope2_q.filter(Scope2Emission.facility_id.in_(allowed_fids))
    if year and year != "all":
        scope2_q = scope2_q.filter(Scope2Emission.year == int(year))
    if facility_id and facility_id != "all":
        scope2_q = scope2_q.filter(Scope2Emission.facility_id == int(facility_id))
    if segment and segment != "all":
        scope2_q = scope2_q.filter(Facility.segment == segment)
    if activity and activity != "all":
        scope2_q = scope2_q.filter(Scope2Emission.activity == activity)
    if division and division != "all":
        scope2_q = scope2_q.filter(Scope2Emission.division == division)
    scope2_q = scope2_q.filter(Scope2Emission.status != "Draft")
    scope2_results = scope2_q.group_by(
        Facility.activity, Facility.division, Facility.name, Facility.field
    ).all()

    scope3_q = db.session.query(
        Facility.activity,
        Facility.division,
        Facility.name.label("region"),
        Facility.field,
        func.sum(Scope3Emission.co2e).label("total_emissions"),
    ).join(Scope3Emission, Facility.id == Scope3Emission.facility_id)
    if allowed_fids is not None:
        scope3_q = scope3_q.filter(Facility.id.in_(allowed_fids))
    if year and year != "all":
        scope3_q = scope3_q.filter(Scope3Emission.year == int(year))
    if facility_id and facility_id != "all":
        scope3_q = scope3_q.filter(Facility.id == int(facility_id))
    if segment and segment != "all":
        scope3_q = scope3_q.filter(Facility.segment == segment)
    if activity and activity != "all":
        scope3_q = scope3_q.filter(Facility.activity == activity)
    if division and division != "all":
        scope3_q = scope3_q.filter(Facility.division == division)
    scope3_q = scope3_q.filter(Scope3Emission.status != "Draft")
    scope3_results = scope3_q.group_by(
        Facility.activity, Facility.division, Facility.name, Facility.field
    ).all()

    output_map = {}
    scope3_map = {}
    for r in results:
        key = (r.activity, r.division, r.region, r.field)
        output_map[key] = float(r.total_emissions or 0)
    for r in scope2_results:
        key = (r.activity, r.division, r.region, r.field)
        output_map[key] = output_map.get(key, 0) + float(r.total_emissions or 0)
    for r in scope3_results:
        key = (r.activity, r.division, r.region, r.field)
        scope3_map[key] = scope3_map.get(key, 0) + float(r.total_emissions or 0)

    output = []
    for key in set(output_map.keys()) | set(scope3_map.keys()):
        act, div, reg, fld = key
        output.append(
            {
                "activity": act,
                "division": div,
                "region": reg,
                "field": fld,
                "total_emissions": output_map.get(key, 0),
                "scope3_emissions": scope3_map.get(key, 0),
                "total_emissions_all": output_map.get(key, 0) + scope3_map.get(key, 0),
            }
        )
    return output


def _query_available_years():
    """Pure query logic for /years — returns a plain Python list."""
    years1 = (
        db.session.query(Emission.year)
        .filter(Emission.status != "Draft")
        .distinct()
        .all()
    )
    years2 = (
        db.session.query(Scope2Emission.year)
        .filter(Scope2Emission.status != "Draft")
        .distinct()
        .all()
    )
    years3 = (
        db.session.query(Scope3Emission.year)
        .filter(Scope3Emission.status != "Draft")
        .distinct()
        .all()
    )
    years4 = db.session.query(ProductionData.year).distinct().all()
    return sorted(
        list(set([y[0] for y in years1 + years2 + years3 + years4])), reverse=True
    )


@dashboard_bp.route("/summary", methods=["GET"])
@login_required
def get_dashboard_summary():
    """
    Get aggregated emissions data for dashboard.
    Query params: facilityId, activity, division, groupBy
    Delegates to _query_summary() for thread-safe reuse.
    """
    user = get_current_user()
    allowed_fids = get_allowed_facility_ids(user)
    return jsonify(
        _query_summary(
            facility_id=request.args.get("facilityId"),
            year=request.args.get("year"),
            activity=request.args.get("activity"),
            division=request.args.get("division"),
            group_by=request.args.get("groupBy"),
            allowed_fids=allowed_fids,
            segment=request.args.get("segment"),
        )
    )


@dashboard_bp.route("/years", methods=["GET"])
@login_required
def get_available_years():
    """Get list of all years present in the emissions and production data"""
    return jsonify(_query_available_years())


@dashboard_bp.route("/mitigation", methods=["GET"])
@login_required
def get_mitigation():
    """Get all mitigation projects and records with filtering.
    Delegates to _query_mitigation() for thread-safe reuse.
    """
    return jsonify(
        _query_mitigation(
            facility_id=request.args.get("facilityId"), year=request.args.get("year")
        )
    )


@dashboard_bp.route("/scope3/summary", methods=["GET"])
@login_required
def get_scope3_summary():
    """Get Scope 3 emissions summary with filtering.
    Delegates to _query_scope3_summary() for thread-safe reuse.
    """
    return jsonify(
        _query_scope3_summary(
            facility_id=request.args.get("facilityId"),
            year=request.args.get("year"),
            activity=request.args.get("activity"),
            division=request.args.get("division"),
        )
    )


@dashboard_bp.route("/goals/<int:year>", methods=["GET"])
@login_required
def get_goal(year):
    """Get goal for specific year"""
    try:
        goal = Goal.query.filter_by(year=year).first()
        if not goal:
            return jsonify(None)

        return jsonify(
            {
                "year": goal.year,
                "target_amount": float(goal.target_amount),
                "created_at": goal.created_at.isoformat() if goal.created_at else None,
            }
        )
    except Exception as e:
        print(f"Error fetching goal for {year}: {e}")
        return jsonify({"error": str(e)}), 500


@dashboard_bp.route("/goals", methods=["POST"])
@login_required
def create_goal():
    """Create or update a goal"""
    try:
        data = request.get_json()
        year = data.get("year")
        target = data.get("target_amount")

        existing = Goal.query.filter_by(year=year).first()
        if existing:
            existing.target_amount = target
        else:
            goal = Goal(year=year, target_amount=target)
            db.session.add(goal)

        db.session.commit()
        return jsonify({"message": "Goal saved successfully"})
    except Exception as e:
        db.session.rollback()
        print(f"Error saving goal: {e}")
        return jsonify({"error": str(e)}), 500


@dashboard_bp.route("/base-year", methods=["GET"])
@login_required
def get_base_year():
    """Get most recent base year recalculation"""
    base_year = BaseYearRecalculation.query.order_by(
        BaseYearRecalculation.recalc_date.desc()
    ).first()

    if not base_year:
        return jsonify(None)

    return jsonify(
        {
            "id": base_year.id,
            "year": base_year.year,
            "reason": base_year.reason,
            "recalc_date": (
                base_year.recalc_date.isoformat() if base_year.recalc_date else None
            ),
        }
    )


@dashboard_bp.route("/categorical-breakdown", methods=["GET"])
@login_required
def get_categorical_breakdown():
    """
    Get emissions breakdown by Activity -> Division -> Region.
    Delegates to _query_categorical_breakdown() for thread-safe reuse.
    """
    return jsonify(
        _query_categorical_breakdown(
            facility_id=request.args.get("facilityId"),
            year=request.args.get("year"),
            activity=request.args.get("activity"),
            division=request.args.get("division"),
        )
    )


@dashboard_bp.route("/base-year-recalculation", methods=["POST"])
@login_required
def create_base_year_recalculation():
    """Create a new base year recalculation entry"""
    data = request.get_json()

    # BUG-20 FIX: Validate required fields before DB operation
    if not data or not data.get("year") or not data.get("reason"):
        return jsonify({"error": "year and reason are required"}), 400

    try:
        year_val = int(data["year"])
    except (ValueError, TypeError):
        return jsonify({"error": "year must be an integer"}), 400

    try:
        recalc = BaseYearRecalculation(
            year=year_val, reason=str(data["reason"]).strip()
        )

        db.session.add(recalc)
        db.session.commit()

        return jsonify({"message": "Base year recalculation recorded"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@dashboard_bp.route("/ogmp-metrics", methods=["GET"])
@login_required
def get_ogmp_metrics():
    """
    OGMP 2.0 Gold Standard roadmap & milestone progress per facility.
    Returns compliance deadlines, current L1-L5 levels, and reconciliation status.
    """
    from routes.auth import _app_settings

    default_base_year = _app_settings.get("ogmp_default_base_year", 2023)
    default_threshold = _app_settings.get("reconciliation_threshold", 20.0)

    user = get_current_user()
    allowed_fids = get_allowed_facility_ids(user)

    fac_id = request.args.get("facilityId")
    year = request.args.get("year")
    current_year = (
        int(year)
        if year and year != "all" and str(year).isdigit()
        else datetime.utcnow().year
    )

    query = Facility.query
    if allowed_fids is not None:
        query = query.filter(Facility.id.in_(allowed_fids))
    if fac_id and fac_id != "all" and str(fac_id).isdigit():
        query = query.filter(Facility.id == int(fac_id))
    if request.args.get("segment"):
        query = query.filter(Facility.segment == request.args.get("segment"))

    facilities = query.all()

    # Query survey top-down sums & facility bottom-up CH4
    survey_query = db.session.query(
        OgmpSurvey.facility_id,
        func.sum(OgmpSurvey.estimated_annual_tch4).label("total_td"),
    )
    if allowed_fids is not None:
        survey_query = survey_query.filter(OgmpSurvey.facility_id.in_(allowed_fids))
    survey_map = {
        r.facility_id: float(r.total_td or 0)
        for r in survey_query.group_by(OgmpSurvey.facility_id).all()
    }

    # Query emissions for bottom-up CH4
    ch4_query = db.session.query(
        Emission.facility_id, func.sum(Emission.ch4_emissions).label("total_ch4")
    ).filter(Emission.status != "Draft")
    if allowed_fids is not None:
        ch4_query = ch4_query.filter(Emission.facility_id.in_(allowed_fids))
    if year and year != "all" and str(year).isdigit():
        ch4_query = ch4_query.filter(Emission.year == int(year))
    ch4_map = {
        r.facility_id: float(r.total_ch4 or 0)
        for r in ch4_query.group_by(Emission.facility_id).all()
    }

    fac_list = []
    total_operated = 0
    total_non_operated = 0
    gold_compliant_count = 0

    for f in facilities:
        op_status = f.operator_status or "operated"
        membership_yr = f.ogmp_membership_year or default_base_year
        target_yr = membership_yr + (3 if op_status == "operated" else 5)
        threshold = f.reconciliation_threshold or default_threshold

        if op_status == "operated":
            total_operated += 1
        else:
            total_non_operated += 1

        is_compliant = current_year <= target_yr
        if is_compliant:
            gold_compliant_count += 1

        top_down = survey_map.get(f.id, 0.0)
        bottom_up = ch4_map.get(f.id, 0.0)
        variance_pct = (
            round(((top_down - bottom_up) / bottom_up * 100.0), 2)
            if (top_down > 0 and bottom_up > 0)
            else None
        )

        if top_down > 0 and variance_pct is not None and abs(variance_pct) <= threshold:
            highest_level = 5
        elif top_down > 0:
            highest_level = 4
        else:
            highest_level = 3

        fac_list.append(
            {
                "facility_id": f.id,
                "id": f.id,
                "facility_name": f.name,
                "name": f.name,
                "facility_code": f.code or f"FAC-{f.id}",
                "segment": f.segment or "Upstream",
                "country": f.country or "Algeria",
                "operator_status": op_status,
                "ogmp_membership_year": membership_yr,
                "target_year": target_yr,
                "target_compliance_year": target_yr,
                "target_gold_year": target_yr,
                "reconciliation_threshold": threshold,
                "is_compliant": is_compliant,
                "highest_ogmp_level": highest_level,
                "reconciliation_variance_pct": variance_pct,
                "status": (
                    "Gold Pathway Active"
                    if is_compliant
                    else "Target Milestone Overdue"
                ),
            }
        )

    return jsonify(
        {
            "facilities": fac_list,
            "summary": {
                "total_facilities": len(facilities),
                "operated_count": total_operated,
                "non_operated_count": total_non_operated,
                "gold_compliant_count": gold_compliant_count,
                "current_reporting_year": current_year,
                "global_default_base_year": default_base_year,
                "global_threshold": default_threshold,
                "upstream_target_pct": _app_settings.get(
                    "ogmp_upstream_target_pct", 0.20
                ),
                "midstream_target_pct": _app_settings.get(
                    "ogmp_midstream_target_pct", 0.05
                ),
            },
        }
    )


@dashboard_bp.route("/intensity-stats", methods=["GET"])
@login_required
def get_intensity_stats():
    """
    Get intensity metrics (kg/BOE) per facility.
    Delegates to _query_intensity_stats() for thread-safe reuse.
    """
    allowed_fids = get_allowed_facility_ids(get_current_user())
    return jsonify(
        _query_intensity_stats(
            facility_id=request.args.get("facilityId"),
            year=request.args.get("year"),
            activity=request.args.get("activity"),
            division=request.args.get("division"),
            allowed_fids=allowed_fids,
            segment=request.args.get("segment"),
        )
    )


# ─────────────────────────────────────────────────────────────────────────────
# BULK INTENSITY TREND (replaces per-year N+1 loop in get_intensity_trend)
# ─────────────────────────────────────────────────────────────────────────────


@cached(
    cache=DASHBOARD_CACHE,
    key=make_cache_key("_query_intensity_trend_bulk"),
    lock=CACHE_LOCK,
)
def _query_intensity_trend_bulk(
    facility_id=None,
    years=None,
    activity=None,
    division=None,
    allowed_fids=None,
    segment=None,
):
    """
    Fetches intensity data for ALL requested years in 5 bulk queries instead of
    5 queries × N_years (the previous N+1 pattern).
    Returns a list of {year, data} dicts compatible with the frontend.
    """
    GAS_TO_BOE = 0.178
    year_list = list(years) if years else list(range(2019, 2031))

    # --- 1. Production (all years) ---
    prod_q = db.session.query(
        ProductionData.year,
        ProductionData.facility_id,
        ProductionData.oil_unit,
        ProductionData.gas_unit,
        func.sum(ProductionData.oil_amount).label("total_oil_raw"),
        func.sum(ProductionData.gas_amount).label("total_gas_raw"),
    ).filter(ProductionData.year.in_(year_list))
    if allowed_fids is not None:
        prod_q = prod_q.filter(ProductionData.facility_id.in_(allowed_fids))
    if facility_id and facility_id != "all":
        prod_q = prod_q.filter(ProductionData.facility_id == int(facility_id))
    if segment and segment != "all":
        prod_q = prod_q.join(
            Facility, ProductionData.facility_id == Facility.id
        ).filter(Facility.segment == segment)
    if activity and activity != "all":
        prod_q = prod_q.filter(ProductionData.activity == activity)
    if division and division != "all":
        prod_q = prod_q.filter(ProductionData.division == division)
    prod_rows = prod_q.group_by(
        ProductionData.year,
        ProductionData.facility_id,
        ProductionData.oil_unit,
        ProductionData.gas_unit,
    ).all()

    # Build prod_map: {(year, fid): {total_oil, total_gas, total_boe}}
    prod_map = {}
    for rec in prod_rows:
        key = (rec.year, rec.facility_id)
        if key not in prod_map:
            prod_map[key] = {"total_oil": 0, "total_gas": 0, "total_boe": 0}
        oil = float(rec.total_oil_raw or 0)
        o_unit = (rec.oil_unit or "bbl").lower().strip()
        if o_unit == "m3":
            oil *= 6.2898
        gas = float(rec.total_gas_raw or 0)
        g_unit = (rec.gas_unit or "mscf").lower().strip()
        if g_unit == "m3":
            gas *= 0.035315
        elif g_unit == "scf":
            gas *= 0.001
        prod_map[key]["total_oil"] += oil
        prod_map[key]["total_gas"] += gas
        prod_map[key]["total_boe"] += oil + (gas * GAS_TO_BOE)

    # --- 2. Scope 1 emissions (all years) ---
    em_q = db.session.query(
        Emission.year,
        Emission.facility_id,
        func.sum(Emission.co2e_total).label("total_co2e"),
        func.sum(Emission.co2_emissions).label("total_co2"),
        func.sum(Emission.ch4_emissions).label("total_ch4"),
        func.sum(Emission.n2o_emissions).label("total_n2o"),
    ).filter(Emission.year.in_(year_list), Emission.status != "Draft")
    if allowed_fids is not None:
        em_q = em_q.filter(Emission.facility_id.in_(allowed_fids))
    if facility_id and facility_id != "all":
        em_q = em_q.filter(Emission.facility_id == int(facility_id))
    if segment and segment != "all":
        em_q = em_q.join(Facility, Emission.facility_id == Facility.id).filter(
            Facility.segment == segment
        )
    if activity and activity != "all":
        em_q = em_q.filter(Emission.activity == activity)
    if division and division != "all":
        em_q = em_q.filter(Emission.division == division)
    em_rows = em_q.group_by(Emission.year, Emission.facility_id).all()
    em_map = (
        {}
    )  # {(year, fid): {total_co2e, total_co2, total_ch4, total_n2o, total_flaring, total_flaring_vol, total_s2}}
    for rec in em_rows:
        em_map[(rec.year, rec.facility_id)] = {
            "total_co2e": float(rec.total_co2e or 0),
            "total_co2": float(rec.total_co2 or 0),
            "total_ch4": float(rec.total_ch4 or 0),
            "total_n2o": float(rec.total_n2o or 0),
            "total_flaring": 0,
            "total_flaring_vol": 0,
            "total_s2": 0,
        }

    # --- 3. Flaring (all years) ---
    flare_q = db.session.query(
        Emission.year,
        Emission.facility_id,
        Emission.unit,
        func.sum(Emission.co2e_total).label("total_flaring"),
        func.sum(Emission.quantity).label("total_flaring_qty"),
    ).filter(
        Emission.year.in_(year_list),
        Emission.status != "Draft",
        Emission.process_type.ilike("%flare%")
        | Emission.process_type.ilike("%flaring%"),
    )
    if allowed_fids is not None:
        flare_q = flare_q.filter(Emission.facility_id.in_(allowed_fids))
    if facility_id and facility_id != "all":
        flare_q = flare_q.filter(Emission.facility_id == int(facility_id))
    if segment and segment != "all":
        flare_q = flare_q.join(Facility, Emission.facility_id == Facility.id).filter(
            Facility.segment == segment
        )
    if activity and activity != "all":
        flare_q = flare_q.filter(Emission.activity == activity)
    if division and division != "all":
        flare_q = flare_q.filter(Emission.division == division)
    flare_rows = flare_q.group_by(
        Emission.year, Emission.facility_id, Emission.unit
    ).all()
    for rec in flare_rows:
        key = (rec.year, rec.facility_id)
        if key not in em_map:
            em_map[key] = {
                "total_co2e": 0,
                "total_co2": 0,
                "total_ch4": 0,
                "total_n2o": 0,
                "total_flaring": 0,
                "total_flaring_vol": 0,
                "total_s2": 0,
            }
        em_map[key]["total_flaring"] += float(rec.total_flaring or 0)
        qty = float(rec.total_flaring_qty or 0)
        unit = (rec.unit or "m3").lower().strip()
        if unit == "scf":
            qty *= 0.028317
        elif unit == "mscf":
            qty *= 28.317
        elif unit in ("liters", "l", "liter"):
            qty *= 0.001
        elif unit == "bbl":
            qty *= 0.158987
        em_map[key]["total_flaring_vol"] += qty

    # --- 4. Scope 2 (all years) ---
    s2_q = db.session.query(
        Scope2Emission.year,
        Scope2Emission.facility_id,
        func.sum(Scope2Emission.co2e).label("total_co2e"),
    ).filter(Scope2Emission.year.in_(year_list), Scope2Emission.status != "Draft")
    if allowed_fids is not None:
        s2_q = s2_q.filter(Scope2Emission.facility_id.in_(allowed_fids))
    if facility_id and facility_id != "all":
        s2_q = s2_q.filter(Scope2Emission.facility_id == int(facility_id))
    if segment and segment != "all":
        s2_q = s2_q.join(Facility, Scope2Emission.facility_id == Facility.id).filter(
            Facility.segment == segment
        )
    s2_rows = s2_q.group_by(Scope2Emission.year, Scope2Emission.facility_id).all()
    for rec in s2_rows:
        key = (rec.year, rec.facility_id)
        if key not in em_map:
            em_map[key] = {
                "total_co2e": 0,
                "total_co2": 0,
                "total_ch4": 0,
                "total_n2o": 0,
                "total_flaring": 0,
                "total_flaring_vol": 0,
                "total_s2": 0,
            }
        s2_val = float(rec.total_co2e or 0)
        em_map[key]["total_s2"] += s2_val
        em_map[key]["total_co2e"] += s2_val

    # --- 5. Scope 3 (all years) ---
    s3_q = db.session.query(
        Scope3Emission.year,
        Scope3Emission.facility_id,
        func.sum(Scope3Emission.co2e).label("total_co2e"),
    ).filter(Scope3Emission.year.in_(year_list), Scope3Emission.status != "Draft")
    if allowed_fids is not None:
        s3_q = s3_q.filter(Scope3Emission.facility_id.in_(allowed_fids))
    if facility_id and facility_id != "all":
        s3_q = s3_q.filter(Scope3Emission.facility_id == int(facility_id))
    if segment and segment != "all":
        s3_q = s3_q.join(Facility, Scope3Emission.facility_id == Facility.id).filter(
            Facility.segment == segment
        )
    s3_rows = s3_q.group_by(Scope3Emission.year, Scope3Emission.facility_id).all()
    s3_map = {}  # {(year, fid): co2e}
    for rec in s3_rows:
        s3_map[(rec.year, rec.facility_id)] = float(rec.total_co2e or 0)

    # --- 6. Facility info (single query) ---
    facilities = Facility.query.all()
    fac_info = {f.id: f for f in facilities}

    # --- 7. Assemble per-year output ---
    all_year_fid_keys = set(
        (y, fid)
        for (y, fid) in list(em_map.keys()) + list(prod_map.keys())
        if y in year_list
    )

    year_buckets = {y: [] for y in year_list}

    # Resolve active 20-year GWP factors
    gwp20_factors = get_active_gwp(horizon="20")
    ch4_gwp20 = float(gwp20_factors.get("CH4", 82.5))
    n2o_gwp20 = float(gwp20_factors.get("N2O", 264.0))

    for yr, fid in all_year_fid_keys:
        boe = prod_map.get((yr, fid), {}).get("total_boe", 0)
        prod_d = prod_map.get((yr, fid), {"total_oil": 0, "total_gas": 0})
        gas_mscf = prod_d.get("total_gas", 0)
        gas_m3 = gas_mscf * 28.3168
        ed = em_map.get(
            (yr, fid),
            {
                "total_co2e": 0,
                "total_co2": 0,
                "total_ch4": 0,
                "total_n2o": 0,
                "total_flaring": 0,
                "total_flaring_vol": 0,
                "total_s2": 0,
            },
        )
        scope3 = s3_map.get((yr, fid), 0)
        fac = fac_info.get(fid)

        ch4_vol_m3 = (ed["total_ch4"] * 1000.0) / 0.6785 if ed["total_ch4"] > 0 else 0.0
        methane_loss_rate_pct = (ch4_vol_m3 / gas_m3 * 100.0) if gas_m3 > 0 else 0.0
        flaring_rate_pct = (
            (ed["total_flaring_vol"] / gas_m3 * 100.0) if gas_m3 > 0 else 0.0
        )

        # Exact GWP20 formula using dynamic active standard
        total_s1 = ed["total_co2e"] - ed["total_s2"]
        s1_gwp20 = (
            ed["total_co2"]
            + (ed["total_ch4"] * ch4_gwp20)
            + (ed["total_n2o"] * n2o_gwp20)
        )
        total_gwp20 = s1_gwp20 + ed["total_s2"]

        if boe > 0:
            co2_int = (ed["total_co2e"] * 1000.0) / boe
            co2_int_gwp20 = (total_gwp20 * 1000.0) / boe
            scope1_int = (total_s1 * 1000.0) / boe
            scope2_int = (ed["total_s2"] * 1000.0) / boe
            scope3_int = (scope3 * 1000.0) / boe
            ch4_int = (ed["total_ch4"] * 1000.0) / boe
            flare_int = (ed["total_flaring"] * 1000.0) / boe
        else:
            co2_int = co2_int_gwp20 = scope1_int = scope2_int = scope3_int = ch4_int = (
                flare_int
            ) = 0

        year_buckets[yr].append(
            {
                "facility_id": fid,
                "facility_name": fac.name if fac else "Unknown",
                "activity": fac.activity if fac else "N/A",
                "co2_intensity": co2_int,
                "co2_intensity_gwp20": co2_int_gwp20,
                "scope1_intensity": scope1_int,
                "scope2_intensity": scope2_int,
                "scope3_intensity": scope3_int,
                "ch4_intensity": ch4_int,
                "api_flaring_intensity": flare_int,
                "methane_loss_rate_pct": methane_loss_rate_pct,
                "flaring_rate_pct": flaring_rate_pct,
                "ogmp_gold_standard_target": 0.20,
                "ogmp_target_status": (
                    "Compliant"
                    if methane_loss_rate_pct <= 0.20
                    else (
                        "Warning" if methane_loss_rate_pct <= 0.25 else "Non-Compliant"
                    )
                ),
                "total_boe": boe,
                "total_oil": prod_d.get("total_oil", 0),
                "total_gas": prod_d.get("total_gas", 0),
                "total_gas_m3": gas_m3,
                "flaring_volume": ed["total_flaring_vol"],
                "flaring_emissions": ed["total_flaring"],
                "total_co2e": ed["total_co2e"],
                "total_co2e_gwp20": total_gwp20,
                "total_scope1": total_s1,
                "total_scope2": ed["total_s2"],
                "total_scope3": scope3,
                "total_co2e_s3": scope3,
                "total_co2e_all": ed["total_co2e"] + scope3,
                "total_ch4": ed["total_ch4"],
            }
        )

    return [{"year": str(y), "data": year_buckets[y]} for y in year_list]


@cached(
    cache=DASHBOARD_CACHE, key=make_cache_key("_query_intensity_stats"), lock=CACHE_LOCK
)
def _query_intensity_stats(
    facility_id=None,
    year=None,
    activity=None,
    division=None,
    allowed_fids=None,
    segment=None,
):
    """
    Pure query logic for /intensity-stats — returns a plain Python list.
    Get intensity metrics (kg/BOE, loss rates %, EPA WEC, GWP20) per facility.
    """
    # 1. Fetch Production Data (Raw for normalization) - Aggregated in SQL
    prod_query = db.session.query(
        ProductionData.facility_id,
        ProductionData.oil_unit,
        ProductionData.gas_unit,
        func.sum(ProductionData.oil_amount).label("total_oil_raw"),
        func.sum(ProductionData.gas_amount).label("total_gas_raw"),
    )

    if allowed_fids is not None:
        prod_query = prod_query.filter(ProductionData.facility_id.in_(allowed_fids))
    if year and year != "all":
        prod_query = prod_query.filter(ProductionData.year == int(year))
    if facility_id and facility_id != "all":
        prod_query = prod_query.filter(ProductionData.facility_id == int(facility_id))
    if segment and segment != "all":
        prod_query = prod_query.join(
            Facility, ProductionData.facility_id == Facility.id
        ).filter(Facility.segment == segment)
    if activity and activity != "all":
        prod_query = prod_query.filter(ProductionData.activity == activity)
    if division and division != "all":
        prod_query = prod_query.filter(ProductionData.division == division)

    prod_grouped = prod_query.group_by(
        ProductionData.facility_id, ProductionData.oil_unit, ProductionData.gas_unit
    ).all()

    prod_results = {}  # fid -> {oil_bbl, gas_mscf, boe, gas_m3}
    GAS_TO_BOE = 0.178

    for rec in prod_grouped:
        fid = rec.facility_id
        if fid not in prod_results:
            prod_results[fid] = {
                "total_oil": 0,
                "total_gas": 0,
                "total_boe": 0,
                "total_gas_m3": 0,
            }

        oil = float(rec.total_oil_raw or 0)
        o_unit = (rec.oil_unit or "bbl").lower().strip()
        if o_unit == "m3":
            oil *= 6.2898

        gas = float(rec.total_gas_raw or 0)
        g_unit = (rec.gas_unit or "mscf").lower().strip()
        gas_m3 = 0
        if g_unit == "m3":
            gas_m3 = gas
            gas *= 0.035315
        elif g_unit == "scf":
            gas_m3 = gas * 0.0283168
            gas *= 0.001
        else:  # mscf
            gas_m3 = gas * 28.3168

        prod_results[fid]["total_oil"] += oil
        prod_results[fid]["total_gas"] += gas
        prod_results[fid]["total_gas_m3"] += gas_m3
        prod_results[fid]["total_boe"] += oil + (gas * GAS_TO_BOE)

    prod_map = {fid: d["total_boe"] for fid, d in prod_results.items()}

    # 2. Fetch Emission Data (Scope 1) with individual gases and processes
    em_query = db.session.query(
        Emission.facility_id,
        Emission.process_type,
        Emission.factor_source,
        Emission.calc_method,
        func.sum(Emission.co2e_total).label("total_co2e"),
        func.sum(Emission.co2_emissions).label("total_co2"),
        func.sum(Emission.ch4_emissions).label("total_ch4"),
        func.sum(Emission.n2o_emissions).label("total_n2o"),
        func.sum(Emission.co2_biogenic).label("total_biogenic"),
    )

    if allowed_fids is not None:
        em_query = em_query.filter(Emission.facility_id.in_(allowed_fids))
    if year and year != "all":
        em_query = em_query.filter(Emission.year == int(year))
    if facility_id and facility_id != "all":
        em_query = em_query.filter(Emission.facility_id == int(facility_id))
    if segment and segment != "all":
        em_query = em_query.join(Facility, Emission.facility_id == Facility.id).filter(
            Facility.segment == segment
        )
    if activity and activity != "all":
        em_query = em_query.filter(Emission.activity == activity)
    if division and division != "all":
        em_query = em_query.filter(Emission.division == division)

    em_query = em_query.filter(Emission.status != "Draft")
    em_grouped = em_query.group_by(
        Emission.facility_id,
        Emission.process_type,
        Emission.factor_source,
        Emission.calc_method,
    ).all()

    em_map = {}  # fid -> totals & detailed splits

    for rec in em_grouped:
        fid = rec.facility_id
        if fid not in em_map:
            em_map[fid] = {
                "total_co2e": 0,
                "total_co2": 0,
                "total_ch4": 0,
                "total_n2o": 0,
                "total_biogenic": 0,
                "total_flaring": 0,
                "total_flaring_vol": 0,
                "ch4_venting": 0,
                "ch4_fugitive": 0,
                "ch4_flaring": 0,
                "ch4_combustion": 0,
                "l3_emissions": 0,
                "l4_emissions": 0,
            }

        co2e = float(rec.total_co2e or 0)
        co2 = float(rec.total_co2 or 0)
        ch4 = float(rec.total_ch4 or 0)
        n2o = float(rec.total_n2o or 0)
        bio = float(rec.total_biogenic or 0)

        em_map[fid]["total_co2e"] += co2e
        em_map[fid]["total_co2"] += co2
        em_map[fid]["total_ch4"] += ch4
        em_map[fid]["total_n2o"] += n2o
        em_map[fid]["total_biogenic"] += bio

        # Process breakdown for methane
        ptype = (rec.process_type or "").lower().strip()
        if "vent" in ptype:
            em_map[fid]["ch4_venting"] += ch4
        elif "fugitive" in ptype or "leak" in ptype:
            em_map[fid]["ch4_fugitive"] += ch4
        elif "flare" in ptype:
            em_map[fid]["ch4_flaring"] += ch4
        else:
            em_map[fid]["ch4_combustion"] += ch4

        # OGMP Level classification: Default = Level 3, Specific/Tier 3 = Level 4
        fsrc = (rec.factor_source or "").lower().strip()
        cmeth = (rec.calc_method or "").lower().strip()
        if fsrc == "default" or "tier 1" in cmeth or "tier 2" in cmeth:
            em_map[fid]["l3_emissions"] += co2e
        else:
            em_map[fid]["l4_emissions"] += co2e

    # Flaring volume specifically (since it needs unit normalization)
    flare_query = db.session.query(
        Emission.facility_id,
        Emission.unit,
        func.sum(Emission.co2e_total).label("total_flaring"),
        func.sum(Emission.quantity).label("total_flaring_qty"),
    ).filter(
        Emission.status != "Draft",
        Emission.process_type.ilike("%flare%")
        | Emission.process_type.ilike("%flaring%"),
    )

    if allowed_fids is not None:
        flare_query = flare_query.filter(Emission.facility_id.in_(allowed_fids))
    if year and year != "all":
        flare_query = flare_query.filter(Emission.year == int(year))
    if facility_id and facility_id != "all":
        flare_query = flare_query.filter(Emission.facility_id == int(facility_id))
    if segment and segment != "all":
        flare_query = flare_query.join(
            Facility, Emission.facility_id == Facility.id
        ).filter(Facility.segment == segment)
    if activity and activity != "all":
        flare_query = flare_query.filter(Emission.activity == activity)
    if division and division != "all":
        flare_query = flare_query.filter(Emission.division == division)

    flare_grouped = flare_query.group_by(Emission.facility_id, Emission.unit).all()

    for rec in flare_grouped:
        fid = rec.facility_id
        if fid not in em_map:
            em_map[fid] = {
                "total_co2e": 0,
                "total_co2": 0,
                "total_ch4": 0,
                "total_n2o": 0,
                "total_biogenic": 0,
                "total_flaring": 0,
                "total_flaring_vol": 0,
                "ch4_venting": 0,
                "ch4_fugitive": 0,
                "ch4_flaring": 0,
                "ch4_combustion": 0,
                "l3_emissions": 0,
                "l4_emissions": 0,
            }

        em_map[fid]["total_flaring"] += float(rec.total_flaring or 0)

        qty = float(rec.total_flaring_qty or 0)
        unit = (rec.unit or "m3").lower().strip()
        if unit == "scf":
            qty *= 0.028317
        elif unit == "mscf":
            qty *= 28.317
        elif unit in ("liters", "l", "liter"):
            qty *= 0.001
        elif unit == "bbl":
            qty *= 0.158987

        em_map[fid]["total_flaring_vol"] += qty

    # Fetch Scope 2 for intensity
    s2_query = db.session.query(
        Scope2Emission.facility_id, func.sum(Scope2Emission.co2e).label("total_co2e")
    )
    if allowed_fids is not None:
        s2_query = s2_query.filter(Scope2Emission.facility_id.in_(allowed_fids))
    if year and year != "all":
        s2_query = s2_query.filter(Scope2Emission.year == int(year))
    if facility_id and facility_id != "all":
        s2_query = s2_query.filter(Scope2Emission.facility_id == int(facility_id))
    if segment and segment != "all":
        s2_query = s2_query.join(
            Facility, Scope2Emission.facility_id == Facility.id
        ).filter(Facility.segment == segment)
    if activity and activity != "all":
        s2_query = s2_query.filter(Scope2Emission.activity == activity)
    if division and division != "all":
        s2_query = s2_query.filter(Scope2Emission.division == division)

    s2_query = s2_query.filter(Scope2Emission.status != "Draft")
    s2_results = s2_query.group_by(Scope2Emission.facility_id).all()
    s2_map = {s2.facility_id: float(s2.total_co2e or 0) for s2 in s2_results}

    for fid, s2_val in s2_map.items():
        if fid not in em_map:
            em_map[fid] = {
                "total_co2e": 0,
                "total_co2": 0,
                "total_ch4": 0,
                "total_n2o": 0,
                "total_biogenic": 0,
                "total_flaring": 0,
                "total_flaring_vol": 0,
                "ch4_venting": 0,
                "ch4_fugitive": 0,
                "ch4_flaring": 0,
                "ch4_combustion": 0,
                "l3_emissions": 0,
                "l4_emissions": 0,
            }
        em_map[fid]["total_co2e"] += s2_val

    # Scope 3 (informational only)
    s3_query = db.session.query(
        Scope3Emission.facility_id, func.sum(Scope3Emission.co2e).label("total_co2e")
    ).join(Facility, Scope3Emission.facility_id == Facility.id)
    if allowed_fids is not None:
        s3_query = s3_query.filter(Scope3Emission.facility_id.in_(allowed_fids))
    if year and year != "all":
        s3_query = s3_query.filter(Scope3Emission.year == int(year))
    if facility_id and facility_id != "all":
        s3_query = s3_query.filter(Scope3Emission.facility_id == int(facility_id))
    if segment and segment != "all":
        s3_query = s3_query.filter(Facility.segment == segment)
    if activity and activity != "all":
        s3_query = s3_query.filter(Facility.activity == activity)
    if division and division != "all":
        s3_query = s3_query.filter(Facility.division == division)
    s3_query = s3_query.filter(Scope3Emission.status != "Draft")
    s3_results = s3_query.group_by(Scope3Emission.facility_id).all()
    s3_map = {s3.facility_id: float(s3.total_co2e or 0) for s3 in s3_results}

    # Top-Down OGMP Surveys
    ogmp_query = db.session.query(
        OgmpSurvey.facility_id,
        func.sum(OgmpSurvey.estimated_annual_tch4).label("total_top_down_tch4"),
    )
    if year and year != "all":
        ogmp_query = ogmp_query.filter(OgmpSurvey.year == int(year))
    if segment and segment != "all":
        ogmp_query = ogmp_query.join(
            Facility, OgmpSurvey.facility_id == Facility.id
        ).filter(Facility.segment == segment)
    ogmp_surveys = {
        o.facility_id: float(o.total_top_down_tch4 or 0)
        for o in ogmp_query.group_by(OgmpSurvey.facility_id).all()
    }

    output = []
    facilities = Facility.query.all()
    fac_info = {f.id: f for f in facilities}
    prod_details_map = {fid: d for fid, d in prod_results.items()}
    all_fids = set(em_map.keys()) | set(prod_map.keys())

    for fid in all_fids:
        ed = em_map.get(
            fid,
            {
                "total_co2e": 0,
                "total_co2": 0,
                "total_ch4": 0,
                "total_n2o": 0,
                "total_biogenic": 0,
                "total_flaring": 0,
                "total_flaring_vol": 0,
                "ch4_venting": 0,
                "ch4_fugitive": 0,
                "ch4_flaring": 0,
                "ch4_combustion": 0,
                "l3_emissions": 0,
                "l4_emissions": 0,
            },
        )
        boe = prod_map.get(fid, 0)
        prod_details = prod_details_map.get(
            fid, {"total_oil": 0, "total_gas": 0, "total_gas_m3": 0}
        )
        gas_m3 = prod_details.get("total_gas_m3", 0)

        # Methane conversion: 1 tonne CH4 = 1000 kg. Density at std cond ~ 0.6785 kg/m3
        ch4_vol_m3 = (ed["total_ch4"] * 1000.0) / 0.6785 if ed["total_ch4"] > 0 else 0.0
        methane_loss_rate_pct = (ch4_vol_m3 / gas_m3 * 100.0) if gas_m3 > 0 else 0.0

        # Flaring Rate %
        flaring_rate_pct = (
            (ed["total_flaring_vol"] / gas_m3 * 100.0) if gas_m3 > 0 else 0.0
        )

        # GWP 20-Year Horizon: dynamic resolution per active standard
        gwp20_factors = get_active_gwp(horizon="20")
        ch4_gwp20 = float(gwp20_factors.get("CH4", 82.5))
        n2o_gwp20 = float(gwp20_factors.get("N2O", 264.0))
        s1_gwp20 = (
            ed["total_co2"]
            + (ed["total_ch4"] * ch4_gwp20)
            + (ed["total_n2o"] * n2o_gwp20)
        )
        s2_val = s2_map.get(fid, 0)
        total_co2e_gwp20 = s1_gwp20 + s2_val

        # Intensities in kg/BOE
        if boe > 0:
            co2_int = (ed["total_co2e"] * 1000.0) / boe
            co2_int_gwp20 = (total_co2e_gwp20 * 1000.0) / boe
            scope1_int = ((ed["total_co2e"] - s2_val) * 1000.0) / boe
            scope2_int = (s2_val * 1000.0) / boe
            scope3_int = (scope3_co2e * 1000.0) / boe
            ch4_int = (ed["total_ch4"] * 1000.0) / boe
            flare_int = (ed["total_flaring"] * 1000.0) / boe
            biogenic_int = (ed["total_biogenic"] * 1000.0) / boe
        else:
            co2_int = co2_int_gwp20 = scope1_int = scope2_int = scope3_int = ch4_int = (
                flare_int
            ) = biogenic_int = 0.0

        # EPA WEC (Waste Emissions Charge per 40 CFR Part 99 / IRA §136)
        from routes.auth import _app_settings

        up_target = float(_app_settings.get("ogmp_upstream_target_pct", 0.20)) / 100.0
        mid_target = float(_app_settings.get("ogmp_midstream_target_pct", 0.05)) / 100.0
        fac = fac_info.get(fid)
        segment = (fac.segment or "Upstream").lower() if fac else "upstream"
        wec_threshold_pct = (
            mid_target
            if ("processing" in segment or "midstream" in segment or "lng" in segment)
            else up_target
        )
        allowed_ch4_tonnes = (gas_m3 * wec_threshold_pct * 0.6785) / 1000.0
        excess_ch4_tonnes = max(0.0, ed["total_ch4"] - allowed_ch4_tonnes)

        # WEC Rate: $900/tonne in 2024, $1,200/tonne in 2025, $1,500/tonne in 2026+
        yr_str = str(year) if year and year != "all" else str(datetime.utcnow().year)
        wec_fee_map = _app_settings.get("wec_fee_rates", {})
        wec_rate = float(
            wec_fee_map.get(
                yr_str,
                900.0 if yr_str == "2024" else (1200.0 if yr_str == "2025" else 1500.0),
            )
        )
        wec_fee_usd = round(excess_ch4_tonnes * wec_rate, 2)
        wec_status = "Compliant" if excess_ch4_tonnes <= 0 else "Taxable Liability"

        # OGMP Level Distribution & Level Progression
        total_s1 = ed["total_co2e"] - s2_val
        l3_pct = (
            round((ed["l3_emissions"] / total_s1 * 100.0), 1) if total_s1 > 0 else 0.0
        )
        l4_pct = (
            round((ed["l4_emissions"] / total_s1 * 100.0), 1) if total_s1 > 0 else 0.0
        )
        top_down_tch4 = ogmp_surveys.get(fid, 0.0)
        reconciliation_ratio = (
            round(top_down_tch4 / ed["total_ch4"], 2)
            if ed["total_ch4"] > 0 and top_down_tch4 > 0
            else None
        )
        variance_pct = (
            round(((top_down_tch4 - ed["total_ch4"]) / ed["total_ch4"] * 100.0), 2)
            if ed["total_ch4"] > 0 and top_down_tch4 > 0
            else None
        )

        # Gold Standard Roadmap & Deadline Tracker
        from routes.auth import _app_settings

        default_base_year = _app_settings.get("ogmp_default_base_year", 2023)
        default_threshold = _app_settings.get("reconciliation_threshold", 20.0)

        op_status = fac.operator_status or "operated" if fac else "operated"
        country = fac.country or "Algeria" if fac else "Algeria"
        base_year = (
            fac.ogmp_membership_year or default_base_year if fac else default_base_year
        )
        deadline_years = 3 if op_status == "operated" else 5
        target_gold_year = base_year + deadline_years
        threshold = (
            fac.reconciliation_threshold or default_threshold
            if fac
            else default_threshold
        )
        variance_flag = (
            (abs(variance_pct) > threshold) if variance_pct is not None else False
        )

        # Determine Current OGMP Level (1 to 5)
        if top_down_tch4 > 0 and (
            variance_pct is not None and abs(variance_pct) <= threshold
        ):
            current_level = 5
        elif top_down_tch4 > 0:
            current_level = 4  # Top-down measured but variance exceeds threshold (needs reconciliation review)
        elif l4_pct >= 50:
            current_level = 4
        elif l3_pct > 0 or ed["total_ch4"] > 0:
            current_level = 3
        else:
            current_level = 2

        current_cal_year = int(year) if (year and str(year).isdigit()) else 2026
        years_left = max(0, target_gold_year - current_cal_year)
        if current_level == 5:
            pathway_status = "Gold Standard Achieved (Level 5)"
        elif current_level == 4 and methane_loss_rate_pct <= 0.20:
            pathway_status = "Level 4 Pathway (Target Met)"
        elif current_cal_year <= target_gold_year:
            pathway_status = (
                f'On Track ({years_left} yr{"s" if years_left != 1 else ""} remaining)'
            )
        else:
            pathway_status = "Overdue / Action Plan Required"

        scope1_2_co2e = ed["total_co2e"]
        scope3_co2e = s3_map.get(fid, 0.0)

        output.append(
            {
                "facility_id": fid,
                "facility_name": fac.name if fac else "Unknown",
                "activity": fac.activity if fac else "N/A",
                "division": fac.division if fac else "N/A",
                "region": fac.region or (fac.name if fac else "N/A"),
                "segment": fac.segment if fac else "Upstream",
                "operator_status": op_status,
                "country": country,
                "ogmp_membership_year": base_year,
                "target_gold_year": target_gold_year,
                "deadline_years": deadline_years,
                "current_ogmp_level": current_level,
                "gold_pathway_status": pathway_status,
                "reconciliation_threshold": threshold,
                "variance_pct": variance_pct,
                "variance_flag": variance_flag,
                # Operational intensities
                "co2_intensity": co2_int,
                "co2_intensity_gwp20": co2_int_gwp20,
                "scope1_intensity": scope1_int,
                "scope2_intensity": scope2_int,
                "scope3_intensity": scope3_int,
                "ch4_intensity": ch4_int,
                "api_flaring_intensity": flare_int,
                "biogenic_intensity": biogenic_int,
                # Loss and flaring rates %
                "methane_loss_rate_pct": methane_loss_rate_pct,
                "flaring_rate_pct": flaring_rate_pct,
                "ogmp_gold_standard_target": 0.20 if "upstream" in segment else 0.05,
                "ogmp_target_status": (
                    "Compliant"
                    if methane_loss_rate_pct <= 0.20
                    else (
                        "Warning" if methane_loss_rate_pct <= 0.25 else "Non-Compliant"
                    )
                ),
                # EPA WEC
                "wec_status": wec_status,
                "excess_ch4_tonnes": excess_ch4_tonnes,
                "wec_fee_usd": wec_fee_usd,
                # OGMP 2.0 Levels & Methane process splits
                "ogmp_l3_pct": l3_pct,
                "ogmp_l4_pct": l4_pct,
                "top_down_tch4": top_down_tch4,
                "reconciliation_ratio": reconciliation_ratio,
                "ch4_venting": ed["ch4_venting"],
                "ch4_fugitive": ed["ch4_fugitive"],
                "ch4_flaring": ed["ch4_flaring"],
                "ch4_combustion": ed["ch4_combustion"],
                # Production
                "total_boe": boe,
                "total_oil": prod_details.get("total_oil", 0),
                "total_gas": prod_details.get("total_gas", 0),
                "total_gas_m3": gas_m3,
                "flaring_volume": ed["total_flaring_vol"],
                "flaring_emissions": ed["total_flaring"],
                # Raw Emissions
                "total_co2e": scope1_2_co2e,
                "total_co2e_gwp20": total_co2e_gwp20,
                "total_scope1": total_s1,
                "total_scope2": s2_val,
                "total_scope3": scope3_co2e,
                "total_co2": ed["total_co2"],
                "total_ch4": ed["total_ch4"],
                "total_n2o": ed["total_n2o"],
                "total_biogenic": ed["total_biogenic"],
                "total_co2e_s3": scope3_co2e,
                "total_co2e_all": scope1_2_co2e + scope3_co2e,
            }
        )

    return output


@dashboard_bp.route("/uncertainty", methods=["GET"])
@login_required
def get_uncertainty_analysis():
    """
    Quantifies inventory uncertainty per ISO 14064-1 §4.6.5.
    Delegates to _query_uncertainty() for thread-safe reuse.
    """
    year = request.args.get("year", type=int)
    return jsonify(_query_uncertainty(year=year))


@cached(
    cache=DASHBOARD_CACHE, key=make_cache_key("_query_uncertainty"), lock=CACHE_LOCK
)
def _query_uncertainty(year=None, allowed_fids=None):
    """
    Pure query logic for /uncertainty — returns a plain Python dict.
    Quantifies inventory uncertainty per ISO 14064-1 §4.6.5
    using SRSS (Square Root of Sum of Squares) propagation.
    PERF: Uses with_entities() to fetch only required columns (avoids loading
    heavy ORM objects for potentially thousands of emission records).
    """
    from datetime import datetime

    if not year:
        latest = db.session.query(func.max(Emission.year)).scalar()
        year = latest or datetime.utcnow().year

    # 1. SCOPE 1 — lightweight column projection
    s1_q = db.session.query(
        Emission.co2e_total,
        Emission.uncertainty,
        Emission.uncertainty_ch4,
        Emission.uncertainty_n2o,
        Emission.calc_method,
        Emission.process_type,
        Emission.fuel_type,
    ).filter(Emission.year == year, Emission.status != "Draft")
    if allowed_fids is not None:
        s1_q = s1_q.filter(Emission.facility_id.in_(allowed_fids))
    s1_emissions = s1_q.all()

    # 2. SCOPE 2 — lightweight column projection
    s2_q = db.session.query(Scope2Emission.co2e, Scope2Emission.source_type).filter(
        Scope2Emission.year == year, Scope2Emission.status != "Draft"
    )
    if allowed_fids is not None:
        s2_q = s2_q.filter(Scope2Emission.facility_id.in_(allowed_fids))
    s2_emissions = s2_q.all()

    # 3. SCOPE 3 — lightweight column projection
    s3_q = db.session.query(Scope3Emission.co2e, Scope3Emission.category).filter(
        Scope3Emission.year == year, Scope3Emission.status != "Draft"
    )
    if allowed_fids is not None:
        s3_q = s3_q.filter(Scope3Emission.facility_id.in_(allowed_fids))
    s3_emissions = s3_q.all()

    def get_ef_uncertainty(em, scope=1):
        """
        Returns the 1σ relative standard uncertainty for a single emission record.
        If measured per-GHG values are stored, use max of those (conservative).
        Otherwise fall back to normative defaults by tier/method.
        Reference: ISO 14064-1:2018 §7.5.2, API Compendium 2021 §2.4
        """
        u_co2 = getattr(em, "uncertainty", None)
        u_ch4 = getattr(em, "uncertainty_ch4", None)
        u_n2o = getattr(em, "uncertainty_n2o", None)

        valid_u = [
            float(u) for u in [u_co2, u_ch4, u_n2o] if u is not None and float(u) > 0
        ]
        if valid_u:
            return max(valid_u)

        # Scope 2 and 3 normative defaults
        if scope == 2:
            return 0.10  # ±10% grid emission factor (1σ)
        if scope == 3:
            return 0.30  # ±30% value chain default (1σ)

        # Scope 1 — resolve from calc_method using numeric thresholds
        # Per API Compendium 2021 §2.4 and IPCC GL Vol.1 Table 3.1:
        #   Tier 3 (measurement/CEMS/composition): EF ±2–5%, AD ±2% → combined ≈ ±3–7%
        #   Tier 2 (regional/custom): EF ±5–10%, AD ±7% → combined ≈ ±9–12%
        #   Tier 1 (default/tabulated): EF ±15–50%, AD ±10% → combined ≈ ±18–51%
        method = (getattr(em, "calc_method", "") or "").lower()
        ptype = (getattr(em, "process_type", "") or "").lower()

        is_fugitive = any(
            x in ptype
            for x in ["fugitive", "vent", "pneumatic", "blowdown", "completion"]
        )

        if any(
            x in method
            for x in [
                "tier 3",
                "tier3",
                "measurement",
                "cems",
                "composition",
                "mass balance",
            ]
        ):
            return 0.05 if not is_fugitive else 0.15  # Tier 3: low uncertainty
        if any(
            x in method
            for x in ["tier 2", "tier2", "regional", "custom", "site-specific"]
        ):
            return 0.10 if not is_fugitive else 0.25  # Tier 2: moderate uncertainty
        if any(
            x in method
            for x in ["tier 1", "tier1", "default", "ipcc", "api", "generic"]
        ):
            return 0.40 if is_fugitive else 0.20  # Tier 1: high uncertainty

        return 0.15  # Conservative baseline fallback

    groups = {}

    # Process Scope 1
    for em in s1_emissions:
        ptype = em.process_type or "Other Scope 1"
        if ptype not in groups:
            groups[ptype] = {"emissions": [], "total_e": 0}
        u = get_ef_uncertainty(em, scope=1)
        groups[ptype]["emissions"].append(
            {
                "e": float(em.co2e_total or 0),
                "u": u,
                "name": em.fuel_type or em.process_type or "Unknown",
            }
        )
        groups[ptype]["total_e"] += float(em.co2e_total or 0)

    # Process Scope 2
    if s2_emissions:
        groups["Scope 2 (Indirect)"] = {"emissions": [], "total_e": 0}
        for em in s2_emissions:
            u = get_ef_uncertainty(em, scope=2)
            groups["Scope 2 (Indirect)"]["emissions"].append(
                {
                    "e": float(em.co2e or 0),
                    "u": u,
                    "name": em.source_type or "Electricity",
                }
            )
            groups["Scope 2 (Indirect)"]["total_e"] += float(em.co2e or 0)

    # Process Scope 3
    if s3_emissions:
        groups["Scope 3 (Value Chain)"] = {"emissions": [], "total_e": 0}
        for em in s3_emissions:
            u = get_ef_uncertainty(em, scope=3)
            groups["Scope 3 (Value Chain)"]["emissions"].append(
                {"e": float(em.co2e or 0), "u": u, "name": em.category or "Value Chain"}
            )
            groups["Scope 3 (Value Chain)"]["total_e"] += float(em.co2e or 0)

    results = []
    total_inventory_e = 0
    total_srss_sq = 0
    tier_counts = {"Tier 1": 0, "Tier 2": 0, "Tier 3": 0}

    for ptype, group in groups.items():
        if group["total_e"] <= 0:
            continue

        sum_sq = sum((item["e"] * item["u"]) ** 2 for item in group["emissions"])
        u_group = (sum_sq**0.5) / group["total_e"]

        # Determine group-level tier for breakdown
        for item in group["emissions"]:
            tier = (
                "Tier 3"
                if item["u"] <= 0.05
                else ("Tier 2" if item["u"] <= 0.15 else "Tier 1")
            )
            tier_counts[tier] += item["e"]

        results.append(
            {
                "category": ptype,
                "total_emissions": group["total_e"],
                "uncertainty_decimal": u_group,
                "uncertainty_pct": f"±{round(u_group * 100, 1)}%",
                "level": (
                    "low"
                    if u_group <= 0.05
                    else ("medium" if u_group <= 0.15 else "high")
                ),
                "top_contributors": [
                    {
                        "name": item["name"],
                        "uncertainty": f"±{round(item['u'] * 100, 1)}%",
                        "contribution": (
                            round((item["e"] / group["total_e"]) * 100, 1)
                            if group["total_e"] > 0
                            else 0
                        ),
                    }
                    for item in sorted(
                        group["emissions"], key=lambda x: x["e"], reverse=True
                    )[:3]
                ],
            }
        )

        total_inventory_e += group["total_e"]
        total_srss_sq += sum_sq

    inventory_uncertainty = (
        (total_srss_sq**0.5) / total_inventory_e if total_inventory_e > 0 else 0
    )

    tier_breakdown = {
        tier: round((val / total_inventory_e) * 100, 1) if total_inventory_e > 0 else 0
        for tier, val in tier_counts.items()
    }

    return {
        "year": year,
        "inventory_uncertainty_pct": f"±{round(inventory_uncertainty * 100, 2)}%",
        "inventory_uncertainty_decimal": inventory_uncertainty,
        "tier_breakdown": tier_breakdown,
        "categories": results,
    }


@dashboard_bp.route("/exclusions", methods=["GET"])
@login_required
def get_report_exclusions():
    """Fetches items marked as exclusions for the report."""
    year = request.args.get("year")
    # activity = request.args.get('activity') # potential future filter

    query = MitigationRecord.query.filter(MitigationRecord.type.ilike("%exclusion%"))

    if year and year != "all":
        query = query.filter(MitigationRecord.year == int(year))

    exclusions = query.all()

    return jsonify(
        [
            {
                "source": e.subtype or e.name or "Unspecified Source",
                "reason": e.notes or "No reason provided",
            }
            for e in exclusions
        ]
    )
