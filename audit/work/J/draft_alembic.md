# BUG-XXX — Alembic migration chain is unusable: `flask db upgrade` fails on both the existing DB and a fresh DB

**Status:** Confirmed
**Severity:** Medium
**Category:** Database
**Discovered by:** Agent J (Database)

## Location
- `new/server/migrations/versions/` (base `815d10c5bbe4` → `61bacaad00dc` → `2ef6f882b02c` → `7fe333372c71` → head `52c620a620d2`)
- `new/server/app.py` module-level `db.create_all()`; `new/server/add_columns.py` (ad-hoc ALTERs outside Alembic)

## Reproduction
1. Copy `audit/db/snapshot_original.db` → `audit/work/J/mig.db`; `DATABASE_URL=sqlite:///.../mig.db FLASK_APP=app.py`.
2. `flask db current` → `7fe333372c71`; `flask db heads` → `52c620a620d2 (head)`.
3. `flask db upgrade` → `OperationalError: duplicate column name: uncertainty_pct`.
4. Point `DATABASE_URL` at a non-existent file and run `flask db upgrade` → `OperationalError: duplicate column name: segment`.

## Input
Snapshot DB; empty DB.

## Expected
The DB stamped revision matches its actual schema, and `flask db upgrade` brings any DB to head.

## Actual
- Existing DB: stamped at `7fe333372c71` but already contains the columns that `52c620a620d2` adds (added by `add_columns.py` / create_all), so upgrade aborts.
- Fresh DB: importing `app` runs `db.create_all()` (full current schema) before Alembic runs, and the base revision is an `add_column("segment")` (no initial create-table revision), so upgrade aborts at the first revision.
- Schema diff create_all-fresh vs snapshot: identical columns/FKs/indexes except server defaults (`facilities.equity_share_pct`, 11 `production_data.*` columns have `DEFAULT 0.0/100.0` in the snapshot but none in a fresh DB) — so today's schema is held together by create_all, not migrations.

## Evidence
Commands above, output captured in this audit session; `audit/work/J/schema_diff.py`; repro `audit/repro/BUG-<id>.py`.

## Root Cause
Schema is managed three ways (create_all at import, ad-hoc ALTER scripts / connect hook, Alembic) with no reconciliation; no baseline revision; `add_columns.py` adds columns without stamping.

## Impact
No working migration path: any future column added to a model will not reach existing DBs (create_all never ALTERs existing tables) and cannot be applied via Alembic without manual stamping. Postgres deployments (docker-compose/Render CMD run only `create_all`) will silently miss new columns → runtime `no such column` errors after upgrades. `server_default` drift means raw-SQL inserts behave differently on fresh vs old DBs.

## Affected Components
All deployments (SQLite and Postgres), `migrations/`, `add_columns.py`, `add_indexes.py`, the custom_factors.description connect hook.

## Recommended Fix
Create a baseline revision matching the current models, `flask db stamp head` existing DBs after verifying, remove create_all/ad-hoc ALTERs from import-time code and run `flask db upgrade` in the container entrypoint.
