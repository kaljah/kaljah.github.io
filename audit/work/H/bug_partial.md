# BUG-XXX — SBTi progress KPI uses the current, incomplete year (and any future year) as the "current" year, so the dashboard reports ~95-99% reduction and ON TRACK

**Status:** Confirmed
**Severity:** High
**Category:** SBTi
**Discovered by:** Agent H (SBTi Auditor)

## Location
`new/server/routes/dashboard.py` `get_sbti_trajectory()` lines ~2816-2843 (`candidate_years` / `latest_actual_year` / `current_actual` / `reduction_achieved_pct` / `on_track`). Consumed by `new/client/src/pages/SbtiDashboard.jsx` KPI cards "Current Year Target", "Pathway Status" (ON TRACK / BEHIND TARGET, "Reduction: X% vs Baseline").

## Reproduction
1. `python C:/Users/samsung/Desktop/H2/audit/repro/<BUG-ID>.py` (own db copy; controlled data).
2. Scenario: base year 2020 = 1000 t (S1+S2+S3), full year 2023 = 950 t, target 4.2 %/yr linear 2020→2030.
3. Add a single Verified January record of the current year (2026) = 50 t.
4. `GET /api/dashboard/sbti-trajectory`.

## Input
Target `{base_year:2020, base_year_emissions:1000, target_year:2030, reduction_rate_pct:4.2}`; Verified rows as above.

## Expected
Progress must be measured on the latest complete reporting year (2023): actual 950 t vs linear target 1000×(1−0.042×3) = 874 t → reduction 5.0 %, **BEHIND TARGET**. The current year should at most be shown as year-to-date, never compared to a full-year target.

## Actual
`latest_actual_year=2026, current_actual=50, current_target=748, reduction_achieved_pct=95.0, on_track=true` → page shows "ON TRACK — Reduction: 95% vs Baseline".
On the unmodified snapshot (admin): `latest_actual_year=2026`, `current_actual=10,261.46 t` (2026 data only through Sept; 2025 full year = 1,954,194 t), `reduction_achieved_pct=98.63`, `on_track=true` although the full year 2025 (1.95 Mt) is 2.7× above its 718,500 t target.

## Evidence
`candidate_years = [y for y in range(base_year, end_year+1) if y in actuals]; latest_actual_year = max(candidate_years)` — no check that the year is complete or ≤ the last closed reporting year. Snapshot DB: 2026 Verified Scope 1 = 9,992 t across months 1–10 (month 10 is in the future), 2025 Verified = 1,636,882 t.

## Root Cause
"Current" year is simply the max year having any Verified row within [base_year, target_year]. Partial current-year data, or mis-dated future-year data (the snapshot has Verified rows in 2099 and in 2026-10), becomes the progress year and is compared to a full-year target.

## Impact
The headline SBTi status and "% reduction vs baseline" on the SBTi page (and any consumer of `on_track`/`reduction_achieved_pct`) is grossly overstated for most of every calendar year; a company that is off-track is shown as ON TRACK. The CSV export marks the current year "Achieved".

## Affected Components
`/api/dashboard/sbti-trajectory` summary fields; `SbtiDashboard.jsx` KPI cards, milestone table row for the current year, CSV export status; `DashboardEnhanced.jsx` SBTi banner (actual line drops to near zero in current year).

## Recommended Fix
Select the progress year as the latest year ≤ (current_year − 1) (or the last year flagged as closed/complete, e.g. 12 months of data), ignore years > current year, and label the current year as YTD / exclude it from on-track evaluation.
