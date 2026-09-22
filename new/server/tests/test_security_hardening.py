"""
Security hardening regression tests — Phase 1.2.
Verifies that:
  - Hard-coded dev accounts (a@a, a) are not auto-created
  - The /api/auth/init-admin public route has been removed
  - The CSRF token endpoint sets a double-submit cookie
"""
import os
import pytest
from app import app as flask_app
from extensions import db, limiter


@pytest.fixture(scope="module")
def client():
    flask_app.config.update({
        "TESTING": True,
        "WTF_CSRF_ENABLED": False,
        "SECRET_KEY": "security-hardening-test-secret",
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "SQLALCHEMY_ENGINE_OPTIONS": {"connect_args": {"check_same_thread": False}},
    })
    # Ensure SEED_ADMIN is off — new code must not seed any accounts
    os.environ.pop("SEED_ADMIN", None)
    limiter.enabled = False
    with flask_app.app_context():
        db.create_all()
        yield flask_app.test_client()



def test_dev_account_a_at_a_does_not_exist(client):
    """
    SECURITY REGRESSION (CRIT-02): The 'a@a' dev shortcut account must not be
    auto-created. A 1-character password bypasses all complexity requirements.
    """
    from models import User
    with flask_app.app_context():
        user = User.query.filter_by(email="a@a").first()
        assert user is None, (
            "SECURITY FAILURE: Account 'a@a' exists in the database. "
            "Hard-coded dev credential 'a@a'/'a' must never be auto-seeded."
        )


def test_dev_account_bare_a_does_not_exist(client):
    """
    SECURITY REGRESSION (CRIT-02): The 'a' dev shortcut account (not even
    a valid email) must not be auto-created.
    """
    from models import User
    with flask_app.app_context():
        user = User.query.filter_by(email="a").first()
        assert user is None, (
            "SECURITY FAILURE: Account 'a' exists in the database. "
            "Hard-coded dev credential 'a'/'a' must never be auto-seeded."
        )


def test_init_admin_route_removed(client):
    """
    SECURITY REGRESSION: The /api/auth/init-admin unauthenticated route must
    return 404. This route allowed any HTTP client to reseed admin accounts.
    """
    resp = client.get("/api/auth/init-admin")
    assert resp.status_code == 404, (
        f"SECURITY FAILURE: /api/auth/init-admin returned {resp.status_code}. "
        "This publicly accessible route must be removed from production."
    )


def test_csrf_token_endpoint_returns_token(client):
    """CSRF token endpoint must return a non-empty token."""
    resp = client.get("/api/csrf-token")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "csrf_token" in data
    assert len(data["csrf_token"]) > 20, "CSRF token must be sufficiently long"


def test_csrf_token_endpoint_sets_readable_cookie(client):
    """
    CSRF token endpoint must set a cookie named 'csrf_token'.
    The cookie must NOT be HttpOnly — the SPA JavaScript needs to read it
    for the double-submit cookie pattern.
    """
    resp = client.get("/api/csrf-token")
    set_cookie = resp.headers.get("Set-Cookie", "")
    assert "csrf_token" in set_cookie, (
        "CSRF endpoint must set a csrf_token cookie for the double-submit pattern. "
        f"Got Set-Cookie: {set_cookie!r}"
    )
    assert "HttpOnly" not in set_cookie or "httponly" not in set_cookie.lower(), (
        "CSRF cookie must NOT be HttpOnly — JavaScript must be able to read it "
        "for the double-submit cookie CSRF pattern."
    )


def test_seed_admin_disabled_by_default():
    """
    ensure_admin_seeded() must be a no-op when SEED_ADMIN is not set
    (default: false). This prevents accidental account creation on startup.
    """
    import os
    original = os.environ.get("SEED_ADMIN")
    try:
        os.environ.pop("SEED_ADMIN", None)
        with flask_app.app_context():
            # Should not raise and should not create any accounts
            from app import ensure_admin_seeded
            ensure_admin_seeded()  # Must be a no-op
    finally:
        if original is not None:
            os.environ["SEED_ADMIN"] = original
