"""
Regression test for N2O flaring default factor harmonization (API Compendium 2021 Table 5-3).
Verifies that FlaringCalculator and _split_vented_and_flared use the exact same
0.0001 kg/MMBtu default factor when ef_n2o is not explicitly provided.
"""
import pytest
from calculations.combustion import FlaringCalculator
from calculations.vented import _split_vented_and_flared
from calculations.constants import GWP_AR5


def test_flaring_n2o_default_consistency():
    calc = FlaringCalculator()
    result = calc.calculate(
        gas_volume=1000.0,
        ch4_fraction=0.85,
        flare_type="elevated",
        uncertainties={},
        hhv=1020.0,
        ef_n2o=None,  # Should use default 0.0001 kg/MMBtu
        gwp_dict=GWP_AR5,
    )
    n2o_val = result["results"]["n2o"]["value"]
    # 1000 m3 = 35314.7 scf * 1020 BTU / 1e6 = 36.02 MMBtu * 0.0001 kg / 1000 = ~3.6e-6 tonnes
    assert n2o_val > 0.0
    assert abs(n2o_val - 0.0000036) < 1e-6


def test_split_vented_and_flared_n2o_default():
    total_gas = 1000.0
    ch4_tonnes = total_gas * 0.85 * 0.6785 / 1000.0
    res = _split_vented_and_flared(
        total_gas_m3=total_gas,
        ch4_tonnes=ch4_tonnes,
        co2_tonnes=0.0,
        ctrl_eff=1.0,
        hhv=1020.0,
        ef_n2o=None,
    )
    assert res["flared_n2o"] > 0.0
    assert abs(res["flared_n2o"] - 0.0000036) < 1e-6
