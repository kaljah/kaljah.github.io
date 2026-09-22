"""
CLEAN-SLATE VALIDATION: Chemical Stoichiometry & Carbon Mass Balance
Validates molecular weights, carbon fractions, and reaction yields.
ZERO reuse of legacy tests. Designed completely from zero.
"""

import pytest
import sys
import os

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SERVER_DIR = os.path.join(BASE_DIR, "new", "server")
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, SERVER_DIR)

from validation.reference_model import ref_calculate_hydrocarbon_stoichiometry
from calculations.stoichiometry import StoichiometricCalculator


class TestCleanStoichiometry:
    """Independent validation of combustion stoichiometry."""

    @pytest.mark.parametrize(
        "name,n,m",
        [
            ("Methane", 1, 4),
            ("Ethane", 2, 6),
            ("Propane", 3, 8),
            ("Butane", 4, 10),
            ("Pentane", 5, 12),
            ("Hexane", 6, 14),
        ]
    )
    def test_hydrocarbon_mass_balance_closure(self, name, n, m):
        """Validates that conservation of mass strictly holds (zero balance error)."""
        ref = ref_calculate_hydrocarbon_stoichiometry(n, m)
        assert ref["mass_balance_error"] < 1e-9
        assert 0.70 < ref["carbon_fraction"] < 0.90
        assert ref["kg_co2_per_kg_fuel"] > 2.5

    def test_production_stoichiometric_calculator_vs_reference(self):
        calc = StoichiometricCalculator()
        fuel_mass_kg = 1000.0  # 1 tonne of pure methane
        n, m = 1, 4
        ref_stoich = ref_calculate_hydrocarbon_stoichiometry(n, m)
        carbon_content = ref_stoich["carbon_fraction"]  # 12.011 / 16.043 = 0.748675

        res = calc.calculate(
            fuel_mass=fuel_mass_kg,
            carbon_content=carbon_content,
            uncertainties={},
            mass_unit="kg",
        )

        # Expected CO2: 1000 * 0.748675 * (44.01 / 12.011) / 1000 = 2.7432 tonnes CO2
        expected_co2 = (fuel_mass_kg * carbon_content * (44.01 / 12.011)) / 1000.0
        assert abs(res["results"]["co2"]["value"] - expected_co2) < 1e-4
        assert abs(res["total_co2e"] - expected_co2) < 1e-4

    def test_stoichiometric_mass_unit_conversions(self):
        calc = StoichiometricCalculator()
        carbon_content = 0.85

        # 1 metric tonne = 1000 kg
        res_t = calc.calculate(1.0, carbon_content, uncertainties={}, mass_unit="tonne")
        # 1000 kg
        res_kg = calc.calculate(1000.0, carbon_content, uncertainties={}, mass_unit="kg")

        assert abs(res_t["total_co2e"] - res_kg["total_co2e"]) < 1e-5
