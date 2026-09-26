# BUG-XXX — Bulk-upload overwrite rewrites approved records without an audit trail and leaves them "Pending" but still marked approved

**Status:** Confirmed
**Severity:** Medium
**Category:** Database
**Discovered by:** Agent J (Database)

## Location
`new/server/background_processor.py` overwrite branches (Scope 1 ~l.1874-1893, Scope 2 ~l.1036-1045, Scope 3 ~l.1141-1150 and ~l.1270-1279) set `existing_obj.status = "Pending"` but never touch `approved_by`/`approved_at`; the whole `_process_file_thread` never calls `log_activity_and_notify` (no ActivityLog for any bulk import).

## Reproduction
1. `make_db` copy; admin. Record id 7 (RNS, pneumatic, 10 devices, eq 7) is Verified, `approved_by=1`, `approved_at=2026-09-22 19:15`.
2. Upload scope=1 CSV with `overwrite_duplicates=true`: `2026-09,RNS,pneumatic,Pneumatic Controller - High Bleed,20,devices,default,7`.
3. Inspect record 7 and `activity_log`.

## Input
As above.

## Expected
Status reset to Pending **and** `approved_by`/`approved_at` cleared (as the manual edit paths do: `emissions.py:3426/3481`, `scope2.py:379`, `scope3.py:240/283`); an ActivityLog UPDATE/IMPORT entry with old and new values.

## Actual
Record 7: `status=Pending, approved_by=1, approved_at=2026-09-22 19:15:13, quantity 10→20, co2e 2325.12→4650.24`. **Zero** activity_log rows were written for the upload (only notifications to admins).

## Evidence
`audit/repro/BUG-<id>.py`; `audit/work/J/bulk.py`. `grep log_activity background_processor.py` → no matches.

## Root Cause
Overwrite branches only partially reset maker-checker state; bulk processor has no audit logging at all.

## Impact
Verified inventory values can be replaced in bulk with no record of the previous value or who changed it (verifier/ISO 14064 audit-trail gap). Records end in a contradictory state (Pending yet carrying an approver and approval time), so any report/QA logic using `approved_by IS NOT NULL` treats them as approved; the approval evidence refers to numbers that no longer exist.

## Affected Components
Bulk import Scope 1/2/3 (all scopes, incl. production/sources/facilities/custom-factor uploads, which also write no ActivityLog); Audit Trail page; QA/approval views.

## Recommended Fix
In overwrite branches clear `approved_by`/`approved_at` (and set `updated_by`), capture old values, and write one ActivityLog per overwritten record plus one IMPORT summary per job, committed in the same transaction as the data.
