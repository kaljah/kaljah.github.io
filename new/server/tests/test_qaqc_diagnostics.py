"""
Test suite for /api/qaqc/dashboard unified diagnostics & QA/QC endpoint.
Covers:
- Auth & RBAC (Admin required)
- Response structure (tier1_uncertainty, diagnostics, flagged_records)
- Diagnostics metrics (health_score, completeness, dimension_completeness, issues, warnings)
- CSV export
"""
import pytest
from app import app
from models import db, User, Facility


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
        user = User.query.filter_by(email="qa_admin@test.com").first()
        if not user:
            user = User(
                email="qa_admin@test.com",
                fullName="QA Admin",
                orgName="Energy Corp",
                sector="Oil & Gas",
                role="admin",
            )
            user.set_password("AdminPass123!")
            db.session.add(user)
            db.session.commit()
        return user


def test_qaqc_unauthenticated(client):
    """Unauthenticated access must be rejected."""
    res = client.get("/api/qaqc/dashboard")
    assert res.status_code in [401, 302]


def test_qaqc_dashboard_unified_payload(client, admin_user):
    """Admin user receives unified uncertainty, diagnostics, and anomaly queue data."""
    login_res = client.post(
        "/api/auth/login",
        json={"email": "qa_admin@test.com", "password": "AdminPass123!"},
    )
    assert login_res.status_code == 200

    res = client.get("/api/qaqc/dashboard")
    assert res.status_code == 200
    data = res.get_json()

    # Core QA/QC keys
    assert data.get("status") == "success"
    assert "tier1_uncertainty" in data
    assert "flagged_records" in data
    assert "total_flagged_count" in data

    # Uncertainty shape
    unc = data["tier1_uncertainty"]
    assert "overall" in unc
    assert "scope1" in unc
    assert "scope2" in unc
    assert "scope3" in unc

    # Unified Diagnostics payload
    assert "diagnostics" in data
    diag = data["diagnostics"]
    assert "health_score" in diag
    assert 0 <= diag["health_score"] <= 100
    assert "completeness" in diag
    assert "dimension_completeness" in diag
    assert "total_records" in diag
    assert "issues" in diag
    assert "warnings" in diag
    assert "suggestions" in diag
    assert "anomalies_summary" in diag


def test_qaqc_export_csv(client, admin_user):
    """Export endpoint returns CSV with correct Content-Type."""
    client.post(
        "/api/auth/login",
        json={"email": "qa_admin@test.com", "password": "AdminPass123!"},
    )
    res = client.get("/api/qaqc/export")
    assert res.status_code == 200
    assert "text/csv" in res.content_type
    content = res.data.decode("utf-8")
    assert "Record ID" in content
    assert "Issue (QA Flag)" in content
