"""RC-3 central input validation regressions (AUDIT_FINDINGS.md)."""
import json

import pytest

from extensions import db
from models import Scope2Emission, Scope3Emission
from tests.audit_helpers import login, make_facility, make_user, uniq


@pytest.fixture
def ctx(app):
    with app.app_context():
        yield


@pytest.fixture
def admin_client(client, ctx):
    login(client, make_user("admin", "Global"))
    return client


# ── BUG-083: non-finite numbers ("NaN", "1e999") must be rejected on every write path ──

@pytest.mark.parametrize("bad", ["NaN", "nan", "1e999", "-1e999", "Infinity"])
def test_bug083_non_finite_rejected_on_all_write_endpoints(admin_client, bad):
    fac = make_facility(region="West")
    calls = {
        "scope2": ("/api/scope2", {"facility_id": fac.id, "year": 2025, "month": 1, "electricity_kwh": bad,
                                   "grid_region": "Algerian National Grid"}),
        "scope3": ("/api/scope3", {"facility_id": fac.id, "year": 2025, "month": 1, "category": 1,
                                   "activity_data": bad, "unit": "USD", "emission_factor": 0.5}),
        "production": ("/api/data/production", {"facility_id": fac.id, "year": 2025, "month": 11,
                                                "oil_amount": bad, "gas_amount": 5}),
        "custom_factor": ("/api/custom-factors", {"name": uniq("CF"), "co2_factor": bad, "unit": "kg/scf"}),
        "mitigation": ("/api/mitigation", {"facility_id": fac.id, "name": uniq("M"), "year": 2025,
                                           "quantity_tco2e": bad}),
        "scope1": ("/api/emissions/", {"process_type": "combustion", "facility_id": fac.id, "year": 2024,
                                       "month": 1, "fuel": "Natural Gas", "amount": bad, "unit": "MMBtu"}),
    }
    for name, (url, body) in calls.items():
        r = admin_client.post(url, json=body)
        assert r.status_code == 400, (name, r.status_code, r.get_data(as_text=True)[:200])


def test_bug083_raw_json_nan_literal_rejected(admin_client):
    fac = make_facility(region="West")
    body = '{"facility_id": %d, "year": 2025, "month": 1, "electricity_kwh": NaN, "grid_region": "Algerian National Grid"}' % fac.id
    r = admin_client.post("/api/scope2", data=body, content_type="application/json")
    assert r.status_code == 400


def test_bug083_reads_stay_valid_json_with_legacy_non_finite_rows(admin_client):
    fac = make_facility(region="West")
    db.session.add(Scope3Emission(facility_id=fac.id, year=2025, month=1, category="Category 1",
                                  activity_data=float("inf"), co2e=float("inf"), status="Verified"))
    db.session.commit()
    for url in ("/api/scope3", f"/api/dashboard/scope3/summary?year=2025&facilityId={fac.id}"):
        r = admin_client.get(url)
        text = r.get_data(as_text=True)
        assert r.status_code == 200, (url, r.status_code)
        assert "Infinity" not in text and "NaN" not in text
        json.loads(text)  # strict JSON
    Scope3Emission.query.filter_by(facility_id=fac.id).delete()
    db.session.commit()
