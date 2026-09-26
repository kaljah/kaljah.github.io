# BUG-XXX — Deleting a user who created production data, SBTi targets or OGMP level logs fails with 500 (FK cleanup list incomplete)

**Status:** Confirmed
**Severity:** Medium
**Category:** Database
**Discovered by:** Agent J (Database)

## Location
`new/server/routes/auth.py:1058` `delete_user` — hard-coded `tables_to_clean` list (emissions, scope2/3, mitigation_projects, mitigation_records, facilities, emission_sources, custom_factors, cbam_product_exports, base_year_recalculations, ogmp_surveys).

## Reproduction
1. `make_db("agentJ", overwrite=True)`; log in as `it_admin`.
2. `DELETE /api/auth/users/1` (user 1 created 864 production_data rows, 3 sbti_targets, 2 level_upgrade_logs).
3. Compare `DELETE /api/auth/users/9` (only emissions references) → 200.

## Input
Snapshot data.

## Expected
User is deleted and every `created_by` reference is nulled (as the endpoint does for other tables), or a clean 409 explaining why deletion is blocked.

## Actual
`500 {"error": "Internal server error"}`; server log: `sqlite3.IntegrityError: FOREIGN KEY constraint failed [SQL: DELETE FROM users WHERE users.id = ?]`. User still exists.

## Evidence
`audit/repro/BUG-<id>.py`, `audit/work/J/userdel.py`. PRAGMA foreign_keys = 1 on every connection (verified), so FKs are enforced.

## Root Cause
Tables with `created_by → users.id` missing from the clean-up list: `production_data`, `sbti_targets`, `level_upgrade_logs`, `cap_emissions`. (`mitigation_records` in the list has no such columns — the try/except silently swallows that.) No `ondelete` on any users FK.

## Impact
IT admins cannot remove accounts of any user who ever entered production data, an SBTi target, or an OGMP level log — i.e. most real operational users (offboarding / access-revocation workflow broken). Also, the preceding UPDATEs are part of the same failed transaction so nothing is changed, but the client only sees a generic 500.

## Affected Components
User management (IT admin), `/api/auth/users/<id>` DELETE.

## Recommended Fix
Derive the clean-up list from `db.metadata` (all FKs referencing `users.id`), or declare `ondelete="SET NULL"` on those FKs; alternatively prefer deactivation (`status='inactive'`) over hard delete.
