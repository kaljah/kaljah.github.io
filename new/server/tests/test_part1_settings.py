"""Item 1.13: Settings Logic and Base Year Rules
==============================================
Verifies:
1. Target year formula: base_year + 3 (operated) or + 5 (non-operated).
2. Changing GWP standard logs a METHODOLOGY_CHANGE audit event.
"""
import pytest
from extensions import db
from models import ActivityLog, Facility
from tests.audit_helpers import make_facility, make_user, login, uniq

def test_settings_target_year_calculation_rule(app, client):
    """Item 1.13: Target year formula = base + 3 (operated) or + 5 (non-operated)."""
    with app.app_context():
        admin = make_user("admin")
        login(client, admin)

        f_op = make_facility(
            name=uniq("FAC_OP"),
            region="Berkine",
            ogmp_membership_year=2023,
            operator_status="operated",
        )
        f_non = make_facility(
            name=uniq("FAC_NONOP"),
            region="Illizi",
            ogmp_membership_year=2023,
            operator_status="non_operated",
        )

        res = client.get('/api/facilities')
        assert res.status_code == 200
        facilities = res.json

        fac_op_res = next((f for f in facilities if f["id"] == f_op.id), None)
        assert fac_op_res is not None
        assert fac_op_res.get('target_year') == 2026  # 2023 + 3

        fac_non_res = next((f for f in facilities if f["id"] == f_non.id), None)
        assert fac_non_res is not None
        assert fac_non_res.get('target_year') == 2028  # 2023 + 5

def test_gwp_standard_change_audit_event(app, client):
    """Item 1.13: Changing GWP standard logs a METHODOLOGY_CHANGE audit event."""
    with app.app_context():
        admin = make_user("admin")
        login(client, admin)

        # Change GWP standard to AR6
        res = client.post('/api/auth/settings', json={'gwp_standard': 'AR6'})
        assert res.status_code == 200

        # Check that an audit log was created with action METHODOLOGY_CHANGE
        log = ActivityLog.query.filter_by(action='METHODOLOGY_CHANGE', entity='SystemSetting').order_by(ActivityLog.timestamp.desc()).first()
        assert log is not None
        assert "IPCC GWP standard" in log.details

        # Revert back to AR5 default
        res2 = client.post('/api/auth/settings', json={'gwp_standard': 'AR5'})
        assert res2.status_code == 200
