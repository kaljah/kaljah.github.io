# BUG-XXX — Deleting a user wipes approved_by/created_by on every record they approved or entered: Verified records lose their maker-checker evidence

**Status:** Confirmed
**Severity:** Low
**Category:** Database
**Discovered by:** Agent J (Database)

## Location
`new/server/routes/auth.py:1090-1112` `delete_user` — `UPDATE <table> SET created_by/approved_by/updated_by = NULL WHERE ... = :uid` across emissions, scope2/3, facilities, custom factors, etc. `ActivityLog.user_id` also nulled (only the free-text `user_name` survives).

## Reproduction
1. `make_db` copy; log in as `it_admin`.
2. User 8 (`test_admin@ghg-test.com`) is `approved_by` on 19 Verified Scope 1 records.
3. `DELETE /api/auth/users/8` → 200.
4. `select count(*) from emissions where status='Verified' and approved_by is null`.

## Input
Snapshot data.

## Expected
Approval provenance stays attached to the record (soft-delete/deactivate the user, or keep an immutable approver name/id), so a Verified record can always show who approved it.

## Actual
Count goes 470 → 489: the 19 records are now "Verified" with `approved_by = NULL` but `approved_at` still set — indistinguishable from records that were never approved through maker-checker (the snapshot already holds 470 such rows; 70 are seed rows, the rest have app-generated UUIDs and cannot be traced to an approver). Only the approval ActivityLog entry's `user_name` text remains, and its `user_id` is also nulled.

## Evidence
`audit/repro/BUG-<id>.py`.

## Root Cause
Hard delete of users combined with nulling every FK to satisfy SQLite FK enforcement; the schema has no user soft-delete or denormalised approver name on records.

## Impact
Verification / assurance (ISO 14064-3, OGMP) needs to prove who approved each figure; after routine staff off-boarding the record-level evidence is gone and `status` contradicts `approved_by`. `created_by` also becomes NULL, so creator-ownership checks for role `user` (`created_by is not None and ...`) no longer apply to those records.

## Affected Components
User deletion; Scope 1/2/3 records, facilities, custom factors, CBAM, OGMP, base-year recalcs; Audit Trail.

## Recommended Fix
Replace hard delete with deactivation (`status='inactive'`), or keep the FKs and block deletion when the user owns approvals; if deletion is required, store approver name/email on the record at approval time.
