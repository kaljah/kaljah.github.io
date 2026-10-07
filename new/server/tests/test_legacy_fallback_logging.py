"""The legacy factor math is the designated path for some requests (hardening plan, phase 4).

Measured over the whole suite it ran 11 times in about 2,500 tests: zero activity, entered
Tier 3 factors, catalog factors of processes the dispatcher does not model. These tests pin
that it is reported at DEBUG (so it can be measured on demand) and never at WARNING.
"""
import logging

from calculations.legacy_engine import compute_emissions

FUEL = {"co2": 1.9, "ch4": 0.001, "n2o": 0.0001, "unit": "m3", "type": "fuel"}


def _zero_activity():
    return compute_emissions(
        {"process_type": "combustion", "amount": 0, "unit": "m3", "fuel": "Natural Gas"}, dict(FUEL)
    )


def test_zero_activity_takes_the_fallback_and_reports_the_branch(caplog):
    with caplog.at_level(logging.DEBUG, logger="calculations.legacy_engine"):
        em, method = _zero_activity()
    assert method == "server_custom_factor"
    assert em["totalCo2e"] == 0
    messages = [r.getMessage() for r in caplog.records if r.name == "calculations.legacy_engine"]
    assert any("branch=server_custom_factor process=combustion" in m for m in messages)


def test_fallback_is_not_reported_above_debug(caplog):
    with caplog.at_level(logging.INFO, logger="calculations.legacy_engine"):
        _zero_activity()
    assert not [r for r in caplog.records if r.name == "calculations.legacy_engine"]


def test_dispatcher_results_do_not_report_a_fallback(caplog):
    with caplog.at_level(logging.DEBUG, logger="calculations.legacy_engine"):
        em, method = compute_emissions(
            {"process_type": "combustion", "amount": 5, "unit": "m3", "factor_source": "custom"},
            {"type": "custom", "co2": 2.0, "ch4": 0.001, "n2o": 0.0001, "unit": "m3"},
        )
    assert method == "api2021_generic"
    assert em["totalCo2e"] > 0
    assert not [r for r in caplog.records if "legacy calculation fallback" in r.getMessage()]
