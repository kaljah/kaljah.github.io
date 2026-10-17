"""calculations/vented_production_pneumatic.py: every mode, table row, disposition and refusal, with values from
API Compendium 2021 Tables 6-14 to 6-18 and Equations 6-13 to 6-17. Fixed while testing: a misspelt controller
type took the 9.2 scf/h unknown-controller factor and an unknown pump type the diaphragm factor; the controller
default composition was 85 % (the tables' basis is 81.6 %); Eq 6-13 / 6-15 / 6-17 inputs without a Compendium
default (supply pressure, actuations, outlet pressure, void fraction) were assumed; 0 pumps / dehydrators / days
counted as 1 / 1 / 365; a flare efficiency below 95 % was raised to 95 %.
"""
import math

import pytest

from calculations.vented_production_pneumatic import (
    GasDehydrationCalculator,
    PneumaticDeviceCalculator,
    PneumaticPumpCalculator,
)

LB_T = 2204.6226218487757


def t_gas(scf, frac, mw=16.04):
    return scf * frac * mw / 379.3 / LB_T


def val(res, gas):
    r = res["results"][gas]
    return (r or {}).get("value", 0.0) if isinstance(r, dict) or r is None else r


def scf(res):
    return res["inputs"]["total_gas_scf"]


# ---------------------------------------------------------------- controllers, Tables 6-14 / 6-15
@pytest.mark.parametrize("ctype,api,subpart_w", [
    ("high_bleed", 16.4, 37.3), ("low_bleed", 2.6, 1.39), ("intermittent_average", 9.3, 13.5),
    ("intermittent_normal", 0.28, 13.5), ("intermittent_malfunctioning", 24.1, 13.5),
])
def test_controller_tables(ctype, api, subpart_w):
    d = PneumaticDeviceCalculator()
    assert scf(d.calculate(count=2, hours=100, controller_type=ctype)) == pytest.approx(2 * api * 100)
    sw = d.calculate(count=2, hours=100, controller_type=ctype, source_standard="SUBPART_W")
    assert scf(sw) == pytest.approx(2 * subpart_w * 100)
    assert sw["inputs"]["ch4_content"] == 0.816                                          # the tables' basis


@pytest.mark.parametrize("ctype", ["unknown", "average", "production_average"])
def test_unknown_controller_type_uses_9_2_scf_per_hour(ctype):
    assert scf(PneumaticDeviceCalculator().calculate(count=1, hours=1000, controller_type=ctype)) == pytest.approx(9200)


def test_monitoring_program_eq_6_14():
    res = PneumaticDeviceCalculator().calculate(monitoring_program=True, normal_count=79, malfunctioning_count=1,
                                                malfunctioning_fraction_year=0.5, hours=8760)
    assert scf(res) == pytest.approx(79 * 0.28 * 8760 + 1 * 24.1 * 8760 * 0.5)
    assert res["inputs"]["count"] == 80


def test_physical_actuation_eq_6_13():
    res = PneumaticDeviceCalculator().calculate(count=3, id_pipe_inches=0.5, length_pipe_ft=20, delta_vol_bonnet_scf=0.1,
                                                p_control_psig=20, actuations_per_year=500)
    pipe = math.pi / 4 * (0.5 / 12) ** 2 * 20
    expected = 3 * (pipe + 0.1) * (20 + 14.7) / 14.696 * 500
    assert scf(res) == pytest.approx(expected, rel=1e-3)
    via_actuations = PneumaticDeviceCalculator().calculate(count=3, id_pipe_inches=0.5, length_pipe_ft=20,
                                                           delta_vol_bonnet_scf=0.1, p_control_psig=20, actuations=500)
    assert scf(via_actuations) == pytest.approx(scf(res))


def test_actuation_with_volume_and_continuous_bleed():
    d = PneumaticDeviceCalculator()
    assert scf(d.calculate(count=2, actuations=100, bleed_rate=0.5)) == pytest.approx(100)
    assert scf(d.calculate(count=2, hours=10, bleed_rate=6.0)) == pytest.approx(120)
    assert scf(d.calculate(count=2, hours=10)) == pytest.approx(2 * 10 * 9.2)            # no rate: 9.2 scf/h
    pct = d.calculate(count=1, hours=1000, bleed_rate=1, ch4_content=90, co2_content=2)
    frac = d.calculate(count=1, hours=1000, bleed_rate=1, ch4_content=0.90, co2_content=0.02)
    assert (val(pct, "ch4"), val(pct, "co2")) == pytest.approx((val(frac, "ch4"), val(frac, "co2")))


@pytest.mark.parametrize("kwargs,match", [
    (dict(count=1, controller_type="high bleed"), "Unknown controller type"),
    (dict(count=1, controller_type="high_bleed", source_standard="epa"), "Unknown factor standard"),
    (dict(count=1, id_pipe_inches=0.5, length_pipe_ft=1, delta_vol_bonnet_scf=0.1, actuations=10), "supply pressure"),
    (dict(count=1, id_pipe_inches=0.5, length_pipe_ft=1, delta_vol_bonnet_scf=0.1, p_control_psig=20), "actuations"),
    (dict(count=1, actuations=10), "gas volume per actuation"),
])
def test_controller_refusals(kwargs, match):
    with pytest.raises(ValueError, match=match):
        PneumaticDeviceCalculator().calculate(**kwargs)


# ---------------------------------------------------------------- chemical injection pumps, Table 6-16 / Eq 6-15
@pytest.mark.parametrize("ptype,rate", [("piston", 2.59), ("diaphragm", 23.6), ("average", 13.1), ("piston_ccac", 2.03),
                                        ("diaphragm_ccac", 18.58)])
def test_pump_table_6_16(ptype, rate):
    res = PneumaticPumpCalculator().calculate(pump_type=ptype, pump_count=2, operating_hours=100)
    assert scf(res) == pytest.approx(2 * rate * 100)
    assert val(res, "ch4") == pytest.approx(t_gas(2 * rate * 100, 0.816))


def test_pump_engineering_eq_6_15_6_16():
    p = PneumaticPumpCalculator()
    res = p.calculate(method="engineering", volume_per_stroke_gal=0.01, strokes_per_minute=10, operating_hours=100,
                      pump_outlet_pressure_psig=200, gas_temperature_f=80)
    v_l = 0.01 / 7.48052 * 10 * 6000                                                   # Eq 6-16
    v_g = (200 + 14.7) / 14.7 * 520 / (459.67 + 80) * v_l * 1.30                       # Eq 6-15, 30 % default
    assert scf(res) == pytest.approx(v_g)
    direct_vl = p.calculate(method="engineering", volume_liquid_pumped_ft3=v_l, pump_outlet_pressure_psig=200,
                            gas_temperature_f=80)
    assert scf(direct_vl) == pytest.approx(v_g)
    minutes = p.calculate(method="engineering", volume_per_stroke_gal=0.01, strokes_per_minute=10,
                          annual_operational_minutes=6000, pump_outlet_pressure_psig=200, gas_temperature_f=80)
    assert scf(minutes) == pytest.approx(v_g)
    cold = p.calculate(method="engineering", volume_liquid_pumped_ft3=v_l, pump_outlet_pressure_psig=200,
                       gas_temperature_f=0, pump_inefficiency=0)
    assert scf(cold) == pytest.approx((200 + 14.7) / 14.7 * 520 / 459.67 * v_l)        # 0 F, no inefficiency


def test_pump_direct_measurement_zero_pumps_and_dispositions():
    p = PneumaticPumpCalculator()
    assert scf(p.calculate(method="direct_measurement", measured_gas_scf=5000)) == 5000
    assert scf(p.calculate(pump_count=0)) == 0                                          # 0 pumps (was 1)
    vented = val(p.calculate(pump_count=1, operating_hours=1000), "ch4")
    assert val(p.calculate(pump_count=1, operating_hours=1000, disposition="recovered"), "ch4") == 0
    flared = p.calculate(pump_count=1, operating_hours=1000, disposition="flared", control_efficiency=0.9)
    assert val(flared, "ch4") == pytest.approx(vented * 0.1)
    pct = p.calculate(pump_count=1, operating_hours=1000, ch4_content=80, co2_content=3)
    assert val(pct, "co2") == pytest.approx(t_gas(23.6 * 1000, 0.03, 44.01))


@pytest.mark.parametrize("kwargs,match", [
    (dict(method="survey"), "Unknown pneumatic pump method"),
    (dict(pump_type="gear"), "Unknown pump type"),
    (dict(pump_count=-1), "cannot be negative"),
    (dict(method="engineering"), "volume_liquid_pumped_ft3 or volume_per_stroke_gal"),
    (dict(method="engineering", volume_liquid_pumped_ft3=10), "outlet pressure"),
    (dict(method="direct_measurement"), "measured_gas_scf"),
    (dict(disposition="sold"), "Unknown disposition"),
])
def test_pump_refusals(kwargs, match):
    with pytest.raises(ValueError, match=match):
        PneumaticPumpCalculator().calculate(**kwargs)


# ---------------------------------------------------------------- dehydration, Tables 6-17 / 6-18, Eq 6-17
def test_glycol_throughput_and_kimray_pump():
    g = GasDehydrationCalculator()
    res = g.calculate(gas_throughput_mmscf_yr=1000, has_gas_assisted_pump=True, ch4_content=80, co2_content=4)
    dehy = 1000 * 0.0052859 * 0.80 / 0.788
    pump = 1000 * 0.01903 * 0.80 / 0.788
    assert val(res, "ch4") == pytest.approx(dehy + pump)
    assert val(res, "co2") == pytest.approx(pump / 16.04 / 0.80 * 0.04 * 44.01)
    assert scf(res) == pytest.approx(1000 * (349.7 + 1258))
    per_day = g.calculate(gas_throughput_mmscfd=10, operating_days=100)
    assert val(per_day, "ch4") == pytest.approx(1000 * 0.0052859)
    assert val(g.calculate(gas_throughput_mmscfd=10, operating_days=0), "ch4") == 0     # 0 days (was 365)


def test_glycol_unit_factor():
    g = GasDehydrationCalculator()
    assert val(g.calculate(dehydrator_count=3), "ch4") == pytest.approx(3 * 0.06149)
    assert val(g.calculate(dehydrator_count=3, use_unit_factor=True, gas_throughput_mmscf_yr=5), "ch4") == pytest.approx(
        3 * 0.06149)
    assert val(g.calculate(dehydrator_count=0), "ch4") == 0                              # 0 units (was 1)


def test_desiccant_eq_6_17_exhibit_6_15():
    res = GasDehydrationCalculator().calculate(dehydrator_type="desiccant", vessel_height_ft=6.40, vessel_diameter_ft=1.60,
                                               vessel_pressure_psig=450, gas_void_fraction=0.45, changeouts_per_year=52,
                                               ch4_content=0.788)
    expected = 6.40 * 1.60 ** 2 * math.pi * 464.7 * 0.45 * 52 / (4 * 14.7)
    assert scf(res) == pytest.approx(expected)
    assert val(res, "ch4") == pytest.approx(t_gas(expected, 0.788))


@pytest.mark.parametrize("kwargs,match", [
    (dict(dehydrator_type="membrane"), "Unknown dehydrator type"),
    (dict(dehydrator_type="desiccant", vessel_height_ft=6, vessel_diameter_ft=1.6, vessel_pressure_psig=450,
          changeouts_per_year=52), "gas_void_fraction"),
    (dict(dehydrator_count=1, disposition="sold"), "Unknown disposition"),
])
def test_dehydration_refusals(kwargs, match):
    with pytest.raises(ValueError, match=match):
        GasDehydrationCalculator().calculate(**kwargs)


def test_dehydration_dispositions():
    g = GasDehydrationCalculator()
    vented = val(g.calculate(gas_throughput_mmscf_yr=100), "ch4")
    assert val(g.calculate(gas_throughput_mmscf_yr=100, disposition="recovered"), "ch4") == 0
    assert val(g.calculate(gas_throughput_mmscf_yr=100, disposition="flared"), "ch4") == pytest.approx(
        vented * 0.02)


def test_kimray_pump_without_co2():
    res = GasDehydrationCalculator().calculate(gas_throughput_mmscf_yr=100, has_gas_assisted_pump=True)
    assert val(res, "co2") == 0 and val(res, "ch4") == pytest.approx(100 * (0.0052859 + 0.01903))
