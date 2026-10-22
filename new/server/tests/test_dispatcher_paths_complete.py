"""calculations/dispatcher.py: the remaining paths (method units, liquid volumes, hydrogen plant, facility fugitives,
CCS capture, catalog lookup, Tier 3 composition, quantity checks, the error path). Fixed while testing: an
unreadable entered uncertainty was ignored (the default was used)."""
import math

import pytest

import calculations.dispatcher as dmod
from calculations.dispatcher import CalculationDispatcher


@pytest.fixture
def d():
    return CalculationDispatcher()


def test_method_unit(d):
    assert d._method_unit({"tank_unit": "bbl"}, ["tank_unit"], "bbl") == "bbl"
    assert d._method_unit({}, ["tank_unit"], None, "m3") == "m3"
    assert d._method_unit({"tank_unit": "widgets"}, ["tank_unit"], "bbl") == "widgets"          # not comparable
    with pytest.raises(ValueError, match="Contradicting units on the row"):
        d._method_unit({"tank_unit": "m3", "amount": 10}, ["tank_unit"], "bbl")
    same = {"tank_unit": "m3", "amount": 1.0, "_top_amount": 6.28981077, "_top_unit": "bbl"}
    assert d._method_unit(same, ["tank_unit"], "bbl") == "m3"                                   # one amount, 2 units
    with pytest.raises(ValueError, match="Contradicting"):
        d._method_unit({"tank_unit": "m3", "amount": "x", "_top_amount": 1, "_top_unit": "bbl"}, ["tank_unit"], "bbl")


def test_liquid_bbl(d):
    assert d._liquid_bbl(1, "m3", "Tank") == pytest.approx(6.28981077)
    with pytest.raises(ValueError, match="is a gas volume"):
        d._liquid_bbl(1, "Mcf", "Tank")
    with pytest.raises(ValueError, match="unknown unit"):
        d._liquid_bbl(1, "barrels of fun", "Tank")
    with pytest.raises(ValueError, match="not a liquid volume"):
        d._liquid_bbl(1, "kg", "Tank")


def test_parse_fraction_value_blank(d):
    assert d._parse_fraction_value(None) is None and d._parse_fraction_value("-") is None


def test_hydrogen_plant_inputs(d):
    with pytest.raises(ValueError, match="finite, non-negative"):
        d.dispatch("hydrogen_plant", {"feedstock_rate_tonnes": -1, "feedstock_carbon_fraction": 75}, {}, {})
    res = d.dispatch("hydrogen_plant", {"feedstock_rate_tonnes": 100, "feedstock_carbon_fraction": 75}, {}, {})
    assert res["results"]["co2"]["value"] == pytest.approx(100 * 0.75 * 44.01 / 12.011, rel=1e-3)


def test_facility_fugitive_type(d):
    with pytest.raises(ValueError, match="facility_type"):
        d._facility_fugitive({"amount": 1, "unit": "bbl"}, {}, None)
    res = d._facility_fugitive({"amount": 1000, "unit": "bbl", "fuel": "Oil Production (Table 7-8)"}, {}, None)
    assert res["results"]["ch4"]["value"] > 0


def test_capture_on_a_plain_number(d, monkeypatch):
    res = {"results": {"co2": 10.0}, "total_co2e": 10.0}
    d._apply_capture(res, {"ccs_capture_rate": 50})
    assert res["total_co2e"] == pytest.approx(5.0)


def test_catalog_lookup_failure_is_no_catalog(monkeypatch):
    import routes.emissions as em

    monkeypatch.setattr(em, "_lookup_api_factor", lambda *_: (_ for _ in ()).throw(RuntimeError("db down")))
    assert CalculationDispatcher._catalog_fuel({"fuel": "Natural Gas"}, {}) == {}


def test_dispatch_passes_non_result_through(d, monkeypatch):
    monkeypatch.setattr(d, "_dispatch_impl", lambda *a, **k: None)
    assert d.dispatch("combustion", {}, {}, {}) is None


def test_unreadable_user_uncertainty_refused(d):
    with pytest.raises(ValueError, match="Uncertainty for ch4 is not a number"):
        d.dispatch("combustion", {"amount": 1, "unit": "m3", "user_uncertainty": {"ch4": "high"}},
                   {"co2": 1.9, "unit": "kg/m3"}, {})


def test_tier3_specific_needs_composition_or_factor(d):
    spec = {"specific_factors": {"n2o": 0.1, "n2oUnit": "kg/m3"}, "factor_source": "specific", "amount": 1,
            "unit": "m3"}
    with pytest.raises(ValueError, match="C1 mole fraction"):
        d.dispatch("combustion", spec, {}, {})


@pytest.mark.parametrize("amount,match", [("lots", "Invalid numeric quantity"), (math.nan, "NaN or Infinite")])
def test_quantity_checks(d, amount, match):
    with pytest.raises(ValueError, match=match):
        d.dispatch("venting", {"amount": amount, "unit": "m3"}, {"ch4": 1, "unit": "kg/m3"}, {})


def test_generic_factor_without_unit(d):
    with pytest.raises(ValueError, match="has no unit"):
        d._generic_calculation({"amount": 5, "unit": "m3", "fuel": "Gas X"}, {"co2": 2.0}, {})


def test_failures_are_logged_and_wrapped(d, caplog):
    with caplog.at_level("ERROR", logger=dmod.__name__):
        with pytest.raises(ValueError, match="Calculation error for 'tank_flashing'"):
            d.dispatch("tank_flashing", {"factor_source": "specific", "amount": 1, "unit": "bbl",
                                         "tank_liquid_type": "milk"}, {}, {})
    assert "Calculation failed for process_type='tank_flashing'" in caplog.text


# ---------------------------------------------------------------- dispatcher_branches_* remaining paths
def test_flaring_branch_composition_and_refinery_default(d):
    base = {"factor_source": "specific", "amount": 1000, "unit": "m3"}
    res = d.dispatch("flaring", {**base, "c1": 0, "c2": 90, "n2_mol": 10}, {}, {})               # an analysis with 0 C1
    assert res["results"]["ch4"]["value"] == 0
    up = d.dispatch("flaring", {**base, "c1": 90}, {}, {})["results"]["ch4"]["value"]
    down = d.dispatch("flaring", {**base, "c1": 90, "facility_segment": "Downstream"}, {}, {})["results"]["ch4"]["value"]
    assert down == pytest.approx(up * 0.005 / 0.02)                                            # 99.5 % refinery DE


def test_completions_tier3_without_volume(d):
    with pytest.raises(ValueError, match="flowback_volume"):
        d.dispatch("completions", {"comp_tier": "tier3", "ch4_content": 80, "factor_source": "specific"}, {}, {})


def test_specific_facility_fugitive(d):
    res = d.dispatch("fugitive", {"factor_source": "specific", "fugitive_method": "facility",
                                  "facility_type": "oil_production", "amount": 1000, "unit": "bbl"}, {}, {})
    assert res["results"]["ch4"]["value"] == pytest.approx(1000 * 2.346e-4, rel=1e-9)    # Table 7-8, 1,000 bbl


def test_correlation_with_zero_screened_count(d):
    res = d.dispatch("fugitive", {"factor_source": "specific", "fugitive_method": "correlation",
                                  "correlation_type": "valve", "service_type": "gas", "corr_screened_count": "0",
                                  "corr_zero_count": 10, "operating_hours": 100, "ch4_wt_fraction": 0.6}, {}, {})
    # only the default-zero valves count (Table 7-41: 7.8e-6 kg TOC/h each): 10 x 7.8e-6 x 100 h x 0.6 wt CH4
    assert res["results"]["ch4"]["value"] == pytest.approx(10 * 7.8e-6 * 100 / 1000 * 0.6, rel=1e-9)


def test_associated_gas_period_days(d):
    base = {"tier": "tier2", "oil_production": 1000, "gor": 500, "venting_duration": 5,
            "duration_unit": "days", "ch4_content": 80}
    full = d.dispatch("associated_gas_venting", {**base, "period_days": 10}, {}, {})["results"]["ch4"]["value"]
    half = d.dispatch("associated_gas_venting", {**base, "period_days": 20}, {}, {})["results"]["ch4"]["value"]
    assert half == pytest.approx(full / 2)


def test_working_loss_factor_must_be_per_bbl(d):
    with pytest.raises(ValueError, match="Working-loss factor cannot be applied per bbl"):
        d.dispatch("tank_flashing", {"factor_source": "specific", "amount": 100, "unit": "bbl",
                                     "tank_method": "working_loss"},
                   {"ch4": 1.0, "unit": "tonne CH4/unit/hr"}, {})
