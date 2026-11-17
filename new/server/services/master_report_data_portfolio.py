"""Master report data: JV equity shares, gas composition, the yearly timeline, the 2030 target projection and
mitigation projects (split from master_report_data.py)."""

import logging
from typing import Any, Dict, List, Optional, Tuple
from models import CustomFactor, Emission, FacilityEquityShare, MitigationProject, Scope2Emission
from services.master_report_data_records import _compute_gas_properties
from extensions import db
from services.tenant_config import get_tenant_config
from utils import normalize_tenant_id, tenant_matches

logger = logging.getLogger("services.master_report_data")


def _normalize_facility_jv_shares(
    shares: List[Any],
    facility_ids: List[int],
    tid: str,
) -> Tuple[Dict[int, Dict[int, float]], Dict[int, Any]]:
    """Normalizes per-facility JV partner shares to 100% and fills unallocated operator shares."""
    fac_share_map: Dict[int, Dict[int, float]] = {}
    partner_meta: Dict[int, Any] = {}
    for s in shares:
        p = s.partner
        if not p or normalize_tenant_id(getattr(p, "tenant_id", None)) != tid:
            continue
        partner_meta[p.id] = p
        fac_share_map.setdefault(s.facility_id, {})[p.id] = float(s.equity_share_pct or 0.0)

    for pshares in fac_share_map.values():
        tot = sum(pshares.values())
        if tot > 0 and abs(tot - 100.0) > 0.01:
            for pid in pshares:
                pshares[pid] = (pshares[pid] / tot) * 100.0

    operator_partner = next((p for p in partner_meta.values() if getattr(p, "is_operator", False)), None)
    if not operator_partner:
        try:
            from models import JvPartner
            op_db = (
                JvPartner.query.filter_by(is_operator=True)
                .filter(tenant_matches(JvPartner.tenant_id, tid))
                .first()
            )
            if op_db:
                operator_partner = op_db
                partner_meta[op_db.id] = op_db
        except Exception as exc:
            logger.warning("Failed querying operator JV partner for tenant %s: %s", tid, exc, exc_info=True)

    if operator_partner:
        for fid in facility_ids:
            pshares = fac_share_map.setdefault(fid, {})
            tot = sum(pshares.values())
            if tot < 99.99:
                pshares[operator_partner.id] = pshares.get(operator_partner.id, 0.0) + (100.0 - tot)
    return fac_share_map, partner_meta


def _accumulate_jv_partner_results(
    facility_ids: List[int],
    years: List[int],
    fac_share_map: Dict[int, Dict[int, float]],
    partner_meta: Dict[int, Any],
    gwp_factors=None,
) -> Dict[int, Dict[str, Any]]:
    """Attributes Verified Scope 1 and Scope 2 emissions per facility and year to JV partners."""
    from services.master_report_data_records import record_co2e_at_gwp

    fac_em: Dict[int, Dict[int, Dict[str, float]]] = {
        fid: {y: {"s1": 0.0, "s2": 0.0, "ch4": 0.0} for y in years}
        for fid in facility_ids
    }
    for e in Emission.query.filter(
        Emission.facility_id.in_(facility_ids),
        Emission.year.in_(years),
        Emission.status == "Verified",
        Emission.is_test.is_(False),
    ).all():
        if e.facility_id in fac_em and e.year in fac_em[e.facility_id]:
            co2e = record_co2e_at_gwp(e, gwp_factors)  # the report's GWP set (BA-033)
            fac_em[e.facility_id][e.year]["s1"] += co2e
            fac_em[e.facility_id][e.year]["ch4"] += float(getattr(e, "ch4_emissions", 0.0) or 0.0)

    for s2 in Scope2Emission.query.filter(
        Scope2Emission.facility_id.in_(facility_ids),
        Scope2Emission.year.in_(years),
        Scope2Emission.status == "Verified",
    ).all():
        if s2.facility_id in fac_em and s2.year in fac_em[s2.facility_id]:
            fac_em[s2.facility_id][s2.year]["s2"] += float(s2.co2e or 0.0)

    partner_results: Dict[int, Dict[str, Any]] = {
        pid: {
            "partner": p.name,
            "partner_name": p.name,
            "code": p.code,
            "partner_code": p.code,
            "is_operator": p.is_operator,
            "yearly_s1": {y: 0.0 for y in years},
            "yearly_s2": {y: 0.0 for y in years},
            "yearly_co2e": {y: 0.0 for y in years},
            "yearly_ch4": {y: 0.0 for y in years},
        }
        for pid, p in partner_meta.items()
    }
    for fid in facility_ids:
        pshares = fac_share_map.get(fid, {})
        for y in years:
            f_s1 = fac_em[fid][y]["s1"]
            f_s2 = fac_em[fid][y]["s2"]
            f_ch4 = fac_em[fid][y]["ch4"]
            for pid, share_pct in pshares.items():
                pr = partner_results.get(pid)
                if pr is None:
                    continue
                ratio = share_pct / 100.0
                pr["yearly_s1"][y] += f_s1 * ratio
                pr["yearly_s2"][y] += f_s2 * ratio
                pr["yearly_co2e"][y] += (f_s1 + f_s2) * ratio
                pr["yearly_ch4"][y] += f_ch4 * ratio
    return partner_results


def _query_jv_equity_breakdown(
    facility_ids: List[int],
    timeline: List[Dict[str, Any]],
    tenant_id: str = "default",
    gwp_factors=None,
) -> Dict[str, Any]:
    """Computes GHG and CH4 emissions apportioned by JV partner equity share."""
    if not timeline:
        return {"is_jv": False, "partners": [], "annual_equity_timeline": []}

    tid = normalize_tenant_id(tenant_id)
    shares = []
    if facility_ids:
        try:
            from routes.equity_routes import sync_equity_shares_for_facilities
            sync_equity_shares_for_facilities(tenant_id=tid, facility_ids=facility_ids)
        except Exception as exc:
            logger.warning("Failed syncing equity shares for facilities %s: %s", facility_ids, exc, exc_info=True)
        shares = FacilityEquityShare.query.filter(
            FacilityEquityShare.facility_id.in_(facility_ids)
        ).all()

    active_timeline = [t for t in timeline if (t.get("total_co2e_t") or 0.0) > 0]
    latest_active_t = active_timeline[-1] if active_timeline else timeline[-1]

    if shares:
        fac_share_map, partner_meta = _normalize_facility_jv_shares(shares, facility_ids, tid)
        years = [t["year"] for t in timeline]
        partner_results = _accumulate_jv_partner_results(facility_ids, years, fac_share_map, partner_meta, gwp_factors)

        total_portfolio_ghg = sum(t["total_co2e_t"] for t in timeline)
        latest_y = latest_active_t["year"]
        partners_list = []
        for pr in partner_results.values():
            tot_p_ghg = sum(pr["yearly_co2e"].values())
            tot_p_s1 = sum(pr["yearly_s1"].values())
            tot_p_s2 = sum(pr["yearly_s2"].values())
            tot_p_ch4 = sum(pr["yearly_ch4"].values())
            effective_pct = (tot_p_ghg / total_portfolio_ghg * 100.0) if total_portfolio_ghg > 0 else 0.0
            latest_y_co2e = pr["yearly_co2e"].get(latest_y, 0.0)

            partners_list.append({
                "partner": pr["partner"],
                "partner_name": pr["partner_name"],
                "code": pr["code"],
                "partner_code": pr["code"],
                "is_operator": pr["is_operator"],
                "share_pct": round(effective_pct, 1),
                "equity_share_pct": round(effective_pct, 1),
                "latest_year": latest_y,
                "latest_year_co2e": round(latest_y_co2e, 1),
                "yearly_co2e": {y: round(v, 1) for y, v in pr["yearly_co2e"].items()},
                "yearly_ch4": {y: round(v, 2) for y, v in pr["yearly_ch4"].items()},
                "equity_s1_tco2e": round(tot_p_s1, 1),
                "equity_s2_tco2e": round(tot_p_s2, 1),
                "equity_total_ghg_tco2e": round(tot_p_ghg, 1),
                "total_equity_co2e": round(tot_p_ghg, 1),
                "equity_ch4_t": round(tot_p_ch4, 2),
            })

        if partners_list and total_portfolio_ghg > 0:
            pct_sum = sum(p["equity_share_pct"] for p in partners_list)
            delta = round(100.0 - pct_sum, 1)
            if abs(delta) > 0 and abs(delta) < 1.0:
                partners_list.sort(key=lambda x: x["equity_share_pct"], reverse=True)
                partners_list[0]["equity_share_pct"] = round(partners_list[0]["equity_share_pct"] + delta, 1)
                partners_list[0]["share_pct"] = partners_list[0]["equity_share_pct"]

        partners_list.sort(key=lambda x: x["equity_share_pct"], reverse=True)

        annual_timeline = []
        for t in timeline:
            y = t["year"]
            p_em = {
                p["code"]: {
                    "total_ghg": p["yearly_co2e"].get(y, 0.0),
                    "total_ghg_tco2e": p["yearly_co2e"].get(y, 0.0),
                    "ch4": p["yearly_ch4"].get(y, 0.0),
                }
                for p in partners_list
            }
            annual_timeline.append({"year": y, "partner_emissions": p_em})

        return {
            "is_jv": True,
            "partners": partners_list,
            "annual_equity_timeline": annual_timeline,
        }

    tot_co2e_sum = sum(t["total_co2e_t"] for t in timeline)
    tot_s1_sum = sum(t["scope1_co2e_t"] for t in timeline)
    tot_s2_sum = sum(t["scope2_co2e_t"] for t in timeline)
    tot_ch4_sum = sum(t["ch4_mass_t"] for t in timeline)
    tenant_cfg = get_tenant_config(tid)
    default_op = "Demo Operator Co." if tid == "default" else tenant_cfg.get("organization_name", "Operator")
    op_name = tenant_cfg.get("legal_entity") or tenant_cfg.get("organization_name", default_op)
    op_code = tenant_cfg.get("short_code", "SH" if tid == "default" else "OP")
    single_p = {
        "partner": op_name,
        "partner_name": op_name,
        "code": op_code,
        "partner_code": op_code,
        "share_pct": 100.0,
        "equity_share_pct": 100.0,
        "is_operator": True,
        "latest_year": latest_active_t["year"],
        "latest_year_co2e": round(latest_active_t["total_co2e_t"], 1),
        "yearly_co2e": {t["year"]: t["total_co2e_t"] for t in timeline},
        "yearly_ch4": {t["year"]: t["ch4_mass_t"] for t in timeline},
        "total_equity_co2e": round(tot_co2e_sum, 1),
        "equity_s1_tco2e": round(tot_s1_sum, 1),
        "equity_s2_tco2e": round(tot_s2_sum, 1),
        "equity_total_ghg_tco2e": round(tot_co2e_sum, 1),
        "equity_ch4_t": round(tot_ch4_sum, 2),
    }
    annual_timeline = [
        {
            "year": t["year"],
            "partner_emissions": {
                op_code: {
                    "total_ghg": t["total_co2e_t"],
                    "total_ghg_tco2e": t["total_co2e_t"],
                    "ch4": t["ch4_mass_t"],
                }
            }
        }
        for t in timeline
    ]
    return {
        "is_jv": False,
        "partners": [single_p],
        "annual_equity_timeline": annual_timeline,
    }


def _resolve_dynamic_gas_composition(
    fac_ids: List[int],
    region_key: Optional[str],
    profile: Dict[str, Any],
    tenant_id: str = "default",
    allowed_is_restricted: bool = False,
    allow_regional_cf_fallback: bool = False,
) -> Tuple[Dict[str, Any], str, str]:
    """Resolves measured gas composition from CustomFactor or baseline profile."""
    if not fac_ids and allowed_is_restricted and not allow_regional_cf_fallback:
        return {}, "", "none"
    matched_cf = None
    if fac_ids:
        used_cf_ids = db.session.query(Emission.custom_factor_id).filter(
            Emission.facility_id.in_(fac_ids),
            Emission.custom_factor_id.isnot(None),
            Emission.status == "Verified",
            Emission.is_test.is_(False),
        ).distinct().all()
        for (cid,) in used_cf_ids:
            cand = db.session.get(CustomFactor, cid)
            if cand and not cand.is_archived and not getattr(cand, "is_test", False) and cand.gas_composition:
                matched_cf = cand
                break

    if not matched_cf and fac_ids:
        cfs_fac = CustomFactor.query.filter(
            CustomFactor.facility_id.in_(fac_ids),
            CustomFactor.is_archived.is_(False),
            CustomFactor.status == "Approved",
            CustomFactor.is_test.is_(False),
        ).all()
        for cand in cfs_fac:
            if cand.gas_composition:
                matched_cf = cand
                break

    if not matched_cf:
        all_cfs = CustomFactor.query.filter(
            CustomFactor.is_archived.is_(False),
            CustomFactor.status == "Approved",
            CustomFactor.is_test.is_(False),
            tenant_matches(CustomFactor.tenant_id, tenant_id),
        ).all()
        for cand in all_cfs:
            if not cand.gas_composition:
                continue
            cand_reg = (cand.region or "").strip().lower()
            cand_reg_norm = cand_reg.replace("-", "_").replace(" ", "_")
            rk_raw = (region_key or "").strip().lower()
            rk_norm = rk_raw.replace("-", "_").replace(" ", "_")
            if cand.region and region_key and (cand_reg == rk_raw or cand_reg_norm == rk_norm):
                matched_cf = cand
                break
            cname = (cand.name or "").lower()
            if region_key and (rk_raw in cname or rk_norm.replace("_", " ") in cname):
                matched_cf = cand
                break
            prof_key = profile.get("key", "").lower()
            aliases = profile.get("aliases", [])
            if (
                (prof_key and (prof_key in cname or prof_key.replace("_", " ") in cname))
                or any(a in cname for a in aliases)
            ):
                matched_cf = cand
                break

    if matched_cf and matched_cf.gas_composition:
        return matched_cf.gas_composition, matched_cf.name, "custom_factor"

    # Also inspect if any Emission record in the perimeter carries direct laboratory GC composition
    if fac_ids:
        em_with_gc = Emission.query.filter(
            Emission.facility_id.in_(fac_ids),
            Emission.gas_composition_json.isnot(None),
            Emission.status == "Verified",
            Emission.is_test.is_(False),
        ).order_by(Emission.year.desc()).first()
        if em_with_gc and em_with_gc.gas_composition:
            fac_name = em_with_gc.facility.name if em_with_gc.facility else "Facility"
            return em_with_gc.gas_composition, f"{fac_name} Stream Analysis ({em_with_gc.year})", "emission_measurement"

    # No composition introduced by the software: return empty structure and "none" source
    return {}, "", "none"


def _assemble_timeline_series(
    start_year: int,
    end_year: int,
    em_data: Dict[int, Dict[str, float]],
    s2_data: Dict[int, float],
    prod_data: Dict[int, Dict[str, float]],
    flare_detail_data: Dict[int, Dict[str, float]],
    gas_comp_data: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """Calculates multi-year annual ESG and intensity metrics."""
    years = sorted(list(range(start_year, end_year + 1)))
    gas_props = _compute_gas_properties(gas_comp_data)
    gas_density = gas_props["density_kg_m3"]
    timeline = []
    for y in years:
        em = em_data.get(y, {})
        s2 = s2_data.get(y, 0.0)
        prod = prod_data.get(y, {})
        fl_det = flare_detail_data.get(y, {})
        s1_co2e = em.get("co2e_direct_t", 0.0)
        total_co2e = s1_co2e + s2
        boe = prod.get("total_boe", 0.0)
        gross_gas_mmsm3 = prod.get("gross_gas_mmsm3", 0.0)
        net_gas_mmsm3 = prod.get("net_gas_mmsm3", 0.0)
        gross_gas_m3 = gross_gas_mmsm3 * 1_000_000.0
        flare_mmsm3 = fl_det.get("total_flaring_mmsm3", 0.0)
        flare_m3 = flare_mmsm3 * 1_000_000.0
        flaring_intensity_pct = (flare_m3 / gross_gas_m3 * 100.0) if gross_gas_m3 > 0 else 0.0
        carbon_intensity_kg_boe = (total_co2e * 1000.0 / boe) if boe > 0 else 0.0
        ch4_mass_t = em.get("ch4_mass_t", 0.0)
        if net_gas_mmsm3 > 0:
            mi_denom_m3 = net_gas_mmsm3 * 1_000_000.0
            mi_basis = "marketed_net_gas"
        elif gross_gas_m3 > 0:
            mi_denom_m3 = gross_gas_m3
            mi_basis = "gross_gas_fallback"
        else:
            mi_denom_m3 = 0.0
            mi_basis = "no_gas_production"
        gas_mass_t = (mi_denom_m3 * gas_density / 1000.0) if mi_denom_m3 > 0 else 0.0
        methane_intensity_pct = (ch4_mass_t / gas_mass_t * 100.0) if gas_mass_t > 0 else 0.0
        timeline.append({
            "year": y, "scope1_co2e_t": s1_co2e, "scope2_co2e_t": s2, "total_co2e_t": total_co2e,
            "scope1_mmt": s1_co2e / 1_000_000.0, "scope2_mmt": s2 / 1_000_000.0, "total_mmt": total_co2e / 1_000_000.0,
            "ch4_mass_t": ch4_mass_t, "co2_mass_t": em.get("co2_mass_t", 0.0), "n2o_mass_t": em.get("n2o_mass_t", 0.0),
            "gross_gas_mmsm3": gross_gas_mmsm3,
            "net_gas_mmsm3": net_gas_mmsm3,
            "liquid_mmbbl": prod.get("total_liquid_bbl", 0.0) / 1_000_000.0, "total_mmboe": boe / 1_000_000.0,
            "flaring_mmsm3": flare_mmsm3,
            "routine_mmsm3": fl_det.get("routine_mmsm3", 0.0),
            "non_routine_mmsm3": fl_det.get("non_routine_mmsm3", 0.0),
            "safety_mmsm3": fl_det.get("safety_mmsm3", 0.0),
            "measured_dre_pct": fl_det.get("measured_dre_pct"),
            "has_measured_dre": fl_det.get("has_measured_dre", False),
            "flaring_intensity_pct": flaring_intensity_pct, "decree_21_330_compliant": flaring_intensity_pct <= 1.00,
            "carbon_intensity_kg_boe": carbon_intensity_kg_boe, "methane_intensity_pct": methane_intensity_pct,
            "methane_intensity_basis": mi_basis,
            "gas_density_kg_m3": gas_density,
            "combustion_t": em.get("combustion_t", 0.0), "flaring_t": em.get("flaring_t", 0.0),
            "fugitives_t": em.get("fugitives_t", 0.0), "venting_t": em.get("venting_t", 0.0),
            "nox_t": em.get("nox_t", 0.0), "co_t": em.get("co_t", 0.0),
            "so2_t": em.get("so2_t", 0.0), "voc_t": em.get("voc_t", 0.0), "pm_t": em.get("pm_t", 0.0),
        })
    return timeline


def _compute_2030_target_projection(
    timeline: List[Dict[str, Any]],
    start_year: int,
    end_year: int,
    tenant_id: str = "default",
) -> Dict[str, Any]:
    """Computes corporate 2030 decarbonization glidepath trajectory and milestones aligned with SBTi / net zero."""
    if not timeline:
        return {}

    active_timeline = [t for t in timeline if (t.get("total_co2e_t") or 0.0) > 0]
    base_t = active_timeline[0] if active_timeline else timeline[0]
    latest_t = active_timeline[-1] if active_timeline else timeline[-1]
    base_year = base_t["year"]
    base_ghg = base_t["total_mmt"]
    total_steps = 2030 - base_year
    target_reduction_pct = 20.0

    try:
        from models import SbtiTarget
        sbti = SbtiTarget.query.filter(tenant_matches(SbtiTarget.tenant_id, tenant_id)).order_by(SbtiTarget.id.desc()).first()
        if sbti and sbti.reduction_rate_pct:
            rate = float(sbti.reduction_rate_pct)
            # If rate is an annual linear rate (e.g. 4.2%/yr for 1.5C),
            # compute cumulative reduction from base_year to 2030:
            if rate <= 10.0 and total_steps > 0:
                target_reduction_pct = min(round(total_steps * rate, 1), 75.0)
            else:
                target_reduction_pct = rate
    except Exception as exc:
        logger.warning("Failed querying SBTi target for tenant %s: %s", tenant_id, exc, exc_info=True)

    target_ghg_2030 = max(base_ghg * (1.0 - target_reduction_pct / 100.0), 0.0) if base_ghg > 0 else 0.0

    proj_years = list(range(base_year, 2031))
    glidepath = []
    if base_ghg > 0 and total_steps > 0:
        for y in proj_years:
            step = (y - base_year) / total_steps
            val = base_ghg - step * (base_ghg - target_ghg_2030)
            glidepath.append(round(val, 3))
    else:
        glidepath = [round(base_ghg, 3)] * len(proj_years)

    current_ghg = round(latest_t["total_mmt"], 3)
    achieved_delta = ((current_ghg - base_ghg) / base_ghg * 100.0) if base_ghg > 0 else 0.0
    delta_pct_str = f"{achieved_delta:+.1f}% vs Baseline"

    interim_year = 2027
    interim_ratio = max(0.0, min(1.0, (interim_year - base_year) / total_steps)) if total_steps > 0 else 0.6
    interim_pct = round(interim_ratio * target_reduction_pct, 1)
    interim_ghg = round(base_ghg * (1.0 - interim_pct / 100.0), 3) if base_ghg > 0 else 0.0

    milestones = [
        {
            "year": base_year,
            "target_ghg_mmt": round(base_ghg, 3),
            "reduction_str": "Reference Point",
            "flaring_objective": "Audited Baseline Level",
            "status": "Audited Baseline",
        },
        {
            "year": latest_t["year"],
            "target_ghg_mmt": current_ghg,
            "reduction_str": delta_pct_str,
            "flaring_objective": "Current Operating Flaring",
            "status": "Achieved" if current_ghg < base_ghg else "Under Tracking",
        },
        {
            "year": interim_year,
            "target_ghg_mmt": interim_ghg,
            "reduction_str": f"-{interim_pct:.1f}% GHG vs Baseline",
            "flaring_objective": "Eliminate Routine Flaring (<0.8%)",
            "status": "Achieved" if current_ghg <= interim_ghg else "In Progress",
        },
        {
            "year": 2030,
            "target_ghg_mmt": round(target_ghg_2030, 3),
            "reduction_str": f"-{target_reduction_pct:.1f}% GHG vs Baseline",
            "flaring_objective": "World Bank Zero Routine Flaring",
            "status": "Statutory Target",
        },
    ]

    return {
        "baseline_year": base_year,
        "base_year": base_year,
        "base_ghg_mmt": round(base_ghg, 3),
        "target_2030_ghg_mmt": round(target_ghg_2030, 3),
        "target_reduction_pct": target_reduction_pct,
        "proj_years": proj_years,
        "glidepath_mmt": glidepath,
        "historical_years": [t["year"] for t in timeline],
        "historical_ghg_mmt": [round(t["total_mmt"], 3) for t in timeline],
        "milestones": milestones,
    }


def _query_mitigation_projects(
    facility_ids: List[int],
    start_year: int,
    end_year: int,
    fallback_projects: Optional[List[Dict[str, Any]]] = None,
    allowed_is_restricted: bool = False,
) -> List[Dict[str, Any]]:
    """Queries live non-test MitigationProject records strictly within the selected facilities and reporting years."""
    if not facility_ids:
        return []

    projects = (
        MitigationProject.query.filter(
            MitigationProject.facility_id.in_(facility_ids),
            MitigationProject.is_test.is_(False),
            (MitigationProject.year.between(start_year, end_year)) | (MitigationProject.year.is_(None)),
        )
        .order_by(MitigationProject.quantity_tco2e.desc())
        .all()
    )

    out = []
    for p in projects:
        title = p.name or "Operational Mitigation Action"
        if p.project_type and p.project_type.upper() not in title.upper():
            title = f"{title} ({p.project_type})"
        status_val = (p.status or "Active").capitalize()
        out.append({
            "title": title,
            "reduction_tco2e": int(p.quantity_tco2e or 0),
            "investment_amount": float(p.investment_amount or 0.0) if p.investment_amount is not None else None,
            "year": p.year,
            "status": status_val,
            "source": "database",
        })
    return out
