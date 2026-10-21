"""calculations/dispatcher_branches_fugitive.calc_fugitive: the operating time. Fixed while testing: an unknown time
unit was read as hours, an entered 0 operating days took the record's month, "operating_time" was ignored (the
record's period was used), a year was 365.25 days but 8,760 h, and the correlation method assumed one component
when the count was missing."""
import pytest

from calculations.dispatcher import CalculationDispatcher

BASE = {"factor_source": "specific", "component_type": "valves", "amount": 20, "ef": 0.005,
        "ef_unit": "kg CH4/hr/component", "year": 2025}


def ch4(**kw):
    res = CalculationDispatcher().dispatch("fugitive_component", {**BASE, **kw}, {}, {})
    return res["results"]["ch4"]["value"]


def test_time_units_scale_the_hours():
    one_hour = ch4(operating_hours=1)
    assert one_hour == pytest.approx(20 * 0.005 / 1000)
    assert ch4(operating_time=10, time_unit="days") == pytest.approx(240 * one_hour)
    assert ch4(operating_hours=2, time_unit="months") == pytest.approx(1460 * one_hour)
    assert ch4(operating_hours=1, time_unit="years") == pytest.approx(8760 * one_hour)
    assert ch4(operating_days=3) == pytest.approx(72 * one_hour)
    assert ch4(operating_days=0) == 0                                                            # 0 days is 0
    assert ch4(month=2) == pytest.approx(28 * 24 * one_hour)                                     # record's month


def test_unknown_time_unit_refused():
    with pytest.raises(ValueError, match="Unknown time unit 'weeks'"):
        ch4(operating_hours=1, time_unit="weeks")


def test_correlation_single_ppm_needs_the_component_count():
    d = CalculationDispatcher()
    inputs = {"factor_source": "specific", "fugitive_method": "correlation", "correlation_type": "valve",
              "service_type": "gas", "fugitive_ppm": 500, "operating_hours": 100, "ch4_wt_fraction": 0.6}
    with pytest.raises(ValueError, match="number of components screened"):
        d.dispatch("fugitive", inputs, {}, {})
    three = d.dispatch("fugitive", {**inputs, "amount": 3}, {}, {})["results"]["ch4"]["value"]
    one = d.dispatch("fugitive", {**inputs, "amount": 1}, {}, {})["results"]["ch4"]["value"]
    assert three == pytest.approx(3 * one)
