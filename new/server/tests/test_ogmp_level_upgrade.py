"""POST /api/data/ogmp/level-upgrade read facility_id, source, target date and justification from
nowhere (they were dropped when the level parsing was guarded), so every call failed with a 500."""
import pytest

from extensions import db
from models import LevelUpgradeLog
from tests.audit_helpers import login, make_facility, make_user


@pytest.fixture
def ctx(app):
    with app.app_context():
        yield


def test_level_upgrade_is_recorded(app, ctx):
    fac = make_facility(region="West")
    with app.test_client() as c:
        login(c, make_user("admin"))
        r = c.post("/api/data/ogmp/level-upgrade", json={
            "facility_id": fac.id, "old_level": 3, "new_level": 4, "source_type_code": "FLARE",
            "target_date": "2027-06", "justification": "site measurement campaign",
        })
    assert r.status_code in (200, 201), r.get_data(as_text=True)
    row = LevelUpgradeLog.query.filter_by(facility_id=fac.id).one()
    assert (row.old_level, row.new_level, row.source_type_code, row.target_date, row.justification) == (
        3, 4, "FLARE", "2027-06", "site measurement campaign")


def test_level_upgrade_needs_a_facility(app, ctx):
    with app.test_client() as c:
        login(c, make_user("admin"))
        assert c.post("/api/data/ogmp/level-upgrade", json={"new_level": 4}).status_code == 400
