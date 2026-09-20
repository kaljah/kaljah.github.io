"""
Property-Based Invariant Verification Suite (Hypothesis).
========================================================
Validates fundamental mathematical invariants across the calculation engine:
1. Linearity: E(k * X) == k * E(X)
2. Additivity: E(A + B) == E(A) + E(B)
3. Monotonicity: A > B ==> E(A) >= E(B)
4. Non-negativity: X >= 0 ==> E(X) >= 0
5. Zero activity: X == 0 ==> E(0) == 0
6. GWP sensitivity order: AR5(CH4) > AR6(CH4) > AR4(CH4)
"""
import pytest
import math
import sys
from pathlib import Path
from hypothesis import given, settings, strategies as st

repo_root = str(Path(__file__).resolve().parents[3])
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

from calculations.dispatcher import CalculationDispatcher
from calculations.constants import GWP_AR4, GWP_AR5, GWP_AR6
from calculations.units import compute_scope3_co2e, calculate_co2e


@pytest.fixture(scope="module")
def dispatcher():
    return CalculationDispatcher()


class TestPropertyInvariantsHypothesis:
    """Hypothesis-driven property invariance tests."""

    @settings(max_examples=50, deadline=None)
    @given(
        qty=st.floats(min_value=1.0, max_value=1_000_000.0, allow_nan=False, allow_infinity=False),
        k=st.floats(min_value=0.1, max_value=10.0, allow_nan=False, allow_infinity=False),
    )
    def test_combustion_linearity(self, dispatcher, qty, k):
        """E(k * X) == k * E(X) for stationary combustion."""
        ef = {"co2": 53.06, "ch4": 0.001, "n2o": 0.0001, "unit": "kg/MMBtu"}
        p1 = {"quantity": qty, "unit": "m3", "fuel_type": "natural_gas", "hhv": 1020.0, "factor_source": "default"}
        p2 = {"quantity": qty * k, "unit": "m3", "fuel_type": "natural_gas", "hhv": 1020.0, "factor_source": "default"}

        r1 = dispatcher.dispatch("stationary_combustion", p1, ef, {}, gwp_dict=GWP_AR5)
        r2 = dispatcher.dispatch("stationary_combustion", p2, ef, {}, gwp_dict=GWP_AR5)

        e1 = r1["total_co2e"]
        e2 = r2["total_co2e"]

        assert pytest.approx(e2, rel=1e-5) == k * e1

    @settings(max_examples=50, deadline=None)
    @given(
        q1=st.floats(min_value=10.0, max_value=500_000.0, allow_nan=False, allow_infinity=False),
        q2=st.floats(min_value=10.0, max_value=500_000.0, allow_nan=False, allow_infinity=False),
    )
    def test_combustion_additivity(self, dispatcher, q1, q2):
        """E(A + B) == E(A) + E(B) for stationary combustion."""
        ef = {"co2": 53.06, "ch4": 0.001, "n2o": 0.0001, "unit": "kg/MMBtu"}
        p1 = {"quantity": q1, "unit": "m3", "fuel_type": "natural_gas", "hhv": 1020.0, "factor_source": "default"}
        p2 = {"quantity": q2, "unit": "m3", "fuel_type": "natural_gas", "hhv": 1020.0, "factor_source": "default"}
        p_sum = {"quantity": q1 + q2, "unit": "m3", "fuel_type": "natural_gas", "hhv": 1020.0, "factor_source": "default"}

        r1 = dispatcher.dispatch("stationary_combustion", p1, ef, {}, gwp_dict=GWP_AR5)
        r2 = dispatcher.dispatch("stationary_combustion", p2, ef, {}, gwp_dict=GWP_AR5)
        r_sum = dispatcher.dispatch("stationary_combustion", p_sum, ef, {}, gwp_dict=GWP_AR5)

        assert pytest.approx(r_sum["total_co2e"], rel=1e-5) == (r1["total_co2e"] + r2["total_co2e"])

    @settings(max_examples=50, deadline=None)
    @given(
        q1=st.floats(min_value=10.0, max_value=100_000.0, allow_nan=False, allow_infinity=False),
        delta=st.floats(min_value=1.0, max_value=10_000.0, allow_nan=False, allow_infinity=False),
    )
    def test_monotonicity(self, dispatcher, q1, delta):
        """A > B ==> E(A) >= E(B)."""
        ef = {"co2": 53.06, "ch4": 0.001, "n2o": 0.0001, "unit": "kg/MMBtu"}
        p_small = {"quantity": q1, "unit": "m3", "fuel_type": "natural_gas", "hhv": 1020.0, "factor_source": "default"}
        p_large = {"quantity": q1 + delta, "unit": "m3", "fuel_type": "natural_gas", "hhv": 1020.0, "factor_source": "default"}

        r_small = dispatcher.dispatch("stationary_combustion", p_small, ef, {}, gwp_dict=GWP_AR5)
        r_large = dispatcher.dispatch("stationary_combustion", p_large, ef, {}, gwp_dict=GWP_AR5)

        assert r_large["total_co2e"] > r_small["total_co2e"]

    @settings(max_examples=30, deadline=None)
    @given(
        qty=st.floats(min_value=0.0, max_value=1_000_000.0, allow_nan=False, allow_infinity=False),
    )
    def test_non_negativity(self, dispatcher, qty):
        """X >= 0 ==> E(X) >= 0 across all gases."""
        ef = {"co2": 53.06, "ch4": 0.001, "n2o": 0.0001, "unit": "kg/MMBtu"}
        p = {"quantity": qty, "unit": "m3", "fuel_type": "natural_gas", "hhv": 1020.0, "factor_source": "default"}

        r = dispatcher.dispatch("stationary_combustion", p, ef, {}, gwp_dict=GWP_AR5)

        assert r["results"]["co2"]["value"] >= 0.0
        assert r["results"]["ch4"]["value"] >= 0.0
        assert r["results"]["n2o"]["value"] >= 0.0
        assert r["total_co2e"] >= 0.0

    def test_zero_activity_yields_zero_emissions(self, dispatcher):
        """E(0) == 0."""
        ef = {"co2": 53.06, "ch4": 0.001, "n2o": 0.0001, "unit": "kg/MMBtu"}
        p = {"quantity": 0.0, "unit": "m3", "fuel_type": "natural_gas", "hhv": 1020.0, "factor_source": "default"}

        r = dispatcher.dispatch("stationary_combustion", p, ef, {}, gwp_dict=GWP_AR5)

        assert r["results"]["co2"]["value"] == 0.0
        assert r["results"]["ch4"]["value"] == 0.0
        assert r["results"]["n2o"]["value"] == 0.0
        assert r["total_co2e"] == 0.0

    @settings(max_examples=30, deadline=None)
    @given(
        ch4_t=st.floats(min_value=1.0, max_value=500.0, allow_nan=False, allow_infinity=False),
    )
    def test_gwp_ordering_invariant(self, ch4_t):
        """GWP AR5 (28) > GWP AR6 (27.9) > GWP AR4 (25) for methane."""
        co2e_ar4 = calculate_co2e(0.0, ch4_t, 0.0, gwp_dict=GWP_AR4)
        co2e_ar5 = calculate_co2e(0.0, ch4_t, 0.0, gwp_dict=GWP_AR5)
        co2e_ar6 = calculate_co2e(0.0, ch4_t, 0.0, gwp_dict=GWP_AR6)

        assert co2e_ar5 > co2e_ar6 > co2e_ar4
