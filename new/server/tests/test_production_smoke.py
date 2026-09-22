"""
Phase 7.1 — Production Smoke Tests.
High-speed (<10 seconds), robust smoke test suite for post-deployment verification.
Verifies health, readiness, auth security, calculation dispatch, GWP constants,
and ensures zero hard-coded dev accounts exist.
"""
import pytest
from app import app as flask_app
from extensions import db, limiter


@pytest.fixture(scope="module")
def smoke_client():
    flask_app.config.update({
        "TESTING": True,
        "WTF_CSRF_ENABLED": False,
        "SECRET_KEY": "smoke-test-key-random",
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "SEED_ADMIN": "false",
    })
    limiter.enabled = False
    with flask_app.app_context():
        db.create_all()
        from models import User
        u = User(
            fullName="Smoke Admin",
            orgName="GHG Operations",
            email="smoke_admin@test.com",
            sector="Energy",
            role="admin",
            status="active"
        )
        u.set_password("SmokeAdmin123!")
        db.session.add(u)
        db.session.commit()
        yield flask_app.test_client()
        db.session.remove()


def test_smoke_01_application_starts(smoke_client):
    """SMOKE-01: Health check endpoint responds with 200 and status ok."""
    resp = smoke_client.get("/api/health")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data.get("status") == "ok"


def test_smoke_02_readiness_probe(smoke_client):
    """SMOKE-02: Deep readiness probe confirms database connectivity and WAL monitoring."""
    resp = smoke_client.get("/api/health/ready")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data.get("database") == "connected"
    assert "wal_size_mb" in data


def test_smoke_03_root_endpoint(smoke_client):
    """SMOKE-03: Root API gateway index responds."""
    resp = smoke_client.get("/")
    assert resp.status_code == 200


def test_smoke_04_authenticated_login(smoke_client):
    """SMOKE-04: Admin login succeeds and returns user info with role."""
    resp = smoke_client.post("/api/auth/login", json={
        "email": "smoke_admin@test.com",
        "password": "SmokeAdmin123!",
    })
    assert resp.status_code == 200
    data = resp.get_json()
    assert data.get("user", {}).get("role") == "admin"


def test_smoke_05_unauthenticated_access_blocked():
    """SMOKE-05: Protected emission endpoints reject unauthenticated access with 401."""
    fresh_client = flask_app.test_client()
    resp = fresh_client.get("/api/emissions/")
    assert resp.status_code == 401



def test_smoke_06_calculation_engine_dispatches(smoke_client):
    """SMOKE-06: Calculation engine dispatches a basic stationary combustion query."""
    from calculations.dispatcher import CalculationDispatcher
    from calculations.constants import GWP_AR5
    dispatcher = CalculationDispatcher()
    result = dispatcher.dispatch(
        "stationary_combustion",
        {"quantity": 1000, "unit": "m3", "fuel_type": "natural_gas", "hhv": 1020.0},
        {"co2": 53.06, "ch4": 0.001, "n2o": 0.0001, "unit": "kg/MMBtu"},
        {},
        gwp_dict=GWP_AR5,
    )
    assert result["total_co2e"] > 0
    assert not any(str(v) == "nan" for v in [result["total_co2e"]])


def test_smoke_07_gwp_constants_accuracy(smoke_client):
    """SMOKE-07: GWP constants match IPCC AR5 and AR6 values exactly."""
    from calculations.constants import GWP_AR5, GWP_AR6
    assert GWP_AR5["CH4"] == 28.0
    assert GWP_AR5["N2O"] == 265.0
    assert GWP_AR6["CH4"] == 27.9
    assert GWP_AR6["N2O"] == 273.0


def test_smoke_08_unit_conversion_sanity(smoke_client):
    """SMOKE-08: Standard scf to m3 conversion factor is accurate."""
    from calculations.units import VOLUME_UNITS_TO_M3
    assert abs(VOLUME_UNITS_TO_M3["scf"] - 0.028316846592) < 1e-10


def test_smoke_09_api_json_error_handling(smoke_client):
    """SMOKE-09: Unhandled 404 routes return JSON, not HTML error pages."""
    resp = smoke_client.get("/api/nonexistent-route-smoke")
    assert resp.status_code == 404
    assert "application/json" in resp.headers.get("Content-Type", "")


def test_smoke_10_no_dev_accounts_exist(smoke_client):
    """SMOKE-10: Insecure hard-coded dev accounts (a@a, a) do not exist."""
    from models import User
    for email in ["a@a", "a"]:
        user = User.query.filter_by(email=email).first()
        assert user is None, f"Security violation: {email} exists"
