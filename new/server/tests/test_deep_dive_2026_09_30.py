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
    assert em["ch4"] == pytest.approx(500_000 * GAS_M3 * 0.8 * (16.04 / 23.685) / 1000, rel=1e-6)  # was x500


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


# -- API Compendium standard conditions (Section 3.4) ---------------------------------------------

def test_gas_densities_on_compendium_standard_conditions():
    """60 F / 14.696 psia; molar volume conversion 379.3 scf/lb-mole = 23.685 m3/kg-mole (the 0.6785 /
    1.861 used before were the 15 C values, 23.645 m3/kg-mole)."""
    from calculations.units import CONVERSIONS, MOLAR_VOLUME_M3_PER_KMOL, MOLAR_VOLUME_SCF_PER_LBMOL

    # the Compendium pairs 379.3 scf/lb-mole with 23.685 m3/kg-mole (0.03 % apart when converted exactly)
    assert MOLAR_VOLUME_SCF_PER_LBMOL * 0.028316846592 / 0.45359237 == pytest.approx(MOLAR_VOLUME_M3_PER_KMOL, rel=5e-4)
    assert CONVERSIONS["density_ch4"] == pytest.approx(0.67722, rel=1e-5)
    assert CONVERSIONS["density_co2"] == pytest.approx(1.85814, rel=1e-5)
    # 1 scf of CH4 = 16.04 / 379.3 lb, whichever unit the volume is entered in
    lb_per_scf = CONVERSIONS["density_ch4"] * 0.028316846592 / 0.45359237
    assert lb_per_scf == pytest.approx(16.04 / 379.3, rel=5e-4)
    from calculations.fugitive_onshore import DENSITY_CH4
    from services.intensity import CH4_DENSITY_KG_M3

    assert DENSITY_CH4 == pytest.approx(CONVERSIONS["density_ch4"]) and CH4_DENSITY_KG_M3 == CONVERSIONS["density_ch4"]


def test_wec_threshold_uses_part_99_methane_density():
    """40 CFR 99.20 Eq B-1: threshold = 0.002 x gas sent to sale (Mscf) x 0.0192 mt CH4/Mscf."""
    from services.intensity import WEC_CH4_DENSITY_T_PER_MSCF

    assert WEC_CH4_DENSITY_T_PER_MSCF == 0.0192
    import sys
    import os

    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))
    from validation.reference_model.aggregation_intensity import IndependentIntensityModel as M

    r = M.calculate_wec(100.0, gas_prod_m3=50e6, segment="upstream", year=2025)
    assert r["allowed_ch4_tonnes"] == pytest.approx(50e6 * 35.3146667 / 1000 * 0.002 * 0.0192)


# -- Invented / hard-coded values (2026-10-01) ------------------------------------------------------

def test_erp_sync_inserts_no_invented_records(admin2, monkeypatch):
    from models import Scope3Emission

    monkeypatch.setenv("ENABLE_MOCK_ERP", "true")  # the old flag no longer enables fake records
    with flask_app.app_context():
        before = Scope3Emission.query.count()
    r = admin2.post("/api/emissions/erp/sync")
    assert r.status_code == 501 and "No ERP connector" in r.get_json()["error"]
    with flask_app.app_context():
        assert Scope3Emission.query.count() == before


@pytest.mark.parametrize("seal,segment,kg_hr", [
    ("centrifugal_wet", "production", 26.0), ("reciprocating", "production", 0.443),
    ("centrifugal_wet", "processing", 86426 / 8760), ("centrifugal_dry", "processing", 28192 / 8760),
    ("reciprocating", "processing", 2.7), ("centrifugal_dry", "transmission", 5.75),
])
def test_compressor_seal_uses_compendium_factors_and_tier_1(seal, segment, kg_hr):
    from calculations.dispatcher import CalculationDispatcher

    r = CalculationDispatcher().dispatch("compressor_seal", dict(
        process_type="compressor_seal", factor_source="specific", compressor_count=2, seal_type=seal,
        segment=segment, hours=744), {}, {})
    assert r["results"]["ch4"]["value"] == pytest.approx(2 * kg_hr * 744 / 1000, rel=1e-9)
    assert r["results"]["ch4"]["tier"] == 1  # a Compendium default, not a measurement (was labelled Tier 3)


def test_compressor_seal_measured_rate_and_missing_factor():
    from calculations.dispatcher import CalculationDispatcher

    d = CalculationDispatcher()
    r = d.dispatch("compressor_seal", dict(process_type="compressor_seal", factor_source="specific",
                                           compressor_count=1, seal_type="dry", leak_rate_kg_hr=0.8, hours=100), {}, {})
    assert r["results"]["ch4"]["value"] == pytest.approx(0.08) and r["results"]["ch4"]["tier"] == 3
    with pytest.raises(ValueError, match="no centrifugal dry"):
        d.dispatch("compressor_seal", dict(process_type="compressor_seal", factor_source="specific",
                                           compressor_count=1, seal_type="dry", hours=100), {}, {})


def test_tank_table_default_is_labelled_tier_1():
    from calculations.dispatcher import CalculationDispatcher

    r = CalculationDispatcher().dispatch("tank_flashing", dict(process_type="tank_flashing", factor_source="specific",
                                                               amount=1000, unit="bbl"), {}, {})
    assert r["inputs"]["method"] == "table_6_22" and r["results"]["ch4"]["tier"] == 1


def test_eq_6_11_needs_the_gas_ch4_content():
    from calculations.dispatcher import CalculationDispatcher

    with pytest.raises(ValueError, match="CH4 content"):
        CalculationDispatcher().dispatch("unloading", dict(
            process_type="unloading", factor_source="specific", calc_method="api_equation_6_11", p_shut=150,
            p_line=50, p_sep=60, sfr_p=1000, t_p=1, unload_freq=4), {}, {})


def test_dehydrator_glycol_rate_alias_is_refused():
    from calculations.dispatcher import CalculationDispatcher

    with pytest.raises(ValueError, match="GLYCalc"):
        CalculationDispatcher().dispatch("dehydrator", dict(process_type="dehydrator", factor_source="specific",
                                                            amount=10, teg_pump_rate=200), {}, {})


def test_email_without_smtp_is_not_reported_as_sent(monkeypatch):
    from services.email_service import send_email

    monkeypatch.delenv("SMTP_HOST", raising=False)
    monkeypatch.delenv("SMTP_USER", raising=False)
    with flask_app.app_context():
        assert send_email("a@b.c", "s", "body") is False
