"""calculations/vented_lng_distribution.py: API Compendium 2021 section 6.7 (Table 6-44 pipeline loss rates, LNG at
95 mol % CH4) and section 6.8 (Tables 6-45 / 6-46). Fixed while testing: the LNG composition defaults (98 % CH4,
0.1 % CO2) had no source, a flare ignored the entered efficiency (100 %), 0 km / controllers / stations counted as
1, and unknown insulation, activities and controller types fell back to a default row.
"""
import pytest

from calculations.units import convert
from calculations.vented_lng_distribution import (
    DistributionNonRoutineCalculator,
    DistributionPneumaticsCalculator,
    LNGVentingCalculator,
)

LB_T = 2204.6226218487757


def t_gas(scf, frac, mw=16.04):
    return scf * frac * mw / 379.3 / LB_T


def val(res, gas):
    r = res["results"][gas]
    return (r or {}).get("value", 0.0) if isinstance(r, dict) or r is None else r


@pytest.mark.parametrize("insulation,rate", [("foam", 0.000012), ("Powder", 0.000006), ("vacuum", 0.0000012)])
def test_table_6_44(insulation, rate):
    res = LNGVentingCalculator().calculate(transfer_volume_m3=100_000, pipe_length_km=2, insulation_type=insulation)
    scf = convert(100_000 * rate * 2 * 600, "m3", "scf")
    assert val(res, "ch4") == pytest.approx(t_gas(scf, 0.95))                    # 95 mol % CH4 (section 6.7)
    assert val(res, "co2") == 0
    bbl = LNGVentingCalculator().calculate(transfer_volume_bbl=100_000 / 0.1589873, pipe_length_km=2,
                                           insulation_type=insulation)
    assert val(bbl, "ch4") == pytest.approx(val(res, "ch4"), rel=1e-6)


def test_lng_direct_volumes_percent_and_zero_length():
    c = LNGVentingCalculator()
    m3 = c.calculate(activity="peak_shaving_blowdown", vented_gas_m3=1000, ch4_content=96, co2_content=1.5)
    assert val(m3, "ch4") == pytest.approx(t_gas(convert(1000, "m3", "scf"), 0.96))
    assert val(m3, "co2") == pytest.approx(t_gas(convert(1000, "m3", "scf"), 0.015, 44.01))
    assert c.calculate(transfer_volume_m3=1000, pipe_length_km=0)["total_co2e"] == 0      # 0 km (was 1 km)
    flared = c.calculate(activity="direct_bog_vent", vented_gas_scf=1e6, disposition="flared", control_efficiency=0.9)
    assert val(flared, "ch4") == pytest.approx(t_gas(1e6, 0.95) * 0.10)                  # the entered 90 %


@pytest.mark.parametrize("kwargs,match", [
    (dict(activity="truck_unloading"), "Unknown LNG activity"),
    (dict(), "transfer_volume_m3 or transfer_volume_bbl"),
    (dict(activity="direct_bog_vent"), "vented_gas_scf or vented_gas_m3"),
    (dict(transfer_volume_m3=1, insulation_type="perlite"), "pipe insulation"),
    (dict(transfer_volume_m3=1, pipe_length_km=-1), "cannot be negative"),
])
def test_lng_refusals(kwargs, match):
    with pytest.raises(ValueError, match=match):
        LNGVentingCalculator().calculate(**kwargs)


@pytest.mark.parametrize("ctype,ef,basis", [("isolation_valves", 0.366, 0.934), ("control_loops", 3.465, 0.944),
                                            ("average", 2.941, 0.949), ("unknown", 2.941, 0.949),
                                            ("industrial_meter_regulator", 3.847, 0.934)])
def test_table_6_45(ctype, ef, basis):
    d = DistributionPneumaticsCalculator()
    assert val(d.calculate(controller_type=ctype, controller_count=4), "ch4") == pytest.approx(4 * ef)
    site = d.calculate(controller_type=ctype, controller_count=4, ch4_content=90, co2_content=1.5)
    assert val(site, "ch4") == pytest.approx(4 * ef * 0.90 / basis)
    scf = 4 * DistributionPneumaticsCalculator.TABLE_6_45["average" if ctype == "unknown" else ctype]["scf_gas_hr"] * 8760
    assert val(site, "co2") == pytest.approx(t_gas(scf, 0.015, 44.01))


def test_distribution_pneumatic_zero_and_refusal():
    assert DistributionPneumaticsCalculator().calculate(controller_count=0)["total_co2e"] == 0     # (was 1)
    with pytest.raises(ValueError, match="distribution controller type"):
        DistributionPneumaticsCalculator().calculate(controller_type="snap_acting")


@pytest.mark.parametrize("act,ef,basis", [("mr_station_blowdown", 0.002895, 0.948), ("odorizer_sampling", 0.02275, 0.948),
                                          ("pipeline_blowdown", 0.03220, 0.934), ("pipeline_dig_in", 0.03040, 0.934),
                                          ("prv_releases", 9.591e-4, 0.934)])
def test_table_6_46(act, ef, basis):
    n = DistributionNonRoutineCalculator()
    assert val(n.calculate(activity=act, count_or_miles=10), "ch4") == pytest.approx(10 * ef)
    site = n.calculate(activity=act, count_or_miles=10, ch4_content=92, co2_content=2)
    assert val(site, "ch4") == pytest.approx(10 * ef * 0.92 / basis)
    scf = 10 * DistributionNonRoutineCalculator.TABLE_6_46[act]["scf_gas"]
    assert val(site, "co2") == pytest.approx(t_gas(scf, 0.02, 44.01))


def test_distribution_non_routine_dispositions_and_refusals():
    n = DistributionNonRoutineCalculator()
    vented = val(n.calculate(count_or_miles=10), "ch4")
    assert val(n.calculate(count_or_miles=10, disposition="recovered"), "ch4") == 0
    assert val(n.calculate(count_or_miles=10, disposition="flared"), "ch4") == pytest.approx(vented * 0.02)
    assert n.calculate(count_or_miles=0)["total_co2e"] == 0
    with pytest.raises(ValueError, match="Table 6-46 activity"):
        n.calculate(activity="purging")
