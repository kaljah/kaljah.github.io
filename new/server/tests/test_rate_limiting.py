import pytest
from app import app as flask_app
from extensions import db, limiter


@pytest.fixture
def rate_limit_client():
    flask_app.config.update({
        "TESTING": True,
        "WTF_CSRF_ENABLED": False,
        "SECRET_KEY": "test-rate-limit-key",
        "RATELIMIT_ENABLED": True,
        "RATELIMIT_STORAGE_URI": "memory://",
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
    })
    limiter.enabled = True
    with flask_app.app_context():
        db.create_all()
        yield flask_app.test_client()
    limiter.enabled = False



def test_login_rate_limit_exceeded(rate_limit_client):
    """Verify login endpoint rate limiting triggers after 20 attempts."""
    payload = {"email": "test_rl@example.com", "password": "WrongPassword123!"}
    for _ in range(20):
        rate_limit_client.post("/api/auth/login", json=payload)

    # 21st attempt should be rate limited (429)
    resp = rate_limit_client.post("/api/auth/login", json=payload)
    assert resp.status_code == 429
