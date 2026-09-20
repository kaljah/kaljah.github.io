"""
Boundary Conditions, Resilience, and Negative Test Suite.
=========================================================
Rigorous edge-case and boundary verification:
1. Negative numbers rejection.
2. NaN / Infinity injection handling.
3. Null, empty string, and missing key validation.
4. Non-numeric string payload injection.
5. Extreme magnitude handling (1e-12 to 1e12).
6. Thermodynamic boundary conditions.
"""
import pytest
import math
import sys
from pathlib import Path

repo_root = str(Path(__file__).resolve().parents[3])
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

from calculations.dispatcher import CalculationDispatcher
from calculations.constants import GWP_AR5
from calculations.units import normalize_gas_volume_to_standard


@pytest.fixture(scope="module")
def dispatcher():
    return CalculationDispatcher()


class TestNegativeValuesRejection:
    """Verifies that negative inputs cannot produce physical emissions or corrupt balances."""

    def test_negative_quantity_combustion(self, dispatcher):
        payload = {"quantity": -500.0, "unit": "m3", "fuel_type": "natural_gas", "hhv": 1020.0}
        ef = {"co2": 53.06, "ch4": 0.001, "n2o": 0.0001, "unit": "kg/MMBtu"}
        with pytest.raises(ValueError, match=r"negative"):
            dispatcher.dispatch("stationary_combustion", payload, ef, {}, gwp_dict=GWP_AR5)

    def test_negative_amount_flaring(self, dispatcher):
        payload = {"amount": -1000.0, "unit": "m3", "factor_source": "specific", "c1": 0.88}
        with pytest.raises(ValueError, match=r"negative"):
            dispatcher.dispatch("flaring", payload, {}, {}, gwp_dict=GWP_AR5)


class TestNaNAndInfinityHandling:
    """Verifies rejection of IEEE 754 NaN, +Inf, -Inf."""

    @pytest.mark.parametrize("bad_val", [float("nan"), float("inf"), float("-inf")])
    def test_nan_inf_activity_rejection(self, dispatcher, bad_val):
        payload = {"quantity": bad_val, "unit": "m3", "fuel_type": "natural_gas", "hhv": 1020.0}
        ef = {"co2": 53.06, "ch4": 0.001, "n2o": 0.0001, "unit": "kg/MMBtu"}
        with pytest.raises(ValueError, match=r"NaN|Infinite"):
            dispatcher.dispatch("stationary_combustion", payload, ef, {}, gwp_dict=GWP_AR5)


class TestMissingAndEmptyInputs:
    """Verifies graceful and explicit validation of missing and empty fields."""

    @pytest.mark.parametrize("empty_val", [None, "", "-", " "])
    def test_tier3_missing_c1_rejected(self, dispatcher, empty_val):
        payload = {
            "quantity": 1000.0,
            "unit": "m3",
            "factor_source": "specific",
            "specific_factors": True,
            "c1": empty_val,
        }
        with pytest.raises(ValueError):
            dispatcher.dispatch("stationary_combustion", payload, {}, {}, gwp_dict=GWP_AR5)

    def test_non_numeric_string_quantity_rejected(self, dispatcher):
        payload = {"quantity": "invalid_number", "unit": "m3", "fuel_type": "natural_gas"}
        with pytest.raises(ValueError, match=r"Invalid numeric"):
            dispatcher.dispatch("stationary_combustion", payload, {}, {}, gwp_dict=GWP_AR5)


class TestExtremeMagnitudesAndThermodynamicBoundaries:
    """Verifies calculation stability under micro and macro numerical regimes."""

    def test_ultra_small_quantity(self, dispatcher):
        qty = 1e-12
        payload = {"quantity": qty, "unit": "m3", "fuel_type": "natural_gas", "hhv": 1020.0}
        ef = {"co2": 53.06, "ch4": 0.001, "n2o": 0.0001, "unit": "kg/MMBtu"}
        res = dispatcher.dispatch("stationary_combustion", payload, ef, {}, gwp_dict=GWP_AR5)
        assert res["total_co2e"] >= 0.0
        assert not math.isnan(res["total_co2e"])
        assert not math.isinf(res["total_co2e"])

    def test_ultra_large_quantity(self, dispatcher):
        qty = 1e9
        payload = {"quantity": qty, "unit": "m3", "fuel_type": "natural_gas", "hhv": 1020.0}
        ef = {"co2": 53.06, "ch4": 0.001, "n2o": 0.0001, "unit": "kg/MMBtu"}
        res = dispatcher.dispatch("stationary_combustion", payload, ef, {}, gwp_dict=GWP_AR5)
        assert res["total_co2e"] > 0.0
        assert not math.isinf(res["total_co2e"])

    def test_high_pressure_normalization(self):
        norm = normalize_gas_volume_to_standard(
            volume=1000.0,
            operating_temp=25.0,
            temp_unit="C",
            operating_press=5000.0,
            press_unit="psig",
            z_factor=1.05,
        )
        assert norm > 1000.0
        assert not math.isnan(norm)
        assert not math.isinf(norm)
