import pytest
from tests.audit_helpers import login, make_facility, make_user, uniq


@pytest.fixture
def ctx(app):
    with app.app_context():
        yield


def test_scope2_scope3_invalid_query_params(client, ctx):
    login(client, make_user("admin", "Global"))

    # Test Scope 2 invalid string year
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

    # Test Scope 2 invalid facilityId (camelCase)
    r = client.get("/api/scope2?facilityId=not_a_number")
    assert r.status_code == 400
    assert "facilityId" in r.get_json()["error"]

    # Test Scope 2 invalid facility_id (snake_case)
    r = client.get("/api/scope2?facility_id=not_a_number")
    assert r.status_code == 400

    # Test Scope 2 integer overflow / negative facilityId
    r = client.get("/api/scope2?facilityId=999999999999999999999")
    assert r.status_code == 400

    r = client.get("/api/scope2?facilityId=-1")
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

    # Test Scope 3 invalid facilityId (camelCase)
    r = client.get("/api/scope3?facilityId=not_a_number")
    assert r.status_code == 400

    # Test Scope 3 invalid facility_id (snake_case)
    r = client.get("/api/scope3?facility_id=not_a_number")
    assert r.status_code == 400

    # Test Scope 3 overflow / negative facilityId
    r = client.get("/api/scope3?facility_id=999999999999999999999")
    assert r.status_code == 400

    r = client.get("/api/scope3?facility_id=-1")
    assert r.status_code == 400

    # Valid values pass properly
    r = client.get("/api/scope2?year=2024")
    assert r.status_code == 200

    r = client.get("/api/scope2?year=all")
    assert r.status_code == 200

    r = client.get("/api/scope3?year=2024")
    assert r.status_code == 200

    r = client.get("/api/scope3?year=all")
    assert r.status_code == 200

    fac = make_facility(region=uniq("TestFac"))
    r = client.get(f"/api/scope2?facilityId={fac.id}")
    assert r.status_code == 200

    r = client.get(f"/api/scope3?facility_id={fac.id}")
    assert r.status_code == 200
