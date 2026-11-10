"""
Verification Test: BUG-03 / CALC-04 (Fixed)
Flaring N2O calculation handles 'btu/m3' HHV unit in new/server/calculations/combustion.py
"""

import sys
import pytest

sys.path.insert(0, "new/server")

from calculations.combustion import FlaringCalculator

def test_flaring_n2o_hhv_unit_m3():
    calc = FlaringCalculator()

    # 1,000 m3 gas with HHV = 36,000 Btu/m3 (standard natural gas heating value ~36-38 MJ/m3)
    # Correct calculation:
    # 1,000 m3 * 36,000 Btu/m3 = 36,000,000 Btu = 36 MMBtu
    # With EF = 0.0001 kg/MMBtu: N2O = 36 * 0.0001 / 1000 = 0.0000036 tonnes
    res = calc.calculate(
        gas_volume=1000.0,
        ch4_fraction=0.95,
        flare_type="steam_assisted",
        uncertainties={},
        fuel_unit="m3",
        hhv=36000.0,
        hhv_unit="btu/m3",
        ef_n2o=0.0001,
        ef_unit="kg/mmbtu",
        c1=0.95,
        co2_comp=0.05
    )

    actual_n2o = res["results"]["n2o"]["value"]
    expected_n2o = (1000.0 * 36000.0 / 1e6) * 0.0001 / 1000.0  # 3.6e-6

    # Verify actual N2O matches expected N2O within 0.1% tolerance
    assert abs(actual_n2o - expected_n2o) / expected_n2o < 0.001, f"Expected {expected_n2o}, got {actual_n2o}"

