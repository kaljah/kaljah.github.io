"""Full calculation audit (all modules), 2026-09-30.

1. Activity-factor rows read every CH4 content as a 0-100 percentage: 0.85 (typed, an Excel percent
   cell, or "85%" from the uploader) was 0.85 %, CH4 100x low.
2. Desiccant dehydrator refills are per year; every monthly record carried a full year of refills.
3. Flaring summary: operator stream volumes (FlaringDetail) of some facilities replaced the volumes of
   every facility, so record-only facilities dropped out of the flared volume while their gas
   production stayed in the Decree 21-330 intensity denominator.
4. Granular intensities: saleable production ignored the activity / division / segment filters.
"""
import pytest

from app import app as flask_app
from extensions import db
from models import Emission, Facility, FlaringDetail, ProductionData, User
from calculations.dispatcher import CalculationDispatcher

EMAIL = "full_audit_0930@ghg.com"
PASSWORD = "FullAudit0930!"


@pytest.fixture
def admin(client):
    with flask_app.app_context():
        if not User.query.filter_by(email=EMAIL).first():
            u = User(email=EMAIL, fullName="Full Audit", orgName="Audit", sector="Oil & Gas", role="admin",
                     location="Global")
            u.set_password(PASSWORD)
            db.session.add(u)
            db.session.commit()
    assert client.post("/api/auth/login", json={"email": EMAIL, "password": PASSWORD}).status_code == 200
    return client


def _facility(name, segment="Upstream", division="Production"):
    f = Facility.query.filter_by(name=name).first()
    if not f:
        f = Facility(name=name, location="Algeria", country="Algeria", region=name, division=division,
                     field=name, segment=segment, activity=segment)
        db.session.add(f)
        db.session.commit()
    return f.id


# -- 1. Activity-factor CH4 content --------------------------------------------------------------

@pytest.mark.parametrize("ch4", [85, 0.85, "85"])
def test_activity_factor_ch4_percent_or_fraction(ch4):
    d = CalculationDispatcher()
    r = d.dispatch("casing_gas", dict(process_type="casing_gas", factor_source="default", activity_key="cg_primary_heavy",
                                      amount=10000, unit="bbl", year=2025, month=3, ch4_content=ch4), {}, {})
    # Table 6-12: 3.28e-3 t CH4/bbl at 81.6 % CH4, scaled to the site's 85 %
    assert r["results"]["ch4"]["value"] == pytest.approx(10000 * 3.28e-3 * 0.85 / 0.816, rel=1e-9)


# -- 2. Desiccant refills per year ---------------------------------------------------------------

def test_desiccant_refills_are_prorated_to_the_month():
    d = CalculationDispatcher()
    base = dict(process_type="desiccant_dehydrator", factor_source="specific", vent_method="desiccant",
                vessel_height_ft=10, vessel_diameter_ft=3, vessel_pressure_psig=500, refills=12, ch4_content=85)
    year = d.dispatch("desiccant_dehydrator", base, {}, {})["results"]["ch4"]["value"]
    march = d.dispatch("desiccant_dehydrator", dict(base, year=2025, month=3), {}, {})["results"]["ch4"]["value"]
    assert march == pytest.approx(year * 31 / 365, rel=1e-9)  # was equal to the year


# -- 3. Flaring summary population ----------------------------------------------------------------

def test_flaring_summary_keeps_record_only_facilities(admin):
    with flask_app.app_context():
        a = _facility("Full Audit Flare A")
        b = _facility("Full Audit Flare B")
        for fid in (a, b):
            db.session.add(ProductionData(facility_id=fid, year=2019, month=1, oil_amount=0, gas_amount=1_000_000,
                                          gas_unit="m3", oil_unit="bbl"))
        db.session.add(FlaringDetail(facility_id=a, year=2019, routine_knm3=5.0))  # 5,000 m3 reported
        db.session.add(Emission(facility_id=b, year=2019, month=1, process_type="flaring", quantity=7000, unit="m3",
                                co2_emissions=10, ch4_emissions=0, n2o_emissions=0, co2e_total=10, status="Verified"))
        db.session.commit()
    ids = ",".join(str(x) for x in (a, b))
    res = admin.get("/api/dashboard/flaring-summary?year=2019&division=Production")
    assert res.status_code == 200, res.get_json()
    js = res.get_json()
    # both facilities: 5,000 m3 (reported) + 7,000 m3 (records) over 2,000,000 m3 of gas
    assert js["total_flaring"]["volume_m3"] == pytest.approx(12000.0), ids
    assert js["flaring_intensity_pct"] == pytest.approx(0.6)


# -- 4. Granular intensities: saleable production filtered like the emissions ---------------------

def test_granular_saleable_production_uses_the_filters(admin):
    with flask_app.app_context():
        up = _facility("Full Audit Up", segment="Upstream", division="Production")
        down = _facility("Full Audit Down", segment="Downstream", division="Refining")
        for fid, sale in ((up, 1.0), (down, 9.0)):
            db.session.add(ProductionData(facility_id=fid, year=2018, month=1, oil_amount=1000, oil_unit="bbl",
                                          gas_amount=0, gas_unit="mscf", saleable_production_mmboe=sale))
            db.session.add(Emission(facility_id=fid, year=2018, month=1, process_type="combustion", quantity=1,
                                    unit="MMBtu", co2_emissions=1000, ch4_emissions=0, n2o_emissions=0,
                                    co2e_total=1000, status="Verified"))
        db.session.commit()
    js = admin.get("/api/dashboard/granular-intensities?year=2018&segment=Upstream").get_json()
    assert js["saleable_production_boe"] == pytest.approx(1.0e6)          # was 10e6 (both facilities)
    assert js["ci_by_saleable_production_kg_boe"] == pytest.approx(1000 * 1000 / 1.0e6)


# -- 5. JV equity allocation covers Scope 1 and Scope 2 -------------------------------------------

def test_equity_allocation_includes_scope2(admin):
    from models import Scope2Emission

    with flask_app.app_context():
        fid = _facility("Full Audit Equity")
        db.session.add(Emission(facility_id=fid, year=2017, month=1, process_type="combustion", quantity=1,
                                unit="MMBtu", co2_emissions=100, ch4_emissions=1, n2o_emissions=0, co2e_total=128,
                                status="Verified"))
        db.session.add(Scope2Emission(facility_id=fid, year=2017, month=1, source_type="electricity",
                                      electricity_kwh=100000, emission_factor=0.5, co2e=50, status="Verified"))
        fac = db.session.get(Facility, fid)
        fac.equity_share_pct = 40.0
        db.session.commit()
    rows = admin.get(f"/api/equity/allocation?year=2017&facility_id={fid}").get_json()
    row = rows[0]
    assert row["total_scope1"] == pytest.approx(128) and row["total_scope2"] == pytest.approx(50)
    assert row["total_co2e"] == pytest.approx(178)
    alloc = sum(p["allocated_co2e"] for p in row["partners"])
    shares = sum(p["equity_pct"] for p in row["partners"])
    assert alloc == pytest.approx(178 * shares / 100.0)
    for p in row["partners"]:
        assert p["allocated_co2e"] == pytest.approx(p["allocated_scope1"] + p["allocated_scope2"], abs=0.02)


# -- 6. A bare "ton" in an uploaded file is refused ------------------------------------------------

def test_bare_ton_detection():
    from background_processor import _bare_ton_error, _is_bare_ton

    for u in ("ton", "Tons", "kg/ton", "t CO2/tons"):
        assert _is_bare_ton(u), u
    for u in ("tonne", "tonnes", "short_ton", "short ton", "long ton", "metric ton", "ton-km", "t", "kg/tonne"):
        assert not _is_bare_ton(u), u
    assert _bare_ton_error({"unit": "ton"})
    assert _bare_ton_error({"unit": "tonne", "fuel_mass_unit": "tons"})
    assert _bare_ton_error({"unit": "MMBtu", "notes": "1 ton"}) is None


def test_bare_ton_row_is_refused_and_explicit_units_are_calculated(admin):
    import os
    import tempfile
    from background_processor import _process_file_thread, get_job_status, upload_jobs, upload_jobs_lock

    with flask_app.app_context():
        _facility("Full Audit Ton")
        uid = User.query.filter_by(email=EMAIL).first().id
    text = ("Facility,Date,Process,Fuel,Quantity,Unit,Factor_Type\n"
            "Full Audit Ton,2016-01,combustion,Bituminous Coal,10,ton,default\n"
            "Full Audit Ton,2016-02,combustion,Bituminous Coal,10,short_ton,default\n"
            "Full Audit Ton,2016-03,combustion,Bituminous Coal,10,tonne,default\n")
    fd, path = tempfile.mkstemp(suffix=".csv")
    os.write(fd, text.encode())
    os.close(fd)
    with upload_jobs_lock:
        upload_jobs["ton-job"] = {"status": "processing", "progress": 0, "processed": 0, "total": 0, "errors": [],
                                  "skipped": [], "error_csv_path": None, "anomalies": []}
    _process_file_thread(app=flask_app, job_id="ton-job", file_path=path, original_filename="t.csv", user_id=uid,
                         global_factor_type="auto", provided_mapping=None, scope=1, overwrite_duplicates=True)
    st = get_job_status("ton-job")
    assert st["skipped_count"] == 1 and "ambiguous" in st["skipped_preview"][0]["reason"]
    with flask_app.app_context():
        fid = Facility.query.filter_by(name="Full Audit Ton").first().id
        short = Emission.query.filter_by(facility_id=fid, year=2016, month=2).first()
        metric = Emission.query.filter_by(facility_id=fid, year=2016, month=3).first()
        assert Emission.query.filter_by(facility_id=fid, year=2016, month=1).first() is None
        assert metric.co2_emissions / short.co2_emissions == pytest.approx(1000 / 907.18474, rel=1e-9)


# -- 7. A GWP switch recalculates Scope 2 as well ---------------------------------------------------

def test_gwp_switch_recalculates_scope2(admin):
    from models import Scope2Emission
    from electricity_factors import grid_entry, grid_factor_kg_co2e_per_kwh
    from calculations.constants import GWP_AR5, GWP_AR6

    with flask_app.app_context():
        fid = _facility("Full Audit GWP")
    assert admin.put("/api/auth/settings", json={"gwp_standard": "AR5"}).status_code == 200
    r1 = admin.post("/api/scope2", json=dict(facility_id=fid, year=2015, month=1, source_type="electricity",
                                            electricity_kwh=1_000_000, grid_region="Algerian National Grid", unit="kWh"))
    r2 = admin.post("/api/scope2", json=dict(facility_id=fid, year=2015, month=2, source_type="indirect_steam",
                                            amount=5000, unit="MMBtu", boiler_efficiency=0.8))
    assert r1.status_code == 201 and r2.status_code == 201
    with flask_app.app_context():
        before = {e.month: e.co2e for e in Scope2Emission.query.filter_by(facility_id=fid, year=2015)}
    try:
        assert admin.put("/api/auth/settings", json={"gwp_standard": "AR6"}).status_code == 200
        with flask_app.app_context():
            after = {e.month: e.co2e for e in Scope2Emission.query.filter_by(facility_id=fid, year=2015)}
            entry = grid_entry("Algerian National Grid")[1]
            assert after[1] == pytest.approx(1_000_000 * grid_factor_kg_co2e_per_kwh(entry, gwp=GWP_AR6) / 1000.0)
            k = lambda g: 53.06 + 0.001 * g["CH4"] + 0.0001 * g["N2O"]
            assert after[2] == pytest.approx(5000 / 0.8 * k(GWP_AR6) / 1000.0, rel=1e-6)
            assert after[2] != pytest.approx(before[2], rel=1e-9)
    finally:
        assert admin.put("/api/auth/settings", json={"gwp_standard": "AR5"}).status_code == 200
    with flask_app.app_context():
        back = {e.month: e.co2e for e in Scope2Emission.query.filter_by(facility_id=fid, year=2015)}
        assert back[1] == pytest.approx(before[1], rel=1e-9) and back[2] == pytest.approx(before[2], rel=1e-6)
        assert GWP_AR5["CH4"] == 28.0
