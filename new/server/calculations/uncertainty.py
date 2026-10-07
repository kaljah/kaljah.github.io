"""
GHG Inventory Uncertainty Quantification Module
================================================
Compliant with:
  - ISO 14064-1:2018 §7.5 (Uncertainty quantification and aggregation)
  - IPCC 2006 GL Vol.1 §3.3 (Error propagation, SRSS Approach 1)
  - ISO/IEC Guide 98-3 (GUM) §6.2 (Coverage factor k=2 for 95% CI)
  - API Compendium 2021 §2.4 (Uncertainty ranges by source type)
  - OGMP 2.0 Framework §5 (Tier-specific uncertainty requirements)

Method:
  E = Activity × Emission_Factor
  u_E = √(u_AD² + u_EF²)      [SRSS for product — IPCC Eq. 3.1]
  U95 = k × u_E  where k = 2  [95% CI — GUM §6.2, coverage factor]

Activity-data uncertainty is tier-specific per IPCC GL Vol.1 Table 3.1:
  Tier 1 (allocation/default):        ±10–15%
  Tier 2 (regional/custom factors):   ±7%
  Tier 3 (calibrated meters/CEMS):    ±2%
  Fugitive/vented (physical meas.):   ±20%
"""

import math

# ---------------------------------------------------------------------------
# TIER CONSTANTS
# ---------------------------------------------------------------------------


class Tier:
    """Calculation tier following IPCC 2006 GL Vol.1 §2.4 hierarchy."""

    T1 = 1  # Default / tabulated EFs (least accurate)
    T2 = 2  # Country/region-specific or custom EFs
    T3 = 3  # Site-measured, CEMS, mass balance (most accurate)


# Activity-data uncertainty by tier — IPCC GL Vol.1 Table 3.1
ACTIVITY_UNCERTAINTY = {
    Tier.T1: 0.10,  # ±10% — metering without calibration, allocation methods
    Tier.T2: 0.07,  # ±7%  — regional data, estimated throughput
    Tier.T3: 0.02,  # ±2%  — calibrated CEMS / Coriolis meters
}

# Supplemental activity uncertainty for processes dominated by physical variance
ACTIVITY_UNCERTAINTY_FUGITIVE = 0.20  # ±20%  — equipment leak frequency / count
ACTIVITY_UNCERTAINTY_VENTED = 0.15  # ±15%  — vent volume measurement

# GUM coverage factor for 95% confidence interval (two-sided, ~normal distribution)
# ISO/IEC Guide 98-3 §6.2
COVERAGE_FACTOR_95 = 2.0

# Per-GHG EF uncertainty defaults when no measured value is available
# Values align with API Compendium 2021 §2.4 and IPCC 2006 GL Vol.1 Annex 3A
DEFAULT_EF_UNCERTAINTY = {
    # Combustion sources — well-characterised stoichiometry
    "combustion": {
        "co2": {"T1": 0.05, "T2": 0.03, "T3": 0.02},  # ±2–5%
        "ch4": {"T1": 0.15, "T2": 0.10, "T3": 0.05},  # ±5–15%
        "n2o": {"T1": 0.20, "T2": 0.15, "T3": 0.10},  # ±10–20%
    },
    # Flaring — combustion efficiency variation is primary driver
    "flaring": {
        "co2": {"T1": 0.10, "T2": 0.07, "T3": 0.05},  # ±5–10%
        "ch4": {"T1": 0.25, "T2": 0.20, "T3": 0.10},  # ±10–25% (destruction eff.)
        "n2o": {"T1": 0.50, "T2": 0.40, "T3": 0.30},  # ±30–50% (poorly constrained)
    },
    # Fugitive — high inherent variability in leak rates
    "fugitive": {
        "co2": {"T1": 0.30, "T2": 0.20, "T3": 0.10},
        "ch4": {"T1": 0.60, "T2": 0.40, "T3": 0.20},
        "n2o": {"T1": 0.50, "T2": 0.35, "T3": 0.20},
    },
    # Vented / pneumatics / blowdowns
    "vented": {
        "co2": {"T1": 0.20, "T2": 0.15, "T3": 0.07},
        "ch4": {"T1": 0.40, "T2": 0.25, "T3": 0.10},
        "n2o": {"T1": 0.50, "T2": 0.40, "T3": 0.25},
    },
    # Midstream (AGR, dehydrator)
    "midstream": {
        "co2": {"T1": 0.10, "T2": 0.07, "T3": 0.03},
        "ch4": {"T1": 0.25, "T2": 0.15, "T3": 0.07},
        "n2o": {"T1": 0.50, "T2": 0.40, "T3": 0.20},
    },
    # Indirect (Steam, Cogen, Electricity)
    "indirect": {
        "co2": {"T1": 0.10, "T2": 0.05, "T3": 0.02},
        "ch4": {"T1": 0.20, "T2": 0.10, "T3": 0.05},
        "n2o": {"T1": 0.25, "T2": 0.15, "T3": 0.08},
    },
    # Stoichiometric (Chemical reactions, sulfur recovery)
    "stoichiometric": {
        "co2": {"T1": 0.05, "T2": 0.03, "T3": 0.01},
        "ch4": {"T1": 0.10, "T2": 0.05, "T3": 0.02},
        "n2o": {"T1": 0.15, "T2": 0.10, "T3": 0.05},
    },
}

# Process-to-source-category mapping for looking up defaults above
PROCESS_CATEGORY = {
    "combustion": "combustion",
    "stationary_combustion": "combustion",
    "mobile": "combustion",
    "mobile_combustion": "combustion",
    "flaring": "flaring",
    "flare": "flaring",
    "fugitive": "fugitive",
    "fugitive_component": "fugitive",
    "equipment_fugitive": "fugitive",
    "compressor_fugitive": "fugitive",
    "compressor_seal": "fugitive",
    "wellhead_fugitive": "fugitive",
    "separator_fugitive": "fugitive",
    "venting": "vented",
    "associated_gas_venting": "vented",
    "associated_venting": "vented",
    "associated_gas": "vented",
    "blowdown": "vented",
    "completions": "vented",
    "completion_flowback": "vented",
    "drilling": "vented",
    "mud_degassing": "vented",
    "unloading": "vented",
    "liquids_unloading": "vented",
    "tank": "vented",
    "tank_flashing": "vented",
    "tank_working": "vented",
    "tank_breathing": "vented",
    "storage_tanks": "vented",
    "pneumatic": "vented",
    "pneumatic_device": "vented",
    "pneumatic_devices": "vented",
    "agr": "midstream",
    "acid_gas_removal": "midstream",
    "dehydrator": "midstream",
    "gathering_boosting": "fugitive",
    "gas_processing": "fugitive",
    "transmission_storage": "fugitive",
    "refinery_fugitive": "fugitive",
    "distribution_fugitive": "fugitive",
    "lng_operations": "fugitive",
    "indirect": "indirect",
    "indirect_steam": "indirect",
    "steam": "indirect",
    "cogen": "indirect",
    "cogen_allocation": "indirect",
    "scope2": "indirect",
    "stoichiometric": "stoichiometric",
    "stoichiometry": "stoichiometric",
    "chemical_production": "stoichiometric",
    "nitric_acid_production": "stoichiometric",
    "adipic_acid_production": "stoichiometric",
    "fccu": "combustion",
}

# ---------------------------------------------------------------------------
# GWP UNCERTAINTIES (IPCC AR5 Chapter 8 / IPCC 2006 GL Vol. 1 §3.3)
# ---------------------------------------------------------------------------
# Relative standard uncertainty (1σ) for 100-year Global Warming Potential metrics
GWP_UNCERTAINTY_1SIGMA = {
    "co2": 0.0,    # Reference gas, identically zero uncertainty by definition
    "ch4": 0.30,   # ±30% standard uncertainty (IPCC AR5 Ch. 8 §8.7 / Table 8.SM.16)
    "n2o": 0.20,   # ±20% standard uncertainty (IPCC AR5 Ch. 8 §8.7 / Table 8.SM.16)
}


def propagate_co2e_uncertainty(
    e_co2,
    u_co2=None,
    e_ch4=0.0,
    u_ch4=None,
    e_n2o=0.0,
    u_n2o=None,
    gwp_dict=None,
    include_gwp_uncertainty=True,
    gwp_uncertainties=None,
):
    """
    Propagates constituent greenhouse gas emissions and uncertainties into total CO2e uncertainty.
    Complies with IPCC AR5 Chapter 8 and IPCC 2006 GL Vol. 1 §3.3 (Taylor series error propagation).

    Formula:
      E_CO2e = E_CO2 + (GWP_CH4 * E_CH4) + (GWP_N2O * E_N2O)
      Var(E_CO2) = (E_CO2 * u_CO2)^2
      Var(E_CH4_CO2e) = (GWP_CH4 * E_CH4)^2 * (u_CH4^2 + u_GWP_CH4^2)   [if include_gwp_uncertainty]
      Var(E_N2O_CO2e) = (GWP_N2O * E_N2O)^2 * (u_N2O^2 + u_GWP_N2O^2)   [if include_gwp_uncertainty]
      sigma_CO2e = sqrt(Var(E_CO2) + Var(E_CH4_CO2e) + Var(E_N2O_CO2e))
      u_CO2e = sigma_CO2e / E_CO2e

    Args:
        e_co2: CO2 emission in physical tonnes (or dict from propagate_uncertainty)
        u_co2: Relative standard uncertainty (1σ, decimal) or None if e_co2 is dict
        e_ch4: CH4 emission in physical tonnes (or dict from propagate_uncertainty)
        u_ch4: Relative standard uncertainty (1σ, decimal) or None if e_ch4 is dict
        e_n2o: N2O emission in physical tonnes (or dict from propagate_uncertainty)
        u_n2o: Relative standard uncertainty (1σ, decimal) or None if e_n2o is dict
        gwp_dict: dict with GWP factors (defaults to AR5: CH4=28, N2O=265)
        include_gwp_uncertainty: bool, whether to include GWP parameter uncertainty
        gwp_uncertainties: optional dict overriding GWP relative 1σ uncertainties

    Returns:
        dict with total_co2e, sigma_co2e, relative_uncertainty_1sigma,
                  relative_uncertainty_95pct, ci_95_abs, lower_bound_95, upper_bound_95
    """
    from .constants import get_active_gwp

    gwps = get_active_gwp(gwp_dict=gwp_dict)
    gwp_ch4 = float(gwps.get("CH4", 28.0))
    gwp_n2o = float(gwps.get("N2O", 265.0))

    val_co2 = float(e_co2["value"] if isinstance(e_co2, dict) else (e_co2 or 0.0))
    unc_co2 = float(
        e_co2.get("relative_uncertainty_1sigma", e_co2.get("uncertainty", 0.0))
        if isinstance(e_co2, dict)
        else (u_co2 or 0.0)
    )

    val_ch4 = float(e_ch4["value"] if isinstance(e_ch4, dict) else (e_ch4 or 0.0))
    unc_ch4 = float(
        e_ch4.get("relative_uncertainty_1sigma", e_ch4.get("uncertainty", 0.0))
        if isinstance(e_ch4, dict)
        else (u_ch4 or 0.0)
    )

    val_n2o = float(e_n2o["value"] if isinstance(e_n2o, dict) else (e_n2o or 0.0))
    unc_n2o = float(
        e_n2o.get("relative_uncertainty_1sigma", e_n2o.get("uncertainty", 0.0))
        if isinstance(e_n2o, dict)
        else (u_n2o or 0.0)
    )

    gwp_uncs = gwp_uncertainties or GWP_UNCERTAINTY_1SIGMA
    u_gwp_ch4 = float(gwp_uncs.get("ch4", 0.30)) if include_gwp_uncertainty else 0.0
    u_gwp_n2o = float(gwp_uncs.get("n2o", 0.20)) if include_gwp_uncertainty else 0.0

    co2e_co2 = val_co2 * 1.0
    co2e_ch4 = val_ch4 * gwp_ch4
    co2e_n2o = val_n2o * gwp_n2o
    total_co2e = co2e_co2 + co2e_ch4 + co2e_n2o

    # Variance contributions per gas
    var_co2 = (val_co2 * unc_co2) ** 2
    var_ch4 = (co2e_ch4 ** 2) * (unc_ch4 ** 2 + u_gwp_ch4 ** 2)
    var_n2o = (co2e_n2o ** 2) * (unc_n2o ** 2 + u_gwp_n2o ** 2)

    total_var = var_co2 + var_ch4 + var_n2o
    sigma_co2e = math.sqrt(total_var)
    abs_total = abs(total_co2e)
    rel_1sigma = (sigma_co2e / abs_total) if abs_total > 1e-12 else 0.0
    ci_95_abs = COVERAGE_FACTOR_95 * sigma_co2e
    rel_95 = COVERAGE_FACTOR_95 * rel_1sigma
    lower_95 = max(0.0, total_co2e - ci_95_abs)
    upper_95 = total_co2e + ci_95_abs

    return {
        "total_co2e": total_co2e,
        "sigma_co2e": sigma_co2e,
        "relative_uncertainty_1sigma": rel_1sigma,
        "relative_uncertainty_95pct": rel_95,
        "ci_95_abs": ci_95_abs,
        "lower_bound_95": lower_95,
        "upper_bound_95": upper_95,
        "coverage_factor": COVERAGE_FACTOR_95,
        "confidence_level_pct": 95,
        "gwp_uncertainty_included": include_gwp_uncertainty,
        "gas_breakdown": {
            "co2": {"co2e": co2e_co2, "sigma": math.sqrt(var_co2), "u_rel": unc_co2},
            "ch4": {
                "co2e": co2e_ch4,
                "sigma": math.sqrt(var_ch4),
                "u_rel": math.sqrt(unc_ch4 ** 2 + u_gwp_ch4 ** 2),
                "u_gwp": u_gwp_ch4,
            },
            "n2o": {
                "co2e": co2e_n2o,
                "sigma": math.sqrt(var_n2o),
                "u_rel": math.sqrt(unc_n2o ** 2 + u_gwp_n2o ** 2),
                "u_gwp": u_gwp_n2o,
            },
        },
    }


# ---------------------------------------------------------------------------
# CORE PROPAGATION FUNCTIONS
# ---------------------------------------------------------------------------


def combine_uncertainties_product(u_ef, u_ad, exact=False):
    """
    Combine relative uncertainties for E = Activity × EF (multiplicative).
    Standard IPCC Eq 3.1: u_E = sqrt(u_AD^2 + u_EF^2).
    If exact=True, includes Goodman (1960) higher-order term sqrt(u_AD^2 + u_EF^2 + u_AD^2*u_EF^2).
    Reference: IPCC 2006 GL Vol.1 §3.3 Eq. 3.1
    Returns: combined relative standard uncertainty (1σ)
    """
    u_ef_f = float(u_ef or 0.0)
    u_ad_f = float(u_ad or 0.0)
    if exact:
        return math.sqrt(u_ef_f**2 + u_ad_f**2 + (u_ef_f**2 * u_ad_f**2))
    return math.sqrt(u_ef_f**2 + u_ad_f**2)


def combine_uncertainties_sum(val1, u1_rel, val2, u2_rel):
    """
    Combine relative uncertainties for E = A + B (additive, independent).
    Formula: u_total = √((E₁·u₁)² + (E₂·u₂)²) / |E₁+E₂|
    Reference: IPCC 2006 GL Vol.1 §3.3 Eq. 3.2
    Returns: combined relative standard uncertainty (1σ)
    """
    u1_abs = abs(val1 * (u1_rel or 0.0))
    u2_abs = abs(val2 * (u2_rel or 0.0))
    total_val = val1 + val2
    if abs(total_val) < 1e-12:
        return 0.0
    u_total_abs = math.sqrt(u1_abs**2 + u2_abs**2)
    return u_total_abs / abs(total_val)


def srss_inventory(source_list):
    """
    Aggregate uncertainty across multiple sources using SRSS Approach 1.
    Formula: U_inv = √(Σ(Eᵢ·uᵢ)²) / |Σ(Eᵢ)|
    Reference: IPCC 2006 GL Vol.1 §3.3 Eq. 3.3

    Args:
        source_list: list of dicts with keys 'value' (tCO2e) and 'relative_uncertainty' (1σ)

    Returns:
        dict with relative_uncertainty_1sigma, relative_uncertainty_95pct, total_value
    """
    if not source_list:
        return {
            "relative_uncertainty_1sigma": 0.0,
            "relative_uncertainty_95pct": 0.0,
            "total_value": 0.0,
        }

    valid_sources = []
    for s in source_list:
        val = float(s.get("value") or 0.0)
        u_rel = s.get("relative_uncertainty")
        if u_rel is None:
            u_rel = s.get("uncertainty") if s.get("uncertainty") is not None else (
                s.get("uncertainty_1sigma") if s.get("uncertainty_1sigma") is not None else 0.05
            )
        u_rel = float(u_rel or 0.0)
        valid_sources.append({"value": val, "relative_uncertainty": u_rel})

    total_value = sum(s["value"] for s in valid_sources)
    abs_total = abs(total_value)
    if abs_total <= 0:
        return {
            "relative_uncertainty_1sigma": 0.0,
            "relative_uncertainty_95pct": 0.0,
            "total_value": 0.0,
        }
    sum_sq = sum(
        (abs(s["value"]) * s["relative_uncertainty"]) ** 2
        for s in valid_sources
    )
    u_1sigma = math.sqrt(sum_sq) / abs_total
    return {
        "relative_uncertainty_1sigma": u_1sigma,
        "relative_uncertainty_95pct": COVERAGE_FACTOR_95 * u_1sigma,
        "total_value": total_value,
    }


def monte_carlo_simulation(
    source_list,
    iterations=10000,
    seed=42,
    confidence_level=0.95,
):
    """
    IPCC 2006 GL Vol.1 §3.4 Approach 2 — Monte Carlo Simulation for GHG Uncertainty Analysis.
    Models each emission source as an independent lognormal random variable:
      ln(X) ~ N(mu, sigma^2)
    where:
      sigma^2 = ln(1 + var / mean^2) = ln(1 + u_rel^2)
      mu = ln(mean^2 / sqrt(var + mean^2))

    Args:
        source_list: list of dicts with 'value' (tCO2e) and 'relative_uncertainty' (1σ, decimal)
        iterations: number of Monte Carlo runs (default: 10,000)
        seed: random seed for reproducibility
        confidence_level: confidence level for bounds (default: 0.95)

    Returns:
        dict containing mean, median, std, ci_lower, ci_upper, relative_uncertainty_95pct, iterations
    """
    import random
    if seed is not None:
        random.seed(seed)

    if not source_list:
        return {
            "mean": 0.0,
            "median": 0.0,
            "std": 0.0,
            "ci_lower": 0.0,
            "ci_upper": 0.0,
            "relative_uncertainty_95pct": 0.0,
            "iterations": iterations,
        }

    params = []
    deterministic_offset = 0.0
    for s in source_list:
        mean_val = float(s.get("value") or 0.0)
        u_rel = s.get("relative_uncertainty")
        if u_rel is None:
            u_rel = s.get("uncertainty") if s.get("uncertainty") is not None else 0.05
        u_rel = max(0.0, float(u_rel or 0.0))

        if mean_val <= 0 or u_rel == 0:
            deterministic_offset += mean_val
        else:
            var = (mean_val * u_rel) ** 2
            sig_sq = math.log(1.0 + (var / (mean_val ** 2)))
            sigma = math.sqrt(sig_sq)
            mu = math.log((mean_val ** 2) / math.sqrt(var + (mean_val ** 2)))
            params.append((mu, sigma))

    if not params:
        return {
            "mean": deterministic_offset,
            "median": deterministic_offset,
            "std": 0.0,
            "ci_lower": deterministic_offset,
            "ci_upper": deterministic_offset,
            "relative_uncertainty_95pct": 0.0,
            "iterations": iterations,
        }

    totals = []
    for _ in range(iterations):
        tot = deterministic_offset
        for mu, sigma in params:
            tot += math.exp(random.gauss(mu, sigma))
        totals.append(tot)

    totals.sort()
    n = len(totals)
    mean_res = sum(totals) / n
    median_res = totals[n // 2]
    var_res = sum((x - mean_res) ** 2 for x in totals) / max(1, n - 1)
    std_res = math.sqrt(var_res)

    alpha = 1.0 - confidence_level
    lower_idx = max(0, int((alpha / 2.0) * n))
    upper_idx = min(n - 1, int((1.0 - alpha / 2.0) * n))
    ci_lower = totals[lower_idx]
    ci_upper = totals[upper_idx]

    half_width = (ci_upper - ci_lower) / 2.0
    u_95_pct = (half_width / abs(mean_res)) * 100.0 if abs(mean_res) > 0 else 0.0

    return {
        "mean": round(mean_res, 4),
        "median": round(median_res, 4),
        "std": round(std_res, 4),
        "ci_lower": round(ci_lower, 4),
        "ci_upper": round(ci_upper, 4),
        "relative_uncertainty_95pct": round(u_95_pct, 2),
        "iterations": iterations,
    }


# ---------------------------------------------------------------------------
# MAIN PROPAGATION FUNCTION
# ---------------------------------------------------------------------------


def propagate_uncertainty(
    value,
    ef_uncertainty,
    activity_uncertainty=None,
    tier=Tier.T1,
    process_category="combustion",
    gas="co2",
    composition_uncertainty=None,
    uncertainties_dict=None,
):
    """
    Propagate uncertainty for a single emission source.
    E = Activity × EF,  u_E = √(u_AD² + u_EF²)

    Compliant with:
      - IPCC 2006 GL Vol.1 §3.3 Eq. 3.1
      - ISO 14064-1:2018 §7.5.2
      - GUM §6.2 (k=2 for 95% CI)

    Args:
        value (float): Calculated emission in tonnes.
        ef_uncertainty (float): Relative EF uncertainty (1σ, e.g. 0.10 = ±10%).
                                Pass 0.0 if the EF is exact (Tier 3 mass balance).
        activity_uncertainty (float|None): Override activity data uncertainty.
                                           If None, derived from tier.
        tier (int): Tier.T1 / Tier.T2 / Tier.T3
        process_category (str): Source category for default lookup.
        gas (str): 'co2' | 'ch4' | 'n2o' — used for lower-bound clamping logic.

    Returns:
        dict with:
          value                 — point estimate (tonnes)
          ef_uncertainty_1sigma — EF component (1σ, relative)
          ad_uncertainty_1sigma — Activity-data component (1σ, relative)
          relative_uncertainty  — Combined standard uncertainty u_E (1σ, relative)
          absolute_uncertainty  — u_E in absolute units (tonnes) at 1σ
          ci_95_abs             — Expanded uncertainty at 95% CI (k=2)
          lower_bound_95        — value − ci_95_abs  (clamped ≥ 0)
          upper_bound_95        — value + ci_95_abs
          lower_bound           — alias for lower_bound_95 (backward-compat.)
          upper_bound           — alias for upper_bound_95
          tier                  — tier used
          coverage_factor       — k value (2)
          confidence_level_pct  — 95
    """
    if uncertainties_dict:
        if activity_uncertainty is None:
            activity_uncertainty = uncertainties_dict.get("_activity_uncertainty")
        if composition_uncertainty is None:
            composition_uncertainty = uncertainties_dict.get("_composition_uncertainty")

    # --- Resolve activity uncertainty from tier if not explicitly provided ---
    if activity_uncertainty is None:
        resolved_cat = PROCESS_CATEGORY.get(str(process_category).lower(), process_category)
        if resolved_cat == "fugitive":
            activity_uncertainty = ACTIVITY_UNCERTAINTY_FUGITIVE
        elif resolved_cat == "vented":
            if tier == Tier.T3:
                activity_uncertainty = ACTIVITY_UNCERTAINTY[Tier.T3]
            else:
                activity_uncertainty = ACTIVITY_UNCERTAINTY_VENTED
        else:
            activity_uncertainty = ACTIVITY_UNCERTAINTY.get(
                tier, ACTIVITY_UNCERTAINTY[Tier.T1]
            )

    # --- Cast to float to prevent TypeError if a string or dict was accidentally passed ---
    try:
        ef_float = float(ef_uncertainty) if isinstance(ef_uncertainty, (int, float, str)) else 0.05
    except (ValueError, TypeError):
        ef_float = 0.05

    try:
        act_float = float(activity_uncertainty) if isinstance(activity_uncertainty, (int, float, str)) else 0.05
    except (ValueError, TypeError):
        act_float = 0.05

    # --- Convert 95% CI table inputs to 1-sigma standard uncertainty (GUM §4.3.7) ---
    # Published IPCC / API uncertainty tables report 95% confidence bounds (U95 = k * u, k=2).
    # Converting to standard uncertainty (1σ) ensures rigorous propagation per GUM & IPCC Eq 3.1.
    u_ef_1sigma = ef_float / COVERAGE_FACTOR_95
    u_act_1sigma = act_float / COVERAGE_FACTOR_95
    u_components = [u_ef_1sigma, u_act_1sigma]

    if composition_uncertainty is not None:
        try:
            comp_float = float(composition_uncertainty)
            if comp_float > 0:
                u_components.append(comp_float / COVERAGE_FACTOR_95)
        except (ValueError, TypeError):
            pass

    # --- SRSS combination (relative standard uncertainty, 1σ) ---
    u_combined_1sigma = math.sqrt(sum(u**2 for u in u_components))

    # --- Absolute standard uncertainty (1σ) ---
    abs_unc_1sigma = value * u_combined_1sigma

    # --- Expanded uncertainty at 95% CI (GUM §6.2, k=2) -> exact match with IPCC Eq. 3.1 ---
    ci_95 = COVERAGE_FACTOR_95 * abs_unc_1sigma
    ci_95_pct = COVERAGE_FACTOR_95 * u_combined_1sigma * 100.0

    # --- Non-negative lower bound (physically constrained) ---
    # Emissions cannot be negative; lognormal tails don't cross zero.
    # ISO 14064-1 §7.5.2 note: report asymmetric intervals if physically required.
    lower_95 = max(0.0, value - ci_95)
    upper_95 = value + ci_95

    return {
        # Core values
        "value": value,
        # Component uncertainties (1σ, relative)
        "ef_uncertainty_1sigma": u_ef_1sigma,
        "ad_uncertainty_1sigma": u_act_1sigma,
        "comp_uncertainty_1sigma": (
            (float(composition_uncertainty) / COVERAGE_FACTOR_95) if composition_uncertainty else 0.0
        ),
        # Combined standard uncertainty (1σ)
        "relative_uncertainty_1sigma": u_combined_1sigma,
        "relative_uncertainty": u_combined_1sigma,
        "uncertainty": u_combined_1sigma,  # Alias for backend DB saver
        "absolute_uncertainty": abs_unc_1sigma,
        # Expanded 95% CI (k=2, IPCC Approach 1)
        "relative_uncertainty_95pct": ci_95_pct / 100.0,
        "ci_95_abs": ci_95,
        "ci_95_pct": ci_95_pct,
        "lower_bound_95": lower_95,
        "upper_bound_95": upper_95,
        "lower_bound": lower_95,  # Alias for frontend charts
        "upper_bound": upper_95,  # Alias for frontend charts
        # Metadata
        "tier": tier,
        "coverage_factor": COVERAGE_FACTOR_95,
        "confidence_level_pct": 95,
    }


# ---------------------------------------------------------------------------
# HELPER: resolve tier from factor_source string
# ---------------------------------------------------------------------------


def resolve_tier(factor_source: str) -> int:
    """
    Map factor_source string to a Tier integer.
    factor_source values: 'default' | 'custom' | 'specific' | 'site_specific'
    """
    if not factor_source:
        return Tier.T1
    fs = str(factor_source).lower().strip()
    if fs in [
        "specific",
        "site_specific",
        "site-specific",
        "engineering",
        "cems",
        "tier3",
        "tier_3",
        "t3",
    ]:
        return Tier.T3
    if fs in [
        "custom",
        "regional",
        "tier2",
        "tier_2",
        "t2",
        "tier2_plus",
        "tier_2_plus",
        "tier2+",
        "tier_2+",
    ]:
        return Tier.T2
    return Tier.T1  # 'default' or unknown → Tier 1


def resolve_ef_uncertainty(
    process_type: str, gas: str, tier: int, measured_u: float = None
) -> float:
    """
    Return the EF uncertainty for a given process, gas, and tier.
    If the user has supplied a measured uncertainty (measured_u), use that.
    Otherwise fall back to the normative table above.

    Args:
        process_type: e.g. 'combustion', 'flaring'
        gas: 'co2' | 'ch4' | 'n2o'
        tier: Tier.T1 / T2 / T3
        measured_u: float in [0,1] or None

    Returns:
        Relative EF uncertainty (decimal, 1σ)
    """
    if measured_u is not None and float(measured_u) > 0:
        return float(measured_u)

    proc_key = str(process_type or "").lower().strip()
    category = PROCESS_CATEGORY.get(proc_key)
    gas_lu = str(gas).lower()
    tier_key = {Tier.T1: "T1", Tier.T2: "T2", Tier.T3: "T3"}.get(tier, "T1")

    if not category:
        # For unclassified processes, avoid deceptively narrow combustion bounds; default to 15%
        return 0.15

    try:
        return DEFAULT_EF_UNCERTAINTY[category][gas_lu][tier_key]
    except KeyError:
        # Safe fallback — 15% is a conservative universal default
        return 0.15
