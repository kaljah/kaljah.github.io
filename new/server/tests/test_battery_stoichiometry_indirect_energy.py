"""
Battery 2: Stoichiometry & Indirect Energy Allocation Test Suite.
================================================================
Verifies mass-balance carbon stoichiometry and Scope 2 energy allocation:
1. Stoichiometric Mass Balance (API §4.1: CO2 = Mass * Carbon * 44.01/12.011 across all mass units).
2. Indirect Steam/Heat (API §8.1: Multiplicative net efficiency, 11 energy/steam units, net efficiency zero/negative trap).
3. Cogeneration Allocation (API §8.3: WRI efficiency method, energy content method, strict emissions conservation).
"""
import pytest
import sys
from pathlib import Path

repo_root = str(Path(__file__).resolve().parents[3])
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

from calculations.stoichiometry import StoichiometricCalculator
from calculations.indirect import IndirectSteamCalculator, CogenAllocationCalculator
from calculations.constants import GWP_AR5
from validation.reference_model.midstream import IndependentStoichiometryModel
from validation.reference_model.scope2 import IndependentScope2Model


def _val(x):
    if isinstance(x, dict):
        return x.get("value", 0.0)
    return float(x or 0.0)


class TestStoichiometricMassBalanceBattery:
    """Verifies API §4.1 stoichiometric carbon mass balance calculations."""

    @pytest.mark.parametrize("fuel_mass, mass_unit, carbon_content", [
        (1000.0, "kg", 0.85),
        (2204.62, "lb", 0.85),
        (5.0, "tonne", 0.90),
        (10.0, "short_ton", 0.82),
        (10.0, "long_ton", 0.82),
        (500000.0, "g", 0.75),
    ])
    def test_stoichiometric_units_and_factors(self, fuel_mass, mass_unit, carbon_content):
        calc = StoichiometricCalculator()
        res = calc.calculate(
            fuel_mass=fuel_mass,
            carbon_content=carbon_content,
            uncertainties={},
            mass_unit=mass_unit,
            gwp_dict=GWP_AR5,
        )
        ref = IndependentStoichiometryModel.calculate(
            fuel_mass=fuel_mass,
            mass_unit=mass_unit,
            carbon_content=carbon_content,
            gwp_standard="AR5",
        )

        assert pytest.approx(_val(res["results"]["co2"]), rel=1e-4) == ref["co2"]
        assert pytest.approx(res["total_co2e"], rel=1e-4) == ref["co2e"]

    def test_pure_carbon_theoretical_maximum(self):
        """1 metric tonne of 100% pure carbon produces exactly 44.01/12.011 = ~3.66414 tonnes CO2."""
        calc = StoichiometricCalculator()
        res = calc.calculate(fuel_mass=1.0, carbon_content=1.0, uncertainties={}, mass_unit="tonne", gwp_dict=GWP_AR5)
        expected_ratio = 44.01 / 12.011
        assert pytest.approx(_val(res["results"]["co2"]), rel=1e-4) == expected_ratio


class TestIndirectSteamHeatBattery:
    """Verifies API §8.1 indirect steam/heat with multiplicative efficiency."""

    @pytest.mark.parametrize("energy_val, unit", [
        (100000000.0, "btu"),
        (100.0, "mmbtu"),
        (29307.1, "kwh"),
        (29.307, "mwh"),
        (105.5, "gj"),
        (105505.6, "mj"),
        (1000.0, "therm"),
        (50.0, "ton"),
        (45.359, "tonne"),
        (100.0, "klb"),
        (100000.0, "lb"),
    ])
    def test_steam_energy_units_conversion(self, energy_val, unit):
        calc = IndirectSteamCalculator()
        b_eff = 0.82
        t_loss = 0.05
        ef_co2 = 53.06  # kg/MMBtu

        res = calc.calculate(
            heat_energy=energy_val,
            ef_co2=ef_co2,
            boiler_efficiency=b_eff,
            transmission_loss=t_loss,
            uncertainties={},
            heat_unit=unit,
        )
        ref = IndependentScope2Model.calculate_indirect_steam(
            amount=energy_val,
            unit=unit,
            boiler_eff=b_eff,
            trans_loss=t_loss,
            ef_co2=ef_co2,
        )

        assert pytest.approx(_val(res["results"]["co2"]), rel=1e-3) == ref["co2"]
        assert pytest.approx(res["total_co2e"], rel=1e-3) == ref["co2e"]

    def test_invalid_net_efficiency_trapping(self):
        """When net efficiency <= 0 (e.g. 100% transmission loss or zero boiler efficiency), must raise ValueError."""
        calc = IndirectSteamCalculator()
        with pytest.raises(ValueError, match=r"Net efficiency must be greater than 0"):
            calc.calculate(
                heat_energy=100.0,
                ef_co2=53.06,
                boiler_efficiency=0.80,
                transmission_loss=1.0,  # 100% loss -> net eff = 0
                uncertainties={},
            )


class TestCogenAllocationBattery:
    """Verifies API §8.3 Cogeneration (CHP) emission allocation."""

    def test_wri_efficiency_method_allocation(self):
        calc = CogenAllocationCalculator()
        total_emissions = 15000.0  # tonnes CO2
        heat_output_mmbtu = 40000.0
        power_output_mmbtu = 20000.0

        res = calc.calculate(
            total_emissions=total_emissions,
            heat_output=heat_output_mmbtu,
            power_output=power_output_mmbtu,
            method="wri_efficiency",
        )
        ref = IndependentScope2Model.calculate_cogen_allocation(
            total_emissions=total_emissions,
            heat_output=heat_output_mmbtu,
            power_output=power_output_mmbtu,
            method="wri_efficiency",
        )

        heat_tonnes = res["metadata"]["allocated_heat_tonnes"]
        power_tonnes = res["metadata"]["allocated_power_tonnes"]

        assert pytest.approx(heat_tonnes, rel=1e-5) == ref["allocated_heat_co2e"]
        assert pytest.approx(power_tonnes, rel=1e-5) == ref["allocated_power_co2e"]

        # Mass conservation: Heat + Power MUST equal Total Emissions exactly
        assert pytest.approx(heat_tonnes + power_tonnes, rel=1e-6) == total_emissions

    def test_energy_content_method_allocation(self):
        calc = CogenAllocationCalculator()
        total_emissions = 8000.0
        heat_output = 3000.0
        power_output = 1000.0

        res = calc.calculate(
            total_emissions=total_emissions,
            heat_output=heat_output,
            power_output=power_output,
            method="energy_content",
        )
        ref = IndependentScope2Model.calculate_cogen_allocation(
            total_emissions=total_emissions,
            heat_output=heat_output,
            power_output=power_output,
            method="energy_content",
        )

        heat_tonnes = res["metadata"]["allocated_heat_tonnes"]
        power_tonnes = res["metadata"]["allocated_power_tonnes"]

        assert pytest.approx(heat_tonnes, rel=1e-5) == ref["allocated_heat_co2e"]
        assert pytest.approx(power_tonnes, rel=1e-5) == ref["allocated_power_co2e"]
        # Heat is 3/4 (6000), Power is 1/4 (2000)
        assert pytest.approx(heat_tonnes, rel=1e-5) == 6000.0
        assert pytest.approx(power_tonnes, rel=1e-5) == 2000.0
        assert pytest.approx(heat_tonnes + power_tonnes, rel=1e-6) == total_emissions
