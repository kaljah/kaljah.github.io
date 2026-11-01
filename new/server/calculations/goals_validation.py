"""
Emission Goals Validation
Validates corporate emission reduction pathways:
1. Non-increasing pathway over time (monotonic reduction) vs base year baseline.
2. Plausibility / scale consistency against verified corporate inventory.
"""
from typing import List, Dict, Any


def validate_goal_trajectory(
    goals: List[Dict[str, Any]],
    base_year: int = 2024,
    base_year_emissions: float = 0.0,
    annual_inventory_baseline: float = 0.0,
    cumulative_scope1: float = 0.0,
) -> Dict[int, List[str]]:
    """
    Given a list of goals [{'year': int, 'target_amount': float}, ...],
    evaluates trajectory monotonicity and scale consistency.
    Returns a dict mapping year -> list of warning strings.
    """
    warnings_by_year: Dict[int, List[str]] = {}
    if not goals:
        return warnings_by_year

    sorted_goals = sorted(goals, key=lambda g: int(g["year"]))

    prev_target = None
    prev_year = None

    for g in sorted_goals:
        yr = int(g["year"])
        target = float(g.get("target_amount") or 0.0)
        yr_warnings = []

        # 1. Comparison against base year baseline
        if base_year and yr > base_year and base_year_emissions > 0:
            if target > base_year_emissions:
                yr_warnings.append(
                    f"Target for {yr} ({target:,.0f} tCO2e) exceeds base year ({base_year}) emissions ({base_year_emissions:,.0f} tCO2e). Reduction pathways must not exceed the baseline."
                )

        # 2. Monotonicity check against previous target year
        if prev_target is not None and prev_year is not None:
            if target > prev_target:
                yr_warnings.append(
                    f"Target for {yr} ({target:,.0f} tCO2e) is higher than target for {prev_year} ({prev_target:,.0f} tCO2e). Trajectory should be non-increasing over time."
                )

        # 3. Consistency with annual and cumulative inventory baseline
        if annual_inventory_baseline > 0:
            if target < 0.10 * annual_inventory_baseline:
                msg = f"Target for {yr} ({target:,.0f} tCO2e) is suspiciously low compared to annual inventory (~{annual_inventory_baseline:,.0f} tCO2e)"
                if cumulative_scope1 > 0:
                    msg += f" and cumulative Scope 1 (~{cumulative_scope1:,.0f} tCO2e)"
                msg += ". Verify if target was entered in kilotonnes (kt) or represents only a single facility."
                yr_warnings.append(msg)
            elif target > 5.0 * annual_inventory_baseline:
                yr_warnings.append(
                    f"Target for {yr} ({target:,.0f} tCO2e) is more than 5x annual inventory (~{annual_inventory_baseline:,.0f} tCO2e). Verify scale."
                )

        if yr_warnings:
            warnings_by_year[yr] = yr_warnings

        prev_target = target
        prev_year = yr

    return warnings_by_year
