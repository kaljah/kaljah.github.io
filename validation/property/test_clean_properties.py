"""
CLEAN-SLATE VALIDATION: Property-Based Testing (Hypothesis)
Verifies mathematical invariants:
1. Zero Invariance: f(0) = 0
2. Linear Scaling: f(k * x) = k * f(x)
3. Additivity: f(x + y) = f(x) + f(y)
4. Unit Invariance: f(1000 kg) = f(1 tonne)
5. Monotonicity: x1 < x2 => f(x1) <= f(x2)
ZERO reuse of legacy tests. Designed completely from zero.
"""

import pytest
import sys
import os
from hypothesis import given, strategies as st, settings

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SERVER_DIR = os.path.join(BASE_DIR, "new", "server")
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, SERVER_DIR)

from calculations.combustion import CombustionCalculator
from calculations.units import compute_scope3_co2e, calculate_co2e, convert
from validation.reference_model import (
    ref_calculate_combustion,
    ref_calculate_scope2_electricity,
    ref_calculate_scope3,
)


class TestCleanMathematicalProperties:
    """Hypothesis property tests for mathematical invariants."""

    @settings(deadline=None)
    @given(st.floats(min_value=0.0, max_value=0.0))
    def test_zero_property_invariance(self, zero_qty):
        """Zero activity data must strictly produce zero emissions: f(0) = 0."""
        calc = CombustionCalculator()
        res = calc.calculate(
            fuel_quantity=zero_qty,
            ef_co2=1.93,
            ef_ch4=0.0001,
            ef_n2o=0.00003,
            uncertainties={},
            hhv=None,
            ef_unit="kg/m3",
            fuel_unit="m3",
            fuel_type="gases",
        )
        assert res["total_co2e"] == 0.0
        assert res["results"]["co2"]["value"] == 0.0

        ref_s2 = ref_calculate_scope2_electricity(zero_qty, 0.50)
        assert ref_s2["co2e"] == 0.0

        ref_s3 = compute_scope3_co2e(zero_qty, 2.50)
        assert ref_s3 == 0.0

    @settings(max_examples=50, deadline=None)
    @given(
        st.floats(min_value=1.0, max_value=50000.0),
        st.floats(min_value=1.1, max_value=10.0),
    )
    def test_linear_scaling_property(self, qty, multiplier):
        """Linearity: f(k * x) = k * f(x) for linear combustion."""
        calc = CombustionCalculator()
        res1 = calc.calculate(
            fuel_quantity=qty,
            ef_co2=1.93,
            ef_ch4=0.0001,
            ef_n2o=0.00003,
            uncertainties={},
            hhv=None,
            ef_unit="kg/m3",
            fuel_unit="m3",
            fuel_type="gases",
        )
        res_scaled = calc.calculate(
            fuel_quantity=qty * multiplier,
            ef_co2=1.93,
            ef_ch4=0.0001,
            ef_n2o=0.00003,
            uncertainties={},
            hhv=None,
            ef_unit="kg/m3",
            fuel_unit="m3",
            fuel_type="gases",
        )

        expected_total = res1["total_co2e"] * multiplier
        assert abs(res_scaled["total_co2e"] - expected_total) < (expected_total * 1e-4)

    @settings(max_examples=50, deadline=None)
    @given(
        st.floats(min_value=1.0, max_value=25000.0),
        st.floats(min_value=1.0, max_value=25000.0),
    )
    def test_additivity_property(self, qty1, qty2):
        """Additivity: f(x + y) = f(x) + f(y) for non-interacting streams."""
        calc = CombustionCalculator()
        res1 = calc.calculate(
            fuel_quantity=qty1, ef_co2=2.0, ef_ch4=0.0, ef_n2o=0.0,
            uncertainties={}, hhv=None, ef_unit="kg/m3", fuel_unit="m3", fuel_type="gases"
        )
        res2 = calc.calculate(
            fuel_quantity=qty2, ef_co2=2.0, ef_ch4=0.0, ef_n2o=0.0,
            uncertainties={}, hhv=None, ef_unit="kg/m3", fuel_unit="m3", fuel_type="gases"
        )
        res_sum = calc.calculate(
            fuel_quantity=qty1 + qty2, ef_co2=2.0, ef_ch4=0.0, ef_n2o=0.0,
            uncertainties={}, hhv=None, ef_unit="kg/m3", fuel_unit="m3", fuel_type="gases"
        )

        expected_sum = res1["total_co2e"] + res2["total_co2e"]
        assert abs(res_sum["total_co2e"] - expected_sum) < 1e-5

    @settings(max_examples=50, deadline=None)
    @given(
        st.floats(min_value=1.0, max_value=10000.0),
        st.floats(min_value=10000.1, max_value=50000.0),
    )
    def test_monotonicity_property(self, small_qty, large_qty):
        """Monotonicity: For positive emission factor, x1 < x2 => f(x1) < f(x2)."""
        calc = CombustionCalculator()
        res_small = calc.calculate(
            fuel_quantity=small_qty, ef_co2=1.93, ef_ch4=0.0001, ef_n2o=0.00003,
            uncertainties={}, hhv=None, ef_unit="kg/m3", fuel_unit="m3", fuel_type="gases"
        )
        res_large = calc.calculate(
            fuel_quantity=large_qty, ef_co2=1.93, ef_ch4=0.0001, ef_n2o=0.00003,
            uncertainties={}, hhv=None, ef_unit="kg/m3", fuel_unit="m3", fuel_type="gases"
        )
        assert res_small["total_co2e"] < res_large["total_co2e"]

    @settings(max_examples=30, deadline=None)
    @given(st.floats(min_value=1.0, max_value=10000.0))
    def test_unit_invariance_property(self, qty_scf):
        """Physical unit invariance: Equivalent physical volumes must yield identical emissions."""
        # qty in scf converted to m3
        qty_m3 = convert(qty_scf, "scf", "m3")

        calc = CombustionCalculator()
        # Using equivalent factors in kg/scf vs kg/m3
        ef_kg_m3 = 2.0
        ef_kg_scf = ef_kg_m3 * 0.028316846592

        res_scf = calc.calculate(
            fuel_quantity=qty_scf, ef_co2=ef_kg_scf, ef_ch4=0.0, ef_n2o=0.0,
            uncertainties={}, hhv=None, ef_unit="kg/scf", fuel_unit="scf", fuel_type="gases"
        )
        res_m3 = calc.calculate(
            fuel_quantity=qty_m3, ef_co2=ef_kg_m3, ef_ch4=0.0, ef_n2o=0.0,
            uncertainties={}, hhv=None, ef_unit="kg/m3", fuel_unit="m3", fuel_type="gases"
        )

        assert abs(res_scf["total_co2e"] - res_m3["total_co2e"]) < 1e-4
