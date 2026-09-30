# BUG-XXX — SBTi dashboard shows "ON TRACK — Reduction: 100% vs Baseline" when there is no verified data at all in the target window

**Status:** Confirmed
**Severity:** Medium
**Category:** SBTi
**Discovered by:** Agent H (SBTi Auditor)

## Location
`new/server/routes/dashboard.py` `get_sbti_trajectory()`: `latest_actual_year = max(candidate_years, default=base_year)`, `current_actual = actuals.get(latest_actual_year, actuals.get(current_year, 0.0))`, `reduction_achieved_pct = (base - current_actual)/base*100`, `on_track = current_actual <= current_target if current_actual > 0 else True`. UI `SbtiDashboard.jsx` "Pathway Status" card (`isOnTrack = sbtiData?.on_track ?? true`).

## Reproduction
1. `python C:/Users/samsung/Desktop/H2/audit/repro/<BUG-ID>.py`
2. Save a target with base year 2024 (baseline 1000 t) where no Verified S1/S2/S3 rows exist for 2024-2030 (same happens for a regional user/facility with no data, or scope=s1_s2 with only S3 data).
3. `GET /api/dashboard/sbti-trajectory`.

## Input
`{base_year:2024, base_year_emissions:1000, target_year:2030, reduction_rate_pct:4.2}`, no actuals in window.

## Expected
Progress not evaluable: reduction % null / "No data", status neither ON TRACK nor BEHIND.

## Actual
`reduction_achieved_pct=100.0, on_track=true, current_actual=0.0` → green "ON TRACK", "Reduction: 100% vs Baseline". Also reproduced with `?facility_id=4` on a facility without data.

## Evidence
See code above: missing data is coerced to 0 t, which the formula turns into a 100 % reduction, and `on_track` is hard-coded `True` when actual is 0.

## Root Cause
Absence of data is represented as 0 emissions and treated as success instead of "not available".

## Impact
A newly configured target (base year = current year before data is verified), or any user whose region has no verified data, sees a false 100 % reduction / ON TRACK headline.

## Affected Components
`/api/dashboard/sbti-trajectory` summary; `SbtiDashboard.jsx` KPI cards.

## Recommended Fix
If no candidate year with data exists (or actual is 0 because no rows exist), return `current_actual=null, reduction_achieved_pct=null, on_track=null`, and render "No data" in the UI.
