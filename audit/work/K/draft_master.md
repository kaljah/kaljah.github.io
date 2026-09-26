# BUG-XXX — Reports "2025 Master Report (PDF)" button sends facility_id=[object Object]; facility selection ignored

**Status:** Confirmed
**Severity:** Medium
**Category:** UI
**Discovered by:** Agent K (Frontend/UI)

## Location
`new/client/src/pages/Reports.jsx` — `handleMasterReportDownload(targetFacilityId = null)` (≈line 296) wired as `onClick={handleMasterReportDownload}` (≈line 575).

## Reproduction
1. Log in as audit_admin on the UI stack (:5191), open /reports.
2. In the "All Regions" table filter choose facility 170 (El Merk).
3. Click "2025 Master Report (PDF)".
4. Observe the network request and downloaded file name.

## Input
Region filter = 170, click the header button.

## Expected
Request `GET /api/reports/master-annual-report?facility_id=170` and the El Merk report (the handler's own logic falls back to `regionId` when no target is passed).

## Actual
Request `GET /api/reports/master-annual-report?facility_id=[object%20Object]`; downloaded file is `Groupement_Berkine_2025_Annual_GHG_Report.pdf` regardless of the selected facility. The toast also says "Downloading Groupement Berkine Master Report".

## Evidence
Playwright capture (audit/work/K/t_reports2.mjs):
```
download filename: Groupement_Berkine_2025_Annual_GHG_Report.pdf
GET /api/reports/master-annual-report?facility_id=[object%20Object]
```
Repro: `audit/repro/BUG-<id>.mjs`.

## Root Cause
React passes the click event as the first argument. `targetFacilityId || ...` is truthy for the event object, so `selectedId` becomes the SyntheticEvent, which is stringified into the URL; the `reportSelectedRegions`/`regionId` fallbacks are never reached.

## Impact
The facility-specific master report can never be obtained from this button; the user silently receives a different organisation's consolidated report. (Only the "Create New Report" modal path passes no argument and works.)

## Affected Components
Reports page header button "2025 Master Report (PDF)". (Related observation: title/filename are hard-coded to 2025 and to two named assets, and the backend endpoint serves static PDFs.)

## Recommended Fix
`onClick={() => handleMasterReportDownload()}` and/or guard `typeof targetFacilityId === "string" || typeof targetFacilityId === "number"`.
