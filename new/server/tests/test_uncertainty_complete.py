"""calculations/uncertainty.py: the last branches (an unseeded Monte Carlo run, explicit activity / composition
uncertainties next to a record's uncertainty dict, a zero or unreadable composition uncertainty)."""
import math

import pytest

from calculations.uncertainty import COVERAGE_FACTOR_95, monte_carlo_simulation, propagate_uncertainty


def test_unseeded_monte_carlo_still_brackets_the_total():
    res = monte_carlo_simulation([{"value": 100.0, "relative_uncertainty": 0.05}], iterations=2000, seed=None)
    assert res["ci_lower"] < 100.0 < res["ci_upper"]


def test_explicit_uncertainties_win_over_the_record_dict():
    record = {"_activity_uncertainty": 0.50, "_composition_uncertainty": 0.50}
    explicit = propagate_uncertainty(10.0, 0.10, activity_uncertainty=0.02, composition_uncertainty=0.04,
                                     uncertainties_dict=record)
    expected = math.sqrt(0.10 ** 2 + 0.02 ** 2 + 0.04 ** 2) / COVERAGE_FACTOR_95
    assert explicit["relative_uncertainty_1sigma"] == pytest.approx(expected)
    from_dict = propagate_uncertainty(10.0, 0.10, uncertainties_dict=record)
    assert from_dict["relative_uncertainty_1sigma"] == pytest.approx(math.sqrt(0.01 + 0.25 + 0.25) / COVERAGE_FACTOR_95)


@pytest.mark.parametrize("comp", [0, -0.1, "n/a"])
def test_zero_or_unreadable_composition_adds_nothing(comp):
    base = propagate_uncertainty(10.0, 0.10, activity_uncertainty=0.02)
    res = propagate_uncertainty(10.0, 0.10, activity_uncertainty=0.02, composition_uncertainty=comp)
    assert res["relative_uncertainty_1sigma"] == pytest.approx(base["relative_uncertainty_1sigma"])
    assert res["comp_uncertainty_1sigma"] == 0.0
