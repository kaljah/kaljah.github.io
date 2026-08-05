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
    Tier.T1: 0.10,   # ±10% — metering without calibration, allocation methods
    Tier.T2: 0.07,   # ±7%  — regional data, estimated throughput
    Tier.T3: 0.02,   # ±2%  — calibrated CEMS / Coriolis meters
}

# Supplemental activity uncertainty for processes dominated by physical variance
ACTIVITY_UNCERTAINTY_FUGITIVE = 0.20   # ±20%  — equipment leak frequency / count
ACTIVITY_UNCERTAINTY_VENTED   = 0.15   # ±15%  — vent volume measurement

# GUM coverage factor for 95% confidence interval (two-sided, ~normal distribution)
# ISO/IEC Guide 98-3 §6.2
COVERAGE_FACTOR_95 = 2.0

# Per-GHG EF uncertainty defaults when no measured value is available
# Values align with API Compendium 2021 §2.4 and IPCC 2006 GL Vol.1 Annex 3A
DEFAULT_EF_UNCERTAINTY = {
    # Combustion sources — well-characterised stoichiometry
    'combustion': {
        'co2': {'T1': 0.05, 'T2': 0.03, 'T3': 0.02},  # ±2–5%
        'ch4': {'T1': 0.15, 'T2': 0.10, 'T3': 0.05},  # ±5–15%
        'n2o': {'T1': 0.20, 'T2': 0.15, 'T3': 0.10},  # ±10–20%
    },
    # Flaring — combustion efficiency variation is primary driver
    'flaring': {
        'co2': {'T1': 0.10, 'T2': 0.07, 'T3': 0.05},  # ±5–10%
        'ch4': {'T1': 0.25, 'T2': 0.20, 'T3': 0.10},  # ±10–25% (destruction eff.)
        'n2o': {'T1': 0.50, 'T2': 0.40, 'T3': 0.30},  # ±30–50% (poorly constrained)
    },
    # Fugitive — high inherent variability in leak rates
    'fugitive': {
        'co2': {'T1': 0.30, 'T2': 0.20, 'T3': 0.10},
        'ch4': {'T1': 0.60, 'T2': 0.40, 'T3': 0.20},
        'n2o': {'T1': 0.50, 'T2': 0.35, 'T3': 0.20},
    },
    # Vented / pneumatics / blowdowns
    'vented': {
        'co2': {'T1': 0.20, 'T2': 0.15, 'T3': 0.07},
        'ch4': {'T1': 0.40, 'T2': 0.25, 'T3': 0.10},
        'n2o': {'T1': 0.50, 'T2': 0.40, 'T3': 0.25},
    },
    # Midstream (AGR, dehydrator)
    'midstream': {
        'co2': {'T1': 0.10, 'T2': 0.07, 'T3': 0.03},
        'ch4': {'T1': 0.25, 'T2': 0.15, 'T3': 0.07},
        'n2o': {'T1': 0.50, 'T2': 0.40, 'T3': 0.20},
    },
}

# Process-to-source-category mapping for looking up defaults above
PROCESS_CATEGORY = {
    'combustion':          'combustion',
    'stationary_combustion': 'combustion',
    'mobile':              'combustion',
    'flaring':             'flaring',
    'fugitive':            'fugitive',
    'fugitive_component':  'fugitive',
    'equipment_fugitive':  'fugitive',
    'compressor_fugitive': 'fugitive',
    'venting':             'vented',
    'blowdown':            'vented',
    'completions':         'vented',
    'drilling':            'vented',
    'unloading':           'vented',
    'tank':                'vented',
    'tank_flashing':       'vented',
    'tank_working':        'vented',
    'tank_breathing':      'vented',
    'pneumatic':           'vented',
    'pneumatic_devices':   'vented',
    'agr':                 'midstream',
    'dehydrator':          'midstream',
}

# ---------------------------------------------------------------------------
# CORE PROPAGATION FUNCTIONS
# ---------------------------------------------------------------------------

def combine_uncertainties_product(u_ef, u_ad):
    """
    Combine relative uncertainties for E = Activity × EF (multiplicative).
    Formula: u_E = √(u_AD² + u_EF²)
    Reference: IPCC 2006 GL Vol.1 §3.3 Eq. 3.1
    Returns: combined relative standard uncertainty (1σ)
    """
    return math.sqrt(u_ef ** 2 + u_ad ** 2)


def combine_uncertainties_sum(val1, u1_rel, val2, u2_rel):
    """
    Combine relative uncertainties for E = A + B (additive, independent).
    Formula: u_total = √((E₁·u₁)² + (E₂·u₂)²) / (E₁+E₂)
    Reference: IPCC 2006 GL Vol.1 §3.3 Eq. 3.2
    Returns: combined relative standard uncertainty (1σ)
    """
    u1_abs = val1 * u1_rel
    u2_abs = val2 * u2_rel
    total_val = val1 + val2
    if total_val == 0:
        return 0.0
    u_total_abs = math.sqrt(u1_abs ** 2 + u2_abs ** 2)
    return u_total_abs / total_val


def srss_inventory(source_list):
    """
    Aggregate uncertainty across multiple sources using SRSS Approach 1.
    Formula: U_inv = √(Σ(Eᵢ·uᵢ)²) / Σ(Eᵢ)
    Reference: IPCC 2006 GL Vol.1 §3.3 Eq. 3.3
    
    Args:
        source_list: list of dicts with keys 'value' (tCO2e) and 'relative_uncertainty' (1σ)
    
    Returns:
        dict with relative_uncertainty_1sigma, relative_uncertainty_95pct, total_value
    """
    total_value = sum(s['value'] for s in source_list if s['value'] > 0)
    if total_value == 0:
        return {'relative_uncertainty_1sigma': 0.0,
                'relative_uncertainty_95pct': 0.0,
                'total_value': 0.0}
    sum_sq = sum((s['value'] * s['relative_uncertainty']) ** 2 for s in source_list)
    u_1sigma = math.sqrt(sum_sq) / total_value
    return {
        'relative_uncertainty_1sigma': u_1sigma,
        'relative_uncertainty_95pct': COVERAGE_FACTOR_95 * u_1sigma,
        'total_value': total_value
    }


# ---------------------------------------------------------------------------
# MAIN PROPAGATION FUNCTION
# ---------------------------------------------------------------------------

def propagate_uncertainty(
    value,
    ef_uncertainty,
    activity_uncertainty=None,
    tier=Tier.T1,
    process_category='combustion',
    gas='co2',
    composition_uncertainty=None,
    uncertainties_dict=None
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
            activity_uncertainty = uncertainties_dict.get('_activity_uncertainty')
        if composition_uncertainty is None:
            composition_uncertainty = uncertainties_dict.get('_composition_uncertainty')

    # --- Resolve activity uncertainty from tier if not explicitly provided ---
    if activity_uncertainty is None:
        if process_category in ('fugitive', 'fugitive_component', 'equipment_fugitive',
                                'compressor_fugitive'):
            activity_uncertainty = ACTIVITY_UNCERTAINTY_FUGITIVE
        elif process_category in ('vented', 'venting', 'blowdown', 'completions',
                                  'drilling', 'unloading', 'tank', 'tank_flashing',
                                  'tank_working', 'tank_breathing', 'pneumatic',
                                  'pneumatic_devices'):
            if tier == Tier.T3:
                activity_uncertainty = ACTIVITY_UNCERTAINTY[Tier.T3]
            else:
                activity_uncertainty = ACTIVITY_UNCERTAINTY_VENTED
        else:
            activity_uncertainty = ACTIVITY_UNCERTAINTY.get(tier, ACTIVITY_UNCERTAINTY[Tier.T1])

    # --- SRSS combination (relative standard uncertainty, 1σ) ---
    u_components = [ef_uncertainty, activity_uncertainty]
    if composition_uncertainty is not None and float(composition_uncertainty) > 0:
        u_components.append(float(composition_uncertainty))
    
    u_combined_1sigma = math.sqrt(sum(u ** 2 for u in u_components))

    # --- Absolute values ---
    abs_unc_1sigma = value * u_combined_1sigma

    # --- Expanded uncertainty at 95% CI (GUM §6.2, k=2) ---
    ci_95 = COVERAGE_FACTOR_95 * abs_unc_1sigma
    ci_95_pct = COVERAGE_FACTOR_95 * u_combined_1sigma * 100.0

    # --- Non-negative lower bound (physically constrained) ---
    # Emissions cannot be negative; lognormal tails don't cross zero.
    # ISO 14064-1 §7.5.2 note: report asymmetric intervals if physically required.
    lower_95 = max(0.0, value - ci_95)
    upper_95 = value + ci_95

    return {
        # Core values
        "value":                  value,
        # Component uncertainties (1σ, relative)
        "ef_uncertainty_1sigma":  ef_uncertainty,
        "ad_uncertainty_1sigma":  activity_uncertainty,
        "comp_uncertainty_1sigma": float(composition_uncertainty) if composition_uncertainty else 0.0,
        # Combined standard uncertainty (1σ)
        "relative_uncertainty":   u_combined_1sigma,
        "uncertainty":            u_combined_1sigma,  # Alias for backend DB saver
        "absolute_uncertainty":   abs_unc_1sigma,
        # Expanded 95% CI (k=2)
        "ci_95_abs":              ci_95,
        "ci_95_pct":              ci_95_pct,
        "lower_bound_95":         lower_95,
        "upper_bound_95":         upper_95,
        "lower_bound":            lower_95,           # Alias for frontend charts
        "upper_bound":            upper_95,           # Alias for frontend charts
        # Metadata
        "tier":                   tier,
        "coverage_factor":        COVERAGE_FACTOR_95,
        "confidence_level_pct":   95
    }


# ---------------------------------------------------------------------------
# HELPER: resolve tier from factor_source string
# ---------------------------------------------------------------------------

def resolve_tier(factor_source: str) -> int:
    """
    Map factor_source string to a Tier integer.
    factor_source values: 'default' | 'custom' | 'specific'
    """
    if not factor_source:
        return Tier.T1
    fs = str(factor_source).lower().strip()
    if fs == 'specific':
        return Tier.T3
    if fs == 'custom':
        return Tier.T2
    return Tier.T1  # 'default' or unknown → Tier 1


def resolve_ef_uncertainty(process_type: str, gas: str, tier: int,
                            measured_u: float = None) -> float:
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

    category = PROCESS_CATEGORY.get(str(process_type).lower(), 'combustion')
    gas_lu = str(gas).lower()
    tier_key = {Tier.T1: 'T1', Tier.T2: 'T2', Tier.T3: 'T3'}.get(tier, 'T1')
    try:
        return DEFAULT_EF_UNCERTAINTY[category][gas_lu][tier_key]
    except KeyError:
        # Safe fallback — 15% is a conservative universal default
        return 0.15
