# BUG-XXX — SBTi target labelled "1.5°C" is not tied to its reduction rate (0.5 %/yr accepted and displayed as 1.5°C); arbitrary pathway strings and future base years accepted; main-dashboard banner hard-codes "SBTi 1.5°C Linear Target"

**Status:** Confirmed
**Severity:** Medium
**Category:** SBTi
**Discovered by:** Agent H (SBTi Auditor)

## Location
`new/server/routes/managedata.py` `manage_sbti()` POST validation (pathway_type is `str(...)` with no whitelist; rate range 0-25 independent of pathway; base_year allowed up to 2035 regardless of current year). `new/client/src/pages/SbtiDashboard.jsx` (rate input editable independently of the pathway buttons; header "SBTi Decarbonization Pathway (1.5C)"). `new/client/src/pages/DashboardEnhanced.jsx` ~1532: series `sbti_target` named "SBTi 1.5°C Linear Target" regardless of `pathway_type`/`reduction_rate_pct`.

## Reproduction
1. `python C:/Users/samsung/Desktop/H2/audit/repro/<BUG-ID>.py`
2. POST `{base_year:2020, base_year_emissions:1000, target_year:2030, reduction_rate_pct:0.5, pathway_type:"1.5C"}` → 201.
3. POST with `pathway_type:"foo"` → 201; with `base_year:2030,target_year:2031` (future base year, no data possible) → 201.
4. `GET /api/dashboard/sbti-trajectory` → `pathway_type "1.5C"`, `target_emissions_final 950`.

## Input
As above.

## Expected
SBTi 1.5°C linear absolute contraction requires ≥ 4.2 %/yr (WB2C ≥ 2.5 %/yr): a 2020→2030 1.5°C target must be ≤ 1000×(1−0.042×10) = 580 t. Pathway must be one of the supported values and consistent with the rate (or the label derived from the rate). Base year should not be in the future (SBTi requires the most recent year with verified data, ≥ 2015).

## Actual
All accepted; the page and the dashboard banner present a 5 % reduction over 10 years as a "1.5°C" pathway. The main-dashboard banner calls the corporate line "SBTi 1.5°C Linear Target" even for WB2C or custom rates.

## Evidence
Repro output: three `expected 400, actual 201` lines; `pathway shown '1.5C', target_emissions_final 950.0`.

## Root Cause
No cross-field validation between `pathway_type` and `reduction_rate_pct`; free-text pathway; hard-coded label in DashboardEnhanced.

## Impact
Misleading claim of 1.5°C alignment on the SBTi page, exports and executive dashboard.

## Affected Components
`/api/manage/sbti` POST; SbtiDashboard.jsx header/legend/CSV; DashboardEnhanced.jsx SBTi banner; ManageData.jsx SBTi tab (same POST).

## Recommended Fix
Whitelist pathway ∈ {1.5C, WB2C, custom}; enforce rate ≥ 4.2 for 1.5C and ≥ 2.5 for WB2C (or label "Custom"); reject base_year > current year; use `sbtiData.pathway_type`/rate in the dashboard banner label.
