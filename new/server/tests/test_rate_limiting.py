import pytest
from app import app as flask_app
from extensions import db, limiter


@pytest.fixture
def rate_limit_client():
    keys = ("TESTING", "WTF_CSRF_ENABLED", "SECRET_KEY", "RATELIMIT_ENABLED", "RATELIMIT_STORAGE_URI")
    prev = {k: flask_app.config.get(k) for k in keys}
    prev_lim = limiter.enabled
    flask_app.config.update({
        "TESTING": True,
        "WTF_CSRF_ENABLED": False,
        "SECRET_KEY": "test-rate-limit-key",
        "RATELIMIT_ENABLED": True,
        "RATELIMIT_STORAGE_URI": "memory://",
    })
    limiter.enabled = True
    try:
        with flask_app.app_context():
            db.create_all()
            yield flask_app.test_client()
    finally:
        try:
            limiter.reset()
        except Exception:
            pass
        limiter.enabled = prev_lim
        for k, v in prev.items():
            if v is None:
                flask_app.config.pop(k, None)
            else:
                flask_app.config[k] = v



def test_login_rate_limit_exceeded(rate_limit_client, monkeypatch):
    """Verify login endpoint rate limiting triggers after 20 attempts."""
    monkeypatch.setenv("LOGIN_RATE_LIMIT", "20 per 15 minutes")
    payload = {"email": "test_rl@example.com", "password": "WrongPassword123!"}
    for _ in range(20):
        rate_limit_client.post("/api/auth/login", json=payload)

    # 21st attempt should be rate limited (429)
    resp = rate_limit_client.post("/api/auth/login", json=payload)
    assert resp.status_code == 429
