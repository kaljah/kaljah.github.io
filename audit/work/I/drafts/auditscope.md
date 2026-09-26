# BUG-XXX — Audit trail (/api/audit/, /api/audit/export) is not facility/region-scoped: a region-restricted superuser reads activity entries for every region's records

**Status:** Confirmed
**Severity:** Medium
**Category:** Security
**Discovered by:** Agent I (Backend/API/Security)

## Location
`new/server/routes/audit.py:52` `_build_audit_query()` — only IT roles are filtered (to security actions); superusers with a restricted `location` get the unfiltered `ActivityLog` table. Same for `/export`, `/filters`, `/stats`.

## Reproduction
1. Log in as `audit_superuser@audit.local` (superuser, location West; `/api/facilities` returns ids 1, 2, 158, 160, 168).
2. `GET /api/audit/?limit=500&entity=Emission` and `GET /api/audit/export`.
3. Map each entry's `entityId` to `emissions.facility_id`.
Script: `audit/repro/<BUG-ID>.py`.

## Input
Snapshot data, West superuser.

## Expected
Only entries about records in the superuser's allowed facilities (the same scoping applied to `/api/emissions`, dashboards etc.).

## Actual
144 of the returned Emission entries concern facilities outside West (e.g. log 1249 → emission 671, facility 165 "North Africa": "Added Combustion emission: … for Updated Facility (1/2099)"). `/api/audit/export` returns the full 211 KB CSV incl. before/after diffs (`old_values`/`new_values`) of all regions.

## Evidence
```
superuser (West) allowed facilities: [1, 2, 158, 160, 168]
actual: 144 entries, e.g. [(1249, (165, 'North Africa'), 'Added Combustion emission: ...'), ...]; /api/audit/export -> 200, 211509 bytes
```

## Root Cause
Audit queries apply role-based action filtering for IT only; no `get_allowed_facility_ids` scoping for regional roles. ActivityLog has no facility column, so scoping requires joining via entity/entity_id.

## Impact
Cross-region disclosure of activity (facility names, quantities, fuels, users, IPs, value diffs) to regional superusers, defeating the region isolation enforced elsewhere.

## Affected Components
`/api/audit/`, `/api/audit/export`, `/api/audit/filters`, `/api/audit/stats`; Audit Trail page.

## Recommended Fix
Store facility_id on ActivityLog (or resolve through entity/entity_id) and filter by `get_allowed_facility_ids(user)` for non-unrestricted roles; or restrict the audit trail to admin/unrestricted superusers.
