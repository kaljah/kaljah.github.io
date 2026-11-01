import pytest
from tests.audit_helpers import make_user, make_facility, login, uniq
from models import FugitiveSurvey


def test_ldar_non_leaking_defaults_to_zero_hours(client, app):
    """Item 1.7: Non-leaking LDAR survey records must default leaking_hours to 0.0, not 8760."""
    with app.app_context():
        user = make_user("admin")
        fac = make_facility(name=uniq("FAC_LDAR"))
        login(client, user)

        # 1. Non-leaking record without explicit leaking_hours
        resp = client.post("/api/ldar/surveys", json={
            "facility_id": fac.id,
            "survey_method": "Method 21",
            "survey_date": "2026-10-15",
            "leak_status": "Non-leaking",
            "screening_value_ppm": 45.0,
        })
        assert resp.status_code == 201
        data = resp.get_json()["survey"]
        assert data["leak_status"] == "Non-leaking"
        assert data["leaking_hours"] == 0.0

        # 2. Leaking record without explicit leaking_hours defaults to 8760
        resp_leak = client.post("/api/ldar/surveys", json={
            "facility_id": fac.id,
            "survey_method": "Method 21",
            "survey_date": "2026-10-15",
            "leak_status": "Leaking",
            "screening_value_ppm": 12500.0,
        })
        assert resp_leak.status_code == 201
        data_leak = resp_leak.get_json()["survey"]
        assert data_leak["leak_status"] == "Leaking"
        assert data_leak["leaking_hours"] == 8760.0
