# BUG-XXX — Reports Excel/PDF exports drop the Division, Field, Method and Search filters shown on screen

**Status:** Confirmed
**Severity:** Medium
**Category:** UI
**Discovered by:** Agent K (Frontend/UI)

## Location
`new/client/src/pages/Reports.jsx` — `handleExcelExport` (≈line 195) and `handlePDFExport` (≈line 228) build their params from `scope/year/month/regionId/processType` only.

## Reproduction
1. Log in as audit_admin (:5191), open /reports, set the table Year filter to "All", Division = "Upstream".
2. The table shows "Total Records: 61".
3. Click "Excel Export" and then "PDF Report"; capture the requests.

## Input
Division = Upstream (same for Field, Method, and the search box).

## Expected
`/api/emissions/export?...&division=Upstream&format=excel` and `/api/reports/export?...&division=Upstream` — both backend endpoints accept `division`, `field`, `method`, `search` (routes/emissions.py ≈4047-4050, routes/reports.py `export_emissions`).

## Actual
```
GET /api/emissions/export?scope=all&format=excel
GET /api/reports/export?scope=all
```
The division filter is silently dropped. Via the API, the unfiltered export contains 660 rows vs 63 with `division=Upstream`, so the downloaded file contains ~10x the records the user was looking at.

## Evidence
Playwright capture `audit/work/K/t_reports3.mjs`; repro `audit/repro/BUG-<id>.mjs`.

## Root Cause
Export param builders were not updated when the Division/Field/Method/Search filters were added to the list query (`fetchEmissions` sends them).

## Impact
Exported spreadsheets/PDFs do not match the on-screen filtered table; a user exporting "Upstream" data submits/uses the whole-company dataset without any warning.

## Affected Components
Reports page: Excel Export, PDF Report buttons.

## Recommended Fix
Build one shared params object (the one used by `fetchEmissions`, minus page/per_page) and reuse it for both exports.
