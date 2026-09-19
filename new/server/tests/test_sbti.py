import pytest
from app import app
from models import db, User, SbtiTarget, Emission, Scope2Emission, Scope3Emission


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
        user = User.query.filter_by(email="a@a").first()
        if not user:
            user = User(email="a@a", fullName="Admin User", orgName="AdminOrg", sector="Energy", role="admin")
            user.set_password("a")
            db.session.add(user)
            db.session.commit()
        return user


@pytest.fixture
def it_admin_user():
    with app.app_context():
        user = User.query.filter_by(email="it@test.com").first()
        if not user:
            user = User(email="it@test.com", fullName="IT Admin", orgName="TestOrg", sector="Oil & Gas", role="it_admin")
            user.set_password("password")
            db.session.add(user)
            db.session.commit()
        return user


def test_manage_sbti_security(client, it_admin_user):
    # Unauthenticated
    res = client.get("/api/manage/sbti")
    assert res.status_code == 401

    # IT Admin blocked
    client.post("/api/auth/login", json={"email": "it@test.com", "password": "password"})
    res_it = client.get("/api/manage/sbti")
    assert res_it.status_code == 403


def test_manage_sbti_validation_and_creation(client, admin_user):
    client.post("/api/auth/login", json={"email": "a@a", "password": "a"})

    # 1. Invalid base_year
    res = client.post("/api/manage/sbti", json={
        "base_year": 2000,
        "target_year": 2050,
        "base_year_emissions": 1000,
        "reduction_rate_pct": 4.2
    })
    assert res.status_code == 400

    # 2. Target year <= base year
    res = client.post("/api/manage/sbti", json={
        "base_year": 2024,
        "target_year": 2024,
        "base_year_emissions": 1000,
        "reduction_rate_pct": 4.2
    })
    assert res.status_code == 400

    # 3. Base year emissions <= 0
    res = client.post("/api/manage/sbti", json={
        "base_year": 2024,
        "target_year": 2050,
        "base_year_emissions": 0,
        "reduction_rate_pct": 4.2
    })
    assert res.status_code == 400

    # 4. Valid target creation
    res = client.post("/api/manage/sbti", json={
        "base_year": 2024,
        "target_year": 2050,
        "base_year_emissions": 5000.0,
        "reduction_rate_pct": 4.2,
        "pathway_type": "1.5C"
    })
    assert res.status_code == 201
    assert "saved successfully" in res.json["message"]


def test_sbti_trajectory_math_and_aliases(client, admin_user):
    client.post("/api/auth/login", json={"email": "a@a", "password": "a"})

    res = client.get("/api/dashboard/sbti-trajectory")
    assert res.status_code == 200
    data = res.json

    assert data["has_target"] is True
    # Aliases
    assert "current_actual" in data
    assert "current_target" in data
    assert "current_actual_emissions" in data
    assert "current_target_emissions" in data
    assert data["current_actual"] == data["current_actual_emissions"]
    assert data["current_target"] == data["current_target_emissions"]

    # SBTi 10% residual floor verification
    residual_floor = data["residual_floor"]
    assert residual_floor == round(5000.0 * 0.10, 2)
    assert data["target_emissions_final"] >= residual_floor

    # Check trajectory points
    trajectory = data["trajectory"]
    assert len(trajectory) > 0
    p_2050 = [p for p in trajectory if p["year"] == "2050"][0]
    # In 2050, 1.5C target must be bounded by residual floor
    assert p_2050["sbti_15c"] == residual_floor
    assert p_2050["sbti_target"] == residual_floor
    # Never negative
    for p in trajectory:
        assert p["sbti_target"] >= residual_floor
        assert p["sbti_15c"] >= residual_floor
        assert p["sbti_wb2c"] >= residual_floor
