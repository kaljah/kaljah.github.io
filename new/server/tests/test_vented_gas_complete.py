"""calculations/vented_gas.py: every gas-volume method (API Compendium 2021 Eq 3-5, 6-2, 6-3, 6-16/6-17, 6-18,
6-20, section 6.3.9.3) and disposition. Fixed while testing: an actual volume without its temperature and
pressure was taken at 60 F / 1 atm (that is, as a standard volume); the desiccant gas fraction (45 %) and the
CO2 mass fraction (100 %) had defaults the Compendium does not give; a flare without an entered efficiency used
98 % for CO2 as well (the Compendium corrections give 96.5 % combustion and 98 % CH4 destruction).
"""
import math

import pytest

from calculations.units import CONVERSIONS
from calculations.vented_gas import FT3_PER_BBL, SCF_TO_M3, VentedGasCalculator

RHO_CH4, RHO_CO2 = CONVERSIONS["density_ch4"], CONVERSIONS["density_co2"]


def val(res, gas):
    r = res["results"][gas]
    return r["value"] if isinstance(r, dict) else r


def t(scf, frac, rho):
    return scf * SCF_TO_M3 * frac * rho / 1000


@pytest.fixture
def g():
    return VentedGasCalculator()


def base(**kw):
    return {"ch4_content": 80, "co2_content": 5, **kw}


@pytest.mark.parametrize("method,inputs,scf", [
    ("volume", dict(gas_volume=2, gas_volume_unit="MMscf"), 2e6),
    ("volume", dict(amount=1000, unit="m³"), 1000 / SCF_TO_M3),
    ("volume", dict(gas_volume=5, gas_volume_unit="Mcf"), 5000),
    ("gor", dict(gor=500, oil_rate=100, vent_hours=48), 500 * 100 * 2),                      # Eq 6-3
    ("rate_days", dict(gas_rate=2, gas_rate_unit="mcf/day", days=10), 20_000),
    ("rate_days", dict(gas_rate=1000, days=3), 3000),
    ("actual", dict(actual_volume=100, actual_unit="bbl", gas_temp_f=100, gas_pressure_atm=2),
     100 * FT3_PER_BBL * 2 * 519.67 / 559.67),                                                   # Eq 3-5
])
def test_volume_methods(g, method, inputs, scf):
    res = g.calculate(method, base(**inputs))
    assert res["intermediate"]["gas_volume_scf"] == pytest.approx(scf)
    assert val(res, "ch4") == pytest.approx(t(scf, 0.80, RHO_CH4))
    assert val(res, "co2") == pytest.approx(t(scf, 0.05, RHO_CO2))


def test_desiccant_eq_6_17_monthly_share(g):
    res = g.calculate("desiccant", base(vessel_height_ft=6.4, vessel_diameter_ft=1.6, vessel_pressure_psig=450,
                                        gas_fraction=45, refills=52, year=2025))
    scf = 6.4 * 1.6 ** 2 * math.pi / 4 * (464.7 / 14.7) * 0.45 * 52
    assert res["intermediate"]["gas_volume_scf"] == pytest.approx(scf)
    month = g.calculate("desiccant", base(vessel_height_ft=6.4, vessel_diameter_ft=1.6, vessel_pressure_psig=450,
                                          gas_fraction=0.45, refills=52, year=2025, month=2))
    assert month["intermediate"]["gas_volume_scf"] == pytest.approx(scf * 28 / 365)


def test_flare_defaults_and_entered_efficiency(g):
    scf = 1e6
    res = g.calculate("volume", base(gas_volume=1, gas_volume_unit="MMscf", c2plus_content=5, disposition="flared"))
    assert val(res, "ch4") == pytest.approx(t(scf, 0.80, RHO_CH4) * 0.02)                       # DE 98 %
    assert val(res, "co2") == pytest.approx(t(scf, 0.05, RHO_CO2) + t(scf, 0.80 + 2 * 0.05, RHO_CO2) * 0.965)  # CE 96.5 %
    entered = g.calculate("volume", base(gas_volume=1, gas_volume_unit="MMscf", disposition="flared",
                                         combustion_efficiency=90))
    assert val(entered, "ch4") == pytest.approx(t(scf, 0.80, RHO_CH4) * 0.10)
    assert val(entered, "co2") == pytest.approx(t(scf, 0.05, RHO_CO2) + t(scf, 0.80, RHO_CO2) * 0.90)


def test_reported_mass_and_thc_mass(g):
    rep = g.calculate("reported_mass", {"ch4_mass": 2000, "co2_mass": 500, "mass_unit": "kg", "control_efficiency": 50})
    assert (val(rep, "ch4"), val(rep, "co2")) == pytest.approx((1.0, 0.25))
    assert rep["intermediate"]["activity_amount"] == pytest.approx(2.0)
    full = g.calculate("reported_mass", {"ch4_mass": 1, "control_efficiency": 100})
    assert val(full, "ch4") == 0 and full["intermediate"]["activity_amount"] == 0
    thc = g.calculate("thc_mass", {"amount": 10, "thc_loss_unit": "short_ton", "ch4_wt_pct": 20, "co2_wt_pct": "5%"})
    assert (val(thc, "ch4"), val(thc, "co2")) == pytest.approx((9.0718474 * 0.20, 9.0718474 * 0.05))


def test_agr_balance_eq_6_18(g):
    res = g.calculate("agr_balance", {"sour_gas_volume": 10, "sweet_gas_volume": 9.6, "gas_volume_unit": "MMscf",
                                      "sour_co2_content": 4, "sweet_co2_content": 0.5})
    co2_scf = 10e6 * 0.04 - 9.6e6 * 0.005
    assert val(res, "co2") == pytest.approx(t(co2_scf, 1.0, RHO_CO2))
    assert val(res, "ch4") == pytest.approx(10 * 0.0185)                                        # Table 6-19
    no_ch4 = g.calculate("agr_balance", {"amount": 10, "unit": "MMscf", "sweet_gas_volume": 9.6,
                                         "sour_co2_content": 4, "include_ch4": "false"})
    assert val(no_ch4, "ch4") == 0


def test_co2_mass_eq_6_20(g):
    res = g.calculate("co2_mass", {"physical_volume_m3": 36.4, "co2_density": 650, "co2_wt_pct": 98.5, "events": 2})
    assert val(res, "co2") == pytest.approx(2 * 36.4 * 650 * 0.985 / 1000)
    one = g.calculate("co2_mass", {"physical_volume_m3": 36.4, "co2_density": 650, "co2_wt_pct": 98.5})
    assert val(one, "co2") == pytest.approx(36.4 * 650 * 0.985 / 1000)


@pytest.mark.parametrize("method,inputs,match", [
    ("volume", base(gas_volume=1, gas_volume_unit="gal"), "Gas volume unit"),
    ("volume", {"gas_volume": 1, "gas_volume_unit": "scf"}, "CH4 content"),
    ("volume", base(gas_volume=-1, gas_volume_unit="scf"), "non-negative"),
    ("volume", base(gas_volume=1, gas_volume_unit="scf", ch4_content=90, co2_content=20), "exceeds 100 %"),
    ("volume", base(gas_volume=1, gas_volume_unit="scf", ch4_content=150), "cannot exceed 100 %"),
    ("volume", base(gas_volume=1, gas_volume_unit="scf", ch4_content=-5), "non-negative"),
    ("rate_days", base(gas_rate=1, gas_rate_unit="kg/day", days=1), "Gas rate unit"),
    ("actual", base(actual_volume=1, actual_unit="liter", gas_temp_f=60, gas_pressure_atm=1), "Actual volume unit"),
    ("actual", base(actual_volume=1, gas_pressure_atm=1), "gas temperature"),
    ("actual", base(actual_volume=1, gas_temp_f=60), "gas pressure"),
    ("desiccant", base(vessel_height_ft=1, vessel_diameter_ft=1, vessel_pressure_psig=1, refills=1), "gas fraction"),
    ("satellite", base(), "Unknown gas volume method"),
    ("reported_mass", {"ch4_mass": 1, "mass_unit": "g"}, "Mass unit"),
    ("thc_mass", {"thc_loss": 1, "thc_loss_unit": "g", "ch4_wt_pct": 1}, "Hydrocarbon loss unit"),
    ("thc_mass", {"thc_loss": 1}, "CH4 in vent"),
    ("thc_mass", {"thc_loss": 1, "ch4_wt_pct": 90, "co2_wt_pct": 20}, "exceeds 100 wt %"),
    ("agr_balance", {"sour_gas_volume": 1, "sweet_gas_volume": 1, "gas_volume_unit": "bbl"}, "Gas volume unit"),
    ("agr_balance", {"sour_gas_volume": 1, "sweet_gas_volume": 1, "gas_volume_unit": "scf"}, "sour gas CO2"),
    ("agr_balance", {"sour_gas_volume": 1, "sweet_gas_volume": 1, "gas_volume_unit": "scf", "sour_co2_content": 1,
                     "sweet_co2_content": 2}, "Sweet gas carries more CO2"),
    ("co2_mass", {"physical_volume_m3": 1, "co2_density": 650}, "CO2 weight"),
])
def test_refusals(g, method, inputs, match):
    with pytest.raises(ValueError, match=match):
        g.calculate(method, inputs)
