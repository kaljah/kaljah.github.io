"""
Test suite for /dashboard/uncertainty endpoint.
Covers: auth, RBAC, year/facility/scope filtering, CSV export,
and 95% CI correctness (k=2 coverage factor per GUM §6.2).
"""
import pytest
import math
from app import app
from models import db, User, Emission, Scope2Emission, Scope3Emission, Facility


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
        user = User.query.filter_by(email="a@a").first()
        if not user:
            user = User(
                email="a@a",
                fullName="Admin User",
                orgName="AdminOrg",
                sector="Energy",
                role="admin",
            )
            user.set_password("a")
            db.session.add(user)
            db.session.commit()
        return user


@pytest.fixture
def it_admin_user():
    with app.app_context():
        user = User.query.filter_by(email="it@test.com").first()
        if not user:
            user = User(
                email="it@test.com",
                fullName="IT Admin",
                orgName="TestOrg",
                sector="Oil & Gas",
                role="it_admin",
            )
            user.set_password("password")
            db.session.add(user)
            db.session.commit()
        return user


# ────────────────────────────────────────────────────────────
# AUTH & RBAC
# ────────────────────────────────────────────────────────────


def test_uncertainty_unauthenticated(client):
    """Unauthenticated requests must return 401."""
    res = client.get("/api/dashboard/uncertainty")
    assert res.status_code == 401


def test_uncertainty_it_admin_blocked(client, it_admin_user):
    """IT Admin users must be forbidden (403) from operational dashboard data."""
    client.post(
        "/api/auth/login",
        json={"email": "it@test.com", "password": "password"},
    )
    res = client.get("/api/dashboard/uncertainty")
    assert res.status_code == 403
    assert "Forbidden" in res.get_json().get("error", "")


# ────────────────────────────────────────────────────────────
# DEFAULT RESPONSE SHAPE
# ────────────────────────────────────────────────────────────


def test_uncertainty_default_response(client, admin_user):
    """Admin users receive a well-formed uncertainty response."""
    client.post("/api/auth/login", json={"email": "a@a", "password": "a"})
    res = client.get("/api/dashboard/uncertainty")
    assert res.status_code == 200

    data = res.get_json()
    assert "year" in data
    assert "inventory_uncertainty_pct" in data
    assert "inventory_uncertainty_decimal" in data
    assert "tier_breakdown" in data
    assert "categories" in data
    assert data.get("confidence_level_pct") == 95
    assert data.get("coverage_factor") == 2.0


# ────────────────────────────────────────────────────────────
# YEAR FILTER
# ────────────────────────────────────────────────────────────


def test_uncertainty_year_filter(client, admin_user):
    """Specifying year= returns that year in the response."""
    client.post("/api/auth/login", json={"email": "a@a", "password": "a"})
    res = client.get("/api/dashboard/uncertainty?year=2024")
    assert res.status_code == 200
    data = res.get_json()
    assert data["year"] == 2024


# ────────────────────────────────────────────────────────────
# SCOPE FILTER
# ────────────────────────────────────────────────────────────


def test_uncertainty_scope_filter(client, admin_user):
    """scope=1 should only return Scope 1 categories (no Scope 2/3 groups)."""
    client.post("/api/auth/login", json={"email": "a@a", "password": "a"})
    res = client.get("/api/dashboard/uncertainty?scope=1")
    assert res.status_code == 200
    data = res.get_json()
    assert data["scope"] == "1"
    # No Scope 2 or Scope 3 categories should be present
    for cat in data.get("categories", []):
        assert "Scope 2" not in cat["category"]
        assert "Scope 3" not in cat["category"]


# ────────────────────────────────────────────────────────────
# CSV EXPORT
# ────────────────────────────────────────────────────────────


def test_uncertainty_csv_export(client, admin_user):
    """export=csv should return text/csv with correct headers."""
    client.post("/api/auth/login", json={"email": "a@a", "password": "a"})
    res = client.get("/api/dashboard/uncertainty?export=csv")
    assert res.status_code == 200
    assert "text/csv" in res.content_type
    content = res.data.decode("utf-8")
    # CSV header row
    assert "Category" in content
    assert "Total Emissions" in content
    assert "Uncertainty" in content
    assert "Coverage Factor" in content


# ────────────────────────────────────────────────────────────
# CALCULATION CORRECTNESS — 95% CI = k × 1σ
# ────────────────────────────────────────────────────────────


def test_uncertainty_95ci_correctness(client, admin_user):
    """
    Verify that inventory_uncertainty_decimal ≈ 2 × inventory_uncertainty_1sigma.
    This confirms the GUM §6.2 coverage factor k=2 is applied correctly.
    """
    client.post("/api/auth/login", json={"email": "a@a", "password": "a"})
    res = client.get("/api/dashboard/uncertainty")
    assert res.status_code == 200
    data = res.get_json()

    u_95 = data.get("inventory_uncertainty_decimal", 0)
    u_1s = data.get("inventory_uncertainty_1sigma", 0)

    if u_1s > 0:
        # 95% CI should be exactly 2× the 1-sigma value
        assert abs(u_95 - 2.0 * u_1s) < 1e-10, (
            f"95% CI ({u_95}) should be 2 × 1σ ({u_1s})"
        )


def test_uncertainty_category_95ci(client, admin_user):
    """Verify per-category uncertainty_decimal is also 95% CI (2× 1sigma)."""
    client.post("/api/auth/login", json={"email": "a@a", "password": "a"})
    res = client.get("/api/dashboard/uncertainty")
    assert res.status_code == 200
    data = res.get_json()

    for cat in data.get("categories", []):
        u_95 = cat.get("uncertainty_decimal", 0)
        u_1s = cat.get("uncertainty_1sigma", 0)
        if u_1s > 0:
            assert abs(u_95 - 2.0 * u_1s) < 1e-10, (
                f"Category '{cat['category']}': 95% CI ({u_95}) should be 2 × 1σ ({u_1s})"
            )
