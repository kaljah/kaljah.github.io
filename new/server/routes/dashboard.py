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
    EmissionSource,
)
from extensions import db
from utils import get_current_user, get_allowed_facility_ids, log_activity_and_notify
from sqlalchemy import func
from datetime import datetime, timezone
from cachetools import TTLCache, cached, keys
from calculations.constants import get_active_gwp
from services.ogmp import compute_facility_ogmp_level, ogmp_level_for
from services.dashboard_filters import _parse_facility_ids
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

# Hit/miss counters for the batch-all cache; summarised in the log every _CACHE_LOG_EVERY lookups.
_CACHE_STATS = {"hits": 0, "misses": 0}
_CACHE_STATS_LOCK = threading.Lock()
_CACHE_LOG_EVERY = 1000


def _record_cache_lookup(hit):
    with _CACHE_STATS_LOCK:
        _CACHE_STATS["hits" if hit else "misses"] += 1
        total = _CACHE_STATS["hits"] + _CACHE_STATS["misses"]
        if total < _CACHE_LOG_EVERY:
            return
        hits, misses = _CACHE_STATS["hits"], _CACHE_STATS["misses"]
        _CACHE_STATS["hits"] = _CACHE_STATS["misses"] = 0
    current_app.logger.info(
        "dashboard batch-all cache: %d hits, %d misses (%.0f%% hit rate) over %d lookups",
        hits, misses, 100.0 * hits / total, total,
    )


def cache_stats():
    """Current batch-all cache counters (since the last log line or reset)."""
    with _CACHE_STATS_LOCK:
        return dict(_CACHE_STATS)


def reset_cache_stats():
    with _CACHE_STATS_LOCK:
        _CACHE_STATS["hits"] = _CACHE_STATS["misses"] = 0


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
    facility_id = request.args.get("facilityId") or request.args.get("facility_id")
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
    scope2_method = request.args.get("scope2_method", "location")

    parsed_facility_ids = _parse_facility_ids(facility_id)
    cache_facility = tuple(sorted(parsed_facility_ids)) if parsed_facility_ids is not None else facility_id
    cache_key = (
        "batch_all",
        cache_facility,
        year,
        activity,
        division,
        segment,
        group_by,
        include_pending,
        gwp_horizon,
        scope2_method,
        user.id if user else 0,
        # BUG-0009: the facility scope is part of the key, so a role or location change made by
        # IT is honoured at once instead of serving the previous scope's totals for 5 minutes
        user.role if user else None,
        tuple(sorted(allowed_fids)) if allowed_fids is not None else None,
    )
    # Honour invalidations made by other workers before trusting this worker's cache
    # (at most one database read per second; a no-op on SQLite).
    _get_global_cache_epoch()
    with CACHE_LOCK:
        cached_result = DASHBOARD_CACHE.get(cache_key)
    if cached_result is not None:
        _record_cache_lookup(hit=True)
        return jsonify(cached_result)
    _record_cache_lookup(hit=False)

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
                scope2_method=scope2_method,
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
                scope2_method=scope2_method,
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
                scope2_method=scope2_method,
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
                    scope2_method=scope2_method,
                )
            # same population as the other panels (the block used to ignore every filter)
            unc_fids = _filtered_facility_ids(allowed_fids, activity, division, segment)
            if parsed_facility_ids is not None:
                if unc_fids is not None:
                    matched = [fid for fid in parsed_facility_ids if fid in unc_fids]
                    unc_fids = tuple(sorted(matched)) if matched else (-1,)
                else:
                    unc_fids = tuple(sorted(parsed_facility_ids))
            f_uncertainty = executor.submit(
                _run_in_app_ctx,
                app,
                _query_uncertainty,
                year=uncertainty_year,
                allowed_fids=unc_fids,
                facility_id=None,
                scope2_method=scope2_method,
            )
            f_years = executor.submit(_run_in_app_ctx, app, _query_available_years, allowed_fids)

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
    facility_id = request.args.get("facilityId") or request.args.get("facility_id")
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
        scope2_method=request.args.get("scope2_method", "location"),
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
    scope2_method="location",
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
                "ch4_total": 0.0, "n2o_total": 0.0, "scope2_total": 0.0, "scope2_location_total": 0.0,
                "scope2_market_total": 0.0, "scope2_energy": 0.0, "scope2_method": scope2_method,
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

    from services.scope2_gases import yearly_totals
    s2_q = apply_year(apply_scope(Scope2Emission.query, Scope2Emission, **scope), Scope2Emission, year)
    s2_q = s2_q.filter(Scope2Emission.status.in_(statuses(include_pending)), Scope2Emission.year.isnot(None))
    for (yr, fid), t in yearly_totals(s2_q, by_fac, horizon).items():
        d = yearly.setdefault((yr, fid), blank(yr, fid))
        d["scope2_location_total"] += t["location"]
        d["scope2_market_total"] += t["market"]
        # Dual reporting: use chosen method
        d["scope2_total"] += t["market"] if str(scope2_method).lower() == "market" else t["location"]
        d["scope2_energy"] += t["energy"]

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
    scope2_method="location",
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
    # Scope 2 per record, as in the summary: the method chosen and the GWP horizon (GWP-20 re-weighted
    # Scope 2 in the summary but not here, so the breakdown did not add up to it; bug hunt 2026-10-15 #18)
    from collections import defaultdict

    from services.scope2_gases import record_totals

    s2_q = apply_year(apply_scope(db.session.query(Scope2Emission), Scope2Emission, **scope), Scope2Emission, year)
    s2_by_fac = defaultdict(float)
    for e in s2_q.filter(Scope2Emission.status.in_(st)).all():
        loc, mkt = record_totals(e, "20" if str(gwp_horizon).lower() in ("20", "gwp20", "20yr") else "100")
        s2_by_fac[e.facility_id] += mkt if str(scope2_method).lower() == "market" else loc
    s2_labels = {f[0]: f for f in db.session.query(*labels).filter(Facility.id.in_(list(s2_by_fac) or [-1])).all()}
    s2 = [(*s2_labels[fid], total) for fid, total in s2_by_fac.items() if fid in s2_labels]
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



def _query_available_years(allowed_fids=None):
    """Pure query logic for /years — returns a plain Python list. Years of the facilities in the
    user's scope only (bug hunt 2026-10-15 #15: every facility's years were offered)."""
    def scoped(model, verified=True):
        q = db.session.query(model.year)
        if verified:
            q = q.filter(model.status == "Verified")
        if allowed_fids is not None:
            q = q.filter(model.facility_id.in_(allowed_fids or [-1]))
        return q.distinct().all()

    years1 = scoped(Emission)
    years2 = scoped(Scope2Emission)
    years3 = scoped(Scope3Emission)
    years4 = scoped(ProductionData, verified=False)
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
    scope2_method = request.args.get("scope2_method") or request.args.get("scope2Method") or "location"
    return jsonify(
        _query_summary(
            facility_id=request.args.get("facilityId") or request.args.get("facility_id"),
            year=request.args.get("year"),
            activity=request.args.get("activity"),
            division=request.args.get("division"),
            group_by=request.args.get("groupBy"),
            allowed_fids=allowed_fids,
            segment=request.args.get("segment"),
            include_pending=request.args.get("includePending", "false").lower() == "true",
            gwp_horizon=request.args.get("gwp_horizon", "100"),
            scope2_method=scope2_method,
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
    return jsonify(_query_available_years(get_allowed_facility_ids(user)))


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
            facility_id=request.args.get("facilityId") or request.args.get("facility_id"),
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
            facility_id=request.args.get("facilityId") or request.args.get("facility_id"),
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
    user = get_current_user()
    if is_it_role(user):
        return (
            jsonify(
                {"error": "Forbidden: IT Administrators cannot access corporate goal data"}
            ),
            403,
        )
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
    user = get_current_user()
    if is_it_role(user):
        return (
            jsonify(
                {"error": "Forbidden: IT Administrators cannot access corporate baseline data"}
            ),
            403,
        )
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
            facility_id=request.args.get("facilityId") or request.args.get("facility_id"),
            year=request.args.get("year"),
            activity=request.args.get("activity"),
            division=request.args.get("division"),
            allowed_fids=allowed_fids,
            segment=request.args.get("segment"),
            gwp_horizon=request.args.get("gwp_horizon", "100"),
            include_pending=request.args.get("includePending", "false").lower() == "true",
            scope2_method=request.args.get("scope2_method", "location"),
        )
    )


@dashboard_bp.route("/base-year-recalculation", methods=["POST"])
@login_required
def create_base_year_recalculation():
    """Create a new base year recalculation entry (delegates to canonical managedata route)."""
    from routes.managedata import add_base_year_recalculation
    return add_base_year_recalculation()



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
            facility_id=request.args.get("facilityId") or request.args.get("facility_id"),
            year=request.args.get("year"),
            activity=request.args.get("activity"),
            division=request.args.get("division"),
            allowed_fids=allowed_fids,
            segment=request.args.get("segment"),
            include_pending=request.args.get("includePending", "false").lower() == "true",
            gwp_horizon=request.args.get("gwp_horizon", "100"),
            scope2_method=request.args.get("scope2_method", "location"),
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
    scope2_method="location",
):
    """Intensity per year for the trend chart (RC-9: same computation as /intensity-stats)."""
    from services.intensity import intensity_trend

    return intensity_trend(years or [], include_pending=include_pending, gwp_horizon=gwp_horizon,
                           scope2_method=scope2_method,
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
    scope2_method="location",
):
    """Per-facility intensity metrics (kg/BOE, loss rates, OGMP) - see services/intensity.py."""
    from services.intensity import intensity_rows

    return intensity_rows(year=year, include_pending=include_pending, gwp_horizon=gwp_horizon,
                          scope2_method=scope2_method,
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
    raw_facility_id = request.args.get("facility_id") or request.args.get("facilityId")
    parsed_facility_ids = _parse_facility_ids(raw_facility_id)
    scope = (request.args.get("scope") or "all").strip().lower()
    export_fmt = (request.args.get("export") or "").strip().lower()
    allowed_fids = get_allowed_facility_ids(user)

    # RBAC: if facility_id requested, verify it's within the user's allowed set
    if parsed_facility_ids and allowed_fids is not None:
        if not set(parsed_facility_ids).issubset(set(allowed_fids)):
            return jsonify({"error": "Forbidden: You do not have access to this facility"}), 403

    include_gwp = request.args.get("gwp_uncertainty", "").strip().lower() in ("true", "1", "yes")
    scope2_method = request.args.get("scope2_method", "location").strip().lower()
    result = _query_uncertainty(
        year=year,
        allowed_fids=allowed_fids,
        facility_id=tuple(sorted(parsed_facility_ids)) if parsed_facility_ids is not None else None,
        scope=scope,
        include_gwp_uncertainty=include_gwp,
        scope2_method=scope2_method,
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
def _query_uncertainty(year=None, allowed_fids=None, facility_id=None, scope="all", include_gwp_uncertainty=False, scope2_method="location"):
    """Inventory uncertainty (95 %, k = 2) - see services/inventory_uncertainty.py (RC-10)."""
    from services.inventory_uncertainty import inventory_uncertainty

    if not year:
        # latest year with Verified data that is not in the future
        cy = datetime.now(timezone.utc).year
        year = db.session.query(func.max(Emission.year)).filter(
            Emission.status == "Verified", Emission.year <= cy).scalar() or cy
    return inventory_uncertainty(
        int(year),
        allowed_fids=allowed_fids,
        facility_id=facility_id,
        scope=scope,
        include_gwp_uncertainty=include_gwp_uncertainty,
        scope2_method=scope2_method,
    )


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


@dashboard_bp.route("/equipment-emissions", methods=["GET"])
@login_required
def get_equipment_emissions():
    """Returns top equipment emissions breakdown for a given process/source category."""
    from services.dashboard_filters import apply_scope, apply_year, source_category, statuses

    user = get_current_user()
    if is_it_role(user):
        return jsonify({"error": "Forbidden: IT personnel cannot access operational dashboard data"}), 403

    allowed_fids = get_allowed_facility_ids(user)
    source_cat = str(request.args.get("source") or request.args.get("process") or "").strip().lower()
    year = request.args.get("year")
    fac_id = request.args.get("facilityId") or request.args.get("facility_id")
    activity = request.args.get("activity")
    division = request.args.get("division")
    segment = request.args.get("segment")
    include_pending = request.args.get("includePending") == "true"
    raw_lim = request.args.get("limit", 8)
    limit = max(1, min(100, int(raw_lim))) if str(raw_lim).isdigit() else 8
    scope = dict(allowed_fids=allowed_fids, facility_id=fac_id, activity=activity, division=division, segment=segment)
    query = Emission.query.filter(Emission.status.in_(statuses(include_pending)))
    query = apply_year(apply_scope(query, Emission, **scope), Emission, year)

    emissions = query.all()

    eq_tags = set(e.equipment_id.strip() for e in emissions if e.equipment_id and str(e.equipment_id).strip())
    source_names = {}
    if eq_tags:
        sources = EmissionSource.query.filter(EmissionSource.equipment_id.in_(list(eq_tags))).all()
        for s in sources:
            if s.equipment_id and s.name:
                source_names[s.equipment_id.strip()] = s.name

    total_source_emissions = 0.0
    unassigned_emissions = 0.0
    unassigned_count = 0
    equipment_totals = {}

    for e in emissions:
        cat = source_category(e.process_type)
        cat_norm = "vented" if source_cat == "venting" else ("fugitive" if source_cat in ("fugitive", "equipment leaks") else source_cat)

        if source_cat and source_cat != "all":
            if cat != cat_norm and str(e.process_type or "").strip().lower() != source_cat:
                continue

        val = float(e.co2e_total or 0.0)
        total_source_emissions += val

        eq_id = (e.equipment_id or "").strip()
        if not eq_id or eq_id.lower() in ("unassigned", "n/a", "none", "-"):
            unassigned_emissions += val
            unassigned_count += 1
        else:
            if eq_id not in equipment_totals:
                equipment_totals[eq_id] = {
                    "equipment_id": eq_id,
                    "name": source_names.get(eq_id) or eq_id,
                    "facility_id": e.facility_id,
                    "emissions": 0.0,
                    "ch4_emissions": 0.0,
                    "record_count": 0,
                    "process_type": e.process_type,
                }
            equipment_totals[eq_id]["emissions"] += val
            equipment_totals[eq_id]["ch4_emissions"] += float(e.ch4_emissions or 0.0)
            equipment_totals[eq_id]["record_count"] += 1

    sorted_eq = sorted(equipment_totals.values(), key=lambda x: x["emissions"], reverse=True)
    top_items = sorted_eq[:limit]
    other_items = sorted_eq[limit:]

    other_emissions = sum(x["emissions"] for x in other_items)
    other_count = len(other_items)

    for item in top_items:
        item["share_pct"] = round((item["emissions"] / total_source_emissions * 100), 2) if total_source_emissions > 0 else 0.0
        item["emissions"] = round(item["emissions"], 2)

    return jsonify({
        "source": source_cat,
        "total_emissions": round(total_source_emissions, 2),
        "total_equipment_count": len(sorted_eq),
        "equipment": top_items,
        "other_emissions": round(other_emissions, 2),
        "other_count": other_count,
        "other_share_pct": round((other_emissions / total_source_emissions * 100), 2) if total_source_emissions > 0 else 0.0,
        "unassigned_emissions": round(unassigned_emissions, 2),
        "unassigned_count": unassigned_count,
        "unassigned_share_pct": round((unassigned_emissions / total_source_emissions * 100), 2) if total_source_emissions > 0 else 0.0,
    })


# Route modules split out of this file; imported last because they use the helpers above.
from routes import dashboard_bridge, dashboard_flaring, dashboard_ogmp, dashboard_sbti  # noqa: E402,F401
