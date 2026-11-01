import pytest
from tests.audit_helpers import make_user, login
from calculations.goals_validation import validate_goal_trajectory


def test_goal_trajectory_validation_unit():
    """Item 1.8: Unit test for non-monotonic and baseline inconsistency warnings."""
    # The exact dataset called out in user prompt:
    # Targets: 2026 = 150,000; 2033 = 410,000; 2034 = 315,000; 2035 = 390,000
    problematic_goals = [
        {"year": 2026, "target_amount": 150000.0},
        {"year": 2033, "target_amount": 410000.0},
        {"year": 2034, "target_amount": 315000.0},
        {"year": 2035, "target_amount": 390000.0},
    ]
    # Annual baseline ~2.3M tCO2e
    warnings = validate_goal_trajectory(
        problematic_goals,
        base_year=2024,
        base_year_emissions=2308212.0,
        annual_inventory_baseline=2308212.0,
    )

    # 1. 2026 target is suspiciously low (<10% of annual inventory)
    assert 2026 in warnings
    assert any("suspiciously low" in w or "inconsistent" in w for w in warnings[2026])

    # 2. 2033 target (410k) is higher than 2026 target (150k) -> non-monotonic
    assert 2033 in warnings
    assert any("higher than target for 2026" in w for w in warnings[2033])

    # 3. 2035 target (390k) is higher than 2034 target (315k) -> non-monotonic
    assert 2035 in warnings
    assert any("higher than target for 2034" in w for w in warnings[2035])

    # 4. Valid monotonic pathway generates no warnings
    valid_goals = [
        {"year": 2026, "target_amount": 2200000.0},
        {"year": 2030, "target_amount": 1800000.0},
        {"year": 2035, "target_amount": 1400000.0},
    ]
    valid_warnings = validate_goal_trajectory(
        valid_goals,
        base_year=2024,
        base_year_emissions=2308212.0,
        annual_inventory_baseline=2308212.0,
    )
    assert len(valid_warnings) == 0


def test_goals_api_returns_warnings_without_hard_blocking(client, app):
    """Item 1.8: API warns on non-monotonic/suspicious targets without hard-blocking."""
    with app.app_context():
        admin = make_user("admin")
        login(client, admin)

        # GET existing goals includes warnings
        get_resp = client.get("/api/goals")
        assert get_resp.status_code == 200
        goals_data = get_resp.get_json()
        assert isinstance(goals_data, list)

        # POST invalid target is hard-blocked with 400
        bad_resp = client.post("/api/goals", json={"year": 2030, "target_amount": -100})
        assert bad_resp.status_code == 400

        # POST initial goal for 2026
        client.post("/api/goals", json={"year": 2026, "target_amount": 150000})

        # POST non-monotonic target (2027 target 300000 > 2026 target 150000) saves successfully (200) with warnings attached
        warn_resp = client.post("/api/goals", json={"year": 2027, "target_amount": 300000})
        assert warn_resp.status_code == 200
        data = warn_resp.get_json()
        assert data["year"] == 2027
        assert data["target_amount"] == 300000.0
        assert "warnings" in data
        assert len(data["warnings"]) > 0
        assert any("higher than target for 2026" in w for w in data["warnings"])
