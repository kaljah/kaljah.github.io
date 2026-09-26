# BUG-XXX — SBTi "Scope 1+2 (Operational)" view compares Scope 1+2 actuals to the Scope 1+2+3 baseline and target line (inflated reduction %, false ON TRACK)

**Status:** Confirmed
**Severity:** High
**Category:** SBTi
**Discovered by:** Agent H (SBTi Auditor)

## Location
`new/server/routes/dashboard.py` `get_sbti_trajectory()` (~2764-2843): `sbti_target`, `current_target`, `reduction_achieved_pct`, `on_track` always use `target.base_year_emissions`, whatever `scope` is. `new/server/routes/managedata.py` `manage_sbti()` GET builds the auto-fill baseline as S1+S2+S3; `SbtiTarget` (models.py:583) has no scope-coverage field. UI: `SbtiDashboard.jsx` scope toggle "Scope 1+2 (Operational)".

## Reproduction
1. `python C:/Users/samsung/Desktop/H2/audit/repro/<BUG-ID>.py`
2. Base year 2020 Verified: S1 700, S2 100, S3 200 (total 1000; S1+S2 800). 2023: S1 650, S2 100, S3 200.
3. Save target via the page's Auto-Fill (1000 t = S1+S2+S3), 4.2 %/yr, 2030.
4. `GET /api/dashboard/sbti-trajectory?scope=s1_s2` (the page's "Scope 1+2" button) and `?scope=s3`.

## Input
Target `{base_year:2020, base_year_emissions:1000, target_year:2030, reduction_rate_pct:4.2}`.

## Expected
Scope 1+2 view: baseline 800 t, 2023 target 800×(1−0.042×3)=699.2 t, actual 750 t → reduction 6.25 %, BEHIND TARGET. S3 view: baseline 200, target 174.8, actual 200 → 0 %, behind.

## Actual
s1_s2: `current_target=874, reduction_achieved_pct=25.0, on_track=true`. s3: `current_target=874, reduction_achieved_pct=80.0, on_track=true`. The chart's "Corporate Target" line and the milestone table "SBTi Target / Variance / Compliance Status" columns likewise compare the S1+S2 actual against the all-scope pathway, so every year looks "Achieved".

## Evidence
Code: `reduction_achieved_pct = (target.base_year_emissions - current_actual)/target.base_year_emissions*100` with `current_actual` = S1+S2 when scope=s1_s2. Baseline auto-fill (`managedata.py` GET) sums S1+S2+S3. The reduction shown is simply the Scope 3 share of the baseline plus the real reduction.

## Root Cause
A single all-scope baseline/target is reused for scope-subset actuals; no per-scope baseline (the per-scope base-year totals are available from the same queries at `base_year`).

## Impact
Every organisation with Scope 3 in its baseline sees an overstated operational reduction and a false ON TRACK when toggling to Scope 1+2. SBTi requires separate S1+2 and S3 targets, so this view is the one users would rely on for the S1+2 near-term target.

## Affected Components
`/api/dashboard/sbti-trajectory?scope=s1_s2|s3`; `SbtiDashboard.jsx` KPI cards, trajectory chart, milestone table, CSV export (Status column).

## Recommended Fix
Store scope coverage with the target (or per-scope baselines) and, for scope subsets, compute baseline = scope-subset base-year actual (or the stored per-scope baseline) and derive the target line / reduction % / on_track from it.
