"""calculations/dispatcher.py helpers. Fixed while testing: unreadable optional inputs took the default
(_optional_float / _optional_fraction), an entered 0 operating days took the record's period, and a disposition was
ignored by the unloading, blowdown, tank and dehydrator branches (a flared row was booked as vented)."""
import pytest

from calculations.dispatcher import CalculationDispatcher, operating_hours, record_period


@pytest.fixture
def d():
    return CalculationDispatcher()


def test_record_period():
    assert record_period({"year": 2024, "month": 2}) == (29 * 24.0, 29.0, 29 / 366)
    assert record_period({"year": 2025, "month": 13}) == (8760.0, 365.0, 1.0)                 # not a month: a year
    assert record_period({"year": "x", "month": 1}) == (8760.0, 365.0, 1.0)


def test_operating_hours():
    assert operating_hours({"operating_hours": 100}) == 100
    assert operating_hours({"operating_days": 0, "duration_days": 5}) == 0                    # 0 days is 0
    assert operating_hours({"duration_days": 2}) == 48
    assert operating_hours({"year": 2025, "month": 4}) == 720
    with pytest.raises(ValueError, match="between 0 and 8784"):
        operating_hours({"hours": 9000})
    with pytest.raises(ValueError, match="between 0 and 366"):
        operating_hours({"operating_days": 400})


def test_optional_readers_refuse_unreadable_text(d):
    assert d._optional_float({"a": "", "b": "2.5"}, ["a", "b"]) == 2.5
    assert d._optional_float({}, "a", 7) == 7
    with pytest.raises(ValueError, match="'a' is not a number: lots"):
        d._optional_float({"a": "lots", "b": 1}, ["a", "b"])
    assert d._optional_fraction({"x": "45%"}, "x") == pytest.approx(0.45)
    with pytest.raises(ValueError, match="'x' is not a number or percentage"):
        d._optional_fraction({"x": "high", "y": 50}, ["x", "y"])


@pytest.mark.parametrize("inputs,share", [({}, 0.0), ({"disposition": "Vented"}, 0.0), ({"disposition": "flared"}, 1.0),
                                          ({"disposition": "flared", "control_efficiency": 40}, 1.0)])
def test_controlled_share(d, inputs, share):
    assert d._controlled_share(inputs, ["control_efficiency"])[0] == pytest.approx(share)


def test_controlled_share_refuses_other_dispositions(d):
    with pytest.raises(ValueError, match="'recovered' is not available for this process"):
        d._controlled_share({"disposition": "recovered"}, ["tank_control_eff", "control_efficiency"])


def test_require(d):
    assert d._require("k", {"k": "3"}, "thing") == 3.0
    with pytest.raises(ValueError, match="Missing required field: k \\(thing\\)"):
        d._require("k", {"k": "-"}, "thing")


def test_flared_unloading_and_tank_rows_are_flared(d):
    unload = {"factor_source": "default", "amount": 10, "unit": "events", "unloading_type": "without_plunger",
              "ch4_content": 80, "well_count": 1}
    vented = d.dispatch("unloading", unload, {}, {})["results"]["ch4"]["value"]
    flared = d.dispatch("unloading", {**unload, "disposition": "flared"}, {}, {})["results"]["ch4"]["value"]
    assert flared == pytest.approx(vented * 0.02)
    tank = {"factor_source": "specific", "throughput": 1000, "amount": 1000, "unit": "bbl", "method": "table_6_22"}
    t_vented = d.dispatch("tank_flashing", tank, {}, {})["results"]["ch4"]["value"]
    t_flared = d.dispatch("tank_flashing", {**tank, "disposition": "flared"}, {}, {})["results"]["ch4"]["value"]
    assert t_flared == pytest.approx(t_vented * 0.02)
