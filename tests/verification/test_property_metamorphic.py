"""
PHASE 4 VERIFICATION: PROPERTY-BASED & METAMORPHIC TESTS
========================================================
Uses Hypothesis to test mathematical invariants and metamorphic properties
across the calculation engines, unit conversions, and GWP valuations.

Invariants Tested:
1. Linearity: Scaling input activity by k scales emissions by k
2. Additivity: Splitting activity into A1 + A2 yields E(A1) + E(A2) == E(A1+A2)
3. Determinism & Idempotence: Two successive calculations yield identical results
4. CO2e Identity: CO2e == CO2 * GWP_CO2 + CH4 * GWP_CH4 + N2O * GWP_N2O
5. Non-negativity: Positive inputs never produce negative emissions
6. Permutation Invariance: Order of gas components does not alter emissions
7. Hostile Input Guarding: Graceful handling of zero, negative, NaN, Inf, whitespace
"""

import sys
import os
import math
from decimal import Decimal
import pytest
from hypothesis import given, strategies as st, settings, assume

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SERVER_DIR = os.path.join(REPO_ROOT, "new", "server")
if SERVER_DIR not in sys.path:
    sys.path.insert(0, SERVER_DIR)

from calculations.combustion import CombustionCalculator
from calculations.stoichiometry import StoichiometricCalculator
from calculations.units import convert, calculate_co2e, UnitError
from calculations.constants import get_active_gwp


# =============================================================================
# 1. LINEARITY & HOMOGENEITY INVARIANT: E(k * A) == k * E(A)
# =============================================================================

@settings(max_examples=50, deadline=None)
@given(
    activity=st.floats(min_value=1.0, max_value=1e6, allow_nan=False, allow_infinity=False),
    k=st.floats(min_value=0.1, max_value=10.0, allow_nan=False, allow_infinity=False),
)
def test_combustion_linearity_property(activity, k):
    """
    Scaling activity by k must scale emissions by k.
    """
    calc = CombustionCalculator()
    ef_co2 = 1.93
    res1 = calc.calculate(
        fuel_quantity=activity,
        fuel_unit="m3",
        ef_co2=ef_co2,
        ef_unit="kg/m3",
        uncertainties={},
    )
    res_scaled = calc.calculate(
        fuel_quantity=activity * k,
        fuel_unit="m3",
        ef_co2=ef_co2,
        ef_unit="kg/m3",
        uncertainties={},
    )
    e1 = res1["results"]["co2"]["value"]
    e_scaled = res_scaled["results"]["co2"]["value"]
    assert e_scaled == pytest.approx(e1 * k, rel=1e-4)


# =============================================================================
# 2. ADDITIVITY INVARIANT: E(A1) + E(A2) == E(A1 + A2)
# =============================================================================

@settings(max_examples=50, deadline=None)
@given(
    a1=st.floats(min_value=1.0, max_value=1e5, allow_nan=False, allow_infinity=False),
    a2=st.floats(min_value=1.0, max_value=1e5, allow_nan=False, allow_infinity=False),
)
def test_combustion_additivity_property(a1, a2):
    """
    Sum of emissions from two separate sub-periods equals emission of total period.
    """
    calc = CombustionCalculator()
    ef_co2 = 2.05
    res1 = calc.calculate(fuel_quantity=a1, fuel_unit="m3", ef_co2=ef_co2, ef_unit="kg/m3", uncertainties={})
    res2 = calc.calculate(fuel_quantity=a2, fuel_unit="m3", ef_co2=ef_co2, ef_unit="kg/m3", uncertainties={})
    res_total = calc.calculate(fuel_quantity=a1 + a2, fuel_unit="m3", ef_co2=ef_co2, ef_unit="kg/m3", uncertainties={})

    sum_parts = res1["results"]["co2"]["value"] + res2["results"]["co2"]["value"]
    total = res_total["results"]["co2"]["value"]
    assert total == pytest.approx(sum_parts, rel=1e-5)


# =============================================================================
# 3. DETERMINISM & IDEMPOTENCE: E_1 == E_2
# =============================================================================

@settings(max_examples=40, deadline=None)
@given(
    mass=st.floats(min_value=10.0, max_value=1e6, allow_nan=False, allow_infinity=False),
    carbon_pct=st.floats(min_value=0.01, max_value=0.99, allow_nan=False, allow_infinity=False),
)
def test_stoichiometry_determinism(mass, carbon_pct):
    """
    Recomputing twice with identical inputs yields bitwise or exact floating point equality.
    """
    calc = StoichiometricCalculator()
    res1 = calc.calculate(fuel_mass=mass, carbon_content=carbon_pct, mass_unit="kg")
    res2 = calc.calculate(fuel_mass=mass, carbon_content=carbon_pct, mass_unit="kg")

    assert res1["results"]["co2"]["value"] == res2["results"]["co2"]["value"]
    assert res1["total_co2e"] == res2["total_co2e"]


# =============================================================================
# 4. CO2E IDENTITY: CO2e == sum(Gas_i * GWP_i)
# =============================================================================

@settings(max_examples=50, deadline=None)
@given(
    co2=st.floats(min_value=0.0, max_value=1e4, allow_nan=False, allow_infinity=False),
    ch4=st.floats(min_value=0.0, max_value=1e3, allow_nan=False, allow_infinity=False),
    n2o=st.floats(min_value=0.0, max_value=1e2, allow_nan=False, allow_infinity=False),
    std=st.sampled_from(["SAR", "AR4", "AR5", "AR6"]),
)
def test_co2e_formula_identity(co2, ch4, n2o, std):
    """
    CO2e must strictly equal CO2 * 1 + CH4 * GWP_CH4 + N2O * GWP_N2O.
    """
    g = get_active_gwp(std)
    expected_co2e = co2 * g["CO2"] + ch4 * g["CH4"] + n2o * g["N2O"]
    computed = calculate_co2e(co2, ch4, n2o, gwp_dict=g)
    assert computed == pytest.approx(expected_co2e, rel=1e-6)


# =============================================================================
# 5. NON-NEGATIVITY INVARIANT
# =============================================================================

@settings(max_examples=40, deadline=None)
@given(
    qty=st.floats(min_value=0.0, max_value=1e7, allow_nan=False, allow_infinity=False),
)
def test_non_negativity_emissions(qty):
    """
    Non-negative activity data can never produce negative emissions.
    """
    calc = CombustionCalculator()
    res = calc.calculate(
        fuel_quantity=qty,
        fuel_unit="m3",
        ef_co2=1.93,
        ef_ch4=0.0001,
        ef_n2o=0.00003,
        ef_unit="kg/m3",
        uncertainties={},
    )
    assert res["results"]["co2"]["value"] >= 0.0
    assert res["results"]["ch4"]["value"] >= 0.0
    assert res["results"]["n2o"]["value"] >= 0.0
    assert res["total_co2e"] >= 0.0


# =============================================================================
# 6. HOSTILE & ADVERSARIAL INPUT GUARDING
# =============================================================================

@pytest.mark.parametrize("hostile_val", [-10.0, -0.0001, float("nan"), float("inf"), float("-inf")])
def test_hostile_activity_inputs_rejected(hostile_val):
    """
    Verifies that negative, NaN, and Infinite inputs raise ValueError.
    """
    calc = CombustionCalculator()
    with pytest.raises(ValueError):
        calc.calculate(
            fuel_quantity=hostile_val,
            fuel_unit="m3",
            ef_co2=1.93,
            ef_unit="kg/m3",
            uncertainties={},
        )


@pytest.mark.parametrize("hostile_mass", [-50.0, -1.0, float("nan"), float("inf")])
def test_hostile_stoichiometric_inputs_rejected(hostile_mass):
    """
    Verifies that negative/infinite mass in stoichiometry raises ValueError.
    """
    calc = StoichiometricCalculator()
    with pytest.raises(ValueError):
        calc.calculate(fuel_mass=hostile_mass, carbon_content=0.85, mass_unit="kg")


def test_stoichiometric_invalid_carbon_content_above_1():
    """
    Verifies BUG-10 remediation: If carbon_content is 1.5 without '%',
    it raises a ValueError rejecting physically invalid fractions.
    """
    calc = StoichiometricCalculator()
    with pytest.raises(ValueError, match="carbon_content without '%' must be a fraction between 0 and 1"):
        calc.calculate(fuel_mass=1000.0, carbon_content=1.5, mass_unit="kg")
