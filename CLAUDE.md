# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Layout

GHG (greenhouse-gas) accounting platform. The real application lives in `new/`:
- `new/server` — Flask 3 API (SQLAlchemy, Flask-WTF CSRF, Flask-Limiter, Redis)
- `new/client` — React 19 + Vite 7 SPA

Loose root scripts and scratch files live in the git-ignored `archive/` (local only, never committed). Git history was purged on 2026-10-15 of every file no longer in the tree (repo cleanup): deleted files, old audit artifacts and `AUDIT_MEMORY.md` are not recoverable from git; the full pre-purge history is in the offline bundle `h2-backup-2026-10-15.bundle` (outside the repo).

Other root dirs: `docs/` (`calculation-specification.md`, `validation-report.md`, `ui-modernization-plan.md`), `validation/` (extra calculation tests collected by the root `pytest.ini`), `.agents/` (tooling rules/workflows, not app code).

## Commands

Backend (run from `new/server`):
```bash
pip install -r requirements.txt
python app.py                      # 127.0.0.1:5000 (PORT env); debug only if FLASK_DEBUG=true
python seed_admin.py [--force-reset-password]   # uses ADMIN_EMAIL/ADMIN_PASSWORD/IT_ADMIN_*
```
Setting `SEED_ADMIN=true` also seeds the admin and IT-admin accounts on startup (an existing account is left unchanged, including a disabled one). `seed_admin.py` creates the optional IT support account (role `it`) only when both `IT_EMAIL` and `IT_PASSWORD` are set.

Database Management & Migrations (run from `new/server`):
```bash
flask db upgrade                   # run Alembic migrations up to head (6a8475783b53)
python scripts/backup.py [--output-dir DIR]              # PostgreSQL (pg_dump --clean) or SQLite; default dir $BACKUP_DIR or ./backups, keeps the newest $BACKUP_RETAIN_COUNT (14)
python scripts/restore.py <path/to/backup.sql> --apply   # without --apply: dry run; PostgreSQL restores in one transaction and stops at the first error (nothing changes on failure)
```

Backend tests (run from `new/server`):
```bash
python -m pytest tests/
python -m pytest tests/test_combustion.py::<test_name> -q     # single test
python -m pytest -x --timeout=300                            # CI test run
```
- `new/server/pytest.ini` also collects `test_*.py` in the server dir itself (ignoring `test_runner.py`). The root `pytest.ini` runs from the repo root and additionally collects `validation/`.
- `python scripts/loc_ratchet.py --check` (CI gate, reworked 2026-10-16): a function in `routes/`, `calculations/`, `services/` or `background_processor.py` may have at most 150 lines and a file at most 800; the ones already longer are recorded in `scripts/loc_baseline.json` and may only shrink (files under 800 lines may grow). After shrinking one, lock it in with `--write`.
- `tests/conftest.py` sets `FLASK_ENV=testing`, uses a temporary `tests/test_app.db`, sets `SEED_ADMIN=false`, turns off CSRF and turns off the rate limiter.
- `new/server/requirements.txt` includes `pytest`, `pytest-timeout`, `hypothesis`, `pytest-benchmark`, and `redis`.
- CI (`.github/workflows/deploy-pages.yml`) also runs these gate groups separately:
  - calculation: `test_independent_differential`, `test_golden_dataset_validation`, `test_property_invariants`, `test_unit_conversions_exhaustive`, `test_battery_gwp_horizons_regulatory`, `test_gwp_uncertainty_propagation`
  - security: `test_api_security`, `test_deep_injection_matrix`, `test_it_role_security`, `test_security_hardening`
  - smoke: `test_production_smoke`

Frontend (run from `new/client`):
```bash
npm run dev      # :5173, proxies /api -> 127.0.0.1:5000
npm run build
npm run lint     # ESLint 9 (0 errors)
npm run typecheck   # tsc --noEmit (client is migrating to TypeScript)
npm run check:ts    # fails on any .js/.jsx under src/ (TypeScript only)
npm run lint:css    # stylelint on src/styles, src/ui, src/app
npm run ui:metrics -- --check   # UI metrics ratchet (baseline: ui-metrics.baseline.json)
npm run test     # vitest + jsdom; only picks up src/**/*.{test,spec}.*
npx vitest run src/__tests__/<file>          # single file
npm run e2e      # Playwright (e2e/)
npm run e2e:smoke   # Tier 1 critical-path specs; e2e:full runs e2e/deep_user_audit/
```
Playwright needs the dev server running (`E2E_BASE_URL`, default `http://127.0.0.1:5173`) and `storageState.json`; `playwright.config.js` uses a local chromium-1208 if present, else the managed browser.

CI: `deploy-pages.yml` runs the backend gate groups above plus frontend `lint`, `check:ts`, `lint:css`, `ui:metrics -- --check` and `test`, then runs the production build (it no longer deploys to GitHub Pages). `e2e-matrix.yml` runs the Playwright smoke tier (21 tests) on pushes and pull requests: CI seeds the `a@example.test`/`a` test sign-in (`scripts/seed_e2e_user.py`, refuses to run in production) and sample data (`seed_showcase_data.py`), then saves the login with `generate_storage_state.js`. `seed_e2e_user.py` also creates the `itadmin@sonatrach.dz` (it_admin) and `operator@sonatrach.dz` (user) sign-ins the full matrix uses; never run it against a database you care about, because it overwrites those accounts' passwords and roles. The full matrix (`e2e:full`, 124 tests in `e2e/deep_user_audit/`) is **manual-only** (`workflow_dispatch`); it ran green (all but one test, then that one was fixed) in a clean Docker clone. Its CI job still raises `LOGIN_RATE_LIMIT` for the test backend; since 2026-10-09 only failed sign-ins count against it (`RATELIMIT_ENABLED` is not read by the backend). Specs read `E2E_BASE_URL`; do not hard-code `localhost` (IPv6-first hosts cannot reach the IPv4-only dev server). To reproduce CI locally, run the same commands in `python:3.11` / `node:20` containers against a fresh clone (this is how a missing `psutil` dependency was found); a clean clone also catches files that exist only on your machine.

Deployment (`deploy/`, guide `docs/deployment.md`): one multi-stage `deploy/Dockerfile` (targets `app` = gunicorn API on `python:3.11-slim`, non-root, PostgreSQL 16 client tools; `web` = nginx with the built SPA), `deploy/compose.yml` (db, redis, app, web; secrets from `deploy/.env`, see `.env.example`), `deploy/nginx/neocarbon.conf.template` (SPA and `/api` on one address, TLS, CSP; also used by the native install), `deploy/native/` (systemd units, `install.sh` for installs without containers), `deploy/release.sh <version>` (offline bundle: saved images, wheels, built SPA; `SKIP_BUILD=1`, `REGISTRY=...`), `deploy/smoke-test.sh` (checks a running stack through nginx; CI `.github/workflows/package.yml` builds the images and runs it). The API container's entrypoint runs `flask db upgrade` then gunicorn; `docker compose run --rm app seed-admin|backup|restore`. `LOG_FILE` sets the warning log (empty = console only; an unwritable path warns). nginx forwards `Host $http_host` so the HTTPS CSRF Referer check also works on a non-standard port.

On-premise install (no containers, no internet): `deploy/native/build-bundle.sh` builds an offline bundle (web build, server code, Linux wheels, checksums); `install.sh` / `upgrade.sh` in it set up `/opt/ghg` + systemd `ghg.service` (gunicorn) + nginx on one origin, with settings in `/etc/ghg/ghg.env` (`ghg.env.example`) and data in `/var/lib/ghg`. Guide: `docs/sonatrach/install-linux.md`. Run `build-bundle.sh` in WSL/Linux; never `npm ci` while a dev server is using `new/client/node_modules`.

Other: `new/setup.bat` / `new/start_all.bat` (Windows native launch scripts for Flask backend + Vite frontend).

## Backend architecture

- **`app.py` creates a module-level `app`, not a factory.** Tests use `from app import app`. Importing it has side effects: it runs `init_schema()`, creates indexes and optionally seeds admins. `init_schema()` upgrades the database to the Alembic head outside production (or with `AUTO_MIGRATE=true`) and refuses to start in production if the database is behind head (`AUTO_MIGRATE=false` disables the auto-upgrade). It does not call `db.create_all()`; only `seed_admin.py` and `build_csv_guide.py` do, and `schema_sync.py`'s docstring is out of date on this point.
- **Schema changes.** Alembic migrations (`migrations/`) manage schema evolution up to head revision `6a8475783b53` (optional `gas_composition` text on Scope 1/2/3 records and custom factors, `region` on Scope 3 records and custom factors, `facility_id` on custom factors; columns are added only when missing), after `d4e8a1b7c2f0` (audit log hash chain: `activity_log.prev_hash` / `entry_hash`, existing rows sealed, append-only trigger on PostgreSQL), after `c3f9a2d18e47` (`import_mappings`, saved import column mappings), after `b7e2d4c91a05` (`emissions.fuel_type` widened to 255) and `a6274c2ef1f5` (audit hardening and foreign keys). The earlier `b2d5f8e31a42` introduced Scope 2 dual-reporting columns, custom factor approval metadata, and composite indexes.
- **SQLite connect hook.** It enables WAL mode, foreign keys and `busy_timeout`, and runs periodic WAL checkpoints in development.
- **Config (`config.py`).**
  - SQLite `ghg_app.db` is permitted only in local development.
  - Production is detected from `FLASK_ENV`/`APP_ENV`/`ENVIRONMENT` and fails closed: only `development`, `dev`, `local`, `testing` and `test` (or unset) are non-production; any other value (`production`, `prod`, `staging`, `live`, ...) is production. Production strictly enforces PostgreSQL (`DB_TYPE=postgres`) and refuses to start without a real `SECRET_KEY` and a valid `DATABASE_URL`.
  - Production also refuses to start with an empty or `*` `ALLOWED_ORIGINS`, and without a shared rate-limit store (`REDIS_URL`; `ALLOW_MEMORY_LIMITER=true` opts out for a single worker). Only the listed origins are allowed: the GitHub Pages origin `https://kaljah.github.io` is no longer added (the Pages deployment and the `CORS_STRICT` switch were removed).
  - Code should read `app.config["IS_PRODUCTION"]`, not compare `FLASK_ENV` to `"production"`.
  - Config tests run `config` in subprocesses (`tests/test_config_safety.py`); production subprocess tests need `ALLOW_MEMORY_LIMITER=true` or a Redis URL.
  - `X-Forwarded-*` headers are trusted (`ProxyFix`) only when `TRUSTED_PROXIES` is set to the number of reverse proxies in front of the app (nginx = 1; `BEHIND_PROXY=true` means 1). Production logs a warning when it is unset; it is no longer enabled automatically in production (a client could forge its address).
  - Flask's `Content-Security-Policy` header (no external sources) covers API responses only; the web server that serves the built SPA must send its own.
  - The session cookie is `SameSite=Lax` (app and API on one address); set `SESSION_COOKIE_SAMESITE=None` only for a cross-site frontend.
- **Dashboard cache.** SQLAlchemy `before_commit`/`after_commit` hooks call `routes.dashboard.clear_dashboard_cache()` when Emission, Scope2/3, ProductionData, Facility, CustomFactor or OgmpSurvey rows change. On Postgres this bumps a shared epoch in `system_settings`; every `batch-all` request calls `_get_global_cache_epoch()` (at most one DB read per second) before trusting its per-process cache, so other workers drop stale results. `routes.dashboard.cache_stats()` exposes hit/miss counters (also logged every 1000 lookups).
- **Route modules.** Large blueprints are split across files that register on the same blueprint: `emissions.py` imports `emissions_bulk_upload`, `_export`, `_import`, `_mappings`, `_review`, `_template_csv`, `_template_excel` (and `reports.py` imports `reports_export`, `reports_ogmp`; `dashboard.py` imports `dashboard_sbti`, `_ogmp`, `_flaring`, `_bridge` (`/api/dashboard/yoy-bridge`, built on `_query_summary` so it reconciles with the yearly totals); `auth.py` imports `auth_settings`, `auth_users` and re-exports their names lazily via `__getattr__`). The helpers stay in the parent module (the splits import them back from it), and the parent imports the split modules last. When moving a route, compare `app.url_map` before and after.
- **Report and import builders (2026-10-16 refactor).** Long route functions were split into services, one function per sheet or step: `services/qaqc_dashboard.py` (`GET /api/qaqc/dashboard`), `services/ogmp_workbook.py` (OGMP workbook), `services/cbam_data.py` / `cbam_xml.py` / `cbam_workbook.py` (CBAM; the old helper names stay importable from `routes.reports_cbam`), and `background_processor._ImportRun` (the steps of `_process_file_thread`). Outputs were compared cell by cell against the previous code.
- **Blueprints (`routes/`).** Each is mounted at `/api/<name>`. The exceptions are `managedata_bp` (mounted at `/api`) and `factors_bp` (no prefix; its routes carry their own paths).
- **`extensions.py`.**
  - `db` is created with `expire_on_commit=False`.
  - `limiter` connects to Redis via `REDIS_URL` (falls back to memory if unset) and defaults to 200/min and 2000/h.
  - `csrf` is Flask-WTF.
- **Access Control & RBAC.**
  - Sessions are cookie-based.
  - Sign-in limits (`services/login_guard.py`): only failed sign-ins count, per client address (`LOGIN_RATE_LIMIT`, default 50 per 15 minutes) and per account from any address (`LOGIN_ACCOUNT_LIMIT`, default 10 per 15 minutes: the account is locked for the rest of the window). Each failure writes a `FAILED_LOGIN` audit entry.
  - Decorators in `routes/auth.py`: `login_required`, `admin_required`, `superuser_required`, `it_admin_required`, `it_access_required`.
  - Role hierarchy and segregation of duties (SoD):
    - `admin`: Client compliance administrator — the **only** role with unrestricted global access to all facilities, system configuration, and approval rights.
    - `superuser`: Operational lead — strictly scoped to **1 assigned facility/region** (no global bypass).
    - `user`: Standard operator — strictly scoped to assigned facility/region.
    - `it` / `it_admin`: Client IT account lifecycle only. Strictly isolated from operational data (zero access to emissions, equity partner, or CAP data). Cannot create, assign, modify, disable, delete or reset passwords for `admin`, `superuser` or `auditor` accounts (only `admin` and `it_manager` grant those roles; an auditor with an unrestricted location reads every facility; nobody can change their own role).
    - `it_manager`: SaaS Vendor / Platform Operator team.
  - Facility scoping goes through `utils.get_allowed_facility_ids` (where only `admin` receives global `None`) and `utils.require_facility_access`.
  - All facility ID query parameters are strictly validated (`422 Unprocessable Entity` on non-numeric input).
- **CSRF.** `GET /api/csrf-token` sets the token, and mutating requests must send it as the `X-CSRFToken` header, sign-in and forgot-password included (no exemptions since 2026-10-09; sign-in starts a new session, so fetch a new token after it). `WTF_CSRF_SSL_STRICT` is on (env `WTF_CSRF_SSL_STRICT=false` turns it off): over HTTPS a write also needs a same-host `Referer`, so behind nginx set `TRUSTED_PROXIES`. The suite keeps an app context open, so a test that turns CSRF on must drop `g.csrf_token` before fetching a token (`tests/test_signin_csrf.py`).
- **Calculation path.**
  - Routes and `background_processor.py` call `calculations.compute_emissions` (in `calculations/legacy_engine.py`).
  - Unit conversions use canonical formulas in `calculations/units.py`.
  - Gas compositions are treated as volume/mole fractions directly without double percentage division.
  - Fields documented as percent (`calculations/dispatcher.PERCENT_FIELDS`: CH4 / CO2 contents including `tank_co2_content` and `co2_mol`, AGR inlet / outlet CO2, CCS capture rate) are always read as percent (0.9 is 0.9 %, 1 is 1 %) and converted to fractions once, at the start of `_dispatch_impl`; the old guess (a value of 1 or less is a fraction) is gone (audit 2026-10-14 BUG-0020/21/22). CH4 / CO2 contents next to a c1..c10 analysis keep that analysis's own basis.
  - `compute_emissions` tries the dispatcher first and falls back to legacy factor math (`server_default` / `server_specific` / `server_custom_factor`) for entered Tier 3 factors (always, even with a catalog fuel), saved custom factors and processes the dispatcher does not model; zero activity keeps the dispatcher's zero result. This is intentional, not dead code (11 uses in ~2,500 tests; none on the API Compendium exhibit tests). Set the `calculations.legacy_engine` logger to DEBUG to see each use.
  - `CalculationDispatcher._dispatch_impl` is a flat `if/elif` chain over process types; each branch body lives in a function in `calculations/dispatcher_branches_{combustion,venting,fugitive}.py` (first argument is the dispatcher; `dispatcher.py` imports them last). Add a new process family by adding a branch there. Calculator classes are likewise split across `vented_*.py` and re-exported from `vented.py` / `vented_production.py`.
  - Dispatcher (`calculations/dispatcher.py`) maps process-type aliases (e.g. `flaring`, `tank_flashing`, `compressor_seal`) to API-Compendium-2021 calculators in `combustion.py`, `vented.py`, `fugitive.py`, `midstream.py`, `indirect.py` and `stoichiometry.py`.
  - Zero-activity/throughput records cleanly compute zero emissions.
  - Flares (2026-10-21): one `_split_vent_flare` in `calculations/vented_production.py`. Without an entered efficiency: 98 % CH4 destruction, 96.5 % carbon to CO2 (Compendium corrections, December 2025); an entered efficiency is used for both, and on every process (unloading, blowdown, tanks and dehydrators included since 2026-10-22) it is the flare's efficiency, not a share sent to a flare. Disposition rules (`_route`, `CalculationDispatcher._controlled_share`) and the other 2026-10-21 behaviour changes are in `docs/CALCULATION_PIPELINE_MEMORY.md` ("Third pass").
  - Steam: net efficiency = boiler efficiency - transmission loss (Exhibit 8.3). Steam bought by mass needs its enthalpy (`steam_enthalpy_btu_lb`, Equation 8-1): `calculations.indirect.heat_to_mmbtu`, shared by the calculator, `routes/scope2.py` and the Scope 2 import.
- **Scope 2 Dual Reporting Architecture.**
  - Complies with GHG Protocol Scope 2 Guidance. Dual reporting computes both:
    - Location-based (`co2e_location_based`): Uses regional/national grid average emission factors.
    - Market-based (`co2e_market_based`): Uses contractual instruments (RECs, GOs, PPAs, supplier-specific factors, or residual mix).
  - Scope 2 emissions store `market_instrument_type`, `market_factor_source`, and `co2e_used` (whichever method is designated for corporate inventory totals).
- **Uncertainty & GWP Propagation.**
  - Category mapping correctly separates combustion, flaring, venting, fugitives, acid_gas, transport, and electricity.
  - GWP uncertainty is propagated into CO2e totals via IPCC AR5 Chapter 8 Taylor series error propagation in `calculations/uncertainty.py` (`propagate_co2e_uncertainty`).
  - Dashboard endpoint `/api/dashboard/uncertainty` accepts `?gwp_uncertainty=true` to toggle scientific GWP uncertainty inclusion.
- **Maker-Checker Workflow.**
  - Custom emission factors created by non-admins are assigned `Pending` status.
  - A `superuser` or `admin` approves or rejects custom factors (`POST /api/custom-factors/<id>/approve` / `reject`), never a factor they created; only a Pending factor can be rejected (archive an approved one). Only an Approved factor calculates (`services.scope1_calc.resolve_factor`, every Scope 1 path); an edited record keeps the factor it was saved with.
  - HR-06 governance (`services/custom_factor_policy.py`): a `source` is required; a value above the bounds (CO2 500, CH4 100, N2O 10 kg/MMBtu) is refused with 422 unless `justification` (10+ characters) is sent, and is then saved `Pending` with the reason appended to `description`; nobody approves a factor they created (an admin may when `CUSTOM_FACTOR_SECOND_APPROVER=false`, for a one-admin install); a superuser edits, archives or deletes only their own unapproved factors; factors used by records cannot change values (audit O-04).
- **Constants.**
  - Units: `calculations/units.py` `CONVERSIONS`.
  - GWPs: `calculations/constants.py` (AR4, AR5 default, AR6, 20-year values; `get_active_gwp()` resolves active set). Keep in sync with `new/client/src/constants.ts`.
- **Record status & Frontend Editing.**
  - Scope 1/2 entries: `Draft`, `Pending`, or `Verified`.
  - Frontend includes `components/modals/EditEmissionModal.tsx` allowing authorized users to edit activity values, fuel types, units, and Scope 2 market instruments directly from the Reports and Review interfaces.
  - Physical edits transition records back to `Pending` for compliance review.
- **Emission columns** (`co2e_total`, `co2e_location_based`, `co2e_market_based`, etc.) are stored in tonnes.
- **Bulk uploads.** Staged uploads are saved in isolated application instance storage (`INSTANCE_PATH/bulk_uploads`), protected against OS `/tmp` collisions and double-insert races. There is no row limit (batched flush on PostgreSQL); the request size is capped by `MAX_CONTENT_LENGTH` (`GET /api/emissions/upload/limits`) and each user may run `MAX_CONCURRENT_UPLOADS_PER_USER` (default 3) jobs at once, but imports of one scope are serialised from their duplicate-key snapshot to their commit (`background_processor._hold_import_lock`: a per-process lock plus a PostgreSQL advisory lock), so overlapping uploads of the same rows store them once. `POST /api/emissions/upload/check` calculates a sample of a file without saving anything; skip reasons are grouped by `services/import_feedback.py`. Scope 1 CSV/Excel templates are built from one column spec in `services/scope1_template.py` (example rows are dated EXAMPLE and never imported). Saved column mappings live in `import_mappings` (`routes/emissions_mappings.py`). Every upload sends `decimal_mark` (`comma` = 1 234,5 or `point` = 1,234.5), chosen per file in the wizard; number-like text cells are read strictly by it (`background_processor.normalize_number_cell`), and without it (API clients) an ambiguous `1,000` is refused instead of guessed (semicolon CSVs default to comma). Duplicate detection keys new rows by the stored catalog fuel name.
- **Notifications.** The client polls `GET /api/notifications` every 30 s and when the tab becomes visible; there is no streaming endpoint (an SSE stream held one worker thread per open tab).
- **Audit logging & Transaction Atomicity.** All mutating routes log activity via `utils.log_activity_and_notify(...)` and commit the data change and audit row atomically in a single database transaction. Audit chain verification streams using `yield_per(1000)` to guarantee constant memory usage.
- **Tamper-evident audit log** (`services/audit_chain.py`). A `before_flush` hook seals every new `ActivityLog` row: `entry_hash` = SHA-256 of its content (details and before/after values included) chained to the previous row's hash (`prev_hash`), under a PostgreSQL advisory lock (on SQLite, the database write lock taken by a no-op write) so concurrent writers never fork the chain (`tests/test_audit_chain_concurrency.py`). `GET /api/audit/verify-chain` recomputes the chain and answers `verified` or `tampered` with the entries concerned; removal of the newest entries is caught by comparing with a saved checkpoint (`/api/audit/verify-checkpoint`). On PostgreSQL a trigger refuses UPDATE / DELETE / TRUNCATE on `activity_log` except clearing `user_id` (user deletion); a migration that must rewrite audit rows drops and recreates it. Exported PDF reports and the OGMP workbook print a data fingerprint that is also recorded in a `REPORT` audit entry.
- **Request input.** A request body that is not JSON reads as `{}` (`app._LenientJSONRequest`), so routes answer 400 for missing fields instead of 500. NUL characters in query parameters or JSON are refused (400). On `/api/dashboard/*` and `/api/data/production` a malformed `year` / `month` (400) or `facility_id` (422) is refused centrally (`input_validation.invalid_query_parameter`); other routes keep their own documented handling.
- **Text columns.** `services/column_guard.py` checks every length-limited `String` column when it is assigned: a value longer than the column, or a list / object, raises `ValidationError` (400 naming the field) instead of failing at commit on PostgreSQL (SQLite does not enforce lengths). Numbers are stored as their text. Edit-facility checks go through `utils.facility_access_error` (422 malformed, 403 not allowed, 404 unknown).
- **Audit 2026-10-14 behaviour** (regression tests: `tests/test_audit_2026_10_14.py`). Manual Scope 1 entry refuses a natural-key duplicate with 409 `requires_confirmation` unless `allow_duplicate: true` (the saved repeat is flagged and goes to review); the JSON import refuses duplicates and reports the saved `status` / `status_counts`. Flagged values, resubmissions of a Rejected record and failed anomaly checks always go to review, an admin's included. Deleting a facility that has records needs `?confirm=true`. An empty edit changes nothing. Draft records are not reviewable. Facility names and codes are unique. Location scope is an exact (case-insensitive) match on region, location or name. Import templates need a sign-in; the public readiness probe no longer reports the WAL size. Without `SECRET_KEY` outside production, a random key is used per process. Notifications about a facility reach only accounts with that facility in scope.
- **Bug hunt 2026-10-15 behaviour** (regression tests: `tests/test_bug_hunt_2026_10_15.py`, client `src/__tests__/analyticsFiltersSync.test.tsx`).
  - Units: a bare "ton" is refused everywhere (`tonne` or `short_ton`; the catalog uses `short_ton`). A temperature without a unit is °C on every process (the blowdown, unloading and dehydrator forms send `F`). Factor denominators such as "1000 scf", "100 gal" and 10ⁿ superscripts scale correctly. An activity amount sent as text with a comma is refused.
  - Calculations refuse instead of guessing: an energy factor with no HHV (never the natural-gas 1020), Tier 3 dehydrators without the gas CH4 content, a measured AGR slip without inlet CH4, the stoichiometric method without carbon content, VBE / Standing / EUB without separator data, and a multi-component composition whose values are all ≤ 1 and lack methane or total under 50 % (it needs `composition_basis`). An entered 0 is a value, not "missing".
  - Scope 2 cooling needs its factor in kg CO2e per ton-hour (no default) and imports must be in ton-hours. A Scope 3 activity unit is converted to the factor's denominator or refused.
  - `background_processor._clean_float` returns None for unreadable or ambiguous text ("1,000"); `default` is for empty cells only.
  - The national inventory and CBAM exports take `?status=` (default Verified; `Verified,Pending` or `all`), refuse a malformed year / facility (400), and print the records' own values (no invented IDs, suppliers, GWP or uncertainty figures). `services/report_params.py` holds the shared parsing.
  - The dashboard sends `scope2_method` (Location / Market toggle); GWP-20 re-weights Scope 2 everywhere via `services.scope2_gases.record_totals`; year lists are scoped to the user's facilities; segments are stored as Upstream / Midstream / Downstream (`services.labels.normalize_segment`).
- **Review 2026-10-15 behaviour** (regression tests: `tests/test_review_2026_10_15.py`).
  - QA/QC resolve (`/api/qaqc/resolve`, `/bulk-resolve`) goes through `services.maker_checker`: only records awaiting review, never your own, one audit entry per record; skipped records are listed with a reason.
  - Idle timeout (`services/session_policy.py`): the server ends a session idle longer than the IT setting `session_timeout_minutes` (default 30); `/api/auth/me` and sign-in return `idle_timeout_minutes` for the client timers; the notification poll is not activity, `GET /api/auth/keepalive` is (the client sends it at most once a minute while the user is active).
  - Deleting the last active admin is refused (409); the email-uniqueness check on edit ignores case; batch endpoints refuse list items that are not objects (400).
- **Review 2026-10-16** (regression tests: `tests/test_review_2026_10_16.py`). The OGMP and CBAM exports print no invented values or claims (no default company, address, member ID, basin, 50 % equity, HMAC / "sealed" seal or perjury clause), without verified Scope 2 data CBAM uses the sourced catalog grid factor of the facility's country (`electricity_factors`, named with its source in the Accounting Basis column) or shows "N/A" when the catalog has none (never the old fixed national table), and every cell taken from records goes through `_safe_excel_value` (only the totals rows hold formulas).
- **No satellite integration.** The Copernicus / Sentinel-5P connection was removed (2026-10-09): no `/api/satellite` routes, no credentials settings (`routes/auth_settings.RETIRED_SETTING_KEYS` are never loaded, stored or returned), no map overlay. OGMP 2.0 site-level surveys of type "Satellite" remain (operators record them).
- **Map tiles.** The Emissions Map basemap comes from `MAP_TILE_URL` (`MAP_TILE_ATTRIBUTION`, `MAP_TILE_SUBDOMAINS`) via `GET /api/map-config`; unset (offline installs) the map shows the facilities without a basemap.

## Frontend architecture

- The client is TypeScript (`.ts/.tsx`; shared types in `src/types/`, hooks in `src/hooks/`); some files remain `.jsx`.
- `src/api.ts` is the shared axios instance.
  - `baseURL` is `VITE_API_URL`, or `/api` if unset, and requests use `withCredentials`.
  - It attaches `X-CSRFToken` to mutating requests and retries once on CSRF 400s.
  - On a 401 it calls `window.__authLogout`.
- `src/App.tsx` uses BrowserRouter with route guards: `PrivateRoute`, `NonITRoute`, `ITRoute`, `AdminRoute`, `SuperuserRoute`, `AuditRoute` (role rules also in `src/app/access.ts` and `RequireRole.tsx`).
- Pages are in `src/pages`, scope forms and import wizards in `src/components`, and auth/layout state in `src/context`.
- **Languages (English, French).** `src/i18n/index.ts` exports `t("English text", {vars})`: the English sentence is the key, `src/i18n/fr.json` holds the French, and a string without an entry stays English (technical terms wait for the HSE glossary, `docs/sonatrach/glossary-fr.csv`). The language is read from `localStorage` (`neocarbon.language`) before any module renders (`main.tsx` imports `./i18n` first), so module-level labels may call `t()`; switching saves the choice (and the account's `language` preference) and reloads. Wrap new interface text in `t()` with a whole sentence and `{{placeholders}}`, not fragments around numbers. `npm run i18n:check` reports coverage (`-- --missing` lists the English-only strings, `-- --strict` fails on unused entries). Data values that are saved, compared or sent to the API (process and activity names, rejection reasons) stay English and are translated where shown (`t(value)`); their entries count as used while the text appears in the code. `scripts/i18n-wrap.mjs` was the one-off codemod that wrapped the existing text. Numbers stay in 1,234.5 format in both languages.
- **Design system (in progress, see `docs/ui-modernization-plan.md`).** `src/styles/tokens.css` holds all design tokens (the only place hex values may live) and bridges the legacy CSS variable names; `src/ui/` holds shared components (Button, Field, DataTable, Dialog, ...); `src/app/` holds the shell (`routes.config.ts` is the single source for routes, nav, breadcrumbs, titles and access rules; `shell/` has Sidebar, TopBar, CommandPalette). Tailwind v4 runs with theme+utilities only (no preflight) and scans `ui/`, `app/`, `filters/`, `dev/`, `pages/`, `components/`. Legacy CSS stays unlayered (it beats utilities unless a utility is `!important`); about half of it was moved into arbitrary-property utilities in the JSX by `scripts/css-to-utilities.mjs` (see the plan, "legacy CSS conversion"). Do not hand-edit those long utility strings expecting legacy cascade behavior: unlayered rules still win over layered ones, and layered `!important` beats unlayered `!important`. Check visual parity with the probes in `scripts/probe/`. Run `npm run lint:css` and `npm run ui:metrics -- --check`.

## Repo conventions

- `AUDIT_MEMORY.md` was the living audit log. It is no longer in the tree or in git history (purged 2026-10-15); a local copy of its last version is in `archive/from-history/AUDIT_MEMORY.md`. Read it before fixing an audit item. Audit runs are written to `AUDIT_ARTIFACTS_*/`, which is git-ignored.
- `docs/CALCULATION_PIPELINE_MEMORY.md`: which route/function calculates and stores each input path (single, file, JSON, legacy; Scope 1/2/3), the intentional differences between them, and the bulk-vs-single parity tests that guard them. Read it before touching an import or calculation path.
- Calculation methodology and validation: `docs/calculation-specification.md`, `docs/validation-report.md`.
- **API Compendium exhibit tests (2026-10-22).** The worked examples are asserted against the numbers the exhibits print, to their printed precision (`tests/compendium_exhibits_support.py`: `assert_printed`; `gas="ch4"` / `"co2"` expects the engine-constants shift of `CONSTANTS_SHIFT` (the exhibits use 16 / 44 lb per lbmole and 379.3 scf/lbmole, the engine 16.04 / 44.01 and 23.685 m3/kmol: CH4 +0.224 %, CO2 -0.003 %); most sites then allow only 0.02 to 0.06 % beyond the printed rounding. The ten that still use `REL_MW` 0.3 % / `REL_ENGINE` 0.5 % or an own `rel=` have a documented larger difference). Files: `test_compendium_exhibits_ch3_5_8.py`, `test_compendium_exhibits_ch6_exploration_production.py`, `test_compendium_exhibits_ch7_other.py` (Exhibits 7-6 to 7-9), `test_onshore_exhibits.py` and `test_api_compendium_exhibits.py` (both through `compute_emissions`), `test_vented_*_compendium.py`. A case the software cannot match is a strict `xfail` naming the difference (none today: Exhibit 4.13 now uses the Table 4-16 ship factors of the catalog row "Marine Diesel Oil", Exhibit 6-11 the CH4-basis factors of Table 6-14). When writing a new test, work the expected value by hand from the inputs: do not read it from the engine, assert more than `> 0`, and mind that the dispatcher reads `ch4_content` etc. as percent, needs `factor_source`, and silently ignores keys it does not know.
- **Wastewater, refrigerant HFC and electrical SF6 (Compendium 7.5 / 7.6, 2026-10-22).** `calculations/fugitive_other.py`: process types `wastewater` (`wastewater_method` aerobic / anaerobic_epa / ipcc; Eq 7-17 to 7-20), `refrigerant` (aliases `hfc`, `air_conditioning`; `refrigerant_method` charge / mass_balance; Eq 7-21, 7-22) and `electrical_equipment` (alias `sf6`; `electrical_method` mass_balance / recharge / distance; Eq 7-23 to 7-26), routed by `CalculationDispatcher.dispatch` before `_dispatch_impl`. HFC and SF6 have no gas column: the result carries `results["f_gas"]` (tonnes, GWP, CO2e) and the CO2e is in `total_co2e` / `totalCo2e` / `co2e_total`, with CO2, CH4 and N2O zero. Their GWPs follow the active IPCC report through the CH4 GWP of `gwp_dict` (SF6 and HFC-134a for AR4 / AR5 / AR6; Table 7-84 blends are AR5 only and refused for another report unless `gwp` is entered). Annual factors cover the record's period (its month, or `operating_days`). The Compendium prints Equations 7-22 and 7-27 with the opposite sign of 7-23; the code follows 7-23. There is no client form, bulk template column or catalog row for these yet: they are reachable through the API (`POST /api/emissions`). A gas volume at absolute zero is refused (blowdown, unloading, `normalize_gas_volume_to_standard`: `to_kelvin(..., above_zero=True)`); it used to be clamped to 1 K.
- A graphify knowledge graph lives in `graphify-out/` when generated (currently absent; `.agents/rules/graphify.md`). Use `graphify query "<q>"`, `graphify path "<A>" "<B>"` or `graphify explain "<concept>"` for architecture questions. Run `graphify update .` after modifying code.

<!-- rtk-instructions v2 -->
# RTK (Rust Token Killer) - Token-Optimized Commands

## Golden Rule

**Always prefix commands with `rtk`**. If RTK has a dedicated filter, it uses it. If not, it passes through unchanged. This means RTK is always safe to use.

**Important**: Even in command chains with `&&`, use `rtk`:
```bash
# ❌ Wrong
git add . && git commit -m "msg" && git push

# ✅ Correct
rtk git add . && rtk git commit -m "msg" && rtk git push
```

## RTK Commands by Workflow

### Build & Compile (80-90% savings)
```bash
rtk cargo build         # Cargo build output
rtk cargo check         # Cargo check output
rtk cargo clippy        # Clippy warnings grouped by file (80%)
rtk tsc                 # TypeScript errors grouped by file/code (83%)
rtk lint                # ESLint/Biome violations grouped (84%)
rtk prettier --check    # Files needing format only (70%)
rtk next build          # Next.js build with route metrics (87%)
```

### Test (60-99% savings)
```bash
rtk cargo test          # Cargo test failures only (90%)
rtk go test             # Go test failures only (90%)
rtk jest                # Jest failures only (99.5%)
rtk vitest              # Vitest failures only (99.5%)
rtk playwright test     # Playwright failures only (94%)
rtk pytest              # Python test failures only (90%)
rtk rake test           # Ruby test failures only (90%)
rtk rspec               # RSpec test failures only (60%)
rtk test <cmd>          # Generic test wrapper - failures only
```

### Git (59-80% savings)
```bash
rtk git status          # Compact status
rtk git log             # Compact log (works with all git flags)
rtk git diff            # Compact diff (80%)
rtk git show            # Compact show (80%)
rtk git add             # Ultra-compact confirmations (59%)
rtk git commit          # Ultra-compact confirmations (59%)
rtk git push            # Ultra-compact confirmations
rtk git pull            # Ultra-compact confirmations
rtk git branch          # Compact branch list
rtk git fetch           # Compact fetch
rtk git stash           # Compact stash
rtk git worktree        # Compact worktree
```

Note: Git passthrough works for ALL subcommands, even those not explicitly listed.

### GitHub (26-87% savings)
```bash
rtk gh pr view <num>    # Compact PR view (87%)
rtk gh pr checks        # Compact PR checks (79%)
rtk gh run list         # Compact workflow runs (82%)
rtk gh issue list       # Compact issue list (80%)
rtk gh api              # Compact API responses (26%)
```

### JavaScript/TypeScript Tooling (70-90% savings)
```bash
rtk pnpm list           # Compact dependency tree (70%)
rtk pnpm outdated       # Compact outdated packages (80%)
rtk pnpm install        # Compact install output (90%)
rtk npm run <script>    # Compact npm script output
rtk npx <cmd>           # Compact npx command output
rtk prisma              # Prisma without ASCII art (88%)
rtk uv run <cmd>        # Compact uv project command output
```

### Files & Search (60-75% savings)
```bash
rtk ls <path>           # Tree format, compact (65%)
rtk read <file>         # Code reading with filtering (60%)
rtk grep <pattern>      # Search grouped by file (75%). Format flags (-c, -l, -L, -o, -Z) run raw.
rtk find <pattern>      # Find grouped by directory (70%)
```

### Analysis & Debug (70-90% savings)
```bash
rtk err <cmd>           # Filter errors only from any command
rtk log <file>          # Deduplicated logs with counts
rtk json <file>         # JSON structure without values
rtk deps                # Dependency overview
rtk env                 # Environment variables compact
rtk summary <cmd>       # Smart summary of command output
rtk diff                # Ultra-compact diffs
```

### Infrastructure (85% savings)
```bash
rtk docker ps           # Compact container list
rtk docker images       # Compact image list
rtk docker logs <c>     # Deduplicated logs
rtk kubectl get         # Compact resource list
rtk kubectl logs        # Deduplicated pod logs
```

### Network (65-70% savings)
```bash
rtk curl <url>          # Compact HTTP responses (70%)
rtk wget <url>          # Compact download output (65%)
```

### Meta Commands
```bash
rtk gain                # View token savings statistics
rtk gain --history      # View command history with savings
rtk discover            # Analyze Claude Code sessions for missed RTK usage
rtk proxy <cmd>         # Run command without filtering (for debugging)
rtk init                # Add RTK instructions to CLAUDE.md
rtk init --global       # Add RTK to ~/.claude/CLAUDE.md
```

## Token Savings Overview

| Category | Commands | Typical Savings |
|----------|----------|-----------------|
| Tests | vitest, playwright, cargo test | 90-99% |
| Build | next, tsc, lint, prettier | 70-87% |
| Git | status, log, diff, add, commit | 59-80% |
| GitHub | gh pr, gh run, gh issue | 26-87% |
| Package Managers | pnpm, npm, npx | 70-90% |
| Files | ls, read, grep, find | 60-75% |
| Infrastructure | docker, kubectl | 85% |
| Network | curl, wget | 65-70% |

Overall average: **60-90% token reduction** on common development operations.
<!-- /rtk-instructions -->