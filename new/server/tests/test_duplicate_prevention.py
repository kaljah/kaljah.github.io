import pytest
from tests.audit_helpers import make_user, make_facility, login, uniq
from models import CustomFactor, MitigationProject, EmissionSource, Scope3Emission
from extensions import db


def test_mitigation_project_uniqueness(client, app):
    """Item 1.6: Duplicate mitigation project for same facility + name + year returns 409."""
    with app.app_context():
        admin = make_user("admin")
        fac = make_facility(name=uniq("FAC_MIT"))
        login(client, admin)

        payload = {
            "facility_id": fac.id,
            "name": "In Salah Geological Storage Unit 2",
            "type": "carbon_capture",
            "year": 2026,
            "quantity_tco2e": 14250.0,
            "status": "active",
        }
        # First creation succeeds
        resp1 = client.post("/api/mitigation", json=payload)
        assert resp1.status_code == 201

        # Second creation with identical (name, facility, year) must return 409 Conflict
        resp2 = client.post("/api/mitigation", json=payload)
        assert resp2.status_code == 409
        data = resp2.get_json()
        assert "already exists" in data["error"]
        assert data.get("code") == "DUPLICATE_RECORD"


def test_emission_source_uniqueness(client, app):
    """Item 1.6: Duplicate emission source for same facility + name returns 409."""
    with app.app_context():
        admin = make_user("admin")
        fac = make_facility(name=uniq("FAC_SRC"))
        login(client, admin)

        payload = {
            "facility_id": fac.id,
            "name": "Gas Lift Compressor Train 4",
            "type": "combustion",
            "equipment_id": "COMP-GL-404",
        }
        # First creation succeeds
        resp1 = client.post("/api/sources", json=payload)
        assert resp1.status_code == 201

        # Second creation with identical (name, facility) must return 409 Conflict
        resp2 = client.post("/api/sources", json=payload)
        assert resp2.status_code == 409
        data = resp2.get_json()
        assert "already exists" in data["error"]
        assert data.get("code") == "DUPLICATE_RECORD"


def test_scope3_record_uniqueness(client, app):
    """Item 1.6: Duplicate Scope 3 record for same period and subcategory returns 409."""
    with app.app_context():
        admin = make_user("admin")
        fac = make_facility(name=uniq("FAC_S3_DUP"))
        login(client, admin)

        payload = {
            "facility_id": fac.id,
            "year": 2026,
            "month": 10,
            "category": "Category 4",
            "sub_category": "Truck Transport",
            "activity_data": 45000.0,
            "unit": "ton-km",
            "emission_factor": 0.12841,
            "factor_unit": "kg CO2e / ton-km",
            "status": "Verified",
        }
        # First creation succeeds
        resp1 = client.post("/api/scope3", json=payload)
        assert resp1.status_code == 201

        # Second creation must return 409 Conflict
        resp2 = client.post("/api/scope3", json=payload)
        assert resp2.status_code == 409
        data = resp2.get_json()
        assert "already exists" in data["error"]
        assert data.get("code") == "DUPLICATE_RECORD"


def test_custom_factor_uniqueness(client, app):
    """Item 1.6: Duplicate custom factor name returns 409."""
    with app.app_context():
        admin = make_user("admin")
        login(client, admin)

        factor_name = uniq("Skikda_Factor")
        payload = {
            "name": factor_name,
            "unit": "kg/MMBtu",
            "co2_factor": 54.85,
            "ch4_factor": 0.001,
            "n2o_factor": 0.0001,
            "source": "Site measurement / user defined",
        }
        # First creation succeeds
        resp1 = client.post("/api/custom-factors/", json=payload)
        assert resp1.status_code == 201

        # Second creation must return 409 Conflict
        resp2 = client.post("/api/custom-factors/", json=payload)
        assert resp2.status_code == 409
        data = resp2.get_json()
        assert "already exists" in data["error"]
