"""Regression tests for the clean-room calculation audit of November 2026, aggregation batch.

Finding IDs refer to CALC_AUDIT_2026-11/REPORT.md. Expected values are worked by hand from the inputs and the cited
norm (IPCC 2006 Vol 1 ch. 3, AR5 / AR6 WG1, NGSI Protocol v3.0, Compendium Table 5-5, 42 USC 7436), never read from
the engine.
"""
import types

import pytest

from app import app
from input_validation import ValidationError


@pytest.fixture
def ctx():
    with app.app_context():
        yield


def _rec(**kw):
    base = dict(process_type="combustion", co2_emissions=None, ch4_emissions=None, n2o_emissions=None,
                co2e_total=50.0, source_payload=None, year=2024, month=1, facility_id=1, fuel_type="", unit="",
                quantity=0, factor_source="default", gwp_version="AR5")
    base.update(kw)
    return types.SimpleNamespace(**base)


# ---------------------------------------------------------------- F-AGG-07 / F-CORE-01 / F-CORE-08
def test_f_agg_07_record_without_gases_keeps_its_co2e(ctx):
    from services.gwp_recalculation import reweighted_co2e

    assert reweighted_co2e(_rec(), {"CO2": 1, "CH4": 29.8, "N2O": 273}) is None


def test_reweighted_co2e_uses_the_gas_masses(ctx):
    from services.gwp_recalculation import reweighted_co2e

    r = _rec(co2_emissions=100.0, ch4_emissions=1.0, n2o_emissions=0.1)
    assert reweighted_co2e(r, {"CO2": 1, "CH4": 29.8, "N2O": 273}) == pytest.approx(100 + 29.8 + 27.3)


def test_f_core_01_fgas_record_without_inputs_is_kept_not_zeroed(ctx):
    from services.gwp_recalculation import reweighted_co2e

    assert reweighted_co2e(_rec(process_type="refrigerant", co2_emissions=0.0, ch4_emissions=0.0,
                                n2o_emissions=0.0), {"CO2": 1, "CH4": 29.8, "N2O": 273}) is None


def test_f_core_08_unknown_gwp_standard_is_refused():
    from services.gwp_recalculation import known_gwp_dict

    with pytest.raises(ValidationError, match="Unknown GWP standard"):
        known_gwp_dict("AR7")
    assert known_gwp_dict("ar6")["CH4"] > 0


# ---------------------------------------------------------------- F-AGG-03 / F-AGG-09 GWP uncertainty
def test_f_agg_03_gwp_uncertainty_is_correlated_across_keys():
    from services.inventory_uncertainty import _gwp_variance

    u = {"co2": 0.0, "ch4": 0.40 / 1.645, "n2o": 0.30 / 1.645}
    # 10 sources x 1,000 t CO2e of CH4 in one category: sigma = 0.40 / 1.645 x 10,000 t, U95 = 48.63 %
    per_cat, total = _gwp_variance({"Venting": {"ch4": 10_000.0}}, u)
    assert 2 * total ** 0.5 / 10_000 == pytest.approx(2 * 0.40 / 1.645, rel=1e-9)
    # two categories: still one GWP, sigma of the sum (not the root-sum-square of the parts)
    _, total2 = _gwp_variance({"A": {"ch4": 4_000.0}, "B": {"ch4": 6_000.0}}, u)
    assert total2 == pytest.approx((0.40 / 1.645 * 10_000) ** 2)


def test_f_agg_09_gwp_ranges_follow_report_and_horizon():
    from calculations.uncertainty import gwp_uncertainty_1sigma

    assert gwp_uncertainty_1sigma({"CH4": 28})["ch4"] == pytest.approx(0.40 / 1.645)
    assert gwp_uncertainty_1sigma({"CH4": 84})["ch4"] == pytest.approx(0.30 / 1.645)
    assert gwp_uncertainty_1sigma({"CH4": 84})["n2o"] == pytest.approx(0.20 / 1.645)
    assert gwp_uncertainty_1sigma({"CH4": 29.8})["ch4"] == pytest.approx(11 / 29.8 / 1.645)
    assert gwp_uncertainty_1sigma({"CH4": 29.8})["n2o"] == pytest.approx(130 / 273 / 1.645)


# ---------------------------------------------------------------- F-AGG-05 NGSI
def test_f_agg_05_gas_ratio_for_production():
    from services.methane_intensity import gas_ratio

    gas_m3, oil_bbl = 9.0e7, 1.0e6
    e_ng = gas_m3 / 28.316846592 * 1.235  # NGSI v3.0: 1.235 MMBtu per Mcf of raw gas
    e_liq = oil_bbl * 5.8                 # 5.8 MMBtu per bbl
    assert gas_ratio("production", gas_m3, oil_bbl) == pytest.approx(e_ng / (e_ng + e_liq))
    assert gas_ratio("processing", gas_m3, oil_bbl) == 1.0


def test_f_agg_05_ngsi_segments_and_contents():
    from services.methane_intensity import ngsi_ch4_content, ngsi_segment

    assert ngsi_segment("Midstream", "Gathering & Boosting") == "gathering_boosting"
    assert ngsi_segment("Midstream", "Transmission pipeline") == "transmission_storage"
    assert ngsi_segment("Midstream", "Gas processing") == "processing"
    assert ngsi_segment("Upstream", None) == "production"
    assert ngsi_ch4_content("gathering_boosting") == 0.833
    assert ngsi_ch4_content("transmission_storage") == 0.934
    assert ngsi_ch4_content("processing") == 0.87


def test_f_agg_05_ngsi_formula_with_gas_ratio():
    from services.methane_intensity import ngsi_intensity_pct

    # 12.5 t CH4 x GR 0.5 / (1e6 Mcf x 83.3 % x 0.0192 t/Mcf) x 100
    got = ngsi_intensity_pct(12.5, 1e6 * 28.316846592, 0.833, 0.5)
    assert got == pytest.approx(12.5 * 0.5 / (1e6 * 0.833 * 0.0192) * 100)


# ---------------------------------------------------------------- F-GAPI-01 categories
@pytest.mark.parametrize("process,cat", [
    ("transmission_non_routine", "vented"), ("gathering_non_routine", "vented"), ("processing_non_routine", "vented"),
    ("distribution_non_routine", "vented"), ("transmission_compressor", "vented"),
    ("gathering_compressor", "vented"), ("wastewater", "process")])
def test_f_gapi_01_midstream_vents_and_wastewater(process, cat):
    from services.dashboard_filters import source_category

    assert source_category(process) == cat


# ---------------------------------------------------------------- F-AGG-12 oil-production flares
def test_f_agg_12_oil_flare_tier1_uncertainty():
    from calculations.uncertainty import Tier, flare_tier1_uncertainty

    assert flare_tier1_uncertainty("Associated Gas (Flaring)", "co2", Tier.T1) == 0.50
    assert flare_tier1_uncertainty("Heavy oil thermal flare", "ch4", Tier.T1) == 0.75
    assert flare_tier1_uncertainty("Natural Gas", "co2", Tier.T1) is None
    assert flare_tier1_uncertainty("Associated Gas (Flaring)", "co2", Tier.T3) is None
    assert flare_tier1_uncertainty("Associated Gas (Flaring)", "n2o", Tier.T1) is None


# ---------------------------------------------------------------- F-AGG-15 net-zero targets
def test_f_agg_15_net_zero_target_is_not_suspicious():
    from calculations.goals_validation import validate_goal_trajectory

    w = validate_goal_trajectory([{"year": 2050, "target_amount": 5_000.0}], 2024, 100_000.0, 100_000.0, 0.0)
    assert not any("suspiciously low" in m for msgs in (w or {}).values() for m in msgs)


# ---------------------------------------------------------------- F-GREST-02 asymmetric Monte Carlo limits
def test_f_grest_02_monte_carlo_gives_lower_and_upper_limits():
    from calculations.uncertainty import monte_carlo_simulation

    res = monte_carlo_simulation([{"value": 1000.0, "relative_uncertainty": 1.5}], iterations=2500, seed=42)
    lo, hi = res["lower_uncertainty_95pct"], res["upper_uncertainty_95pct"]
    assert lo < 0 < hi
    assert hi > -lo  # a skewed (lognormal-like) distribution is not symmetric
