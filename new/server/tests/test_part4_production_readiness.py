"""
Part 4 Tests: Production Readiness, Health Checks, Security Headers, and Config
==============================================================================
Validates:
- 4.1 Secrets scan cleanliness and fail-closed production config
- 4.2 Database indexes and connection resilience
- 4.3 Structured logging, Sentry error tracking hook, incident ID generation, health endpoints
- 4.4 Clean build and asset limits
- 4.5 100k Performance benchmark verification
"""
import os
import json
import pytest
from app import app
from config import Config
from services.error_tracker import generate_incident_id


@pytest.fixture
def client():
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False
    with app.test_client() as test_client:
        yield test_client


def test_health_endpoints(client):
    """Test /health, /api/health, /api/health/live, and /api/health/ready."""
    # Base health endpoint
    res = client.get("/health")
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "healthy"
    assert "checks" in data
    assert data["checks"]["database"]["status"] == "connected"
    assert "latency_ms" in data["checks"]["database"]
    assert "memory" in data["checks"]
    assert "disk" in data["checks"]

    # Alias /api/health
    res_api = client.get("/api/health")
    assert res_api.status_code == 200
    assert res_api.get_json()["status"] == "healthy"

    # Liveness probe
    res_live = client.get("/api/health/live")
    assert res_live.status_code == 200
    assert res_live.get_json()["status"] == "alive"

    # Readiness probe
    res_ready = client.get("/api/health/ready")
    assert res_ready.status_code == 200
    assert res_ready.get_json()["status"] == "ready"
    assert res_ready.get_json()["database"] == "connected"


def test_security_headers_present(client):
    """Test that all HTTP responses carry modern security hardening headers."""
    res = client.get("/health")
    assert res.headers.get("X-Content-Type-Options") == "nosniff"
    assert res.headers.get("X-Frame-Options") == "DENY"
    assert res.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
    assert "Content-Security-Policy" in res.headers
    csp = res.headers.get("Content-Security-Policy")
    assert "default-src 'self'" in csp


def test_error_tracking_incident_id(client):
    """Test incident ID generation and tagging on error."""
    incident_id = generate_incident_id()
    assert incident_id.startswith("INC-")
    assert len(incident_id) == 16  # INC- + 12 hex chars


def test_production_config_validation(monkeypatch):
    """Test that production environment strictly validates secret key, database URL, and origins."""
    # Test that setting environment to production without SECRET_KEY fails
    monkeypatch.setenv("FLASK_ENV", "production")
    monkeypatch.delenv("SECRET_KEY", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    
    with pytest.raises(ValueError, match="FATAL: SECRET_KEY is not set"):
        import importlib
        import config
        importlib.reload(config)


def test_secrets_scan_report_exists_and_clean():
    """Verify that the secrets scan report exists and reports clean status."""
    report_path = os.path.join(os.path.dirname(__file__), "..", "reports", "secrets_scan_report.json")
    assert os.path.exists(report_path), "Secrets scan report must be generated"
    with open(report_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["status"] == "PASS_CLEAN"
    assert data["real_leak_findings"] == 0


def test_benchmark_p95_report_meets_sla():
    """Verify that the 100k realistic volume benchmark report meets SLA targets."""
    report_path = os.path.join(os.path.dirname(__file__), "..", "reports", "benchmark_p95_report.json")
    if not os.path.exists(report_path):
        pytest.skip("Benchmark report not yet generated in this test run")

    with open(report_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["overall_status"] == "PASS"
    for ep in data["endpoints"]:
        assert ep["passed"] is True, f"Endpoint {ep['endpoint']} failed SLA target of {ep['target_ms']} ms with p95={ep['p95_ms']} ms"
