"""Sign-in and forgot-password require the CSRF token (readiness plan C4, HR-07).

They were exempt for the former cross-site GitHub Pages frontend; the app and the API now share
one address. The test suite turns CSRF off (conftest), so these tests switch it back on.
"""
import sys

import pytest
from flask import g, has_app_context

from tests.audit_helpers import make_user


@pytest.fixture
def csrf_on(app):
    app.config["WTF_CSRF_ENABLED"] = True
    try:
        yield
    finally:
        app.config["WTF_CSRF_ENABLED"] = False


def _token(client):
    # The suite keeps an app context open across tests, and Flask-WTF caches the token on `g`
    # for the life of a context: drop it so the token is signed for this client's session.
    if has_app_context():
        g.pop("csrf_token", None)
    return client.get("/api/csrf-token").get_json()["csrf_token"]


@pytest.mark.parametrize("url", ["/api/auth/login", "/api/auth/forgot-password"])
def test_missing_csrf_token_is_refused(app, csrf_on, url):
    with app.test_client() as c:
        r = c.post(url, json={"email": "nobody@example.com", "password": "x"})
        assert r.status_code == 400
        assert "csrf" in r.get_data(as_text=True).lower()


def test_sign_in_with_token_then_fresh_token_for_writes(app, csrf_on):
    with app.app_context():
        email = make_user("admin").email
    with app.test_client() as c:
        r = c.post("/api/auth/login", json={"email": email, "password": "AuditPass!2026"},
                   headers={"X-CSRFToken": _token(c)})
        assert r.status_code == 200, r.get_data(as_text=True)
        # sign-in starts a new session: the client fetches a new token, as src/context/AuthContext does
        r = c.put("/api/auth/settings", json={"theme": "light"}, headers={"X-CSRFToken": _token(c)})
        assert r.status_code == 200, r.get_data(as_text=True)


def test_forgot_password_with_token(app, csrf_on):
    with app.test_client() as c:
        r = c.post("/api/auth/forgot-password", json={"email": "nobody@example.com"},
                   headers={"X-CSRFToken": _token(c)})
        assert r.status_code == 200, r.get_data(as_text=True)


@pytest.mark.parametrize("argv,expected", [
    (["flask", "db", "upgrade"], True),
    (["flask", "--app", "app", "db", "upgrade"], True),
    (["flask", "-A", "app", "db", "upgrade"], True),
    (["flask", "--app=app", "--debug", "db", "current"], True),
    (["flask", "run"], False),
    (["gunicorn", "app:app"], False),
    (["app.py"], False),
])
def test_schema_cli_detection(monkeypatch, argv, expected):
    import app as app_module

    monkeypatch.setattr(sys, "argv", argv)
    assert app_module._is_schema_cli() is expected
