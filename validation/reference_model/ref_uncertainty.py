"""
INDEPENDENT REFERENCE MODEL: Analytical Uncertainty Propagation
First-principles implementation - ZERO production code imports.
Governing equations:
- ISO/IEC Guide 98-3 (GUM: Guide to the Expression of Uncertainty in Measurement)
- IPCC 2006 Guidelines for National GHG Inventories, Vol 1, Chapter 3 (Uncertainties)
"""

import math


def ref_propagate_product_uncertainty(
    emission_value,
    activity_uncertainty=0.05,  # 1-sigma relative uncertainty (e.g. 5%)
    ef_uncertainty=0.10,        # 1-sigma relative uncertainty (e.g. 10%)
):
    """
    Gaussian error propagation for product Y = Activity * EF:
    u_rel(Y) = sqrt(u_rel(Act)^2 + u_rel(EF)^2)
    95% CI half-width = 1.96 * u_rel(Y)
    """
    val = float(emission_value or 0.0)
    if val <= 0:
        return {
            "value": 0.0,
            "relative_uncertainty": 0.0,
            "uncertainty_pct": 0.0,
            "ci_lower_95": 0.0,
            "ci_upper_95": 0.0,
        }

    u_act = float(activity_uncertainty or 0.0)
    u_ef = float(ef_uncertainty or 0.0)

    # Combined relative standard uncertainty (1-sigma)
    u_rel = math.sqrt(u_act**2 + u_ef**2)

    # 95% Confidence Interval (Coverage factor k = 1.96)
    half_width = 1.96 * u_rel
    ci_lower = max(0.0, val * (1.0 - half_width))
    ci_upper = val * (1.0 + half_width)

    return {
        "value": val,
        "relative_uncertainty": u_rel,
        "uncertainty_pct": u_rel * 100.0,
        "ci_lower_95": ci_lower,
        "ci_upper_95": ci_upper,
    }


def ref_propagate_sum_uncertainty(components):
    """
    Gaussian propagation for independent sum Z = sum(Y_i):
    u_abs(Z) = sqrt(sum(u_abs(Y_i)^2))
    u_rel(Z) = u_abs(Z) / Z
    """
    total_val = sum(c["value"] for c in components)
    if total_val <= 0:
        return {"total": 0.0, "relative_uncertainty": 0.0, "ci_lower_95": 0.0, "ci_upper_95": 0.0}

    sum_var = sum((c["value"] * c["relative_uncertainty"]) ** 2 for c in components)
    u_abs = math.sqrt(sum_var)
    u_rel = u_abs / total_val

    half_width = 1.96 * u_rel
    ci_lower = max(0.0, total_val * (1.0 - half_width))
    ci_upper = total_val * (1.0 + half_width)

    return {
        "total": total_val,
        "relative_uncertainty": u_rel,
        "uncertainty_pct": u_rel * 100.0,
        "ci_lower_95": ci_lower,
        "ci_upper_95": ci_upper,
    }
