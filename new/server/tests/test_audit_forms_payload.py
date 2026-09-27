"""Form / payload contract regressions (BUG-090, BUG-110).

Hand values:
- BUG-110 facility-level fugitives, API Compendium 2021 Table 7-1 as held in
  calculations/fugitive_onshore.py: gas well pad with dehydrator 0.106 t CH4/facility-day,
  2 facilities x 365 d = 77.38 t CH4.
"""
import pytest

from calculations.dispatcher import dispatcher

DEHY = {"dehy_throughput": 1000, "dehy_pump_rate": 5, "dehy_ch4_content": 85, "dehy_hours": 8760,
        "dehy_temp": 100, "factor_source": "specific"}


def _ch4(res):
    return res["results"]["ch4"]["value"]


def test_bug090_dehydrator_pressure_from_form_key_is_used():
    lo = dispatcher.dispatch("dehydrator", dict(DEHY, dehy_pressure=200), {})
    hi = dispatcher.dispatch("dehydrator", dict(DEHY, dehy_pressure=1000), {})
    assert _ch4(lo) != pytest.approx(_ch4(hi))
    same = dispatcher.dispatch("dehydrator", dict(DEHY, dehy_press=200), {})
    assert _ch4(same) == pytest.approx(_ch4(lo))


AGR = {"agr_throughput": 100, "agr_unit": "MMscf/yr", "agr_co2_in": 5, "agr_co2_out": 0.1, "factor_source": "specific"}


def test_bug090_agr_control_is_applied():
    vent = dispatcher.dispatch("agr", dict(AGR), {})
    flare = dispatcher.dispatch("agr", dict(AGR, agr_control_type="flare", agr_control_eff=98), {})
    assert _ch4(flare) == pytest.approx(_ch4(vent) * 0.02)
    legacy = dispatcher.dispatch("agr", dict(AGR, offgas_to_flare=True, agr_control_eff=98), {})
    assert _ch4(legacy) == pytest.approx(_ch4(flare))


def test_bug090_agr_control_without_efficiency_is_rejected():
    with pytest.raises(ValueError, match="efficiency"):
        dispatcher.dispatch("agr", dict(AGR, agr_control_type="flare"), {})


UI_T1 = {"facility_type": "gas_pad_dehy", "unit": "facilities", "time_unit": "days", "facility_count": 2,
         "amount": 2, "fugitive_tier": "tier1", "fugitive_method": "component", "factor_source": "default",
         "operating_days": 365}


def test_bug110_facility_level_fugitive_uses_table_factor():
    r = dispatcher.dispatch("fugitive", dict(UI_T1), {})
    assert _ch4(r) == pytest.approx(2 * 0.106 * 365)
    assert r["intermediate"]["api_table"] == "Table 7-1"


def test_bug110_duration_in_months_matches_days():
    r = dispatcher.dispatch("fugitive", dict(UI_T1, operating_days=None, operating_hours=12, time_unit="months"), {})
    assert _ch4(r) == pytest.approx(2 * 0.106 * 365)


def test_bug110_unknown_facility_type_rejected():
    with pytest.raises(ValueError, match="facility type"):
        dispatcher.dispatch("fugitive", dict(UI_T1, facility_type="gas_production"), {})


def test_bug110_unrecognised_fugitive_request_not_booked_as_valves(app):
    from calculations.legacy_engine import compute_emissions

    payload = {"process_type": "fugitive", "factor_source": "default", "amount": 2, "quantity": 2,
               "unit": "count", "calc_inputs": {"fugitive": {"amount": 2}}}
    with app.app_context(), pytest.raises(Exception):
        compute_emissions(payload, {})
