"""calculations/midstream.py: acid gas removal (API Compendium 2021 Equation 6-18 with contactor shrinkage,
Table 6-19 vent factor) and glycol dehydrators (Table 6-17). The dehydrator's circulation-rate model had no
Compendium source and is refused.
"""
import pytest

from calculations.midstream import AGRCalculator, DehydratorCalculator
from calculations.units import CONVERSIONS, convert


def val(res, gas):
    r = res["results"][gas]
    return (r or {}).get("value", 0.0) if isinstance(r, dict) or r is None else r


def co2_t(scf):
    return convert(scf, "scf", "m3") * CONVERSIONS["density_co2"] / 1000


def ch4_t(scf):
    return convert(scf, "scf", "m3") * CONVERSIONS["density_ch4"] / 1000


@pytest.fixture
def agr():
    return AGRCalculator()


def test_agr_eq_6_18_fraction_and_percent(agr):
    frac = agr.calculate(throughput=1000, co2_in=0.04, co2_out=0.005, ch4_slip_fraction=None)
    assert val(frac, "co2") == pytest.approx(co2_t(1e9 * 0.035 / 0.995))
    assert val(frac, "ch4") == pytest.approx(1000 * 0.0185)                     # Table 6-19
    pct = agr.calculate(throughput=1000, co2_in=4, co2_out=0.5, ch4_slip_fraction=None)
    assert val(pct, "co2") == pytest.approx(val(frac, "co2"))


def test_agr_measured_slip_and_percent_ch4(agr):
    res = agr.calculate(throughput=100, co2_in=0.05, ch4_in=85, ch4_slip_fraction=0.002)
    assert val(res, "ch4") == pytest.approx(ch4_t(100e6 * 0.85 * 0.002))
    default_ch4 = agr.calculate(throughput=100, co2_in=0.05, ch4_in=None, ch4_slip_fraction=0.002)
    assert val(default_ch4, "ch4") == pytest.approx(val(res, "ch4"))


@pytest.mark.parametrize("ctype", ["agi", "ccus", "injection", "sequestration", "vent"])
def test_agr_capture_types(agr, ctype):
    base = agr.calculate(throughput=100, co2_in=0.05, ch4_slip_fraction=None)
    res = agr.calculate(throughput=100, co2_in=0.05, ch4_slip_fraction=None, acid_gas_control_eff=0.9,
                        acid_gas_control_type=ctype)
    assert val(res, "co2") == pytest.approx(val(base, "co2") * 0.1)
    assert val(res, "ch4") == pytest.approx(val(base, "ch4") * 0.1)


@pytest.mark.parametrize("ctype", ["claus", "thermal_oxidizer", "incinerator", "flare", "combustor"])
def test_agr_destruction_types(agr, ctype):
    base = agr.calculate(throughput=100, co2_in=0.05, ch4_slip_fraction=None)
    res = agr.calculate(throughput=100, co2_in=0.05, ch4_slip_fraction=None, acid_gas_control_eff=0.98,
                        acid_gas_control_type=ctype)
    assert val(res, "ch4") == pytest.approx(val(base, "ch4") * 0.02)
    assert val(res, "co2") == pytest.approx(val(base, "co2") + val(base, "ch4") * 0.98 * 44.01 / 16.04)


@pytest.mark.parametrize("kwargs,match", [
    (dict(co2_in=50, co2_out=100), "below 100 %"),
    (dict(co2_in=0.05, ch4_slip_fraction=2), "fraction of the inlet CH4"),
    (dict(co2_in=None), "co2_in"),
])
def test_agr_refusals(agr, kwargs, match):
    with pytest.raises(ValueError, match=match):
        agr.calculate(throughput=100, **kwargs)


def test_dehydrator_table_6_17():
    d = DehydratorCalculator()
    assert val(d.calculate(throughput=1000), "ch4") == pytest.approx(1000 * 0.0052859)          # 78.8 % basis
    assert val(d.calculate(gas_throughput=1000, ch4_content=90, control_eff=0.5), "ch4") == pytest.approx(
        1000 * 0.0052859 * 0.90 / 0.788 * 0.5)
    for kwargs in (dict(pump_rate=100, throughput=10), dict()):
        with pytest.raises(ValueError, match="no API Compendium method"):
            d.calculate(**kwargs)
