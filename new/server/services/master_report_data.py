"""
Master Report Data Aggregation Service
======================================
Extracts, harmonizes, and calculates multi-year greenhouse gas inventories,
production statistics, flaring streams, intensities, and regulatory compliance
metrics from the database for the Universal Master Publication Report Engine.

The queries live in master_report_data_records (yearly aggregates), _portfolio (JV equity, gas composition,
timeline, targets), _breakdowns (uncertainty, facility, Scope 3, OGMP, CBAM), _ledgers (source ledger, census,
chromatography, flaring split) and _quality (sub-annual series, quality audit); this module assembles them.
"""

import hashlib
import json
import logging
from typing import Any, Dict, List, Optional
from models import (
    Facility, Emission, ProductionData, Scope2Emission, FlaringDetail, Scope3Emission, PeriodLock,
    ReportingMetadata,
)
from calculations.constants import get_active_gwp
from services.regional_profiles import get_regional_profile, REGIONAL_PROFILES
from services.tenant_config import get_tenant_config
from utils import normalize_tenant_id, tenant_matches
from services.master_report_data_records import (
    _query_emissions_by_year, _query_flaring_breakdown, _query_production_by_year, _query_scope2_by_year,
    get_facilities_for_scope,
)
from services.master_report_data_portfolio import (
    _assemble_timeline_series, _compute_2030_target_projection, _query_jv_equity_breakdown,
    _query_mitigation_projects, _resolve_dynamic_gas_composition,
)
from services.master_report_data_breakdowns import (
    _query_base_year_recalculations, _query_cbam_and_macc_breakdown, _query_facility_breakdowns,
    _query_ogmp_breakdown, _query_scope3_breakdown, _query_uncertainty_assessment,
)
from services.master_report_data_ledgers import (
    _query_equipment_census, _query_flaring_operational_split, _query_granular_source_ledger,
    _query_multistream_gas_chromatography,
)
from services.master_report_data_quality import _generate_dynamic_quality_audit, _query_subannual_time_series

logger = logging.getLogger(__name__)


def _extract_active_modules(ledger_rows: List[Dict[str, Any]]) -> List[str]:
    """Derives sorted canonical PFD module keys from a facility or portfolio source ledger."""
    active_modules_set = set()
    for row in ledger_rows:
        mod = str(row.get("module") or "").lower()
        sname = str(row.get("source_name") or "").lower()
        if "combustion" in mod or "turbine" in sname or "heater" in sname:
            active_modules_set.add("combustion")
        if "flare" in mod or "flare" in sname:
            active_modules_set.add("flare")
        if "leak" in mod or "fugitive" in mod:
            active_modules_set.add("fugitives")
        if "vent" in mod:
            active_modules_set.add("venting")
        if "tank" in mod:
            active_modules_set.add("tank")
        if "scope 2" in mod or "scope 2" in str(row.get("scope") or "").lower():
            active_modules_set.add("scope2")
        if "compress" in sname:
            active_modules_set.add("compression")
        if "dehydrat" in sname or "glycol" in sname:
            active_modules_set.add("dehydration")
        if "water" in sname:
            active_modules_set.add("water")
        if "reinject" in sname:
            active_modules_set.add("reinjection")
    return sorted(active_modules_set)


def _scope1_at_gwp(fac_ids, years, gwp_factors):
    """{(facility_id, year): verified Scope 1 tCO2e on `gwp_factors`} (services.master_report_data_records)."""
    from models import Emission
    from services.master_report_data_records import record_co2e_at_gwp

    out = {}
    for e in Emission.query.filter(Emission.facility_id.in_(fac_ids), Emission.year.in_(years),
                                   Emission.status == "Verified", Emission.is_test.is_(False)).all():
        out[(e.facility_id, e.year)] = out.get((e.facility_id, e.year), 0.0) + record_co2e_at_gwp(e, gwp_factors)
    return out


def _apply_methane_intensities(timeline, fac_ids, gas_comp_data=None, gwp_factors=None):
    """Methane intensity of each report year from the dashboard's computation (services.intensity /
    services.methane_intensity, BA-054): the OGCI / OGMP volume figure (CH4 volume / marketed gas, compared to the
    0.20 % target) as methane_intensity_pct, and the NGSI figure (CH4 / CH4 in the throughput at 0.0192 t/Mcf) as
    methane_intensity_ngsi_pct, over the facility-years with production. It was CH4 / gas mass at 0.717 kg/m3."""
    from models import Facility
    from services.intensity import intensity_cells, segment_category
    from services.methane_intensity import (M3_PER_MCF, NGSI_CH4_T_PER_MCF, ngsi_ch4_content,
                                            volume_intensity_pct)

    if not fac_ids:
        return
    years = [int(t["year"]) for t in timeline]
    cells = intensity_cells(years=years, allowed_fids=list(fac_ids))
    seg = {f.id: segment_category(f.segment) for f in Facility.query.filter(Facility.id.in_(fac_ids)).all()}
    s1_at_gwp = _scope1_at_gwp(fac_ids, years, gwp_factors) if gwp_factors else {}
    c1 = None
    if isinstance(gas_comp_data, dict):
        try:
            raw = float(gas_comp_data.get("c1") or gas_comp_data.get("ch4") or 0)
            c1 = raw / 100.0 if raw > 1 else (raw or None)
        except (TypeError, ValueError):
            c1 = None
    for t in timeline:
        y = int(t["year"])
        matched = [(k, c) for k, c in cells.items() if k[1] == y and c["has_prod"]]
        ch4 = sum(c["ch4"] for _, c in matched)
        marketed = sum(c["marketed_m3"] for _, c in matched)
        in_thru = sum(c["gas_m3"] / M3_PER_MCF * ngsi_ch4_content(seg.get(k[0]), c1) * NGSI_CH4_T_PER_MCF
                      for k, c in matched)
        vol = volume_intensity_pct(ch4, marketed)
        t["methane_intensity_pct"] = vol or 0.0
        t["methane_intensity_basis"] = "marketed_gas" if vol is not None else "no_gas_production"
        t["methane_intensity_ngsi_pct"] = (ch4 / in_thru * 100.0) if in_thru > 0 else None
        t["marketed_gas_mmsm3"] = marketed / 1e6
        # Decree 21-330 flaring intensity over the same facility-years (flared / produced gas), as the dashboard:
        # flaring at facilities without production is not divided by other facilities' gas (BA-034 / BA-055)
        boe = sum(c["boe"] for _, c in matched)
        if boe > 0:
            # carbon intensity over the facility-years with production, as the dashboard (BA-032), Scope 1 on the
            # report's GWP set from each record's own GWP basis
            t["carbon_intensity_kg_boe"] = sum(s1_at_gwp.get(k, c["s1"]) + c["s2"] for k, c in matched) * 1000.0 / boe
        gas = sum(c["gas_m3"] for _, c in matched)
        if gas > 0:
            t["flaring_intensity_pct"] = sum(c["flaring_m3"] for _, c in matched) / gas * 100.0
            t["decree_21_330_compliant"] = t["flaring_intensity_pct"] <= 1.00


def aggregate_master_report_data(
    mode: str,
    region_key: Optional[str],
    start_year: int,
    end_year: int,
    gwp_standard: str = "AR5",
    allowed_facility_ids: Optional[List[int]] = None,
    tenant_id: str = "default",
) -> Dict[str, Any]:
    """Main aggregator function returning operational, emission, and compliance metrics strictly scoped to one tenant."""
    tid = normalize_tenant_id(tenant_id)
    tenant_config = get_tenant_config(tid)
    allowed_is_restricted = (allowed_facility_ids is not None) or (mode == "regional") or (tid != "default")

    facilities = get_facilities_for_scope(
        mode,
        region_key,
        allowed_facility_ids,
        tenant_config=tenant_config,
        tenant_id=tid,
    )
    fac_ids = [f.id for f in facilities]
    profile = get_regional_profile(
        region_key if mode == "regional" else "national",
        tenant_config=tenant_config,
    )

    gwp_factors = get_active_gwp(standard=gwp_standard)
    em_data = _query_emissions_by_year(fac_ids, start_year, end_year, gwp_factors)
    s2_data = _query_scope2_by_year(fac_ids, start_year, end_year, gwp_factors)
    prod_data = _query_production_by_year(fac_ids, start_year, end_year)
    flare_detail_data = _query_flaring_breakdown(fac_ids, start_year, end_year, em_data, prod_data)

    gas_comp_data, gas_comp_name, gas_comp_source = _resolve_dynamic_gas_composition(
        fac_ids,
        region_key,
        profile,
        tenant_id=tid,
        allowed_is_restricted=allowed_is_restricted,
        allow_regional_cf_fallback=(
            allowed_facility_ids is None and mode == "regional" and bool(region_key)
        ),
    )

    decarb_projects = _query_mitigation_projects(fac_ids, start_year, end_year, [],
                                                 allowed_is_restricted=allowed_is_restricted)

    timeline_summary = _assemble_timeline_series(
        start_year,
        end_year,
        em_data,
        s2_data,
        prod_data,
        flare_detail_data,
        gas_comp_data=gas_comp_data,
    )

    _apply_methane_intensities(timeline_summary, fac_ids, gas_comp_data, gwp_factors)
    excluded_unverified = _count_excluded_records(fac_ids, start_year, end_year)

    target_proj = _compute_2030_target_projection(timeline_summary, start_year, end_year, tenant_id=tid)
    jv_equity = _query_jv_equity_breakdown(fac_ids, timeline_summary, tenant_id=tid, gwp_factors=gwp_factors)
    uncertainty_data = _query_uncertainty_assessment(fac_ids, end_year, allowed_is_restricted=allowed_is_restricted)
    facility_breakdowns = _query_facility_breakdowns(facilities, start_year, end_year, gwp_factors)
    scope3_data = _query_scope3_breakdown(fac_ids, start_year, end_year, allowed_is_restricted=allowed_is_restricted)
    ogmp_data = _query_ogmp_breakdown(fac_ids, start_year, end_year, allowed_is_restricted=allowed_is_restricted)
    cbam_macc_data = _query_cbam_and_macc_breakdown(fac_ids, start_year, end_year, allowed_is_restricted=allowed_is_restricted)
    base_year_recalcs = _query_base_year_recalculations(start_year, end_year, tenant_id=tid)

    # Dynamic Granular & Sub-Annual Engineering Ledgers
    granular_source_ledger = _query_granular_source_ledger(fac_ids, end_year, gwp_factors)
    equipment_census = _query_equipment_census(fac_ids)
    multistream_gas_chromatography = _query_multistream_gas_chromatography(fac_ids)
    flaring_operational_split = _query_flaring_operational_split(fac_ids, end_year)
    subannual_time_series = _query_subannual_time_series(fac_ids, end_year, gwp_factors, gas_comp_data=gas_comp_data)
    dynamic_quality_audit = _generate_dynamic_quality_audit(
        fac_ids,
        end_year,
        excluded_unverified=excluded_unverified,
        start_year=start_year,
    )

    # Active module inventory per DB sources + verified emissions (portfolio & per-facility PFD blocks)
    ledger_by_fac = granular_source_ledger.get("ledger_by_facility", {})
    active_modules = _extract_active_modules(granular_source_ledger.get("total_ledger_rows", [])) if fac_ids else []
    active_modules_by_facility = {
        fac.name: _extract_active_modules(ledger_by_fac.get(fac.name, []))
        for fac in facilities
    }

    governance = _query_governance(tid, start_year, end_year, timeline_summary)
    regional_benchmarks = (
        _query_regional_benchmarks(facilities, start_year, end_year, allowed_facility_ids, tenant_config, tid,
                                   gwp_factors)
        if mode == "comparison" else []
    )

    result = {
        "mode": mode,
        "region_key": region_key,
        "tenant_id": tid,
        "tenant_config": tenant_config,
        "profile": profile,
        "facilities": [
            {
                "id": f.id,
                "name": f.name,
                "region": f.region,
                "field": f.field,
                "segment": getattr(f, "segment", None),
                "description": getattr(f, "description", None),
                "boundary_notes": getattr(f, "boundary_notes", None),
            }
            for f in facilities
        ],
        "start_year": start_year,
        "end_year": end_year,
        "gwp_standard": gwp_standard,
        "gwp_factors": gwp_factors,
        "timeline": timeline_summary,
        "target_projection": target_proj,
        "jv_equity": jv_equity,
        "uncertainty": uncertainty_data,
        "facility_breakdowns": facility_breakdowns,
        "decarbonization_projects": decarb_projects,
        "regional_benchmarks": regional_benchmarks,
        "gas_composition": gas_comp_data,
        "gas_comp_name": gas_comp_name,
        "gas_comp_source": gas_comp_source,
        "scope3": scope3_data,
        "ogmp": ogmp_data,
        "cbam_macc": cbam_macc_data,
        "base_year_recalcs": base_year_recalcs,
        "granular_source_ledger": granular_source_ledger,
        "equipment_census": equipment_census,
        "multistream_gas_chromatography": multistream_gas_chromatography,
        "flaring_operational_split": flaring_operational_split,
        "subannual_time_series": subannual_time_series,
        "dynamic_quality_audit": dynamic_quality_audit,
        "excluded_unverified": excluded_unverified,
        "active_modules": active_modules,
        "active_modules_by_facility": active_modules_by_facility,
        "governance": governance,
    }
    canonical_payload = json.dumps(result, sort_keys=True, default=str, ensure_ascii=False).encode("utf-8")
    result["dataset_sha256"] = hashlib.sha256(canonical_payload).hexdigest()
    return result


def _count_excluded_records(fac_ids: List[int], start_year: int, end_year: int) -> Dict[str, int]:
    """Unverified/pending/test records excluded from the verified report perimeter."""
    excluded_unverified = {
        "emission_unverified": 0,
        "emission_test": 0,
        "scope2_unverified": 0,
        "scope3_unverified": 0,
        "flaring_unverified": 0,
        "prod_test": 0,
        "total_excluded": 0,
    }
    if fac_ids:
        excluded_unverified["emission_unverified"] = Emission.query.filter(
            Emission.facility_id.in_(fac_ids),
            Emission.year.between(start_year, end_year),
            Emission.is_test.is_(False),
            Emission.status != "Verified",
        ).count()
        excluded_unverified["emission_test"] = Emission.query.filter(
            Emission.facility_id.in_(fac_ids),
            Emission.year.between(start_year, end_year),
            Emission.is_test.is_(True),
        ).count()
        excluded_unverified["scope2_unverified"] = Scope2Emission.query.filter(
            Scope2Emission.facility_id.in_(fac_ids),
            Scope2Emission.year.between(start_year, end_year),
            Scope2Emission.status != "Verified",
        ).count()
        excluded_unverified["scope3_unverified"] = Scope3Emission.query.filter(
            Scope3Emission.facility_id.in_(fac_ids),
            Scope3Emission.year.between(start_year, end_year),
            Scope3Emission.status != "Verified",
        ).count()
        excluded_unverified["flaring_unverified"] = FlaringDetail.query.filter(
            FlaringDetail.facility_id.in_(fac_ids),
            FlaringDetail.year.between(start_year, end_year),
            FlaringDetail.status != "Verified",
        ).count()
        excluded_unverified["prod_test"] = ProductionData.query.filter(
            ProductionData.facility_id.in_(fac_ids),
            ProductionData.year.between(start_year, end_year),
            ProductionData.is_test.is_(True),
        ).count()
        excluded_unverified["total_excluded"] = sum(v for k, v in excluded_unverified.items() if k != "total_excluded")
    return excluded_unverified


def _query_governance(tid: str, start_year: int, end_year: int, timeline_summary: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Period lock sign-off and assurance metadata of the reporting window."""
    locks = PeriodLock.query.filter(
        tenant_matches(PeriodLock.tenant_id, tid),
        PeriodLock.year >= start_year,
        PeriodLock.year <= end_year,
        PeriodLock.month.is_(None),
    ).order_by(PeriodLock.year.asc()).all()
    locked_years = {int(lk.year): lk for lk in locks if str(lk.status or "").lower() == "locked"}
    active_years = [
        int(t["year"])
        for t in timeline_summary
        if (t.get("total_co2e_t") or 0.0) > 0 or (t.get("gross_gas_mmsm3") or 0.0) > 0
    ]
    required_lock_years = active_years or [int(end_year)]
    is_locked = bool(required_lock_years) and all(y in locked_years for y in required_lock_years)
    latest_lock = None
    if is_locked:
        latest_yr = max(y for y in required_lock_years if y in locked_years)
        latest_lock = locked_years[latest_yr]

    rep_meta_dict = None
    if tid == "default":
        rm = (
            ReportingMetadata.query.filter(
                ReportingMetadata.year >= start_year,
                ReportingMetadata.year <= end_year,
            )
            .order_by(ReportingMetadata.year.desc())
            .first()
        )
        if rm:
            rep_meta_dict = {
                "year": rm.year,
                "assurance_level": rm.assurance_level,
                "assurance_provider": rm.assurance_provider,
                "is_tcfd_aligned": bool(rm.is_tcfd_aligned),
                "has_reduction_target": bool(rm.has_reduction_target),
                "target_description": rm.target_description,
            }

    return {
        "is_locked": is_locked,
        "locked_years": sorted(list(locked_years.keys())),
        "required_lock_years": required_lock_years,
        "signoff_signatory": (
            (latest_lock.signoff_signatory or (latest_lock.user_locked.fullName if latest_lock.user_locked else None))
            if latest_lock else None
        ),
        "locked_by_name": (latest_lock.user_locked.fullName if latest_lock and latest_lock.user_locked else None),
        "locked_at": (latest_lock.locked_at.strftime("%Y-%m-%d %H:%M UTC") if latest_lock and latest_lock.locked_at else None),
        "signoff_notes": (latest_lock.signoff_notes if latest_lock else None),
        "reporting_metadata": rep_meta_dict,
    }


def _query_regional_benchmarks(
    facilities: List[Facility],
    start_year: int,
    end_year: int,
    allowed_facility_ids: Optional[List[int]],
    tenant_config: Dict[str, Any],
    tid: str,
    gwp_factors=None,
) -> List[Dict[str, Any]]:
    """Comparison mode: carbon and flaring intensity per regional profile and per other region."""
    gwp_factors = gwp_factors or get_active_gwp()
    regional_benchmarks = []
    years = range(start_year, end_year + 1)
    bench_matched_ids = set()

    def _append_benchmark_bucket(b_key: str, b_name: str, b_basin: str, b_seg: str, r_facs: List[Facility]):
        # the dashboard's facility-year cells: emissions and production over the same facility-years (all-year
        # emissions were divided by producing-year BOE, 5.3 x; F-GUI2-09) and one flared volume (metered records,
        # else the production data; never a CO2e-derived volume: F-GUI2-08)
        from services.intensity import intensity_cells
        r_ids = [rf.id for rf in r_facs]
        all_cells = list(intensity_cells(years=list(years), facility_id=r_ids).values())
        cells = [c for c in all_cells if c["has_prod"]]
        # Scope 1 CH4 / N2O re-weighted to the report's GWP set (F-RPT-25)
        _ga = get_active_gwp()
        _rw = lambda c: c["s1"] + c["s2"] + c["ch4"] * (float(gwp_factors["CH4"]) - float(_ga["CH4"])) + c["n2o"] * (
            float(gwp_factors["N2O"]) - float(_ga["N2O"]))
        tot_co2e = sum(_rw(c) for c in all_cells)  # the bucket's emissions; intensities on matched years
        tot_boe = sum(c["boe"] for c in cells)
        tot_gas_m3 = sum(c["gas_m3"] for c in cells)
        tot_flare_m3 = sum(c["flaring_m3"] for c in cells)

        ci = (sum(_rw(c) for c in cells) * 1000.0 / tot_boe) if tot_boe > 0 else None
        fi = (tot_flare_m3 / tot_gas_m3 * 100.0) if tot_gas_m3 > 0 else None

        regional_benchmarks.append({
            "key": b_key,
            "name": b_name,
            "basin": b_basin,
            "segment": b_seg,
            "facility_count": len(r_facs),
            "total_co2e_t": tot_co2e,
            "total_mmboe": tot_boe / 1e6,
            "carbon_intensity_kg_boe": ci,
            "flaring_intensity_pct": fi,
            "decree_compliant": (fi <= 1.00) if fi is not None else None,
        })

    for rk in REGIONAL_PROFILES:
        rprof = get_regional_profile(rk, tenant_config=tenant_config)
        r_facs = get_facilities_for_scope(
            "regional",
            rk,
            allowed_facility_ids,
            tenant_config=tenant_config,
            tenant_id=tid,
        )
        if not r_facs:
            continue
        for rf in r_facs:
            bench_matched_ids.add(rf.id)
        _append_benchmark_bucket(
            rk,
            rprof["name"],
            rprof["basin"],
            rprof["segment"].capitalize(),
            r_facs,
        )

    custom_groups: Dict[str, List[Facility]] = {}
    for fac in facilities:
        if fac.id in bench_matched_ids:
            continue
        reg_name = fac.region or fac.location or fac.name
        if not reg_name or reg_name.lower() in ("algeria", "global", "south", "none"):
            continue
        custom_groups.setdefault(reg_name, []).append(fac)

    for reg_name, r_facs in custom_groups.items():
        clean_key = reg_name.lower().replace(" ", "_").replace("/", "_")
        seg = (r_facs[0].segment or "Upstream").capitalize()
        _append_benchmark_bucket(
            clean_key,
            f"{reg_name} Production Area",
            f"{reg_name} Basin",
            seg,
            r_facs,
        )
    return regional_benchmarks
