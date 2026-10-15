# Neocarbon — Codebase Map

**Read this before changing code.** It is a navigational index: where each subsystem lives, how a
request flows end to end, which rules bind each area, and how to verify a change. It is *not* a
rule book — binding conventions live in `CLAUDE.md`, and calculation methodology lives in
`docs/calculation-specification.md`. Where those cover a topic, this map links to them instead of
restating.

Last verified against the working tree: **2026-10-10**.

---

## 1. Orientation

**What it is.** Neocarbon is an on-premise greenhouse-gas (GHG) accounting and compliance platform
for the oil & gas industry. It is built for the **Sonatrach** pilot: operators record activity data
per facility, the platform computes Scope 1 / 2 / 3 emissions using published methodology, and a
maker-checker workflow plus a tamper-evident audit trail produce an assurance-ready inventory.

**Standards implemented.** API Compendium 2021 (the primary calculation source), GHG Protocol
(Corporate, Scope 2 Guidance, Scope 3), IPCC AR4 / AR5 / AR6 global warming potentials, OGMP 2.0
(methane reporting levels), ISO 14064 (QA/QC), CBAM (product-embedded emissions), SBTi (targets).

**Two applications, one repo.**

| App | Path | Stack | Port |
|---|---|---|---|
| API | `new/server` | Flask 3 + SQLAlchemy 2 + Alembic | 5000 (`PORT`) |
| SPA | `new/client` | React 19 + TypeScript + Vite 7 | 5173 |

**How to use this map.**

1. Find the subsystem that owns your change in §2 (topology) and §4 / §5 (backend / frontend maps).
2. Read the binding rules for that area in §6 (cross-cutting rules) before writing anything.
3. Run the matching verification in §8 (testing & CI).
4. Walk the pre-flight checklist in §11.

If the map and the code disagree, **the code wins** — and the map is stale; update it (§12).

---

## 2. Repository topology

```
h2/
├── new/                      the real application (everything else is support)
│   ├── server/               Flask API  — see §4
│   └── client/               React SPA  — see §5
├── docs/                     maintained documentation (see §10)
│   ├── validation/           dated audit artifacts (history, not live rules)
│   └── sonatrach/            glossary-fr.csv (HSE French terminology)
├── validation/               extra calculation tests, collected by the ROOT pytest.ini
│   ├── calculation/ differential/ property/ mutation/ regression/ reference_model/
│   └── golden_data/ golden_dataset/ expected_results/ reports/ scripts/ test_cases/
├── deploy/                   containers, nginx, systemd, release tooling — see §9
├── specs/                    spec-driven-development feature specs
│   ├── 001-batch-approve-reject/
│   └── 002-qa-qc-ipcc-iso14064/
├── .agents/                  agent tooling: rules/, workflows/, agents/ (not app code)
├── .specify/                 speckit templates/scripts
├── .github/workflows/        deploy-pages.yml, e2e-matrix.yml, package.yml
├── pytest.ini                ROOT pytest config (collects validation/ + new/server/tests)
└── CLAUDE.md                 binding conventions (read alongside this map)
```

**Generated vs. hand-written.**

| Generated — never hand-edit | Hand-written — safe to edit |
|---|---|
| `new/server/migrations/versions/*.py` (via `flask db`) | `new/server/routes/`, `calculations/`, `services/` |
| `new/client/dist/` (`npm run build`) | `new/client/src/` |
| `__pycache__/`, `.pytest_cache/`, `node_modules/` | `deploy/`, `docs/`, `specs/` |
| `new/client/src/i18n/fr.json` (partly, via `scripts/i18n-wrap.mjs`) | `deploy/.env` (local secrets, untracked) |

**Not in the repository** (do not assume they exist): `archive/` (git-ignored, local only), `graphify-out/` (generated), `AUDIT_MEMORY.md` and a root `package.json` (purged from history on 2026-10-15; kept only in the offline backup bundle), `AUDIT_ARTIFACTS_*/` and `test_artifacts/` (git-ignored outputs).

---

## 3. Runtime topology & request flow

### 3.1 Topology

```
Browser (React SPA, :5173 dev / nginx :80,:443 prod)
   │  fetch/axios, credentials: 'include', X-CSRFToken header on writes
   ▼
Vite dev proxy (/api → 127.0.0.1:5000)   |   nginx (SPA + /api on one address)
   ▼
Flask app (app.py, module-level `app`)
   ├─ ProxyFix (only when TRUSTED_PROXIES is set)
   ├─ Flask-Limiter (Redis or memory)
   ├─ CORS (ALLOWED_ORIGINS only)
   ├─ Flask-WTF CSRF (mutating requests; sign-in included)
   ▼
Blueprint route  →  login_required / admin_required / ... decorator
   ▼
utils.get_allowed_facility_ids / require_facility_access   (RBAC + facility scope)
   ▼
calculations.compute_emissions  |  services/*  |  input_validation
   ▼
SQLAlchemy session  →  SQLite (dev, WAL)  |  PostgreSQL (production)
   └─ before_flush hook (services.audit_chain) seals every ActivityLog row
```

### 3.2 Synchronous write trace — "create a Scope 1 emission record"

| # | Step | Location |
|---|---|---|
| 1 | SPA sends `POST /api/emissions/` with `X-CSRFToken` | `src/api.ts` interceptor |
| 2 | CSRF validated (a 400 triggers one automatic retry after re-fetching the token) | `extensions.py` `csrf` |
| 3 | Implicit limiter check (2000/h default) | `extensions.py` `limiter` |
| 4 | Route handler resolves the current user | `routes/emissions.py` (`POST /`, line 496) |
| 5 | Role + facility scope enforced | `utils.require_facility_access`, `facility_access_error` |
| 6 | Payload validated; body that is not JSON reads as `{}` → 400 not 500 | `input_validation.py`, `app._LenientJSONRequest` |
| 7 | Status chosen (admin → `Verified`, else `Pending`) | `utils.initial_record_status` |
| 8 | Emissions computed | `calculations.compute_emissions` → `flare_defaults` → `legacy_engine` |
| 9 | Row written + audit row written **in one transaction** | `utils.log_activity_and_notify` |
| 10 | `before_flush` seals the audit row's hash chain | `services/audit_chain.py` |
| 11 | `after_commit` clears the dashboard cache | `routes/dashboard.clear_dashboard_cache` |
| 12 | Response returns the created record | `routes/emissions.py` |

### 3.3 Asynchronous path — bulk upload

Uploads do **not** run in the request. The API starts a background job and the client polls:

```
POST /api/emissions/upload/start      routes/emissions_import.py:87
      → background_processor.start_background_upload
      → returns job_id immediately
GET  /api/emissions/upload/status/<job_id>   routes/emissions_import.py:174   (poll)
GET  /api/emissions/upload/errors/<job_id>   routes/emissions_import.py:183   (skip reasons)
POST /api/emissions/upload/check      routes/emissions_import.py:131  (dry-run, saves nothing)
GET  /api/emissions/upload/limits     routes/emissions_import.py:156  (size + concurrency caps)
```

Contrast: `routes/emissions_bulk_upload.py` is the **synchronous** `POST /bulk-upload` (one route);
`emissions_import.py` is the asynchronous wizard API. Do not confuse them.

---

## 4. Backend map (`new/server`)

### 4.1 Entry, config, schema

| File | Owns | Watch out for |
|---|---|---|
| `app.py` | Module-level `app` (**not** a factory). Registers blueprints, Swagger, error handlers, `_LenientJSONRequest`. Calls `init_schema()`. | Importing it has side effects (schema upgrade, indexes, optional admin seed). Tests do `from app import app`. |
| `config.py` | `Config` class. Fail-closed production detection, DB URI, session/cookie, CSRF, rate-limit store. | Any env name that is not `development/dev/local/testing/test` (or unset) is treated as **production** and enforces the checks. |
| `extensions.py` | `db` (`expire_on_commit=False`), `limiter` (Redis or memory), `csrf` (Flask-WTF). | No app object — created here to break import cycles. |
| `input_validation.py` | `ValidationError` + shared query-parameter checks (`invalid_query_parameter`). | Central for `/api/dashboard/*` and `/api/data/production`; other routes keep their own handling. |
| `schema_sync.py` | Legacy index/column sync helpers. | Its docstring still claims it runs `db.create_all()` — it does not. |
| `id_guard.py` | Guards the `it` role against operational-data access by id. | |
| `utils.py` | RBAC + facility scoping + audit/notification + `internal_error` + `iso_utc`. | The enforcement site for most §6 rules. |
| `status.py`, `process_categories.py`, `electricity_factors.py` | Small shared constants/tables. | |
| `background_processor.py` | The async bulk-upload worker. | Not under `services/`. |

**Migration chain** (`migrations/versions/`, 12 revisions, base → head):

```
815d10c5bbe4 → 61bacaad00dc → 2ef6f882b02c → 7fe333372c71 → 52c620a620d2
→ 9c3e1a7b5d20 → a1c4e7f20b31 → b2d5f8e31a42 → a6274c2ef1f5 → b7e2d4c91a05
→ c3f9a2d18e47 → d4e8a1b7c2f0  (HEAD)
```

| Revision | What it added |
|---|---|
| `b2d5f8e31a42` | Scope 2 dual-reporting columns, custom-factor approval metadata, composite indexes |
| `a6274c2ef1f5` | Audit hardening + foreign keys |
| `b7e2d4c91a05` | `emissions.fuel_type` widened to 255 |
| `c3f9a2d18e47` | `import_mappings` (saved import column mappings) |
| `d4e8a1b7c2f0` (head) | Audit-log hash chain: `activity_log.prev_hash` / `entry_hash`, existing rows sealed, append-only trigger on PostgreSQL |

`init_schema()` upgrades to head outside production (or with `AUTO_MIGRATE=true`) and **refuses to
start** in production if the database is behind head. Update the head note here whenever a new
revision lands.

### 4.2 Data model (`models.py` — 31 `db.Model` classes)

| Concern | Models |
|---|---|
| Auth / RBAC | `User` |
| Facilities | `Facility`, `JvPartner`, `FacilityEquityShare` |
| Scope 1 | `Emission`, `EmissionSource`, `ProductionData`, `FlaringDetail` |
| Scope 2 (dual reporting) | `Scope2Emission` |
| Scope 3 | `Scope3Data`, `Scope3Emission` |
| Fugitives | `ComponentInventory`, `FugitiveSurvey`, `MethaneSourceType` |
| Factors | `CustomFactor`, `ImportMapping` |
| OGMP 2.0 | `OgmpSurvey`, `LevelUpgradeLog` |
| Targets / mitigation | `SbtiTarget`, `Goal`, `BaseYear`, `BaseYearRecalculation`, `MitigationRecord`, `MitigationProject` |
| Reporting | `ReportingMetadata`, `CbamProductExport` |
| Audit / system | `ActivityLog`, `Notification`, `SystemSetting` |

Key facts: emission amounts (`co2e_total`, `co2e_location_based`, `co2e_market_based`, ...) are
stored in **tonnes**. `ActivityLog` rows are append-only and hash-chained — never update or delete
them in application code.

### 4.3 HTTP surface

**16 blueprints** registered in `app.py` (~line 400). 191 URL rules in total across all blueprints.

| Blueprint | Mount prefix | Owns |
|---|---|---|
| `auth_bp` | `/api/auth` | sign-in/out, session, CSRF token, password reset |
| `emissions_bp` | `/api/emissions` | Scope 1 records, bulk upload, import/export, review |
| `facilities_bp` | `/api/facilities` | facility CRUD, scoping |
| `data_bp` | `/api/data` | production, emission sources, components, surveys |
| `reports_bp` | `/api/reports` | report generation, exports, OGMP workbook |
| `dashboard_bp` | `/api/dashboard` | all analytics endpoints |
| `custom_factors_bp` | `/api/custom-factors` | custom factor CRUD + approve |
| `scope2_bp` | `/api/scope2` | Scope 2 dual reporting |
| `scope3_bp` | `/api/scope3` | Scope 3 |
| `managedata_bp` | `/api` | manage-data endpoints (mounted at root) |
| `factors_bp` | *(none)* | emission factor catalog; routes carry their own paths |
| `notifications_bp` | `/api/notifications` | polling notifications |
| `audit_bp` | `/api/audit` | audit trail + chain verification |
| `qaqc_bp` | `/api/qaqc` | QA/QC diagnostics |
| `equity_bp` | `/api/equity` | equity shares / JV partners |

Swagger UI is registered at `/api/docs` **only** when not in production (or `ENABLE_PUBLIC_SWAGGER=true`).

**Split-module pattern.** Large blueprints are split across sibling files that register on the
*same* blueprint object. The parent keeps the route handlers and shared helpers; the split modules
import those helpers *back from the parent*, and the parent imports the split modules **last**.

| Parent | Split modules |
|---|---|
| `emissions.py` | `emissions_bulk_upload`, `emissions_export`, `emissions_import`, `emissions_mappings`, `emissions_review`, `emissions_template_csv`, `emissions_template_excel` |
| `dashboard.py` | `dashboard_sbti`, `dashboard_ogmp`, `dashboard_flaring`, `dashboard_bridge` |
| `reports.py` | `reports_export`, `reports_ogmp`, `reports_fingerprint` |
| `auth.py` | `auth_settings`, `auth_users` (re-exported lazily via module `__getattr__`) |

When you move a route, compare `app.url_map` before and after — the split modules register on the
parent blueprint, so a route can silently land under the wrong prefix.

### 4.4 Calculation engine

The entry point every caller uses is **`calculations.compute_emissions`**. It resolves in two layers:

```
routes/*  +  background_processor.py
      │  from calculations import compute_emissions
      ▼
calculations/__init__.py     re-exports compute_emissions from flare_defaults
      ▼
calculations/flare_defaults.py::compute_emissions      (line 36)
      │  applies facility-dependent flare defaults (downstream refinery destruction efficiency 99.5%),
      │  then delegates
      ▼
calculations/legacy_engine.py::compute_emissions       (line 450)
      │  tries the dispatcher first, falls back to legacy factor math
      ▼
calculations/dispatcher.py::CalculationDispatcher      (class at line 125)
      │  ACTIVITY_PROCESS_ALIASES (line 45) + COMBUSTION_METHOD_PROCESSES (line 53)
      │  flat if/elif over process types → branch bodies in:
      │      dispatcher_branches_combustion.py
      │      dispatcher_branches_venting.py
      │      dispatcher_branches_fugitive.py
      ▼
calculators: combustion.py · vented*.py (family) · fugitive*.py · midstream.py · indirect.py · stoichiometry.py
```

- The **legacy fallback** in `legacy_engine` is *not* dead code: it handles zero activity, entered
  Tier 3 factors, saved custom factors, and process types the dispatcher does not model. Set the
  `calculations.legacy_engine` logger to DEBUG to see each use.
- `flare_defaults.facility_segment` reads `Facility.segment` and tolerates **no app context** (for
  offline calculations).
- Unit conversions live in `calculations/units.py`; GWPs in `calculations/constants.py`
  (keep in sync with `new/client/src/constants.ts`); uncertainty in `calculations/uncertainty.py`.

To add a **new process family**: add a branch in the appropriate `dispatcher_branches_*.py` file and
register its aliases in `ACTIVITY_PROCESS_ALIASES` / the dispatcher map.

### 4.5 Services (`services/`, 17 modules + `__init__.py`)

| Module | Responsibility |
|---|---|
| `audit_chain.py` | `before_flush` hook sealing `ActivityLog` rows (SHA-256 chain under a lock) |
| `login_guard.py` | per-address and per-account failed sign-in limits |
| `maker_checker.py` | approval policy helpers |
| `review_batch.py` | batch approve/reject |
| `import_feedback.py` | groups upload skip reasons |
| `scope1_template.py` | one column spec → CSV/Excel Scope 1 templates |
| `column_guard.py` | length/type guard on every length-limited `String` column |
| `dashboard_filters.py` | shared dashboard filter parsing |
| `intensity.py`, `inventory_uncertainty.py`, `gwp_recalculation.py` | analytics helpers |
| `ogmp.py`, `scope2_activity.py`, `scope2_gases.py`, `scope1_calc.py` | domain calculators |
| `email_service.py`, `labels.py` | notifications / display labels |

`background_processor.py` (server root, not under `services/`) owns the async upload worker:
`start_background_upload`, `run_file_check`, `get_job_status`, `normalize_number_cell`,
`active_job_count`.

---

## 5. Frontend map (`new/client`)

### 5.1 Boot & routing

```
src/main.tsx      imports ./i18n FIRST (language resolved before any module renders)
   ▼
src/App.tsx       BrowserRouter + route guards
   │   PrivateRoute · NonITRoute · ITRoute · AdminRoute · SuperuserRoute · AuditRoute
   │   rules also in src/app/access.ts and src/app/RequireRole.tsx
   ▼
src/app/routes.config.ts   ← SINGLE SOURCE for routes, nav, breadcrumbs, titles, access, palette
```

Editing navigation, a page title, or an access rule means editing `routes.config.ts` — not the
sidebar or the router. `NAV_GROUPS = ["Overview", "Data", "Assurance & Reporting", "Administration"]`.

**14 routes + 1 alias:**

| Path | Title | Group | Access |
|---|---|---|---|
| `/` (index) | Dashboard | Overview | nonIT |
| `/carbon-intensity` | Carbon Intensity | Overview | nonIT |
| `/methane-intensity` | Methane Intensity | Overview | nonIT |
| `/sbti` | SBTi & Net-Zero | Overview | nonIT |
| `/methane-explorer` | Emissions Map | Overview | nonIT |
| `/emissions` | Calculations | Data | nonIT |
| `/manage-data` | Manage Data | Data | nonIT |
| `/reference-data` | Reference Data | Data | nonIT |
| `/reports` | Reports | Assurance & Reporting | nonIT |
| `/uncertainty` | Uncertainty | Assurance & Reporting | nonIT |
| `/qa-dashboard` | QA/QC & Diagnostics | Assurance & Reporting | superuser |
| `/audit-trail` | Audit Trail | Assurance & Reporting | audit |
| `/user-management` | User Management | Administration | it |
| `/settings` | Settings | *(pinned, no group)* | nonIT |

Alias: `/dashboard` → `/`. `findRoute()` strips trailing slashes.

### 5.2 API client & state

| File | Owns |
|---|---|
| `src/api.ts` | shared axios instance. `baseURL` = `VITE_API_URL` or `/api`; `withCredentials`. Attaches `X-CSRFToken` on writes and retries **once** on a CSRF 400. On 401 calls `window.__authLogout`. |
| `src/context/AuthContext.tsx` | session/user, login/logout |
| `src/context/LayoutContext.tsx` | shell layout state |
| `src/filters/` | the analytics filter store (`useAnalyticsFilter`) |
| `src/hooks/` | shared hooks (document title, breadcrumb extras, GWP standard, media query) |

There is **no state-management library** (no Redux/Zustand). Two React contexts + a filter store.

### 5.3 Layout

- Pages: `src/pages/` (page components + matching CSS, plus per-page subdirectories).
- Shared shell: `src/app/shell/` (`AppShell`, `Sidebar`, `TopBar`, `Breadcrumbs`, `CommandPalette`,
  `AccountMenu`, ...).
- Component forms/wizards: `src/components/` (e.g. `modals/EditEmissionModal.tsx`, import wizards).
- Shared UI kit: `src/ui/` (Button, Field, DataTable, Dialog, ... + `charts/`, `table/`).

### 5.4 i18n

`src/i18n/index.ts` exports `t("English text", {vars})` — **the English sentence is the key**;
`src/i18n/fr.json` holds the French. A string with no entry stays English. Language is read from
`localStorage` (`neocarbon.language`) before any module renders. Wrap whole sentences, not fragments
around numbers. Data values saved/sent to the API stay English and are translated where shown.
Check coverage with `npm run i18n:check` (`-- --missing`, `-- --strict`).

### 5.5 Design system

- `src/styles/tokens.css` is the **only** place hex colour values may live (it also bridges legacy
  CSS variable names). Palette is unchanged by the modernization work.
- Tailwind v4 runs **theme + utilities only, no preflight**; it scans `ui/`, `app/`, `filters/`,
  `dev/`, `pages/`, `components/`.
- **Legacy CSS is unlayered and wins over layered utilities** unless a utility is `!important`.
  Some legacy rules were converted into long arbitrary-property utility strings by
  `scripts/css-to-utilities.mjs` — do not hand-edit those expecting old cascade behaviour.
- Verify visual parity with the probes in `scripts/probe/`; run `npm run lint:css` and
  `npm run ui:metrics -- --check`.

---

## 6. Cross-cutting rules

Each rule below is enforced somewhere specific. Ignoring it breaks that subsystem in a way tests may
not always catch.

| Rule | Enforced by | If you ignore it |
|---|---|---|
| **RBAC + separation of duties.** `admin` is the only globally-scoped role; `superuser`/`user` are region-scoped; `it`/`it_admin`/`it_manager` have **zero** operational-data access. | decorators in `routes/auth.py`; `utils.get_allowed_facility_ids`, `require_facility_access` | data leak across regions or into IT accounts |
| **Facility ID validation.** Non-numeric facility params → 422. | `utils.facility_access_error`, `input_validation` | 500s from bad foreign keys |
| **CSRF.** `GET /api/csrf-token` sets the token; all writes send `X-CSRFToken`; **sign-in included** (no exemptions). New session after sign-in ⇒ re-fetch the token. | `extensions.csrf`; `src/api.ts` | writes rejected 400 (or a false sense of exemption) |
| **Tamper-evident audit.** Every `ActivityLog` row is SHA-256-chained (`prev_hash`/`entry_hash`) under an advisory lock; append-only trigger on PostgreSQL; checkpoint verification. | `services/audit_chain.py`; migration `d4e8a1b7c2f0` | a chain that forks or a log that can be edited — assurance failure |
| **Atomicity.** Data change + audit row commit in **one** transaction. | `utils.log_activity_and_notify` callers | audit trail that disagrees with the data |
| **Maker-checker / status.** Non-admin records are `Pending`; only `admin` may approve custom factors; `admin`'s own manual entry is `Verified` at creation. | `utils.initial_record_status`, `can_approve`, `services/maker_checker.py` | records approved without a second party |
| **Dashboard cache epochs.** Row changes bump a shared epoch in `system_settings`; every `batch-all` re-checks it (≤1 DB read/s). | `routes/dashboard` `before_commit` hooks + `_get_global_cache_epoch` | stale dashboards across workers |
| **Bulk-upload semantics.** `decimal_mark` required per file; duplicate detection keys on the stored catalog fuel name; concurrency capped per user; `1,000` without a decimal mark is refused, not guessed. | `background_processor.normalize_number_cell`, `services/import_feedback.py` | silently mis-parsed numbers |
| **Text columns.** Over-length / list / dict values raise `ValidationError` (400 naming the field) instead of failing at commit. | `services/column_guard.py` | PostgreSQL commit errors (SQLite does not enforce lengths) |
| **Sign-in limits.** Only failed sign-ins count, per address and per account. | `services/login_guard.py` | lockout behaviour that does not match the docs |
| **No satellite integration.** Copernicus / Sentinel-5P was removed; retired setting keys are never loaded or returned. | `routes/auth_settings.RETIRED_SETTING_KEYS` | resurrecting a removed feature |
| **Map tiles.** Basemap from `MAP_TILE_URL` via `GET /api/map-config`; unset ⇒ facilities without a basemap. | `app.py` map config route | broken map on offline installs |
| **Request body leniency.** A non-JSON body reads as `{}` (400, not 500); NUL characters refused. | `app._LenientJSONRequest` | 500s from malformed clients |

---

## 7. Data & persistence

- **Development:** SQLite `ghg_app.db`. Connect hook enables **WAL**, foreign keys, and
  `busy_timeout`, and runs periodic WAL checkpoints. Engine: `NullPool` (file) / `StaticPool` (`:memory:`).
- **Production:** PostgreSQL **only** (`DB_TYPE=postgres`), engine `pool_size 25 / max_overflow 25 /
  pool_timeout 60`. `postgresql://` / `postgres://` URLs are rewritten to `postgresql+psycopg2://`.
- **Transactions:** a data change and its audit row are committed together. The audit chain seals
  rows in `before_flush`.
- **Backups / restore** (`new/server/scripts/`): `backup.py` (pg_dump `--clean` or SQLite; keeps the
  newest `BACKUP_RETAIN_COUNT`, default 14) and `restore.py` (`--apply` to execute; PostgreSQL
  restores in one transaction and stops at the first error).

---

## 8. Testing & CI

### 8.1 Layout

| Suite | Location | Runner | Notes |
|---|---|---|---|
| Backend unit/integration | `new/server/tests/` (~125 files) | pytest | `tests/conftest.py`: `FLASK_ENV=testing`, temp `tests/test_app.db`, `SEED_ADMIN=false`, CSRF + rate limiter off |
| Independent calculation validation | `validation/` (repo root) | root `pytest.ini` | differential, property, golden-dataset, mutation suites |
| Frontend unit | `new/client/src/**/*.{test,spec}.*` | vitest + jsdom | |
| End-to-end | `new/client/e2e/` + `e2e/deep_user_audit/` | Playwright | needs a running dev server + `storageState.json` |

Two pytest roots: `new/server/pytest.ini` collects `test_*.py` in the server dir (ignoring
`test_runner.py`); the **root** `pytest.ini` sets `pythonpath = . new/server` and
`testpaths = validation new/server/tests`.

### 8.2 Running

```bash
# from new/server
python -m pytest tests/                                   # full backend suite
python -m pytest tests/test_combustion.py::<test_name> -q # one test
python -m pytest -x --timeout=300                         # CI-style run

# from new/client
npm run test                                              # vitest
npx vitest run src/__tests__/<file>                       # one vitest file
npm run e2e:smoke                                         # Tier 1 critical paths
```

### 8.3 CI gates (`.github/workflows/deploy-pages.yml`)

| Group | Tests |
|---|---|
| calculation | `test_independent_differential`, `test_golden_dataset_validation`, `test_property_invariants`, `test_unit_conversions_exhaustive`, `test_battery_gwp_horizons_regulatory`, `test_gwp_uncertainty_propagation` |
| security | `test_api_security`, `test_deep_injection_matrix`, `test_it_role_security`, `test_security_hardening` |
| smoke | `test_production_smoke` |

Frontend gates in the same workflow: `lint`, `check:ts` (fails on any `.js`/`.jsx` under `src/`),
`lint:css`, `ui:metrics -- --check`, `test`, then the production `build`. `e2e-matrix.yml` runs the
Playwright smoke tier (21 tests) on push/PR; the full 124-test matrix is manual-only
(`workflow_dispatch`). `package.yml` builds the Docker images and runs `deploy/smoke-test.sh`.

### 8.4 Ratchets (these fail CI when exceeded)

- `python scripts/loc_ratchet.py --check` — a file in `routes/`, `calculations/` or `services/`
  may not grow past `scripts/loc_baseline.json`; a new file may not exceed 800 lines. After
  shrinking a file, lock it in with `--write`.
- `npm run ui:metrics -- --check` — UI metrics against `ui-metrics.baseline.json`.

---

## 9. Deployment & ops (`deploy/`)

| Artifact | Purpose |
|---|---|
| `Dockerfile` | one multi-stage build; `app` target = gunicorn API on `python:3.11-slim` (non-root, PostgreSQL 16 client tools); `web` target = nginx serving the built SPA |
| `compose.yml` | db, redis, app, web; secrets from `deploy/.env` (see `.env.example`) |
| `nginx/neocarbon.conf.template` | SPA + `/api` on one address, TLS, CSP; forwards `Host $http_host` so the HTTPS CSRF Referer check works on non-standard ports |
| `native/` | systemd units + `install.sh` for installs without containers |
| `release.sh <version>` | offline bundle (saved images, wheels, built SPA); `SKIP_BUILD=1`, `REGISTRY=...` |
| `smoke-test.sh` | checks a running stack through nginx |

The API container entrypoint runs `flask db upgrade` then gunicorn. Helper commands:
`docker compose run --rm app seed-admin|backup|restore`.

**Production fail-closed checks** (`config.py` — startup aborts if any fail): real `SECRET_KEY`; a
valid `DATABASE_URL`; PostgreSQL (no SQLite); non-empty `ALLOWED_ORIGINS` without `*`; a shared
rate-limit store (`REDIS_URL`) unless `ALLOW_MEMORY_LIMITER=true`. Set `TRUSTED_PROXIES` behind a
proxy. Full guide: `docs/deployment.md`.

---

## 10. Docs & specs index

| Document | Read it when |
|---|---|
| `CLAUDE.md` | always — binding rules and conventions |
| `docs/CODEBASE_MAP.md` | this file — navigation before a change |
| `docs/calculation-specification.md` | working on calculation methodology |
| `docs/validation-report.md` | understanding validation evidence |
| `docs/deployment.md` | deploying / operating the stack |
| `docs/ui-modernization-plan.md` | frontend structural/CSS work |
| `docs/hardening-plan.md` | security-hardening history |
| `docs/sonatrach-implementation-plan.md`, `docs/sonatrach-readiness-plan.md` | pilot scope/readiness |
| `docs/sonatrach/glossary-fr.csv` | French terminology for translations |
| `docs/validation/00-current-architecture.md` | a **dated** audit artifact (Sep 2026) — history, not live rules; this map is the maintained reference |
| `docs/validation/*` | forensics on a specific past audit (per-area audits, pilot readiness, 100k bulk) |
| `specs/001-batch-approve-reject/` | batch approve/reject feature spec |
| `specs/002-qa-qc-ipcc-iso14064/` | QA/QC + IPCC/ISO 14064 spec |
| `.agents/rules/`, `.agents/workflows/` | agent-tooling conventions (not application code) |

A graphify knowledge graph (`graphify-out/`) is **absent** from the working tree; if regenerated,
use `graphify query|path|explain` for architecture questions and re-run `graphify update .` after
code changes.

---

## 11. Before you change anything — checklist

1. **Locate ownership.** Which subsystem owns this? Backend route → §4.3; calculation → §4.4;
   page/route → §5.1; shell/design → §5.5.
2. **Check the binding rules** for that area in §6 and in `CLAUDE.md`. Do they constrain the change?
3. **Respect the registration patterns.** New blueprint → register in `app.py` and update §4.3.
   New frontend route → `routes.config.ts` (and §5.1). New process family → dispatcher branch file.
4. **Verify locally** with the matching gate from §8 (single test → targeted suite → full group).
5. **Watch the ratchets** (§8.4): file length in `routes/`/`calculations/`/`services/`, UI metrics.
6. **Re-verify the invariants you touched:** audit chain still verifies, RBAC scope unchanged,
   CSRF still required, status transitions correct.
7. **Do not commit or push unless asked.**
8. **Update this map** if you changed a structure it documents (§12).

---

## 12. Maintenance note

A stale map is worse than none — it sends the next reader to the wrong place with confidence. Update
the map in the **same change** that makes it stale:

| Change | Update |
|---|---|
| New / renamed blueprint or mount prefix | §4.3 table (and the count) |
| New Alembic revision | §4.1 migration chain + head |
| New model class | §4.2 |
| New service / calculation module | §4.4 / §4.5 |
| New / renamed frontend route, nav group, access rule | §5.1 |
| New cross-cutting rule | §6 |
| New CI gate or ratchet | §8.3 / §8.4 |
| New deployment artifact | §9 |
| New top-level doc | §10 |

When in doubt, re-derive the fact from the code (`app.url_map`, `flask db heads`,
`routes.config.ts`) rather than trusting this file.