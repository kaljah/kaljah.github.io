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


def list_row_gases(row):
    """Gas masses of a GET /api/emissions/ Scope 2 row (fuel = grid region, amount = kWh), so a report on
    another GWP set re-weights a grid record's CH4 / N2O as it does Scope 1 (the list gave 0 for every gas).
    The split is used only when it gives back the stored CO2e; otherwise the CO2e is reported as CO2."""
    from types import SimpleNamespace

    from calculations.constants import get_active_gwp

    co2e = float(row.co2e_total or 0)
    g = gas_split(SimpleNamespace(source_type="electricity", grid_region=row.fuel, electricity_kwh=row.amount, co2e=co2e))
    gwp = get_active_gwp()
    if abs(g["co2"] + g["ch4"] * gwp["CH4"] + g["n2o"] * gwp["N2O"] - co2e) > 1e-3 * max(abs(co2e), 1e-9):
        g = {"co2": co2e, "ch4": 0.0, "n2o": 0.0}
    return {"co2_emissions": g["co2"], "ch4_emissions": g["ch4"], "n2o_emissions": g["n2o"]}


def yearly_totals(query, by_fac, horizon="100"):
    """{(year, facility_id | "total"): {"location", "market", "energy"}} over a filtered Scope 2 query.
    The location total follows the GWP horizon (GWP-20 adds CH4 / N2O x (GWP20 - GWP100))."""
    from services.dashboard_filters import horizon_delta

    out = defaultdict(lambda: {"location": 0.0, "market": 0.0, "energy": 0.0})
    for e in query.all():
        d = out[(int(e.year), e.facility_id if by_fac else "total")]
        loc, mkt = record_totals(e, horizon)
        d["location"] += loc
        d["market"] += mkt
        d["energy"] += float(e.electricity_kwh or 0)
    return out


def record_totals(e, horizon="100"):
    """(location, market) tCO2e of one Scope 2 record at the GWP horizon (GWP-20 adds the CH4 / N2O
    share x (GWP20 - GWP100); a market total entered by the user is kept as given)."""
    from services.dashboard_filters import horizon_delta

    delta = 0.0
    if str(horizon) == "20":
        g = gas_split(e)
        delta = horizon_delta(g["ch4"], g["n2o"], "20")
    location = float(e.co2e or 0) + delta
    market = e.co2e_market_based if e.co2e_market_based is not None else e.co2e
    return location, float(market or 0) + (delta if e.co2e_market_based is None else 0.0)
