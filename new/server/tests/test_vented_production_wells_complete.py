"""calculations/vented_production_wells.py beyond tests/test_vented_production_compendium.py: every method, table
row, disposition and refusal, with values from API Compendium 2021 Tables 6-9, 6-12, 6-13 and 6-28 (whole gas
x CH4 mole fraction x 16.04 / 379.3 / 2204.62). Fixed while testing: a flare efficiency below 95 % was raised to
95 % (flared gas: all of it to the flare, the entered efficiency its destruction efficiency), 0 operating days counted as 365 and 0 PRVs as 1, unknown types took the first table row, and the CO2-EOR
density and mass fraction had invented defaults.
"""
import pytest

from calculations.vented_production_wells import (
    CasingGasVentCalculator,
    CO2EORVentingCalculator,
    ProductionNonRoutineVentingCalculator,
    WorkoverWithoutFracturingCalculator,
)

LB_T = 2204.6226218487757


def t_gas(scf, frac, mw=16.04):
    return scf * frac * mw / 379.3 / LB_T


def val(res, gas):
    r = res["results"][gas]
    return (r or {}).get("value", 0.0) if isinstance(r, dict) or r is None else r


# ---------------------------------------------------------------- workovers, Table 6-9
@pytest.mark.parametrize("well,scf,table_t", [("gas_well", 3114, 0.0470), ("oil_well", 122, 0.0018)])
def test_table_6_9(well, scf, table_t):
    res = WorkoverWithoutFracturingCalculator().calculate(workovers=4, well_type=well)
    assert val(res, "ch4") == pytest.approx(4 * t_gas(scf, 0.788))
    assert val(res, "ch4") / 4 == pytest.approx(table_t, rel=0.03)


def test_workover_dispositions():
    w = WorkoverWithoutFracturingCalculator()
    gross = t_gas(3114 * 10, 0.80)
    flared_90 = w.calculate(workovers=10, ch4_content=0.80, disposition="flared", control_efficiency=0.90)
    assert val(flared_90, "ch4") == pytest.approx(gross * 0.10)    # all flared at 90 % destruction (it became 95 %)
    flared_default = w.calculate(workovers=10, ch4_content=0.80, disposition="flared")
    assert val(flared_default, "ch4") == pytest.approx(gross * 0.02)  # 98 % destruction without an entry
    assert val(w.calculate(workovers=10, disposition="recovered"), "ch4") == 0
    partial = w.calculate(workovers=10, ch4_content=0.80, control_efficiency=0.5)
    assert val(partial, "ch4") == pytest.approx(gross * (0.5 + 0.5 * 0.02))


# ---------------------------------------------------------------- casing gas, Tables 6-12 / 6-13, Exhibit 6-10
@pytest.mark.parametrize("oil,scf_bbl,table", [("primary_heavy_oil", 210, 3.28), ("thermal_heavy_oil", 14.2, 0.223),
                                               ("crude_bitumen", 12.9, 0.207)])
def test_table_6_12_throughput(oil, scf_bbl, table):
    c = CasingGasVentCalculator()
    res = c.calculate(method="throughput", oil_type=oil, throughput=1000)
    assert val(res, "ch4") == pytest.approx(t_gas(1000 * scf_bbl, 0.816))
    # t CH4 / 1,000 bbl; bitumen's 12.9 scf/bbl gives 0.202, printed 0.207 (the table's own metric rounding)
    assert val(res, "ch4") == pytest.approx(table, rel=0.03)
    per_day = c.calculate(method="throughput", oil_type=oil, throughput=10, throughput_unit="bbl/day", operating_days=100)
    assert val(per_day, "ch4") == pytest.approx(val(res, "ch4"))
    rate = c.calculate(method="throughput", oil_type=oil, throughput_rate=10, operating_days=100)
    assert val(rate, "ch4") == pytest.approx(val(res, "ch4"))


def test_actual_vent_fraction_scales_the_factor():
    c = CasingGasVentCalculator()
    base = val(c.calculate(throughput=1000), "ch4")                                     # 63.2 % vented basis
    assert val(c.calculate(throughput=1000, actual_vent_fraction=31.6), "ch4") == pytest.approx(base / 2)
    assert val(c.calculate(throughput=1000, actual_vent_fraction=0.316), "ch4") == pytest.approx(base / 2)


@pytest.mark.parametrize("status,scf_day,table", [("active_wells", 1310, 0.0205), ("suspended_wells", 710, 0.0111)])
def test_table_6_13_well_basis(status, scf_day, table):
    res = CasingGasVentCalculator().calculate(method="well_count", well_status=status, well_count=3, operating_days=10)
    assert val(res, "ch4") == pytest.approx(30 * t_gas(scf_day, 0.816))
    assert val(res, "ch4") / 30 == pytest.approx(table, rel=0.01)


def test_migration_and_direct_measurement():
    c = CasingGasVentCalculator()
    mig = c.calculate(method="migration", well_count=1, operating_days=1)
    assert val(mig, "ch4") == pytest.approx(0.00213, rel=0.01)                          # 3.85 m3 gas / well-day
    m3 = c.calculate(method="direct_measurement", measured_gas_volume=1000, volume_unit="m3", ch4_content=0.9,
                     co2_content=0.05)
    scf = c.calculate(method="direct_measurement", measured_gas_volume=1000 * 35.3147, ch4_content=0.9, co2_content=0.05)
    assert val(m3, "ch4") == pytest.approx(val(scf, "ch4"), rel=1e-4)
    assert val(scf, "co2") == pytest.approx(t_gas(35314.7, 0.05, 44.01), rel=1e-4)
    assert val(c.calculate(method="well_count", well_count=5, operating_days=0), "ch4") == 0   # 0 days (was 365)


def test_casing_dispositions():
    c = CasingGasVentCalculator()
    assert val(c.calculate(throughput=1000, disposition="recovered"), "ch4") == 0
    gross = t_gas(210_000, 0.816)
    assert val(c.calculate(throughput=1000, disposition="flared", control_efficiency=0.9), "ch4") == pytest.approx(
        gross * 0.1)


@pytest.mark.parametrize("kwargs,match", [
    (dict(method="satellite"), "Unknown casing gas method"),
    (dict(throughput=1, oil_type="light_oil"), "Unknown oil type"),
    (dict(throughput=1, throughput_unit="m3/day"), "Unknown throughput unit"),
    (dict(method="well_count", well_count=1, well_status="shut_in"), "Unknown well status"),
    (dict(method="direct_measurement", measured_gas_volume=1, volume_unit="Mscf"), "Unknown volume unit"),
    (dict(method="well_count", well_count=1, operating_days=-1), "cannot be negative"),
    (dict(throughput=1, disposition="sold"), "Unknown disposition"),
])
def test_casing_refusals(kwargs, match):
    with pytest.raises(ValueError, match=match):
        CasingGasVentCalculator().calculate(**kwargs)


def test_workover_refusals():
    with pytest.raises(ValueError, match="Unknown well type"):
        WorkoverWithoutFracturingCalculator().calculate(workovers=1, well_type="injector")


# ---------------------------------------------------------------- CO2 EOR, Equations 6-26 / 6-27
def test_eor_blowdown_in_ft3_and_percent_fraction():
    e = CO2EORVentingCalculator()
    ft3 = e.calculate(events=2, physical_volume_ft3=36.4 * 35.3147, co2_density_kg_m3=650, co2_weight_fraction=98.5)
    assert val(ft3, "co2") == pytest.approx(2 * 36.4 * 650 * 0.985 * 0.001, rel=1e-4)


@pytest.mark.parametrize("kwargs,match", [
    (dict(physical_volume_m3=36.4, co2_weight_fraction=0.985), "co2_density_kg_m3"),
    (dict(physical_volume_m3=36.4, co2_density_kg_m3=650), "co2_weight_fraction"),
    (dict(co2_density_kg_m3=650, co2_weight_fraction=0.985), "physical_volume_m3 or physical_volume_ft3"),
    (dict(activity="flaring"), "Unknown CO2 EOR activity"),
])
def test_eor_refusals(kwargs, match):
    with pytest.raises(ValueError, match=match):
        CO2EORVentingCalculator().calculate(**kwargs)


# ---------------------------------------------------------------- non-routine, Table 6-28 / Equation 6-28
def test_table_6_28_and_co2_from_the_ratio():
    n = ProductionNonRoutineVentingCalculator()
    esd = n.calculate(source_type="esd_platform", equipment_count=2)
    assert val(esd, "ch4") == pytest.approx(2 * 4.9276)
    with_co2 = n.calculate(source_type="prv", equipment_count=10, ch4_content=0.80, co2_content=0.05)
    ch4_t = 10 * 0.00065 * 0.80 / 0.788
    assert val(with_co2, "ch4") == pytest.approx(ch4_t)
    assert val(with_co2, "co2") == pytest.approx(10 * 43.0 * 0.05 * 44.01 / 379.3 / 2204.62262)  # Table 6-28 scf/yr
    assert val(n.calculate(source_type="prv", equipment_count=0), "ch4") == 0          # 0 PRVs (was 1)


def test_equation_6_28_event():
    n = ProductionNonRoutineVentingCalculator()
    res = n.calculate(source_type="event", vent_rate_scfm=50, duration_minutes=30, events=4, ch4_content=0.85,
                      co2_content=0.02)
    assert val(res, "ch4") == pytest.approx(t_gas(50 * 30 * 4, 0.85))
    assert val(res, "co2") == pytest.approx(t_gas(50 * 30 * 4, 0.02, 44.01))
    assert val(n.calculate(vent_rate_scfm=50, duration_minutes=30, events=None), "ch4") == pytest.approx(
        t_gas(1500, 0.788))
    assert val(n.calculate(vent_rate_scfm=50, duration_minutes=30, disposition="recovered"), "ch4") == 0
    flared = n.calculate(vent_rate_scfm=50, duration_minutes=30, disposition="flared")
    assert val(flared, "ch4") == pytest.approx(t_gas(1500, 0.788) * 0.02)
    with pytest.raises(ValueError, match="Unknown non-routine source"):
        n.calculate(source_type="blowdown")


@pytest.mark.parametrize("calc,kwargs", [
    (WorkoverWithoutFracturingCalculator, dict(workovers=3)),
    (CasingGasVentCalculator, dict(throughput=1000)),
    (ProductionNonRoutineVentingCalculator, dict(vent_rate_scfm=10, duration_minutes=60)),
])
def test_composition_above_one_is_percent(calc, kwargs):
    frac = calc().calculate(ch4_content=0.85, co2_content=0.02, **kwargs)
    pct = calc().calculate(ch4_content=85, co2_content=2, **kwargs)
    assert (val(pct, "ch4"), val(pct, "co2")) == pytest.approx((val(frac, "ch4"), val(frac, "co2")))


def test_workover_keeps_an_entered_uncertainty():
    res = WorkoverWithoutFracturingCalculator().calculate(workovers=3, uncertainties={"ch4": 0.25})
    table = WorkoverWithoutFracturingCalculator().calculate(workovers=3)
    assert res["results"]["ch4"]["uncertainty"] != table["results"]["ch4"]["uncertainty"]
