"""Master report data: the per-source ledger, equipment census, gas chromatography streams and the flaring
operational split (split from master_report_data.py)."""

import logging
import json
from typing import Any, Dict, List, Optional, Tuple
from models import (
    ComponentInventory,
    CustomFactor,
    Emission,
    EmissionSource,
    Facility,
    FlaringDetail,
    FugitiveSurvey,
    Scope2Emission,
)
from services.master_report_data_records import DEFAULT_FLARING_EF_TCO2E_PER_M3, _compute_gas_properties
from extensions import db

logger = logging.getLogger("services.master_report_data")


def _map_ledger_module(stype: str, sname: str) -> str:
    s = f"{stype} {sname}".lower()
    if "purchased" in s or "grid" in s or "scope 2" in s or ("electricity" in s and "import" in s):
        return "Indirect Emissions (Scope 2)"
    if "flare" in s or "flaring" in s:
        return "Flare"
    if "leak" in s or "fugitive" in s or "ldar" in s:
        return "Equipment Leaks"
    if "vent" in s:
        return "Oil and Gas Venting"
    if "tank" in s:
        return "Storage Tank"
    if "mobile" in s or "transport" in s or ("diesel" in s and ("road" in s or "hd" in s or "ld" in s)) or "gasoline" in s or "aviation" in s:
        return "Mobile and Transportation"
    if "combust" in s or "heater" in s or "turbine" in s or "generator" in s or "ice" in s or "engine" in s or "solar" in s or "gen " in s:
        return "Stationary Combustion"
    if "waste" in s or "stp" in s or "fire" in s or "suppressant" in s or "misc" in s:
        return "Miscellaneous"
    return "Stationary Combustion"


def _load_ledger_records(fac_ids: List[int], target_year: int):
    """Registered sources, verified Scope 1 records (by facility, equipment and process) and Scope 2 records."""
    srcs_by_fac: Dict[int, List[EmissionSource]] = {}
    ems_by_fac: Dict[int, List[Emission]] = {}
    em_by_equip: Dict[int, Dict[Any, List[Emission]]] = {}
    em_by_proc: Dict[int, Dict[Any, List[Emission]]] = {}
    s2_by_fac: Dict[int, List[Scope2Emission]] = {}
    if fac_ids:
        for s in EmissionSource.query.filter(
            EmissionSource.facility_id.in_(fac_ids),
            EmissionSource.is_test.is_(False),
        ).order_by(
            EmissionSource.type, EmissionSource.name
        ).all():
            srcs_by_fac.setdefault(s.facility_id, []).append(s)

        for em in Emission.query.filter(
            Emission.facility_id.in_(fac_ids),
            Emission.year == target_year,
            Emission.status == "Verified",
            Emission.is_test.is_(False),
        ).order_by(Emission.id).all():
            ems_by_fac.setdefault(em.facility_id, []).append(em)
            if em.equipment_id:
                em_by_equip.setdefault(em.facility_id, {}).setdefault(em.equipment_id, []).append(em)
            if em.process_type:
                em_by_proc.setdefault(em.facility_id, {}).setdefault(em.process_type, []).append(em)

        for s2 in Scope2Emission.query.filter(
            Scope2Emission.facility_id.in_(fac_ids),
            Scope2Emission.year == target_year,
            Scope2Emission.status == "Verified",
        ).all():
            s2_by_fac.setdefault(s2.facility_id, []).append(s2)
    return srcs_by_fac, ems_by_fac, em_by_equip, em_by_proc, s2_by_fac


def _ledger_em_co2e(em: Emission, gwp_factors: Dict[str, float]) -> float:
    from services.master_report_data_records import record_co2e_at_gwp

    return record_co2e_at_gwp(em, gwp_factors)


def _ledger_row(fac: Facility, source_name, equipment_id, module: str, ems: List[Emission],
                gwp_factors: Dict[str, float]) -> Dict[str, Any]:
    """One ledger line summing the records attributed to a source."""
    units = {str(em.unit) for em in ems if em.unit}
    return {
        "facility_id": fac.id,
        "facility_name": fac.name,
        "source_name": source_name,
        "equipment_id": equipment_id,
        "module": module,
        "scope": "Scope 2" if "Scope 2" in module else "Scope 1",
        "quantity": sum(float(em.quantity or 0.0) for em in ems),
        "unit": next(iter(units)) if len(units) == 1 else ("Mixed" if len(units) > 1 else "N/A"),
        "co2": sum(float(em.co2_emissions or 0.0) for em in ems),
        "ch4": sum(float(em.ch4_emissions or 0.0) for em in ems),
        "n2o": sum(float(em.n2o_emissions or 0.0) for em in ems),
        "co2e": sum(_ledger_em_co2e(em, gwp_factors) for em in ems),
    }


def _facility_ledger_rows(fac: Facility, records, gwp_factors: Dict[str, float]) -> List[Dict[str, Any]]:
    """Registered sources with their matched records, then unmatched records grouped by equipment, then the grid."""
    srcs_by_fac, ems_by_fac, em_by_equip, em_by_proc, s2_by_fac = records
    fac_rows = []
    fac_equip_map = em_by_equip.get(fac.id, {})
    fac_proc_map = em_by_proc.get(fac.id, {})
    matched_em_ids = set()

    for s in srcs_by_fac.get(fac.id, []):
        cand_ems: List[Emission] = []
        if s.equipment_id and s.equipment_id in fac_equip_map:
            cand_ems = [em for em in fac_equip_map[s.equipment_id] if em.id not in matched_em_ids]
        if not cand_ems and s.name and s.name in fac_equip_map:
            cand_ems = [em for em in fac_equip_map[s.name] if em.id not in matched_em_ids]
        if not cand_ems and s.type and s.type in fac_proc_map:
            cand_ems = [em for em in fac_proc_map[s.type] if em.id not in matched_em_ids]

        for em in cand_ems:
            matched_em_ids.add(em.id)
        module = _map_ledger_module(s.type or "", s.name or "")
        fac_rows.append(_ledger_row(fac, s.name, s.equipment_id or s.name, module, cand_ems, gwp_factors))

    unmapped_ems = [em for em in ems_by_fac.get(fac.id, []) if em.id not in matched_em_ids]
    unmapped_groups: Dict[Tuple[str, str], List[Emission]] = {}
    for uem in unmapped_ems:
        sname = str(uem.equipment_id or uem.process_type or f"Process {uem.id}")
        ptype = str(uem.process_type or "")
        unmapped_groups.setdefault((sname, ptype), []).append(uem)

    for (sname, ptype), uems in unmapped_groups.items():
        module = _map_ledger_module(ptype, sname)
        fac_rows.append(_ledger_row(fac, sname, uems[0].equipment_id or sname, module, uems, gwp_factors))

    s2_list = s2_by_fac.get(fac.id, [])
    if s2_list:
        tot_kwh = sum(float(s.electricity_kwh or 0.0) for s in s2_list)
        tot_co2e = sum(float(s.co2e or s.co2e_location_based or 0.0) for s in s2_list)
        fac_rows.append({
            "facility_id": fac.id,
            "facility_name": fac.name,
            "source_name": "Purchased Electricity (Grid)",
            "equipment_id": "SCOPE2-GRID",
            "module": "Indirect Emissions (Scope 2)",
            "scope": "Scope 2",
            "quantity": tot_kwh / 1000.0 if tot_kwh else 0.0,
            "unit": "MWh",
            "co2": 0.0,
            "ch4": 0.0,
            "n2o": 0.0,
            "co2e": tot_co2e,
        })
    return fac_rows


def _query_granular_source_ledger(
    fac_ids: List[int],
    target_year: int,
    gwp_factors: Dict[str, float]
) -> Dict[str, Any]:
    """
    Dynamically queries every registered physical emission source across facilities in scope.
    Completely unbounded: works for 5, 34, 68, or 250+ sources without any hardcoded limit.
    """
    facilities = Facility.query.filter(Facility.id.in_(fac_ids)).all() if fac_ids else []
    records = _load_ledger_records(fac_ids, target_year)

    ledger_by_facility = {}
    total_ledger_rows = []
    for fac in facilities:
        fac_rows = _facility_ledger_rows(fac, records, gwp_factors)
        total_ledger_rows.extend(fac_rows)
        ledger_by_facility[fac.name] = fac_rows

    # Module rollups
    module_totals = {}
    for r in total_ledger_rows:
        mod = r["module"]
        if mod not in module_totals:
            module_totals[mod] = {"co2": 0.0, "ch4": 0.0, "n2o": 0.0, "co2e": 0.0, "count": 0}
        module_totals[mod]["co2"] += r["co2"]
        module_totals[mod]["ch4"] += r["ch4"]
        module_totals[mod]["n2o"] += r["n2o"]
        module_totals[mod]["co2e"] += r["co2e"]
        module_totals[mod]["count"] += 1

    return {
        "ledger_by_facility": ledger_by_facility,
        "total_sources_count": len(total_ledger_rows),
        "total_ledger_rows": total_ledger_rows,
        "module_totals": module_totals,
        "total_co2e": sum(r["co2e"] for r in total_ledger_rows),
        "total_co2": sum(r["co2"] for r in total_ledger_rows),
        "total_ch4": sum(r["ch4"] for r in total_ledger_rows),
        "total_n2o": sum(r["n2o"] for r in total_ledger_rows),
    }


_CENSUS_STATIC_NOTES = {
    "Combustion – Heaters": "Fuel gas combustion sources",
    "Combustion – Turbines / Generators": "Fuel gas power generation & compression drivers",
    "Combustion – Diesel fired engines": "Emergency generators and utility diesel units",
    "Flares": "Smokeless high/low pressure flare networks",
    "Oil and Gas Venting Activities": "Maintenance, blowdown and non-routine events",
    "Mobile & Transportation – Aviation": "Fixed-wing/rotary logistics aircraft (if registered)",
    "Storage Tanks – Produced Water Tanks": "Separator / produced water atmospheric storage tanks",
    "Indirect – Purchased Electricity": "Scope 2 grid import power supply",
}


def _count_facility_category_sources(
    fac: Facility,
    cat_name: str,
    keywords: List[str],
    srcs: List[EmissionSource],
    comps: List[ComponentInventory],
    s2_fac_ids: set,
) -> int:
    """Counts active emission sources (or component/Scope 2 proxies) matching a census category."""
    cnt = sum(1 for s in srcs if any(kw in f"{s.name} {s.type or ''}".lower() for kw in keywords))
    if "Leaks – CPF Gas processing" in cat_name and cnt == 0:
        cnt = sum(int(c.quantity or 1) for c in comps)
    if "Electricity" in cat_name and cnt == 0 and fac.id in s2_fac_ids:
        cnt = 1
    return cnt


def _resolve_census_note(cat_name: str, row_total: int, m21_count_total: int, total_components_all: int) -> str:
    """Resolves truthful methodology note for a census category based on logged LDAR/source data."""
    if cat_name in _CENSUS_STATIC_NOTES:
        return _CENSUS_STATIC_NOTES[cat_name]
    if "Leaks" not in cat_name:
        return "Operational support systems"
    if row_total == 0 and "CPF Gas processing" not in cat_name:
        return "No production leak sources logged in this sub-category"
    if m21_count_total > 0:
        return f"EPA Method 21 LDAR ({total_components_all:,} components logged)"
    if total_components_all > 0:
        return f"Component-level LDAR inventory ({total_components_all:,} components; no Method 21 surveys)"
    return "Level 2 facility-level fugitive estimates (no component inventory logged)"


def _query_equipment_census(fac_ids: List[int]) -> List[Dict[str, Any]]:
    """
    Generates dynamic equipment count census across all facilities in scope.
    Matches Table 2 format dynamically.
    """
    facilities = Facility.query.filter(Facility.id.in_(fac_ids)).all() if fac_ids else []
    categories = [
        ("Combustion – Heaters", ["heater", "hot oil", "reboiler"]),
        ("Combustion – Turbines / Generators", ["turbine", "gen ", "generator", "solar", "igc", "rgc"]),
        ("Combustion – Diesel fired engines", ["diesel", "ice", "firewater"]),
        ("Flares", ["flare"]),
        ("Equipment Leaks – Gas production", ["leak – gas", "leak - gas", "gas production leak"]),
        ("Equipment Leaks – Oil production", ["leak – oil", "leak - oil", "oil production leak"]),
        ("Equipment Leaks – CPF Gas processing", ["leak – cpf", "leak - cpf", "cpf gas processing"]),
        ("Oil and Gas Venting Activities", ["vent"]),
        ("Mobile & Transportation – On-road vehicles", ["road", "hd diesel", "ld diesel", "gasoline"]),
        ("Mobile & Transportation – Aviation", ["aviation", "aircraft"]),
        ("Storage Tanks – Produced Water Tanks", ["tank", "water tank", "storage"]),
        ("Miscellaneous – Wastewater Treatment", ["stp", "wastewater", "aerobic"]),
        ("Miscellaneous – Fire Suppressant", ["fire suppressant", "suppressant"]),
        ("Indirect – Purchased Electricity", ["electricity", "imported", "grid"]),
    ]

    srcs_by_fac: Dict[int, List[EmissionSource]] = {}
    comps_by_fac: Dict[int, List[ComponentInventory]] = {}
    m21_count_total = 0
    s2_fac_ids: set = set()
    if fac_ids:
        for s in EmissionSource.query.filter(
            EmissionSource.facility_id.in_(fac_ids),
            EmissionSource.is_test.is_(False),
        ).all():
            srcs_by_fac.setdefault(s.facility_id, []).append(s)
        for c in ComponentInventory.query.filter(ComponentInventory.facility_id.in_(fac_ids)).all():
            comps_by_fac.setdefault(c.facility_id, []).append(c)
        m21_count_total = FugitiveSurvey.query.filter(
            FugitiveSurvey.facility_id.in_(fac_ids),
            db.func.lower(FugitiveSurvey.survey_method).like("%method 21%"),
        ).count()
        s2_fac_ids = {
            fid
            for (fid,) in db.session.query(Scope2Emission.facility_id)
            .filter(Scope2Emission.facility_id.in_(fac_ids), Scope2Emission.status == "Verified")
            .distinct()
            .all()
        }

    total_components_all = sum(int(c.quantity or 1) for clist in comps_by_fac.values() for c in clist)

    census_rows = []
    for cat_name, keywords in categories:
        counts = {}
        row_total = 0
        for fac in facilities:
            cnt = _count_facility_category_sources(
                fac,
                cat_name,
                keywords,
                srcs_by_fac.get(fac.id, []),
                comps_by_fac.get(fac.id, []),
                s2_fac_ids,
            )
            counts[fac.name] = cnt
            row_total += cnt

        census_rows.append({
            "category": cat_name,
            "counts": counts,
            "total": row_total,
            "notes": _resolve_census_note(cat_name, row_total, m21_count_total, total_components_all),
        })

    return census_rows


def _query_multistream_gas_chromatography(fac_ids: List[int]) -> List[Dict[str, Any]]:
    """
    Dynamically extracts multi-stream gas chromatography assays from CustomFactors in the DB.
    Matches Tables 6 & 13 format dynamically.
    """
    if not fac_ids:
        return []
    facilities = Facility.query.filter(Facility.id.in_(fac_ids)).all()
    fac_map = {f.id: f for f in facilities}

    cfs = CustomFactor.query.filter(
        CustomFactor.facility_id.in_(fac_ids),
        CustomFactor.gas_composition_json.isnot(None),
        CustomFactor.is_archived.is_(False),
        CustomFactor.status == "Approved",
        CustomFactor.is_test.is_(False),
    ).all()

    stream_rows = []
    for cf in cfs:
        try:
            comp = json.loads(cf.gas_composition_json) if isinstance(cf.gas_composition_json, str) else cf.gas_composition_json
        except (json.JSONDecodeError, TypeError, ValueError) as exc:
            logger.warning("Invalid gas composition JSON on CustomFactor %s: %s", getattr(cf, "id", None), exc)
            comp = {}
        if not isinstance(comp, dict) or not comp:
            continue

        props = _compute_gas_properties(comp)
        fac_name = fac_map.get(cf.facility_id).name if cf.facility_id in fac_map else "Field Stream"
        stream_type = comp.get("stream_type") or (cf.name or "Field Stream").replace("Assay", "").replace("Stream", "").strip()
        hhv_val = props["hhv_btu_scf"] or float(cf.hhv_factor or 0.0)

        stream_rows.append({
            "facility_id": cf.facility_id,
            "facility_name": fac_name,
            "stream_name": stream_type,
            "carbon_content": props["carbon_content"],
            "c1": props["c1"],
            "c2": props["c2"],
            "c3": props["c3"],
            "c4": props["c4"],
            "c5": props["c5"],
            "c6": props["c6"],
            "c7": props["c7"],
            "c8": props["c8"],
            "co2": props["co2"],
            "n2": props["n2"],
            "hhv_btu_scf": hhv_val,
            "mw_kg_mole": props["mw_kg_mole"],
        })

    return stream_rows


def _query_flaring_operational_split(
    fac_ids: List[int],
    target_year: int
) -> Dict[str, Any]:
    """
    Queries FlaringDetail to extract routine, non-routine, and safety flaring volumes and DRE.
    Matches Table E-5 / 22 flaring blocks dynamically.
    """
    facilities = Facility.query.filter(Facility.id.in_(fac_ids)).all() if fac_ids else []
    fds_by_fac: Dict[int, List[FlaringDetail]] = {}
    flare_co2e_by_fac: Dict[int, float] = {}
    if fac_ids:
        for fd in FlaringDetail.query.filter(
            FlaringDetail.facility_id.in_(fac_ids),
            FlaringDetail.year == target_year,
            FlaringDetail.status == "Verified",
        ).all():
            fds_by_fac.setdefault(fd.facility_id, []).append(fd)
        for em in Emission.query.filter(
            Emission.facility_id.in_(fac_ids),
            Emission.year == target_year,
            Emission.status == "Verified",
            Emission.is_test.is_(False),
        ).all():
            pt = (em.process_type or "").lower()
            if "flare" in pt or "flaring" in pt:
                flare_co2e_by_fac[em.facility_id] = flare_co2e_by_fac.get(em.facility_id, 0.0) + float(em.co2e_total or 0.0)

    fac_split = {}
    tot_routine = 0.0
    tot_non_routine = 0.0
    tot_safety = 0.0
    tot_flaring = 0.0
    tot_flare_ghg_mmt = 0.0
    dre_weighted_num = 0.0
    dre_weighted_den = 0.0
    dre_all_measured: List[float] = []

    for fac in facilities:
        fds = fds_by_fac.get(fac.id, [])
        if not fds and fac.id not in flare_co2e_by_fac:
            continue
        r_knm3 = sum(f.routine_knm3 or 0.0 for f in fds)
        nr_knm3 = sum(f.non_routine_knm3 or 0.0 for f in fds)
        sf_knm3 = sum(f.safety_knm3 or 0.0 for f in fds)
        t_knm3 = sum(f.total_knm3 or 0.0 for f in fds)
        dre_list = [float(f.measured_dre_pct) for f in fds if f.measured_dre_pct is not None]
        avg_dre: Optional[float] = (sum(dre_list) / len(dre_list)) if dre_list else None

        r_mmsm3 = r_knm3 / 1000.0
        nr_mmsm3 = nr_knm3 / 1000.0
        sf_mmsm3 = sf_knm3 / 1000.0
        t_mmsm3 = t_knm3 / 1000.0 if t_knm3 > 0 else (r_mmsm3 + nr_mmsm3 + sf_mmsm3)

        if fac.id in flare_co2e_by_fac:
            fl_ghg_mmt = flare_co2e_by_fac[fac.id] / 1_000_000.0
        else:
            fl_ghg_mmt = (t_mmsm3 * 1e6 * DEFAULT_FLARING_EF_TCO2E_PER_M3) / 1e6 if t_mmsm3 > 0 else 0.0

        if avg_dre is not None:
            dre_all_measured.append(avg_dre)
            if t_mmsm3 > 0:
                dre_weighted_num += avg_dre * t_mmsm3
                dre_weighted_den += t_mmsm3

        fac_split[fac.name] = {
            "routine_mmsm3": r_mmsm3,
            "non_routine_mmsm3": nr_mmsm3,
            "safety_mmsm3": sf_mmsm3,
            "total_mmsm3": t_mmsm3,
            "measured_dre_pct": avg_dre,
            "flaring_ghg_co2e_mmt": fl_ghg_mmt,
        }
        tot_routine += r_mmsm3
        tot_non_routine += nr_mmsm3
        tot_safety += sf_mmsm3
        tot_flaring += t_mmsm3
        tot_flare_ghg_mmt += fl_ghg_mmt

    weighted_dre: Optional[float]
    if dre_weighted_den > 0:
        weighted_dre = dre_weighted_num / dre_weighted_den
    elif dre_all_measured:
        weighted_dre = sum(dre_all_measured) / len(dre_all_measured)
    else:
        weighted_dre = None

    return {
        "by_facility": fac_split,
        "total_routine_mmsm3": tot_routine,
        "total_non_routine_mmsm3": tot_non_routine,
        "total_safety_mmsm3": tot_safety,
        "total_flaring_mmsm3": tot_flaring,
        "weighted_dre_pct": weighted_dre,
        "total_flaring_ghg_co2e_mmt": tot_flare_ghg_mmt,
    }
