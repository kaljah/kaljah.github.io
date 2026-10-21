"""calculations/vented_production_tank.py: the blowdown cylinder inputs (Exhibit 6-25). Fixed while testing: a
negative diameter or length, or a liquid fraction above 1, gave a negative or wrong gas volume (only a negative
result was caught, after the fact)."""
import math

import pytest

from calculations.units import convert
from calculations.vented_production_tank import BlowdownCalculator


def test_cylinder_volume_with_liquid_share():
    b = BlowdownCalculator()
    res = b.calculate(diameter_ft=2, length_ft=100, liquid_volume_fraction=0.25, pressure=0, events=1,
                      ch4_content=90, press_unit="psig")
    expected_m3 = convert(math.pi * 1 ** 2 * 100 * 0.75, "scf", "m3")
    assert res["inputs"]["total_v_std_m3"] == pytest.approx(expected_m3)                          # 0 psig, 60 F


@pytest.mark.parametrize("kw,match", [
    (dict(diameter_ft=-2, length_ft=100), "cannot be negative"),
    (dict(diameter_ft=2, length_ft=-100), "cannot be negative"),
    (dict(diameter_ft=2, length_ft=100, liquid_volume_fraction=1.5), "liquid_volume_fraction"),
])
def test_cylinder_refusals(kw, match):
    with pytest.raises(ValueError, match=match):
        BlowdownCalculator().calculate(pressure=100, events=1, ch4_content=90, **kw)


# ---------------------------------------------------------------- AcidGasRemovalCalculator (no dispatcher route)
def test_agr_unit_count_days_and_dispositions():
    from calculations.vented_production_tank import AcidGasRemovalCalculator

    a = AcidGasRemovalCalculator()
    assert a.calculate(method="unit_count", unit_count=2, operating_days=30)["results"]["ch4"]["value"] == \
        pytest.approx(2 * 0.6482 * 30)                                                           # Table 6-19
    assert a.calculate(method="unit_count", unit_count=2, operating_days=0)["results"]["ch4"]["value"] == 0
    assert a.calculate(method="unit_count", unit_count=0)["results"]["ch4"]["value"] == 0
    flared = a.calculate(sour_gas_mmscf_yr=10, disposition="flared")
    assert flared["results"]["ch4"]["value"] == pytest.approx(10 * 0.0185 * 0.02)
    with pytest.raises(ValueError, match="Unknown disposition"):
        a.calculate(sour_gas_mmscf_yr=10, disposition="sold")


@pytest.mark.parametrize("kw,match", [
    (dict(operating_days=-1), "cannot be negative"),
    (dict(sour_gas_mmscf_yr=1, sour_co2_content=-5), "sour_co2_content must be between"),
    (dict(sour_gas_mmscf_yr=1, sour_co2_content="150%"), "sour_co2_content must be between"),
    (dict(sour_gas_mmscf_yr=1, sour_co2_content=4, sweet_co2_content=-1), "sweet_co2_content must be between"),
])
def test_agr_refusals(kw, match):
    from calculations.vented_production_tank import AcidGasRemovalCalculator

    with pytest.raises(ValueError, match=match):
        AcidGasRemovalCalculator().calculate(**kw)
