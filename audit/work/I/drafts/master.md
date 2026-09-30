# BUG-XXX — /api/reports/master-annual-report serves full annual GHG report PDFs to any logged-in role (incl. it_admin and out-of-region users) and returns a static, pre-generated file regardless of facility_id

**Status:** Confirmed
**Severity:** High
**Category:** Security
**Discovered by:** Agent I (Backend/API/Security)

## Location
`new/server/routes/reports.py:454-482` `get_master_annual_report()` — only `@login_required`; no role check, no `get_allowed_facility_ids` / `require_facility_access`.

## Reproduction
1. Log in as `audit_user@audit.local` (role user, West; allowed facility ids 1,2,158,160,168...) or `audit_itadmin@audit.local`.
2. `GET /api/reports/master-annual-report?facility_id=170` and `GET /api/reports/master-annual-report`.
Script: `audit/repro/<BUG-ID>.py`.

## Input
facility_id=170 (El Merk, region "El Merk", outside West) and no facility_id (consolidated).

## Expected
403 for it_admin (IT roles have zero business-data access, cf. `get_allowed_facility_ids` → []) and for a West user requesting El Merk / consolidated data. The report should also reflect the requested facility and the current database.

## Actual
All four requests return 200 `application/pdf` (1,901,139 bytes El Merk report; 1,912,094 bytes Groupement Berkine report). Additionally:
- Any `facility_id` other than 170/"elm" (e.g. a West facility the user owns) returns the *Groupement Berkine* report — a different facility's data.
- The PDF is read from a hard-coded absolute path `c:/Users/samsung/Desktop/H2/*.pdf` and only regenerated if missing, so the numbers are frozen at the time the file was generated (files dated 2026-09-24), not the current DB; on any other host/path it would try to generate into the developer's desktop path.

## Evidence
```
user: 170 in scope=False; GET ...?facility_id=170 -> 200 application/pdf 1901139 bytes
user: GET ... (no facility) -> 200 application/pdf 1912094 bytes
it_admin: ... -> 200 application/pdf 1901139 bytes / 1912094 bytes
```

## Root Cause
Demo endpoint wired to static files with no authorization or facility scoping.

## Impact
Cross-region data exposure of full annual GHG/CAP reports (emissions, production, compliance) to any authenticated user and to IT administrators; logically wrong report content for any facility other than El Merk; stale figures.

## Affected Components
`/api/reports/master-annual-report`; client report download UI that calls it.

## Recommended Fix
Require business role + `require_facility_access(user, facility_id)` (and unrestricted access for the consolidated report); generate from current DB per request (or cache keyed by facility/DB version) instead of a hard-coded desktop path; 404 for unsupported facility ids.
