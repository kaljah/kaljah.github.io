# BUG-XXX — Maker-checker bypass through edit and delete: a superuser can approve a record they just edited, silently re-date/re-assign Verified records, and a user can hard-delete their own Verified records

**Status:** Confirmed
**Severity:** High
**Category:** Security
**Discovered by:** Agent I (Backend/API/Security)

## Location
- `new/server/routes/emissions.py:3423-3480` `update_emission()` — status reset to Pending only when a *non-admin/superuser* edits a Verified record, or when "physical" keys change and user ≠ admin. `year`, `month`, `facility_id` edits by a superuser leave the record Verified. No `updated_by`/last-maker is recorded.
- `emissions.py:4488` `approve_emission()` — segregation check compares only `created_by == user.id`, so the person who last changed the values can approve them.
- `emissions.py:3341-3395` `delete_emission()` — a `user` may delete any record it created regardless of status (Verified included); no review step. (Same patterns exist in `scope2.py` / `scope3.py` PUT/DELETE.)

## Reproduction
1. Superuser (West) `PUT /api/emissions/145 {"year":2019}` (Verified record, facility 2).
2. User creates Scope 1 record (Pending, created_by=user); superuser `PUT /api/emissions/<id> {"quantity":999999}`; superuser `POST /api/emissions/approve/<id>`.
3. User `DELETE /api/emissions/<id>` of that now-Verified record.
Script: `audit/repro/<BUG-ID>.py`.

## Expected
(1) Record returns to Pending (a year change moves emissions between reporting periods). (2) 403 — the superuser is the maker of the approved values. (3) Deleting Verified data requires reviewer action (or 403).

## Actual
(1) `{'year': 2019, 'status': 'Verified'}`. (2) 200, record `quantity 999999, status Verified, approved_by 17` (the editor). (3) 200, row deleted.

## Evidence
```
1) superuser changes year 2020->2019 on Verified #145: expected Pending, actual {'year': 2019, 'status': 'Verified'}
2) superuser edits qty then approves own edit: expected 403, actual 200 [{'quantity': 999999.0, 'status': 'Verified', 'approved_by': 17}]
3) user deletes own Verified record #752: expected 403 / deletion request pending review, actual 200, rows left=0
```
Activity log for #752 shows CREATE (Audit user) → UPDATE quantity (Audit superuser) → approved by Audit superuser.

## Root Cause
Segregation of duties keyed only on `created_by`; the status-reset rule exempts superusers for non-quantity fields; delete has no status gate.

## Impact
One person can put arbitrary values into Verified totals (edit + self-approve), move Verified emissions between reporting years/facilities without review, and remove Verified data — defeats the maker-checker control that dashboards rely on (they aggregate Verified only).

## Affected Components
`PUT/DELETE /api/emissions/<id>`, `POST /api/emissions/approve/<id>`, `/approve/batch`; Scope 2/3 equivalents.

## Recommended Fix
Track `last_modified_by`; block approval when approver is creator OR last modifier; any edit by non-admin (incl. superuser) to a Verified record → Pending; forbid deleting Verified records for non-admins (or route via a pending-deletion review).
