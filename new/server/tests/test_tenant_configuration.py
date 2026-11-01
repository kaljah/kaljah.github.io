"""
Tests for Tenant Configuration (Item 3.7)
Verifies that operator metadata ('Sonatrach') and regulatory decree ('Executive Decree 21-330 Article 9')
are configurable via service, DB persistence, and API.
"""
import pytest
from app import app
from models import db, User, ActivityLog, SystemSetting
from services.tenant_config import get_tenant_config, update_tenant_config, DEFAULT_TENANT_CONFIG


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        with app.app_context():
            yield client


@pytest.fixture
def admin_user():
    with app.app_context():
        user = User.query.filter_by(email="tenant_admin@test.com").first()
        if not user:
            user = User(
                email="tenant_admin@test.com",
                fullName="Tenant Admin",
                orgName="Sonatrach",
                sector="Oil & Gas",
                role="admin",
                status="active",
            )
            user.set_password("TenantAdmin123!")
            db.session.add(user)
            db.session.commit()
        return user


def test_default_tenant_config_values():
    """Verify default tenant configuration matches Sonatrach & Executive Decree 21-330 Article 9."""
    cfg = get_tenant_config("default")
    assert cfg["organization_name"] == "Sonatrach"
    assert cfg["regulatory_framework"] == "Executive Decree 21-330 Article 9"
    assert cfg["country"] == "Algeria"


def test_get_tenant_config_api(client, admin_user):
    """Verify GET /api/tenant/config returns active tenant settings."""
    with client.session_transaction() as sess:
        sess["user_id"] = admin_user.id
        sess["role"] = admin_user.role

    res = client.get("/api/tenant/config")
    assert res.status_code == 200
    data = res.get_json()
    assert data["organization_name"] == "Sonatrach"
    assert data["regulatory_framework"] == "Executive Decree 21-330 Article 9"


def test_update_tenant_config_persists_and_audits(client, admin_user):
    """Verify PUT /api/tenant/config persists changes to DB and logs an audit trail event."""
    with client.session_transaction() as sess:
        sess["user_id"] = admin_user.id
        sess["role"] = admin_user.role

    update_payload = {
        "organization_name": "Sonatrach E&P Joint Venture",
        "regulatory_framework": "Executive Decree 21-330 Article 9 (Audited)",
        "country": "Algeria",
    }
    res = client.put("/api/tenant/config", json=update_payload)
    assert res.status_code == 200
    body = res.get_json()
    assert body["status"] == "success"
    assert body["config"]["organization_name"] == "Sonatrach E&P Joint Venture"
    assert body["config"]["regulatory_framework"] == "Executive Decree 21-330 Article 9 (Audited)"

    # Verify persistence via get_tenant_config
    refreshed = get_tenant_config("default")
    assert refreshed["organization_name"] == "Sonatrach E&P Joint Venture"

    # Verify ActivityLog audit entry
    log = ActivityLog.query.filter_by(action="SETTINGS_CHANGE", entity="TenantConfig").order_by(ActivityLog.id.desc()).first()
    assert log is not None
    assert "Sonatrach E&P Joint Venture" in log.new_values

    # Clean up test override
    update_tenant_config("default", {
        "organization_name": "Sonatrach",
        "regulatory_framework": "Executive Decree 21-330 Article 9",
        "country": "Algeria",
    }, user=admin_user)
