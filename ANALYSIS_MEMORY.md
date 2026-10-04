# ANALYSIS MEMORY — H2 / NeoCarbon GHG Platform

> **Read-only analysis artefact.** Created 2026-10-02 for the agent's own reuse across sessions.
> **No application source, test, configuration, or database file was modified to produce this file.**
> Evidence-first: every claim below carries `path:line`. Verified = read in the current working tree.
> Supersedes stale statements in `AUDIT_MEMORY.md` §0 where the two disagree (see §8).

---

## 1. What this software is

An enterprise GHG (greenhouse-gas) accounting, MRV and regulatory-reporting platform for oil & gas and
heavy industry. It is **not one app** — the repo is a working directory containing a real product plus a
large amount of one-off tooling, audit output, marketing collateral and archives.

| Layer | Location | Stack | Scale |
|---|---|---|---|
| API | `new/server` | Flask 3.0.3, SQLAlchemy 3.1.1, Flask-Migrate, Flask-WTF CSRF, Flask-Limiter | 214 `.py`, **68,498 LOC** (100 test files, 21,994 LOC) |
| SPA | `new/client` | React 19, Vite 7, axios, recharts **+** chart.js, Formik+Yup, jsPDF, Leaflet | 143 files, **81,768 LOC** |
| Domain | `new/server/calculations/` | API Compendium 2021 calculators + legacy factor engine | 25 modules |
| Governance | root `*.md`, `audit/`, `docs/validation/` | living audit memory, 115-entry defect ledger, 12-workstream audit | ~340 KB of markdown |

Root-level `package.json` (Express/Electron) is **unrelated** to the Flask app.

---

## 2. Backend architecture (verified)

### 2.1 App assembly — `new/server/app.py`
- **Module-level `app`, not a factory** (`app.py:16`). Import has side effects; tests do `from app import app`.
- On import: `init_schema()` → `ensure_database_indexes()` → `ensure_admin_seeded()` (`app.py:486-489`).
- 17 blueprints (`app.py:322-338`). Prefixes: `/api/auth`, `/api/emissions`, `/api/facilities`, `/api/data`,
  `/api/reports`, `/api/dashboard`, `/api/custom-factors`, `/api/scope2`, `/api/scope3`,
  `managedata_bp` at `/api`, `factors_bp` with **no prefix** (routes carry own paths), `/api/notifications`,
  `/api/audit`, `/api/satellite`, `/api/qaqc`, `/api/cap`, `/api/equity`.
- Middleware chain: rotating log handler 50 MB ×3 (`app.py:25-33`); CORS with credentials (`app.py:37-44`);
  `id_guard.install()` (`app.py:52-54`); SQLite pragmas WAL + FK + `busy_timeout=30000` (`app.py:75-84`);
  cache-invalidation session hooks (`app.py:87-110`); `FiniteJSONProvider` that never emits NaN/Infinity
  (`app.py:142-150`); request guards for non-finite JSON (`app.py:158-164`), **session-version revocation**
  (`app.py:168-185`), non-object JSON rejection (`app.py:189-206`).
- Security headers set on every response: CSP, `X-Frame-Options: DENY`, `nosniff`, `Referrer-Policy`
  (`app.py:213-223`). All `/api` responses `no-store` except the SSE stream (`app.py:227-234`).
- Probes: `/`, `/api/health`, `/api/health/live`, `/api/health/ready` (the last also reports WAL size).
- Runs `127.0.0.1:5000` only, debug gated on `FLASK_DEBUG` (`app.py:562-572`).

### 2.2 Configuration — `new/server/config.py`
- Production detection from `FLASK_ENV`/`APP_ENV`/`ENVIRONMENT`; production **refuses to start** without a real
  `SECRET_KEY` and `DATABASE_URL` (`config.py:19-32`).
- Dev `SECRET_KEY` fallback is the literal `dev-secret-key-change-in-prod-please` (`config.py:35`).
- SQLite is the default; file-backed SQLite uses **`NullPool`** (`config.py:77-81`), `:memory:` uses `StaticPool`.
- Session: 8 h, `HttpOnly`, `SameSite=None` + `Secure` in prod else `Lax` (`config.py:90-99`).
- `WTF_CSRF_SSL_STRICT = False` (`config.py:103`) — needed for the GitHub-Pages-origin frontend.
- `MAX_CONTENT_LENGTH` 50 MB (`config.py:109`); limiter storage `memory://` (`config.py:116`).
- Rate-limit key is **per signed-in user**, per IP otherwise (`extensions.py:25-46`), default 200/min + 2000/h.

### 2.3 Persistence — `new/server/models.py` (798 lines, 32 tables)
- `db = SQLAlchemy(session_options={"expire_on_commit": False})` (`extensions.py:7`).
- Core entities: `User`, `Facility`, `Emission` (Scope 1), `Scope2Emission`, `Scope3Emission`,
  `ProductionData`, `EmissionSource`, `ComponentInventory`, `FugitiveSurvey`, `CustomFactor`, `ActivityLog`,
  `Notification`, `OgmpSurvey`, `MethaneSourceType`, `LevelUpgradeLog`, `SbtiTarget`, `Goal`, `BaseYear`,
  `BaseYearRecalculation`, `MitigationRecord`, `MitigationProject`, `Scope3Data`, `ReportingMetadata`,
  `CbamProductExport`, `CapEmission`, `CapRegulatoryLimit`, `FlaringDetail`, `JvPartner`,
  `FacilityEquityShare`, `SystemSetting`, and `id_high_water` (created at runtime by `id_guard.py`).
- Passwords: `werkzeug.security.generate_password_hash` / `check_password_hash` (`models.py:37-41`).
- `Emission` carries per-gas values, GWP version, tier/OGMP level, maker-checker identity snapshots, and
  **four composite indexes** (`models.py:199-204`).
- `Facility` cascades to 9 child tables (`models.py:76-117`).
- Progress/status vocabulary is centralised in `utils.py:155-171` (`Draft` / `Pending` / `Verified` / `Rejected`).

### 2.4 Schema governance
- **Alembic chain is linear and complete** — verified by reading every revision:
  `815d10c5bbe4` (root, facilities.segment) → `61bacaad00dc` → `2ef6f882b02c` → `7fe333372c71` →
  `52c620a620d2` → `9c3e1a7b5d20` → `a1c4e7f20b31` (head). Live DB is **at head** (`alembic_version = a1c4e7f20b31`).
  Every revision implements both `upgrade()` and `downgrade()`.
- **The real schema authority is `models.py` metadata, executed through Alembic**, not the revisions
  themselves: `9c3e1a7b5d20_reconcile_schema_with_models.py:27` calls `db.metadata.create_all(bind, checkfirst=True)`
  then `add_missing_columns` / `create_missing_indexes` from `schema_sync.py`. Consequences: a fresh DB
  bootstraps correctly, but `alembic downgrade` below that revision does not drop tables (its `downgrade` is `pass`),
  and `flask db migrate` autogenerate will produce enormous diffs.
- `init_schema()` (`app.py:454-483`) upgrades to head outside production (or with `AUTO_MIGRATE=true`) and
  **refuses to start** if the DB is not at head in production.
- `ensure_database_indexes()` still issues raw `CREATE INDEX IF NOT EXISTS` DDL (`app.py:422-446`) — a second,
  parallel index source alongside the model-declared indexes. Both are present on the live DB.
- `id_guard.py` monkey-patches `before_insert` on `Emission`, `Scope2Emission`, `Scope3Emission`,
  `CustomFactor`, `ProductionData` so SQLite never reuses a deleted row's id (audit references ids).
  It assigns the PK explicitly from an `id_high_water` table; the `INSERT OR IGNORE` takes the write lock first,
  which serialises concurrent inserts. Correct, but it adds one write per insert.

### 2.5 Calculation path
```
routes/*.py ─â"
             ├─► calculations/legacy_engine.py:compute_emissions  (entry point, calculations/__init__.py:4)
background_processor.py ─┘
   └─► _compute_emissions_impl
          ├─ 1. normalize process_type aliases (legacy_engine.py:243-263)
          ├─ 2. merge flat payload + calc_inputs[process] into `inputs` (legacy_engine.py:287-316)
          ├─ 3. dispatcher.dispatch(process, inputs, factor_data, uncertainties, gwp_dict)   â| primary
          │        CalculationsDispatcher.calculators: ~90 process aliases (dispatcher.py:130-207)
          ├─ 4. Tier-3 "specific" engineering factors (legacy_engine.py:390-465)
          ├─ 5. custom factor with `type` key (legacy_engine.py:467-483)
          └─ 6. legacy factor math keyed by factor_source default/custom/specific (legacy_engine.py:485-554)
   └─► MissingFactorError if amount > 0, source in (default/custom), and no factor values resolved
       (legacy_engine.py:558-596)  â| deliberately refuses to book a silent 0 tCO2e
```
- Unit/GWP truth: `calculations/units.py` (`CONVERSIONS` 23-79, dimensional maps 202-283, canonical
  `norm_unit`/`unit_dimension`/`parse_factor_unit` helpers 623-839) and `calculations/constants.py` (GWP sets).
- Active GWP resolves through `get_active_gwp()`: explicit dict → explicit standard → `SystemSetting.gwp_standard`
  with a **30-second in-process cache** (`constants.py:38-88`).
- Uncertainty: `calculations/uncertainty.py`; inventory roll-up in `services/inventory_uncertainty.py`.

### 2.6 Auth / RBAC (verified in `routes/auth.py`, `utils.py`)
- Decorators: `login_required`, `it_admin_required` (`it_admin`,`it_manager`), `it_access_required`
  (adds `it`), `admin_required`, `superuser_required` (`superuser`,`admin`). All check `status == "active"`.
- `get_allowed_facility_ids(user)` (`utils.py:21-55`): `None` = unrestricted (admin; superuser with
  location in `all/global/""`), `[]` = **zero access** for `it_admin`/`it_manager`/`it`, else ids matching
  `region|location|name ILIKE user.location`.
- `require_facility_access` always denies IT roles (`utils.py:58-73`).
- `facility_in_user_scope` / `facility_change_allowed` (`utils.py:85-118`) validate the *resulting* attributes so a
  regional user cannot re-region a facility out of their own scope.
- Session revocation: `User.session_version` bumped on logout, password change/reset, status change; a
  `before_request` hook clears any session whose `sv` is stale (`app.py:168-185`).
- Maker-checker state machine is centralised in `services/maker_checker.py` — see §7.

---

## 3. Frontend architecture (verified)

- `src/api.js` — single axios instance; `baseURL = VITE_API_URL || "/api"`, `withCredentials`, `X-CSRFToken`
  on mutations, **one** retry on a CSRF-flavoured 400 (`api.js:44-63`), `window.__authLogout()` on 401.
- `src/App.jsx` guards: `PrivateRoute`, `NonITRoute` (redirects IT roles to `/user-management`),
  `ITRoute`, `AdminRoute` (admin only), `SuperuserRoute` (admin+superuser), `AuditRoute`
  (admin+superuser+it_admin+it_manager).
- 15 page areas; the five largest files are `ManageData.jsx` (4,030), `Scope1Form.jsx` (3,209),
  `UserManagement.jsx` (1,776), `DashboardEnhanced.jsx` (1,747), `BulkImportModal.jsx` (1,718).
- The client **re-implements** emission arithmetic, factor catalogs and PDF generation
  (`utils/EmissionFactors.js` 1,093 LOC, `utils/ModernReportGenerator.js` 1,607 LOC) — a standing drift risk
  against the Python catalogs.
- GWP constants are correctly mirrored: `src/constants.js:1-76` matches `calculations/constants.py` exactly
  (AR4 25/298/72/289, AR5 28/265/84/264, AR6 27.9/273/81.2/273) and `CH4_DENSITY_KG_M3 = 16.04/23.685`
  matches `units.py:66`. **No drift.**
- Build emits `stats.html` (1.4 MB rollup bundle analysis) on **every** build (`vite.config.js` visualizer,
  `open:false`) — it lands in the client directory and is not in `.gitignore`.
- Two charting libraries are shipped (recharts **and** chart.js); `new/client/dist/` contains stale
  production assets including a captured session cookie file (`storageState.json`, untracked/ignored).

---

## 4. Verified current state (what is actually fixed)

Spot-verified against the current tree, independently of `AUDIT_MEMORY.md` claims:

| Item | Evidence | Verdict |
|---|---|---|
| BUG-001 bulk-job RBAC/scope bypass | `routes/emissions.py:2571-2578` rejects IT roles and gates `facilities`/`custom_factors` to admin/superuser; `background_processor.py:2222-2240` re-checks uploader role + region scope per row | **FIXED** |
| BUG-016 Alembic chain unusable | 7-revision linear chain, all reversible, live DB at head `a1c4e7f20b31` | **FIXED** |
| BUG-012/023/024 composition %, denominators, 10^n scale | `units.py:862-894` (`composition_fractions` scales all components once), `units.py:744-797` (`parse_factor_unit` applies `_SCALE`) | **FIXED** |
| BUG-005/013/082 GWP-20 and hard-coded GWP labels | `constants.py:9-17` carries correct 20-yr pairs; client mirrors them | **FIXED** |
| BUG-009/010/069 facility & user deletion FK failures / maker-checker identity loss | `models.py:651` cascade added; `routes/auth.py:1113-1133` derives every `users.id` FK from `db.metadata` and snapshots `*_name` labels first | **FIXED** |
| BUG-114 cookie survives logout | `session_version` + `app.py:168-185` | **FIXED** |
| BUG-076 bulk job readable by others | `routes/emissions.py:2625-2631` owner-or-admin check | **FIXED** |
| BUG-067/070/074/092 maker-checker | `services/maker_checker.py` — segregation-of-duties filter, status guard, atomic conditional UPDATE, maker notification | **FIXED** |
| BUG-087 raw `str(e)` leakage | `utils.internal_error()` + central handlers | **FIXED** (residual `except:` blocks remain in `legacy_engine.py:404,418`) |

Ledger status: `AUDIT_FINDINGS.md` holds **BUG-001 ... BUG-115**, every one still marked
`**Status:** Confirmed` — the file is an append-only discovery log and is **not** updated when a bug is fixed.
Fixes are recorded separately in `AUDIT_MEMORY.md`, `audit/FIX_LOG.md` and the per-workstream files.
**Never read `AUDIT_FINDINGS.md` as a list of open defects.**

---

## 5. Findings from this analysis (new / not in the ledger)

Severity: C = critical, H = high, M = medium, L = low.
Totals: **8 critical, 24 high, 33 medium, 9 low** across 5.1-5.8, plus the SPA findings in 5.9.
Every item marked **[verified]** was independently reproduced by reading the code or inspecting the live
database; the rest are code-backed reads. Findings unique to the security deep-read are also written up in
`audit/SECURITY_REVIEW_GHG_AUTH_CSRF_INJECTION.md`.

### 5.1 Access control
1. **[H] The lowest IT tier (`it`) can reset any password, including an administrator's.**
   `routes/auth.py:1152-1153` protects `/api/auth/users/<id>/reset-password` with `it_access_required`, which
   admits `it`, `it_manager`, `it_admin` (`routes/auth.py:181-201`); there is no rank check and no target
   restriction. The endpoint's own docstring says "IT Admin resets a user's password directly".
   **Important nuance: this appears to be intended** — `tests/test_it_role_security.py:84-101`
   (`test_it_user_can_reset_password`) asserts exactly this and passes. Treat it as an accepted-risk decision
   to re-confirm rather than a regression: any `it` account is a full account-takeover path to `admin`, and
   there is no forced rotation after an admin-initiated reset.
   *If it is not intended: use `it_admin_required` and forbid resetting a target whose role outranks the caller.*
2. **[H] An IT administrator can mint `superuser` accounts.**
   `routes/auth.py:281-282` blocks IT roles only from `role_requested == "admin"`. `superuser` is accepted, and
   `superuser_required` grants that role broad data authority (`routes/auth.py:246`). Contradicts the
   separation-of-duties rule enforced on updates (`routes/auth.py:1034-1036`).
   *Fix: extend the register guard to `role_requested in ("admin", "superuser")`.*
3. **[M] `POST /api/auth/logout` has no `@login_required` and no `@csrf.exempt`** (`routes/auth.py:484-486`).
   A cross-site request can log a victim out; because logout **increments `session_version`**
   (`routes/auth.py:493`), every other device the victim is signed in on is invalidated too. Bounded by
   `60 per minute`, still a CSRF-able denial of service.
   *Fix: `@login_required` + CSRF on logout, and revoke only the current session.*
4. **[M] Latent `auditor` role.** `auditor` is treated as a read-only role in **18 places** across
   `routes/scope2.py`, `scope3.py`, `data.py`, `cap_routes.py`, `services/maker_checker.py`,
   `routes/emissions.py` — but it is absent from every `VALID_ROLES` set
   (`routes/auth.py:273-277`, `1026-1027`) and from the client's role list. Unreachable-by-API dead policy.
5. **[M] The client role catalogue contradicts the server's.**
   The dropdowns offer `user`, `superuser`, `admin`, `it_manager`, `it`
   (`UserManagement.jsx:797-801, 1364-1368`) — **`it_admin`, the highest-ranked role (`routes/auth.py:273`),
   cannot be assigned through the UI at all**, even though the server accepts it (`routes/auth.py:274`) and the
   admin seed script creates it. Conversely the test suite asserts an `it` user can reset passwords
   (`tests/test_it_role_security.py:84`), a capability the IT-only screens do not surface clearly.
6. **[M] UI navigation and route guards disagree, so some accounts see links they are redirected away from.**
   - `Sidebar.jsx:324` shows Reports to `it_admin`/`it_manager`, but `/reports` is `NonITRoute`
     (`App.jsx:130-137`), which redirects IT roles to `/user-management`; the API also 403s them
     (`routes/reports.py:321, 522, 560, 797`).
   - `/qa-dashboard` is `SuperuserRoute` (`App.jsx:122-129`) while `Sidebar.jsx:511` lists it for
     `it_admin`/`it_manager` as well.
   Root cause: the role hierarchy is re-declared in the sidebar, in six route guards, in ~18 server-side
   `in [...]` checks and in two `ROLE_RANK` dicts. There is no single source of truth.
7. **[L] Duplicated `VALID_ROLES`.** Two hand-maintained `ROLE_RANK`/`VALID_ROLES` literals in the same file
   (`routes/auth.py:273` and `1026`).
8. **[L] Every route was checked for a missing auth decorator.** The only handlers without one are
   `POST /auth/login` and `POST /auth/forgot-password` (both deliberately `@csrf.exempt`), `/logout`
   (item 3), `GET /auth/me` (answers 401 itself), and the two unauthenticated template downloads
   (finding 124). The `/api/audit/stats` alias in `routes/managedata.py:978-983` has no decorator but calls
   the decorated view, so it inherits the check — **verified with a test client: anonymous GET returns 401,
   not data.** It is nonetheless a genuine duplicate registration (`app.py:331` and `:334`) — protection by
   accident.
9. **[H] The IT lockout is applied per-module, not centrally, so several modules leak to IT roles.**
   `utils.get_allowed_facility_ids` returns `[]` for every IT role (`utils.py:31`), and most routes check it
   with `if allowed is not None` (correct). But some read endpoints have **no role gate at all**:
   - `GET /api/cap/limits`, `/api/cap/emissions`, `/api/cap/compliance` (`cap_routes.py:37, 56, 203`) —
     readable by `it`, `it_manager` and `it_admin`. Criteria-air-pollutant and Decree 06-138 data.
   - `GET /api/equity/partners`, `/shares`, `/allocation` (`equity_routes.py:34, 51, 203`) — same, plus
     commercial JV ownership data.
   - `/api/satellite/sentinel5p/*` blocks **only `it_admin`** (`satellite.py:111, 134, 205, 349`; no gate at
     all on `/test-connection` at `:67`), so `it_manager` and `it` pass. The membership check at
     `satellite.py:147` is further short-circuited by `facility_id and ...`, so an IT account with
     `allowed_fids == []` can query arbitrary coordinates. **Verified with a test client: `it_manager` gets
     200 on layer-config, test-connection and coordinate-only queries, while `GET /api/emissions` gives 403.**
   - `GET /api/auth/users` (`auth.py:984-985`) exposes the full directory (emails, roles, locations) to the
     lowest IT rung via `it_access_required`.
   Root cause: five ad-hoc role tuples instead of one predicate. *Fix: a single `services/rbac.py` predicate.*
10. **[H] Unguarded `int()`/`float()` on user input returns HTTP 500 and can skip the authorization comparison.**
    Worst cases: `scope2.py:308` and `scope3.py:118`, where the scope test itself is
    `int(facility_id) not in allowed_fids` — a non-numeric `facility_id` raises **before** any scope check.
    **Verified with a test client: `POST /api/scope2` and `/api/scope3` with `facility_id="abc"` return 500.**
    Also `data.py:543-544`, `managedata.py:771, 774, 779`, `dashboard.py:868, 874, 879`, `facilities.py:181,
    301`, `reports.py:617`, `cap_routes.py:226`, `equity_routes.py:226`, `data.py:331, 634, 681-682`,
    `satellite.py:238-251`, `auth.py:909`.
11. **[H] 26 mutating routes write no `ActivityLog` at all** — production data create/delete/import
    (`data.py:75, 220, 253`), OGMP level upgrades (`data.py:537`), the mitigation and reporting-metadata
    group (`managedata.py:269, 340, 428`), goals and base years (`managedata.py:677, 760, 819`), facility
    import (`facilities.py:428`), every notification mutation (`notifications.py:167, 200, 237, 261`), the
    legacy bulk JSON import (`emissions.py:506`), report issuance (`reports.py:316`) and equity shares
    (`equity_routes.py:139`). For a product whose selling point is an assurance trail this is the largest
    single functional gap.
12. **[H] Ten routes commit the data change and the audit row in two separate transactions**, so a crash or a
    failed second commit leaves a record with no audit entry: `custom_factors.py:214/229, 312/327, 357/372,
    474/489`; `emissions.py:2871/2906`; `managedata.py:101/115, 137/151, 173/187, 594/608`;
    `scope2.py:423/454`; `scope3.py:184/199/211`; `dashboard.py:902/914`. This violates the documented
    contract (`utils.py:210-281` adds rows; the caller commits once). `background_processor.py:982-997`
    gets it right.
13. **[M] Silent data loss on a blank numeric field.** `scope2.py:558-560` calls
    `parse_number(..., required=False, default=0.0)` for four activity columns, so `{"heat_mmbtu": null}` in a
    PUT **zeroes** the stored activity with no error and no before/after audit values.
14. **[M] `ilike` filters built from user input without escaping** in `reports.py:641, 643, 645, 650-653, 687,
    689, 694, 733-734` (`search=%` forces a full scan and neutralises other filters) and in the facility-scope
    matcher itself (`auth.py:48-50`, where a `user.location` of `%` would match every facility).
    `emissions.py:36-38` already carries the `_escape_like` helper.
15. **[M] Unbounded queries** — `audit.py:406` runs `ActivityLog.query.all()` then a pure-Python SHA-256 chain
    over every row; `qaqc.py:114-135` loads every non-flagged emission and computes medians in Python;
    `dashboard.py` has 22 `.all()` calls and zero `.limit()`; `equity_routes.py:236-268` and
    `cap_routes.py:231-234` are N+1 per facility. `emissions.py:4047` removes the row bound for `?all=true`
    while `?limit=abc` raises `ValueError` → 500.
16. **[M] `GET /api/production/years` (`managedata.py:493-498`) and the year list in `/filters/available`
    (`managedata.py:511-527`) are not facility-scoped**, unlike every sibling handler in the same file.
17. **[M] A region-scoped superuser can DELETE corporate goals and base years but not create them** —
    `managedata.py:649` and `:904` require `get_allowed_facility_ids(user) is None` (unrestricted) while the
    siblings `:681` and `:823` require only `admin|superuser`.
18. **[M] `utils.can_approve` (`utils.py:174-179`) is dead code**; the live rule is duplicated in
    `services/maker_checker.py:164`.
19. **[M] `utils.log_activity_and_notify` only fans out notifications for `CREATE`/`UPDATE`/`DELETE`**
    (`utils.py:252`), so `APPROVE`, `REJECT`, `IMPORT`, `ARCHIVE`, `EXPORT`, `LOGIN`, `LOGOUT`, `REGISTER`
    and `DELETE_USER` never notify anyone despite the function name.
20. **[M] Bulk-job state is more durable than `CLAUDE.md` claims.** `background_processor.py:31-93` snapshots
    each job to `<tempdir>/ghg_upload_jobs/<job_id>.json` atomically and `_load_job` serves other workers,
    with a 600 s staleness rule (`:19, 88-92`). Real gaps instead: the snapshot lives in the OS temp dir
    (wiped on reboot/container recycle), the **staged upload file** is written to the temp root and so is
    never reaped by `_prune_old_jobs` (`:265-294`) if a worker dies, and the dedupe maps are built before the
    loop (`:739-764`) so two concurrent jobs importing the same natural keys both insert.
21. **[L] `POST /api/emissions/upload/start` and every synchronous bulk-import endpoint carry no per-route
    rate limit** (`emissions.py:2545`; `scope2.py:685`; `scope3.py:394`; `data.py:251`; `managedata.py:157, 577`).
22. **[L] `rate_limit_key` falls back to `get_remote_address()`** (`extensions.py:36`) while `ProxyFix` is
    opt-in (`app.py:64-66`), so behind a reverse proxy every anonymous user shares one bucket.
23. **[L] `satellite.py:298-312` builds its `ActivityLog` by hand** with `entity_id=str(facility_id)` and a
    NULL `facility_id`, so the entry is invisible to regional auditors (`audit.py:68`).

### 5.2 Calculation engine (independently reproduced where marked)
24. **[C] `GHGCalculator.convert_factor_to_kg` is dimensionally unsound. [verified by execution]**
   `legacy_engine.py:111-159` puts volume, mass **and time** denominators in one `conv` table and applies it as
   `f/a` (`:156-159`), defaulting unknown tokens to `1`. Reproduced:
   `convert_factor_to_kg(1.0, "tonne CH4/yr", "m3")` → **8,760,000.0** (should be ≈0.001 kg/m³);
   `(1.0, "kg/hr", "m3")` → `1.0`; `(1.0, "kg/TJ", "m3")` → `1.0` (silently unscaled).
   Live on the documented Tier-3 specific-factor path (`legacy_engine.py:343-346, 390-465`), which still calls
   it — the strict `combustion.convert_factor_to_kg_per_unit` is only used by the dispatcher's generic path.
   *Fix: delete the function and route the specific-factor path through the strict converter.*
25. **[C] AGR books CH4 for a zero-throughput record.** `midstream.py:1086, 1100-1106` defaults `unit_count` to 1
    and the dispatcher never passes it (`dispatcher.py:2015-2025`), so `throughput = 0` still yields
    0.6482 t CH4/day × 365 ≈ **236.6 t CH4**.
26. **[H] Bare `except:` silently switches the calculation method.** `legacy_engine.py:404` and `:418` swallow
    every exception and fall through to a different factor source; a failed unit conversion becomes the raw
    value rather than an error. Enables finding 9 to pass unnoticed.
27. **[H] `VentedGasCalculator._frac` treats every composition input as a percentage.** `vented_gas.py:42-44`
    divides by 100 unconditionally, so a user entering the fraction `0.85` (85 %) gets **0.85 % — 100× low**,
    silently. Live via `dispatcher.py:534-536` for `vented_gas`, `desiccant_dehydrator`, `co2_eor`.
    `activity_factors.py:222-225` and `midstream.py:191-192` accept fractions correctly, so the app is
    self-inconsistent.
28. **[H] CH4/CO2 asymmetry in the activity-factor calculator.** `activity_factors.py:221-226` reads
    `ch4_content = 0.85` as 85 % but `co2_content = 0.85` as 0.85 % → **CO2 100× low**; TOC rows drop CO2
    entirely (`:228-231`).
29. **[H] Uncertainty taxonomy is missing 24 of the 38 category strings the calculators pass.**
    `uncertainty.py:101-155, 402-413, 545-552` and `dispatcher.py:2361`: `fugitive_facility`,
    `fugitive_screening/_ogi/_measurement`, `tank_flashing`, `workover_no_hf`, `casing_gas`, `loading`,
    `well_testing`, `compressor_venting`, `non_routine_venting`, `co2_eor`, `vented_gas`,
    `desiccant_dehydrator`, `thermal_oxidizer`, `routine/non_routine/safety_flaring`, `gathering_*`,
    `processing_*`, `transmission_*`, `distribution_*`, `lng_venting`, `ccus_venting`, `blanketed_tanks`,
    `chemical_injection_pump`, `gas_dehydration`, `crude_transport`, `fire_suppression`,
    `production_non_routine` all collapse to `"combustion"`, losing the ±20 % fugitive / ±15 % vented
    activity terms. The **Uncertainty and QA dashboards are therefore wrong for those pathways.**
30. **[H] Silent unit fallbacks keep bad units from erroring.** `dispatcher.py:1566-1567` (any unknown tank
    throughput unit is read as bbl), `dispatcher.py:690` (missing unit → m3), `vented.py:733-734` (unknown
    completion volume unit → scf), `vented.py:2186-2187` (`except Exception: oil_bbl = oil_val`),
    `vented.py:2462` (unknown vent-rate unit → scf/hr), `legacy_engine.py:156-159`.
31. **[M] `calculate_co2e` arguments are swapped in five places** — `vented_downstream.py:293, 418, 600, 711, 794`
    pass `(ch4, co2, n2o)` into `(co2, ch4, n2o)`. Currently **dormant** (that module's calculators are not
    routed — see finding 22), but any 100 t CO2-only record would report 2,800 t.
32. **[M] A guaranteed exception sits in `vented_downstream.py:706`** — `convert(scf_ch4, "scf", "tonne_ch4")`
    and `"tonne_ch4"` does not exist in `units.py`. Also dormant.
33. **[M] A 0.95 flare-efficiency floor overrides user input** at 15 sites
    (`vented_production.py:218, 439, 797, 995, 1140, 1704`; `vented_midstream.py:204, 313, 400, 507, 599, 676,
    806, 899`; `vented_lng_distribution.py:371`): `eff = max(0.95, eff)` silently raises a genuine 0.60.
    Dormant today, live the moment those calculators are registered.
34. **[M] `fugitive_onshore.py:467, 549, 607, 647` pass `tier="Tier 3"` (a string)**, so
    `ACTIVITY_UNCERTAINTY.get("Tier 3", T1)` yields the ±10 % Tier-1 activity uncertainty instead of ±2 %.
35. **[M] Partial gas analyses understate mass.** `vented_downstream.py:495-507` sums only the supplied species
    for `mix_mw`, so an 85 %-CH4-only analysis is ~22 % light (reached via `dispatcher.py:358-372`).
36. **[M] Invented defaults survive in live paths** even though the audit removed the worst ones: 85 % CH4
    (`dispatcher.py:1993, 2170`; `vented.py:654, 2469`; `midstream.py:76, 238`), 70 %/10 % associated-gas Tier 2
    (`vented.py:2366-2367`), desiccant 3.0 scf/gal and an 80/20 flash split (`midstream.py:254-257, 302`),
    `has_flash_tank=True` (`dispatcher.py:2188`), 0.0001 kg/MMBtu N2O (`combustion.py:541`, `vented.py:70, 551`,
    `vented_production.py:85`), AGR `co2_out=0.001` (`dispatcher.py:1977`), and a hard-coded `"Algeria"` country
    in `services/intensity.py:239, 265`.
37. **[M] ≈3,000 lines of calculator code are unreachable from `dispatch()`** — all of `vented_midstream.py`,
    `vented_lng_distribution.py`, `vented_ccus_transport.py`, `vented_exploration.py`, `vented_downstream.py`
    except `RefiningHydrogenPlantCalculator`, plus seven classes inside `vented_production.py`. They have
    compendium tests (so they "pass") but no production caller. `fugitive.py:68 EquipmentFugitiveCalculator` is
    registered for six aliases yet those aliases reach `_generic_calculation` (`dispatcher.py:847`) first.
38. **[M] Duplicate factor tables disagree.** `emission_factors.py:27` imports the canonical
    `CORRELATION_EQUATIONS` from `emission_factors_api2021.py:1941-1948` and then **shadows it** at
    `emission_factors.py:377-427` with legacy keys and no `default_zero`. **Verified at runtime:** the live
    object is the legacy one (`flange.pegged_100k = 0.089`, canonical is `0.084`; legacy has no `default_zero`).
    Also duplicated: Table 7-8 (`fugitive_onshore.py:83-88` / `emission_factors_chapter7_onshore.py:31-84`),
    Tables 6-17/18 and 6-19 (`midstream.py` vs `vented_production.py`), Tables 6-47/48/49
    (`activity_factors.py:147-152` vs `vented_ccus_transport.py:228-245`), and Table 6-4 disagrees
    (0.7288/0.0565 vs 0.728/0.057). Three copies each of `_split_vent_flare` and `_propagate_results`.
39. **[M] `emission_factors.py` and the `emission_factors/` package coexist and the package re-executes the
    file. [verified by execution]** `emission_factors/__init__.py:5-16` loads `../emission_factors.py` with
    `exec_module`, so `sys.modules` never registers it and the module body runs twice: two distinct
    `API_FACTORS` dicts (181 entries each, `is` comparison False). Code importing via different paths holds
    different objects.
40. **[M] Statistics/plumbing defects.** `anomaly.py:197, 265, 333, 407` fail **open** (a DB error reads as
    "clean"); `dispatcher.py:563-565` misreads an uncertainties dict containing `"CH4"` as a GWP dict;
    `dispatcher.py:2325-2331` swallows the HHV-lookup failure; `constants.py:63-71` silently falls back to AR5;
    `inventory_uncertainty.py:130` uses the max per-record gas uncertainty; `monte_carlo_simulation` is unused
    and re-seeds the global RNG.
41. **[L] Wrong API-table citations in comments/docstrings** — `process_categories.py:152, 161, 170, 189, 198,
    207, 216, 262, 307` (e.g. "Table 6-167", which does not exist; it is Table 6-53), `emission_factors.py:276`,
    `fugitive_onshore.py:434, 443, 496, 580`, `midstream.py:37, 46, 70`. Matters for a compliance deliverable.
42. **[L] `units.CONVERSIONS["GWP_AR5"]` uses UPPER-case keys while `GWP_AR4`/`GWP_AR6` use lower**
    (`units.py:76-78`); no `bbl_to_ft3` entry although three different values are hard-coded elsewhere
    (`units.py:33-41` derived, `vented_gas.py:27` `5.61458333`, `legacy_engine.py:92` `5.61458`).

### 5.3 Production-operability
43. **[C] The app is not safe with more than one worker process.** Four pieces of state live in process memory:
    the limiter (`extensions.py:44-46` → `memory://`), the dashboard cache `TTLCache` (`dashboard.py:32`),
    the SSE notification path, and the bulk-job registry. `clear_dashboard_cache` only synchronises workers
    over Postgres via a `system_settings` epoch row (`dashboard.py:38-91`); on SQLite it returns the local epoch.
    Multi-worker requires `RATELIMIT_STORAGE_URI=redis://...` **and** a real queue for jobs.
    `docker-compose.yml`/`Dockerfile` must pin `--workers 1` or this silently breaks.
44. **[H] Bulk-upload job state and scope.** A `threading.Thread` per job (documented in `CLAUDE.md`); job state in
    a module-level dict, now with a TTL prune and an on-disk snapshot directory. Restart-safe for status, but
    concurrent large uploads still mean N threads × 50 MB in a single process, and `MAX_CONTENT_LENGTH` is 50 MB.
45. **[M] SQLite WAL checkpoints run inside the `after_commit` session hook** (`app.py:106-122`) every 100 commits.
    A synchronous `PRAGMA wal_checkpoint(PASSIVE)` on the request path is a latency spike and, under `NullPool`,
    opens yet another connection per checkpoint.
46. **[M] Schema has two authorities.** Model metadata (via the reconcile revision) plus
    `ensure_database_indexes()` raw DDL (`app.py:422-446`) plus `add_columns.py`/`schema_sync.py` helpers.
    Fresh-DB path works; `downgrade` does not actually roll back the schema.
47. **[M] Demo/dev database is not representative.** Live `ghg_app.db` holds 32 tables but only 24 emissions,
    4 facilities, 1 user, 1 custom factor; the audit baseline snapshot had 744 S1 / 37 S2 / 28 S3 rows and
    170 facilities. Performance and integration conclusions drawn from the current DB are not meaningful.

### 5.4 Deployment and security configuration (independently verified)
58. **[C] Hard-coded production `SECRET_KEY` is accepted at startup.**
    `docker-compose.yml:11,13` sets `FLASK_ENV=production` + a literal
    `SECRET_KEY=enterprise-ghg-production-secret-change-in-prod`. The production guard
    (`config.py:19-28`) blacklists only `None` and three exact strings, so this passes.
    **Verified by execution:** with those env vars set, `Config` imports cleanly and
    `IS_PRODUCTION is True`. Flask signs the session cookie with that key, so anyone who
    reads the repo can forge an `admin` session (and a matching `sv`). *Fix: require a
    ≥32-char random secret, reject any value matching `dev|change|secret|test|example`,
    and interpolate the compose secret from the environment.*
59. **[C] Postgres is published to the host with trivial credentials.**
    `docker-compose.yml:24-28` (`test:test`, port `5432:5432`). Full read/write of every
    emissions record and password hash, bypassing the application entirely.
60. **[H] The effective Docker image never contains the frontend.** The `Dockerfile` declares a
    **second** `FROM python:3.11-slim` at line 46, after the first stage's `CMD` at line 44. Only
    stage 2 is kept, it has no `COPY --from=frontend-builder`, and `new/server/static/` contains
    only `swagger.json` — so `/` serves the API JSON and the built SPA (in `new/client/dist`,
    87 assets) is discarded. The `flask db upgrade && gunicorn` invocation at line 44 is dead code.
    *Fix: keep one runtime stage and copy `dist` into `static/dist`, or serve the SPA separately.*
61. **[H] `--workers 4` with a `memory://` limiter makes every rate limit ~4× weaker.**
    `Dockerfile:44` runs 4 Gunicorn workers; `config.py:116` + `extensions.py:38-46` store counters
    in process memory. The login budget (20/15 min) becomes ~80/15 min and resets on restart.
    Tighten by using Redis storage or pinning workers to 1.
62. **[H] `it_manager` and `it` can read satellite data and write the OGMP ledger.**
    All four `/api/satellite/sentinel5p/*` guards check only `user.role == "it_admin"`
    (`routes/satellite.py:111, 134, 205, 349`), while `utils.py:31` makes all three IT roles
    zero-access for facility data. `it_manager`/`it` pass the satellite checks. Same class of gap as
    finding 1.
63. **[H] `GET /api/auth/settings` returns Copernicus credentials to any authenticated user.**
    `routes/auth.py:807-834` masks only `copernicus_password` and `copernicus_client_secret`;
    `copernicus_username` and `copernicus_client_id` are returned verbatim, and `_app_settings` holds
    the real password in process memory (plaintext in `SystemSetting`).
64. **[H] The audit "hash chain" always reports verified.** `routes/audit.py:395-431` recomputes
    SHA-256 from the live rows with a hard-coded genesis value and never compares against a stored
    hash, so `verify-chain` is structurally incapable of detecting tampering, while the hashed payload
    omits `details`, `old_values`, `new_values` and `ip_address`. Any tamper-evidence claim built on it
    (ISO 14064-3 / ISAE 3410 assurance) is unsupported.
65. **[H] No failed-login record and no lockout.** `FAILED_LOGIN` is read by the audit dashboard
    (`routes/audit.py:228, 241`) but never written anywhere, so `security_alerts` is permanently 0
    while `routes/auth.py:336-408` protects login with an IP limiter only.
66. **[H] Unbounded thread-per-upload plus a weak xlsx check.** `background_processor.py:500-516`
    spawns a raw thread per job with no cap or queue; `routes/emissions.py:2596-2607` validates an xlsx
    only by its 4-byte `PK\x03\x04` header, and `MAX_CONTENT_LENGTH` (50 MB, `config.py:109`) bounds the
    *compressed* body only.
67. **[M] CSRF is session-bound Flask-WTF, not the double-submit cookie the code claims.**
    `app.py:495-512` sets a `csrf_token` cookie and its docstring says "double-submit cookie pattern",
    but there is no `WTF_CSRF_COOKIE*`/`CSRF_HEADERS` configuration anywhere and nothing compares the
    cookie to the header. The client sends the token from the JSON body (`api.js:17, 31`). Functionally
    sound (Flask-WTF stores it in the session), but the cookie is dead weight and the docstring is wrong.
68. **[M] Production CORS list is hard-coded and cannot be narrowed.** `config.py:38-49` defaults to
    dev origins even in production and **forcibly appends** `https://kaljah.github.io` regardless of
    `ALLOWED_ORIGINS`, with `supports_credentials=True` (`app.py:37-44`).
69. **[M] `SameSite=None` in production removes the browser's CSRF barrier** (`config.py:92-95`),
    and combined with `WTF_CSRF_SSL_STRICT=False` (`config.py:103`) the token is the only control.
70. **[M] Facility scoping uses the raw user location as a `LIKE` pattern.**
    `utils.py:46-52` builds `Facility.region.ilike(user_region)` unescaped, so a location containing
    `%` or `_` broadens scope. `_escape_like` exists but only in `routes/emissions.py:36`.
71. **[M] Only 6 routes carry a per-route rate limit** (`routes/auth.py:254, 338, 413, 485, 592`,
    `routes/emissions.py:504`). Notably unlimited beyond the 200/min global default:
    `POST /api/emissions/upload/start`, `POST /api/reports/generate`, every report export, all
    `/api/satellite/*` (each call makes outbound HTTPS), `POST /api/data/production/bulk-import`,
    `GET /api/auth/users`, `PUT /api/auth/settings` (which can trigger a full-table emissions UPDATE).
72. **[M] Missing response headers:** no HSTS, `Permissions-Policy`, COOP or CORP
    (`app.py:213-223`). `style-src 'unsafe-inline'`, `img-src https:` are permissive.

### 5.5 Data model, schema governance and persistence (independently verified)
73. **[C] The SQLite→Postgres migration silently drops 7 tables.** `scripts/migrate_sqlite_to_postgres.py:15-39`
    lists 23 tables; `models.py` declares 30. Missing: `cap_emissions`, `cap_regulatory_limits`,
    `flaring_details`, `jv_partners`, `facility_equity_shares`, `component_inventories`, `fugitive_surveys`
    — i.e. all CAP/Decree 06-138 data, all flaring detail, all equity/JV data and all LDAR component data.
    **Verified by reading the list.** The same script copies explicit PKs and never advances the Postgres
    sequences, so the first insert after migration raises `UniqueViolation`.
74. **[C] Changing the GWP standard restates every Scope 1 record with no audit trail and no review.**
    `recalculate_all_emissions_gwp` (`routes/auth.py:742-805`) issues a bulk `UPDATE` over `Emission`
    including **Verified** rows, writes no `ActivityLog`/`Notification`, does not return records to `Pending`
    (violating the maker-checker contract in `services/maker_checker.py:174-191`), and leaves
    `Scope3Emission.co2e` and every `uncertainty*` column stale. The failure is swallowed into a log line
    (`routes/auth.py:924-928`). `scripts/recalculate_emissions.py:135-148` shows the correct pattern.
75. **[H] `schema_sync.add_missing_columns` never emits `NOT NULL`** (`schema_sync.py:36-45, 65-68`).
    **Verified on the live DB by `PRAGMA table_info`:** `users.session_version`, `custom_factors.is_archived`
    and `sbti_targets.scope_coverage` are `NOT NULL` in `models.py` (`:35, :350, :670`) but `notnull=0` in the
    database. Model truth is not enforced.
76. **[H] Four foreign keys declared in `models.py` never reached the database.**
    **Verified by `PRAGMA foreign_key_list`:** `cap_emissions` has only `created_by, facility_id` (missing
    `approved_by`, `updated_by`), and both `scope2_emissions` and `scope3_emissions` are missing `updated_by`.
    Dangling user ids are prevented only by the reflection code in `routes/auth.py:1118-1133`.
77. **[H] `notifications` has no index of any kind.** **Verified:** zero index rows in `sqlite_master` for the
    table, while every notification read filters `user_id` + `is_read` and orders by `created_at`
    (`routes/notifications.py:40-43, 206-215, 268`) and rows are created on every create/update
    (`utils.py:252-278`) and per maker per decision (`services/maker_checker.py:100-106`). It is the
    fastest-growing table in the schema and every read is a full scan.
78. **[H] `flask db downgrade` cannot complete, and the two schema-owning revisions downgrade to a no-op.**
    `9c3e1a7b5d20:32-34` and `a1c4e7f20b31:81-83` are both `def downgrade(): pass`, while
    `2ef6f882b02c:45` drops an unnamed FK constraint (raises on SQLite batch mode) and `2ef6f882b02c:46-47`
    drops indexes that `7fe333372c71:74-75` had already dropped. Alembic still moves `alembic_version`, so a
    failed rollback leaves a database claiming an older revision with the newer schema — after which future
    upgrades become silent no-ops.
79. **[H] Facility deletion returns 500 for any facility with LDAR data.** `ComponentInventory` and
    `FugitiveSurvey` (`models.py:276-323`) have **no relationship from `Facility`**, so the ORM cascade never
    reaches them; with `PRAGMA foreign_keys=ON` (`app.py:80`) and no `ondelete=` anywhere in the codebase
    (grep: 0 hits), `DELETE /api/facilities/<id>` (`routes/facilities.py:394-417`) raises `IntegrityError`.
80. **[H] WAL growth is not actually bounded.** `app.py:68-69` documents `wal_checkpoint(TRUNCATE)` every 500
    commits; the code sets the interval to **100** (`app.py:71`) and runs **`PASSIVE`** (`app.py:119`).
    `PASSIVE` never truncates while any reader holds a snapshot and never waits. The counter is an unlocked
    module global and per-process (2 Gunicorn workers ⇒ effective interval 200). Each checkpoint also opens a
    fresh connection via `NullPool`.
81. **[M] The live database is 79 % free pages.** **Verified:** `page_count=564`, `freelist_count=444`,
    `page_size=4096` ⇒ 1.82 MB of 2.31 MB unreclaimed, with no `VACUUM`, no `auto_vacuum` and no
    incremental vacuum anywhere in the repo.
82. **[M] No `UNIQUE` constraint on any natural key that changes reported totals** for `scope2_emissions`,
    `scope3_emissions`, `cap_emissions`, `flaring_details`, `ogmp_surveys`, `facility_equity_shares` or
    `custom_factors.name`; dedupe lives only in Python (`background_processor.py:449-456`) and equity's
    ≤100 % rule is a check-then-insert (`routes/equity_routes.py:166-184`) — a TOCTOU that double-counts
    equity emissions.
83. **[M] Five schema authorities coexist**: `models.py` metadata (executed through `9c3e1a7b5d20`'s
    `create_all`), the six patch revisions, `ensure_database_indexes()` raw DDL on every start
    (`app.py:422-446, 488`), the ad-hoc `add_columns.py` / `add_indexes.py` / `migrate_ogmp.py`, and
    `id_guard._next_id` creating `id_high_water` from a request path (`id_guard.py:23-24`).
    `tests/test_audit_rc14_schema.py:78-83` asserts "no create_all/ALTER in app.py" while
    `ensure_database_indexes` still emits 11 `CREATE INDEX` statements there.
84. **[M] `id_guard` is fragile.** It requires SQLite ≥3.35 for `UPDATE ... RETURNING` (3.45.3 here, but every
    insert on the 5 guarded tables fails on older system SQLite), issues DDL from a request path, guards only
    5 of 30 tables, full-scans `activity_log` with `GLOB` on first use, and ignores the non-numeric
    `record_id` values the maker-checker writes (`"Scope 1-43"`, `services/maker_checker.py:139`).
85. **[M] One transaction per import file** (`background_processor.py:465, 997`; 50,000-row cap) holds the
    SQLite write lock for the whole file: every other writer blocks up to `busy_timeout`=30 s and then fails
    with "database is locked", while the WAL grows by the size of the import.
86. **[M] `flaring_details.status` defaults to `"Verified"`** (`models.py:756`), so flaring rows are born
    approved without maker-checker while feeding Decree 21-330 reporting; `OgmpSurvey` and `FlaringDetail`
    are absent from `maker_checker.RECORD_TYPES` (`services/maker_checker.py:24-29`).
87. **[M] `activity_log.facility_id` is effectively unpopulated. Verified:** 54 of 56 rows are `NULL`,
    so audit-by-facility is close to blind even though the column was added for exactly that purpose
    (`models.py:368-369`, `utils.py:190-207`).
88. **[M] Dead columns that no code path writes**: `Emission.co2_biogenic`, `calc_version`, `factor_version`,
    `ef_used_co` (`models.py:139, 147, 178-179`) — the live DB is 24/24 `NULL` for the version columns, so an
    auditor reading them would conclude "not reported".
89. **[M] `_memory:` test DBs use `StaticPool` with `check_same_thread=False`** (`config.py:70-75`): one
    connection shared by every thread, letting concurrent test sessions interleave transactions.

### 5.6 Repository hygiene
90. **[H] Committed artefacts the audit already scheduled for removal are still tracked**:
    `new/server.rar`, `new/server/calculations/calculations.rar` (both are **full server source snapshots**,
    including `models.py` with password hashes), `cbam_removal.patch` (770 KB), `cbam_removal_utf8.patch`
    (386 KB), plus `cbam_diff_*.patch`. `AUDIT_MEMORY.md:139` flags this explicitly.
91. **[M] 16,804 tracked files / ~490 MB pack**, including `brain/**/.tempmediaStorage/*.pdf` session media,
    several multi-MB PDFs and `audit/work/**` drafts. `git status` is otherwise clean apart from modified
    client chart files and untracked work in progress.
92. **[M] `.env.production` is tracked while `.env` is ignored** (`.gitignore:6-9` ignores `.env`, `.env.local`,
    `.env.*.local`, `*.env` — not `.env.production`). Currently a placeholder URL, but the pattern will leak
    real configuration.
93. **[M] ~4.2 GB of untracked SQLite snapshots on disk** (`new/server/backups/ghg_app_20260920_172952.db`
    1.91 GB, `..._173146.db` 2.34 GB) plus `ghg_app.db.bak_before_scope_deletion`, `database.db`,
    `ghg_emissions.db`, `users_v2.db`, `new/instance/ghg_app.db`. Every one contains full
    `scrypt` password hashes and the complete emissions history; neither backup script prunes or rotates
    (`scripts/backup.py:11-29`, `scripts/backup.ps1:12`), and none has a tested restore path.
94. **[L] `stats.html` (1.4 MB) is regenerated by every client build** and is not ignored.

### 5.7 Test-suite and CI weaknesses (independently verified)
95. **[C] The `sqlite:///:memory:` overrides in three test modules are silently ignored.**
    `test_production_smoke.py:18`, `test_rate_limiting.py:14` and `test_security_hardening.py:20` all set
    `SQLALCHEMY_DATABASE_URI` **after** `db.init_app(app)` already ran at import
    (`app.py:47`; `extensions.py:7`). Flask-SQLAlchemy 3.1.1 builds and caches engines inside `init_app`
    (`_app_engines` set at `flask_sqlalchemy/extension.py:273-274`, populated at `:359-374`, read back at
    `:689-696`) — **verified in the installed library source.** Those modules keep using the shared
    `tests/test_app.db`, so the `StaticPool` path is never exercised and the intended isolation does not exist.
95b. **[verified] I ran the backend suite.** `python -m pytest tests/` against an isolated
    `DATABASE_URL` in the system temp directory: **1,968 passed, 3 errors, 0 failed, in 317 s.**
    The three errors are the `tests/test_audit_rc14_schema.py` cases that shell out via
    `subprocess.run([...], capture_output=True, text=True)` (`:27`) to run `flask db upgrade`: they fail
    whenever the harness forbids capturing a child process's piped output, and **pass (13/13) when that
    restriction is lifted.** So the suite is green; a fresh database genuinely bootstraps through all seven
    Alembic revisions, and importing the app yields **187 URL rules**.
    Independently: my runs used their own temp DB (the artefacts remain on disk), and the repository's
    `ghg_app.db` is held open by the developer's own running `python app.py` on :5000, which is what writes it.
95c. **[verified] A fresh database bootstraps from nothing.** Running `import app` with an empty
    `DATABASE_URL` applied `815d10c5bbe4 -> 61bacaad00dc -> 2ef6f882b02c -> 7fe333372c71 -> 52c620a620d2 ->
    9c3e1a7b5d20 -> a1c4e7f20b31` in order and logged "Database upgraded to Alembic head a1c4e7f20b31".
    This confirms finding 45's claim that `9c3e1a7b5d20` is the revision that actually creates the schema
    (`db.metadata.create_all`) and that the other six are column/index patches on top of it.
95d. **[verified] The three test environments disagree.**
    - Local (this machine): **Python 3.12.4**, `pytest 9.1.1`, `hypothesis` and `pytest-benchmark` present,
      **`pytest-timeout` absent** — so `python -m pytest tests/ --timeout=300` fails with
      *"unrecognized arguments: --timeout=300"* until it is installed by hand.
    - CI (`.github/workflows/deploy-pages.yml`): **Python 3.11**, and it installs
      `pytest pytest-timeout hypothesis` ad hoc at `:48` while `requirements.txt` lists none of them.
    - `requirements.txt` pins Flask 3.0.3 but the installed runtime reports Flask 3.0.0 / Werkzeug 3.0.3
      against the file's `Werkzeug>=3.0.6`.
    A test that passes locally therefore proves nothing about CI, and vice versa.
95e. **[verified] Python 3.12 emits deprecation warnings this codebase will eventually have to fix**:
    `sqlalchemy`'s default SQLite date adapter (deprecated as of 3.12) fires on every dashboard test, and
    `app.py:117` raises `SADeprecationWarning` for `_ConnectionFairy.connection`. Neither is fatal today.
96. **[H] The CSRF-protected mutating path is never tested end-to-end.** `tests/conftest.py:29` forces
    `WTF_CSRF_ENABLED=False` and 24 further modules repeat it. No test sends `X-CSRFToken` on a mutating
    request, so a regression that breaks token issuance passes CI.
97. **[H] The rate-limit test cannot fail.** `tests/test_api_security.py:262-276` accepts `401 or 429`
    explicitly because the limiter is disabled; `tests/test_rate_limiting.py` is the only module that
    re-enables it, and `conftest.py:42-48` disables it for every other test.
98. **[H] The `SEED_ADMIN=true` bootstrap — the path that makes a fresh deployment usable — is untested in
    its success branch.** `app.py:360-419` is only covered as a no-op (`tests/test_security_hardening.py:99`).
99. **[H] Postgres, the advertised production database, has zero tests.** Nothing exercises `config.py:83-87`,
    the non-SQLite branch of `_get_global_cache_epoch` (`routes/dashboard.py:49-64`) — the only mechanism
    that makes multi-worker cache invalidation work — or `id_guard`'s absence on PG.
100. **[H] `routes/managedata.py` (~950 LOC) and `routes/emission_factors_routes.py` have no functional
    coverage.** No test imports `managedata`; only one 401 probe touches `/api/emission-factors`
    (`tests/test_api_security.py:120`).
101. **[M] Thirteen `test_*` functions are really fixtures and assert nothing** (collected as passing tests):
    `test_audit_remediation.py:19`, `test_audit_bug_fixes.py:17`, `test_calculations_page.py:75`,
    `test_csv_engine_matrix.py:77,95`, `test_deep_injection_matrix.py:62,80`, `test_it_role_security.py:16`,
    `test_reports.py:22`, `test_stress_concurrency.py:22`, `test_tier2_api_e2e.py:29,47`,
    `test_ui_calculation_parity.py:113`. `tests/test_qfull_validation.py:422` is genuinely empty
    (`pass  # Optional robust test`).
102. **[M] `tests/test_unit_conversions_exhaustive.py:43-99` is tautological** — it multiplies and divides by
    the same `CONVERSIONS` dict entries, so no wrong factor can ever fail it. Only the hard-coded anchors at
    `:105-137` are real oracles.
103. **[M] Wide accepted-status sets make several tests unable to detect a wrong code**:
    `test_deep_dive_2026_09_30.py:197` `(200,201)`, `test_stress_boundary_resilience.py:204,235`
    `[200,201,400,413,422]`, `test_api_security.py:127` `404 or 405`.
    `test_audit_remediation.py:534` allows ±2.4 % on an exact unit conversion.
104. **[M] CI runs the same 11 gate files ~4×** and the first run's `-x` aborts before the diagnostic groups
    produce their `-v --tb=long` output (`.github/workflows/deploy-pages.yml:56-103`).
    `pip-audit ... || true` (`:108`) means the only supply-chain gate cannot fail the build.
104b. **[H] [verified] CI runs the smaller half of the test suite.** Both counts were measured on this
    machine against an isolated temp database:

    | Command | Result | Gated by CI? |
    |---|---|---|
    | `cd new/server && pytest tests/` (what CI runs, `:56`) | **1,968 passed, 3 errors, 0 failed, 317 s** | yes |
    | `pytest` at the repo root (root `pytest.ini`: `testpaths = validation new/server/tests`) | **2,099 passed, 0 failed, 281 s** | **no** |

    The 131-test difference is the whole `validation/` tree: **44 Python files, ~5,450 LOC**, comprising
    `validation/reference_model/` (18 modules - the independent oracle), plus `validation/calculation/`,
    `validation/differential/`, `validation/mutation/`, `validation/property/` and `validation/regression/`
    suites, and two golden-case JSONs (`golden_data/`, 25 KB and `golden_dataset/`, 24 KB). The only
    occurrences of the word "validation" in the workflow are a comment and a job title - CI **never
    executes `validation/`**.
    So the "GHG calculation differential validation" step (`:65-78`) picks up the reference model as a
    *dependency* of `tests/test_independent_differential.py`, while the reference model's own tests, the
    mutation and property suites, and the regression archive are un-gated and could rot silently. My root
    run shows they are green today (2,099 passing), which is worth knowing but changes nothing about the
    gate: **the independent oracle is not what blocks a merge.**
105. **[M] No coverage, backend-lint, Docker-build, migration or E2E gate exists.** The 10 Playwright specs in
    `new/client/e2e/` are never run by any workflow, and the Docker image is never built in CI - which is why
    finding 45 (discarded frontend stage) survives.
105b. **[H] [verified] The frontend lint gate is red, so CI cannot be green as written.**
    I ran `npx eslint .` from `new/client` exactly as the workflow does (`npm run lint`,
    `deploy-pages.yml:137`): **exit code 1, 9 errors and 38 warnings (47 problems).** The errors are two
    `no-undef` for `global` in `src/test-setup.js:3` plus `react-hooks` rule failures in the chart wrappers;
    the 38 warnings are `react-hooks/exhaustive-deps` across 19 files, including the exact effects that cause
    finding 133 (the missing `AbortController`). Because `build` has `needs: backend-tests` and the lint step
    precedes the build, a strict reading is that the Pages deploy has been failing or the step is being
    ignored.
105c. **[L] [verified] Bulk-upload job snapshots are accumulating in the OS temp directory.**
    `<tempdir>/ghg_upload_jobs/` holds many `*.json` files; the ones listed were from 15:41-15:49 the same day.
    The 24 h `_prune_old_jobs` (`background_processor.py:265-294`) only runs when a new job starts, so on an
    idle machine they persist until the OS clears temp.
105d. **[L] [verified] Error handling on the live server is healthy for malformed input.**
    The running dev server's `trace.log` shows a fuzz attempt being rejected cleanly and logged:
    `[Dispatcher] Calculation failed for process_type='stoichiometry': Unknown mass unit 'furlong'
    (use kg, tonne, short ton, long ton, lb or g)`, with the traceback captured server-side and the client
    receiving a 4xx. The strict unit parser and the `dispatcher.py:2269-2284` re-raise behave as documented
    (see finding 26's "dispatcher failure is not swallowed").
105e. **[H] [verified] The independent differential gate floors every tolerance at 5 %, and its own report
    misstates the tolerance it applied.** `validation/differential/test_clean_differential.py`:

    ```python
    80:  tolerance = case.get("tolerance", 0.001)          # from the golden case
    270: allowed_tol = 0.05 if calc_type in ["venting_blowdown", "blowdown"] else tolerance
    271: is_pass = abs_diff <= allowed_tol or rel_diff <= 0.05      # <-- unconditional 5 % floor
    281: "tolerance": allowed_tol,
    282: "status": "PASS" if is_pass else "FAIL",
    287: assert is_pass, ...
    ```

    `rel_diff <= 0.05` is an **OR** that is not conditional on the case, so no case can fail while its
    relative difference is under 5 %, whatever tolerance the golden data declares. The `tolerance` written
    into the report is `allowed_tol`, and for non-blowdown cases that is the case's own value - frequently
    `0.001`. The published artefact therefore shows `"tolerance": 0.001, "status": "PASS"` while enforcing
    0.05: a reader of `validation/reports/differential_report.json` is told a 0.1 % bar was met when the bar
    was 5 %.
    **This is not hypothetical.** Regenerating the report on the current tree produced real divergences that
    still passed, e.g.:

    | Case | production | reference | rel diff | reported tolerance | status |
    |---|---|---|---|---|---|
    | `GOLDEN-S1-COMB-003` (Tier-3 gas-composition carbon balance) | 45.303331 | 45.373687 | **0.1551 %** | 0.001 | PASS |
    | `GOLDEN-S1-FLARE-001` (dual-efficiency flare) | 98.994830 | 99.153096 | **0.1596 %** | 0.001 | PASS |

    So the production engine and the independent reference model disagree by ~0.16 % on the two most
    calculation-heavy Tier-3 pathways, and the gate reports that as a clean pass. Given finding 108 (the
    engine was never formula-audited) and 109 (the golden data may be circular), this is the strongest
    available signal that a real, small, systematic divergence exists in Tier-3 combustion and flare
    stoichiometry. **Recommendation: make the OR conditional on a per-case allowance and re-run; the two
    cases above should be investigated by hand before anything else in this document is fixed.**
    Note also that this test **writes `validation/reports/differential_report.json` as a side effect of
    running** (`:68`), so `pytest` at the repo root mutates a tracked file.
106. **[M] `tests/conftest.py:5-9` uses `os.environ.setdefault` for `DATABASE_URL`/`SECRET_KEY`**, so an
    exported value silently redirects the entire suite — including at a real database. (This is also what let
    me run the suite safely against a temp DB simply by exporting `DATABASE_URL` first.)
107. **[M] The golden-dataset gate can pass while asserting nothing**: `tests/test_golden_dataset_validation.py`
    guards its per-gas assertions behind `if key in expected and key in res`.

### 5.8 Other verification gaps
108. **[H] The calculation engine was never formula-audited.** `AUDIT_SCOPE.md:104-107`: workstream A
    (calculation engine) "was stopped by usage limits and then placed out of scope"; the per-calculation
    inventory appendix is "**not completed**". BUG-100...BUG-104 were appended by an external process and are
    explicitly "**not verified by this audit**" (`AUDIT_SCOPE.md:116`).
109. **[H] The golden dataset may be circular.** `docs/validation/HUMAN_REVIEW_REQUIRED.md:170-182` (HR-10) states
    the 25 golden cases have no documented cross-reference to published worked examples and asks for external
    validation; until then they validate the calculator against itself. (The independent differential oracle in
    `validation/reference_model/` and `tests/test_independent_differential.py` is genuinely separate and is the
    strongest non-circular check in the repo.)
110. **[M] `pytest-timeout` and `hypothesis` are used by CI but absent from `requirements.txt`** (`CLAUDE.md`,
    `new/server/requirements.txt`). CI installs them ad hoc (`deploy-pages.yml:48`); a local
    `python -m pytest` from `new/server` also fails on `test_performance.py` (needs `pytest-benchmark`).
111. **[M] ~25 production scripts sit in the server root** (`generate_*.py`, `seed_berkine*.py`,
    `restore_full_data.py`, `fix_dashboard.py`, `patch_bg.py`, `test_emission_calculations.py`, ...).
    `new/server/pytest.ini` collects `testpaths = tests .`, so every root-level `test_*.py` is part of the suite.
112. **[H] The two "Master Report" PDFs are hard-coded documents wearing a dynamic API.**
    `routes/reports.py:503` states "the master reports are generated per request from the current database",
    but `generate_berkine_master_report.py` and `generate_elm_master_report.py` contain **no database access at
    all** — every chart series, KPI, table and claim is a literal (e.g. `generate_berkine_master_report.py:122-123`
    production `[5088.03, 5497.26, ...]`, `:568-574` "1,908,885 tCO2e / -15.9% vs Baseline", `:677-680` narrative).
    The numbers simply cannot change with the data. Both modules also write to an absolute developer path
    (`.py:1359` and `generate_elm_master_report.py:708`, `c:/Users/samsung/Desktop/H2/...`) if run as `__main__`.
113. **[L] The unauthenticated template endpoints** `GET /api/emissions/template/csv` and `/template/excel`
    (`routes/emissions.py:1025, 1856`) are the only routes in the app missing `@login_required` besides
    `/me` (which handles it) and `/logout` (finding 3). They disclose the full field/process/unit taxonomy.

---

### 5.9 SPA (`new/client`) - highest-impact findings
- **[C] The client factor catalogue and the server catalogue disagree, so selectable factors hard-fail.**
  `src/utils/EmissionFactors.js` has 80 coded entries against 120 unique server codes: **23 client factor
  names have no server entry** (Acetylene, Butane, CNG, LNG, Isobutane, Naphtha, Lubricants, Tires, Waste Oil,
  Propylene, 4 completion variants, 4 liquids-unloading variants, ...) and 7 codes carry different names. The
  dropdown value *is* the client name and is submitted as `fuel`/`fuel_type` (`Scope1Form.jsx:258-262,
  1482-1483`); the server resolves by exact/normalized/alias match and otherwise raises `MissingFactorError`
  (`legacy_engine.py:590-595`). Of the 59 shared codes, **0 values differ** - so the drift is purely
  identifier-level. *Fix: generate the client list from the server catalog.*
- **[C] `Scope3Form.jsx:230` computes `co2e = amount * ef / 1000` in the browser and never sends
  `factor_unit` (`:232-244`)**, so the server can only assume a kilogram numerator
  (`units.py:558` `_SCOPE3_MASS_TONNES[""] = 0.001`; `routes/scope3.py:134-137`). A `t/unit` factor is
  therefore overstated 1000x, and the server's bare-`ton` ambiguity guard (`units.py:614-616`) is
  unreachable. For admin/superuser the server also trusts a client-supplied `co2e` outright when
  activity/EF is 0 (`scope3.py:138-140`).
- **[C] `new/client/storageState.json:5` holds a live Flask session cookie for `user_id: 1`** in the working
  tree. It is currently untracked and excluded only by `**/storageState.json` in `.gitignore:114` - one
  `git add -A` from being committed. Rotate and delete it.
- **[H] `Scope1Form.jsx:1538` divides combustion efficiency by 100 unconditionally**, while the server's
  `normalize_efficiency` (`units.py:520-538`) accepts either `"%"` or a fraction, so a fraction entry (0.98)
  becomes 0.0098 - a 100x understatement.
- **[H] `ManageData.jsx:4089` annualises with a flat `(rate * 8760) / 1000`** while the server is leap-aware
  and prorates to the record's month (`units.py:718-741, 818-819`).
- **[H] `ModernReportGenerator.js:84` caps the client dataset at `limit: 5000`** and only `console.warn`s
  (`:221-226`), so a compliance PDF silently omits records beyond 5,000 (the server-side `/reports/export`
  is complete).
- **[H] No `AbortController` or request-sequence guard exists anywhere in `src`** (grep: 0 hits), so the
  unbounded filter effects in 8 pages (`Scope1Form.jsx:165-167`, `DashboardEnhanced.jsx:179-192`,
  `CarbonIntensity.jsx:126-149`, `MethaneIntensity.jsx:160,173`, `UncertaintyAssessment.jsx:61,88`,
  `Reports.jsx:112,159`, `SbtiDashboard.jsx:94`, `MethaneExplorer.jsx:209`) let a stale response overwrite a
  fresh one. `Scope1Form.jsx:2865-2875` also searches **undebounced** - one request per keystroke.
  Note: `new/client/tests/test_ui_stress_fuzzing_mutations.mjs:79-136` tests a mock fetcher class and an
  `AbortController` pattern that exist nowhere in `src`, so it provides false assurance about exactly this
  defect - and no npm script runs it anyway.
- **[H] Accessibility on the primary flows**: the Emissions page scope cards are click-only divs
  (`Emissions.jsx:54-57, 110-113, 166-169`) with no role/tabIndex/keyboard, toasts carry no
  `role`/`aria-live` (`Toast.jsx:86, 160`), five hand-rolled modals bypass the accessible `Modal`/`Drawer`
  (no `role="dialog"`, `aria-modal`, Escape or focus trap), all 249 `<th>` lack `scope`, and there are **0**
  `aria-invalid`/`aria-describedby` — validation errors are toast-only. `src/utils/a11yLabels.js` patches
  labels at runtime with a `MutationObserver`, which hides the underlying gap.
- **[H] `src/hooks/useGwpStandard.js:14` caches the GWP standard in a module variable that is never
  invalidated** after `Settings.jsx:195` saves a new one, so every tooltip/label keeps the old standard until
  a full reload. `ModernReportGenerator.js:1601-1614` additionally hard-codes an AR5 fallback
  (1/28/265), which is wrong whenever the active standard is AR4 or AR6.
- **[M] The lint gate is broken and self-blinding**: `npm run lint` runs `eslint .` and exits **1 with 47
  problems** (38 `react-hooks/exhaustive-deps` in 19 files, 3 `set-state-in-effect`, 3 static-components,
  2 `no-undef`, 1 unused). `eslint.config.js:27` sets
  `no-unused-vars: ['error', { varsIgnorePattern: '^([A-Z_]|motion$)' }]`, which exempts **every
  PascalCase identifier** and therefore hides all dead component imports.
- **[M] Dead weight in the client tree**: ~2,300 lines of never-imported components
  (`BulkImportModal.jsx` 1,785 lines, `CsvUploader.jsx`, `EmissionFactorOption.jsx`, `FormField.jsx`,
  `hooks/useFormDraft.js`) plus 690 lines of CSS; `AdminRoute` (`App.jsx:52-58`) is defined and never used;
  `pages/Diagnostics.jsx` is a 10-line stub that is never routed; there is no `path="*"` catch-all; and five
  tracked Python patch scripts live **inside `src/`** (`src/fix_wizards.py`, `src/patch_app.py`,
  `src/components/patch_s3.py`, `patch_s3_form.py`, `src/components/layout/patch_sidebar.py`) alongside a
  tracked 1.4 MB `stats.html`.
- **[M] Duplicated implementations**: approve/reject exists twice (`ManageData.jsx:408-543` vs
  `BatchReviewWizard.jsx:323-461`), upload polling exists **three** times
  (`BulkImportModal.jsx:807`, `UploadProgress.jsx:135`, `ColumnMappingWizard.jsx` step 4), and the PDF export
  flow is duplicated (`DashboardEnhanced.jsx:854` vs `Reports.jsx:428`).
- **[M] Client-only arithmetic with no server counterpart**: unsourced FX rates and business-day periods
  (`Scope3Form.jsx:88-89`: EUR 1.1, DZD 0.0074, week 5 / month 20 / year 240); methane-loss-rate thresholds and
  compliance classification (`MethaneIntensity.jsx:252-281`); browser-side re-aggregation of
  `/dashboard/intensity-stats` (`CarbonIntensity.jsx:251-256`); a carbon-balance engine in
  `GasCompositionCalculator.jsx:85-193` whose output is **persisted as custom factors** (`:245-254`) and which
  ignores the server's percent-vs-fraction detection and >100.5 % rejection (`units.py:862-895`).
  Its `:326` labels a value of 23.685 as "Molar Volume (L/mol)" when it is m3/kg-mol (`units.py:19`).
- **[M] `emissionFactorsAPI.js:298` silently returns the input for an unconvertible pair** where the server
  raises (`units.py:502`).
- **[L] Unused declared dependencies**: `chart.js` (a second chart library, only `recharts` is used),
  `@radix-ui/react-label`, `@radix-ui/react-slot`, `class-variance-authority`, `clsx`, `formik`,
  `tailwind-merge`, `yup`, plus `tailwindcss`/`postcss`/`autoprefixer` with no config. Separately
  `redux`/`react-redux`/`redux-thunk` sit in `node_modules` but are **not** in `package.json`.
- **[L] `playwright.config.js:5-9` hard-codes a machine-specific Chromium path**, the baseURL is a literal
  `127.0.0.1:5173`, `generate_storage_state.js:31-32` and several specs use admin credentials `a`/`a`, and
  `e2e/ghg-workflow.spec.js:6-19` wraps its assertions in `if (response.ok())`, so it passes vacuously when
  the backend is down.
- Tools available here could not run `vitest` (the sandbox blocks `child_process.spawn`, `spawn EPERM`), so
  the client test suite was not executed during this analysis.

## 6. Documented-but-unresolved design questions (inherited, still open)

From `audit/SUSPECTED_AND_QUESTIONS.md` and `docs/validation/HUMAN_REVIEW_REQUIRED.md`:

- **Scope 2 has no market-based method** — no contractual instruments, supplier/residual-mix factors or
  market/location flag; GHG Protocol Scope 2 Guidance requires dual reporting.
- **No edit UI for emission records** although `PUT /api/emissions/<id>` exists.
- **SBTi base-year recalculation does not flow into the SBTi target** — `BaseYear` singleton and the target's
  `base_year` are unlinked sources of truth.
- **Region-restricted superusers can POST `/api/manage/sbti` and `/api/goals`**, overwriting the single
  corporate-wide target.
- **Custom-factor governance**: any numeric value is accepted with no published-range plausibility check and no
  approval workflow (HR-06); referenced factors are archived rather than deleted.
- **GWP uncertainty is not propagated into CO2e uncertainty** (HR-05).
- **No backup/restore procedure or test for the SQLite database** (HR-08, marked CRITICAL/blocking).
- **Regulatory alignment undecided** — which jurisdiction's accepted methodology governs (HR-09).
- **N2O flaring default factor disagrees between two code paths** (HR-01).
- **`co2_biogenic` is never set** (column retained, always 0; biomass fuels removed instead).

---

## 7. Invariants to respect when touching this code

1. Emission quantities are stored in **tonnes**; uncertainty columns are **fractions** (0.05 = 5 %).
2. Record status is exactly `Draft | Pending | Verified | Rejected`; only `Verified` is aggregated by dashboards.
   Admin manual entries are auto-`Verified`; bulk is always `Pending`; bulk and physical-input edits reset to `Pending`.
3. `log_activity_and_notify(...)` **adds to the session and never commits** — the calling route commits once,
   atomically with the data change. `Notification.create(...)` follows the same rule.
4. `get_allowed_facility_ids` contract: `None` = unrestricted, `[]` = nothing, list = explicit ids. `or [-1]`
   is the idiom used to make an empty list mean "no rows".
5. Migrations are never the schema author — `models.py` is; a new column needs a small idempotent revision.
6. Both `new/server/calculations/constants.py` **and** `new/client/src/constants.js` carry the GWP table; they must
   stay byte-identical in value.
7. Factor resolution must go through `units.parse_factor_unit` / `factor_to_kg_per_activity`; an unknown unit
   must raise, never pass through 1:1.
8. An activity amount > 0 that resolves to zero emissions with a default/custom factor is an **error**
   (`MissingFactorError`), not a zero-valued record. Tier 3 (`specific`) is exempt.
9. `AUDIT_MEMORY.md` must be read before fixing an audit item and updated after. `AUDIT_FINDINGS.md` is
   append-only discovery and is not a status list.

---

## 8. Corrections to existing documentation

- `AUDIT_MEMORY.md:19` still says "20-yr AR5 CH4 82.5, N2O 268". The code fixed this (BUG-013):
  current truth is `calculations/constants.py:13` → **CH4_20 = 84.0, N2O_20 = 264.0**, mirrored in
  `new/client/src/constants.js:14-15`.
- `AUDIT_MEMORY.md:20` still says `density_ch4 0.6785` / `density_co2 1.861`. Corrected 2026-10-01:
  current truth is `units.py:66-71` → **0.67722 / 1.85814 kg/m³** at 60 °F / 14.696 psia (23.685 m³/kg-mole),
  mirrored in `new/client/src/constants.js:76`.
- `AUDIT_MEMORY.md:16` places `it_admin` in the unrestricted group; the code denies IT roles entirely
  (`utils.py:31-32`). The "roles `user` < `superuser` < `admin` < `it_admin`" ordering is also wrong —
  the code's own rank map is `user:0, it:1, superuser:2, admin:3, it_admin/it_manager:4`
  (`routes/auth.py:273`), and `it_admin` has *less* data access than `admin`.
- `AUDIT_MEMORY.md:23, 36-139` claims (C1-C5, H1-H9, S1-S7, B1-B15, L1-L13, T1-T6) are "FIXED"; the
  spot checks in §4 confirm the ones tested. Treat the rest as claimed-not-independently-verified.
- `AUDIT_MEMORY.md:138` reports "1071 passed" and later entries up to "1,965 / 0 failed"; the repo now has
  **100** test files, not the 55 named in `AUDIT_SCOPE.md:36`. Test counts in the memory are historical.

---

## 9. Open questions for the owner

1. Is the intended deployment **single-process** (SQLite + memory limiter) or multi-worker (Postgres + Redis)?
   The answer changes the severity of §5.3 items 13-15 from "must configure" to "must re-architect".
2. Which formula pathways are authoritative — the Compendium-2021 dispatcher or the legacy factor engine?
   Several calculations exist in both, with different defaults (§5.2 item 7-8).
3. Is the `auditor` role meant to exist (§5.1 item 4)? If yes it needs to be in `VALID_ROLES` and the UI.
4. Is Scope 2 market-based reporting in scope? It is a GHG Protocol requirement and is entirely absent.
5. Which jurisdiction's reporting standard governs? `docs/validation/HUMAN_REVIEW_REQUIRED.md` HR-09 marks this
   blocking for production certification.
6. Is the client-side arithmetic (`utils/EmissionFactors.js`, forms, `ModernReportGenerator.js`) meant to be
   authoritative or display-only? It independently duplicates server catalogs.

---

## 10. Pointers

| Purpose | Path |
|---|---|
| App entry / middleware | `new/server/app.py` |
| Config / env contract | `new/server/config.py`, `new/server/.env.example` |
| Schema (single source of truth) | `new/server/models.py` |
| Auth, RBAC decorators, settings, GWP recalculation | `new/server/routes/auth.py` |
| Facility scoping helpers | `new/server/utils.py` |
| Calculation entry point | `new/server/calculations/legacy_engine.py` |
| Process routing table | `new/server/calculations/dispatcher.py` |
| Units / factor-unit parser | `new/server/calculations/units.py` |
| GWP sets | `new/server/calculations/constants.py` |
| Maker-checker state machine | `new/server/services/maker_checker.py` |
| Bulk ingestion | `new/server/background_processor.py` |
| Cache + scoping pattern | `new/server/routes/dashboard.py` |
| Client API + CSRF | `new/client/src/api.js` |
| Client constants to keep in sync | `new/client/src/constants.js` |
| Living audit log (read before fixing) | `AUDIT_MEMORY.md` |
| Append-only defect ledger (001-115) | `AUDIT_FINDINGS.md` |
| Audit scope + known gaps | `AUDIT_SCOPE.md` |
| Unresolved questions | `audit/SUSPECTED_AND_QUESTIONS.md` |
| Human-review items | `docs/validation/HUMAN_REVIEW_REQUIRED.md` |
| Security deep-read write-up | `audit/SECURITY_REVIEW_GHG_AUTH_CSRF_INJECTION.md` |
| This analysis (memory) | `ANALYSIS_MEMORY.md` |

---

## 11. Analysis provenance

Produced 2026-10-02 in one read-only pass over the working tree at commit `aaf31c70` (branch `main`) by a
lead agent plus six parallel subsystem deep-reads (calculation engine; Flask API surface and authorization;
data model, schema and persistence; SPA; test suite, CI and deployment; security and data protection).

Method: full reads of the core files by the lead agent, exhaustive reads by the sub-reads, and targeted
re-execution or live-database inspection to confirm the highest-severity claims - among them the production
`SECRET_KEY` guard accepting the compose value, the legacy unit converter's 8,760,000x result, the
`emission_factors` double module object, the ignored `sqlite:///:memory:` overrides (checked against the
installed Flask-SQLAlchemy source), the live SQLite schema's nullability / missing FKs / missing indexes /
free pages, the PostgreSQL migration table list, and the client factor-name set.

**The only files created by this analysis are `ANALYSIS_MEMORY.md` and
`audit/SECURITY_REVIEW_GHG_AUTH_CSRF_INJECTION.md`. No application source, test, configuration, database or
migration file was created, modified or deleted, and no server was started.**
