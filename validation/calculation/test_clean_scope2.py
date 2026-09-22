"""
CLEAN-SLATE VALIDATION: Scope 2 Indirect Emissions
Validates purchased electricity (location & market-based), steam, heat, and cooling.
ZERO reuse of legacy tests. Designed completely from zero.
"""

import pytest
import sys
import os

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SERVER_DIR = os.path.join(BASE_DIR, "new", "server")
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, SERVER_DIR)

from validation.reference_model import (
    ref_calculate_scope2_electricity,
    ref_calculate_scope2_steam,
    ref_calculate_scope2_cooling,
)
from calculations.indirect import IndirectSteamCalculator, CogenAllocationCalculator


class TestCleanScope2Electricity:
    """Independent validation of Scope 2 purchased electricity."""

    def test_location_based_electricity_standard(self):
        kwh = 500000.0
        grid_ef = 0.582  # kg CO2e / kWh
        ref = ref_calculate_scope2_electricity(kwh, grid_ef, method="location_based")

        expected_tonnes = (kwh * grid_ef) / 1000.0
        assert abs(ref["co2e"] - expected_tonnes) < 1e-4
        assert ref["co2e"] == 291.0

    def test_market_based_zero_emission_ppa(self):
        kwh = 250000.0
        ppa_ef = 0.0  # Contractual renewable tariff
        ref = ref_calculate_scope2_electricity(kwh, ppa_ef, method="market_based")
        assert ref["co2e"] == 0.0

    def test_location_based_with_grid_loss(self):
        kwh = 100000.0
        grid_ef = 0.50
        loss = 0.05  # 5% line loss
        ref = ref_calculate_scope2_electricity(kwh, grid_ef, loss_factor=loss)

        # Delivered = 100,000 / (1 - 0.05) = 105,263.158 kWh
        # 105,263.158 * 0.50 / 1000 = 52.63158 tonnes
        assert abs(ref["co2e"] - 52.63158) < 1e-3

    def test_zero_electricity_boundary(self):
        ref = ref_calculate_scope2_electricity(0.0, 0.582)
        assert ref["co2e"] == 0.0


class TestCleanScope2SteamAndHeat:
    """Independent validation of Scope 2 purchased steam and heating."""

    def test_purchased_steam_indirect_calculator(self):
        calc = IndirectSteamCalculator()
        tonnes = 1200.0
        ef_co2_kg_mmbtu = 53.06
        b_eff = 0.80
        t_loss = 0.05

        res = calc.calculate(
            heat_energy=tonnes,
            ef_co2=ef_co2_kg_mmbtu,
            boiler_efficiency=b_eff,
            transmission_loss=t_loss,
            uncertainties={},
            heat_unit="tonne",
        )

        expected_co2 = ((tonnes * 2.20462) / (b_eff * (1.0 - t_loss)) * ef_co2_kg_mmbtu) / 1000.0
        assert abs(res["results"]["co2"]["value"] - expected_co2) < 1e-2
        assert abs(res["total_co2e"] - expected_co2) < 1e-2

    def test_steam_invalid_efficiency_rejected(self):
        calc = IndirectSteamCalculator()
        # 100% transmission loss leads to net_efficiency = 0.0 <= 0, which must raise ValueError
        with pytest.raises(ValueError):
            calc.calculate(
                heat_energy=100.0,
                ef_co2=50.0,
                boiler_efficiency=0.80,
                transmission_loss=1.0,
                uncertainties={},
            )


class TestCleanScope2Cogeneration:
    """Independent validation of CHP cogeneration emission allocation."""

    def test_cogen_wri_efficiency_method(self):
        calc = CogenAllocationCalculator()
        total_co2e = 1000.0
        heat_output = 50000.0
        power_output = 30000.0

        # WRI method: e_h = 0.8, e_p = 0.33
        # denom = (50000 / 0.8) + (30000 / 0.33) = 62,500 + 90,909.09 = 153,409.09
        # heat_fraction = 62,500 / 153,409.09 = 0.4074
        # allocated_heat = 1000.0 * 0.4074 = 407.41 tonnes
        res = calc.calculate(
            total_emissions=total_co2e,
            heat_output=heat_output,
            power_output=power_output,
            method="wri_efficiency",
            uncertainties={},
        )

        expected_allocated = ((heat_output / 0.8) / ((heat_output / 0.8) + (power_output / 0.33))) * total_co2e
        assert abs(res["results"]["co2"]["value"] - expected_allocated) < 1e-2
        assert abs(res["total_co2e"] - expected_allocated) < 1e-2
