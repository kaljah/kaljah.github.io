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


# -- Round 2: remaining bugs ----------------------------------------------------------------------

def test_tank_measured_gor_zero_is_zero():
    from calculations.dispatcher import CalculationDispatcher

    d = CalculationDispatcher()
    base = dict(amount=1000, unit="bbl", factor_source="specific", tank_ch4_content=50)
    zero = d.dispatch("tank_flashing", dict(base, tank_gor=0), {}, {})
    assert zero["total_co2e"] == 0  # was the Table 6-22 default (3.3 t)
    default = d.dispatch("tank_flashing", dict(base), {}, {})
    assert default["total_co2e"] > 0  # no GOR given: the table default still applies


def test_completion_zero_flowback_duration_is_zero():
    from calculations.vented import CompletionFlowbackCalculator

    r = CompletionFlowbackCalculator().calculate(tier="tier2", calculation_method="production_rate_duration",
                                                 daily_production_rate=1000, prod_rate_unit="mcf/day",
                                                 flowback_duration_hours=0, ch4_content=0.8)
    assert r["results"]["ch4"]["value"] == 0  # 0 h was read as 24 h


EMAIL2 = "deep_dive_round2@ghg.com"


@pytest.fixture
def admin2(client):
    from extensions import db
    from models import User

    with flask_app.app_context():
        if not User.query.filter_by(email=EMAIL2).first():
            u = User(email=EMAIL2, fullName="Deep Dive", orgName="Audit", sector="Oil & Gas", role="admin",
                     location="Global")
            u.set_password("DeepDive0930!")
            db.session.add(u)
            db.session.commit()
    assert client.post("/api/auth/login", json={"email": EMAIL2, "password": "DeepDive0930!"}).status_code == 200
    return client


def _run_upload(text, scope, email=EMAIL2):
    import os
    import tempfile
    import uuid
    from background_processor import _process_file_thread, get_job_status, upload_jobs, upload_jobs_lock
    from models import User

    with flask_app.app_context():
        uid = User.query.filter_by(email=email).first().id
    fd, path = tempfile.mkstemp(suffix=".csv")
    os.write(fd, text.encode())
    os.close(fd)
    job = "dd-" + uuid.uuid4().hex
    with upload_jobs_lock:
        upload_jobs[job] = {"status": "processing", "progress": 0, "processed": 0, "total": 0, "errors": [],
                            "skipped": [], "error_csv_path": None, "anomalies": []}
    _process_file_thread(app=flask_app, job_id=job, file_path=path, original_filename="t.csv", user_id=uid,
                         global_factor_type="auto", provided_mapping=None, scope=scope, overwrite_duplicates=True)
    return get_job_status(job)


def test_csv_row_with_more_values_than_header_is_refused(admin2):
    from extensions import db
    from models import Emission, Facility

    with flask_app.app_context():
        if not Facility.query.filter_by(name="Deep Dive Shift").first():
            db.session.add(Facility(name="Deep Dive Shift", location="Algeria", country="Algeria", region="DDS",
                                    division="Production", field="DDS", segment="Upstream", activity="Upstream"))
            db.session.commit()
    text = ("Facility,Date,Process,Fuel,Quantity,Unit,Factor_Type\n"
            "Deep Dive Shift,2014-01,combustion,Diesel,10,gal,default\n"
            "Deep Dive Shift,2014-02,combustion,Diesel,,10,gal,default\n"      # extra comma: shifted
            "Deep Dive Shift,2014-03,combustion,Diesel,10,gal,default,,\n")    # trailing blanks: fine
    st = _run_upload(text, 1)
    assert st["skipped_count"] == 1 and "extra comma" in st["skipped_preview"][0]["reason"]
    with flask_app.app_context():
        fid = Facility.query.filter_by(name="Deep Dive Shift").first().id
        assert {e.month for e in Emission.query.filter_by(facility_id=fid, year=2014)} == {1, 3}


def test_custom_factor_parent_fuel_is_a_catalog_fuel(admin2):
    base = {"co2_factor": 73.96, "unit": "kg/MMBtu", "hhv_factor": 138000}
    r = admin2.post("/api/custom-factors", json=dict(base, name="DD diesel typo", parent_fuel="Deisel"))
    assert r.status_code == 400 and "catalog fuel" in r.get_json()["error"]
    r = admin2.post("/api/custom-factors", json=dict(base, name="DD diesel ok", parent_fuel="diesel"))
    assert r.status_code in (200, 201), r.get_json()
    from models import CustomFactor

    with flask_app.app_context():
        assert CustomFactor.query.filter_by(name="DD diesel ok").first().parent_fuel == "Diesel (No. 2 Fuel Oil)"


def test_chp_edit_recalculates_or_is_refused(admin2):
    from extensions import db
    from models import Facility

    with flask_app.app_context():
        if not Facility.query.filter_by(name="Deep Dive CHP").first():
            db.session.add(Facility(name="Deep Dive CHP", location="Algeria", country="Algeria", region="DDC",
                                    division="Production", field="DDC", segment="Upstream", activity="Upstream"))
            db.session.commit()
        fid = Facility.query.filter_by(name="Deep Dive CHP").first().id
    ci = {"total_emissions": 1000, "heat_output": 5000, "power_output": 800, "allocation_method": "energy_content"}
    r = admin2.post("/api/scope2", json={"facility_id": fid, "year": 2013, "month": 1, "source_type": "cogen_allocation",
                                          "amount": 1000, "calc_inputs": {"cogen_allocation": ci}})
    assert r.status_code == 201
    rid = (r.get_json().get("emission") or r.get_json().get("data") or r.get_json())["id"]
    assert admin2.put(f"/api/scope2/{rid}", json={"heat_mmbtu": 2500}).status_code == 422
    r = admin2.put(f"/api/scope2/{rid}", json={"calc_inputs": {"cogen_allocation": dict(ci, heat_output=2500)}})
    assert r.status_code == 200
    from models import Scope2Emission

    with flask_app.app_context():
        e = db.session.get(Scope2Emission, rid)
        assert e.co2e == pytest.approx(1000 * 2500 / (2500 + 800 * 3.412142), abs=1e-4)
        assert e.heat_mmbtu == 2500
