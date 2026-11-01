"""Regression tests for Part 1.8: Goals and base year validation.

Requirements:
- Targets: 2026=150,000; 2033=410,000; 2034=315,000; 2035=390,000 tCO2e.
- Warn on non-monotonic pathway vs base year.
- Warn on targets wildly inconsistent with inventory (150k vs about 12M t Scope 1).
- Warn, do not hard-block unless invalid.
"""
import pytest
from tests.audit_helpers import make_user, login
from calculations.goals_validation import validate_goal_trajectory


def test_part1_goals_trajectory_validation():
    # Targets identified in prompt
    problematic_goals = [
        {"year": 2026, "target_amount": 150000.0},
        {"year": 2033, "target_amount": 410000.0},
        {"year": 2034, "target_amount": 315000.0},
        {"year": 2035, "target_amount": 390000.0},
    ]
    # Annual baseline ~2.3M tCO2e, cumulative scope 1 ~12.1M tCO2e
    warnings = validate_goal_trajectory(
        problematic_goals,
        base_year=2024,
        base_year_emissions=2669170.59,
        annual_inventory_baseline=2308211.59,
        cumulative_scope1=12128166.47,
    )

    # 1. 2026 is wildly inconsistent with ~2.3M annual and ~12M cumulative Scope 1
    assert 2026 in warnings
    assert any("suspiciously low" in w or "inconsistent" in w for w in warnings[2026])
    assert any("12,128,166" in w or "Scope 1" in w for w in warnings[2026])

    # 2. 2033 is higher than 2026 -> non-monotonic
    assert 2033 in warnings
    assert any("higher than target for 2026" in w for w in warnings[2033])

    # 3. 2035 is higher than 2034 -> non-monotonic
    assert 2035 in warnings
    assert any("higher than target for 2034" in w for w in warnings[2035])


def test_part1_goals_api_warns_and_does_not_block(client, app):
    with app.app_context():
        admin = make_user("admin")
        login(client, admin)

        # GET /api/goals returns goals with their warnings
        resp = client.get("/api/goals")
        assert resp.status_code == 200
        goals_data = resp.get_json()
        assert isinstance(goals_data, list)

        # POST invalid goal is hard-blocked (400)
        invalid_resp = client.post("/api/goals", json={"year": 2028, "target_amount": -500})
        assert invalid_resp.status_code == 400

        # POST non-monotonic goal is saved (200) with warnings attached
        # Base year 2024 has ~2.3M. Target 2030=100k, then 2031=500k (higher -> non-monotonic)
        res1 = client.post("/api/goals", json={"year": 2030, "target_amount": 100000})
        assert res1.status_code == 200
        res2 = client.post("/api/goals", json={"year": 2031, "target_amount": 500000})
        assert res2.status_code == 200
        data2 = res2.get_json()
        assert data2["year"] == 2031
        assert "warnings" in data2
        assert any("higher than target for 2030" in w for w in data2["warnings"])
