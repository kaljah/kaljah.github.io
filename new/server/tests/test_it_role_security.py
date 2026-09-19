import pytest
from app import app
from models import db, User


@pytest.fixture
def client():
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False
    with app.test_client() as c:
        with app.app_context():
            yield c


@pytest.fixture
def test_accounts(client):
    """Sets up an IT user, IT Admin user, and a target standard user."""
    with app.app_context():
        # Target standard user
        target = User.query.filter_by(email="it_test_target@domain.com").first()
        if not target:
            target = User(
                email="it_test_target@domain.com",
                fullName="Target Standard User",
                orgName="Energy Corp",
                sector="Energy",
                role="user",
                location="Hassi Messaoud",
                department="Operations",
                jobTitle="Technician",
            )
            target.set_password("OldTargetPass123!")
            db.session.add(target)

        # IT user (restricted role)
        it_user = User.query.filter_by(email="it_test_support@domain.com").first()
        if not it_user:
            it_user = User(
                email="it_test_support@domain.com",
                fullName="IT Support Person",
                orgName="Energy Corp",
                sector="Energy",
                role="it",
                jobTitle="Helpdesk Specialist",
            )
            it_user.set_password("ITUserPassword123!")
            db.session.add(it_user)

        # IT Admin user
        it_admin = User.query.filter_by(email="it_test_admin@domain.com").first()
        if not it_admin:
            it_admin = User(
                email="it_test_admin@domain.com",
                fullName="IT Admin Supervisor",
                orgName="Energy Corp",
                sector="Energy",
                role="it_admin",
                jobTitle="Systems Administrator",
            )
            it_admin.set_password("ITAdminPassword123!")
            db.session.add(it_admin)

        db.session.commit()
        return {
            "target_id": target.id,
            "it_id": it_user.id,
            "it_admin_id": it_admin.id,
        }


def test_it_user_can_login_and_fetch_users(client, test_accounts):
    """IT role can access the user list to view users."""
    with client.session_transaction() as sess:
        sess["user_id"] = test_accounts["it_id"]

    res = client.get("/api/auth/users")
    assert res.status_code == 200
    users = res.get_json()
    assert isinstance(users, list)
    user_emails = [u["email"] for u in users]
    assert "it_test_target@domain.com" in user_emails


def test_it_user_can_reset_password(client, test_accounts):
    """IT role can reset user passwords."""
    with client.session_transaction() as sess:
        sess["user_id"] = test_accounts["it_id"]

    new_pass = "BrandNewValidPass2026!"
    res = client.post(
        f"/api/auth/users/{test_accounts['target_id']}/reset-password",
        json={"newPassword": new_pass},
    )
    assert res.status_code == 200
    data = res.get_json()
    assert "successfully reset" in data["message"].lower()

    # Verify password hash updated and works
    with app.app_context():
        u = db.session.get(User, test_accounts["target_id"])
        assert u.check_password(new_pass)


def test_it_user_cannot_register_user(client, test_accounts):
    """IT role cannot register / provision new users (403 Forbidden)."""
    with client.session_transaction() as sess:
        sess["user_id"] = test_accounts["it_id"]

    payload = {
        "fullName": "Intruder User",
        "email": "intruder@domain.com",
        "orgName": "Energy Corp",
        "sector": "Energy",
        "password": "Password123!@#",
    }
    res = client.post("/api/auth/register", json=payload)
    assert res.status_code == 403


def test_it_user_cannot_update_user_profile(client, test_accounts):
    """IT role cannot modify user profiles, names, roles, or departments (403 Forbidden)."""
    with client.session_transaction() as sess:
        sess["user_id"] = test_accounts["it_id"]

    payload = {
        "fullName": "Tampered Name",
        "role": "admin",
    }
    res = client.put(f"/api/auth/users/{test_accounts['target_id']}", json=payload)
    assert res.status_code == 403


def test_it_user_cannot_delete_user(client, test_accounts):
    """IT role cannot delete users (403 Forbidden)."""
    with client.session_transaction() as sess:
        sess["user_id"] = test_accounts["it_id"]

    res = client.delete(f"/api/auth/users/{test_accounts['target_id']}")
    assert res.status_code == 403


def test_it_user_cannot_access_audit_trail(client, test_accounts):
    """IT role cannot view or export audit trail (403 Forbidden)."""
    with client.session_transaction() as sess:
        sess["user_id"] = test_accounts["it_id"]

    res = client.get("/api/audit/")
    assert res.status_code == 403

    res_export = client.get("/api/audit/export")
    assert res_export.status_code == 403


def test_it_user_cannot_access_operational_facilities_or_emissions(client, test_accounts):
    """IT role has zero access to facilities, emissions, scope 2/3, sources, or reports."""
    with client.session_transaction() as sess:
        sess["user_id"] = test_accounts["it_id"]

    assert client.get("/api/facilities").status_code == 403
    assert client.get("/api/emissions").status_code == 403
    assert client.get("/api/scope2").status_code == 403
    assert client.get("/api/scope3").status_code == 403
    assert client.get("/api/sources").status_code == 403
    assert client.get("/api/reports/export").status_code == 403
    assert client.get("/api/custom-factors").status_code == 403


def test_it_user_can_access_all_regions_for_filtering(client, test_accounts):
    """IT role can access region identifiers for UI filtering without error."""
    with client.session_transaction() as sess:
        sess["user_id"] = test_accounts["it_id"]

    res = client.get("/api/facilities/all-regions")
    assert res.status_code == 200
    assert isinstance(res.get_json(), list)


def test_it_user_cannot_modify_settings(client, test_accounts):
    """IT role cannot modify application or user settings (403 Forbidden)."""
    with client.session_transaction() as sess:
        sess["user_id"] = test_accounts["it_id"]

    res = client.put("/api/auth/settings", json={"theme": "dark", "gwp_standard": "AR6"})
    assert res.status_code == 403


def test_it_admin_can_assign_it_role(client, test_accounts):
    """IT Admin can assign the 'it' role to an existing user."""
    with client.session_transaction() as sess:
        sess["user_id"] = test_accounts["it_admin_id"]

    res = client.put(
        f"/api/auth/users/{test_accounts['target_id']}",
        json={"role": "it"},
    )
    assert res.status_code == 200
    data = res.get_json()
    assert data["user"]["role"] == "it"

    # Verify directly from DB
    with app.app_context():
        u = db.session.get(User, test_accounts["target_id"])
        assert u.role == "it"
