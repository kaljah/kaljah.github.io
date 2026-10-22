import pytest

from calculations.combustion import FlaringCalculator, CombustionCalculator

# Independent reference constants (API Compendium 2021 Tables 3-3 and 3-7): 23.685 m3/kmol at 60 F and 1 atm,
# CH4 16.04, CO2 44.01 kg/kmol. The expected values below are worked by hand from the inputs, not read from the engine.
RHO_CH4 = 16.04 / 23.685      # kg/m3
RHO_CO2 = 44.01 / 23.685      # kg/m3


def test_flaring_calculator_basic():
    calc = FlaringCalculator()
    data = {
        "gas_volume": 1000,
        "ch4_fraction": 0.85,
        "flare_type": "elevated",
        "uncertainties": {},
    }
    res = calc.calculate(**data)
    # 1,000 m3 x 85 % CH4; an elevated flare without an entered efficiency destroys 98 % of the CH4 and converts
    # 96.5 % of the carbon to CO2 (Compendium corrections, December 2025)
    assert res["results"]["ch4"]["value"] == pytest.approx(1000 * 0.85 * 0.02 * RHO_CH4 / 1000, rel=1e-9)
    assert res["results"]["co2"]["value"] == pytest.approx(1000 * 0.85 * 0.965 * RHO_CO2 / 1000, rel=1e-9)


def test_flaring_calculator_specific_c1_c10():
    calc = FlaringCalculator()
    data = {
        "gas_volume": 1000,
        "ch4_fraction": 0.80,
        "flare_type": "elevated",
        "uncertainties": {},
        "c1": 80.0,
        "c2": 10.0,
        "c3": 5.0,
        "co2_comp": 2.0,
    }
    res = calc.calculate(**data)
    # carbon per mole of gas: 0.80 CH4 x 1 + 0.10 C2H6 x 2 + 0.05 C3H8 x 3 = 1.15 (C4+ absent); 2 % native CO2
    carbon = 0.80 * 1 + 0.10 * 2 + 0.05 * 3
    assert res["results"]["co2"]["value"] == pytest.approx(1000 * (carbon * 0.965 + 0.02) * RHO_CO2 / 1000, rel=1e-9)
    assert res["results"]["ch4"]["value"] == pytest.approx(1000 * 0.80 * 0.02 * RHO_CH4 / 1000, rel=1e-9)


def test_stationary_combustion_calculator():
    calc = CombustionCalculator()
    data = {
        "fuel_quantity": 500,
        "fuel_unit": "gal",
        "hhv": 138000,
        "fuel_type": "liquids",
        "ef_co2": 73.96,
        "ef_ch4": 0.003,
        "ef_n2o": 0.0006,
        "ef_unit": "kg/mmbtu",
        "uncertainties": {},
    }
    res = calc.calculate(**data)
    # 500 gal x 138,000 Btu/gal = 69 MMBtu x 73.96 kg/MMBtu = 5.10324 tonnes
    assert res["results"]["co2"]["value"] == pytest.approx(500 * 138000 / 1e6 * 73.96 / 1000, rel=1e-9)
