"""calculations/activity_factors.py: every activity basis (per unit, unit-year, unit-day, unit-hour, MMscf,
million m3, thousand gal, bbl), the CH4 / CO2 scaling, TOC rows (15 wt % CH4 in the vapour, AP-42 via the API
Compendium 2021 section 5.7) and every refusal.
"""
import pytest

from calculations.activity_factors import ACTIVITY_FACTORS, ActivityFactorCalculator
from calculations.units import CONVERSIONS
from calculations.vented_gas import SCF_TO_M3

RHO_CH4, RHO_CO2 = CONVERSIONS["density_ch4"], CONVERSIONS["density_co2"]


def val(res, gas):
    r = res["results"][gas]
    return r["value"] if isinstance(r, dict) else r


@pytest.fixture
def a():
    return ActivityFactorCalculator()


def test_every_row_has_a_known_basis():
    assert {r["per"] for r in ACTIVITY_FACTORS.values()} <= {"unit", "unit_day", "unit_hr", "mmscf", "mm_m3", "mgal",
                                                            "bbl"}


def test_per_event_with_site_gas(a):
    res = a.calculate("wt_gas", 2, ch4_content=81.6, co2_content="2%")                            # Table 6-4
    assert val(res, "ch4") == pytest.approx(2 * 0.728)
    assert val(res, "co2") == pytest.approx(2 * 46625 * 0.02 * SCF_TO_M3 * RHO_CO2 / 1000)
    leaner = a.calculate("wt_gas", 2, ch4_content=40.8)
    assert val(leaner, "ch4") == pytest.approx(0.728) and leaner["intermediate"]["ch4_scale"] == pytest.approx(0.5)


def test_per_unit_year_share(a):
    assert val(a.calculate("proc_recip", 3, year_fraction=1 / 12), "ch4") == pytest.approx(3 * 16.3 / 12)
    assert val(a.calculate("proc_recip", 3, year_fraction=""), "ch4") == pytest.approx(3 * 16.3)


def test_per_unit_day_and_mass_factor_co2(a):
    assert val(a.calculate("agr_unit", 1), "ch4") == pytest.approx(0.6482 * 365)                 # a whole year
    res = a.calculate("agr_unit", 2, days=30, ch4_content=50, co2_content=2)
    ch4 = 2 * 30 * 0.6482
    assert val(res, "ch4") == pytest.approx(ch4)                                                 # no basis: no scaling
    assert val(res, "co2") == pytest.approx(ch4 * (0.02 / 0.5) * 44.01 / 16.04)


def test_per_unit_hour_from_gas_rate(a):
    per_hr = 19.25 * 0.816 * SCF_TO_M3 * RHO_CH4 / 1000                                          # Table 6-29
    assert val(a.calculate("gb_pc_high_bleed", 4), "ch4") == pytest.approx(4 * 8760 * per_hr)
    assert val(a.calculate("gb_pc_high_bleed", 4, hours=100), "ch4") == pytest.approx(400 * per_hr)


def test_gas_throughput_bases(a):
    assert val(a.calculate("agr_throughput", 10, unit="MMscf"), "ch4") == pytest.approx(0.185)    # Table 6-19
    assert val(a.calculate("agr_throughput", 10_000, unit="Mcf"), "ch4") == pytest.approx(0.185)
    m3 = a.calculate("proc_non_routine_m3", 2e6, unit="m³")
    assert val(m3, "ch4") == pytest.approx(2 * 0.1244)


def test_liquid_bases_and_toc(a):
    ship = a.calculate("load_marine_ship", 1e6, unit="gal")                                       # Table 6-47, TOC
    assert val(ship, "ch4") == pytest.approx(0.28 * 0.15) and val(ship, "co2") == 0
    assert val(a.calculate("load_marine_ship", 1e6, unit="gal", toc_ch4_wt=50), "ch4") == pytest.approx(0.14)
    assert val(a.calculate("load_marine_ship", 1e6, unit="gal", toc_ch4_wt=0.5), "ch4") == pytest.approx(0.14)
    crude = a.calculate("sep_dump_valve_crude", 1, unit="m3", co2_content=2)
    bbl = 6.28981077
    assert val(crude, "ch4") == pytest.approx(bbl * 2.7e-6)
    assert val(crude, "co2") == pytest.approx(bbl * 2.7e-6 * (0.02 / 0.816) * 44.01 / 16.04)    # CH4 basis 81.6 %


@pytest.mark.parametrize("key,kwargs,match", [
    ("nope", dict(amount=1), "Unknown activity factor"),
    ("wt_gas", dict(amount=-1), "cannot be negative"),
    ("proc_recip", dict(amount=1, year_fraction=1.5), "fraction of a year"),
    ("agr_throughput", dict(amount=1, unit="bbl"), "Gas throughput unit"),
    ("proc_non_routine_m3", dict(amount=1, unit="kg"), "Gas throughput unit"),
    ("load_marine_ship", dict(amount=1, unit="scf"), "Liquid volume unit"),
    ("sep_dump_valve_crude", dict(amount=1, unit="scf"), "Oil volume unit"),
    ("wt_gas", dict(amount=1, ch4_content="abc"), "Invalid gas content"),
    ("wt_gas", dict(amount=1, ch4_content=-1), "non-negative"),
    ("wt_gas", dict(amount=1, co2_content=150), "cannot exceed 100"),
    ("agr_unit", dict(amount=1, co2_content=2), "positive site CH4 content"),
])
def test_refusals(a, key, kwargs, match):
    with pytest.raises(ValueError, match=match):
        a.calculate(key, **kwargs)


def test_activity_factor_list_by_process():
    from calculations.activity_factors import activity_factor_list

    rows = activity_factor_list("agr")
    assert {r["key"] for r in rows} == {"agr_throughput", "agr_unit"}
    assert len(activity_factor_list()) == len(ACTIVITY_FACTORS)
