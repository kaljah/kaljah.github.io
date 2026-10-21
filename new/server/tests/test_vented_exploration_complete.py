"""calculations/vented_exploration.py (no dispatcher route; kept and tested, see docs/CALCULATION_PIPELINE_MEMORY.md):
every tier, unit, disposition and refusal of WellTestingCalculator (API Compendium 2021 section 6.2.2, Table 6-4,
Equations 6-1 to 6-3) and CoalSeamDrillingCalculator (section 6.2.4, Exhibit 6-5). Fixed while testing: unknown
units, well types and dispositions were read as scf, scf/day, scf/bbl, bbl/day, an oil well and vented; Tier 2 / 3
gas took the Table 6-4 composition (81.6 % CH4); a flare formed CO2 at 98 % (96.5 % since December 2025)."""
import pytest

from calculations.units import convert
from calculations.vented_exploration import CoalSeamDrillingCalculator, WellTestingCalculator

LB = 2204.6226218487757


def val(res, gas):
    r = res["results"][gas]
    return r["value"] if isinstance(r, dict) else (r or 0.0)


def tonnes(scf, frac, mw):
    return scf / 379.3 * frac * mw / LB


@pytest.fixture
def w():
    return WellTestingCalculator()


def test_tier1_table_6_4(w):
    gas = w.calculate(well_type="gas_well", events=2)
    assert val(gas, "ch4") == pytest.approx(2 * tonnes(46625, 0.816, 16.04))
    assert val(w.calculate(), "ch4") == pytest.approx(tonnes(3613, 0.816, 16.04))              # oil well default
    assert val(w.calculate(events=None), "ch4") == pytest.approx(tonnes(3613, 0.816, 16.04))


@pytest.mark.parametrize("unit,scf", [("scf", 1000), ("Mcf", 1e6), ("MMscf", 1e9), ("m3", convert(1000, "m3", "scf"))])
def test_tier3_metered_volume(w, unit, scf):
    res = w.calculate(measured_gas_volume=1000, volume_unit=unit, ch4_content=80, co2_content="2%")
    assert res["inputs"]["tier"] == "tier3"
    assert val(res, "ch4") == pytest.approx(tonnes(scf, 0.80, 16.04))
    assert val(res, "co2") == pytest.approx(tonnes(scf, 0.02, 44.01))


@pytest.mark.parametrize("unit,per_day", [
    ("scf/day", 1000), ("Mcf/day", 1e6), ("MMscf/day", 1e9), ("scf/hr", 24_000), ("m3/day", convert(1000, "m3", "scf")),
    ("m3/hr", convert(24_000, "m3", "scf")),
])
def test_tier2_gas_well_rate_units(w, unit, per_day):
    res = w.calculate(well_type="gas", gas_production_rate=1000, rate_unit=unit, test_duration_hours=48,
                      ch4_content=0.8)
    assert res["inputs"]["total_gas_scf"] == pytest.approx(per_day * 2)


def test_tier2_oil_well_gor(w):
    total = w.calculate(gor=500, oil_production_total=100, ch4_content=80, events=2)
    assert total["inputs"]["total_gas_scf"] == pytest.approx(100_000)
    rate = w.calculate(gor=500, oil_production_rate=50, test_duration_days=2, ch4_content=80)
    assert rate["inputs"]["total_gas_scf"] == pytest.approx(50_000)
    m3 = w.calculate(gor=1, gor_unit="m3/m3", oil_production_rate=1, oil_rate_unit="m3/day", test_duration_days=1,
                     ch4_content=80)
    assert m3["inputs"]["total_gas_scf"] == pytest.approx(convert(1, "m3", "scf"))
    assert w.calculate(tier="engineering", gor=500, oil_production_total=10, ch4_content=80)["inputs"]["tier"] \
        == "engineering"


def test_dispositions(w):
    base = dict(measured_gas_volume=1_000_000, ch4_content=80, co2_content=5)
    ch4, co2 = tonnes(1e6, 0.80, 16.04), tonnes(1e6, 0.05, 44.01)
    flared = w.calculate(**base, disposition="flared")
    assert val(flared, "ch4") == pytest.approx(ch4 * 0.02)
    assert val(flared, "co2") == pytest.approx(co2 + ch4 * 0.965 * 44.01 / 16.04)
    assert val(flared, "n2o") > 0
    assert val(w.calculate(**base, disposition="sales"), "ch4") == 0
    assert val(w.calculate(**base, control_efficiency=0.5), "ch4") == pytest.approx(ch4 * 0.5 + ch4 * 0.5 * 0.02)
    split = w.calculate(**base, frac_vented=0.2, frac_flared=0.3, frac_recovered=0.5)
    assert val(split, "ch4") == pytest.approx(ch4 * 0.2 + ch4 * 0.3 * 0.02)
    none = w.calculate(**base, frac_recovered=1.0)
    assert val(none, "ch4") == 0


@pytest.mark.parametrize("kw,match", [
    (dict(well_type="water"), "Unknown well type"),
    (dict(well_type="oil and gas"), "Unknown well type"),
    (dict(events=-1), "cannot be negative"),
    (dict(ch4_content=150), "ch4_content must be between"),
    (dict(ch4_content=-1), "ch4_content must be between"),
    (dict(co2_content=150), "co2_content must be between"),
    (dict(ch4_content=90, co2_content=20), "cannot exceed 100%"),
    (dict(tier="tier3", ch4_content=80), "requires non-negative measured_gas_volume"),
    (dict(measured_gas_volume=1, volume_unit="bbl", ch4_content=80), "Unknown gas volume unit"),
    (dict(measured_gas_volume=1), "CH4 content of the test gas"),
    (dict(tier="tier2", well_type="gas", ch4_content=80), "requires non-negative gas_production_rate"),
    (dict(tier="tier2", well_type="gas", gas_production_rate=1, ch4_content=80), "positive duration"),
    (dict(well_type="gas", gas_production_rate=1, rate_unit="bbl/day", test_duration_days=1, ch4_content=80),
     "Unknown gas rate unit"),
    (dict(tier="tier2", ch4_content=80), "requires non-negative GOR"),
    (dict(tier="tier2", gor=1, ch4_content=80), "requires oil_production_rate or oil_production_total"),
    (dict(tier="tier2", gor=1, oil_production_rate=1, ch4_content=80), "positive duration"),
    (dict(gor=1, gor_unit="mcf/bbl", oil_production_total=1, ch4_content=80), "Unknown GOR unit"),
    (dict(gor=1, oil_production_rate=1, oil_rate_unit="gal/day", test_duration_days=1, ch4_content=80),
     "Unknown oil rate unit"),
    (dict(frac_vented=0.8, frac_flared=0.5), "cannot exceed 1.0"),
    (dict(disposition="pipeline"), "Unknown disposition"),
])
def test_well_testing_refusals(w, kw, match):
    with pytest.raises(ValueError, match=match):
        w.calculate(**kw)


def test_coal_seam_exhibit_6_5():
    c = CoalSeamDrillingCalculator()
    res = c.calculate(wells_data=[{"duration_days": 5, "gas_consumption_mmscf_day": 1.5}, {"days": 2, "rate_mmscf": 1}],
                      well_testing_gas_flared_scf=1e6)
    drill = 9.5e6
    assert res["metadata"]["drilling_ch4_tonnes"] == pytest.approx(tonnes(drill, 0.887, 16.04))
    assert res["metadata"]["flared_ch4_tonnes"] == pytest.approx(tonnes(1e6, 0.887 * 0.02, 16.04))
    assert res["metadata"]["flared_co2_tonnes"] == pytest.approx(tonnes(1e6, 0.887 * 0.98 + 0.109, 44.01))
    direct = c.calculate(drilling_gas_vented_scf=1e6, ch4_content="90%", co2_content=5, flare_combustion_efficiency=None)
    assert direct["metadata"]["drilling_ch4_tonnes"] == pytest.approx(tonnes(1e6, 0.90, 16.04))
    assert c.calculate()["results"]["ch4"]["value"] == 0
    unset = c.calculate(drilling_gas_vented_scf=1e6, ch4_content=None, co2_content="")              # Exhibit 6-5 gas
    assert unset["metadata"]["drilling_ch4_tonnes"] == pytest.approx(tonnes(1e6, 0.887, 16.04))


@pytest.mark.parametrize("kw,match", [
    (dict(ch4_content=-1), "cannot be negative"),
    (dict(ch4_content="150%"), "cannot exceed 100%"),
    (dict(ch4_content=90, co2_content=20), "cannot exceed 100%"),
    (dict(drilling_gas_vented_scf=-1), "cannot be negative"),
    (dict(well_testing_gas_flared_scf=-1), "cannot be negative"),
])
def test_coal_seam_refusals(kw, match):
    with pytest.raises(ValueError, match=match):
        CoalSeamDrillingCalculator().calculate(**kw)
