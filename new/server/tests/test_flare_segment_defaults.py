"""Flare defaults per the API Compendium 2021 corrections (December 2025, Section 5.1.2): 96.5 % combustion
efficiency for CO2; CH4 destruction 98 % for production flares, 99.5 % for refinery (Downstream) flares."""
import pytest

from calculations import compute_emissions
from calculations.constants import get_active_gwp
from calculations.units import CONVERSIONS
from services.scope1_calc import resolve_factor

GWP = get_active_gwp(standard="AR5")


def _tier3(segment, **extra):
    p = {"process_type": "flaring", "factor_source": "specific", "amount": 10000, "unit": "m3", "c1": 1.0,
         "flare_type": "elevated", "facility_segment": segment, **extra}
    em, _ = compute_emissions(p, {}, gwp_dict=GWP)
    return em


def _catalog(segment):
    p = {"process_type": "flaring", "factor_source": "default", "fuel": "Natural Gas (Flaring)", "amount": 10000,
         "unit": "m3", "facility_segment": segment}
    em, _ = compute_emissions(p, resolve_factor(p) or {}, gwp_dict=GWP)
    return em


def test_tier3_defaults_by_segment(app):
    with app.app_context():
        up, down = _tier3("Upstream"), _tier3("Downstream")
    co2 = 10000 * 0.965 * CONVERSIONS["density_co2"] / 1000
    assert up["co2"] == pytest.approx(co2, rel=1e-6) and down["co2"] == pytest.approx(co2, rel=1e-6)
    assert up["ch4"] == pytest.approx(10000 * 0.02 * CONVERSIONS["density_ch4"] / 1000, rel=1e-6)
    assert down["ch4"] == pytest.approx(10000 * 0.005 * CONVERSIONS["density_ch4"] / 1000, rel=1e-6)


def test_entered_efficiency_wins_over_segment(app):
    with app.app_context():
        em = _tier3("Downstream", destruction_efficiency=96)
    assert em["ch4"] == pytest.approx(10000 * 0.04 * CONVERSIONS["density_ch4"] / 1000, rel=1e-6)


def test_catalog_factor_by_segment(app):
    with app.app_context():
        up, down = _catalog("Upstream"), _catalog("Downstream")
    assert up["co2"] == pytest.approx(10000 * 1.9039 / 1000, rel=1e-6) and down["co2"] == pytest.approx(up["co2"])
    assert up["ch4"] == pytest.approx(10000 * 0.012447 / 1000, rel=1e-6)
    assert down["ch4"] == pytest.approx(up["ch4"] * 0.25, rel=1e-6)
