# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Layout

GHG (greenhouse-gas) accounting platform. The real application lives in `new/`:
- `new/server` — Flask 3 API (SQLAlchemy, Flask-WTF CSRF, Flask-Limiter)
- `new/client` — React 19 + Vite 7 SPA

Everything else at the repo root (loose `*.py`, CSV/PDF/`.patch` files, `temp_old/`, `scratch/`) and the `new/test_*.py` / `new/update_logs*.py` scripts are one-off tooling and data, not app code. The root `package.json` (Express/Electron) is unrelated to the Flask app.

## Commands

Backend (run from `new/server`):
```bash
pip install -r requirements.txt
python app.py                      # 127.0.0.1:5000 (PORT env); debug only if FLASK_DEBUG=true
python seed_admin.py [--force-reset-password]   # uses ADMIN_EMAIL/ADMIN_PASSWORD/IT_ADMIN_*
```
Setting `SEED_ADMIN=true` also seeds the admin and IT-admin accounts on startup.

Backend tests (run from `new/server`):
```bash
python -m pytest tests/
python -m pytest tests/test_combustion.py::<test_name> -q     # single test
```
- `tests/conftest.py` sets `FLASK_ENV=testing`, uses a temporary `tests/test_app.db`, sets `SEED_ADMIN=false`, turns off CSRF and turns off the rate limiter.
- `new/server/pytest.ini` also collects `test_*.py` in the server dir itself. The root `pytest.ini` additionally collects `validation/`.
- CI runs with `-x --timeout=300`, which needs `pytest-timeout` and `hypothesis`. Neither is in requirements.txt.
- CI (`.github/workflows/deploy-pages.yml`) also runs these gate groups separately:
  - calculation: `test_independent_differential`, `test_golden_dataset_validation`, `test_property_invariants`, `test_unit_conversions_exhaustive`, `test_battery_gwp_horizons_regulatory`
  - security: `test_api_security`, `test_deep_injection_matrix`, `test_it_role_security`, `test_security_hardening`
  - smoke: `test_production_smoke`

Frontend (run from `new/client`):
```bash
npm run dev      # :5173, proxies /api -> 127.0.0.1:5000
npm run build
npm run lint
npm run test     # vitest + jsdom; only picks up src/**/*.{test,spec}.*
npx vitest run src/__tests__/<file>          # single file
npm run e2e      # Playwright (e2e/)
```
Playwright needs the dev server running and `storageState.json`, and it hard-codes a local chromium-1208 path.

Other: `new/setup.bat` / `new/start_all.bat` (Windows). There is no Docker setup (removed 2026-10-01): the client is deployed to GitHub Pages by CI; the API runs as a plain Python service (`flask db upgrade`, then `gunicorn app:app` from `new/server`).

## Backend architecture

- **`app.py` creates a module-level `app`, not a factory.** Tests use `from app import app`. Importing it has side effects: it runs `db.create_all()`, creates indexes and optionally seeds admins.
- **Schema changes.** Alembic (`migrations/`) has only two revisions. The schema mostly comes from `create_all`, plus ad-hoc column patches, such as the SQLite connect hook that adds `custom_factors.description`. When adding columns to existing tables, plan how existing DBs get them.
- **SQLite connect hook.** It enables WAL mode, foreign keys and `busy_timeout`, and runs periodic WAL checkpoints.
- **Config (`config.py`).**
  - SQLite `ghg_app.db` is the default. `DB_TYPE=postgres` requires `DATABASE_URL`.
  - Production (detected from `FLASK_ENV`/`APP_ENV`/`ENVIRONMENT`) refuses to start without a real `SECRET_KEY` and a `DATABASE_URL`.
- **Dashboard cache.** SQLAlchemy `before_commit`/`after_commit` hooks call `routes.dashboard.clear_dashboard_cache()` when Emission, Scope2/3, ProductionData, Facility, CustomFactor or OgmpSurvey rows change.
- **Blueprints (`routes/`).** Each is mounted at `/api/<name>`. The exceptions are `managedata_bp` (mounted at `/api`) and `factors_bp` (no prefix; its routes carry their own paths).
- **`extensions.py`.**
  - `db` is created with `expire_on_commit=False`.
  - `limiter` uses `memory://` storage and defaults to 200/min and 2000/h.
  - `csrf` is Flask-WTF.
- **Auth.**
  - Sessions are cookie-based.
  - Decorators in `routes/auth.py`: `login_required`, `admin_required`, `superuser_required`, `it_admin_required`, `it_access_required`.
  - Roles: `user`, `it`, `superuser`, `admin`, `it_admin`, `it_manager`.
  - Facility scoping goes through `utils.get_allowed_facility_ids` (location/region based) and `utils.require_facility_access`, which always denies IT roles.
  - Only `admin` is organisation-wide. A `superuser` is always limited to one region (their `location`; a superuser without a specific region sees nothing). Org-wide records (settings, custom factors, goals, base year, SBTi, reporting metadata) are admin only.
  - Custom factors used by emission records cannot have their values edited (409): create a new factor and archive the old one.
- **CSRF.** `GET /api/csrf-token` sets the token, and mutating requests must send it as the `X-CSRFToken` header.
- **Calculation path.**
  - Routes and `background_processor.py` call `calculations.compute_emissions` (defined in `calculations/legacy_engine.py`).
  - It first tries `dispatcher.dispatch` in `calculations/dispatcher.py`. The dispatcher maps process-type aliases (e.g. `flaring`, `tank_flashing`, `compressor_seal`) to API-Compendium-2021 calculators in `combustion.py`, `vented.py`, `fugitive.py`, `midstream.py`, `indirect.py` and `stoichiometry.py`.
  - If the dispatcher doesn't handle the process type, it falls back to legacy factor math keyed by `factor_source`: `default` (catalog), `custom` (user factor) or `specific` (Tier 3 engineering inputs).
- **Constants.**
  - Units: `calculations/units.py` `CONVERSIONS`.
  - GWPs: `calculations/constants.py`. It holds AR4/AR5/AR6 plus 20-year values, AR5 is the default, and `get_active_gwp()` resolves the active set. The client hard-codes the same values in `new/client/src/constants.js`, so keep the two in sync.
- **Record status.**
  - Manual Scope 1 entries: `Draft` if requested, otherwise `Verified` for `admin` and `Pending` for everyone else (including superuser).
  - Bulk imports, and edits that change physical inputs, set records to `Pending`.
  - Dashboards aggregate `Verified` records.
- **Emission columns** (`co2e_total` etc.) are stored in tonnes.
- **Bulk uploads.** `background_processor.py` runs one `threading.Thread` per job. Job state is kept in the module-level `upload_jobs` dict, so it exists only in that process's memory and is lost on restart.
- **Audit logging.** `utils.log_activity_and_notify(...)` adds ActivityLog and Notification rows to the session **without committing**. The calling route commits.

## Frontend architecture

- Notifications are polled every 30 s (`NotificationCenter.jsx`); there is no SSE stream.
- `src/api.js` is the shared axios instance.
  - `baseURL` is `VITE_API_URL`, or `/api` if unset, and requests use `withCredentials`.
  - It attaches `X-CSRFToken` to mutating requests and retries once on CSRF 400s.
  - On a 401 it calls `window.__authLogout`.
- `src/App.jsx` uses BrowserRouter with route guards: `PrivateRoute`, `NonITRoute`, `ITRoute`, `AdminRoute`, `SuperuserRoute`, `AuditRoute`.
- Pages are in `src/pages`, scope forms and import wizards in `src/components`, and auth/layout state in `src/context`.

## Repo conventions

- `AUDIT_MEMORY.md` (root) is the living audit log. Read it before fixing an audit item and update it afterwards.
- A graphify knowledge graph exists in `graphify-out/` (`.agents/rules/graphify.md`). Use `graphify query "<q>"`, `graphify path "<A>" "<B>"` or `graphify explain "<concept>"` for architecture questions. Run `graphify update .` after modifying code.

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