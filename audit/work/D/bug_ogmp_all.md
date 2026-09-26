# BUG-XXX — OGMP reconciliation in the default "All years" view compares the AVERAGE of annual top-down surveys with the SUM of multi-year bottom-up CH4, so perfectly reconciled facilities are flagged (−80 %)

**Status:** Confirmed
**Severity:** Medium
**Category:** Methane
**Discovered by:** Agent D (Methane Auditor)

## Location
- `new/server/routes/dashboard.py` `get_ogmp_metrics()` ~1146-1172: `func.avg(OgmpSurvey.estimated_annual_tch4)` against `func.sum(Emission.ch4_emissions)`. When `year` is "all", neither side is year-filtered.
- `_query_intensity_stats()` ~1961-1980 and 2128-2130: the same avg-vs-sum pairing (`top_down_tch4`, `variance_pct`, `reconciliation_status`, `current_ogmp_level`).
- `new/server/routes/reports.py` OGMP export (~897-922, ~1212-1226) when no year filter is given.
- `MethaneIntensity.jsx` defaults `selectedYear` to "all" (line 43) and shows the `/ogmp-metrics` variance/status in the OGMP roadmap.

## Reproduction
1. Fresh DB copy, admin. Facility 169 Verified bottom-up CH4 by year: 2021 2,891.59 · 2022 2,765.88 · 2023 2,568.91 · 2024 1,350.04 · 2025 772.46 t.
2. For each year, `POST /api/data/ogmp-surveys` with a rate that exactly matches that year's inventory (`measured_rate_kg_hr = t×1000/8760`).
3. `GET /api/dashboard/ogmp-metrics?year=<Y>&facilityId=169` for each year, then with `year=all`. Do the same for `/intensity-stats`.

## Input
Five annual surveys, each equal to its year's bottom-up CH4.

## Expected
Every year reconciles (0 %). The multi-year view should compare like with like: Σ top-down (10,348.88) vs Σ bottom-up (10,348.88), which is 0 % and "Reconciled", or it should reconcile year by year.

## Actual
- Per year: 0.0 %, "Reconciled".
- `year=all`: top-down 2,069.78 (the mean) vs bottom-up 10,348.88 (the sum) gives **−80.0 %, "Discrepancy Flagged"** on both `/ogmp-metrics` and `/intensity-stats`. `intensity-stats.current_ogmp_level` drops from 5 to 4.

## Evidence
`audit/work/D/s14.py` output (current code, baseline2). Repro: `audit/repro/<ID>.py`.

## Root Cause
Aggregation mismatch. The mean of annual surveys is an annual rate, while the unfiltered sum is a multi-year total. Averaging is meant for multiple surveys within one facility-year (Decision D-02), but it is applied across years.

## Impact
The OGMP Gold-Standard roadmap on the Methane Intensity page, which opens in "All years" by default, flags reconciliation discrepancies and understates levels for every facility with more than one year of inventory. The same mismatch applies in the OGMP Excel export without a year filter.

## Affected Components
/api/dashboard/ogmp-metrics, /api/dashboard/intensity-stats (top_down_tch4, variance_pct, reconciliation_status, current_ogmp_level), /api/reports/ogmp-export (no year), MethaneIntensity.jsx OGMP roadmap.

## Recommended Fix
Average surveys per (facility, year), then sum across years, or reconcile per year and report the multi-year view as per-year statuses. Never pair an average with an unfiltered sum.
