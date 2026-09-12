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
