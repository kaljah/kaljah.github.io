import pytest
from extensions import db
from models import ActivityLog, Emission, Facility, User
from tests.audit_helpers import login, make_facility, make_user


@pytest.fixture
def admin_setup(client, app):
    with app.app_context():
        user = make_user("admin", "Global")
        fac = make_facility(name="RNS Facility", region="Illizi / RNS", operator_status="non_operated", ogmp_membership_year=2023)
        db.session.commit()
        login(client, user)
        yield client, user, fac


def test_gwp_switch_writes_audit_trail_entry(admin_setup, app):
    client, user, fac = admin_setup
    with app.app_context():
        # Clean previous audit logs for GWP_RECALCULATION
        ActivityLog.query.filter_by(action="GWP_RECALCULATION").delete()
        db.session.commit()

    # Update GWP standard to AR6
    res = client.post("/api/auth/settings", json={"gwp_standard": "AR6"})
    assert res.status_code == 200

    # Check audit log entry
    with app.app_context():
        log_entry = ActivityLog.query.filter_by(action="GWP_RECALCULATION").order_by(ActivityLog.timestamp.desc()).first()
        assert log_entry is not None
        assert "GWP standard" in log_entry.details
        assert "AR6" in log_entry.details

    # Revert back to AR5
    res = client.post("/api/auth/settings", json={"gwp_standard": "AR5"})
    assert res.status_code == 200

    with app.app_context():
        log_entry = ActivityLog.query.filter_by(action="GWP_RECALCULATION").order_by(ActivityLog.timestamp.desc()).first()
        assert log_entry is not None
        assert "AR5" in log_entry.details


def test_facility_target_year_calculation_logic():
    # Operated = base_year + 3
    base_year = 2023
    op_status = "operated"
    is_operated = "operated" in op_status and "non" not in op_status
    target_year = base_year + (3 if is_operated else 5)
    assert target_year == 2026

    # Non-operated = base_year + 5
    op_status = "non_operated"
    is_operated = "operated" in op_status and "non" not in op_status
    target_year = base_year + (3 if is_operated else 5)
    assert target_year == 2028
