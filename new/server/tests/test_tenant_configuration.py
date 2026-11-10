"""
Tests for Tenant Configuration (Item 3.7)
Verifies that operator metadata ('Demo Operator Co.') and regulatory decree ('Executive Decree 21-330 Article 9')
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
                orgName="Demo Operator Co.",
                sector="Oil & Gas",
                role="admin",
                status="active",
            )
            user.set_password("TenantAdmin123!")
            db.session.add(user)
            db.session.commit()
        return user


def test_default_tenant_config_values():
    """Verify default tenant configuration matches Demo Operator Co. & Executive Decree 21-330 Article 9."""
    cfg = get_tenant_config("default")
    assert cfg["organization_name"] == "Demo Operator Co."
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
    assert data["organization_name"] == "Demo Operator Co."
    assert data["regulatory_framework"] == "Executive Decree 21-330 Article 9"


def test_update_tenant_config_persists_and_audits(client, admin_user):
    """Verify PUT /api/tenant/config persists changes to DB and logs an audit trail event."""
    with client.session_transaction() as sess:
        sess["user_id"] = admin_user.id
        sess["role"] = admin_user.role

    update_payload = {
        "organization_name": "Demo Operator Co. E&P Joint Venture",
        "regulatory_framework": "Executive Decree 21-330 Article 9 (Audited)",
        "country": "Algeria",
    }
    res = client.put("/api/tenant/config", json=update_payload)
    assert res.status_code == 200
    body = res.get_json()
    assert body["status"] == "success"
    assert body["config"]["organization_name"] == "Demo Operator Co. E&P Joint Venture"
    assert body["config"]["regulatory_framework"] == "Executive Decree 21-330 Article 9 (Audited)"

    # Verify persistence via get_tenant_config
    refreshed = get_tenant_config("default")
    assert refreshed["organization_name"] == "Demo Operator Co. E&P Joint Venture"

    # Verify ActivityLog audit entry
    log = ActivityLog.query.filter_by(action="SETTINGS_CHANGE", entity="TenantConfig").order_by(ActivityLog.id.desc()).first()
    assert log is not None
    assert "Demo Operator Co. E&P Joint Venture" in log.new_values

    # Clean up test override from DB
    from models import SystemSetting
    setting = SystemSetting.query.filter_by(key="tenant_config").first()
    if setting:
        db.session.delete(setting)
        db.session.commit()


def test_tenant_config_cross_tenant_isolation(client, app):
    """Verify that updating default tenant does not leak into other tenant configs."""
    with app.app_context():
        from models import SystemSetting
        # Ensure default override exists
        update_tenant_config("default", {"organization_name": "Demo Operator Co. Custom EP"})
        
        # Non-default tenant should still retain its own registry values
        mena_b = get_tenant_config("mena_operator_b")
        assert mena_b["organization_name"] == "Al-Amal Petroleum Corp"
        assert mena_b["country"] == "MENA Region"

        # Clean up
        setting = SystemSetting.query.filter_by(key="tenant_config").first()
        if setting:
            db.session.delete(setting)
            db.session.commit()


def test_tenant_config_idor_and_validation(client, admin_user):
    """Verify IDOR prevention and invalid year rejection."""
    with client.session_transaction() as sess:
        sess["user_id"] = admin_user.id
        sess["role"] = admin_user.role
        sess["tenant_id"] = "default"

    # 1. Non-superuser cannot modify another tenant
    res_idor = client.put("/api/tenant/config?tenant_id=mena_operator_b", json={"organization_name": "Hacked Corp"})
    assert res_idor.status_code == 403

    # 2. Invalid year format is rejected
    res_val = client.put("/api/tenant/config", json={"base_year": "invalid_year"})
    assert res_val.status_code == 400

    res_val2 = client.put("/api/tenant/config", json={"base_year": 1850})
    assert res_val2.status_code == 400
