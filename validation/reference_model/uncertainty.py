"""
Independent Uncertainty Quantification & Propagation Model.
Source of Truth: IPCC 2006 GL Vol. 1 §3.3 (Eq. 3.1, 3.2, 3.3), ISO 14064-1 §7.5, ISO/IEC Guide 98-3 (GUM) §6.2.
Zero production dependencies.
"""
import math

COVERAGE_FACTOR_95 = 2.0


class IndependentUncertaintyModel:
    @staticmethod
    def combine_product(u_ad, u_ef):
        """IPCC 2006 Eq. 3.1: u_E = sqrt(u_AD^2 + u_EF^2)"""
        ad = float(u_ad or 0.0)
        ef = float(u_ef or 0.0)
        return math.sqrt(ad**2 + ef**2)

    @staticmethod
    def combine_sum(source_list):
        """IPCC 2006 Eq. 3.2 / 3.3: u_total = sqrt(sum((E_i * u_i)^2)) / sum(E_i)"""
        if not source_list:
            return 0.0
        total_val = sum(float(s.get("value", 0.0)) for s in source_list if float(s.get("value", 0.0)) > 0)
        if total_val <= 0:
            return 0.0
        sum_sq = sum(
            (float(s.get("value", 0.0)) * float(s.get("uncertainty", 0.0))) ** 2
            for s in source_list
            if float(s.get("value", 0.0)) > 0
        )
        return math.sqrt(sum_sq) / total_val

    @staticmethod
    def propagate(value, ef_uncertainty, activity_uncertainty=0.10, coverage_factor=COVERAGE_FACTOR_95, input_is_95pct=True):
        """Propagates uncertainties per IPCC 2006 Eq 3.1 & GUM §6.2.
        
        If input_is_95pct is True (standard IPCC approach where published table values are 95% CI half-widths):
        - 1-sigma components = input / coverage_factor (k=2)
        - relative_uncertainty_1sigma = sqrt(u_ef_1sigma^2 + u_ad_1sigma^2)
        - relative_uncertainty_95pct = relative_uncertainty_1sigma * coverage_factor = sqrt(ef^2 + ad^2)
        - ci_95_abs = value * relative_uncertainty_95pct
        """
        val = float(value or 0.0)
        ef_val = float(ef_uncertainty or 0.0)
        ad_val = float(activity_uncertainty or 0.0)

        if input_is_95pct:
            u_ef_1sigma = ef_val / coverage_factor
            u_ad_1sigma = ad_val / coverage_factor
            u_rel_1sigma = math.sqrt(u_ef_1sigma**2 + u_ad_1sigma**2)
            ci_95_rel = u_rel_1sigma * coverage_factor
        else:
            u_rel_1sigma = math.sqrt(ef_val**2 + ad_val**2)
            ci_95_rel = u_rel_1sigma * coverage_factor

        abs_1sigma = val * u_rel_1sigma
        ci_95_abs = val * ci_95_rel
        lower = max(0.0, val - ci_95_abs)
        upper = val + ci_95_abs

        return {
            "value": val,
            "relative_uncertainty_1sigma": u_rel_1sigma,
            "relative_uncertainty_95pct": ci_95_rel,
            "absolute_uncertainty_1sigma": abs_1sigma,
            "ci_95_abs": ci_95_abs,
            "lower_bound_95": lower,
            "upper_bound_95": upper,
            "coverage_factor": coverage_factor,
        }
