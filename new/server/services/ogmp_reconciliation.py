"""
UNEP OGMP 2.0 Level 4 / Level 5 Reconciliation, Materiality & Portfolio Engine.

Implements UNEP / IMEO Technical Guidance Document rules:
- 15 Upstream and 12 Mid/Downstream standardized source catalogs with Quantified / MI / N/A status flags
- Zero-emission and >10% YoY change explanation enforcement
- Bottom-Up L4 Materiality check (>=90% directly quantified at L4, or >=70% with documented justification,
  and remaining material sources (>=5% share) quantified at >= L3)
- Root-Sum-of-Squares (RSS) uncertainty propagation & 95% confidence interval (CI) calculation
- Site-level Instantaneous vs Annualized and Option 1 / Option 2 aggregation & 95% CI overlap reconciliation
- Reconciliation Pathways (1, 2a, 2b, 2c, 2d, 3) alongside +/- threshold variance flagging
- Portfolio 95% equity CH4 materiality coverage & <5% Non-Operated JV exclusion tracking
- Y0-Y10 Implementation Plan (3-year operated / 5-year non-operated Gold Standard milestones)
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional


UPSTREAM_SOURCE_CATALOG: List[Dict[str, str]] = [
    {"code": "UP-01", "name": "Stationary Combustion (Turbines, Engines & Heaters)", "category": "Combustion", "default_ef_ref": "API Compendium 2021 Ch. 4"},
    {"code": "UP-02", "name": "Flaring (Routine, Non-Routine & Safety Flares)", "category": "Flaring", "default_ef_ref": "API Compendium 2021 Ch. 4.6 / VISR DRE"},
    {"code": "UP-03", "name": "Hydrocarbon Storage Tanks (Flashing, Working & Breathing)", "category": "Vented", "default_ef_ref": "API Compendium 2021 Ch. 5.2 / Vasques"},
    {"code": "UP-04", "name": "Pneumatic Devices & Controllers (Bleed & Intermittent)", "category": "Vented", "default_ef_ref": "API Compendium 2021 Table 5-16 / L4 Manufacturer"},
    {"code": "UP-05", "name": "Compressor Seals (Centrifugal Wet/Dry & Reciprocating Rod)", "category": "Fugitive", "default_ef_ref": "API Compendium 2021 Table 5-19 / Direct Flow"},
    {"code": "UP-06", "name": "Glycol Dehydrators & Stripping Gas Vents", "category": "Vented", "default_ef_ref": "GRI-GLYCalc / API Compendium 2021 Ch. 5.4"},
    {"code": "UP-07", "name": "Acid Gas Removal & Amine Sweetening Units", "category": "Process", "default_ef_ref": "Process Simulation / Stack CEMS"},
    {"code": "UP-08", "name": "Well Completions & Workovers (Flowback Venting)", "category": "Vented", "default_ef_ref": "API Compendium 2021 Ch. 5.6"},
    {"code": "UP-09", "name": "Liquids Unloading & Well Deliquification Venting", "category": "Vented", "default_ef_ref": "API Compendium 2021 Eq. 5-11"},
    {"code": "UP-10", "name": "Associated Gas Venting & Casinghead Gas", "category": "Vented", "default_ef_ref": "Metered Flow / GOR Mass Balance"},
    {"code": "UP-11", "name": "Equipment Leaks & Component Fugitives (Valves/Flanges)", "category": "Fugitive", "default_ef_ref": "EPA Method 21 / OGI Hi-Flow (EN 15446)"},
    {"code": "UP-12", "name": "Blowdowns, Purging & Vessel Depressurization", "category": "Vented", "default_ef_ref": "Engineering Volume x Gas Density"},
    {"code": "UP-13", "name": "Produced Water Handling, Vessels & Flash Separators", "category": "Vented", "default_ef_ref": "API Compendium 2021 Table 5-14"},
    {"code": "UP-14", "name": "Maintenance, Turnarounds & Start-Up/Shut-Down Events", "category": "Vented", "default_ef_ref": "Event Log Engineering Calculation"},
    {"code": "UP-15", "name": "Other Upstream Incidents, Abnormalities & Uninventoried", "category": "Fugitive", "default_ef_ref": "Root-Cause Event Quantification"},
]

MID_DOWNSTREAM_SOURCE_CATALOG: List[Dict[str, str]] = [
    {"code": "MD-01", "name": "Compressor Station Seals & Unit Blowdowns", "category": "Fugitive", "default_ef_ref": "API Compendium 2021 / Hi-Flow Measurement"},
    {"code": "MD-02", "name": "Pipeline Segment Leaks, Tie-Ins & Transmission Integrity", "category": "Fugitive", "default_ef_ref": "INGAA / Marcogaz Line-Km & Direct Leak"},
    {"code": "MD-03", "name": "Metering, Pressure-Regulating & City Gate Stations", "category": "Fugitive", "default_ef_ref": "OGI Survey + Component Hi-Flow"},
    {"code": "MD-04", "name": "Pneumatic Controllers, Actuators & Valve Operators", "category": "Vented", "default_ef_ref": "Site Actuation Count & Stem Calibration"},
    {"code": "MD-05", "name": "Stationary Combustion & Boil-Off Gas (BOG) Turbines", "category": "Combustion", "default_ef_ref": "API Compendium 2021 / Exhaust Slip Stack"},
    {"code": "MD-06", "name": "LNG Liquefaction, Regasification & Marine Loading Vents", "category": "Vented", "default_ef_ref": "GIIGNL Boil-Off Balance & Vapor Recovery"},
    {"code": "MD-07", "name": "Underground Gas Storage & Cavern Surface Facilities", "category": "Vented", "default_ef_ref": "Marcogaz Storage TGD / OGI Quantification"},
    {"code": "MD-08", "name": "Distribution Mains, Service Lines & Gate Fugitives", "category": "Fugitive", "default_ef_ref": "Material-Specific Leak Survey Rates"},
    {"code": "MD-09", "name": "Process, Acid Gas & Sulphur Recovery Tail Gas Vents", "category": "Process", "default_ef_ref": "CEMS Stack / Process Simulation"},
    {"code": "MD-10", "name": "Refinery & Gas Plant Flares (Routine & Uncombusted Slip)", "category": "Flaring", "default_ef_ref": "Ultrasonic Flare Meter + DRE Spectrometry"},
    {"code": "MD-11", "name": "Hydrocarbon Storage Tanks & Terminal Loading Racks", "category": "Vented", "default_ef_ref": "API MPMS Chapter 19.1 / Vapor Recovery"},
    {"code": "MD-12", "name": "Turnaround Maintenance, Purging & Third-Party Incidents", "category": "Vented", "default_ef_ref": "Event Mass Balance / Direct Plume"},
]

PATHWAY_DEFINITIONS: Dict[str, Dict[str, str]] = {
    "1": {
        "code": "1",
        "title": "Pathway 1 — Direct Agreement (Gold Level 5)",
        "description": "Reasonable agreement: the bottom-up central estimate lies within the top-down 95% band, or the reverse (Reconciliation & L5 Guidance s3.3.1).",
    },
    "2a": {
        "code": "2a",
        "title": "Pathway 2a — Uncertainty-Bounded Difference",
        "description": "Point variance exceeds tolerance threshold, but combined 95% confidence intervals overlap; prioritize uncertainty reduction.",
    },
    "2b": {
        "code": "2b",
        "title": "Pathway 2b — Top-Down Exceeds Bottom-Up",
        "description": "Site-level measurement significantly exceeds bottom-up inventory without 95% CI overlap; investigate uninventoried vents or super-emitters.",
    },
    "2c": {
        "code": "2c",
        "title": "Pathway 2c — Bottom-Up Exceeds Top-Down",
        "description": "Bottom-up inventory exceeds site measurement without 95% CI overlap; review intermittent event timing or generic EFs.",
    },
    "2d": {
        "code": "2d",
        "title": "Pathway 2d — Instantaneous Extrapolation Mismatch",
        "description": "Instantaneous site snapshot diverges from annual inventory; schedule annualized Option 2 multi-campaign sampling.",
    },
    "3": {
        "code": "3",
        "title": "Pathway 3 — Unresolved",
        "description": "No reasonable agreement and no explanation recorded, Level 4 materiality not met, or a top-down / bottom-up estimate missing: the asset stays at Level 4.",
    },
}

VALID_STATUS_FLAGS = ("Quantified", "MI", "N/A")
VALID_PATHWAYS = tuple(PATHWAY_DEFINITIONS.keys())
VALID_MEASUREMENT_MODES = ("Instantaneous", "Annualized")
VALID_OPTION_MODES = ("Option 1", "Option 2")


def get_source_catalog(segment: Optional[str] = None) -> Dict[str, Any]:
    """Return official UNEP OGMP 2.0 15 Upstream / 12 Mid-Downstream source catalogs."""
    seg = (segment or "").strip().lower()
    if seg in ("midstream", "downstream", "mid/downstream", "mid-downstream"):
        active = MID_DOWNSTREAM_SOURCE_CATALOG
    elif seg == "upstream":
        active = UPSTREAM_SOURCE_CATALOG
    else:
        active = UPSTREAM_SOURCE_CATALOG + MID_DOWNSTREAM_SOURCE_CATALOG
    return {
        "upstream": UPSTREAM_SOURCE_CATALOG,
        "mid_downstream": MID_DOWNSTREAM_SOURCE_CATALOG,
        "active": active,
        "pathways": list(PATHWAY_DEFINITIONS.values()),
        "status_flags": list(VALID_STATUS_FLAGS),
        "measurement_modes": list(VALID_MEASUREMENT_MODES),
        "option_modes": list(VALID_OPTION_MODES),
    }


def validate_emission_source_payload(
    payload: Dict[str, Any],
    prior_year_ch4: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Validate UNEP source-level disclosure rules:
    - status_flag in {'Quantified', 'MI', 'N/A'}
    - MI / N/A allow zero ch4_tonnes without zero-emission justification; N/A forces ch4=0
    - Quantified with ch4_tonnes == 0 requires non-empty zero_emission_explanation
    - |yoy_change_pct| > 10.0 requires non-empty yoy_explanation
    """
    status_flag = str(payload.get("status_flag") or "Quantified").strip()
    if status_flag not in VALID_STATUS_FLAGS:
        raise ValueError(f"status_flag must be one of: {', '.join(VALID_STATUS_FLAGS)}")

    segment = str(payload.get("segment") or "Upstream").strip()
    source_code = str(payload.get("source_code") or "").strip()
    source_name = str(payload.get("source_name") or "").strip()
    if not source_code or not source_name:
        raise ValueError("source_code and source_name are required")

    try:
        ogmp_level = int(payload.get("ogmp_level") or 3)
    except (TypeError, ValueError):
        raise ValueError("ogmp_level must be an integer between 1 and 4")
    if not 1 <= ogmp_level <= 4:
        raise ValueError("Source-level ogmp_level must be between 1 and 4")

    raw_ch4 = payload.get("ch4_tonnes", 0.0)
    try:
        ch4_tonnes = float(raw_ch4 if raw_ch4 not in (None, "") else 0.0)
    except (TypeError, ValueError):
        raise ValueError("ch4_tonnes must be numeric")
    if ch4_tonnes < 0 or not math.isfinite(ch4_tonnes):
        raise ValueError("ch4_tonnes must be a finite non-negative number")

    if status_flag in ("N/A", "MI"):
        ch4_tonnes = 0.0

    raw_unc = payload.get("uncertainty_pct")
    if raw_unc in (None, ""):
        # no silent 60 / 45 / 30 / 15 % by level (no OGMP source gives them; audit 2026-11 F-RPT-06): a Level 4
        # source needs its own uncertainty (the Upstream template asks for it), the others may leave it blank
        if ogmp_level >= 4 and status_flag == "Quantified" and ch4_tonnes > 0:
            raise ValueError("A Level 4 source needs its measurement uncertainty (uncertainty_pct, 95 %)")
        uncertainty_pct = None
    else:
        try:
            uncertainty_pct = float(raw_unc)
        except (TypeError, ValueError):
            raise ValueError("uncertainty_pct must be numeric")
    if uncertainty_pct is not None and (uncertainty_pct < 0 or uncertainty_pct > 500 or not math.isfinite(uncertainty_pct)):
        raise ValueError("uncertainty_pct must be between 0 and 500")

    zero_explanation = str(payload.get("zero_emission_explanation") or "").strip()
    if status_flag == "Quantified" and ch4_tonnes == 0.0 and not zero_explanation:
        raise ValueError("zero_emission_explanation is required when a Quantified source reports 0 tCH4")

    yoy_change_pct = payload.get("yoy_change_pct")
    if yoy_change_pct in (None, ""):
        if prior_year_ch4 is not None and prior_year_ch4 > 0 and status_flag == "Quantified":
            yoy_change_pct = round(((ch4_tonnes - prior_year_ch4) / prior_year_ch4) * 100.0, 2)
        else:
            yoy_change_pct = None
    else:
        try:
            yoy_change_pct = float(yoy_change_pct)
        except (TypeError, ValueError):
            raise ValueError("yoy_change_pct must be numeric")

    yoy_explanation = str(payload.get("yoy_explanation") or "").strip()
    if yoy_change_pct is not None and abs(yoy_change_pct) > 10.0 and not yoy_explanation:
        raise ValueError("yoy_explanation is required when Year-over-Year change exceeds ±10%")

    pathway_code = payload.get("pathway_code")
    if pathway_code is not None and str(pathway_code).strip() != "":
        pathway_code = str(pathway_code).strip()
        if pathway_code not in VALID_PATHWAYS:
            raise ValueError(f"pathway_code must be one of: {', '.join(VALID_PATHWAYS)}")
    else:
        pathway_code = None

    return {
        "segment": segment,
        "source_code": source_code,
        "source_name": source_name,
        "source_category": str(payload.get("source_category") or "").strip() or "Fugitive",
        "ogmp_level": ogmp_level,
        "status_flag": status_flag,
        "ch4_tonnes": round(ch4_tonnes, 4),
        "uncertainty_pct": round(uncertainty_pct, 2) if uncertainty_pct is not None else None,
        "emission_factor_ref": str(payload.get("emission_factor_ref") or "").strip(),
        "quantification_method": str(payload.get("quantification_method") or "").strip(),
        "pathway_code": pathway_code,
        "yoy_change_pct": yoy_change_pct,
        "yoy_explanation": yoy_explanation,
        "zero_emission_explanation": zero_explanation,
    }


def evaluate_l4_materiality(sources: List[Any], l4_justification: str = "") -> Dict[str, Any]:
    """
    UNEP OGMP 2.0 Level 4 Materiality Validation:
    - Active denominator = Quantified sources (excludes N/A).
    - Requires >= 90% of quantified CH4 at Level 4, OR >= 70% with documented justification.
    - All remaining material sources (individually >= 5% of total CH4) must be at Level >= 3.
    - Flags any 'MI' (Material Insufficient Data) sources still requiring resolution.
    """
    quantified = [s for s in sources if (getattr(s, "status_flag", "Quantified") or "Quantified") == "Quantified"]
    mi_sources = [
        {"id": getattr(s, "id", None), "source_code": getattr(s, "source_code", ""), "source_name": getattr(s, "source_name", "")}
        for s in sources
        if getattr(s, "status_flag", "") == "MI"
    ]
    na_count = sum(1 for s in sources if getattr(s, "status_flag", "") == "N/A")

    total_ch4 = sum(float(getattr(s, "ch4_tonnes", 0.0) or 0.0) for s in quantified)
    l4_ch4 = sum(
        float(getattr(s, "ch4_tonnes", 0.0) or 0.0)
        for s in quantified
        if int(getattr(s, "ogmp_level", 1) or 1) >= 4
    )
    l3_plus_ch4 = sum(
        float(getattr(s, "ch4_tonnes", 0.0) or 0.0)
        for s in quantified
        if int(getattr(s, "ogmp_level", 1) or 1) >= 3
    )

    l4_pct = round((l4_ch4 / total_ch4) * 100.0, 2) if total_ch4 > 0 else 0.0
    l3_plus_pct = round((l3_plus_ch4 / total_ch4) * 100.0, 2) if total_ch4 > 0 else 0.0

    remaining_material_below_l3 = []
    if total_ch4 > 0:
        for s in quantified:
            lvl = int(getattr(s, "ogmp_level", 1) or 1)
            val = float(getattr(s, "ch4_tonnes", 0.0) or 0.0)
            share_pct = (val / total_ch4) * 100.0
            # every remaining source must be at least Level 3 (Checklist 2.1); only those >= 5 % were checked and an
            # L2 source at 4.3 % passed (audit 2026-11 F-RPT-04)
            if lvl < 3:
                remaining_material_below_l3.append({
                    "id": getattr(s, "id", None),
                    "source_code": getattr(s, "source_code", ""),
                    "source_name": getattr(s, "source_name", ""),
                    "ogmp_level": lvl,
                    "share_pct": round(share_pct, 2),
                })

    has_just = bool((l4_justification or "").strip())
    meets_pct_rule = (l4_pct >= 90.0) or (l4_pct >= 70.0 and has_just)
    passed = bool(total_ch4 > 0 and meets_pct_rule and len(remaining_material_below_l3) == 0)

    if total_ch4 <= 0:
        rule_status = "No quantified CH4 sources logged"
    elif remaining_material_below_l3:
        rule_status = "Non-compliant (material remaining sources below Level 3)"
    elif l4_pct >= 90.0:
        rule_status = "Compliant (>=90% L4 coverage)"
    elif l4_pct >= 70.0 and has_just:
        rule_status = "Compliant (70-89.9% L4 with technical justification)"
    elif l4_pct >= 70.0 and not has_just:
        rule_status = "Justification required (L4 coverage between 70% and 90%)"
    else:
        rule_status = "Below 70% L4 materiality threshold"

    return {
        "total_quantified_tch4": round(total_ch4, 4),
        "l4_tch4": round(l4_ch4, 4),
        "l4_materiality_pct": l4_pct,
        "l3_plus_pct": l3_plus_pct,
        "has_justification": has_just,
        "passed": passed,
        "rule_status": rule_status,
        "remaining_material_below_l3": remaining_material_below_l3,
        "mi_sources": mi_sources,
        "mi_count": len(mi_sources),
        "na_count": na_count,
        "quantified_count": len(quantified),
    }


def compute_bottom_up_rss(sources: List[Any]) -> Dict[str, Any]:
    """
    Propagate source-level 95% relative uncertainties via Root Sum of Squares (RSS):
      H_bu = sqrt( sum_i (E_i * u_i / 100)^2 )
    Returns total BU CH4, combined 95% relative uncertainty %, and [CI low, CI high].
    """
    quantified = [
        s for s in sources
        if (getattr(s, "status_flag", "Quantified") or "Quantified") == "Quantified"
        and float(getattr(s, "ch4_tonnes", 0.0) or 0.0) > 0
    ]
    total = sum(float(getattr(s, "ch4_tonnes", 0.0) or 0.0) for s in quantified)
    if total <= 0:
        return {
            "total_tch4": 0.0,
            "uncertainty_pct": 0.0,
            "half_width_tch4": 0.0,
            "ci_low_tch4": 0.0,
            "ci_high_tch4": 0.0,
            "source_count": len(quantified),
        }

    rss_sq, missing = 0.0, 0
    for s in quantified:
        e_i = float(getattr(s, "ch4_tonnes", 0.0) or 0.0)
        raw_u = getattr(s, "uncertainty_pct", None)
        if raw_u is None:  # not recorded: left out of the band and counted, never a level default (F-RPT-06)
            missing += 1 if e_i > 0 else 0
            continue
        rss_sq += (e_i * (float(raw_u) / 100.0)) ** 2

    half_width = math.sqrt(rss_sq)
    rel_pct = (half_width / total) * 100.0
    return {
        "total_tch4": round(total, 4),
        "uncertainty_pct": round(rel_pct, 2),
        "half_width_tch4": round(half_width, 4),
        "ci_low_tch4": round(max(0.0, total - half_width), 4),
        "ci_high_tch4": round(total + half_width, 4),
        "source_count": len(quantified),
        "sources_without_uncertainty": missing,
    }


_T975 = {1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571, 6: 2.447, 7: 2.365, 8: 2.306, 9: 2.262, 10: 2.228,
         11: 2.201, 12: 2.179, 13: 2.160, 14: 2.145, 15: 2.131, 16: 2.120, 17: 2.110, 18: 2.101, 19: 2.093, 20: 2.086,
         21: 2.080, 22: 2.074, 23: 2.069, 24: 2.064, 25: 2.060, 26: 2.056, 27: 2.052, 28: 2.048, 29: 2.045, 30: 2.042}


def _t975(df):
    """Two-sided 95 % Student t quantile (1.96 beyond 30 degrees of freedom, within 4 %)."""
    return _T975.get(int(df), 1.96)


def compute_top_down_rss(measurements: List[Any], option_mode: Optional[str] = None) -> Dict[str, Any]:
    """
    Aggregate site-level measurements across Option 1 (campaign average RSS) and
    Option 2 (independent multi-campaign RSS + inter-campaign sample spread at 95% CI).
    Handles Instantaneous vs Annualized scaling cleanly.
    """
    if not measurements:
        return {
            "total_tch4": 0.0,
            "uncertainty_pct": 0.0,
            "half_width_tch4": 0.0,
            "ci_low_tch4": 0.0,
            "ci_high_tch4": 0.0,
            "measurement_count": 0,
            "measurement_mode": "Annualized",
            "option_mode": option_mode or "Option 1",
        }

    modes = [(getattr(m, "measurement_mode", None) or "Annualized") for m in measurements]
    opts = [(getattr(m, "option_mode", None) or "Option 1") for m in measurements]
    effective_opt = option_mode or ("Option 2" if "Option 2" in opts else opts[0])
    effective_mode = "Instantaneous" if all(m == "Instantaneous" for m in modes) else (
        "Mixed" if len(set(modes)) > 1 else modes[0]
    )

    annual_vals: List[float] = []
    half_widths: List[float] = []
    for m in measurements:
        rate = float(getattr(m, "measured_rate_kg_hr", 0.0) or 0.0)
        hrs = float(getattr(m, "operating_hours_year", 8760.0) or 8760.0)
        ann = getattr(m, "annualized_tch4", None)
        val = float(ann) if (ann is not None and float(ann) > 0) else (rate * hrs / 1000.0)
        u_pct = getattr(m, "uncertainty_pct", None)
        u = float(u_pct) if u_pct is not None else 0.0  # required at entry; legacy rows without one have no band
        annual_vals.append(val)
        half_widths.append(val * (u / 100.0))

    n = len(annual_vals)
    mean_td = sum(annual_vals) / n
    if mean_td <= 0:
        return {
            "total_tch4": 0.0,
            "uncertainty_pct": 0.0,
            "half_width_tch4": 0.0,
            "ci_low_tch4": 0.0,
            "ci_high_tch4": 0.0,
            "measurement_count": n,
            "measurement_mode": effective_mode,
            "option_mode": effective_opt,
        }

    # Combine single-campaign uncertainty of mean via RSS
    rss_mean_hw = math.sqrt(sum(hw ** 2 for hw in half_widths)) / n

    # Option 2 incorporates inter-campaign variance: the sample standard error x Student t(0.975, n - 1); z = 1.96 was
    # used whatever the number of campaigns (audit 2026-11 F-GOGMP-08: 2 campaigns need t = 12.706)
    if effective_opt == "Option 2" and n > 1:
        sample_var = sum((x - mean_td) ** 2 for x in annual_vals) / (n - 1)
        inter_hw = _t975(n - 1) * math.sqrt(sample_var / n)
        combined_hw = math.sqrt(rss_mean_hw ** 2 + inter_hw ** 2)
    else:
        combined_hw = rss_mean_hw

    rel_pct = (combined_hw / mean_td) * 100.0
    return {
        "total_tch4": round(mean_td, 4),
        "uncertainty_pct": round(rel_pct, 2),
        "half_width_tch4": round(combined_hw, 4),
        "ci_low_tch4": round(max(0.0, mean_td - combined_hw), 4),
        "ci_high_tch4": round(mean_td + combined_hw, 4),
        "measurement_count": n,
        "measurement_mode": effective_mode,
        "option_mode": effective_opt,
    }


def reconcile_l4_l5(
    sources: List[Any],
    measurements: List[Any],
    *,
    threshold_pct: float = 20.0,
    l4_justification: str = "",
    option_mode: Optional[str] = None,
    pathway_override: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Full UNEP OGMP 2.0 Level 4 / Level 5 reconciliation with:
    - RSS 95% confidence intervals on Bottom-Up & Top-Down
    - CI overlap test + +/- threshold % variance test
    - L4 Materiality check (>=90%, or >=70% with justification + remaining material sources >= L3)
    - Pathway 1 / 2a / 2b / 2c / 2d / 3 classifier
    """
    mat = evaluate_l4_materiality(sources, l4_justification=l4_justification)
    bu = compute_bottom_up_rss(sources)
    td = compute_top_down_rss(measurements, option_mode=option_mode)

    bu_total = bu["total_tch4"]
    td_total = td["total_tch4"]
    thr = float(threshold_pct or 20.0)

    variance_pct: Optional[float] = None
    variance_flag = False
    ci_overlaps = False

    if bu_total > 0 and td_total > 0:
        variance_pct = round(((td_total - bu_total) / bu_total) * 100.0, 2)
        variance_flag = abs(variance_pct) > thr
        ci_overlaps = (bu["ci_high_tch4"] >= td["ci_low_tch4"]) and (td["ci_high_tch4"] >= bu["ci_low_tch4"])

    # Reconciliation & L5 Guidance s3.3.1: reasonable agreement (Pathway 1) = one central estimate inside the other's
    # 95 % band; overlapping bands alone (large uncertainty) are not agreement (Figure 3-5). A discrepancy becomes
    # Pathway 2 only when the operator explains it (an override 2a-2d); unexplained it is Pathway 3 and the asset
    # stays at L4. The +/-20 % variance and "CI overlap" rules are not in the Guidance (audit 2026-11 F-RPT-02 / -03).
    bu_band_ok = not bu.get("sources_without_uncertainty")  # an incomplete bottom-up band is not used
    # instantaneous snapshots are reconciled per measurement against the L4 estimate at the survey time (Guidance
    # s3.2.1, Checklist 3.4.1), never averaged into an annual figure: no annual agreement is claimed from them
    # (they gave Pathway 1 / Level 5: audit 2026-11 F-GOGMP-03)
    snapshots = td.get("measurement_mode") in ("Instantaneous", "Mixed")
    agreement = not snapshots and bool(bu_total > 0 and td_total > 0 and (
        td["ci_low_tch4"] <= bu_total <= td["ci_high_tch4"]
        or (bu_band_ok and bu["ci_low_tch4"] <= td_total <= bu["ci_high_tch4"])))
    if bu_total <= 0 or td_total <= 0 or not mat["passed"]:
        recommended_pathway = "3"
    elif agreement:
        recommended_pathway = "1"
    else:
        recommended_pathway = "3"  # until the discrepancy is explained (Pathway 2)
    explained = pathway_override in ("2a", "2b", "2c", "2d")
    pathway_code = pathway_override if pathway_override in VALID_PATHWAYS else recommended_pathway
    if pathway_code == "1" and not agreement:
        pathway_code = recommended_pathway  # Pathway 1 cannot be claimed without agreement
    pathway_info = PATHWAY_DEFINITIONS[pathway_code]

    # Determine resulting OGMP facility level (1..5)
    if bu_total <= 0:
        # no source inventory: no source-level level can be assessed (Level 3 was given; F-GOGMP-04)
        resulting_level = _highest_material_bu_level(sources) if sources else None
        reconciliation_status = "No Bottom-Up" if td_total > 0 else "No Activity"
    elif td_total <= 0:
        resulting_level = 4 if mat["passed"] else _highest_material_bu_level(sources)
        reconciliation_status = "No Top-Down"
    elif mat["passed"] and (pathway_code == "1" or (explained and pathway_code.startswith("2"))):
        resulting_level = 5
        reconciliation_status = "Reconciled" if pathway_code == "1" else "Reconciled (discrepancy explained)"
    elif mat["passed"]:
        resulting_level = 4
        reconciliation_status = "Discrepancy Flagged"
    else:
        resulting_level = min(4, max(2, _highest_material_bu_level(sources)))
        reconciliation_status = "Discrepancy Flagged" if variance_flag else "L4 Materiality Incomplete"

    return {
        "reporting_level": resulting_level,
        "reconciliation_status": reconciliation_status,
        "threshold_pct": thr,
        "variance_pct": variance_pct,
        "variance_flag": variance_flag,
        "ci_overlaps": ci_overlaps,
        "pathway_code": pathway_code,
        "recommended_pathway_code": recommended_pathway,
        "pathway_title": pathway_info["title"],
        "pathway_description": pathway_info["description"],
        "bottom_up": bu,
        "top_down": td,
        "materiality": mat,
    }


def _highest_material_bu_level(sources: List[Any]) -> int:
    quantified = [
        s for s in sources
        if (getattr(s, "status_flag", "Quantified") or "Quantified") == "Quantified"
    ]
    total = sum(float(getattr(s, "ch4_tonnes", 0.0) or 0.0) for s in quantified)
    if total <= 0:
        return 2
    by_lvl: Dict[int, float] = {}
    for s in quantified:
        lvl = int(getattr(s, "ogmp_level", 2) or 2)
        by_lvl[lvl] = by_lvl.get(lvl, 0.0) + float(getattr(s, "ch4_tonnes", 0.0) or 0.0)
    # one rule with evaluate_l4_materiality (a 50 % majority gave L4 where the 90 / 70 % rule did not: F-RPT-05):
    # L4 needs >= 90 % of the CH4 at L4; L3 needs every source at L3 or above
    if sum(v for k, v in by_lvl.items() if k >= 4) / total >= 0.90:
        return 4
    if all(k >= 3 for k in by_lvl):
        return 3
    return 2


def compute_portfolio_materiality(
    entities: List[Any],
    facility_ch4_map: Dict[int, float],
) -> Dict[str, Any]:
    """
    UNEP OGMP 2.0 portfolio materiality (Framework s4.5, Checklist 1.4 and the Portfolio Materiality template):
    - a non-operated JV (NOJV) with an equity share below 5 % is immaterial;
    - the other assets are ranked by their *absolute* CH4 emissions (no equity weighting); those up to a cumulative
      95 % of the absolute emissions are material, the rest may be excluded.
    The equity-weighted CH4 and a NOJV test on its share of the portfolio's equity CH4 were used (audit 2026-11
    F-RPT-01). Equity CH4 is kept in the rows for information.
    """
    rows = []
    for ent in entities:
        fid = getattr(ent, "facility_id", None)
        fac_ch4 = float(facility_ch4_map.get(fid, 0.0) if fid else 0.0)
        raw_wi = getattr(ent, "working_interest_pct", None)
        wi = float(raw_wi) if raw_wi is not None else 100.0
        op_st = (getattr(ent, "operator_status", "operated") or "operated").lower()
        rows.append((ent, fac_ch4, wi, fac_ch4 * (wi / 100.0), op_st))

    total_abs = sum(r[1] for r in rows)
    total_eq = sum(r[3] for r in rows)
    immaterial_nojv = {id(r[0]) for r in rows if r[4] != "operated" and r[2] < 5.0}
    ranked = sorted((r for r in rows if id(r[0]) not in immaterial_nojv), key=lambda r: r[1], reverse=True)
    ranked_total = sum(r[1] for r in ranked)
    material, cum = set(), 0.0
    for r in ranked:
        before = (cum / ranked_total * 100.0) if ranked_total > 0 else 0.0
        if before < 95.0:
            material.add(id(r[0]))
        cum += r[1]

    enriched, nojv_exclusions, member_reported_nojvs = [], [], []
    included_abs = excluded_abs = included_eq = excluded_eq = 0.0
    for ent, fac_ch4, wi, eq_ch4, op_st in rows:
        is_excluded = bool(getattr(ent, "is_nojv_material_excluded", False))
        is_member_reported = bool(getattr(ent, "is_member_reported_nojv", False))
        eligible = id(ent) in immaterial_nojv or id(ent) not in material
        exclusion_valid = (not is_excluded) or eligible
        if is_excluded and exclusion_valid:
            excluded_abs, excluded_eq = excluded_abs + fac_ch4, excluded_eq + eq_ch4
        else:
            included_eq += eq_ch4
            if id(ent) not in immaterial_nojv:
                included_abs += fac_ch4
        item = {
            "id": getattr(ent, "id", None),
            "facility_id": getattr(ent, "facility_id", None),
            "entity_name": getattr(ent, "entity_name", ""),
            "asset_name": getattr(ent, "asset_name", "") or getattr(ent, "entity_name", ""),
            "segment": getattr(ent, "segment", "Upstream"),
            "country": getattr(ent, "country", "") or "",
            "operator_status": op_st,
            "operating_company": getattr(ent, "operating_company", "") or "",
            "working_interest_pct": round(wi, 2),
            "facility_ch4_tch4": round(fac_ch4, 4),
            "equity_ch4_tch4": round(eq_ch4, 4),
            "portfolio_equity_share_pct": round((eq_ch4 / total_eq) * 100.0, 2) if total_eq > 0 else 0.0,
            "absolute_share_pct": round((fac_ch4 / total_abs) * 100.0, 2) if total_abs > 0 else 0.0,
            "material": id(ent) in material,
            "immaterial_nojv_below_5pct_equity": id(ent) in immaterial_nojv,
            "eligible_below_5pct_exclusion": eligible,
            "is_nojv_material_excluded": is_excluded,
            "exclusion_valid": exclusion_valid,
            "exclusion_reason": getattr(ent, "exclusion_reason", "") or "",
            "is_member_reported_nojv": is_member_reported,
        }
        enriched.append(item)
        if is_excluded:
            nojv_exclusions.append(item)
        if is_member_reported:
            member_reported_nojvs.append(item)

    # coverage of the assets that are not immaterial NOJVs (those are out of the portfolio test by definition)
    included_pct = round((included_abs / ranked_total) * 100.0, 2) if ranked_total > 0 else 100.0
    return {
        "total_equity_ch4_tch4": round(total_eq, 4),
        "included_equity_ch4_tch4": round(included_eq, 4),
        "excluded_equity_ch4_tch4": round(excluded_eq, 4),
        "total_absolute_ch4_tch4": round(total_abs, 4),
        "included_coverage_pct": included_pct,
        "meets_95pct_threshold": (included_pct >= 95.0) or (len(enriched) == 0),
        "nojv_exclusion_count": len(nojv_exclusions),
        "nojv_exclusions": nojv_exclusions,
        "member_reported_nojv_count": len(member_reported_nojvs),
        "member_reported_nojvs": member_reported_nojvs,
        "entities": enriched,
    }


def build_default_implementation_plan(
    facility_id: int,
    asset_name: str,
    operator_status: str = "operated",
    base_year: int = 2023,
) -> List[Dict[str, Any]]:
    """
    Generate standard Y0-Y10 UNEP OGMP 2.0 Implementation Plan rows:
    - Operated assets hit Level 4/5 by Y3 (3-year deadline)
    - Non-operated JV assets hit Level 4/5 by Y5 (5-year deadline)
    """
    op_st = (operator_status or "operated").lower()
    gold_offset = 3 if op_st == "operated" else 5
    rows = []
    for yr_offset in range(0, 11):
        if yr_offset == 0:
            lvl, scope, meth = 2, "Initial Venture Inventory", "Generic EFs & asset screening"
        elif yr_offset < gold_offset:
            lvl = 3 if yr_offset == 1 else (4 if op_st == "operated" else 3)
            scope = "Material Sources (>=90% CH4)" if lvl >= 4 else "Equipment & Component Grouping"
            meth = "API Compendium L3 + initial OGI/Hi-Flow pilots" if lvl == 3 else "Direct source measurement & calibration"
        elif yr_offset == gold_offset:
            lvl, scope, meth = 5, "Full Asset Gold Standard", "L4 Source Inventory + L5 Site-Level RSS 95% CI Reconciliation"
        else:
            lvl, scope, meth = 5, "Sustained Gold Standard", "Annual multi-campaign Option 2 verification & continuous sensors"
        rows.append({
            "facility_id": facility_id,
            "asset_name": asset_name,
            "operator_status": op_st,
            "base_year": base_year,
            "milestone_horizon": f"Y{yr_offset}",
            "planned_year": base_year + yr_offset,
            "target_level": lvl,
            "source_scope": scope,
            "methodology_upgrade": meth,
            "milestone_status": "Planned",
        })
    return rows
