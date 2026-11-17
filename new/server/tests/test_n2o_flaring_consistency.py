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
    co2_val = result["results"]["co2"]["value"]
    # Compendium Eq 5-6 (Dec 2025 natural-gas factor): E_N2O = E_CO2 x 1.0E-04 / 60 (blind audit BA-017)
    assert n2o_val > 0.0
    assert n2o_val == pytest.approx(co2_val * 0.0001 / 60.0, rel=1e-9)


def test_split_vented_and_flared_n2o_default():
    total_gas = 1000.0
    ch4_tonnes = total_gas * 0.85 * (16.04 / 23.685) / 1000.0
    res = _split_vented_and_flared(
        total_gas_m3=total_gas,
        ch4_tonnes=ch4_tonnes,
        co2_tonnes=0.0,
        ctrl_eff=1.0,
        hhv=1020.0,
        ef_n2o=None,
    )
    assert res["flared_n2o"] > 0.0
    assert res["flared_n2o"] == pytest.approx(res["flared_co2"] * 0.0001 / 60.0, rel=1e-9)  # Eq 5-6 (BA-017)
