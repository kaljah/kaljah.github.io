"""Scope 2 gas split and dual-reporting totals.

Scope 2 rows store CO2e only. For grid electricity the split is not lost: the grid region's factor
is CO2 + CH4 x GWP + N2O x GWP per kWh (electricity_factors), so the gas masses follow from the kWh.
That split is reported by the API (it used to give the whole CO2e as CO2) and lets the GWP-20 view
re-weight Scope 2 like Scope 1 (it was left on GWP-100). Other sources (supplier factors, steam,
cooling) stay CO2e reported as CO2.
"""
from collections import defaultdict


def _grid_lookup(source_type, grid_region, electricity_kwh, grid_cache=None, year=None):
    """The grid row of the record's reporting year (eGRID2022 from 2022; audit 2026-11 F-S23-09)."""
    if "electric" not in str(source_type or "").lower() or not grid_region or not electricity_kwh:
        return None
    from electricity_factors import EGRID2022_FIRST_YEAR, grid_entry_for_year

    vintage = 2022 if year not in (None, "") and int(year) >= EGRID2022_FIRST_YEAR else None
    if grid_cache is not None and (grid_region, vintage) in grid_cache:
        return grid_cache[(grid_region, vintage)]
    entry = grid_entry_for_year(grid_region, vintage)[1]
    if grid_cache is not None:
        grid_cache[(grid_region, vintage)] = entry
    return entry


def _grid(e):
    return _grid_lookup(e.source_type, e.grid_region, e.electricity_kwh, year=getattr(e, "year", None))


def _matches_co2e(g, e):
    from calculations.constants import get_active_gwp

    gw = get_active_gwp()
    co2e = g["co2"] + g["ch4"] * float(gw["CH4"]) + g["n2o"] * float(gw["N2O"])
    ref = float(getattr(e, "co2e_location_based", None) or getattr(e, "co2e", None) or 0.0)
    return ref > 0 and abs(co2e - ref) <= 1e-3 * ref


def gas_split(e, co2e_as_co2=True):
    """{"co2", "ch4", "n2o"} in tonnes for one Scope 2 record (location-based): the masses stored with the
    record when its calculation gave them (steam, BA-009), else the grid split, else the CO2e as CO2."""
    if getattr(e, "co2_emissions", None) is not None and getattr(e, "ch4_emissions", None) is not None:
        stored = {"co2": float(e.co2_emissions), "ch4": float(e.ch4_emissions), "n2o": float(e.n2o_emissions or 0)}
        if "electric" not in str(getattr(e, "source_type", "") or "").lower() or _matches_co2e(stored, e):
            # electricity too, when the stored masses still give the record's CO2e (an edit may have left them
            # behind); the grid split ignored them (audit 2026-11 F-RPT-15)
            return stored
    entry = _grid(e)
    if entry is None:
        # no split known (CHP, cooling, a supplier factor): the CO2e as CO2, or zeros where a CO2 *mass* column is
        # printed (the CO2e was put in the CO2 column: audit 2026-11 F-E2E-04)
        return {"co2": float(e.co2e or 0) if co2e_as_co2 else 0.0, "ch4": 0.0, "n2o": 0.0}
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
            *_s2_gas_columns(),
        ).all()
        for yr, fid, src_type, grid_region, kwh, co2e, co2e_mkt, ch4_t, n2o_t, mkt_ef, _yr in rows:
            d = out[(int(yr), fid if by_fac else "total")]
            loc, mkt = record_totals_fields(
                src_type, grid_region, kwh, co2e, co2e_mkt, horizon,
                grid_cache=grid_cache, gwp_diff=gwp_diff, ch4_t=ch4_t, n2o_t=n2o_t, market_ef=mkt_ef, year=yr,
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
    ch4_t=None,
    n2o_t=None,
    market_ef=None,
    year=None,
):
    """Tuple-friendly counterpart to record_totals() avoiding full ORM hydration in hot paths.

    GWP-20 re-weights every CH4 / N2O mass in the totals: the grid split of an electricity record, or the masses
    stored with a steam record; the market total gets the same delta when its factor is not a contract or a
    (CO2-only) residual mix, i.e. when it equals the location-based value. Steam and grid-fallback market totals
    were left on GWP-100 (audit 2026-11 F-GUI-02 / F-S23-08)."""
    delta = 0.0
    is_elec = "electric" in str(source_type or "").lower()
    if str(horizon) == "20":
        entry = _grid_lookup(source_type, grid_region, electricity_kwh, grid_cache=grid_cache, year=year)
        if entry is not None:
            kwh = float(electricity_kwh)
            c, n = kwh * float(entry.get("ch4") or 0) / 1000.0, kwh * float(entry.get("n2o") or 0) / 1000.0
        elif not is_elec and (ch4_t is not None or n2o_t is not None):
            c, n = float(ch4_t or 0.0), float(n2o_t or 0.0)
        else:
            c, n = 0.0, 0.0
        if gwp_diff is None:
            from services.dashboard_filters import horizon_delta

            delta = horizon_delta(c, n, "20")
        else:
            delta = c * gwp_diff[0] + n * gwp_diff[1]
    location = float(co2e or 0) + delta
    if co2e_market_based is None:
        return location, location
    market = float(co2e_market_based or 0)
    if delta and market_ef is None:
        if not is_elec:
            market += delta  # steam / heat: the market value is the location value
        else:
            from electricity_factors import residual_mix_for

            if residual_mix_for(grid_region) is None and abs(market - float(co2e or 0)) <= 1e-9 * max(1.0, abs(market)):
                market += delta  # grid-average fallback: the location value
    return location, market


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
        ch4_t=getattr(e, "ch4_emissions", None),
        n2o_t=getattr(e, "n2o_emissions", None),
        market_ef=getattr(e, "market_emission_factor", None),
    )


def _s2_gas_columns():
    from models import Scope2Emission

    return (Scope2Emission.ch4_emissions, Scope2Emission.n2o_emissions, Scope2Emission.market_emission_factor,
            Scope2Emission.year)


def __getattr__(name):  # S2_GAS_COLUMNS, resolved after the models are importable
    if name == "S2_GAS_COLUMNS":
        return _s2_gas_columns()
    raise AttributeError(name)
