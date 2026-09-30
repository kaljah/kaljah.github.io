"""Calculation / CSV uploader audit, 2026-09-30.

1. Scope 3: a per-USD factor with an "EEIO" method was read as per $1,000 (1000x low), and a
   tonnes-per-1,000-units factor as kg per 1,000 units (1000x low).
2. Semicolon CSV (French / European Excel): "1,500" is 1.5, it was stored as 1500.
3. Bulk user uncertainty overwrote the propagated 1-sigma result instead of feeding the
   calculation like the manual form.
4. Catalog per-event / per-well-year / per-bbl factors used the amount whatever its unit
   (1,000 m3 of a completion factor = 1,000 completions).
5. "1%" efficiency was 100 %; "2%" file uncertainty was 200 %; 1 therm was not 0.1 MMBtu;
   an unknown Scope 2 source type was booked as electricity.
"""
import os
import tempfile

import pytest

from app import app as flask_app
from extensions import db
from models import Emission, Facility, Scope2Emission, Scope3Emission, User
from background_processor import (
    _decimal_comma_to_point, _file_uncertainty, _process_file_thread, get_job_status, upload_jobs, upload_jobs_lock,
)
from calculations.units import compute_scope3_co2e, convert, normalize_efficiency
from input_validation import ValidationError

FACILITY = "Calc Audit 0930 Facility"
EMAIL = "calc_audit_0930@ghg.com"
PASSWORD = "CalcAudit0930!"


@pytest.fixture
def user():
    with flask_app.app_context():
        u = User.query.filter_by(email=EMAIL).first()
        if not u:
            u = User(email=EMAIL, fullName="Calc Audit", orgName="Audit", sector="Oil & Gas", role="admin",
                     location="Global")
            u.set_password(PASSWORD)
            db.session.add(u)
            db.session.commit()
        return u.id


@pytest.fixture
def facility(user):
    with flask_app.app_context():
        f = Facility.query.filter_by(name=FACILITY).first()
        if not f:
            f = Facility(name=FACILITY, location="Hassi R'Mel", country="Algeria", region="Laghouat",
                         division="Production", field="Gas Field", segment="Upstream", created_by=user)
            db.session.add(f)
            db.session.commit()
        return f.id


def _upload(text, user_id, scope, name="audit.csv"):
    with flask_app.app_context():
        db.session.commit()
    fd, path = tempfile.mkstemp(suffix=".csv")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(text.encode("utf-8"))
        job_id = "job-calc-audit-" + os.urandom(6).hex()
        with upload_jobs_lock:
            upload_jobs[job_id] = {"status": "processing", "progress": 0, "processed": 0, "total": 0, "errors": [],
                                   "skipped": [], "error_csv_path": None, "anomalies": []}
        _process_file_thread(app=flask_app, job_id=job_id, file_path=path, original_filename=name, user_id=user_id,
                             global_factor_type="auto", provided_mapping=None, scope=scope, overwrite_duplicates=True)
        return get_job_status(job_id)
    finally:
        if os.path.exists(path):  # the upload thread deletes its file
            os.remove(path)


# -- 1. Scope 3 factor units ------------------------------------------------------------------

@pytest.mark.parametrize("amount, ef, unit, method, expected", [
    (100_000, 0.5, "kg CO2e/USD", "Spend-based (EEIO)", 50.0),        # was 0.05
    (100_000, 0.5, "", "Spend-based (EEIO)", 50.0),                   # stored EEIO record: no unit
    (5_000, 0.2, "t CO2e/1000 km", "", 1.0),                          # was 0.001
    (10, 2, "kg CO2e/1kWh", "", 0.02),
    (100_000, 350, "kg CO2e / $1000", "", 35.0),                      # unchanged
    (250_000, 3200.1, "kg CO2e/$1000", "spend_eeio", 800.025),        # unchanged
    (2_000, 1.5, "kg CO2e per $1,000", "", 0.003),
    (1_000, 4, "kg CO2e/10000 km", "", 4.0),
    (100, 0.43, "tCO2e / bbl", "", 43.0),
    (1_000, 120, "g CO2e/km", "", 0.12),
    (1_000, 2, "lb CO2e/gal", "", 0.90718474),
])
def test_scope3_factor_units(amount, ef, unit, method, expected):
    assert compute_scope3_co2e(amount, ef, unit, method) == pytest.approx(expected, rel=1e-12)


def test_scope3_edit_of_spend_based_record_is_not_1000x_low(client, user, facility):
    """A bulk EEIO record stores kg CO2e per USD and method "Spend-based (EEIO)"; editing its amount
    recalculated it as per $1,000."""
    with flask_app.app_context():
        rec = Scope3Emission(facility_id=facility, year=2025, month=4, category="Category 1",
                             sub_category="Spend-based: audit (NAICS 211120)", activity_data=100_000, unit="USD",
                             emission_factor=0.5, co2e=50.0, calculation_method="Spend-based (EEIO)",
                             created_by=user, status="Pending")
        db.session.add(rec)
        db.session.commit()
        rec_id = rec.id
    assert client.post("/api/auth/login", json={"email": EMAIL, "password": PASSWORD}).status_code == 200
    res = client.put(f"/api/scope3/{rec_id}", json={"activity_data": 200_000})
    assert res.status_code == 200, res.get_json()
    with flask_app.app_context():
        rec = db.session.get(Scope3Emission, rec_id)
        assert rec.co2e == pytest.approx(100.0)
        assert rec.emission_factor == pytest.approx(0.5)


def test_scope3_bulk_row_with_eeio_method_column(user, facility):
    csv = ("Facility,Date,Category,Amount,Unit,EmissionFactor,EFUnit,Calculation_Method\n"
           f"{FACILITY},2025-05,Category 1,100000,USD,0.5,kg CO2e/USD,Spend-based (EEIO)\n")
    status = _upload(csv, user, scope=3)
    assert status["status"] == "completed", status
    with flask_app.app_context():
        rec = Scope3Emission.query.filter_by(facility_id=facility, year=2025, month=5).first()
        assert rec.co2e == pytest.approx(50.0)


# -- 2. Decimal-comma (semicolon) CSV ------------------------------------------------------------

@pytest.mark.parametrize("cell, expected", [
    ("1,500", "1.500"), ("1,5", "1.5"), ("1.250,75", "1250.75"), ("12 345,6", "12345.6"), ("-0,25", "-0.25"),
    ("1 234,5", "1234.5"), ("2024-01", "2024-01"), ("Hassi Messaoud, Nord", "Hassi Messaoud, Nord"),
    ("1,234,567", "1,234,567"), ("1500", "1500"),
])
def test_decimal_comma_cells(cell, expected):
    assert _decimal_comma_to_point(cell) == expected


def test_semicolon_csv_reads_comma_as_decimal(user, facility):
    csv = ("Facility;Date;Process;Fuel;Quantity;Unit;Factor_Type\n"
           f"{FACILITY};2025-06;combustion;Natural Gas;1,500;MMBtu;default\n")
    status = _upload(csv, user, scope=1)
    assert status["status"] == "completed", status
    with flask_app.app_context():
        rec = Emission.query.filter_by(facility_id=facility, year=2025, month=6).first()
        assert rec.quantity == pytest.approx(1.5)
        assert rec.co2_emissions == pytest.approx(1.5 * 53.06 / 1000.0)


def test_comma_csv_keeps_thousands_separator(user, facility):
    csv = ("Facility,Date,Process,Fuel,Quantity,Unit,Factor_Type\n"
           f'{FACILITY},2025-07,combustion,Natural Gas,"1,500",MMBtu,default\n')
    status = _upload(csv, user, scope=1)
    assert status["status"] == "completed", status
    with flask_app.app_context():
        rec = Emission.query.filter_by(facility_id=facility, year=2025, month=7).first()
        assert rec.quantity == pytest.approx(1500.0)


# -- 3. Bulk user uncertainty = manual form ------------------------------------------------------

def test_bulk_user_uncertainty_is_propagated_like_the_manual_form(user, facility):
    from calculations import compute_emissions
    from calculations.constants import get_active_gwp
    from services.scope1_calc import apply_result, canonicalize, resolve_factor

    csv = ("Facility,Date,Process,Fuel,Quantity,Unit,Factor_Type,user_unc_co2\n"
           f"{FACILITY},2025-08,combustion,Natural Gas,1000,MMBtu,default,5\n")
    status = _upload(csv, user, scope=1)
    assert status["status"] == "completed", status
    with flask_app.app_context():
        bulk = Emission.query.filter_by(facility_id=facility, year=2025, month=8).first()
        payload = canonicalize({"process_type": "combustion", "source_type": "combustion", "factor_source": "default",
                                "fuel": "Natural Gas", "amount": 1000.0, "unit": "MMBtu", "year": 2025, "month": 8,
                                "facility_id": facility, "user_uncertainty": {"co2": 5.0}})
        fd = resolve_factor(payload)
        em, method = compute_emissions(payload, fd, gwp_dict=get_active_gwp())
        manual = Emission()
        apply_result(manual, payload, em, method, fd, "AR5")
        assert bulk.uncertainty == pytest.approx(manual.uncertainty)
        assert bulk.uncertainty != pytest.approx(0.05)  # not the raw input copied over the result


# -- 4. Catalog factors: the activity unit must match the factor's denominator --------------------

def _check(fuel, unit):
    from services.scope1_calc import check_activity_unit
    from emission_factors import API_FACTORS
    with flask_app.app_context():
        check_activity_unit(API_FACTORS[fuel], unit, fuel)


@pytest.mark.parametrize("fuel, unit", [
    ("Well Completion - Gas Well with Hydraulic Fracturing (Uncontrolled Venting)", "m3"),
    ("Workover - Gas Well (No Flaring)", "tonne"),
    ("Liquids Unloading - Plunger Lift (Tier 1 Default)", "scf"),
    ("Associated Gas Venting - US Average", "MMBtu"),
    ("Associated Gas Venting - US Average", "tonne"),
])
def test_incompatible_activity_unit_is_rejected(fuel, unit):
    with pytest.raises(ValidationError):
        _check(fuel, unit)


@pytest.mark.parametrize("fuel, unit", [
    ("Well Completion - Gas Well with Hydraulic Fracturing (Uncontrolled Venting)", "events"),
    ("Well Completion - Gas Well with Hydraulic Fracturing (Uncontrolled Venting)", "completions"),
    ("Liquids Unloading - Plunger Lift (Tier 1 Default)", "wells"),
    ("Associated Gas Venting - US Average", "bbl"),
    ("Associated Gas Venting - US Average", "m3"),
    ("Natural Gas", "scf"),       # energy factor: volume via the heating value
    ("Natural Gas", "MMBtu"),
    ("Natural Gas", "equipment"),  # not a parseable unit: left to the calculator
])
def test_compatible_activity_unit_is_accepted(fuel, unit):
    _check(fuel, unit)


def test_bulk_completion_in_m3_is_a_row_error(user, facility):
    csv = ("Facility,Date,Process,Fuel,Quantity,Unit,Factor_Type\n"
           f"{FACILITY},2025-09,completions,Workover - Gas Well (No Flaring),1000,m3,default\n")
    status = _upload(csv, user, scope=1)
    with flask_app.app_context():
        assert Emission.query.filter_by(facility_id=facility, year=2025, month=9).first() is None
    assert status["skipped_count"] == 1 or status["status"] == "error"


# -- 5. Percent signs, therm, Scope 2 source type -------------------------------------------------

def test_explicit_percent_efficiency():
    assert normalize_efficiency("1%") == pytest.approx(0.01)
    assert normalize_efficiency("0.5%") == pytest.approx(0.005)
    assert normalize_efficiency("98%") == pytest.approx(0.98)
    assert normalize_efficiency("98") == pytest.approx(0.98)
    assert normalize_efficiency("0.98") == pytest.approx(0.98)


def test_file_uncertainty_percent_sign():
    assert _file_uncertainty("2%") == pytest.approx(0.02)   # was 2.0 (200 %)
    assert _file_uncertainty("5") == pytest.approx(0.05)
    assert _file_uncertainty("0.05") == pytest.approx(0.05)
    assert _file_uncertainty("300%") is None


def test_therm_is_a_tenth_of_an_mmbtu():
    assert convert(10, "therm", "MMBtu") == pytest.approx(1.0, rel=1e-12)
    assert convert(1, "therm", "MJ") == pytest.approx(105.505585262, rel=1e-12)


def test_unknown_scope2_source_type_is_a_row_error(user, facility):
    csv = ("Facility,Date,Source_Type,Consumption,Unit,Grid_Region,Factor\n"
           f"{FACILITY},2025-10,district cooling,5000,kWh,,0.4\n"
           f"{FACILITY},2025-11,Purchased Steam,100,MMBtu,,\n")
    status = _upload(csv, user, scope=2)
    with flask_app.app_context():
        assert Scope2Emission.query.filter_by(facility_id=facility, year=2025, month=10).first() is None
        steam = Scope2Emission.query.filter_by(facility_id=facility, year=2025, month=11).first()
        assert steam is not None and steam.source_type == "indirect_steam"
    assert status["skipped_count"] == 1
