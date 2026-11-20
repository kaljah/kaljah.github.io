"""Master report data: uncertainty, per-facility, Scope 3, OGMP, CBAM / MACC and base-year recalculation
breakdowns (split from master_report_data.py)."""

import logging
import math
import re
from typing import Any, Dict, List, Optional
from models import (
    BaseYearRecalculation,
    CbamProductExport,
    ComponentInventory,
    Emission,
    Facility,
    FlaringDetail,
    MitigationProject,
    OgmpSurvey,
    ProductionData,
    Scope2Emission,
    Scope3Emission,
    User,
)
from services.master_report_data_records import (
    _aggregate_emissions_records,
    _aggregate_flaring_records,
    _aggregate_production_records,
    _aggregate_scope2_records,
)
from extensions import db
from utils import tenant_matches

logger = logging.getLogger("services.master_report_data")


def _normalize_uncertainty_category(raw_process_type: Optional[str]) -> str:
    """Maps raw Scope 1 process types into consolidated IPCC uncertainty categories."""
    raw_pt = (raw_process_type or "combustion").lower()
    if any(tok in raw_pt for tok in ("fuel", "combustion", "turbine", "engine")):
        return "Stationary Fuel Gas Combustion"
    if "flare" in raw_pt or "flaring" in raw_pt:
        return "Operational Flaring (Routine & Safety)"
    if any(tok in raw_pt for tok in ("leak", "fugitive", "ldar")):
        return "Fugitive LDAR Component Leaks"
    if "vent" in raw_pt:
        return "Process Venting & Tank Storage"
    return (raw_process_type or "combustion").replace("_", " ").title()


def _aggregate_db_uncertainty_fallback(facility_ids: List[int], end_year: int) -> Optional[Dict[str, Any]]:
    """Computes category and tier uncertainty directly from Verified DB emissions when primary service has no data."""
    from services.inventory_uncertainty import default_rel_1sigma
    from calculations.uncertainty import resolve_tier

    records = Emission.query.filter(
        Emission.year == end_year,
        Emission.facility_id.in_(facility_ids),
        Emission.status == "Verified",
        Emission.is_test.is_(False),
    ).all()
    s2_records = Scope2Emission.query.filter(
        Scope2Emission.year == end_year,
        Scope2Emission.facility_id.in_(facility_ids),
        Scope2Emission.status == "Verified",
    ).all()
    if not records and not s2_records:
        return None

    cat_map: Dict[str, Dict[str, Any]] = {}
    total_e = 0.0
    tier_counts = {"Tier 1": 0.0, "Tier 2": 0.0, "Tier 3": 0.0}

    for r in records:
        co2e = float(getattr(r, "co2e_total", None) or getattr(r, "co2e", 0.0) or 0.0)
        if co2e <= 0:
            continue
        raw_pt = (r.process_type or "combustion").lower()
        p_type = _normalize_uncertainty_category(r.process_type)
        u_1s = default_rel_1sigma(1, r.process_type, getattr(r, "calc_method", ""), getattr(r, "factor_source", ""))
        is_tier3 = (
            ("flare" in raw_pt or "flaring" in raw_pt)
            or getattr(r, "tier", None) == 3
            or str(getattr(r, "calc_method", "")).lower() in ("cems", "continuous", "visr")
        )
        t_num = 3 if is_tier3 else (resolve_tier(getattr(r, "factor_source", "")) or 2)
        t_key = f"Tier {t_num}"
        tier_counts[t_key] = tier_counts.get(t_key, 0.0) + co2e

        bucket = cat_map.setdefault(p_type, {"total_emissions": 0.0, "var": 0.0, "u_1s": u_1s})
        bucket["total_emissions"] += co2e
        bucket["var"] += (co2e * u_1s) ** 2
        total_e += co2e

    for s2 in s2_records:
        s2_co2e = float(s2.co2e or 0.0)
        if s2_co2e <= 0:
            continue
        u_1s = default_rel_1sigma(2)
        bucket = cat_map.setdefault("Purchased Electricity (Scope 2)", {"total_emissions": 0.0, "var": 0.0, "u_1s": u_1s})
        bucket["total_emissions"] += s2_co2e
        bucket["var"] += (s2_co2e * u_1s) ** 2
        total_e += s2_co2e

    if total_e <= 0:
        return None

    categories = []
    for p_type, cdata in cat_map.items():
        c_tot = cdata["total_emissions"]
        c_u1 = math.sqrt(cdata["var"]) / c_tot if c_tot > 0 else 0.05
        c_u95 = c_u1 * 2.0
        categories.append({
            "category": p_type,
            "total_emissions": round(c_tot, 1),
            "uncertainty_pct": f"±{c_u95 * 100:.1f}%",
            "uncertainty_1sigma": round(c_u1, 4),
            "level": "low" if c_u95 <= 0.10 else ("medium" if c_u95 <= 0.30 else "high"),
        })
    categories.sort(key=lambda x: x["total_emissions"], reverse=True)
    overall_var = sum(c["var"] for c in cat_map.values())
    overall_u95 = (math.sqrt(overall_var) / total_e) * 2.0
    return {
        "year": end_year,
        "inventory_uncertainty_pct": f"±{overall_u95 * 100:.2f}%",
        "tier_breakdown": {k: round(v / total_e * 100.0, 1) for k, v in tier_counts.items()},
        "confidence_level_pct": 95,
        "coverage_factor": 2.0,
        "categories": categories,
        "has_data": True,
    }


def _query_uncertainty_assessment(
    facility_ids: List[int],
    end_year: int,
    allowed_is_restricted: bool = False,
) -> Dict[str, Any]:
    """Queries inventory uncertainty and Monte Carlo metrics calculated directly from database records."""
    empty_state = {
        "year": end_year,
        "inventory_uncertainty_pct": "N/A",
        "tier_breakdown": {"Tier 1": 0.0, "Tier 2": 0.0, "Tier 3": 0.0},
        "confidence_level_pct": 95,
        "coverage_factor": 2.0,
        "categories": [],
        "has_data": False,
    }
    if not facility_ids:
        return empty_state
    try:
        from services.inventory_uncertainty import inventory_uncertainty
        u_res = inventory_uncertainty(
            year=end_year,
            allowed_fids=facility_ids,
            scope="all",
            statuses=("Verified",),
        )
        if u_res and u_res.get("has_data") and u_res.get("categories"):
            return u_res
    except Exception as exc:
        logger.warning("Primary uncertainty query failed for year %s: %s", end_year, exc, exc_info=True)

    try:
        fallback_res = _aggregate_db_uncertainty_fallback(facility_ids, end_year)
        if fallback_res is not None:
            return fallback_res
    except Exception as exc:
        logger.warning("Fallback uncertainty calculation failed for year %s: %s", end_year, exc, exc_info=True)

    return empty_state


def _query_facility_breakdowns(
    facilities: List[Facility],
    start_year: int,
    end_year: int,
    gwp_factors=None,
) -> List[Dict[str, Any]]:
    """Computes granular multi-year operational and emissions ledger for each facility."""
    if not facilities:
        return []

    fac_ids = [f.id for f in facilities]
    em_by_fac: Dict[int, List[Emission]] = {}
    for e in Emission.query.filter(
        Emission.facility_id.in_(fac_ids),
        Emission.year >= start_year,
        Emission.year <= end_year,
        Emission.status == "Verified",
        Emission.is_test.is_(False),
    ).all():
        em_by_fac.setdefault(e.facility_id, []).append(e)

    s2_by_fac: Dict[int, List[Scope2Emission]] = {}
    for r in Scope2Emission.query.filter(
        Scope2Emission.facility_id.in_(fac_ids),
        Scope2Emission.year >= start_year,
        Scope2Emission.year <= end_year,
        Scope2Emission.status == "Verified",
    ).all():
        s2_by_fac.setdefault(r.facility_id, []).append(r)

    prod_by_fac: Dict[int, List[ProductionData]] = {}
    for p in ProductionData.query.filter(
        ProductionData.facility_id.in_(fac_ids),
        ProductionData.year >= start_year,
        ProductionData.year <= end_year,
        ProductionData.is_test.is_(False),
    ).all():
        prod_by_fac.setdefault(p.facility_id, []).append(p)

    fd_by_fac: Dict[int, List[FlaringDetail]] = {}
    for fd in FlaringDetail.query.filter(
        FlaringDetail.facility_id.in_(fac_ids),
        FlaringDetail.year >= start_year,
        FlaringDetail.year <= end_year,
        FlaringDetail.status == "Verified",
    ).all():
        fd_by_fac.setdefault(fd.facility_id, []).append(fd)

    out = []
    years = list(range(start_year, end_year + 1))
    for f in facilities:
        f_id = f.id
        f_em = _aggregate_emissions_records(em_by_fac.get(f_id, []), start_year, end_year, gwp_factors)
        f_s2 = _aggregate_scope2_records(s2_by_fac.get(f_id, []), start_year, end_year)
        f_prod = _aggregate_production_records(prod_by_fac.get(f_id, []), start_year, end_year)
        f_fl = _aggregate_flaring_records(fd_by_fac.get(f_id, []), start_year, end_year, f_em, f_prod)

        timeline = []
        for y in years:
            em = f_em.get(y, {})
            s2 = f_s2.get(y, 0.0)
            prod = f_prod.get(y, {})
            fl = f_fl.get(y, {})

            s1 = em.get("co2e_direct_t", 0.0)
            tot_co2e = s1 + s2
            boe = prod.get("total_boe", 0.0)
            gross_gas_m3 = prod.get("gross_gas_mmsm3", 0.0) * 1e6
            fl_mmsm3 = fl.get("total_flaring_mmsm3", 0.0)
            fl_m3 = fl_mmsm3 * 1e6

            fi = (fl_m3 / gross_gas_m3 * 100.0) if gross_gas_m3 > 0 else 0.0
            ci = (tot_co2e * 1000.0 / boe) if boe > 0 else 0.0

            timeline.append({
                "year": y,
                "gross_gas_mmsm3": prod.get("gross_gas_mmsm3", 0.0),
                "liquid_mmbbl": prod.get("total_liquid_bbl", 0.0) / 1e6,
                "total_mmboe": boe / 1e6,
                "scope1_t": s1,
                "scope2_t": s2,
                "total_ghg_t": tot_co2e,
                "flaring_mmsm3": fl_mmsm3,
                "routine_mmsm3": fl.get("routine_mmsm3", 0.0),
                "flaring_intensity_pct": fi,
                "carbon_intensity_kg_boe": ci,
                "ch4_t": em.get("ch4_mass_t", 0.0),
            })

        out.append({
            "facility_id": f_id,
            "name": f.name or f"Facility {f_id}",
            "code": getattr(f, "code", "") or f"CPF-{f_id}",
            "region": f.region or "",
            "field": f.field or "",
            "timeline": timeline,
        })
    return out


def _query_scope3_breakdown(
    facility_ids: List[int],
    start_year: int,
    end_year: int,
    allowed_is_restricted: bool = False,
) -> Dict[str, Any]:
    """
    Aggregates Scope 3 Value Chain emissions across GHG Protocol categories 1 to 15.
    Returns category breakdown, multi-year totals, and data quality metadata.
    """
    if facility_ids:
        records = Scope3Emission.query.filter(
            Scope3Emission.facility_id.in_(facility_ids),
            Scope3Emission.year >= start_year,
            Scope3Emission.year <= end_year,
            Scope3Emission.status == "Verified",
        ).all()
    else:
        records = []

    by_year: Dict[int, float] = {y: 0.0 for y in range(start_year, end_year + 1)}
    cat_map: Dict[str, Dict[str, Any]] = {}
    total_period_co2e = 0.0
    latest_year_co2e = 0.0
    tier2_co2e = 0.0

    for r in records:
        y = r.year
        val = float(r.co2e or 0.0)
        if y in by_year:
            by_year[y] += val
        total_period_co2e += val
        if y == end_year:
            latest_year_co2e += val

        dq = str(getattr(r, "data_quality", None) or "").lower()
        cm = str(getattr(r, "calculation_method", None) or "").lower()
        is_t2 = dq in ("high", "tier2", "tier 2", "measured", "primary") or "tier 2" in cm or "supplier" in cm
        if is_t2:
            tier2_co2e += val

        raw_cname = r.category or "Other Value Chain"
        cname = str(raw_cname)
        if cname not in cat_map:
            cat_map[cname] = {
                "category_name": cname,
                "sub_categories": set(),
                "activity_data": 0.0,
                "unit": str(r.unit or "tonnes"),
                "factor_unit": str(getattr(r, "factor_unit", None) or ""),
                "emission_factor": float(r.emission_factor or 0.0),
                "co2e_t": 0.0,
                "latest_co2e_t": 0.0,
                "method": str(r.calculation_method or "Spend/Activity Hybrid"),
                "tier": "Tier 2" if is_t2 else "Tier 1",
            }
        if r.sub_category:
            cat_map[cname]["sub_categories"].add(str(r.sub_category))
        cat_map[cname]["activity_data"] += float(r.activity_data or 0.0)
        cat_map[cname]["co2e_t"] += val
        if y == end_year:
            cat_map[cname]["latest_co2e_t"] += val
        if r.emission_factor:
            cat_map[cname]["emission_factor"] = float(r.emission_factor)

    cat_list = []
    for cname, cdata in cat_map.items():
        sub_str = ", ".join(sorted(list(cdata["sub_categories"]))) if cdata["sub_categories"] else "General Procurement & Lifecycle"
        share = (cdata["co2e_t"] / total_period_co2e * 100.0) if total_period_co2e > 0 else 0.0
        cat_list.append({
            "category_name": cname,
            "sub_category": sub_str,
            "activity_data": cdata["activity_data"],
            "unit": cdata["unit"],
            "factor_unit": cdata["factor_unit"],
            "emission_factor": cdata["emission_factor"],
            "co2e_t": round(cdata["co2e_t"], 1),
            "latest_co2e_t": round(cdata["latest_co2e_t"], 1),
            "share_pct": round(share, 1),
            "method": cdata["method"],
            "tier": cdata["tier"],
        })
    cat_list.sort(key=lambda x: x["co2e_t"], reverse=True)

    import re as _re

    def _cat_no(name):
        # the category number as a whole word: "category 1" also matched "Category 11" (BA-056)
        m = _re.search(r"category\s*(\d{1,2})(?!\d)", str(name or "").lower())
        return int(m.group(1)) if m else None

    upstream_t = sum(c["co2e_t"] for c in cat_list if (_cat_no(c["category_name"]) or 0) in range(1, 9))
    downstream_t = sum(c["co2e_t"] for c in cat_list if (_cat_no(c["category_name"]) or 0) in range(9, 16))
    if upstream_t == 0 and downstream_t == 0 and total_period_co2e > 0:
        upstream_t = total_period_co2e

    tier2_cov_pct = round((tier2_co2e / total_period_co2e * 100.0), 1) if total_period_co2e > 0 else 0.0
    has_data = len(records) > 0 and total_period_co2e > 0
    return {
        "categories": cat_list,
        "by_year": by_year,
        "total_period_co2e": round(total_period_co2e, 1),
        "latest_year_co2e": round(latest_year_co2e, 1),
        "upstream_t": round(upstream_t, 1),
        "downstream_t": round(downstream_t, 1),
        "upstream_pct": round(upstream_t / total_period_co2e * 100.0, 1) if total_period_co2e > 0 else 0.0,
        "downstream_pct": round(downstream_t / total_period_co2e * 100.0, 1) if total_period_co2e > 0 else 0.0,
        "tier2_coverage_pct": tier2_cov_pct,
        "has_data": has_data,
        "perimeter_note": (
            "Direct corporate Scope 3 value chain emissions accounted under ISO 14064-1:2018 Category 3–6 boundary."
            if has_data else
            "No Verified Scope 3 value chain emissions recorded in database for this reporting perimeter and period."
        ),
    }


def _query_ogmp_breakdown(
    facility_ids: List[int],
    start_year: int,
    end_year: int,
    allowed_is_restricted: bool = False,
) -> Dict[str, Any]:
    """
    Queries OGMP 2.0 Level 4/5 survey reconciliation data and LDAR component inventory.
    """
    if facility_ids:
        surveys_raw = OgmpSurvey.query.filter(
            OgmpSurvey.facility_id.in_(facility_ids),
            OgmpSurvey.year >= start_year,
            OgmpSurvey.year <= end_year,
            db.func.lower(db.func.coalesce(OgmpSurvey.status, "pending")) != "rejected",
        ).all()
        components_raw = ComponentInventory.query.filter(
            ComponentInventory.facility_id.in_(facility_ids)
        ).all()
    else:
        surveys_raw = []
        components_raw = []

    survey_list = []
    tot_td = 0.0
    tot_bu = 0.0
    var_list = []

    for s in surveys_raw:
        td = float(s.estimated_annual_tch4 or 0.0)
        bu = float(s.bottom_up_tch4 or 0.0)
        var = float(s.variance_pct) if (s.variance_pct is not None and bu > 0) else None  # missing is not 0 (F-RPT-03)
        tot_td += td
        tot_bu += bu
        if var is not None:
            var_list.append(var)
        survey_list.append({
            "id": s.id,
            "year": s.year,
            "survey_date": str(s.survey_date or str(s.year)),
            "survey_type": str(s.survey_type or "Site Survey"),
            "vendor": str(s.instrument_vendor or "Not Specified"),
            "measured_rate_kg_hr": float(s.measured_rate_kg_hr or 0.0),
            "top_down_tch4": round(td, 1),
            "bottom_up_tch4": round(bu, 1),
            "variance_pct": round(var, 2) if var is not None else None,
            "status": s.reconciliation_status or "Not recorded",
        })

    component_list = []
    for c in components_raw:
        component_list.append({
            "equipment_type": c.equipment_type or "Valves & Flanges",
            "component_type": c.component_type or "Standard Valve",
            "service_type": c.service_type or "Gas Service",
            "quantity": int(c.quantity or 1),
            "methodology": c.methodology or "Component Average",
        })

    has_surveys = len(survey_list) > 0
    has_components = len(component_list) > 0
    mean_var = (sum(var_list) / len(var_list)) if var_list else None
    # the stored reconciliation outcomes (a mean variance within +/-20 % printed "Gold Standard Level 5" for a
    # survey without a bottom-up; audit 2026-11 F-RPT-03)
    stored = [str(x["status"]).lower() for x in survey_list]
    gold_std = (any(st.startswith("reconciled") for st in stored)
                and not any("discrepancy" in st for st in stored)) if survey_list else None
    has_data = has_surveys or has_components

    return {
        "surveys": survey_list,
        "components": component_list,
        "total_top_down_tch4": round(tot_td, 1),
        "total_bottom_up_tch4": round(tot_bu, 1),
        "mean_variance_pct": round(mean_var, 2) if mean_var is not None else None,
        "gold_standard_compliant": gold_std,
        "total_components_monitored": sum(c["quantity"] for c in component_list),
        "has_surveys": has_surveys,
        "has_components": has_components,
        "has_data": has_data,
        "perimeter_note": (
            "OGMP 2.0 Level 4/5 top-down reconciliation and LDAR component ledger sourced from database."
            if has_surveys else
            "No OGMP 2.0 Level 4/5 top-down measurement campaigns recorded in database for this perimeter and reporting cycle."
        ),
    }


def _query_cbam_and_macc_breakdown(
    facility_ids: List[int],
    start_year: int,
    end_year: int,
    allowed_is_restricted: bool = False,
) -> Dict[str, Any]:
    """
    Queries EU CBAM Regulation (EU) 2023/956 export emissions and MACC abatement economics.
    """
    if facility_ids:
        exports_raw = CbamProductExport.query.filter(
            CbamProductExport.facility_id.in_(facility_ids),
            CbamProductExport.year >= start_year,
            CbamProductExport.year <= end_year,
        ).all()
    else:
        exports_raw = []

    prod_map: Dict[str, Dict[str, Any]] = {}
    total_export_tonnes = 0.0
    total_embedded_co2e = 0.0

    for r in exports_raw:
        pname_clean = str(r.product_name or "Export Hydrocarbon").strip() or "Export Crude Hydrocarbon"
        cn = str(r.cn_code or "2709 00")
        qty = float(r.quantity_tonnes or 0.0)
        see_dir = float(r.specific_embedded_direct or 0.0)
        see_indir = float(r.specific_embedded_indirect or 0.0)
        dest = str(r.export_destination or "EU")
        total_see = see_dir + see_indir
        row_ghg = qty * total_see

        key = f"{pname_clean}::{cn}"
        if key not in prod_map:
            prod_map[key] = {
                "product_name": pname_clean,
                "cn_code": cn,
                "quantity_tonnes": 0.0,
                "weighted_see_dir": 0.0,
                "weighted_see_indir": 0.0,
                "total_embedded_ghg": 0.0,
                "destinations": set(),
            }
        prod_map[key]["quantity_tonnes"] += qty
        prod_map[key]["weighted_see_dir"] += see_dir * qty
        prod_map[key]["weighted_see_indir"] += see_indir * qty
        prod_map[key]["total_embedded_ghg"] += row_ghg
        prod_map[key]["destinations"].add(dest)
        total_export_tonnes += qty
        total_embedded_co2e += row_ghg

    product_list = []
    for key, pdata in prod_map.items():
        q = pdata["quantity_tonnes"]
        avg_dir = (pdata["weighted_see_dir"] / q) if q > 0 else 0.0
        avg_indir = (pdata["weighted_see_indir"] / q) if q > 0 else 0.0
        dest_str = ", ".join(sorted(list(pdata["destinations"])))
        product_list.append({
            "product_name": pdata["product_name"],
            "cn_code": pdata["cn_code"],
            "quantity_tonnes": round(q, 1),
            "see_direct": round(avg_dir, 4),
            "see_indirect": round(avg_indir, 4),
            "see_total": round(avg_dir + avg_indir, 4),
            "total_embedded_ghg": round(pdata["total_embedded_ghg"], 1),
            "destinations": dest_str,
        })
    product_list.sort(key=lambda x: x["quantity_tonnes"], reverse=True)

    if facility_ids:
        mits_raw = MitigationProject.query.filter(
            MitigationProject.facility_id.in_(facility_ids),
            MitigationProject.is_test.is_(False),
            (MitigationProject.year.between(start_year, end_year)) | (MitigationProject.year.is_(None)),
        ).all()
    else:
        mits_raw = []

    macc_list = []
    total_abatement_capacity = 0.0
    for m in mits_raw:
        qty = float(m.quantity_tco2e or 0.0)
        inv = float(m.investment_amount or 0.0)
        cost_per_t = round(inv / qty, 1) if (qty > 0 and inv > 0) else None
        total_abatement_capacity += qty
        macc_list.append({
            "name": str(m.name or "Decarbonization Project"),
            "project_type": (m.project_type or "Decarbonization").upper(),
            "year": m.year or end_year,
            "annual_abatement_tco2e": round(qty, 0),
            "investment_usd": round(inv, 0) if inv > 0 else None,
            "cost_per_tonne_usd": cost_per_t,
            "status": m.status or "Active",
        })
    macc_list.sort(key=lambda x: (x["cost_per_tonne_usd"] is None, x["cost_per_tonne_usd"] or 0.0, -x["annual_abatement_tco2e"]))

    has_cbam = len(product_list) > 0
    has_macc = len(macc_list) > 0
    has_data = has_cbam or has_macc
    return {
        "products": product_list,
        "macc_projects": macc_list,
        "total_export_tonnes": round(total_export_tonnes, 1),
        "total_embedded_co2e": round(total_embedded_co2e, 1),
        "total_abatement_capacity": round(total_abatement_capacity, 0),
        "has_cbam_data": has_cbam,
        "has_macc_data": has_macc,
        "has_data": has_data,
        "perimeter_note": (
            "EU Carbon Border Adjustment Mechanism (Regulation (EU) 2023/956) export ledger and MACC economics sourced from database."
            if has_cbam else
            "No EU CBAM covered product exports recorded in database for this perimeter and reporting cycle."
        ),
    }


def _query_base_year_recalculations(
    start_year: int,
    end_year: int,
    tenant_id: str = "default",
) -> List[Dict[str, Any]]:
    """
    Queries formal ISO 14064-1:2018 Clause 6.4.1 base year recalculations audit trail.
    """
    raw_by = BaseYearRecalculation.query.filter(
        tenant_matches(BaseYearRecalculation.tenant_id, tenant_id),
        BaseYearRecalculation.year.between(1990, 2035),
        BaseYearRecalculation.previous_emissions.isnot(None),
        BaseYearRecalculation.adjusted_emissions.isnot(None),
    ).order_by(BaseYearRecalculation.year.desc(), BaseYearRecalculation.id.desc()).all()

    clean_by = []
    seen = set()
    for r in raw_by:
        reason = (r.reason or "").strip()
        r_lower = reason.lower()
        if re.search(r"\b(bypass|negative|test)\b", r_lower):
            continue
        prev = float(r.previous_emissions or 0.0)
        adj = float(r.adjusted_emissions or 0.0)
        if prev <= 0 or adj <= 0:
            continue
        key = (r.year, round(prev, 0), round(adj, 0))
        if key in seen:
            continue
        seen.add(key)
        delta_pct = ((adj - prev) / prev * 100.0) if prev > 0 else 0.0
        date_str = r.recalc_date.strftime("%Y-%m-%d") if r.recalc_date else "2024-10-06"
        approver_display: Optional[str] = None
        if r.approved_by is not None:
            if isinstance(r.approved_by, int):
                u_app = db.session.get(User, r.approved_by)
                approver_display = u_app.fullName if u_app else f"User #{r.approved_by}"
            elif str(r.approved_by).strip().isdigit():
                u_app = db.session.get(User, int(str(r.approved_by).strip()))
                approver_display = u_app.fullName if u_app else f"User #{r.approved_by}"
            else:
                approver_display = str(r.approved_by).strip() or None

        clean_by.append({
            "year": r.year,
            "date": date_str,
            "reason": str(reason),
            "previous_emissions_t": round(prev, 1),
            "adjusted_emissions_t": round(adj, 1),
            "delta_pct": round(delta_pct, 2),
            "approved_by": approver_display,
            "scope_boundary": "Corporate Group",
        })

    return clean_by
