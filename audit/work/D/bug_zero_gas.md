# BUG-XXX — Facilities with CH4 emissions but no gas production get methane_loss_rate_pct = 0 and ogmp_target_status "Compliant"

**Status:** Confirmed
**Severity:** Low
**Category:** Methane
**Discovered by:** Agent D (Methane Auditor)

## Location
`new/server/routes/dashboard.py` `_query_intensity_stats` (~2014-2018, 2214-2220) and `_query_intensity_trend_bulk` (~1584-1585, 1626-1634):
`methane_loss_rate_pct = ... if gas_m3 > 0 else 0.0`, then `"Compliant" if methane_loss_rate_pct <= ogmp_target`.

## Reproduction
1. Snapshot copy, admin. `GET /api/dashboard/intensity-stats?year=2025`.
2. Select the rows where `total_ch4 > 0` and `total_gas_m3 == 0`.

## Input
Facility 147 (2025): 0.026 tCH4 Verified, no production data.

## Expected
The loss rate is undefined (null), with a status such as "Missing Production Data" or "N/A". The OGMP Excel export handles this case correctly with "Non-Compliant (Missing Production Data)" in `reports.py` ~933-936, and the MethaneIntensity page KPI shows "Pending Production".

## Actual
`methane_loss_rate_pct: 0.0`, `ogmp_target_status: "Compliant"` (facilities 146 and 147). The per-facility bar chart and heatmap show 0 / "-" for them.

## Evidence
`audit/work/D/s6.py` output (current code). Repro: `audit/repro/<ID>.py`.

## Root Cause
A zero denominator is coerced to a 0 % rate, which then passes the ≤ target test.

## Impact
The API reports compliance for facilities that emit methane but have no production denominator. This is inconsistent with the OGMP export and the page-level KPI.

## Affected Components
/api/dashboard/intensity-stats, /api/dashboard/intensity-trend (`methane_loss_rate_pct`, `ogmp_target_status`), MethaneIntensity per-facility loss chart and heatmap.

## Recommended Fix
Return `null` and a "Missing Production Data" status when gas = 0 and CH4 > 0.
