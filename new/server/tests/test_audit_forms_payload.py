"""Form / payload contract regressions (BUG-090, BUG-110).

Hand values:
- BUG-110 facility-level fugitives, API Compendium 2021 Table 7-8 (per unit of PRODUCTION, checked
  against the Compendium text): gas production 2.601E-02 t CH4 / 10^6 scf, oil production
  2.346E-04 t CH4 / bbl. 500 MMscf -> 13.005 t CH4; 20,000 bbl -> 4.692 t CH4.
"""
import pytest

from calculations.dispatcher import dispatcher

DEHY = {"dehy_throughput": 1000, "dehy_pump_rate": 5, "dehy_ch4_content": 85, "dehy_hours": 8760,
        "dehy_temp": 100, "factor_source": "specific"}


def _ch4(res):
    return res["results"]["ch4"]["value"]


def test_bug090_dehydrator_pressure_from_form_key_is_used():
    # BUG-090 made the contactor pressure reach the parametric solubility model; that model had no
    # API Compendium source and was removed (audit/TIER3_BROWSER_TEST.md #12). Its inputs are now
    # rejected with guidance instead of producing an unsourced result.
    for key in ("dehy_pressure", "dehy_press"):
        with pytest.raises(ValueError, match="GLYCalc"):
            dispatcher.dispatch("dehydrator", dict(DEHY, **{key: 200}), {})


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


UI_T1 = {"facility_type": "gas_production", "unit": "MMscf", "amount": 500, "fugitive_tier": "tier1",
         "factor_source": "default"}


def test_bug110_facility_level_fugitive_uses_table_7_8():
    r = dispatcher.dispatch("fugitive", dict(UI_T1), {})
    assert _ch4(r) == pytest.approx(500 * 2.601e-02)
    assert r["intermediate"]["api_table"] == "Table 7-8"
    oil = dispatcher.dispatch("fugitive", dict(UI_T1, facility_type="oil_production", amount=20000, unit="bbl"), {})
    assert _ch4(oil) == pytest.approx(20000 * 2.346e-04)


def test_bug110_gas_units_and_composition():
    r = dispatcher.dispatch("fugitive", dict(UI_T1, amount=500e6, unit="scf"), {})
    assert _ch4(r) == pytest.approx(500 * 2.601e-02)
    # site gas at 90 % CH4 scales the 78.8 % basis factor
    r = dispatcher.dispatch("fugitive", dict(UI_T1, ch4_content=90), {})
    assert _ch4(r) == pytest.approx(500 * 2.601e-02 * 0.90 / 0.788)


def test_bug110_unknown_facility_type_rejected():
    with pytest.raises(ValueError, match="facility type"):
        dispatcher.dispatch("fugitive", dict(UI_T1, facility_type="gas_pad_dehy"), {})
    with pytest.raises(ValueError, match="Oil production must be in bbl"):
        dispatcher.dispatch("fugitive", dict(UI_T1, facility_type="oil_production", unit="facilities"), {})


def test_bug110_unrecognised_fugitive_request_not_booked_as_valves(app):
    from calculations.legacy_engine import compute_emissions

    payload = {"process_type": "fugitive", "factor_source": "default", "amount": 2, "quantity": 2,
               "unit": "count", "calc_inputs": {"fugitive": {"amount": 2}}}
    with app.app_context(), pytest.raises(Exception):
        compute_emissions(payload, {})
