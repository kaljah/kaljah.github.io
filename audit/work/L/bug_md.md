# BUG-XXX — Manage Data page crashes for every user when any facility has a NULL name; POST /api/facilities accepts facilities with no name

**Status:** Confirmed
**Severity:** High
**Category:** UI
**Discovered by:** Agent L (Browser)

## Location
- `new/client/src/pages/ManageData.jsx:1306-1307` (`getFilteredFacilities`: `f.name.toLowerCase()` with no null guard)
- `new/server/routes/facilities.py:121-170` (`add_facility`: no required-field validation; `name=data.get("name")`)
- `new/server/models.py:44` (`Facility.name = db.Column(db.String(120))` — nullable)

## Reproduction
1. Log in to the UI (:5190) as any non-IT role (verified: audit_admin, audit_user).
2. Open `/manage-data`.
3. The page renders the ErrorBoundary "Something went wrong" screen; console: `TypeError: Cannot read properties of null (reading 'toLowerCase') at getFilteredFacilities (ManageData.jsx:1362)`.
4. To create the trigger from a clean DB: as admin, `POST /api/facilities` with `{"region":"West"}` → `201 {"id":172,"message":"Facility added"}` and the stored row has `name = NULL`.

## Input
`POST /api/facilities {"region": "West"}` (no name). The audit snapshot already contains 8 facilities with `name IS NULL` (ids 149,151,153,156,159,161,163,166) and 5 with `name = ''`.

## Expected
The API rejects a facility without a name (400), and the page tolerates a missing name instead of crashing.

## Actual
The API returns 201 and stores `name=NULL`. The whole Manage Data page (facilities, production data, emission sources, mitigation tabs) is unusable for every user while such a row exists. The snapshot DB already has such rows, so in the audited state Manage Data is always broken.

## Evidence
- Playwright run `audit/work/L/w_md_crash.mjs`: `POST /api/facilities {region:West} -> 201 {"id":172}`, `user manage-data crashed: true`; screenshot `audit/work/L/md_crash_user.png`.
- `select id,name from facilities where name is null` → 8 rows in `snapshot_original.db`.

## Root Cause
The server has no required-field validation for facility name (and the column is nullable). The client assumes `f.name` is always a string (`f.name.toLowerCase()`), while it guards `f.location?.` and `f.field?.` on the same line.

## Impact
A core data-management workflow is blocked: users cannot create or edit facilities, production data (carbon-intensity denominators) or emission sources through the UI. Any admin/superuser (or a bulk import) can cause this with one blank facility.

## Affected Components
ManageData page (all tabs); `POST /api/facilities`; probably also the bulk facility import path (not verified separately).

## Recommended Fix
Require a non-empty `name` in `add_facility`/update (and bulk import), make `Facility.name` NOT NULL after cleaning the data, and use `(f.name || '').toLowerCase()` in `getFilteredFacilities`.
