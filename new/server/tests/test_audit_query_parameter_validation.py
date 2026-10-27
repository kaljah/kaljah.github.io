import pytest
from tests.audit_helpers import login, make_facility, make_user, uniq
from models import BaseYear


@pytest.fixture
def ctx(app):
    with app.app_context():
        yield


def test_scope2_scope3_query_params(client, ctx):
    login(client, make_user("admin", "Global"))

    # Test Scope 2 invalid string year (not 'all' and not 'baseline')
    r = client.get("/api/scope2?year=invalid_string")
    assert r.status_code == 400
    assert "year" in r.get_json()["error"].lower()

    # Test Scope 2 integer overflow / out of bounds year
    r = client.get("/api/scope2?year=999999999999999999999")
    assert r.status_code == 400

    r = client.get("/api/scope2?year=1850")
    assert r.status_code == 400

    r = client.get("/api/scope2?year=-1")
    assert r.status_code == 400

    # Test Scope 3 invalid string year
    r = client.get("/api/scope3?year=invalid_string")
    assert r.status_code == 400
    assert "year" in r.get_json()["error"].lower()

    # Test Scope 3 out of bounds / overflow year
    r = client.get("/api/scope3?year=999999999999999999999")
    assert r.status_code == 400

    r = client.get("/api/scope3?year=-5")
    assert r.status_code == 400

    # Valid year values pass properly
    r = client.get("/api/scope2?year=2024")
    assert r.status_code == 200

    r = client.get("/api/scope2?year=all")
    assert r.status_code == 200

    r = client.get("/api/scope3?year=2024")
    assert r.status_code == 200

    r = client.get("/api/scope3?year=all")
    assert r.status_code == 200

    # Baseline year query succeeds (parity with Scope 1 / dashboard)
    r = client.get("/api/scope2?year=baseline")
    assert r.status_code == 200

    r = client.get("/api/scope3?year=baseline")
    assert r.status_code == 200

    # Facility parameters: handles camelCase, snake_case, comma lists, 'all', 'null', 'none'
    fac1 = make_facility(region=uniq("TestFac1"))
    fac2 = make_facility(region=uniq("TestFac2"))

    r = client.get(f"/api/scope2?facilityId={fac1.id}")
    assert r.status_code == 200

    r = client.get(f"/api/scope2?facility_id={fac1.id},{fac2.id}")
    assert r.status_code == 200

    r = client.get("/api/scope2?facilityId=null")
    assert r.status_code == 200

    r = client.get("/api/scope2?facility_id=none")
    assert r.status_code == 200

    r = client.get(f"/api/scope3?facility_id={fac1.id}")
    assert r.status_code == 200

    r = client.get(f"/api/scope3?facilityId={fac1.id},{fac2.id}")
    assert r.status_code == 200

    r = client.get("/api/scope3?facilityId=all")
    assert r.status_code == 200

    r = client.get("/api/scope3?facility_id=none")
    assert r.status_code == 200

    # Status filtering parity
    r = client.get("/api/scope2?status=Verified")
    assert r.status_code == 200

    r = client.get("/api/scope3?status=Verified")
    assert r.status_code == 200
