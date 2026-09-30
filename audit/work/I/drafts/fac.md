# BUG-XXX — Region-restricted superuser can re-region its own facility (PUT /api/facilities/<id>), pushing the facility and all its emissions into another region's scope and out of its own

**Status:** Confirmed
**Severity:** Medium
**Category:** Security
**Discovered by:** Agent I (Backend/API/Security)

## Location
`new/server/routes/facilities.py:220-350` `update_facility()` — checks that the facility is currently in the caller's allowed set, then assigns `facility.region` / `location` / `name` from the payload with no check that the new values stay within the caller's region. `add_facility()` (l.137) and `import_facilities()` do enforce the superuser's region, so behaviour is inconsistent.

## Reproduction
1. Log in as `audit_superuser@audit.local` (superuser, location West).
2. `POST /api/facilities {"name":"ZZ_SOUTH","region":"South",...}` → 403 (correct).
3. `PUT /api/facilities/1 {"region":"South"}`.
Script: `audit/repro/<BUG-ID>.py`.

## Expected
403 — a West-restricted superuser must not assign a facility to another region (same rule as create).

## Actual
200 "Facility updated"; facility 1 region is now "South", carrying its 153 emission rows into South users' scope and dashboards; the West superuser loses access to it (it no longer appears in their `/api/facilities`). Pulling a Center facility into West is correctly denied (403), because the current-region check runs first.

## Evidence
```
create facility in South as West superuser: 403 (correctly denied)
expected: PUT region West->South denied (403) like create; actual: 200, facility 1 region now 'South' with its 153 emission rows
```

## Root Cause
Missing target-region validation in `update_facility`. Region membership (`get_allowed_facility_ids`) is derived from the editable `region` / `location` / `name` columns.

## Impact
A regional superuser can inject its region's data (including Pending/Verified emissions it entered) into another region's inventory and reports, or hide a facility from its own region's reviewers. Region-level totals change without an admin.

## Affected Components
`PUT /api/facilities/<id>` (fields region, location, name); every region-scoped endpoint.

## Recommended Fix
For non-unrestricted superusers, reject updates whose new `region` / `location` / `name` would move the facility outside `user.location` (reuse the create-path check); log old and new values.
