# Implementation Plan — Path to A+ across every layer

**Baseline:** commit `aaf31c70` (branch `main`), 2026-10-02.
**Source of truth for findings:** `ANALYSIS_MEMORY.md` (89 findings, each with `file:line`).
**Assumed decisions (state them back if wrong):**
1. **Docker is removed entirely** and is not a grading category. No `Dockerfile`, no `docker-compose.yml`, no container assumptions anywhere in the plan.
2. The deployment target is therefore a **single supervised process** on a host (systemd / NSSM / a managed Python service), serving Flask behind a TLS-terminating reverse proxy, with a built SPA served either by that same process or as static files.
3. **Single-process is a deliberate architectural choice, not a temporary state.** This is what makes the operational layer A+ cheaply. If multi-worker is ever required, Phase 7 has the escape hatch — but do not half-adopt it.

---

## 0. Grading rubric — what "A+" means here, concretely

Grades are only useful if they are measurable. These are the exit criteria. Each is machine-checkable so it cannot drift.

| Layer | A+ means | Gate that enforces it |
|---|---|---|
| **Verification** | Every calculation pathway has at least one oracle that is independent of the code under test and traceable to a published source; no assertion can be satisfied by a tautology; a wrong result fails the build | `scripts/quality_gates.py` (new) runs in CI: fails on missing oracle, on tolerance > per-case allowance, on any `assert` inside a conditional, on a vacuous status-code set |
| **Correctness** | Production output matches the independent reference model within each case's declared tolerance; no pathway depends on an unknown unit or an invented default without recording it | Calc-differential CI job + a "no silent default" audit test |
| **Operability** | One process, restart-safe, with a **tested** restore, and no unbounded growth | `scripts/verify_restore.py` in CI against a seeded DB; readiness probe that fails when WAL/disk thresholds are exceeded |
| **Security** | No committed secret, no account-takeover path, every mutating route CSRF-checked and rate-limited | `test_security_gates.py` asserting rate limits and CSRF per route; `pip-audit` with no `\|\| true` |
| **Hygiene** | Docs match code; the defect ledger has real status; no binaries or secrets in git | `scripts/check_docs.py` (asserts `AUDIT_FINDINGS.md` has no `Confirmed` entry whose fix is in the log) + a repo-size budget check |

**Anti-goal, stated up front:** do not add calculation capability this quarter. There are ~3,000 lines of calculator code no production path can reach. Adding more widens the unaudited surface. Freeze features (P0–P6); unfreeze after P7.

---

## PHASE P0 — Stop the bleeding (day 1, ~4 hours)

These are one-line-to-one-screen fixes that remove live risk. Do all of them before anything else.

| # | Action | File | Why now |
|---|---|---|---|
| 0.1 | Rotate `SECRET_KEY`; move it out of compose into the host env; and **extend the production guard's denylist** to reject any value matching `dev\|change\|secret\|test\|example\|password` or shorter than 32 chars | `config.py:21-28` | I verified by execution that the current guard accepts a literal from the repo → forgeable admin session |
| 0.2 | Delete `docker-compose.yml`; strip Docker references from `README.md`, `CLAUDE.md`, `AUDIT_MEMORY.md` | repo root | Removes the published-Postgres `test:test` exposure and the hard-coded key in one move |
| 0.3 | Add `storageState.json` and `.env.production` to `.gitignore`; **delete `new/client/storageState.json`** and rotate the session it contains | `.gitignore` | Live admin session cookie sitting in the working tree |
| 0.4 | Change `@it_access_required` → `@it_admin_required` on the password-reset route, **and decide the `it`-can-reset-admin question explicitly** (the test suite currently asserts the permissive behaviour, so update `test_it_role_security.py:84` in the same commit) | `routes/auth.py:1152-1153` | Lowest IT tier can take over `admin` |
| 0.5 | Extend the register guard to `role_requested in ("admin", "superuser")` | `routes/auth.py:281-282` | IT admin can currently mint a `superuser` |
| 0.6 | Add `@login_required` to both template downloads | `routes/emissions.py:1025, 1856` | Anonymous ~90 KB xlsx generation per request |
| 0.7 | Delete the duplicate `/api/audit/stats` route (keep the `audit_bp` one) | `routes/managedata.py:976-982` | Duplicate registration; protection currently accidental |
| 0.8 | Add `@login_required` + CSRF to `/auth/logout` | `routes/auth.py:484-486` | Cross-site logout forces a re-login on every device |
| 0.9 | Wrap every raw `int()`/`float()` on user input with `input_validation.parse_number`/`parse_year` — **start with the two that skip authorization** (`scope2.py:308`, `scope3.py:118`), then the 20-odd others listed in `ANALYSIS_MEMORY.md` finding 10 | routes/* | A non-numeric `facility_id` currently 500s *inside* the scope test |
| 0.10 | Give `it` accounts a reduced projection on `GET /auth/users` (or drop `it` from that route) | `routes/auth.py:984-985` | Full directory (emails, roles, locations) to the lowest IT rung |

**P0 verification:** the 1,968-test suite still passes; a new `tests/test_security_gates.py` proves 0.4–0.8 by asserting 403/400 for the formerly-permitted calls.

---

## PHASE P1 — Resolve the numeric divergence (days 2-3, blocking)

**This is the only finding in the review that says the numbers may be wrong, so it goes first among the real work.**

### 1.1 Fix the gate that hid it
`validation/differential/test_clean_differential.py:271`:
```python
is_pass = abs_diff <= allowed_tol or rel_diff <= 0.05   # unconditional OR
```
Replace with a per-case allowance that is explicit in the golden data — e.g. `case["tolerance"]` for tight cases and a named `case["engineering_tolerance"]` where a model genuinely cannot match (blowdown inventory vs delta-P). Then:
- `"tolerance"` written into the report must be **the value actually enforced** (today it writes `allowed_tol`, which for most cases is `0.001`, while enforcing `0.05` — the report misstates its own bar).
- Add a meta-test asserting that no `assert` in the differential/validation suites sits behind a short-circuit that makes it unreachable.

### 1.2 Investigate the two reproduced divergences
| Case | production | reference | rel diff |
|---|---|---|---|
| `GOLDEN-S1-COMB-003` Tier-3 gas-composition carbon balance | 45.303331 | 45.373687 | 0.1551% |
| `GOLDEN-S1-FLARE-001` dual-efficiency flare | 98.994830 | 99.153096 | 0.1596% |

Both are ~0.16% **low**. A same-sign, same-magnitude error in two pathways that share the stoichiometric carbon-balance code strongly suggests one shared root cause — most likely a molecular-weight or molar-volume constant, or a C2+ handling difference. Work it as: `calculations/stoichiometry.py` + `calculations/combustion.py` flare path vs `validation/reference_model/{ref_combustion,ref_flaring,combustion_flaring}.py`, diffing every constant and intermediate. Expected outcome is a one-line fix plus a new golden case pinning it.
**Do not "adjust the reference to match"** — that converts a real bug into permanent tolerance.

### 1.3 Make the artefact read-only
The test writes `validation/reports/differential_report.json` (`:68`) as a side effect, so `pytest` mutates a tracked file. Write to a temp dir and have CI publish it as an artifact instead.

**P1 exit criteria:** the two cases match to ≤0.01%; the report's `tolerance` field equals the enforced value; running `pytest` leaves the working tree clean.

---

## PHASE P2 — Make verification real (week 1-2) — *the highest-leverage phase*

Everything else can be regraded after this. Fixing defects without fixing the gates means re-finding them.

### 2.1 One quality-gate script, wired into CI
New `scripts/quality_gates.py` + a CI job that fails on any of:
- **Tautology detector:** an `assert` whose both sides derive from the same production symbol (catches `test_unit_conversions_exhaustive.py:43-99`, which multiplies and divides by the same `CONVERSIONS` dict).
- **Conditional-assert detector:** an `assert` inside an `if` guarded by a response-shape check (catches `test_golden_dataset_validation.py`'s `if key in expected and key in res` and `test_api_security.py:233`).
- **Vacuous status-set detector:** any `assert ... status_code in [...]` / `in (200, 201, ...)` with more than one accepted code (catches `test_api_security.py:262` accepting `401 or 429`, `test_stress_boundary_resilience.py:204,235`, `test_deep_dive_2026_09_30.py:197`).
- **Empty-test detector:** a collected `test_*` with no `assert` and no call that raises (catches the 13 fixture-shaped functions and `test_qfull_validation.py:422`).
- **Oracle-completeness check:** every module under `calculations/` must be named by at least one test that compares against `validation/reference_model/` or a literal from a cited exhibit.

Estimated finding count on first run: ~40. **Do not fix them by loosening the detector.**

### 2.2 Make CI run the whole suite
- Change the backend job to `python -m pytest tests/` **and** the root config, so the 131 `validation/` tests (44 files, ~5,450 LOC) actually gate the build. Today the independent reference model is a *dependency* of a CI test while its own tests are un-gated.
- Remove the 4× duplication of the same 11 gate files (`deploy-pages.yml:56-103`) — use `-m` markers for the calculation/security/smoke groups instead of re-running `tests/`.
- **Add the missing dependency manifest.** Create `new/server/requirements-dev.txt` with `pytest`, `pytest-timeout`, `hypothesis`, `pytest-benchmark`, `locust`; pin them. Today local is Python 3.12.4 / pytest 9.1.1 with no `pytest-timeout` (so `--timeout=300` errors out), CI is Python 3.11 installing three packages ad hoc, and `requirements.txt` pins Flask 3.0.3 while the installed runtime reports 3.0.0.
- **Pin the CI Python to the same version the host runs**, and add a `python -V` echo so drift is visible.
- Drop `|| true` from `pip-audit` (`deploy-pages.yml:108`) — the only supply-chain gate currently cannot fail.

### 2.3 Close the untested-bootstrap hole
`app.py:360-419` (`SEED_ADMIN=true`) is the path that makes a fresh deployment usable and is only tested in its *disabled* branch. Add a test that seeds from `ADMIN_EMAIL`/`ADMIN_PASSWORD`, asserts the account can log in, and asserts a second run does **not** overwrite the password.

### 2.4 Test CSRF, rate limiting and the hash chain honestly
- One module with `WTF_CSRF_ENABLED=True` asserting 400 without `X-CSRFToken` and 2xx with it (24 modules force it off today).
- One module that re-enables the limiter and asserts a real 429 with `Retry-After`.
- **The audit "hash chain"** (`routes/audit.py:395-431`) recomputes SHA-256 from live rows with a hard-coded genesis and never compares to a stored hash — it structurally cannot detect tampering while returning `is_tamper_evident: true`. Either store the chain (a `prev_hash` column per `ActivityLog` row, verified on read) or **delete the claim**. This is an assurance statement; a false one is worse than none.

### P2 exit criteria
Quality-gate script green; CI green on Python pinned to the host version; suite count reported in the build log; the hash-chain endpoint either verifies against stored state or no longer claims to.

---

## PHASE P3 — Correctness sweep (weeks 2-4)

Now that the gates are trustworthy, fix the real defects. Order by blast radius.

### 3.1 Delete the unsound unit converter (biggest single risk)
`GHGCalculator.convert_factor_to_kg` (`legacy_engine.py:111-159`) mixes volume, mass and time in one table and applies it as `f/a`. Reproduced: `convert_factor_to_kg(1.0, "tonne CH4/yr", "m3")` → **8,760,000.0** (should be ~0.001 kg/m³). It is live on the Tier-3 specific-factor path.
**Action:** route that path through `combustion.convert_factor_to_kg_per_unit` (the strict, already-correct implementation) and delete the legacy function. Replace both bare `except:` blocks (`legacy_engine.py:404, 418`) with explicit exceptions that re-raise.

### 3.2 Fix the percent/fraction inconsistencies
Three modules disagree about whether a composition input is a percentage or a fraction:
- `vented_gas.py:42-44` divides by 100 unconditionally → a user entering `0.85` gets 0.85% (100× low).
- `activity_factors.py:221-226` reads `ch4_content=0.85` as 85% but `co2_content=0.85` as 0.85% (CO2 100× low).
- `midstream.py:191-192` accepts fractions correctly.
**Action:** one shared helper (the `units.composition_fractions` decision logic already exists at `units.py:862-895` — reuse it) applied everywhere, plus a test per call site.

### 3.3 Complete the uncertainty taxonomy
24 of the 38 `category=` strings the calculators pass are absent from `uncertainty.PROCESS_CATEGORY`, and 33 from `DEFAULT_EF_UNCERTAINTY`, so they silently collapse to `"combustion"` and lose the ±20% fugitive / ±15% vented activity terms. `fugitive_onshore.py:467, 549, 607, 647` also pass the string `"Tier 3"` instead of the enum, yielding ±10% instead of ±2%.
**This makes the Uncertainty and QA dashboards wrong for most pathways** — a headline feature. Add the missing keys and a test asserting every calculator's category resolves to a non-default entry.

### 3.4 Stop the silent unit/default fallbacks
`dispatcher.py:1566-1567` (unknown tank unit read as bbl), `:690` (missing unit → m3), `vented.py:733-734, 2186-2187, 2462`, `legacy_engine.py:156-159`. Rule to adopt: **an unknown unit raises; a genuine default is recorded on the record** (`calc_method` / `source_payload`) so a reviewer can see that an assumption was made.

### 3.5 Remove the invented defaults from live paths
85% CH4 (`dispatcher.py:1993, 2170`; `vented.py:654, 2469`; `midstream.py:76, 238`), the 70%/10% associated-gas split (`vented.py:2366-2367`), desiccant 3.0 scf/gal (`midstream.py:254-257`), `has_flash_tank=True` (`dispatcher.py:2188`), the hard-coded `"Algeria"` country (`services/intensity.py:239, 265`). Either require the input or persist the assumption.

### 3.6 Fix the AGR zero-throughput booking
`midstream.py:1086, 1100-1106` + `dispatcher.py:2015-2025`: `unit_count` defaults to 1, so a zero-gas record books ~236.6 t CH4. Raise on `throughput <= 0`.

### 3.7 Fix the factor-table divergences
- `emission_factors.py:377-427` **shadows** the canonical `CORRELATION_EQUATIONS` imported at `:27`. I verified at runtime that the legacy table wins (flange `pegged_100k` 0.089 vs canonical 0.084, and no `default_zero`). Delete the legacy block.
- `emission_factors.py` and the `emission_factors/` package coexist; the package re-executes the file via `importlib` (`__init__.py:5-16`), producing two distinct `API_FACTORS` objects (verified). Make one the single source.
- Table 6-4 disagrees between `vented_exploration.py:111,117` and `activity_factors.py:34-35`.

### 3.8 Decide the fate of the ~3,000 unreachable calculator lines
`vented_midstream.py`, `vented_lng_distribution.py`, `vented_ccus_transport.py`, `vented_exploration.py`, most of `vented_downstream.py` and seven classes in `vented_production.py` have compendium tests but **no production caller**; those tests pass and prove nothing about the app. Either register them (with the fixes from 3.2-3.5 applied) or move them to `calculations/_unreleased/` so the test suite stops implying coverage. Do not leave them in the ambiguous middle.

### P3 exit criteria
Every pathway in `AUDIT_SCOPE.md` §3 either has a live caller and passing strict differential coverage, or is explicitly parked. No calculator resolves an unknown unit to 1. No invented default is applied without being recorded.

---

## PHASE P4 — The SPA (weeks 2-4, parallel with P3)

### 4.1 Kill the factor-catalogue drift (highest user impact)
23 client factor names have no server entry and 7 carry different names, so those dropdown entries **hard-fail on submit** with `MissingFactorError`. Of the 59 shared codes, 0 values differ — the drift is purely identifier-level.
**Action:** generate `client/src/utils/EmissionFactors.js` from the server catalogue at build time (a small script + a CI check that regenerates and diffs). Delete the hand-maintained copy. Same treatment for `scope3Factors.js`.

### 4.2 Stop the client computing authoritative numbers
- `Scope3Form.jsx:230` computes `co2e = amount * ef / 1000` and never sends `factor_unit`, so a `t/unit` factor is overstated 1000× and the server cannot tell. Send `factor_unit`; let `compute_scope3_co2e` own the arithmetic.
- `Scope1Form.jsx:1538` divides combustion efficiency by 100 unconditionally; the server accepts `%` or a fraction. Send raw.
- `ManageData.jsx:4089` annualises at a flat 8760 h; the server is leap- and month-aware.
- `Scope3Form.jsx:88-89` applies unsourced FX rates (EUR 1.1, DZD 0.0074) and business-day periods to *persisted* factors. Remove or move server-side with a versioned source.
- `ModernReportGenerator.js:84` caps the dataset at 5000 rows with only a `console.warn` → a compliance PDF silently truncates. Paginate or refuse with a visible error.
- `GasCompositionCalculator.jsx:326` labels a 23.685 m³/kg-mol value as "L/mol" (a 1000× trap for anyone following the label), and its output is persisted as custom factors.

### 4.3 Stale-response and performance correctness
No `AbortController` or request-id guard exists anywhere in `src`. Add one shared `useApiQuery` hook and adopt it in the 8 affected pages (`Scope1Form`, `DashboardEnhanced`, `CarbonIntensity`, `MethaneIntensity`, `UncertaintyAssessment`, `Reports`, `SbtiDashboard`, `MethaneExplorer`). Debounce `Scope1Form.jsx:2865-2875` as `Reports.jsx:115` already does. Invalidate the module-level GWP cache in `useGwpStandard.js:14` when Settings saves.

### 4.4 Accessibility on the primary flows (this is a compliance product; assume an auditor uses it)
- Make the Emissions scope cards real buttons and the breadcrumbs links (`Emissions.jsx:54-57, 110-113, 166-169, 227-241`) — today the entry point to all three scopes is mouse-only.
- `role="status"`/`aria-live` on toasts (`Toast.jsx:86, 160`) and a labelled close button.
- Replace the 5 hand-rolled modals with the existing accessible `components/Modal.jsx` / `Drawer.jsx` (they already have `role="dialog"`, `aria-modal`, Escape; the hand-rolled ones have none).
- `scope="col"` on tables, `htmlFor` on labels, `aria-invalid`/`aria-describedby` wired to field errors — and **delete `utils/a11yLabels.js`**, the runtime `MutationObserver` that fakes labels and hides the gap.
- `type="button"` on the 270 untyped buttons.

### 4.5 Lint and dead weight
`npm run lint` currently exits 1 with 9 errors and 38 warnings, and `eslint.config.js:27`'s `varsIgnorePattern: '^([A-Z_]|motion$)'` exempts every PascalCase identifier — which is why dead imports survive. Narrow the pattern, fix the findings, wire lint into CI. Delete the ~2,300 lines of never-imported components, the five tracked Python patch scripts inside `src/`, and the tracked 1.4 MB `stats.html`. Prune the unused deps (`chart.js`, the radix/cva/clsx/formik/yup/tailwind stack) and decide on the undeclared redux trio.

### P4 exit criteria
Zero client-only authoritative arithmetic; generated catalogues byte-identical to the server's; keyboard-only operation possible end-to-end; `npm run lint` exit 0; CI runs the Playwright specs that currently never execute.

---

## PHASE P5 — Operations (week 3-4) — *cheap, because Docker is gone*

### 5.1 Commit to one process, and make the code enforce it
Add a startup assertion that refuses to boot when more than one worker is configured (a `WORKERS`/`WEB_CONCURRENCY` guard in `app.py`), so the four latent multi-process bugs cannot be triggered by accident:
limiter `memory://` (`config.py:116`), dashboard `TTLCache` (`dashboard.py:32`), `upload_jobs` (`background_processor.py:14`), WAL counter (`app.py:70`).
Then document it in `README.md`: **one process, one host, no `--workers`.**

### 5.2 Fix the real operational defects that survive single-process
- **Bulk jobs are unbounded threads.** `background_processor.py:500-516` spawns a raw thread per job with no cap. Add a small bounded pool (2-3) and reject beyond it with a clear message. Also move the *staged upload file* into `UPLOAD_JOB_DIR` (today it goes to the OS temp root and is never reaped by `_prune_old_jobs`, `:265-294`; I found leftovers accumulating).
- **One transaction per import file** (`:465, 997`; 50k cap) holds the SQLite write lock for the whole file, blocking every other writer for up to `busy_timeout=30s`, and grows the WAL by the import size. Commit in ~2k-row batches with savepoints.
- **WAL growth is not actually bounded.** `app.py:68-69` documents `wal_checkpoint(TRUNCATE)` every 500 commits; the code sets the interval to 100 (`:71`) and runs **`PASSIVE`** (`:119`), which never truncates while any reader holds a snapshot and never waits. Fix the checkpoint mode and the comment, guard the counter with the existing lock, and stop opening a fresh pooled connection per checkpoint.
- **`notifications` has no index at all** while being written on every create/update. Add `(user_id, is_read, created_at)` plus a partial index for the `user_id IS NULL` broadcast branch. This is the fastest-growing table in the schema.
- **79% of the live DB is free pages** (`freelist 444/564`). Enable `auto_vacuum=INCREMENTAL` on new databases and schedule a periodic `VACUUM`.
- **Missing UNIQUE constraints** on the natural keys of `scope2_emissions`, `scope3_emissions`, `cap_emissions`, `flaring_details`, `ogmp_surveys`, `facility_equity_shares` and `custom_factors.name`. Duplicate prevention is Python-only, so two concurrent imports double-count reported totals. Add the constraints and make the importers upsert.
- **Equity's ≤100% rule is check-then-insert** (`equity_routes.py:166-184`) — a TOCTOU that over-allocates and doubles equity emissions. Serialize it.
- **Facility deletion 500s** whenever LDAR rows exist, because `ComponentInventory`/`FugitiveSurvey` have no relationship from `Facility` (`models.py:276-323`). Add the cascades.
- **`flaring_details.status` defaults to `"Verified"`** (`models.py:756`), so flaring rows bypass maker-checker while feeding Decree 21-330 reporting. Default to `Pending` and add it plus `OgmpSurvey` to `maker_checker.RECORD_TYPES`.

### 5.3 Make the schema honest
Five mechanisms currently create schema: `models.py` metadata (via the reconcile revision), six patch revisions, `ensure_database_indexes()` raw DDL on every start (`app.py:422-446, 488`), the ad-hoc `add_columns.py`/`add_indexes.py`/`migrate_ogmp.py`, and `id_guard._next_id` creating `id_high_water` from a request path.
**Action:** delete `ensure_database_indexes()` and the ad-hoc scripts; move `id_high_water` into a revision; fix the two irreversible revisions (`9c3e1a7b5d20:32-34` and `a1c4e7f20b31:81-83` are `def downgrade(): pass`, and `2ef6f882b02c:45` drops an unnamed FK constraint that raises on SQLite — so a downgrade cannot complete while `alembic_version` still moves, after which future upgrades silently no-op).
Then fix what the schema lost: `schema_sync.add_missing_columns` never emits `NOT NULL` (`schema_sync.py:36-45`), so `users.session_version`, `custom_factors.is_archived` and `sbti_targets.scope_coverage` are NOT NULL in the models and nullable in the DB (I verified all three). Four model FKs never reached the database (`cap_emissions.approved_by/updated_by`, `scope2/scope3.updated_by` — verified). Add a revision that backfills and enforces.

### 5.4 Fix the audit-trail gaps — the product's core claim
- **26 mutating routes write no `ActivityLog` at all**: production data create/delete/import (`data.py:75, 220, 253`), OGMP level upgrades (`data.py:537`), mitigation and reporting-metadata (`managedata.py:269, 340, 428`), goals and base years (`managedata.py:677, 760, 819`), facility import (`facilities.py:428`), every notification mutation (`notifications.py:167, 200, 237, 261`), the legacy bulk JSON import (`emissions.py:506`), report issuance (`reports.py:316`), equity shares (`equity_routes.py:139`).
- **10 routes commit the data change and the audit row in separate transactions**, so a crash leaves an unaudited record: `custom_factors.py:214/229, 312/327, 357/372, 474/489`; `emissions.py:2871/2906`; `managedata.py:101/115, 137/151, 173/187, 594/608`; `scope2.py:423/454`; `scope3.py:184/199/211`; `dashboard.py:902/914`.
- **The GWP-standard change rewrites every Scope 1 `co2e_total` including Verified rows, with no audit entry, no return to Pending, and Scope 3 left stale** (`routes/auth.py:742-805, 924-928`). `scripts/recalculate_emissions.py:135-148` already shows the correct pattern (RECALCULATE log + `status="Pending"`). Adopt it.
- Minor: `equity_routes.py:196` logs `UPDATE` on create; `emissions.py:3266-3273` collapses a bulk delete into one `record_id="BULK"` row; `satellite.py:298-312` hand-builds a log with a NULL `facility_id`, making it invisible to regional auditors.

Enforce the contract with a test: walk `app.url_map`, and for every non-GET rule assert that its handler calls `log_activity_and_notify` (or is on an explicit allowlist). That converts "26 missing" from a discovery into a permanent gate.

### 5.5 Backup and restore — tested, or it does not exist
`docs/validation/HUMAN_REVIEW_REQUIRED.md` HR-08 marks this CRITICAL/blocking. Currently: two untracked snapshots of 1.91 GB and 2.34 GB, no pruning (neither `scripts/backup.py:11-29` nor `backup.ps1:12` rotates), and `scripts/restore.py` only verifies into a sandbox then deletes it — the name is misleading.
**Action:** scheduled backup with keep-N retention, and a `scripts/verify_restore.py` that restores the newest backup into a scratch DB, runs `PRAGMA integrity_check`, asserts row counts against the live DB, and **runs in CI on a seeded fixture** so the restore path is exercised weekly.

### P5 exit criteria
One process enforced by code; bounded job concurrency; indexes and UNIQUE constraints present; schema created by exactly one mechanism; every mutating route audited in the same transaction; a restore that has been executed, not just written.

---

## PHASE P6 — Security and configuration (week 4, largely done by P0)

| # | Action | Where |
|---|---|---|
| 6.1 | One `services/rbac.py` predicate replacing five ad-hoc role tuples, so the IT lockout cannot leak per-module again. Fix the leaks: CAP read (`cap_routes.py:37, 56, 203`), equity read (`equity_routes.py:34, 51, 203`), satellite (`satellite.py:67, 111, 134, 205, 349` — blocks only `it_admin`, and `:147` short-circuits on an empty allowed-list) | routes/* |
| 6.2 | Escape `ilike` input: `reports.py:641-734` and the scope matcher `auth.py:48-50` (a `user.location` of `%` matches every facility). The `_escape_like` helper already exists at `emissions.py:36-38` | routes/* |
| 6.3 | Per-route rate limits on the currently-unlimited expensive/outbound endpoints: `POST /emissions/upload/start`, `POST /reports/generate`, every report export, all `/api/satellite/*` (each makes an outbound HTTPS call), `PUT /auth/settings` (can trigger a full-table UPDATE) | routes/* |
| 6.4 | Encrypt Copernicus credentials at rest, and stop returning `copernicus_username`/`client_id` to every authenticated user (`auth.py:807-834` masks only the password and secret) | `routes/auth.py`, `SystemSetting` |
| 6.5 | Add `HSTS`, `Permissions-Policy`, COOP/CORP; tighten `style-src 'unsafe-inline'` and `img-src https:` | `app.py:213-223` |
| 6.6 | Narrow the hard-coded CORS list and remove the forced append of `kaljah.github.io` (`config.py:38-49`); reconcile with `.env.example` | `config.py` |
| 6.7 | Decide `SameSite` policy. `SameSite=None` in production (`config.py:92-95`) plus `WTF_CSRF_SSL_STRICT=False` (`:103`) leaves the token as the only control. Also: **the `/api/csrf-token` "double-submit cookie" is not double-submit** — the cookie is never compared to the header (`app.py:495-512` and its docstring). Either implement it or fix the docstring and the test that asserts it | `app.py`, `config.py` |
| 6.8 | Default `USE_PROXY_FIX=true` (or configure trusted proxies) — otherwise the limiter keys anonymous traffic on the proxy address (`extensions.py:36`, `app.py:64-66`) | `app.py` |
| 6.9 | Implement failed-login recording (`FAILED_LOGIN` is read at `audit.py:228, 241` and never written) and account lockout | `routes/auth.py`, `routes/audit.py` |

---

## PHASE P7 — Hygiene and governance (week 5, mostly deletion)

- **Repo hygiene:** delete `new/server.rar`, `new/server/calculations/calculations.rar` (both are full source snapshots including `models.py`), `cbam_removal.patch` (770 KB), `cbam_removal_utf8.patch`, `cbam_diff_*.patch`, the `brain/**/.tempmediaStorage/*.pdf` session media, and `db.bak_before_scope_deletion`. Bring the pack from ~490 MB toward <50 MB. Move the ~25 one-off `generate_*.py`/`seed_*.py` scripts out of the server root (they are currently collected by `pytest.ini`'s `testpaths = tests .`).
- **Flip the defect ledger's contract.** `AUDIT_FINDINGS.md` still shows all 115 entries as `**Status:** Confirmed` after most were fixed, so no reader can tell open from closed. Add a real status field (`open`/`fixed`/`wontfix` with commit SHA) and a `scripts/check_docs.py` that fails when a bug cited in `audit/FIX_LOG.md` is still `open`.
- **Correct the drifted docs.** `AUDIT_MEMORY.md` §0 is wrong on: AR5 20-yr GWP (says 82.5/268; code has 84/264), CH4 density (says 0.6785/1.861; code has 0.67722/1.85814), the role model (says `it_admin` is unrestricted and ranks it above `admin`; `utils.py:31` denies IT roles entirely and `it_admin` has *less* data access than `admin`), and "Alembic holds only 2 revisions" in `CLAUDE.md` (there are 7). §8 of `ANALYSIS_MEMORY.md` has the corrected text.
- **Single source of truth for constants.** `client/src/constants.js` and `calculations/constants.py` must stay byte-identical in value; generate one from the other and add the parity test that `test_catalog_factors.py:119` already does for factors.
- **Write the ADRs** for the decisions currently living only in code comments: single-process deployment, SQLite-vs-Postgres, the D-04 admin self-verification policy (which means the `admin` role has no separation of duties against itself), Scope 2 market-based exclusion, and the `auditor` role (referenced in 18 places, assignable nowhere — either implement it or delete the branches).

---

## Suggested sequencing

```
Week 1   P0 (4h) ──► P1 numeric divergence ──► P2.1 quality gates
Week 2   P2.2-2.4 CI+bootstrap ──► P3.1-3.3 correctness   ──┐
         P4.1-4.2 SPA numerics ─────────────────────────────┤ parallel
Week 3   P3.4-3.8 ──► P5.1-5.2 ops ─────────────────────────┤
Week 4   P5.3-5.5 schema+audit+restore ──► P6 security ─────┤
Week 5   P7 hygiene ──► regrade ────────────────────────────┘
```

**Regrade gate (end of week 5):** quality-gate script green · CI runs the whole 2,099-test suite on the host's Python with a pinned dev-requirements · zero known numeric divergence · no mutating route unaudited or unrated-limited · `verify_restore.py` green in CI · `npm run lint` exit 0 · keyboard-only end-to-end run · repo pack <50 MB · `AUDIT_FINDINGS.md` statuses reconciled.

---

## What would still not be A+ afterwards

Being honest about the ceiling, so nobody is surprised at the regrade:

1. **External validation of the calculation engine.** Every oracle in this repo — including `validation/reference_model/` — was written by the same effort that wrote the code. Fixing the differential gate makes the oracles *strict*; it does not make them *external*. A+ in a regulated domain requires at least 2-3 pathways traced to published worked examples (API Compendium 2021 exhibits, EPA GHG Reporting Rule examples) and signed off by a qualified reviewer. That is `HR-10`, and no amount of engineering closes it.
2. **The regulatory-standards question** (`HR-09`): which jurisdiction's accepted methodology governs. Until answered, "correct" has no definition.
3. **Scope 2 market-based reporting** is entirely absent (GHG Protocol Scope 2 Guidance requires dual reporting). That is a feature gap, not a defect — but it caps the product's compliance claim.
4. **The `admin` self-verification policy** (D-04) means the maker-checker control has a documented hole by design. A+ would require four-eyes above a materiality threshold.
5. **Brute-force/credential-stuffing resistance** needs the lockout from 6.9 plus, ideally, an external identity provider.

If those five are addressed too, this stops being "a good platform with weak verification" and becomes a defensible compliance system. That is the whole distance.
