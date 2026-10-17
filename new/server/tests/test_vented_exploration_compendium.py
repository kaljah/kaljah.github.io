"""calculations/vented_exploration.py: well testing (API Compendium 2021 section 6.2.2) and coal seam drilling
(section 6.2.4, Exhibit 6-5). Neither calculator has a dispatcher route today (the platform's well testing goes
through ActivityFactorCalculator), so these tests pin the equations should they be wired in.

Hand values: 379.3 scf/lbmol, CH4 16.04, CO2 44.01 lb/lbmol, 2,204.62 lb/tonne.
"""
import pytest

from calculations.vented_exploration import CoalSeamDrillingCalculator, WellTestingCalculator

GWP = {"CO2": 1.0, "CH4": 28.0, "N2O": 265.0}


def gas_t(scf, frac, mw):
    return scf / 379.3 * frac * mw / 2204.62


def val(res, gas):
    r = res["results"].get(gas)
    return (r or {}).get("value", 0.0) if isinstance(r, dict) else (r or 0.0)


@pytest.fixture
def wt():
    return WellTestingCalculator()


@pytest.mark.parametrize("well,scf,table_t", [("gas_well", 46625.0, 0.7288), ("oil_well", 3613.0, 0.0565)])
def test_tier1_table_6_4(wt, well, scf, table_t):
    res = wt.calculate(tier="tier1", well_type=well, events=3, gwp_dict=GWP)
    assert val(res, "ch4") == pytest.approx(3 * gas_t(scf, 0.816, 16.04), rel=1e-5)
    assert val(res, "ch4") / 3 == pytest.approx(table_t, rel=5e-3)        # the table's rounded factor


def test_tier2_gas_well_equation_6_1(wt):
    res = wt.calculate(tier="tier2", well_type="gas_well", gas_production_rate=100_000, rate_unit="scf/day",
                       test_duration_hours=48, ch4_content=85, co2_content=2, gwp_dict=GWP)
    assert val(res, "ch4") == pytest.approx(gas_t(200_000, 0.85, 16.04), rel=1e-5)
    assert val(res, "co2") == pytest.approx(gas_t(200_000, 0.02, 44.01), rel=1e-5)
    mcf = wt.calculate(tier="tier2", well_type="gas_well", gas_production_rate=100, rate_unit="mcf/day",
                       test_duration_days=2, ch4_content=85, co2_content=2, gwp_dict=GWP)
    assert val(mcf, "ch4") == pytest.approx(val(res, "ch4"), rel=1e-5)


def test_tier2_oil_well_equation_6_3(wt):
    res = wt.calculate(tier="tier2", well_type="oil_well", gor=500, oil_production_rate=100, test_duration_days=3,
                       ch4_content=80, gwp_dict=GWP)
    assert val(res, "ch4") == pytest.approx(gas_t(150_000, 0.80, 16.04), rel=1e-5)
    total = wt.calculate(tier="tier2", well_type="oil_well", gor=500, oil_production_total=300, ch4_content=80, gwp_dict=GWP)
    assert val(total, "ch4") == pytest.approx(val(res, "ch4"), rel=1e-5)


def test_tier3_metered_volume_equation_6_2(wt):
    a = wt.calculate(tier="tier3", measured_gas_volume=50, volume_unit="mcf", ch4_content=90, gwp_dict=GWP)
    b = wt.calculate(tier="tier3", measured_gas_volume=50_000, volume_unit="scf", ch4_content=90, gwp_dict=GWP)
    assert val(a, "ch4") == pytest.approx(gas_t(50_000, 0.90, 16.04), rel=1e-5)
    assert val(b, "ch4") == pytest.approx(val(a, "ch4"), rel=1e-5)
    auto = wt.calculate(measured_gas_volume=50_000, ch4_content=90, gwp_dict=GWP)   # a metered volume means Tier 3
    assert val(auto, "ch4") == pytest.approx(val(a, "ch4"), rel=1e-5)


def test_dispositions(wt):
    base = dict(tier="tier3", measured_gas_volume=100_000, ch4_content=90, co2_content=5, gwp_dict=GWP)
    vented = wt.calculate(**base, disposition="vented")
    flared = wt.calculate(**base, disposition="flared")
    recovered = wt.calculate(**base, disposition="recovered")
    assert val(vented, "ch4") == pytest.approx(gas_t(100_000, 0.90, 16.04), rel=1e-5)
    assert 0 < val(flared, "ch4") < val(vented, "ch4") * 0.05            # most methane destroyed
    assert val(flared, "co2") > val(vented, "co2")                        # and turned into CO2
    assert val(recovered, "ch4") == pytest.approx(0.0, abs=1e-12)
    split = wt.calculate(**base, disposition="split", frac_vented=0.5, frac_flared=0.0, frac_recovered=0.5)
    assert val(split, "ch4") == pytest.approx(val(vented, "ch4") * 0.5, rel=1e-5)


@pytest.mark.parametrize("kwargs,match", [
    (dict(tier="tier3", measured_gas_volume=-1), "non-negative"),
    (dict(tier="tier2", well_type="gas_well", gas_production_rate=1000), "positive duration"),
    (dict(tier="tier2", well_type="oil_well", gor=500), "oil_production_rate or oil_production_total"),
    (dict(tier="tier2", well_type="oil_well", gor=500, oil_production_rate=10), "positive duration"),
    (dict(tier="tier1", ch4_content=80, co2_content=30), "cannot exceed 100%"),
    (dict(tier="tier1", disposition="split", frac_vented=0.7, frac_flared=0.5), "cannot exceed 1.0"),
])
def test_refusals(wt, kwargs, match):
    with pytest.raises(ValueError, match=match):
        wt.calculate(gwp_dict=GWP, **kwargs)


def test_zero_events_and_volume_are_zero(wt):
    assert val(wt.calculate(tier="tier1", events=0, gwp_dict=GWP), "ch4") == 0
    assert val(wt.calculate(tier="tier3", measured_gas_volume=0, gwp_dict=GWP), "ch4") == 0


# ---------------------------------------------------------------- coal seam drilling, Exhibit 6-5
def test_coal_seam_drilling_material_balance():
    calc = CoalSeamDrillingCalculator()
    res = calc.calculate(drilling_gas_vented_scf=1_000_000, gwp_dict=GWP)
    assert val(res, "ch4") == pytest.approx(gas_t(1_000_000, 0.887, 16.04), rel=1e-5)   # 88.7 mol % default
    assert val(res, "co2") == pytest.approx(gas_t(1_000_000, 0.109, 44.01), rel=1e-5)   # 10.9 mol % default
    wells = calc.calculate(wells_data=[{"duration_days": 5, "gas_consumption_mmscf_day": 1.5},
                                       {"days": 3, "rate_mmscf": 2.0}], gwp_dict=GWP)
    assert val(wells, "ch4") == pytest.approx(gas_t(13_500_000, 0.887, 16.04), rel=1e-5)


def test_coal_seam_well_test_flaring():
    calc = CoalSeamDrillingCalculator()
    res = calc.calculate(drilling_gas_vented_scf=0, well_testing_gas_flared_scf=100_000, gwp_dict=GWP)
    moles = 100_000 / 379.3
    assert val(res, "ch4") == pytest.approx(moles * 0.887 * 0.02 * 16.04 / 2204.62, rel=1e-5)
    assert val(res, "co2") == pytest.approx(moles * (0.887 * 0.98 + 0.109) * 44.01 / 2204.62, rel=1e-5)
    assert val(res, "n2o") == pytest.approx(100_000 * 1020 / 1e6 * 0.0001 / 1000, rel=1e-5)
    assert val(calc.calculate(drilling_gas_vented_scf=0, gwp_dict=GWP), "ch4") == 0
