# BUG-XXX — Deleting a facility that has any OGMP level-upgrade log fails with 500 (FK violation) and leaks raw SQL

**Status:** Confirmed
**Severity:** Medium
**Category:** Database
**Discovered by:** Agent J (Database)

## Location
- `new/server/models.py` `LevelUpgradeLog` (line ~567): `facility_id` FK `nullable=False`, `facility = db.relationship("Facility")` with no backref/cascade; `Facility` (line ~41) declares cascades for emissions, production, scope2/3, sources, mitigation, CBAM, OGMP, (backref) CAP, flaring, equity — but not level-upgrade logs.
- `new/server/routes/facilities.py:351` `delete_facility` — returns `f"Failed to delete facility: {str(e)}"`.

## Reproduction
1. `make_db("agentJ", overwrite=True)`; log in as admin.
2. `DELETE /api/facilities/1` (facility 1 has one row in `level_upgrade_logs`, created through `POST /api/data/ogmp/level-upgrade`).
3. Compare with `DELETE /api/facilities/2` (no level-upgrade log).

## Input
Snapshot data; facility 1 and 4 each have one `level_upgrade_logs` row.

## Expected
Either the facility and its dependent rows are deleted (as for every other child table), or a clear 409 "facility has dependent OGMP level logs" is returned.

## Actual
`500 {"error": "Failed to delete facility: (sqlite3.IntegrityError) FOREIGN KEY constraint failed\n[SQL: DELETE FROM facilities WHERE facilities.id = ?]..."}`. Facility 2 (no log) deletes fine with 200.

## Evidence
`audit/repro/BUG-<id>.py`; `audit/work/J/cascade.py` output: facility 1 → 500, facility 4 → 500, facility 2 → 200, facility 169 → 200 (CAP/flaring/equity cascades work).
`PRAGMA foreign_keys` = 1 on every connection (NullPool + connect hook), so the FK is enforced.

## Root Cause
`LevelUpgradeLog` is the only facility child table without a delete cascade (or `ondelete`), and its `facility_id` is NOT NULL, so SQLAlchemy cannot null it and SQLite rejects the parent delete.

## Impact
Once anyone logs an OGMP level upgrade for a facility (normal OGMP workflow), that facility can never be deleted through the app. The error body exposes internal SQL text to the client. (On Postgres the same FK error occurs.)

## Affected Components
Facility delete endpoint, Manage Data / facility admin UI, OGMP level-upgrade workflow.

## Recommended Fix
Add `level_upgrade_logs = db.relationship("LevelUpgradeLog", backref=..., cascade="all, delete-orphan")` on Facility (or `ondelete="CASCADE"` + passive_deletes), or explicitly block with a 409 and a clean message; never echo `str(e)` to the client.
