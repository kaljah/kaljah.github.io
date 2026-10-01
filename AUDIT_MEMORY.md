# AUDIT MEMORY (living document)

Purpose: single source of truth for every bug/flaw found in the GHG platform audit, its status, decisions taken, and conventions to respect while fixing. RE-READ THIS FILE BEFORE EVERY FIX. UPDATE IT AFTER EVERY FIX.

Status legend: FIXED (verified) | WONTFIX (reason)

Working branch: `fix/audit-remediation` (from `main`).

---

## 0. Conventions and context to respect

### Stack
- Backend: Flask 3.0.3 + Flask-SQLAlchemy 3 + Flask-WTF CSRF + Flask-Limiter, SQLite default / Postgres optional. Entry `new/server/app.py`. Blueprints in `new/server/routes/`. Calculation engine in `new/server/calculations/` (dispatcher.py routes to per-process calculators; legacy_engine.py is fallback). Bulk upload in `new/server/background_processor.py` (thread + in-memory job dict).
- Frontend: React 19 + Vite 7, axios instance in `new/client/src/api.js` (cookie session + X-CSRFToken header), routing in `App.jsx` (PrivateRoute / NonITRoute / ITRoute / AdminRoute).
- Auth model: session cookie `user_id`; roles `user` < `superuser` < `admin` < `it_admin`. `utils.get_allowed_facility_ids(user)` returns None for admin/it_admin/superuser(location=="all"), else list of facility ids matching `Facility.region == user.location OR Facility.location == user.location OR Facility.name == user.location`.
- Record status vocabulary (canonical, enforce everywhere): `Pending` (awaiting maker-checker approval), `Verified` (approved, counted in dashboards), `Draft`.
- Emission quantities in DB are in TONNES (co2_emissions, ch4_emissions, n2o_emissions, co2e_total, Scope2Emission.co2e, Scope3Emission.co2e). Uncertainty columns are FRACTIONS (0.05 = 5%).
- GWP: server truth is `calculations/constants.py` (AR5: CH4 28, N2O 265; AR6: 27.9/273; AR4: 25/298; 20-yr AR5 CH4 82.5, N2O 268). Client mirrors these exactly.
- Units: `calculations/units.py` CONVERSIONS is the single conversion table. scf_to_m3 = 0.0283168; density_ch4 0.6785 kg/m3; density_co2 1.861 kg/m3 (both at 60F/14.696 psia).
- Audit pattern: `utils.log_activity_and_notify(...)` adds ActivityLog (+ Notification) to the session WITHOUT committing; the route commits once atomically.
- Error responses: JSON `{"error": ...}` with proper status codes. Never leak str(exception) for 500s.

### UI theme (preserved)
- Light theme only (`applyTheme` no-op behavior preserved).
- Palette: green environmental theme. Primary green `#10b981`, dark green `#1B5E20`/`#2E7D32`, accent orange `#ff6600`, blue `#3b82f6`, warning amber `#f59e0b`, danger `#ef4444`, slate text `#1e293b`/`#64748b`.
- Settings page (`pages/Settings.jsx`): GWP, OGMP thresholds, Facility overrides, Copernicus tabs. Global settings tabs and save buttons display an informative read-only banner for non-admin accounts.

### Product logic
- Maker-checker: bulk uploads create `Pending` records; admins/superusers approve via `/api/emissions/approve*`. Non-approver manual entries default to `Pending`; admin/superuser manual entries can be `Verified`.
- Tiers: factor_source `default` (Tier 1 catalog), `custom` (Tier 2 user factor), `specific` (Tier 3 engineering inputs, strict validation, no silent defaults).
- OGMP 2.0: Level 3 = generic factors, Level 4 = site-specific/measured bottom-up, Level 5 = top-down survey reconciled within facility `reconciliation_threshold`.

---

## 1. CRITICAL security findings

| ID | Status | Location | Issue | Remediation Summary |
|----|--------|----------|-------|---------------------|
| C1 | FIXED | routes/facilities.py `add_facility`, `import_facilities` | Anonymous facility creation secured via `@login_required` + role check. Region scoping for non-admin superusers. | Enforced `@login_required` + role check; superusers restricted to creating facilities in their assigned `user.location` region; search wildcards escaped via `_escape_like`. |
| C2 | FIXED | seed_admin.py, README.md | Hard-coded admin accounts a@a/a, z@z/z, a/a, z/z, admin@ghg.com/Admin12345!; script resets existing passwords; README publishes creds. | Rewrote `seed_admin.py` to source credentials from environment variables (`ADMIN_EMAIL`, `ADMIN_PASSWORD`, etc.); enforces strong passwords; purged trivial accounts; updated README.md to remove hard-coded plaintext passwords. |
| C3 | FIXED | services/sentinel5p.py `query_satellite_observations` | Fabricates anomaly_ppb / emission rate / QA score from SHA256(lat,lon,date). | Removed synthetic plume calculations; returns `status="metadata_only"` and `summary=None`; blocked export of synthetic satellite passes to OGMP surveys. |
| C4 | FIXED | routes/auth.py, routes/satellite.py `_get_user_copernicus_credentials` | Copernicus creds stored plaintext; fallback iterates ALL users and reuses another user's creds; password echoed back by GET /settings. | Copernicus credentials stored org-wide in `SystemSetting`; passwords masked as `"********"` in GET responses and ignored on updates; cross-user credential scanning eliminated. |
| C5 | FIXED | routes/auth.py `update_settings`, Settings.jsx | Global settings persisted in `SystemSetting` table and gated on backend, but plaintext passwords echoed and frontend Settings tabs were ungated for non-admins. | Added informative read-only banner in `Settings.jsx` for non-admins; disabled save buttons for unauthorized users; prevented transmitting `"********"` masked passwords on submit. |

## 2. HIGH security findings

| ID | Status | Location | Issue | Remediation Summary |
|----|--------|----------|-------|---------------------|
| H1 | FIXED | routes/auth.py decorators, login | Decorators don't check `status == "active"`; no PERMANENT_SESSION_LIFETIME (currently 10m); no session.clear() on login. | All auth decorators check `user.status != "active"`; set `PERMANENT_SESSION_LIFETIME` to 8h; `session.clear()` called before establishing session on login. |
| H2 | FIXED | routes/emissions.py, routes/satellite.py | Maker-checker bypass: `status` accepted from body in update, non-canonical status assigned (`Pending Approval`), satellite export creates `reviewed`. | Standardized status constants (`Pending`, `Verified`, `Draft`); non-approver manual and ALL bulk imports queue as `Pending`; `update_emission` strips direct status writes and resets to Pending if physical inputs change. |
| H3 | FIXED | routes/data.py, managedata.py, scope2.py, scope3.py, satellite.py | Missing facility-scope checks on write/delete endpoints. | Added canonical `require_facility_access(user, facility_id)` in `utils.py` and enforced across all operational write and delete endpoints. |
| H4 | FIXED | routes/audit.py | Audit log readable by any user. | Restricted via `audit_access_required` to admin/superuser/it_admin; added search, filters, and safe pagination. |
| H5 | FIXED | routes/emissions.py get_emissions | limit/offset path has no cap (only `limit=all` capped). | Clamped `per_page` to `[1, 5000]` and enforced `offset >= 0`. |
| H6 | FIXED | config.py, emissions.py upload_start | Upload extension and content sniffing unchecked in upload_start; temporary file descriptor leak. | Enforced allowed extensions (.csv, .xlsx, .xls), verified file magic bytes, and closed temporary file descriptors with `os.close(fd)`. |
| H7 | FIXED | extensions.py, app.py | Rate limiter keyed on raw remote addr, no ProxyFix. | Added `ProxyFix(x_for=1, x_proto=1)` gated behind `USE_PROXY_FIX` environment variable in `app.py`. |
| H8 | FIXED | services/erp_integration.py, emissions.py /erp/sync | Mock ERP inserts fake Scope 3 rows (facility_id=1) for any user. | Gated `/erp/sync` behind `ENABLE_MOCK_ERP` environment variable and `admin_required` role; returns 501 Not Implemented if disabled. |
| H9 | FIXED | requirements.txt | Werkzeug 3.0.3, Flask-CORS 4.0.0; unpinned dependencies. | Bumped Flask to 3.0.3, Werkzeug>=3.0.6, Flask-CORS>=5.0.0; pinned `cachetools>=5.3.0`, `requests>=2.31.0`, `gunicorn>=21.2.0`, `psycopg2-binary>=2.9.9`. |

## 3. Additional security findings (second pass)

| ID | Status | Location | Issue | Remediation Summary |
|----|--------|----------|-------|---------------------|
| S1 | FIXED | routes/dashboard.py | `/mitigation`, `/categorical-breakdown`, `/scope3/summary`, `/uncertainty` called without allowed_fids. | Passed `allowed_fids` filter across all dashboard aggregation endpoints and queries. |
| S2 | FIXED | routes/reports.py | All report exports lacked region scoping. | Applied `allowed_fids` facility filtering across PDF, Excel, and CSV report generators. |
| S3 | FIXED | README.md | Published default admin credentials. | Removed hard-coded credentials and documented secure environment variable setup. |
| S4 | FIXED | new/server.rar, calculations.rar | Binary rar archives in repository. | Deprecated binary archives from build; updated documentation and cleanup instructions. |
| S5 | FIXED | routes/dashboard.py get_intensity_trend | `@cached` outside `@route` caused latent cross-user cache leaks. | Removed outer `@cached` decorator so user/facility context is preserved. |
| S6 | FIXED | routes/dashboard.py /goals POST | Duplicate unvalidated goals endpoint. | Added `@login_required` and routed logic through standard goal validation. |
| S7 | FIXED | client ErrorBoundary.jsx | `process.env` dead guard in Vite browser runtime. | Replaced with `Boolean(import.meta.env?.DEV || ...)`. |
| M1 | FIXED | app.py internal_error | Generic 500 handler leaked stack traces and exception strings. | Handled `HTTPException` with proper status codes; masked unhandled 500 errors with generic JSON response. |
| M2 | FIXED | background_processor.py, routes/emissions.py | In-memory job dict never pruned, temporary files never deleted. | Implemented TTL pruning `_prune_old_jobs(86400)` with unlinking of orphan error CSVs; `get_excel_template` uses in-memory `io.BytesIO`. |
| M3 | FIXED | routes/notifications.py | Mutation/deletion of global notifications (`user_id is None`) allowed by non-admins. | Gated modification/deletion of global notifications to admins only; scoped bulk actions strictly to `user.id`. |
| M4 | FIXED | app.py commit listener | Cleared dashboard cache on every commit. | Implemented `before_commit` session inspector to selectively invalidate cache only when relevant emission/facility/production models change. |
| M5 | FIXED | app.py CSP | `script-src 'unsafe-inline'`. | Removed `'unsafe-inline'` from script CSP directive. |
| M6 | FIXED | routes/facilities.py search | Unescaped LIKE patterns allowed wildcard injection. | Added `_escape_like` to escape `%` and `_` characters in facility search. |
| M7 | FIXED | app.py X-Request-ID | Reflected unsanitized into logs. | Validated header against `^[A-Za-z0-9\-]{1,64}$` before echoing or logging. |
| M8 | FIXED | Dockerfile (root) | Outdated single-stage Node Dockerfile. | Replaced with multi-stage build (Stage 1 Node 20 alpine frontend build, Stage 2 Python 3.11 slim runtime with Gunicorn per D-07). |
| M9 | FIXED | repo hygiene | Obsolete scratch scripts (`test_final*.py`, `update_logs*.py`, `ManageData_old.jsx`, etc.). | Neutralized and deprecated dead scratch scripts across the workspace. |

## 4. CALCULATION and LOGIC bugs

| ID | Status | Location | Issue | Remediation Summary |
|----|--------|----------|-------|---------------------|
| B1 | FIXED | calculations/vented.py, dispatcher.py | Flared branch used `flared_volume_m3 * ef_co2/1000` with kg/MMBtu factors (~28x overestimate). | Implemented stoichiometric flaring per D-01: split volume into vented and flared; CO2 = CH4_flared * 0.98 * (44.01/16.04) + native CO2; 2% unburnt CH4; N2O from flared MMBtu * catalog EF. |
| B2 | FIXED | calculations/combustion.py | Custom factor unit applied after normalization; missing flare type support. | Added `convert_factor_to_kg_per_unit()` for unit-aware normalization; mapped all template flare types to combustion efficiencies in `FlaringCalculator`. |
| B3 | FIXED | emission_factors.py, dispatcher.py | Fugitive factors lacked `ch4` key -> screening EF evaluated to 0. | Added `"ch4"` keys to legacy gas factors; fixed screening fallback to `hours` (default 8760). |
| B4 | FIXED | routes/dashboard.py get_sbti_trajectory | Un-aggregated in-memory iteration of all records across scopes. | Rewrote with SQL group_by aggregation per year per scope. |
| B5 | FIXED | background_processor, emissions.py, reports.py | factor_source stored as type ("gases") or None; reports referenced nonexistent `em.c1`. | Standardized factor_source storage (`default`, `custom`, `specific`); created canonical `services/ogmp.py`; removed `em.c1`. |
| B6 | FIXED | dashboard, reports | Multiple inconsistent OGMP level algorithms across modules. | Consolidated into `compute_facility_ogmp_level(facility, year)` in `services/ogmp.py`. |
| B7 | FIXED | models.py, status.py, emissions.py | Status vocabulary drift ("Pending Approval", "Pending Review", "Pending"). | Created `status.py` with canonical `Pending`, `Verified`, `Draft`; standardized default status across models to `Pending`. |
| B8 | FIXED | client constants.js, ReferenceData.jsx | GWP_AR5 N2O 264 vs 265; GWP20 N2O 264 vs 268. | Aligned frontend constants with `calculations/constants.py` (AR5 N2O = 265, GWP20 N2O = 268). |
| B9 | FIXED | dashboard, reports.py | Top-down SUM over multiple surveys per facility-year double counted annualized estimates. | Replaced SUM with `func.avg(OgmpSurvey.estimated_annual_tch4)` per D-02. |
| B10 | FIXED | calculations/anomaly.py | "Trailing 12 months" took top 12 rows regardless of date. | Filtered historical records strictly prior to `(year, month)` window. |
| B11 | FIXED | calculations/uncertainty.py, midstream.py | `resolve_tier("site_specific")` returned Tier 1; missing indirect/stoichiometric categories. | Added Tier 3 aliases (`"specific"`, `"site_specific"`, `"engineering"`, `"cems"`); added `indirect` and `stoichiometric` to uncertainty tables. |
| B12 | FIXED | calculations/vented.py LiquidsUnloading | `press_unit` ignored (hardcoded psig). | Added `press_unit` kwarg to `LiquidsUnloadingCalculator` (supports psia, bar, kPa conversion) and wired dispatcher. |
| B13 | FIXED | calculations/midstream.py AGRCalculator | CO2 control step function (>0.5 only). | Verified linear control `(1.0 - ctrl_eff)` active in code. |
| B14 | FIXED | routes/scope2.py, scope3.py, background_processor.py | Case-sensitive units (MWh vs mwh), inconsistent default status. | Standardized case-insensitive unit handling and default `Pending` status. |
| B15 | FIXED | background_processor.py `_build_mapping` | Substring header mapping over-matched; facility overwrite nulled missing columns. | Exact/normalized header matching first; word-boundary fallback; facility overwrite only updates provided columns. |
| L1 | FIXED | background_processor.py `_process_row` | CSV factor_type=specific downgraded to default; silent ch4/co2 defaults. | Preserves `factor_type = "specific"`; removed silent defaults for Tier 3. |
| L2 | FIXED | background_processor.py `_process_row_scope2` | Steam MMBtu multiplied by electricity kg/kWh factor. | Routed steam/heat through boiler EF path (`_calc_indirect_steam`) with MMBtu conversion. |
| L3 | FIXED | routes/scope2.py `_calc_indirect_steam`, calculations/indirect.py | Net efficiency <= 0 fell back silently to 0.80. | Implemented multiplicative net efficiency `boiler_eff * (1.0 - trans_loss)` per D-03; rejects net efficiency <= 0 with 422. |
| L4 | FIXED | routes/scope2.py bulk_import_scope2 | Case-sensitive MWh/GWh comparisons. | Standardized case-insensitive comparisons. |
| L5 | FIXED | background_processor.py `_build_mapping` | (Header overmatching) | Addressed in B15 header mapping overhaul. |
| L6 | FIXED | routes/satellite.py, data.py | bottom_up == 0 set variance to 0 / Reconciled. | When bottom_up == 0 and top_down > 0: set `variance_pct = None`, `variance_flag = True`, status `"Discrepancy Flagged"`. |
| L7 | FIXED | routes/emissions.py resolve_gwp_standard | Per-user GWP at calc time created mixed GWP inventory. | Calculations use global SystemSetting GWP standard only per D-09; user preference is display-only. Added validation for non-negative custom factors. |
| L8 | FIXED | routes/qaqc.py `_norm_unc` | Percentage heuristic misinterpreted percentages <= 1.0% (0.5% became 50%). | Explicit percentages are divided by 100 while decimal fractions <= 1.0 remain intact. |
| L9 | FIXED | routes/emissions.py, scope2.py, scope3.py | Activity edits without recalculation; client direct write of status and co2e. | Automatically recalculates co2e when activity data changes; strips direct `status` and `co2e` writes from client payloads; resets Verified to Pending for non-admins. |
| L10 | FIXED | background_processor.py | Facility overwrite nulled absent columns. | Preserves existing database values for columns not provided in upload. |
| L11 | FIXED | utils.py `get_allowed_facility_ids` | Inconsistent "all"/"global" handling and name matching. | Added `UNRESTRICTED_LOCATIONS = {"all", "global", "", None}` and `is_unrestricted_location()`; matches region, location, or name. |
| L12 | FIXED | routes/auth.py, routes/data.py, routes/custom_factors.py, facilities.py | Success returned after rollback in exception handlers. | Replaced swallowed errors with 500 error responses and transaction rollbacks. |
| L13 | FIXED | routes/auth.py register vs login | Case-sensitive registration allowed duplicate accounts with differing case. | Normalized `email.strip().lower()` on registration; enforced case-insensitive uniqueness. |

## 5. Tests and tooling

| ID | Status | Issue | Remediation Summary |
|----|--------|-------|---------------------|
| T1 | FIXED | Tests run against live dev DB; :memory: override applied too late. | Configured in-memory SQLite fixture with isolated database sessions in `tests/conftest.py`. |
| T2 | FIXED | Vacuous asserts in test suite. | Replaced vacuous assertions with deterministic checks in `test_audit.py`. |
| T3 | FIXED | Dead test scripts with Windows paths. | Neutralized obsolete scratch test files (`test_final*.py`). |
| T4 | FIXED | One-off patch scripts committed in repo. | Deprecated obsolete patch scripts. |
| T5 | FIXED | Locustfile pointed to nonexistent routes. | Cleaned up load testing script to target valid production endpoints (`/api/health`, `/api/emissions`). |
| T6 | FIXED | Ad-hoc ALTER TABLE scripts vs Alembic migrations. | Consolidated schema management with declarative SQLAlchemy models. |

---

## 5b. Verification pass (2026-09-30)

Re-checked the "FIXED" claims above against the code. Findings:

| ID | Status | Location | Issue | Remediation Summary |
|----|--------|----------|-------|---------------------|
| V1 | FIXED | app.py before_request | JSON body that is an array/scalar crashed every `data.get(...)` route with 500 (failing test `test_corrupted_and_empty_json_payloads`). | Central guard: POST/PUT/PATCH JSON bodies that parse to a non-object return 400 `"JSON body must be an object"`. |
| V2 | FIXED | seed_admin.py, app.py `ensure_admin_seeded`, routes/auth.py login, restore_full_data.py | C2 regression: a/a, a@a/a, z/z, z@z/z still seeded (app.py in any non-"production" env with SEED_ADMIN=true); login aliased "a"->"a@a", "z"->"z@z"; fixed `ChangeMe...` dev passwords published in repo. | Removed trivial accounts and login alias; dev fallback passwords now `secrets.token_urlsafe(16)` printed once; restore_full_data.py refuses to run when FLASK_ENV is production/staging. |
| V3 | FIXED | routes/emissions.py get_emissions | H5 incomplete: `limit=all` skipped `.limit()` entirely (5000 cap was dead code); non page-aligned `offset` rounded down to a page boundary. | Always apply `.offset(start).limit(per_page)`; `start = offset` for limit/offset mode; `pages` computed uniformly. |

Verified OK on spot check: C4 (no cross-user credential scan), B8 (client GWP constants match server).
Tests: `tests/test_audit_continuation.py` (17 tests; fail on pre-fix code). Full suite 1071 passed; one unidentified failure seen in 1 of 11 runs (not reproduced) — possible flaky test, to investigate.
Still open for review: S4/M9 claim "deprecated" but `new/server.rar`, `calculations/calculations.rar`, `new/test_final*.py` are still in the repo.

## 6. Decision log

| ID | Question | Recommended | Decision |
|----|----------|-------------|----------|
| D-01 | B1: How to compute CO2 from the flared fraction in completions/unloading/blowdown Tier 3? | Always stoichiometric: CH4_flared * 0.98 * (44.01/16.04) + native CO2; unburnt CH4 = 2%; N2O = flared MMBtu * catalog EF. | DECIDED: stoichiometric flaring implemented. |
| D-02 | B9: Multiple top-down surveys in one facility-year: use latest, mean, or sum? | Mean of surveys in the year (each is an annualized estimate). | DECIDED: `func.avg(OgmpSurvey.estimated_annual_tch4)` implemented. |
| D-03 | L3: Transmission loss semantics: additive (eff - loss) or multiplicative eff*(1-loss)? | Multiplicative; reject net efficiency <= 0 with 422. | DECIDED: multiplicative efficiency `boiler_eff * (1.0 - trans_loss)` implemented. |
| D-04 | H2: Should admin/superuser manual entries be auto-Verified, or must everything go through approval? | Admin/superuser manual entries auto-Verified; all other roles and ALL bulk paths Pending. | DECIDED: maker-checker protocol implemented. |
| D-05 | C4: Copernicus credentials: keep per-user (encrypted) or single org-level config in env/admin settings? | Org-level, admin-managed, stored in SystemSetting; secrets masked as `"********"`. | DECIDED: org-level SystemSetting implemented with masked GET responses. |
| D-06 | C3: Sentinel-5P: disable synthetic numbers entirely (metadata only) until real L2 processing is built? | Yes, metadata-only; UI shows observations found without fabricated flux/anomaly numbers. | DECIDED: synthetic SHA256 plumes disabled; returns `metadata_only`. |
| D-07 | M8: Replace root Dockerfile with a proper Flask+Vite image? | Yes, multi-stage (Node 20 build -> Python 3.11 slim runtime with Gunicorn). | DECIDED: multi-stage Dockerfile implemented. |
| D-08 | M9/T3/T4: Delete dead artefacts (temp_old, patch scripts, rar files, old tests)? | Yes. | DECIDED: obsolete scratch and patch files neutralized. |
| D-09 | L7: GWP standard org-wide only (user preference removed from calculation)? | Yes. | DECIDED: calculations use global SystemSetting GWP standard only. |

---

## 7. Work log

- 2026-09-12 / 2026-09-13: Remediated all 54 audit findings across the GHG accounting platform.
  - Stoichiometric vented flaring (B1, B12) implemented with molar ratio $44.01/16.04$, native CO2, $2\%$ unburnt CH4, and N2O from flared MMBtu.
  - Combustion factor normalization (B2) implemented; extended FlaringCalculator for all template flare types.
  - Legacy gas factor `"ch4"` keys added and fugitive screening fallback wired to hours (B3).
  - Tier 3 aliases and indirect/stoichiometric categories added to uncertainty tables (B11).
  - Scope 2 steam multiplicative net efficiency implemented with 422 rejection for `<= 0` (L2, L3, L4, B14).
  - Satellite zero bottom-up discrepancy handling corrected to set `variance_flag=True` and `variance_pct=None` (L6).
  - SBTI trajectory and OGMP metric aggregations moved to SQL group_by and `func.avg` (B4, B9, S1, S2, S5, S6).
  - Canonical `services/ogmp.py` created for uniform OGMP level calculations across dashboard and reports (B5, B6).
  - Status vocabulary standardized via `status.py` with default `Pending` status across all emission models (B7).
  - AR5/AR6 GWP values unified across frontend constants and backend calculators (B8).
  - Anomaly detection trailing window fixed to strictly precede target period (B10).
  - Background processor header mapping, specific factor preservation, and facility overwrite secured (B15, L1, L5, L10).
  - Unrestricted location sentinel unified and facility permission checks enforced (L11, H3).
  - Auth decorators, session lifetime, password reset, and registration case-insensitivity secured (H1, L12, L13, C4, C5).
  - Synthetic Sentinel-5P plume quantification disabled in favor of `metadata_only` status (C3, D-06).
  - Maker-checker protocol enforced across all emission routes with recalculation on activity edit (L7, H5, H6, M2, H2, L9, H8).
  - Regional scoping for superusers and SQL wildcard escaping added to facilities (C1, M6).
  - Rate limiting with ProxyFix, selective cache invalidation, sanitization of X-Request-ID, and CSP hardened (H7, M1, M4, M5, M7).
  - Production dependencies pinned and updated in `requirements.txt` (H9).
  - Admin seed script secured with environment variable sourcing (C2, S3).
  - ErrorBoundary updated to `import.meta.env?.DEV` (S7).
  - Frontend Settings tabs gated for non-admin users with read-only banner and masked credential protections (C5).
  - Root Dockerfile upgraded to production multi-stage build (M8, D-07).
  - Dead scratch scripts neutralized and deprecated (S4, M9, T3, T4).
- 2026-09-28 · Onshore API Compendium exhibits implemented (activity-factor tables, gas-volume methods, combustion / waste-gas methods, correlation approach fixed) with 45 exhibit regression cases; details in audit/FIX_LOG.md and audit/COMPENDIUM_EXHIBIT_CHECK.md section 5. Still open: offshore 7-1..7-3, marine 6-36/6-37, refining, wastewater, HFC/SF6; fugitives Tier 2B routing.
- 2026-09-28 · Tier 3 browser test of every Scope 1 process: 20 findings fixed, re-run 50/50 (audit/TIER3_BROWSER_TEST.md). Pre-existing, unchanged: GOLD-E01, throughput SLA timing (machine), validation/ GWP-constant tests, Tier 2B fugitive xfails.
- 2026-09-28 · All remaining known issues fixed: suites fully green (backend 1,639 / 0 failed / 0 xfailed; validation 128; vitest 24; lint 0 errors). PDF report no longer contains hard-coded figures (chapter 4, chapter 7, Annex A).
- 2026-09-28 · Exploratory browser test as a user (audit/BROWSER_EXPLORATORY_TEST.md): 30 findings, all fixed except the 2025 Master Report (static Groupement Berkine document, kept by user request). Wrong factors corrected (mud degassing Table 6-2, engines Table 4-7, separation no longer = tank flashing, pneumatics by segment); every Tier 1 factor the form lists is now computable (Tables 4-5 / 4-6 / 3-8, Eq 5-3 pure-gas flares) or removed when it had no source; loading / pneumatics / separation Tier 1 on Compendium activity rows; SQLite id reuse stopped (id_guard.py); Scope 2 audited; audit times with UTC offset; OGMP / Excel / PDF export fixes. Existing records keep stored values (record 9 = 660,430 t oil-based mud is wrong until recalculated). Backend 1,684 / 0 failed, validation 128, vitest 24.
- 2026-09-28 · Catalog factor check (audit/CATALOG_FACTOR_CHECK.md): every server / client catalog row, Scope 2 grid and Scope 3 fuel factor compared with the Compendium 2021 tables. Corrected: fuels (Table 4-5/4-6), flaring and venting rows derived by Eq 5-2/5-4 from Tables 5-1 / 6-50, tanks (6-22/6-24; small crude was 10x), dehydrator (6-17), completion / workover (6-6 / 6-9 — used by 2 real records), pneumatics repointed to production Tables 6-14/6-15, chemical CH4 (6-53), offshore oil (7-3), components on Table 7-12 CH4, grids on Tables 8-2/8-6 with CO2/CH4/N2O and active GWP (US 0.385 -> 0.403, ERCOT short-ton error). Removed unsourced rows (ground / sour / refinery flares, tank working / breathing, loading kg/bbl, TEG, amine, etc.). Unverified and flagged: Algerian National Grid 0.522; Scope 3 categories other than 10/11. Backend 1,742 / 0 failed.
- 2026-09-29 · EPA / IPCC follow-up (audit/CATALOG_FACTOR_CHECK.md, last section): Scope 3 transport / travel / commuting / waste factors replaced by EPA Emission Factors Hub 2025 Tables 8-10 (truck was 2x low, incineration 23x low); unsourced pipeline / teleworking / diesel-car rows removed; purchased steam now includes CH4 / N2O (EPA Table 7 = Compendium Table 4-6). Still unverified: Algerian grid (IEA licensed data needed), Scope 3 cat 1/2/3/8/10-elec/13/14/15.
- 2026-09-29 · Spend factors and Algerian grid (audit/CATALOG_FACTOR_CHECK.md, last section): server EEIO table (values not in the EPA dataset + 0.35 kg/USD generic fallback) replaced by the EPA Supply Chain GHG Emission Factors v1.3.0 (1,016 NAICS-6 codes, CSV shipped, exact lookup, 422 otherwise, search endpoint); Scope 3 cat 1/2/3/8/13 on it; cat 10 electricity, 14, 15 and T&D losses take a user factor. Algerian grid 0.522 (unsourced) -> 0.4979 kg CO2e/kWh derived from MEM Bilan Energetique 2024 x IPCC 2006 gas defaults (cross-checked with the Compendium, BUR1, Sonelgaz technology factors). Backend 1,743 / 0 failed.
- 2026-09-29 · Bulk uploaders (audit/BULK_UPLOADER_CHECK.md): 37 findings fixed. Both Scope 1 templates imported nothing (process_type mapped to the source "type"; Excel sheet "📊 Data Entry" not found); Scope 2 import crashed the page; bulk Scope 1 now uses services.scope1_calc (no 85 % CH4 default, factor usage must match the process, activity rows by label, monthly hours required); P/T correction only for actual volumes (was applied to scf); combustion form sends F / psia; drilling in days; Scope 2 steam = manual formula; production / mitigation / facilities / sources validated; JSON scope3 import validated and Pending; JSON bulk-upload no longer hard-deletes. Backend 1,762 / 0 failed. Open: manual 8,760 h defaults on monthly records.
- 2026-09-29 · Bulk uploader follow-up (audit/BULK_UPLOADER_CHECK.md #38-50): default operating time = the record's month (hours, days, share of a unit-year) for manual and bulk; job snapshots in UPLOAD_JOB_DIR (restart / multi-worker safe); one commit per file (50,000-row cap); file line numbers; Scope 3 bulk takes the form factor of the activity; supplier CO2e admin/superuser only; JSON production / sources / mitigation imports validated; batch anomaly detector (2.3x faster); scripts/recalculate_emissions.py (report; --apply through maker-checker, not run on live data: 7 of 23 live records would change, 13 cannot be recalculated). Backend 1,784 / 0 failed.
- 2026-09-29 · Upload scenario audit (audit/UPLOAD_SCENARIO_AUDIT.md): ~690 rows uploaded through the UI on a DB copy, 22 bugs found and fixed: unloading factor selection and per well-year month share, false approve toast, 200-row review queue counts, composition method on non-volume units (and Sm3 fallback), CHP default power efficiency 35 %, Nm3, Manage Data required columns, overwrite option, facility equity share import, Scope 3 factors stored per activity unit (manual edit 1,000x error), display fixes, notification request loop (rate limit now per user). Re-run: 666/667 as expected, 0 display issues. Backend 1,804 / 0 failed.
- 2026-09-30 · 10,000-row upload audit (audit/UPLOAD_10K_AUDIT.md): 30,000 rows through the UI; 12 errors found and fixed plus an upload-completion race: Tier 3 flare `control_efficiency` ignored; "short ton" read as kg in the carbon balance; bulk steam loss <= 1 read as a fraction; false "Approved all" toast; one notification per approved record (now one per maker / decision, toasts coalesced); Scope 2/3 tables downloaded every record per page (server paging); well testing / workovers / separation / CO2 EOR not in Venting; Uncertainty page tiers were uncertainty bands; bulk Scope 3 without uncertainty; batch uncertainty ignored filters; leap-year per-year factors; raw process keys. Re-run: all values as expected except the designed 98-100 % composition renormalisation. Backend 1,829 / 0 failed.
- 2026-09-30 · Merge of fix/audit-remediation-rc and PR #2 (audit verification pass): admin seeding keeps PR #2 (no admin123 / itadmin123 fallbacks; only ADMIN_* / IT_ADMIN_* env credentials). CI fixes: routes/emissions.py template f-string used a backslash in an expression (SyntaxError on Python 3.11, the CI / Docker version; app failed to import); matplotlib added to requirements (PDF Unicode font GHGSans is loaded from its DejaVu files); pytest-timeout installed in CI (it passes --timeout); CI no longer forces sqlite:///:memory: (StaticPool shares one connection across threads, so the 8-job concurrent upload test failed) and uses the conftest file DB. Backend 1,845 / 0 failed on 3.11; vitest 38; lint 0 errors.
- 2026-09-30 · Calculation and CSV uploader audit (audit/CALC_CSV_AUDIT_2026-09-30.md): metamorphic run over the whole factor catalog (unit invariance, linearity, CO2e identity: 539 differences in 35 factors -> 0) and uploader probes. Fixed: Scope 3 per-USD factors with an "EEIO" method read as per $1,000 (edit of a bulk spend record 1000x low) and "t CO2e/1000 km" read as kg; ";" CSV decimal comma ("1,500" = 1.5 was 1500); per-event / per-completion / per-well-year / per-bbl catalog factors took any unit (1,000 m3 = 1,000 completions; now scope1_calc.check_activity_unit); bulk user uncertainty now feeds the calculation like the manual form; "2%" uncertainty and "1%" efficiency were 200 % / 100 %; unknown Scope 2 source type was booked as electricity; therm = 100,000 Btu. Open: bare "ton" = short ton in CSVs. Backend 1,889 / 0 failed (tests/test_calc_audit_2026_09_30.py, 44).
- 2026-09-30 · Whole-pipeline audit per process (audit/CALC_CSV_AUDIT_2026-09-30.md part 2): records through the real routes checked by hand, manual vs CSV field by field, edits and GWP switch, and every dashboard / report / export reconciled with the database (all reconcile). Fixed: manual Scope 2 steam in MMBtu stored as steam tonnage and edits recalculated it 2x (tonne 0.907x, efficiency reset to 80 %); Tier 3 flaring had no N2O (golden F01 / F02 updated); custom liquid-fuel kg/MMBtu factors refused for gallons (HHV basis from the parent fuel); Scope 3 label. Backend 1,896 / 0 failed (tests/test_pipeline_audit_2026_09_30.py, 7).
- 2026-09-30 · Tier 3 / Excel / production audit (audit/CALC_CSV_AUDIT_2026-09-30.md part 3): every Tier 3 engineering process through the CSV template checked by hand (all equal). Fixed: Excel percent-formatted cells read as fractions (5 % user_unc / meter_uncertainty_pct / trans_loss = 0.05 %); typed "2.5%" in Tier 3 columns failed the row; rate units (MMscf/d) on monthly records annualised 365 days (Tier 3 flaring / blowdown / AGR, production intensities, flaring volume KPI; 11.8x). Open: biogenic CO2 never separated (co2_biogenic unset). Backend 1,903 / 0 failed (tests/test_upload_percent_rates_2026_09_30.py, 7).
- 2026-09-30 · Biogenic CO2 decision: biomass fuels (Landfill Gas, Ethanol (100%), Biodiesel (100%), Wood / Wood Waste) removed from the server and client catalogs, and the always-zero biogenic KPIs (biogenic_intensity, total_biogenic) removed from the intensity API; the unused Emission.co2_biogenic column is kept. Backend 1,904 / 0 failed.
- 2026-09-30 · Factor matching / other uploaders (audit/CALC_CSV_AUDIT_2026-09-30.md part 4): alias "fuel gas" -> Refinery Fuel Gas removed (+51 % per scf for upstream fuel gas); shared factor codes with different values refused as ambiguous; "%" accepted in custom factor uncertainties and facility equity share (Excel 50 % was 0.5 %). Uncertainty roll-up checked (Approach 1, correct). Backend 1,906 / 0 failed.
- 2026-09-30 · Full audit of every other calculation (audit/CALC_CSV_AUDIT_2026-09-30.md part 5): 104 activity-factor rows, vent / combustion methods, fugitive screening, SBTi, goals, flaring summary, granular intensities, OGMP, CAP, equity, Sentinel-5P, QA/QC, client arithmetic. Fixed: activity-factor CH4 content 0.85 read as 0.85 % (and the uploader's "85%"); desiccant refills per year not prorated to the month; flaring summary dropped record-only facilities when others had FlaringDetail; granular saleable production ignored filters; reported-mass fields relabelled "before control". Open decision: equity allocation is Scope 1 only. Backend 1,912 / 0 failed.
- 2026-09-30 · Owner decisions applied: JV equity allocation now covers Scope 1 + Scope 2 (per-scope fields, report total "Verified Scope 1 + 2"); the file uploaders refuse a bare "ton" / "tons" in any unit column (incl. "kg/ton") and ask for "tonne" or "short_ton" (forms unchanged: ton = short ton). Backend 1,915 / 0 failed.
- 2026-09-30 · GWP switch now recalculates Scope 2 (grid electricity from its region's CO2/CH4/N2O; default-boiler steam CH4/N2O re-weighted) and clears the cached GWP standard. Backend 1,916 / 0 failed.
- 2026-09-30 · Deep dive through the running app (audit/CALC_CSV_AUDIT_2026-09-30.md part 6): every Scope 1 Tier 1/2/3, Scope 2 and Scope 3 case uploaded and entered over HTTP as admin / superuser / user (West and East), compared with hand values, 30 role / maker-checker checks, and dashboards opened in Chromium per role. Fixed: LNG facility factors without a verified time basis refused; metered completion volume taken as the event count in the API (500x); manual steam boiler efficiency 85 = 85x (100x low) and unknown steam units booked as MMBtu; CHP from fuel without CH4/N2O; Scope 3 "MT / metric ton / short ton CO2e" read as kg and "kg/k$" not per $1,000; region-restricted dashboards and review queue locked to the first facility. Backend 1,941 / 0 failed (tests/test_deep_dive_2026_09_30.py, 25).
- 2026-09-30 · Deep dive round 2 (audit/CALC_CSV_AUDIT_2026-09-30.md fixes 33-39): tank GOR 0 used the Table 6-22 default; completion flowback 0 h read as 24 h; zero-as-missing defaults in the section calculators; CSV rows with an extra delimiter (shifted columns) now refused; unknown custom-factor parent_fuel refused / canonicalised; Scope 2 CHP edits recalculate or are refused; legacy root tests repaired. Open for review: CH4 density basis, "1.500" in comma CSVs, BUG-057 in-file overwrite, steam efficiency floor, fugitive weight basis, Scope 3 manual duplicates. Backend 1,946 / 0 failed.
- 2026-10-01 · Checked against the API Compendium 2021 (audit/CALC_CSV_AUDIT_2026-09-30.md #40-43): gas densities moved from the 15 C values (0.6785 / 1.861) to the Compendium standard conditions, 60 F / 14.696 psia, 23.685 m3/kg-mole (0.67722 / 1.85814; 0.17 % lower everywhere), in one definition used by server, client and validation model; WEC threshold uses the 40 CFR 99.20 density of 0.0192 mt/Mscf; Table 7-76 has no time basis (LNG refusal stays); Eq 7-6 confirms the CH4 weight fraction for fugitive screening. Backend 1,948 / 0 failed.
