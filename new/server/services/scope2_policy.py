"""Scope 2 factor policy and the purchased-steam calculation (moved out of routes/scope2.py, blind audit 2026-11-17).

- Location-based electricity uses a grid-average factor (the facility's country grid for an unknown region); a
  supplier / contractual factor is the market-based factor (GHG Protocol Scope 2 Guidance ch. 6; BA-007 / BA-010).
- Steam of unknown generation: API Compendium 2021 Exhibit 8.3 (LHV basis, CH4 / N2O always added; BA-045 / BA-008).
"""
from calculations.indirect import DEFAULT_BOILER_EFFICIENCY, DEFAULT_TRANSMISSION_LOSS, heat_to_mmbtu
from electricity_factors import GRID_FACTORS, grid_entry, grid_entry_for_year, grid_factor_kg_co2e_per_kwh
from extensions import db
from input_validation import ValidationError, parse_number
from models import Facility

# Steam / heat of unknown generation (API Compendium 2021 s8.1.5, Exhibit 8.3): a natural-gas boiler at 92 %
# efficiency on the LHV basis, so the LHV natural-gas factors: CO2 5.90E-02 t/MMBtu (Table 4-3), CH4 1.1E-06 and
# N2O 3.0E-07 t/MMBtu (Table 4-7, controlled boiler). It used the HHV 53.06 kg/MMBtu with the LHV efficiency
# (-10.2 % vs Exhibit 8.3, BA-045) and added CH4 / N2O only when the CO2 factor was exactly the default (BA-008).
_DEFAULT_BOILER_EF_KG_PER_MMBTU = 59.0
_DEFAULT_BOILER_CH4_KG_PER_MMBTU = 0.0011
_DEFAULT_BOILER_N2O_KG_PER_MMBTU = 0.0003
# natural gas, HHV basis (40 CFR 98 Table C-1): the CHP fuel factor, and the steam default of records saved before
# 2026-11-17 (kept for the GWP re-weighting of those records)
_LEGACY_BOILER_EF_KG_PER_MMBTU = 53.06
# Upper bound for a supplier-specific grid factor; the most carbon-intensive grids are ~1.2 kg CO2e/kWh.
MAX_GRID_EF_KG_PER_KWH = 2.0


def resolve_electricity_factor(grid_region, facility_id=None, year=None):
    """Location-based grid factor of a Scope 2 electricity record, one policy for manual, JSON-import and
    file-bulk paths (BUG-099).

    GHG Protocol Scope 2 Guidance ch. 6: the location-based method uses a grid-average factor. A known grid
    region gives its factor (API Compendium Tables 8-2 / 8-6, active GWP set); an unknown one falls back to the
    catalog grid of the facility's country, and is refused when there is none. A supplier / contractual factor
    is never the location-based value (it was, for an unknown grid, BA-007): callers pass it to the market-based
    method (supplier_market_factor). Returns (factor_kg_per_kwh, resolved_grid_region).
    """
    name = str(grid_region or "").strip()
    # the reporting year's vintage (eGRID2022 from 2022; audit 2026-11 F-S23-09)
    canonical, entry = grid_entry_for_year(name, year) if name else (name, None)
    if entry is not None:
        return grid_factor_kg_co2e_per_kwh(entry), canonical
    country = None
    if facility_id not in (None, ""):
        try:
            fac = db.session.get(Facility, int(facility_id))
            country = getattr(fac, "country", None) if fac else None
        except (TypeError, ValueError):
            country = None
    c_name, c_entry = grid_entry_for_year(country, year) if country else (None, None)
    if c_entry is not None:
        return grid_factor_kg_co2e_per_kwh(c_entry), c_name
    raise ValidationError(
        f"Unknown grid region '{name}'"
        + (f" and no catalog grid for the facility's country ({country})" if country else "")
        + ": the location-based method needs a grid-average factor. Select a known grid; a supplier or "
        "contractual factor is entered as the market-based factor (market_emission_factor).",
        "grid_region",
        extra={"valid_regions": sorted(list(GRID_FACTORS.keys()))},
    )


def supplier_market_factor(market_ef, supplied_ef):
    """The contractual factor for the market-based method: market_emission_factor, else a supplier factor given
    as emission_factor (it was the location value or silently ignored, BA-007 / BA-010). kg CO2e/kWh or None."""
    raw = market_ef if market_ef not in (None, "") else supplied_ef
    if raw in (None, ""):
        return None
    return parse_number(raw, "market_emission_factor", required=False, min_value=0, max_value=MAX_GRID_EF_KG_PER_KWH)


def _boiler_gas_factor(ci, key, default):
    raw = ci.get(key)
    if raw in (None, ""):
        return default
    val = parse_number(raw, key, min_value=0)
    return val * 1000.0 if str(ci.get("ef_unit") or "").lower().strip() in ("t/mmbtu", "tonne/mmbtu", "tonnes/mmbtu",
                                                                               "mt/mmbtu") else val


def steam_emissions(data):
    """CO2 / CH4 / N2O (tonnes), CO2e, delivered heat and factors of an indirect steam / heat entry."""
    amount = float(data.get("amount") or data.get("heat_mmbtu") or 0)
    unit = (data.get("unit") or "mmbtu").lower().replace(" ", "")
    ci = data.get("calc_inputs", {}).get("indirect_steam", {})
    raw_be = next(
        (
            v
            for v in (
                data.get("boiler_efficiency"),
                data.get("boiler_eff"),
                ci.get("boiler_eff"),
                ci.get("boiler_efficiency"),
            )
            if v not in (None, "")
        ),
        DEFAULT_BOILER_EFFICIENCY,
    )
    boiler_eff = float(str(raw_be).replace("%", "").strip())
    if boiler_eff > 1.0 or "%" in str(raw_be):
        # 85 is 85 %, as in the file upload (no boiler runs at 1 %); it was used as 85 x, so the
        # manual form booked 1/100 of the emissions
        boiler_eff /= 100.0
    if not 0 < boiler_eff <= 1.0:
        raise ValidationError(f"Boiler efficiency must be above 0 and at most 100 % (got {raw_be})", "boiler_eff")
    raw_tl = next(
        (
            v
            for v in (
                data.get("transmission_loss"),
                data.get("trans_loss"),
                ci.get("trans_loss"),
                ci.get("transmission_loss"),
            )
            if v not in (None, "")
        ),
        DEFAULT_TRANSMISSION_LOSS,
    )
    tl_str = str(raw_tl).strip()
    trans_loss = float(tl_str.replace("%", "").strip() or 0.0)
    if "%" in tl_str:
        trans_loss /= 100.0
    if not 0 <= trans_loss < 1.0:
        raise ValidationError(f"Transmission loss is a fraction from 0 to below 1 (got {trans_loss}; 5 % is 0.05)",
                              "trans_loss")
    ef_co2 = float(ci.get("ef_co2", _DEFAULT_BOILER_EF_KG_PER_MMBTU))
    ef_u = str(ci.get("ef_unit") or ci.get("factor_unit") or "").lower().strip()
    # the unit says t per MMBtu; the size of the number does not (a value under 0.1 was read as t/MMBtu on create and
    # one under 1 on edit: audit 2026-11 F-S23-10). Without a unit a value under 1 kg CO2/MMBtu is refused.
    if ef_u in ("t/mmbtu", "tonne/mmbtu", "tonnes/mmbtu", "mt/mmbtu"):
        ef_co2 = ef_co2 * 1000.0
    elif not ef_u and 0 < ef_co2 < 1.0:
        raise ValidationError(f"Boiler factor {ef_co2:g}: give its unit (kg/MMBtu or t/MMBtu); a boiler emits about "
                              "53 to 100 kg CO2/MMBtu", "ef_unit")

    try:
        energy_mmbtu = heat_to_mmbtu(amount, unit, ci.get("steam_enthalpy"), ci.get("steam_enthalpy_btu_lb"))
    except ValueError as exc:
        raise ValidationError(str(exc), "unit") from None

    net_eff = boiler_eff - trans_loss  # API Compendium Exhibit 8.3: 0.92 - 0.10 (it was 0.92 x (1 - 0.10))
    if net_eff <= 0:
        raise ValidationError(
            f"Net efficiency must be greater than 0 (got {net_eff:.4f}). "
            f"Check boiler efficiency ({boiler_eff}) and transmission loss ({trans_loss}).", "trans_loss"
        )
    fuel_mmbtu = energy_mmbtu / net_eff
    # boiler CH4 / N2O: entered (ef_ch4 / ef_n2o, kg per MMBtu of fuel) or the Exhibit 8.3 natural-gas boiler
    ef_ch4 = _boiler_gas_factor(ci, "ef_ch4", _DEFAULT_BOILER_CH4_KG_PER_MMBTU)
    ef_n2o = _boiler_gas_factor(ci, "ef_n2o", _DEFAULT_BOILER_N2O_KG_PER_MMBTU)
    from calculations.constants import get_active_gwp
    gwp = get_active_gwp()
    co2_t = fuel_mmbtu * ef_co2 / 1000.0
    ch4_t = fuel_mmbtu * ef_ch4 / 1000.0
    n2o_t = fuel_mmbtu * ef_n2o / 1000.0
    return {"co2": co2_t, "ch4": ch4_t, "n2o": n2o_t,
            "co2e": co2_t + ch4_t * float(gwp["CH4"]) + n2o_t * float(gwp["N2O"]),
            "energy_mmbtu": energy_mmbtu, "fuel_mmbtu": fuel_mmbtu, "ef_co2": ef_co2, "ef_ch4": ef_ch4, "ef_n2o": ef_n2o}


def apply_electricity_edit(emission, data):
    """(data, changed) of an edited electricity record: the location factor of its grid (the facility's country
    grid for an unknown region, refused without one), and a supplier factor sent as emission_factor turned into
    the market-based factor (it was ignored on a known grid and was the location value on an unknown one)."""
    known = grid_entry(emission.grid_region)[1] is not None
    try:
        emission.emission_factor, _ = resolve_electricity_factor(emission.grid_region, emission.facility_id,
                                                                 emission.year)
    except ValidationError:
        db.session.rollback()
        raise
    if "emission_factor" in data and "market_emission_factor" not in data and data["emission_factor"] not in (None, ""):
        data = {**data, "market_emission_factor": data["emission_factor"]}
    return data, not known


def scale_steam_gases(emission, old_co2e, same_factor):
    """Keep a recalculated steam record's gas masses with its CO2e: scaled when the boiler factors are unchanged,
    cleared (CO2e reported as CO2) otherwise."""
    if emission.co2_emissions is not None and old_co2e and float(old_co2e) > 0 and same_factor:
        k = float(emission.co2e) / float(old_co2e)
        emission.co2_emissions *= k
        emission.ch4_emissions = (emission.ch4_emissions or 0.0) * k
        emission.n2o_emissions = (emission.n2o_emissions or 0.0) * k
    else:
        emission.co2_emissions = emission.ch4_emissions = emission.n2o_emissions = None


BTU_PER_TON_HOUR = 12000.0
BTU_PER_KWH = 3412.142


def cooling_factor_from_cop(cop, grid_region, facility_id=None, year=None):
    """kg CO2e per ton-hour of cooling made by an electric chiller (API Compendium 2021 Equation 8-2: electricity =
    cooling x 12,000 Btu/ton-hr / COP / 3,412 Btu/kWh, times the grid factor). Cooling could only be entered with a
    factor per ton-hour (audit 2026-11 F-S23-12). Returns (factor, kWh per ton-hour, resolved grid)."""
    try:
        c = float(cop)
    except (TypeError, ValueError):
        raise ValidationError("The chiller's coefficient of performance (COP) must be a number", "cooling_cop") from None
    if not c > 0:
        raise ValidationError("The chiller's coefficient of performance (COP) must be greater than 0", "cooling_cop")
    grid_ef, grid = resolve_electricity_factor(grid_region, facility_id, year)
    kwh_per_ton_hour = BTU_PER_TON_HOUR / c / BTU_PER_KWH
    return kwh_per_ton_hour * grid_ef, kwh_per_ton_hour, grid


def cooling_factor(data):
    """kg CO2e per ton-hour of a cooling record: the entered factor, else Equation 8-2 from the chiller COP."""
    raw_ef = data.get("emission_factor") if data.get("emission_factor") not in (None, "") else data.get("ef")
    if raw_ef in (None, "") and data.get("cooling_cop") not in (None, ""):
        return cooling_factor_from_cop(data.get("cooling_cop"), data.get("grid_region"), data.get("facility_id"),
                                       data.get("year"))[0]
    return parse_number(raw_ef, "emission_factor", min_value=0)
