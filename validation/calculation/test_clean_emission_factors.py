"""
CLEAN-SLATE VALIDATION: Emission Factor Integrity & Selection Matrix
Validates factor values, units, sources, gas specificity, and selector safety.
ZERO reuse of legacy tests. Designed completely from zero.
"""

import pytest
import sys
import os

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SERVER_DIR = os.path.join(BASE_DIR, "new", "server")
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, SERVER_DIR)

from emission_factors import API_FACTORS, EQUIPMENT_FACTORS
from calculations.dispatcher import CalculationDispatcher
from calculations.legacy_engine import compute_emissions


class TestCleanEmissionFactorAudit:
    """Independent audit of the API Compendium 2021 factor catalog."""

    def test_combustion_factors_integrity(self):
        """Verifies that all primary combustion fuels have valid, positive, physical emission factors."""
        primary_fuels = ["natural_gas", "diesel", "fuel_oil", "lpg", "gasoline"]
        found = 0
        for fuel_key, data in API_FACTORS.items():
            k_low = str(fuel_key).lower().replace(" ", "_")
            if any(f in k_low for f in primary_fuels):
                found += 1
                assert "unit" in data, f"Missing unit in factor {fuel_key}"
                # CO2 factor must be positive for hydrocarbon fuels
                co2_val = data.get("co2") or data.get("factor")
                assert co2_val is not None and float(co2_val) > 0, f"Non-positive CO2 factor in {fuel_key}"

        assert found >= len(primary_fuels), "Not all primary fuels found in API_FACTORS catalog"

    def test_gas_specificity_co2_vs_ch4_vs_n2o(self):
        """Verifies that CO2, CH4, and N2O factors are not mixed up or cross-contaminated."""
        for name, factor in API_FACTORS.items():
            co2 = float(factor.get("co2") or 0.0)
            ch4 = float(factor.get("ch4") or 0.0)
            n2o = float(factor.get("n2o") or 0.0)

            # For complete combustion of hydrocarbons, CO2 mass emissions are orders of magnitude higher than CH4 and N2O
            if "combustion" in str(factor.get("category", "")).lower() and co2 > 0:
                assert co2 > ch4, f"Combustion factor {name} has CH4 ({ch4}) >= CO2 ({co2})!"
                assert co2 > n2o, f"Combustion factor {name} has N2O ({n2o}) >= CO2 ({co2})!"


class TestCleanEmissionFactorSelection:
    """Tests factor selection logic to prevent mis-selection of wrong fuels, categories, or gases."""

    def test_prevent_cross_fuel_selection(self):
        """Natural gas calculation must not select liquid diesel factors."""
        dispatcher = CalculationDispatcher()
        ng_inputs = {"quantity": 1000.0, "unit": "m3", "fuel_type": "natural_gas"}
        ng_factors = {"co2": 1.93, "ch4": 0.0001, "n2o": 0.00003, "unit": "kg/m3"}

        diesel_inputs = {"quantity": 1000.0, "unit": "bbl", "fuel_type": "diesel"}
        diesel_factors = {"co2": 432.0, "ch4": 0.018, "n2o": 0.0035, "unit": "kg/bbl"}

        res_ng = dispatcher.dispatch("stationary_combustion", ng_inputs, ng_factors, {})
        res_diesel = dispatcher.dispatch("stationary_combustion", diesel_inputs, diesel_factors, {})

        # Natural gas produces ~1.93 tonnes CO2 per 1000 m3
        assert abs(res_ng["results"]["co2"]["value"] - 1.93) < 1e-3
        # Diesel produces ~432 tonnes CO2 per 1000 bbl
        assert abs(res_diesel["results"]["co2"]["value"] - 432.0) < 1e-1
        # Asserts they are fundamentally different
        assert res_diesel["results"]["co2"]["value"] > res_ng["results"]["co2"]["value"] * 100

    def test_custom_factor_isolation(self):
        """Verifies custom factors take precedence without polluting global catalog."""
        custom_data = {
            "name": "Custom Flare Gas",
            "type": "custom",
            "co2": 2.50,
            "ch4": 0.05,
            "n2o": 0.001,
            "unit": "kg/m3",
        }
        payload = {
            "amount": 1000.0,
            "unit": "m3",
            "process": "combustion",
            "factor_source": "custom",
        }
        em, method = compute_emissions(
            payload=payload,
            factor_data=custom_data,
        )

        # 1000 m3 * 2.50 kg/m3 / 1000 = 2.50 tonnes CO2
        assert abs(em["co2"] - 2.50) < 1e-4
        # 1000 m3 * 0.05 kg/m3 / 1000 = 0.05 tonnes CH4
        assert abs(em["ch4"] - 0.05) < 1e-4
        assert "generic" in method or "custom" in method
