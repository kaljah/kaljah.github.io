import pytest
from app import app
from models import db, User, Facility, Emission, Scope2Emission, Scope3Emission


@pytest.fixture
def client():
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False
    with app.test_client() as c:
        with app.app_context():
            yield c


@pytest.fixture
def admin_user():
    with app.app_context():
        user = User.query.filter_by(email="admin_calc@test.com").first()
        if not user:
            user = User(
                email="admin_calc@test.com",
                fullName="Admin Calc",
                orgName="TestOrg",
                sector="Energy",
                role="admin",
                location="Algiers",
            )
            user.set_password("password")
            db.session.add(user)
            db.session.commit()
        return user


@pytest.fixture
def regular_user():
    with app.app_context():
        user = User.query.filter_by(email="maker_calc@test.com").first()
        if not user:
            user = User(
                email="maker_calc@test.com",
                fullName="Maker User",
                orgName="TestOrg",
                sector="Energy",
                role="user",
                location="Algiers",
            )
            user.set_password("password")
            db.session.add(user)
            db.session.commit()
        else:
            user.location = "Algiers"
            db.session.commit()
        return user


@pytest.fixture
def it_admin_user():
    with app.app_context():
        user = User.query.filter_by(email="it_calc@test.com").first()
        if not user:
            user = User(
                email="it_calc@test.com",
                fullName="IT Admin Calc",
                orgName="TestOrg",
                sector="Energy",
                role="it_admin",
            )
            user.set_password("password")
            db.session.add(user)
            db.session.commit()
        return user


@pytest.fixture
def test_facility_id():
    with app.app_context():
        fac = Facility.query.filter_by(name="Test Calc Facility").first()
        if not fac:
            fac = Facility(
                name="Test Calc Facility",
                location="Algiers",
                activity="Extraction",
                division="Production",
                region="Algiers",
                field="OF",
                segment="Upstream",
            )
            db.session.add(fac)
            db.session.commit()
        fid = fac.id
        return fid


def test_calculations_rbac_and_it_admin(client, regular_user, it_admin_user):
    # 1. Unauthenticated requests should be 401
    assert client.get("/api/emissions/").status_code == 401
    assert client.get("/api/scope2").status_code == 401
    assert client.get("/api/scope3").status_code == 401

    # 2. IT Admin is blocked with 403
    client.post("/api/auth/login", json={"email": "it_calc@test.com", "password": "password"})
    assert client.get("/api/emissions/").status_code == 403
    assert client.get("/api/scope2").status_code == 403
    assert client.get("/api/scope3").status_code == 403


def test_scope1_calculation_and_maker_checker(client, admin_user, regular_user, test_facility_id):
    # 1. Maker Mode: Regular user saves Scope 1 as Draft
    client.post("/api/auth/login", json={"email": "maker_calc@test.com", "password": "password"})
    draft_payload = {
        "year": 2024,
        "month": 5,
        "facility_id": test_facility_id,
        "process_type": "combustion",
        "fuel": "Natural Gas",
        "amount": 1000,
        "unit": "m3",
        "status": "Draft",
        "calc_inputs": {
            "combustion": {
                "fuel_gas_volume": 1000,
                "fuel_type": "Natural Gas",
            }
        },
    }
    res_draft = client.post("/api/emissions", json=draft_payload)
    assert res_draft.status_code in [200, 201]
    data_draft = res_draft.get_json()
    assert "emissions" in data_draft
    assert data_draft["emissions"]["totalCo2e"] > 0
    assert "uncertainty" in data_draft["emissions"]

    record_id = data_draft["id"]
    with app.app_context():
        rec = db.session.get(Emission, record_id)
        assert rec is not None
        assert rec.status == "Draft"

    # 2. Regular user submits for review (non-draft) -> status should be "Pending Approval"
    submit_payload = {
        "year": 2024,
        "month": 6,
        "facility_id": test_facility_id,
        "process_type": "combustion",
        "fuel": "Natural Gas",
        "amount": 1000,
        "unit": "m3",
        "status": "Verified",  # Regular user requests verification
        "calc_inputs": {
            "combustion": {
                "fuel_gas_volume": 1000,
                "fuel_type": "Natural Gas",
            }
        },
    }
    res_submit = client.post("/api/emissions", json=submit_payload)
    assert res_submit.status_code in [200, 201]
    with app.app_context():
        rec_pending = db.session.get(Emission, res_submit.get_json()["id"])
        assert rec_pending.status in ["Pending", "Pending Approval"]

    # 3. Admin user submits -> status should be "Verified"
    client.post("/api/auth/login", json={"email": "admin_calc@test.com", "password": "password"})
    res_admin = client.post("/api/emissions", json=submit_payload)
    assert res_admin.status_code in [200, 201]
    with app.app_context():
        rec_admin = db.session.get(Emission, res_admin.get_json()["id"])
        assert rec_admin.status == "Verified"


def test_scope2_authoritative_calculation_and_draft(client, admin_user, regular_user, test_facility_id):
    # 1. Maker Mode: Regular user saves Scope 2 as Draft with authoritative calculation fallback
    client.post("/api/auth/login", json={"email": "maker_calc@test.com", "password": "password"})
    payload_draft = {
        "year": 2024,
        "month": 7,
        "facility_id": test_facility_id,
        "source_type": "electricity",
        "electricity_kwh": 50000,
        "grid_region": "US Average",
        "status": "Draft",
        # client omitted co2e or sent 0
        "co2e": 0,
    }
    res = client.post("/api/scope2", json=payload_draft)
    assert res.status_code == 201
    data = res.get_json()
    assert "emissions" in data
    assert data["emissions"]["totalCo2e"] > 0
    assert data["record"]["status"] == "Draft"

    rec_id = data["record"]["id"]
    with app.app_context():
        rec = db.session.get(Scope2Emission, rec_id)
        assert rec is not None
        assert rec.status == "Draft"
        # Verify co2e was calculated from grid factors rather than saved as 0.0
        assert rec.co2e > 0.0

    # 2. Regular user calculates & submits for review -> status "Pending Approval"
    payload_submit = {
        "year": 2024,
        "month": 8,
        "facility_id": test_facility_id,
        "source_type": "electricity",
        "electricity_kwh": 20000,
        "grid_region": "US Average",
        "status": "Verified",
    }
    res_sub = client.post("/api/scope2", json=payload_submit)
    assert res_sub.status_code == 201
    assert res_sub.get_json()["record"]["status"] in ["Pending", "Pending Approval"]


def test_scope3_eeio_and_fallback_calculation(client, admin_user, regular_user, test_facility_id):
    client.post("/api/auth/login", json={"email": "admin_calc@test.com", "password": "password"})

    # 1. Test EEIO quick calculator endpoint
    eeio_res = client.post("/api/scope3/eeio-calculate", json={
        "naics_code": "2111",
        "spend_usd": 10000,
    })
    assert eeio_res.status_code == 200
    eeio_data = eeio_res.get_json()
    assert "emission_factor" in eeio_data
    assert "co2e" in eeio_data
    assert eeio_data["co2e"] > 0

    # 2. Test Scope 3 submission with draft and fallback calculation
    client.post("/api/auth/login", json={"email": "maker_calc@test.com", "password": "password"})
    s3_payload = {
        "year": 2024,
        "month": 9,
        "facility_id": test_facility_id,
        "category": "1",
        "sub_category": "Purchased Goods",
        "activity_data": 10000,
        "unit": "USD",
        "emission_factor": 0.35,  # kg CO2e / $1
        "status": "Draft",
        # co2e omitted to test backend authoritative calculation fallback
    }
    res_s3 = client.post("/api/scope3", json=s3_payload)
    assert res_s3.status_code == 201
    s3_data = res_s3.get_json()
    assert "emissions" in s3_data
    # 10,000 USD * 0.35 kg/USD / 1000 = 3.50 tCO2e
    assert pytest.approx(s3_data["emissions"]["totalCo2e"], 0.01) == 3.50
    assert s3_data["record"]["status"] == "Draft"

    with app.app_context():
        s3_rec = db.session.get(Scope3Emission, s3_data["record"]["id"])
        assert s3_rec is not None
        assert s3_rec.status == "Draft"
        assert pytest.approx(s3_rec.co2e, 0.01) == 3.50
