"""Regression tests for Part 1.6: Duplicates prevention and natural-key uniqueness.

Requirements:
- Stop appending timestamps: reject timestamp-suffixed names at API level (400 INVALID_NAME).
- Natural-key uniqueness at API and DB level (unique constraint + 409 DUPLICATE_RECORD):
  - Custom emission factors: unique name
  - Mitigation projects: unique (facility_id, name, year)
  - Emission sources: unique (facility_id, name) and unique (facility_id, equipment_id)
  - Scope 3 emissions: unique (facility_id, year, month, category, sub_category)
- Submit disabled while pending in UI.
- Cleanup script produces dry-run report without auto-delete.
"""
import pytest
from tests.audit_helpers import make_facility, make_user, login, uniq


def test_custom_factor_rejects_timestamp_suffix(client, app):
    with app.app_context():
        user = make_user(role="admin")
        login(client, user)

        res = client.post("/api/custom-factors", json={
            "name": f"Skikda Light Refinery Gas 2026-1791316242057",
            "unit": "kg/MMBtu",
            "co2_factor": 54.85,
            "ch4_factor": 0.0018,
            "n2o_factor": 0.0001,
            "source": "GC Analysis",
        })
        assert res.status_code == 400
        assert "timestamp" in res.get_json()["error"].lower()


def test_custom_factor_rejects_duplicate_name(client, app):
    with app.app_context():
        user = make_user(role="admin")
        login(client, user)
        factor_name = uniq("Skikda Refinery Gas")

        # Create first
        res1 = client.post("/api/custom-factors", json={
            "name": factor_name,
            "unit": "kg/MMBtu",
            "co2_factor": 54.85,
            "source": "Site Measurement",
        })
        assert res1.status_code == 201

        # Attempt duplicate
        res2 = client.post("/api/custom-factors", json={
            "name": factor_name,
            "unit": "kg/MMBtu",
            "co2_factor": 54.85,
            "source": "Site Measurement",
        })
        assert res2.status_code == 409
        assert "already exists" in res2.get_json()["error"].lower()


def test_emission_source_rejects_timestamp_suffix(client, app):
    with app.app_context():
        user = make_user(role="admin")
        fac = make_facility()
        login(client, user)

        res = client.post("/api/sources", json={
            "facility_id": fac.id,
            "name": "Gas Lift Compressor Train 4-1791314717740",
            "equipment_id": uniq("EQ-404"),
            "type": "combustion",
        })
        assert res.status_code == 400
        assert "timestamp" in res.get_json()["error"].lower()


def test_emission_source_rejects_duplicate_equipment_id(client, app):
    with app.app_context():
        user = make_user(role="admin")
        fac = make_facility()
        login(client, user)
        eq_id = uniq("COMP-GL-404")

        # First source
        res1 = client.post("/api/sources", json={
            "facility_id": fac.id,
            "name": uniq("Compressor Train A"),
            "equipment_id": eq_id,
            "type": "combustion",
        })
        assert res1.status_code == 201

        # Second source with same equipment_id at same facility
        res2 = client.post("/api/sources", json={
            "facility_id": fac.id,
            "name": uniq("Compressor Train B"),
            "equipment_id": eq_id,
            "type": "combustion",
        })
        assert res2.status_code == 409
        assert "equipment id" in res2.get_json()["error"].lower()


def test_mitigation_project_rejects_timestamp_suffix(client, app):
    with app.app_context():
        user = make_user(role="admin")
        fac = make_facility()
        login(client, user)

        res = client.post("/api/mitigation", json={
            "facility_id": fac.id,
            "name": "In Salah Geological Storage Unit 2-1791314724941",
            "type": "CCUS",
            "year": 2026,
            "quantity_tco2e": 14250.0,
        })
        assert res.status_code == 400
        assert "timestamp" in res.get_json()["error"].lower()


def test_mitigation_project_rejects_duplicate(client, app):
    with app.app_context():
        user = make_user(role="admin")
        fac = make_facility()
        login(client, user)
        proj_name = uniq("In Salah CCUS")

        # First
        res1 = client.post("/api/mitigation", json={
            "facility_id": fac.id,
            "name": proj_name,
            "type": "CCUS",
            "year": 2026,
            "quantity_tco2e": 14250.0,
        })
        assert res1.status_code == 201

        # Duplicate
        res2 = client.post("/api/mitigation", json={
            "facility_id": fac.id,
            "name": proj_name,
            "type": "CCUS",
            "year": 2026,
            "quantity_tco2e": 14250.0,
        })
        assert res2.status_code == 409
        assert "already exists" in res2.get_json()["error"].lower()


def test_scope3_rejects_duplicate_natural_key(client, app):
    with app.app_context():
        user = make_user(role="admin")
        fac = make_facility()
        login(client, user)

        # First Scope 3 row
        res1 = client.post("/api/scope3", json={
            "facility_id": fac.id,
            "year": 2026,
            "month": 4,
            "category": "Category 11",
            "sub_category": "Natural Gas",
            "activity_data": 5000.0,
            "unit": "mcf",
            "emission_factor": 54.18,
            "factor_unit": "kg CO2e / MMBtu",
        })
        assert res1.status_code == 201

        # Duplicate Scope 3 row
        res2 = client.post("/api/scope3", json={
            "facility_id": fac.id,
            "year": 2026,
            "month": 4,
            "category": "Category 11",
            "sub_category": "Natural Gas",
            "activity_data": 5000.0,
            "unit": "mcf",
            "emission_factor": 54.18,
            "factor_unit": "kg CO2e / MMBtu",
        })
        assert res2.status_code == 409
        assert "already exists" in res2.get_json()["error"].lower()
