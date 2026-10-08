"""Year-over-year emissions bridge ("what moved the total").

Registered on the same ``dashboard_bp`` blueprint as the other dashboard routes. It reuses
``_query_summary`` so the bridge always reconciles with the per-year totals shown elsewhere on the
dashboard: start (previous year) + sum of the category changes = end (selected year).
"""
from flask import jsonify, request
from routes.auth import login_required
from utils import get_allowed_facility_ids, get_current_user
from routes.dashboard import _query_scope3_summary, _query_summary, dashboard_bp, is_it_role

# (label, summary keys that feed it). Scope 3 is not part of the Scope 1+2 summary; it is added as its
# own step only when asked for (``include_scope3``), with the per-year totals injected under "scope3".
BRIDGE_CATEGORIES = (
    ("Combustion", ("combustion",)),
    ("Flaring", ("flaring",)),
    ("Venting", ("venting",)),
    ("Fugitive", ("fugitive",)),
    ("Process & other", ("process", "other")),
    ("Scope 2", ("scope2_total",)),
)
SCOPE3_CATEGORY = ("Scope 3", ("scope3",))


def build_bridge(rows, year, include_scope3=False):
    """Pure helper: ``rows`` are ``_query_summary`` rows (one per year), ``year`` the selected year.

    Returns the bridge dict, or ``None`` when there is no earlier year to compare against.
    """
    by_year = {int(r["year"]): r for r in rows if r.get("year") is not None}
    if not by_year:
        return None
    if year is None:
        year = max(by_year)
    prev_candidates = [y for y in by_year if y < year]
    if year not in by_year or not prev_candidates:
        return None
    prev_year = max(prev_candidates)
    cur, prev = by_year[year], by_year[prev_year]
    categories = BRIDGE_CATEGORIES + ((SCOPE3_CATEGORY,) if include_scope3 else ())

    def val(row, keys):
        return sum(float(row.get(k) or 0) for k in keys)

    steps = [
        {"name": label, "delta": round(val(cur, keys) - val(prev, keys), 3)}
        for label, keys in categories
    ]
    start = sum(val(prev, keys) for _, keys in categories)
    end = sum(val(cur, keys) for _, keys in categories)
    return {
        "year": year,
        "prev_year": prev_year,
        "start": round(start, 3),
        "end": round(end, 3),
        "steps": steps,
        "scope3": include_scope3,
        "reconciles": abs(start + sum(s["delta"] for s in steps) - end) < 0.01,
    }


@dashboard_bp.route("/yoy-bridge", methods=["GET"])
@login_required
def get_yoy_bridge():
    """Scope 1+2 change between the selected year and the closest earlier year with data."""
    user = get_current_user()
    if is_it_role(user):
        return jsonify({"error": "Forbidden: IT Administrators cannot access operational dashboard data"}), 403

    year = request.args.get("year")
    try:
        yr = None if not year or year == "all" else int(year)
    except ValueError:
        return jsonify({"error": "Invalid year"}), 400

    include_scope3 = request.args.get("includeScope3", "false").lower() == "true"
    allowed_fids = get_allowed_facility_ids(user)
    rows = _query_summary(
        facility_id=request.args.get("facilityId"),
        year=None,
        activity=request.args.get("activity"),
        division=request.args.get("division"),
        allowed_fids=allowed_fids,
        segment=request.args.get("segment"),
        include_pending=request.args.get("includePending", "false").lower() == "true",
        gwp_horizon=request.args.get("gwp_horizon", "100"),
    )
    if include_scope3:
        s3 = _query_scope3_summary(
            facility_id=request.args.get("facilityId"),
            year=None,
            activity=request.args.get("activity"),
            division=request.args.get("division"),
            allowed_fids=allowed_fids,
            segment=request.args.get("segment"),
            include_pending=request.args.get("includePending", "false").lower() == "true",
        )["by_year"]
        # _query_summary is cached and returns shared dicts: copy before adding a key.
        rows = [dict(r, scope3=s3.get(str(r["year"]), 0.0)) for r in rows]
    return jsonify(build_bridge(rows, yr, include_scope3) or {"steps": [], "message": "No earlier year to compare against"})
