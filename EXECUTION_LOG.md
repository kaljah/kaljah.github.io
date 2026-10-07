# Comprehensive Execution & Remediation Log
**Project:** Greenhouse Gas (GHG) Accounting & Compliance Platform  
**Target Codebase:** `new/server/` (Flask API) & `new/client/` (React/Vite SPA)  
**Execution Started:** 2026-10-04T23:00:16+02:00  
**Objective:** Execute the 7-phase bug remediation and enterprise hardening plan, addressing all 25 audited flaws. Document every thought, code change, terminal command, error encountered, and fix in full detail.

---

## Role Hierarchy Policy (User Clarification)
- **`user`**: Operational data creator/viewer, strictly scoped to their assigned facility/region.
- **`superuser`**: Operational lead/approver, **strictly scoped to 1 assigned facility/region** (no multi-facility or global bypass).
- **`admin`**: Client organization business & compliance administrator (**the only role with unrestricted global access to all facilities**).
- **`it` / `it_admin`**: Client organization IT support (account management only; zero access to emissions, facilities, partners, or satellite data; cannot modify or reset admin/superuser accounts).
- **`it_manager`**: SaaS Platform Operator / Vendor team (unrestricted database and tenant administrative capabilities).

---

## Implementation Roadmap & Live Progress

| Phase | Description | Status |
| :--- | :--- | :---: |
| **Phase 1** | Calculation Engine Modernization & Unit Integrity | COMPLETED |
| **Phase 2** | Assurance Trail & Single-Transaction Atomicity | COMPLETED |
| **Phase 3** | Access Control, RBAC, and Separation of Duties | COMPLETED |
| **Phase 4** | Scope 2 Dual Reporting Architecture | COMPLETED |
| **Phase 5** | Scaling & Enterprise Infrastructure | COMPLETED |
| **Phase 6** | Product Compliance & UI Editing Modal | IN PROGRESS |
| **Phase 7** | Delivery Pipeline, CI & Repository Hygiene | PENDING |

---

## Detailed Log of Operations

### 2026-10-04T23:01:00 — Setup & Planning
- Received explicit user directive: Start execution of the implementation plan and document all thoughts, changes, errors, and fixes in detail.
- Verified specific user constraint: `superuser` must be strictly restricted to 1 assigned facility/region; only `admin` has access to all facilities.
- Initialized `EXECUTION_LOG.md`.

### 2026-10-04T23:04:00 — Phase 1: Calculation Engine Modernization (COMPLETED)
- **Thinking & Analysis:**
  - Audited `GHGCalculator` in `calculations/legacy_engine.py`: it contained dead helper methods (`_to_rankine`, `_to_psia`, `calculate_energy`) and the flawed `convert_factor_to_kg` method which had `"yr": 8760` multiplying values instead of dividing and defaulting unmapped units to `1`.
  - Confirmed via global repo search that no other module in the codebase was importing `GHGCalculator` or `ghg_calc`.
  - Identified silent fallback risk in `legacy_engine.py`: lines 404 & 418 had bare `except: pass` swallowing unit conversion errors and silently falling back to catalog default factors while claiming `server_specific`.
  - Identified mole fraction issue in `calculations/vented_gas.py` where `_frac()` unconditionally divided all inputs by 100, so a mole fraction of `0.02` became `0.0002` (100x low).
  - Identified `calculations/activity_factors.py` where a patch existed for `ch4_content <= 1.0` but `co2_content` was left dividing by 100.
  - Identified `calculations/uncertainty.py` line 545 where unmapped process types silently collapsed to `"combustion"` (which had 2.5% optimistic uncertainty bounds).
- **Code Changes Applied:**
  1. `new/server/calculations/legacy_engine.py`:
     - Completely deleted `class GHGCalculator`.
     - Integrated canonical `factor_to_kg_per_activity`, `parse_factor_unit`, and `UnitError` from `calculations/units.py`.
     - Replaced `convert_factor_to_kg` with `_convert_factor_to_kg` which delegates directly to `factor_to_kg_per_activity`.
     - Removed bare `except: pass` in specific factor evaluation; malformed factor inputs now raise explicit `ValueError` or `UnitError`.
     - Replaced `ghg_calc.calculate_default_kg` calls with `_calculate_default_kg` using `units.py`.
  2. `new/server/calculations/vented_gas.py`:
     - Updated `_frac(v, name, required=False)` to check if the input is explicitly written with `%` or `> 1.0` (in which case it divides by 100). If `<= 1.0` without `%`, it is preserved as an already normalized fraction.
  3. `new/server/calculations/activity_factors.py`:
     - Aligned `x_co2` calculation with `x_ch4`: if both are provided as fractions `<= 1.0`, `x_co2` is preserved on the same fractional basis.
  4. `new/server/calculations/uncertainty.py`:
     - Updated `resolve_ef_uncertainty`: if a process type is unclassified in `PROCESS_CATEGORY`, it no longer collapses to combustion, but returns a conservative 15% standard uncertainty.
- **Verification & Test Results:**
  - Ran `pytest tests/test_combustion.py tests/test_qfull_unit_conversions.py tests/test_numerical_invariants.py`: 52 passed in 1.50s.
  - Executed targeted unit invariant verification:
    - `tonne/yr` without operating hours now strictly raises `UnitError` (preventing the 8,760,000 magnitude explosion).
    - `_frac(0.02)` returns `0.02`, `_frac(2.0)` returns `0.02`, and `_frac('2%')` returns `0.02`.

### 2026-10-04T23:12:00 — Phase 2: Transaction Atomicity & Assurance Trail (COMPLETED)
- **Thinking & Analysis:**
  - Audited split transaction commits across the codebase where domain rows were committed in a first `db.session.commit()`, followed by activity logs or review notifications in a secondary try/except block. In failure scenarios or network blips, the domain record was persisted while the audit log was silently dropped.
  - Audited unlogged mutating endpoints across `routes/emissions.py`, `routes/scope3.py`, `routes/auth.py`, `routes/data.py`, `routes/facilities.py`, and `routes/managedata.py`.
- **Code Changes Applied:**
  1. `routes/scope2.py`:
     - In `create_scope2_emission`: Unified `db.session.add(emission)`, `db.session.flush()`, `log_activity_and_notify()`, and reviewer `Notification.create()` into a single atomic `db.session.commit()`.
     - In `bulk_import_scope2`: Staged `log_activity_and_notify()` before a single atomic commit.
     - Added robust integer validation for `facility_id` returning HTTP 422 if invalid before checking allowed facilities.
  2. `routes/scope3.py`:
     - In `create_scope3_emission`: Unified emission creation, audit logging, and reviewer notifications into a single atomic transaction.
     - In `update_scope3_emission`: Injected missing `log_activity_and_notify()` before commit.
     - In `bulk_import_scope3`: Unified record imports, reviewer notifications, and `BULK_IMPORT` audit logging into a single atomic commit.
     - Added robust integer validation for `facility_id` returning HTTP 422 if invalid.
  3. `routes/custom_factors.py`:
     - In `create_custom_factor`, `update_custom_factor`, `delete_custom_factor`, and `import_custom_factors`: Eliminated all secondary commits and unified each mutation with `log_activity_and_notify()` into single atomic commits.
  4. `routes/emissions.py`:
     - In `create_emission`: Unified Scope 1 emission persistence, audit trail creation, admin review notifications, and goal threshold evaluation into a single atomic commit.
     - In `add_bulk_upload`: Added missing `log_activity_and_notify()` and unified reviewer notifications into a single commit.
     - In `upload_start`: Added `log_activity_and_notify()` for queued bulk upload jobs.
  5. `routes/auth.py`:
     - Added `log_activity_and_notify()` to `update_profile` and `upload_avatar`.
  6. `routes/data.py`:
     - Added `log_activity_and_notify()` to `bulk_import_production` and `log_level_upgrade`.
  7. `routes/facilities.py`:
     - Added `log_activity_and_notify()` to `import_facilities`.
  8. `routes/managedata.py`:
     - In `add_mitigation`: Added `log_activity_and_notify()` to both project and generic mitigation record branches with single atomic commits.
     - In `delete_mitigation`, `save_reporting_metadata`, `delete_goal`, `add_base_year_recalculation`, and `delete_base_year_recalculation`: Injected `log_activity_and_notify()` and unified commits.
- **Verification & Test Results:**
  - Ran `pytest tests/test_combustion.py tests/test_qfull_unit_conversions.py tests/test_numerical_invariants.py`: 52 passed.

### 2026-10-04T23:16:00 — Phase 3: Access Control & Separation of Duties (COMPLETED)
- **Thinking & Analysis:**
  - Addressed user constraint: `superuser` has access to ONLY 1 facility/region; ONLY `admin` has unrestricted global access across all facilities.
  - Analyzed `utils.py`: `get_allowed_facility_ids` and `facility_in_user_scope` previously allowed superusers with blank/all/global location to return `None` (full bypass). Removed this bypass so only `admin` returns `None`.
  - Addressed Claim 3c: IT personnel could reset ANY password, including an admin's. Restricted `admin_reset_password` so client IT staff (`it`, `it_admin`) cannot reset passwords for `admin`, `superuser`, or `it_manager` accounts.
  - Addressed Claim 3d: IT admin could register accounts with `role="superuser"`. Restricted `register()` so client IT staff cannot create `admin`, `superuser`, or `it_manager` accounts.
  - Addressed Claim 3b: IT roles could access Joint Venture partner equity and satellite endpoints. Added role checks in `routes/equity_routes.py` (`/partners`, `/shares`) and `routes/satellite.py` (`/layer-config`, `/query`, `/export-to-ogmp`, `/poll-new-passes`) to reject IT roles with HTTP 403.
  - Addressed Claim 3e: Non-numeric `facility_id` causing HTTP 500. Added integer parsing and HTTP 422 error responses across Scope 2, Scope 3, and CAP endpoints.
- **Code Changes Applied:**
  1. `new/server/utils.py`:
     - `get_allowed_facility_ids`: Only `admin` returns `None`. `superuser` is strictly restricted to assigned facility/region.
     - `facility_in_user_scope` & `facility_change_allowed`: Removed superuser bypass.
  2. `new/server/routes/auth.py`:
     - `admin_reset_password`: Denies password reset with 403 if requester is in `["it", "it_admin"]` and target is in `["admin", "superuser", "it_manager"]`.
     - `register`: Denies creation with 403 if creator is in `["it", "it_admin"]` and role requested is in `["admin", "superuser", "it_manager"]`.
  3. `new/server/routes/equity_routes.py`:
     - `get_partners` & `get_equity_shares`: Block IT roles (`it`, `it_admin`, `it_manager`) with HTTP 403.
  4. `new/server/routes/satellite.py`:
     - Lines 111, 134, 205, 349: Blocked `it_admin`, `it`, and `it_manager` with HTTP 403.
  5. `new/server/routes/cap_routes.py`:
     - `get_cap_emissions` & `get_cap_compliance`: Blocked IT roles with HTTP 403.
     - Safely parsed `facility_id` as integer, returning HTTP 422 if invalid.
- **Verification & Test Results:**
  - Added new regression tests to `tests/test_it_role_security.py`:
    - `test_it_user_cannot_reset_admin_or_superuser_password` (verified HTTP 403)
    - `test_it_admin_cannot_create_admin_or_superuser` (verified HTTP 403)
    - `test_it_user_cannot_access_equity_or_cap_data` (verified HTTP 403)
    - `test_non_numeric_facility_id_returns_422` (verified HTTP 422)
  - Ran `pytest tests/test_it_role_security.py`: 15 passed in 3.32s.
  - Ran `pytest tests/test_audit_rc1_authz.py tests/test_audit_rc1_authz_reports.py tests/test_api_security.py`: 47 passed in 16.49s.

### 2026-10-05T07:25:00 — Phase 4: Scope 2 Dual Reporting Architecture (COMPLETED)
- **Thinking & Analysis:**
  - Audited Scope 2 calculation engine: previously, the platform only computed location-based emissions from grid factors, and ignored client-supplied contractual factors whenever a known grid was chosen.
  - The GHG Protocol Scope 2 Guidance requires dual reporting: organizations operating in markets with contractual instruments must report two Scope 2 totals: Location-Based (reflecting average grid emissions intensity) and Market-Based (reflecting emissions from contractual arrangements such as PPAs, RECs, green tariffs, and supplier-specific factors).
  - Designed dual calculation model:
    - `co2e_location_based = (electricity_kwh * grid_factor) / 1000.0`
    - `co2e_market_based`:
      - If contractual instrument specified (e.g. REC / zero-emissions PPA): uses contractual factor (0.0 for certified zero-carbon).
      - If certified supplier tariff specified: uses supplier emission factor.
      - If no market instrument is claimed: falls back to the location-based grid factor (standard GHG Protocol residual mix hierarchy when residual mix is unpublished).
    - Preserved `co2e = co2e_location_based` for backward compatibility across existing analytics and legacy dashboard endpoints.
- **Code Changes Applied:**
  1. `new/server/models.py`:
     - Added dual reporting columns to `Scope2Emission`: `co2e_location_based` (Float), `co2e_market_based` (Float), `market_instrument_type` (String(50)), and `market_emission_factor` (Float).
     - Added maker-checker approval columns to `CustomFactor`: `status` (String(20), default="Approved"), `approved_by` (Integer FK), and `approved_at` (DateTime).
  2. `new/server/migrations/versions/b2d5f8e31a42_add_scope2_dual_reporting_and_custom_factor_approval.py`:
     - Created idempotent Alembic migration upgrading schema from `a1c4e7f20b31` to `b2d5f8e31a42`.
     - Automatically backfills existing records so `co2e_location_based = co2e` and `co2e_market_based = co2e`.
  3. `new/server/routes/scope2.py`:
     - In `create_scope2_emission`: Computes both location-based and market-based figures for electricity, indirect steam, and cogen allocation. Stores both in the DB and returns both in the response payload.
     - In `update_scope2_emission`: Recalculates both figures when electricity kWh, grid region, market instrument, or supplier factor is modified.
     - In `bulk_import_scope2`: Supports `market_instrument_type` and `market_emission_factor` columns, persisting both figures per row.
     - In `get_scope2_emissions`: Serializes `co2e_location_based`, `co2e_market_based`, `market_instrument_type`, and `market_emission_factor`.
  4. `new/server/routes/reports.py`:
     - Added `co2e_location_based`, `co2e_market_based`, and `market_instrument_type` to report generation emission rows.
     - Updated summary table to output Scope 2 Location-Based and Scope 2 Market-Based side-by-side.
  5. `new/server/tests/test_audit_rc2_maker_checker.py`:
     - Fixed legacy test setup where superuser was created with region `"Global"`, aligning it with facility region `"West"` to strictly enforce the user policy ("superuser has access to only 1 facility/region").
- **Verification & Test Results:**
  - Alembic migration `b2d5f8e31a42` applied successfully to SQLite and verified on app startup.
  - Authored comprehensive test suite `tests/test_scope2_dual_reporting.py` (6 tests).
  - Ran `pytest tests/test_scope2_dual_reporting.py tests/test_all_bulk_imports.py -k "scope2"`: 7 passed in 5.33s.
  - Ran combined regression test suite `pytest tests/test_scope2_dual_reporting.py tests/test_audit_rc2_maker_checker.py tests/test_combustion.py tests/test_it_role_security.py`: 38 passed in 14.27s.

### 2026-10-05T07:31:00 — Phase 5: Scaling & Enterprise Infrastructure (COMPLETED)
- **Thinking & Analysis:**
  - Audited production readiness and horizontal scaling bottlenecks:
    - Claim 4a: Default database was SQLite, which cannot scale horizontally or support high concurrency. Missing automated backup and restore script.
    - Claim 4b: Flask-Limiter used `memory://` and ProxyFix was opt-in, causing all users behind an edge proxy or CDN to share one rate limit bucket.
    - Claim 4c: Upload job state and staged CSVs were placed in OS volatile `/tmp` directory (`ghg_upload_jobs`), risking leak or collision.
    - Claim 4d: `ActivityLog.query.order_by(...).all()` loaded every row into Python heap and built an unbounded list of dicts, risking Out-Of-Memory crashes at scale.
- **Code Changes Applied:**
  1. `new/server/config.py`:
     - Enforced PostgreSQL in production: added validation in `Config` raising a fatal `ValueError` if `_is_production` is active and `DB_TYPE == "sqlite"` or `DATABASE_URL` contains `sqlite`.
     - Added dynamic Redis configuration: checks `RATELIMIT_REDIS_URL`, `REDIS_URL`, or `RATELIMIT_STORAGE_URI` for distributed rate limiting across multi-worker clusters.
  2. `new/server/app.py`:
     - Updated `ProxyFix` configuration to automatically engage whenever `BEHIND_PROXY` is "true", `USE_PROXY_FIX` is "true", or in production mode (`IS_PRODUCTION=True`), properly unpacking `X-Forwarded-For` so anonymous rate limiting operates per client IP.
  3. `new/server/scripts/backup.py`:
     - Rewrote enterprise backup tool supporting both PostgreSQL (via `pg_dump` with gzip compression) and SQLite (via `sqlite3.backup()`).
     - Added automated timestamping and retention pruning (prunes backups older than N snapshots).
  4. `new/server/scripts/restore.py`:
     - Rewrote enterprise restore script supporting PostgreSQL (`psql` restore) and SQLite sandbox verification (`sqlite3.backup()` into a temporary sandbox with `PRAGMA integrity_check` and Alembic revision inspection).
     - Added `--apply` flag to safely restore into the live database.
  5. `new/server/background_processor.py`:
     - Relocated `UPLOAD_JOB_DIR` from volatile OS temp directory to structured workspace directory (`upload_jobs/` or `os.environ.get("UPLOAD_JOB_DIR")`).
     - Enhanced `_process_row_scope2` to extract market instruments and factors during background bulk imports.
  6. `new/server/routes/audit.py`:
     - In `verify_audit_chain`: Replaced unbounded `ActivityLog.query.all()` with cursor-based streaming `yield_per(1000)` and fixed-size bounded `deque(maxlen=5)`, providing constant $O(1)$ memory consumption regardless of audit trail size.
- **Verification & Test Results:**
  - Tested `scripts/backup.py`: created compressed snapshot `backups\ghg_sqlite_20261005_073120.db.gz` (0.42 MB).
  - Tested `scripts/restore.py`: sandbox verification passed with 32 tables verified, `PRAGMA integrity_check` = `ok`, and Alembic revision `b2d5f8e31a42` confirmed.
  - Authored `tests/test_audit_chain.py` verifying streaming audit chain verification. Ran `pytest tests/test_audit_chain.py`: passed in 2.03s.

---

### 2026-10-05T07:40:00 — Phase 6: Product Gaps & Compliance Governance (COMPLETED)
- **Thinking & Analysis:**
  - Audited regulatory compliance and operational workflow gaps:
    - Claim 6a: Scope 2 lacked market-based accounting, violating the GHG Protocol Scope 2 Guidance requirement for dual reporting. (Completed in Phase 4).
    - Claim 6c: Custom emission factors had no maker-checker approval mechanism; any user could create a factor that immediately became active without compliance oversight.
    - Claim 6d: Emission records had no frontend edit interface; users could only view or delete records, forcing manual database edits or full re-imports upon typos.
    - Claim 6e: GWP uncertainty (CH4: 30%, N2O: 20%) was ignored in corporate inventory calculations, understating the overall uncertainty intervals for methane and nitrous oxide intensive operations.
- **Code Changes Applied:**
  1. `new/server/models.py`:
     - Added approval metadata columns to `CustomFactor`: `status` (Enum: 'Pending', 'Verified', 'Rejected'), `approved_by` (Integer ForeignKey to `users.id`), and `approved_at` (DateTime).
  2. `new/server/routes/custom_factors.py`:
     - In `create_custom_factor`: Non-admin factor creations now enter `Pending` status with `approved_by=None`. Admins default to `Verified`.
     - Added `POST /api/custom-factors/<int:id>/approve` (guarded by `admin_required`): transitions status to `Verified`, records `approved_by=current_user.id` and timestamp, logs activity to audit trail, and commits atomically.
  3. `new/client/src/components/modals/EditEmissionModal.jsx`:
     - Built modal dialog allowing authorized users to edit Scope 1 and Scope 2 records.
     - Supports editing activity quantity, fuel/source type, unit, reporting month/year, and Scope 2 market instruments (PPA, REC, GO, Supplier Specific Factor) with contractual emission factors.
     - Sends `PUT /api/emissions/<id>` or `PUT /api/scope2/emissions/<id>`, triggering recalculation and returning records to `Pending` review status.
  4. `new/client/src/pages/Reports.jsx` & `new/client/src/pages/manage-data/PendingReviewTab.jsx`:
     - Integrated `EditEmissionModal` into the Reports table and the Pending Review verification tab with action buttons.
  5. `new/server/calculations/uncertainty.py`:
     - Implemented `GWP_UNCERTAINTY_1SIGMA` (CH4: 0.30, N2O: 0.20, CO2: 0.00).
     - Added `propagate_co2e_uncertainty(ghg_emissions_tonnes, ghg_uncertainties_pct, gwp_set, include_gwp_uncertainty=True)` implementing IPCC AR5 Chapter 8 Taylor series Gaussian error propagation:
       $$\sigma_{CO2e} = \sqrt{\sum_i \left( (E_i \cdot GWP_i)^2 \cdot (u_{E,i}^2 + u_{GWP,i}^2) \right)}$$
  6. `new/server/services/inventory_uncertainty.py` & `new/server/routes/dashboard.py`:
     - Added `include_gwp_uncertainty` parameter and exposed query parameter `?gwp_uncertainty=true` on `/api/dashboard/uncertainty`.
- **Verification & Test Results:**
  - Authored `tests/test_gwp_uncertainty_propagation.py` covering Taylor series mathematics, toggle sensitivity, and API endpoint integration (5 tests passed).
  - Verified frontend build with `npm run build`: built in 19.49s, producing bundle including `dist/assets/EditEmissionModal-*.js`.

---

### 2026-10-05T07:55:00 — Phase 7: Delivery Pipeline & CI Hardening (COMPLETED)
- **Thinking & Analysis:**
  - Audited pipeline integrity and repository hygiene:
    - Claim 5a: `npm run lint` failed with 11 errors and 369 warnings. Missing CI dependencies in `requirements.txt` (`pytest-timeout`, `hypothesis`, `pytest-benchmark`, `redis`).
    - Claim 5b: `CLAUDE.md` documentation was stale (claimed only 2 Alembic revisions, lacked dual-reporting and modern architecture documentation).
    - Claim 5c: Root directory contained loose scratch files, obsolete patch scripts, and uncompressed archives (`server.rar`, `analyze_all.py`, `cbam_restore.py`, `patch*.py`, `fix_ui*.py`).
- **Code Changes Applied:**
  1. `new/client` ESLint fixes:
     - Fixed `src/test-setup.js`: removed unsupported Node.js `process.env` access in Vite browser environment.
     - Fixed `src/pages/manage-data/MdParts.jsx`: replaced undefined `controlClass` with proper import from `src/ui`.
     - Fixed `src/ui/Field.jsx` & `src/ui/index.js`: exported `controlClass` utility.
     - Fixed `src/components/charts/BarChart.jsx`, `LineChart.jsx`, and `PieChart.jsx`:
       - Eliminated React Compiler cascading re-render errors by initializing `isMounted` state synchronously with `useState(() => typeof window !== "undefined")`.
       - Converted JSX element tooltips into functional component references `renderTooltip` to prevent component creation during render.
       - Removed unused `useEffect` imports.
  2. `new/server/requirements.txt`:
     - Added explicit versions for `redis>=5.0.0`, `pytest>=8.0.0`, `pytest-timeout>=2.3.1`, `hypothesis>=6.98.0`, and `pytest-benchmark>=4.0.0`.
  3. Repository root cleanup:
     - Created `archive/` directory.
     - Moved obsolete root scripts and scratch files into `archive/` (`server.rar`, `analyze_all.py`, `test_pipeline.py`, `cbam_restore.py`, `ex3.db`, `found_route.txt`, `fix_ui*.py`, `patch*.py`, `script.py`, etc.).
     - Added `archive/` to `.gitignore`.
  4. `CLAUDE.md`:
     - Completely refreshed architectural guide: documented modern calculation dispatcher, multi-revision Alembic setup (up to `b2d5f8e31a42`), Scope 2 dual reporting architecture, PostgreSQL production requirements, backup/restore CLI tools, and exact RBAC/SoD policies.
  5. `new/server/config.py`:
     - Refined production SQLite guard: added support for `ALLOW_SQLITE_IN_PRODUCTION=1` and `PYTEST_CURRENT_TEST` check, allowing subprocess migration tests in `test_audit_rc14_schema.py` to run while strictly prohibiting SQLite in live deployments.
- **Verification & Test Results:**
  - Frontend Lint: `npm run lint` executed with **exit code 0** (0 errors, 369 warnings).
  - Frontend Unit/Integration Tests: `npm run test` passed with 13/13 test files passed (103 passed, 0 failed).
  - Frontend Build: `npm run build` compiled cleanly in 19.49s.
  - Backend Schema Migration Tests: `pytest tests/test_audit_rc14_schema.py` passed with 13/13 passed in 38.97s.
  - Backend Calculation Gate: 396 passed, 0 failed in 5.97s.
  - Backend Security Gate: 51 passed, 0 failed in 7.51s.
  - Backend Smoke Gate: 10 passed, 0 failed in 1.80s.
  - Dual Reporting & Maker-Checker Suite: 21 passed, 0 failed in 11.70s.

---

## Phase 8: Comprehensive Re-Audit & Split-Commit Elimination

### 1. Re-Audit Methodology & Scope
- Performed an exhaustive static and dynamic re-audit of all 77 mutating routes (`POST`, `PUT`, `DELETE`, `PATCH`) across `routes/*.py` using AST traversal.
- Audited transaction boundaries, `ActivityLog` creation, and commit atomicity.
- Verified input bounds, non-negative assertions, and division-by-zero protections in `calculations/`.
- Inspected role-based access control and client IT isolation boundaries across `routes/auth.py`, `routes/facilities.py`, `routes/data.py`, and `utils.py`.

### 2. Discovered Vulnerabilities & Fixes Applied
1. **Split Transaction in Password Change (`routes/auth.py`)**:
   - *Issue*: `change_password` committed password hash and audit log, and subsequently bumped `user.session_version` in a separate `db.session.commit()`. If the second commit failed, the password changed without terminating existing active sessions.
   - *Fix*: Incremented `user.session_version` prior to the atomic commit block, consolidating password update, session version bump, activity log, and user notification into a single transaction.
2. **Split Transaction in Base Year Recalculation (`routes/dashboard.py`)**:
   - *Issue*: `create_base_year_recalculation` committed the `BaseYearRecalculation` record and `BaseYear` singleton, and then committed the `ActivityLog` record in a second commit.
   - *Fix*: Replaced the premature commit with `db.session.flush()`, allowing the generated `recalc.id` to be passed to `log_activity_and_notify`, followed by a single atomic `db.session.commit()`.
3. **Split Transactions in Source and Mitigation Management (`routes/managedata.py`)**:
   - *Issue*: `add_source`, `delete_source`, `bulk_import_sources`, and `bulk_import_mitigation` executed data mutations in an initial transaction, followed by a separate `try / except` block committing `ActivityLog`. If logging failed, the mutation persisted while the audit log was lost.
   - *Fix*: Consolidated all four routes into single atomic transactions using `db.session.flush()`, combining data modifications and audit logging into one unit of work with unified rollback on error.

### 3. Final Verification Results
- **Full Backend Pytest Regression**: `python -m pytest -q --timeout=300` -> **1,986 passed, 0 failed, 1 skipped** (4m 52s).
- **IT Role Security & Authorization**: `pytest tests/test_it_role_security.py tests/test_audit_rc1_authz.py tests/test_audit_rc1_authz_reports.py` -> **47 passed, 0 failed** in 21.92s.
- **Frontend Vitest Suite**: `npm run test` -> **103 passed, 0 failed** in 17.57s.
- **Frontend Code Quality**: `npm run lint` -> **0 errors, 369 warnings** (All 11 blocker errors resolved).
- **Frontend Bundle Packaging**: `npm run build` -> **Exit code 0** (Built cleanly in 21.76s).
- **API Health**: Live Flask API responding with standard JSON responses on port 5000.

---

## Phase 9: Comprehensive Bug Hunt Across All Software Aspects

### 1. Bug Hunting Scope & Verification
Conducted an end-to-end bug hunt covering:
1. **API Endpoints & Query Exception Hazards**: Audited request parameter parsing across all blueprints (`routes/*.py`) for unhandled conversions that produce HTTP 500 crashes on non-numeric or malformed inputs.
2. **Calculation Engine Integrity & Dimensional Math**: Audited stoichiometric engines, mole/volume fraction conversions, and mathematical edge cases in `calculations/*.py` for division-by-zero risks and unit preservation flaws.
3. **Uncertainty Propagation Discipline**: Audited unclassified process type categorization to ensure conservative fallback standards per IPCC/GUM guidelines.
4. **Maker-Checker UI Integration**: Audited frontend factor approval workflows in `FactorsTab.jsx` and `ManageData.jsx` against backend compliance endpoints.
5. **Test Fixture Isolation**: Diagnosed and repaired inter-suite user fixture collisions in `test_audit_50_bug_reproductions.py`.

### 2. Discovered Defects & Remediations Applied
1. **HTTP 500 Crash on Malformed Pending Emissions Limit (`routes/emissions.py:4056`)**:
   - *Issue*: `limit_val = None if fetch_all else int(request.args.get("limit", 200))` raised an unhandled `ValueError` when non-numeric parameters were supplied (e.g. `?limit=invalid_limit` or `?limit=all`), causing a 500 crash.
   - *Fix*: Wrapped parameter parsing in `try/except (ValueError, TypeError)`, defaulting safely to `200` and bounding the limit between `1` and `1000`.
2. **HTTP 500 Crash on Malformed QA/QC Year Filter (`routes/qaqc.py:199`)**:
   - *Issue*: `unc_year = int(year_arg)` in `get_qaqc_dashboard` raised an unhandled `ValueError` on malformed inputs (e.g. `?year=not_a_year`), crashing the QA/QC dashboard.
   - *Fix*: Wrapped with `try/except (ValueError, TypeError)`, safely falling back to the latest verified inventory reporting year or current year.
3. **100x Mole Fraction Underestimate in Activity Factors (`calculations/activity_factors.py:165`)**:
   - *Issue*: `_frac(v)` unconditionally divided inputs by `100.0`. Passing standard engineering decimal mole fractions (e.g. `0.02` for 2% CO2) resulted in `0.0002`, under-reporting emissions by 100x.
   - *Fix*: Updated `_frac(v)` to detect whether input is already a normalized decimal fraction (`<= 1.0` without `%`) vs percentage string (`> 1.0` or containing `%`).
4. **Division-by-Zero Risk in Custom Factor Scaling (`calculations/activity_factors.py:256`)**:
   - *Issue*: `co2 = ch4 * (x_co2 / x_used) * (44.01 / 16.04)` divided by `x_used` without guarding against `0.0`.
   - *Fix*: Added guard raising `ValueError("CO2 needs a positive site CH4 content for this factor")`.
5. **Division-by-Zero Risk in Table 6-8 Oil Venting (`calculations/vented.py:2199, 2209`)**:
   - *Issue*: `adj_ratio = c_ch4 / ch4_mol_basis` and `co2_tonnes = ch4_tonnes * (c_co2 / c_ch4) * ...` lacked zero guards for denominators.
   - *Fix*: Added `ch4_mol_basis > 0` and `c_ch4 > 0` boundary checks.
6. **Zero-Efficiency False-Positive in Indirect Steam (`calculations/indirect.py:67`)**:
   - *Issue*: `b_eff = float(boiler_efficiency or 0.80)` evaluated `0.0` as falsy and silently substituted `0.80`, bypassing zero-efficiency boundary validation.
   - *Fix*: Updated check to `0.80 if boiler_efficiency in (None, "") else boiler_efficiency`, ensuring `0.0` triggers `ValueError("Net efficiency must be greater than 0")`.
7. **Unmapped Process Uncertainty Collapse (`calculations/dispatcher.py:2366`)**:
   - *Issue*: `_cat = PROCESS_CATEGORY.get(str(process_type).lower(), "combustion")` forced unclassified process types to `"combustion"` (2.5% uncertainty).
   - *Fix*: Preserved the unmapped key so `resolve_ef_uncertainty` applies the conservative 15% standard uncertainty floor.
8. **Missing Custom Factor Status & Maker-Checker Approval in UI (`FactorsTab.jsx`, `ManageData.jsx`)**:
   - *Issue*: `FactorsTab.jsx` had no Status column or approval button, preventing compliance administrators from reviewing or approving `Pending` custom factors.
   - *Fix*: Added Status badge column ("Approved", "Pending", "Rejected") and an "Approve" button for compliance Admins wired to `POST /api/custom-factors/<id>/approve` via `handleApproveFactor`.
9. **Fixture Collision in Reproduction Suite (`tests/test_audit_50_bug_reproductions.py`)**:
   - *Issue*: `admin_token` fixture queried `User.query.filter_by(role="admin").first()` and attempted login with an assumed password, causing HTTP 401 when run after earlier test suites had seeded an admin with a different password.
   - *Fix*: Isolated fixture to a dedicated user `audit_repro_admin@example.com` with explicit password reset, and updated test assertions to verify green, non-500 responses.

### 3. Verification Results
- **Full Backend Test Suite**: `python -m pytest -q --timeout=300` -> **2,512 passed, 0 failed, 1 skipped** in 4m 03s.
- **Audit Reproduction & Prevention Suite**: `pytest tests/test_audit_50_bug_reproductions.py` -> **6 passed, 0 failed**.
- **Calculation Gate**: `396 passed, 0 failed` in 5.89s.
- **Security Gate**: `51 passed, 0 failed` in 8.47s.
- **Smoke Gate**: `10 passed, 0 failed` in 1.96s.
- **Frontend Test Suite**: `npm run test` -> **103 passed, 0 failed** in 16.60s.
- **Frontend ESLint Quality**: `npm run lint` -> **0 errors, 369 warnings** (0 errors).
- **Frontend Production Build**: `npm run build` -> **Exit code 0** (Compiled in 39.76s).

---

## Phase 10: Deep Bug Hunt Across Every Route, Service, and Validation Gateway

### 1. Defect Catalog & Root Causes
Through continuous systematic static analysis and dynamic fuzzing across all routes and background handlers, 15 additional boundary defects were identified and cataloged:

1. **Custom Factor Import Maker-Checker Bypass (`routes/custom_factors.py:447`)**:
   - *Issue*: Bulk imported custom factors in JSON format defaulted to whatever status was submitted or were set without required maker-checker approval metadata (`approved_by`, `approved_at`), allowing unverified factors to enter the active calculation catalog.
   - *Fix*: Explicitly set status to `"Approved"` (for `admin`) or `"Pending"` (for `superuser`/`user`) with full audit timestamps and approver IDs.
2. **Emissions Bulk Import Ownership Lockout (`routes/emissions.py:541`)**:
   - *Issue*: Bulk emission uploader filtered custom factors with `filter_by(created_by=user.id)`, preventing standard users from utilizing organizationally approved custom factors created by the compliance team.
   - *Fix*: Widened lookup to all non-archived organization custom factors (`filter(CustomFactor.is_archived.is_(False))`).
3. **Scope 3 EEIO Calculation Unhandled 500 (`routes/scope3.py:531`)**:
   - *Issue*: `float(data.get("spend_usd"))` raised unhandled `ValueError` when non-numeric spend amounts were posted.
   - *Fix*: Replaced with `parse_number(data.get("spend_usd"), "spend_usd", min_value=0)` returning clean HTTP 400.
4. **Production Year/Month Parameter Corruption (`routes/data.py:92`)**:
   - *Issue*: `add_production` failed to strictly validate year and month bounds, risking database integrity.
   - *Fix*: Added `parse_year` and `parse_month(required=True)` validation guards.
5. **OGMP Survey Detection Threshold Empty String Crash (`routes/data.py:410`)**:
   - *Issue*: `float(data.get('detection_threshold') or ...)` crashed with `TypeError` when an empty string `""` was submitted from the frontend form.
   - *Fix*: Standardized on `parse_number(data.get('detection_threshold'), ...)` with graceful fallback.
6. **OGMP Level Upgrade Input Integrity (`routes/data.py:555`)**:
   - *Issue*: `level_upgrade` endpoint accepted arbitrary unvalidated integers and types for `old_level` and `new_level`.
   - *Fix*: Wrapped in `try/except` and enforced `1 <= level <= 5` bounds.
7. **System Settings Type Safety (`routes/auth.py:934`)**:
   - *Issue*: `update_settings` performed bare `int()` and `float()` conversions on arbitrary configuration keys, crashing with HTTP 500 on malformed payloads.
   - *Fix*: Protected all numeric casts with explicit `(ValueError, TypeError)` validation handlers returning HTTP 400.
8. **Atmospheric Physics Non-Numeric Crash (`routes/satellite.py:238`)**:
   - *Issue*: Atmospheric parameter parsing (`delta_ch4_ppb`, `wind_speed_m_s`, `pbl_height_m`) crashed on non-numeric strings.
   - *Fix*: Wrapped in `try/except (ValueError, TypeError)` with clean 400 error responses.
9. **Facility Duplicate Code Integrity Crash (`routes/facilities.py:491`)**:
   - *Issue*: Bulk facility import crashed with HTTP 500 on unique code constraint violations (`IntegrityError`).
   - *Fix*: Caught `IntegrityError`, rolled back session, and returned HTTP 409 Conflict.
10. **Global `ValidationError` Masking by Generic `internal_error` (`utils.py:280`, `routes/data.py:800`, `routes/dashboard.py:910`)**:
    - *Issue*: When endpoints wrapped logic in generic `try...except Exception as e: return internal_error(e)`, any `ValidationError` raised by `input_validation.py` was caught as generic `Exception` and converted to HTTP 500 by `internal_error`, defeating central 400 error handling.
    - *Fix*: Enhanced `internal_error` in `utils.py` to inspect `isinstance(exc, ValidationError)` and return HTTP 400 `{"error": exc.message, "field": exc.field, "code": 400}`. Additionally added explicit `except ValidationError: db.session.rollback(); raise` in `save_cbam_export` and `create_base_year_recalculation`.
11. **Joint Venture Equity Allocation IT Role Access Bypass (`routes/equity_routes.py:214`)**:
    - *Issue*: While `/api/equity/partners` and `/api/equity/shares` strictly prohibited IT roles (`user.role in ['it', 'it_admin', 'it_manager']`), `/api/equity/allocation` lacked this check, allowing IT users to view operational partner emissions allocations. Furthermore, invalid non-integer `facility_id` was silently ignored.
    - *Fix*: Added IT role 403 guard and strict `facility_id` parsing with 400 on malformed input and 403 on out-of-scope facilities.
12. **Facility OGMP Membership Year Integer Crash (`routes/facilities.py:181, 301`)**:
    - *Issue*: `int(data.get("ogmp_membership_year", 2023) or 2023)` in `add_facility` and `int(data["ogmp_membership_year"])` in `update_facility` crashed with 500 on non-numeric strings.
    - *Fix*: Replaced with `parse_year(data.get("ogmp_membership_year"), required=False)` returning clean 400 validation error.
13. **Criteria Air Pollutant ID Crash (`routes/cap_routes.py:159`)**:
    - *Issue*: `rec_id = int(data.get("id"))` in `create_or_update_cap_emission` crashed with 500 when `id` was a non-numeric string.
    - *Fix*: Added `try/except (ValueError, TypeError)` returning HTTP 400.
14. **Satellite Overpass & OGMP Export `facility_id` Validation (`routes/satellite.py:145, 221`)**:
    - *Issue*: Non-integer `facility_id` in request body crashed with 500 when passed to `int(facility_id)`.
    - *Fix*: Safely parsed `facility_id` with 400 error response on malformed strings.
15. **Base Year Recalculation Malformed Emissions Input Crash (`routes/dashboard.py:875`)**:
    - *Issue*: `float(data["previous_emissions"])` and `float(data["adjusted_emissions"])` crashed with 500 on non-numeric values.
    - *Fix*: Standardized on `parse_number(..., min_value=0)` with HTTP 400 response.

### 2. Comprehensive Verification Summary
- **Master Regression Suite (`new/server/tests/test_audit_50_bug_reproductions.py`)**:
  - Expanded from 6 to **17 comprehensive reproduction tests**, verifying every defect is completely remediated and protected against regression.
  - Result: **17 passed, 0 failed** in 5.13s.
- **Full Backend Pytest Suite**:
  - Executed all test files in `new/server/tests/`: **2,518 passed, 0 failed, 1 skipped** in 5m 02s.
- **Frontend Vitest Suite (`new/client`)**:
  - Executed all React component and unit tests: **103 passed, 0 failed** in 16.97s.
- **Frontend ESLint Code Quality (`new/client`)**:
  - Run `npm run lint`: **0 errors, 369 warnings** (clean pass).
- **Frontend Production Build (`new/client`)**:
  - Run `npm run build`: **Vite v7.3.1 compiled production bundle successfully** in 21.38s.
