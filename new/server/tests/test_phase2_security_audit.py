import pytest
import os
import json
from extensions import db
from models import User, ActivityLog
from services.login_guard import validate_password_complexity, record_failed_sign_in
from utils import get_client_ip, log_activity_and_notify


@pytest.fixture
def it_admin_client(app, client):
    with app.app_context():
        user = User.query.filter_by(role="it_admin", status="active").first()
        if not user:
            user = User(
                email="it_phase2_admin@sonatrach.dz",
                fullName="IT Admin",
                orgName="Sonatrach",
                sector="Oil & Gas",
                role="it_admin",
                status="active"
            )
            user.set_password("AdminPass123!@#")
            db.session.add(user)
            db.session.commit()
        user_id = user.id
        sv = int(user.session_version or 0)
    with client.session_transaction() as sess:
        sess["user_id"] = user_id
        sess["sv"] = sv
    return client


def test_password_complexity_validator():
    """Item 2.1: Verify Enterprise Complexity Policy rules."""
    # Too short (< 10)
    ok, msg = validate_password_complexity("Ab1!")
    assert not ok
    assert "10 characters" in msg

    # Missing uppercase
    ok, msg = validate_password_complexity("lowercase123!@#")
    assert not ok
    assert "uppercase" in msg

    # Missing lowercase
    ok, msg = validate_password_complexity("UPPERCASE123!@#")
    assert not ok
    assert "lowercase" in msg

    # Missing digit
    ok, msg = validate_password_complexity("NoDigitsHere!@#")
    assert not ok
    assert "numeric digit" in msg

    # Missing special character
    ok, msg = validate_password_complexity("NoSpecialChars123")
    assert not ok
    assert "special character" in msg

    # Valid password
    ok, msg = validate_password_complexity("ValidEnterpriseP@ss2026")
    assert ok
    assert msg == ""


def test_session_policy_password_label(app, it_admin_client):
    """Item 2.1: Verify session policy endpoint returns clear enterprise policy label."""
    res = it_admin_client.get("/api/auth/sessions/policy")
    assert res.status_code == 200
    data = res.get_json()
    assert "Enterprise Complexity Standard" in data.get("password_policy", "") or "Enterprise Complexity Standard" in data.get("nist_password_policy", "")


def test_failed_login_records_attempted_email_actor(app, client):
    """Item 2.4: Failed sign-in records the attempted email as actor, not 'System'."""
    with app.app_context():
        test_email = "intruder_attempt@sonatrach.dz"
        client.post(
            "/api/auth/login",
            json={"email": test_email, "password": "WrongPassword123!"},
            headers={"X-Forwarded-For": "198.51.100.77"}
        )
        log = ActivityLog.query.filter_by(action="FAILED_LOGIN").order_by(ActivityLog.id.desc()).first()
        assert log is not None
        assert log.user_name == test_email
        assert log.user_name != "System"
        assert log.ip_address == "198.51.100.77"


def test_client_ip_behind_dev_proxy():
    """Item 2.4: get_client_ip correctly extracts client IP from X-Forwarded-For."""
    class MockRequest:
        def __init__(self, remote_addr, xff):
            self.remote_addr = remote_addr
            self.headers = {"X-Forwarded-For": xff} if xff else {}

    # Behind local dev proxy (127.0.0.1) with XFF
    req = MockRequest("127.0.0.1", "203.0.113.55, 127.0.0.1")
    assert get_client_ip(req) == "203.0.113.55"

    # Direct connection without XFF
    req_direct = MockRequest("10.0.0.5", None)
    assert get_client_ip(req_direct) == "10.0.0.5"


def test_emergency_session_revocation_preserves_admin(app, it_admin_client):
    """Item 2.3: Revoke all active sessions excludes current admin and logs audit entry."""
    with app.app_context():
        # Get current admin from session
        with it_admin_client.session_transaction() as sess:
            admin_id = sess.get("user_id")
        
        admin_user = db.session.get(User, admin_id)
        orig_admin_sv = int(admin_user.session_version or 0)

        # Create or fetch a test regular user
        reg_user = User.query.filter(User.role == "user", User.id != admin_id).first()
        if not reg_user:
            reg_user = User(email="temp_user@test.com", fullName="Temp User", orgName="Sonatrach", sector="Oil & Gas", role="user", session_version=1)
            reg_user.set_password("TempUserPass123!")
            db.session.add(reg_user)
            db.session.commit()
        orig_user_sv = int(reg_user.session_version or 0)

        res = it_admin_client.post("/api/auth/sessions/revoke-all")
        assert res.status_code == 200

        # Admin session version preserved
        db.session.refresh(admin_user)
        db.session.refresh(reg_user)
        assert int(admin_user.session_version or 0) == orig_admin_sv
        assert int(reg_user.session_version or 0) > orig_user_sv

        # Check audit trail
        audit_log = ActivityLog.query.filter_by(action="REVOKE_ALL_SESSIONS").order_by(ActivityLog.id.desc()).first()
        assert audit_log is not None
        assert "preserved" in audit_log.details.lower() or "revoked" in audit_log.details.lower()


def test_audit_stats_categories_sum_to_total(app, it_admin_client):
    """Item 2.4: Category counters sum exactly to total events."""
    res = it_admin_client.get("/api/audit/stats")
    assert res.status_code == 200
    data = res.get_json()
    total = data["totalEvents"]
    logins = data["totalLogins"]
    mutations = data["dataMutations"]
    security = data["securityAlerts"]
    other = data.get("otherEvents", 0)

    assert logins + mutations + security + other == total
