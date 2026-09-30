# BUG-XXX — Sentinel-5P "Export to OGMP" stores a 1-hour CH4 mass as the survey's "estimated annual tCH4" (default operating_hours = 1): top-down understated 8,760× and reconciliation always flagged

**Status:** Confirmed
**Severity:** Medium
**Category:** Methane
**Discovered by:** Agent D (Methane Auditor)

## Location
- `new/server/routes/satellite.py` `export_satellite_to_ogmp()` ~lines 258-270: `operating_hours = 8760.0 if is_continuous else 1.0`, then `estimated_annual_tch4 = measured_rate_kg_hr * operating_hours / 1000`. The value is saved in `OgmpSurvey.estimated_annual_tch4` / `operating_hours_year`.
- `new/client/src/pages/MethaneExplorer.jsx` `handleExportToOgmp` (~line 430): posts `facility_id, observation_date, anomaly_ppb, estimated_emission_rate_kg_hr, ...`. It sends no `is_continuous`, `operating_hours` or duration, so the 1-hour default always applies.
- Contrast: the manual survey path (`routes/data.py save_ogmp_survey`) annualises the same kg/h rate with 8,760 h by default.

## Reproduction
1. Fresh DB copy, admin. Facility 169 has Verified bottom-up CH4 of 772.46 t for 2025.
2. `POST /api/satellite/sentinel5p/export-to-ogmp` with exactly the MethaneExplorer payload: `{"facility_id":169,"observation_date":"2025-07-01","anomaly_ppb":10,"estimated_emission_rate_kg_hr":100.0,...}`.
3. Inspect the stored survey and `GET /api/dashboard/ogmp-metrics?year=2025&facilityId=169`.

## Input
Satellite flux 100 kg CH4/h.

## Expected
The field is named, displayed and reconciled as an **annual** quantity against the annual bottom-up inventory, so the rate must be annualised on the same basis as manual surveys: 100 × 8,760 / 1000 = 876 tCH4/yr. Variance vs 772.46 t = +13.4 %, which is within the 20 % threshold: "Reconciled". Otherwise the export must require the user to state an emission duration.

## Actual
`operating_hours_year = 1.0`, `estimated_annual_tch4 = 0.1`, `variance_pct = −99.99`, `reconciliation_status = "Discrepancy Flagged"`. `/ogmp-metrics` then reports −99.99 % "Discrepancy Flagged". The survey is saved as `status "Verified"` for admin/superuser, and the API response tells the user it was "reconciled".

## Evidence
`audit/work/D/s13.py` output (current code, baseline2). Repro: `audit/repro/<ID>.py`.

## Root Cause
There is a 1-hour default duration in the export path, and the UI never provides a duration. Top-down averaging (`func.avg(estimated_annual_tch4)` in `/ogmp-metrics`, `/intensity-stats` and the OGMP export) then mixes 1-hour masses with 8,760-hour annualised manual surveys.

## Impact
Every satellite survey exported from Methane Explorer is 8,760× too small as an annual estimate. Top-down/bottom-up reconciliation (the OGMP Level 5 criterion) is systematically falsified toward "discrepancy". Averaged top-down values for facilities with both survey types are meaningless.

## Affected Components
routes/satellite.py export-to-ogmp, MethaneExplorer "Export to OGMP", /api/dashboard/ogmp-metrics, /api/dashboard/intensity-stats (top_down_tch4, variance), /api/reports/ogmp-export, MethaneIntensity survey table.

## Recommended Fix
Annualise consistently (8,760 h or facility operating hours), or make duration a required, explicit input in the UI. Store the observed rate separately from any annualised figure, and do not average surveys that were annualised on different bases.
