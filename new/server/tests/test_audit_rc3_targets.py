"""RC-3 / RC-11 validation of SBTi targets and goals (BUG-034, BUG-039, BUG-059)."""
import datetime
import json

import pytest

from extensions import db
from tests.audit_helpers import login, make_user


@pytest.fixture
def admin_client(client, app):
    with app.app_context():
        login(client, make_user("admin", "Global"))
        yield client


BASE = {"base_year": 2020, "base_year_emissions": 1000, "target_year": 2030, "reduction_rate_pct": 4.2, "pathway_type": "1.5C"}


@pytest.mark.parametrize("override", [
    {"base_year_emissions": "NaN"}, {"reduction_rate_pct": "Infinity"}, {"base_year_emissions": -1},
    {"pathway_type": "banana"}, {"pathway_type": "1.5C", "reduction_rate_pct": 0.5},
    {"pathway_type": "WB2C", "reduction_rate_pct": 1.0}, {"base_year": 2099}, {"scope_coverage": "S3"},
])
def test_bug034_059_invalid_sbti_targets_rejected(admin_client, override):
    body = dict(BASE, **override)
    assert admin_client.post("/api/manage/sbti", json=body).status_code == 400


def test_bug059_valid_targets_accepted(admin_client):
    for extra in ({"pathway_type": "1.5C", "reduction_rate_pct": 4.2}, {"pathway_type": "WB2C", "reduction_rate_pct": 2.5},
                  {"pathway_type": "custom", "reduction_rate_pct": 0.5, "scope_coverage": "S1S2"}):
        assert admin_client.post("/api/manage/sbti", json=dict(BASE, **extra)).status_code == 201, extra


@pytest.mark.parametrize("body", [{"year": 2030, "target_amount": -5}, {"year": 1, "target_amount": 10},
                                  {"year": 2030, "target_amount": "NaN"}, {"year": 2030, "target_amount": 0},
                                  {"year": 2030.5, "target_amount": 10}])
def test_bug039_invalid_goals_rejected(admin_client, body):
    assert admin_client.post("/api/goals", json=body).status_code == 400


def test_bug039_dashboard_survives_legacy_nan_goal(admin_client):
    from models import Goal

    y = datetime.date.today().year
    g = Goal.query.filter_by(year=y).first() or Goal(year=y, target_amount=1.0)
    g.target_amount = float("nan")
    db.session.add(g)
    db.session.commit()
    r = admin_client.get(f"/api/dashboard/batch-all?year={y}")
    assert r.status_code == 200
    json.loads(r.get_data(as_text=True))
    db.session.delete(g)
    db.session.commit()
