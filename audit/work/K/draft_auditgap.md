# BUG-XXX — User Management actions are missing from the Audit Trail: account creation and logout logs are never committed, and user deletion is not logged at all

**Status:** Confirmed
**Severity:** Medium
**Category:** Security
**Discovered by:** Agent K (Frontend/UI)

## Location
`new/server/routes/auth.py`:
- `register()` (also used by `POST /api/auth/users`, the User Management "Create user" button): `db.session.commit()` at ≈L297 happens **before** `log_activity_and_notify(action="REGISTER", …)` (≈L301); no commit follows, so the ActivityLog/Notification rows are discarded.
- `logout()` (≈L485-512): `log_activity_and_notify(action="LOGOUT")` then `session.clear()` and return — never committed.
- `delete_user()` (≈L1060-1117): no `log_activity_and_notify` call at all.
(`utils.log_activity_and_notify` adds to the session without committing, per the project's own convention.)

## Reproduction
1. As it_admin: `POST /api/auth/register` (or create a user in User Management), then `DELETE /api/auth/users/<id>`, then `POST /api/auth/logout` (`audit/work/K/reg2.py`, own db copy).
2. Query `activity_log` for the new user's email / REGISTER / LOGOUT; open Audit Trail in the UI.

## Input
Create user k…@audit.local (id 22), delete it, log out.

## Expected
Audit Trail entries for REGISTER/CREATE user, DELETE user and LOGOUT.

## Actual
`register 201`, `delete 200`, `logout 200`; `activity_log` contains no row mentioning the user's email and `select count(*) … where action='LOGOUT'` = 0. The UI DB (audit/db/ui.db) after a full day of activity has actions CREATE/DELETE/EXPORT/LOGIN/UPDATE only — never REGISTER or LOGOUT.

## Evidence
`audit/work/K/reg2.py` output above; repro `audit/repro/BUG-<id>.py`.

## Root Cause
Log helper called after the only commit (register, logout); missing call (delete_user).

## Impact
Privileged account lifecycle (who created or removed which account, when) cannot be reconstructed from the Audit Trail; the Audit Trail page gives an incomplete record for IT/security review.

## Affected Components
Audit Trail page and export, User Management (create/delete), logout.

## Recommended Fix
Call the logger before the commit (or commit again afterwards) in register/logout, and log DELETE in delete_user with the deleted user's identity.
