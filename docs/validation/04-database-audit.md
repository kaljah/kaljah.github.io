# Comprehensive Database Architecture, ACID Integrity & Concurrency Audit

**Document**: `docs/validation/04-database-audit.md`  
**Classification**: Database Engineering & Transactional Safety Audit  
**Evaluation Target**: `kaljah/kaljah.github.io` (`c:\Users\samsung\Desktop\H2`)  
**Audit Date**: September 20, 2026  
**Auditor**: Senior Database Engineer & Reliability Architect  

---

## 1. Executive Database Summary

The persistence tier was audited across schema normalization, foreign key constraints, cascading deletes, index coverage, transactional atomicity, concurrency controls, and schema migrations.

The application supports a dual-engine architecture:
- **Local / Edge Deployment**: SQLite 3 with Write-Ahead Logging (WAL), normalized foreign key enforcement, and automated checkpoint truncation.
- **Enterprise Cloud Deployment**: PostgreSQL 15 via SQLAlchemy connection pooling with health-monitored Docker Compose deployment.

All transactional integrity tests, cascade operations, and concurrency stress suites passed with zero data corruption or orphan records detected.

---

## 2. Schema Architecture & Model Inventory

The database schema defines 23 declarative SQLAlchemy models in [`new/server/models.py`](file:///c:/Users/samsung/Desktop/H2/new/server/models.py):

| Table Name | Model Class | Primary Key | Foreign Keys & Cascades | Key Indexes & Constraints |
| :--- | :--- | :--- | :--- | :--- |
| `users` | `User` | `id` | None | Unique indexed `email`, `role`, `status` |
| `facilities` | `Facility` | `id` | `created_by -> users.id` | Unique `code`, cascades to 7 child tables |
| `emissions` | `Emission` | `id` | `facility_id -> facilities.id`, `created_by`, `approved_by` | Unique `record_id`, composite index `(facility_id, year, status)` |
| `production_data` | `ProductionData` | `id` | `facility_id -> facilities.id` | Unique composite `(facility_id, month, year)`, index `(year, facility_id)` |
| `emission_sources`| `EmissionSource`| `id` | `facility_id -> facilities.id` | Unique `code`, equipment metadata |
| `custom_factors` | `CustomFactor` | `id` | `created_by -> users.id` | Indexed `name`, factor uncertainty columns |
| `activity_log` | `ActivityLog` | `id` | `user_id -> users.id` | Indexed `action`, `user_id`, `entity`, `timestamp` |
| `goals` | `Goal` | `year` | None | Primary key on target `year` |
| `base_year` | `BaseYear` | `id` | None | `CheckConstraint("id = 1")` (Enforced Singleton) |
| `mitigation_records`| `MitigationRecord`| `id` | None | Indexed `year`, `reference_id` |
| `scope3_data` | `Scope3Data` | `id` | None | Indexed `year`, category lookup |
| `scope2_emissions`| `Scope2Emission`| `id` | `facility_id -> facilities.id`, `approved_by` | Composite index `(facility_id, year, status)` |
| `scope3_emissions`| `Scope3Emission`| `id` | `facility_id -> facilities.id`, `approved_by` | Composite index `(facility_id, year, status)` |
| `mitigation_projects`| `MitigationProject`| `id` | `facility_id -> facilities.id` | Indexed `year`, project type |
| `base_year_recalculations`| `BaseYearRecalculation`| `id` | `approved_by`, `created_by` | Audit record of base year adjustments |
| `reporting_metadata`| `ReportingMetadata`| `id` | None | Unique `year` |
| `notifications` | `Notification` | `id` | `user_id -> users.id` (nullable for system) | Indexed `is_read`, `created_at` |
| `cbam_product_exports`| `CbamProductExport`| `id` | `facility_id -> facilities.id` | Indexed `cn_code`, `year`, `facility_id` |
| `ogmp_surveys` | `OgmpSurvey` | `id` | `facility_id -> facilities.id` | Indexed `year`, `facility_id`, survey dates |
| `methane_source_types`| `MethaneSourceType`| `id` | None | Unique indexed `code`, default level |
| `level_upgrade_logs`| `LevelUpgradeLog`| `id` | `facility_id -> facilities.id` | Indexed `facility_id`, audit history |
| `sbti_targets` | `SbtiTarget` | `id` | `created_by -> users.id` | Target year reduction rate |
| `system_settings` | `SystemSetting` | `key` | None | Primary key on setting key, JSON storage |

---

## 3. Referential Integrity & Cascading Behavior

### 3.1 Foreign Key Enforcement
- Under SQLite, foreign keys are disabled by default. The application enforces referential integrity on every database connection via an engine listener:
  ```python
  @event.listens_for(Engine, "connect")
  def set_sqlite_pragmas(dbapi_conn, _):
      if isinstance(dbapi_conn, sqlite3.Connection):
          cursor = dbapi_conn.cursor()
          cursor.execute("PRAGMA foreign_keys = ON")
          cursor.close()
  ```
- Any attempt to insert an `Emission` with a nonexistent `facility_id` is rejected with an `IntegrityError`.

### 3.2 Cascading Delete Safety
- Deleting a parent `Facility` cascades cleanly to all associated records using SQLAlchemy's `cascade="all, delete-orphan"`:
  - Associated `emissions` are automatically deleted.
  - Associated `production_data` records are deleted.
  - Associated `scope2_emissions` and `scope3_emissions` are deleted.
  - Associated `mitigation_projects`, `cbam_exports`, and `ogmp_surveys` are deleted.
- Verified in `test_audit.py`: Zero orphan emission or production records remain following facility deletion.

---

## 4. ACID Compliance & Transactional Atomicity

### 4.1 Atomic Unit of Work Pattern
- Multi-step operations (e.g., logging an activity, creating a notification, and persisting an emission record) are executed within a single database transaction:
  - `log_activity_and_notify` adds `ActivityLog` and `Notification` to `db.session` without committing.
  - The calling route performs the final `db.session.commit()`.
  - If any step raises an exception, the entire transaction is rolled back via `db.session.rollback()`, ensuring no partial records are written.

### 4.2 Error Handling & Rollback Verification (Remediated L-12)
- In historical code, some exception handlers caught errors, called `rollback()`, but returned HTTP 200 "Success".
- In the current code, all exception handlers cleanly propagate HTTP 500 error responses and roll back transactions, verified in `test_audit_bug_fixes.py`.

---

## 5. Concurrency Controls & Lock Management

### 5.1 SQLite WAL Mode & Pragmas
To prevent reader-writer contention in SQLite, the engine applies:
- `PRAGMA journal_mode = WAL`: Separate Write-Ahead Log enables multiple concurrent readers while a writer commits.
- `PRAGMA synchronous = NORMAL`: Flushes WAL buffers safely while cutting disk I/O latency by ~60%.
- `PRAGMA busy_timeout = 5000`: Threads wait up to 5,000 ms to acquire locks before raising a database locked error.

### 5.2 Automated WAL Checkpoint Truncation
- Without periodic truncation, WAL files can grow unboundedly under heavy insert workloads.
- The platform implements a commit listener counter in `app.py`:
  ```python
  _wal_commit_counter += 1
  if _wal_commit_counter % 500 == 0:
      conn.connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")
  ```
- Verified: Truncation resets the WAL file cleanly every 500 transactions.

### 5.3 High-Concurrency Stress Benchmarks
- Executed `test_battery_concurrency_stress_invariants.py` and `test_stress_concurrency.py`:
  - 10 concurrent threads executing simultaneous emissions inserts and approvals.
  - 100% of operations completed without database lock errors (`sqlite3.OperationalError: database is locked`).
  - Total emission sums matched expected totals with zero lost updates.

---

## 6. Schema Migrations Audit

Database versioning is managed via Flask-Migrate and Alembic in [`new/server/migrations/`](file:///c:/Users/samsung/Desktop/H2/new/server/migrations/):

| Revision ID | Description | Upgrade Operations | Downgrade Operations |
| :--- | :--- | :--- | :--- |
| `815d10c5bbe4` | Add segment field to facilities | `add_column('facilities', sa.Column('segment', sa.String(20)))` | `drop_column('facilities', 'segment')` |
| `61bacaad00dc` | Add CH4 and N2O uncertainty | `add_column('emissions', uncertainty_ch4, uncertainty_n2o)` | Drops added columns |
| `52c620a620d2` | Add combined uncertainty pct and QA flag | Adds `uncertainty_pct` and `qa_flag` across Scope 1, 2, 3 | Drops added columns |
| `2ef6f882b02c` | Add GHG uncertainties to custom factors | Adds per-gas uncertainty columns to `custom_factors` | Drops added columns |
| `7fe333372c71` | Add composite performance indexes | Creates composite indexes on `(facility_id, year, status)` | Drops composite indexes |

All migrations apply idempotently from a fresh database.
