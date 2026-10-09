# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Layout

GHG (greenhouse-gas) accounting platform. The real application lives in `new/`:
- `new/server` — Flask 3 API (SQLAlchemy, Flask-WTF CSRF, Flask-Limiter, Redis)
- `new/client` — React 19 + Vite 7 SPA

Loose root scripts and scratch files were archived into `archive/` (not present in the current working tree; recover via git history). A root `package.json` (Express/Electron), where present in history, is unrelated to the Flask app (absent in the working tree now).

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
flask db upgrade                   # run Alembic migrations up to head (d4e8a1b7c2f0)
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
- `python scripts/loc_ratchet.py --check` (CI gate) fails if a file in `routes/`, `calculations/` or `services/` grows past `scripts/loc_baseline.json`, or a new one exceeds 800 lines. After shrinking a file, lock it in with `--write`.
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

CI: `deploy-pages.yml` runs the backend gate groups above plus frontend `lint`, `check:ts`, `lint:css`, `ui:metrics -- --check` and `test`, then runs the production build (it no longer deploys to GitHub Pages). `e2e-matrix.yml` runs the Playwright smoke tier (21 tests) on pushes and pull requests: CI seeds the `a`/`a` test sign-in (`scripts/seed_e2e_user.py`, refuses to run in production) and sample data (`seed_showcase_data.py`), then saves the login with `generate_storage_state.js`. `seed_e2e_user.py` also creates the `itadmin@sonatrach.dz` (it_admin) and `operator@sonatrach.dz` (user) sign-ins the full matrix uses; never run it against a database you care about, because it overwrites those accounts' passwords and roles. The full matrix (`e2e:full`, 124 tests in `e2e/deep_user_audit/`) is **manual-only** (`workflow_dispatch`); it ran green (all but one test, then that one was fixed) in a clean Docker clone. Its CI job still raises `LOGIN_RATE_LIMIT` for the test backend; since 2026-10-09 only failed sign-ins count against it (`RATELIMIT_ENABLED` is not read by the backend). Specs read `E2E_BASE_URL`; do not hard-code `localhost` (IPv6-first hosts cannot reach the IPv4-only dev server). To reproduce CI locally, run the same commands in `python:3.11` / `node:20` containers against a fresh clone (this is how a missing `psutil` dependency was found); a clean clone also catches files that exist only on your machine.

Other: `new/setup.bat` / `new/start_all.bat` (Windows native launch scripts for Flask backend + Vite frontend).

## Backend architecture

- **`app.py` creates a module-level `app`, not a factory.** Tests use `from app import app`. Importing it has side effects: it runs `init_schema()`, creates indexes and optionally seeds admins. `init_schema()` upgrades the database to the Alembic head outside production (or with `AUTO_MIGRATE=true`) and refuses to start in production if the database is behind head (`AUTO_MIGRATE=false` disables the auto-upgrade). It does not call `db.create_all()`; only `seed_admin.py` and `build_csv_guide.py` do, and `schema_sync.py`'s docstring is out of date on this point.
- **Schema changes.** Alembic migrations (`migrations/`) manage schema evolution up to head revision `d4e8a1b7c2f0` (audit log hash chain: `activity_log.prev_hash` / `entry_hash`, existing rows sealed, append-only trigger on PostgreSQL), after `c3f9a2d18e47` (`import_mappings`, saved import column mappings), after `b7e2d4c91a05` (`emissions.fuel_type` widened to 255) and `a6274c2ef1f5` (audit hardening and foreign keys). The earlier `b2d5f8e31a42` introduced Scope 2 dual-reporting columns, custom factor approval metadata, and composite indexes.
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
    - `it` / `it_admin`: Client IT account lifecycle only. Strictly isolated from operational data (zero access to emissions, equity partner, satellite, or CAP data). Cannot reset passwords for or create `admin` or `superuser` accounts.
    - `it_manager`: SaaS Vendor / Platform Operator team.
  - Facility scoping goes through `utils.get_allowed_facility_ids` (where only `admin` receives global `None`) and `utils.require_facility_access`.
  - All facility ID query parameters are strictly validated (`422 Unprocessable Entity` on non-numeric input).
- **CSRF.** `GET /api/csrf-token` sets the token, and mutating requests must send it as the `X-CSRFToken` header.
- **Calculation path.**
  - Routes and `background_processor.py` call `calculations.compute_emissions` (in `calculations/legacy_engine.py`).
  - Unit conversions use canonical formulas in `calculations/units.py`.
  - Gas compositions are treated as volume/mole fractions directly without double percentage division.
  - `compute_emissions` tries the dispatcher first and falls back to legacy factor math (`server_default` / `server_specific` / `server_custom_factor`) for zero activity, entered Tier 3 factors, saved custom factors and processes the dispatcher does not model. This is intentional, not dead code (11 uses in ~2,500 tests; none on the API Compendium exhibit tests). Set the `calculations.legacy_engine` logger to DEBUG to see each use.
  - `CalculationDispatcher._dispatch_impl` is a flat `if/elif` chain over process types; each branch body lives in a function in `calculations/dispatcher_branches_{combustion,venting,fugitive}.py` (first argument is the dispatcher; `dispatcher.py` imports them last). Add a new process family by adding a branch there. Calculator classes are likewise split across `vented_*.py` and re-exported from `vented.py` / `vented_production.py`.
  - Dispatcher (`calculations/dispatcher.py`) maps process-type aliases (e.g. `flaring`, `tank_flashing`, `compressor_seal`) to API-Compendium-2021 calculators in `combustion.py`, `vented.py`, `fugitive.py`, `midstream.py`, `indirect.py` and `stoichiometry.py`.
  - Zero-activity/throughput records cleanly compute zero emissions.
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
  - Only compliance `admin` accounts can approve custom factors via `POST /api/custom-factors/<id>/approve`.
- **Constants.**
  - Units: `calculations/units.py` `CONVERSIONS`.
  - GWPs: `calculations/constants.py` (AR4, AR5 default, AR6, 20-year values; `get_active_gwp()` resolves active set). Keep in sync with `new/client/src/constants.ts`.
- **Record status & Frontend Editing.**
  - Scope 1/2 entries: `Draft`, `Pending`, or `Verified`.
  - Frontend includes `components/modals/EditEmissionModal.tsx` allowing authorized users to edit activity values, fuel types, units, and Scope 2 market instruments directly from the Reports and Review interfaces.
  - Physical edits transition records back to `Pending` for compliance review.
- **Emission columns** (`co2e_total`, `co2e_location_based`, `co2e_market_based`, etc.) are stored in tonnes.
- **Bulk uploads.** Staged uploads are saved in isolated application instance storage (`INSTANCE_PATH/bulk_uploads`), protected against OS `/tmp` collisions and double-insert races. There is no row limit (batched flush on PostgreSQL); the request size is capped by `MAX_CONTENT_LENGTH` (`GET /api/emissions/upload/limits`) and each user may run `MAX_CONCURRENT_UPLOADS_PER_USER` (default 3) jobs at once. `POST /api/emissions/upload/check` calculates a sample of a file without saving anything; skip reasons are grouped by `services/import_feedback.py`. Scope 1 CSV/Excel templates are built from one column spec in `services/scope1_template.py` (example rows are dated EXAMPLE and never imported). Saved column mappings live in `import_mappings` (`routes/emissions_mappings.py`). Every upload sends `decimal_mark` (`comma` = 1 234,5 or `point` = 1,234.5), chosen per file in the wizard; number-like text cells are read strictly by it (`background_processor.normalize_number_cell`), and without it (API clients) an ambiguous `1,000` is refused instead of guessed (semicolon CSVs default to comma). Duplicate detection keys new rows by the stored catalog fuel name.
- **Notifications.** The client polls `GET /api/notifications` every 30 s and when the tab becomes visible; there is no streaming endpoint (an SSE stream held one worker thread per open tab).
- **Audit logging & Transaction Atomicity.** All mutating routes log activity via `utils.log_activity_and_notify(...)` and commit the data change and audit row atomically in a single database transaction. Audit chain verification streams using `yield_per(1000)` to guarantee constant memory usage.
- **Tamper-evident audit log** (`services/audit_chain.py`). A `before_flush` hook seals every new `ActivityLog` row: `entry_hash` = SHA-256 of its content (details and before/after values included) chained to the previous row's hash (`prev_hash`), under a PostgreSQL advisory lock so concurrent workers never fork the chain. `GET /api/audit/verify-chain` recomputes the chain and answers `verified` or `tampered` with the entries concerned; removal of the newest entries is caught by comparing with a saved checkpoint (`/api/audit/verify-checkpoint`). On PostgreSQL a trigger refuses UPDATE / DELETE / TRUNCATE on `activity_log` except clearing `user_id` (user deletion); a migration that must rewrite audit rows drops and recreates it. Exported PDF reports and the OGMP workbook print a data fingerprint that is also recorded in a `REPORT` audit entry.
- **Request input.** A request body that is not JSON reads as `{}` (`app._LenientJSONRequest`), so routes answer 400 for missing fields instead of 500. NUL characters in query parameters or JSON are refused (400). On `/api/dashboard/*` and `/api/data/production` a malformed `year` / `month` (400) or `facility_id` (422) is refused centrally (`input_validation.invalid_query_parameter`); other routes keep their own documented handling.
- **Text columns.** `services/column_guard.py` checks every length-limited `String` column when it is assigned: a value longer than the column, or a list / object, raises `ValidationError` (400 naming the field) instead of failing at commit on PostgreSQL (SQLite does not enforce lengths). Numbers are stored as their text. Edit-facility checks go through `utils.facility_access_error` (422 malformed, 403 not allowed, 404 unknown).
- **Map tiles.** The Emissions Map basemap comes from `MAP_TILE_URL` (`MAP_TILE_ATTRIBUTION`, `MAP_TILE_SUBDOMAINS`) via `GET /api/map-config`; unset (offline installs) the map shows the facilities without a basemap.

## Frontend architecture

- The client is TypeScript (`.ts/.tsx`; shared types in `src/types/`, hooks in `src/hooks/`); some files remain `.jsx`.
- `src/api.ts` is the shared axios instance.
  - `baseURL` is `VITE_API_URL`, or `/api` if unset, and requests use `withCredentials`.
  - It attaches `X-CSRFToken` to mutating requests and retries once on CSRF 400s.
  - On a 401 it calls `window.__authLogout`.
- `src/App.tsx` uses BrowserRouter with route guards: `PrivateRoute`, `NonITRoute`, `ITRoute`, `AdminRoute`, `SuperuserRoute`, `AuditRoute` (role rules also in `src/app/access.ts` and `RequireRole.tsx`).
- Pages are in `src/pages`, scope forms and import wizards in `src/components`, and auth/layout state in `src/context`.
- **Design system (in progress, see `docs/ui-modernization-plan.md`).** `src/styles/tokens.css` holds all design tokens (the only place hex values may live) and bridges the legacy CSS variable names; `src/ui/` holds shared components (Button, Field, DataTable, Dialog, ...); `src/app/` holds the shell (`routes.config.ts` is the single source for routes, nav, breadcrumbs, titles and access rules; `shell/` has Sidebar, TopBar, CommandPalette). Tailwind v4 runs with theme+utilities only (no preflight) and scans `ui/`, `app/`, `filters/`, `dev/`, `pages/`, `components/`. Legacy CSS stays unlayered (it beats utilities unless a utility is `!important`); about half of it was moved into arbitrary-property utilities in the JSX by `scripts/css-to-utilities.mjs` (see the plan, "legacy CSS conversion"). Do not hand-edit those long utility strings expecting legacy cascade behavior: unlayered rules still win over layered ones, and layered `!important` beats unlayered `!important`. Check visual parity with the probes in `scripts/probe/`. Run `npm run lint:css` and `npm run ui:metrics -- --check`.

## Repo conventions

- `AUDIT_MEMORY.md` (root) is the living audit log, if present (currently deleted in the working tree; see git history). Read it before fixing an audit item and update it afterwards.
- Calculation methodology and validation: `docs/calculation-specification.md`, `docs/validation-report.md`.
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