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


def test_qaqc_status_filtering_excludes_rejected_on_all(client, admin_user):
    """Verify that 'all' status excludes rejected records, and 'rejected' status returns only rejected."""
    client.post(
        "/api/auth/login",
        json={"email": "qa_admin@test.com", "password": "AdminPass123!"},
    )

    # 1. Default / All statuses query
    res_all = client.get("/api/qaqc/dashboard?status=all")
    assert res_all.status_code == 200
    data_all = res_all.get_json()
    flagged_all = data_all["flagged_records"]
    # None of the records in 'all' should be rejected
    for rec in flagged_all:
        status_lower = (rec.get("status") or "").lower()
        assert "rejected" not in status_lower, f"Record {rec['id']} with status {rec.get('status')} should not appear in 'all'"

    # 2. Rejected tab query
    res_rej = client.get("/api/qaqc/dashboard?status=rejected")
    assert res_rej.status_code == 200
    data_rej = res_rej.get_json()
    flagged_rej = data_rej["flagged_records"]
    # All records returned should be rejected
    for rec in flagged_rej:
        status_lower = (rec.get("status") or "").lower()
        assert "rejected" in status_lower, f"Record {rec['id']} with status {rec.get('status')} must be rejected"


def test_qaqc_diagnostics_action_urls_and_samples(client, admin_user):
    """Verify that all diagnostic action URLs route to /manage-data and provide sample records when affected_count > 0."""
    client.post(
        "/api/auth/login",
        json={"email": "qa_admin@test.com", "password": "AdminPass123!"},
    )

    res = client.get("/api/qaqc/dashboard")
    assert res.status_code == 200
    data = res.get_json()
    diag = data["diagnostics"]

    all_items = diag.get("issues", []) + diag.get("warnings", []) + diag.get("suggestions", [])
    for item in all_items:
        action_url = item.get("action_url")
        if action_url:
            assert "/reference-data" not in action_url, f"Finding {item.get('id')} should not link to /reference-data"
            assert "/manage-data" in action_url, f"Finding {item.get('id')} action_url should route to /manage-data"

        if item.get("affected_count", 0) > 0:
            sample_records = item.get("sample_records", [])
            assert len(sample_records) > 0, f"Finding {item.get('id')} with affected_count {item.get('affected_count')} must provide sample_records"
            assert "id" in sample_records[0], f"Sample records for {item.get('id')} must include an id"


