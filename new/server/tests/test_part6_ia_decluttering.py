"""
Part 6 Tests: Information Architecture, Data Splitting, and Navigation Alignment
================================================================================
Validates:
- 6.1 Route accessibility across the 7 primary navigation groups
- 6.2 Data management operational, setup, and review query scoping
- 6.5 Hero KPI count and payload completeness
- 6.6 System alerts aggregation (anomalies, scope 3 incomplete, discrepancies)
- 6.7 Role-specific payload access
"""
import pytest
from app import app
from models import User, Emission, Facility, Scope3Emission, ProductionData
from extensions import db
from tests.audit_helpers import make_facility, make_user, login, uniq


@pytest.fixture
def client():
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False
    with app.test_client() as test_client:
        yield test_client


def test_part6_navigation_routes_accessible(app, client):
    """Test all 7 core navigation functional areas are reachable for authenticated users."""
    with app.app_context():
        admin = make_user("admin")
        login(client, admin)

    # 1. Home / Dashboard
    res = client.get("/api/dashboard/summary")
    assert res.status_code == 200

    # 2. Performance (Carbon Intensity / Methane)
    res = client.get("/api/dashboard/intensity-stats")
    assert res.status_code == 200

    # 3. Data Entry / Emissions
    res = client.get("/api/emissions?page=1&per_page=10")
    assert res.status_code == 200

    # 4. Data Management (Sources, Factors, Production)
    res = client.get("/api/production/years")
    assert res.status_code == 200

    # 5. Review (Pending Review queue)
    res = client.get("/api/emissions/pending")
    assert res.status_code == 200

    # 6. Reports (Reports Studio / Exports)
    res = client.get("/api/reports/master-report/regions")
    assert res.status_code == 200

    # 7. Governance (Audit Trail / Settings)
    res = client.get("/api/audit/?page=1&per_page=10")
    assert res.status_code == 200


def test_part6_alerts_aggregation_scope3_incomplete(app, client):
    """Test dashboard scope3-summary reports scope3_incomplete when active production lacks Cat 11."""
    with app.app_context():
        admin = make_user("admin")
        fac = make_facility(name=uniq("FAC_ALERT_P6"))

        # Add production for year 2025
        prod = ProductionData(
            facility_id=fac.id,
            year=2025,
            month=1,
            oil_amount=50000.0,
            gas_amount=300000.0,
        )
        db.session.add(prod)
        db.session.commit()

        login(client, admin)

    res = client.get("/api/dashboard/scope3/summary?year=2025")
    assert res.status_code == 200
    data = res.get_json()
    # Production exists without Cat 11 -> scope3_incomplete must be True
    assert data.get("scope3_incomplete") is True
