"""calculations/vented_unloading.py and the dispatcher's unloading routes: every Table 6-10 / 6-11 row, Equations
6-3, 6-10 and 6-11, unit and refusal. Values from API Compendium 2021 section 6.3.4. Fixed while testing: an
unknown lift type was plunger lift, an unknown region / frequency class / depth or diameter unit fell back to a
default, 0 events or 0 wells became 1 (or the record quantity), and the engineering methods had an invented 85 %
CH4 default.
"""
import math

import pytest

from calculations.units import CONVERSIONS, STD_TEMP_K
from calculations.vented_unloading import LiquidsUnloadingCalculator

T_CH4 = 16.04 / (379.3 * 2204.6226218)
T_CO2 = 44.01 / (379.3 * 2204.6226218)


def val(res, gas):
    r = res["results"][gas]
    return (r or {}).get("value", 0.0) if isinstance(r, dict) or r is None else r


@pytest.fixture
def u():
    return LiquidsUnloadingCalculator()


# ---------------------------------------------------------------- Tier 1, Table 6-11
@pytest.mark.parametrize("utype,t,scf", [("plunger", 1.774, 113466), ("Non-Plunger", 2.792, 178531),
                                         ("without plunger", 2.792, 178531), ("", 1.774, 113466)])
def test_table_6_11(u, utype, t, scf):
    res = u.calculate_tier1(well_count=3, unloading_type=utype)
    assert val(res, "ch4") == pytest.approx(3 * t)
    site = u.calculate_tier1(well_count=3, unloading_type=utype, ch4_content=0.90, co2_content=0.03)
    assert val(site, "ch4") == pytest.approx(3 * scf * 0.90 * T_CH4)
    assert val(site, "co2") == pytest.approx(3 * scf * 0.03 * T_CO2)


def test_tier1_zero_wells_and_control(u):
    assert u.calculate_tier1(well_count=0)["total_co2e"] == 0
    flared = u.calculate_tier1(well_count=1, control_efficiency=0.9)
    assert val(flared, "ch4") == pytest.approx(1.774 * (0.1 + 0.9 * 0.02))


@pytest.mark.parametrize("kwargs,match", [
    (dict(well_count=None), "Number of wells is required"), (dict(well_count=""), "Number of wells is required"),
    (dict(well_count="many"), "Invalid well count"), (dict(well_count=-1), "cannot be negative"),
    (dict(well_count=200000), "Unrealistic number of wells"), (dict(well_count=1, unloading_type="gas_lift"),
                                                               "Unknown unloading type"),
    (dict(well_count=1, ch4_content="x"), "Invalid numeric value"), (dict(well_count=1, ch4_content=-1), "cannot be negative"),
    (dict(well_count=1, ch4_content=150), "cannot exceed 100%"), (dict(well_count=1, ch4_content=0.9, co2_content=0.2),
                                                                  "cannot exceed 100%"),
])
def test_tier1_refusals(u, kwargs, match):
    with pytest.raises(ValueError, match=match):
        u.calculate_tier1(**kwargs)


# ---------------------------------------------------------------- Tier 2, Table 6-10 averages
@pytest.mark.parametrize("utype,events,cat", [
    ("plunger", 50, "plunger_le100"), ("plunger", 150, "plunger_gt100"), ("non_plunger", 5, "non_plunger_le10"),
    ("non_plunger", 30, "non_plunger_10_to_50"), ("non_plunger", 80, "non_plunger_gt50"),
])
def test_table_6_10_average_by_frequency(u, utype, events, cat):
    row = u.TABLE_6_10_AVERAGE[cat]
    res = u.calculate_tier2(events=events, unloading_type=utype, well_count=2)
    assert val(res, "ch4") == pytest.approx(2 * events * row["tonnes_ch4_event"])
    site = u.calculate_tier2(events=events, unloading_type=utype, well_count=2, ch4_content=0.80, co2_content=0.02)
    assert val(site, "ch4") == pytest.approx(2 * events * row["scf_gas_event"] * 0.80 * T_CH4)
    assert val(site, "co2") == pytest.approx(2 * events * row["scf_gas_event"] * 0.02 * T_CO2)


@pytest.mark.parametrize("region", ["appalachia", "Gulf Coast", "midcontinent", "rocky-mountain"])
def test_table_6_10_regional(u, region):
    rows = u.TABLE_6_10_REGIONAL[region.lower().replace(" ", "_").replace("-", "_")]
    for utype, events, key in (("plunger", 50, "plunger_le100"), ("plunger", 150, "plunger_gt100"),
                               ("non_plunger", 20, "non_plunger")):
        res = u.calculate_tier2(events=events, unloading_type=utype, region=region)
        assert val(res, "ch4") == pytest.approx(events * rows[key]["tonnes_ch4"]), (region, key)
    explicit = u.calculate_tier2(events=500, unloading_type="plunger", region=region, frequency_category="plunger_le100")
    assert val(explicit, "ch4") == pytest.approx(500 * rows["plunger_le100"]["tonnes_ch4"])


def test_tier2_explicit_class_zero_events_and_average_names(u):
    res = u.calculate_tier2(events=5, unloading_type="non_plunger", frequency_category="non_plunger_gt50")
    assert val(res, "ch4") == pytest.approx(5 * 0.670)
    assert u.calculate_tier2(events=0)["total_co2e"] == 0
    for name in ("average", "US Average", "national", ""):
        assert val(u.calculate_tier2(events=10, region=name), "ch4") == pytest.approx(10 * 0.185)


@pytest.mark.parametrize("kwargs,match", [
    (dict(events=None), "unloading events is required"), (dict(events="x"), "Invalid unloading events"),
    (dict(events=-1), "cannot be negative"), (dict(events=1, well_count=0), "greater than zero"),
    (dict(events=1, region="permian"), "Unknown Table 6-10 region"),
    (dict(events=1, frequency_category="weekly"), "Unknown Table 6-10 frequency class"),
    (dict(events=1, ch4_content=0.9, co2_content=0.2), "cannot exceed 100%"),
])
def test_tier2_refusals(u, kwargs, match):
    with pytest.raises(ValueError, match=match):
        u.calculate_tier2(**kwargs)


# ---------------------------------------------------------------- Equation 6-10
def eq_6_10(ev, d_in, depth_ft, p_psig, sfr, hr, x):
    z = 1.0 if hr >= 1 else 0.0
    return ev * 0.37e-3 * d_in ** 2 * depth_ft * p_psig + ev * sfr * max(0.0, hr - x) * z


@pytest.mark.parametrize("utype,x", [("plunger", 0.5), ("non_plunger", 1.0)])
def test_equation_6_10(u, utype, x):
    res = u.calculate_tier3_equation_6_10(events=12, well_depth=8500, diameter=4.5, pressure=800, sfr=1000,
                                          hours_open=3, unloading_type=utype, well_count=2, ch4_content=0.87,
                                          co2_content=0.015)
    vr = eq_6_10(12, 4.5, 8500, 800, 1000, 3, x)
    assert res["inputs"]["vr_per_well_scf"] == pytest.approx(vr)
    assert val(res, "ch4") == pytest.approx(2 * vr * 0.87 * T_CH4)
    short = u.calculate_tier3_equation_6_10(events=12, well_depth=8500, diameter=4.5, pressure=800, sfr=1000,
                                            hours_open=0.5, unloading_type=utype, ch4_content=0.87)
    assert short["inputs"]["vr_per_well_scf"] == pytest.approx(eq_6_10(12, 4.5, 8500, 800, 1000, 0.5, x))  # Z = 0


@pytest.mark.parametrize("diam,unit", [(114.3, "mm"), (11.43, "cm"), (0.1143, "m"), (0.375, "ft"), (4.5, "inches")])
def test_equation_6_10_diameter_units(u, diam, unit):
    res = u.calculate_tier3_equation_6_10(events=1, well_depth=1000, diameter=diam, diameter_unit=unit, pressure=100,
                                          ch4_content=0.9)
    assert res["inputs"]["diameter_in"] == pytest.approx(4.5, rel=1e-4)


def test_equation_6_10_depth_in_km_and_zero_activity(u):
    res = u.calculate_tier3_equation_6_10(events=1, well_depth=1.524, depth_unit="km", diameter=2, pressure=100,
                                          ch4_content=0.9)
    assert res["inputs"]["depth_ft"] == pytest.approx(5000, rel=1e-4)
    zero = u.calculate_tier3_equation_6_10(events=0, well_depth=1000, diameter=2, pressure=100, ch4_content=0.9)
    assert zero["total_co2e"] == 0


@pytest.mark.parametrize("kwargs,match", [
    (dict(well_depth=0), "Well depth must be greater than zero"), (dict(diameter=0), "diameter must be greater"),
    (dict(pressure=None), "Flow-line pressure is required"), (dict(events=-1), "cannot be negative"),
    (dict(diameter=80), "Unrealistic well diameter"), (dict(well_depth=60000), "Unrealistic well depth"),
    (dict(diameter_unit="yd"), "Unknown diameter unit"), (dict(depth_unit="yd"), "Unknown depth unit"),
    (dict(ch4_content=None), "gas CH4 content"), (dict(well_count=0), "greater than zero"),
    (dict(ch4_content=0.9, co2_content=0.2), "cannot exceed 100%"),
])
def test_equation_6_10_refusals(u, kwargs, match):
    base = dict(events=1, well_depth=1000, diameter=2, pressure=100, ch4_content=0.9)
    with pytest.raises(ValueError, match=match):
        u.calculate_tier3_equation_6_10(**{**base, **kwargs})


# ---------------------------------------------------------------- Equation 6-11
def test_equation_6_11(u):
    res = u.calculate_tier3_equation_6_11(p_shut=300, p_line=150, p_sep=100, sfr_p=500, t_p=0.5, events=20, well_count=3,
                                          ch4_content=0.85, co2_content=0.01)
    vr = math.sqrt(300 - 14.696) / math.sqrt(150 - 100) * 500 * 0.5
    assert res["inputs"]["vr_per_event_scf"] == pytest.approx(vr)
    assert val(res, "ch4") == pytest.approx(vr * 60 * 0.85 * T_CH4)
    gauge = u.calculate_tier3_equation_6_11(p_shut=285.304, p_line=135.304, p_sep=85.304, sfr_p=500, t_p=0.5, events=20,
                                            well_count=3, ch4_content=0.85, press_unit="psig")
    assert gauge["inputs"]["vr_per_event_scf"] == pytest.approx(vr, rel=1e-4)
    for kw in (dict(events=0), dict(sfr_p=0), dict(t_p=0)):
        z = u.calculate_tier3_equation_6_11(**{**dict(p_shut=300, p_line=150, p_sep=100, sfr_p=500, t_p=0.5,
                                                    ch4_content=0.85), **kw})
        assert z["total_co2e"] == 0


@pytest.mark.parametrize("kwargs,match", [
    (dict(p_shut=None), "Pressures"), (dict(sfr_p=None), "SFRp is required"), (dict(t_p=None), "Tp is required"),
    (dict(events=-1), "cannot be negative"), (dict(well_count=0), "greater than zero"),
    (dict(p_shut=10), "Shut-in pressure"), (dict(p_line=90), "Line pressure"),
    (dict(ch4_content=None), "gas CH4 content"), (dict(ch4_content=0.9, co2_content=0.2), "cannot exceed 100%"),
])
def test_equation_6_11_refusals(u, kwargs, match):
    base = dict(p_shut=300, p_line=150, p_sep=100, sfr_p=500, t_p=0.5, ch4_content=0.85)
    with pytest.raises(ValueError, match=match):
        u.calculate_tier3_equation_6_11(**{**base, **kwargs})


# ---------------------------------------------------------------- volume-based (Eq 6-3 wellbore decompression)
def vol_std_m3(d_m, depth_m, p_psig, t_k=STD_TEMP_K, z=1.0):
    return math.pi / 4 * d_m ** 2 * depth_m * (p_psig / 14.696) * (STD_TEMP_K / t_k) / z


@pytest.mark.parametrize("diam,unit,d_m", [(4.5, "in", 0.1143), (114.3, "mm", 0.1143), (11.43, "cm", 0.1143),
                                           (0.1143, "m", 0.1143), (0.375, "ft", 0.1143)])
def test_volume_based_units(u, diam, unit, d_m):
    res = u.calculate_volume_based(well_depth=1000, depth_unit="m", diameter=diam, diameter_unit=unit, pressure=200,
                                   ch4_content=0.9, co2_content=0.02, events=3, well_count=2, temp_unit="K",
                                   operating_temperature=STD_TEMP_K)
    v = vol_std_m3(d_m, 1000, 200) * 6
    assert val(res, "ch4") == pytest.approx(v * 0.9 * CONVERSIONS["density_ch4"] / 1000, rel=1e-4)
    assert val(res, "co2") == pytest.approx(v * 0.02 * CONVERSIONS["density_co2"] / 1000, rel=1e-4)


def test_volume_based_depth_km_ft_and_z(u):
    km = u.calculate_volume_based(well_depth=1, depth_unit="km", diameter=4.5, pressure=200, ch4_content=0.9, events=1,
                                  temp_unit="K", operating_temperature=STD_TEMP_K, z_factor=0.9)
    assert val(km, "ch4") == pytest.approx(vol_std_m3(0.1143, 1000, 200, z=0.9) * 0.9 * CONVERSIONS["density_ch4"] / 1000,
                                           rel=1e-4)
    ft = u.calculate_volume_based(well_depth=3280.84, diameter=4.5, pressure=200, ch4_content=0.9, events=1,
                                  temp_unit="K", operating_temperature=STD_TEMP_K, z_factor=0)    # z 0 is not valid: 1
    assert val(ft, "ch4") == pytest.approx(vol_std_m3(0.1143, 1000, 200) * 0.9 * CONVERSIONS["density_ch4"] / 1000,
                                           rel=1e-4)


@pytest.mark.parametrize("kwargs,match", [
    (dict(diameter=0), "diameter must be greater than zero"), (dict(well_depth=0), "depth must be greater than zero"),
    (dict(diameter_unit="yd"), "Unknown diameter unit"), (dict(depth_unit="yd"), "Unknown depth unit"),
    (dict(events=-1), "cannot be negative"), (dict(well_count=0), "greater than zero"),
    (dict(ch4_content=None), "gas CH4 content"), (dict(ch4_content=0.9, co2_content=0.2), "cannot exceed 100%"),
])
def test_volume_based_refusals(u, kwargs, match):
    base = dict(well_depth=1000, diameter=4.5, pressure=200, ch4_content=0.9, events=1)
    with pytest.raises(ValueError, match=match):
        u.calculate_volume_based(**{**base, **kwargs})


# ---------------------------------------------------------------- the router and the dispatcher
def test_router_paths_keep_an_entered_zero(u):
    eq11 = u.calculate(method="eq_6_11", p_shut=300, p_line=150, p_sep=100, sfr_p=500, t_p=0.5, events=0, ch4_content=0.85)
    assert eq11["total_co2e"] == 0                                                           # 0 events, not 1
    eq11_default = u.calculate(p_shut=300, p_line=150, p_sep=100, sfr=500, hours_open=0.5, ch4_content=0.85)
    assert eq11_default["inputs"]["events"] == 1
    eq10 = u.calculate(method="eq_6_10", unload_events=0, unload_depth=1000, unload_diam=2, unload_press=100, sfr=1,
                       hours_open=0.5, ch4_content=0.9)
    assert eq10["total_co2e"] == 0
    eq10_wells = u.calculate(sfr=1000, hours_open=3, well_depth=1000, diameter=2, pressure=100, events=2, wells=3,
                             ch4_content=0.9)
    assert eq10_wells["inputs"]["well_count"] == 3
    t1 = u.calculate(tier="tier1", well_count=0)
    assert t1["total_co2e"] == 0                                                             # 0 wells, not 1
    t1_amount = u.calculate(method="per_well", amount=2)
    assert val(t1_amount, "ch4") == pytest.approx(2 * 1.774)
    t2 = u.calculate(tier="2", unload_freq=0)
    assert t2["total_co2e"] == 0
    t2_amount = u.calculate(uncertainties={"_factor_source": "custom"}, amount=10, wells=2)
    assert val(t2_amount, "ch4") == pytest.approx(20 * 0.185)


def test_dispatcher_keeps_an_entered_zero():
    from calculations.dispatcher import CalculationDispatcher

    d = CalculationDispatcher()
    t2 = d.dispatch("unloading", {"factor_source": "custom", "tier": "tier2", "events": 0, "amount": 12, "unit": "events",
                                  "unloading_type": "plunger"}, {}, {})
    assert t2["total_co2e"] == 0                                         # 0 events (it took the record's 12)
    with pytest.raises(ValueError, match="greater than zero"):
        d.dispatch("unloading", {"factor_source": "custom", "tier": "tier2", "events": 5, "well_count": 0, "unit": "events"},
                   {}, {})


def test_percent_composition_and_rate_units(u):
    pct = u.calculate_tier1(well_count=1, ch4_content=90, co2_content=3)
    frac = u.calculate_tier1(well_count=1, ch4_content=0.90, co2_content=0.03)
    assert (val(pct, "ch4"), val(pct, "co2")) == pytest.approx((val(frac, "ch4"), val(frac, "co2")))
    mcfd = u.calculate_tier3_equation_6_10(events=2, well_depth=1000, diameter=2, pressure=100, sfr=24, sfr_unit="Mcf/day",
                                           hours_open=3, ch4_content=0.9)
    assert mcfd["inputs"]["sfr_scf_hr"] == pytest.approx(1000, rel=1e-4)
    with pytest.raises(ValueError, match="Flow-line rate unit"):
        u.calculate_tier3_equation_6_10(events=2, well_depth=1000, diameter=2, pressure=100, sfr=24, sfr_unit="kg/hr",
                                        hours_open=3, ch4_content=0.9)
