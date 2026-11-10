"""
Verification of Remediation: BUG-09 / SEC-03
GET /api/tenant/config is protected by @login_required (returns 401 when unauthenticated).
GET /api/tenant/branding provides safe unauthenticated branding metadata for public login screens.
"""

import sys
sys.path.insert(0, "new/server")

def test_tenant_config_protected_and_branding_public():
    from app import app

    with app.test_client() as client:
        # 1. Unauthenticated /api/tenant/config must return 401 Unauthorized
        resp_config = client.get("/api/tenant/config")
        assert resp_config.status_code in (401, 302), f"Expected 401 for unauthenticated config, got {resp_config.status_code}"

        # 2. Unauthenticated /api/tenant/branding must return 200 OK with branding metadata
        resp_branding = client.get("/api/tenant/branding")
        assert resp_branding.status_code == 200
        branding = resp_branding.get_json()
        assert "organization_name" in branding
        assert "regulatory_framework" in branding
        # Sensitive operational fields must not be present in public branding
        assert "email_domain" not in branding
