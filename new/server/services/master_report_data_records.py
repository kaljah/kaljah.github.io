"""Master report data: the yearly Scope 1 / Scope 2 / production / flaring aggregates and gas properties
that the other master_report_data_* modules build on (split from master_report_data.py)."""

from typing import Any, Dict, List, Optional
from models import Emission, Facility, FlaringDetail, ProductionData, Scope2Emission
from calculations.units import VOLUME_UNITS_TO_M3
from services.regional_profiles import get_regional_profile
from utils import tenant_matches


# API Compendium Section 4 stoichiometric combustion ratios (t pollutant / t CO2e)
DEFAULT_STOICHIOMETRIC_NOX_RATIO = 0.0018


DEFAULT_STOICHIOMETRIC_CO_RATIO = 0.0035


DEFAULT_STOICHIOMETRIC_SO2_RATIO = 0.0003


DEFAULT_STOICHIOMETRIC_VOC_RATIO = 0.0008


DEFAULT_STOICHIOMETRIC_PM_RATIO = 0.0002


# Standard fuel gas flaring emission factor (t CO2e / m3)
DEFAULT_FLARING_EF_TCO2E_PER_M3 = 0.0024


# Pure methane density at 0 C / 1 atm (kg/m3): a fallback only when no gas analysis gives the mixture density
STANDARD_NATURAL_GAS_DENSITY_KG_M3 = 0.717


DEFAULT_FLARE_DRE_PCT = 98.0


def get_facilities_for_scope(
    mode: str,
    region_key: Optional[str],
    allowed_facility_ids: Optional[List[int]] = None,
    tenant_config: Optional[Dict[str, Any]] = None,
    tenant_id: Optional[str] = None,
) -> List[Facility]:
    """Resolves target facilities strictly within the caller's tenant and regional filters."""
    query = Facility.query
    if hasattr(Facility, "is_test"):
        query = query.filter(Facility.is_test.is_(False))
    if tenant_id is not None:
        query = query.filter(tenant_matches(Facility.tenant_id, tenant_id))
    if allowed_facility_ids is not None:
        query = query.filter(Facility.id.in_(allowed_facility_ids or [-1]))

    all_facs = query.all()
    if mode == "national" or not region_key or region_key.lower() in ("all", "national", "global"):
        return all_facs

    profile = get_regional_profile(region_key, tenant_config=tenant_config)
    aliases = [a.lower() for a in profile.get("aliases", [])]
    target_key = profile.get("key", "").lower()
    target_name = profile.get("name", "").lower()
    rk_raw = (region_key or "").strip().lower()
    rk_spaced = rk_raw.replace("_", " ").replace("-", " ")

    matched = []
    for f in all_facs:
        reg_str = (f.region or "").lower()
        name_str = (f.name or "").lower()
        field_str = (f.field or "").lower()
        loc_str = (f.location or "").lower()
        code_str = (getattr(f, "code", "") or "").lower()

        is_match = (
            (target_key and (target_key in reg_str or target_key in name_str))
            or any(alias in reg_str or alias in name_str or alias in field_str for alias in aliases)
            or (target_name and (target_name in name_str or target_name in reg_str))
            or (rk_raw and (rk_raw in reg_str or rk_raw in name_str or rk_raw in field_str or rk_raw in loc_str or rk_raw in code_str))
            or (rk_spaced and (rk_spaced in reg_str or rk_spaced in name_str or rk_spaced in field_str or rk_spaced in loc_str))
        )
        if is_match:
            matched.append(f)

    return matched


def record_co2e_at_gwp(e, gwp_factors=None) -> float:
    """CO2e of a Scope 1 record on the report's GWP set: its gas masses re-weighted (BA-033: the stored CO2e was
    printed whatever GWP set the report named). A record whose CO2e is not in its gases (HFC / SF6, fire
    suppression agents) keeps the stored CO2e plus the re-weighted CH4 / N2O difference. The difference is taken
    from the GWP set the record was calculated with (its gwp_version), else the active one."""
    stored = float(getattr(e, "co2e_total", None) or getattr(e, "co2e", 0.0) or 0.0)
    if not gwp_factors:
        return stored
    from calculations.constants import GWP_STANDARDS, get_active_gwp

    ch4 = float(getattr(e, "ch4_emissions", 0.0) or 0.0)
    n2o = float(getattr(e, "n2o_emissions", 0.0) or 0.0)
    base = GWP_STANDARDS.get(str(getattr(e, "gwp_version", None) or "").upper()) or get_active_gwp()
    delta = (ch4 * (float(gwp_factors.get("CH4", base["CH4"])) - float(base["CH4"]))
             + n2o * (float(gwp_factors.get("N2O", base["N2O"])) - float(base["N2O"])))
    return stored + delta


def _aggregate_emissions_records(em_records: List[Emission], start_year: int, end_year: int,
                                 gwp_factors=None) -> Dict[int, Dict[str, float]]:
    """Aggregates preloaded Scope 1 emission rows by category and gas species per year."""
    years = range(start_year, end_year + 1)
    out: Dict[int, Dict[str, float]] = {
        y: {
            "combustion_t": 0.0,
            "flaring_t": 0.0,
            "fugitives_t": 0.0,
            "venting_t": 0.0,
            "process_t": 0.0,
            "co2_mass_t": 0.0,
            "ch4_mass_t": 0.0,
            "n2o_mass_t": 0.0,
            "co2e_direct_t": 0.0,
            "routine_flaring_m3": 0.0,
            "non_routine_flaring_m3": 0.0,
            "safety_flaring_m3": 0.0,
            "total_flaring_m3": 0.0,
            "nox_t": 0.0,
            "co_t": 0.0,
            "so2_t": 0.0,
            "voc_t": 0.0,
            "pm_t": 0.0,
        }
        for y in years
    }
    for e in em_records:
        y = e.year
        if y not in out:
            continue
        co2e = record_co2e_at_gwp(e, gwp_factors)
        co2 = float(getattr(e, "co2_emissions", 0.0) or 0.0)
        ch4 = float(getattr(e, "ch4_emissions", 0.0) or 0.0)
        n2o = float(getattr(e, "n2o_emissions", 0.0) or 0.0)

        out[y]["co2e_direct_t"] += co2e
        out[y]["co2_mass_t"] += co2
        out[y]["ch4_mass_t"] += ch4
        out[y]["n2o_mass_t"] += n2o

        cat = (getattr(e, "process_type", None) or getattr(e, "category", "") or "").lower()
        subcat = (getattr(e, "fuel_type", None) or getattr(e, "sub_category", "") or "").lower()
        stream_str = f"{cat} {subcat}"

        is_flare = "flare" in cat or "flaring" in cat
        is_vent = "vent" in cat
        is_fugitive = "fugitive" in cat or "leak" in cat or "ldar" in cat
        is_combustion = (
            "combustion" in cat or "fuel" in cat or "turbine" in cat or
            "engine" in cat or "heater" in cat or "boiler" in cat or
            (not is_flare and not is_vent and not is_fugitive)
        )

        if is_combustion:
            out[y]["combustion_t"] += co2e
        elif is_flare:
            out[y]["flaring_t"] += co2e
            qty = float(getattr(e, "quantity", None) or getattr(e, "activity_data", 0.0) or 0.0)
            u_c = (e.unit or "").lower().strip()
            if u_c in VOLUME_UNITS_TO_M3:
                m3_val = qty * VOLUME_UNITS_TO_M3[u_c]
            else:
                m3_val = co2e / DEFAULT_FLARING_EF_TCO2E_PER_M3 if co2e > 0 else 0.0
            out[y]["total_flaring_m3"] += m3_val
            if "routine" in stream_str and "non" not in stream_str:
                out[y]["routine_flaring_m3"] += m3_val
            elif "safety" in stream_str or "emergency" in stream_str:
                out[y]["safety_flaring_m3"] += m3_val
            else:
                out[y]["non_routine_flaring_m3"] += m3_val
        elif is_vent:
            out[y]["venting_t"] += co2e
        elif is_fugitive:
            out[y]["fugitives_t"] += co2e

        is_comb = "combustion" in cat or "flare" in cat or "flaring" in cat
        co_val = getattr(e, "co_emissions", None)
        out[y]["co_t"] += float(co_val if co_val is not None and co_val > 0 else ((co2e * DEFAULT_STOICHIOMETRIC_CO_RATIO) if is_comb and co2e > 0 else 0.0))
        out[y]["nox_t"] += float(getattr(e, "nox_emissions", 0.0) or ((co2e * DEFAULT_STOICHIOMETRIC_NOX_RATIO) if is_comb and co2e > 0 else 0.0))
        out[y]["so2_t"] += float(getattr(e, "so2_emissions", 0.0) or ((co2e * DEFAULT_STOICHIOMETRIC_SO2_RATIO) if is_comb and co2e > 0 else 0.0))
        out[y]["voc_t"] += float(getattr(e, "voc_emissions", 0.0) or ((co2e * DEFAULT_STOICHIOMETRIC_VOC_RATIO) if is_comb and co2e > 0 else 0.0))
        out[y]["pm_t"] += float(getattr(e, "pm_emissions", 0.0) or ((co2e * DEFAULT_STOICHIOMETRIC_PM_RATIO) if is_comb and co2e > 0 else 0.0))

    return out


def _query_emissions_by_year(facility_ids: List[int], start_year: int, end_year: int,
                             gwp_factors=None) -> Dict[int, Dict[str, float]]:
    """Aggregates Scope 1 emissions by category and gas species per year (CO2e on `gwp_factors` when given)."""
    if not facility_ids:
        return _aggregate_emissions_records([], start_year, end_year)

    em_records = Emission.query.filter(
        Emission.facility_id.in_(facility_ids),
        Emission.year >= start_year,
        Emission.year <= end_year,
        Emission.status == "Verified",
        Emission.is_test.is_(False),
    ).all()
    return _aggregate_emissions_records(em_records, start_year, end_year, gwp_factors)


def _aggregate_scope2_records(records: List[Scope2Emission], start_year: int, end_year: int) -> Dict[int, float]:
    """Aggregates preloaded Scope 2 records per year."""
    out = {y: 0.0 for y in range(start_year, end_year + 1)}
    for r in records:
        if r.year in out:
            out[r.year] += float(r.co2e or 0.0)
    return out


def _query_scope2_by_year(facility_ids: List[int], start_year: int, end_year: int) -> Dict[int, float]:
    """Aggregates Scope 2 indirect emissions (grid electricity, steam) per year."""
    if not facility_ids:
        return {y: 0.0 for y in range(start_year, end_year + 1)}

    records = Scope2Emission.query.filter(
        Scope2Emission.facility_id.in_(facility_ids),
        Scope2Emission.year >= start_year,
        Scope2Emission.year <= end_year,
        Scope2Emission.status == "Verified",
    ).all()
    return _aggregate_scope2_records(records, start_year, end_year)


def _aggregate_production_records(records: List[ProductionData], start_year: int, end_year: int) -> Dict[int, Dict[str, float]]:
    """Aggregates preloaded production volume records per year."""
    years = range(start_year, end_year + 1)
    out = {
        y: {
            "gross_gas_mmsm3": 0.0,
            "net_gas_mmsm3": 0.0,
            "crude_oil_bbl": 0.0,
            "condensate_bbl": 0.0,
            "total_liquid_bbl": 0.0,
            "total_boe": 0.0,
            "prod_flaring_mmsm3": 0.0,
        }
        for y in years
    }
    for p in records:
        y = p.year
        if y not in out:
            continue
        # one production basis with the dashboard (services.dashboard_filters): the gas unit is read (500,000
        # Mscf was taken as 0.5 MMSm3 by its size) and the BOE is the platform's 5,686 scf/BOE (it was 170
        # Sm3/BOE); BA-032
        from services.dashboard_filters import gas_volume_m3, production_boe, production_gas_m3

        gas_mmsm3 = float(getattr(p, "gross_gas_mmsm3", 0.0) or 0.0)
        if gas_mmsm3 == 0.0 and getattr(p, "gas_amount", None):
            g_m3 = gas_volume_m3(p.gas_amount, getattr(p, "gas_unit", None) or "mscf", p.year, p.month)
            gas_mmsm3 = (g_m3 or 0.0) / 1e6

        crude = float(getattr(p, "oil_amount", 0.0) or 0.0)
        cond_mmboe = float(getattr(p, "condensate_mmboe", 0.0) or 0.0)
        condensate = cond_mmboe * 1e6
        liquids = crude + condensate

        boe = float(production_boe(p) or 0.0)

        net_gas = float(production_gas_m3(p) or 0.0) / 1e6

        out[y]["gross_gas_mmsm3"] += gas_mmsm3
        out[y]["net_gas_mmsm3"] += net_gas
        out[y]["crude_oil_bbl"] += crude
        out[y]["condensate_bbl"] += condensate
        out[y]["total_liquid_bbl"] += liquids
        out[y]["total_boe"] += boe
        out[y]["prod_flaring_mmsm3"] += float(getattr(p, "flared_gas_mmsm3", None) or 0.0)

    return out


def _query_production_by_year(facility_ids: List[int], start_year: int, end_year: int) -> Dict[int, Dict[str, float]]:
    """Aggregates production volumes (gas, crude, condensate, BOE) per year."""
    if not facility_ids:
        return _aggregate_production_records([], start_year, end_year)

    records = ProductionData.query.filter(
        ProductionData.facility_id.in_(facility_ids),
        ProductionData.year >= start_year,
        ProductionData.year <= end_year,
        ProductionData.is_test.is_(False),
    ).all()
    return _aggregate_production_records(records, start_year, end_year)


def _aggregate_flaring_records(
    fd_records: List[FlaringDetail],
    start_year: int,
    end_year: int,
    em_data: Dict[int, Dict[str, float]],
    prod_data: Dict[int, Dict[str, float]],
) -> Dict[int, Dict[str, float]]:
    """Aggregates preloaded FlaringDetail rows with emission/production fallbacks per year."""
    years = range(start_year, end_year + 1)
    out = {}
    fd_by_year: Dict[int, List[FlaringDetail]] = {y: [] for y in years}
    for fd in fd_records:
        if fd.year in fd_by_year:
            fd_by_year[fd.year].append(fd)

    for y in years:
        fds = fd_by_year[y]
        if fds:
            r_m3 = sum(fd.routine_knm3 or 0.0 for fd in fds) * 1000.0
            nr_m3 = sum(fd.non_routine_knm3 or 0.0 for fd in fds) * 1000.0
            s_m3 = sum(fd.safety_knm3 or 0.0 for fd in fds) * 1000.0
            tot_m3 = sum(fd.total_knm3 or 0.0 for fd in fds) * 1000.0
            dre_weighted_num = sum(
                float(fd.measured_dre_pct) * float(fd.total_knm3 or 0.0)
                for fd in fds
                if fd.measured_dre_pct is not None and (fd.total_knm3 or 0.0) > 0
            )
            dre_weighted_den = sum(
                float(fd.total_knm3 or 0.0)
                for fd in fds
                if fd.measured_dre_pct is not None and (fd.total_knm3 or 0.0) > 0
            )
            dre_vals = [float(fd.measured_dre_pct) for fd in fds if fd.measured_dre_pct is not None]
            has_measured_dre = len(dre_vals) > 0
            if dre_weighted_den > 0:
                dre: Optional[float] = dre_weighted_num / dre_weighted_den
            elif dre_vals:
                dre = sum(dre_vals) / len(dre_vals)
            else:
                dre = None
        else:
            em = em_data.get(y, {})
            tot_m3 = em.get("total_flaring_m3", 0.0)
            if tot_m3 <= 0:
                tot_m3 = prod_data.get(y, {}).get("prod_flaring_mmsm3", 0.0) * 1_000_000.0
            r_m3 = em.get("routine_flaring_m3", 0.0)
            nr_m3 = em.get("non_routine_flaring_m3", 0.0)
            s_m3 = em.get("safety_flaring_m3", 0.0)
            if (r_m3 + nr_m3 + s_m3) <= 0 and tot_m3 > 0:
                nr_m3 = tot_m3
            has_measured_dre = False
            dre = None

        out[y] = {
            "routine_mmsm3": r_m3 / 1_000_000.0,
            "non_routine_mmsm3": nr_m3 / 1_000_000.0,
            "safety_mmsm3": s_m3 / 1_000_000.0,
            "total_flaring_mmsm3": tot_m3 / 1_000_000.0,
            "measured_dre_pct": dre,
            "has_measured_dre": has_measured_dre,
        }
    return out


def _query_flaring_breakdown(
    facility_ids: List[int],
    start_year: int,
    end_year: int,
    em_data: Dict[int, Dict[str, float]],
    prod_data: Dict[int, Dict[str, float]],
) -> Dict[int, Dict[str, float]]:
    """Queries detailed flaring streams (routine, non-routine, safety) from FlaringDetail or emissions."""
    fd_records = []
    if facility_ids:
        fd_records = FlaringDetail.query.filter(
            FlaringDetail.facility_id.in_(facility_ids),
            FlaringDetail.year >= start_year,
            FlaringDetail.year <= end_year,
            FlaringDetail.status == "Verified",
        ).all()
    fd_facs = {fd.facility_id for fd in fd_records}
    if len(facility_ids or []) <= 1 or not fd_facs:
        return _aggregate_flaring_records(fd_records, start_year, end_year, em_data, prod_data)
    # Facility by facility: FlaringDetail where a facility has it, its emission / production records otherwise.
    # The portfolio used FlaringDetail as soon as any facility had rows and dropped every other facility's
    # flaring (4.902 instead of 6.902 MMSm3, BA-055)
    out = _aggregate_flaring_records(fd_records, start_year, end_year, {}, {})
    others = [fid for fid in facility_ids if fid not in fd_facs]
    if others:
        rest = _aggregate_flaring_records([], start_year, end_year, _query_emissions_by_year(others, start_year, end_year),
                                          _query_production_by_year(others, start_year, end_year))
        for y, r in rest.items():
            o = out[y]
            for k in ("routine_mmsm3", "non_routine_mmsm3", "safety_mmsm3", "total_flaring_mmsm3"):
                o[k] = o.get(k, 0.0) + r.get(k, 0.0)
    return out


def _compute_gas_properties(comp: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Derives molar fractions, MW (kg/kmol), HHV (Btu/scf), carbon mass fraction, and density (kg/Sm3 at 15C/1atm) from GC data."""
    if not comp or not isinstance(comp, dict):
        return {
            "has_composition": False,
            "c1": 0.0, "c2": 0.0, "c3": 0.0, "c4": 0.0, "c5": 0.0,
            "c6": 0.0, "c7": 0.0, "c8": 0.0, "co2": 0.0, "n2": 0.0,
            "carbon_content": 0.0,
            "hhv_btu_scf": 0.0,
            "mw_kg_mole": 0.0,
            "density_kg_m3": STANDARD_NATURAL_GAS_DENSITY_KG_M3,
        }

    def _frac(pct_key: str, frac_key: Optional[str] = None) -> float:
        try:
            if frac_key and comp.get(frac_key) is not None:
                val = comp.get(frac_key)
                if str(val).strip() != "":
                    v = float(val)
                    return v / 100.0 if v > 1.0 else v
            if comp.get(pct_key) is not None:
                val = comp.get(pct_key)
                if str(val).strip() != "":
                    v = float(val)
                    return v / 100.0 if v > 1.0 else v
        except (ValueError, TypeError):
            pass
        return 0.0

    c1 = _frac("ch4_mol_pct", "c1")
    c2 = _frac("c2h6_mol_pct", "c2")
    c3 = _frac("c3h8_mol_pct", "c3")
    ic4 = _frac("ic4_mol_pct")
    nc4 = _frac("nc4_mol_pct")
    c4 = _frac("c4_mol_pct", "c4") or (ic4 + nc4)
    ic5 = _frac("ic5_mol_pct")
    nc5 = _frac("nc5_mol_pct")
    c5 = _frac("c5_mol_pct", "c5") or (ic5 + nc5)
    c6 = _frac("c6_plus_mol_pct", "c6")
    c7 = _frac("c7_mol_pct", "c7")
    c8 = _frac("c8_mol_pct", "c8")
    co2 = _frac("co2_mol_pct", "co2")
    n2 = _frac("n2_mol_pct", "n2")
    try:
        h2s = (float(comp.get("h2s_ppm") or 0.0) / 1_000_000.0) if comp.get("h2s_ppm") not in (None, "") else _frac("h2s_mol_pct", "h2s")
    except (ValueError, TypeError):
        h2s = _frac("h2s_mol_pct", "h2s")

    tot_mol = c1 + c2 + c3 + c4 + c5 + c6 + c7 + c8 + co2 + n2 + h2s
    if tot_mol > 0:
        norm = tot_mol
        f1, f2, f3, f4, f5, f6, f7, f8, fco2, fn2, fh2s = (
            v / norm for v in (c1, c2, c3, c4, c5, c6, c7, c8, co2, n2, h2s)
        )
        fi4 = ic4 / norm if (ic4 + nc4) > 0 else f4 * 0.5
        fn4 = nc4 / norm if (ic4 + nc4) > 0 else f4 * 0.5
        fi5 = ic5 / norm if (ic5 + nc5) > 0 else f5 * 0.5
        fn5 = nc5 / norm if (ic5 + nc5) > 0 else f5 * 0.5
        mw_calc = (
            f1 * 16.043 + f2 * 30.070 + f3 * 44.097 + f4 * 58.123
            + f5 * 72.150 + f6 * 86.177 + f7 * 100.204 + f8 * 114.231
            + fco2 * 44.009 + fn2 * 28.014 + fh2s * 34.081
        )
        hhv_calc = (
            f1 * 1010.0 + f2 * 1769.6 + f3 * 2516.1
            + fi4 * 3251.9 + fn4 * 3262.3
            + fi5 * 4000.9 + fn5 * 4008.9
            + f6 * 4755.9 + f7 * 5502.5 + f8 * 6248.9
        )
        c_atoms_mass = 12.011 * (
            f1 * 1 + f2 * 2 + f3 * 3 + f4 * 4 + f5 * 5
            + f6 * 6 + f7 * 7 + f8 * 8 + fco2 * 1
        )
        c_frac_calc = (c_atoms_mass / mw_calc) if mw_calc > 0 else 0.0
    else:
        mw_calc, hhv_calc, c_frac_calc = 0.0, 0.0, 0.0

    mw = float(comp.get("mw_kg_mole") or mw_calc or 0.0)
    hhv = float(comp.get("hhv_btu_scf") or hhv_calc or 0.0)
    c_content = float(comp.get("carbon_content") or c_frac_calc or 0.0)
    density = (mw / 23.6445) if mw > 0 else STANDARD_NATURAL_GAS_DENSITY_KG_M3

    return {
        "has_composition": tot_mol > 0,
        "c1": round(c1, 6), "c2": round(c2, 6), "c3": round(c3, 6),
        "c4": round(c4, 6), "c5": round(c5, 6), "c6": round(c6, 6),
        "c7": round(c7, 6), "c8": round(c8, 6), "co2": round(co2, 6),
        "n2": round(n2, 6),
        "carbon_content": round(c_content, 4),
        "hhv_btu_scf": round(hhv, 1),
        "mw_kg_mole": round(mw, 2),
        "density_kg_m3": round(density, 4),
    }
