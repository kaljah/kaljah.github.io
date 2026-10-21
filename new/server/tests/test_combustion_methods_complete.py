"""calculations/combustion_methods.py: every method and refusal (API Compendium 2021 Exhibits 4.5, 4.7/4.8,
4.12, 5.2, 5.3). Fixed while testing: a fuel-gas HHV of 0 was accepted, so the equipment method booked no energy.
"""
import pytest

from calculations.combustion_methods import (C_TO_CO2, EQUIPMENT_FACTORS, FUEL_BASIS, TOC_CH4_WT,
                                             CombustionMethodCalculator, equipment_factor_list)


def val(res, gas):
    r = res["results"][gas]
    return r["value"] if isinstance(r, dict) else r


@pytest.fixture
def c():
    return CombustionMethodCalculator()


def test_carbon_content_by_mass_and_volume(c):
    by_mass = c.calculate("carbon_content", {"fuel_mass": 2000, "fuel_mass_unit": "kg", "carbon_wt_pct": 85})
    assert val(by_mass, "co2") == pytest.approx(2 * 0.85 * C_TO_CO2)
    by_vol = c.calculate("carbon_content", {"amount": 1, "unit": "bbl", "fuel_density": 7.0, "carbon_wt_pct": 87,
                                            "oxidation_pct": 99})
    assert val(by_vol, "co2") == pytest.approx(42 * 7.0 / 2204.62 * 0.87 * 0.99 * C_TO_CO2)


def test_equipment_energy_sources(c):
    row = EQUIPMENT_FACTORS["ic_diesel"]
    direct = c.calculate("equipment", {"equipment_type": "ic_diesel", "energy_mmbtu": 100})
    assert val(direct, "ch4") == pytest.approx(100 * row["ch4"] * TOC_CH4_WT)                        # TOC row
    assert val(direct, "n2o") == pytest.approx(100 * FUEL_BASIS["diesel"]["n2o"])                     # fuel basis
    liquid = c.calculate("equipment", {"equipment_type": "ic_diesel", "fuel_volume": 1000, "fuel_volume_unit": "gal"})
    assert liquid["intermediate"]["energy_mmbtu"] == pytest.approx(138.0)
    engine = c.calculate("equipment", {"equipment_type": "ic_4s_lean_ng", "engine_hp": 1000, "load_pct": 50,
                                       "operating_hours": 100})
    assert engine["intermediate"]["energy_mmbtu"] == pytest.approx(1000 * 0.5 * 100 * 7000 / 1e6)
    gas = c.calculate("equipment", {"equipment_type": "boiler_ng_controlled", "amount": 1e6, "unit": "scf", "hhv": 1030})
    assert gas["intermediate"]["energy_mmbtu"] == pytest.approx(1030)
    assert val(gas, "n2o") == pytest.approx(1030 * 2.8e-7)
    assert len(equipment_factor_list()) == len(EQUIPMENT_FACTORS)


def test_vehicle_distance(c):
    res = c.calculate("vehicle_distance", {"distance": 1000, "distance_unit": "km", "vehicle_type": "hd_diesel_advanced",
                                           "fuel_economy_mpg": 6.2137119})
    gal = 1000 * 0.621371192 / 6.2137119
    assert val(res, "ch4") == pytest.approx(gal / 1000 * 4.2e-4)
    own = c.calculate("vehicle_distance", {"amount": 100, "vehicle_fuel": "gasoline", "fuel_economy_mpg": 20})
    assert val(own, "ch4") == pytest.approx(5 * 0.125 * FUEL_BASIS["gasoline"]["ch4"])


def test_flare_voc_and_thermal_oxidizer(c):
    voc = c.calculate("flare_voc", {"voc_mass": 1, "wt_ch4": 50, "wt_c2h6": 10, "wt_c3h8": 30, "wt_c4h10": 10})
    assert val(voc, "ch4") == pytest.approx(1 / 0.4 * 0.5)
    assert val(voc, "n2o") > 0
    by_mass = c.calculate("thermal_oxidizer", {"toc_mass": 10, "toc_carbon_wt_pct": 85, "toc_ch4_wt_pct": 15})
    assert val(by_mass, "co2") == pytest.approx(10 * 0.85 * C_TO_CO2 * 0.98)
    assert val(by_mass, "ch4") == pytest.approx(10 * 0.15 * 0.02)
    loaded = c.calculate("thermal_oxidizer", {"amount": 1e6, "unit": "gal", "loading_loss_lb_kgal": 2.0,
                                              "toc_carbon_wt_pct": 85, "toc_ch4_wt_pct": 15})
    assert loaded["intermediate"]["toc_t"] == pytest.approx(1000 * 2.0 / 0.85 / 2204.62)             # VOC 85 % of TOC


@pytest.mark.parametrize("method,inputs,match", [
    ("carbon_content", {"fuel_mass": 1}, "Missing required field: carbon content"),
    ("carbon_content", {"fuel_mass": "lots", "carbon_wt_pct": 85}, "must be a number"),
    ("carbon_content", {"fuel_mass": -1, "carbon_wt_pct": 85}, "non-negative"),
    ("carbon_content", {"fuel_mass": 1, "carbon_wt_pct": 120}, "cannot exceed 100"),
    ("carbon_content", {"fuel_mass": 1, "fuel_mass_unit": "ton", "carbon_wt_pct": 85}, "Fuel mass unit"),
    ("equipment", {"equipment_type": "kettle"}, "Unknown equipment type"),
    ("equipment", {"equipment_type": "boiler_ng_controlled", "amount": 1, "unit": "scf", "hhv": 0}, "positive"),
    ("vehicle_distance", {"distance": 1, "vehicle_fuel": "lpg", "fuel_economy_mpg": 5}, "diesel or gasoline"),
    ("flare_voc", {"voc_mass": 1, "wt_ch4": 90}, "VOC \\(C3\\+\\) weight"),
    ("flare_voc", {"voc_mass": 1, "wt_ch4": 60, "wt_c3h8": 50}, "exceeds 100 wt"),
    ("flare_voc", {"voc_mass": 1, "wt_c3h8": 50, "combustion_efficiency": 100}, "below 100 %"),
    ("thermal_oxidizer", {"amount": 1, "unit": "gal", "loading_loss_lb_kgal": 1, "voc_fraction_of_toc": 0,
                          "toc_carbon_wt_pct": 85, "toc_ch4_wt_pct": 1}, "above zero"),
    ("smelting", {}, "Unknown combustion method"),
])
def test_refusals(c, method, inputs, match):
    with pytest.raises(ValueError, match=match):
        c.calculate(method, inputs)
