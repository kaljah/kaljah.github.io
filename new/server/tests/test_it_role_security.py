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


def test_it_manager_full_management_capabilities(client):
    """IT Manager role has full access to user management without limitation."""
    with app.app_context():
        mgr = User.query.filter_by(email="it_manager_tester@domain.com").first()
        if not mgr:
            mgr = User(
                email="it_manager_tester@domain.com",
                fullName="IT Manager Tester",
                orgName="Energy Corp",
                sector="Energy",
                role="it_manager",
                jobTitle="Head of IT",
            )
            mgr.set_password("SecureManagerPass123!")
            db.session.add(mgr)
            db.session.commit()
        mgr_id = mgr.id

    with client.session_transaction() as sess:
        sess["user_id"] = mgr_id

    # 1. IT Manager can create user with any role
    res_create = client.post(
        "/api/auth/register",
        json={
            "fullName": "Managed User One",
            "email": "managed_user_1@domain.com",
            "orgName": "Energy Corp",
            "sector": "Energy",
            "password": "InitialUserPass123!",
            "role": "user",
            "location": "Ouargla",
        },
    )
    assert res_create.status_code in [200, 201]
    created_id = res_create.get_json()["user"]["id"]

    # 2. IT Manager can modify role, region, and status
    res_update = client.put(
        f"/api/auth/users/{created_id}",
        json={
            "fullName": "Managed User One Updated",
            "role": "superuser",
            "location": "Hassi Messaoud",
            "status": "disabled",
        },
    )
    assert res_update.status_code == 200
    u_data = res_update.get_json()["user"]
    assert u_data["role"] == "superuser"
    assert u_data["location"] == "Hassi Messaoud"
    assert u_data["status"] == "disabled"

    # 3. IT Manager can reset password
    res_reset = client.post(
        f"/api/auth/users/{created_id}/reset-password",
        json={"newPassword": "NewManagedPass2026!"},
    )
    assert res_reset.status_code == 200

    # 4. IT Manager can delete user
    res_delete = client.delete(f"/api/auth/users/{created_id}")
    assert res_delete.status_code == 200

    # 5. IT Manager has zero operational data access
    assert client.get("/api/facilities").status_code == 403
    assert client.get("/api/emissions").status_code == 403


def test_it_user_cannot_reset_admin_or_superuser_password(client, test_accounts):
    """IT and IT Admin roles cannot reset password for Admin or Superuser accounts (403 Forbidden)."""
    with app.app_context():
        admin_u = User.query.filter_by(role="admin").first()
        if not admin_u:
            admin_u = User(
                email="admin_sec_test@domain.com",
                fullName="Compliance Admin",
                orgName="Energy Corp",
                sector="Energy",
                role="admin",
            )
            admin_u.set_password("AdminSecurePass123!")
            db.session.add(admin_u)
            db.session.commit()
        admin_id = admin_u.id

        super_u = User.query.filter_by(role="superuser").first()
        if not super_u:
            super_u = User(
                email="super_sec_test@domain.com",
                fullName="Operational Lead",
                orgName="Energy Corp",
                sector="Energy",
                role="superuser",
                location="Hassi Messaoud",
            )
            super_u.set_password("SuperSecurePass123!")
            db.session.add(super_u)
            db.session.commit()
        super_id = super_u.id

    # Test as IT Support
    with client.session_transaction() as sess:
        sess["user_id"] = test_accounts["it_id"]

    res_admin = client.post(
        f"/api/auth/users/{admin_id}/reset-password",
        json={"newPassword": "HackedPassword123!"},
    )
    assert res_admin.status_code == 403

    res_super = client.post(
        f"/api/auth/users/{super_id}/reset-password",
        json={"newPassword": "HackedPassword123!"},
    )
    assert res_super.status_code == 403

    # Test as IT Admin
    with client.session_transaction() as sess:
        sess["user_id"] = test_accounts["it_admin_id"]

    res_admin2 = client.post(
        f"/api/auth/users/{admin_id}/reset-password",
        json={"newPassword": "HackedPassword123!"},
    )
    assert res_admin2.status_code == 403

    res_super2 = client.post(
        f"/api/auth/users/{super_id}/reset-password",
        json={"newPassword": "HackedPassword123!"},
    )
    assert res_super2.status_code == 403


def test_it_admin_cannot_create_admin_or_superuser(client, test_accounts):
    """IT Admin cannot create business admin or superuser accounts (403 Forbidden)."""
    with client.session_transaction() as sess:
        sess["user_id"] = test_accounts["it_admin_id"]

    res_admin = client.post(
        "/api/auth/register",
        json={
            "fullName": "Disallowed Admin",
            "email": "disallowed_admin@domain.com",
            "orgName": "Energy Corp",
            "sector": "Energy",
            "password": "Password123!@#",
            "role": "admin",
        },
    )
    assert res_admin.status_code == 403

    res_super = client.post(
        "/api/auth/register",
        json={
            "fullName": "Disallowed Superuser",
            "email": "disallowed_super@domain.com",
            "orgName": "Energy Corp",
            "sector": "Energy",
            "password": "Password123!@#",
            "role": "superuser",
        },
    )
    assert res_super.status_code == 403


def test_it_user_cannot_access_equity_or_cap_data(client, test_accounts):
    """IT roles cannot access Joint Venture partners, equity shares, CAP emissions or CAP compliance."""
    with client.session_transaction() as sess:
        sess["user_id"] = test_accounts["it_id"]

    assert client.get("/api/equity/partners").status_code == 403
    assert client.get("/api/equity/shares").status_code == 403
    assert client.get("/api/cap/emissions").status_code == 403
    assert client.get("/api/cap/compliance").status_code == 403
    assert client.get("/api/satellite/sentinel5p/layer-config").status_code == 403
    assert client.get("/api/satellite/sentinel5p/query").status_code == 403


def test_non_numeric_facility_id_returns_422(client, test_accounts):
    """Invalid / non-numeric facility_id returns HTTP 422 Unprocessable Entity instead of 500 error."""
    with app.app_context():
        admin_u = User.query.filter_by(role="admin").first()
        admin_id = admin_u.id

    with client.session_transaction() as sess:
        sess["user_id"] = admin_id

    # Scope 2
    res_s2 = client.post(
        "/api/scope2",
        json={"facility_id": "not-an-id", "year": 2024, "month": 6, "source_type": "electricity"},
    )
    assert res_s2.status_code == 422

    # Scope 3
    res_s3 = client.post(
        "/api/scope3",
        json={"facility_id": "bad_fid", "year": 2024, "category": "Category 1", "amount": 100, "emission_factor": 1.5},
    )
    assert res_s3.status_code == 422

    # CAP
    res_cap = client.get("/api/cap/emissions?facility_id=non_int")
    assert res_cap.status_code == 422


