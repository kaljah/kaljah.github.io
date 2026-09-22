"""
CLEAN-SLATE VALIDATION: Unit Conversions & Invariance
Validates volume, mass, energy, and temperature/pressure unit conversions.
Tests A -> B, B -> A, and A -> B -> A round-trip invariance.
ZERO reuse of legacy tests. Designed completely from zero.
"""

import pytest
import sys
import os

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SERVER_DIR = os.path.join(BASE_DIR, "new", "server")
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, SERVER_DIR)

from calculations.units import (
    convert,
    to_kelvin,
    to_fahrenheit,
    to_psia,
    CONVERSIONS,
)
from validation.reference_model.ref_constants import (
    CONV_SCF_TO_M3,
    CONV_M3_TO_SCF,
    CONV_MSCF_TO_M3,
    CONV_BBL_TO_M3,
    CONV_M3_TO_BBL,
    CONV_LB_TO_KG,
    CONV_KG_TO_LB,
    CONV_SHORT_TON_TO_KG,
    CONV_MMBTU_TO_MJ,
    CONV_KWH_TO_MJ,
)


class TestCleanUnitConversions:
    """Independent validation of physical unit conversions."""

    @pytest.mark.parametrize(
        "val,unit_a,unit_b,expected_factor",
        [
            (100.0, "scf", "m3", CONV_SCF_TO_M3),
            (10.0, "mscf", "m3", CONV_MSCF_TO_M3),
            (50.0, "bbl", "m3", CONV_BBL_TO_M3),
            (1000.0, "lb", "kg", CONV_LB_TO_KG),
            (5.0, "short_ton", "kg", CONV_SHORT_TON_TO_KG),
            (25.0, "mmbtu", "mj", CONV_MMBTU_TO_MJ),
            (1000.0, "kwh", "mj", CONV_KWH_TO_MJ),
        ]
    )
    def test_round_trip_conversions_a_to_b_to_a(self, val, unit_a, unit_b, expected_factor):
        """Tests A -> B, B -> A, and A -> B -> A round-trip precision."""
        # A -> B
        val_b = convert(val, unit_a, unit_b)
        expected_b = val * expected_factor
        assert abs(val_b - expected_b) < 1e-4

        # B -> A
        val_a_reconstructed = convert(val_b, unit_b, unit_a)
        assert abs(val_a_reconstructed - val) < 1e-4

        # Strict round trip ratio == 1.0 within floating precision
        ratio = val_a_reconstructed / val
        assert abs(ratio - 1.0) < 1e-6

    def test_extreme_values_and_precision(self):
        """Tests unit conversions on very small and very large magnitudes."""
        tiny = 1e-9
        converted_tiny = convert(tiny, "scf", "m3")
        assert converted_tiny > 0
        assert abs(convert(converted_tiny, "m3", "scf") - tiny) < 1e-15

        huge = 1e12
        converted_huge = convert(huge, "lb", "kg")
        assert converted_huge > 0
        assert abs((convert(converted_huge, "kg", "lb") / huge) - 1.0) < 1e-9

    def test_incompatible_unit_error(self):
        """Converting between incompatible dimensions (e.g. mass to energy) must fail gracefully."""
        with pytest.raises(ValueError):
            convert(100.0, "kg", "kwh")

    def test_temperature_conversions(self):
        """Standard thermodynamic temperature conversions."""
        # 15.556 C = 60 F = 288.706 K
        assert abs(to_kelvin(15.5556, "c") - 288.706) < 1e-2
        assert abs(to_kelvin(60.0, "f") - 288.706) < 1e-2
        assert abs(to_fahrenheit(15.5556, "c") - 60.0) < 1e-2

    def test_pressure_conversions(self):
        """Standard thermodynamic pressure conversions."""
        # 0 psig = 14.696 psia
        assert abs(to_psia(0.0, "psig") - 14.696) < 1e-3
        # 100 kpa gauge ~ 100 * 0.145038 + 14.696 psia ~ 29.20 psia
        assert abs(to_psia(100.0, "kpag") - 29.20) < 0.1
