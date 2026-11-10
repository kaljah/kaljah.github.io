"""
Verification Test: BUG-04 / CALC-08 (Fixed)
FlaringCalculator includes native CO2 when passed with key 'co2' in new/server/calculations/combustion.py
"""

import sys
import pytest

sys.path.insert(0, "new/server")

from calculations.combustion import FlaringCalculator

def test_flaring_co2_dropped_with_standard_key():
    calc = FlaringCalculator()

    # Pass 2% native CO2 using standard key 'co2'
    res_with_co2_key = calc.calculate(
        gas_volume=10000.0,
        ch4_fraction=0.85,
        flare_type="steam_assisted",
        uncertainties={},
        fuel_unit="m3",
        c1=0.85,
        c2=0.05,
        co2=0.02
    )

    # Pass 2% native CO2 using non-standard key 'co2_comp'
    res_with_co2_comp = calc.calculate(
        gas_volume=10000.0,
        ch4_fraction=0.85,
        flare_type="steam_assisted",
        uncertainties={},
        fuel_unit="m3",
        c1=0.85,
        c2=0.05,
        co2_comp=0.02
    )

    co2_with_co2_key = res_with_co2_key["results"]["co2"]["value"]
    co2_with_co2_comp = res_with_co2_comp["results"]["co2"]["value"]

    diff = abs(co2_with_co2_comp - co2_with_co2_key)

    # Both keys produce identical results now
    assert diff < 1e-6, f"Expected key 'co2' and 'co2_comp' to yield identical CO2, but diff was {diff}"

