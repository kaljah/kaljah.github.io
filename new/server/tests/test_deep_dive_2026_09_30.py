"""Deep-dive audit through the running app (uploads and manual entries as each role), 2026-09-30.

1. A metered completion entered through the API with the volume in calc_inputs.amount (unit Mcf, no
   comp_volume) read the volume as the event count too: 500 Mcf was 500 events x 500 Mcf.
2. LNG facility factors (Table 7-76, "tonne CH4/facility") have no verified time basis; a monthly
   record must not book them.
"""
import json

import pytest

from app import app as flask_app
from calculations import compute_emissions
from calculations.constants import get_active_gwp
from services.scope1_calc import resolve_factor
from input_validation import ValidationError

GAS_M3 = 0.028316846592


def _run(payload):
    with flask_app.app_context():
        p = json.loads(json.dumps(payload))
        em, _ = compute_emissions(p, resolve_factor(p) or {}, gwp_dict=get_active_gwp(standard="AR5"))
        return em


@pytest.mark.parametrize("ci_extra", [{}, {"comp_method": "metered_volume"}, {"comp_volume": 500}])
def test_metered_completion_volume_is_not_an_event_count(ci_extra):
    ci = {"amount": 500, "unit": "Mcf", "ch4_content": 80, "comp_method": "metered_volume", **ci_extra}
    em = _run({"process_type": "completions", "factor_source": "specific", "year": 2022, "month": 3,
               "amount": 500, "unit": "Mcf", "calc_inputs": {"completions": ci}})
    assert em["ch4"] == pytest.approx(500_000 * GAS_M3 * 0.8 * 0.6785 / 1000, rel=1e-6)  # was x500


def test_completion_event_count_still_counts_events():
    em = _run({"process_type": "completions", "factor_source": "default", "year": 2022, "month": 3,
               "amount": 3, "unit": "events", "fuel": "Gas Well Completion - HF Uncontrolled",
               "calc_inputs": {"completions": {"amount": 3, "unit": "events", "tier": "tier1"}}})
    one = _run({"process_type": "completions", "factor_source": "default", "year": 2022, "month": 3,
                "amount": 1, "unit": "events", "fuel": "Gas Well Completion - HF Uncontrolled",
                "calc_inputs": {"completions": {"amount": 1, "unit": "events", "tier": "tier1"}}})
    assert em["ch4"] == pytest.approx(3 * one["ch4"], rel=1e-9) and one["ch4"] > 0


@pytest.mark.parametrize("name", ["LNG - Storage Station", "LNG - Import Terminal", "LNG - Export Terminal"])
def test_lng_facility_factor_without_time_basis_is_refused(name):
    with flask_app.app_context(), pytest.raises(ValidationError, match="no verified time basis"):
        resolve_factor({"process_type": "fugitive", "factor_source": "default", "fuel": name,
                        "amount": 1, "unit": "facilities", "year": 2022, "month": 3})


# -- Scope 2 steam / CHP (manual form) --------------------------------------------------------------

NG_KG = 53.06 + 0.001 * 28 + 0.0001 * 265  # default natural-gas boiler, AR5


def _steam(**kw):
    from routes.scope2 import _calc_indirect_steam

    with flask_app.app_context():
        return _calc_indirect_steam(kw)[0]


@pytest.mark.parametrize("eff", [0.85, 85, "85%"])
def test_steam_boiler_efficiency_percent_or_fraction(eff):
    got = _steam(amount=1000, unit="mmbtu", calc_inputs={"indirect_steam": {"boiler_eff": eff}})
    assert got == pytest.approx(1000 / 0.85 * NG_KG / 1000, rel=1e-9)  # 85 was used as 85x: 1/100


def test_steam_unknown_unit_and_percent_loss_are_refused():
    with pytest.raises(ValidationError, match="Unknown unit"):
        _steam(amount=1000, unit="furlong", calc_inputs={"indirect_steam": {"boiler_eff": 0.8}})
    with pytest.raises(ValidationError, match="Transmission loss"):
        _steam(amount=1000, unit="mmbtu", calc_inputs={"indirect_steam": {"boiler_eff": 0.8, "trans_loss": 5}})
    assert _steam(amount=1000, unit="MMBtu", calc_inputs={"indirect_steam": {"boiler_eff": 0.8}}) == \
        pytest.approx(1000 / 0.8 * NG_KG / 1000)


def test_chp_from_fuel_includes_boiler_ch4_n2o():
    from routes.scope2 import _calc_cogen_allocation

    with flask_app.app_context():
        got = _calc_cogen_allocation({"fuel_consumed_mmbtu": 10000, "heat_output_mmbtu": 5000,
                                      "power_output_mwh": 800, "allocation_method": "energy_content"})
    assert got == pytest.approx(10000 * NG_KG / 1000 * 5000 / (5000 + 800 * 3.412142), rel=1e-6)


# -- Scope 3 factor units ---------------------------------------------------------------------------

@pytest.mark.parametrize("unit,to_t", [
    ("MT CO2e/unit", 1.0), ("metric tons CO2e/unit", 1.0), ("short ton CO2e/unit", 0.90718474),
    ("kg CO2e/k$", 1e-6), ("kgCO2e/kUSD", 1e-6), ("kg CO2e/unit", 1e-3), ("t CO2e/unit", 1.0),
    ("g CO2e/km", 1e-6), ("kg CO2e/$1000", 1e-6), ("", 1e-3), ("kg CO2e/kWh", 1e-3),
])
def test_scope3_factor_units(unit, to_t):
    from calculations.units import compute_scope3_co2e

    assert compute_scope3_co2e(1000, 2.5, unit) == pytest.approx(2500 * to_t, rel=1e-12)


@pytest.mark.parametrize("unit", ["tons CO2e/unit", "kt CO2e/unit"])
def test_scope3_ambiguous_or_unknown_mass_is_refused(unit):
    from calculations.units import compute_scope3_co2e

    with pytest.raises(ValidationError):
        compute_scope3_co2e(1000, 2.5, unit)
