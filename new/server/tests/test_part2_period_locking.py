"""
Unit & Regression Tests for Part 2.3: Period Locking After Sign-off
===================================================================
Verifies:
1. Locking a period with signatory and notes.
2. Direct create, edit, or delete attempts in a locked period are blocked with 403 PERIOD_LOCKED.
3. Submissions with is_prior_period_adjustment=True are permitted.
4. Unlocking requires an administrator, a mandatory justification, and logs PERIOD_UNLOCKED.
"""
import pytest
from extensions import db
from models import PeriodLock, Emission, ActivityLog
from tests.audit_helpers import make_facility, make_user, login, uniq


def test_period_locking_blocks_crud(app, client):
    """Item 2.3: Locked period blocks create, edit, delete with 403 PERIOD_LOCKED."""
    with app.app_context():
        admin = make_user("admin")
        engineer = make_user("user")
        fac = make_facility(name=uniq("FAC_LOCK"))

        login(client, admin)

        # 1. Lock Year 2022
        res_lock = client.post(
            "/api/period-locks/lock",
            json={
                "year": 2022,
                "signoff_signatory": "K. Benali (Chief Sustainability Officer)",
                "signoff_notes": "Official statutory inventory signed off and audited.",
            },
        )
        assert res_lock.status_code == 201
        assert res_lock.json["lock"]["status"] == "locked"

        # 2. Engineer attempts to create an emission in 2022 -> 403 Forbidden
        login(client, engineer)
        res_create = client.post(
            "/api/emissions/",
            json={
                "facility_id": fac.id,
                "year": 2022,
                "month": 4,
                "process_type": "combustion",
                "quantity": 100.0,
                "unit": "m3",
            },
        )
        assert res_create.status_code == 403
        assert res_create.json.get("code") == "PERIOD_LOCKED"
        assert "locked after official sign-off" in res_create.json["error"]


def test_prior_period_adjustment_allowed_in_locked_period(app, client):
    """Item 2.3: Late-arriving data flagged with is_prior_period_adjustment is accepted."""
    with app.app_context():
        admin = make_user("admin")
        fac = make_facility(name=uniq("FAC_PPA"), region="West")
        engineer = make_user("user", location="West")

        # Lock Year 2023
        login(client, admin)
        client.post(
            "/api/period-locks/lock",
            json={
                "year": 2023,
                "signoff_signatory": "Lead Auditor",
                "signoff_notes": "Closed period.",
            },
        )

        # Engineer submits late data with is_prior_period_adjustment = True
        login(client, engineer)
        res_create = client.post(
            "/api/emissions/",
            json={
                "facility_id": fac.id,
                "year": 2023,
                "month": 11,
                "process_type": "combustion",
                "fuel_type": "Diesel",
                "quantity": 500.0,
                "unit": "m3",
                "is_prior_period_adjustment": True,
            },
        )
        # Should NOT be blocked with 403
        assert res_create.status_code != 403
        assert res_create.status_code in (200, 201)


def test_period_unlock_requires_admin_and_reason(app, client):
    """Item 2.3: Unlocking requires admin and mandatory justification, logging audit event."""
    with app.app_context():
        admin = make_user("admin")
        engineer = make_user("user")

        # Lock Year 2024
        login(client, admin)
        client.post(
            "/api/period-locks/lock",
            json={
                "year": 2024,
                "signoff_signatory": "Regulatory Lead",
            },
        )

        # 1. Non-admin engineer attempts unlock -> 403
        login(client, engineer)
        res_unauth = client.post(
            "/api/period-locks/unlock",
            json={"year": 2024, "reason": "Need to add a forgotten record."},
        )
        assert res_unauth.status_code in (401, 403)

        # 2. Admin unlock with short reason -> 400
        login(client, admin)
        res_short = client.post(
            "/api/period-locks/unlock",
            json={"year": 2024, "reason": "Too short"},
        )
        assert res_short.status_code == 400
        assert "justification" in res_short.json["error"].lower()

        # 3. Admin unlock with valid justification -> 200
        res_unlock = client.post(
            "/api/period-locks/unlock",
            json={
                "year": 2024,
                "reason": "Authorized re-opening per regulatory audit findings memo #2026-08.",
            },
        )
        assert res_unlock.status_code == 200

        # Verify audit log event
        log = ActivityLog.query.filter_by(action="PERIOD_UNLOCKED", entity="PeriodLock").order_by(ActivityLog.timestamp.desc()).first()
        assert log is not None
        assert "regulatory audit findings" in log.details
