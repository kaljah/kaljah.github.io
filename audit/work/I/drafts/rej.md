# BUG-XXX — POST /api/emissions/reject/<id> has no status check: a superuser can flip an admin-Verified record to Rejected (removing it from all totals) and overwrite its approver

**Status:** Confirmed
**Severity:** Medium
**Category:** API
**Discovered by:** Agent I (Backend/API/Security)

## Location
`new/server/routes/emissions.py:4511-4559` `reject_emission()` — unlike `approve_emission()` (l.4485 `if emission.status not in ["Pending","Draft","Pending Approval"]: 400`) and `reject_batch_emissions()` (filters on pending statuses), the single reject path changes any record's status.

## Reproduction
1. Superuser (West) `POST /api/emissions/reject/24 {"reason":"x"}` — record 24 is Verified, approved_by=1 (admin).
2. Compare `POST /api/emissions/reject/batch {"ids":[24],"scope":"1"}`.
Script: `audit/repro/<BUG-ID>.py`.

## Expected
400 "Record is not pending approval" (consistent with approve and batch reject).

## Actual
200; record becomes `status=Rejected, approved_by=17 (superuser), qa_flag='Rejected: x'`; the admin's approval is overwritten. Batch reject on the same id returns `deleted_count=0`. Repeating the reject also returns 200.

## Evidence
```
before: {'id': 24, 'status': 'Verified', 'approved_by': 1}
actual: 200, after={'status': 'Rejected', 'approved_by': 17, 'qa_flag': 'Rejected: x'}; /reject/batch on a non-pending id deleted_count=0
```

## Root Cause
Missing pending-status guard on the single-record reject.

## Impact
Verified inventory data can be withdrawn from dashboards/reports by a superuser without admin involvement; the audit field `approved_by` loses who originally verified it. Double-submits are not idempotent-safe (each re-reject rewrites approver/time).

## Affected Components
`/api/emissions/reject/<id>` (scope 1/2/3 via `scope` param).

## Recommended Fix
Apply the same pending-status check as `approve_emission`; return 409/400 for already-decided records.
