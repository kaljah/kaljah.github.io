# BUG-XXX — GET /api/manage/sbti ignores facility/region scoping: region-restricted users can read organisation-wide Verified emission totals for any year

**Status:** Confirmed
**Severity:** Medium
**Category:** Security
**Discovered by:** Agent H (SBTi Auditor)

## Location
`new/server/routes/managedata.py` `manage_sbti()` GET branch (~lines 996-1033): `Emission.query.filter_by(status="Verified", year=calc_year)` (and Scope2/Scope3) without `get_allowed_facility_ids(user)`.

## Reproduction
1. `python C:/Users/samsung/Desktop/H2/audit/repro/<BUG-ID>.py`
2. Log in as `audit_user@audit.local` (role user, location West).
3. `GET /api/manage/sbti?base_year=2023` (any year 2015-9999 can be queried).

## Input
Controlled data: 2023 Verified West (facility 1) S1 350 + S2 100 = 450 t; Center (facility 3) S1 300 + S3 200 = 500 t.

## Expected
Either scoped to the caller's allowed facilities (450 t) or forbidden for non-admin roles — the sibling endpoint `/api/dashboard/sbti-trajectory` does apply `allowed_fids`.

## Actual
`suggested_base_year_emissions = 950.0` (includes the Center facility the user cannot access). Looping `base_year` over years yields the full org-wide annual total series.

## Evidence
Response above; code has no `allowed_fids` filter in the GET branch.

## Root Cause
Missing `get_allowed_facility_ids` scoping in the baseline suggestion query.

## Impact
Aggregate cross-region disclosure (org-wide yearly S1+S2+S3 totals) to region-restricted users. Limited to aggregate totals (no record detail), hence Medium.

## Affected Components
`/api/manage/sbti` and `/api/sbti` GET; SbtiDashboard "Auto-Fill Verified" and ManageData SBTi tab.

## Recommended Fix
Apply `allowed_fids` to the three queries (or restrict the suggestion to admins), consistent with `/dashboard/sbti-trajectory`.
