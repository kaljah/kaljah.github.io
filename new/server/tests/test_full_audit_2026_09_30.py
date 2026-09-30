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
