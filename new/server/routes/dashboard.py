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
    BaseYear,
    BaseYearRecalculation,
    ProductionData,
    OgmpSurvey,
)
from extensions import db
from utils import get_current_user, get_allowed_facility_ids, log_activity_and_notify
from sqlalchemy import func
from datetime import datetime, timezone
from cachetools import TTLCache, cached, keys
from calculations.constants import get_active_gwp
from services.ogmp import compute_facility_ogmp_level, ogmp_level_for
import threading
import concurrent.futures
import math
from utils import internal_error

def is_it_role(user):
    return bool(user and getattr(user, "role", None) in ["it_admin", "it_manager", "it"])

# Global cache for dashboard queries (5 minutes TTL)
DASHBOARD_CACHE = TTLCache(maxsize=200, ttl=300)
CACHE_LOCK = threading.Lock()
_LOCAL_CACHE_EPOCH = 0.0
_LAST_EPOCH_CHECK = 0.0


def _get_global_cache_epoch():
    """Fetches the latest global cache epoch timestamp from DB to sync multi-worker Gunicorn processes."""
    global _LOCAL_CACHE_EPOCH, _LAST_EPOCH_CHECK
    import time

    now = time.time()
    try:
        from extensions import db
        if str(db.engine.url).startswith("sqlite"):
            return _LOCAL_CACHE_EPOCH

        # Check at most once every 1.0s to avoid database query overhead
        if now - _LAST_EPOCH_CHECK > 1.0:
            _LAST_EPOCH_CHECK = now
            from sqlalchemy import text

            with db.engine.connect() as conn:
                row = conn.execute(
                    text("SELECT value FROM system_settings WHERE key = :key"),
                    {"key": "_dashboard_cache_epoch"}
                ).fetchone()
                if row and row[0]:
                    epoch_val = float(row[0])
                    if epoch_val > _LOCAL_CACHE_EPOCH:
                        with CACHE_LOCK:
                            DASHBOARD_CACHE.clear()
                        _LOCAL_CACHE_EPOCH = epoch_val
    except Exception:
        pass
    return _LOCAL_CACHE_EPOCH


def clear_dashboard_cache():
    """Updates global epoch in shared DB state and invalidates local worker heap."""
    import time
    global _LOCAL_CACHE_EPOCH

    now = time.time()
    _LOCAL_CACHE_EPOCH = now
    try:
        from extensions import db
        if not str(db.engine.url).startswith("sqlite"):
            from sqlalchemy import text

            with db.engine.begin() as conn:
                conn.execute(
                    text("INSERT INTO system_settings (key, value) VALUES (:key, :val) "
                         "ON CONFLICT(key) DO UPDATE SET value = :val"),
                    {"key": "_dashboard_cache_epoch", "val": str(now)}
                )
    except Exception:
        pass
    with CACHE_LOCK:
        DASHBOARD_CACHE.clear()


def make_cache_key(namespace):
    def cache_key_builder(*args, **kwargs):
        epoch = _get_global_cache_epoch()
        # Convert any list values to tuples so they are hashable for the cache key
        hashable_kwargs = {
            k: tuple(v) if isinstance(v, list) else v for k, v in kwargs.items()
        }
        return keys.hashkey(namespace, epoch, *args, **hashable_kwargs)

    return cache_key_builder


def _run_in_app_ctx(app, fn, *args, **kwargs):
    """
    Helper: push the Flask application context in a background thread
    before calling fn, so db.session works correctly.
    Flask-SQLAlchemy scopes sessions to the app context; worker threads
    spawned by ThreadPoolExecutor don't inherit it automatically.
    """
    with app.app_context():
        try:
            return fn(*args, **kwargs)
        finally:
            db.session.remove()


dashboard_bp = Blueprint("dashboard", __name__)



def _finite_or_none(value):
    """BUG-039: legacy goal rows may hold NULL/NaN; never let them break the dashboard."""
    import math

    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) else None

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
    include_pending = request.args.get("includePending") == "true"

    user = get_current_user()
    if is_it_role(user):
        return (
            jsonify(
                {"error": "Forbidden: IT Administrators cannot access operational dashboard data"}
            ),
            403,
        )
    allowed_fids = get_allowed_facility_ids(user)
    include_pending = request.args.get("includePending", "false").lower() == "true"
    gwp_horizon = request.args.get("gwp_horizon", "100")

    cache_key = (
        "batch_all",
        facility_id,
        year,
        activity,
        division,
        segment,
        group_by,
        include_pending,
        gwp_horizon,
        user.id if user else 0,
    )
    with CACHE_LOCK:
        if cache_key in DASHBOARD_CACHE:
            return jsonify(DASHBOARD_CACHE[cache_key])

    # Capture app reference NOW (inside the request context) so worker
    # threads can push their own app context independently.
    app = current_app._get_current_object()

    try:
        goal_year = int(year) if year and year != "all" else datetime.now(timezone.utc).year
        uncertainty_year = int(year) if year and year != "all" else None

        # Run all independent queries in parallel — eliminates sequential wait time.
        # Each future wraps the call in _run_in_app_ctx to supply the app context.
        with concurrent.futures.ThreadPoolExecutor(max_workers=7) as executor:
            f_summary = executor.submit(
                _run_in_app_ctx,
                app,
                _query_summary,
                facility_id=facility_id,
                year=None,
                activity=activity,
                division=division,
                group_by=group_by,
                allowed_fids=allowed_fids,
                segment=segment,
                include_pending=include_pending,
                gwp_horizon=gwp_horizon,
            )
            f_mitigation = executor.submit(
                _run_in_app_ctx,
                app,
                _query_mitigation,
                facility_id=facility_id,
                year=year,
                allowed_fids=allowed_fids,
                segment=segment,
                activity=activity,
                division=division,
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
                include_pending=include_pending,
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
                gwp_horizon=gwp_horizon,
                include_pending=include_pending,
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
                include_pending=include_pending,
                gwp_horizon=gwp_horizon,
            )
            f_intensity_py = None
            if year and year != "all" and str(year).isdigit():
                f_intensity_py = executor.submit(
                    _run_in_app_ctx,
                    app,
                    _query_intensity_stats,
                    facility_id=facility_id,
                    year=int(year) - 1,
                    activity=activity,
                    division=division,
                    allowed_fids=allowed_fids,
                    segment=segment,
                    include_pending=include_pending,
                    gwp_horizon=gwp_horizon,
                )
            # same population as the other panels (the block used to ignore every filter)
            unc_fids = _filtered_facility_ids(allowed_fids, activity, division, segment)
            unc_fid = int(facility_id) if str(facility_id or "").isdigit() else None
            if unc_fid is not None and unc_fids is not None and unc_fid not in unc_fids:
                unc_fid = -1  # outside the user's scope or the other filters: no records
            f_uncertainty = executor.submit(
                _run_in_app_ctx,
                app,
                _query_uncertainty,
                year=uncertainty_year,
                allowed_fids=unc_fids,
                facility_id=unc_fid,
            )
            f_years = executor.submit(_run_in_app_ctx, app, _query_available_years)

        # Static / cheap lookups (sequential is fine — they're single-row queries)
        # BUG-041: a single-year organisation goal is only comparable with a single-year,
        # unfiltered, organisation-wide total
        filtered_view = allowed_fids is not None or any(
            v not in (None, "", "all") for v in (facility_id, activity, division, segment)
        )
        goal = None if (not year or year == "all" or filtered_view) else Goal.query.filter_by(year=goal_year).first()
        goal_obj = (
            {
                "year": goal.year,
                "target_amount": _finite_or_none(goal.target_amount),
                "created_at": goal.created_at.isoformat() if goal.created_at else None,
            }
            if goal
            else None
        )
        base_year_rec = BaseYearRecalculation.query.order_by(
            BaseYearRecalculation.recalc_date.desc()
        ).first()
        if base_year_rec:
            base_year_obj = {
                "id": base_year_rec.id,
                "year": base_year_rec.year,
                "reason": base_year_rec.reason,
                "recalc_date": (
                    base_year_rec.recalc_date.isoformat()
                    if base_year_rec.recalc_date
                    else None
                ),
            }
        else:
            base_year_singleton = db.session.get(BaseYear, 1) or BaseYear.query.first()
            base_year_obj = (
                {
                    "id": base_year_singleton.id,
                    "year": base_year_singleton.year,
                    "reason": "Official Baseline",
                    "recalc_date": None,
                }
                if base_year_singleton
                else None
            )

        # BUG-054 / BUG-072: pending banner uses the same filters as every other panel, includes
        # Scope 3, and follows the GWP horizon
        from services.dashboard_filters import apply_scope, apply_year, horizon_delta

        pscope = dict(allowed_fids=allowed_fids, facility_id=facility_id, activity=activity, division=division,
                      segment=segment)
        pend = ("Pending", "Pending Approval")

        def pend_q(model, *cols):
            q = db.session.query(func.count(model.id), *[func.coalesce(func.sum(c), 0.0) for c in cols])
            return apply_year(apply_scope(q, model, **pscope), model, year).filter(model.status.in_(pend)).first()

        p1 = pend_q(Emission, Emission.co2e_total, Emission.ch4_emissions, Emission.n2o_emissions)
        p2 = pend_q(Scope2Emission, Scope2Emission.co2e)
        p3 = pend_q(Scope3Emission, Scope3Emission.co2e)
        pending_stats = {
            "count": int(p1[0] or 0) + int(p2[0] or 0) + int(p3[0] or 0),
            "totalCo2e": round(float(p1[1]) + horizon_delta(p1[2], p1[3], gwp_horizon) + float(p2[1]) + float(p3[1]), 2),
            "scope3_count": int(p3[0] or 0),
            "gwp_horizon": "20" if str(gwp_horizon) == "20" else "100",
        }

        batch_result = {
            "summary": f_summary.result(),
            # BUG-094: only implemented projects are netted; planned ones are listed separately
            "mitigation": [m for m in f_mitigation.result() if m.get("counts_toward_net", True)],
            "mitigation_planned": [m for m in f_mitigation.result() if not m.get("counts_toward_net", True)],
            "scope3_summary": f_scope3.result(),
            "categorical_breakdown": f_categorical.result(),
            "intensity_stats": f_intensity.result(),
            "intensity_stats_py": f_intensity_py.result() if f_intensity_py else None,
            "uncertainty": f_uncertainty.result(),
            "years": f_years.result(),
            "goal": goal_obj,
            "base_year": base_year_obj,
            "pending_stats": pending_stats,
        }
        with CACHE_LOCK:
            DASHBOARD_CACHE[cache_key] = batch_result
        return jsonify(batch_result)
    except Exception as e:
        import traceback

        print(traceback.format_exc())
        return internal_error(e)


# ─────────────────────────────────────────────────────────────────────────────
# PRIVATE QUERY HELPERS
# Each helper contains the pure DB logic extracted from the matching route.
# Routes delegate to them; get_batch_dashboard_data() calls them directly.
# This eliminates the need to mutate request.args (BUG-10 fix).
# ─────────────────────────────────────────────────────────────────────────────


@dashboard_bp.route("/intensity-trend", methods=["GET"])
@login_required
def get_intensity_trend():
    user = get_current_user()
    if is_it_role(user):
        return (
            jsonify(
                {"error": "Forbidden: IT Administrators cannot access operational dashboard data"}
            ),
            403,
        )
    facility_id = request.args.get("facilityId")
    activity = request.args.get("activity")
    division = request.args.get("division")
    segment = request.args.get("segment")
    years_str = request.args.get("years", "")

    allowed_fids = get_allowed_facility_ids(user)

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
        include_pending=request.args.get("includePending", "false").lower() == "true",
        gwp_horizon=request.args.get("gwp_horizon", "100"),
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
    include_pending=False,
    gwp_horizon="100",
):
    """Scope 1 / Scope 2 totals per year (optionally per facility) with the source split.

    RC-9: facility-level filters (BUG-004), one grouped Scope 1 query from which both the totals
    and the source split are derived so they always reconcile (BUG-040), canonical source
    classification with a fugitive bucket (BUG-061), GWP-20 from the per-gas columns with the
    active standard and no clamping (BUG-005), NULL years never crash the endpoint (BUG-073).
    """
    from services.dashboard_filters import apply_scope, apply_year, horizon_delta, source_category, statuses

    is_20 = str(gwp_horizon).lower() in ("20", "gwp20", "20yr")
    horizon = "20" if is_20 else "100"
    scope = dict(allowed_fids=allowed_fids, facility_id=facility_id, activity=activity, division=division,
                 segment=segment)
    by_fac = group_by == "facility"

    s1_cols = [Emission.year.label("year"), Emission.process_type.label("process_type")]
    if by_fac:
        s1_cols.append(Emission.facility_id.label("facility_id"))
    s1_q = db.session.query(
        *s1_cols,
        func.sum(Emission.co2_emissions).label("co2_total"),
        func.sum(Emission.ch4_emissions).label("ch4_total"),
        func.sum(Emission.n2o_emissions).label("n2o_total"),
        func.sum(Emission.co2e_total).label("total"),
    )
    s1_q = apply_year(apply_scope(s1_q, Emission, **scope), Emission, year)
    s1_q = s1_q.filter(Emission.status.in_(statuses(include_pending)), Emission.year.isnot(None))
    s1_rows = s1_q.group_by(*[c for c in (Emission.year, Emission.process_type,
                                          Emission.facility_id if by_fac else None) if c is not None]).all()

    def blank(yr, fid):
        return {"year": yr, "facility_id": fid, "scope1_total": 0.0, "scope1_total_gwp100": 0.0,
                "scope1_total_gwp20": 0.0, "gwp_horizon": 20 if is_20 else 100, "co2_total": 0.0,
                "ch4_total": 0.0, "n2o_total": 0.0, "scope2_total": 0.0, "scope2_energy": 0.0,
                "combustion": 0.0, "flaring": 0.0, "venting": 0.0, "fugitive": 0.0, "process": 0.0, "other": 0.0}

    yearly = {}
    for r in s1_rows:
        yr = int(r.year)
        fid = getattr(r, "facility_id", "total") if by_fac else "total"
        d = yearly.setdefault((yr, fid), blank(yr, fid))
        g100 = float(r.total or 0)
        g20 = g100 + horizon_delta(r.ch4_total, r.n2o_total, "20")
        shown = g20 if is_20 else g100
        d["scope1_total_gwp100"] += g100
        d["scope1_total_gwp20"] += g20
        d["scope1_total"] += shown
        d["co2_total"] += float(r.co2_total or 0)
        d["ch4_total"] += float(r.ch4_total or 0)
        d["n2o_total"] += float(r.n2o_total or 0)
        cat = source_category(r.process_type)
        d["venting" if cat == "vented" else cat] += shown

    s2_cols = [Scope2Emission.year.label("year")]
    if by_fac:
        s2_cols.append(Scope2Emission.facility_id.label("facility_id"))
    s2_q = db.session.query(*s2_cols, func.sum(Scope2Emission.co2e).label("scope2_total"),
                            func.sum(Scope2Emission.electricity_kwh).label("scope2_energy"))
    s2_q = apply_year(apply_scope(s2_q, Scope2Emission, **scope), Scope2Emission, year)
    s2_q = s2_q.filter(Scope2Emission.status.in_(statuses(include_pending)), Scope2Emission.year.isnot(None))
    s2_rows = s2_q.group_by(*[c for c in (Scope2Emission.year, Scope2Emission.facility_id if by_fac else None)
                              if c is not None]).all()
    for r in s2_rows:
        yr = int(r.year)
        fid = getattr(r, "facility_id", "total") if by_fac else "total"
        d = yearly.setdefault((yr, fid), blank(yr, fid))
        d["scope2_total"] += float(r.scope2_total or 0)  # Scope 2 stores CO2e only (no per-gas split)
        d["scope2_energy"] += float(r.scope2_energy or 0)

    for d in yearly.values():
        for k in ("scope1_total", "scope1_total_gwp100", "scope1_total_gwp20"):
            d[k] = round(d[k], 6)
    return list(yearly.values())


IMPLEMENTED_MITIGATION = {"active", "completed", "implemented", "operational", "verified"}


@cached(cache=DASHBOARD_CACHE, key=make_cache_key("_query_mitigation"), lock=CACHE_LOCK)
def _query_mitigation(facility_id=None, year=None, allowed_fids=None, segment=None, activity=None, division=None):
    """Mitigation items for the dashboard.

    BUG-094: same facility-level filters as the other panels; unscoped company-wide records are
    only shown in the unfiltered corporate view; each item says whether it counts toward "Net"
    (implemented projects only — Planned projects are shown but not netted).
    """
    from services.dashboard_filters import apply_scope, apply_year

    proj_query = apply_scope(MitigationProject.query, MitigationProject, allowed_fids=allowed_fids,
                             facility_id=facility_id, activity=activity, division=division, segment=segment)
    projects = apply_year(proj_query, MitigationProject, year).all()

    filtered = any(v not in (None, "", "all") for v in (facility_id, activity, division, segment))
    records = []
    if not filtered and allowed_fids is None:
        records = apply_year(MitigationRecord.query, MitigationRecord, year).all()

    results = []
    for p in projects:
        status = (p.status or "").strip()
        results.append(
            {
                "id": f"proj_{p.id}",
                "name": p.name,
                "type": p.project_type,
                "quantity_tco2e": float(p.quantity_tco2e or 0),
                "year": p.year,
                "status": status,
                "counts_toward_net": status.lower() in IMPLEMENTED_MITIGATION,
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
                "status": "Recorded",
                "counts_toward_net": True,
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
    include_pending=False,
):
    """Scope 3 total and per-year totals (RC-9 shared filters and status; NULL years excluded
    from both the total and by_year so they always reconcile - BUG-073)."""
    from services.dashboard_filters import apply_scope, statuses

    q = db.session.query(Scope3Emission.year, func.sum(Scope3Emission.co2e))
    q = apply_scope(q, Scope3Emission, allowed_fids=allowed_fids, facility_id=facility_id, activity=activity,
                    division=division, segment=segment)
    q = q.filter(Scope3Emission.status.in_(statuses(include_pending)), Scope3Emission.year.isnot(None))
    by_year = {str(y): float(v or 0) for y, v in q.group_by(Scope3Emission.year).all()}
    total = by_year.get(str(year), 0.0) if year and year != "all" else sum(by_year.values())
    return {"total": float(total), "by_year": by_year}


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
    gwp_horizon="100",
    include_pending=False,
):
    """Emissions per facility with its organisational labels.

    BUG-064: grouped by facility id (distinct facilities with the same name stay separate).
    BUG-004 / BUG-054: facility-level filters and the shared status rule.
    """
    from services.dashboard_filters import apply_scope, apply_year, horizon_delta, statuses

    scope = dict(allowed_fids=allowed_fids, facility_id=facility_id, activity=activity, division=division,
                 segment=segment)
    st = statuses(include_pending)
    labels = (Facility.id, Facility.activity, Facility.division, Facility.name, Facility.field)

    def grouped(model, *cols):
        q = db.session.query(*labels, *cols).join(Facility, Facility.id == model.facility_id)
        q = apply_year(apply_scope(q, model, joined=True, **scope), model, year)
        return q.filter(model.status.in_(st)).group_by(Facility.id).all()

    s1 = grouped(Emission, func.sum(Emission.co2e_total), func.sum(Emission.ch4_emissions),
                 func.sum(Emission.n2o_emissions))
    s2 = grouped(Scope2Emission, func.sum(Scope2Emission.co2e))
    s3 = grouped(Scope3Emission, func.sum(Scope3Emission.co2e))

    out = {}

    def row(r):
        return out.setdefault(r[0], {
            "facility_id": r[0], "activity": r[1], "division": r[2], "region": r[3], "field": r[4],
            "total_emissions": 0.0, "scope3_emissions": 0.0,
        })

    for r in s1:
        row(r)["total_emissions"] += float(r[5] or 0) + horizon_delta(r[6], r[7], gwp_horizon)
    for r in s2:
        row(r)["total_emissions"] += float(r[5] or 0)
    for r in s3:
        row(r)["scope3_emissions"] += float(r[5] or 0)
    for d in out.values():
        d["total_emissions_all"] = d["total_emissions"] + d["scope3_emissions"]
    return list(out.values())



def _query_available_years():
    """Pure query logic for /years — returns a plain Python list."""
    years1 = (
        db.session.query(Emission.year)
        .filter(Emission.status == "Verified")
        .distinct()
        .all()
    )
    years2 = (
        db.session.query(Scope2Emission.year)
        .filter(Scope2Emission.status == "Verified")
        .distinct()
        .all()
    )
    years3 = (
        db.session.query(Scope3Emission.year)
        .filter(Scope3Emission.status == "Verified")
        .distinct()
        .all()
    )
    years4 = db.session.query(ProductionData.year).distinct().all()
    valid_years = {
        int(y[0])
        for y in years1 + years2 + years3 + years4
        if y[0] is not None and str(y[0]).isdigit()
    }
    return sorted(list(valid_years), reverse=True)


@dashboard_bp.route("/summary", methods=["GET"])
@login_required
def get_dashboard_summary():
    """
    Get aggregated emissions data for dashboard.
    Query params: facilityId, activity, division, groupBy
    Delegates to _query_summary() for thread-safe reuse.
    """
    user = get_current_user()
    if is_it_role(user):
        return (
            jsonify(
                {"error": "Forbidden: IT Administrators cannot access operational dashboard data"}
            ),
            403,
        )
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
            include_pending=request.args.get("includePending", "false").lower() == "true",
            gwp_horizon=request.args.get("gwp_horizon", "100"),
        )
    )


@dashboard_bp.route("/years", methods=["GET"])
@login_required
def get_available_years():
    """Get list of all years present in the emissions and production data"""
    user = get_current_user()
    if is_it_role(user):
        return (
            jsonify(
                {"error": "Forbidden: IT Administrators cannot access operational dashboard data"}
            ),
            403,
        )
    return jsonify(_query_available_years())


@dashboard_bp.route("/mitigation", methods=["GET"])
@login_required
def get_mitigation():
    """Get all mitigation projects and records with filtering.
    Delegates to _query_mitigation() for thread-safe reuse.
    """
    user = get_current_user()
    if is_it_role(user):
        return (
            jsonify(
                {"error": "Forbidden: IT Administrators cannot access operational dashboard data"}
            ),
            403,
        )
    allowed_fids = get_allowed_facility_ids(user)
    return jsonify(
        _query_mitigation(
            facility_id=request.args.get("facilityId"),
            year=request.args.get("year"),
            allowed_fids=allowed_fids,
            segment=request.args.get("segment"),
            activity=request.args.get("activity"),
            division=request.args.get("division"),
        )
    )


@dashboard_bp.route("/scope3/summary", methods=["GET"])
@login_required
def get_scope3_summary():
    """Get Scope 3 emissions summary with filtering.
    Delegates to _query_scope3_summary() for thread-safe reuse.
    """
    user = get_current_user()
    if is_it_role(user):
        return (
            jsonify(
                {"error": "Forbidden: IT Administrators cannot access operational dashboard data"}
            ),
            403,
        )
    allowed_fids = get_allowed_facility_ids(user)
    return jsonify(
        _query_scope3_summary(
            facility_id=request.args.get("facilityId"),
            year=request.args.get("year"),
            activity=request.args.get("activity"),
            division=request.args.get("division"),
            allowed_fids=allowed_fids,
            segment=request.args.get("segment"),
            include_pending=request.args.get("includePending", "false").lower() == "true",
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
                "target_amount": _finite_or_none(goal.target_amount),
                "created_at": goal.created_at.isoformat() if goal.created_at else None,
            }
        )
    except Exception as e:
        print(f"Error fetching goal for {year}: {e}")
        return internal_error(e)


@dashboard_bp.route("/base-year", methods=["GET"])
@login_required
def get_base_year():
    """Get most recent base year recalculation or baseline"""
    base_year = BaseYearRecalculation.query.order_by(
        BaseYearRecalculation.recalc_date.desc()
    ).first()

    if not base_year:
        base_year_singleton = db.session.get(BaseYear, 1) or BaseYear.query.first()
        if base_year_singleton:
            return jsonify({
                "id": base_year_singleton.id,
                "year": base_year_singleton.year,
                "reason": "Official Baseline",
                "recalc_date": None,
            })
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
    user = get_current_user()
    if is_it_role(user):
        return (
            jsonify(
                {"error": "Forbidden: IT Administrators cannot access operational dashboard data"}
            ),
            403,
        )
    allowed_fids = get_allowed_facility_ids(user)
    return jsonify(
        _query_categorical_breakdown(
            facility_id=request.args.get("facilityId"),
            year=request.args.get("year"),
            activity=request.args.get("activity"),
            division=request.args.get("division"),
            allowed_fids=allowed_fids,
            segment=request.args.get("segment"),
            gwp_horizon=request.args.get("gwp_horizon", "100"),
            include_pending=request.args.get("includePending", "false").lower() == "true",
        )
    )


@dashboard_bp.route("/base-year-recalculation", methods=["POST"])
@login_required
def create_base_year_recalculation():
    """Create a new base year recalculation entry"""
    user = get_current_user()
    if not user or user.role not in ["admin", "superuser"]:
        return jsonify({"error": "Admin or Superuser privileges required"}), 403
    if is_it_role(user):
        return jsonify({"error": "IT Admins do not have access to emission calculations"}), 403

    data = request.get_json()

    # BUG-20 FIX: Validate required fields before DB operation
    if not data or not data.get("year") or not data.get("reason"):
        return jsonify({"error": "year and reason are required"}), 400

    try:
        year_val = int(data["year"])
    except (ValueError, TypeError):
        return jsonify({"error": "year must be an integer"}), 400

    try:
        prev_em = (
            float(data["previous_emissions"])
            if data.get("previous_emissions") not in (None, "")
            else None
        )
        adj_em = (
            float(data["adjusted_emissions"])
            if data.get("adjusted_emissions") not in (None, "")
            else None
        )

        recalc = BaseYearRecalculation(
            year=year_val,
            reason=str(data["reason"]).strip(),
            previous_emissions=prev_em,
            adjusted_emissions=adj_em,
            created_by=user.id,
        )

        db.session.add(recalc)

        # Keep BaseYear singleton synchronized (atomic upsert)
        base_year_singleton = db.session.get(BaseYear, 1)
        if base_year_singleton:
            base_year_singleton.year = year_val
        else:
            base_year_singleton = BaseYear(id=1, year=year_val, locked=1)
            db.session.merge(base_year_singleton)

        db.session.commit()

        clear_dashboard_cache()

        log_activity_and_notify(
            action="CREATE",
            record_id=str(recalc.id),
            user=user,
            request=request,
            entity="BaseYearRecalculation",
            details=f"Base year recalculated to {year_val} by {user.fullName}",
        )
        db.session.commit()

        return jsonify({"message": "Base year recalculation recorded", "id": recalc.id}), 201
    except Exception as e:
        db.session.rollback()
        return internal_error(e)


@dashboard_bp.route("/ogmp-metrics", methods=["GET"])
@login_required
def get_ogmp_metrics():
    """
    OGMP 2.0 Gold Standard roadmap & milestone progress per facility.
    Returns compliance deadlines, current L1-L5 levels, and reconciliation status.
    """
    user = get_current_user()
    if is_it_role(user):
        return (
            jsonify(
                {"error": "Forbidden: IT Administrators cannot access operational dashboard data"}
            ),
            403,
        )
    from routes.auth import _app_settings

    default_base_year = _app_settings.get("ogmp_default_base_year", 2023)
    default_threshold = _app_settings.get("reconciliation_threshold", 20.0)
    allowed_fids = get_allowed_facility_ids(user)

    fac_id = request.args.get("facilityId")
    year = request.args.get("year")
    current_year = (
        int(year)
        if year and year != "all" and str(year).isdigit()
        else datetime.now(timezone.utc).year
    )

    query = Facility.query
    if allowed_fids is not None:
        query = query.filter(Facility.id.in_(allowed_fids))
    if fac_id and fac_id != "all" and str(fac_id).isdigit():
        query = query.filter(Facility.id == int(fac_id))
    if request.args.get("segment") and request.args.get("segment") != "all":
        query = query.filter(Facility.segment == request.args.get("segment"))
    if request.args.get("activity") and request.args.get("activity") != "all":
        query = query.filter(Facility.activity == request.args.get("activity"))
    if request.args.get("division") and request.args.get("division") != "all":
        query = query.filter(Facility.division == request.args.get("division"))

    facilities = query.all()

    # BUG-079: reconcile per facility-YEAR. Surveys are annual estimates, so they are averaged within
    # a facility-year (D-02) and summed across years; the bottom-up side covers exactly the years
    # that have a survey. Never pair a multi-year average with a multi-year sum.
    single_year = year and year != "all" and str(year).isdigit()
    survey_query = db.session.query(
        OgmpSurvey.facility_id, OgmpSurvey.year, func.avg(OgmpSurvey.estimated_annual_tch4).label("td"),
    )
    if allowed_fids is not None:
        survey_query = survey_query.filter(OgmpSurvey.facility_id.in_(allowed_fids or [-1]))
    if fac_id and fac_id != "all" and str(fac_id).isdigit():
        survey_query = survey_query.filter(OgmpSurvey.facility_id == int(fac_id))
    if single_year:
        survey_query = survey_query.filter(OgmpSurvey.year == int(year))
    survey_years = {}
    for r in survey_query.group_by(OgmpSurvey.facility_id, OgmpSurvey.year).all():
        if r.td is not None:
            survey_years.setdefault(r.facility_id, {})[r.year] = float(r.td)

    ch4_query = db.session.query(
        Emission.facility_id, Emission.year, func.sum(Emission.ch4_emissions).label("total_ch4")
    ).filter(Emission.status == "Verified")
    if allowed_fids is not None:
        ch4_query = ch4_query.filter(Emission.facility_id.in_(allowed_fids or [-1]))
    if single_year:
        ch4_query = ch4_query.filter(Emission.year == int(year))
    ch4_years = {}
    for r in ch4_query.group_by(Emission.facility_id, Emission.year).all():
        ch4_years.setdefault(r.facility_id, {})[r.year] = float(r.total_ch4 or 0)

    survey_map, ch4_map = {}, {}
    for fid in set(survey_years) | set(ch4_years):
        sy = survey_years.get(fid, {})
        cy = ch4_years.get(fid, {})
        survey_map[fid] = sum(sy.values())
        # bottom-up over the surveyed years when there are surveys, else over all years in scope
        ch4_map[fid] = sum(cy.get(y, 0.0) for y in sy) if sy else sum(cy.values())

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

        top_down = float(survey_map.get(f.id, 0.0) or 0.0)
        bottom_up = float(ch4_map.get(f.id, 0.0) or 0.0)
        if top_down > 0 and bottom_up > 0:
            variance_pct = round(((top_down - bottom_up) / bottom_up * 100.0), 2)
            variance_flag = abs(variance_pct) > threshold
            rec_status = "Discrepancy Flagged" if variance_flag else "Reconciled"
        elif top_down > 0 and bottom_up == 0:
            # Invariant Zero (Decision D-02): Zero Bottom-Up Edge Case
            variance_pct = None
            variance_flag = True
            rec_status = "Discrepancy Flagged"
        elif top_down == 0 and bottom_up > 0:
            variance_pct = None
            variance_flag = False
            rec_status = "Bottom-Up Only"
        else:
            variance_pct = None
            variance_flag = False
            rec_status = "No Activity"

        highest_level = compute_facility_ogmp_level(
            f, year=int(year) if single_year else None, top_down_tch4=top_down, bottom_up_tch4=bottom_up
        )

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
                "variance_flag": variance_flag,
                "reconciliation_status": rec_status,
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
    user = get_current_user()
    if is_it_role(user):
        return (
            jsonify(
                {"error": "Forbidden: IT Administrators cannot access operational dashboard data"}
            ),
            403,
        )
    allowed_fids = get_allowed_facility_ids(user)
    return jsonify(
        _query_intensity_stats(
            facility_id=request.args.get("facilityId"),
            year=request.args.get("year"),
            activity=request.args.get("activity"),
            division=request.args.get("division"),
            allowed_fids=allowed_fids,
            segment=request.args.get("segment"),
            include_pending=request.args.get("includePending", "false").lower() == "true",
            gwp_horizon=request.args.get("gwp_horizon", "100"),
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
    include_pending=False,
    gwp_horizon="100",
):
    """Intensity per year for the trend chart (RC-9: same computation as /intensity-stats)."""
    from services.intensity import intensity_trend

    return intensity_trend(years or [], include_pending=include_pending, gwp_horizon=gwp_horizon,
                           facility_id=facility_id, activity=activity, division=division,
                           allowed_fids=allowed_fids, segment=segment)

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
    include_pending=False,
    gwp_horizon="100",
):
    """Per-facility intensity metrics (kg/BOE, loss rates, OGMP) - see services/intensity.py."""
    from services.intensity import intensity_rows

    return intensity_rows(year=year, include_pending=include_pending, gwp_horizon=gwp_horizon,
                          facility_id=facility_id, activity=activity, division=division,
                          allowed_fids=allowed_fids, segment=segment)

@dashboard_bp.route("/uncertainty", methods=["GET"])
@login_required
def get_uncertainty_analysis():
    """
    Quantifies inventory uncertainty per ISO 14064-1 §4.6.5.
    Delegates to _query_uncertainty() for thread-safe reuse.

    Query parameters:
        year (int, optional): Reporting year. Defaults to latest available.
        facility_id (int, optional): Filter to a single facility.
        scope (str, optional): "1", "2", "3", or "all" (default).
        export (str, optional): "csv" to download uncertainty breakdown as CSV.
    """
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
    year = request.args.get("year", type=int)
    facility_id = request.args.get("facility_id", type=int) or request.args.get("facilityId", type=int)
    scope = (request.args.get("scope") or "all").strip().lower()
    export_fmt = (request.args.get("export") or "").strip().lower()
    allowed_fids = get_allowed_facility_ids(user)

    # RBAC: if facility_id requested, verify it's within the user's allowed set
    if facility_id and allowed_fids is not None and facility_id not in allowed_fids:
        return jsonify({"error": "Forbidden: You do not have access to this facility"}), 403

    result = _query_uncertainty(
        year=year,
        allowed_fids=allowed_fids,
        facility_id=facility_id,
        scope=scope,
    )

    # CSV export
    if export_fmt == "csv":
        import csv
        import io

        def _safe_csv(val):
            """Prevent formula injection (DDE/CSV injection) in spreadsheet cells including leading whitespace bypasses."""
            if isinstance(val, str) and val:
                stripped = val.lstrip()
                if stripped and stripped[0] in ("=", "-", "+", "@", "\t", "\r", "%"):
                    return "'" + val
            return val

        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(["Category", "Total Emissions (tCO2e)", "Uncertainty (±%)", "Level"])
        for cat in result.get("categories", []):
            writer.writerow([
                _safe_csv(cat["category"]),
                round(cat["total_emissions"], 2),
                _safe_csv(cat["uncertainty_pct"]),
                _safe_csv(cat["level"]),
            ])
        writer.writerow([])
        writer.writerow(["Overall Inventory Uncertainty", "", _safe_csv(result["inventory_uncertainty_pct"]), ""])
        writer.writerow(["Confidence Level", "", f"{result['confidence_level_pct']}%", ""])
        writer.writerow(["Coverage Factor (k)", "", result["coverage_factor"], ""])
        csv_content = buf.getvalue()
        from flask import Response
        return Response(
            csv_content,
            mimetype="text/csv",
            headers={"Content-Disposition": f"attachment; filename=uncertainty_{result['year']}.csv"},
        )

    return jsonify(result)


def _filtered_facility_ids(allowed_fids, activity=None, division=None, segment=None):
    """Facility ids for the activity / division / segment filters within the user's scope, as a
    sorted tuple (hashable for the cache); None = unrestricted."""
    if all(v in (None, "", "all") for v in (activity, division, segment)):
        return tuple(sorted(allowed_fids)) if allowed_fids is not None else None
    q = Facility.query
    if activity not in (None, "", "all"):
        q = q.filter(Facility.activity == activity)
    if division not in (None, "", "all"):
        q = q.filter(Facility.division == division)
    if segment not in (None, "", "all"):
        q = q.filter(Facility.segment == segment)
    ids = {f.id for f in q.with_entities(Facility.id).all()}
    if allowed_fids is not None:
        ids &= set(allowed_fids)
    return tuple(sorted(ids))


@cached(
    cache=DASHBOARD_CACHE, key=make_cache_key("_query_uncertainty"), lock=CACHE_LOCK
)
def _query_uncertainty(year=None, allowed_fids=None, facility_id=None, scope="all"):
    """Inventory uncertainty (95 %, k = 2) - see services/inventory_uncertainty.py (RC-10)."""
    from services.inventory_uncertainty import inventory_uncertainty

    if not year:
        # latest year with Verified data that is not in the future
        cy = datetime.now(timezone.utc).year
        year = db.session.query(func.max(Emission.year)).filter(
            Emission.status == "Verified", Emission.year <= cy).scalar() or cy
    return inventory_uncertainty(int(year), allowed_fids=allowed_fids, facility_id=facility_id, scope=scope)


@dashboard_bp.route("/exclusions", methods=["GET"])
@login_required
def get_report_exclusions():
    """Fetches items marked as exclusions for the report."""
    user = get_current_user()
    if is_it_role(user):
        return (
            jsonify(
                {"error": "Forbidden: IT Administrators cannot access operational dashboard data"}
            ),
            403,
        )
    year = request.args.get("year")
    # activity = request.args.get('activity') # potential future filter

    query = MitigationRecord.query.filter(MitigationRecord.type.ilike("%exclusion%"))

    if year and year != "all":
        query = query.filter(MitigationRecord.year == int(year))

    exclusions = query.all()

    return jsonify(
        [
            {
                "source": e.subtype or getattr(e, "name", None) or getattr(e, "reference_id", None) or "Unspecified Source",
                "reason": e.notes or "No reason provided",
            }
            for e in exclusions
        ]
    )

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


@dashboard_bp.route("/flaring-summary", methods=["GET"])
@login_required
def get_flaring_summary():
    """Flaring by operational stream (Routine / Non-Routine / Safety / Unclassified) and the
    Decree 21-330 Art. 9 flaring intensity.

    RC-9 / RC-5: same facility-level filters, status, year and GWP horizon as the rest of the
    dashboard (BUG-026, BUG-072 addendum); exact unit conversion for flared and produced gas
    (BUG-033/035); no invented stream split or proxy factor (BUG-036).
    """
    from models import FlaringDetail
    from services.dashboard_filters import (apply_scope, gas_volume_m3, horizon_delta, production_gas_m3,
                                            source_category, statuses)

    user = get_current_user()
    allowed_fids = get_allowed_facility_ids(user)
    year = request.args.get("year")
    all_years = not year or year == "all"
    try:
        yr = None if all_years else int(year)
    except ValueError:
        return jsonify({"error": "Invalid year"}), 400

    facility_id = request.args.get("facility_id") or request.args.get("facilityId")
    fac_filter = int(facility_id) if facility_id and facility_id != "all" else None
    if fac_filter and allowed_fids is not None and fac_filter not in allowed_fids:
        return jsonify({"error": "Unauthorized facility"}), 403
    scope = dict(allowed_fids=allowed_fids, facility_id=fac_filter, activity=request.args.get("activity"),
                 division=request.args.get("division"), segment=request.args.get("segment"))
    include_pending = request.args.get("includePending", "false").lower() == "true"
    horizon = request.args.get("gwp_horizon", "100")

    def streams_for(year_value):
        fd_q = apply_scope(FlaringDetail.query, FlaringDetail, **scope)
        if year_value is not None:
            fd_q = fd_q.filter(FlaringDetail.year == year_value)
        fd = fd_q.all()
        em_q = apply_scope(Emission.query, Emission, **scope).filter(Emission.status.in_(statuses(include_pending)))
        if year_value is not None:
            em_q = em_q.filter(Emission.year == year_value)
        out = {k: {"m3": 0.0, "tco2e": 0.0} for k in ("routine", "non_routine", "safety", "unclassified")}
        unconverted = 0
        for e in em_q.all():
            if source_category(e.process_type) != "flaring":
                continue
            pt = (e.process_type or "").strip().lower()
            key = {"routine_flaring": "routine", "non_routine_flaring": "non_routine",
                   "safety_flaring": "safety"}.get(pt, "unclassified")
            vol = gas_volume_m3(e.quantity, e.unit)
            if vol is None:
                unconverted += 1
            else:
                out[key]["m3"] += vol
            out[key]["tco2e"] += float(e.co2e_total or 0) + horizon_delta(e.ch4_emissions, e.n2o_emissions, horizon)
        detail_used = False
        if fd and any((r.routine_knm3 or 0) or (r.non_routine_knm3 or 0) or (r.safety_knm3 or 0) for r in fd):
            # operator-reported stream volumes take precedence; totals are the sum of the parts
            detail_used = True
            out["routine"]["m3"] = sum(float(r.routine_knm3 or 0) for r in fd) * 1000.0
            out["non_routine"]["m3"] = sum(float(r.non_routine_knm3 or 0) for r in fd) * 1000.0
            out["safety"]["m3"] = sum(float(r.safety_knm3 or 0) for r in fd) * 1000.0
            out["unclassified"]["m3"] = 0.0
        dres = [float(r.measured_dre_pct) for r in fd if r.measured_dre_pct is not None]
        return out, unconverted, detail_used, dres

    streams, unconverted, detail_used, dres = streams_for(yr)
    total_m3 = sum(v["m3"] for v in streams.values())
    total_tco2e = sum(v["tco2e"] for v in streams.values())

    # Gas produced over the same population and period
    prod_q = apply_scope(ProductionData.query, ProductionData, **scope)
    if yr is not None:
        prod_q = prod_q.filter(ProductionData.year == yr)
    gas_m3, prod_unconverted = 0.0, 0
    for prow in prod_q.all():
        g = production_gas_m3(prow)
        if g is None:
            prod_unconverted += 1
        else:
            gas_m3 += g

    if all_years:
        intensity, compliant, status_txt = None, None, "Select a single year to assess Decree 21-330 compliance"
    elif gas_m3 > 0:
        intensity = total_m3 / gas_m3 * 100.0
        compliant = intensity <= 1.00
        status_txt = "COMPLIANT (Under 1.00% Target)" if compliant else "EXCEEDS THRESHOLD (> 1.00%)"
    else:
        intensity, compliant, status_txt = None, None, "No gas production recorded for this period"

    yoy = None
    if not all_years:
        prev, _, _, _ = streams_for(yr - 1)
        prev_m3 = sum(v["m3"] for v in prev.values())
        if prev_m3 > 0:
            yoy = (total_m3 - prev_m3) / prev_m3 * 100.0

    def block(key):
        m3 = streams[key]["m3"]
        return {
            "volume_m3": round(m3, 2),
            "volume_knm3": round(m3 / 1000.0, 2),
            "percentage": round(m3 / total_m3 * 100.0, 1) if total_m3 > 0 else 0.0,
            # with operator stream volumes the emissions records may not be split by stream
            "tco2e": round(streams[key]["tco2e"], 2),
        }

    return jsonify({
        "year": yr if yr is not None else "all",
        "facility_id": fac_filter,
        "gwp_horizon": "20" if str(horizon) == "20" else "100",
        "includes_pending": include_pending,
        "routine_flaring": block("routine"),
        "non_routine_flaring": block("non_routine"),
        "safety_flaring": block("safety"),
        "unclassified_flaring": block("unclassified"),
        "total_flaring": {
            "volume_m3": round(total_m3, 2),
            "volume_knm3": round(total_m3 / 1000.0, 2),
            "tco2e": round(total_tco2e, 2),
        },
        "stream_volume_source": "FlaringDetail (operator-reported)" if detail_used else "Emission records",
        "records_with_unknown_volume_unit": unconverted,
        "production_rows_with_unknown_gas_unit": prod_unconverted,
        "gas_production_m3": round(gas_m3, 2),
        "flaring_intensity_pct": round(intensity, 3) if intensity is not None else None,
        "regulatory_threshold_pct": 1.00,
        "statute": "Executive Decree 21-330 Article 9",
        "is_compliant": compliant,
        "compliance_status": status_txt,
        "yoy_change_pct": round(yoy, 2) if yoy is not None else None,
        "measured_dre_pct": round(sum(dres) / len(dres), 2) if dres else None,
        "dre_method": "Measured (FlaringDetail)" if dres else "Not measured (98% default in calculations)",
    })


@dashboard_bp.route("/granular-intensities", methods=["GET"])
@login_required
def get_granular_intensities():
    """Multi-metric intensities for the Master Report (BUG-044).

    Numerator and denominator cover the same facility-years (those with production); BOE is
    computed per production row with the platform's single BOE definition; values that are not
    recorded (saleable production, gas throughput) are returned as null instead of invented
    constants. Same filters and role rules as the rest of the dashboard.
    """
    from services.dashboard_filters import SCF_PER_BOE
    from services.intensity import intensity_cells

    user = get_current_user()
    if is_it_role(user):
        return jsonify({"error": "Forbidden: IT Administrators cannot access operational dashboard data"}), 403
    allowed_fids = get_allowed_facility_ids(user)

    year = request.args.get("year")
    try:
        years = None if (not year or year == "all") else [int(year)]
    except ValueError:
        return jsonify({"error": "Invalid year"}), 400
    facility_id = request.args.get("facility_id") or request.args.get("facilityId")
    fac_filter = int(facility_id) if facility_id and facility_id != "all" else None
    if fac_filter and allowed_fids is not None and fac_filter not in allowed_fids:
        return jsonify({"error": "Unauthorized facility"}), 403

    cells = intensity_cells(years=years, facility_id=fac_filter, allowed_fids=allowed_fids,
                            activity=request.args.get("activity"), division=request.args.get("division"),
                            segment=request.args.get("segment"))
    matched = [(k, c) for k, c in cells.items() if c["has_prod"]]
    ghg = sum(c["s1"] + c["s2"] for _, c in matched)
    ch4 = sum(c["ch4"] for _, c in matched)
    boe = sum(c["boe"] for _, c in matched)
    gas_m3 = sum(c["gas_m3"] for _, c in matched)
    unmatched_ghg = sum(c["s1"] + c["s2"] for _, c in cells.items() if not c["has_prod"])

    # saleable production only where it is actually recorded (no assumed 85 % fraction)
    prod_q = ProductionData.query
    if years:
        prod_q = prod_q.filter(ProductionData.year.in_(years))
    if allowed_fids is not None:
        prod_q = prod_q.filter(ProductionData.facility_id.in_(allowed_fids or [-1]))
    if fac_filter:
        prod_q = prod_q.filter(ProductionData.facility_id == fac_filter)
    saleable_rows = [p for p in prod_q.all() if p.saleable_production_mmboe]
    saleable_boe = sum(float(p.saleable_production_mmboe) * 1e6 for p in saleable_rows) or None
    saleable_ghg = sum(cells[(p.facility_id, p.year)]["s1"] + cells[(p.facility_id, p.year)]["s2"]
                       for p in {(r.facility_id, r.year): r for r in saleable_rows}.values()
                       if (p.facility_id, p.year) in cells) if saleable_boe else None

    ci_total = ghg * 1000.0 / boe if boe > 0 else None
    ci_saleable = saleable_ghg * 1000.0 / saleable_boe if saleable_boe else None
    # NGSI methane intensity (wt %): CH4 mass / natural gas mass, pipeline gas ~0.80 kg/Sm3
    ngsi = ch4 / (gas_m3 * 0.00080) * 100.0 if gas_m3 > 0 else None

    OGCI_TARGET = 17.0
    basis = ci_saleable if ci_saleable is not None else ci_total
    ratio = basis / OGCI_TARGET if basis is not None else None
    return jsonify({
        "year": years[0] if years else "all",
        "facility_id": fac_filter,
        "total_ghg_tco2e": round(ghg, 2),
        "unmatched_ghg_tco2e": round(unmatched_ghg, 2),
        "total_ch4_tonnes": round(ch4, 2),
        "total_production_boe": round(boe, 2),
        "boe_definition_scf_per_boe": round(SCF_PER_BOE, 1),
        "saleable_production_boe": round(saleable_boe, 2) if saleable_boe else None,
        "gross_gas_sm3": round(gas_m3, 2),
        "ci_by_total_production_kg_boe": round(ci_total, 2) if ci_total is not None else None,
        "ci_by_saleable_production_kg_boe": round(ci_saleable, 2) if ci_saleable is not None else None,
        "methane_intensity_ngsi_wt_pct": round(ngsi, 3) if ngsi is not None else None,
        "ogci_target_kg_boe": OGCI_TARGET,
        "ogci_comparison_basis": "saleable" if ci_saleable is not None else ("total" if ci_total is not None else None),
        "ratio_to_ogci_target": round(ratio, 2) if ratio is not None else None,
        "ogci_status": None if ratio is None else ("WITHIN TARGET" if basis <= OGCI_TARGET else f"{round(ratio, 1)}x ABOVE TARGET"),
    })


