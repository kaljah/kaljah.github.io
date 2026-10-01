"""RC-5 unit handling regressions. Every expected value is hand-derived from the unit definitions
(1 scf = 0.028316846592 m3, 1 gal = 3.785411784 L, 1 bbl = 42 gal, 1 MMBtu = 1055.05585262 MJ,
1 kWh = 3.6 MJ, CH4 0.67722 kg/m3 at 60 F) and the catalog factors quoted in each test."""
import math

import pytest

from calculations.combustion import convert_factor_to_kg_per_unit as conv
from calculations.units import (UnitError, annual_volume_m3, factor_to_kg_per_activity, parse_factor_unit,
                                parse_volume_rate, per_source_hour_kg)

SCF_M3 = 0.028316846592


# BUG-047: per-hour factors x hours (annual inventory default 8,760 h)
def test_bug047_per_hour_factor_times_hours():
    kg = factor_to_kg_per_activity(4.36e-6, "tonne CH₄/hr/source", "count", hours=8760)
    assert kg * 10 / 1000 == pytest.approx(10 * 4.36e-6 * 8760)  # 0.381936 t
    with pytest.raises(UnitError):
        factor_to_kg_per_activity(4.36e-6, "tonne CH4/hr/source", "count")  # hours required


# BUG-048: Unicode subscript and tonne numerator
def test_bug048_subscript_ch4_and_tonne_numerator():
    kg_hr, is_ch4 = per_source_hour_kg(1.8e-5, "tonne CH₄/well/hr")
    assert is_ch4 and kg_hr == pytest.approx(0.018)
    kg_hr, is_ch4 = per_source_hour_kg(0.0045, "kg TOC/hr/component")
    assert not is_ch4 and kg_hr == pytest.approx(0.0045)


# BUG-049: 10^n scale in the denominator
@pytest.mark.parametrize("value,unit,act,expected_kg_per_act", [
    (0.0104, "tonne CH₄/10⁶ scf produced", "scf", 0.0104 * 1000 / 1e6),
    (0.000375, "tonnes CH₄/10³ bbl feedstock", "bbl", 0.000375 * 1000 / 1e3),
])
def test_bug049_scale_prefix(value, unit, act, expected_kg_per_act):
    assert factor_to_kg_per_activity(value, unit, act) == pytest.approx(expected_kg_per_act)


# BUG-051: energy units convert as energy, never as scf
def test_bug051_kwh_mj_btu():
    assert conv(53.06, "kg/MMBtu", "kwh", hhv=1020, fuel_type="gases") == pytest.approx(53.06 * 3.6 / 1055.05585262)
    assert conv(53.06, "kg/MMBtu", "mj", hhv=1020, fuel_type="gases") == pytest.approx(53.06 / 1055.05585262)
    assert conv(53.06, "kg/MMBtu", "btu", hhv=1020, fuel_type="gases") == pytest.approx(53.06 / 1e6)


# BUG-027: HHV basis from the factor, density needed across mass/volume, phases not mixed
def test_bug027_hhv_basis():
    # diesel per m3: 264.172052 gal x 0.138 MMBtu/gal x 73.96 kg/MMBtu
    assert conv(73.96, "kg/MMBtu", "m3", hhv=138000, fuel_type="liquids") == pytest.approx(264.172052 * 0.138 * 73.96, rel=1e-6)
    # diesel per tonne at 850 kg/m3: 1000/850 m3 -> 3.1718 t CO2 (audit hand value 3.17 t)
    t = conv(73.96, "kg/MMBtu", "tonne", hhv=138000, fuel_type="liquids", density=850) / 1000
    assert t == pytest.approx(1000 / 850 * 264.172052 * 0.138 * 73.96 / 1000, rel=1e-6)
    assert t == pytest.approx(3.17, rel=0.01)
    # coal per tonne: 24.93 MMBtu/short ton x 1.1023113 short ton/t
    assert conv(93.26, "kg/MMBtu", "tonne", hhv=24930, fuel_type="solids") == pytest.approx(24.93 * 1.1023113 * 93.26, rel=1e-6)
    with pytest.raises(UnitError):
        conv(73.96, "kg/MMBtu", "tonne", hhv=138000, fuel_type="liquids")  # no density
    with pytest.raises(UnitError):
        conv(59.6, "kg/MMBtu", "scf", hhv=69600, fuel_type="gases", hhv_unit="btu/gal")  # ethane per gallon
    with pytest.raises(UnitError):
        conv(53.06, "kg/MMBtu", "gal", hhv=1020, fuel_type="gases")  # gas HHV per liquid gallon


# BUG-063: custom factor units
@pytest.mark.parametrize("ef,fu,act,expected_kg", [
    (3170.0, "tonne", "kg", 3.17),          # kg per tonne of fuel, activity in kg
    (3.17, "kg", "tonne", 3170.0),
    (10.21, "gal", "bbl", 42 * 10.21),
    (0.0541, "scf", "m3", 0.0541 / SCF_M3),
    (1.9, "m³", "scf", 1.9 * SCF_M3),
])
def test_bug063_bare_units_are_kg_per_unit(ef, fu, act, expected_kg):
    assert conv(ef, fu, act) == pytest.approx(expected_kg, rel=1e-6)


def test_bug063_unknown_factor_unit_rejected_not_applied_1_to_1():
    with pytest.raises(UnitError):
        conv(1.0, "kg/furlong", "scf")
    with pytest.raises(UnitError):
        parse_factor_unit("scf/MMscf")


# BUG-011 / BUG-066: rate units
@pytest.mark.parametrize("unit,expected_mmscf_per_year", [
    ("MMscf/yr", 1.0), ("MMscfd", 365.0), ("mmscf/d", 365.0), ("Mcf/day", 0.365), ("m3/yr", 1 / 28316.846592),
])
def test_bug066_rate_units_annualised(unit, expected_mmscf_per_year):
    assert annual_volume_m3(1.0, unit) / 28316.846592 == pytest.approx(expected_mmscf_per_year)


def test_bug011_mmscf_is_not_mscf():
    assert parse_volume_rate("mmscf/day")[0] == pytest.approx(28316.846592)
    assert parse_volume_rate("mscf/day")[0] == pytest.approx(28.316846592)
    assert parse_volume_rate("Mcf/hr")[1] == 8760.0


def test_bug011_completion_rate_default_is_mcf_per_hr():
    """10 Mcf/hr x 5 h = 50,000 scf = 1415.84 m3 x 0.85 x 0.67722 kg/m3 = 0.81655 t CH4."""
    from calculations.legacy_engine import compute_emissions

    em, _ = compute_emissions({"process_type": "completions", "factor_source": "specific", "comp_method": "rate_duration",
                               "comp_rate": 10, "comp_duration": 5, "amount": 1, "unit": "count", "ch4_content": 0.85}, {})
    assert em["ch4"] == pytest.approx(50000 * SCF_M3 * 0.85 * (16.04 / 23.685) / 1000, rel=1e-6)


def test_bug012_completions_form_amount_is_events():
    """calc_inputs.amount (form event count) = 2 events: 0.5 Mcf/hr x 24 h x 2 x 0.80 x 0.67722."""
    from calculations.legacy_engine import compute_emissions

    em, _ = compute_emissions({"process_type": "completions", "factor_source": "specific", "amount": 339.8016, "unit": "m3",
                               "calc_inputs": {"completions": {"comp_rate": 0.5, "comp_duration": 24, "ch4_content": 80,
                                                               "amount": 2}}}, {})
    assert em["ch4"] == pytest.approx(0.5 * 1000 * 24 * 2 * SCF_M3 * 0.80 * (16.04 / 23.685) / 1000, rel=1e-6)


def test_bug066_agr_units_agree():
    """1 MMscf/d == 365 MMscf/yr == 365,000 Mcf/yr: all three give the same AGR CO2."""
    from calculations.dispatcher import CalculationDispatcher

    d = CalculationDispatcher()
    vals = [d._normalize_volume(1, "MMscfd", "mmscf"), d._normalize_volume(365, "MMscf/yr", "mmscf"),
            d._normalize_volume(1000, "Mcf/day", "mmscf")]
    assert vals[0] == pytest.approx(365) and vals[1] == pytest.approx(365) and vals[2] == pytest.approx(365)
    with pytest.raises(ValueError):
        d._normalize_volume(1, "furlongs", "mmscf")
