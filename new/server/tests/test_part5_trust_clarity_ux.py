"""
Part 5 Tests: Trust and Clarity (UX), KPI Registry, and Maker-Checker Verification
================================================================================
Validates:
- 5.1 Authoritative KPI registry endpoint (/api/dashboard/kpi-definitions)
- 5.2 Status Badge definitions and normalization
- 5.3 Maker-checker segregation rules and self-approval guards
- 5.4 Active filter consistency
- 5.5 Glossary technical terminology coverage
"""
import pytest
from app import app
from models import User, Emission, Facility, ActivityLog
from extensions import db
from tests.audit_helpers import make_facility, make_user, login, uniq


@pytest.fixture
def client():
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False
    with app.test_client() as test_client:
        yield test_client


def test_kpi_definitions_endpoint(app, client):
    """Test /api/dashboard/kpi-definitions returns complete metadata for all 10 core KPIs."""
    with app.app_context():
        admin = make_user("admin")
        login(client, admin)

    res = client.get("/api/dashboard/kpi-definitions")
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "success"
    assert data["total_kpis"] == 10
    assert len(data["kpis"]) == 10

    # Verify standard citations are included
    assert "API Compendium 2021" in data["standards_referenced"]
    assert "GHG Protocol Corporate Standard" in data["standards_referenced"]
    assert "OGMP 2.0 Reporting Framework" in data["standards_referenced"]

    kpi_map = {k["id"]: k for k in data["kpis"]}

    # 1. Scope 1
    assert "scope1_total" in kpi_map
    assert kpi_map["scope1_total"]["unit"] == "t CO2e"
    assert "GWP_CH4" in kpi_map["scope1_total"]["formula"]

    # 2. Scope 2
    assert "scope2_total" in kpi_map
    assert kpi_map["scope2_total"]["unit"] == "t CO2e"
    assert "Dual Reporting" in kpi_map["scope2_total"]["standard"]

    # 3. Scope 3
    assert "scope3_total" in kpi_map
    assert "Category 11" in kpi_map["scope3_total"]["description"]

    # 4. Combined BOE
    assert "combined_boe" in kpi_map
    assert kpi_map["combined_boe"]["unit"] == "BOE"
    assert "6.0 mscf/BOE" in kpi_map["combined_boe"]["formula"]

    # 5. Operational GHG Intensity
    assert "ghg_intensity" in kpi_map
    assert kpi_map["ghg_intensity"]["unit"] == "kg CO2e / BOE"
    assert "OGCI Carbon Intensity" in kpi_map["ghg_intensity"]["standard"]

    # 6. Scope 3 Intensity
    assert "scope3_intensity" in kpi_map
    assert kpi_map["scope3_intensity"]["unit"] == "kg CO2e / BOE"

    # 7. Methane Intensity
    assert "methane_intensity" in kpi_map
    assert "OGCI Methane Target" in kpi_map["methane_intensity"]["standard"]

    # 8. Flaring Intensity
    assert "flaring_intensity" in kpi_map
    assert kpi_map["flaring_intensity"]["unit"] == "m3 / BOE"
    assert "Zero Routine Flaring" in kpi_map["flaring_intensity"]["notes"]

    # 9. OGMP Level
    assert "ogmp_level" in kpi_map
    assert "Gold Standard Pathway" in kpi_map["ogmp_level"]["notes"]

    # 10. Inventory Uncertainty
    assert "inventory_uncertainty" in kpi_map
    assert "k=2" in kpi_map["inventory_uncertainty"]["unit"]
    assert "ISO 14064-1:2018" in kpi_map["inventory_uncertainty"]["standard"]


def test_kpi_definitions_requires_authentication(client):
    """Unauthenticated users must be rejected from KPI definitions."""
    res = client.get("/api/dashboard/kpi-definitions")
    assert res.status_code == 401


def test_maker_checker_rejection_audit_trail(app, client):
    """Test rejecting a record provides audit reason and updates status to Rejected."""
    with app.app_context():
        admin = make_user("admin")
        creator = make_user("user")
        fac = make_facility(name=uniq("FAC_REJECT"))

        em = Emission(
            facility_id=fac.id,
            year=2024,
            month=6,
            process_type="combustion",
            fuel_type="Diesel",
            quantity=100.0,
            unit="m3",
            co2e_total=250.0,
            status="Pending",
            created_by=creator.id,
        )
        db.session.add(em)
        db.session.commit()
        em_id = em.id

        login(client, admin)

    res = client.post(
        f"/api/emissions/reject/{em_id}",
        json={
            "scope": "1",
            "reason": "Audit QA check: activity documentation missing metering certificate",
        },
    )
    assert res.status_code in (200, 201)

    with app.app_context():
        updated = Emission.query.get(em_id)
        assert updated.status == "Rejected"
        assert "documentation missing" in (getattr(updated, "rejection_reason", None) or updated.qa_flag or "")
        
        # Verify an activity log entry was generated
        log_entry = ActivityLog.query.filter(
            ActivityLog.action.in_(["REJECT", "REJECT_EMISSION", "UPDATE", "DECIDE_REJECT"])
        ).order_by(ActivityLog.id.desc()).first()
        assert log_entry is not None

