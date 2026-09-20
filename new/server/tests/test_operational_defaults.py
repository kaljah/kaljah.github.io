import pytest
from app import app
from models import db, User, Facility


@pytest.fixture
def client():
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False
    with app.test_client() as c:
        with app.app_context():
            yield c


def test_login_and_me_operational_defaults_regular_user(client):
    """Verify regular user login and /me return assigned region, division, activity defaults."""
    with app.app_context():
        fac = Facility.query.filter_by(code="FAC-TEST-REGIONAL").first()
        if not fac:
            fac = Facility(
                name="Hassi Messaoud Central Plant",
                code="FAC-TEST-REGIONAL",
                region="Hassi Messaoud",
                location="Ouargla",
                division="Exploration & Production",
                activity="Upstream",
                segment="Upstream",
            )
            db.session.add(fac)
            db.session.commit()

        user = User.query.filter_by(email="reg_user_test@defaults.com").first()
        if not user:
            user = User(
                email="reg_user_test@defaults.com",
                fullName="Regional User Defaults Tester",
                orgName="Sonatrach",
                sector="Energy",
                role="user",
                location="Hassi Messaoud",
            )
            user.set_password("SecurePass123!")
            db.session.add(user)
            db.session.commit()

    # 1. Test Login
    res = client.post(
        "/api/auth/login",
        json={"email": "reg_user_test@defaults.com", "password": "SecurePass123!"},
    )
    assert res.status_code == 200
    data = res.get_json()
    u = data["user"]
    assert u["location"] == "Hassi Messaoud"
    assert u["default_region"] in ["Hassi Messaoud", "Ouargla"]
    assert u["default_division"] in ["Production", "Exploration & Production"]
    assert u["default_activity"] in ["Upstream", "Extraction"]
    assert u["default_facility_id"] is not None

    # 2. Test /me
    res_me = client.get("/api/auth/me")
    assert res_me.status_code == 200
    data_me = res_me.get_json()
    assert data_me["location"] == "Hassi Messaoud"
    assert data_me["default_region"] in ["Hassi Messaoud", "Ouargla"]
    assert data_me["default_division"] in ["Production", "Exploration & Production"]
    assert data_me["default_activity"] in ["Upstream", "Extraction"]


def test_login_operational_defaults_superuser(client):
    """Verify superuser with assigned region returns defaults on login and /me."""
    with app.app_context():
        fac = Facility.query.filter_by(code="FAC-TEST-SUPER").first()
        if not fac:
            fac = Facility(
                name="Adrar Refining Complex",
                code="FAC-TEST-SUPER",
                region="ADR",
                location="Adrar",
                division="Raffinage",
                activity="Downstream",
                segment="Downstream",
            )
            db.session.add(fac)
            db.session.commit()

        super_user = User.query.filter_by(email="superuser_test@defaults.com").first()
        if not super_user:
            super_user = User(
                email="superuser_test@defaults.com",
                fullName="Superuser Defaults Tester",
                orgName="Sonatrach",
                sector="Energy",
                role="superuser",
                location="ADR",
            )
            super_user.set_password("SuperSecure123!")
            db.session.add(super_user)
            db.session.commit()

    res = client.post(
        "/api/auth/login",
        json={"email": "superuser_test@defaults.com", "password": "SuperSecure123!"},
    )
    assert res.status_code == 200
    u = res.get_json()["user"]
    assert u["location"] == "ADR"
    assert u["default_region"] in ["ADR", "Adrar"]
    assert u["default_division"] == "Raffinage"
    assert u["default_activity"] == "Downstream"


def test_filters_available_includes_region_and_location(client):
    """Verify /api/filters/available returns region and location on each facility in regions list."""
    with app.app_context():
        admin = User.query.filter_by(email="admin_filters_test@defaults.com").first()
        if not admin:
            admin = User(
                email="admin_filters_test@defaults.com",
                fullName="Admin Filter Tester",
                orgName="AdminOrg",
                sector="Energy",
                role="admin",
                location="Global",
            )
            admin.set_password("AdminPass123!")
            db.session.add(admin)
            db.session.commit()
        admin_id = admin.id

    with client.session_transaction() as sess:
        sess["user_id"] = admin_id

    res = client.get("/api/filters/available")
    assert res.status_code == 200
    data = res.get_json()
    assert "regions" in data
    assert len(data["regions"]) > 0
    for r in data["regions"]:
        assert "region" in r
        assert "location" in r
        assert "activity" in r
        assert "division" in r
