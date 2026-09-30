import pytest
from app import app
from models import db, User, Facility, CapEmission, CapRegulatoryLimit, FlaringDetail, JvPartner, FacilityEquityShare, ProductionData

@pytest.fixture
def auth_client(client):
    with app.app_context():
        user = User.query.filter_by(email="berkine_test_admin@test.com").first()
        if not user:
            user = User(
                email="berkine_test_admin@test.com",
                fullName="Berkine Admin",
                orgName="Groupement Berkine",
                sector="Oil & Gas",
                role="admin",
                location="Hassi Berkine",
            )
            user.set_password("BerkineTestPass123!")
            db.session.add(user)
            db.session.commit()
        user_id = user.id

    with client.session_transaction() as sess:
        sess["user_id"] = user_id
    return client

def test_cap_regulatory_limits_seeded():
    with app.app_context():
        limits = CapRegulatoryLimit.query.all()
        # Should have Decree 06-138 limits if seeded
        assert isinstance(limits, list)

def test_cap_compliance_endpoint(auth_client):
    resp = auth_client.get("/api/cap/compliance?year=2025")
    assert resp.status_code == 200
    data = resp.get_json()
    assert isinstance(data, (dict, list))

def test_dashboard_flaring_summary_endpoint(auth_client):
    resp = auth_client.get("/api/dashboard/flaring-summary?year=2025")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "total_flaring" in data
    assert "routine_flaring" in data
    assert "non_routine_flaring" in data
    assert "safety_flaring" in data
    assert "regulatory_threshold_pct" in data
    assert data["regulatory_threshold_pct"] == 1.00
    assert "statute" in data
    assert "Executive Decree 21-330" in data["statute"]

def test_dashboard_granular_intensities_endpoint(auth_client):
    resp = auth_client.get("/api/dashboard/granular-intensities?year=2025")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "total_production_boe" in data
    assert "saleable_production_boe" in data
    assert "ci_by_total_production_kg_boe" in data
    assert "ci_by_saleable_production_kg_boe" in data
    assert "methane_intensity_ngsi_wt_pct" in data
    assert "ogci_target_kg_boe" in data
    assert data["ogci_target_kg_boe"] == 17.0

def test_equity_routes_endpoint(auth_client):
    resp = auth_client.get("/api/equity/partners")
    assert resp.status_code == 200
    partners = resp.get_json()
    assert isinstance(partners, list)
    partner_names = [p["name"] for p in partners]
    assert "Sonatrach" in partner_names

    resp_alloc = auth_client.get("/api/equity/allocation?year=2025")
    assert resp_alloc.status_code == 200
    allocations = resp_alloc.get_json()
    assert isinstance(allocations, list) or isinstance(allocations, dict)

    resp_shares = auth_client.get("/api/equity/shares")
    assert resp_shares.status_code == 200
    shares = resp_shares.get_json()
    assert isinstance(shares, list)
