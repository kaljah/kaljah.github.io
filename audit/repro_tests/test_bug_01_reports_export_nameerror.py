"""
Verification Test: BUG-01 / AS-01 (Fixed)
Verify symbols are imported in new/server/routes/reports_export.py and GET /api/reports/export succeeds.
"""

import sys
import pytest

sys.path.insert(0, "new/server")

def test_reports_export_name_errors():
    import routes.reports_export as mod

    # Verify required symbols exist in module globals
    required_symbols = ["db", "or_", "func", "Scope2Emission", "Scope3Emission"]
    for sym in required_symbols:
        assert hasattr(mod, sym), f"Expected '{sym}' to be imported in routes.reports_export"

def test_reports_export_runtime_500():
    from app import app
    from models import db, User

    with app.test_client() as client:
        with app.app_context():
            # Create a mock authenticated user session
            user = User.query.filter_by(role="admin").first()
            if not user:
                user = User(
                    fullName="Audit Admin",
                    orgName="Audit Org",
                    email="audit_admin@example.com",
                    role="admin",
                    sector="Oil & Gas",
                    department="Audit",
                    status="active"
                )
                user.set_password("AuditPassword123!")
                db.session.add(user)
                db.session.commit()

            with client.session_transaction() as sess:
                sess["user_id"] = user.id
                sess["sv"] = user.session_version or 0

            # Access GET /api/reports/export with default status
            response = client.get("/api/reports/export")
            # Should succeed with HTTP 200 (PDF stream), not fail with 500 NameError
            assert response.status_code == 200, f"Expected HTTP 200, got {response.status_code}"
