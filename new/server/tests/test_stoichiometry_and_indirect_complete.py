"""Exhaustive test suite for Stoichiometric Mass Balance and Indirect Energy / Cogeneration Calculators.

Covers:
- calculations/stoichiometry.py:
  - mass_to_kg (all mass units, hyphen/space aliases, error cases)
  - StoichiometricCalculator (API Eq 4-3/4-4, stoichiometric ratio 44.01/12.011, carbon contents, oxidation factors)
  - NitricAcidCalculator (API Compendium Table 6-53, nitric acid default 9.0 kg/t, adipic acid default 300 kg/t, abatement)
- calculations/indirect.py:
  - heat_to_mmbtu (energy units, steam mass units with enthalpy, ambiguous unit validation)
  - IndirectSteamCalculator (API Section 8.1.5, boiler efficiency, transmission losses, multi-gas CH4/N2O)
  - CogenAllocationCalculator (API Section 8.3, WRI efficiency vs energy content methods, strict mass conservation)
"""
import pytest
from calculations.stoichiometry import (
    mass_to_kg,
    StoichiometricCalculator,
    NitricAcidCalculator,
)
from calculations.indirect import (
    heat_to_mmbtu,
    IndirectSteamCalculator,
    CogenAllocationCalculator,
)
from calculations.constants import get_active_gwp, GWP_AR5


# ---------------------------------------------------------------------------
# calculations/stoichiometry.py Tests
# ---------------------------------------------------------------------------

def test_mass_to_kg_all_units():
    # SI Units
    assert mass_to_kg(1.0, "kg") == 1.0
    assert mass_to_kg(1000.0, "g") == 1.0
    assert mass_to_kg(1.0, "tonne") == 1000.0
    assert mass_to_kg(1.0, "metric_ton") == 1000.0

    # US Customary / Imperial Units
    assert mass_to_kg(100.0, "lb") == pytest.approx(45.359237)
    assert mass_to_kg(1.0, "short_ton") == pytest.approx(907.18474)
    assert mass_to_kg(1.0, "us_ton") == pytest.approx(907.18474)
    assert mass_to_kg(1.0, "long_ton") == pytest.approx(1016.0469088)

    # Spacing and hyphenation variations
    assert mass_to_kg(2.0, "short ton") == mass_to_kg(2.0, "short_ton")
    assert mass_to_kg(2.0, "Short-Ton") == mass_to_kg(2.0, "short_ton")
    assert mass_to_kg(2.0, "long ton") == mass_to_kg(2.0, "long_ton")


def test_mass_to_kg_unknown_unit_raises():
    with pytest.raises(ValueError) as exc:
        mass_to_kg(100.0, "bushels")
    assert "Unknown mass unit" in str(exc.value)


def test_stoichiometric_calculator_exact_math():
    calc = StoichiometricCalculator()

    # 1000 kg fuel, 85% carbon content, 100% oxidation
    # Expected CO2 = 1000 * 0.85 * 1.0 * (44.01 / 12.011) / 1000.0 tonnes
    res = calc.calculate(
        fuel_mass=1000.0,
        carbon_content=0.85,
        mass_unit="kg",
        oxidation_factor=1.0,
    )
    expected_co2 = 1000.0 * 0.85 * (44.01 / 12.011) / 1000.0
    assert res["results"]["co2"]["value"] == pytest.approx(expected_co2)
    assert res["total_co2e"] == pytest.approx(expected_co2)

    # Percentage inputs normalization (85.0 instead of 0.85, 99.0% oxidation)
    res_pct = calc.calculate(
        fuel_mass=1000.0,
        carbon_content=85.0,
        mass_unit="kg",
        oxidation_factor=99.0,
    )
    expected_co2_ox = 1000.0 * 0.85 * 0.99 * (44.01 / 12.011) / 1000.0
    assert res_pct["results"]["co2"]["value"] == pytest.approx(expected_co2_ox)

    # Mass in tonnes: 5 tonnes
    res_tonnes = calc.calculate(
        fuel_mass=5.0,
        carbon_content=0.80,
        mass_unit="tonne",
    )
    expected_tonnes = (5000.0 * 0.80 * (44.01 / 12.011)) / 1000.0
    assert res_tonnes["results"]["co2"]["value"] == pytest.approx(expected_tonnes)


def test_nitric_acid_calculator_defaults_and_abatement():
    calc = NitricAcidCalculator()

    # 1. Nitric acid default (9.0 kg N2O/t, 0% abatement)
    res_nitric = calc.calculate(
        production_amount=1000.0,  # tonnes
        process_type="nitric_acid_production",
        mass_unit="tonne",
    )
    # 1000 t * 9.0 kg/t = 9000 kg N2O = 9.0 tonnes N2O
    gwp = get_active_gwp()
    assert res_nitric["results"]["n2o"]["value"] == pytest.approx(9.0)
    assert res_nitric["total_co2e"] == pytest.approx(9.0 * float(gwp["N2O"]))

    # 2. Nitric acid with 80% catalytic abatement
    res_abated = calc.calculate(
        production_amount=1000.0,
        abatement_efficiency=80.0,
        process_type="nitric_acid_production",
    )
    # 9.0 t * (1 - 0.80) = 1.8 tonnes N2O
    assert res_abated["results"]["n2o"]["value"] == pytest.approx(1.8)

    # 3. Adipic acid default (300.0 kg N2O/t)
    res_adipic = calc.calculate(
        production_amount=500.0,
        process_type="adipic_acid_production",
    )
    # 500 t * 300 kg/t = 150,000 kg = 150.0 tonnes N2O
    assert res_adipic["results"]["n2o"]["value"] == pytest.approx(150.0)

    # 4. Custom emission factor
    res_custom = calc.calculate(
        production_amount=1000.0,
        ef_n2o=4.5,
        abatement_efficiency=0.0,
    )
    assert res_custom["results"]["n2o"]["value"] == pytest.approx(4.5)


# ---------------------------------------------------------------------------
# calculations/indirect.py Tests
# ---------------------------------------------------------------------------

def test_heat_to_mmbtu_energy_units():
    # Direct energy conversions
    assert heat_to_mmbtu(1.0, "mmbtu") == 1.0
    assert heat_to_mmbtu(1_000_000.0, "btu") == pytest.approx(1.0)
    assert heat_to_mmbtu(10.0, "therm") == pytest.approx(1.0)
    assert heat_to_mmbtu(1.0 / 0.947817, "gj") == pytest.approx(1.0, rel=1e-4)
    assert heat_to_mmbtu(1.0 / 3.412142, "mwh") == pytest.approx(1.0, rel=1e-4)


def test_heat_to_mmbtu_steam_mass_with_enthalpy():
    # 1000 lb of steam with 1170 Btu/lb enthalpy
    # Energy = 1000 * 1170 / 1e6 = 1.17 MMBtu
    assert heat_to_mmbtu(1000.0, "lb", steam_enthalpy_btu_lb=1170.0) == pytest.approx(1.17)

    # 1 tonne of steam (2204.62262 lb) with 1000 Btu/lb enthalpy
    expected_tonne = 2204.62262 * 1000.0 / 1e6
    assert heat_to_mmbtu(1.0, "tonne", steam_enthalpy_btu_lb=1000.0) == pytest.approx(expected_tonne)

    # Direct MMBtu per unit enthalpy
    assert heat_to_mmbtu(5.0, "tonne", steam_enthalpy=2.5) == pytest.approx(12.5)


def test_heat_to_mmbtu_validation_errors():
    # Ambiguous ton
    with pytest.raises(ValueError) as exc:
        heat_to_mmbtu(10.0, "ton")
    assert "ambiguous" in str(exc.value)

    # Steam mass without enthalpy
    with pytest.raises(ValueError) as exc_enth:
        heat_to_mmbtu(1000.0, "lb")
    assert "needs its enthalpy" in str(exc_enth.value)

    # Unknown unit
    with pytest.raises(ValueError):
        heat_to_mmbtu(100.0, "cubic_yards")


def test_indirect_steam_calculator_physics():
    calc = IndirectSteamCalculator()

    # 1000 MMBtu delivered heat, 80% boiler efficiency, 5% transmission loss
    # Net efficiency = 0.80 - 0.05 = 0.75 (Exhibit 8.3)
    # Fuel consumed = 1000 / 0.75 = 1333.333 MMBtu
    # EF_CO2 = 53.06 kg CO2/MMBtu
    # CO2 = 1333.333 * 53.06 / 1000 = 70.7467 tCO2
    res = calc.calculate(
        heat_energy=1000.0,
        ef_co2=53.06,
        boiler_efficiency=0.80,
        transmission_loss=0.05,
        uncertainties=None,
        heat_unit="mmbtu",
        ef_ch4=0.001,
        ef_n2o=0.0001,
    )
    expected_fuel = 1000.0 / 0.75
    expected_co2 = expected_fuel * 53.06 / 1000.0
    expected_ch4 = expected_fuel * 0.001 / 1000.0
    expected_n2o = expected_fuel * 0.0001 / 1000.0
    gwp = get_active_gwp()
    expected_co2e = expected_co2 + expected_ch4 * float(gwp["CH4"]) + expected_n2o * float(gwp["N2O"])

    assert res["results"]["co2"]["value"] == pytest.approx(expected_co2, rel=1e-4)
    assert res["results"]["ch4"]["value"] == pytest.approx(expected_ch4, rel=1e-4)
    assert res["results"]["n2o"]["value"] == pytest.approx(expected_n2o, rel=1e-4)
    assert res["total_co2e"] == pytest.approx(expected_co2e, rel=1e-4)


def test_indirect_steam_calculator_error_boundaries():
    calc = IndirectSteamCalculator()
    # Net efficiency <= 0
    with pytest.raises(ValueError):
        calc.calculate(heat_energy=100.0, ef_co2=50.0, boiler_efficiency=0.0, transmission_loss=0.0, uncertainties=None)
    with pytest.raises(ValueError):
        calc.calculate(heat_energy=100.0, ef_co2=50.0, boiler_efficiency=0.8, transmission_loss=1.0, uncertainties=None)
    with pytest.raises(ValueError):
        calc.calculate(heat_energy=100.0, ef_co2=50.0, boiler_efficiency=1.5, transmission_loss=0.0, uncertainties=None)


def test_cogen_allocation_calculator_conservation_of_emissions():
    calc = CogenAllocationCalculator()
    total_emissions = 10_000.0  # tCO2e total from CHP plant

    # 1. WRI Efficiency Method (Equation 8-5)
    res_wri = calc.calculate(
        total_emissions=total_emissions,
        heat_output=50_000.0,
        power_output=20_000.0,
        method="wri_efficiency",
        heat_unit="mmbtu",
        power_unit="mmbtu",
        heat_efficiency=0.80,
        power_efficiency=0.35,
    )
    heat_t = res_wri["metadata"]["allocated_heat_tonnes"]
    power_t = res_wri["metadata"]["allocated_power_tonnes"]

    # Conservation Law: heat_allocated + power_allocated MUST equal total_emissions
    assert (heat_t + power_t) == pytest.approx(total_emissions, rel=1e-6)
    assert 0 < heat_t < total_emissions
    assert 0 < power_t < total_emissions

    # 2. Energy Content Method
    res_energy = calc.calculate(
        total_emissions=total_emissions,
        heat_output=60_000.0,
        power_output=40_000.0,
        method="energy_content",
        heat_unit="mmbtu",
        power_unit="mmbtu",
    )
    heat_e = res_energy["metadata"]["allocated_heat_tonnes"]
    power_e = res_energy["metadata"]["allocated_power_tonnes"]

    # In energy content with 60% heat and 40% power, heat gets 6000 and power gets 4000
    assert (heat_e + power_e) == pytest.approx(total_emissions, rel=1e-6)
    assert heat_e == pytest.approx(6000.0)
    assert power_e == pytest.approx(4000.0)

    # 3. Method validation
    with pytest.raises(ValueError) as exc:
        calc.calculate(
            total_emissions=1000.0,
            heat_output=100.0,
            power_output=50.0,
            method="invalid_method",
        )
    assert "Unknown cogeneration allocation method" in str(exc.value)
