# BUG-XXX — Approve/reject endpoints are not concurrency-safe: two simultaneous approvals of the same record both return 200 (duplicate audit entries; approve+reject race ends in an arbitrary final state)

**Status:** Confirmed
**Severity:** Low
**Category:** Backend
**Discovered by:** Agent I (Backend/API/Security)

## Location
`new/server/routes/emissions.py` `approve_emission()` (~l.4456) and `reject_emission()` — read `emission.status`, check it in Python, then assign and commit; no conditional `UPDATE … WHERE status IN (pending)`, no row lock / version column.

## Reproduction
1. Two admin sessions POST `/api/emissions/approve/<id>` at the same time (threads) for 30 Pending records.
Script: `audit/repro/<BUG-ID>.py`.

## Expected
One 200 and one 400 "Record is not pending approval" per record; one approval activity-log row per record.

## Actual
17 of 30 records got 200 for both requests; 47 approval log rows for 30 records (and duplicate notifications). In a variant where an admin approves while a superuser rejects the same record, both calls returned 200 for 18/20 records and the final status (7 Rejected / 13 Verified) depended on commit order, while both users were told their decision succeeded.

## Evidence
```
actual: 17/30 records approved twice (both 200); approval log rows = 47
```

## Root Cause
Check-then-act without atomic conditional update (the batch endpoints use `query.filter(status.in_(pending)).update(...)`, which is atomic; the single-record endpoints do not).

## Impact
Non-idempotent double submits; audit trail shows two approvals by different people; conflicting reviewer decisions both acknowledged.

## Affected Components
`/api/emissions/approve/<id>`, `/api/emissions/reject/<id>` (all scopes).

## Recommended Fix
Use `UPDATE … SET status='Verified' WHERE id=:id AND status IN (…)` and check `rowcount == 1` (or optimistic version column), returning 409 otherwise.
