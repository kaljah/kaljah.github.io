"""Scope 2 gas split and dual-reporting totals.

Scope 2 rows store CO2e only. For grid electricity the split is not lost: the grid region's factor
is CO2 + CH4 x GWP + N2O x GWP per kWh (electricity_factors), so the gas masses follow from the kWh.
That split is reported by the API (it used to give the whole CO2e as CO2) and lets the GWP-20 view
re-weight Scope 2 like Scope 1 (it was left on GWP-100). Other sources (supplier factors, steam,
cooling) stay CO2e reported as CO2.
"""
from collections import defaultdict


def _grid_lookup(source_type, grid_region, electricity_kwh, grid_cache=None):
    if "electric" not in str(source_type or "").lower() or not grid_region or not electricity_kwh:
        return None
    if grid_cache is not None and grid_region in grid_cache:
        return grid_cache[grid_region]
    from electricity_factors import grid_entry

    entry = grid_entry(grid_region)[1]
    if grid_cache is not None:
        grid_cache[grid_region] = entry
    return entry


def _grid(e):
    return _grid_lookup(e.source_type, e.grid_region, e.electricity_kwh)


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
    out = defaultdict(lambda: {"location": 0.0, "market": 0.0, "energy": 0.0})
    if hasattr(query, "with_entities"):
        from models import Scope2Emission

        grid_cache = {}
        gwp_diff = None
        if str(horizon) == "20":
            from services.dashboard_filters import gwp_pair

            c100, n100 = gwp_pair("100")
            c20, n20 = gwp_pair("20")
            gwp_diff = (c20 - c100, n20 - n100)
        rows = query.with_entities(
            Scope2Emission.year,
            Scope2Emission.facility_id,
            Scope2Emission.source_type,
            Scope2Emission.grid_region,
            Scope2Emission.electricity_kwh,
            Scope2Emission.co2e,
            Scope2Emission.co2e_market_based,
        ).all()
        for yr, fid, src_type, grid_region, kwh, co2e, co2e_mkt in rows:
            d = out[(int(yr), fid if by_fac else "total")]
            loc, mkt = record_totals_fields(
                src_type, grid_region, kwh, co2e, co2e_mkt, horizon,
                grid_cache=grid_cache, gwp_diff=gwp_diff,
            )
            d["location"] += loc
            d["market"] += mkt
            d["energy"] += float(kwh or 0)
        return out

    for e in query.all():
        d = out[(int(e.year), e.facility_id if by_fac else "total")]
        loc, mkt = record_totals(e, horizon)
        d["location"] += loc
        d["market"] += mkt
        d["energy"] += float(e.electricity_kwh or 0)
    return out


def record_totals_fields(
    source_type,
    grid_region,
    electricity_kwh,
    co2e,
    co2e_market_based,
    horizon="100",
    grid_cache=None,
    gwp_diff=None,
):
    """Tuple-friendly counterpart to record_totals() avoiding full ORM hydration in hot paths."""
    delta = 0.0
    if str(horizon) == "20":
        entry = _grid_lookup(source_type, grid_region, electricity_kwh, grid_cache=grid_cache)
        if entry is None:
            ch4_t, n2o_t = 0.0, 0.0
        else:
            kwh = float(electricity_kwh)
            ch4_t = kwh * float(entry.get("ch4") or 0) / 1000.0
            n2o_t = kwh * float(entry.get("n2o") or 0) / 1000.0
        if gwp_diff is None:
            from services.dashboard_filters import horizon_delta

            delta = horizon_delta(ch4_t, n2o_t, "20")
        else:
            delta = ch4_t * gwp_diff[0] + n2o_t * gwp_diff[1]
    location = float(co2e or 0) + delta
    market = co2e_market_based if co2e_market_based is not None else co2e
    return location, float(market or 0) + (delta if co2e_market_based is None else 0.0)


def record_totals(e, horizon="100"):
    """(location, market) tCO2e of one Scope 2 record at the GWP horizon (GWP-20 adds the CH4 / N2O
    share x (GWP20 - GWP100); a market total entered by the user is kept as given)."""
    return record_totals_fields(
        e.source_type,
        e.grid_region,
        e.electricity_kwh,
        e.co2e,
        e.co2e_market_based,
        horizon,
    )
