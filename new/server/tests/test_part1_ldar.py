"""Regression tests for Part 1.7: LDAR counts and duration.

Requirements:
- "Surveys & Repairs" badge and chip counts (Leaking, Repaired, Non-leaking) must be consistent with queried table records.
- Render empty state only when the filtered list is empty.
- A "Non-leaking" record must have leaking_hours = 0.0 (never 8760).
- Updates/bulk-updates to "Non-leaking" must enforce leaking_hours = 0.0.
"""
import pytest
from tests.audit_helpers import make_facility, make_user, login, uniq
from models import FugitiveSurvey


def test_ldar_non_leaking_enforces_zero_hours_on_create(client, app):
    with app.app_context():
        user = make_user("admin")
        fac = make_facility(name=uniq("FAC_LDAR"))
        login(client, user)

        # 1. Non-leaking with no leaking_hours provided
        resp1 = client.post("/api/ldar/surveys", json={
            "facility_id": fac.id,
            "survey_method": "Method 21",
            "survey_date": "2026-10-15",
            "leak_status": "Non-leaking",
            "screening_value_ppm": 0.0,
        })
        assert resp1.status_code == 201
        assert resp1.get_json()["survey"]["leak_status"] == "Non-leaking"
        assert resp1.get_json()["survey"]["leaking_hours"] == 0.0

        # 2. Non-leaking with explicit 8760 leaking_hours -> must be forced to 0.0
        resp2 = client.post("/api/ldar/surveys", json={
            "facility_id": fac.id,
            "survey_method": "Method 21",
            "survey_date": "2026-10-15",
            "leak_status": "Non-leaking",
            "leaking_hours": 8760.0,
            "screening_value_ppm": 0.0,
        })
        assert resp2.status_code == 201
        assert resp2.get_json()["survey"]["leak_status"] == "Non-leaking"
        assert resp2.get_json()["survey"]["leaking_hours"] == 0.0


def test_ldar_updating_to_non_leaking_resets_hours(client, app):
    with app.app_context():
        user = make_user("admin")
        fac = make_facility(name=uniq("FAC_LDAR"))
        login(client, user)

        # Create a leaking record
        resp = client.post("/api/ldar/surveys", json={
            "facility_id": fac.id,
            "survey_method": "Method 21",
            "survey_date": "2026-10-15",
            "leak_status": "Leaking",
            "leaking_hours": 500.0,
            "screening_value_ppm": 15000.0,
        })
        assert resp.status_code == 201
        survey_id = resp.get_json()["survey"]["id"]
        assert resp.get_json()["survey"]["leaking_hours"] == 500.0

        # Update to Non-leaking
        resp_up = client.put(f"/api/ldar/surveys/{survey_id}", json={
            "leak_status": "Non-leaking",
        })
        assert resp_up.status_code == 200
        assert resp_up.get_json()["survey"]["leak_status"] == "Non-leaking"
        assert resp_up.get_json()["survey"]["leaking_hours"] == 0.0


def test_ldar_bulk_update_to_non_leaking_resets_hours(client, app):
    with app.app_context():
        user = make_user("admin")
        fac = make_facility(name=uniq("FAC_LDAR"))
        login(client, user)

        # Create 2 leaking records
        resp1 = client.post("/api/ldar/surveys", json={
            "facility_id": fac.id,
            "survey_method": "Method 21",
            "survey_date": "2026-10-15",
            "leak_status": "Leaking",
            "leaking_hours": 200.0,
            "screening_value_ppm": 10000.0,
        })
        resp2 = client.post("/api/ldar/surveys", json={
            "facility_id": fac.id,
            "survey_method": "Method 21",
            "survey_date": "2026-10-15",
            "leak_status": "Leaking",
            "leaking_hours": 300.0,
            "screening_value_ppm": 12000.0,
        })
        id1 = resp1.get_json()["survey"]["id"]
        id2 = resp2.get_json()["survey"]["id"]

        # Bulk update to Non-leaking
        bulk_resp = client.post("/api/ldar/surveys/bulk-update", json={
            "ids": [id1, id2],
            "leak_status": "Non-leaking",
        })
        assert bulk_resp.status_code == 200

        # Verify via GET
        get1 = client.get(f"/api/ldar/surveys/{id1}").get_json()["survey"]
        get2 = client.get(f"/api/ldar/surveys/{id2}").get_json()["survey"]
        assert get1["leak_status"] == "Non-leaking"
        assert get1["leaking_hours"] == 0.0
        assert get2["leak_status"] == "Non-leaking"
        assert get2["leaking_hours"] == 0.0
