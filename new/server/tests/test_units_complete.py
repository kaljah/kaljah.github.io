"""calculations/units.py: the last branches (no Z given, a unit of the wrong dimension, extra words in a factor
numerator, a count denominator after the activity denominator)."""
import pytest

from calculations.units import (UnitError, factor_to_kg_per_activity, normalize_gas_volume_to_standard,
                                parse_factor_unit, to_base)


def test_no_compressibility_factor_is_ideal_gas():
    assert normalize_gas_volume_to_standard(100, z_factor=None) == normalize_gas_volume_to_standard(100, z_factor=1.0)
    assert normalize_gas_volume_to_standard(100, z_factor="-") == normalize_gas_volume_to_standard(100)
    with pytest.raises(ValueError, match="not a number"):
        normalize_gas_volume_to_standard(100, z_factor="abc")
    with pytest.raises(ValueError, match="strictly positive"):
        normalize_gas_volume_to_standard(100, z_factor=0)


def test_to_base_checks_the_dimension():
    assert to_base(2, "tonne", "mass") == pytest.approx(2000)
    with pytest.raises(UnitError, match="expected volume"):
        to_base(1, "kg", "volume")


def test_factor_numerator_words_and_count_denominator():
    spec = parse_factor_unit("kg ch4 vented/scf")
    assert spec["gas"] == "ch4" and spec["mass_kg"] == 1.0
    assert factor_to_kg_per_activity(2.0, "kg/scf/source", "scf") == pytest.approx(2.0)
