"""calculations/vented_mud.py: API Compendium 2021 Table 6-3 (0.0524 t CH4 per gas well) and Table 6-2 (mud
degassing per drilling day, onshore 0.0458 / 0.0103, offshore 0.2605 / 0.0586, basis 83.85 mol % CH4).
Fixed while testing: an unknown mud type took the water-based factor, an unknown location the onshore factors,
and a call without wells or days counted 1 well.
"""
import pytest

from calculations.vented_mud import MudDegassingCalculator


def val(res, gas):
    r = res["results"][gas]
    return (r or {}).get("value", 0.0) if isinstance(r, dict) or r is None else r


@pytest.fixture
def mud():
    return MudDegassingCalculator()


def test_tier1_wells_table_6_3(mud):
    assert val(mud.calculate(wells=3), "ch4") == pytest.approx(3 * 0.0524)
    assert val(mud.calculate(wells=3, ef_ch4=0.1), "ch4") == pytest.approx(0.3)
    # drilling days are a Table 6-2 activity even with "tier1" (Table 6-3 is per well)
    assert val(mud.calculate(drilling_days=4, tier="tier1"), "ch4") == pytest.approx(4 * 0.0458)
    assert val(mud.calculate(mud_volume=2, tier="tier1"), "ch4") == pytest.approx(2 * 0.0524)


@pytest.mark.parametrize("mud_type,loc,ef", [
    ("water_based", "onshore", 0.0458), ("oil_based", "onshore", 0.0103), ("synthetic", "onshore", 0.0103),
    ("Water", "offshore", 0.2605), ("oil", "OFFSHORE", 0.0586), ("synthetic-based", "offshore", 0.0586),
])
def test_tier2_table_6_2(mud, mud_type, loc, ef):
    res = mud.calculate(drilling_days=10, mud_type=mud_type, location=loc)
    assert val(res, "ch4") == pytest.approx(10 * ef)
    assert res["inputs"]["location"] == loc.lower()


def test_tier2_sources(mud):
    assert val(mud.calculate(drilling_days=10, tier="custom", ef_ch4=0.05), "ch4") == pytest.approx(0.5)
    assert val(mud.calculate(mud_volume=10, tier="tier2"), "ch4") == pytest.approx(0.458)
    assert val(mud.calculate(wells=10, tier="tier2"), "ch4") == pytest.approx(0.458)
    assert val(mud.calculate(drilling_days=10, uncertainties={"_factor_source": "custom"}), "ch4") == pytest.approx(0.458)


def test_tier2_plus_site_gas(mud):
    res = mud.calculate(drilling_days=85, mud_type="water_based", location="offshore", ch4_concentration=70,
                        co2_concentration=9)
    assert val(res, "ch4") == pytest.approx(85 * 0.2605 * 0.70 / 0.8385)                  # Exhibit 6-1: 18.49
    assert val(res, "co2") == pytest.approx(85 * 0.2605 * 0.09 / 0.8385 * 44.01 / 16.04)  # Exhibit 6-1: 6.54
    # the exhibit prints 6.54 with molar masses 16 / 44 (2.75); the engine uses 16.04 / 44.01 (2.744)
    assert val(res, "ch4") == pytest.approx(18.49, rel=2e-3) and val(res, "co2") == pytest.approx(6.54, rel=5e-3)
    basis = mud.calculate(drilling_days=10, tier="tier2_plus")
    assert val(basis, "ch4") == pytest.approx(0.458) and val(basis, "co2") == 0
    assert val(mud.calculate(drilling_days=10, uncertainties={"_factor_source": "tier2+"}, ch4_concentration=0.8385),
               "ch4") == pytest.approx(0.458)
    from_volume = mud.calculate(mud_volume=10, ch4_concentration=0.5)
    assert val(from_volume, "ch4") == pytest.approx(0.458 * 0.5 / 0.8385)
    from_wells = mud.calculate(wells=10, tier="tier2_plus", ch4_concentration=0.5)
    assert val(from_wells, "ch4") == pytest.approx(0.458 * 0.5 / 0.8385)


def test_legacy_positional_forms(mud):
    assert val(mud.calculate(2), "ch4") == pytest.approx(2 * 0.0524)                      # wells
    assert val(mud.calculate("tier2", "oil_based", drilling_days=5), "ch4") == pytest.approx(5 * 0.0103)
    assert val(mud.calculate(None, {"ch4": 0.5}, drilling_days=5), "ch4") == pytest.approx(5 * 0.0458)
    assert val(mud.calculate(7, wells=2), "ch4") == pytest.approx(2 * 0.0524)            # keyword wins
    assert val(mud.calculate("tier1", tier="tier2", drilling_days=5), "ch4") == pytest.approx(5 * 0.0458)


@pytest.mark.parametrize("kwargs,match", [
    (dict(), "number of wells"),
    (dict(wells=-1), "cannot be negative"),
    (dict(drilling_days=-1), "cannot be negative"),
    (dict(drilling_days=-1, tier="tier2_plus"), "cannot be negative"),
    (dict(drilling_days=1, ch4_concentration=-0.1), "ch4_concentration cannot be negative"),
    (dict(drilling_days=1, ch4_concentration=0.5, co2_concentration=-0.1), "co2_concentration cannot be negative"),
    (dict(drilling_days=1, ch4_concentration=0.9, co2_concentration=0.2), "cannot exceed 100%"),
    (dict(drilling_days=1, mud_type="foam"), "Unknown mud type"),
    (dict(drilling_days=1, location="offshore_platform"), "Unknown well location"),
])
def test_refusals(mud, kwargs, match):
    with pytest.raises(ValueError, match=match):
        mud.calculate(**kwargs)
