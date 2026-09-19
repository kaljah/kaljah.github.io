import pytest
from app import app
from calculations.fugitive import ComponentFugitiveCalculator
from calculations.vented import TankFlashingCalculator
from models import OgmpSurvey, Goal, Facility, User
from extensions import db

@pytest.fixture
def client():
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False
    with app.test_client() as c:
        with app.app_context():
            yield c

@pytest.fixture
def test_users():
    with app.app_context():
        admin = User.query.filter_by(email="bugfix_admin@test.com").first()
        if not admin:
            admin = User(
                email="bugfix_admin@test.com",
                fullName="BugFix Admin",
                orgName="TestCorp",
                sector="Energy",
                role="admin",
                location="Global Corporate Head Office",
            )
            admin.set_password("AdminPass123!")
            db.session.add(admin)
        else:
            admin.role = "admin"
            admin.location = "Global Corporate Head Office"

        user = User.query.filter_by(email="bugfix_user@test.com").first()
        if not user:
            user = User(
                email="bugfix_user@test.com",
                fullName="BugFix User",
                orgName="TestCorp",
                sector="Energy",
                role="admin",
                location="Global Corporate Head Office",
            )
            user.set_password("UserPass123!")
            db.session.add(user)
        else:
            user.role = "admin"
            user.location = "Global Corporate Head Office"

        db.session.commit()
        return {"admin": admin.id, "user": user.id}

def test_component_fugitive_calculator_scalar_counts():
    """Verify ComponentFugitiveCalculator handles scalar counts without AttributeError."""
    calc = ComponentFugitiveCalculator()
    # Passing scalar counts instead of nested dicts
    counts = {"valves": 50, "flanges": 120}
    res = calc.calculate(component_counts=counts, ch4_content=0.85, uncertainties={})
    assert res is not None
    assert "results" in res
    assert "ch4" in res["results"]
    assert "total_co2e" in res
    assert res["total_co2e"] >= 0

def test_tank_flashing_calculator_null_gor():
    """Verify TankFlashingCalculator handles null or missing GOR without TypeError."""
    calc = TankFlashingCalculator()
    res = calc.calculate(
        throughput=1000.0,
        gas_oil_ratio=None,
        ch4_content=None,
        control_efficiency=0.0,
        uncertainties={},
        process_type="tank_flashing"
    )
    assert res is not None
    assert "total_co2e" in res
    assert res["total_co2e"] == 0.0

def test_delete_mitigation_invalid_id_format(client, test_users):
    """Verify delete_mitigation returns 400 Bad Request on malformed ID instead of 500 crash."""
    with client.session_transaction() as sess:
        sess["user_id"] = test_users["admin"]

    resp = client.delete("/api/mitigation/proj_nonnumeric")
    assert resp.status_code == 400
    data = resp.get_json()
    assert "error" in data
    assert "Invalid" in data["error"]

    resp2 = client.delete("/api/mitigation/rec_invalid")
    assert resp2.status_code == 400

def test_ogmp_survey_null_measured_rate(client, test_users):
    """Verify get_ogmp_surveys handles records with null measured_rate_kg_hr without TypeError."""
    with app.app_context():
        fac = Facility.query.first()
        if not fac:
            fac = Facility(name="Test Field Fac", code="TFF-01", segment="Upstream", activity="Upstream Oil & Gas")
            db.session.add(fac)
            db.session.commit()
        fac_id = fac.id

        survey = OgmpSurvey(
            facility_id=fac_id,
            year=2026,
            survey_date="2026-06-01",
            survey_type="Satellite (Sentinel-5P/MethaneSAT)",
            measured_rate_kg_hr=None,
            estimated_annual_tch4=None
        )
        db.session.add(survey)
        db.session.commit()
        survey_id = survey.id

    try:
        with client.session_transaction() as sess:
            sess["user_id"] = test_users["user"]

        resp = client.get(f"/api/data/ogmp-surveys?facilityId={fac_id}&year=2026")
        assert resp.status_code == 200
        records = resp.get_json()
        match = [r for r in records if r["id"] == survey_id]
        assert len(match) == 1
        assert match[0]["estimatedAnnualTch4"] == 0.0
    finally:
        with app.app_context():
            s = db.session.get(OgmpSurvey, survey_id)
            if s:
                db.session.delete(s)
                db.session.commit()
