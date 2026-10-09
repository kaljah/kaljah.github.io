"""Regression tests for the Tier 3 browser test findings (audit/TIER3_BROWSER_TEST.md).

Payloads have the shape the Scope 1 form sends; expected values are the API Compendium 2021
exhibits / tables or hand values from the stated equation (379.3 scf/lbmol, 2,204.62 lb/t).
"""
import json

import pytest

from calculations.constants import get_active_gwp
from calculations.legacy_engine import compute_emissions
from services.scope1_calc import resolve_factor

LB = 2204.62


def gas(v_scf, y, mw):
    return v_scf * y / 379.3 * mw / LB


def run(app, process, source="specific", top=None, **ci):
    p = {"process_type": process, "factor_source": source, **(top or {}), "calc_inputs": {process: ci}}
    with app.app_context():
        p = json.loads(json.dumps(p))
        em, _ = compute_emissions(p, resolve_factor(p) or {}, gwp_dict=get_active_gwp(standard="AR5"))
        return em


def fails(app, match, process, source="specific", top=None, **ci):
    with pytest.raises(Exception, match=match):
        run(app, process, source, top, **ci)


# 1 — the metered flowback volume is not an event count (Exhibit 6-3)
def test_1_completions_metered_volume_is_not_events(app):
    em = run(app, "completions", top={"amount": 1480000, "quantity": 1480000, "unit": "scf"},
             comp_volume=1480000, flowback_volume=1480000, amount=1480000, volume_unit="scf", unit="scf",
             comp_injected_n2=7390, comp_initial_flowback_hours=4, comp_duration=20, ch4_content=70, co2_content=0,
             comp_c2plus_content=30, comp_disposition="flared", disposition="flared", tier="tier3",
             comp_injected_n2_unit="scf", calc_method="metered")
    assert em["ch4"] == pytest.approx(2.36, rel=0.02)
    assert em["co2"] == pytest.approx(98.7, rel=0.02)


# 2 — associated gas venting Tier 3: the duration is in hours
def test_2_agv_rate_duration_in_hours(app):
    em = run(app, "associated_gas_venting", top={"amount": 150, "unit": "scf"}, tier="tier3",
             calc_method="api_equation_6_8_direct", tier3_mode="rate", vent_rate=150, vent_rate_unit="scfh",
             venting_duration=72, duration_unit="hours", ch4_content=85, co2_content=2.5)
    assert em["ch4"] == pytest.approx(gas(10800, .85, 16.04), rel=0.01)
    assert em["co2"] == pytest.approx(gas(10800, .025, 44.01), rel=0.01)


# 3 / 4 — screening ranges route to Table 7-26 (not to direct measurement)
def test_3_4_method21_ranges_table_7_26(app):
    em = run(app, "fugitive", fugitive_tier="tier3", fugitive_method="method21", m21_component="valve",
             m21_service="gas", m21_below_count=95, m21_above_count=5, operating_hours=8760)
    # Table 7-26 valves-gas 2.5E-05 / 9.8E-02 kg TOC/h; Table C-1 gas production 0.920 CH4 wt
    assert em["ch4"] == pytest.approx((95 * 2.5e-5 + 5 * 9.8e-2) * 0.92 * 8760 / 1000, rel=1e-3)
    assert not em["co2"]
    # older payload: one screening value for `amount` components
    em = run(app, "fugitive", fugitive_tier="tier3", fugitive_method="method21", screening_ppm=15000, amount=5)
    assert em["ch4"] == pytest.approx(5 * 9.8e-2 * 0.92 * 8760 / 1000, rel=1e-3)


def test_4_method21_na_factor_rejected_and_water_oil_needs_ch4(app):
    fails(app, "no >= 10,000", "fugitive", fugitive_tier="tier3", fugitive_method="method21",
          m21_component="valve", m21_service="heavy_oil", m21_above_count=1)
    fails(app, "CH4 weight fraction", "fugitive", fugitive_tier="tier3", fugitive_method="method21",
          m21_component="valve", m21_service="water_oil", m21_below_count=10)


# 5 — leaker survey: Table 7-23 whole-gas factors
def test_5_ogi_table_7_23(app):
    em = run(app, "fugitive", fugitive_tier="tier3", fugitive_method="ogi", ogi_component="valve",
             ogi_service="gas", leakers_count=2, operating_hours=8760)
    assert em["ch4"] == pytest.approx(2 * 7.7e-5 * 8760, rel=0.01)
    em = run(app, "fugitive", fugitive_tier="tier3", fugitive_method="ogi", ogi_component="connector",
             ogi_service="light_crude", leakers_count=10, operating_hours=8760, ch4_content=70, co2_content=5)
    assert em["ch4"] == pytest.approx(gas(10 * 1.0 * 8760, .70, 16.04), rel=0.01)
    assert em["co2"] == pytest.approx(gas(10 * 1.0 * 8760, .05, 44.01), rel=0.01)


# 7 — direct measurement: explicit units, no hidden composition
def test_7_direct_measurement_units(app):
    em = run(app, "fugitive", fugitive_tier="tier3", fugitive_method="measurement", measured_rate=0.5,
             rate_unit="kg/hr", operating_hours=8760)
    assert em["ch4"] == pytest.approx(4.38, rel=1e-6)
    assert not em["co2"]
    em = run(app, "fugitive", fugitive_tier="tier3", fugitive_method="measurement", measured_rate=10,
             rate_unit="scf/hr", operating_hours=8760, ch4_content=78.8)
    assert em["ch4"] == pytest.approx(gas(87600, .788, 16.04), rel=0.01)
    fails(app, "CH4 content", "fugitive", fugitive_tier="tier3", fugitive_method="measurement",
          measured_rate=10, rate_unit="scf/hr", operating_hours=8760)
    fails(app, "unit", "fugitive", fugitive_tier="tier3", fugitive_method="measurement", measured_rate=10)


# stale keys of another method do not re-route a record (#20)
def test_20_explicit_fugitive_method_wins_over_stale_keys(app):
    em = run(app, "fugitive", fugitive_tier="tier3", fugitive_method="correlation", correlation_type="flange",
             corr_zero_count=95, corr_screened_count=4, screening_ppm=7950, corr_pegged_10k_count=1,
             leakers_count=2, operating_hours=8760)
    assert em["ch4"] == pytest.approx(0.47, rel=0.01)


# 8 — flaring variants calculate like flaring (engine side of the missing form)
@pytest.mark.parametrize("process", ["routine_flaring", "non_routine_flaring", "safety_flaring"])
def test_8_flaring_variants_metered_volume(app, process):
    em = run(app, process, top={"amount": 20e6, "unit": "scf", "hhv": 1020}, hhv=1020, ch4_content=80,
             unit="scf", amount=20e6)
    assert em["ch4"] == pytest.approx(gas(20e6, .8 * .02, 16.04), rel=0.01)
    assert em["co2"] == pytest.approx(gas(20e6, .8 * .965, 44.01), rel=0.01)


# 9 — AGR: slip is a fraction of inlet CH4; blank slip -> Table 6-19; form percentages
def test_9_agr_slip_and_percent_inputs(app):
    base = dict(agr_throughput=1000, agr_unit="MMscf/yr", agr_co2_in=5, agr_co2_out=0.05, ch4_mole_pct=85)
    top = {"amount": 1000, "unit": "MMscf/yr"}
    em = run(app, "agr", top=top, methane_slip_factor=0.0004, **base)
    assert em["ch4"] == pytest.approx(gas(1e9 * .85 * .0004, 1, 16.04), rel=0.01)
    assert em["co2"] == pytest.approx(gas(1e9 * (0.05 - 0.0005), 1, 44.01), rel=0.01)
    em = run(app, "agr", top=top, **base)
    assert em["ch4"] == pytest.approx(1000 * 0.0185, rel=1e-6)
    em = run(app, "agr", top=top, **{**base, "agr_co2_in": 0.9})
    assert em["co2"] == pytest.approx(gas(1e9 * (0.009 - 0.0005), 1, 44.01), rel=0.01)
    fails(app, "Outlet CO2", "agr", top=top, **{**base, "agr_co2_out": 6})


# 10 — Tier 3 fuel analysis without composition or factors is rejected (was a 0 t record)
def test_10_combustion_tier3_hhv_only_rejected(app):
    top = {"amount": 8e8, "unit": "scf", "hhv": 1020, "combustion_efficiency": 1}
    fails(app, "composition", "combustion", top=top, hhv=1020, combustion_efficiency=1)
    em = run(app, "combustion", top={"amount": 1000, "unit": "m3", "hhv": 1020, "combustion_efficiency": 0.995,
                                     "specific_factors": {"co2": 1.9, "co2Unit": "kg/m3", "ch4": 0.01, "ch4Unit": "kg/m3"}},
             hhv=1020)
    assert em["co2"] == pytest.approx(1.9)


# 11 — working / breathing losses: total hydrocarbon loss x vent wt % (Section 6.3.9.3)
@pytest.mark.parametrize("process", ["tank_working", "tank_breathing"])
def test_11_working_breathing_losses(app, process):
    em = run(app, process, vent_method="thc_mass", thc_loss=12.5, thc_loss_unit="t", ch4_wt_pct=8, co2_wt_pct=1)
    assert em["ch4"] == pytest.approx(1.0) and em["co2"] == pytest.approx(0.125)
    fails(app, "Working and breathing", process, top={"amount": 164615, "unit": "bbl"}, tank_gor=47, ch4_content=27.4)


# 12 — dehydrator Tier 3: simulation / measurement, no unsourced model
def test_12_dehydrator_tier3(app):
    em = run(app, "dehydrator", vent_method="reported_mass", ch4_mass=22.06, co2_mass=1.2, control_efficiency=90)
    assert em["ch4"] == pytest.approx(2.206) and em["co2"] == pytest.approx(0.12)
    fails(app, "GLYCalc", "dehydrator", dehy_throughput=9125, dehy_pump_rate=200, dehy_ch4_content=90)


# 13 / 14 — unloading: CO2 kept, 1 mol % is 1 %, decompression = Eq 6-10 casing term (gauge)
def test_13_14_unloading(app):
    em = run(app, "unloading", calc_method="api_equation_6_10", unloading_type="non_plunger", unload_events=12, unload_diam=10,
             unload_depth=12000, unload_press=250, sfr=35000, hours_open=1, ch4_content=80, co2_content=3)
    assert em["ch4"] == pytest.approx(20.39, rel=0.01) and em["co2"] == pytest.approx(2.10, rel=0.01)
    v = 12 * 0.37e-3 * 2.5 ** 2 * 5000 * 150
    em = run(app, "unloading", calc_method="well_decompression", unload_freq=12, unload_diam=2.5,
             unload_depth=5000, unload_press=150, ch4_content=85, co2_content=1, unload_temp=60)
    assert em["ch4"] == pytest.approx(gas(v, .85, 16.04), rel=0.01)
    assert em["co2"] == pytest.approx(gas(v, .01, 44.01), rel=0.01)


# 15 — blowdown volume in the unit shown (Exhibit 6-25)
def test_15_blowdown_unit(app):
    em = run(app, "venting", top={"amount": 83.8, "unit": "ft3"}, blowdown_volume=83.8, blowdown_unit="ft3",
             blowdown_pressure=100, blowdown_events=1, ch4_content=90, co2_content=0, blowdown_temp=80)
    assert em["ch4"] == pytest.approx(0.011, rel=0.02)


# 18 / 19 — stored activity and uncertainty (POST path)
@pytest.fixture
def api(app, client):
    from tests.audit_helpers import login, make_facility, make_user

    with app.app_context():
        f = make_facility(region="West")
        login(client, make_user("admin", "Global"))
        yield f


def _post(client, f, process, source, top=None, **ci):
    body = {"facility_id": f.id, "year": 2025, "month": 3, "process_type": process, "factor_source": source,
            **(top or {}), "calc_inputs": {process: ci}}
    r = client.post("/api/emissions/", json=body)
    assert r.status_code == 201, r.get_json()
    return r.get_json()


def test_18_engineered_record_stores_its_activity(app, client, api):
    from models import Emission

    rid = _post(client, api, "vented_gas", "specific", vent_method="volume", gas_volume=1e6,
                gas_volume_unit="scf", ch4_content=90)["id"]
    with app.app_context():
        rec = Emission.query.get(rid)
        assert rec.quantity == pytest.approx(1e6) and rec.unit == "scf"


def test_19_entered_factor_record_has_uncertainty(app, client, api):
    from models import Emission

    rid = _post(client, api, "combustion", "specific",
                top={"amount": 1000, "quantity": 1000, "unit": "m3", "hhv": 1020, "combustion_efficiency": 0.995,
                     "specific_factors": {"co2": 1.9, "co2Unit": "kg/m3", "ch4": 0.01, "ch4Unit": "kg/m3"}},
                hhv=1020)["id"]
    with app.app_context():
        rec = Emission.query.get(rid)
        assert rec.uncertainty is not None and rec.uncertainty_ch4 is not None


# ---- follow-up fixes (audit/TIER3_BROWSER_TEST.md, "Remaining issues") ----
def test_exhibit_4_4a_n2_is_read_not_renormalised(app):
    # N2 1.6 % under the form key n2_content: the analysis is complete, nothing is renormalised
    # (dropping N2 inflated the hydrocarbons by 1/0.984). Expected: Eq 4-11, 1.014 mol C / mol gas.
    em = run(app, "combustion", top={"amount": 8e8, "unit": "scf", "hhv": 1020, "combustion_efficiency": 1},
             hhv=1020, combustion_efficiency=100, c1=95.3, c2=1.7, c3=0.5, c4=0.1, co2_content=0.8, n2_content=1.6)
    assert em["co2"] == pytest.approx(800e6 / 379.3 * 1.014 * 44.01 / LB, rel=5e-3)


def test_tier3_zero_result_is_saved_as_zero(app):
    em = run(app, "fugitive", fugitive_tier="tier3", fugitive_method="ogi", ogi_component="valve",
             ogi_service="gas", leakers_count=2, operating_hours=0)
    assert em["ch4"] == 0 and em["totalCo2e"] == 0


def test_equipment_factor_not_ch4_needs_weight_fraction(app):
    from calculations.fugitive_onshore import OnshoreEquipmentFugitiveCalculator
    calc = OnshoreEquipmentFugitiveCalculator()
    with pytest.raises(ValueError, match="CH4 weight fraction"):
        calc.calculate(equipment_count=10, equipment_type="x", factor_value=0.0045, factor_unit="kg/hr")
    res = calc.calculate(equipment_count=10, equipment_type="x", factor_value=0.0045, factor_unit="kg/hr",
                         ch4_wt_fraction=0.8)
    assert res["results"]["ch4"]["value"] == pytest.approx(10 * 0.0045 * 0.8 * 8760 / 1000)


def test_tier2b_component_count_uses_table_7_12(app):
    em = run(app, "fugitive", source="custom", top={"amount": 100, "unit": "components"}, fugitive_tier="tier2",
             fugitive_method="component", component_type="valve", service_type="gas", amount=100,
             operating_hours=8760, ch4_mole_pct=70)
    assert em["ch4"] == pytest.approx(100 * 2.94e-6 * 8760 * 70 / 81.6, rel=1e-6)
    fails(app, "component type", "fugitive", source="custom", top={"amount": 100, "unit": "components"},
          fugitive_tier="tier2", fugitive_method="component", amount=100)


def test_cap_compliance_not_measured_is_not_compliant(app, client, api):
    from models import CapEmission
    from extensions import db

    with app.app_context():
        db.session.add(CapEmission(facility_id=api.id, year=2032, source_module="Flare", pollutant="NO2",
                                   mass_tonnes=5.0, status="Verified"))
        db.session.commit()
    rows = client.get(f"/api/cap/compliance?year=2032&facility_id={api.id}").get_json()
    no2 = [p for r in rows for p in r["pollutants"] if p["pollutant"] == "NO2"][0]
    assert no2["status"] == "NOT MEASURED" and no2["is_compliant"] is None and no2["total_tonnes"] == 5.0
    assert rows[0]["overall_status"] == "NOT ASSESSED"
