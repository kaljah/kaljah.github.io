"""Master report data: the monthly / quarterly time series and the data quality audit recommendations
(split from master_report_data.py)."""

from typing import Any, Dict, List, Optional, Tuple
from models import (
    ComponentInventory,
    CustomFactor,
    Emission,
    Facility,
    FlaringDetail,
    MitigationProject,
    OgmpSurvey,
    ProductionData,
    Scope2Emission,
)
from calculations.units import VOLUME_UNITS_TO_M3
from services.master_report_data_records import _compute_gas_properties
from extensions import db


_MONTH_NAMES = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
_DAYS_IN_MONTH = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]


def _load_subannual_records(fac_ids: List[int], target_year: int):
    """Production by facility, and verified Scope 1 / Scope 2 records by (facility, month or None)."""
    prods_by_fac: Dict[int, List[ProductionData]] = {}
    ems_by_fac_month: Dict[Tuple[int, Any], List[Emission]] = {}
    s2_by_fac_month: Dict[Tuple[int, Any], List[Scope2Emission]] = {}

    if fac_ids:
        for p in ProductionData.query.filter(
            ProductionData.facility_id.in_(fac_ids),
            ProductionData.year == target_year,
            ProductionData.is_test.is_(False),
        ).order_by(ProductionData.month).all():
            prods_by_fac.setdefault(p.facility_id, []).append(p)
        for em in Emission.query.filter(
            Emission.facility_id.in_(fac_ids),
            Emission.year == target_year,
            Emission.status == "Verified",
            Emission.is_test.is_(False),
        ).all():
            m_key = em.month if (em.month is not None and 1 <= em.month <= 12) else None
            ems_by_fac_month.setdefault((em.facility_id, m_key), []).append(em)
        for s2 in Scope2Emission.query.filter(
            Scope2Emission.facility_id.in_(fac_ids),
            Scope2Emission.year == target_year,
            Scope2Emission.status == "Verified",
        ).all():
            m_key = s2.month if (s2.month is not None and 1 <= s2.month <= 12) else None
            s2_by_fac_month.setdefault((s2.facility_id, m_key), []).append(s2)
    return prods_by_fac, ems_by_fac_month, s2_by_fac_month


def _subannual_em_co2e(e: Emission, gwp_factors: Dict[str, float]) -> float:
    from services.master_report_data_records import record_co2e_at_gwp

    return record_co2e_at_gwp(e, gwp_factors)


def _subannual_energy_btu(ems_list: List[Emission], s2_list: List[Scope2Emission], hhv_btu_scf: float) -> float:
    btu = 0.0
    for e in ems_list:
        pt = (e.process_type or "").lower()
        if "combust" in pt or "fuel" in pt or "turbine" in pt or "engine" in pt or "heater" in pt or "boiler" in pt:
            qty = float(e.quantity or 0.0)
            u = (e.unit or "").lower().strip()
            if u in VOLUME_UNITS_TO_M3:
                m3_v = qty * VOLUME_UNITS_TO_M3[u]
                btu += m3_v * 35.3147 * hhv_btu_scf
    for s2 in s2_list:
        kwh = float(s2.electricity_kwh or 0.0)
        btu += kwh * 3412.14
    return btu


def _subannual_month_row(m_idx: int, p, ems_m, s2_m, gwp_factors: Dict[str, float], hhv_btu_scf: float) -> Dict[str, Any]:
    oil = float(p.oil_amount or 0.0) if p else 0.0
    gas_mscf = float(p.gas_amount or 0.0) if p else 0.0
    tot_mmboe_val = float(getattr(p, "total_production_mmboe", 0.0) or 0.0) if p else 0.0
    if tot_mmboe_val > 0:
        tot_boe = tot_mmboe_val * 1_000_000.0
    else:
        tot_boe = oil + (gas_mscf * 1000.0 / 5800.0)

    co2e_m = sum(_subannual_em_co2e(e, gwp_factors) for e in ems_m) + sum(float(s.co2e or 0.0) for s in s2_m)
    energy_btu_m = _subannual_energy_btu(ems_m, s2_m, hhv_btu_scf)
    days = _DAYS_IN_MONTH[m_idx - 1]
    return {
        "month": m_idx,
        "month_name": _MONTH_NAMES[m_idx - 1],
        "co2e": co2e_m,
        "co2": sum(float(e.co2_emissions or 0.0) for e in ems_m),
        "ch4": sum(float(e.ch4_emissions or 0.0) for e in ems_m),
        "n2o": sum(float(e.n2o_emissions or 0.0) for e in ems_m),
        "oil_bbl": oil,
        "gas_mscf": gas_mscf,
        "total_boe": tot_boe,
        "intensity_co2e_boe": (co2e_m / tot_boe) if tot_boe > 0 else 0.0,
        "energy_hhv": energy_btu_m,
        "energy_intensity": ((energy_btu_m / 1e6) / tot_boe) if tot_boe > 0 else 0.0,
        "daily_avg_co2e": (co2e_m / days) if days > 0 else 0.0,
    }


def _subannual_quarter_rows(monthly_rows, annual_ems, annual_s2, gwp_factors, hhv_btu_scf) -> List[Dict[str, Any]]:
    """Quarter sums of the monthly rows, with annual-only records spread over the quarters by production."""
    q_sums = {
        "Qtr1": {"co2e": 0.0, "co2": 0.0, "ch4": 0.0, "n2o": 0.0, "oil": 0.0, "gas_mscf": 0.0, "boe": 0.0, "energy_hhv": 0.0, "days": 90},
        "Qtr2": {"co2e": 0.0, "co2": 0.0, "ch4": 0.0, "n2o": 0.0, "oil": 0.0, "gas_mscf": 0.0, "boe": 0.0, "energy_hhv": 0.0, "days": 91},
        "Qtr3": {"co2e": 0.0, "co2": 0.0, "ch4": 0.0, "n2o": 0.0, "oil": 0.0, "gas_mscf": 0.0, "boe": 0.0, "energy_hhv": 0.0, "days": 92},
        "Qtr4": {"co2e": 0.0, "co2": 0.0, "ch4": 0.0, "n2o": 0.0, "oil": 0.0, "gas_mscf": 0.0, "boe": 0.0, "energy_hhv": 0.0, "days": 92},
    }
    for row in monthly_rows:
        q = q_sums[f"Qtr{(row['month'] - 1) // 3 + 1}"]
        q["co2e"] += row["co2e"]
        q["co2"] += row["co2"]
        q["ch4"] += row["ch4"]
        q["n2o"] += row["n2o"]
        q["oil"] += row["oil_bbl"]
        q["gas_mscf"] += row["gas_mscf"]
        q["boe"] += row["total_boe"]
        q["energy_hhv"] += row["energy_hhv"]

    # Apportion annual-only rows (month is None) ONCE across Q1..Q4 so YTD matches Ch. 2 cleanly
    if annual_ems or annual_s2:
        ann_co2 = sum(float(e.co2_emissions or 0.0) for e in annual_ems)
        ann_ch4 = sum(float(e.ch4_emissions or 0.0) for e in annual_ems)
        ann_n2o = sum(float(e.n2o_emissions or 0.0) for e in annual_ems)
        ann_co2e = sum(_subannual_em_co2e(e, gwp_factors) for e in annual_ems) + sum(float(s.co2e or 0.0) for s in annual_s2)
        ann_energy = _subannual_energy_btu(annual_ems, annual_s2, hhv_btu_scf)
        tot_q_boe = sum(qd["boe"] for qd in q_sums.values())
        for qk, qd in q_sums.items():
            w = (qd["boe"] / tot_q_boe) if tot_q_boe > 0 else 0.25
            qd["co2e"] += ann_co2e * w
            qd["co2"] += ann_co2 * w
            qd["ch4"] += ann_ch4 * w
            qd["n2o"] += ann_n2o * w
            qd["energy_hhv"] += ann_energy * w

    quarterly_rows = []
    for qk, qd in q_sums.items():
        q_boe = qd["boe"]
        q_co2e = qd["co2e"]
        quarterly_rows.append({
            "quarter": qk,
            "co2e": q_co2e,
            "co2": qd["co2"],
            "ch4": qd["ch4"],
            "n2o": qd["n2o"],
            "oil_bbl": qd["oil"],
            "gas_mscf": qd["gas_mscf"],
            "total_boe": q_boe,
            "intensity_co2e_boe": (q_co2e / q_boe) if q_boe > 0 else 0.0,
            "energy_hhv": qd["energy_hhv"],
            "energy_intensity": (qd["energy_hhv"] / q_boe / 1e6) if q_boe > 0 else 0.0,
            "daily_avg_co2e": (q_co2e / qd["days"]) if qd["days"] > 0 else 0.0,
            "days": qd["days"],
        })
    return quarterly_rows


def _query_subannual_time_series(
    fac_ids: List[int],
    target_year: int,
    gwp_factors: Dict[str, float],
    gas_comp_data: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Compiles monthly (Jan-Dec) and quarterly (Q1-Q4) production, emissions, and intensity tables.
    Strictly sums verified database rows per month without synthetic 1/12th duplication.
    """
    facilities = Facility.query.filter(Facility.id.in_(fac_ids)).all() if fac_ids else []
    prods_by_fac, ems_by_fac_month, s2_by_fac_month = _load_subannual_records(fac_ids, target_year)

    gas_props = _compute_gas_properties(gas_comp_data)
    hhv_btu_scf = float(gas_props.get("hhv_btu_scf") or 0.0) or 1020.0

    subannual_by_fac = {}
    for fac in facilities:
        prod_by_month = {p.month: p for p in prods_by_fac.get(fac.id, [])}
        distinct_em_months = [m for m in range(1, 13) if ems_by_fac_month.get((fac.id, m))]
        annual_ems = ems_by_fac_month.get((fac.id, None), [])
        annual_s2 = s2_by_fac_month.get((fac.id, None), [])

        has_monthly = len(distinct_em_months) >= 6
        if has_monthly:
            granularity = "monthly"
        elif distinct_em_months:
            granularity = "quarterly_only"
        elif annual_ems or annual_s2:
            granularity = "annual_only"
        else:
            granularity = "none"

        monthly_rows = [
            _subannual_month_row(
                m_idx, prod_by_month.get(m_idx), ems_by_fac_month.get((fac.id, m_idx), []),
                s2_by_fac_month.get((fac.id, m_idx), []), gwp_factors, hhv_btu_scf,
            )
            for m_idx in range(1, 13)
        ]
        quarterly_rows = _subannual_quarter_rows(monthly_rows, annual_ems, annual_s2, gwp_factors, hhv_btu_scf)

        subannual_by_fac[fac.name] = {
            "has_monthly_data": has_monthly,
            "subannual_granularity": granularity,
            "monthly_rows": monthly_rows,
            "quarterly_rows": quarterly_rows,
            "ytd_totals": {
                "co2e": sum(r["co2e"] for r in quarterly_rows),
                "co2": sum(r["co2"] for r in quarterly_rows),
                "ch4": sum(r["ch4"] for r in quarterly_rows),
                "n2o": sum(r["n2o"] for r in quarterly_rows),
                "oil_bbl": sum(r["oil_bbl"] for r in quarterly_rows),
                "gas_mscf": sum(r["gas_mscf"] for r in quarterly_rows),
                "total_boe": sum(r["total_boe"] for r in quarterly_rows),
                "energy_hhv": sum(r["energy_hhv"] for r in quarterly_rows),
            },
        }

    return subannual_by_fac


def _audit_fuel_sampling(fac_ids: List[int], facilities: List[Facility]) -> List[Dict[str, Any]]:
    recommendations = []
    # 1. Fuel property sampling frequency
    gc_count = CustomFactor.query.filter(
        CustomFactor.facility_id.in_(fac_ids),
        CustomFactor.gas_composition_json.isnot(None),
        CustomFactor.is_archived.is_(False),
        CustomFactor.status == "Approved",
        CustomFactor.is_test.is_(False),
    ).count()
    if gc_count < len(facilities) * 4:
        recommendations.append({
            "topic": "Fuel Property Sampling & Testing Frequency",
            "topic_fr": "Fréquence d'Échantillonnage et d'Analyse des Combustibles",
            "observation": f"Database logs {gc_count} approved laboratory gas chromatography stream analysis/analyses across {len(facilities)} facility/facilities.",
            "observation_fr": f"La base enregistre {gc_count} analyse(s) chromatographique(s) de laboratoire approuvée(s) sur {len(facilities)} installation(s).",
            "recommendation": "Establish periodic gas chromatography sampling per fuel/flare header to strengthen Tier 2/3 compositional emission factors.",
            "recommendation_fr": "Mettre en place un échantillonnage chromatographique périodique par collecteur combustible/torche pour consolider les facteurs Niveau 2/3.",
            "priority": "High",
            "priority_fr": "Élevée",
            "statutory_ref": "API Compendium 2021 Section 4.1 & ISO 14064-1",
            "statutory_ref_fr": "API Compendium 2021 Sect. 4.1 & ISO 14064-1",
        })
    else:
        recommendations.append({
            "topic": "Fuel Property Sampling & Chromatography Verification",
            "topic_fr": "Échantillonnage des Combustibles et Vérification Chromatographique",
            "observation": f"Comprehensive multi-stream GC laboratory assays logged ({gc_count} approved streams across active trains).",
            "observation_fr": f"Analyses chromatographiques multi-flux complètes enregistrées ({gc_count} flux approuvés sur les trains actifs).",
            "recommendation": "Maintain periodic gas chromatography sampling and annual lab cross-checks across all manifolds.",
            "recommendation_fr": "Maintenir la fréquence périodique de chromatographie et les recoupements annuels en laboratoire sur tous les collecteurs.",
            "priority": "Low",
            "priority_fr": "Faible",
            "statutory_ref": "API Compendium 2021 Section 4.1",
            "statutory_ref_fr": "API Compendium 2021 Sect. 4.1",
        })
    return recommendations


def _audit_flare_dre(fac_ids: List[int], target_year: int) -> List[Dict[str, Any]]:
    recommendations = []
    # 2. Flare DRE verification
    visr_rows = FlaringDetail.query.filter(
        FlaringDetail.facility_id.in_(fac_ids),
        FlaringDetail.year == target_year,
        FlaringDetail.status == "Verified",
        FlaringDetail.measured_dre_pct.isnot(None),
    ).all()
    visr_count = len(visr_rows)
    if visr_count > 0:
        avg_dre = sum(float(r.measured_dre_pct) for r in visr_rows) / visr_count
        recommendations.append({
            "topic": "Flare Destruction Efficiency (DRE) Telemetry",
            "topic_fr": "Télémétrie d'Efficacité de Destruction en Torche (DRE)",
            "observation": f"Verified flare records log field DRE measurements ({visr_count} record(s), mean {avg_dre:.2f}% DRE) for {target_year}.",
            "observation_fr": f"Les enregistrements vérifiés consignent {visr_count} mesure(s) terrain de DRE (moyenne {avg_dre:.2f} % DRE) pour {target_year}.",
            "recommendation": "Continue periodic optical flare telemetry calibration to maintain traceable destruction efficiency evidence.",
            "recommendation_fr": "Poursuivre l'étalonnage périodique de la télémétrie optique des torches pour maintenir une preuve traçable de destruction.",
            "priority": "Medium",
            "priority_fr": "Moyenne",
            "statutory_ref": "Executive Decree 21-330 & OGMP 2.0 Level 4",
            "statutory_ref_fr": "Décret Exécutif 21-330 & OGMP 2.0 Niveau 4",
        })
    else:
        recommendations.append({
            "topic": "Flare Destruction Efficiency (DRE) Measurement",
            "topic_fr": "Mesure de l'Efficacité de Destruction en Torche (DRE)",
            "observation": f"No verified field-measured flare DRE telemetry recorded for {target_year}; EPA 98.0% engineering default applies where unmeasured.",
            "observation_fr": f"Aucune télémétrie optique DRE vérifiée enregistrée pour {target_year} ; le facteur défaut EPA de 98,0 % s'applique.",
            "recommendation": "Deploy optical gas imaging or multi-spectral flare monitoring to record empirical DRE values.",
            "recommendation_fr": "Déployer l'imagerie optique des gaz ou la télémétrie spectrale VISR pour enregistrer des valeurs empiriques de DRE.",
            "priority": "High",
            "priority_fr": "Élevée",
            "statutory_ref": "Executive Decree 21-330 & API Compendium Section 5",
            "statutory_ref_fr": "Décret Exécutif 21-330 & API Compendium Sect. 5",
        })
    return recommendations


def _audit_ldar(fac_ids: List[int], target_year: int) -> List[Dict[str, Any]]:
    recommendations = []
    # 3. LDAR & Component-level leak detection
    ogmp_surveys = OgmpSurvey.query.filter(
        OgmpSurvey.facility_id.in_(fac_ids),
        OgmpSurvey.year <= target_year,
    ).count()
    comp_qty_sum = int(
        db.session.query(db.func.coalesce(db.func.sum(ComponentInventory.quantity), 0))
        .filter(ComponentInventory.facility_id.in_(fac_ids))
        .scalar()
        or 0
    )
    if ogmp_surveys > 0 or comp_qty_sum > 0:
        recommendations.append({
            "topic": "Equipment Leaks & LDAR Program",
            "topic_fr": "Fuites d'Équipements et Programme LDAR",
            "observation": f"Component inventory tracks {comp_qty_sum:,} physical components alongside {ogmp_surveys} OGMP top-down survey campaign(s) in database.",
            "observation_fr": f"L'inventaire suit {comp_qty_sum:,} composant(s) physique(s) et {ogmp_surveys} campagne(s) descendante(s) OGMP en base.",
            "recommendation": "Maintain scheduled Method 21 / OGI LDAR surveys and reconcile component counts against fugitive emission records.",
            "recommendation_fr": "Maintenir les campagnes périodiques Méthode 21 / OGI LDAR et réconcilier les comptes de composants avec les émissions fugitives.",
            "priority": "Medium",
            "priority_fr": "Moyenne",
            "statutory_ref": "OGMP 2.0 Gold Standard & EPA Method 21",
            "statutory_ref_fr": "OGMP 2.0 Gold Standard & EPA Méthode 21",
        })
    else:
        recommendations.append({
            "topic": "Fugitive Emissions & LDAR Implementation",
            "topic_fr": "Émissions Fugitives et Déploiement LDAR",
            "observation": "No component-level inventory or OGMP survey records logged for these facilities.",
            "observation_fr": "Aucun inventaire détaillé de composants ni campagne OGMP n'est enregistré pour ces installations.",
            "recommendation": "Implement component-level LDAR inventory tracking and OGI campaigns to advance toward OGMP 2.0 Level 4/5.",
            "recommendation_fr": "Déployer un inventaire de composants LDAR et des campagnes optiques OGI pour progresser vers OGMP 2.0 Niveau 4/5.",
            "priority": "High",
            "priority_fr": "Élevée",
            "statutory_ref": "API Compendium Section 7 & OGMP 2.0",
            "statutory_ref_fr": "API Compendium Sect. 7 & OGMP 2.0",
        })
    return recommendations


def _audit_mitigation_projects(fac_ids: List[int], target_year: int, start_year: Optional[int]) -> List[Dict[str, Any]]:
    recommendations = []
    # 4. Pull any active HSE projects from MitigationProject scoped to the reporting window
    eff_start_year = min(start_year, target_year) if start_year is not None else target_year
    active_projects = (
        MitigationProject.query.filter(
            MitigationProject.facility_id.in_(fac_ids),
            MitigationProject.is_test.is_(False),
            (MitigationProject.year.between(eff_start_year, target_year)) | (MitigationProject.year.is_(None)),
            db.func.lower(MitigationProject.status).in_(["active", "executing", "proposed"]),
        )
        .order_by(MitigationProject.id.desc())
        .limit(3)
        .all()
    )
    for proj in active_projects:
        p_name = proj.name or "Decarbonization Initiative"
        p_red = proj.quantity_tco2e or 0.0
        recommendations.append({
            "topic": f"Field Decarbonization: {p_name}",
            "topic_fr": f"Décarbonation Terrain : {p_name}",
            "observation": f"Mitigation initiative logged in database with estimated reduction of {p_red:,.0f} t CO2e/year.",
            "observation_fr": f"Initiative d'atténuation enregistrée en base avec une réduction estimée à {p_red:,.0f} t CO2e/an.",
            "recommendation": f"Verify post-commissioning emission delta against baseline metering (Target completion: {proj.end_date or 'Scheduled'}).",
            "recommendation_fr": f"Vérifier l'écart d'émissions après mise en service par rapport au comptage de référence (Échéance : {proj.end_date or 'Planifiée'}).",
            "priority": "Medium",
            "priority_fr": "Moyenne",
            "statutory_ref": "Decarbonization Abatement Registry",
            "statutory_ref_fr": "Registre d'Abattement & Décarbonation",
        })
    return recommendations


def _audit_governance(fac_ids: List[int], target_year: int, excluded_unverified: Optional[Dict[str, int]]) -> List[Dict[str, Any]]:
    recommendations = []
    # 5. Data Governance, Maker-Checker Verification & Exclusions
    verified_em_cnt = Emission.query.filter(
        Emission.facility_id.in_(fac_ids),
        Emission.year == target_year,
        Emission.status == "Verified",
        Emission.is_test.is_(False),
    ).count()
    excl_tot = int((excluded_unverified or {}).get("total_excluded", 0) or 0)
    if excl_tot > 0:
        recommendations.append({
            "topic": "Unverified & Test Record Exclusion Disclosure",
            "topic_fr": "Divulgation des Exclusions Non Vérifiées et Tests",
            "observation": f"{verified_em_cnt} Verified Scope 1 row(s) included for {target_year}; {excl_tot} unverified/pending/test row(s) were automatically excluded from official totals.",
            "observation_fr": f"{verified_em_cnt} ligne(s) Scope 1 vérifiée(s) incluse(s) pour {target_year} ; {excl_tot} ligne(s) non vérifiée(s)/test automatiquement exclue(s) des totaux officiels.",
            "recommendation": "Complete Maker-Checker sign-off or purge test records prior to final period locking and statutory publication.",
            "recommendation_fr": "Finaliser la validation Maker-Checker ou purger les données de test avant clôture de période et publication réglementaire.",
            "priority": "High",
            "priority_fr": "Élevée",
            "statutory_ref": "ISO 14064-1:2018 Clause 6.2 & QA/QC Gate",
            "statutory_ref_fr": "ISO 14064-1:2018 Clause 6.2 & Porte QA/QC",
        })
    else:
        recommendations.append({
            "topic": "Continuous MRV Governance & Verification Integrity",
            "topic_fr": "Gouvernance MRV Continue et Intégrité de Vérification",
            "observation": f"{verified_em_cnt} Verified Scope 1 emission record(s) passed Maker-Checker quality gates for {target_year} with 0 pending/test rows excluded.",
            "observation_fr": f"{verified_em_cnt} ligne(s) d'émissions Scope 1 vérifiée(s) validée(s) pour {target_year} avec 0 ligne en attente ou test exclue.",
            "recommendation": "Complete statutory Period Lock sign-off and archive calibration certificates to finalize external audit readiness.",
            "recommendation_fr": "Finaliser le verrouillage annuel Period Lock et archiver les certificats d'étalonnage pour l'audit externe.",
            "priority": "Low" if verified_em_cnt > 0 else "Medium",
            "priority_fr": "Faible" if verified_em_cnt > 0 else "Moyenne",
            "statutory_ref": "ISO 14064-1:2018 Clause 6.2 & Period Lock Governance",
            "statutory_ref_fr": "ISO 14064-1:2018 Clause 6.2 & Clôture Period Lock",
        })
    return recommendations


def _generate_dynamic_quality_audit(
    fac_ids: List[int],
    target_year: int,
    excluded_unverified: Optional[Dict[str, int]] = None,
    start_year: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    Algorithmically audits live database completeness, meter tiers, component sums, and flare DRE measurements.
    """
    if not fac_ids:
        return []
    facilities = Facility.query.filter(Facility.id.in_(fac_ids)).all()
    recommendations = []

    recommendations += _audit_fuel_sampling(fac_ids, facilities)
    recommendations += _audit_flare_dre(fac_ids, target_year)
    recommendations += _audit_ldar(fac_ids, target_year)
    recommendations += _audit_mitigation_projects(fac_ids, target_year, start_year)
    recommendations += _audit_governance(fac_ids, target_year, excluded_unverified)

    return recommendations
