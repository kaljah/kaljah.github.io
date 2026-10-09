"""Scope 2 gas split and dual-reporting totals.

Scope 2 rows store CO2e only. For grid electricity the split is not lost: the grid region's factor
is CO2 + CH4 x GWP + N2O x GWP per kWh (electricity_factors), so the gas masses follow from the kWh.
That split is reported by the API (it used to give the whole CO2e as CO2) and lets the GWP-20 view
re-weight Scope 2 like Scope 1 (it was left on GWP-100). Other sources (supplier factors, steam,
cooling) stay CO2e reported as CO2.
"""
from collections import defaultdict


def _grid(e):
    if "electric" not in str(e.source_type or "").lower() or not e.grid_region or not e.electricity_kwh:
        return None
    from electricity_factors import grid_entry

    return grid_entry(e.grid_region)[1]


def gas_split(e):
    """{"co2", "ch4", "n2o"} in tonnes for one Scope 2 record (location-based)."""
    entry = _grid(e)
    if entry is None:
        return {"co2": float(e.co2e or 0), "ch4": 0.0, "n2o": 0.0}
    kwh = float(e.electricity_kwh)
    return {g: kwh * float(entry.get(g) or 0) / 1000.0 for g in ("co2", "ch4", "n2o")}


def yearly_totals(query, by_fac, horizon="100"):
    """{(year, facility_id | "total"): {"location", "market", "energy"}} over a filtered Scope 2 query.
    The location total follows the GWP horizon (GWP-20 adds CH4 / N2O x (GWP20 - GWP100))."""
    from services.dashboard_filters import horizon_delta

    out = defaultdict(lambda: {"location": 0.0, "market": 0.0, "energy": 0.0})
    for e in query.all():
        d = out[(int(e.year), e.facility_id if by_fac else "total")]
        delta = 0.0
        if str(horizon) == "20":
            g = gas_split(e)
            delta = horizon_delta(g["ch4"], g["n2o"], "20")
        d["location"] += float(e.co2e or 0) + delta
        market = e.co2e_market_based if e.co2e_market_based is not None else e.co2e
        d["market"] += float(market or 0) + (delta if e.co2e_market_based is None else 0.0)
        d["energy"] += float(e.electricity_kwh or 0)
    return out
