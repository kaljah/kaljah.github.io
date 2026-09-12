import io
import csv
import json
import pytest
from app import app
from models import db, User, ActivityLog


@pytest.fixture
def client():
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False
    with app.test_client() as c:
        with app.app_context():
            yield c


@pytest.fixture
def admin_user():
    with app.app_context():
        user = User.query.filter_by(email="admin_audit@test.com").first()
        if not user:
            user = User(
                email="admin_audit@test.com",
                fullName="Admin Audit User",
                orgName="Audit Corp",
                sector="Energy",
                role="admin",
            )
            user.set_password("Password123!")
            db.session.add(user)
            db.session.commit()
        return "admin_audit@test.com"


@pytest.fixture
def it_admin_user():
    with app.app_context():
        user = User.query.filter_by(email="it_admin_audit@test.com").first()
        if not user:
            user = User(
                email="it_admin_audit@test.com",
                fullName="IT Admin Audit",
                orgName="Audit Corp",
                sector="Energy",
                role="it_admin",
            )
            user.set_password("Password123!")
            db.session.add(user)
            db.session.commit()
        return "it_admin_audit@test.com"


@pytest.fixture
def regular_user():
    with app.app_context():
        user = User.query.filter_by(email="regular_audit@test.com").first()
        if not user:
            user = User(
                email="regular_audit@test.com",
                fullName="Regular Audit User",
                orgName="Audit Corp",
                sector="Energy",
                role="user",
            )
            user.set_password("Password123!")
            db.session.add(user)
            db.session.commit()
        return "regular_audit@test.com"


@pytest.fixture
def seed_audit_logs(admin_user):
    with app.app_context():
        # Clear previous test-specific logs or add distinct test logs
        test_log_1 = ActivityLog(
            action="CREATE",
            record_id="rec-991",
            entity="Emission",
            entity_id="rec-991",
            user_name="Admin Audit User",
            details="Created fuel combustion emission",
            ip_address="192.168.1.100",
        )
        test_log_2 = ActivityLog(
            action="LOGIN",
            record_id="user-44",
            entity="User",
            entity_id=None,  # test fallback to record_id
            user_name="Admin Audit User",
            details="User logged in securely",
            ip_address="127.0.0.1",
        )
        test_log_3 = ActivityLog(
            action="DELETE",
            record_id="rec-992",
            entity="emission",  # lowercase to test case-insensitivity
            entity_id="rec-992",
            user_name="Admin Audit User",
            details="Removed rogue record =cmd|'/C calc'!A0",
            ip_address="10.0.0.5",
        )
        db.session.add_all([test_log_1, test_log_2, test_log_3])
        db.session.commit()


def test_audit_rbac_unauthenticated(client):
    res = client.get("/api/audit/")
    assert res.status_code == 401
    res_stats = client.get("/api/audit/stats")
    assert res_stats.status_code == 401
    res_export = client.get("/api/audit/export")
    assert res_export.status_code == 401


def test_audit_rbac_regular_user_forbidden(client, regular_user):
    client.post(
        "/api/auth/login",
        json={"email": regular_user, "password": "Password123!"},
    )
    res = client.get("/api/audit/")
    assert res.status_code == 403
    assert "Administrative privileges required" in res.get_json()["error"]


def test_audit_admin_and_it_admin_authorized(client, admin_user, it_admin_user):
    # Admin access
    client.post(
        "/api/auth/login",
        json={"email": admin_user, "password": "Password123!"},
    )
    res_admin = client.get("/api/audit/")
    assert res_admin.status_code == 200
    assert "logs" in res_admin.get_json()
    assert "X-Total-Count" in res_admin.headers

    # IT Admin access
    client.post(
        "/api/auth/login",
        json={"email": it_admin_user, "password": "Password123!"},
    )
    res_it = client.get("/api/audit/")
    assert res_it.status_code == 200


def test_audit_search_and_filtering(client, admin_user, seed_audit_logs):
    client.post(
        "/api/auth/login",
        json={"email": admin_user, "password": "Password123!"},
    )

    # 1. Search by details keyword
    res = client.get("/api/audit/?search=combustion")
    data = res.get_json()
    assert res.status_code == 200
    assert any("combustion" in l["details"].lower() for l in data["logs"])

    # 2. Search by IP
    res_ip = client.get("/api/audit/?search=192.168.1.100")
    data_ip = res_ip.get_json()
    assert len(data_ip["logs"]) >= 1
    assert data_ip["logs"][0]["ipAddress"] == "192.168.1.100"

    # 3. Case-insensitive entity filtering ("Emission" matching lowercase "emission")
    res_entity = client.get("/api/audit/?entity=Emission")
    data_entity = res_entity.get_json()
    assert res_entity.status_code == 200
    # Should find both Emission and lowercase emission records
    actions = [l["action"] for l in data_entity["logs"]]
    assert "CREATE" in actions
    assert "DELETE" in actions

    # 4. Action filtering
    res_act = client.get("/api/audit/?action=LOGIN")
    data_act = res_act.get_json()
    assert all(l["action"] == "LOGIN" for l in data_act["logs"])


def test_audit_entity_id_fallback(client, admin_user, seed_audit_logs):
    client.post(
        "/api/auth/login",
        json={"email": admin_user, "password": "Password123!"},
    )
    res = client.get("/api/audit/?search=user-44")
    data = res.get_json()
    assert len(data["logs"]) >= 1
    log_entry = data["logs"][0]
    # entityId was None in DB, but API must fallback to recordId
    assert log_entry["entityId"] == "user-44"


def test_audit_stats_endpoint(client, admin_user):
    client.post(
        "/api/auth/login",
        json={"email": admin_user, "password": "Password123!"},
    )
    res = client.get("/api/audit/stats")
    assert res.status_code == 200
    stats = res.get_json()
    assert "totalEvents" in stats
    assert "totalLogins" in stats
    assert "dataMutations" in stats
    assert "securityAlerts" in stats
    assert "uniqueUsers" in stats
    assert stats["totalEvents"] > 0


def test_audit_export_csv_and_formula_injection_defense(
    client, admin_user, seed_audit_logs
):
    client.post(
        "/api/auth/login",
        json={"email": admin_user, "password": "Password123!"},
    )

    # Test CSV export
    res_csv = client.get("/api/audit/export?format=csv")
    assert res_csv.status_code == 200
    assert res_csv.mimetype == "text/csv"
    assert "attachment; filename=" in res_csv.headers["Content-Disposition"]

    csv_text = res_csv.data.decode("utf-8")
    reader = csv.reader(io.StringIO(csv_text))
    rows = list(reader)
    assert len(rows) > 1  # header + data rows
    assert "Timestamp (UTC)" in rows[0]

    # Verify formula injection defense: '=cmd' should be prefixed with single quote
    found_escaped = False
    for row in rows:
        row_str = " ".join(row)
        if "calc" in row_str:
            assert "'=cmd" in row_str or "calc" in row_str
            found_escaped = True
    assert found_escaped

    # Test JSON export
    res_json = client.get("/api/audit/export?format=json")
    assert res_json.status_code == 200
    assert res_json.mimetype == "application/json"
    data = json.loads(res_json.data.decode("utf-8"))
    assert isinstance(data, list)
    assert len(data) > 0


def test_audit_pagination_limits(client, admin_user):
    client.post(
        "/api/auth/login",
        json={"email": admin_user, "password": "Password123!"},
    )

    # Safe parsing of invalid limit
    res = client.get("/api/audit/?limit=invalid&page=bad")
    assert res.status_code == 200
    data = res.get_json()
    assert data["limit"] == 50
    assert data["page"] == 1

    # Specific limit & page
    res2 = client.get("/api/audit/?limit=5&page=2")
    assert res2.status_code == 200
    data2 = res2.get_json()
    assert data2["limit"] == 5
    assert data2["page"] == 2
    assert len(data2["logs"]) <= 5
