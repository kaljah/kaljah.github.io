# BUG-XXX — Bulk upload job API lets any logged-in role (user, it_admin) create/overwrite facilities and custom factors, bypassing RBAC and region scoping

**Status:** Confirmed
**Severity:** Critical
**Category:** Security
**Discovered by:** Agent I (Backend/API/Security)

## Location
- `new/server/routes/emissions.py:2881` `upload_start()` — only `@login_required`, no role check, `scope` taken verbatim from form data.
- `new/server/background_processor.py:494-500` dispatches `scope=custom_factors` → `_process_row_custom_factors` (l.1520) and `scope=facilities` → `_process_row_facilities` (l.1550). Neither checks the uploader's role; `_process_row_facilities` looks up `Facility.query.filter_by(name=name)` across ALL facilities (not the uploader's allowed set) and overwrites fields when `overwrite_duplicates=true`.

## Reproduction
1. Log in as `audit_user@audit.local` (role `user`, location West) or `audit_itadmin@audit.local` (role `it_admin`).
2. `POST /api/emissions/upload/start` multipart: `file=f.csv`, `scope=facilities`, `overwrite_duplicates=true`, CSV:
   `name,location,region,description` / `Cimenterie Industrielle de Chlef (GICA),HACKED_user,Center,pwned` / `NEWFAC_user,X,East,created by user`
3. Poll `/api/emissions/upload/status/<job_id>` until `completed`.
4. Repeat with `scope=custom_factors`, CSV `name,co2_factor,ch4_factor,unit` / `EVIL_user,999,1,scf`.
Script: `audit/repro/<BUG-ID>.py`.

## Input
Role `user` (West) and role `it_admin`; target facility id 3 (region Center — outside West).

## Expected
403 (the direct routes are protected: `POST /api/facilities/import` → 403 and `POST /api/custom-factors` → 403 for both roles; it_admin must have zero business-data write access; a West user must not touch a Center facility).

## Actual
Both jobs complete (`status=completed, processed=2`). Facility 3 (Center) `location` overwritten to `HACKED_user` / `HACKED_it_admin`; new facilities `NEWFAC_user` (created_by 18) and `NEWFAC_it_admin` (created_by 19) created in region East; custom factors `EVIL_user` / `EVIL_it_admin` with `co2_factor=999` created. Same calls to the direct endpoints return 403.

## Evidence
```
user 200 {'job_id': '064f85cb-...'}  -> {'status': 'completed', 'processed': 2}
[{'id': 3, 'name': 'Cimenterie Industrielle de Chlef (GICA)', 'location': 'HACKED_user', 'region': 'Center'}, {'id': 171, 'name': 'NEWFAC_user', 'region': 'East', 'created_by': 18}]
[{'id': 102, 'name': 'EVIL_user', 'co2_factor': 999.0, 'created_by': 18}]
user direct POST custom-factors: 403 direct facilities import: 403
it_admin ... identical (facility 3 location HACKED_it_admin, NEWFAC_it_admin, EVIL_it_admin)
```

## Root Cause
Authorization is enforced per-route on the dedicated endpoints but the generic job endpoint accepts an arbitrary `scope` and the background processor trusts it. No role / facility-scope checks exist in the facilities/custom-factor row handlers. (Also applies to `scope=sources|production|mitigation` for it_admin — those use the facility map, which is empty for IT roles, so they fail; facilities/custom_factors do not use it.)

## Impact
Privilege escalation: any authenticated account, including IT administrators who are supposed to have zero business-data access, can create facilities, rename/relocate/re-region any facility in any region (which also changes which users can see it via region scoping), and inject custom emission factors that feed Scope 1 calculations (factor lookup by name in `cf_name_map`). Custom factors created this way have no maker-checker step.

## Affected Components
`/api/emissions/upload/start`, `background_processor._process_row_facilities`, `_process_row_custom_factors`; downstream: facility scoping, custom-factor-based Scope 1 calculations, dashboards.

## Recommended Fix
In `upload_start`, whitelist `scope` per role: reject IT roles entirely; allow `facilities` / `custom_factors` only for admin/superuser (and apply the same region restriction as `/api/facilities/import`); in `_process_row_facilities` restrict the existing-name lookup to the uploader's allowed facility ids.
