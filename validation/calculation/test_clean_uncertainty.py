"""
CLEAN-SLATE VALIDATION: Analytical Uncertainty Propagation
Validates Tier 1/2/3 uncertainty resolution, Gaussian error propagation, and 95% CI bounds.
ZERO reuse of legacy tests. Designed completely from zero.
"""

import pytest
import sys
import os
import math

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SERVER_DIR = os.path.join(BASE_DIR, "new", "server")
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, SERVER_DIR)

from calculations.uncertainty import (
    propagate_uncertainty,
    resolve_tier,
    resolve_ef_uncertainty,
    Tier,
)
from validation.reference_model import (
    ref_propagate_product_uncertainty,
    ref_propagate_sum_uncertainty,
)


class TestCleanUncertainty:
    """Independent validation of analytical uncertainty calculations."""

    def test_tier_resolution_logic(self):
        assert resolve_tier("default") == Tier.T1
        assert resolve_tier("custom") == Tier.T2
        assert resolve_tier("specific") == Tier.T3
        assert resolve_tier("site_specific") == Tier.T3
        assert resolve_tier("engineering") == Tier.T3
        assert resolve_tier("cems") == Tier.T3

    def test_analytical_gaussian_propagation(self):
        val = 100.0
        u_act = 0.05   # 5%
        u_ef = 0.10    # 10%

        # Combined relative uncertainty: sqrt(0.05^2 + 0.10^2) = sqrt(0.0125) = 0.111803 (11.18%)
        ref = ref_propagate_product_uncertainty(val, u_act, u_ef)
        expected_u_rel = math.sqrt(0.05**2 + 0.10**2)
        assert abs(ref["relative_uncertainty"] - expected_u_rel) < 1e-6
        assert abs(ref["uncertainty_pct"] - 11.1803) < 1e-3

        # Bounds at 95% CI (k=1.96): 100 * (1 - 1.96*0.1118) = 78.087, 100 * (1 + 1.96*0.1118) = 121.913
        assert abs(ref["ci_lower_95"] - (100.0 * (1.0 - 1.96 * expected_u_rel))) < 1e-4
        assert abs(ref["ci_upper_95"] - (100.0 * (1.0 + 1.96 * expected_u_rel))) < 1e-4

    def test_non_negative_lower_bound(self):
        """Even with extreme relative uncertainty (e.g. 150%), lower bound must be clipped at 0.0."""
        ref = ref_propagate_product_uncertainty(50.0, 1.0, 1.0)
        # 1.96 * sqrt(2) = 2.77 > 1.0 -> raw lower bound would be negative
        assert ref["ci_lower_95"] == 0.0
        assert ref["ci_upper_95"] > 50.0

    def test_production_propagate_uncertainty_structure(self):
        val = 500.0
        res = propagate_uncertainty(val, ef_uncertainty=0.08, activity_uncertainty=0.04)
        assert res["value"] == 500.0
        assert "uncertainty" in res or "abs_uncertainty" in res
        assert res["lower_bound"] >= 0.0
        assert res["upper_bound"] > val

    def test_sum_propagation_independent_sources(self):
        c1 = {"value": 100.0, "relative_uncertainty": 0.05}
        c2 = {"value": 200.0, "relative_uncertainty": 0.10}
        ref_sum = ref_propagate_sum_uncertainty([c1, c2])

        # var1 = (100 * 0.05)^2 = 25
        # var2 = (200 * 0.10)^2 = 400
        # total_abs_u = sqrt(425) = 20.6155
        # total_rel_u = 20.6155 / 300 = 0.068718 (6.87%)
        assert ref_sum["total"] == 300.0
        assert abs(ref_sum["relative_uncertainty"] - (math.sqrt(425) / 300.0)) < 1e-6
