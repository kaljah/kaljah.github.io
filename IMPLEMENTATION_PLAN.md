# IMPLEMENTATION PLAN — GHG Platform Audit Remediation

Prepared by the lead auditor after the discovery phase. **No fixes have been implemented.** Each entry is derived from the confirmed bug in `AUDIT_FINDINGS.md`. Priorities, root-cause groups, risks and the final re-run status were added by the lead auditor.

## Summary

- Bugs in this plan: **109**. Critical: 4 · High: 37 · Medium: 52 · Low: 16
- Final re-run against the current code: **85 still reproduce**, **1 no longer reproduce** (BUG-024), 0 inconclusive (none), 23 are browser repros confirmed by the agents on the post-change code but not re-run in the final pass.
- Merged duplicate: BUG-035 → BUG-033.
- Not in the plan: BUG-100 to BUG-104 — see *Excluded entries* at the end.

## Before starting

1. **Freeze the baseline.** The calculation engine and client forms were edited while the audit was running (`audit/baseline2_uncommitted.diff`). Commit or branch the current state so every fix is measured against a known tree.
2. **Fix BUG-016 first.** Several fixes add constraints or columns and must ship as Alembic migrations.
3. **Decide the data policy.** Many fixes stop bad data from entering but do not clean what is already stored (test rows of 1e13–1e15, NULL facility names, years 1800/2099, duplicate rows, rows computed with wrong formulas). Each cleanup or recalculation should be an explicit, logged job approved by the data owner.
4. **Calculation scope.** At the user's request the calculation workstreams (A, C) were stopped mid-audit. The calculation bugs they had already confirmed are included (P2/P3). Other calculators were **not** audited and are listed as unverified in the final report.

## Data policy (decided by the user, 2026-09-26)

| Topic | Decision | Consequence |
|---|---|---|
| 9 absurd Scope 1 test rows (ids 640, 645, 649, 658, 662, 667, 669: 1e13 MMBtu gas; 655, 675: 1e15 t coal) | **Hard delete** | Step D-1 below. Irreversible: back up the DB first and get explicit go-ahead at execution time, since it runs on the live DB. |
| Records stored with a wrong formula | **New data only** | No recalculation job. Past records and previously issued reports keep known-wrong values; fixed logic applies to new and re-edited records. |
| Other invalid stored data (13 nameless facilities, years 1800/2099, month 99, duplicate groups, split Scope 3 categories) | **Block only new bad data** | Validation stops new occurrences. Constraints that existing rows would violate become application-level checks. Existing rows remain. |
| User deletion vs approver evidence | **Delete, keep a snapshot** | Approver/creator name and email copied onto records at write/approval time. The 470 historic Verified rows without an approver stay as they are. |

**Known residual after the policy:** once the 9 rows are deleted, Verified Scope 1 is still ≈5.1e9 t, mostly seed rows inserted by an external tester script with precomputed CO2e (Agent B). Under *block only new bad data* these stay, so dashboards will still show implausible totals until they are decided on separately.

### Step D-1 — Delete the 9 test rows (runs once, in phase P1)

1. Back up `new/server/ghg_app.db` (stop the app, or use the SQLite backup API).
2. List the 9 rows (id, facility, quantity, unit, co2e_total, status, created_by) and confirm they are the test rows. The ids come from the audit snapshot and must be re-checked against the live DB.
3. Delete them in one transaction, with one ActivityLog entry per row (action `DATA_CLEANUP_DELETE`, old values captured).
4. Clear the dashboard cache and confirm the Verified and Pending Scope 1 totals drop by the deleted amounts (≈3.718e12 t Verified, ≈4.686e12 t Pending).

## Root-cause groups (fix these once, not per bug)

| Group | Root cause | Bugs | Shared fix |
|---|---|---|---|
| RC-1 | **No central input validation** — Numeric fields parsed with bare float() (NaN/Inf pass `< 0` checks), no required-field / year / month / unit / plausibility validation, and bulk import applies weaker rules than the manual API. | BUG-007, BUG-029, BUG-034, BUG-039, BUG-043, BUG-045, BUG-050, BUG-073, BUG-083, BUG-085, BUG-087, BUG-099, BUG-109, BUG-111, BUG-112 | One shared validator module (`new/server/validation.py`): finite numbers, ranges, required fields, year 1900–(current+1), month 1–12, unit whitelist, per-unit plausibility caps; used by every create / PUT / JSON-bulk / file-bulk path; generic error bodies with request id. |
| RC-2 | **Maker-checker / status policy duplicated per route** — Each scope and route decides status on its own; no guard on already-decided records; no concurrency control; outcome never reaches the maker. | BUG-053, BUG-060, BUG-067, BUG-070, BUG-074, BUG-058, BUG-092, BUG-031 | One status-policy helper (initial status by role and channel, allowed transitions, approver ≠ creator/last-modifier), conditional UPDATE … WHERE status IN (…) for approve/reject, notification to `created_by`. |
| RC-3 | **Authorization / region scoping applied inconsistently** — `@login_required` alone on sensitive endpoints; `get_allowed_facility_ids` not applied to every read/write; client-side-only session. | BUG-001, BUG-020, BUG-032, BUG-038, BUG-046, BUG-076, BUG-093, BUG-114, BUG-106 | Role + facility-scope decorator applied uniformly (inventory in `audit/notes/I_endpoints.md`); server-side session revocation (`session_version`). |
| RC-4 | **Units are not parsed / converted in one place** — Factor and activity units are matched by substring in several places; scale prefixes, time denominators, energy units, subscripts and rate-vs-annual units are mishandled; client labels disagree with what the server assumes. | BUG-011, BUG-027, BUG-033, BUG-047, BUG-048, BUG-049, BUG-051, BUG-063, BUG-066, BUG-091, BUG-096, BUG-097 | Single unit parser/normaliser in `calculations/units.py` (canonical unit tokens, numerator/denominator, scale prefixes, time basis); unknown units rejected, never passed through 1:1; custom factors stored with explicit units. |
| RC-5 | **Edit / recalculation path diverges from the create path** — PUT re-computes from a stale `source_payload`, drops custom-factor ids, stores different uncertainty semantics, and create persists different fields than it computes from. | BUG-003, BUG-030, BUG-037, BUG-042, BUG-071 | One `build_calc_payload()` + `persist_calc_result()` used by create, PUT, import and bulk; explicit cache invalidation after every write. |
| RC-6 | **Client and server hold separate copies of catalogs, constants and formulas** — Tier 1 catalog, GWP tables, field names, preview formulas and segment rules are duplicated and have drifted. | BUG-015, BUG-090, BUG-110, BUG-082, BUG-012, BUG-013, BUG-005, BUG-086, BUG-080 | Serve catalogs/constants from the API; server preview endpoint instead of client-side formulas; reject unknown `calc_inputs` keys. |
| RC-7 | **Dashboard filters not applied through one base query** — Each dashboard sub-query re-implements year / segment / activity / division / pending / GWP filtering, so panels on the same page disagree. | BUG-004, BUG-017, BUG-026, BUG-036, BUG-040, BUG-041, BUG-054, BUG-061, BUG-064, BUG-072, BUG-079, BUG-094, BUG-088 | One filtered base query per scope (joined through `Facility`) that every panel derives from; invariant tests (parts sum to totals under every filter combination). |
| RC-8 | **Uncertainty aggregation model** — Correlated EF uncertainty treated as independent; max-of-gases instead of CO2e weighting; inconsistent fraction/percent and k; overrides ignored. | BUG-008, BUG-018, BUG-025, BUG-037, BUG-043, BUG-055, BUG-062 | One uncertainty service (IPCC Approach 1 with correlation by EF source, CO2e-weighted per gas, stored as 1σ fraction, displayed as 95 % k=2) used by the Uncertainty page, QA dashboard and result panel. |
| RC-9 | **SBTi period / scope logic** — Progress year, scope coverage, empty data and pathway validation are not modelled. | BUG-014, BUG-019, BUG-028, BUG-034, BUG-059 | Store scope coverage with the target; progress on the last complete year; explicit 'no data' state; validated pathway. |
| RC-10 | **Bulk import integrity** — Duplicate keys too coarse or not updated in-batch, name-based factor lookup, silent defaults, no audit log, canonical forms differ from the manual API. | BUG-057, BUG-058, BUG-065, BUG-081, BUG-085, BUG-089, BUG-111, BUG-001 | Bulk rows go through the same validator + persistence helpers as manual create (RC-1, RC-5); natural-key unique indexes; per-row audit log. |
| RC-11 | **Referential integrity on delete** — Hard deletes with hand-maintained clean-up lists; ids reused; name-based references. | BUG-009, BUG-010, BUG-056, BUG-069 | Soft-delete/deactivate users and factors; real FKs with explicit ON DELETE; AUTOINCREMENT ids. |
| RC-12 | **Reports print unverified, mislabelled or fabricated content** — Client PDF generator hard-codes claims and mislabels scope/period; granular intensities invent constants. | BUG-077, BUG-078, BUG-044, BUG-084, BUG-002, BUG-006, BUG-113 | Reports built only from server aggregates with explicit period/status labels; no literal performance claims. |

## Fix order

| Phase | Focus | Bugs |
|---|---|---|
| P0 | Prerequisites (do first — other fixes depend on these) | BUG-016 (M) |
| P1 | Critical data-integrity & security defects | BUG-001 (C), BUG-015 (C), BUG-077 (C), BUG-020 (H), BUG-053 (H), BUG-067 (H), BUG-099 (H), BUG-083 (H), BUG-114 (M), BUG-078 (H) |
| P2 | Critical & high calculation errors | BUG-066 (C), BUG-011 (H), BUG-012 (H), BUG-023 (H), BUG-027 (H), BUG-047 (H), BUG-048 (H), BUG-049 (H), BUG-063 (H), BUG-110 (H), BUG-090 (H) |
| P3 | Systemic calculation / business-logic defects | BUG-003 (H), BUG-030 (M), BUG-037 (H), BUG-042 (H), BUG-068 (H), BUG-024 (M), BUG-051 (M), BUG-050 (M), BUG-013 (M), BUG-005 (M), BUG-109 (M), BUG-091 (M), BUG-096 (M), BUG-097 (M) |
| P4 | Backend / API defects | BUG-007 (M), BUG-029 (H), BUG-073 (H), BUG-085 (H), BUG-111 (M), BUG-112 (M), BUG-034 (M), BUG-039 (M), BUG-045 (M), BUG-060 (M), BUG-070 (M), BUG-074 (L), BUG-093 (M), BUG-032 (M), BUG-038 (M), BUG-046 (H), BUG-076 (L), BUG-106 (M), BUG-087 (L) |
| P5 | Database defects | BUG-057 (H), BUG-081 (H), BUG-089 (M), BUG-058 (M), BUG-065 (M), BUG-056 (M), BUG-009 (M), BUG-010 (M), BUG-069 (L) |
| P6 | Emissions / reporting defects | BUG-044 (H), BUG-084 (M), BUG-002 (M), BUG-006 (M), BUG-113 (L), BUG-031 (M), BUG-052 (M), BUG-075 (M) |
| P7 | Dashboard / intensity defects | BUG-040 (H), BUG-004 (H), BUG-017 (H), BUG-026 (H), BUG-094 (H), BUG-033 (H), BUG-036 (M), BUG-054 (M), BUG-041 (M), BUG-061 (M), BUG-071 (M), BUG-079 (M), BUG-064 (L), BUG-072 (L), BUG-080 (L), BUG-086 (L), BUG-088 (L) |
| P8 | Uncertainty / SBTi defects | BUG-008 (H), BUG-018 (H), BUG-025 (M), BUG-043 (M), BUG-055 (M), BUG-062 (L), BUG-014 (H), BUG-019 (H), BUG-028 (M), BUG-059 (M) |
| P9 | UI defects | BUG-092 (M), BUG-105 (M), BUG-107 (M), BUG-021 (M), BUG-095 (M), BUG-115 (L), BUG-022 (L), BUG-082 (L), BUG-098 (L), BUG-108 (L) |


# PHASE P0 — Prerequisites (do first — other fixes depend on these)

_Phase regression risk:_ Stamping existing databases wrongly can skip or duplicate columns. Test on copies of every deployed DB.

---

# BUG-016 — Alembic migration chain is unusable: `flask db upgrade` fails on both the existing DB and a fresh DB

**Severity:** Medium · **Category:** Database · **Phase:** P0 · **Root cause group:** — · **Found by:** Agent J (Database)

**Current status:** **Still present** — `audit/repro/BUG-016.py` re-run on the final code: bug reproduced.

## Problem

Alembic migration chain is unusable: `flask db upgrade` fails on both the existing DB and a fresh DB

- **Actual:** - Existing DB: stamped at `7fe333372c71` but already contains the columns that `52c620a620d2` adds (added by `add_columns.py` / create_all), so upgrade aborts. - Fresh DB: importing `app` runs `db.create_all()` (full current schema) before Alembic runs, and the base revision is an `add_column("segment")` (no initial create-table revision), so upgrade aborts at the first revision. - Schema diff create_all-fresh vs snapshot: identical columns/FKs/indexes except server defaults (`facilities.equity_share_pct`, 11 `production_data.*` columns have `DEFAULT 0.0/100.0` in the snapshot but none in a f…
- **Expected:** The DB stamped revision matches its actual schema, and `flask db upgrade` brings any DB to head.

## Root Cause

Schema is managed three ways (create_all at import, ad-hoc ALTER scripts / connect hook, Alembic) with no reconciliation; no baseline revision; `add_columns.py` adds columns without stamping.

## Affected Files

- `new/server/add_columns.py`
- `new/server/app.py`

## Affected Features

No working migration path: any future column added to a model will not reach existing DBs (create_all never ALTERs existing tables) and cannot be applied via Alembic without manual stamping. Postgres deployments (docker-compose/Render CMD run only `create_all`) will silently miss new columns → runtime `no such column` errors after upgrades. `server_default` drift means raw-SQL inserts behave differently on fresh vs old DBs.

## Required Changes

Create a baseline revision matching the current models, `flask db stamp head` existing DBs after verifying, remove create_all/ad-hoc ALTERs from import-time code and run `flask db upgrade` in the container entrypoint.

## Database Changes

Baseline Alembic revision matching current models; stamp existing DBs; stop import-time create_all/ALTER.

## Backend Changes

Changes in `new/server/add_columns.py`, `new/server/app.py` as described above.

## Frontend Changes

None.

## Calculation Changes

None.

## Tests To Add/Change

- Port `audit/repro/BUG-016.py` into a pytest regression test under `new/server/tests/` (assert the Expected value; independent hand-derived numbers, not a second call to the same function).
- Add edge cases: zero, missing, negative, NaN/Inf, boundary values for every field the fix touches.
- Review existing tests that assert the old behaviour; change an expected value only when the new value is independently derived and documented in the test.

## Browser Verification

- API/backend fix. After the fix, open the page(s) that consume this data (see Affected Features) and confirm the displayed value matches the API and DB.

## Regression Risks

- Stamping existing databases wrongly can skip or duplicate columns. Test on copies of every deployed DB.

## Acceptance Criteria

1. `audit/repro/BUG-016.py` exits 0 on the fixed code (it prints expected vs actual).
2. Expected behaviour holds: The DB stamped revision matches its actual schema, and `flask db upgrade` brings any DB to head.
3. Full backend suite (`python -m pytest tests/` in `new/server`) and frontend checks (`npm run lint`, `npm run test`) pass.
4. No other open bug's repro changes from fail→pass or pass→fail unexpectedly (re-run `audit/work/rerun/run_all.sh`).

---


# PHASE P1 — Critical data-integrity & security defects

_Phase regression risk:_ Tightening authorization can lock out legitimate workflows (bulk facility import by superusers, report downloads). Re-run the full role matrix after the change.

---

# BUG-001 — Bulk upload job API lets any logged-in role (user, it_admin) create/overwrite facilities and custom factors, bypassing RBAC and region scoping

**Severity:** Critical · **Category:** Security · **Phase:** P1 · **Root cause group:** RC-3, RC-10 · **Found by:** Agent I (Backend/API/Security)

**Current status:** **Still present** — `audit/repro/BUG-001.py` re-run on the final code: bug reproduced.

## Problem

Bulk upload job API lets any logged-in role (user, it_admin) create/overwrite facilities and custom factors, bypassing RBAC and region scoping

- **Actual:** Both jobs complete (`status=completed, processed=2`). Facility 3 (Center) `location` overwritten to `HACKED_user` / `HACKED_it_admin`; new facilities `NEWFAC_user` (created_by 18) and `NEWFAC_it_admin` (created_by 19) created in region East; custom factors `EVIL_user` / `EVIL_it_admin` with `co2_factor=999` created. Same calls to the direct endpoints return 403.
- **Expected:** 403 (the direct routes are protected: `POST /api/facilities/import` → 403 and `POST /api/custom-factors` → 403 for both roles; it_admin must have zero business-data write access; a West user must not touch a Center facility).

## Root Cause

Authorization is enforced per-route on the dedicated endpoints but the generic job endpoint accepts an arbitrary `scope` and the background processor trusts it. No role / facility-scope checks exist in the facilities/custom-factor row handlers. (Also applies to `scope=sources|production|mitigation` for it_admin — those use the facility map, which is empty for IT roles, so they fail; facilities/custom_factors do not use it.)

## Affected Files

- `new/server/background_processor.py`
- `new/server/routes/emissions.py`

## Affected Features

Privilege escalation: any authenticated account, including IT administrators who are supposed to have zero business-data access, can create facilities, rename/relocate/re-region any facility in any region (which also changes which users can see it via region scoping), and inject custom emission factors that feed Scope 1 calculations (factor lookup by name in `cf_name_map`). Custom factors created this way have no maker-checker step.

## Required Changes

In `upload_start`, whitelist `scope` per role: reject IT roles entirely; allow `facilities` / `custom_factors` only for admin/superuser (and apply the same region restriction as `/api/facilities/import`); in `_process_row_facilities` restrict the existing-name lookup to the uploader's allowed facility ids.

Implement through the shared fix for RC-3 (Authorization / region scoping applied inconsistently), RC-10 (Bulk import integrity) rather than a local patch.

## Database Changes

None required.

## Backend Changes

Changes in `new/server/background_processor.py`, `new/server/routes/emissions.py` as described above.

## Frontend Changes

None.

## Calculation Changes

None.

## Tests To Add/Change

- Port `audit/repro/BUG-001.py` into a pytest regression test under `new/server/tests/` (assert the Expected value; independent hand-derived numbers, not a second call to the same function).
- Add edge cases: zero, missing, negative, NaN/Inf, boundary values for every field the fix touches.
- Add the group-level invariant tests for RC-3, RC-10 (see Root-Cause Groups).
- Review existing tests that assert the old behaviour; change an expected value only when the new value is independently derived and documented in the test.

## Browser Verification

- API/backend fix. After the fix, open the page(s) that consume this data (see Affected Features) and confirm the displayed value matches the API and DB.

## Regression Risks

- Tightening authorization can lock out legitimate workflows (superuser bulk facility import, report downloads, audit trail). Re-run the endpoint role matrix in `audit/notes/I_endpoints.md`.
- Bulk imports that previously succeeded may now fail row validation or de-duplicate differently; unique indexes fail on existing duplicates until cleaned.

## Acceptance Criteria

1. `audit/repro/BUG-001.py` exits 0 on the fixed code (it prints expected vs actual).
2. Expected behaviour holds: 403 (the direct routes are protected: `POST /api/facilities/import` → 403 and `POST /api/custom-factors` → 403 for both roles; it_admin must have zero business-data write access; a West user must not touch a Center facility).
3. Full backend suite (`python -m pytest tests/` in `new/server`) and frontend checks (`npm run lint`, `npm run test`) pass.
4. No other open bug's repro changes from fail→pass or pass→fail unexpectedly (re-run `audit/work/rerun/run_all.sh`).

---

# BUG-015 — 43 Tier 1 factors offered in the Scope 1 UI do not exist in the server catalog; records save with HTTP 201 and 0 emissions

**Severity:** Critical · **Category:** Emissions · **Phase:** P1 · **Root cause group:** RC-6 · **Found by:** Agent C (Tier / Factor Auditor) · **Independent confirmations:** 2

**Current status:** **Still present** — `audit/repro/BUG-015.py` re-run on the final code: bug reproduced.

## Problem

43 Tier 1 factors offered in the Scope 1 UI do not exist in the server catalog; records save with HTTP 201 and 0 emissions

- **Actual:** 43 of the 56 are stored with `co2e_total = 0` and HTTP 201, with calc_method `server_default` or a `server_*_factor` fallback. Admin records are stored as `Verified`, so they count in dashboards and reports as zero-emission sources. The other 13 are non-zero only because a hard-coded legacy fallback, such as the fugitive average table, computes something unrelated to the selected factor.
- **Expected:** The client factor is applied. For Butane 1000 scf: 3.28 MMBtu × 65 = 213.2 kg CO2 = 0.213 t. Otherwise the server rejects the request with 4xx "factor not found".

## Root Cause

There are two independent factor catalogs. The UI lists client keys, but the server looks the factor up by name in its own catalog. On a miss, `factor_data={}` flows into the calculators, and a missing factor is treated as 0 instead of an error. Only the bulk-upload path rejects a missing standard factor, and only for combustion processes (`emissions.py` ~line 666).

## Affected Files

- `new/client/src/utils/EmissionFactors.js`
- `new/server/calculations/legacy_engine.py`
- `new/server/routes/emissions.py`

## Affected Features

Whole emission sources silently vanish from inventories. Examples: pneumatic devices, blowdowns, tank flashing, CNG/LNG and biofuel combustion. The user sees a success toast, and no QA flag is raised.

## Required Changes

- Serve the Tier 1 dropdown from the server catalog (`/api/emission-factors`), or merge the catalogs into one source. - In `compute_emissions`/`create_emission`, reject `factor_source` default/custom when no factor is resolved, instead of computing with 0.

Implement through the shared fix for RC-6 (Client and server hold separate copies of catalogs, constants and formulas) rather than a local patch.

## Database Changes

None required.

## Backend Changes

Changes in `new/server/routes/emissions.py` as described above.

## Frontend Changes

Changes in `new/client/src/utils/EmissionFactors.js` as described above.

## Calculation Changes

Changes in `new/server/calculations/legacy_engine.py`. **Data policy: new data only** — records already stored are NOT recalculated; the fix applies to new records and to records edited after the fix. Past reports keep their existing values.

## Tests To Add/Change

- Port `audit/repro/BUG-015.py` into a pytest regression test under `new/server/tests/` (assert the Expected value; independent hand-derived numbers, not a second call to the same function).
- Add edge cases: zero, missing, negative, NaN/Inf, boundary values for every field the fix touches.
- Add the group-level invariant tests for RC-6 (see Root-Cause Groups).
- Review existing tests that assert the old behaviour; change an expected value only when the new value is independently derived and documented in the test.

## Browser Verification

- Reproduce the steps in AUDIT_FINDINGS.md on an isolated stack (`audit/tools/vite_audit.mjs` + backend on an audit DB copy) and confirm the Expected result on screen.
- Compare the UI value with the API response and the DB row for the same record; refresh and reopen the record.

## Regression Risks

- Removing a client-side catalog/formula can remove options users rely on; every factor still offered must exist server-side before the switch. Previews will change to server-computed values.
- Correcting a formula changes every stored value computed by it. Stored records are NOT recomputed automatically — a controlled recalculation job with before/after diff and audit log is required, and reported totals for past periods will move.

## Acceptance Criteria

1. `audit/repro/BUG-015.py` exits 0 on the fixed code (it prints expected vs actual).
2. Expected behaviour holds: The client factor is applied. For Butane 1000 scf: 3.28 MMBtu × 65 = 213.2 kg CO2 = 0.213 t. Otherwise the server rejects the request with 4xx "factor not found".
3. Full backend suite (`python -m pytest tests/` in `new/server`) and frontend checks (`npm run lint`, `npm run test`) pass.
4. No other open bug's repro changes from fail→pass or pass→fail unexpectedly (re-run `audit/work/rerun/run_all.sh`).

---

# BUG-077 — Dashboard "Export Executive Brief (PDF)" in the default All-Years view reports every year and every Pending record as "FISCAL YEAR 2026" / "Total verified records": PDF total 8.41 T tCO2e vs 3.72 T on the dashboard

**Severity:** Critical · **Category:** Dashboard · **Phase:** P1 · **Root cause group:** RC-12 · **Found by:** Agent F (Dashboard reconciliation auditor)

**Current status:** **Still present** — `audit/repro/BUG-077.py` re-run on the final code: bug reproduced.

## Problem

Dashboard "Export Executive Brief (PDF)" in the default All-Years view reports every year and every Pending record as "FISCAL YEAR 2026" / "Total verified records": PDF total 8.41 T tCO2e vs 3.72 T on the dashboard

- **Actual:** The PDF cover says "FISCAL YEAR 2026" and "The reporting period is for the year 2026". Table 5.1 shows Scope 1 **8,409,567,617,747.49**, Scope 2 **1,540,060.68** (Verified + Pending), Scope 3 **366.85** (Verified + Pending) and a Total of **8,409,569,158,175.02**. The Annex footer says "Total verified records: 809 | Fiscal Year: 2026", although 149 of the 809 rows are Pending. The Chapter 6 flaring table in the same PDF covers 2026 only (100 kNm3 / 210.2 t, see BUG-026).
- **Expected:** The PDF matches the dashboard it was exported from (Verified only, All Years): Scope 1 3,723,125,709,415.04, Scope 2 1,539,702.62, total S1+S2 **3,723,127,249,117.66**, Scope 3 216.85, and a cover that says "All Historical Records". Or, if the report is for FY2026, only 2026 Verified data: S1+S2 = 9,992.41 + S2 2026.

## Root Cause

The dashboard sends `undefined` instead of "all", and the generator defaults a missing year to the current year for labels only, not for data. The generator never filters by approval status and trusts `/api/emissions`, which is a data-management listing and not an inventory query. The generator also re-derives CO2e client-side.

## Affected Files

- `new/client/src/pages/DashboardEnhanced.jsx`
- `new/client/src/utils/ModernReportGenerator.js`

## Affected Features

The one-click "Executive Brief" from the main dashboard presents multi-year totals, including unapproved Pending records, as a single fiscal year of verified data. Reported emissions are overstated by 2.26× on the snapshot, and by roughly the number of reporting years on any normal dataset. The labels ("verified", "FY2026", ISO 14064-1 table) give it the look of an official disclosure.

## Required Changes

Pass "all" explicitly and label it correctly, or require a single year for the brief. Request only `status=Verified` (add a status filter to `/api/emissions` or use the dashboard aggregate endpoints). Use the stored `co2e_total` so the PDF reconciles with the dashboard. Count Verified rows only in the "verified records" footer.

Implement through the shared fix for RC-12 (Reports print unverified, mislabelled or fabricated content) rather than a local patch.

## Database Changes

None required.

## Backend Changes

None beyond the above.

## Frontend Changes

Changes in `new/client/src/pages/DashboardEnhanced.jsx`, `new/client/src/utils/ModernReportGenerator.js` as described above.

## Calculation Changes

None.

## Tests To Add/Change

- Port `audit/repro/BUG-077.py` into a pytest regression test under `new/server/tests/` (assert the Expected value; independent hand-derived numbers, not a second call to the same function).
- Add edge cases: zero, missing, negative, NaN/Inf, boundary values for every field the fix touches.
- Add the group-level invariant tests for RC-12 (see Root-Cause Groups).
- Review existing tests that assert the old behaviour; change an expected value only when the new value is independently derived and documented in the test.

## Browser Verification

- Reproduce the steps in AUDIT_FINDINGS.md on an isolated stack (`audit/tools/vite_audit.mjs` + backend on an audit DB copy) and confirm the Expected result on screen.
- Compare the UI value with the API response and the DB row for the same record; refresh and reopen the record.

## Regression Risks

- Report output changes visibly; stakeholders may compare against previously issued PDFs.

## Acceptance Criteria

1. `audit/repro/BUG-077.py` exits 0 on the fixed code (it prints expected vs actual).
2. Expected behaviour holds: The PDF matches the dashboard it was exported from (Verified only, All Years): Scope 1 3,723,125,709,415.04, Scope 2 1,539,702.62, total S1+S2 **3,723,127,249,117.66**, Scope 3 216.85, and a cover that says "All Historical Records". Or, if the report is for FY2026, only 2026 Verified data: S1+S2 = 9,992.41 + S2 2026.
3. Full backend suite (`python -m pytest tests/` in `new/server`) and frontend checks (`npm run lint`, `npm run test`) pass.
4. No other open bug's repro changes from fail→pass or pass→fail unexpectedly (re-run `audit/work/rerun/run_all.sh`).

---

# BUG-020 — /api/reports/master-annual-report serves full annual GHG report PDFs to any logged-in role (incl. it_admin and out-of-region users) and returns a static, pre-generated file regardless of facility_id

**Severity:** High · **Category:** Security · **Phase:** P1 · **Root cause group:** RC-3 · **Found by:** Agent I (Backend/API/Security)

**Current status:** **Still present** — `audit/repro/BUG-020.py` re-run on the final code: bug reproduced.

## Problem

/api/reports/master-annual-report serves full annual GHG report PDFs to any logged-in role (incl. it_admin and out-of-region users) and returns a static, pre-generated file regardless of facility_id

- **Actual:** All four requests return 200 `application/pdf` (1,901,139 bytes El Merk report; 1,912,094 bytes Groupement Berkine report). Additionally: - Any `facility_id` other than 170/"elm" (e.g. a West facility the user owns) returns the *Groupement Berkine* report — a different facility's data. - The PDF is read from a hard-coded absolute path `c:/Users/samsung/Desktop/H2/*.pdf` and only regenerated if missing, so the numbers are frozen at the time the file was generated (files dated 2026-09-24), not the current DB; on any other host/path it would try to generate into the developer's desktop path.
- **Expected:** 403 for it_admin (IT roles have zero business-data access, cf. `get_allowed_facility_ids` → []) and for a West user requesting El Merk / consolidated data. The report should also reflect the requested facility and the current database.

## Root Cause

Demo endpoint wired to static files with no authorization or facility scoping.

## Affected Files

- `new/server/routes/reports.py`

## Affected Features

Cross-region data exposure of full annual GHG/CAP reports (emissions, production, compliance) to any authenticated user and to IT administrators; logically wrong report content for any facility other than El Merk; stale figures.

## Required Changes

Require business role + `require_facility_access(user, facility_id)` (and unrestricted access for the consolidated report); generate from current DB per request (or cache keyed by facility/DB version) instead of a hard-coded desktop path; 404 for unsupported facility ids.

Implement through the shared fix for RC-3 (Authorization / region scoping applied inconsistently) rather than a local patch.

## Database Changes

None required.

## Backend Changes

Changes in `new/server/routes/reports.py` as described above.

## Frontend Changes

None.

## Calculation Changes

None.

## Tests To Add/Change

- Port `audit/repro/BUG-020.py` into a pytest regression test under `new/server/tests/` (assert the Expected value; independent hand-derived numbers, not a second call to the same function).
- Add edge cases: zero, missing, negative, NaN/Inf, boundary values for every field the fix touches.
- Add the group-level invariant tests for RC-3 (see Root-Cause Groups).
- Review existing tests that assert the old behaviour; change an expected value only when the new value is independently derived and documented in the test.

## Browser Verification

- API/backend fix. After the fix, open the page(s) that consume this data (see Affected Features) and confirm the displayed value matches the API and DB.

## Regression Risks

- Tightening authorization can lock out legitimate workflows (superuser bulk facility import, report downloads, audit trail). Re-run the endpoint role matrix in `audit/notes/I_endpoints.md`.

## Acceptance Criteria

1. `audit/repro/BUG-020.py` exits 0 on the fixed code (it prints expected vs actual).
2. Expected behaviour holds: 403 for it_admin (IT roles have zero business-data access, cf. `get_allowed_facility_ids` → []) and for a West user requesting El Merk / consolidated data. The report should also reflect the requested facility and the current database.
3. Full backend suite (`python -m pytest tests/` in `new/server`) and frontend checks (`npm run lint`, `npm run test`) pass.
4. No other open bug's repro changes from fail→pass or pass→fail unexpectedly (re-run `audit/work/rerun/run_all.sh`).

---

# BUG-053 — CAP (air-pollutant) emissions bypass maker-checker: POST /api/cap/emissions stores records as "Verified" by default (client-controlled status) for role user; negative mass/concentration accepted

**Severity:** High · **Category:** API · **Phase:** P1 · **Root cause group:** RC-2 · **Found by:** Agent I (Backend/API/Security)

**Current status:** **Still present** — `audit/repro/BUG-053.py` re-run on the final code: bug reproduced.

## Problem

CAP (air-pollutant) emissions bypass maker-checker: POST /api/cap/emissions stores records as "Verified" by default (client-controlled status) for role user; negative mass/concentration accepted

- **Actual:** All 200; stored rows: `(NO2, 0.15 t, Verified, created_by 18)`, `(SO2, -5000.0 t, conc -1.0, Verified)`, `(CO, 1.0 t, Verified)`.
- **Expected:** Data-entry records created as Pending (the platform's maker-checker rule: only admin entries are auto-Verified; bulk/non-admin entries are Pending), `status` not client-settable, negative mass/concentration rejected with 400.

## Root Cause

Status defaulted/taken from the payload; no validation.

## Affected Files

- `new/server/routes/cap_routes.py`

## Affected Features

Unreviewed (and negative) air-pollutant masses enter regulatory CAP totals and Decree 06-138 compliance results as Verified; a user can also overwrite an existing verified CAP record by passing its `id`.

## Required Changes

Ignore client `status`; set Pending for non-admin (Verified only via an approval step); validate finite, non-negative numbers; make `/compliance` use Verified records only.

Implement through the shared fix for RC-2 (Maker-checker / status policy duplicated per route) rather than a local patch.

## Database Changes

None required.

## Backend Changes

Changes in `new/server/routes/cap_routes.py` as described above.

## Frontend Changes

None.

## Calculation Changes

None.

## Tests To Add/Change

- Port `audit/repro/BUG-053.py` into a pytest regression test under `new/server/tests/` (assert the Expected value; independent hand-derived numbers, not a second call to the same function).
- Add edge cases: zero, missing, negative, NaN/Inf, boundary values for every field the fix touches.
- Add the group-level invariant tests for RC-2 (see Root-Cause Groups).
- Review existing tests that assert the old behaviour; change an expected value only when the new value is independently derived and documented in the test.

## Browser Verification

- API/backend fix. After the fix, open the page(s) that consume this data (see Affected Features) and confirm the displayed value matches the API and DB.

## Regression Risks

- Status-policy changes alter who can approve and what edits reset records to Pending; re-run the full maker-checker role matrix (user, superuser, admin, it roles) for Scope 1/2/3, CAP and bulk.

## Acceptance Criteria

1. `audit/repro/BUG-053.py` exits 0 on the fixed code (it prints expected vs actual).
2. Expected behaviour holds: Data-entry records created as Pending (the platform's maker-checker rule: only admin entries are auto-Verified; bulk/non-admin entries are Pending), `status` not client-settable, negative mass/concentration rejected with 400.
3. Full backend suite (`python -m pytest tests/` in `new/server`) and frontend checks (`npm run lint`, `npm run test`) pass.
4. No other open bug's repro changes from fail→pass or pass→fail unexpectedly (re-run `audit/work/rerun/run_all.sh`).

---

# BUG-067 — Maker-checker bypass through edit and delete: a superuser can approve a record they just edited, silently re-date/re-assign Verified records, and a user can hard-delete their own Verified records

**Severity:** High · **Category:** Security · **Phase:** P1 · **Root cause group:** RC-2 · **Found by:** Agent I (Backend/API/Security)

**Current status:** **Still present** — `audit/repro/BUG-067.py` re-run on the final code: bug reproduced.

## Problem

Maker-checker bypass through edit and delete: a superuser can approve a record they just edited, silently re-date/re-assign Verified records, and a user can hard-delete their own Verified records

- **Actual:** (1) `{'year': 2019, 'status': 'Verified'}`. (2) 200, record `quantity 999999, status Verified, approved_by 17` (the editor). (3) 200, row deleted.
- **Expected:** (1) Record returns to Pending (a year change moves emissions between reporting periods). (2) 403 — the superuser is the maker of the approved values. (3) Deleting Verified data requires reviewer action (or 403).

## Root Cause

Segregation of duties keyed only on `created_by`; the status-reset rule exempts superusers for non-quantity fields; delete has no status gate.

## Affected Files

- `new/server/routes/emissions.py`

## Affected Features

One person can put arbitrary values into Verified totals (edit + self-approve), move Verified emissions between reporting years/facilities without review, and remove Verified data — defeats the maker-checker control that dashboards rely on (they aggregate Verified only).

## Required Changes

Track `last_modified_by`; block approval when approver is creator OR last modifier; any edit by non-admin (incl. superuser) to a Verified record → Pending; forbid deleting Verified records for non-admins (or route via a pending-deletion review).

Implement through the shared fix for RC-2 (Maker-checker / status policy duplicated per route) rather than a local patch.

## Database Changes

None required.

## Backend Changes

Changes in `new/server/routes/emissions.py` as described above.

## Frontend Changes

None.

## Calculation Changes

None.

## Tests To Add/Change

- Port `audit/repro/BUG-067.py` into a pytest regression test under `new/server/tests/` (assert the Expected value; independent hand-derived numbers, not a second call to the same function).
- Add edge cases: zero, missing, negative, NaN/Inf, boundary values for every field the fix touches.
- Add the group-level invariant tests for RC-2 (see Root-Cause Groups).
- Review existing tests that assert the old behaviour; change an expected value only when the new value is independently derived and documented in the test.

## Browser Verification

- API/backend fix. After the fix, open the page(s) that consume this data (see Affected Features) and confirm the displayed value matches the API and DB.

## Regression Risks

- Status-policy changes alter who can approve and what edits reset records to Pending; re-run the full maker-checker role matrix (user, superuser, admin, it roles) for Scope 1/2/3, CAP and bulk.

## Acceptance Criteria

1. `audit/repro/BUG-067.py` exits 0 on the fixed code (it prints expected vs actual).
2. Expected behaviour holds: (1) Record returns to Pending (a year change moves emissions between reporting periods). (2) 403 — the superuser is the maker of the approved values. (3) Deleting Verified data requires reviewer action (or 403).
3. Full backend suite (`python -m pytest tests/` in `new/server`) and frontend checks (`npm run lint`, `npm run test`) pass.
4. No other open bug's repro changes from fail→pass or pass→fail unexpectedly (re-run `audit/work/rerun/run_all.sh`).

---

# BUG-099 — Scope 2 electricity create trusts client-supplied `co2e` / `emission_factor`: 0 kWh can be booked as 12,345 tCO2e, negative Scope 2 (-500 t) is accepted, and any unknown grid region takes the client's factor

**Severity:** High · **Category:** API · **Phase:** P1 · **Root cause group:** RC-1 · **Found by:** Agent L (Browser) · **Independent confirmations:** 1

**Current status:** **Confirmed on the post-change code by the browser agent** (`audit/repro/BUG-099.mjs`); not re-run in the final pass (needs a live UI stack).

## Problem

Scope 2 electricity create trusts client-supplied `co2e` / `emission_factor`: 0 kWh can be booked as 12,345 tCO2e, negative Scope 2 (-500 t) is accepted, and any unknown grid region takes the client's factor

- **Actual:** All return 201. DB (`scope2_emissions`): - id 42 (user, Pending): `electricity_kwh=0, emission_factor=0.522, co2e=12345.0` - id 41 (user, Pending): `electricity_kwh=0, co2e=-500.0` - id 40 (user, Pending): `electricity_kwh=1000, emission_factor=0.001, co2e=0.001` (client factor on an unknown region) - ids 43-46: the same payloads as audit_superuser are stored **Verified** directly (BUG-060), e.g. id 46 `0 kWh → 12345 t`, id 45 `-500 t`, and are counted in dashboard totals.
- **Expected:** The server derives Scope 2 CO2e only from activity data × a server-resolved factor. It rejects zero/negative consumption with a non-zero CO2e, rejects negative CO2e, and rejects unknown grid regions (or requires a documented supplier/market factor with validation).

## Root Cause

The endpoint was written to accept a client-calculated result and only overrides it when its own inputs are positive. There is no input validation for the direct `co2e` path, and `GRID_FACTORS` lookups that miss fall back to the client EF.

## Affected Files

- `new/server/routes/scope2.py`

## Affected Features

Scope 2 totals, the dashboard, SBTi Scope 1+2 progress and intensity can be set to arbitrary values (including negative, which offsets real emissions) without any consumption data. For superusers this is immediately Verified. Integrity of the reported Scope 2 inventory cannot be guaranteed.

## Required Changes

Ignore client `co2e`/`emission_factor` for electricity; require `electricity_kwh > 0` (or amount+unit) and a known grid region, or a separately validated market-based instrument (supplier factor with evidence field, 0 ≤ EF ≤ plausible max). Reject negative/non-finite values with 400.

Implement through the shared fix for RC-1 (No central input validation) rather than a local patch.

## Database Changes

None required.

## Backend Changes

Changes in `new/server/routes/scope2.py` as described above.

## Frontend Changes

None.

## Calculation Changes

None.

## Tests To Add/Change

- Port `audit/repro/BUG-099.mjs` into a Playwright spec under `new/client/e2e/` (or a vitest test where it is pure component logic).
- Add edge cases: zero, missing, negative, NaN/Inf, boundary values for every field the fix touches.
- Add the group-level invariant tests for RC-1 (see Root-Cause Groups).
- Review existing tests that assert the old behaviour; change an expected value only when the new value is independently derived and documented in the test.

## Browser Verification

- Reproduce the steps in AUDIT_FINDINGS.md on an isolated stack (`audit/tools/vite_audit.mjs` + backend on an audit DB copy) and confirm the Expected result on screen.
- Compare the UI value with the API response and the DB row for the same record; refresh and reopen the record.

## Regression Risks

- Stricter validation will reject inputs accepted today (existing bulk templates, integrations, scripts). Existing invalid rows remain until a cleanup job runs.

## Acceptance Criteria

1. `audit/repro/BUG-099.mjs` exits 0 on the fixed code (it prints expected vs actual).
2. Expected behaviour holds: The server derives Scope 2 CO2e only from activity data × a server-resolved factor. It rejects zero/negative consumption with a non-zero CO2e, rejects negative CO2e, and rejects unknown grid regions (or requires a documented supplier/market factor with validation).
3. Full backend suite (`python -m pytest tests/` in `new/server`) and frontend checks (`npm run lint`, `npm run test`) pass.
4. No other open bug's repro changes from fail→pass or pass→fail unexpectedly (re-run `audit/work/rerun/run_all.sh`).

---

# BUG-083 — Activity-data write endpoints accept "NaN" / "1e999" (±Infinity): a Scope 3 record with activity_data=Infinity makes /dashboard/batch-all, /scope3/summary and /api/scope3 emit invalid JSON ("Infinity")

**Severity:** High · **Category:** API · **Phase:** P1 · **Root cause group:** RC-1 · **Found by:** Agent I (Backend/API/Security)

**Current status:** **Still present** — `audit/repro/BUG-083.py` re-run on the final code: bug reproduced.

## Problem

Activity-data write endpoints accept "NaN" / "1e999" (±Infinity): a Scope 3 record with activity_data=Infinity makes /dashboard/batch-all, /scope3/summary and /api/scope3 emit invalid JSON ("Infinity")

- **Actual:** All 5 → 201. Stored: scope3 id 29 `activity_data=inf, co2e=inf, status=Verified`; scope2 `electricity_kwh=NULL, co2e=NULL` (SQLite turns NaN into NULL, so a "created" record silently has no value); custom factor `co2_factor=NULL`. Afterwards `batch-all` returns `"scope3_emissions":Infinity`, `scope3/summary` returns `"2025":Infinity`, `/api/scope3` returns `"activity_data":Infinity` — all HTTP 200 with bodies that are not valid JSON (browser `JSON.parse` rejects `Infinity`), so the main dashboard batch and Scope 3 pages fail to load for every user who can see that facility.
- **Expected:** 400 for non-finite numbers (the fuzz found the same for 1e999/NaN across these 5 endpoints).

## Root Cause

No `math.isfinite` validation on numeric inputs; Flask's JSON provider serialises inf as `Infinity`.

## Affected Files

- See Location in AUDIT_FINDINGS.md: Numeric fields are parsed with bare `float(...)` and only range-checked with `< 0` (which NaN/inf pass) or not at all: - `routes/scope3.py:96` `activity_data = float(data.get("activity_data") or data.get("amount", 0))`, `emission_factor` - `routes/scope2.py` `electricity_kwh`, `steam_ton`, `heat_mm…

## Affected Features

One entry (any business role can create Scope 3 data for its facility; admin entries are auto-Verified) breaks the dashboard/Scope 3 views for all users in scope; NaN inputs create records with NULL activity/emissions that pass as successful saves.

## Required Changes

Central numeric parser rejecting non-finite / out-of-range values with 400 in all write paths (manual, PUT, JSON bulk, file bulk).

Implement through the shared fix for RC-1 (No central input validation) rather than a local patch.

## Database Changes

None required.

## Backend Changes

None beyond the above.

## Frontend Changes

None.

## Calculation Changes

None.

## Tests To Add/Change

- Port `audit/repro/BUG-083.py` into a pytest regression test under `new/server/tests/` (assert the Expected value; independent hand-derived numbers, not a second call to the same function).
- Add edge cases: zero, missing, negative, NaN/Inf, boundary values for every field the fix touches.
- Add the group-level invariant tests for RC-1 (see Root-Cause Groups).
- Review existing tests that assert the old behaviour; change an expected value only when the new value is independently derived and documented in the test.

## Browser Verification

- API/backend fix. After the fix, open the page(s) that consume this data (see Affected Features) and confirm the displayed value matches the API and DB.

## Regression Risks

- Stricter validation will reject inputs accepted today (existing bulk templates, integrations, scripts). Existing invalid rows remain until a cleanup job runs.

## Acceptance Criteria

1. `audit/repro/BUG-083.py` exits 0 on the fixed code (it prints expected vs actual).
2. Expected behaviour holds: 400 for non-finite numbers (the fuzz found the same for 1e999/NaN across these 5 endpoints).
3. Full backend suite (`python -m pytest tests/` in `new/server`) and frontend checks (`npm run lint`, `npm run test`) pass.
4. No other open bug's repro changes from fail→pass or pass→fail unexpectedly (re-run `audit/work/rerun/run_all.sh`).

---

# BUG-114 — Logout does not invalidate the session: a session cookie captured before logout keeps full API access (client-side signed cookie, no server-side revocation)

**Severity:** Medium · **Category:** Security · **Phase:** P1 · **Root cause group:** RC-3 · **Found by:** Agent L (Browser) · **Independent confirmations:** 1

**Current status:** **Confirmed on the post-change code by the browser agent** (`audit/repro/BUG-114.mjs`); not re-run in the final pass (needs a live UI stack).

## Problem

Logout does not invalidate the session: a session cookie captured before logout keeps full API access (client-side signed cookie, no server-side revocation)

- **Actual:** Context B: `/api/auth/me` → **200** `{"authenticated":true,...}` for audit_superuser; `/api/emissions…` → **200**. Logout only removes the cookie from the browser that clicked it.
- **Expected:** After logout the old session is dead everywhere: 401 for any reuse of the cookie.

## Root Cause

Stateless signed-cookie sessions without a revocation list or server-side session id; logout cannot invalidate copies of the cookie.

## Affected Files

- `new/server/config.py`
- `new/server/routes/auth.py`

## Affected Features

A stolen or shared cookie (shared workstation, proxy logs, XSS, browser sync) stays usable after the user logs out, for the session lifetime; the same applies after an admin deactivates/changes the role only if the per-request user reload does not catch it (not tested here). For an emissions-reporting system with maker-checker roles this undermines the "log out ends access" control expected by ISO 27001-style reviews.

## Required Changes

Use a server-side session store (Flask-Session with Redis/DB) or add a per-user `session_version`/random session id stored server-side that is checked on every request and rotated on logout, password change and deactivation.

Implement through the shared fix for RC-3 (Authorization / region scoping applied inconsistently) rather than a local patch.

## Database Changes

Per-user `session_version` column (or server-side session table).
 Ship as an Alembic migration (requires BUG-016).

## Backend Changes

Changes in `new/server/config.py`, `new/server/routes/auth.py` as described above.

## Frontend Changes

None.

## Calculation Changes

None.

## Tests To Add/Change

- Port `audit/repro/BUG-114.mjs` into a Playwright spec under `new/client/e2e/` (or a vitest test where it is pure component logic).
- Add edge cases: zero, missing, negative, NaN/Inf, boundary values for every field the fix touches.
- Add the group-level invariant tests for RC-3 (see Root-Cause Groups).
- Review existing tests that assert the old behaviour; change an expected value only when the new value is independently derived and documented in the test.

## Browser Verification

- Reproduce the steps in AUDIT_FINDINGS.md on an isolated stack (`audit/tools/vite_audit.mjs` + backend on an audit DB copy) and confirm the Expected result on screen.
- Compare the UI value with the API response and the DB row for the same record; refresh and reopen the record.

## Regression Risks

- Tightening authorization can lock out legitimate workflows (superuser bulk facility import, report downloads, audit trail). Re-run the endpoint role matrix in `audit/notes/I_endpoints.md`.

## Acceptance Criteria

1. `audit/repro/BUG-114.mjs` exits 0 on the fixed code (it prints expected vs actual).
2. Expected behaviour holds: After logout the old session is dead everywhere: 401 for any reuse of the cookie.
3. Full backend suite (`python -m pytest tests/` in `new/server`) and frontend checks (`npm run lint`, `npm run test`) pass.
4. No other open bug's repro changes from fail→pass or pass→fail unexpectedly (re-run `audit/work/rerun/run_all.sh`).

---

# BUG-078 — Executive Brief / Master PDF prints hard-coded performance claims ("15.9 % reduction… on track for -30 %", "65.9 % methane reduction", "Lowest annual flaring on record (-38.0 %)", "VISR camera verified" DRE) regardless of the data

**Severity:** High · **Category:** Dashboard · **Phase:** P1 · **Root cause group:** RC-12 · **Found by:** Agent F (Dashboard reconciliation auditor)

**Current status:** **Still present** — `audit/repro/BUG-078.py` re-run on the final code: bug reproduced.

## Problem

Executive Brief / Master PDF prints hard-coded performance claims ("15.9 % reduction… on track for -30 %", "65.9 % methane reduction", "Lowest annual flaring on record (-38.0 %)", "VISR camera verified" DRE) regardless of the data

- **Actual:** The PDF page 3 "2030 Decarbonization Roadmap & Operational Milestones" prints "15.9% reduction achieved… on track for -30% by 2030", "65.9% reduction from baseline…", "Lowest annual flaring on record (-38.0% vs baseline); compliant…" and "98% **Measured** — Multi-spectral VISR camera verified". The DRE value is the 98 % default. Chapter 6 marks the DRE "VISR Infrared Multi-Spectral Camera … VERIFIED EFFICIENT".
- **Expected:** Narrative percentages are computed from the inventory, or omitted. Independent SQL on Verified data: S1+S2 2025 vs the 2021-2023 average = **-99.89 %**, CH4 = **-99.96 %** (both driven by bad seed data, but they are the platform's numbers); flaring YoY from the API = -99.92 %. `/flaring-summary` returns `dre_method: "Standard 98% Default"`, so the DRE must not be described as camera-measured.

## Root Cause

Demo or marketing copy, and sample figures from one reference dataset, were left in the report template as literals and fallbacks instead of being computed.

## Affected Files

- `new/client/src/utils/ModernReportGenerator.js`

## Affected Features

Every exported brief makes specific quantitative reduction and compliance claims that the data does not support, and presents default assumptions as measured and verified. This is a greenwashing and disclosure-integrity risk for any report shared externally.

## Required Changes

Compute each milestone (base-year average, YoY, CH4 change, flaring vs baseline) from the fetched data, or drop the sentences. Show "n/a" instead of numeric fallbacks. Derive DRE wording from `dre_method`.

Implement through the shared fix for RC-12 (Reports print unverified, mislabelled or fabricated content) rather than a local patch.

## Database Changes

None required.

## Backend Changes

None beyond the above.

## Frontend Changes

Changes in `new/client/src/utils/ModernReportGenerator.js` as described above.

## Calculation Changes

None.

## Tests To Add/Change

- Port `audit/repro/BUG-078.py` into a pytest regression test under `new/server/tests/` (assert the Expected value; independent hand-derived numbers, not a second call to the same function).
- Add edge cases: zero, missing, negative, NaN/Inf, boundary values for every field the fix touches.
- Add the group-level invariant tests for RC-12 (see Root-Cause Groups).
- Review existing tests that assert the old behaviour; change an expected value only when the new value is independently derived and documented in the test.

## Browser Verification

- Reproduce the steps in AUDIT_FINDINGS.md on an isolated stack (`audit/tools/vite_audit.mjs` + backend on an audit DB copy) and confirm the Expected result on screen.
- Compare the UI value with the API response and the DB row for the same record; refresh and reopen the record.

## Regression Risks

- Report output changes visibly; stakeholders may compare against previously issued PDFs.

## Acceptance Criteria

1. `audit/repro/BUG-078.py` exits 0 on the fixed code (it prints expected vs actual).
2. Expected behaviour holds: Narrative percentages are computed from the inventory, or omitted. Independent SQL on Verified data: S1+S2 2025 vs the 2021-2023 average = **-99.89 %**, CH4 = **-99.96 %** (both driven by bad seed data, but they are the platform's numbers); flaring YoY from the API = -99.92 %. `/flaring-summary` returns `dre_method: "Standard 98% Default"`, so the DRE must not be described as camera-measured.
3. Full backend suite (`python -m pytest tests/` in `new/server`) and frontend checks (`npm run lint`, `npm run test`) pass.
4. No other open bug's repro changes from fail→pass or pass→fail unexpectedly (re-run `audit/work/rerun/run_all.sh`).

---


# PHASE P2 — Critical & high calculation errors

_Phase regression risk:_ Correcting a formula changes every stored value computed by it. Stored records are NOT recomputed automatically — a controlled recalculation job with before/after diff and audit log is required, and reported totals for past periods will move.

---

# BUG-066 — AGR form throughput units MMscfd / Mcf/day / m³/yr are ignored by the server (read as MMscf/yr): CO2 365× low, 2.7× high, or 28,317× high

**Severity:** Critical · **Category:** Calculation · **Phase:** P2 · **Root cause group:** RC-4 · **Found by:** Agent K (Frontend/UI)

**Current status:** **Still present** — `audit/repro/BUG-066.py` re-run on the final code: bug reproduced.

## Problem

AGR form throughput units MMscfd / Mcf/day / m³/yr are ignored by the server (read as MMscf/yr): CO2 365× low, 2.7× high, or 28,317× high

- **Actual:** | Input | CO2 (t) | totalCo2e (t) | |---|---|---| | 1000 MMscf/yr | 2,371.4 | 2,828.7 (correct) | | 2.740 MMscfd | 6.5 | 7.7 (365× low) | | 2,739.7 Mcf/day | 6,497.0 | 7,749.8 (2.74× high) | | 28,316,847 m³/yr | 67,150,409 | 80,098,823 (28,317× high) | Browser submission (record id 752 in audit/db/ui.db): request `amount: 1, unit: "MMscf"`, `calc_inputs.agr = {agr_throughput: 28316800, agr_unit: "m3/yr", ...}`; response/record `co2e_total = 80,436,130 t` for a 1000 MMscf/yr unit, and stored activity `amount = 1 MMscf` (client conversion divides m³ by 28,316.8 **and** by 1000; correct is ÷28,3…
- **Expected:** Hand calculation: 1000 MMscf × (5 − 0.5) % = 45 MMscf CO2 = 4.5e7 scf ÷ 379.5 scf/lbmol × 44.01 lb/lbmol × 0.4536 kg/lb ≈ **2,367 t CO2** — identical for every unit.

## Root Cause

Client converts the throughput only into `amount`, but also forwards the raw throughput and unit string in `calc_inputs`; the dispatcher prefers `agr_throughput` and its `_normalize_volume` has no rate units (`/day`, `/yr`) and no `m3/yr`, falling through to "already MMscf". The client's m³/yr branch additionally has a spurious `/1000`.

## Affected Files

- `new/client/src/components/Scope1Form.jsx`
- `new/client/src/components/scope1/AGRForm.jsx`
- `new/server/calculations/dispatcher.py`

## Affected Features

Any AGR record entered in three of the four offered units is wrong by 2.7× to 28,000×; a single m³/yr entry adds ~80 Mt CO2e to the inventory and is auto-Verified for admin. Stored activity amount is also 1000× wrong for m³/yr.

## Required Changes

Server: handle rate/annual units explicitly (`mmscf/day`×365, `mcf/day`×0.365, `m3/yr`/`m3`÷28,316.85 etc.) and reject unknown units instead of passing through. Client: send one canonical value (MMscf/yr) in both `amount` and `calc_inputs.agr.agr_throughput`, and remove the extra `/1000`.

Implement through the shared fix for RC-4 (Units are not parsed / converted in one place) rather than a local patch.

## Database Changes

None required.

## Backend Changes

None beyond the above.

## Frontend Changes

Changes in `new/client/src/components/Scope1Form.jsx`, `new/client/src/components/scope1/AGRForm.jsx` as described above.

## Calculation Changes

Changes in `new/server/calculations/dispatcher.py`. **Data policy: new data only** — records already stored are NOT recalculated; the fix applies to new records and to records edited after the fix. Past reports keep their existing values.

## Tests To Add/Change

- Port `audit/repro/BUG-066.py` into a pytest regression test under `new/server/tests/` (assert the Expected value; independent hand-derived numbers, not a second call to the same function).
- Add edge cases: zero, missing, negative, NaN/Inf, boundary values for every field the fix touches.
- Add the group-level invariant tests for RC-4 (see Root-Cause Groups).
- Review existing tests that assert the old behaviour; change an expected value only when the new value is independently derived and documented in the test.

## Browser Verification

- Reproduce the steps in AUDIT_FINDINGS.md on an isolated stack (`audit/tools/vite_audit.mjs` + backend on an audit DB copy) and confirm the Expected result on screen.
- Compare the UI value with the API response and the DB row for the same record; refresh and reopen the record.

## Regression Risks

- A central unit parser changes results for every unit it now interprets correctly; stored records keep old values until a controlled recalculation. Unknown units that used to pass through will now be rejected.
- Correcting a formula changes every stored value computed by it. Stored records are NOT recomputed automatically — a controlled recalculation job with before/after diff and audit log is required, and reported totals for past periods will move.

## Acceptance Criteria

1. `audit/repro/BUG-066.py` exits 0 on the fixed code (it prints expected vs actual).
2. Expected behaviour holds: Hand calculation: 1000 MMscf × (5 − 0.5) % = 45 MMscf CO2 = 4.5e7 scf ÷ 379.5 scf/lbmol × 44.01 lb/lbmol × 0.4536 kg/lb ≈ **2,367 t CO2** — identical for every unit.
3. Full backend suite (`python -m pytest tests/` in `new/server`) and frontend checks (`npm run lint`, `npm run test`) pass.
4. No other open bug's repro changes from fail→pass or pass→fail unexpectedly (re-run `audit/work/rerun/run_all.sh`).

---

# BUG-011 — Well-completion "Rate × Duration" method divides the Mcf/hr rate by 24 (treats it as Mcf/day): CH4 understated 24×

**Severity:** High · **Category:** Calculation · **Phase:** P2 · **Root cause group:** RC-4 · **Found by:** Agent A (Calculation Engine Auditor)

**Current status:** **Still present** — `audit/repro/BUG-011.py` re-run on the final code: bug reproduced.

## Problem

Well-completion "Rate × Duration" method divides the Mcf/hr rate by 24 (treats it as Mcf/day): CH4 understated 24×

- **Actual:** `ch4_emissions = 0.015370 t`, `co2e_total = 0.4304 t`. That is exactly 1/24 of the expected value.
- **Expected:** Gas = 0.5 Mcf/hr × 1000 scf/Mcf × 24 h × 2 events = 24,000 scf = 679.60 m³ (60 °F, 14.696 psia). CH4 = 679.60 × 0.80 × 0.6785 kg/m³ = 368.9 kg = **0.3689 t CH4** → 10.33 tCO2e (GWP 28).

## Root Cause

The calculator assumes the rate is in Mcf/**day** unless `rate_unit` contains "hr". The dispatcher never passes a rate unit, but the UI collects Mcf/**hr**. The multiplier logic is also order-dependent: `"mscf" in "mmscf/day"` is true, so an MMscf rate would get ×1000 instead of ×1e6.

## Affected Files

- `new/client/src/components/scope1/CompletionsForm.jsx`
- `new/server/calculations/dispatcher.py`
- `new/server/calculations/vented.py`

## Affected Features

Every Tier 3 completion or flowback record entered with the Rate × Duration method (the form's default) under-reports CH4 and CO2e by 24×. This feeds Scope 1, methane intensity and OGMP totals.

## Required Changes

Pass an explicit `rate_unit` (UI: "mcf/hr") from the dispatcher, and make the calculator's default match the UI label. Test "mmscf" before "mscf" in the multiplier. Add a regression test against the hand value above.

Implement through the shared fix for RC-4 (Units are not parsed / converted in one place) rather than a local patch.

## Database Changes

None required.

## Backend Changes

None beyond the above.

## Frontend Changes

Changes in `new/client/src/components/scope1/CompletionsForm.jsx` as described above.

## Calculation Changes

Changes in `new/server/calculations/dispatcher.py`, `new/server/calculations/vented.py`. **Data policy: new data only** — records already stored are NOT recalculated; the fix applies to new records and to records edited after the fix. Past reports keep their existing values.

## Tests To Add/Change

- Port `audit/repro/BUG-011.py` into a pytest regression test under `new/server/tests/` (assert the Expected value; independent hand-derived numbers, not a second call to the same function).
- Add edge cases: zero, missing, negative, NaN/Inf, boundary values for every field the fix touches.
- Add the group-level invariant tests for RC-4 (see Root-Cause Groups).
- Review existing tests that assert the old behaviour; change an expected value only when the new value is independently derived and documented in the test.

## Browser Verification

- Reproduce the steps in AUDIT_FINDINGS.md on an isolated stack (`audit/tools/vite_audit.mjs` + backend on an audit DB copy) and confirm the Expected result on screen.
- Compare the UI value with the API response and the DB row for the same record; refresh and reopen the record.

## Regression Risks

- A central unit parser changes results for every unit it now interprets correctly; stored records keep old values until a controlled recalculation. Unknown units that used to pass through will now be rejected.
- Correcting a formula changes every stored value computed by it. Stored records are NOT recomputed automatically — a controlled recalculation job with before/after diff and audit log is required, and reported totals for past periods will move.

## Acceptance Criteria

1. `audit/repro/BUG-011.py` exits 0 on the fixed code (it prints expected vs actual).
2. Expected behaviour holds: Gas = 0.5 Mcf/hr × 1000 scf/Mcf × 24 h × 2 events = 24,000 scf = 679.60 m³ (60 °F, 14.696 psia). CH4 = 679.60 × 0.80 × 0.6785 kg/m³ = 368.9 kg = **0.3689 t CH4** → 10.33 tCO2e (GWP 28).
3. Full backend suite (`python -m pytest tests/` in `new/server`) and frontend checks (`npm run lint`, `npm run test`) pass.
4. No other open bug's repro changes from fail→pass or pass→fail unexpectedly (re-run `audit/work/rerun/run_all.sh`).

---

# BUG-012 — Well-completion Tier 3 uses `amount` as both the flowback volume and the event count (volume squared), and ignores rate × duration when the method dropdown is left at its default

**Severity:** High · **Category:** Calculation · **Phase:** P2 · **Root cause group:** RC-6 · **Found by:** Agent A (Calculation Engine Auditor)

**Current status:** **Still present** — `audit/repro/BUG-012.py` re-run on the final code: bug reproduced.

## Problem

Well-completion Tier 3 uses `amount` as both the flowback volume and the event count (volume squared), and ignores rate × duration when the method dropdown is left at its default

- **Actual:** (1) `ch4_emissions = 542.8 t` (**1000× too high**: volume 1000 × "events" 1000). (2) `ch4_emissions = 0.002171 t` (**170× too low**). The server fell back to `metered_volume`, took `amount`=2 (the event count) as 2 m³ of gas, and multiplied by 2 events. Rate and duration were ignored.
- **Expected:** (1) 1000 × 0.80 × 0.6785 / 1000 = **0.5428 t CH4** (15.20 tCO2e AR5). (2) 24,000 scf = 679.6 m³ → **0.3689 t CH4**.

## Root Cause

The single field `amount` is read both as the event multiplier and as the metered volume. The server defaults the method to `metered_volume`, while the UI displays `rate_duration` as its default and never sends it.

## Affected Files

- `new/client/src/components/scope1/CompletionsForm.jsx`
- `new/server/calculations/dispatcher.py`

## Affected Features

Metered completions submitted through the API or bulk import are inflated by a factor equal to the volume (quadratic). UI entries where the method dropdown was left at its default are understated by orders of magnitude. Both errors flow into Scope 1 CH4, methane intensity and OGMP.

## Required Changes

Use a dedicated `events` field (never `amount`) for the event count, and a dedicated volume field for metered flowback. Default the server method to the one the UI shows, or have the UI always send `calc_method`. Reject ambiguous payloads.

Implement through the shared fix for RC-6 (Client and server hold separate copies of catalogs, constants and formulas) rather than a local patch.

## Database Changes

None required.

## Backend Changes

None beyond the above.

## Frontend Changes

Changes in `new/client/src/components/scope1/CompletionsForm.jsx` as described above.

## Calculation Changes

Changes in `new/server/calculations/dispatcher.py`. **Data policy: new data only** — records already stored are NOT recalculated; the fix applies to new records and to records edited after the fix. Past reports keep their existing values.

## Tests To Add/Change

- Port `audit/repro/BUG-012.py` into a pytest regression test under `new/server/tests/` (assert the Expected value; independent hand-derived numbers, not a second call to the same function).
- Add edge cases: zero, missing, negative, NaN/Inf, boundary values for every field the fix touches.
- Add the group-level invariant tests for RC-6 (see Root-Cause Groups).
- Review existing tests that assert the old behaviour; change an expected value only when the new value is independently derived and documented in the test.

## Browser Verification

- Reproduce the steps in AUDIT_FINDINGS.md on an isolated stack (`audit/tools/vite_audit.mjs` + backend on an audit DB copy) and confirm the Expected result on screen.
- Compare the UI value with the API response and the DB row for the same record; refresh and reopen the record.

## Regression Risks

- Removing a client-side catalog/formula can remove options users rely on; every factor still offered must exist server-side before the switch. Previews will change to server-computed values.
- Correcting a formula changes every stored value computed by it. Stored records are NOT recomputed automatically — a controlled recalculation job with before/after diff and audit log is required, and reported totals for past periods will move.

## Acceptance Criteria

1. `audit/repro/BUG-012.py` exits 0 on the fixed code (it prints expected vs actual).
2. Expected behaviour holds: (1) 1000 × 0.80 × 0.6785 / 1000 = **0.5428 t CH4** (15.20 tCO2e AR5). (2) 24,000 scf = 679.6 m³ → **0.3689 t CH4**.
3. Full backend suite (`python -m pytest tests/` in `new/server`) and frontend checks (`npm run lint`, `npm run test`) pass.
4. No other open bug's repro changes from fail→pass or pass→fail unexpectedly (re-run `audit/work/rerun/run_all.sh`).

---

# BUG-023 — Tier 3 combustion/flaring gas composition: each component is converted percent→fraction on its own, so mol% values ≤ 1 (e.g. C4 = 1.0 %, C5 = 0.5 %) become 100 % / 50 %; CO2 inflated 2.7× on the app's own template sample

**Severity:** High · **Category:** Calculation · **Phase:** P2 · **Root cause group:** — · **Found by:** Agent A (Calculation Engine Auditor)

**Current status:** **Still present** — `audit/repro/BUG-023.py` re-run on the final code: bug reproduced.

## Problem

Tier 3 combustion/flaring gas composition: each component is converted percent→fraction on its own, so mol% values ≤ 1 (e.g. C4 = 1.0 %, C5 = 0.5 %) become 100 % / 50 %; CO2 inflated 2.7× on the app's own template sample

- **Actual:** `co2_emissions = 8.021 t`, `ch4_emissions = 0.002386 t`, `co2e_total = 8.089 t` (**2.6× too high**; CH4 2.5× too low). With the same composition entered as fractions (0.875, 0.052, …) the result is 3.001 t CO2. The remaining +1.9 % error is a separate issue: N2 is left out of the normalisation sum.
- **Expected:** Carbon number Σ(xᵢ·nᵢ) = 0.875 + 2(0.052) + 3(0.021) + 4(0.010) + 5(0.005) = 1.107 mol C / mol gas. CO2 = 1415.84 × (1.107 × 0.993 + 0.018) × 1.861 kg/m³ = **2.944 t CO2**. CH4 slip = 1415.84 × 0.875 × 0.007 × 0.6785 = **0.00588 t**. CO2e (AR5) ≈ **3.11 t**.

## Root Cause

Percent-vs-fraction detection is done per value (`> 1.0`) and not per composition. Any component whose mol% is ≤ 1 is misread as a fraction. The calculator then applies a second heuristic on the mixed sum.

## Affected Files

- `new/server/calculations/combustion.py`
- `new/server/calculations/dispatcher.py`

## Affected Features

Every Tier 3 combustion or flaring entry, whether through the API or bulk import, with any minor component between 0 and 1 mol% gets a wrong carbon balance. That describes most real gas analyses (C4–C10, CO2 often < 1 %). CO2 is overstated by up to several times and CH4 slip is wrong. The app's own sample row is affected.

## Required Changes

Decide the basis once for the whole composition (e.g. the documented mol% basis, or sum > 1.5 ⇒ percent) and apply it to every component, including CO2 and N2. Do not scale components individually.

## Database Changes

None required.

## Backend Changes

None beyond the above.

## Frontend Changes

None.

## Calculation Changes

Changes in `new/server/calculations/combustion.py`, `new/server/calculations/dispatcher.py`. **Data policy: new data only** — records already stored are NOT recalculated; the fix applies to new records and to records edited after the fix. Past reports keep their existing values.

## Tests To Add/Change

- Port `audit/repro/BUG-023.py` into a pytest regression test under `new/server/tests/` (assert the Expected value; independent hand-derived numbers, not a second call to the same function).
- Add edge cases: zero, missing, negative, NaN/Inf, boundary values for every field the fix touches.
- Review existing tests that assert the old behaviour; change an expected value only when the new value is independently derived and documented in the test.

## Browser Verification

- API/backend fix. After the fix, open the page(s) that consume this data (see Affected Features) and confirm the displayed value matches the API and DB.

## Regression Risks

- Correcting a formula changes every stored value computed by it. Stored records are NOT recomputed automatically — a controlled recalculation job with before/after diff and audit log is required, and reported totals for past periods will move.

## Acceptance Criteria

1. `audit/repro/BUG-023.py` exits 0 on the fixed code (it prints expected vs actual).
2. Expected behaviour holds: Carbon number Σ(xᵢ·nᵢ) = 0.875 + 2(0.052) + 3(0.021) + 4(0.010) + 5(0.005) = 1.107 mol C / mol gas. CO2 = 1415.84 × (1.107 × 0.993 + 0.018) × 1.861 kg/m³ = **2.944 t CO2**. CH4 slip = 1415.84 × 0.875 × 0.007 × 0.6785 = **0.00588 t**. CO2e (AR5) ≈ **3.11 t**.
3. Full backend suite (`python -m pytest tests/` in `new/server`) and frontend checks (`npm run lint`, `npm run test`) pass.
4. No other open bug's repro changes from fail→pass or pass→fail unexpectedly (re-run `audit/work/rerun/run_all.sh`).

---

# BUG-027 — Tier 1 combustion applies the catalog HHV in the wrong basis when the activity unit is mass or the other phase (diesel/crude per tonne ×3.6, natural gas per tonne ÷40, ethane per scf ×39)

**Severity:** High · **Category:** Calculation · **Phase:** P2 · **Root cause group:** RC-4 · **Found by:** Agent C (Tier / Factor Auditor)

**Current status:** **Still present** — `audit/repro/BUG-027.py` re-run on the final code: bug reproduced.

## Problem

Tier 1 combustion applies the catalog HHV in the wrong basis when the activity unit is mass or the other phase (diesel/crude per tonne ×3.6, natural gas per tonne ÷40, ethane per scf ×39)

- **Actual:** | Case | Actual (t CO2) | Ratio to expected | |---|---|---| | Diesel | 11.25 | 3.55× | | Crude | 11.34 | 3.66× | | Natural gas | 0.0597 | 0.025× | | Ethane | 4.148 | 39.5× (identical to 1000 gal) | | Propane (Liquid) | 0.203 | 0.13× | All cases return HTTP 201, with calc_method "Stationary Combustion" and no warning.

## Root Cause

The catalog HHV carries no unit. Its basis is implied by `baseUnit` (gal, scf or ton). The converter infers the basis from the activity unit, and from fuel-name keywords, instead of from the factor's basis. It has no density bridge between volume-basis HHV and mass activity.

## Affected Files

- `new/server/calculations/combustion.py`
- `new/server/emission_factors_api2021.py`

## Affected Features

Tier 1 combustion totals are wrong by 3.5× to 40× whenever a liquid or gaseous fuel is reported in kg or tonnes. Mass reporting is common outside the US. The same applies to ethane reported in scf, and to liquid propane in m3 or L via bulk upload/API.

## Required Changes

- Store the HHV unit explicitly (Btu/gal, Btu/scf, MMBtu/short ton). - Convert activity to the HHV basis using density when crossing mass↔volume, or reject units incompatible with the fuel's basis. - Fix `Ethane` to a liquid basis, or add a gaseous HHV.

Implement through the shared fix for RC-4 (Units are not parsed / converted in one place) rather than a local patch.

## Database Changes

None required.

## Backend Changes

None beyond the above.

## Frontend Changes

None.

## Calculation Changes

Changes in `new/server/calculations/combustion.py`, `new/server/emission_factors_api2021.py`. **Data policy: new data only** — records already stored are NOT recalculated; the fix applies to new records and to records edited after the fix. Past reports keep their existing values.

## Tests To Add/Change

- Port `audit/repro/BUG-027.py` into a pytest regression test under `new/server/tests/` (assert the Expected value; independent hand-derived numbers, not a second call to the same function).
- Add edge cases: zero, missing, negative, NaN/Inf, boundary values for every field the fix touches.
- Add the group-level invariant tests for RC-4 (see Root-Cause Groups).
- Review existing tests that assert the old behaviour; change an expected value only when the new value is independently derived and documented in the test.

## Browser Verification

- API/backend fix. After the fix, open the page(s) that consume this data (see Affected Features) and confirm the displayed value matches the API and DB.

## Regression Risks

- A central unit parser changes results for every unit it now interprets correctly; stored records keep old values until a controlled recalculation. Unknown units that used to pass through will now be rejected.
- Correcting a formula changes every stored value computed by it. Stored records are NOT recomputed automatically — a controlled recalculation job with before/after diff and audit log is required, and reported totals for past periods will move.

## Acceptance Criteria

1. `audit/repro/BUG-027.py` exits 0 on the fixed code (it prints expected vs actual).
2. Full backend suite (`python -m pytest tests/` in `new/server`) and frontend checks (`npm run lint`, `npm run test`) pass.
3. No other open bug's repro changes from fail→pass or pass→fail unexpectedly (re-run `audit/work/rerun/run_all.sh`).

---

# BUG-047 — Tier 1 fugitive and equipment factors in "per hour" units are multiplied only by the source count (no operating hours): annual CH4 understated 8,760×, and Tier 1 disagrees with Tier 3 for the same factor

**Severity:** High · **Category:** Calculation · **Phase:** P2 · **Root cause group:** RC-4 · **Found by:** Agent A (Calculation Engine Auditor) · **Independent confirmations:** 1

**Current status:** **Still present** — `audit/repro/BUG-047.py` re-run on the final code: bug reproduced.

## Problem

Tier 1 fugitive and equipment factors in "per hour" units are multiplied only by the source count (no operating hours): annual CH4 understated 8,760×, and Tier 1 disagrees with Tier 3 for the same factor

- **Actual:** Valves `ch4_emissions = 4.36e-5 t`; wellheads `1.8e-4 t`. That is the emission for **one hour**, 8,760× below annual. For comparison, Tier 3 (`factor_source=specific`) with the same factor gives 1.340 t for the wellheads, because `EquipmentFugitiveCalculator` multiplies by 8760. It also applies a separate 0.85 error.
- **Expected:** Annual (8,760 h): valves 10 × 4.36e-6 × 8760 = **0.3819 t CH4**; wellheads 10 × 1.8e-5 × 8760 = **1.577 t CH4**. Even for a one-month record (744 h) the values are 0.0324 t and 0.134 t.

## Root Cause

The generic calculator treats every factor as "per activity unit". Per-hour factors need count × hours, but no hours input is collected or applied.

## Affected Files

- `new/server/calculations/dispatcher.py`

## Affected Features

All Tier 1 equipment/component fugitive CH4 (usually the largest methane source in upstream inventories) is understated by about 4 orders of magnitude. This affects methane intensity, OGMP and Scope 1 totals.

## Required Changes

Parse the time denominator. Require operating hours (default to hours in the reporting period) for "/hr" factors and multiply. Share one implementation between Tier 1 and Tier 3.

Implement through the shared fix for RC-4 (Units are not parsed / converted in one place) rather than a local patch.

## Database Changes

None required.

## Backend Changes

None beyond the above.

## Frontend Changes

None.

## Calculation Changes

Changes in `new/server/calculations/dispatcher.py`. **Data policy: new data only** — records already stored are NOT recalculated; the fix applies to new records and to records edited after the fix. Past reports keep their existing values.

## Tests To Add/Change

- Port `audit/repro/BUG-047.py` into a pytest regression test under `new/server/tests/` (assert the Expected value; independent hand-derived numbers, not a second call to the same function).
- Add edge cases: zero, missing, negative, NaN/Inf, boundary values for every field the fix touches.
- Add the group-level invariant tests for RC-4 (see Root-Cause Groups).
- Review existing tests that assert the old behaviour; change an expected value only when the new value is independently derived and documented in the test.

## Browser Verification

- API/backend fix. After the fix, open the page(s) that consume this data (see Affected Features) and confirm the displayed value matches the API and DB.

## Regression Risks

- A central unit parser changes results for every unit it now interprets correctly; stored records keep old values until a controlled recalculation. Unknown units that used to pass through will now be rejected.
- Correcting a formula changes every stored value computed by it. Stored records are NOT recomputed automatically — a controlled recalculation job with before/after diff and audit log is required, and reported totals for past periods will move.

## Acceptance Criteria

1. `audit/repro/BUG-047.py` exits 0 on the fixed code (it prints expected vs actual).
2. Expected behaviour holds: Annual (8,760 h): valves 10 × 4.36e-6 × 8760 = **0.3819 t CH4**; wellheads 10 × 1.8e-5 × 8760 = **1.577 t CH4**. Even for a one-month record (744 h) the values are 0.0324 t and 0.134 t.
3. Full backend suite (`python -m pytest tests/` in `new/server`) and frontend checks (`npm run lint`, `npm run test`) pass.
4. No other open bug's repro changes from fail→pass or pass→fail unexpectedly (re-run `audit/work/rerun/run_all.sh`).

---

# BUG-048 — Tier 3 fugitive calculators misread catalog factor units: "CH₄" (Unicode subscript) is not recognised as methane (×0.85 applied), and ComponentFugitiveCalculator treats tonne/hr factors as kg/hr (1000× too low)

**Severity:** High · **Category:** Calculation · **Phase:** P2 · **Root cause group:** RC-4 · **Found by:** Agent A (Calculation Engine Auditor)

**Current status:** **Still present** — `audit/repro/BUG-048.py` re-run on the final code: bug reproduced.

## Problem

Tier 3 fugitive calculators misread catalog factor units: "CH₄" (Unicode subscript) is not recognised as methane (×0.85 applied), and ComponentFugitiveCalculator treats tonne/hr factors as kg/hr (1000× too low)

- **Actual:** Wellheads `1.34028 t` (= × 0.85, −15 %). Valves `3.246e-4 t` (= × 0.85 / 1000, **1,176× too low**).
- **Expected:** Wellheads: 10 × 1.8e-5 t/h × 8760 = **1.5768 t CH4** (the factor is already CH4, so no gas fraction applies). Valves: 10 × 4.36e-6 t/h × 8760 = **0.3819 t CH4**.

## Root Cause

String matching on units does not normalise the Unicode subscript. The component calculator hard-codes kg.

## Affected Files

- `new/server/calculations/fugitive.py`

## Affected Features

Every Tier 3 equipment-level fugitive is 15 % low. Every Tier 3 component-level fugitive using catalog factors is about 1000× low.

## Required Changes

Normalise units before matching (map subscript digits to ASCII, strip spaces). Parse the numerator mass unit explicitly (t/kg/g/lb) in both calculators. Add regression tests with the real catalog strings.

Implement through the shared fix for RC-4 (Units are not parsed / converted in one place) rather than a local patch.

## Database Changes

None required.

## Backend Changes

None beyond the above.

## Frontend Changes

None.

## Calculation Changes

Changes in `new/server/calculations/fugitive.py`. **Data policy: new data only** — records already stored are NOT recalculated; the fix applies to new records and to records edited after the fix. Past reports keep their existing values.

## Tests To Add/Change

- Port `audit/repro/BUG-048.py` into a pytest regression test under `new/server/tests/` (assert the Expected value; independent hand-derived numbers, not a second call to the same function).
- Add edge cases: zero, missing, negative, NaN/Inf, boundary values for every field the fix touches.
- Add the group-level invariant tests for RC-4 (see Root-Cause Groups).
- Review existing tests that assert the old behaviour; change an expected value only when the new value is independently derived and documented in the test.

## Browser Verification

- API/backend fix. After the fix, open the page(s) that consume this data (see Affected Features) and confirm the displayed value matches the API and DB.

## Regression Risks

- A central unit parser changes results for every unit it now interprets correctly; stored records keep old values until a controlled recalculation. Unknown units that used to pass through will now be rejected.
- Correcting a formula changes every stored value computed by it. Stored records are NOT recomputed automatically — a controlled recalculation job with before/after diff and audit log is required, and reported totals for past periods will move.

## Acceptance Criteria

1. `audit/repro/BUG-048.py` exits 0 on the fixed code (it prints expected vs actual).
2. Expected behaviour holds: Wellheads: 10 × 1.8e-5 t/h × 8760 = **1.5768 t CH4** (the factor is already CH4, so no gas fraction applies). Valves: 10 × 4.36e-6 t/h × 8760 = **0.3819 t CH4**.
3. Full backend suite (`python -m pytest tests/` in `new/server`) and frontend checks (`npm run lint`, `npm run test`) pass.
4. No other open bug's repro changes from fail→pass or pass→fail unexpectedly (re-run `audit/work/rerun/run_all.sh`).

---

# BUG-049 — Generic factor math ignores the 10³ / 10⁶ multiplier in factor denominators: offshore gas fugitives 1,000,000× and refinery fuel-gas fugitives 1,000× overstated

**Severity:** High · **Category:** Calculation · **Phase:** P2 · **Root cause group:** RC-4 · **Found by:** Agent A (Calculation Engine Auditor)

**Current status:** **Still present** — `audit/repro/BUG-049.py` re-run on the final code: bug reproduced.

## Problem

Generic factor math ignores the 10³ / 10⁶ multiplier in factor denominators: offshore gas fugitives 1,000,000× and refinery fuel-gas fugitives 1,000× overstated

- **Actual:** Offshore `ch4_emissions = 52,000 t` (co2e 1,456,000 t). Refinery `18.75 t`. No unit choice gives the right answer: entering scf also multiplies by 1e6.
- **Expected:** Offshore: 5 MMscf × 0.0104 t/MMscf = **0.052 t CH4**. Refinery: 50 kbbl × 0.000375 = **0.01875 t CH4**.

## Root Cause

Denominator parsing takes the first unit-name substring and ignores numeric scale prefixes (10³, 10⁶, "per thousand").

## Affected Files

- `new/server/calculations/dispatcher.py`

## Affected Features

A single offshore gas facility-month can inject 10⁶ t CO2e into Scope 1. Refinery fuel-gas fugitives are 1000× high.

## Required Changes

Parse scale prefixes (10³/10⁶/k/M/MM) in denominators and divide accordingly. Better still, store factors in canonical units with an explicit denominator unit field.

Implement through the shared fix for RC-4 (Units are not parsed / converted in one place) rather than a local patch.

## Database Changes

None required.

## Backend Changes

None beyond the above.

## Frontend Changes

None.

## Calculation Changes

Changes in `new/server/calculations/dispatcher.py`. **Data policy: new data only** — records already stored are NOT recalculated; the fix applies to new records and to records edited after the fix. Past reports keep their existing values.

## Tests To Add/Change

- Port `audit/repro/BUG-049.py` into a pytest regression test under `new/server/tests/` (assert the Expected value; independent hand-derived numbers, not a second call to the same function).
- Add edge cases: zero, missing, negative, NaN/Inf, boundary values for every field the fix touches.
- Add the group-level invariant tests for RC-4 (see Root-Cause Groups).
- Review existing tests that assert the old behaviour; change an expected value only when the new value is independently derived and documented in the test.

## Browser Verification

- API/backend fix. After the fix, open the page(s) that consume this data (see Affected Features) and confirm the displayed value matches the API and DB.

## Regression Risks

- A central unit parser changes results for every unit it now interprets correctly; stored records keep old values until a controlled recalculation. Unknown units that used to pass through will now be rejected.
- Correcting a formula changes every stored value computed by it. Stored records are NOT recomputed automatically — a controlled recalculation job with before/after diff and audit log is required, and reported totals for past periods will move.

## Acceptance Criteria

1. `audit/repro/BUG-049.py` exits 0 on the fixed code (it prints expected vs actual).
2. Expected behaviour holds: Offshore: 5 MMscf × 0.0104 t/MMscf = **0.052 t CH4**. Refinery: 50 kbbl × 0.000375 = **0.01875 t CH4**.
3. Full backend suite (`python -m pytest tests/` in `new/server`) and frontend checks (`npm run lint`, `npm run test`) pass.
4. No other open bug's repro changes from fail→pass or pass→fail unexpectedly (re-run `audit/work/rerun/run_all.sh`).

---

# BUG-063 — Tier 2 custom factors whose unit is not "kg/<unit>" are misapplied (Manage Data form stores a bare activity unit): tonne factors ×1000 (×10⁶ with kg activity), no volume/mass conversion at all; unknown units such as kg/TJ or kg/GJ are applied 1:1

**Severity:** High · **Category:** Calculation · **Phase:** P2 · **Root cause group:** RC-4 · **Found by:** Agent C (Tier / Factor Auditor)

**Current status:** **Still present** — `audit/repro/BUG-063.py` re-run on the final code: bug reproduced.

## Problem

Tier 2 custom factors whose unit is not "kg/<unit>" are misapplied (Manage Data form stores a bare activity unit): tonne factors ×1000 (×10⁶ with kg activity), no volume/mass conversion at all; unknown units such as kg/TJ or kg/GJ are applied 1:1


## Root Cause

There is no canonical unit format for custom factors, and the calculator does not validate units. It parses the numerator from the text before "/", and treats a unit without a "/" as having no denominator. Units it does not recognise fall through unconverted, with no error.

## Affected Files

- `new/client/src/pages/ManageData.jsx`
- `new/server/calculations/dispatcher.py`
- `new/server/routes/custom_factors.py`

## Affected Features

Tier 2 emissions are wrong by factors of 35 up to 10⁶, depending on the unit chosen in the app's own Manage Data form. An IPCC-style factor (kg/TJ, kg/GJ) is off by 1000×, or is dimensionally meaningless without an error.

## Required Changes

- Store custom factors with an explicit numerator/denominator unit from a whitelist, and migrate bare units to `kg/<unit>`. - In the calculator, reject factor units it cannot convert to the activity unit instead of applying them 1:1. - Add GJ/TJ/MJ energy denominators, and require an HHV for energy ↔ volume conversion.

Implement through the shared fix for RC-4 (Units are not parsed / converted in one place) rather than a local patch.

## Database Changes

Custom factor numerator/denominator unit columns for new/edited factors; existing bare-unit factors are not migrated (data policy) — the calculator must reject, not guess, factors whose unit it cannot interpret.
 Ship as an Alembic migration (requires BUG-016).

## Backend Changes

Changes in `new/server/routes/custom_factors.py` as described above.

## Frontend Changes

Changes in `new/client/src/pages/ManageData.jsx` as described above.

## Calculation Changes

Changes in `new/server/calculations/dispatcher.py`. **Data policy: new data only** — records already stored are NOT recalculated; the fix applies to new records and to records edited after the fix. Past reports keep their existing values.

## Tests To Add/Change

- Port `audit/repro/BUG-063.py` into a pytest regression test under `new/server/tests/` (assert the Expected value; independent hand-derived numbers, not a second call to the same function).
- Add edge cases: zero, missing, negative, NaN/Inf, boundary values for every field the fix touches.
- Add the group-level invariant tests for RC-4 (see Root-Cause Groups).
- Review existing tests that assert the old behaviour; change an expected value only when the new value is independently derived and documented in the test.

## Browser Verification

- Reproduce the steps in AUDIT_FINDINGS.md on an isolated stack (`audit/tools/vite_audit.mjs` + backend on an audit DB copy) and confirm the Expected result on screen.
- Compare the UI value with the API response and the DB row for the same record; refresh and reopen the record.

## Regression Risks

- A central unit parser changes results for every unit it now interprets correctly; stored records keep old values until a controlled recalculation. Unknown units that used to pass through will now be rejected.
- Correcting a formula changes every stored value computed by it. Stored records are NOT recomputed automatically — a controlled recalculation job with before/after diff and audit log is required, and reported totals for past periods will move.

## Acceptance Criteria

1. `audit/repro/BUG-063.py` exits 0 on the fixed code (it prints expected vs actual).
2. Full backend suite (`python -m pytest tests/` in `new/server`) and frontend checks (`npm run lint`, `npm run test`) pass.
3. No other open bug's repro changes from fail→pass or pass→fail unexpectedly (re-run `audit/work/rerun/run_all.sh`).

---

# BUG-110 — Onshore fugitives "Tier 1: Facility-Level" form: the on-screen preview says 16,644 tCO2e but the saved record is 1.456 tCO2e — the server ignores the selected facility type and duration and books the facility count as a count of valves

**Severity:** High · **Category:** Emissions · **Phase:** P2 · **Root cause group:** RC-6 · **Found by:** Agent L (Browser) · **Independent confirmations:** 1

**Current status:** **Confirmed on the post-change code by the browser agent** (`audit/repro/BUG-110.mjs`); not re-run in the final pass (needs a live UI stack).

## Problem

Onshore fugitives "Tier 1: Facility-Level" form: the on-screen preview says 16,644 tCO2e but the saved record is 1.456 tCO2e — the server ignores the selected facility type and duration and books the facility count as a count of valves

- **Actual:** Saved record 763: `ch4 0.052 t, co2 0, totalCo2e 1.456 t, calculation_method server_fugitive_average` vs preview 16,644 t (591.3 t CH4 + 87.6 t CO2). Ratio ≈ 11,400×. The CO2 component shown in the preview is dropped entirely. The user sees the large preview, gets "Scope 1 entry added successfully", and the dashboard/inventory receive 1.456 t.
- **Expected:** The stored record matches what the form shows for the same inputs (whatever the correct factor math is, UI preview and server must use the same method, facility type and duration), and visible defaults are the values actually submitted.

## Root Cause

The facility-level Tier 1 method exists only in the client preview. The server's legacy fugitive branch has no facility-level method and silently falls back to "average component = valves × count". The client preview uses placeholder defaults that are not in the submitted state.

## Affected Files

- `new/client/src/components/scope1/FugitivesForm.jsx`
- `new/server/calculations/legacy_engine.py`

## Affected Features

The figure a user validates on screen is not what is recorded. Upstream fugitive methane — a key OGMP/methane-intensity input — is recorded orders of magnitude off with no warning, and the facility type/duration chosen are lost from the record.

## Required Changes

Implement the facility-level (Table 7-1/7-2) method on the server using `facility_type`, `facility_count` and duration, or post the preview inputs to a server preview endpoint so both use one implementation. Reject fugitive requests whose method/fields the server does not understand instead of defaulting to valves. Initialise `formData` with the displayed defaults.

Implement through the shared fix for RC-6 (Client and server hold separate copies of catalogs, constants and formulas) rather than a local patch.

## Database Changes

None required.

## Backend Changes

None beyond the above.

## Frontend Changes

Changes in `new/client/src/components/scope1/FugitivesForm.jsx` as described above.

## Calculation Changes

Changes in `new/server/calculations/legacy_engine.py`. **Data policy: new data only** — records already stored are NOT recalculated; the fix applies to new records and to records edited after the fix. Past reports keep their existing values.

## Tests To Add/Change

- Port `audit/repro/BUG-110.mjs` into a Playwright spec under `new/client/e2e/` (or a vitest test where it is pure component logic).
- Add edge cases: zero, missing, negative, NaN/Inf, boundary values for every field the fix touches.
- Add the group-level invariant tests for RC-6 (see Root-Cause Groups).
- Review existing tests that assert the old behaviour; change an expected value only when the new value is independently derived and documented in the test.

## Browser Verification

- Reproduce the steps in AUDIT_FINDINGS.md on an isolated stack (`audit/tools/vite_audit.mjs` + backend on an audit DB copy) and confirm the Expected result on screen.
- Compare the UI value with the API response and the DB row for the same record; refresh and reopen the record.

## Regression Risks

- Removing a client-side catalog/formula can remove options users rely on; every factor still offered must exist server-side before the switch. Previews will change to server-computed values.
- Correcting a formula changes every stored value computed by it. Stored records are NOT recomputed automatically — a controlled recalculation job with before/after diff and audit log is required, and reported totals for past periods will move.

## Acceptance Criteria

1. `audit/repro/BUG-110.mjs` exits 0 on the fixed code (it prints expected vs actual).
2. Expected behaviour holds: The stored record matches what the form shows for the same inputs (whatever the correct factor math is, UI preview and server must use the same method, facility type and duration), and visible defaults are the values actually submitted.
3. Full backend suite (`python -m pytest tests/` in `new/server`) and frontend checks (`npm run lint`, `npm run test`) pass.
4. No other open bug's repro changes from fail→pass or pass→fail unexpectedly (re-run `audit/work/rerun/run_all.sh`).

---

# BUG-090 — Dehydrator form sends "Contactor Pressure" as `dehy_pressure`, but the server reads `dehy_press`: user pressure silently ignored, 800 psig default always used (AGR "routed to flare"/"flash gas recycled" checkboxes also unread)

**Severity:** High · **Category:** UI · **Phase:** P2 · **Root cause group:** RC-6 · **Found by:** Agent K (Frontend/UI)

**Current status:** **Still present** — `audit/repro/BUG-090.py` re-run on the final code: bug reproduced.

## Problem

Dehydrator form sends "Contactor Pressure" as `dehy_pressure`, but the server reads `dehy_press`: user pressure silently ignored, 800 psig default always used (AGR "routed to flare"/"flash gas recycled" checkboxes also unread)

- **Actual:** POST body `calc_inputs.dehydrator = {..., "dehy_pressure": 200, ...}` → response CH4 1.30610 t, CO2e 36.571 t; with 1000 psig → identical 1.30610 t / 36.571 t (records 756/757). That is the 800 psig default. At 200 psig the stored CO2e is 3.6× the value the server would compute for the entered pressure. AGR: toggling "Acid Gas / Offgas Routed to Flare" and "Flash Gas Recycled" gives byte-identical results (2371.39 t CO2 / 16.331 t CH4).
- **Expected:** Different CH4 (the server calculator is pressure-sensitive: with `dehy_press` it returns 0.363 t CH4 at 200 psig and 1.613 t at 1000 psig).

## Root Cause

Field-name mismatch between the form (`dehy_pressure`) and the dispatcher (`dehy_press`/`contactor_pressure`); AGR checkbox keys have no server counterpart. No warning is shown for an ignored required input.

## Affected Files

- `new/client/src/components/scope1/AGRForm.jsx`
- `new/client/src/components/scope1/DehydratorForm.jsx`
- `new/server/calculations/dispatcher.py`

## Affected Features

Every UI-entered dehydrator record ignores the contactor pressure the user typed (marked required); AGR control options displayed to the user have no effect.

## Required Changes

Rename the form key to `dehy_press` (or accept `dehy_pressure` server-side); map the AGR checkboxes to `agr_control_type` / flash handling or remove them; reject/flag unknown calc_inputs keys.

Implement through the shared fix for RC-6 (Client and server hold separate copies of catalogs, constants and formulas) rather than a local patch.

## Database Changes

None required.

## Backend Changes

None beyond the above.

## Frontend Changes

Changes in `new/client/src/components/scope1/AGRForm.jsx`, `new/client/src/components/scope1/DehydratorForm.jsx` as described above.

## Calculation Changes

Changes in `new/server/calculations/dispatcher.py`. **Data policy: new data only** — records already stored are NOT recalculated; the fix applies to new records and to records edited after the fix. Past reports keep their existing values.

## Tests To Add/Change

- Port `audit/repro/BUG-090.py` into a pytest regression test under `new/server/tests/` (assert the Expected value; independent hand-derived numbers, not a second call to the same function).
- Add edge cases: zero, missing, negative, NaN/Inf, boundary values for every field the fix touches.
- Add the group-level invariant tests for RC-6 (see Root-Cause Groups).
- Review existing tests that assert the old behaviour; change an expected value only when the new value is independently derived and documented in the test.

## Browser Verification

- Reproduce the steps in AUDIT_FINDINGS.md on an isolated stack (`audit/tools/vite_audit.mjs` + backend on an audit DB copy) and confirm the Expected result on screen.
- Compare the UI value with the API response and the DB row for the same record; refresh and reopen the record.

## Regression Risks

- Removing a client-side catalog/formula can remove options users rely on; every factor still offered must exist server-side before the switch. Previews will change to server-computed values.
- Correcting a formula changes every stored value computed by it. Stored records are NOT recomputed automatically — a controlled recalculation job with before/after diff and audit log is required, and reported totals for past periods will move.

## Acceptance Criteria

1. `audit/repro/BUG-090.py` exits 0 on the fixed code (it prints expected vs actual).
2. Expected behaviour holds: Different CH4 (the server calculator is pressure-sensitive: with `dehy_press` it returns 0.363 t CH4 at 200 psig and 1.613 t at 1000 psig).
3. Full backend suite (`python -m pytest tests/` in `new/server`) and frontend checks (`npm run lint`, `npm run test`) pass.
4. No other open bug's repro changes from fail→pass or pass→fail unexpectedly (re-run `audit/work/rerun/run_all.sh`).

---


# PHASE P3 — Systemic calculation / business-logic defects

_Phase regression risk:_ Shared payload/persistence helpers touch every Scope 1 write path (create, PUT, import, bulk).

---

# BUG-003 — Editing a Scope 1 record's quantity via PUT /api/emissions/<id> does not recalculate emissions (stale `amount` from source_payload wins)

**Severity:** High · **Category:** Emissions · **Phase:** P3 · **Root cause group:** RC-5 · **Found by:** Agent B (Emissions Auditor)

**Current status:** **Still present** — `audit/repro/BUG-003.py` re-run on the final code: bug reproduced.

## Problem

Editing a Scope 1 record's quantity via PUT /api/emissions/<id> does not recalculate emissions (stale `amount` from source_payload wins)

- **Actual:** `quantity` = 2000.0 but `co2e_total` = **53.1145** (the value for 1000 MMBtu). The API returns 200 "Record updated". The stored row now says 2000 MMBtu but reports emissions for 1000 MMBtu; the saved `source_payload` then has `quantity:2000, amount:1000`.
- **Expected:** Hand calc (EPA NG 53.06 kg CO2/MMBtu, 1 g CH4, 0.1 g N2O, AR5 28/265): 2000 MMBtu -> 106.12 t CO2 + 0.002 t CH4 + 0.0002 t N2O = **106.229 tCO2e**, and `quantity`=2000.

## Root Cause

`recalc_keys` includes `quantity`, so recalculation runs. But the merged payload starts from the stored `source_payload`, which already has the old `amount`. `calc_payload.update({"quantity":2000})` leaves `amount` at 1000, and `compute_emissions` prefers `amount` over `quantity`. The same thing happens the other way round (fuel/fuel_type): a PUT of `fuel_type` leaves the old `fuel` in the payload. `_lookup_api_factor` uses the new fuel_type, but the dispatcher reads `inputs['fuel']`.

## Affected Files

- `new/server/calculations/legacy_engine.py`
- `new/server/routes/emissions.py`

## Affected Features

Any API/integration edit of activity quantity silently keeps the old emissions while showing the new quantity. The inventory and the audit trail disagree (the ActivityLog "after" state shows quantity 2000 with co2e 53.11). The record stays Verified for an admin.

## Required Changes

Canonicalise in `update_emission`: when `quantity` or `amount` is in `data`, set both `calc_payload["amount"]` and `calc_payload["quantity"]` to the new value (same for `fuel`/`fuel_type`) before calling `compute_emissions`.

Implement through the shared fix for RC-5 (Edit / recalculation path diverges from the create path) rather than a local patch.

## Database Changes

None required.

## Backend Changes

Changes in `new/server/routes/emissions.py` as described above.

## Frontend Changes

None.

## Calculation Changes

Changes in `new/server/calculations/legacy_engine.py`. **Data policy: new data only** — records already stored are NOT recalculated; the fix applies to new records and to records edited after the fix. Past reports keep their existing values.

## Tests To Add/Change

- Port `audit/repro/BUG-003.py` into a pytest regression test under `new/server/tests/` (assert the Expected value; independent hand-derived numbers, not a second call to the same function).
- Add edge cases: zero, missing, negative, NaN/Inf, boundary values for every field the fix touches.
- Add the group-level invariant tests for RC-5 (see Root-Cause Groups).
- Review existing tests that assert the old behaviour; change an expected value only when the new value is independently derived and documented in the test.

## Browser Verification

- API/backend fix. After the fix, open the page(s) that consume this data (see Affected Features) and confirm the displayed value matches the API and DB.

## Regression Risks

- Shared payload/persistence helpers touch every Scope 1 write path (create, PUT, import, bulk); edits to existing records will now produce different (correct) values than before.
- Correcting a formula changes every stored value computed by it. Stored records are NOT recomputed automatically — a controlled recalculation job with before/after diff and audit log is required, and reported totals for past periods will move.

## Acceptance Criteria

1. `audit/repro/BUG-003.py` exits 0 on the fixed code (it prints expected vs actual).
2. Expected behaviour holds: Hand calc (EPA NG 53.06 kg CO2/MMBtu, 1 g CH4, 0.1 g N2O, AR5 28/265): 2000 MMBtu -> 106.12 t CO2 + 0.002 t CH4 + 0.0002 t N2O = **106.229 tCO2e**, and `quantity`=2000.
3. Full backend suite (`python -m pytest tests/` in `new/server`) and frontend checks (`npm run lint`, `npm run test`) pass.
4. No other open bug's repro changes from fail→pass or pass→fail unexpectedly (re-run `audit/work/rerun/run_all.sh`).

---

# BUG-030 — POST /api/emissions/ calculates from `quantity`/`fuel_type` but stores only `amount`/`fuel`: records keep emissions with NULL activity quantity and fuel

**Severity:** Medium · **Category:** Emissions · **Phase:** P3 · **Root cause group:** RC-5 · **Found by:** Agent B (Emissions Auditor)

**Current status:** **Still present** — `audit/repro/BUG-030.py` re-run on the final code: bug reproduced.

## Problem

POST /api/emissions/ calculates from `quantity`/`fuel_type` but stores only `amount`/`fuel`: records keep emissions with NULL activity quantity and fuel

- **Actual:** co2e_total = 2582.96 t (correct), but `fuel_type=NULL` and `quantity=NULL` (row id 752 in agentB db). Sending the same payload with `fuel`/`amount` stores both fields.
- **Expected:** `fuel_type='Coal'`, `quantity=1000`, co2e = 2582.96 t. Hand check: 1000 t x 1.10231 st/t x 24.93 MMBtu/st x 93.28 kg/MMBtu = 2563.4 t CO2, plus CH4/N2O.

## Root Cause

Key-name mismatch between the fields used for the calculation (either alias accepted) and the fields persisted (only `amount`/`fuel`).

## Affected Files

- `new/server/routes/emissions.py`

## Affected Features

Verified emissions with no stored activity data or fuel. Reviewers cannot see or verify what was entered, activity-based QA and outlier checks cannot see the quantity, and fuel-level breakdowns and exports drop these rows into "blank".

## Required Changes

Persist `fuel_type=data.get("fuel") or data.get("fuel_type")` and `quantity=` the same parsed `amount`/`quantity` value that `compute_emissions` used.

Implement through the shared fix for RC-5 (Edit / recalculation path diverges from the create path) rather than a local patch.

## Database Changes

None required.

## Backend Changes

Changes in `new/server/routes/emissions.py` as described above.

## Frontend Changes

None.

## Calculation Changes

None.

## Tests To Add/Change

- Port `audit/repro/BUG-030.py` into a pytest regression test under `new/server/tests/` (assert the Expected value; independent hand-derived numbers, not a second call to the same function).
- Add edge cases: zero, missing, negative, NaN/Inf, boundary values for every field the fix touches.
- Add the group-level invariant tests for RC-5 (see Root-Cause Groups).
- Review existing tests that assert the old behaviour; change an expected value only when the new value is independently derived and documented in the test.

## Browser Verification

- API/backend fix. After the fix, open the page(s) that consume this data (see Affected Features) and confirm the displayed value matches the API and DB.

## Regression Risks

- Shared payload/persistence helpers touch every Scope 1 write path (create, PUT, import, bulk); edits to existing records will now produce different (correct) values than before.

## Acceptance Criteria

1. `audit/repro/BUG-030.py` exits 0 on the fixed code (it prints expected vs actual).
2. Expected behaviour holds: `fuel_type='Coal'`, `quantity=1000`, co2e = 2582.96 t. Hand check: 1000 t x 1.10231 st/t x 24.93 MMBtu/st x 93.28 kg/MMBtu = 2563.4 t CO2, plus CH4/N2O.
3. Full backend suite (`python -m pytest tests/` in `new/server`) and frontend checks (`npm run lint`, `npm run test`) pass.
4. No other open bug's repro changes from fail→pass or pass→fail unexpectedly (re-run `audit/work/rerun/run_all.sh`).

---

# BUG-037 — Editing a Scope 1 record replaces its propagated 1σ uncertainty with the raw catalog EF half-width (95 %, EF-only); user_uncertainty is stored unpropagated

**Severity:** High · **Category:** Uncertainty · **Phase:** P3 · **Root cause group:** RC-5, RC-8 · **Found by:** Agent G (Uncertainty Auditor)

**Current status:** **Still present** — `audit/repro/BUG-037.py` re-run on the final code: bug reproduced.

## Problem

Editing a Scope 1 record replaces its propagated 1σ uncertainty with the raw catalog EF half-width (95 %, EF-only); user_uncertainty is stored unpropagated

- **Actual:** - After POST: (0.0559, 0.1118, 0.1118). Dashboard ±22.36 %. - After PUT: **(0.05, 0.20, 0.20)**. Dashboard **±40.0 %**, with CO2e unchanged. - user_uncertainty 50 %: POST stores 0.2550, PUT stores **0.5000**. The dashboard then shows ±100 %.
- **Expected:** Stored values are unchanged by a no-op recalculation. By hand, u_CO2 (1σ) = √(0.025² + 0.05²) = 0.0559 and u_CH4 = u_N2O = 0.1118. The same holds for `user_uncertainty co2=50 %`: POST stores √(0.25² + 0.05²) = 0.2550, and PUT should store the same.

## Root Cause

Two code paths persist different quantities in the same column. The POST/bulk paths store the 1σ combined EF+AD value from `propagate_uncertainty`. The PUT and `/import` paths store the unpropagated 95 % EF-only half-width, which omits the AD term and the /k conversion. Consumers then apply k=2 again.

## Affected Files

- `new/server/routes/emissions.py`

## Affected Features

Any edit, including a no-op recalculation, changes a record's reported uncertainty with no change in data. The reported 95 % interval roughly doubles for EF-dominated gases (0.05 read as 1σ is 10 % at 95 %, against the correct 11.18 %; 0.20 read as 1σ is 40 %, against the correct 22.4 %). User-supplied uncertainties are doubled. Persisted values mix two incompatible semantics, which corrupts the Uncertainty page, the CSV/PDF outputs and CalculationDetails.

## Required Changes

In `update_emission` and `import_emissions`, persist `calculated_em["_full_api_res"]["results"][gas]["uncertainty"]`, as `add_emission` does, and drop the post-hoc `user_uncertainty/100` override (the dispatcher already propagates it). Back-fill the existing rows by recomputing them.

Implement through the shared fix for RC-5 (Edit / recalculation path diverges from the create path), RC-8 (Uncertainty aggregation model) rather than a local patch.

## Database Changes

None required.

## Backend Changes

Changes in `new/server/routes/emissions.py` as described above.

## Frontend Changes

None.

## Calculation Changes

None.

## Tests To Add/Change

- Port `audit/repro/BUG-037.py` into a pytest regression test under `new/server/tests/` (assert the Expected value; independent hand-derived numbers, not a second call to the same function).
- Add edge cases: zero, missing, negative, NaN/Inf, boundary values for every field the fix touches.
- Add the group-level invariant tests for RC-5, RC-8 (see Root-Cause Groups).
- Review existing tests that assert the old behaviour; change an expected value only when the new value is independently derived and documented in the test.

## Browser Verification

- API/backend fix. After the fix, open the page(s) that consume this data (see Affected Features) and confirm the displayed value matches the API and DB.

## Regression Risks

- Shared payload/persistence helpers touch every Scope 1 write path (create, PUT, import, bulk); edits to existing records will now produce different (correct) values than before.
- Reported uncertainty percentages will change materially (some up, some down); QA and Uncertainty pages must switch together.

## Acceptance Criteria

1. `audit/repro/BUG-037.py` exits 0 on the fixed code (it prints expected vs actual).
2. Expected behaviour holds: Stored values are unchanged by a no-op recalculation. By hand, u_CO2 (1σ) = √(0.025² + 0.05²) = 0.0559 and u_CH4 = u_N2O = 0.1118. The same holds for `user_uncertainty co2=50 %`: POST stores √(0.25² + 0.05²) = 0.2550, and PUT should store the same.
3. Full backend suite (`python -m pytest tests/` in `new/server`) and frontend checks (`npm run lint`, `npm run test`) pass.
4. No other open bug's repro changes from fail→pass or pass→fail unexpectedly (re-run `audit/work/rerun/run_all.sh`).

---

# BUG-042 — Recalculating a Tier 2 (custom-factor) Scope 1 record drops the custom factor: emissions become 0 or silently switch to the catalog factor, while factor_source stays "custom"

**Severity:** High · **Category:** Emissions · **Phase:** P3 · **Root cause group:** RC-5 · **Found by:** Agent C (Tier / Factor Auditor)

**Current status:** **Still present** — `audit/repro/BUG-042.py` re-run on the final code: bug reproduced.

## Problem

Recalculating a Tier 2 (custom-factor) Scope 1 record drops the custom factor: emissions become 0 or silently switch to the catalog factor, while factor_source stays "custom"

- **Actual:** - The record becomes co2 = 0, ch4 = 0, co2e_total = 0, with calc_method `server_default` and factor_source still `custom`. HTTP 200. - If the record's fuel is a catalog name (API/bulk path, e.g. `fuel="Natural Gas"`), the recalculation silently switches to the Tier 1 catalog factor instead. In the test, 2.0 t became 1.911 t (53.06 kg/MMBtu × 1020 Btu/scf). The record still claims Tier 2, and its uncertainty is replaced by the catalog's 0.05.
- **Expected:** Recalculation re-applies the record's custom factor: 2.0 t CO2 and 0.01 t CH4 (2.28 t CO2e at AR5).

## Root Cause

The update route rebuilds `factor_data` only from the request body. The custom factor linkage (`custom_factor_id` in `source_payload`) is ignored. The fallback lookup by `fuel_type` (the custom factor id as a string) finds nothing, and a missing factor is treated as 0.

## Affected Files

- `new/server/routes/emissions.py`

## Affected Features

Any API/ERP edit or recalculation of a Tier 2 record zeroes it, or re-tiers it to catalog defaults without notice. Records edited by an admin stay `Verified`. The tier label ("custom") no longer matches the factor applied, which breaks audit traceability.

## Required Changes

- On recalculation, resolve `custom_factor_id` from the request, else from `source_payload`, and fail if the factor no longer exists. - Never fall back to the catalog, or to 0, for a record whose `factor_source` is `custom`.

Implement through the shared fix for RC-5 (Edit / recalculation path diverges from the create path) rather than a local patch.

## Database Changes

None required.

## Backend Changes

Changes in `new/server/routes/emissions.py` as described above.

## Frontend Changes

None.

## Calculation Changes

None.

## Tests To Add/Change

- Port `audit/repro/BUG-042.py` into a pytest regression test under `new/server/tests/` (assert the Expected value; independent hand-derived numbers, not a second call to the same function).
- Add edge cases: zero, missing, negative, NaN/Inf, boundary values for every field the fix touches.
- Add the group-level invariant tests for RC-5 (see Root-Cause Groups).
- Review existing tests that assert the old behaviour; change an expected value only when the new value is independently derived and documented in the test.

## Browser Verification

- API/backend fix. After the fix, open the page(s) that consume this data (see Affected Features) and confirm the displayed value matches the API and DB.

## Regression Risks

- Shared payload/persistence helpers touch every Scope 1 write path (create, PUT, import, bulk); edits to existing records will now produce different (correct) values than before.

## Acceptance Criteria

1. `audit/repro/BUG-042.py` exits 0 on the fixed code (it prints expected vs actual).
2. Expected behaviour holds: Recalculation re-applies the record's custom factor: 2.0 t CO2 and 0.01 t CH4 (2.28 t CO2e at AR5).
3. Full backend suite (`python -m pytest tests/` in `new/server`) and frontend checks (`npm run lint`, `npm run test`) pass.
4. No other open bug's repro changes from fail→pass or pass→fail unexpectedly (re-run `audit/work/rerun/run_all.sh`).

---

# BUG-068 — Purchased steam/heat (`indirect_steam`) and CHP allocation (`cogen_allocation`) are accepted as Scope 1 process types and added to Scope 1 totals (Scope 2 counted as Scope 1; CHP double counting)

**Severity:** High · **Category:** Emissions · **Phase:** P3 · **Root cause group:** — · **Found by:** Agent B (Emissions Auditor)

**Current status:** **Still present** — `audit/repro/BUG-068.py` re-run on the final code: bug reproduced.

## Problem

Purchased steam/heat (`indirect_steam`) and CHP allocation (`cogen_allocation`) are accepted as Scope 1 process types and added to Scope 1 totals (Scope 2 counted as Scope 1; CHP double counting)

- **Actual:** - `summary` → `scope1_total: 53.1145, other: 53.1145, scope2_total: 0` (`audit/work/B/t7.py` + `t8.py`). The purchased steam is booked as **Scope 1**. - It was also computed as plain fuel combustion (`calc_method api2021_generic`): boiler efficiency was ignored, and CH4/N2O were added. - `cogen_allocation` entered through the Scope 1 route is stored in Scope 1 too. The snapshot contains 4 such Pending rows (ids 620-623, "total_emissions 1000 tCO2e", allocated 346.6-562.5 t each, 2034 t in total). These would be added to Scope 1 on approval, on top of the CHP's fuel combustion, which is double…
- **Expected:** Purchased steam/heat is Scope 2 (GHG Protocol Scope 2 Guidance). It should be stored in `scope2_emissions` via /api/scope2, which has a dedicated `indirect_steam` path. Hand calc: 1000 / 0.8 x 53.06 kg = **66.33 t CO2, reported as Scope 2**, with Scope 1 unchanged. A CHP owned by the reporter is Scope 1 in full, via its fuel combustion. The heat-share allocation is not an additional Scope 1 emission.

## Root Cause

Scope is implied only by which table a row lands in. The Scope 1 create and bulk paths accept Scope 2 process types (documented as Scope 1 in the template and UI), and the aggregations never exclude them.

## Affected Files

- `new/server/routes/emissions.py`

## Affected Features

Scope 1 is overstated and Scope 2 understated for any site recording purchased steam or CHP allocation through the Scope 1 forms or template. With the Scope 2 form also used, emissions are double counted. SBTi, intensity and report splits by scope are wrong.

## Required Changes

Reject `indirect_steam`, `cogen_allocation` and `cogen` in Scope 1 create, PUT and bulk, or redirect them to `scope2_emissions`. Remove them from the Scope 1 process list and template. Exclude any legacy rows with these process types from Scope 1 aggregates.

## Database Changes

None required.

## Backend Changes

Changes in `new/server/routes/emissions.py` as described above.

## Frontend Changes

None.

## Calculation Changes

None.

## Tests To Add/Change

- Port `audit/repro/BUG-068.py` into a pytest regression test under `new/server/tests/` (assert the Expected value; independent hand-derived numbers, not a second call to the same function).
- Add edge cases: zero, missing, negative, NaN/Inf, boundary values for every field the fix touches.
- Review existing tests that assert the old behaviour; change an expected value only when the new value is independently derived and documented in the test.

## Browser Verification

- API/backend fix. After the fix, open the page(s) that consume this data (see Affected Features) and confirm the displayed value matches the API and DB.

## Regression Risks

- Shared payload/persistence helpers touch every Scope 1 write path (create, PUT, import, bulk).

## Acceptance Criteria

1. `audit/repro/BUG-068.py` exits 0 on the fixed code (it prints expected vs actual).
2. Expected behaviour holds: Purchased steam/heat is Scope 2 (GHG Protocol Scope 2 Guidance). It should be stored in `scope2_emissions` via /api/scope2, which has a dedicated `indirect_steam` path. Hand calc: 1000 / 0.8 x 53.06 kg = **66.33 t CO2, reported as Scope 2**, with Scope 1 unchanged. A CHP owned by the reporter is Scope 1 in full, via its fuel combustion. The heat-share allocation is not an additional Scope 1 emiss…
3. Full backend suite (`python -m pytest tests/` in `new/server`) and frontend checks (`npm run lint`, `npm run test`) pass.
4. No other open bug's repro changes from fail→pass or pass→fail unexpectedly (re-run `audit/work/rerun/run_all.sh`).

---

# BUG-024 — Tier 3 flaring/combustion renormalises the gas composition without N2 (and without unspecified components), inflating CH4 and CO2 by 1/(1 − x_inert)

**Severity:** Medium · **Category:** Calculation · **Phase:** P3 · **Root cause group:** — · **Found by:** Agent A (Calculation Engine Auditor)

**Current status:** **Not reproduced on the final code** — `audit/repro/BUG-024.py` exited 0. Likely fixed by code changes made during the audit; confirm and close.

## Problem

Tier 3 flaring/combustion renormalises the gas composition without N2 (and without unspecified components), inflating CH4 and CO2 by 1/(1 − x_inert)

- **Actual:** `ch4_emissions = 0.013570 t`, `co2_emissions = 1.831224 t`. Both are **+11.1 %**: the gas was renormalised to 100 % CH4.
- **Expected:** CH4 = 1000 × 0.90 × (1 − 0.98) × 0.6785 kg/m³ = **0.012213 t**. CO2 = 1000 × 0.90 × 1 × 0.984 × 1.861 kg/m³ = **1.6481 t**.

## Root Cause

Normalisation to 1.0 uses only C1–C10 and CO2. N2, H2S and any unspecified components are dropped, and the composition is forced to sum to 1.

## Affected Files

- `new/server/calculations/combustion.py`

## Affected Features

Flared and combusted CH4 and CO2 are overstated in proportion to the inert/unspecified fraction. The typical range is 2–15 %, and more for high-N2 associated gas.

## Required Changes

Include N2 (and other inerts) in the sum. Renormalise only when the analysis is complete (sum close to 100 %, within a tolerance). Otherwise use the stated mole fractions as given, and warn.

## Database Changes

None required.

## Backend Changes

None beyond the above.

## Frontend Changes

None.

## Calculation Changes

Changes in `new/server/calculations/combustion.py`. **Data policy: new data only** — records already stored are NOT recalculated; the fix applies to new records and to records edited after the fix. Past reports keep their existing values.

## Tests To Add/Change

- Port `audit/repro/BUG-024.py` into a pytest regression test under `new/server/tests/` (assert the Expected value; independent hand-derived numbers, not a second call to the same function).
- Add edge cases: zero, missing, negative, NaN/Inf, boundary values for every field the fix touches.
- Review existing tests that assert the old behaviour; change an expected value only when the new value is independently derived and documented in the test.

## Browser Verification

- API/backend fix. After the fix, open the page(s) that consume this data (see Affected Features) and confirm the displayed value matches the API and DB.

## Regression Risks

- Shared payload/persistence helpers touch every Scope 1 write path (create, PUT, import, bulk).
- Correcting a formula changes every stored value computed by it. Stored records are NOT recomputed automatically — a controlled recalculation job with before/after diff and audit log is required, and reported totals for past periods will move.

## Acceptance Criteria

1. `audit/repro/BUG-024.py` exits 0 on the fixed code (it prints expected vs actual).
2. Expected behaviour holds: CH4 = 1000 × 0.90 × (1 − 0.98) × 0.6785 kg/m³ = **0.012213 t**. CO2 = 1000 × 0.90 × 1 × 0.984 × 1.861 kg/m³ = **1.6481 t**.
3. Full backend suite (`python -m pytest tests/` in `new/server`) and frontend checks (`npm run lint`, `npm run test`) pass.
4. No other open bug's repro changes from fail→pass or pass→fail unexpectedly (re-run `audit/work/rerun/run_all.sh`).

---

# BUG-051 — Energy activity units kWh / MJ / Btu with a kg/MMBtu factor are treated as scf of gas (× 1020 Btu/scf): 1000 kWh of natural gas is 3.3× too low, MJ 7.6 % too high

**Severity:** Medium · **Category:** Calculation · **Phase:** P3 · **Root cause group:** RC-4 · **Found by:** Agent A (Calculation Engine Auditor)

**Current status:** **Still present** — `audit/repro/BUG-051.py` re-run on the final code: bug reproduced.

## Problem

Energy activity units kWh / MJ / Btu with a kg/MMBtu factor are treated as scf of gas (× 1020 Btu/scf): 1000 kWh of natural gas is 3.3× too low, MJ 7.6 % too high

- **Actual:** kWh → `0.054121 t` (0.30×). MJ → `54.121 t` (1.076×). Both are computed as if the number were scf × 1020 Btu/scf.
- **Expected:** 1000 kWh = 3.412142 MMBtu × 53.06 = **0.18105 t CO2**. 1,000,000 MJ = 947.817 MMBtu × 53.06 = **50.29 t CO2** (as the app correctly returns for 1000 GJ).

## Root Cause

Energy units are hard-coded to a short list, and the fallback silently assumes a gas volume.

## Affected Files

- `new/server/calculations/combustion.py`

## Affected Features

Fuel reported by energy in kWh, MWh, MJ or Btu (common for metered gas and for purchased-fuel invoices) gives wrong CO2/CH4/N2O.

## Required Changes

Convert all energy units through `ENERGY_UNITS_TO_MJ`. Raise an error for unrecognised units instead of assuming scf.

Implement through the shared fix for RC-4 (Units are not parsed / converted in one place) rather than a local patch.

## Database Changes

None required.

## Backend Changes

None beyond the above.

## Frontend Changes

None.

## Calculation Changes

Changes in `new/server/calculations/combustion.py`. **Data policy: new data only** — records already stored are NOT recalculated; the fix applies to new records and to records edited after the fix. Past reports keep their existing values.

## Tests To Add/Change

- Port `audit/repro/BUG-051.py` into a pytest regression test under `new/server/tests/` (assert the Expected value; independent hand-derived numbers, not a second call to the same function).
- Add edge cases: zero, missing, negative, NaN/Inf, boundary values for every field the fix touches.
- Add the group-level invariant tests for RC-4 (see Root-Cause Groups).
- Review existing tests that assert the old behaviour; change an expected value only when the new value is independently derived and documented in the test.

## Browser Verification

- API/backend fix. After the fix, open the page(s) that consume this data (see Affected Features) and confirm the displayed value matches the API and DB.

## Regression Risks

- A central unit parser changes results for every unit it now interprets correctly; stored records keep old values until a controlled recalculation. Unknown units that used to pass through will now be rejected.
- Correcting a formula changes every stored value computed by it. Stored records are NOT recomputed automatically — a controlled recalculation job with before/after diff and audit log is required, and reported totals for past periods will move.

## Acceptance Criteria

1. `audit/repro/BUG-051.py` exits 0 on the fixed code (it prints expected vs actual).
2. Expected behaviour holds: 1000 kWh = 3.412142 MMBtu × 53.06 = **0.18105 t CO2**. 1,000,000 MJ = 947.817 MMBtu × 53.06 = **50.29 t CO2** (as the app correctly returns for 1000 GJ).
3. Full backend suite (`python -m pytest tests/` in `new/server`) and frontend checks (`npm run lint`, `npm run test`) pass.
4. No other open bug's repro changes from fail→pass or pass→fail unexpectedly (re-run `audit/work/rerun/run_all.sh`).

---

# BUG-050 — Negative activity amounts are accepted for process types that are not in the dispatcher (e.g. "loading") and saved as negative emissions

**Severity:** Medium · **Category:** Calculation · **Phase:** P3 · **Root cause group:** RC-1 · **Found by:** Agent A (Calculation Engine Auditor)

**Current status:** **Still present** — `audit/repro/BUG-050.py` re-run on the final code: bug reproduced.

## Problem

Negative activity amounts are accepted for process types that are not in the dispatcher (e.g. "loading") and saved as negative emissions

- **Actual:** HTTP 201. Stored `ch4_emissions = -0.16`, `co2e_total = -4.48`, `quantity = -1000000`, status Verified (admin).
- **Expected:** HTTP 422 (negative activity), as returned for dispatcher processes (e.g. `separation` → "Quantity/Amount cannot be negative").

## Root Cause

Input validation is applied only on the calculator path and only to the `quantity` key.

## Affected Files

- `new/server/calculations/dispatcher.py`
- `new/server/routes/emissions.py`

## Affected Features

Negative records silently offset real emissions in totals (API and bulk callers). The same path does no NaN/Inf check for unknown process types.

## Required Changes

Validate `amount` and `quantity` (finite, ≥ 0) in the route. Move the dispatcher's quantity validation above the `if not calculator` early return.

Implement through the shared fix for RC-1 (No central input validation) rather than a local patch.

## Database Changes

None required.

## Backend Changes

Changes in `new/server/routes/emissions.py` as described above.

## Frontend Changes

None.

## Calculation Changes

Changes in `new/server/calculations/dispatcher.py`. **Data policy: new data only** — records already stored are NOT recalculated; the fix applies to new records and to records edited after the fix. Past reports keep their existing values.

## Tests To Add/Change

- Port `audit/repro/BUG-050.py` into a pytest regression test under `new/server/tests/` (assert the Expected value; independent hand-derived numbers, not a second call to the same function).
- Add edge cases: zero, missing, negative, NaN/Inf, boundary values for every field the fix touches.
- Add the group-level invariant tests for RC-1 (see Root-Cause Groups).
- Review existing tests that assert the old behaviour; change an expected value only when the new value is independently derived and documented in the test.

## Browser Verification

- API/backend fix. After the fix, open the page(s) that consume this data (see Affected Features) and confirm the displayed value matches the API and DB.

## Regression Risks

- Stricter validation will reject inputs accepted today (existing bulk templates, integrations, scripts). Existing invalid rows remain until a cleanup job runs.
- Correcting a formula changes every stored value computed by it. Stored records are NOT recomputed automatically — a controlled recalculation job with before/after diff and audit log is required, and reported totals for past periods will move.

## Acceptance Criteria

1. `audit/repro/BUG-050.py` exits 0 on the fixed code (it prints expected vs actual).
2. Expected behaviour holds: HTTP 422 (negative activity), as returned for dispatcher processes (e.g. `separation` → "Quantity/Amount cannot be negative").
3. Full backend suite (`python -m pytest tests/` in `new/server`) and frontend checks (`npm run lint`, `npm run test`) pass.
4. No other open bug's repro changes from fail→pass or pass→fail unexpectedly (re-run `audit/work/rerun/run_all.sh`).

---

# BUG-013 — AR5 20-year GWPs are wrong (CH4 82.5 instead of 84, N2O 268 instead of 264); AR6 pairs the fossil CH4 GWP-20 with the non-fossil-weighted GWP-100

**Severity:** Medium · **Category:** Methane · **Phase:** P3 · **Root cause group:** RC-6 · **Found by:** Agent D (Methane Auditor) · **Independent confirmations:** 1

**Current status:** **Still present** — `audit/repro/BUG-013.py` re-run on the final code: bug reproduced.

## Problem

AR5 20-year GWPs are wrong (CH4 82.5 instead of 84, N2O 268 instead of 264); AR6 pairs the fossil CH4 GWP-20 with the non-fossil-weighted GWP-100

- **Actual:** - AR5: 1 t CH4 gives 82.5 tCO2e (−1.8 %); 1 t N2O gives 268 tCO2e (+1.5 %). - AR6: 27.9 is paired with 82.5, so the 100-yr and 20-yr figures come from different CH4 categories. - The UI tooltip tells users 84 is used.
- **Expected:** IPCC AR5 WG1 Table 8.7 (without climate-carbon feedback, the set whose GWP-100 values 28 / 265 the app uses): - CH4: GWP-20 = 84, GWP-100 = 28 - N2O: GWP-20 = 264, GWP-100 = 265 IPCC AR6 WG1 Table 7.15: - CH4, fossil: GWP-20 = 82.5, GWP-100 = 29.8 - CH4, non-fossil: GWP-20 = 80.8, GWP-100 = 27.2 - The app's AR6 GWP-100 of 27.9 is the generic CH4 value, whose matching GWP-20 is 81.2. For 1 t CH4 under AR5: expected 84 tCO2e (GWP-20); for 1 t N2O: 264 tCO2e.

## Root Cause

Wrong literals in the GWP table (82.5 is the AR6 fossil-CH4 GWP-20, copied into AR5; 268 matches no AR5 table value), mirrored into the client constants.

## Affected Files

- `new/client/src/constants.js`
- `new/server/calculations/constants.py`

## Affected Features

With the GWP-20 toggle under the default AR5 standard, every methane CO2e is understated by 1.5 tCO2e per tCH4. For the snapshot's 84.3 Mt Verified CH4 that is ≈126 MtCO2e. The GWP-20 hero total, categorical breakdown, intensity (co2_intensity_gwp20), Settings table and Reports "20yr" option all use these values.

## Required Changes

Set AR5 `CH4_20 = 84`, `N2O_20 = 264`. For AR6, use a consistent CH4 pair (27.9 / 81.2, or fossil 29.8 / 82.5 by source category). Keep constants.js, Settings.jsx and auth.py in sync, and make the tooltip read from the active constants.

Implement through the shared fix for RC-6 (Client and server hold separate copies of catalogs, constants and formulas) rather than a local patch.

## Database Changes

None required.

## Backend Changes

None beyond the above.

## Frontend Changes

Changes in `new/client/src/constants.js` as described above.

## Calculation Changes

Changes in `new/server/calculations/constants.py`. **Data policy: new data only** — records already stored are NOT recalculated; the fix applies to new records and to records edited after the fix. Past reports keep their existing values.

## Tests To Add/Change

- Port `audit/repro/BUG-013.py` into a pytest regression test under `new/server/tests/` (assert the Expected value; independent hand-derived numbers, not a second call to the same function).
- Add edge cases: zero, missing, negative, NaN/Inf, boundary values for every field the fix touches.
- Add the group-level invariant tests for RC-6 (see Root-Cause Groups).
- Review existing tests that assert the old behaviour; change an expected value only when the new value is independently derived and documented in the test.

## Browser Verification

- Reproduce the steps in AUDIT_FINDINGS.md on an isolated stack (`audit/tools/vite_audit.mjs` + backend on an audit DB copy) and confirm the Expected result on screen.
- Compare the UI value with the API response and the DB row for the same record; refresh and reopen the record.

## Regression Risks

- Removing a client-side catalog/formula can remove options users rely on; every factor still offered must exist server-side before the switch. Previews will change to server-computed values.
- Correcting a formula changes every stored value computed by it. Stored records are NOT recomputed automatically — a controlled recalculation job with before/after diff and audit log is required, and reported totals for past periods will move.

## Acceptance Criteria

1. `audit/repro/BUG-013.py` exits 0 on the fixed code (it prints expected vs actual).
2. Expected behaviour holds: IPCC AR5 WG1 Table 8.7 (without climate-carbon feedback, the set whose GWP-100 values 28 / 265 the app uses): - CH4: GWP-20 = 84, GWP-100 = 28 - N2O: GWP-20 = 264, GWP-100 = 265 IPCC AR6 WG1 Table 7.15: - CH4, fossil: GWP-20 = 82.5, GWP-100 = 29.8 - CH4, non-fossil: GWP-20 = 80.8, GWP-100 = 27.2 - The app's AR6 GWP-100 of 27.9 is the generic CH4 value, whose matching GWP-20 is 81.2. For 1 t CH4 u…
3. Full backend suite (`python -m pytest tests/` in `new/server`) and frontend checks (`npm run lint`, `npm run test`) pass.
4. No other open bug's repro changes from fail→pass or pass→fail unexpectedly (re-run `audit/work/rerun/run_all.sh`).

---

# BUG-005 — GWP-20 conversion in intensity-stats / intensity-trend hard-codes AR5 GWP-100 (28 / 265), so GWP-20 CO2e is wrong whenever the active standard is AR4 or AR6

**Severity:** Medium · **Category:** Methane · **Phase:** P3 · **Root cause group:** RC-6 · **Found by:** Agent D (Methane Auditor)

**Current status:** **Still present** — `audit/repro/BUG-005.py` re-run on the final code: bug reproduced.

## Problem

GWP-20 conversion in intensity-stats / intensity-trend hard-codes AR5 GWP-100 (28 / 265), so GWP-20 CO2e is wrong whenever the active standard is AR4 or AR6

- **Actual:** - `/summary` (hero card): 5,736,270,170.28 (2021) and 2,423,600.75 (2023). These are correct. - `/intensity-stats` Σ total_scope1_gwp20: **5,697,952,104** (2021, −38.3 Mt, −0.67 %) and **2,406,187.46** (2023, −17.4 kt, −0.72 %). Under AR4 the code applies CH4·44 + N2O·24 instead of CH4·47 − N2O·9. Under AR6 it applies CH4·54.5 + N2O·8 instead of CH4·54.6 + N2O·0; the 2023 overstatement is 187.7 t.
- **Expected:** GWP-20 CO2e = CO2 + CH4·GWP20_CH4 + N2O·GWP20_N2O for the active standard. Equivalently, the delta applied to the stored GWP-100 total must be CH4·(GWP20_CH4 − GWP100_CH4_active) + N2O·(GWP20_N2O − GWP100_N2O_active). For AR4 that is CH4·47 − N2O·9. - 2021: 5,736,270,170 tCO2e - 2023: 2,423,600.75 tCO2e

## Root Cause

The 100-year base in the GWP-20 delta is the literal AR5 value (28 / 265), not `get_active_gwp(horizon="100")`. `recalculate_all_emissions_gwp()` restates stored `co2e_total` with the active standard's GWP-100, so the literal subtraction no longer matches the stored basis.

## Affected Files

- `new/server/routes/dashboard.py`

## Affected Features

With AR4 or AR6 selected, every GWP-20 value derived from intensity-stats or intensity-trend is wrong. That covers `co2_intensity_gwp20`, `scope1_intensity_gwp20`, `total_co2e_gwp20` and `total_scope1_gwp20`: the dashboard Performance Intensity KPI in GWP-20 mode, Carbon/Methane intensity pages and trend charts. They then disagree with the dashboard hero total, which is computed correctly.

## Required Changes

Use `gwp100 = get_active_gwp(horizon="100")` and compute `delta = ch4*(g20["CH4"]-g100["CH4"]) + n2o*(g20["N2O"]-g100["N2O"])`, or better, compute GWP-20 directly as CO2 + CH4·g20 + N2O·g20. Share one helper across all four call sites.

Implement through the shared fix for RC-6 (Client and server hold separate copies of catalogs, constants and formulas) rather than a local patch.

## Database Changes

None required.

## Backend Changes

Changes in `new/server/routes/dashboard.py` as described above.

## Frontend Changes

None.

## Calculation Changes

None.

## Tests To Add/Change

- Port `audit/repro/BUG-005.py` into a pytest regression test under `new/server/tests/` (assert the Expected value; independent hand-derived numbers, not a second call to the same function).
- Add edge cases: zero, missing, negative, NaN/Inf, boundary values for every field the fix touches.
- Add the group-level invariant tests for RC-6 (see Root-Cause Groups).
- Review existing tests that assert the old behaviour; change an expected value only when the new value is independently derived and documented in the test.

## Browser Verification

- API/backend fix. After the fix, open the page(s) that consume this data (see Affected Features) and confirm the displayed value matches the API and DB.

## Regression Risks

- Removing a client-side catalog/formula can remove options users rely on; every factor still offered must exist server-side before the switch. Previews will change to server-computed values.

## Acceptance Criteria

1. `audit/repro/BUG-005.py` exits 0 on the fixed code (it prints expected vs actual).
2. Expected behaviour holds: GWP-20 CO2e = CO2 + CH4·GWP20_CH4 + N2O·GWP20_N2O for the active standard. Equivalently, the delta applied to the stored GWP-100 total must be CH4·(GWP20_CH4 − GWP100_CH4_active) + N2O·(GWP20_N2O − GWP100_N2O_active). For AR4 that is CH4·47 − N2O·9. - 2021: 5,736,270,170 tCO2e - 2023: 2,423,600.75 tCO2e
3. Full backend suite (`python -m pytest tests/` in `new/server`) and frontend checks (`npm run lint`, `npm run test`) pass.
4. No other open bug's repro changes from fail→pass or pass→fail unexpectedly (re-run `audit/work/rerun/run_all.sh`).

---

# BUG-109 — Scope 1 form saves an entry with no Unit selected: the client silently assumes m³ (10 → 2,641.72 gal stored) while the server calculates from the raw 10 in calc_inputs, so the stored activity and its emissions disagree 264×

**Severity:** Medium · **Category:** UI · **Phase:** P3 · **Root cause group:** RC-1 · **Found by:** Agent L (Browser) · **Independent confirmations:** 1

**Current status:** **Confirmed on the post-change code by the browser agent** (`audit/repro/BUG-109.mjs`); not re-run in the final pass (needs a live UI stack).

## Problem

Scope 1 form saves an entry with no Unit selected: the client silently assumes m³ (10 → 2,641.72 gal stored) while the server calculates from the raw 10 in calc_inputs, so the stored activity and its emissions disagree 264×

- **Actual:** Request: `quantity 2641.72, unit "gal", calc_inputs {"combustion":{"fuel":"Diesel (No. 2 Fuel Oil)","amount":10}}` → 201. Record 759 stores `quantity=2641.72 gal, co2e_total=0.1024 t`. The same 2641.72 gal entered explicitly gives 27.05 t. The Recent Activity table, CSV export and reports show "2,641.72 gal … 0.102 tCO2e".
- **Expected:** The form refuses to submit without a unit ("Please select a unit"), and in any case the stored activity quantity/unit and the stored emissions describe the same activity.

## Root Cause

A hidden default unit ("m3") on the client instead of a required-field check. The client sends two different representations of the activity (converted top-level vs raw calc_inputs), and the server calculates from one and persists the other without checking they agree.

## Affected Files

- `new/client/src/components/Scope1Form.jsx`

## Affected Features

Silent data-quality defect: an entry the user never gave a unit for is saved, and its recorded activity data cannot be reconciled with its emissions (264× here). Auditors comparing activity × factor against CO2e find unexplainable records; the user may believe they entered 10 gal or 10 m³ and either reading is wrong in one of the two fields.

## Required Changes

Require a unit in `handleAddEntry` (no "m3" fallback). Send one activity representation. On the server, reject a request whose top-level quantity/unit and calc_inputs amount/unit disagree, or persist exactly the values used in the calculation.

Implement through the shared fix for RC-1 (No central input validation) rather than a local patch.

## Database Changes

None required.

## Backend Changes

None beyond the above.

## Frontend Changes

Changes in `new/client/src/components/Scope1Form.jsx` as described above.

## Calculation Changes

None.

## Tests To Add/Change

- Port `audit/repro/BUG-109.mjs` into a Playwright spec under `new/client/e2e/` (or a vitest test where it is pure component logic).
- Add edge cases: zero, missing, negative, NaN/Inf, boundary values for every field the fix touches.
- Add the group-level invariant tests for RC-1 (see Root-Cause Groups).
- Review existing tests that assert the old behaviour; change an expected value only when the new value is independently derived and documented in the test.

## Browser Verification

- Reproduce the steps in AUDIT_FINDINGS.md on an isolated stack (`audit/tools/vite_audit.mjs` + backend on an audit DB copy) and confirm the Expected result on screen.
- Compare the UI value with the API response and the DB row for the same record; refresh and reopen the record.

## Regression Risks

- Stricter validation will reject inputs accepted today (existing bulk templates, integrations, scripts). Existing invalid rows remain until a cleanup job runs.

## Acceptance Criteria

1. `audit/repro/BUG-109.mjs` exits 0 on the fixed code (it prints expected vs actual).
2. Expected behaviour holds: The form refuses to submit without a unit ("Please select a unit"), and in any case the stored activity quantity/unit and the stored emissions describe the same activity.
3. Full backend suite (`python -m pytest tests/` in `new/server`) and frontend checks (`npm run lint`, `npm run test`) pass.
4. No other open bug's repro changes from fail→pass or pass→fail unexpectedly (re-run `audit/work/rerun/run_all.sh`).

---

# BUG-091 — Dehydrator throughput entered under the label "MMscf/yr" is saved with unit "MMscf/day" (record activity unit 365× off)

**Severity:** Medium · **Category:** UI · **Phase:** P3 · **Root cause group:** RC-4 · **Found by:** Agent K (Frontend/UI)

**Current status:** **Confirmed on the post-change code by the browser agent** (`audit/repro/BUG-091.mjs`); not re-run in the final pass (needs a live UI stack).

## Problem

Dehydrator throughput entered under the label "MMscf/yr" is saved with unit "MMscf/day" (record activity unit 365× off)

- **Actual:** POST `amount: 1000, unit: "MMscf/day"`; stored record 756 shows 1000 MMscf/day, i.e. 365,000 MMscf/yr of activity in the record table, exports and anything that reads amount/unit.
- **Expected:** Record activity `amount: 1000, unit: "MMscf/yr"` (or "MMscf").

## Root Cause

Hard-coded fallback unit contradicts the form label.

## Affected Files

- `new/client/src/components/Scope1Form.jsx`

## Affected Features

Activity data audit trail and exports carry the wrong unit (365×); anyone recalculating from amount/unit gets the wrong result.

## Required Changes

Use "MMscf/yr" (matching the label) or add an explicit unit selector.

Implement through the shared fix for RC-4 (Units are not parsed / converted in one place) rather than a local patch.

## Database Changes

None required.

## Backend Changes

None beyond the above.

## Frontend Changes

Changes in `new/client/src/components/Scope1Form.jsx` as described above.

## Calculation Changes

None.

## Tests To Add/Change

- Port `audit/repro/BUG-091.mjs` into a Playwright spec under `new/client/e2e/` (or a vitest test where it is pure component logic).
- Add edge cases: zero, missing, negative, NaN/Inf, boundary values for every field the fix touches.
- Add the group-level invariant tests for RC-4 (see Root-Cause Groups).
- Review existing tests that assert the old behaviour; change an expected value only when the new value is independently derived and documented in the test.

## Browser Verification

- Reproduce the steps in AUDIT_FINDINGS.md on an isolated stack (`audit/tools/vite_audit.mjs` + backend on an audit DB copy) and confirm the Expected result on screen.
- Compare the UI value with the API response and the DB row for the same record; refresh and reopen the record.

## Regression Risks

- A central unit parser changes results for every unit it now interprets correctly; stored records keep old values until a controlled recalculation. Unknown units that used to pass through will now be rejected.

## Acceptance Criteria

1. `audit/repro/BUG-091.mjs` exits 0 on the fixed code (it prints expected vs actual).
2. Expected behaviour holds: Record activity `amount: 1000, unit: "MMscf/yr"` (or "MMscf").
3. Full backend suite (`python -m pytest tests/` in `new/server`) and frontend checks (`npm run lint`, `npm run test`) pass.
4. No other open bug's repro changes from fail→pass or pass→fail unexpectedly (re-run `audit/work/rerun/run_all.sh`).

---

# BUG-096 — Scope 2 form: switching Source Type to Steam/Heat or CHP leaves the hidden unit at "kWh" — dropdown shows "Select..." but the request sends unit "kWh" (1000 "MMBtu" of steam booked as 3.41 MMBtu)

**Severity:** Medium · **Category:** UI · **Phase:** P3 · **Root cause group:** RC-4 · **Found by:** Agent K (Frontend/UI)

**Current status:** **Confirmed on the post-change code by the browser agent** (`audit/repro/BUG-096.mjs`); not re-run in the final pass (needs a live UI stack).

## Problem

Scope 2 form: switching Source Type to Steam/Heat or CHP leaves the hidden unit at "kWh" — dropdown shows "Select..." but the request sends unit "kWh" (1000 "MMBtu" of steam booked as 3.41 MMBtu)

- **Actual:** POST `/api/scope2` body contains `"amount":1000,"unit":"kWh"`; server converts 1000 kWh → `heat_mmbtu 3.412142`, `co2e 0.2263 t` (record 39). Had the user meant MMBtu (the record inspector for steam labels the amount "MMBtu") the correct value is 66.3 t (1000 × 53.06 / 0.8 / 1000) — 293× understated, with no warning. CHP entries also show "Select..." for Unit.
- **Expected:** Either the form forces a unit choice, or the default is one of the displayed steam units.

## Root Cause

Stale unit state from the electricity option set; no validation that `unit` belongs to the current option list.

## Affected Files

- `new/client/src/components/Scope2Form.jsx`

## Affected Features

Silent, invisible unit on Scope 2 steam/heat records; large understatement if the user assumes MMBtu.

## Required Changes

Reset `unit` in the Source Type `onChange` (e.g. to "mmbtu" for steam) and block submit when `unit` is not one of the displayed options.

Implement through the shared fix for RC-4 (Units are not parsed / converted in one place) rather than a local patch.

## Database Changes

None required.

## Backend Changes

None beyond the above.

## Frontend Changes

Changes in `new/client/src/components/Scope2Form.jsx` as described above.

## Calculation Changes

None.

## Tests To Add/Change

- Port `audit/repro/BUG-096.mjs` into a Playwright spec under `new/client/e2e/` (or a vitest test where it is pure component logic).
- Add edge cases: zero, missing, negative, NaN/Inf, boundary values for every field the fix touches.
- Add the group-level invariant tests for RC-4 (see Root-Cause Groups).
- Review existing tests that assert the old behaviour; change an expected value only when the new value is independently derived and documented in the test.

## Browser Verification

- Reproduce the steps in AUDIT_FINDINGS.md on an isolated stack (`audit/tools/vite_audit.mjs` + backend on an audit DB copy) and confirm the Expected result on screen.
- Compare the UI value with the API response and the DB row for the same record; refresh and reopen the record.

## Regression Risks

- A central unit parser changes results for every unit it now interprets correctly; stored records keep old values until a controlled recalculation. Unknown units that used to pass through will now be rejected.

## Acceptance Criteria

1. `audit/repro/BUG-096.mjs` exits 0 on the fixed code (it prints expected vs actual).
2. Expected behaviour holds: Either the form forces a unit choice, or the default is one of the displayed steam units.
3. Full backend suite (`python -m pytest tests/` in `new/server`) and frontend checks (`npm run lint`, `npm run test`) pass.
4. No other open bug's repro changes from fail→pass or pass→fail unexpectedly (re-run `audit/work/rerun/run_all.sh`).

---

# BUG-097 — CHP allocation form labels Power Output "MWh" but the server uses the number as MMBtu: heat share (and Scope 2 tCO2e) overstated ~2.7× with WRI efficiency method

**Severity:** Medium · **Category:** UI · **Phase:** P3 · **Root cause group:** RC-4 · **Found by:** Agent K (Frontend/UI)

**Current status:** **Confirmed on the post-change code by the browser agent** (`audit/repro/BUG-097.mjs`); not re-run in the final pass (needs a live UI stack).

## Problem

CHP allocation form labels Power Output "MWh" but the server uses the number as MMBtu: heat share (and Scope 2 tCO2e) overstated ~2.7× with WRI efficiency method

- **Actual:** Response/record 40: `co2e 292.04 tCO2e` = 125 / (125 + 100/0.33) — power treated as 100 MMBtu. 2.71× overstated. (Energy-content method: 50 % instead of 22.7 %.)
- **Expected:** WRI efficiency method (e_H 0.8, e_P 0.33, the server's own constants): heat share = (100/0.8) / (100/0.8 + 341.21/0.33) = 125 / 1158.98 = 10.79 % → **107.9 tCO2e**.

## Root Cause

Unit contract mismatch: the UI asks for MWh, the server variable is named `power_mmbtu` but is never converted (even the explicit `power_output_mwh` key is not converted).

## Affected Files

- `new/client/src/components/Scope2Form.jsx`
- `new/server/routes/scope2.py`

## Affected Features

Every CHP allocation entered through the UI over-allocates emissions to heat (Scope 2) by a factor that depends on the power/heat ratio.

## Required Changes

Convert MWh → MMBtu (×3.412142) on the server (or send MMBtu from the client and relabel), and name the payload key with its unit.

Implement through the shared fix for RC-4 (Units are not parsed / converted in one place) rather than a local patch.

## Database Changes

None required.

## Backend Changes

Changes in `new/server/routes/scope2.py` as described above.

## Frontend Changes

Changes in `new/client/src/components/Scope2Form.jsx` as described above.

## Calculation Changes

None.

## Tests To Add/Change

- Port `audit/repro/BUG-097.mjs` into a Playwright spec under `new/client/e2e/` (or a vitest test where it is pure component logic).
- Add edge cases: zero, missing, negative, NaN/Inf, boundary values for every field the fix touches.
- Add the group-level invariant tests for RC-4 (see Root-Cause Groups).
- Review existing tests that assert the old behaviour; change an expected value only when the new value is independently derived and documented in the test.

## Browser Verification

- Reproduce the steps in AUDIT_FINDINGS.md on an isolated stack (`audit/tools/vite_audit.mjs` + backend on an audit DB copy) and confirm the Expected result on screen.
- Compare the UI value with the API response and the DB row for the same record; refresh and reopen the record.

## Regression Risks

- A central unit parser changes results for every unit it now interprets correctly; stored records keep old values until a controlled recalculation. Unknown units that used to pass through will now be rejected.

## Acceptance Criteria

1. `audit/repro/BUG-097.mjs` exits 0 on the fixed code (it prints expected vs actual).
2. Expected behaviour holds: WRI efficiency method (e_H 0.8, e_P 0.33, the server's own constants): heat share = (100/0.8) / (100/0.8 + 341.21/0.33) = 125 / 1158.98 = 10.79 % → **107.9 tCO2e**.
3. Full backend suite (`python -m pytest tests/` in `new/server`) and frontend checks (`npm run lint`, `npm run test`) pass.
4. No other open bug's repro changes from fail→pass or pass→fail unexpectedly (re-run `audit/work/rerun/run_all.sh`).

---


# PHASE P4 — Backend / API defects

_Phase regression risk:_ Stricter validation will reject data that is accepted today (including existing bulk templates); existing bad rows need a data-cleanup decision rather than silent correction.

---

# BUG-007 — Manual Scope 1 entry has no plausibility bound or QA flag: 9 test records (1e13 MMBtu gas, 1e15 t coal) make up about 99.99% of the snapshot's Scope 1 total (3.72e12 t Verified, 4.69e12 t Pending)

**Severity:** Medium · **Category:** Emissions · **Phase:** P4 · **Root cause group:** RC-1 · **Found by:** Agent B (Emissions Auditor) · **Independent confirmations:** 2

**Current status:** **Still present** — `audit/repro/BUG-007.py` re-run on the final code: bug reproduced.

## Problem

Manual Scope 1 entry has no plausibility bound or QA flag: 9 test records (1e13 MMBtu gas, 1e15 t coal) make up about 99.99% of the snapshot's Scope 1 total (3.72e12 t Verified, 4.69e12 t Pending)

- **Actual:** The request is accepted and Verified, with no flag. On the snapshot DB this is what drives the dashboard lead: - Scope 1 Verified sum = 3,723,125,709,415 t. Seven rows (ids 640, 645, 649, 658, 662, 667, 669) contribute 3,718,014,999,999.6 t, which is 99.86%. Each is "Admin test record", NG `quantity` 9,999,999,999,999 MMBtu (from `source_payload`), co2e = 531,145,000,000 t. Hand calc: 9.999999999999e12 x (53.06 + 0.001x28 + 0.0001x265) kg / 1000 = 5.31145e11 t. **The math is correct, but the input is absurd.** - Scope 1 Pending sum = 4,686,441,566,610 t. Two rows (655, 675) contribute 4,686,4…
- **Expected:** The request is rejected, or at least flagged (`qa_flag`) and kept out of auto-Verified status. The bulk path already applies a z-score anomaly check and a 1e7 outlier flag.

## Root Cause

Only `isfinite`/`>=0` checks are applied to quantity. There is no magnitude or statistical plausibility check on the manual create path, and admin-created rows skip review.

## Affected Files

- `new/server/routes/emissions.py`

## Affected Features

One typo (extra zeros) or test entry through the UI/API is instantly Verified and dominates every Scope 1 total, intensity, SBTi trajectory and report. On the snapshot, the dashboard gross Scope 1+2 (3.7 trillion t) is wrong by about 3 orders of magnitude for this reason.

## Required Changes

Run the same `anomaly_detector.check_scope1` / outlier threshold used in bulk upload on manual create and PUT. Set `qa_flag` and force `Pending` when flagged, even for admin. Also add a hard sanity cap per unit (e.g. co2e per record > 1e8 t rejected).

Implement through the shared fix for RC-1 (No central input validation) rather than a local patch.

## Database Changes

None required.

## Backend Changes

Changes in `new/server/routes/emissions.py` as described above.

## Frontend Changes

None.

## Calculation Changes

None.

## Tests To Add/Change

- Port `audit/repro/BUG-007.py` into a pytest regression test under `new/server/tests/` (assert the Expected value; independent hand-derived numbers, not a second call to the same function).
- Add edge cases: zero, missing, negative, NaN/Inf, boundary values for every field the fix touches.
- Add the group-level invariant tests for RC-1 (see Root-Cause Groups).
- Review existing tests that assert the old behaviour; change an expected value only when the new value is independently derived and documented in the test.

## Browser Verification

- API/backend fix. After the fix, open the page(s) that consume this data (see Affected Features) and confirm the displayed value matches the API and DB.

## Regression Risks

- Stricter validation will reject inputs accepted today (existing bulk templates, integrations, scripts). Existing invalid rows remain until a cleanup job runs.

## Acceptance Criteria

1. `audit/repro/BUG-007.py` exits 0 on the fixed code (it prints expected vs actual).
2. Expected behaviour holds: The request is rejected, or at least flagged (`qa_flag`) and kept out of auto-Verified status. The bulk path already applies a z-score anomaly check and a 1e7 outlier flag.
3. Full backend suite (`python -m pytest tests/` in `new/server`) and frontend checks (`npm run lint`, `npm run test`) pass.
4. No other open bug's repro changes from fail→pass or pass→fail unexpectedly (re-run `audit/work/rerun/run_all.sh`).

---

# BUG-029 — Manage Data page crashes for every user when any facility has a NULL name; POST /api/facilities accepts facilities with no name

**Severity:** High · **Category:** UI · **Phase:** P4 · **Root cause group:** RC-1 · **Found by:** Agent L (Browser) · **Independent confirmations:** 4

**Current status:** **Confirmed on the post-change code by the browser agent** (`audit/repro/BUG-029.mjs`); not re-run in the final pass (needs a live UI stack).

## Problem

Manage Data page crashes for every user when any facility has a NULL name; POST /api/facilities accepts facilities with no name

- **Actual:** The API returns 201 and stores `name=NULL`. The whole Manage Data page (facilities, production data, emission sources, mitigation tabs) is unusable for every user while such a row exists. The snapshot DB already has such rows, so in the audited state Manage Data is always broken.
- **Expected:** The API rejects a facility without a name (400), and the page tolerates a missing name instead of crashing.

## Root Cause

The server has no required-field validation for facility name (and the column is nullable). The client assumes `f.name` is always a string (`f.name.toLowerCase()`), while it guards `f.location?.` and `f.field?.` on the same line.

## Affected Files

- `new/client/src/pages/ManageData.jsx`
- `new/server/models.py`
- `new/server/routes/facilities.py`

## Affected Features

A core data-management workflow is blocked: users cannot create or edit facilities, production data (carbon-intensity denominators) or emission sources through the UI. Any admin/superuser (or a bulk import) can cause this with one blank facility.

## Required Changes

Require a non-empty `name` in `add_facility`/update (and bulk import), make `Facility.name` NOT NULL after cleaning the data, and use `(f.name || '').toLowerCase()` in `getFilteredFacilities`.

Implement through the shared fix for RC-1 (No central input validation) rather than a local patch.

## Database Changes

Data policy: block new bad data only — no NOT NULL constraint (13 existing nameless facilities would violate it). Enforce a required name in the API and bulk import; the UI tolerates legacy NULL names.

## Backend Changes

Changes in `new/server/routes/facilities.py` as described above.

## Frontend Changes

Changes in `new/client/src/pages/ManageData.jsx` as described above.

## Calculation Changes

None.

## Tests To Add/Change

- Port `audit/repro/BUG-029.mjs` into a Playwright spec under `new/client/e2e/` (or a vitest test where it is pure component logic).
- Add edge cases: zero, missing, negative, NaN/Inf, boundary values for every field the fix touches.
- Add the group-level invariant tests for RC-1 (see Root-Cause Groups).
- Review existing tests that assert the old behaviour; change an expected value only when the new value is independently derived and documented in the test.

## Browser Verification

- Reproduce the steps in AUDIT_FINDINGS.md on an isolated stack (`audit/tools/vite_audit.mjs` + backend on an audit DB copy) and confirm the Expected result on screen.
- Compare the UI value with the API response and the DB row for the same record; refresh and reopen the record.

## Regression Risks

- Stricter validation will reject inputs accepted today (existing bulk templates, integrations, scripts). Existing invalid rows remain until a cleanup job runs.

## Acceptance Criteria

1. `audit/repro/BUG-029.mjs` exits 0 on the fixed code (it prints expected vs actual).
2. Expected behaviour holds: The API rejects a facility without a name (400), and the page tolerates a missing name instead of crashing.
3. Full backend suite (`python -m pytest tests/` in `new/server`) and frontend checks (`npm run lint`, `npm run test`) pass.
4. No other open bug's repro changes from fail→pass or pass→fail unexpectedly (re-run `audit/work/rerun/run_all.sh`).

---

# BUG-073 — Scope 2 and Scope 3 create accept a missing or non-numeric year: one year-less Scope 2 record makes the main dashboard (summary/batch-all) return 500, and year-less Scope 3 is in the total but missing from by-year

**Severity:** High · **Category:** Emissions · **Phase:** P4 · **Root cause group:** RC-1 · **Found by:** Agent B (Emissions Auditor)

**Current status:** **Still present** — `audit/repro/BUG-073.py` re-run on the final code: bug reproduced.

## Problem

Scope 2 and Scope 3 create accept a missing or non-numeric year: one year-less Scope 2 record makes the main dashboard (summary/batch-all) return 500, and year-less Scope 3 is in the total but missing from by-year

- **Actual:** - Scope 2 create returns 201 for no year, and for `year:"abc", month:13`. - After that, `/api/dashboard/summary` and `/api/dashboard/batch-all` return **500** for admin and for the West-region user (`TypeError: int() argument must be ... not 'NoneType'` at dashboard.py:508). The main dashboard is unusable for every user whose facility scope includes that facility. - Scope 3 summary: `total 217.35` vs `sum(by_year) 216.85`. The year-less 0.5 t is counted in the headline total but is in no year, so the year chart does not add up to the KPI, and the row drops out of every year-filtered view.
- **Expected:** Create returns 422 for a missing, non-integer or out-of-range year or month, as Scope 1 does. Aggregations never crash on one bad row. Scope 3 `total` equals the sum of `by_year`.

## Root Cause

Scope 2 and Scope 3 create have no date validation, and the summary aggregation casts `row.year` without a guard.

## Affected Files

- `new/server/routes/scope2.py`

## Affected Features

Any user with Scope 2 create rights (the admin or superuser auto-Verify path, BUG-060) can take down the organisation dashboard with one API call or one client bug. Year-less Scope 2/3 emissions silently disappear from every year-filtered total, SBTi and intensity figure, while still inflating the all-years Scope 3 KPI.

## Required Changes

Apply the Scope 1 year/month validation, ideally a shared helper, to the Scope 2 and Scope 3 create, update and bulk paths. Guard `int(row.year)` in the aggregations, skipping or bucketing NULL years as "Unknown" and surfacing them.

Implement through the shared fix for RC-1 (No central input validation) rather than a local patch.

## Database Changes

None required.

## Backend Changes

Changes in `new/server/routes/scope2.py` as described above.

## Frontend Changes

None.

## Calculation Changes

None.

## Tests To Add/Change

- Port `audit/repro/BUG-073.py` into a pytest regression test under `new/server/tests/` (assert the Expected value; independent hand-derived numbers, not a second call to the same function).
- Add edge cases: zero, missing, negative, NaN/Inf, boundary values for every field the fix touches.
- Add the group-level invariant tests for RC-1 (see Root-Cause Groups).
- Review existing tests that assert the old behaviour; change an expected value only when the new value is independently derived and documented in the test.

## Browser Verification

- API/backend fix. After the fix, open the page(s) that consume this data (see Affected Features) and confirm the displayed value matches the API and DB.

## Regression Risks

- Stricter validation will reject inputs accepted today (existing bulk templates, integrations, scripts). Existing invalid rows remain until a cleanup job runs.

## Acceptance Criteria

1. `audit/repro/BUG-073.py` exits 0 on the fixed code (it prints expected vs actual).
2. Expected behaviour holds: Create returns 422 for a missing, non-integer or out-of-range year or month, as Scope 1 does. Aggregations never crash on one bad row. Scope 3 `total` equals the sum of `by_year`.
3. Full backend suite (`python -m pytest tests/` in `new/server`) and frontend checks (`npm run lint`, `npm run test`) pass.
4. No other open bug's repro changes from fail→pass or pass→fail unexpectedly (re-run `audit/work/rerun/run_all.sh`).

---

# BUG-085 — Scope 2/3 bulk import silently books rows with a blank or non-ISO date to January 2024, and stores a blank Scope 3 category as "Category "

**Severity:** High · **Category:** Emissions · **Phase:** P4 · **Root cause group:** RC-1, RC-10 · **Found by:** Agent B (Emissions Auditor) · **Independent confirmations:** 1

**Current status:** **Still present** — `audit/repro/BUG-085.py` re-run on the final code: bug reproduced.

## Problem

Scope 2/3 bulk import silently books rows with a blank or non-ISO date to January 2024, and stores a blank Scope 3 category as "Category "

- **Actual:** All rows are accepted (skipped 0): ``` scope3 stored: [{'year': 2024, 'month': 1, 'category': 'Category 4', 'sub_category': 'no date'}, {'year': 2024, 'month': 1, 'category': 'Category 7', 'sub_category': 'slash date'}, {'year': 2037, 'month': 4, 'category': 'Category ', 'sub_category': 'blank category'}] scope2 stored: [{'year': 2024, 'month': 1, 'electricity_kwh': 3000.0}] ``` The 2037 data is moved into the 2024 inventory, and the upload reports success. Because the fabricated 2024-01 key then collides with other undated rows, subsequent undated or mis-formatted rows for the same facility…
- **Expected:** Rows with a missing or unparseable date, or a missing or invalid category, are rejected with a row error, as Scope 1 bulk does.

## Root Cause

Hard-coded fallback year and month, a swallowed parse exception, and no category validation in the Scope 2/3 row processors.

## Affected Files

- `new/server/background_processor.py`

## Affected Features

Emissions are silently shifted between reporting years. 2024 is inflated and the true year understated, which affects SBTi base/target years, YoY and intensity. Unclassified Scope 3 records ("Category ") fall outside every per-category breakdown.

## Required Changes

Remove the 2024/1 defaults. Parse the accepted date formats explicitly (YYYY-MM, YYYY-MM-DD, MM/YYYY), otherwise return a row error. Validate year and month ranges. Require a category that maps to Category 1-15, rejecting blank or unknown values.

Implement through the shared fix for RC-1 (No central input validation), RC-10 (Bulk import integrity) rather than a local patch.

## Database Changes

None required.

## Backend Changes

Changes in `new/server/background_processor.py` as described above.

## Frontend Changes

None.

## Calculation Changes

None.

## Tests To Add/Change

- Port `audit/repro/BUG-085.py` into a pytest regression test under `new/server/tests/` (assert the Expected value; independent hand-derived numbers, not a second call to the same function).
- Add edge cases: zero, missing, negative, NaN/Inf, boundary values for every field the fix touches.
- Add the group-level invariant tests for RC-1, RC-10 (see Root-Cause Groups).
- Review existing tests that assert the old behaviour; change an expected value only when the new value is independently derived and documented in the test.

## Browser Verification

- API/backend fix. After the fix, open the page(s) that consume this data (see Affected Features) and confirm the displayed value matches the API and DB.

## Regression Risks

- Stricter validation will reject inputs accepted today (existing bulk templates, integrations, scripts). Existing invalid rows remain until a cleanup job runs.
- Bulk imports that previously succeeded may now fail row validation or de-duplicate differently; unique indexes fail on existing duplicates until cleaned.

## Acceptance Criteria

1. `audit/repro/BUG-085.py` exits 0 on the fixed code (it prints expected vs actual).
2. Expected behaviour holds: Rows with a missing or unparseable date, or a missing or invalid category, are rejected with a row error, as Scope 1 bulk does.
3. Full backend suite (`python -m pytest tests/` in `new/server`) and frontend checks (`npm run lint`, `npm run test`) pass.
4. No other open bug's repro changes from fail→pass or pass→fail unexpectedly (re-run `audit/work/rerun/run_all.sh`).

---

# BUG-111 — Scope 1 bulk import books a row with a blank Unit as m³ and accepts year 1800, both of which the manual form/API reject

**Severity:** Medium · **Category:** Emissions · **Phase:** P4 · **Root cause group:** RC-1, RC-10 · **Found by:** Agent L (Browser)

**Current status:** **Confirmed on the post-change code by the browser agent** (`audit/repro/BUG-111.mjs`); not re-run in the final pass (needs a live UI stack).

## Problem

Scope 1 bulk import books a row with a blank Unit as m³ and accepts year 1800, both of which the manual form/API reject

- **Actual:** - Row 5 imported as record 767: `quantity 200, unit 'm3'`, 72.32 tCO2e (Pending) — the file never said m³. - Row 6 imported as record 768: `year 1800` (Pending). Once approved it appears as a separate year in dashboards/filters (the snapshot already contains a year-1800 record). Job status: `processed 8, skipped_count 4` — the skip list (unknown region, negative, "abc", duplicate) contains neither row.
- **Expected:** Both rows are skipped with a reason ("Unit is required", "Year out of range 1900-2100"), as the manual path does for the year (422 "Invalid year") and as the wizard marks Unit as a required field.

## Root Cause

The bulk processor substitutes a default for a missing unit instead of rejecting the row, and it does not share the manual route's year validation.

## Affected Files

- `new/server/background_processor.py`

## Affected Features

Silent unit assumption changes the magnitude of imported emissions (a blank unit on a gal/bbl/tonne row is booked as m³); out-of-range years enter the inventory. Channel inconsistency: the same data is rejected manually but accepted in bulk.

## Required Changes

Treat a blank unit as a row error (no default). Apply the same year (1900-2100, or reporting-period) and month validation in `background_processor` as in `POST /api/emissions/`.

Implement through the shared fix for RC-1 (No central input validation), RC-10 (Bulk import integrity) rather than a local patch.

## Database Changes

None required.

## Backend Changes

Changes in `new/server/background_processor.py` as described above.

## Frontend Changes

None.

## Calculation Changes

None.

## Tests To Add/Change

- Port `audit/repro/BUG-111.mjs` into a Playwright spec under `new/client/e2e/` (or a vitest test where it is pure component logic).
- Add edge cases: zero, missing, negative, NaN/Inf, boundary values for every field the fix touches.
- Add the group-level invariant tests for RC-1, RC-10 (see Root-Cause Groups).
- Review existing tests that assert the old behaviour; change an expected value only when the new value is independently derived and documented in the test.

## Browser Verification

- Reproduce the steps in AUDIT_FINDINGS.md on an isolated stack (`audit/tools/vite_audit.mjs` + backend on an audit DB copy) and confirm the Expected result on screen.
- Compare the UI value with the API response and the DB row for the same record; refresh and reopen the record.

## Regression Risks

- Stricter validation will reject inputs accepted today (existing bulk templates, integrations, scripts). Existing invalid rows remain until a cleanup job runs.
- Bulk imports that previously succeeded may now fail row validation or de-duplicate differently; unique indexes fail on existing duplicates until cleaned.

## Acceptance Criteria

1. `audit/repro/BUG-111.mjs` exits 0 on the fixed code (it prints expected vs actual).
2. Expected behaviour holds: Both rows are skipped with a reason ("Unit is required", "Year out of range 1900-2100"), as the manual path does for the year (422 "Invalid year") and as the wizard marks Unit as a required field.
3. Full backend suite (`python -m pytest tests/` in `new/server`) and frontend checks (`npm run lint`, `npm run test`) pass.
4. No other open bug's repro changes from fail→pass or pass→fail unexpectedly (re-run `audit/work/rerun/run_all.sh`).

---

# BUG-112 — Custom emission factor with every factor field blank is saved (CO2/CH4/N2O = 0) and Tier 2 records that use it are stored with 0 tCO2e and no warning

**Severity:** Medium · **Category:** API · **Phase:** P4 · **Root cause group:** RC-1 · **Found by:** Agent L (Browser)

**Current status:** **Confirmed on the post-change code by the browser agent** (`audit/repro/BUG-112.mjs`); not re-run in the final pass (needs a live UI stack).

## Problem

Custom emission factor with every factor field blank is saved (CO2/CH4/N2O = 0) and Tier 2 records that use it are stored with 0 tCO2e and no warning

- **Actual:** - 201 `{"id":102}`; stored row `co2_factor 0.0, ch4_factor 0.0, n2o_factor 0.0`. (Saved twice → ids 102 and 104, same name.) - Scope 1 record: 201, `emissions {"ch4":0,"co2":0,"n2o":0,"totalCo2e":0}`, `calculation_method server_custom_factor`. - For comparison the negative case is rejected server-side (400 "co2_factor must be a non-negative number") but the UI shows only "Failed to save factor".
- **Expected:** The factor is rejected ("enter at least one emission factor"), or at minimum records using an all-zero factor are refused/flagged.

## Root Cause

Validation treats blank as zero and zero as valid for all gases simultaneously.

## Affected Files

- `new/client/src/pages/ManageData.jsx`

## Affected Features

Activity data entered against such a factor contributes nothing to the inventory while looking complete (201, success toast, Verified for admin). Because factor names are not unique (BUG-065), an empty duplicate can also be picked by name in bulk import.

## Required Changes

Require at least one factor > 0 (and non-empty numeric input for each provided gas); reject blank-only factors with 400; surface the server's validation message in the toast.

Implement through the shared fix for RC-1 (No central input validation) rather than a local patch.

## Database Changes

None required.

## Backend Changes

None beyond the above.

## Frontend Changes

Changes in `new/client/src/pages/ManageData.jsx` as described above.

## Calculation Changes

None.

## Tests To Add/Change

- Port `audit/repro/BUG-112.mjs` into a Playwright spec under `new/client/e2e/` (or a vitest test where it is pure component logic).
- Add edge cases: zero, missing, negative, NaN/Inf, boundary values for every field the fix touches.
- Add the group-level invariant tests for RC-1 (see Root-Cause Groups).
- Review existing tests that assert the old behaviour; change an expected value only when the new value is independently derived and documented in the test.

## Browser Verification

- Reproduce the steps in AUDIT_FINDINGS.md on an isolated stack (`audit/tools/vite_audit.mjs` + backend on an audit DB copy) and confirm the Expected result on screen.
- Compare the UI value with the API response and the DB row for the same record; refresh and reopen the record.

## Regression Risks

- Stricter validation will reject inputs accepted today (existing bulk templates, integrations, scripts). Existing invalid rows remain until a cleanup job runs.

## Acceptance Criteria

1. `audit/repro/BUG-112.mjs` exits 0 on the fixed code (it prints expected vs actual).
2. Expected behaviour holds: The factor is rejected ("enter at least one emission factor"), or at minimum records using an all-zero factor are refused/flagged.
3. Full backend suite (`python -m pytest tests/` in `new/server`) and frontend checks (`npm run lint`, `npm run test`) pass.
4. No other open bug's repro changes from fail→pass or pass→fail unexpectedly (re-run `audit/work/rerun/run_all.sh`).

---

# BUG-034 — SBTi target POST accepts NaN / Infinity (range checks pass for non-finite floats); trajectory endpoint then returns 500 or invalid JSON for all users

**Severity:** Medium · **Category:** SBTi · **Phase:** P4 · **Root cause group:** RC-1, RC-9 · **Found by:** Agent H (SBTi Auditor)

**Current status:** **Still present** — `audit/repro/BUG-034.py` re-run on the final code: bug reproduced.

## Problem

SBTi target POST accepts NaN / Infinity (range checks pass for non-finite floats); trajectory endpoint then returns 500 or invalid JSON for all users

- **Actual:** Stored; the latest target is used by `/sbti-trajectory`, so the SBTi page and the main dashboard SBTi banner break for every user until another target is posted (there is no delete/edit endpoint).
- **Expected:** 400 "must be a finite number". Checks such as `reduction_rate_pct <= 0 or > 25` are all False for NaN, so they do not reject it.

## Root Cause

No `math.isfinite` check; range comparisons against NaN are always False.

## Affected Files

- `new/server/routes/dashboard.py`
- `new/server/routes/managedata.py`

## Affected Features

One API call (admin/superuser) disables SBTi tracking platform-wide; error text leaks SQL. The UI form itself cannot produce NaN (parseFloat || 0), so it is an API-level validation gap.

## Required Changes

Reject non-finite values (`math.isfinite`) for all numeric fields; return generic errors instead of `str(e)`; guard `reduction_rate_pct is None` in the trajectory.

Implement through the shared fix for RC-1 (No central input validation), RC-9 (SBTi period / scope logic) rather than a local patch.

## Database Changes

None required.

## Backend Changes

Changes in `new/server/routes/dashboard.py`, `new/server/routes/managedata.py` as described above.

## Frontend Changes

None.

## Calculation Changes

None.

## Tests To Add/Change

- Port `audit/repro/BUG-034.py` into a pytest regression test under `new/server/tests/` (assert the Expected value; independent hand-derived numbers, not a second call to the same function).
- Add edge cases: zero, missing, negative, NaN/Inf, boundary values for every field the fix touches.
- Add the group-level invariant tests for RC-1, RC-9 (see Root-Cause Groups).
- Review existing tests that assert the old behaviour; change an expected value only when the new value is independently derived and documented in the test.

## Browser Verification

- API/backend fix. After the fix, open the page(s) that consume this data (see Affected Features) and confirm the displayed value matches the API and DB.

## Regression Risks

- Stricter validation will reject inputs accepted today (existing bulk templates, integrations, scripts). Existing invalid rows remain until a cleanup job runs.
- SBTi progress and on-track status will change; previously shown 'ON TRACK' states may flip.

## Acceptance Criteria

1. `audit/repro/BUG-034.py` exits 0 on the fixed code (it prints expected vs actual).
2. Expected behaviour holds: 400 "must be a finite number". Checks such as `reduction_rate_pct <= 0 or > 25` are all False for NaN, so they do not reject it.
3. Full backend suite (`python -m pytest tests/` in `new/server`) and frontend checks (`npm run lint`, `npm run test`) pass.
4. No other open bug's repro changes from fail→pass or pass→fail unexpectedly (re-run `audit/work/rerun/run_all.sh`).

---

# BUG-039 — Emission goals API ("+ Set Target") has no value validation: negative, year 1, and NaN goals are accepted; a NaN goal for the current year makes the main dashboard batch return 500

**Severity:** Medium · **Category:** API · **Phase:** P4 · **Root cause group:** RC-1 · **Found by:** Agent H (SBTi Auditor)

**Current status:** **Still present** — `audit/repro/BUG-039.py` re-run on the final code: bug reproduced.

## Problem

Emission goals API ("+ Set Target") has no value validation: negative, year 1, and NaN goals are accepted; a NaN goal for the current year makes the main dashboard batch return 500

- **Actual:** All accepted. The snapshot already contains goals up to year 2126 (100 rows 2027-2126), showing there is no range check. With the NaN goal the main dashboard fails to load for every user for that year (for the current year: the default view).
- **Expected:** 400 for non-finite, negative/zero targets and for years outside a sane range (e.g. 1990-2100).

## Root Cause

Only presence checks (`data.get("year")`, `target_amount is not None`) and `float()` conversion; no `isfinite`, sign or range check. Readers call `float(goal.target_amount)` without None-guard (`/goals` list guards it, the other two do not).

## Affected Files

- `new/server/routes/dashboard.py`
- `new/server/routes/managedata.py`

## Affected Features

An API-only (UI sends `null` for NaN, which is rejected) admin/superuser input can take down the main dashboard; negative goals make the "% GOAL" badge nonsensical. Medium: requires privileged API use, but the effect is platform-wide.

## Required Changes

Validate `math.isfinite(target) and target > 0` and a year range; guard `target_amount is None` in the readers.

Implement through the shared fix for RC-1 (No central input validation) rather than a local patch.

## Database Changes

None required.

## Backend Changes

Changes in `new/server/routes/dashboard.py`, `new/server/routes/managedata.py` as described above.

## Frontend Changes

None.

## Calculation Changes

None.

## Tests To Add/Change

- Port `audit/repro/BUG-039.py` into a pytest regression test under `new/server/tests/` (assert the Expected value; independent hand-derived numbers, not a second call to the same function).
- Add edge cases: zero, missing, negative, NaN/Inf, boundary values for every field the fix touches.
- Add the group-level invariant tests for RC-1 (see Root-Cause Groups).
- Review existing tests that assert the old behaviour; change an expected value only when the new value is independently derived and documented in the test.

## Browser Verification

- API/backend fix. After the fix, open the page(s) that consume this data (see Affected Features) and confirm the displayed value matches the API and DB.

## Regression Risks

- Stricter validation will reject inputs accepted today (existing bulk templates, integrations, scripts). Existing invalid rows remain until a cleanup job runs.

## Acceptance Criteria

1. `audit/repro/BUG-039.py` exits 0 on the fixed code (it prints expected vs actual).
2. Expected behaviour holds: 400 for non-finite, negative/zero targets and for years outside a sane range (e.g. 1990-2100).
3. Full backend suite (`python -m pytest tests/` in `new/server`) and frontend checks (`npm run lint`, `npm run test`) pass.
4. No other open bug's repro changes from fail→pass or pass→fail unexpectedly (re-run `audit/work/rerun/run_all.sh`).

---

# BUG-045 — "Add Region" (create facility) form fails with HTTP 500 unless the optional Latitude/Longitude fields are filled

**Severity:** Medium · **Category:** Backend · **Phase:** P4 · **Root cause group:** RC-1 · **Found by:** Agent L (Browser)

**Current status:** **Confirmed on the post-change code by the browser agent** (`audit/repro/BUG-045.mjs`); not re-run in the final pass (needs a live UI stack).

## Problem

"Add Region" (create facility) form fails with HTTP 500 unless the optional Latitude/Longitude fields are filled

- **Actual:** `POST /api/facilities` → `500 {"error":"Internal server error"}`. Server log: `sqlalchemy.exc.StatementError: (builtins.ValueError) could not convert string to float: ''` on the INSERT into facilities. The UI shows only "Failed to add region". The same form with Latitude=31.5 / Longitude=5.2 → 201 (facility id 173).
- **Expected:** Facility created (201) with NULL coordinates, or a clear 400 validation message.

## Root Cause

The route does not coerce empty strings for the Float columns latitude/longitude (unlike `equity_share_pct`/`reconciliation_threshold`, which use `float(x or default)`), and the form always sends them as "".

## Affected Files

- `new/client/src/pages/ManageData.jsx`
- `new/server/routes/facilities.py`

## Affected Features

The only UI path for creating a facility fails in the default case (coordinates are optional and usually unknown). Users see a non-actionable error. The side effect also shows the 500 handler is reached for plain input-type errors.

## Required Changes

Parse latitude/longitude as `float(v) if v not in (None, "") else None` (with range checks -90..90 / -180..180) in both create and update, and return 400 on invalid values. The client should also omit empty numeric fields.

Implement through the shared fix for RC-1 (No central input validation) rather than a local patch.

## Database Changes

None required.

## Backend Changes

Changes in `new/server/routes/facilities.py` as described above.

## Frontend Changes

Changes in `new/client/src/pages/ManageData.jsx` as described above.

## Calculation Changes

None.

## Tests To Add/Change

- Port `audit/repro/BUG-045.mjs` into a Playwright spec under `new/client/e2e/` (or a vitest test where it is pure component logic).
- Add edge cases: zero, missing, negative, NaN/Inf, boundary values for every field the fix touches.
- Add the group-level invariant tests for RC-1 (see Root-Cause Groups).
- Review existing tests that assert the old behaviour; change an expected value only when the new value is independently derived and documented in the test.

## Browser Verification

- Reproduce the steps in AUDIT_FINDINGS.md on an isolated stack (`audit/tools/vite_audit.mjs` + backend on an audit DB copy) and confirm the Expected result on screen.
- Compare the UI value with the API response and the DB row for the same record; refresh and reopen the record.

## Regression Risks

- Stricter validation will reject inputs accepted today (existing bulk templates, integrations, scripts). Existing invalid rows remain until a cleanup job runs.

## Acceptance Criteria

1. `audit/repro/BUG-045.mjs` exits 0 on the fixed code (it prints expected vs actual).
2. Expected behaviour holds: Facility created (201) with NULL coordinates, or a clear 400 validation message.
3. Full backend suite (`python -m pytest tests/` in `new/server`) and frontend checks (`npm run lint`, `npm run test`) pass.
4. No other open bug's repro changes from fail→pass or pass→fail unexpectedly (re-run `audit/work/rerun/run_all.sh`).

---

# BUG-060 — Scope 2 manual entries and Scope 2 bulk imports by a superuser are auto-Verified, while Scope 1 and Scope 3 require admin approval (inconsistent maker-checker)

**Severity:** Medium · **Category:** API · **Phase:** P4 · **Root cause group:** RC-2 · **Found by:** Agent I (Backend/API/Security)

**Current status:** **Still present** — `audit/repro/BUG-060.py` re-run on the final code: bug reproduced.

## Problem

Scope 2 manual entries and Scope 2 bulk imports by a superuser are auto-Verified, while Scope 1 and Scope 3 require admin approval (inconsistent maker-checker)

- **Actual:** Scope 1 id 752 → Pending, Scope 3 id 29 → Pending, Scope 2 ids 38 (manual) and 39 (bulk) → **Verified, approved_by = 17 (the superuser themself)**.
- **Expected:** Superuser entries Pending in all scopes (and bulk imports always Pending), awaiting a second person's approval.

## Root Cause

Scope 2 routes use a different role list for auto-verification than Scope 1/3 and than the documented bulk-import rule.

## Affected Files

- `new/server/routes/scope2.py`

## Affected Features

A superuser self-approves Scope 2 data (including whole bulk files) straight into Verified dashboard/report totals with no second reviewer — segregation of duties is violated for Scope 2 only. If D-04 truly intends superuser auto-verification, Scope 1/3 are wrong instead; either way the workflow is inconsistent.

## Required Changes

Use one shared status policy helper for all scopes (admin → Verified, others → Pending; bulk → Pending).

Implement through the shared fix for RC-2 (Maker-checker / status policy duplicated per route) rather than a local patch.

## Database Changes

None required.

## Backend Changes

Changes in `new/server/routes/scope2.py` as described above.

## Frontend Changes

None.

## Calculation Changes

None.

## Tests To Add/Change

- Port `audit/repro/BUG-060.py` into a pytest regression test under `new/server/tests/` (assert the Expected value; independent hand-derived numbers, not a second call to the same function).
- Add edge cases: zero, missing, negative, NaN/Inf, boundary values for every field the fix touches.
- Add the group-level invariant tests for RC-2 (see Root-Cause Groups).
- Review existing tests that assert the old behaviour; change an expected value only when the new value is independently derived and documented in the test.

## Browser Verification

- API/backend fix. After the fix, open the page(s) that consume this data (see Affected Features) and confirm the displayed value matches the API and DB.

## Regression Risks

- Status-policy changes alter who can approve and what edits reset records to Pending; re-run the full maker-checker role matrix (user, superuser, admin, it roles) for Scope 1/2/3, CAP and bulk.

## Acceptance Criteria

1. `audit/repro/BUG-060.py` exits 0 on the fixed code (it prints expected vs actual).
2. Expected behaviour holds: Superuser entries Pending in all scopes (and bulk imports always Pending), awaiting a second person's approval.
3. Full backend suite (`python -m pytest tests/` in `new/server`) and frontend checks (`npm run lint`, `npm run test`) pass.
4. No other open bug's repro changes from fail→pass or pass→fail unexpectedly (re-run `audit/work/rerun/run_all.sh`).

---

# BUG-070 — POST /api/emissions/reject/<id> has no status check: a superuser can flip an admin-Verified record to Rejected (removing it from all totals) and overwrite its approver

**Severity:** Medium · **Category:** API · **Phase:** P4 · **Root cause group:** RC-2 · **Found by:** Agent I (Backend/API/Security)

**Current status:** **Still present** — `audit/repro/BUG-070.py` re-run on the final code: bug reproduced.

## Problem

POST /api/emissions/reject/<id> has no status check: a superuser can flip an admin-Verified record to Rejected (removing it from all totals) and overwrite its approver

- **Actual:** 200; record becomes `status=Rejected, approved_by=17 (superuser), qa_flag='Rejected: x'`; the admin's approval is overwritten. Batch reject on the same id returns `deleted_count=0`. Repeating the reject also returns 200.
- **Expected:** 400 "Record is not pending approval" (consistent with approve and batch reject).

## Root Cause

Missing pending-status guard on the single-record reject.

## Affected Files

- `new/server/routes/emissions.py`

## Affected Features

Verified inventory data can be withdrawn from dashboards/reports by a superuser without admin involvement; the audit field `approved_by` loses who originally verified it. Double-submits are not idempotent-safe (each re-reject rewrites approver/time).

## Required Changes

Apply the same pending-status check as `approve_emission`; return 409/400 for already-decided records.

Implement through the shared fix for RC-2 (Maker-checker / status policy duplicated per route) rather than a local patch.

## Database Changes

None required.

## Backend Changes

Changes in `new/server/routes/emissions.py` as described above.

## Frontend Changes

None.

## Calculation Changes

None.

## Tests To Add/Change

- Port `audit/repro/BUG-070.py` into a pytest regression test under `new/server/tests/` (assert the Expected value; independent hand-derived numbers, not a second call to the same function).
- Add edge cases: zero, missing, negative, NaN/Inf, boundary values for every field the fix touches.
- Add the group-level invariant tests for RC-2 (see Root-Cause Groups).
- Review existing tests that assert the old behaviour; change an expected value only when the new value is independently derived and documented in the test.

## Browser Verification

- API/backend fix. After the fix, open the page(s) that consume this data (see Affected Features) and confirm the displayed value matches the API and DB.

## Regression Risks

- Status-policy changes alter who can approve and what edits reset records to Pending; re-run the full maker-checker role matrix (user, superuser, admin, it roles) for Scope 1/2/3, CAP and bulk.

## Acceptance Criteria

1. `audit/repro/BUG-070.py` exits 0 on the fixed code (it prints expected vs actual).
2. Expected behaviour holds: 400 "Record is not pending approval" (consistent with approve and batch reject).
3. Full backend suite (`python -m pytest tests/` in `new/server`) and frontend checks (`npm run lint`, `npm run test`) pass.
4. No other open bug's repro changes from fail→pass or pass→fail unexpectedly (re-run `audit/work/rerun/run_all.sh`).

---

# BUG-074 — Approve/reject endpoints are not concurrency-safe: two simultaneous approvals of the same record both return 200 (duplicate audit entries; approve+reject race ends in an arbitrary final state)

**Severity:** Low · **Category:** Backend · **Phase:** P4 · **Root cause group:** RC-2 · **Found by:** Agent I (Backend/API/Security)

**Current status:** **Still present** — `audit/repro/BUG-074.py` re-run on the final code: bug reproduced.

## Problem

Approve/reject endpoints are not concurrency-safe: two simultaneous approvals of the same record both return 200 (duplicate audit entries; approve+reject race ends in an arbitrary final state)

- **Actual:** 17 of 30 records got 200 for both requests; 47 approval log rows for 30 records (and duplicate notifications). In a variant where an admin approves while a superuser rejects the same record, both calls returned 200 for 18/20 records and the final status (7 Rejected / 13 Verified) depended on commit order, while both users were told their decision succeeded.
- **Expected:** One 200 and one 400 "Record is not pending approval" per record; one approval activity-log row per record.

## Root Cause

Check-then-act without atomic conditional update (the batch endpoints use `query.filter(status.in_(pending)).update(...)`, which is atomic; the single-record endpoints do not).

## Affected Files

- `new/server/routes/emissions.py`

## Affected Features

Non-idempotent double submits; audit trail shows two approvals by different people; conflicting reviewer decisions both acknowledged.

## Required Changes

Use `UPDATE … SET status='Verified' WHERE id=:id AND status IN (…)` and check `rowcount == 1` (or optimistic version column), returning 409 otherwise.

Implement through the shared fix for RC-2 (Maker-checker / status policy duplicated per route) rather than a local patch.

## Database Changes

Optional `version` column on emissions for optimistic locking (or conditional UPDATE only).
 Ship as an Alembic migration (requires BUG-016).

## Backend Changes

Changes in `new/server/routes/emissions.py` as described above.

## Frontend Changes

None.

## Calculation Changes

None.

## Tests To Add/Change

- Port `audit/repro/BUG-074.py` into a pytest regression test under `new/server/tests/` (assert the Expected value; independent hand-derived numbers, not a second call to the same function).
- Add edge cases: zero, missing, negative, NaN/Inf, boundary values for every field the fix touches.
- Add the group-level invariant tests for RC-2 (see Root-Cause Groups).
- Review existing tests that assert the old behaviour; change an expected value only when the new value is independently derived and documented in the test.

## Browser Verification

- API/backend fix. After the fix, open the page(s) that consume this data (see Affected Features) and confirm the displayed value matches the API and DB.

## Regression Risks

- Status-policy changes alter who can approve and what edits reset records to Pending; re-run the full maker-checker role matrix (user, superuser, admin, it roles) for Scope 1/2/3, CAP and bulk.

## Acceptance Criteria

1. `audit/repro/BUG-074.py` exits 0 on the fixed code (it prints expected vs actual).
2. Expected behaviour holds: One 200 and one 400 "Record is not pending approval" per record; one approval activity-log row per record.
3. Full backend suite (`python -m pytest tests/` in `new/server`) and frontend checks (`npm run lint`, `npm run test`) pass.
4. No other open bug's repro changes from fail→pass or pass→fail unexpectedly (re-run `audit/work/rerun/run_all.sh`).

---

# BUG-093 — Region-restricted superuser can re-region its own facility (PUT /api/facilities/<id>), pushing the facility and all its emissions into another region's scope and out of its own

**Severity:** Medium · **Category:** Security · **Phase:** P4 · **Root cause group:** RC-3 · **Found by:** Agent I (Backend/API/Security)

**Current status:** **Still present** — `audit/repro/BUG-093.py` re-run on the final code: bug reproduced.

## Problem

Region-restricted superuser can re-region its own facility (PUT /api/facilities/<id>), pushing the facility and all its emissions into another region's scope and out of its own

- **Actual:** 200 "Facility updated"; facility 1 region is now "South", carrying its 153 emission rows into South users' scope and dashboards; the West superuser loses access to it (it no longer appears in their `/api/facilities`). Pulling a Center facility into West is correctly denied (403), because the current-region check runs first.
- **Expected:** 403 — a West-restricted superuser must not assign a facility to another region (same rule as create).

## Root Cause

Missing target-region validation in `update_facility`. Region membership (`get_allowed_facility_ids`) is derived from the editable `region` / `location` / `name` columns.

## Affected Files

- `new/server/routes/facilities.py`

## Affected Features

A regional superuser can inject its region's data (including Pending/Verified emissions it entered) into another region's inventory and reports, or hide a facility from its own region's reviewers. Region-level totals change without an admin.

## Required Changes

For non-unrestricted superusers, reject updates whose new `region` / `location` / `name` would move the facility outside `user.location` (reuse the create-path check); log old and new values.

Implement through the shared fix for RC-3 (Authorization / region scoping applied inconsistently) rather than a local patch.

## Database Changes

None required.

## Backend Changes

Changes in `new/server/routes/facilities.py` as described above.

## Frontend Changes

None.

## Calculation Changes

None.

## Tests To Add/Change

- Port `audit/repro/BUG-093.py` into a pytest regression test under `new/server/tests/` (assert the Expected value; independent hand-derived numbers, not a second call to the same function).
- Add edge cases: zero, missing, negative, NaN/Inf, boundary values for every field the fix touches.
- Add the group-level invariant tests for RC-3 (see Root-Cause Groups).
- Review existing tests that assert the old behaviour; change an expected value only when the new value is independently derived and documented in the test.

## Browser Verification

- API/backend fix. After the fix, open the page(s) that consume this data (see Affected Features) and confirm the displayed value matches the API and DB.

## Regression Risks

- Tightening authorization can lock out legitimate workflows (superuser bulk facility import, report downloads, audit trail). Re-run the endpoint role matrix in `audit/notes/I_endpoints.md`.

## Acceptance Criteria

1. `audit/repro/BUG-093.py` exits 0 on the fixed code (it prints expected vs actual).
2. Expected behaviour holds: 403 — a West-restricted superuser must not assign a facility to another region (same rule as create).
3. Full backend suite (`python -m pytest tests/` in `new/server`) and frontend checks (`npm run lint`, `npm run test`) pass.
4. No other open bug's repro changes from fail→pass or pass→fail unexpectedly (re-run `audit/work/rerun/run_all.sh`).

---

# BUG-032 — GET /api/manage/sbti ignores facility/region scoping: region-restricted users can read organisation-wide Verified emission totals for any year

**Severity:** Medium · **Category:** Security · **Phase:** P4 · **Root cause group:** RC-3 · **Found by:** Agent H (SBTi Auditor)

**Current status:** **Still present** — `audit/repro/BUG-032.py` re-run on the final code: bug reproduced.

## Problem

GET /api/manage/sbti ignores facility/region scoping: region-restricted users can read organisation-wide Verified emission totals for any year

- **Actual:** `suggested_base_year_emissions = 950.0` (includes the Center facility the user cannot access). Looping `base_year` over years yields the full org-wide annual total series.
- **Expected:** Either scoped to the caller's allowed facilities (450 t) or forbidden for non-admin roles — the sibling endpoint `/api/dashboard/sbti-trajectory` does apply `allowed_fids`.

## Root Cause

Missing `get_allowed_facility_ids` scoping in the baseline suggestion query.

## Affected Files

- `new/server/routes/managedata.py`

## Affected Features

Aggregate cross-region disclosure (org-wide yearly S1+S2+S3 totals) to region-restricted users. Limited to aggregate totals (no record detail), hence Medium.

## Required Changes

Apply `allowed_fids` to the three queries (or restrict the suggestion to admins), consistent with `/dashboard/sbti-trajectory`.

Implement through the shared fix for RC-3 (Authorization / region scoping applied inconsistently) rather than a local patch.

## Database Changes

None required.

## Backend Changes

Changes in `new/server/routes/managedata.py` as described above.

## Frontend Changes

None.

## Calculation Changes

None.

## Tests To Add/Change

- Port `audit/repro/BUG-032.py` into a pytest regression test under `new/server/tests/` (assert the Expected value; independent hand-derived numbers, not a second call to the same function).
- Add edge cases: zero, missing, negative, NaN/Inf, boundary values for every field the fix touches.
- Add the group-level invariant tests for RC-3 (see Root-Cause Groups).
- Review existing tests that assert the old behaviour; change an expected value only when the new value is independently derived and documented in the test.

## Browser Verification

- API/backend fix. After the fix, open the page(s) that consume this data (see Affected Features) and confirm the displayed value matches the API and DB.

## Regression Risks

- Tightening authorization can lock out legitimate workflows (superuser bulk facility import, report downloads, audit trail). Re-run the endpoint role matrix in `audit/notes/I_endpoints.md`.

## Acceptance Criteria

1. `audit/repro/BUG-032.py` exits 0 on the fixed code (it prints expected vs actual).
2. Expected behaviour holds: Either scoped to the caller's allowed facilities (450 t) or forbidden for non-admin roles — the sibling endpoint `/api/dashboard/sbti-trajectory` does apply `allowed_fids`.
3. Full backend suite (`python -m pytest tests/` in `new/server`) and frontend checks (`npm run lint`, `npm run test`) pass.
4. No other open bug's repro changes from fail→pass or pass→fail unexpectedly (re-run `audit/work/rerun/run_all.sh`).

---

# BUG-038 — Audit trail (/api/audit/, /api/audit/export) is not facility/region-scoped: a region-restricted superuser reads activity entries for every region's records

**Severity:** Medium · **Category:** Security · **Phase:** P4 · **Root cause group:** RC-3 · **Found by:** Agent I (Backend/API/Security)

**Current status:** **Still present** — `audit/repro/BUG-038.py` re-run on the final code: bug reproduced.

## Problem

Audit trail (/api/audit/, /api/audit/export) is not facility/region-scoped: a region-restricted superuser reads activity entries for every region's records

- **Actual:** 144 of the returned Emission entries concern facilities outside West (e.g. log 1249 → emission 671, facility 165 "North Africa": "Added Combustion emission: … for Updated Facility (1/2099)"). `/api/audit/export` returns the full 211 KB CSV incl. before/after diffs (`old_values`/`new_values`) of all regions.
- **Expected:** Only entries about records in the superuser's allowed facilities (the same scoping applied to `/api/emissions`, dashboards etc.).

## Root Cause

Audit queries apply role-based action filtering for IT only; no `get_allowed_facility_ids` scoping for regional roles. ActivityLog has no facility column, so scoping requires joining via entity/entity_id.

## Affected Files

- `new/server/routes/audit.py`

## Affected Features

Cross-region disclosure of activity (facility names, quantities, fuels, users, IPs, value diffs) to regional superusers, defeating the region isolation enforced elsewhere.

## Required Changes

Store facility_id on ActivityLog (or resolve through entity/entity_id) and filter by `get_allowed_facility_ids(user)` for non-unrestricted roles; or restrict the audit trail to admin/unrestricted superusers.

Implement through the shared fix for RC-3 (Authorization / region scoping applied inconsistently) rather than a local patch.

## Database Changes

Add nullable `facility_id` to `activity_log`, filled for new entries only (no backfill, per data policy); legacy entries without facility are visible to unrestricted roles only.
 Ship as an Alembic migration (requires BUG-016).

## Backend Changes

Changes in `new/server/routes/audit.py` as described above.

## Frontend Changes

None.

## Calculation Changes

None.

## Tests To Add/Change

- Port `audit/repro/BUG-038.py` into a pytest regression test under `new/server/tests/` (assert the Expected value; independent hand-derived numbers, not a second call to the same function).
- Add edge cases: zero, missing, negative, NaN/Inf, boundary values for every field the fix touches.
- Add the group-level invariant tests for RC-3 (see Root-Cause Groups).
- Review existing tests that assert the old behaviour; change an expected value only when the new value is independently derived and documented in the test.

## Browser Verification

- API/backend fix. After the fix, open the page(s) that consume this data (see Affected Features) and confirm the displayed value matches the API and DB.

## Regression Risks

- Tightening authorization can lock out legitimate workflows (superuser bulk facility import, report downloads, audit trail). Re-run the endpoint role matrix in `audit/notes/I_endpoints.md`.

## Acceptance Criteria

1. `audit/repro/BUG-038.py` exits 0 on the fixed code (it prints expected vs actual).
2. Expected behaviour holds: Only entries about records in the superuser's allowed facilities (the same scoping applied to `/api/emissions`, dashboards etc.).
3. Full backend suite (`python -m pytest tests/` in `new/server`) and frontend checks (`npm run lint`, `npm run test`) pass.
4. No other open bug's repro changes from fail→pass or pass→fail unexpectedly (re-run `audit/work/rerun/run_all.sh`).

---

# BUG-046 — Equity-share allocation ignores effective dates (time-sliced ownership never applied) and POST /api/equity/shares accepts any percentage (500, -50, inf) from any business role

**Severity:** High · **Category:** API · **Phase:** P4 · **Root cause group:** RC-3 · **Found by:** Agent I (Backend/API/Security)

**Current status:** **Still present** — `audit/repro/BUG-046.py` re-run on the final code: bug reproduced.

## Problem

Equity-share allocation ignores effective dates (time-sliced ownership never applied) and POST /api/equity/shares accepts any percentage (500, -50, inf) from any business role

- **Actual:** Sonatrach pct 51.0, allocated 360,031.27 tCO2e (uses the expired 2021 slice). 500 and -50 and inf saved with 200; "nan" and "abc" → HTTP 500. A `user`-role account got 200 setting a 99 % partner share on its own facility 1.
- **Expected:** 2025 Sonatrach share = 70 % → 494,160.57 tCO2e. Percentages outside 0–100 or non-numeric rejected with 400.

## Root Cause

Missing date filter when selecting the active slice; no input validation on the write endpoint.

## Affected Files

- `new/server/routes/equity_routes.py`

## Affected Features

Equity-share (JV partner) emission allocations are wrong for any facility whose ownership changed, and allocations can exceed 100 % / go negative; ownership data can be modified by data-entry users without review.

## Required Changes

Select shares where `effective_start_date <= year-end` and (`effective_end_date` is null or `>= year-start`), pro-rating mid-year changes; validate 0 ≤ pct ≤ 100, finite, and per-period sum ≤ 100; restrict writes to admin/superuser; return 400 on parse errors.

Implement through the shared fix for RC-3 (Authorization / region scoping applied inconsistently) rather than a local patch.

## Database Changes

Validation only (no schema change) unless a per-period sum constraint is enforced in DB.

## Backend Changes

Changes in `new/server/routes/equity_routes.py` as described above.

## Frontend Changes

None.

## Calculation Changes

None.

## Tests To Add/Change

- Port `audit/repro/BUG-046.py` into a pytest regression test under `new/server/tests/` (assert the Expected value; independent hand-derived numbers, not a second call to the same function).
- Add edge cases: zero, missing, negative, NaN/Inf, boundary values for every field the fix touches.
- Add the group-level invariant tests for RC-3 (see Root-Cause Groups).
- Review existing tests that assert the old behaviour; change an expected value only when the new value is independently derived and documented in the test.

## Browser Verification

- API/backend fix. After the fix, open the page(s) that consume this data (see Affected Features) and confirm the displayed value matches the API and DB.

## Regression Risks

- Tightening authorization can lock out legitimate workflows (superuser bulk facility import, report downloads, audit trail). Re-run the endpoint role matrix in `audit/notes/I_endpoints.md`.

## Acceptance Criteria

1. `audit/repro/BUG-046.py` exits 0 on the fixed code (it prints expected vs actual).
2. Expected behaviour holds: 2025 Sonatrach share = 70 % → 494,160.57 tCO2e. Percentages outside 0–100 or non-numeric rejected with 400.
3. Full backend suite (`python -m pytest tests/` in `new/server`) and frontend checks (`npm run lint`, `npm run test`) pass.
4. No other open bug's repro changes from fail→pass or pass→fail unexpectedly (re-run `audit/work/rerun/run_all.sh`).

---

# BUG-076 — Bulk-upload job status and error CSV have no owner check: any logged-in account (incl. it_admin) can read another user's job rows; absolute server temp path is disclosed

**Severity:** Low · **Category:** Security · **Phase:** P4 · **Root cause group:** RC-3 · **Found by:** Agent I (Backend/API/Security)

**Current status:** **Still present** — `audit/repro/BUG-076.py` re-run on the final code: bug reproduced.

## Problem

Bulk-upload job status and error CSV have no owner check: any logged-in account (incl. it_admin) can read another user's job rows; absolute server temp path is disclosed

- **Actual:** Both 200 for it_admin: `skipped_preview` contains the uploaded rows (facility, quantity, reason), `error_csv_path = C:\Users\samsung\AppData\Local\Temp\tmp….csv_errors.csv`, error CSV downloaded (228 bytes).
- **Expected:** 403/404 for anyone but the uploader (and admins); no server filesystem path in the response.

## Root Cause

Job records lack an owner field; endpoints don't authorize.

## Affected Files

- `new/server/routes/emissions.py`

## Affected Features

Exploitation requires the job UUID (uuid4, not guessable), so severity is Low; but job ids appear in logs/URLs and IT roles are meant to have zero business-data access. Path disclosure aids other attacks.

## Required Changes

Store `user_id` in the job dict; return 404 unless `session user == owner` (or admin); drop `error_csv_path` from the response.

Implement through the shared fix for RC-3 (Authorization / region scoping applied inconsistently) rather than a local patch.

## Database Changes

None required.

## Backend Changes

Changes in `new/server/routes/emissions.py` as described above.

## Frontend Changes

None.

## Calculation Changes

None.

## Tests To Add/Change

- Port `audit/repro/BUG-076.py` into a pytest regression test under `new/server/tests/` (assert the Expected value; independent hand-derived numbers, not a second call to the same function).
- Add edge cases: zero, missing, negative, NaN/Inf, boundary values for every field the fix touches.
- Add the group-level invariant tests for RC-3 (see Root-Cause Groups).
- Review existing tests that assert the old behaviour; change an expected value only when the new value is independently derived and documented in the test.

## Browser Verification

- API/backend fix. After the fix, open the page(s) that consume this data (see Affected Features) and confirm the displayed value matches the API and DB.

## Regression Risks

- Tightening authorization can lock out legitimate workflows (superuser bulk facility import, report downloads, audit trail). Re-run the endpoint role matrix in `audit/notes/I_endpoints.md`.

## Acceptance Criteria

1. `audit/repro/BUG-076.py` exits 0 on the fixed code (it prints expected vs actual).
2. Expected behaviour holds: 403/404 for anyone but the uploader (and admins); no server filesystem path in the response.
3. Full backend suite (`python -m pytest tests/` in `new/server`) and frontend checks (`npm run lint`, `npm run test`) pass.
4. No other open bug's repro changes from fail→pass or pass→fail unexpectedly (re-run `audit/work/rerun/run_all.sh`).

---

# BUG-106 — User Management actions are missing from the Audit Trail: account creation and logout logs are never committed, and user deletion is not logged at all

**Severity:** Medium · **Category:** Security · **Phase:** P4 · **Root cause group:** RC-3 · **Found by:** Agent K (Frontend/UI)

**Current status:** **Still present** — `audit/repro/BUG-106.py` re-run on the final code: bug reproduced.

## Problem

User Management actions are missing from the Audit Trail: account creation and logout logs are never committed, and user deletion is not logged at all

- **Actual:** `register 201`, `delete 200`, `logout 200`; `activity_log` contains no row mentioning the user's email and `select count(*) … where action='LOGOUT'` = 0. The UI DB (audit/db/ui.db) after a full day of activity has actions CREATE/DELETE/EXPORT/LOGIN/UPDATE only — never REGISTER or LOGOUT.
- **Expected:** Audit Trail entries for REGISTER/CREATE user, DELETE user and LOGOUT.

## Root Cause

Log helper called after the only commit (register, logout); missing call (delete_user).

## Affected Files

- `new/server/routes/auth.py`

## Affected Features

Privileged account lifecycle (who created or removed which account, when) cannot be reconstructed from the Audit Trail; the Audit Trail page gives an incomplete record for IT/security review.

## Required Changes

Call the logger before the commit (or commit again afterwards) in register/logout, and log DELETE in delete_user with the deleted user's identity.

Implement through the shared fix for RC-3 (Authorization / region scoping applied inconsistently) rather than a local patch.

## Database Changes

None required.

## Backend Changes

Changes in `new/server/routes/auth.py` as described above.

## Frontend Changes

None.

## Calculation Changes

None.

## Tests To Add/Change

- Port `audit/repro/BUG-106.py` into a pytest regression test under `new/server/tests/` (assert the Expected value; independent hand-derived numbers, not a second call to the same function).
- Add edge cases: zero, missing, negative, NaN/Inf, boundary values for every field the fix touches.
- Add the group-level invariant tests for RC-3 (see Root-Cause Groups).
- Review existing tests that assert the old behaviour; change an expected value only when the new value is independently derived and documented in the test.

## Browser Verification

- API/backend fix. After the fix, open the page(s) that consume this data (see Affected Features) and confirm the displayed value matches the API and DB.

## Regression Risks

- Tightening authorization can lock out legitimate workflows (superuser bulk facility import, report downloads, audit trail). Re-run the endpoint role matrix in `audit/notes/I_endpoints.md`.

## Acceptance Criteria

1. `audit/repro/BUG-106.py` exits 0 on the fixed code (it prints expected vs actual).
2. Expected behaviour holds: Audit Trail entries for REGISTER/CREATE user, DELETE user and LOGOUT.
3. Full backend suite (`python -m pytest tests/` in `new/server`) and frontend checks (`npm run lint`, `npm run test`) pass.
4. No other open bug's repro changes from fail→pass or pass→fail unexpectedly (re-run `audit/work/rerun/run_all.sh`).

---

# BUG-087 — Malformed input on create endpoints returns HTTP 500/409 with raw exception and SQL text (≈40 handlers return `str(e)`)

**Severity:** Low · **Category:** API · **Phase:** P4 · **Root cause group:** RC-1 · **Found by:** Agent I (Backend/API/Security)

**Current status:** **Still present** — `audit/repro/BUG-087.py` re-run on the final code: bug reproduced.

## Problem

Malformed input on create endpoints returns HTTP 500/409 with raw exception and SQL text (≈40 handlers return `str(e)`)

- **Actual:** ``` /api/emissions/: HTTP 500 "(sqlite3.ProgrammingError) Error binding parameter 7: type 'list' is not supported\n[SQL: INSERT INTO e..." /api/scope2: HTTP 500 "(sqlite3.IntegrityError) FOREIGN KEY constraint failed\n[SQL: INSERT INTO scope2_emissions (fac..." /api/data/production: HTTP 409 "Concurrency conflict: (sqlite3.IntegrityError) NOT NULL constraint failed: production_data.year\n[SQL: ..." /api/goals: HTTP 500 "invalid literal for int() with base 10: 'abc'" /api/sources: HTTP 500 "Failed to add source: Python int too large to convert to SQLite INTEGER" ``` A fuzz of 15 create endpoin…
- **Expected:** 400 with a field-level validation message; no internals.

## Root Cause

No schema validation of request types; broad `except Exception` handlers echo the exception.

## Affected Files

- See Location in AUDIT_FINDINGS.md: Handlers that catch `Exception` and return `jsonify({"error": ... str(e)})` — 41 occurrences, e.g. `routes/emissions.py:962,3187`, `routes/scope2.py:156,287,475,666`, `routes/scope3.py:155,299,473`, `routes/data.py:343,563,642,846,880`, `routes/managedata.py:102,138,222,347,372,426,516,724,766,808,…

## Affected Features

Schema/table/column disclosure; wrong status codes (500/409 instead of 400) hamper clients and monitoring.

## Required Changes

Validate types/required fields up front (400); log exceptions server-side and return a generic message with request id.

Implement through the shared fix for RC-1 (No central input validation) rather than a local patch.

## Database Changes

None required.

## Backend Changes

None beyond the above.

## Frontend Changes

None.

## Calculation Changes

None.

## Tests To Add/Change

- Port `audit/repro/BUG-087.py` into a pytest regression test under `new/server/tests/` (assert the Expected value; independent hand-derived numbers, not a second call to the same function).
- Add edge cases: zero, missing, negative, NaN/Inf, boundary values for every field the fix touches.
- Add the group-level invariant tests for RC-1 (see Root-Cause Groups).
- Review existing tests that assert the old behaviour; change an expected value only when the new value is independently derived and documented in the test.

## Browser Verification

- API/backend fix. After the fix, open the page(s) that consume this data (see Affected Features) and confirm the displayed value matches the API and DB.

## Regression Risks

- Stricter validation will reject inputs accepted today (existing bulk templates, integrations, scripts). Existing invalid rows remain until a cleanup job runs.

## Acceptance Criteria

1. `audit/repro/BUG-087.py` exits 0 on the fixed code (it prints expected vs actual).
2. Expected behaviour holds: 400 with a field-level validation message; no internals.
3. Full backend suite (`python -m pytest tests/` in `new/server`) and frontend checks (`npm run lint`, `npm run test`) pass.
4. No other open bug's repro changes from fail→pass or pass→fail unexpectedly (re-run `audit/work/rerun/run_all.sh`).

---


# PHASE P5 — Database defects

_Phase regression risk:_ New unique constraints fail on existing duplicate rows — de-duplicate (with owner sign-off) before adding them.

---

# BUG-057 — Bulk upload with "Overwrite Duplicates" enabled inserts every in-file duplicate row as a separate record (double counting)

**Severity:** High · **Category:** Database · **Phase:** P5 · **Root cause group:** RC-10 · **Found by:** Agent J (Database)

**Current status:** **Still present** — `audit/repro/BUG-057.py` re-run on the final code: bug reproduced.

## Problem

Bulk upload with "Overwrite Duplicates" enabled inserts every in-file duplicate row as a separate record (double counting)

- **Actual:** - overwrite=true → **3 records inserted** (3 × 8.81 = 26.42 t CO2e instead of 8.81). - overwrite=false → 1 inserted, 2 rejected "Duplicate record…" (correct).
- **Expected:** Overwrite mode: the key (facility, year, month, process, fuel, equipment) ends with exactly one record (last row wins). Non-overwrite mode: 1 inserted, 2 rejected as duplicates.

## Root Cause

A newly-seen key is stored as `batch_keys[key] = None` (the new object has no id yet). On a later in-file hit with overwrite enabled, `existing_id` is None → `existing_obj` is None → the `if existing_obj:` branch is skipped and execution falls through to creating another new record. The "overwrite" option is thus less safe than the default.

## Affected Files

- `new/server/background_processor.py`

## Affected Features

Users who enable "Overwrite Duplicates" precisely to make re-uploads idempotent get duplicated emissions whenever a file contains a repeated key (common with re-exported spreadsheets); once approved, the Scope 1/2/3 totals are double counted. The DB has no unique constraint on emissions to catch it (only production_data has one). The snapshot already contains 16 Scope 1 duplicate groups (51 rows), 2 Scope 2 and 2 Scope 3 groups, e.g. facility 5 2025-03 flaring 15000 ×5 inserted in the same second.

## Required Changes

Store the pending object itself in `batch_keys` (as `_process_row_production` does with `batch_prod_map`) and update it in place on in-file repeats; add a DB unique index on the natural key (or at least a QA duplicate check).

Implement through the shared fix for RC-10 (Bulk import integrity) rather than a local patch.

## Database Changes

Data policy: block new bad data only — no unique index (existing duplicate groups would violate it). Enforce the natural key in application code (in-batch map + existing-key check). Existing duplicates remain.

## Backend Changes

Changes in `new/server/background_processor.py` as described above.

## Frontend Changes

None.

## Calculation Changes

None.

## Tests To Add/Change

- Port `audit/repro/BUG-057.py` into a pytest regression test under `new/server/tests/` (assert the Expected value; independent hand-derived numbers, not a second call to the same function).
- Add edge cases: zero, missing, negative, NaN/Inf, boundary values for every field the fix touches.
- Add the group-level invariant tests for RC-10 (see Root-Cause Groups).
- Review existing tests that assert the old behaviour; change an expected value only when the new value is independently derived and documented in the test.

## Browser Verification

- API/backend fix. After the fix, open the page(s) that consume this data (see Affected Features) and confirm the displayed value matches the API and DB.

## Regression Risks

- Bulk imports that previously succeeded may now fail row validation or de-duplicate differently; unique indexes fail on existing duplicates until cleaned.

## Acceptance Criteria

1. `audit/repro/BUG-057.py` exits 0 on the fixed code (it prints expected vs actual).
2. Expected behaviour holds: Overwrite mode: the key (facility, year, month, process, fuel, equipment) ends with exactly one record (last row wins). Non-overwrite mode: 1 inserted, 2 rejected as duplicates.
3. Full backend suite (`python -m pytest tests/` in `new/server`) and frontend checks (`npm run lint`, `npm run test`) pass.
4. No other open bug's repro changes from fail→pass or pass→fail unexpectedly (re-run `audit/work/rerun/run_all.sh`).

---

# BUG-081 — Scope 2/3 bulk import duplicate key is too coarse: separate meters and sub-categories in the same facility-month are rejected as "duplicates", or with Overwrite they replace a different existing record

**Severity:** High · **Category:** Emissions · **Phase:** P5 · **Root cause group:** RC-10 · **Found by:** Agent B (Emissions Auditor) · **Independent confirmations:** 1

**Current status:** **Still present** — `audit/repro/BUG-081.py` re-run on the final code: bug reproduced.

## Problem

Scope 2/3 bulk import duplicate key is too coarse: separate meters and sub-categories in the same facility-month are rejected as "duplicates", or with Overwrite they replace a different existing record

- **Actual:** ``` S3 same cat/month two sub-categories: expected 2 rows 0.23 t, actual {'n': 1, 's': 0.2} S2 two meters same month: expected 2 rows 3000 kWh, actual {'n': 1, 's': 1000.0} S3 2nd upload w/ overwrite, other sub-category: expected 2 rows 0.23 t, actual {'n': 1, 's': 0.03} ``` - Without overwrite, the second line is skipped: "Duplicate record: Scope 3 emission for facility 'ADR' (2037-03, Category 6) already exists". - With overwrite, the existing Air-travel record is silently turned into Hotel nights (0.2 t becomes 0.03 t, and it is set back to Pending). - The EEIO spend path allows only one C…
- **Expected:** The rows are distinct activity lines, not duplicates. Scope 3 2037-03 gives 2 rows and 0.23 t. Scope 2 2037-03 gives 2 rows and 3000 kWh. Scope 3 2037-05 gives 2 rows and 0.23 t.

## Root Cause

The dedup key identifies a Scope 2/3 record by facility, month and category/source type only. Real inventories have many lines per category per month: purchased goods by commodity, business travel by mode, multiple meters and suppliers. Scope 1 by contrast includes fuel and equipment_id in its key.

## Affected Files

- `new/server/background_processor.py`

## Affected Features

Bulk-imported Scope 2 and Scope 3 inventories are silently incomplete: only the first line per category-month survives. With "Overwrite Duplicates" on, unrelated existing records are replaced, which destroys data. Scope 3 Category 1 spend-based (EEIO) inventories can hold only one NAICS line per month.

## Required Changes

Include sub_category, meter/grid_region, NAICS code (and ideally unit and an optional external row id) in the key. Exclude Rejected and Draft rows from the pre-loaded duplicate set, or handle them explicitly. Never overwrite a record whose descriptive fields differ.

Implement through the shared fix for RC-10 (Bulk import integrity) rather than a local patch.

## Database Changes

Extend the Scope 2/3 natural key (sub_category, meter/grid_region, NAICS) in application code; no DB unique index (data policy: existing rows untouched).

## Backend Changes

Changes in `new/server/background_processor.py` as described above.

## Frontend Changes

None.

## Calculation Changes

None.

## Tests To Add/Change

- Port `audit/repro/BUG-081.py` into a pytest regression test under `new/server/tests/` (assert the Expected value; independent hand-derived numbers, not a second call to the same function).
- Add edge cases: zero, missing, negative, NaN/Inf, boundary values for every field the fix touches.
- Add the group-level invariant tests for RC-10 (see Root-Cause Groups).
- Review existing tests that assert the old behaviour; change an expected value only when the new value is independently derived and documented in the test.

## Browser Verification

- API/backend fix. After the fix, open the page(s) that consume this data (see Affected Features) and confirm the displayed value matches the API and DB.

## Regression Risks

- Bulk imports that previously succeeded may now fail row validation or de-duplicate differently; unique indexes fail on existing duplicates until cleaned.

## Acceptance Criteria

1. `audit/repro/BUG-081.py` exits 0 on the fixed code (it prints expected vs actual).
2. Expected behaviour holds: The rows are distinct activity lines, not duplicates. Scope 3 2037-03 gives 2 rows and 0.23 t. Scope 2 2037-03 gives 2 rows and 3000 kWh. Scope 3 2037-05 gives 2 rows and 0.23 t.
3. Full backend suite (`python -m pytest tests/` in `new/server`) and frontend checks (`npm run lint`, `npm run test`) pass.
4. No other open bug's repro changes from fail→pass or pass→fail unexpectedly (re-run `audit/work/rerun/run_all.sh`).

---

# BUG-089 — Scope 3 category is stored as "6" by the UI/API and as "Category 6" by bulk import: cross-channel duplicates are not detected (double counting) and category breakdowns split

**Severity:** Medium · **Category:** Emissions · **Phase:** P5 · **Root cause group:** RC-10 · **Found by:** Agent B (Emissions Auditor)

**Current status:** **Still present** — `audit/repro/BUG-089.py` re-run on the final code: bug reproduced.

## Problem

Scope 3 category is stored as "6" by the UI/API and as "Category 6" by bulk import: cross-channel duplicates are not detected (double counting) and category breakdowns split

- **Actual:** ``` UI create: 201 ; bulk skipped: 0 rows: [{'id': 29, 'category': '6', ... 'co2e': 0.2, 'status': 'Verified'}, {'id': 30, 'category': 'Category 6', ... 'co2e': 0.2, 'status': 'Pending'}] ``` Once the bulk row is approved, the activity is counted twice. The snapshot already mixes labels: category `'11'` (1 row, 216.85 t, the only material Verified Scope 3 row) next to `'Category 11'`, and `'Category 1'`...`'Category 15'` from other paths. Per-category views (uncertainty items, reports, exports) show "11" and "Category 11" as different categories.
- **Expected:** One canonical category label. The bulk row is reported as a duplicate of the existing record, which is what happens for Scope 1 and for bulk-vs-bulk Scope 3.

## Root Cause

There is no canonical category representation. The API accepts any string or integer, and only the bulk path normalises it.

## Affected Files

- `new/client/src/components/Scope3Form.jsx`
- `new/server/routes/scope3.py`

## Affected Features

Scope 3 records entered through different channels are double counted, because the duplicate protection is bypassed. Category-level totals, uncertainty groupings and GHG-Protocol category reporting are fragmented. There is also no validation that the category is 1-15 (see also BUG-085).

## Required Changes

Normalise the category to a single canonical form (e.g. integer 1-15 or "Category N") in every create, update and bulk path. Reject values outside 1-15. Migrate existing rows.

Implement through the shared fix for RC-10 (Bulk import integrity) rather than a local patch.

## Database Changes

Data policy: block new bad data only — no migration of stored values. Normalise on every write; aggregations must map legacy '6' / 'Category 6' to one key when grouping so breakdowns stop splitting.

## Backend Changes

Changes in `new/server/routes/scope3.py` as described above.

## Frontend Changes

Changes in `new/client/src/components/Scope3Form.jsx` as described above.

## Calculation Changes

None.

## Tests To Add/Change

- Port `audit/repro/BUG-089.py` into a pytest regression test under `new/server/tests/` (assert the Expected value; independent hand-derived numbers, not a second call to the same function).
- Add edge cases: zero, missing, negative, NaN/Inf, boundary values for every field the fix touches.
- Add the group-level invariant tests for RC-10 (see Root-Cause Groups).
- Review existing tests that assert the old behaviour; change an expected value only when the new value is independently derived and documented in the test.

## Browser Verification

- Reproduce the steps in AUDIT_FINDINGS.md on an isolated stack (`audit/tools/vite_audit.mjs` + backend on an audit DB copy) and confirm the Expected result on screen.
- Compare the UI value with the API response and the DB row for the same record; refresh and reopen the record.

## Regression Risks

- Bulk imports that previously succeeded may now fail row validation or de-duplicate differently; unique indexes fail on existing duplicates until cleaned.

## Acceptance Criteria

1. `audit/repro/BUG-089.py` exits 0 on the fixed code (it prints expected vs actual).
2. Expected behaviour holds: One canonical category label. The bulk row is reported as a duplicate of the existing record, which is what happens for Scope 1 and for bulk-vs-bulk Scope 3.
3. Full backend suite (`python -m pytest tests/` in `new/server`) and frontend checks (`npm run lint`, `npm run test`) pass.
4. No other open bug's repro changes from fail→pass or pass→fail unexpectedly (re-run `audit/work/rerun/run_all.sh`).

---

# BUG-058 — Bulk-upload overwrite rewrites approved records without an audit trail and leaves them "Pending" but still marked approved

**Severity:** Medium · **Category:** Database · **Phase:** P5 · **Root cause group:** RC-2, RC-10 · **Found by:** Agent J (Database)

**Current status:** **Still present** — `audit/repro/BUG-058.py` re-run on the final code: bug reproduced.

## Problem

Bulk-upload overwrite rewrites approved records without an audit trail and leaves them "Pending" but still marked approved

- **Actual:** Record 7: `status=Pending, approved_by=1, approved_at=2026-09-22 19:15:13, quantity 10→20, co2e 2325.12→4650.24`. **Zero** activity_log rows were written for the upload (only notifications to admins).
- **Expected:** Status reset to Pending **and** `approved_by`/`approved_at` cleared (as the manual edit paths do: `emissions.py:3426/3481`, `scope2.py:379`, `scope3.py:240/283`); an ActivityLog UPDATE/IMPORT entry with old and new values.

## Root Cause

Overwrite branches only partially reset maker-checker state; bulk processor has no audit logging at all.

## Affected Files

- `new/server/background_processor.py`

## Affected Features

Verified inventory values can be replaced in bulk with no record of the previous value or who changed it (verifier/ISO 14064 audit-trail gap). Records end in a contradictory state (Pending yet carrying an approver and approval time), so any report/QA logic using `approved_by IS NOT NULL` treats them as approved; the approval evidence refers to numbers that no longer exist.

## Required Changes

In overwrite branches clear `approved_by`/`approved_at` (and set `updated_by`), capture old values, and write one ActivityLog per overwritten record plus one IMPORT summary per job, committed in the same transaction as the data.

Implement through the shared fix for RC-2 (Maker-checker / status policy duplicated per route), RC-10 (Bulk import integrity) rather than a local patch.

## Database Changes

None required.

## Backend Changes

Changes in `new/server/background_processor.py` as described above.

## Frontend Changes

None.

## Calculation Changes

None.

## Tests To Add/Change

- Port `audit/repro/BUG-058.py` into a pytest regression test under `new/server/tests/` (assert the Expected value; independent hand-derived numbers, not a second call to the same function).
- Add edge cases: zero, missing, negative, NaN/Inf, boundary values for every field the fix touches.
- Add the group-level invariant tests for RC-2, RC-10 (see Root-Cause Groups).
- Review existing tests that assert the old behaviour; change an expected value only when the new value is independently derived and documented in the test.

## Browser Verification

- API/backend fix. After the fix, open the page(s) that consume this data (see Affected Features) and confirm the displayed value matches the API and DB.

## Regression Risks

- Status-policy changes alter who can approve and what edits reset records to Pending; re-run the full maker-checker role matrix (user, superuser, admin, it roles) for Scope 1/2/3, CAP and bulk.
- Bulk imports that previously succeeded may now fail row validation or de-duplicate differently; unique indexes fail on existing duplicates until cleaned.

## Acceptance Criteria

1. `audit/repro/BUG-058.py` exits 0 on the fixed code (it prints expected vs actual).
2. Expected behaviour holds: Status reset to Pending **and** `approved_by`/`approved_at` cleared (as the manual edit paths do: `emissions.py:3426/3481`, `scope2.py:379`, `scope3.py:240/283`); an ActivityLog UPDATE/IMPORT entry with old and new values.
3. Full backend suite (`python -m pytest tests/` in `new/server`) and frontend checks (`npm run lint`, `npm run test`) pass.
4. No other open bug's repro changes from fail→pass or pass→fail unexpectedly (re-run `audit/work/rerun/run_all.sh`).

---

# BUG-065 — Custom factor names are not unique, yet bulk import resolves factors by name: the most recently created same-named factor is silently applied

**Severity:** Medium · **Category:** Database · **Phase:** P5 · **Root cause group:** RC-10 · **Found by:** Agent J (Database)

**Current status:** **Still present** — `audit/repro/BUG-065.py` re-run on the final code: bug reproduced.

## Problem

Custom factor names are not unique, yet bulk import resolves factors by name: the most recently created same-named factor is silently applied

- **Actual:** Both saved. Import silently used factor id 103: `ef_used_co2=100, co2_emissions=100 t` (100× the other factor). Which factor is chosen depends only on row order in the table; the delete-guard (`fuel_type == factor.name`) also cannot tell same-named factors apart.
- **Expected:** Second create rejected (409) or the uploader forced to disambiguate; result would be 1.0 t CO2 with the first factor.

## Root Cause

Custom factors are referenced by free-text name everywhere, but the name has no uniqueness constraint or validation (including case-insensitive collisions, since lookups use `lower()`).

## Affected Files

- `new/server/background_processor.py`
- `new/server/models.py`
- `new/server/routes/custom_factors.py`

## Affected Features

Any organisation with two users each saving e.g. "Fuel Gas" (or a superuser saving a revised version under the same name) gets Tier 2 imports computed with whichever was created last, without warning; emissions can be off by the ratio of the two factors.

## Required Changes

Add a (case-insensitive) unique constraint on `custom_factors.name` (or name+unit+version) and reject duplicates on create/rename/import; reference factors by id in records.

Implement through the shared fix for RC-10 (Bulk import integrity) rather than a local patch.

## Database Changes

Data policy: block new bad data only — application-level case-insensitive uniqueness check on create/rename/import; no DB constraint while duplicates exist.

## Backend Changes

Changes in `new/server/background_processor.py`, `new/server/routes/custom_factors.py` as described above.

## Frontend Changes

None.

## Calculation Changes

None.

## Tests To Add/Change

- Port `audit/repro/BUG-065.py` into a pytest regression test under `new/server/tests/` (assert the Expected value; independent hand-derived numbers, not a second call to the same function).
- Add edge cases: zero, missing, negative, NaN/Inf, boundary values for every field the fix touches.
- Add the group-level invariant tests for RC-10 (see Root-Cause Groups).
- Review existing tests that assert the old behaviour; change an expected value only when the new value is independently derived and documented in the test.

## Browser Verification

- API/backend fix. After the fix, open the page(s) that consume this data (see Affected Features) and confirm the displayed value matches the API and DB.

## Regression Risks

- Bulk imports that previously succeeded may now fail row validation or de-duplicate differently; unique indexes fail on existing duplicates until cleaned.

## Acceptance Criteria

1. `audit/repro/BUG-065.py` exits 0 on the fixed code (it prints expected vs actual).
2. Expected behaviour holds: Second create rejected (409) or the uploader forced to disambiguate; result would be 1.0 t CO2 with the first factor.
3. Full backend suite (`python -m pytest tests/` in `new/server`) and frontend checks (`npm run lint`, `npm run test`) pass.
4. No other open bug's repro changes from fail→pass or pass→fail unexpectedly (re-run `audit/work/rerun/run_all.sh`).

---

# BUG-056 — Custom factors used by Tier 2 records can be deleted: the reference check matches `fuel_type == factor name`, but UI records store the factor id, which SQLite then reuses for the next factor

**Severity:** Medium · **Category:** Database · **Phase:** P5 · **Root cause group:** RC-11 · **Found by:** Agent C (Tier / Factor Auditor)

**Current status:** **Still present** — `audit/repro/BUG-056.py` re-run on the final code: bug reproduced.

## Problem

Custom factors used by Tier 2 records can be deleted: the reference check matches `fuel_type == factor name`, but UI records store the factor id, which SQLite then reuses for the next factor

- **Actual:** The DELETE returns 200 and the factor row is removed. The next custom factor created gets id 102 again, so the record's stored fuel_type / custom_factor_id now point to an unrelated factor ("Unrelated diesel EF").
- **Expected:** 409 "referenced by 1 emission records", as the route intends.

## Root Cause

The reference check compares by name, but the UI links records by id. There is also no FK from emissions to custom_factors, and ids are reused.

## Affected Files

- `new/client/src/components/Scope1Form.jsx`
- `new/server/routes/custom_factors.py`

## Affected Features

- The audit trail for Tier 2 records breaks: the factor behind a reported number disappears, or is replaced by another factor under the same id. - A later recalculation (see the Tier 2 recalculation bug) or an audit lookup resolves the wrong factor. - The dashboards shared with Tier 2 records cannot be traced to their EF.

## Required Changes

- Store `custom_factor_id` as a real FK column on emissions. - Block deletion by id reference (and by the name for legacy rows), or soft-archive factors. - Use AUTOINCREMENT, or never reuse ids.

Implement through the shared fix for RC-11 (Referential integrity on delete) rather than a local patch.

## Database Changes

Add `emissions.custom_factor_id` FK; AUTOINCREMENT on `custom_factors.id`.
 Ship as an Alembic migration (requires BUG-016).

## Backend Changes

Changes in `new/server/routes/custom_factors.py` as described above.

## Frontend Changes

Changes in `new/client/src/components/Scope1Form.jsx` as described above.

## Calculation Changes

None.

## Tests To Add/Change

- Port `audit/repro/BUG-056.py` into a pytest regression test under `new/server/tests/` (assert the Expected value; independent hand-derived numbers, not a second call to the same function).
- Add edge cases: zero, missing, negative, NaN/Inf, boundary values for every field the fix touches.
- Add the group-level invariant tests for RC-11 (see Root-Cause Groups).
- Review existing tests that assert the old behaviour; change an expected value only when the new value is independently derived and documented in the test.

## Browser Verification

- Reproduce the steps in AUDIT_FINDINGS.md on an isolated stack (`audit/tools/vite_audit.mjs` + backend on an audit DB copy) and confirm the Expected result on screen.
- Compare the UI value with the API response and the DB row for the same record; refresh and reopen the record.

## Regression Risks

- Soft-delete changes list/lookup queries everywhere (must filter inactive rows).

## Acceptance Criteria

1. `audit/repro/BUG-056.py` exits 0 on the fixed code (it prints expected vs actual).
2. Expected behaviour holds: 409 "referenced by 1 emission records", as the route intends.
3. Full backend suite (`python -m pytest tests/` in `new/server`) and frontend checks (`npm run lint`, `npm run test`) pass.
4. No other open bug's repro changes from fail→pass or pass→fail unexpectedly (re-run `audit/work/rerun/run_all.sh`).

---

# BUG-009 — Deleting a facility that has any OGMP level-upgrade log fails with 500 (FK violation) and leaks raw SQL

**Severity:** Medium · **Category:** Database · **Phase:** P5 · **Root cause group:** RC-11 · **Found by:** Agent J (Database)

**Current status:** **Still present** — `audit/repro/BUG-009.py` re-run on the final code: bug reproduced.

## Problem

Deleting a facility that has any OGMP level-upgrade log fails with 500 (FK violation) and leaks raw SQL

- **Actual:** `500 {"error": "Failed to delete facility: (sqlite3.IntegrityError) FOREIGN KEY constraint failed\n[SQL: DELETE FROM facilities WHERE facilities.id = ?]..."}`. Facility 2 (no log) deletes fine with 200.
- **Expected:** Either the facility and its dependent rows are deleted (as for every other child table), or a clear 409 "facility has dependent OGMP level logs" is returned.

## Root Cause

`LevelUpgradeLog` is the only facility child table without a delete cascade (or `ondelete`), and its `facility_id` is NOT NULL, so SQLAlchemy cannot null it and SQLite rejects the parent delete.

## Affected Files

- `new/server/models.py`
- `new/server/routes/facilities.py`

## Affected Features

Once anyone logs an OGMP level upgrade for a facility (normal OGMP workflow), that facility can never be deleted through the app. The error body exposes internal SQL text to the client. (On Postgres the same FK error occurs.)

## Required Changes

Add `level_upgrade_logs = db.relationship("LevelUpgradeLog", backref=..., cascade="all, delete-orphan")` on Facility (or `ondelete="CASCADE"` + passive_deletes), or explicitly block with a 409 and a clean message; never echo `str(e)` to the client.

Implement through the shared fix for RC-11 (Referential integrity on delete) rather than a local patch.

## Database Changes

ON DELETE behaviour for `level_upgrade_logs.facility_id` (cascade or block with 409).
 Ship as an Alembic migration (requires BUG-016).

## Backend Changes

Changes in `new/server/routes/facilities.py` as described above.

## Frontend Changes

None.

## Calculation Changes

None.

## Tests To Add/Change

- Port `audit/repro/BUG-009.py` into a pytest regression test under `new/server/tests/` (assert the Expected value; independent hand-derived numbers, not a second call to the same function).
- Add edge cases: zero, missing, negative, NaN/Inf, boundary values for every field the fix touches.
- Add the group-level invariant tests for RC-11 (see Root-Cause Groups).
- Review existing tests that assert the old behaviour; change an expected value only when the new value is independently derived and documented in the test.

## Browser Verification

- API/backend fix. After the fix, open the page(s) that consume this data (see Affected Features) and confirm the displayed value matches the API and DB.

## Regression Risks

- Soft-delete changes list/lookup queries everywhere (must filter inactive rows).

## Acceptance Criteria

1. `audit/repro/BUG-009.py` exits 0 on the fixed code (it prints expected vs actual).
2. Expected behaviour holds: Either the facility and its dependent rows are deleted (as for every other child table), or a clear 409 "facility has dependent OGMP level logs" is returned.
3. Full backend suite (`python -m pytest tests/` in `new/server`) and frontend checks (`npm run lint`, `npm run test`) pass.
4. No other open bug's repro changes from fail→pass or pass→fail unexpectedly (re-run `audit/work/rerun/run_all.sh`).

---

# BUG-010 — Deleting a user who created production data, SBTi targets or OGMP level logs fails with 500 (FK cleanup list incomplete)

**Severity:** Medium · **Category:** Database · **Phase:** P5 · **Root cause group:** RC-11 · **Found by:** Agent J (Database)

**Current status:** **Still present** — `audit/repro/BUG-010.py` re-run on the final code: bug reproduced.

## Problem

Deleting a user who created production data, SBTi targets or OGMP level logs fails with 500 (FK cleanup list incomplete)

- **Actual:** `500 {"error": "Internal server error"}`; server log: `sqlite3.IntegrityError: FOREIGN KEY constraint failed [SQL: DELETE FROM users WHERE users.id = ?]`. User still exists.
- **Expected:** User is deleted and every `created_by` reference is nulled (as the endpoint does for other tables), or a clean 409 explaining why deletion is blocked.

## Root Cause

Tables with `created_by → users.id` missing from the clean-up list: `production_data`, `sbti_targets`, `level_upgrade_logs`, `cap_emissions`. (`mitigation_records` in the list has no such columns — the try/except silently swallows that.) No `ondelete` on any users FK.

## Affected Files

- `new/server/routes/auth.py`

## Affected Features

IT admins cannot remove accounts of any user who ever entered production data, an SBTi target, or an OGMP level log — i.e. most real operational users (offboarding / access-revocation workflow broken). Also, the preceding UPDATEs are part of the same failed transaction so nothing is changed, but the client only sees a generic 500.

## Required Changes

Derive the clean-up list from `db.metadata` (all FKs referencing `users.id`), or declare `ondelete="SET NULL"` on those FKs; alternatively prefer deactivation (`status='inactive'`) over hard delete.

Implement through the shared fix for RC-11 (Referential integrity on delete) rather than a local patch.

## Database Changes

Data policy: delete with snapshot — ON DELETE SET NULL for every FK referencing `users.id` (derive the list from metadata), combined with the BUG-069 snapshot columns.
 Ship as an Alembic migration (requires BUG-016).

## Backend Changes

Changes in `new/server/routes/auth.py` as described above.

## Frontend Changes

None.

## Calculation Changes

None.

## Tests To Add/Change

- Port `audit/repro/BUG-010.py` into a pytest regression test under `new/server/tests/` (assert the Expected value; independent hand-derived numbers, not a second call to the same function).
- Add edge cases: zero, missing, negative, NaN/Inf, boundary values for every field the fix touches.
- Add the group-level invariant tests for RC-11 (see Root-Cause Groups).
- Review existing tests that assert the old behaviour; change an expected value only when the new value is independently derived and documented in the test.

## Browser Verification

- API/backend fix. After the fix, open the page(s) that consume this data (see Affected Features) and confirm the displayed value matches the API and DB.

## Regression Risks

- Soft-delete changes list/lookup queries everywhere (must filter inactive rows).

## Acceptance Criteria

1. `audit/repro/BUG-010.py` exits 0 on the fixed code (it prints expected vs actual).
2. Expected behaviour holds: User is deleted and every `created_by` reference is nulled (as the endpoint does for other tables), or a clean 409 explaining why deletion is blocked.
3. Full backend suite (`python -m pytest tests/` in `new/server`) and frontend checks (`npm run lint`, `npm run test`) pass.
4. No other open bug's repro changes from fail→pass or pass→fail unexpectedly (re-run `audit/work/rerun/run_all.sh`).

---

# BUG-069 — Deleting a user wipes approved_by/created_by on every record they approved or entered: Verified records lose their maker-checker evidence

**Severity:** Low · **Category:** Database · **Phase:** P5 · **Root cause group:** RC-11 · **Found by:** Agent J (Database)

**Current status:** **Still present** — `audit/repro/BUG-069.py` re-run on the final code: bug reproduced.

## Problem

Deleting a user wipes approved_by/created_by on every record they approved or entered: Verified records lose their maker-checker evidence

- **Actual:** Count goes 470 → 489: the 19 records are now "Verified" with `approved_by = NULL` but `approved_at` still set — indistinguishable from records that were never approved through maker-checker (the snapshot already holds 470 such rows; 70 are seed rows, the rest have app-generated UUIDs and cannot be traced to an approver). Only the approval ActivityLog entry's `user_name` text remains, and its `user_id` is also nulled.
- **Expected:** Approval provenance stays attached to the record (soft-delete/deactivate the user, or keep an immutable approver name/id), so a Verified record can always show who approved it.

## Root Cause

Hard delete of users combined with nulling every FK to satisfy SQLite FK enforcement; the schema has no user soft-delete or denormalised approver name on records.

## Affected Files

- `new/server/routes/auth.py`

## Affected Features

Verification / assurance (ISO 14064-3, OGMP) needs to prove who approved each figure; after routine staff off-boarding the record-level evidence is gone and `status` contradicts `approved_by`. `created_by` also becomes NULL, so creator-ownership checks for role `user` (`created_by is not None and ...`) no longer apply to those records.

## Required Changes

Replace hard delete with deactivation (`status='inactive'`), or keep the FKs and block deletion when the user owns approvals; if deletion is required, store approver name/email on the record at approval time.

Implement through the shared fix for RC-11 (Referential integrity on delete) rather than a local patch.

## Database Changes

Data policy: delete with snapshot — add `approved_by_name`, `approved_by_email`, `created_by_name`, `created_by_email` columns to emission tables, filled at create/approval time; user delete keeps SET NULL on the FK. Historic rows are not backfilled.
 Ship as an Alembic migration (requires BUG-016).

## Backend Changes

Changes in `new/server/routes/auth.py` as described above.

## Frontend Changes

None.

## Calculation Changes

None.

## Tests To Add/Change

- Port `audit/repro/BUG-069.py` into a pytest regression test under `new/server/tests/` (assert the Expected value; independent hand-derived numbers, not a second call to the same function).
- Add edge cases: zero, missing, negative, NaN/Inf, boundary values for every field the fix touches.
- Add the group-level invariant tests for RC-11 (see Root-Cause Groups).
- Review existing tests that assert the old behaviour; change an expected value only when the new value is independently derived and documented in the test.

## Browser Verification

- API/backend fix. After the fix, open the page(s) that consume this data (see Affected Features) and confirm the displayed value matches the API and DB.

## Regression Risks

- Soft-delete changes list/lookup queries everywhere (must filter inactive rows).

## Acceptance Criteria

1. `audit/repro/BUG-069.py` exits 0 on the fixed code (it prints expected vs actual).
2. Expected behaviour holds: Approval provenance stays attached to the record (soft-delete/deactivate the user, or keep an immutable approver name/id), so a Verified record can always show who approved it.
3. Full backend suite (`python -m pytest tests/` in `new/server`) and frontend checks (`npm run lint`, `npm run test`) pass.
4. No other open bug's repro changes from fail→pass or pass→fail unexpectedly (re-run `audit/work/rerun/run_all.sh`).

---


# PHASE P6 — Emissions / reporting defects

_Phase regression risk:_ Report output changes visibly; stakeholders may compare against previously issued PDFs.

---

# BUG-044 — /granular-intensities (Master Report "Multi-Metric Intensities") divides all-facility emissions by only the facilities with granular MMboe fields, and fabricates NGSI methane (0.05 %) and saleable production (85 %)

**Severity:** High · **Category:** Carbon Intensity · **Phase:** P6 · **Root cause group:** RC-12 · **Found by:** Agent E (Carbon-intensity auditor) · **Independent confirmations:** 1

**Current status:** **Still present** — `audit/repro/BUG-044.py` re-run on the final code: bug reproduced.

## Problem

/granular-intensities (Master Report "Multi-Metric Intensities") divides all-facility emissions by only the facilities with granular MMboe fields, and fabricates NGSI methane (0.05 %) and saleable production (85 %)

- **Actual:** - 2025: `ci_by_total_production_kg_boe` = **14.93** over 130,930,000 BOE (Berkine only, 47 % too high). `ci_by_saleable_production_kg_boe` = 34.51, reported as "2.0x ABOVE TARGET". - Facility 13, 2026: `methane_intensity_ngsi_wt_pct` = **0.05** (a constant). The report then prints "Far below global 0.20% methane intensity ceiling". - Corporate 2026 also returns 0.05.
- **Expected:** - 2025 CI (total production) = 1,954,194 t × 1000 / 192,634,702 BOE = **10.14 kg CO2e/BOE**. The endpoint's own OGCI test on saleable volume gives about 17.9 kg/BOE. - Facility 13, 2026, NGSI CH4 wt% = 338.91 t / (134.7 M m3 × 0.0008 t/m3) = **0.31 %**. That is above the 0.20 % ceiling the report cites.

## Root Cause

The fallback is decided all-or-nothing on the aggregate instead of per row, and it is unit-blind. Missing inputs are replaced by invented constants (0.85 saleable, 0.05 % CH4) rather than being reported as "not available". The report template also hard-codes values and verdicts.

## Affected Files

- `new/client/src/utils/ModernReportGenerator.js`
- `new/server/routes/dashboard.py`

## Affected Features

The Master Report "Multi-Metric Intensities Matrix" (Chapter 8) shows a carbon intensity that is 47 % too high for 2025. It shows a methane intensity that is invented, and in the facility 13 case hides a breach of the 0.20 % threshold. It also shows a flaring Sm³/BOE value and compliance statements that do not come from data.

## Required Changes

Compute BOE per production row: use `total_production_mmboe` when it is present, otherwise unit-converted oil + gas with a single shared BOE factor. Use the same factor in every endpoint. Return null / "insufficient data" instead of 0.85 or 0.05. For NGSI, fall back to `gas_amount` converted to m³. Compute the report's flaring Sm³/BOE and its verdict strings from data.

Implement through the shared fix for RC-12 (Reports print unverified, mislabelled or fabricated content) rather than a local patch.

## Database Changes

None required.

## Backend Changes

Changes in `new/server/routes/dashboard.py` as described above.

## Frontend Changes

Changes in `new/client/src/utils/ModernReportGenerator.js` as described above.

## Calculation Changes

None.

## Tests To Add/Change

- Port `audit/repro/BUG-044.py` into a pytest regression test under `new/server/tests/` (assert the Expected value; independent hand-derived numbers, not a second call to the same function).
- Add edge cases: zero, missing, negative, NaN/Inf, boundary values for every field the fix touches.
- Add the group-level invariant tests for RC-12 (see Root-Cause Groups).
- Review existing tests that assert the old behaviour; change an expected value only when the new value is independently derived and documented in the test.

## Browser Verification

- Reproduce the steps in AUDIT_FINDINGS.md on an isolated stack (`audit/tools/vite_audit.mjs` + backend on an audit DB copy) and confirm the Expected result on screen.
- Compare the UI value with the API response and the DB row for the same record; refresh and reopen the record.

## Regression Risks

- Report output changes visibly; stakeholders may compare against previously issued PDFs.

## Acceptance Criteria

1. `audit/repro/BUG-044.py` exits 0 on the fixed code (it prints expected vs actual).
2. Expected behaviour holds: - 2025 CI (total production) = 1,954,194 t × 1000 / 192,634,702 BOE = **10.14 kg CO2e/BOE**. The endpoint's own OGCI test on saleable volume gives about 17.9 kg/BOE. - Facility 13, 2026, NGSI CH4 wt% = 338.91 t / (134.7 M m3 × 0.0008 t/m3) = **0.31 %**. That is above the 0.20 % ceiling the report cites.
3. Full backend suite (`python -m pytest tests/` in `new/server`) and frontend checks (`npm run lint`, `npm run test`) pass.
4. No other open bug's repro changes from fail→pass or pass→fail unexpectedly (re-run `audit/work/rerun/run_all.sh`).

---

# BUG-084 — QA/QC Dashboard shows "Zero Anomalies Detected… The inventory is fully verified and audit-compliant" with 149 Pending records and 11 records more than 10^6 × the median; the anomaly queue only lists a stored `qa_flag`, which is never computed for existing data

**Severity:** Medium · **Category:** Dashboard · **Phase:** P6 · **Root cause group:** RC-12 · **Found by:** Agent F (Dashboard reconciliation auditor)

**Current status:** **Still present** — `audit/repro/BUG-084.py` re-run on the final code: bug reproduced.

## Problem

QA/QC Dashboard shows "Zero Anomalies Detected… The inventory is fully verified and audit-compliant" with 149 Pending records and 11 records more than 10^6 × the median; the anomaly queue only lists a stored `qa_flag`, which is never computed for existing data

- **Actual:** "FLAGGED ANOMALIES 0 active", "Zero Anomalies Detected", "The inventory is fully verified and audit-compliant." "INVENTORY COVERAGE 809 entries" counts all statuses.
- **Expected:** With Pending records the page must not claim the inventory is "fully verified". Obvious outliers (10^6 × the median) should be flagged by the page's "statistical outlier" check, or the text should say that only import-time flags are shown.

## Root Cause

The QA page reflects only `qa_flag` values written by the bulk-import anomaly detector. Manual entries are never flagged (BUG-007), and nothing re-scans stored data. The empty-state copy asserts verification status without checking record status.

## Affected Files

- `new/client/src/pages/QADashboard.jsx`
- `new/server/routes/qaqc.py`

## Affected Features

Reviewers and assurers are told the inventory is clean and fully verified while a small number of records inflate totals by about 1000× and 149 records are still unapproved.

## Required Changes

Run the anomaly detector (z-score or ratio to median, per process type and unit) over stored records when building the QA dashboard, or on a schedule. Base the "verified" wording on the actual count of non-Verified records.

Implement through the shared fix for RC-12 (Reports print unverified, mislabelled or fabricated content) rather than a local patch.

## Database Changes

None required.

## Backend Changes

Changes in `new/server/routes/qaqc.py` as described above.

## Frontend Changes

Changes in `new/client/src/pages/QADashboard.jsx` as described above.

## Calculation Changes

None.

## Tests To Add/Change

- Port `audit/repro/BUG-084.py` into a pytest regression test under `new/server/tests/` (assert the Expected value; independent hand-derived numbers, not a second call to the same function).
- Add edge cases: zero, missing, negative, NaN/Inf, boundary values for every field the fix touches.
- Add the group-level invariant tests for RC-12 (see Root-Cause Groups).
- Review existing tests that assert the old behaviour; change an expected value only when the new value is independently derived and documented in the test.

## Browser Verification

- Reproduce the steps in AUDIT_FINDINGS.md on an isolated stack (`audit/tools/vite_audit.mjs` + backend on an audit DB copy) and confirm the Expected result on screen.
- Compare the UI value with the API response and the DB row for the same record; refresh and reopen the record.

## Regression Risks

- Report output changes visibly; stakeholders may compare against previously issued PDFs.

## Acceptance Criteria

1. `audit/repro/BUG-084.py` exits 0 on the fixed code (it prints expected vs actual).
2. Expected behaviour holds: With Pending records the page must not claim the inventory is "fully verified". Obvious outliers (10^6 × the median) should be flagged by the page's "statistical outlier" check, or the text should say that only import-time flags are shown.
3. Full backend suite (`python -m pytest tests/` in `new/server`) and frontend checks (`npm run lint`, `npm run test`) pass.
4. No other open bug's repro changes from fail→pass or pass→fail unexpectedly (re-run `audit/work/rerun/run_all.sh`).

---

# BUG-002 — Reports "2025 Master Report (PDF)" button sends facility_id=[object Object]; facility selection ignored

**Severity:** Medium · **Category:** UI · **Phase:** P6 · **Root cause group:** RC-12 · **Found by:** Agent K (Frontend/UI)

**Current status:** **Confirmed on the post-change code by the browser agent** (`audit/repro/BUG-002.mjs`); not re-run in the final pass (needs a live UI stack).

## Problem

Reports "2025 Master Report (PDF)" button sends facility_id=[object Object]; facility selection ignored

- **Actual:** Request `GET /api/reports/master-annual-report?facility_id=[object%20Object]`; downloaded file is `Groupement_Berkine_2025_Annual_GHG_Report.pdf` regardless of the selected facility. The toast also says "Downloading Groupement Berkine Master Report".
- **Expected:** Request `GET /api/reports/master-annual-report?facility_id=170` and the El Merk report (the handler's own logic falls back to `regionId` when no target is passed).

## Root Cause

React passes the click event as the first argument. `targetFacilityId || ...` is truthy for the event object, so `selectedId` becomes the SyntheticEvent, which is stringified into the URL; the `reportSelectedRegions`/`regionId` fallbacks are never reached.

## Affected Files

- `new/client/src/pages/Reports.jsx`

## Affected Features

The facility-specific master report can never be obtained from this button; the user silently receives a different organisation's consolidated report. (Only the "Create New Report" modal path passes no argument and works.)

## Required Changes

`onClick={() => handleMasterReportDownload()}` and/or guard `typeof targetFacilityId === "string" || typeof targetFacilityId === "number"`.

Implement through the shared fix for RC-12 (Reports print unverified, mislabelled or fabricated content) rather than a local patch.

## Database Changes

None required.

## Backend Changes

None beyond the above.

## Frontend Changes

Changes in `new/client/src/pages/Reports.jsx` as described above.

## Calculation Changes

None.

## Tests To Add/Change

- Port `audit/repro/BUG-002.mjs` into a Playwright spec under `new/client/e2e/` (or a vitest test where it is pure component logic).
- Add edge cases: zero, missing, negative, NaN/Inf, boundary values for every field the fix touches.
- Add the group-level invariant tests for RC-12 (see Root-Cause Groups).
- Review existing tests that assert the old behaviour; change an expected value only when the new value is independently derived and documented in the test.

## Browser Verification

- Reproduce the steps in AUDIT_FINDINGS.md on an isolated stack (`audit/tools/vite_audit.mjs` + backend on an audit DB copy) and confirm the Expected result on screen.
- Compare the UI value with the API response and the DB row for the same record; refresh and reopen the record.

## Regression Risks

- Report output changes visibly; stakeholders may compare against previously issued PDFs.

## Acceptance Criteria

1. `audit/repro/BUG-002.mjs` exits 0 on the fixed code (it prints expected vs actual).
2. Expected behaviour holds: Request `GET /api/reports/master-annual-report?facility_id=170` and the El Merk report (the handler's own logic falls back to `regionId` when no target is passed).
3. Full backend suite (`python -m pytest tests/` in `new/server`) and frontend checks (`npm run lint`, `npm run test`) pass.
4. No other open bug's repro changes from fail→pass or pass→fail unexpectedly (re-run `audit/work/rerun/run_all.sh`).

---

# BUG-006 — Reports Excel/PDF exports drop the Division, Field, Method and Search filters shown on screen

**Severity:** Medium · **Category:** UI · **Phase:** P6 · **Root cause group:** RC-12 · **Found by:** Agent K (Frontend/UI)

**Current status:** **Confirmed on the post-change code by the browser agent** (`audit/repro/BUG-006.mjs`); not re-run in the final pass (needs a live UI stack).

## Problem

Reports Excel/PDF exports drop the Division, Field, Method and Search filters shown on screen

- **Actual:** ``` GET /api/emissions/export?scope=all&format=excel GET /api/reports/export?scope=all ``` The division filter is silently dropped. Via the API, the unfiltered export contains 660 rows vs 63 with `division=Upstream`, so the downloaded file contains ~10x the records the user was looking at.
- **Expected:** `/api/emissions/export?...&division=Upstream&format=excel` and `/api/reports/export?...&division=Upstream` — both backend endpoints accept `division`, `field`, `method`, `search` (routes/emissions.py ≈4047-4050, routes/reports.py `export_emissions`).

## Root Cause

Export param builders were not updated when the Division/Field/Method/Search filters were added to the list query (`fetchEmissions` sends them).

## Affected Files

- `new/client/src/pages/Reports.jsx`

## Affected Features

Exported spreadsheets/PDFs do not match the on-screen filtered table; a user exporting "Upstream" data submits/uses the whole-company dataset without any warning.

## Required Changes

Build one shared params object (the one used by `fetchEmissions`, minus page/per_page) and reuse it for both exports.

Implement through the shared fix for RC-12 (Reports print unverified, mislabelled or fabricated content) rather than a local patch.

## Database Changes

None required.

## Backend Changes

None beyond the above.

## Frontend Changes

Changes in `new/client/src/pages/Reports.jsx` as described above.

## Calculation Changes

None.

## Tests To Add/Change

- Port `audit/repro/BUG-006.mjs` into a Playwright spec under `new/client/e2e/` (or a vitest test where it is pure component logic).
- Add edge cases: zero, missing, negative, NaN/Inf, boundary values for every field the fix touches.
- Add the group-level invariant tests for RC-12 (see Root-Cause Groups).
- Review existing tests that assert the old behaviour; change an expected value only when the new value is independently derived and documented in the test.

## Browser Verification

- Reproduce the steps in AUDIT_FINDINGS.md on an isolated stack (`audit/tools/vite_audit.mjs` + backend on an audit DB copy) and confirm the Expected result on screen.
- Compare the UI value with the API response and the DB row for the same record; refresh and reopen the record.

## Regression Risks

- Report output changes visibly; stakeholders may compare against previously issued PDFs.

## Acceptance Criteria

1. `audit/repro/BUG-006.mjs` exits 0 on the fixed code (it prints expected vs actual).
2. Expected behaviour holds: `/api/emissions/export?...&division=Upstream&format=excel` and `/api/reports/export?...&division=Upstream` — both backend endpoints accept `division`, `field`, `method`, `search` (routes/emissions.py ≈4047-4050, routes/reports.py `export_emissions`).
3. Full backend suite (`python -m pytest tests/` in `new/server`) and frontend checks (`npm run lint`, `npm run test`) pass.
4. No other open bug's repro changes from fail→pass or pass→fail unexpectedly (re-run `audit/work/rerun/run_all.sh`).

---

# BUG-113 — Reports "PDF Report" prints every unit and gas name with a missing-glyph box: "tCO■e", "CO■", "CH■", "N■O"

**Severity:** Low · **Category:** UI · **Phase:** P6 · **Root cause group:** RC-12 · **Found by:** Agent L (Browser)

**Current status:** **Still present** — `audit/repro/BUG-113.py` re-run on the final code: bug reproduced.

## Problem

Reports "PDF Report" prints every unit and gas name with a missing-glyph box: "tCO■e", "CO■", "CH■", "N■O"

- **Actual:** Rendered page shows "58.54 tCO■e", "Total CO■ Gas Mass", "tonnes CH■", "N■O" (screenshot `audit/work/L/rep_pdf.png`; text extraction gives "tCOne", "CHn", "NnO"). The numbers themselves match the DB/dashboard (S1 58.54, S2 11,845.52, S3 1.85 for facility 173 / 2025, Verified only).
- **Expected:** "tCO₂e", "CO₂", "CH₄", "N₂O" (or ASCII "tCO2e") in the summary table and detail headers.

## Root Cause

reportlab standard Type 1 fonts only cover Latin-1; subscript characters need an embedded TTF (e.g. DejaVuSans) or `<sub>` markup in Paragraphs.

## Affected Files

- `new/server/routes/reports.py`

## Affected Features

The regulatory-facing PDF export looks broken on every unit label; recipients cannot tell CO₂ from CH₄ columns reliably in the detail table.

## Required Changes

Register and use a Unicode TTF font in the PDF styles, or render subscripts with `<sub>2</sub>` / ASCII "CO2e".

Implement through the shared fix for RC-12 (Reports print unverified, mislabelled or fabricated content) rather than a local patch.

## Database Changes

None required.

## Backend Changes

Changes in `new/server/routes/reports.py` as described above.

## Frontend Changes

None.

## Calculation Changes

None.

## Tests To Add/Change

- Port `audit/repro/BUG-113.py` into a pytest regression test under `new/server/tests/` (assert the Expected value; independent hand-derived numbers, not a second call to the same function).
- Add edge cases: zero, missing, negative, NaN/Inf, boundary values for every field the fix touches.
- Add the group-level invariant tests for RC-12 (see Root-Cause Groups).
- Review existing tests that assert the old behaviour; change an expected value only when the new value is independently derived and documented in the test.

## Browser Verification

- API/backend fix. After the fix, open the page(s) that consume this data (see Affected Features) and confirm the displayed value matches the API and DB.

## Regression Risks

- Report output changes visibly; stakeholders may compare against previously issued PDFs.

## Acceptance Criteria

1. `audit/repro/BUG-113.py` exits 0 on the fixed code (it prints expected vs actual).
2. Expected behaviour holds: "tCO₂e", "CO₂", "CH₄", "N₂O" (or ASCII "tCO2e") in the summary table and detail headers.
3. Full backend suite (`python -m pytest tests/` in `new/server`) and frontend checks (`npm run lint`, `npm run test`) pass.
4. No other open bug's repro changes from fail→pass or pass→fail unexpectedly (re-run `audit/work/rerun/run_all.sh`).

---

# BUG-031 — Facility OGMP 2.0 level counts Draft, Pending and Rejected emission records, so a rejected record can raise a facility's level

**Severity:** Medium · **Category:** Methane · **Phase:** P6 · **Root cause group:** RC-2 · **Found by:** Agent D (Methane Auditor)

**Current status:** **Still present** — `audit/repro/BUG-031.py` re-run on the final code: bug reproduced.

## Problem

Facility OGMP 2.0 level counts Draft, Pending and Rejected emission records, so a rejected record can raise a facility's level

- **Actual:** Level 4. In the same way, a Draft/Pending/Rejected Tier-3 record also removes the "bottom-up must be L4" cap on Level 5 (Gold Standard), which the code itself describes as mandatory.
- **Expected:** Only Verified records form the reported bottom-up inventory. The same Verified filter is already applied to the CH4 totals in the same endpoint. Level should stay 3.

## Root Cause

The record query in `compute_facility_ogmp_level` lacks the status filter. It also takes the **max** level over records rather than the level of the material share of emissions. For example, facility 13 (2026) has 236.6 t of its 338.9 tCH4 at Level 2 and is still reported as Level 4.

## Affected Files

- `new/server/services/ogmp.py`

## Affected Features

OGMP 2.0 levels and Gold-Standard status on the dashboard OGMP roadmap and in the regulator-facing OGMP Excel export can be overstated by unapproved or rejected data.

## Required Changes

Filter `Emission.status == "Verified"`. Derive the facility bottom-up level from the emission-weighted (materiality) share at L4, not the maximum over any single record.

Implement through the shared fix for RC-2 (Maker-checker / status policy duplicated per route) rather than a local patch.

## Database Changes

None required.

## Backend Changes

Changes in `new/server/services/ogmp.py` as described above.

## Frontend Changes

None.

## Calculation Changes

None.

## Tests To Add/Change

- Port `audit/repro/BUG-031.py` into a pytest regression test under `new/server/tests/` (assert the Expected value; independent hand-derived numbers, not a second call to the same function).
- Add edge cases: zero, missing, negative, NaN/Inf, boundary values for every field the fix touches.
- Add the group-level invariant tests for RC-2 (see Root-Cause Groups).
- Review existing tests that assert the old behaviour; change an expected value only when the new value is independently derived and documented in the test.

## Browser Verification

- API/backend fix. After the fix, open the page(s) that consume this data (see Affected Features) and confirm the displayed value matches the API and DB.

## Regression Risks

- Status-policy changes alter who can approve and what edits reset records to Pending; re-run the full maker-checker role matrix (user, superuser, admin, it roles) for Scope 1/2/3, CAP and bulk.

## Acceptance Criteria

1. `audit/repro/BUG-031.py` exits 0 on the fixed code (it prints expected vs actual).
2. Expected behaviour holds: Only Verified records form the reported bottom-up inventory. The same Verified filter is already applied to the CH4 totals in the same endpoint. Level should stay 3.
3. Full backend suite (`python -m pytest tests/` in `new/server`) and frontend checks (`npm run lint`, `npm run test`) pass.
4. No other open bug's repro changes from fail→pass or pass→fail unexpectedly (re-run `audit/work/rerun/run_all.sh`).

---

# BUG-052 — OGMP survey reconciliation status defaults to "Reconciled" whatever the computed variance; a +354 % discrepancy is stored and shown as Reconciled, and a zero bottom-up case is shown as "+0.0 %"

**Severity:** Medium · **Category:** Methane · **Phase:** P6 · **Root cause group:** — · **Found by:** Agent D (Methane Auditor)

**Current status:** **Still present** — `audit/repro/BUG-052.py` re-run on the final code: bug reproduced.

## Problem

OGMP survey reconciliation status defaults to "Reconciled" whatever the computed variance; a +354 % discrepancy is stored and shown as Reconciled, and a zero bottom-up case is shown as "+0.0 %"

- **Actual:** - Case 1: stored and returned `variance_pct 353.62, variance_flag true, reconciliation_status "Reconciled"`. - Case 2 (zero bottom-up): `bottom_up_tch4 0.0, variance_pct 0.0, variance_flag true, reconciliation_status "Reconciled"`. The survey table then shows a green "+0.0 %" and a green "Reconciled" badge. - The seed data has the same contradiction (e.g. survey id 2: flag 1, status "Reconciled").
- **Expected:** Variance = (3504 − 772.46)/772.46 = +353.6 %, which exceeds the 20 % threshold. Status should be "Discrepancy Flagged", derived server-side. With a zero bottom-up, variance should be null/"N/A" and the status "Discrepancy Flagged", as `/ogmp-metrics` itself reports.

## Root Cause

The reconciliation status is a free-text client field with a "Reconciled" default and is never tied to the computed flag. `None` variance is coerced to 0.0 on read. The stored `bottom_up_tch4` / `variance_pct` are also a snapshot taken at save time and never refreshed when emissions change.

## Affected Files

- `new/server/routes/data.py`

## Affected Features

The OGMP 2.0 top-down/bottom-up reconciliation evidence shown to users (and available for disclosure) can claim reconciliation for large discrepancies. This contradicts `/api/dashboard/ogmp-metrics`, which flags the same facility.

## Required Changes

Derive `reconciliation_status` server-side from the variance and threshold ("Discrepancy Flagged" / "Reconciled" / "No Bottom-Up"). Only allow an explicit override with a justification. Return `null` variance as null, and recompute bottom-up on read.

## Database Changes

None required.

## Backend Changes

Changes in `new/server/routes/data.py` as described above.

## Frontend Changes

None.

## Calculation Changes

None.

## Tests To Add/Change

- Port `audit/repro/BUG-052.py` into a pytest regression test under `new/server/tests/` (assert the Expected value; independent hand-derived numbers, not a second call to the same function).
- Add edge cases: zero, missing, negative, NaN/Inf, boundary values for every field the fix touches.
- Review existing tests that assert the old behaviour; change an expected value only when the new value is independently derived and documented in the test.

## Browser Verification

- API/backend fix. After the fix, open the page(s) that consume this data (see Affected Features) and confirm the displayed value matches the API and DB.

## Regression Risks

- Report output changes visibly; stakeholders may compare against previously issued PDFs.

## Acceptance Criteria

1. `audit/repro/BUG-052.py` exits 0 on the fixed code (it prints expected vs actual).
2. Expected behaviour holds: Variance = (3504 − 772.46)/772.46 = +353.6 %, which exceeds the 20 % threshold. Status should be "Discrepancy Flagged", derived server-side. With a zero bottom-up, variance should be null/"N/A" and the status "Discrepancy Flagged", as `/ogmp-metrics` itself reports.
3. Full backend suite (`python -m pytest tests/` in `new/server`) and frontend checks (`npm run lint`, `npm run test`) pass.
4. No other open bug's repro changes from fail→pass or pass→fail unexpectedly (re-run `audit/work/rerun/run_all.sh`).

---

# BUG-075 — Sentinel-5P "Export to OGMP" stores a 1-hour CH4 mass as the survey's "estimated annual tCH4" (default operating_hours = 1): top-down understated 8,760× and reconciliation always flagged

**Severity:** Medium · **Category:** Methane · **Phase:** P6 · **Root cause group:** — · **Found by:** Agent D (Methane Auditor) · **Independent confirmations:** 2

**Current status:** **Still present** — `audit/repro/BUG-075.py` re-run on the final code: bug reproduced.

## Problem

Sentinel-5P "Export to OGMP" stores a 1-hour CH4 mass as the survey's "estimated annual tCH4" (default operating_hours = 1): top-down understated 8,760× and reconciliation always flagged

- **Actual:** `operating_hours_year = 1.0`, `estimated_annual_tch4 = 0.1`, `variance_pct = −99.99`, `reconciliation_status = "Discrepancy Flagged"`. `/ogmp-metrics` then reports −99.99 % "Discrepancy Flagged". The survey is saved as `status "Verified"` for admin/superuser, and the API response tells the user it was "reconciled".
- **Expected:** The field is named, displayed and reconciled as an **annual** quantity against the annual bottom-up inventory, so the rate must be annualised on the same basis as manual surveys: 100 × 8,760 / 1000 = 876 tCH4/yr. Variance vs 772.46 t = +13.4 %, which is within the 20 % threshold: "Reconciled". Otherwise the export must require the user to state an emission duration.

## Root Cause

There is a 1-hour default duration in the export path, and the UI never provides a duration. Top-down averaging (`func.avg(estimated_annual_tch4)` in `/ogmp-metrics`, `/intensity-stats` and the OGMP export) then mixes 1-hour masses with 8,760-hour annualised manual surveys.

## Affected Files

- `new/client/src/pages/MethaneExplorer.jsx`
- `new/server/routes/satellite.py`

## Affected Features

Every satellite survey exported from Methane Explorer is 8,760× too small as an annual estimate. Top-down/bottom-up reconciliation (the OGMP Level 5 criterion) is systematically falsified toward "discrepancy". Averaged top-down values for facilities with both survey types are meaningless.

## Required Changes

Annualise consistently (8,760 h or facility operating hours), or make duration a required, explicit input in the UI. Store the observed rate separately from any annualised figure, and do not average surveys that were annualised on different bases.

## Database Changes

None required.

## Backend Changes

Changes in `new/server/routes/satellite.py` as described above.

## Frontend Changes

Changes in `new/client/src/pages/MethaneExplorer.jsx` as described above.

## Calculation Changes

None.

## Tests To Add/Change

- Port `audit/repro/BUG-075.py` into a pytest regression test under `new/server/tests/` (assert the Expected value; independent hand-derived numbers, not a second call to the same function).
- Add edge cases: zero, missing, negative, NaN/Inf, boundary values for every field the fix touches.
- Review existing tests that assert the old behaviour; change an expected value only when the new value is independently derived and documented in the test.

## Browser Verification

- Reproduce the steps in AUDIT_FINDINGS.md on an isolated stack (`audit/tools/vite_audit.mjs` + backend on an audit DB copy) and confirm the Expected result on screen.
- Compare the UI value with the API response and the DB row for the same record; refresh and reopen the record.

## Regression Risks

- Report output changes visibly; stakeholders may compare against previously issued PDFs.

## Acceptance Criteria

1. `audit/repro/BUG-075.py` exits 0 on the fixed code (it prints expected vs actual).
2. Expected behaviour holds: The field is named, displayed and reconciled as an **annual** quantity against the annual bottom-up inventory, so the rate must be annualised on the same basis as manual surveys: 100 × 8,760 / 1000 = 876 tCH4/yr. Variance vs 772.46 t = +13.4 %, which is within the 20 % threshold: "Reconciled". Otherwise the export must require the user to state an emission duration.
3. Full backend suite (`python -m pytest tests/` in `new/server`) and frontend checks (`npm run lint`, `npm run test`) pass.
4. No other open bug's repro changes from fail→pass or pass→fail unexpectedly (re-run `audit/work/rerun/run_all.sh`).

---


# PHASE P7 — Dashboard / intensity defects

_Phase regression risk:_ Dashboard numbers change under filters; users will see different totals than before (they were wrong before).

---

# BUG-040 — Supply Chain filter is not applied to the emissions-by-source split: "Emissions by Source" donut and Detailed Breakdown rows show company-wide values (sources add up to 7× Scope 1)

**Severity:** High · **Category:** Dashboard · **Phase:** P7 · **Root cause group:** RC-7 · **Found by:** Agent F (Dashboard reconciliation auditor)

**Current status:** **Still present** — `audit/repro/BUG-040.py` re-run on the final code: bug reproduced.

## Problem

Supply Chain filter is not applied to the emissions-by-source split: "Emissions by Source" donut and Detailed Breakdown rows show company-wide values (sources add up to 7× Scope 1)

- **Actual:** - Heavy Industry: Scope 1 KPI 532.85 B (correct), but the sum of sources is **3,723,125,709,361.93 t** and flaring is **2,199,048.57 t** (company-wide Berkine flaring on a steel plant). - Upstream: sum of sources is 3.723 T against a Scope 1 of 3.190 T. The donut and the table therefore show 7× (Heavy Industry) or 1.17× (Upstream) more emissions than the Scope 1 KPI above them.
- **Expected:** Source rows add up to Scope 1 (independent SQL on `facilities.segment`): - Heavy Industry: Scope 1 = 532,854,262,072.39 t. Flaring = 15.93 t. - Upstream: Scope 1 = 3,190,271,328,984.07 t. Flaring = 2,199,032.63 t.

## Root Cause

The `segment` join and filter were added to the Scope 1 and Scope 2 queries of `_query_summary` but not to the third (source-split) query. The merge loop only checks `key in yearly_data` and does not check that the populations match.

## Affected Files

- `new/server/routes/dashboard.py`

## Affected Features

With any Supply Chain filter selected, the "Emissions by Source" donut and the Stationary Combustion / Flaring / Venting / Other rows show the whole company's emissions. The dashboard's source mix does not reconcile with its own Scope 1 figure.

## Required Changes

Apply the same `Facility` join and `Facility.segment == segment` filter to `activity_query`. Better, derive all three queries from one filtered base query. Add an invariant test that the source sum equals Scope 1.

Implement through the shared fix for RC-7 (Dashboard filters not applied through one base query) rather than a local patch.

## Database Changes

None required.

## Backend Changes

Changes in `new/server/routes/dashboard.py` as described above.

## Frontend Changes

None.

## Calculation Changes

None.

## Tests To Add/Change

- Port `audit/repro/BUG-040.py` into a pytest regression test under `new/server/tests/` (assert the Expected value; independent hand-derived numbers, not a second call to the same function).
- Add edge cases: zero, missing, negative, NaN/Inf, boundary values for every field the fix touches.
- Add the group-level invariant tests for RC-7 (see Root-Cause Groups).
- Review existing tests that assert the old behaviour; change an expected value only when the new value is independently derived and documented in the test.

## Browser Verification

- API/backend fix. After the fix, open the page(s) that consume this data (see Affected Features) and confirm the displayed value matches the API and DB.

## Regression Risks

- Dashboard numbers under filters will change (they were inconsistent before). Watch query performance when all panels derive from one filtered base query.

## Acceptance Criteria

1. `audit/repro/BUG-040.py` exits 0 on the fixed code (it prints expected vs actual).
2. Expected behaviour holds: Source rows add up to Scope 1 (independent SQL on `facilities.segment`): - Heavy Industry: Scope 1 = 532,854,262,072.39 t. Flaring = 15.93 t. - Upstream: Scope 1 = 3,190,271,328,984.07 t. Flaring = 2,199,032.63 t.
3. Full backend suite (`python -m pytest tests/` in `new/server`) and frontend checks (`npm run lint`, `npm run test`) pass.
4. No other open bug's repro changes from fail→pass or pass→fail unexpectedly (re-run `audit/work/rerun/run_all.sh`).

---

# BUG-004 — Intensity activity/division filter uses record-level columns that are NULL/inconsistent, so numerator and denominator are filtered differently (Upstream intensity blank, E&P intensity 0.0)

**Severity:** High · **Category:** Carbon Intensity · **Phase:** P7 · **Root cause group:** RC-7 · **Found by:** Agent E (Carbon-intensity auditor) · **Independent confirmations:** 1

**Current status:** **Still present** — `audit/repro/BUG-004.py` re-run on the final code: bug reproduced.

## Problem

Intensity activity/division filter uses record-level columns that are NULL/inconsistent, so numerator and denominator are filtered differently (Upstream intensity blank, E&P intensity 0.0)

- **Actual:** - activity=Upstream: every row has total_boe=0 → co2_intensity 0 for all facilities, weighted KPI undefined (dashboard shows "Pending Production" even though 116.7 M BOE exist) - activity=Activité E&P: 0.0 kg/BOE (production counted, 160 emissions dropped from numerator) - Steel & Iron 2022: 0.0 kg/BOE instead of 85.97 - Unfiltered (year=2025) matches expected (10.855) → the discrepancy comes only from the filter.
- **Expected:** Same filter applied to numerator and denominator (facility-level): - activity=Upstream, 2025: 16.355 kg CO2e/BOE over 116.7 M BOE; 2022: 19.554 kg/BOE - activity=Activité E&P, 2025: 0.772 kg/BOE; 2022: 0.227 - activity=Steel & Iron (Acier DRI), 2022: 85.968 kg/BOE

## Root Cause

The activity/division filter is applied to four different columns (record-level on production, Scope 1 and Scope 2; facility-level on Scope 3). Record-level labels are optional, often NULL and can differ from the facility's label, so the numerator and the denominator are filtered on different populations.

## Affected Files

- `new/server/routes/dashboard.py`

## Affected Features

With the activity or division filter set, the corporate and facility carbon intensity (Dashboard "Performance Intensity" KPI, Carbon Intensity page, Methane Intensity page, intensity trend and PDF report) is wrong or missing. The largest producers (Berkine, about 65% of 2025 BOE) disappear from the "Upstream" view.

## Required Changes

Filter all numerator and denominator queries by the same facility attribute (join `Facility` and filter `Facility.activity/division`). Alternatively, default record-level activity/division to the facility's value on every write path, including `POST /api/data/production`, and backfill the NULL values.

Implement through the shared fix for RC-7 (Dashboard filters not applied through one base query) rather than a local patch.

## Database Changes

None required.

## Backend Changes

Changes in `new/server/routes/dashboard.py` as described above.

## Frontend Changes

None.

## Calculation Changes

None.

## Tests To Add/Change

- Port `audit/repro/BUG-004.py` into a pytest regression test under `new/server/tests/` (assert the Expected value; independent hand-derived numbers, not a second call to the same function).
- Add edge cases: zero, missing, negative, NaN/Inf, boundary values for every field the fix touches.
- Add the group-level invariant tests for RC-7 (see Root-Cause Groups).
- Review existing tests that assert the old behaviour; change an expected value only when the new value is independently derived and documented in the test.

## Browser Verification

- API/backend fix. After the fix, open the page(s) that consume this data (see Affected Features) and confirm the displayed value matches the API and DB.

## Regression Risks

- Dashboard numbers under filters will change (they were inconsistent before). Watch query performance when all panels derive from one filtered base query.

## Acceptance Criteria

1. `audit/repro/BUG-004.py` exits 0 on the fixed code (it prints expected vs actual).
2. Expected behaviour holds: Same filter applied to numerator and denominator (facility-level): - activity=Upstream, 2025: 16.355 kg CO2e/BOE over 116.7 M BOE; 2022: 19.554 kg/BOE - activity=Activité E&P, 2025: 0.772 kg/BOE; 2022: 0.227 - activity=Steel & Iron (Acier DRI), 2022: 85.968 kg/BOE
3. Full backend suite (`python -m pytest tests/` in `new/server`) and frontend checks (`npm run lint`, `npm run test`) pass.
4. No other open bug's repro changes from fail→pass or pass→fail unexpectedly (re-run `audit/work/rerun/run_all.sh`).

---

# BUG-017 — Intensity with year="all" (default view) pairs each facility's emissions from every year with production from other years; KPI mixes periods

**Severity:** High · **Category:** Carbon Intensity · **Phase:** P7 · **Root cause group:** RC-7 · **Found by:** Agent E (Carbon-intensity auditor)

**Current status:** **Still present** — `audit/repro/BUG-017.py` re-run on the final code: bug reproduced.

## Problem

Intensity with year="all" (default view) pairs each facility's emissions from every year with production from other years; KPI mixes periods

- **Actual:** - Facility 2: 13.61 kg/BOE (11× too high, because the 2020 emissions are divided by 2022-26 production) - Facility 9: 203,285 kg/BOE; facility 10: 105,601 kg/BOE - Many facilities with 2026 emissions and only 2025 production are also mixed (fid 46-141). - The corporate KPI in the default dashboard view becomes 627,530 kg/BOE, which is the "627.53K kg/BOE" on the snapshot. The year-matched value on the same data is 621,561. See Impact for why the rest of the 627K comes from absurd seed records.
- **Expected:** Year-matched (only (facility, year) pairs with production > 0), all years: - Facility 2: 1.225 kg CO2e/BOE - Facility 9: 0.0 kg/BOE (it has no verified emissions in its production years) - Facility 10: 0.0 kg/BOE

## Root Cause

Intensity must be computed from emissions and production that cover the same period. With year="all" the server aggregates each facility across all years separately for the numerator and the denominator. Emissions from years without production (and years such as 1800 or 2099) enter the numerator but have no denominator. The client then BOE-weights these mixed per-facility ratios.

## Affected Files

- `new/client/src/pages/DashboardEnhanced.jsx`
- `new/server/routes/dashboard.py`

## Affected Features

The default dashboard KPI "Performance Intensity" and the Carbon Intensity page, which also default to "All years", show period-inconsistent intensities. For the snapshot KPI of 627.53K kg/BOE: most of the value comes from 7 Verified 2024 "Combustion" records of 5.31e11 tCO2e each, which have quantity NULL and unit MMBtu. Facility 1 (Tosyali) holds one of them against 5.46 M BOE. Those records are bad seed data (or a validation gap) and are reported separately if they are not already. The period mixing adds to that value and independently distorts facility-level results, such as Fertial being 11× too high.

## Required Changes

For year="all", group production and emissions by (facility_id, year) and include a (facility, year) pair in both the numerator and the denominator only when it has production. Alternatively, do not offer an "all years" intensity and require a single reporting year.

Implement through the shared fix for RC-7 (Dashboard filters not applied through one base query) rather than a local patch.

## Database Changes

None required.

## Backend Changes

Changes in `new/server/routes/dashboard.py` as described above.

## Frontend Changes

Changes in `new/client/src/pages/DashboardEnhanced.jsx` as described above.

## Calculation Changes

None.

## Tests To Add/Change

- Port `audit/repro/BUG-017.py` into a pytest regression test under `new/server/tests/` (assert the Expected value; independent hand-derived numbers, not a second call to the same function).
- Add edge cases: zero, missing, negative, NaN/Inf, boundary values for every field the fix touches.
- Add the group-level invariant tests for RC-7 (see Root-Cause Groups).
- Review existing tests that assert the old behaviour; change an expected value only when the new value is independently derived and documented in the test.

## Browser Verification

- Reproduce the steps in AUDIT_FINDINGS.md on an isolated stack (`audit/tools/vite_audit.mjs` + backend on an audit DB copy) and confirm the Expected result on screen.
- Compare the UI value with the API response and the DB row for the same record; refresh and reopen the record.

## Regression Risks

- Dashboard numbers under filters will change (they were inconsistent before). Watch query performance when all panels derive from one filtered base query.

## Acceptance Criteria

1. `audit/repro/BUG-017.py` exits 0 on the fixed code (it prints expected vs actual).
2. Expected behaviour holds: Year-matched (only (facility, year) pairs with production > 0), all years: - Facility 2: 1.225 kg CO2e/BOE - Facility 9: 0.0 kg/BOE (it has no verified emissions in its production years) - Facility 10: 0.0 kg/BOE
3. Full backend suite (`python -m pytest tests/` in `new/server`) and frontend checks (`npm run lint`, `npm run test`) pass.
4. No other open bug's repro changes from fail→pass or pass→fail unexpectedly (re-run `audit/work/rerun/run_all.sh`).

---

# BUG-026 — Flaring panel treats "All Years" as the current calendar year and ignores the Supply-Chain/Activity/Division/Preview-Pending filters, so it contradicts the dashboard it sits in

**Severity:** High · **Category:** Dashboard · **Phase:** P7 · **Root cause group:** RC-7 · **Found by:** Agent F (Dashboard reconciliation auditor)

**Current status:** **Still present** — `audit/repro/BUG-026.py` re-run on the final code: bug reproduced.

## Problem

Flaring panel treats "All Years" as the current calendar year and ignores the Supply-Chain/Activity/Division/Preview-Pending filters, so it contradicts the dashboard it sits in

- **Actual:** - `flaring-summary` returns `year: 2026` for "All Years": total 100 kNm3 / **210.2 tCO2e**, and a YoY of -99.92% (2026 vs 2025). - In the same table, "Flaring = 2.2M" sits above "Routine 0 / Non-Routine 0 / Safety 0". The children add up to 0 and come from another year. - Supply Chain = Heavy Industry, 2025: the panel still shows **119,346 kNm3 / 306,015 tCO2e** (company-wide Berkine flaring). The Activity and Division filters behave the same way. The Preview-Pending toggle does not change it.
- **Expected:** - With "All Years", the panel covers all years, like every other card. Independent SQL: `sum(co2e_total)` of Verified rows whose process_type contains "flar" = **2,199,048.57 tCO2e**. This equals the Detailed Breakdown "Flaring" row (2.2M). - The Routine + Non-Routine + Safety sub-rows add up to their parent "Flaring" row. - Segment "Heavy Industry", 2025: 0 flaring (SQL = 0).

## Root Cause

`get_flaring_summary` was written as a single-year and single-facility endpoint. It maps "all" to `datetime.now().year` and never reads the other filter parameters. The client renders its result inside the all-years, filtered dashboard with no year label.

## Affected Files

- `new/client/src/pages/DashboardEnhanced.jsx`
- `new/server/routes/dashboard.py`

## Affected Features

The headline flaring volume, flaring tCO2e, Decree 21-330 intensity/compliance badge and YoY on the default dashboard view describe only the current, partial calendar year (2026). Every other card shows all years. Under any Supply-Chain, Activity or Division filter the panel still shows company-wide flaring. The compliance verdict ("COMPLIANT 0.003%") is therefore computed on the wrong population.

## Required Changes

Support `year=all` (sum all years, or show "select a year" for the compliance ratio) and apply `activity/division/segment` through `Facility`, plus `includePending`. Label the panel with the year it actually covers. Do not render stream sub-rows under a parent computed from a different population.

Implement through the shared fix for RC-7 (Dashboard filters not applied through one base query) rather than a local patch.

## Database Changes

None required.

## Backend Changes

Changes in `new/server/routes/dashboard.py` as described above.

## Frontend Changes

Changes in `new/client/src/pages/DashboardEnhanced.jsx` as described above.

## Calculation Changes

None.

## Tests To Add/Change

- Port `audit/repro/BUG-026.py` into a pytest regression test under `new/server/tests/` (assert the Expected value; independent hand-derived numbers, not a second call to the same function).
- Add edge cases: zero, missing, negative, NaN/Inf, boundary values for every field the fix touches.
- Add the group-level invariant tests for RC-7 (see Root-Cause Groups).
- Review existing tests that assert the old behaviour; change an expected value only when the new value is independently derived and documented in the test.

## Browser Verification

- Reproduce the steps in AUDIT_FINDINGS.md on an isolated stack (`audit/tools/vite_audit.mjs` + backend on an audit DB copy) and confirm the Expected result on screen.
- Compare the UI value with the API response and the DB row for the same record; refresh and reopen the record.

## Regression Risks

- Dashboard numbers under filters will change (they were inconsistent before). Watch query performance when all panels derive from one filtered base query.

## Acceptance Criteria

1. `audit/repro/BUG-026.py` exits 0 on the fixed code (it prints expected vs actual).
2. Expected behaviour holds: - With "All Years", the panel covers all years, like every other card. Independent SQL: `sum(co2e_total)` of Verified rows whose process_type contains "flar" = **2,199,048.57 tCO2e**. This equals the Detailed Breakdown "Flaring" row (2.2M). - The Routine + Non-Routine + Safety sub-rows add up to their parent "Flaring" row. - Segment "Heavy Industry", 2025: 0 flaring (SQL = 0).
3. Full backend suite (`python -m pytest tests/` in `new/server`) and frontend checks (`npm run lint`, `npm run test`) pass.
4. No other open bug's repro changes from fail→pass or pass→fail unexpectedly (re-run `audit/work/rerun/run_all.sh`).

---

# BUG-094 — "Net Emissions" KPI subtracts company-wide mitigation whatever the Activity/Division filter (Steel & Iron view: Net = −1,027,393 t) and counts "Planned" projects as achieved reductions

**Severity:** High · **Category:** Dashboard · **Phase:** P7 · **Root cause group:** RC-7 · **Found by:** Agent F (Dashboard reconciliation auditor)

**Current status:** **Still present** — `audit/repro/BUG-094.py` re-run on the final code: bug reproduced.

## Problem

"Net Emissions" KPI subtracts company-wide mitigation whatever the Activity/Division filter (Steel & Iron view: Net = −1,027,393 t) and counts "Planned" projects as achieved reductions

- **Actual:** - activity = Steel & Iron: mitigation used = **1,027,500 t**, Net = **−1,027,393.16 t**. - All filters: mitigation = 1,027,500 t, which includes 312,000 t from Planned projects.
- **Expected:** - Mitigation follows the same facility filter as the gross figure. Steel & Iron: 0 t, Net = Gross = 106.84 t. (The gross value itself is affected by BUG-004.) - Only implemented or achieved reductions are subtracted. All filters: 715,500 t, not 1,027,500 t.

## Root Cause

The mitigation sub-query was not given the Activity or Division filters that the other sub-queries receive. The status of a project is ignored when netting.

## Affected Files

- `new/client/src/pages/DashboardEnhanced.jsx`
- `new/server/routes/dashboard.py`

## Affected Features

The Net Emissions KPI and the "Net Footprint" row are wrong for every Activity or Division view and can become negative. Every view overstates reductions by the Planned pipeline (+44 % on the snapshot).

## Required Changes

Pass `activity` and `division` to `_query_mitigation` and filter through `Facility`. Exclude `Planned` (and any not-implemented) projects from netting, or show them separately.

Implement through the shared fix for RC-7 (Dashboard filters not applied through one base query) rather than a local patch.

## Database Changes

None required.

## Backend Changes

Changes in `new/server/routes/dashboard.py` as described above.

## Frontend Changes

Changes in `new/client/src/pages/DashboardEnhanced.jsx` as described above.

## Calculation Changes

None.

## Tests To Add/Change

- Port `audit/repro/BUG-094.py` into a pytest regression test under `new/server/tests/` (assert the Expected value; independent hand-derived numbers, not a second call to the same function).
- Add edge cases: zero, missing, negative, NaN/Inf, boundary values for every field the fix touches.
- Add the group-level invariant tests for RC-7 (see Root-Cause Groups).
- Review existing tests that assert the old behaviour; change an expected value only when the new value is independently derived and documented in the test.

## Browser Verification

- Reproduce the steps in AUDIT_FINDINGS.md on an isolated stack (`audit/tools/vite_audit.mjs` + backend on an audit DB copy) and confirm the Expected result on screen.
- Compare the UI value with the API response and the DB row for the same record; refresh and reopen the record.

## Regression Risks

- Dashboard numbers under filters will change (they were inconsistent before). Watch query performance when all panels derive from one filtered base query.

## Acceptance Criteria

1. `audit/repro/BUG-094.py` exits 0 on the fixed code (it prints expected vs actual).
2. Expected behaviour holds: - Mitigation follows the same facility filter as the gross figure. Steel & Iron: 0 t, Net = Gross = 106.84 t. (The gross value itself is affected by BUG-004.) - Only implemented or achieved reductions are subtracted. All filters: 715,500 t, not 1,027,500 t.
3. Full backend suite (`python -m pytest tests/` in `new/server`) and frontend checks (`npm run lint`, `npm run test`) pass.
4. No other open bug's repro changes from fail→pass or pass→fail unexpectedly (re-run `audit/work/rerun/run_all.sh`).

---

# BUG-033 — Decree 21-330 flaring intensity (/flaring-summary) misconverts units: MMscf 1000× too low, scf/kscf 35× too high, UI "m³" gas production 28× too high; compliance verdict flips

**Severity:** High · **Category:** Carbon Intensity · **Phase:** P7 · **Root cause group:** RC-4 · **Found by:** Agent E (Carbon-intensity auditor) · **Independent confirmations:** 2

**Current status:** **Still present** — `audit/repro/BUG-033.py` re-run on the final code: bug reproduced.

_BUG-035 (filed concurrently by Agent F) is a duplicate of this bug and is merged here; its prior-year conversion path and case-sensitive matching are in scope of this fix._

## Problem

Decree 21-330 flaring intensity (/flaring-summary) misconverts units: MMscf 1000× too low, scf/kscf 35× too high, UI "m³" gas production 28× too high; compliance verdict flips

- **Actual:** - mmscf: +28.32 m3 (1000× too low) - scf: +1,000,000 m3 (35.3× too high) - kscf: +1,000,000 m3 (35.3× too high) - Production in m³: +28,316,800 m3 to the denominator (28.3× too high) - Final: `flaring_intensity_pct` 1.288, "EXCEEDS THRESHOLD (> 1.00%)"
- **Expected:** - Each flaring record adds +28,316.8 m3. Total flared = 184,950 m3. - Gas produced increases by 1,000,000 m3, to 135,733,458 m3. - Flaring intensity = 0.136%, "COMPLIANT (Under 1.00% Target)".

## Root Cause

Unit detection uses substring tests in the wrong order ("mscf" is checked before "mmscf", and any "k" means kilo-m3). It has no scf branch and does not recognise the "m³" spelling that the client stores. Three separate ad-hoc conversion tables exist, for the flaring-summary numerator, the denominator and the prior year.

## Affected Files

- `new/server/routes/dashboard.py`

## Affected Features

The regulatory Decree 21-330 Art. 9 flaring-intensity KPI on the Dashboard (DashboardEnhanced L1328-1345) and in the PDF report (ModernReportGenerator `/flaring-summary`) can be wrong by 1000× in either direction. The compliant or non-compliant verdict and the YoY change can be wrong. The volume shown per stream (routine, non-routine, safety) is wrong as well.

## Required Changes

Use one shared exact-match unit normaliser, e.g. `calculations/units.py`, for flared volume, produced gas and prior year. Match exact tokens (m3, m³, sm3, knm3, scf, mscf/mcf, mmscf, kscf). Reject or flag unknown units instead of defaulting to m3 or mscf.

Implement through the shared fix for RC-4 (Units are not parsed / converted in one place) rather than a local patch.

## Database Changes

None required.

## Backend Changes

Changes in `new/server/routes/dashboard.py` as described above.

## Frontend Changes

None.

## Calculation Changes

None.

## Tests To Add/Change

- Port `audit/repro/BUG-033.py` into a pytest regression test under `new/server/tests/` (assert the Expected value; independent hand-derived numbers, not a second call to the same function).
- Add edge cases: zero, missing, negative, NaN/Inf, boundary values for every field the fix touches.
- Add the group-level invariant tests for RC-4 (see Root-Cause Groups).
- Review existing tests that assert the old behaviour; change an expected value only when the new value is independently derived and documented in the test.

## Browser Verification

- API/backend fix. After the fix, open the page(s) that consume this data (see Affected Features) and confirm the displayed value matches the API and DB.

## Regression Risks

- A central unit parser changes results for every unit it now interprets correctly; stored records keep old values until a controlled recalculation. Unknown units that used to pass through will now be rejected.

## Acceptance Criteria

1. `audit/repro/BUG-033.py` exits 0 on the fixed code (it prints expected vs actual).
2. Expected behaviour holds: - Each flaring record adds +28,316.8 m3. Total flared = 184,950 m3. - Gas produced increases by 1,000,000 m3, to 135,733,458 m3. - Flaring intensity = 0.136%, "COMPLIANT (Under 1.00% Target)".
3. Full backend suite (`python -m pytest tests/` in `new/server`) and frontend checks (`npm run lint`, `npm run test`) pass.
4. No other open bug's repro changes from fail→pass or pass→fail unexpectedly (re-run `audit/work/rerun/run_all.sh`).

---

# BUG-036 — Flaring panel invents a 56 % / 40 % / 4 % Routine / Non-Routine / Safety split for generic "flaring" records and shows 0 tCO₂e for every stream (and a 2.5 t/kNm³ proxy when CO₂e is 0)

**Severity:** Medium · **Category:** Dashboard · **Phase:** P7 · **Root cause group:** RC-7 · **Found by:** Agent F (Dashboard reconciliation auditor)

**Current status:** **Still present** — `audit/repro/BUG-036.py` re-run on the final code: bug reproduced.

## Problem

Flaring panel invents a 56 % / 40 % / 4 % Routine / Non-Routine / Safety split for generic "flaring" records and shows 0 tCO₂e for every stream (and a 2.5 t/kNm³ proxy when CO₂e is 0)

- **Actual:** The panel shows Routine **56 kNm3 (56 %) • 0 tCO2e**, Non-Routine **40 kNm3 (40 %) • 0 tCO2e**, Safety **4 kNm3 (4 %) • 0 tCO2e** and Total **100 kNm3 • 210.2 tCO2e**. The percentages look measured but are a hard-coded "industry benchmark". The streams add up to 0 t against a 210.2 t total. When a generic flaring row has `co2e_total = 0` (e.g. the 2025 Verified `mscf` rows), the total CO2e is replaced by a 2.5 t/kNm3 proxy and presented as a result.
- **Expected:** The stream breakdown is unknown. The panel should show the 100 kNm3 / 210.2 t as "unclassified flaring", or refuse to split it. If a split is shown, the tCO2e must be split the same way (117.7 / 84.1 / 8.4 t) so that the streams add up to the total.

## Root Cause

A fallback allocates the volume by fixed benchmark ratios but does not allocate the CO2e. There is no indicator that the figures are modeled.

## Affected Files

- `new/server/routes/dashboard.py`

## Affected Features

Routine-flaring volume is the quantity regulated by Decree 21-330, Zero Routine Flaring and OGMP. The dashboard reports a routine volume that was never measured or entered, and zero emissions for every stream. Users can take fabricated routine-flaring figures into disclosures.

## Required Changes

Remove the fixed 56/40/4 split. Report generic flaring as "Unclassified". If modeled values are kept, allocate the CO2e with them and label them as estimated. Do not substitute a 2.5 t/kNm3 proxy without a flag.

Implement through the shared fix for RC-7 (Dashboard filters not applied through one base query) rather than a local patch.

## Database Changes

None required.

## Backend Changes

Changes in `new/server/routes/dashboard.py` as described above.

## Frontend Changes

None.

## Calculation Changes

None.

## Tests To Add/Change

- Port `audit/repro/BUG-036.py` into a pytest regression test under `new/server/tests/` (assert the Expected value; independent hand-derived numbers, not a second call to the same function).
- Add edge cases: zero, missing, negative, NaN/Inf, boundary values for every field the fix touches.
- Add the group-level invariant tests for RC-7 (see Root-Cause Groups).
- Review existing tests that assert the old behaviour; change an expected value only when the new value is independently derived and documented in the test.

## Browser Verification

- API/backend fix. After the fix, open the page(s) that consume this data (see Affected Features) and confirm the displayed value matches the API and DB.

## Regression Risks

- Dashboard numbers under filters will change (they were inconsistent before). Watch query performance when all panels derive from one filtered base query.

## Acceptance Criteria

1. `audit/repro/BUG-036.py` exits 0 on the fixed code (it prints expected vs actual).
2. Expected behaviour holds: The stream breakdown is unknown. The panel should show the 100 kNm3 / 210.2 t as "unclassified flaring", or refuse to split it. If a split is shown, the tCO2e must be split the same way (117.7 / 84.1 / 8.4 t) so that the streams add up to the total.
3. Full backend suite (`python -m pytest tests/` in `new/server`) and frontend checks (`npm run lint`, `npm run test`) pass.
4. No other open bug's repro changes from fail→pass or pass→fail unexpectedly (re-run `audit/work/rerun/run_all.sh`).

---

# BUG-054 — "Preview Pending Data" and the pending banner are inconsistent with the rest of the dashboard: the toggle changes only the KPIs (categorical/org breakdown and Scope 3 stay Verified-only), and the banner ignores the Supply Chain, Activity and Division filters and omits Scope 3

**Severity:** Medium · **Category:** Dashboard · **Phase:** P7 · **Root cause group:** RC-7 · **Found by:** Agent F (Dashboard reconciliation auditor)

**Current status:** **Still present** — `audit/repro/BUG-054.py` re-run on the final code: bug reproduced.

## Problem

"Preview Pending Data" and the pending banner are inconsistent with the rest of the dashboard: the toggle changes only the KPIs (categorical/org breakdown and Scope 3 stay Verified-only), and the banner ignores the Supply Chain, Activity and Division filters and omits Scope 3

- **Actual:** - Toggle on: Gross KPI = 8,409,568,816,085.97 (correct). Categorical/organizational-breakdown sum = **3,723,127,249,117.66** (Verified only). Scope 3 stays 216.85. Activity donut, categorical overview and flaring panel do not change. - The banner shows 128 records / 4,686,441,566,968.31 t for every Supply Chain, Activity and Division selection (verified via API for activity=Steel & Iron, division=Metallurgy, segment=Heavy Industry and segment=Upstream). Only the Year and Region (facility) filters change it. The 21 Pending Scope 3 rows are never counted.
- **Expected:** - With the toggle on, every panel shows Verified + Pending. SQL V+P: S1+S2 = 8,409,568,816,085.97 t and Scope 3 = 366.85 t. The organizational breakdown equals the Gross KPI. - The banner describes the filtered population. For Supply Chain = Heavy Industry: 13 S1 + 3 S2 = **16 records**, 4,686,441,120,049 t. For Upstream: 101 S1 rows, 446,561 t. Scope 3 Pending rows are included, or the banner says they are excluded.

## Root Cause

The `includePending` flag and the filter set are applied per sub-query and not shared. Only `_query_summary` received the flag, and the pending-stats query was written with a subset of the filters.

## Affected Files

- `new/server/routes/dashboard.py`

## Affected Features

In preview mode the same screen shows two different totals (8.41 T vs 3.72 T) for the same scope. The pending banner overstates or understates the pending volume for filtered views, e.g. it tells an Upstream reviewer there are 4.69 T t pending when their view has 446,561 t.

## Required Changes

Pass `include_pending` to every sub-query, or show a clear "verified-only" label on panels that ignore it. Apply the same Facility-level activity, division and segment filters to `pending_stats`, and add Scope 3 Pending rows.

Implement through the shared fix for RC-7 (Dashboard filters not applied through one base query) rather than a local patch.

## Database Changes

None required.

## Backend Changes

Changes in `new/server/routes/dashboard.py` as described above.

## Frontend Changes

None.

## Calculation Changes

None.

## Tests To Add/Change

- Port `audit/repro/BUG-054.py` into a pytest regression test under `new/server/tests/` (assert the Expected value; independent hand-derived numbers, not a second call to the same function).
- Add edge cases: zero, missing, negative, NaN/Inf, boundary values for every field the fix touches.
- Add the group-level invariant tests for RC-7 (see Root-Cause Groups).
- Review existing tests that assert the old behaviour; change an expected value only when the new value is independently derived and documented in the test.

## Browser Verification

- API/backend fix. After the fix, open the page(s) that consume this data (see Affected Features) and confirm the displayed value matches the API and DB.

## Regression Risks

- Dashboard numbers under filters will change (they were inconsistent before). Watch query performance when all panels derive from one filtered base query.

## Acceptance Criteria

1. `audit/repro/BUG-054.py` exits 0 on the fixed code (it prints expected vs actual).
2. Expected behaviour holds: - With the toggle on, every panel shows Verified + Pending. SQL V+P: S1+S2 = 8,409,568,816,085.97 t and Scope 3 = 366.85 t. The organizational breakdown equals the Gross KPI. - The banner describes the filtered population. For Supply Chain = Heavy Industry: 13 S1 + 3 S2 = **16 records**, 4,686,441,120,049 t. For Upstream: 101 S1 rows, 446,561 t. Scope 3 Pending rows are included, or the banner sa…
3. Full backend suite (`python -m pytest tests/` in `new/server`) and frontend checks (`npm run lint`, `npm run test`) pass.
4. No other open bug's repro changes from fail→pass or pass→fail unexpectedly (re-run `audit/work/rerun/run_all.sh`).

---

# BUG-041 — Dashboard "% GOAL" badge in the default All-years view divides the cumulative multi-year Scope 1+2 total by the single current-year goal (and ignores region/facility filters)

**Severity:** Medium · **Category:** Dashboard · **Phase:** P7 · **Root cause group:** RC-7 · **Found by:** Agent H (SBTi Auditor)

**Current status:** **Still present** — `audit/repro/BUG-041.py` re-run on the final code: bug reproduced.

## Problem

Dashboard "% GOAL" badge in the default All-years view divides the cumulative multi-year Scope 1+2 total by the single current-year goal (and ignores region/facility filters)

- **Actual:** "155.0% GOAL" in red (danger class, >100 %), and the header shows "Target 2026: 1,000 tCO₂e" next to a cumulative 2020-2026 total. The goal is also compared with region/facility-filtered totals although goals are corporate-wide.
- **Expected:** Either no goal badge in the All-years view, or current-year actual / current-year goal = 0 / 1000 = 0 % (YTD).

## Root Cause

Year = "all" is mapped to the current year's goal while the numerator is the all-year sum; no filter-scope awareness.

## Affected Files

- `new/client/src/pages/DashboardEnhanced.jsx`
- `new/server/routes/dashboard.py`

## Affected Features

The default dashboard view shows a meaningless and alarming goal attainment percentage once a goal exists for the current year.

## Required Changes

Hide the badge when Year = All (or compare only the goal year's actual), and hide/scale it when region/facility filters are active.

Implement through the shared fix for RC-7 (Dashboard filters not applied through one base query) rather than a local patch.

## Database Changes

None required.

## Backend Changes

Changes in `new/server/routes/dashboard.py` as described above.

## Frontend Changes

Changes in `new/client/src/pages/DashboardEnhanced.jsx` as described above.

## Calculation Changes

None.

## Tests To Add/Change

- Port `audit/repro/BUG-041.py` into a pytest regression test under `new/server/tests/` (assert the Expected value; independent hand-derived numbers, not a second call to the same function).
- Add edge cases: zero, missing, negative, NaN/Inf, boundary values for every field the fix touches.
- Add the group-level invariant tests for RC-7 (see Root-Cause Groups).
- Review existing tests that assert the old behaviour; change an expected value only when the new value is independently derived and documented in the test.

## Browser Verification

- Reproduce the steps in AUDIT_FINDINGS.md on an isolated stack (`audit/tools/vite_audit.mjs` + backend on an audit DB copy) and confirm the Expected result on screen.
- Compare the UI value with the API response and the DB row for the same record; refresh and reopen the record.

## Regression Risks

- Dashboard numbers under filters will change (they were inconsistent before). Watch query performance when all panels derive from one filtered base query.

## Acceptance Criteria

1. `audit/repro/BUG-041.py` exits 0 on the fixed code (it prints expected vs actual).
2. Expected behaviour holds: Either no goal badge in the All-years view, or current-year actual / current-year goal = 0 / 1000 = 0 % (YTD).
3. Full backend suite (`python -m pytest tests/` in `new/server`) and frontend checks (`npm run lint`, `npm run test`) pass.
4. No other open bug's repro changes from fail→pass or pass→fail unexpectedly (re-run `audit/work/rerun/run_all.sh`).

---

# BUG-061 — Dashboard "Emissions by Source" mis-classifies process types: fuel-gas combustion (6.47 M t) shown as "Other", pneumatics/tanks/dehydrators/unloading/completions as "Other" instead of Venting, fugitives merged into "Venting", mobile combustion labelled "Stationary Combustion"

**Severity:** Medium · **Category:** Dashboard · **Phase:** P7 · **Root cause group:** RC-7 · **Found by:** Agent F (Dashboard reconciliation auditor) · **Independent confirmations:** 1

**Current status:** **Still present** — `audit/repro/BUG-061.py` re-run on the final code: bug reproduced.

## Problem

Dashboard "Emissions by Source" mis-classifies process types: fuel-gas combustion (6.47 M t) shown as "Other", pneumatics/tanks/dehydrators/unloading/completions as "Other" instead of Venting, fugitives merged into "Venting", mobile combustion labelled "Stationary Combustion"

- **Actual:** API/UI: Combustion 3,723,116,579,281.52 · Flaring 2,199,048.57 · Venting 460,645.31 (includes fugitives) · Other **6,470,439.64**. The UI "Other Sources 6.5M" is 99.95 % fuel-gas combustion. Vented CH4 sources (pneumatics, tanks, dehydrator, unloading) are hidden in "Other". `mobile_combustion` is shown in the "Stationary Combustion" row, while `mobile` goes to "Other".
- **Expected:** Classification by source category, as in the platform's own dispatcher and the API Compendium: fuel gas is combustion; pneumatic, tank, dehydrator, AGR, unloading, completion and drilling are vented; fugitives are a separate category, or at least not called "Venting"; mobile combustion is not "Stationary". Independent split: Combustion 3,723,123,046,693.43 · Flaring 2,199,048.57 · Venting 140,187.52 · Fugitive 323,458.97 · Other **26.56**.

## Root Cause

A hand-written, incomplete substring map is used instead of the dispatcher's process-type to category mapping. The client relabels the combustion bucket as "Stationary".

## Affected Files

- `new/client/src/pages/DashboardEnhanced.jsx`
- `new/server/routes/dashboard.py`

## Affected Features

The source mix on the dashboard (and in the Detailed Breakdown) misreports where emissions come from. Venting and fugitives, the key methane categories for OGMP and methane regulation, are mixed together or hidden in "Other", and a large combustion source is shown as "Other".

## Required Changes

Classify with the dispatcher's canonical process-type categories (combustion stationary/mobile, flaring, vented, fugitive, process). Add a `fugitive` bucket, and label the combustion row "Combustion", or split it into stationary and mobile.

Implement through the shared fix for RC-7 (Dashboard filters not applied through one base query) rather than a local patch.

## Database Changes

None required.

## Backend Changes

Changes in `new/server/routes/dashboard.py` as described above.

## Frontend Changes

Changes in `new/client/src/pages/DashboardEnhanced.jsx` as described above.

## Calculation Changes

None.

## Tests To Add/Change

- Port `audit/repro/BUG-061.py` into a pytest regression test under `new/server/tests/` (assert the Expected value; independent hand-derived numbers, not a second call to the same function).
- Add edge cases: zero, missing, negative, NaN/Inf, boundary values for every field the fix touches.
- Add the group-level invariant tests for RC-7 (see Root-Cause Groups).
- Review existing tests that assert the old behaviour; change an expected value only when the new value is independently derived and documented in the test.

## Browser Verification

- Reproduce the steps in AUDIT_FINDINGS.md on an isolated stack (`audit/tools/vite_audit.mjs` + backend on an audit DB copy) and confirm the Expected result on screen.
- Compare the UI value with the API response and the DB row for the same record; refresh and reopen the record.

## Regression Risks

- Dashboard numbers under filters will change (they were inconsistent before). Watch query performance when all panels derive from one filtered base query.

## Acceptance Criteria

1. `audit/repro/BUG-061.py` exits 0 on the fixed code (it prints expected vs actual).
2. Expected behaviour holds: Classification by source category, as in the platform's own dispatcher and the API Compendium: fuel gas is combustion; pneumatic, tank, dehydrator, AGR, unloading, completion and drilling are vented; fugitives are a separate category, or at least not called "Venting"; mobile combustion is not "Stationary". Independent split: Combustion 3,723,123,046,693.43 · Flaring 2,199,048.57 · Venting 140,187…
3. Full backend suite (`python -m pytest tests/` in `new/server`) and frontend checks (`npm run lint`, `npm run test`) pass.
4. No other open bug's repro changes from fail→pass or pass→fail unexpectedly (re-run `audit/work/rerun/run_all.sh`).

---

# BUG-071 — Dashboard cache is not invalidated after a manual Scope 1 create or a bulk upload: new records are missing from the dashboard for up to 5 minutes (per worker)

**Severity:** Medium · **Category:** Dashboard · **Phase:** P7 · **Root cause group:** RC-5 · **Found by:** Agent B (Emissions Auditor) · **Independent confirmations:** 1

**Current status:** **Still present** — `audit/repro/BUG-071.py` re-run on the final code: bug reproduced.

## Problem

Dashboard cache is not invalidated after a manual Scope 1 create or a bulk upload: new records are missing from the dashboard for up to 5 minutes (per worker)

- **Actual:** ``` before=3718016910467.4102 after=3718016910467.4102 db=3718016910520.5249 actual diff=0.0000 ``` After a completed bulk upload of 5 rows (year 2038), `summary?year=2038&includePending=true` in the same process still returned `[]`. A fresh process returned scope1_total 129.26 t (`audit/work/B/t11.py`, `t13.py`).
- **Expected:** The summary increases by 53.1145 t right away, as it does after approve, delete and Scope 2/3 creates. Hand calc: 1000 x (53.06 + 0.001x28 + 0.0001x265) / 1000.

## Root Cause

Cache invalidation depends on detecting pending ORM objects in `before_commit`. This does not work when rows were flushed earlier or written with `bulk_save_objects`.

## Affected Files

- `new/server/app.py`

## Affected Features

Users who add data, or finish an import, and then open the dashboard see stale totals, KPIs, pending counts and charts (DASHBOARD_CACHE TTL 300 s, every cached query and batch-all). This looks like data loss or a failed upload.

## Required Changes

Call `clear_dashboard_cache()` explicitly in `add_emission` and at the end of `_process_file_thread`. Alternatively, track changes in an `after_flush` listener, or set `session.info["has_relevant_changes"]=True` at flush time, instead of inspecting `session.new` in `before_commit`.

Implement through the shared fix for RC-5 (Edit / recalculation path diverges from the create path) rather than a local patch.

## Database Changes

None required.

## Backend Changes

Changes in `new/server/app.py` as described above.

## Frontend Changes

None.

## Calculation Changes

None.

## Tests To Add/Change

- Port `audit/repro/BUG-071.py` into a pytest regression test under `new/server/tests/` (assert the Expected value; independent hand-derived numbers, not a second call to the same function).
- Add edge cases: zero, missing, negative, NaN/Inf, boundary values for every field the fix touches.
- Add the group-level invariant tests for RC-5 (see Root-Cause Groups).
- Review existing tests that assert the old behaviour; change an expected value only when the new value is independently derived and documented in the test.

## Browser Verification

- API/backend fix. After the fix, open the page(s) that consume this data (see Affected Features) and confirm the displayed value matches the API and DB.

## Regression Risks

- Shared payload/persistence helpers touch every Scope 1 write path (create, PUT, import, bulk); edits to existing records will now produce different (correct) values than before.

## Acceptance Criteria

1. `audit/repro/BUG-071.py` exits 0 on the fixed code (it prints expected vs actual).
2. Expected behaviour holds: The summary increases by 53.1145 t right away, as it does after approve, delete and Scope 2/3 creates. Hand calc: 1000 x (53.06 + 0.001x28 + 0.0001x265) / 1000.
3. Full backend suite (`python -m pytest tests/` in `new/server`) and frontend checks (`npm run lint`, `npm run test`) pass.
4. No other open bug's repro changes from fail→pass or pass→fail unexpectedly (re-run `audit/work/rerun/run_all.sh`).

---

# BUG-079 — OGMP reconciliation in the default "All years" view compares the AVERAGE of annual top-down surveys with the SUM of multi-year bottom-up CH4, so perfectly reconciled facilities are flagged (−80 %)

**Severity:** Medium · **Category:** Methane · **Phase:** P7 · **Root cause group:** RC-7 · **Found by:** Agent D (Methane Auditor)

**Current status:** **Still present** — `audit/repro/BUG-079.py` re-run on the final code: bug reproduced.

## Problem

OGMP reconciliation in the default "All years" view compares the AVERAGE of annual top-down surveys with the SUM of multi-year bottom-up CH4, so perfectly reconciled facilities are flagged (−80 %)

- **Actual:** - Per year: 0.0 %, "Reconciled". - `year=all`: top-down 2,069.78 (the mean) vs bottom-up 10,348.88 (the sum) gives **−80.0 %, "Discrepancy Flagged"** on both `/ogmp-metrics` and `/intensity-stats`. `intensity-stats.current_ogmp_level` drops from 5 to 4.
- **Expected:** Every year reconciles (0 %). The multi-year view should compare like with like: Σ top-down (10,348.88) vs Σ bottom-up (10,348.88), which is 0 % and "Reconciled", or it should reconcile year by year.

## Root Cause

Aggregation mismatch. The mean of annual surveys is an annual rate, while the unfiltered sum is a multi-year total. Averaging is meant for multiple surveys within one facility-year (Decision D-02), but it is applied across years.

## Affected Files

- `new/server/routes/dashboard.py`
- `new/server/routes/reports.py`

## Affected Features

The OGMP Gold-Standard roadmap on the Methane Intensity page, which opens in "All years" by default, flags reconciliation discrepancies and understates levels for every facility with more than one year of inventory. The same mismatch applies in the OGMP Excel export without a year filter.

## Required Changes

Average surveys per (facility, year), then sum across years, or reconcile per year and report the multi-year view as per-year statuses. Never pair an average with an unfiltered sum.

Implement through the shared fix for RC-7 (Dashboard filters not applied through one base query) rather than a local patch.

## Database Changes

None required.

## Backend Changes

Changes in `new/server/routes/dashboard.py`, `new/server/routes/reports.py` as described above.

## Frontend Changes

None.

## Calculation Changes

None.

## Tests To Add/Change

- Port `audit/repro/BUG-079.py` into a pytest regression test under `new/server/tests/` (assert the Expected value; independent hand-derived numbers, not a second call to the same function).
- Add edge cases: zero, missing, negative, NaN/Inf, boundary values for every field the fix touches.
- Add the group-level invariant tests for RC-7 (see Root-Cause Groups).
- Review existing tests that assert the old behaviour; change an expected value only when the new value is independently derived and documented in the test.

## Browser Verification

- API/backend fix. After the fix, open the page(s) that consume this data (see Affected Features) and confirm the displayed value matches the API and DB.

## Regression Risks

- Dashboard numbers under filters will change (they were inconsistent before). Watch query performance when all panels derive from one filtered base query.

## Acceptance Criteria

1. `audit/repro/BUG-079.py` exits 0 on the fixed code (it prints expected vs actual).
2. Expected behaviour holds: Every year reconciles (0 %). The multi-year view should compare like with like: Σ top-down (10,348.88) vs Σ bottom-up (10,348.88), which is 0 % and "Reconciled", or it should reconcile year by year.
3. Full backend suite (`python -m pytest tests/` in `new/server`) and frontend checks (`npm run lint`, `npm run test`) pass.
4. No other open bug's repro changes from fail→pass or pass→fail unexpectedly (re-run `audit/work/rerun/run_all.sh`).

---

# BUG-064 — Categorical Emissions Overview groups facilities by name instead of id: six distinct facilities are merged into one "Updated Facility" card (3.19 T t)

**Severity:** Low · **Category:** Dashboard · **Phase:** P7 · **Root cause group:** RC-7 · **Found by:** Agent F (Dashboard reconciliation auditor)

**Current status:** **Still present** — `audit/repro/BUG-064.py` re-run on the final code: bug reproduced.

## Problem

Categorical Emissions Overview groups facilities by name instead of id: six distinct facilities are merged into one "Updated Facility" card (3.19 T t)

- **Actual:** The API returns one merged row, total 3,186,870,000,265.25 t. The UI shows a single "Updated Facility 3.2T" card.
- **Expected:** One card per facility (6 cards, each 531,145,000,044 t approx.), or names disambiguated.

## Root Cause

The group key uses display attributes instead of the facility primary key.

## Affected Files

- `new/server/routes/dashboard.py`

## Affected Features

Per-facility drill-down is wrong whenever two facilities share a name and field, which the data model does not prevent. The merged card overstates one "facility" by the number of namesakes.

## Required Changes

Group by `Facility.id`, return `facility_id`, and key `output_map` on it. Consider a uniqueness constraint or warning on facility names.

Implement through the shared fix for RC-7 (Dashboard filters not applied through one base query) rather than a local patch.

## Database Changes

None required.

## Backend Changes

Changes in `new/server/routes/dashboard.py` as described above.

## Frontend Changes

None.

## Calculation Changes

None.

## Tests To Add/Change

- Port `audit/repro/BUG-064.py` into a pytest regression test under `new/server/tests/` (assert the Expected value; independent hand-derived numbers, not a second call to the same function).
- Add edge cases: zero, missing, negative, NaN/Inf, boundary values for every field the fix touches.
- Add the group-level invariant tests for RC-7 (see Root-Cause Groups).
- Review existing tests that assert the old behaviour; change an expected value only when the new value is independently derived and documented in the test.

## Browser Verification

- API/backend fix. After the fix, open the page(s) that consume this data (see Affected Features) and confirm the displayed value matches the API and DB.

## Regression Risks

- Dashboard numbers under filters will change (they were inconsistent before). Watch query performance when all panels derive from one filtered base query.

## Acceptance Criteria

1. `audit/repro/BUG-064.py` exits 0 on the fixed code (it prints expected vs actual).
2. Expected behaviour holds: One card per facility (6 cards, each 531,145,000,044 t approx.), or names disambiguated.
3. Full backend suite (`python -m pytest tests/` in `new/server`) and frontend checks (`npm run lint`, `npm run test`) pass.
4. No other open bug's repro changes from fail→pass or pass→fail unexpectedly (re-run `audit/work/rerun/run_all.sh`).

---

# BUG-072 — Pending-records banner ignores the GWP-20 toggle: it always shows GWP-100 tCO2e while every other dashboard figure switches to GWP-20

**Severity:** Low · **Category:** Dashboard · **Phase:** P7 · **Root cause group:** RC-7 · **Found by:** Agent D (Methane Auditor) · **Independent confirmations:** 2

**Current status:** **Still present** — `audit/repro/BUG-072.py` re-run on the final code: bug reproduced.

## Problem

Pending-records banner ignores the GWP-20 toggle: it always shows GWP-100 tCO2e while every other dashboard figure switches to GWP-20

- **Actual:** `totalCo2e` = 446,919.3 in both horizons (GWP-100). The banner understates pending CO2e by 34 % in GWP-20 mode, so it disagrees with the amount the hero card jumps by when "Preview Pending" is switched on (summary applies GWP-20 to pending rows).
- **Expected:** In GWP-20 mode the banner figure should be on the same basis as the KPIs next to it: 678,365.0 tCO2e (app's own AR5 20-yr factors, 82.5 / 268; 695,856 with the correct AR5 84 / 264, see BUG-013).

## Root Cause

The pending summary sums the stored GWP-100 `co2e_total` and never applies the horizon delta that `_query_summary` applies.

## Affected Files

- `new/client/src/pages/DashboardEnhanced.jsx`
- `new/server/routes/dashboard.py`

## Affected Features

Misleading figure next to methane-heavy KPIs in GWP-20 mode. The pending backlog looks a third smaller than it is on the chosen basis.

## Required Changes

Include CH4/N2O sums in the pending query and apply the same `get_active_gwp` delta as `_query_summary` when `gwp_horizon=20`, or label the banner figure "GWP-100".

Implement through the shared fix for RC-7 (Dashboard filters not applied through one base query) rather than a local patch.

## Database Changes

None required.

## Backend Changes

Changes in `new/server/routes/dashboard.py` as described above.

## Frontend Changes

Changes in `new/client/src/pages/DashboardEnhanced.jsx` as described above.

## Calculation Changes

None.

## Tests To Add/Change

- Port `audit/repro/BUG-072.py` into a pytest regression test under `new/server/tests/` (assert the Expected value; independent hand-derived numbers, not a second call to the same function).
- Add edge cases: zero, missing, negative, NaN/Inf, boundary values for every field the fix touches.
- Add the group-level invariant tests for RC-7 (see Root-Cause Groups).
- Review existing tests that assert the old behaviour; change an expected value only when the new value is independently derived and documented in the test.

## Browser Verification

- Reproduce the steps in AUDIT_FINDINGS.md on an isolated stack (`audit/tools/vite_audit.mjs` + backend on an audit DB copy) and confirm the Expected result on screen.
- Compare the UI value with the API response and the DB row for the same record; refresh and reopen the record.

## Regression Risks

- Dashboard numbers under filters will change (they were inconsistent before). Watch query performance when all panels derive from one filtered base query.

## Acceptance Criteria

1. `audit/repro/BUG-072.py` exits 0 on the fixed code (it prints expected vs actual).
2. Expected behaviour holds: In GWP-20 mode the banner figure should be on the same basis as the KPIs next to it: 678,365.0 tCO2e (app's own AR5 20-yr factors, 82.5 / 268; 695,856 with the correct AR5 84 / 264, see BUG-013).
3. Full backend suite (`python -m pytest tests/` in `new/server`) and frontend checks (`npm run lint`, `npm run test`) pass.
4. No other open bug's repro changes from fail→pass or pass→fail unexpectedly (re-run `audit/work/rerun/run_all.sh`).

---

# BUG-080 — Two contradictory OGMP facility-level algorithms: /intensity-stats reports Level 5 (Gold Standard) where the canonical service (/ogmp-metrics, OGMP export) reports Level 4 for the same facility and year

**Severity:** Low · **Category:** Methane · **Phase:** P7 · **Root cause group:** RC-6 · **Found by:** Agent D (Methane Auditor)

**Current status:** **Still present** — `audit/repro/BUG-080.py` re-run on the final code: bug reproduced.

## Problem

Two contradictory OGMP facility-level algorithms: /intensity-stats reports Level 5 (Gold Standard) where the canonical service (/ogmp-metrics, OGMP export) reports Level 4 for the same facility and year

- **Actual:** - Facility 169 / 2021: `/ogmp-metrics` gives 4; `/intensity-stats` gives **5**. - Snapshot 2024: 9 of 25 facilities differ (e.g. facilities 1, 150, 155: 2 vs 3; facility 169: 3 vs 4). - 2025: 5 of 80 differ.
- **Expected:** One level per facility-year. Per the code's own OGMP 2.0 note, reconciliation with an L2/L3 inventory is capped at Level 4.

## Root Cause

The OGMP level logic is duplicated in `_query_intensity_stats` instead of calling `services.ogmp.compute_facility_ogmp_level` / `ogmp_level_for`.

## Affected Files

- `new/server/routes/dashboard.py`
- `new/server/services/ogmp.py`

## Affected Features

API consumers of `/intensity-stats` and `batch-all.intensity_stats` get a Gold-Standard Level 5 claim that the roadmap page and the regulatory export deny. The current client renders `highest_ogmp_level` first, so the UI impact is limited.

## Required Changes

Use the canonical service in `_query_intensity_stats`, and fix the service itself as described in BUG-031.

Implement through the shared fix for RC-6 (Client and server hold separate copies of catalogs, constants and formulas) rather than a local patch.

## Database Changes

None required.

## Backend Changes

Changes in `new/server/routes/dashboard.py`, `new/server/services/ogmp.py` as described above.

## Frontend Changes

None.

## Calculation Changes

None.

## Tests To Add/Change

- Port `audit/repro/BUG-080.py` into a pytest regression test under `new/server/tests/` (assert the Expected value; independent hand-derived numbers, not a second call to the same function).
- Add edge cases: zero, missing, negative, NaN/Inf, boundary values for every field the fix touches.
- Add the group-level invariant tests for RC-6 (see Root-Cause Groups).
- Review existing tests that assert the old behaviour; change an expected value only when the new value is independently derived and documented in the test.

## Browser Verification

- API/backend fix. After the fix, open the page(s) that consume this data (see Affected Features) and confirm the displayed value matches the API and DB.

## Regression Risks

- Removing a client-side catalog/formula can remove options users rely on; every factor still offered must exist server-side before the switch. Previews will change to server-computed values.

## Acceptance Criteria

1. `audit/repro/BUG-080.py` exits 0 on the fixed code (it prints expected vs actual).
2. Expected behaviour holds: One level per facility-year. Per the code's own OGMP 2.0 note, reconciliation with an L2/L3 inventory is capped at Level 4.
3. Full backend suite (`python -m pytest tests/` in `new/server`) and frontend checks (`npm run lint`, `npm run test`) pass.
4. No other open bug's repro changes from fail→pass or pass→fail unexpectedly (re-run `audit/work/rerun/run_all.sh`).

---

# BUG-086 — Methane loss-rate segment classification differs between the KPI cards, the trend chart and the server: "Downstream / Processing" counts as Midstream in the trend, and "Upstream / Extraction" is dropped from the Upstream KPI

**Severity:** Low · **Category:** Methane · **Phase:** P7 · **Root cause group:** RC-6 · **Found by:** Agent D (Methane Auditor)

**Current status:** **Still present** — `audit/repro/BUG-086.py` re-run on the final code: bug reproduced.

## Problem

Methane loss-rate segment classification differs between the KPI cards, the trend chart and the server: "Downstream / Processing" counts as Midstream in the trend, and "Upstream / Extraction" is dropped from the Upstream KPI

- **Actual:** For 2025: - KPI midstream gas = **0 m³**, and the Midstream card shows no rate. The trend's midstream gas = **122,158,675 m³**, all from "Downstream / Processing" facilities. - KPI upstream gas = 15,490,256,856 m³; trend upstream gas = 15,548,277,980 m³. The KPI omits the "Upstream / Extraction" facilities. - Loss rates therefore differ between the card and the chart point for the same year.
- **Expected:** The same year, filters and facilities give the same Upstream/Midstream gas denominators and loss rates in the KPI cards and in the 5-year trend chart. Refinery ("Downstream / Processing") gas should not count toward the Midstream OGMP rate.

## Root Cause

Three independent, inconsistent segment-to-category mappings. There is no canonical segment enum; the facility data uses free-text composites.

## Affected Files

- `new/client/src/pages/MethaneIntensity.jsx`
- `new/server/routes/dashboard.py`

## Affected Features

Segment-level methane loss rates and OGMP targets (0.20 % vs 0.05 %) are applied to different facility sets depending on which widget is read. With the current data the numeric difference is small, but it grows with the volume of refinery or "Upstream / Extraction" gas.

## Required Changes

Add one server-side canonical segment classifier (and return `segment_category` in the API), then use it in all three places. Validate the facility segment against an enum.

Implement through the shared fix for RC-6 (Client and server hold separate copies of catalogs, constants and formulas) rather than a local patch.

## Database Changes

None required.

## Backend Changes

Changes in `new/server/routes/dashboard.py` as described above.

## Frontend Changes

Changes in `new/client/src/pages/MethaneIntensity.jsx` as described above.

## Calculation Changes

None.

## Tests To Add/Change

- Port `audit/repro/BUG-086.py` into a pytest regression test under `new/server/tests/` (assert the Expected value; independent hand-derived numbers, not a second call to the same function).
- Add edge cases: zero, missing, negative, NaN/Inf, boundary values for every field the fix touches.
- Add the group-level invariant tests for RC-6 (see Root-Cause Groups).
- Review existing tests that assert the old behaviour; change an expected value only when the new value is independently derived and documented in the test.

## Browser Verification

- Reproduce the steps in AUDIT_FINDINGS.md on an isolated stack (`audit/tools/vite_audit.mjs` + backend on an audit DB copy) and confirm the Expected result on screen.
- Compare the UI value with the API response and the DB row for the same record; refresh and reopen the record.

## Regression Risks

- Removing a client-side catalog/formula can remove options users rely on; every factor still offered must exist server-side before the switch. Previews will change to server-computed values.

## Acceptance Criteria

1. `audit/repro/BUG-086.py` exits 0 on the fixed code (it prints expected vs actual).
2. Expected behaviour holds: The same year, filters and facilities give the same Upstream/Midstream gas denominators and loss rates in the KPI cards and in the 5-year trend chart. Refinery ("Downstream / Processing") gas should not count toward the Midstream OGMP rate.
3. Full backend suite (`python -m pytest tests/` in `new/server`) and frontend checks (`npm run lint`, `npm run test`) pass.
4. No other open bug's repro changes from fail→pass or pass→fail unexpectedly (re-run `audit/work/rerun/run_all.sh`).

---

# BUG-088 — Facilities with CH4 emissions but no gas production get methane_loss_rate_pct = 0 and ogmp_target_status "Compliant"

**Severity:** Low · **Category:** Methane · **Phase:** P7 · **Root cause group:** RC-7 · **Found by:** Agent D (Methane Auditor)

**Current status:** **Still present** — `audit/repro/BUG-088.py` re-run on the final code: bug reproduced.

## Problem

Facilities with CH4 emissions but no gas production get methane_loss_rate_pct = 0 and ogmp_target_status "Compliant"

- **Actual:** `methane_loss_rate_pct: 0.0`, `ogmp_target_status: "Compliant"` (facilities 146 and 147). The per-facility bar chart and heatmap show 0 / "-" for them.
- **Expected:** The loss rate is undefined (null), with a status such as "Missing Production Data" or "N/A". The OGMP Excel export handles this case correctly with "Non-Compliant (Missing Production Data)" in `reports.py` ~933-936, and the MethaneIntensity page KPI shows "Pending Production".

## Root Cause

A zero denominator is coerced to a 0 % rate, which then passes the ≤ target test.

## Affected Files

- `new/server/routes/dashboard.py`

## Affected Features

The API reports compliance for facilities that emit methane but have no production denominator. This is inconsistent with the OGMP export and the page-level KPI.

## Required Changes

Return `null` and a "Missing Production Data" status when gas = 0 and CH4 > 0.

Implement through the shared fix for RC-7 (Dashboard filters not applied through one base query) rather than a local patch.

## Database Changes

None required.

## Backend Changes

Changes in `new/server/routes/dashboard.py` as described above.

## Frontend Changes

None.

## Calculation Changes

None.

## Tests To Add/Change

- Port `audit/repro/BUG-088.py` into a pytest regression test under `new/server/tests/` (assert the Expected value; independent hand-derived numbers, not a second call to the same function).
- Add edge cases: zero, missing, negative, NaN/Inf, boundary values for every field the fix touches.
- Add the group-level invariant tests for RC-7 (see Root-Cause Groups).
- Review existing tests that assert the old behaviour; change an expected value only when the new value is independently derived and documented in the test.

## Browser Verification

- API/backend fix. After the fix, open the page(s) that consume this data (see Affected Features) and confirm the displayed value matches the API and DB.

## Regression Risks

- Dashboard numbers under filters will change (they were inconsistent before). Watch query performance when all panels derive from one filtered base query.

## Acceptance Criteria

1. `audit/repro/BUG-088.py` exits 0 on the fixed code (it prints expected vs actual).
2. Expected behaviour holds: The loss rate is undefined (null), with a status such as "Missing Production Data" or "N/A". The OGMP Excel export handles this case correctly with "Non-Compliant (Missing Production Data)" in `reports.py` ~933-936, and the MethaneIntensity page KPI shows "Pending Production".
3. Full backend suite (`python -m pytest tests/` in `new/server`) and frontend checks (`npm run lint`, `npm run test`) pass.
4. No other open bug's repro changes from fail→pass or pass→fail unexpectedly (re-run `audit/work/rerun/run_all.sh`).

---


# PHASE P8 — Uncertainty / SBTi defects

_Phase regression risk:_ Uncertainty and SBTi progress figures will change materially; communicate before release.

---

# BUG-008 — Inventory uncertainty shrinks by √N when the same emissions are split into N records (shared EF uncertainty treated as independent)

**Severity:** High · **Category:** Uncertainty · **Phase:** P8 · **Root cause group:** RC-8 · **Found by:** Agent G (Uncertainty Auditor)

**Current status:** **Still present** — `audit/repro/BUG-008.py` re-run on the final code: bug reproduced.

## Problem

Inventory uncertainty shrinks by √N when the same emissions are split into N records (shared EF uncertainty treated as independent)

- **Actual:** - 12 monthly records: ±6.45 % - 1 annual record: ±22.36 % The ratio is exactly √12 = 3.464. (The ±22.36 % is itself 2× too high because of a separate cross-gas max issue.)
- **Expected:** Identical inventory uncertainty for both years. The EF (±5 % @95 %) is a single value shared by all 12 records, so its error is fully correlated; IPCC 2006 Vol.1 Ch.3 Approach 1 applies the EF uncertainty to the category total. Hand calculation for this category: √(5² + 10²) = ±11.18 % (95 %).

## Root Cause

Every record (or group of records) is treated as an independent source. That holds for random activity-data metering error, but not for the emission-factor component, which is common to every record using the same factor. The EF and AD components are never separated. Only a single combined per-record 1σ is stored, so the dashboard cannot correlate them.

## Affected Files

- `new/server/routes/dashboard.py`

## Affected Features

The reported inventory and category uncertainty depends on data-entry granularity rather than on data quality. Monthly entry, which is the normal workflow, understates uncertainty by about √12 ≈ 3.5×. Facilities with many small records look far more certain than they are. For example, snapshot 2022 fuel_gas shows ±21.3 % while every contributor is ±30 %. The figure on the Uncertainty Assessment page, in its CSV export and in the Master Report is therefore not ISO 14064-1 / IPCC-defensible.

## Required Changes

Aggregate emissions per source category / emission factor first. Apply the EF uncertainty to the category total, fully correlated. Combine only the independent activity-data components in quadrature within a category. Then combine categories with IPCC Eq. 3.2. This requires persisting the EF and AD components separately, or recomputing them from tier/factor at query time.

Implement through the shared fix for RC-8 (Uncertainty aggregation model) rather than a local patch.

## Database Changes

None required.

## Backend Changes

Changes in `new/server/routes/dashboard.py` as described above.

## Frontend Changes

None.

## Calculation Changes

None.

## Tests To Add/Change

- Port `audit/repro/BUG-008.py` into a pytest regression test under `new/server/tests/` (assert the Expected value; independent hand-derived numbers, not a second call to the same function).
- Add edge cases: zero, missing, negative, NaN/Inf, boundary values for every field the fix touches.
- Add the group-level invariant tests for RC-8 (see Root-Cause Groups).
- Review existing tests that assert the old behaviour; change an expected value only when the new value is independently derived and documented in the test.

## Browser Verification

- API/backend fix. After the fix, open the page(s) that consume this data (see Affected Features) and confirm the displayed value matches the API and DB.

## Regression Risks

- Reported uncertainty percentages will change materially (some up, some down); QA and Uncertainty pages must switch together.

## Acceptance Criteria

1. `audit/repro/BUG-008.py` exits 0 on the fixed code (it prints expected vs actual).
2. Expected behaviour holds: Identical inventory uncertainty for both years. The EF (±5 % @95 %) is a single value shared by all 12 records, so its error is fully correlated; IPCC 2006 Vol.1 Ch.3 Approach 1 applies the EF uncertainty to the category total. Hand calculation for this category: √(5² + 10²) = ±11.18 % (95 %).
3. Full backend suite (`python -m pytest tests/` in `new/server`) and frontend checks (`npm run lint`, `npm run test`) pass.
4. No other open bug's repro changes from fail→pass or pass→fail unexpectedly (re-run `audit/work/rerun/run_all.sh`).

---

# BUG-018 — Uncertainty dashboard applies max(u_CO2, u_CH4, u_N2O) to each record's total CO2e instead of CO2e-weighting the per-gas uncertainties

**Severity:** High · **Category:** Uncertainty · **Phase:** P8 · **Root cause group:** RC-8 · **Found by:** Agent G (Uncertainty Auditor)

**Current status:** **Still present** — `audit/repro/BUG-018.py` re-run on the final code: bug reproduced.

## Problem

Uncertainty dashboard applies max(u_CO2, u_CH4, u_N2O) to each record's total CO2e instead of CO2e-weighting the per-gas uncertainties

- **Actual:** The dashboard shows **±22.36 %**. This is 2× the expected value: the CH4 value of 0.1118 was applied to 100 % of the CO2e. Each top contributor is also labelled ±22.4 %.
- **Expected:** Weight the per-gas uncertainty by each gas's CO2e contribution. Activity data (±10 % @95 %) is common to all gases. The EFs are CO2 ±5 %, CH4 ±20 % and N2O ±20 % (95 %). Hand calculation: U95 = 2·√((0.05·E)² + Σ(u_EF,g·E_g)²)/E = **±11.18 %**.

## Root Cause

The gases are aggregated without CO2e weighting. The docstring says "use max of those (conservative)". That is not IPCC Approach 1 propagation.

## Affected Files

- `new/server/routes/dashboard.py`

## Affected Features

Category and inventory uncertainty are overstated by 2 to 4× for every combustion and flaring category whose CH4 and N2O uncertainty exceeds its CO2 uncertainty. This is almost all of them. Categories are pushed into the "medium"/"high" level and the tier breakdown is distorted, because tier classification uses the same inflated `u`. The same inflated number appears on the Uncertainty page, in its CSV export and in the PDF report.

## Required Changes

Per record: u_rec = √((u_AD·E)² + Σ_g (u_EF,g · GWP_g · m_g)²) / E. At minimum use Σ_g u_g·E_g,CO2e combined in quadrature, not the max. This requires the per-gas CO2e amounts, which are already stored as co2/ch4/n2o_emissions.

Implement through the shared fix for RC-8 (Uncertainty aggregation model) rather than a local patch.

## Database Changes

None required.

## Backend Changes

Changes in `new/server/routes/dashboard.py` as described above.

## Frontend Changes

None.

## Calculation Changes

None.

## Tests To Add/Change

- Port `audit/repro/BUG-018.py` into a pytest regression test under `new/server/tests/` (assert the Expected value; independent hand-derived numbers, not a second call to the same function).
- Add edge cases: zero, missing, negative, NaN/Inf, boundary values for every field the fix touches.
- Add the group-level invariant tests for RC-8 (see Root-Cause Groups).
- Review existing tests that assert the old behaviour; change an expected value only when the new value is independently derived and documented in the test.

## Browser Verification

- API/backend fix. After the fix, open the page(s) that consume this data (see Affected Features) and confirm the displayed value matches the API and DB.

## Regression Risks

- Reported uncertainty percentages will change materially (some up, some down); QA and Uncertainty pages must switch together.

## Acceptance Criteria

1. `audit/repro/BUG-018.py` exits 0 on the fixed code (it prints expected vs actual).
2. Expected behaviour holds: Weight the per-gas uncertainty by each gas's CO2e contribution. Activity data (±10 % @95 %) is common to all gases. The EFs are CO2 ±5 %, CH4 ±20 % and N2O ±20 % (95 %). Hand calculation: U95 = 2·√((0.05·E)² + Σ(u_EF,g·E_g)²)/E = **±11.18 %**.
3. Full backend suite (`python -m pytest tests/` in `new/server`) and frontend checks (`npm run lint`, `npm run test`) pass.
4. No other open bug's repro changes from fail→pass or pass→fail unexpectedly (re-run `audit/work/rerun/run_all.sh`).

---

# BUG-025 — Meter (activity-data) and GC (composition) uncertainty inputs are accepted but silently ignored by every calculator

**Severity:** Medium · **Category:** Uncertainty · **Phase:** P8 · **Root cause group:** RC-8 · **Found by:** Agent G (Uncertainty Auditor)

**Current status:** **Still present** — `audit/repro/BUG-025.py` re-run on the final code: bug reproduced.

## Problem

Meter (activity-data) and GC (composition) uncertainty inputs are accepted but silently ignored by every calculator

- **Actual:** All three records store **0.0559**, the tier default (AD 10 %, EF 5 %). By contrast, `user_uncertainty` does work (50 % gives 0.2550).
- **Expected:** Hand calculation (1σ = U95/2): - meter 40 %: √(0.025² + 0.20²) = **0.2016** - meter 40 % + GC 30 %: √(0.025² + 0.20² + 0.15²) = **0.2512**

## Root Cause

The dispatcher writes the overrides into the `uncertainties` dict. The calculators pass that dict's per-gas entries to `resolve_ef_uncertainty` but never pass the dict itself to `propagate_uncertainty(..., uncertainties_dict=uncertainties)`. As a result, `_activity_uncertainty` and `_composition_uncertainty` are dead.

## Affected Files

- `new/server/calculations/dispatcher.py`

## Affected Features

The Scope1Form "specific" mode fields (Meter Uncertainty %, GC Uncertainty %), the bulk-import columns `[Unc] meter_uncertainty_pct` / `gc_uncertainty_pct` (template text: "overrides Tier default"), and the ColumnMappingWizard/BulkImportModal mappings are no-ops. A user who records a poor meter (e.g. ±40 %) still gets the Tier default (±2 % for Tier 3, ±10 % for Tier 1). Their persisted and reported uncertainty is understated with no warning.

## Required Changes

Pass `uncertainties_dict=uncertainties` in every `propagate_uncertainty` call, or have the dispatcher apply the overrides centrally after the calculator returns. Add a test asserting that a meter override changes `relative_uncertainty`.

Implement through the shared fix for RC-8 (Uncertainty aggregation model) rather than a local patch.

## Database Changes

None required.

## Backend Changes

None beyond the above.

## Frontend Changes

None.

## Calculation Changes

Changes in `new/server/calculations/dispatcher.py`. **Data policy: new data only** — records already stored are NOT recalculated; the fix applies to new records and to records edited after the fix. Past reports keep their existing values.

## Tests To Add/Change

- Port `audit/repro/BUG-025.py` into a pytest regression test under `new/server/tests/` (assert the Expected value; independent hand-derived numbers, not a second call to the same function).
- Add edge cases: zero, missing, negative, NaN/Inf, boundary values for every field the fix touches.
- Add the group-level invariant tests for RC-8 (see Root-Cause Groups).
- Review existing tests that assert the old behaviour; change an expected value only when the new value is independently derived and documented in the test.

## Browser Verification

- API/backend fix. After the fix, open the page(s) that consume this data (see Affected Features) and confirm the displayed value matches the API and DB.

## Regression Risks

- Reported uncertainty percentages will change materially (some up, some down); QA and Uncertainty pages must switch together.
- Correcting a formula changes every stored value computed by it. Stored records are NOT recomputed automatically — a controlled recalculation job with before/after diff and audit log is required, and reported totals for past periods will move.

## Acceptance Criteria

1. `audit/repro/BUG-025.py` exits 0 on the fixed code (it prints expected vs actual).
2. Expected behaviour holds: Hand calculation (1σ = U95/2): - meter 40 %: √(0.025² + 0.20²) = **0.2016** - meter 40 % + GC 30 %: √(0.025² + 0.20² + 0.15²) = **0.2512**
3. Full backend suite (`python -m pytest tests/` in `new/server`) and frontend checks (`npm run lint`, `npm run test`) pass.
4. No other open bug's repro changes from fail→pass or pass→fail unexpectedly (re-run `audit/work/rerun/run_all.sh`).

---

# BUG-043 — Stored uncertainty has no range or unit validation: Scope 2/3 accept percent values, negatives, NaN and 1e6, and the Uncertainty dashboard shows ±3600 %

**Severity:** Medium · **Category:** Uncertainty · **Phase:** P8 · **Root cause group:** RC-1, RC-8 · **Found by:** Agent G (Uncertainty Auditor)

**Current status:** **Still present** — `audit/repro/BUG-043.py` re-run on the final code: bug reproduced.

## Problem

Stored uncertainty has no range or unit validation: Scope 2/3 accept percent values, negatives, NaN and 1e6, and the Uncertainty dashboard shows ±3600 %

- **Actual:** - 18 → HTTP 201, stored 18.0, dashboard category and inventory **±3600.0 %**, level "high". - -0.5 → HTTP 201, stored -0.5. The dashboard silently substitutes its 0.10 default (±20 %). - "NaN" → HTTP 201. The response body contains the bare token `NaN`, which is not valid JSON. The dashboard substitutes the default. - 1e6 → HTTP 201, dashboard ±200000000 %. Scope 3 accepts -3 the same way (HTTP 201).
- **Expected:** The API rejects with 422 any value that is not a finite fraction in [0, ~2], or explicitly converts a percent value. The dashboard never reports an impossible ±3600 %.

## Root Cause

No validation or unit contract on uncertainty inputs: the fraction/percent ambiguity is never resolved and there are no finiteness or range checks. The consumers handle out-of-range values inconsistently: the dashboard applies no guard, QAQC applies a heuristic /100, and negatives fall back to a default.

## Affected Files

- `new/server/routes/dashboard.py`
- `new/server/routes/scope2.py`
- `new/server/routes/scope3.py`

## Affected Features

A single mis-keyed record, or any percent-valued import, can make the whole-inventory uncertainty meaningless in the Uncertainty page, its CSV and the PDF report. Negative and NaN values are silently replaced. The API also emits invalid JSON.

## Required Changes

Validate that uncertainty is finite and satisfies 0 ≤ u ≤ 2 (fraction, 1σ) on every write path, or accept a clearly named `uncertainty_pct` and convert it. Reject NaN/Inf. Apply one shared normalisation or guard in both dashboard consumers and flag out-of-range stored rows instead of propagating them.

Implement through the shared fix for RC-1 (No central input validation), RC-8 (Uncertainty aggregation model) rather than a local patch.

## Database Changes

None required.

## Backend Changes

Changes in `new/server/routes/dashboard.py`, `new/server/routes/scope2.py`, `new/server/routes/scope3.py` as described above.

## Frontend Changes

None.

## Calculation Changes

None.

## Tests To Add/Change

- Port `audit/repro/BUG-043.py` into a pytest regression test under `new/server/tests/` (assert the Expected value; independent hand-derived numbers, not a second call to the same function).
- Add edge cases: zero, missing, negative, NaN/Inf, boundary values for every field the fix touches.
- Add the group-level invariant tests for RC-1, RC-8 (see Root-Cause Groups).
- Review existing tests that assert the old behaviour; change an expected value only when the new value is independently derived and documented in the test.

## Browser Verification

- API/backend fix. After the fix, open the page(s) that consume this data (see Affected Features) and confirm the displayed value matches the API and DB.

## Regression Risks

- Stricter validation will reject inputs accepted today (existing bulk templates, integrations, scripts). Existing invalid rows remain until a cleanup job runs.
- Reported uncertainty percentages will change materially (some up, some down); QA and Uncertainty pages must switch together.

## Acceptance Criteria

1. `audit/repro/BUG-043.py` exits 0 on the fixed code (it prints expected vs actual).
2. Expected behaviour holds: The API rejects with 422 any value that is not a finite fraction in [0, ~2], or explicitly converts a percent value. The dashboard never reports an impossible ±3600 %.
3. Full backend suite (`python -m pytest tests/` in `new/server`) and frontend checks (`npm run lint`, `npm run test`) pass.
4. No other open bug's repro changes from fail→pass or pass→fail unexpectedly (re-run `audit/work/rerun/run_all.sh`).

---

# BUG-055 — QA Dashboard "IPCC Tier 1 Uncertainty" reports 1σ as ±%, uses only the CO2 column, and includes Draft and Pending records, so it contradicts the Uncertainty page

**Severity:** Medium · **Category:** Uncertainty · **Phase:** P8 · **Root cause group:** RC-8 · **Found by:** Agent G (Uncertainty Auditor)

**Current status:** **Still present** — `audit/repro/BUG-055.py` re-run on the final code: bug reproduced.

## Problem

QA Dashboard "IPCC Tier 1 Uncertainty" reports 1σ as ±%, uses only the CO2 column, and includes Draft and Pending records, so it contradicts the Uncertainty page

- **Actual:** - QA card: **±5.11 %** on **252.547 t**. The value is 1σ (no k=2), and the total includes the Draft record. - Uncertainty page: ±22.36 % on 22.959 t. That figure is itself inflated by BUG-018. On the snapshot, year 2022 shows QA ±2.08 % against the Uncertainty page ±57.18 %, and year 2020 shows 4.09 % against 818.97 %.
- **Expected:** Both pages report the same inventory quantity. For the Verified inventory at 95 % (IPCC Eq. 3.1): √(5² + 10²) = ±11.18 % on 22.959 t.

## Root Cause

The QA dashboard reimplements the aggregation independently. It uses a different subset (all non-rejected records instead of Verified), a different confidence level (1σ instead of 95 %), and a different gas basis (CO2 column only). Its default for missing values is 0.05 for S1/S2 and 0.10 for S3, against the Uncertainty page's 0.10–0.40. The UI labels the result "IPCC Tier 1 Uncertainty ±x%", which reads as a 95 % figure.

## Affected Files

- `new/client/src/pages/QADashboard.jsx`
- `new/server/routes/qaqc.py`

## Affected Features

The two pages give contradictory inventory uncertainty for the same year and facilities, often by more than 10×. The QA figure understates the 95 % uncertainty by about half and covers unapproved data. For CH4-dominated sources (venting, fugitive), where only `uncertainty_ch4` is stored, it falls back to 5 %.

## Required Changes

Reuse `_query_uncertainty`, or a shared service, for the QA card: Verified status, 95 % (k=2), and CO2e-weighted per-gas uncertainty. Label the confidence level in the UI.

Implement through the shared fix for RC-8 (Uncertainty aggregation model) rather than a local patch.

## Database Changes

None required.

## Backend Changes

Changes in `new/server/routes/qaqc.py` as described above.

## Frontend Changes

Changes in `new/client/src/pages/QADashboard.jsx` as described above.

## Calculation Changes

None.

## Tests To Add/Change

- Port `audit/repro/BUG-055.py` into a pytest regression test under `new/server/tests/` (assert the Expected value; independent hand-derived numbers, not a second call to the same function).
- Add edge cases: zero, missing, negative, NaN/Inf, boundary values for every field the fix touches.
- Add the group-level invariant tests for RC-8 (see Root-Cause Groups).
- Review existing tests that assert the old behaviour; change an expected value only when the new value is independently derived and documented in the test.

## Browser Verification

- Reproduce the steps in AUDIT_FINDINGS.md on an isolated stack (`audit/tools/vite_audit.mjs` + backend on an audit DB copy) and confirm the Expected result on screen.
- Compare the UI value with the API response and the DB row for the same record; refresh and reopen the record.

## Regression Risks

- Reported uncertainty percentages will change materially (some up, some down); QA and Uncertainty pages must switch together.

## Acceptance Criteria

1. `audit/repro/BUG-055.py` exits 0 on the fixed code (it prints expected vs actual).
2. Expected behaviour holds: Both pages report the same inventory quantity. For the Verified inventory at 95 % (IPCC Eq. 3.1): √(5² + 10²) = ±11.18 % on 22.959 t.
3. Full backend suite (`python -m pytest tests/` in `new/server`) and frontend checks (`npm run lint`, `npm run test`) pass.
4. No other open bug's repro changes from fail→pass or pass→fail unexpectedly (re-run `audit/work/rerun/run_all.sh`).

---

# BUG-062 — Uncertainty display inconsistencies: EmissionResult shows the ±1σ (68 %) band as the "Confidence Interval", Scope 2/3 tables use k=1.96 while everything else uses k=2, and the Uncertainty page badge thresholds contradict its legend

**Severity:** Low · **Category:** UI · **Phase:** P8 · **Root cause group:** RC-8 · **Found by:** Agent G (Uncertainty Auditor)

**Current status:** **Still present** — `audit/repro/BUG-062.py` re-run on the final code: bug reproduced.

## Problem

Uncertainty display inconsistencies: EmissionResult shows the ±1σ (68 %) band as the "Confidence Interval", Scope 2/3 tables use k=1.96 while everything else uses k=2, and the Uncertainty page badge thresholds contradict its legend

- **Actual:** - The result panel shows a 68 % interval as the CI, about half the width of the 95 % CI the rest of the app reports. - The Scope 2/3 "95 % CI" column uses 1.96, which differs by 2 % relative from the k=2 value shown elsewhere for the same record. - An inventory at ±25 % gets a red "high" badge, while the legend and the backend category level call it "medium".
- **Expected:** Label the interval as 1σ, or show the 95 % CI (k=2): 1.6976 - 2.1250 t. Use one coverage factor everywhere. Use the same level thresholds in the badge, the legend and the backend.

## Root Cause

There is no shared convention for confidence level, coverage factor or level thresholds between components.

## Affected Files

- `new/client/src/components/EmissionResult.jsx`

## Affected Features

Users are shown an uncertainty range that is too narrow on the result panel, and the pages disagree on confidence levels. The effect is cosmetic or misleading rather than a stored-data error.

## Required Changes

Render `value ± 2·u·value` and label it "95 % CI (k=2)". Replace 1.96 with the shared constant. Use the backend-provided `level` or the same thresholds for the inventory badge.

Implement through the shared fix for RC-8 (Uncertainty aggregation model) rather than a local patch.

## Database Changes

None required.

## Backend Changes

None beyond the above.

## Frontend Changes

Changes in `new/client/src/components/EmissionResult.jsx` as described above.

## Calculation Changes

None.

## Tests To Add/Change

- Port `audit/repro/BUG-062.py` into a pytest regression test under `new/server/tests/` (assert the Expected value; independent hand-derived numbers, not a second call to the same function).
- Add edge cases: zero, missing, negative, NaN/Inf, boundary values for every field the fix touches.
- Add the group-level invariant tests for RC-8 (see Root-Cause Groups).
- Review existing tests that assert the old behaviour; change an expected value only when the new value is independently derived and documented in the test.

## Browser Verification

- Reproduce the steps in AUDIT_FINDINGS.md on an isolated stack (`audit/tools/vite_audit.mjs` + backend on an audit DB copy) and confirm the Expected result on screen.
- Compare the UI value with the API response and the DB row for the same record; refresh and reopen the record.

## Regression Risks

- Reported uncertainty percentages will change materially (some up, some down); QA and Uncertainty pages must switch together.

## Acceptance Criteria

1. `audit/repro/BUG-062.py` exits 0 on the fixed code (it prints expected vs actual).
2. Expected behaviour holds: Label the interval as 1σ, or show the 95 % CI (k=2): 1.6976 - 2.1250 t. Use one coverage factor everywhere. Use the same level thresholds in the badge, the legend and the backend.
3. Full backend suite (`python -m pytest tests/` in `new/server`) and frontend checks (`npm run lint`, `npm run test`) pass.
4. No other open bug's repro changes from fail→pass or pass→fail unexpectedly (re-run `audit/work/rerun/run_all.sh`).

---

# BUG-014 — SBTi progress KPI uses the current, incomplete year (and any future year) as the "current" year, so the dashboard reports ~95-99% reduction and ON TRACK

**Severity:** High · **Category:** SBTi · **Phase:** P8 · **Root cause group:** RC-9 · **Found by:** Agent H (SBTi Auditor)

**Current status:** **Still present** — `audit/repro/BUG-014.py` re-run on the final code: bug reproduced.

## Problem

SBTi progress KPI uses the current, incomplete year (and any future year) as the "current" year, so the dashboard reports ~95-99% reduction and ON TRACK

- **Actual:** `latest_actual_year=2026, current_actual=50, current_target=748, reduction_achieved_pct=95.0, on_track=true` → page shows "ON TRACK — Reduction: 95% vs Baseline". On the unmodified snapshot (admin): `latest_actual_year=2026`, `current_actual=10,261.46 t` (2026 data only through Sept; 2025 full year = 1,954,194 t), `reduction_achieved_pct=98.63`, `on_track=true` although the full year 2025 (1.95 Mt) is 2.7× above its 718,500 t target.
- **Expected:** Progress must be measured on the latest complete reporting year (2023): actual 950 t vs linear target 1000×(1−0.042×3) = 874 t → reduction 5.0 %, **BEHIND TARGET**. The current year should at most be shown as year-to-date, never compared to a full-year target.

## Root Cause

"Current" year is simply the max year having any Verified row within [base_year, target_year]. Partial current-year data, or mis-dated future-year data (the snapshot has Verified rows in 2099 and in 2026-10), becomes the progress year and is compared to a full-year target.

## Affected Files

- `new/client/src/pages/SbtiDashboard.jsx`
- `new/server/routes/dashboard.py`

## Affected Features

The headline SBTi status and "% reduction vs baseline" on the SBTi page (and any consumer of `on_track`/`reduction_achieved_pct`) is grossly overstated for most of every calendar year; a company that is off-track is shown as ON TRACK. The CSV export marks the current year "Achieved".

## Required Changes

Select the progress year as the latest year ≤ (current_year − 1) (or the last year flagged as closed/complete, e.g. 12 months of data), ignore years > current year, and label the current year as YTD / exclude it from on-track evaluation.

Implement through the shared fix for RC-9 (SBTi period / scope logic) rather than a local patch.

## Database Changes

None required.

## Backend Changes

Changes in `new/server/routes/dashboard.py` as described above.

## Frontend Changes

Changes in `new/client/src/pages/SbtiDashboard.jsx` as described above.

## Calculation Changes

None.

## Tests To Add/Change

- Port `audit/repro/BUG-014.py` into a pytest regression test under `new/server/tests/` (assert the Expected value; independent hand-derived numbers, not a second call to the same function).
- Add edge cases: zero, missing, negative, NaN/Inf, boundary values for every field the fix touches.
- Add the group-level invariant tests for RC-9 (see Root-Cause Groups).
- Review existing tests that assert the old behaviour; change an expected value only when the new value is independently derived and documented in the test.

## Browser Verification

- Reproduce the steps in AUDIT_FINDINGS.md on an isolated stack (`audit/tools/vite_audit.mjs` + backend on an audit DB copy) and confirm the Expected result on screen.
- Compare the UI value with the API response and the DB row for the same record; refresh and reopen the record.

## Regression Risks

- SBTi progress and on-track status will change; previously shown 'ON TRACK' states may flip.

## Acceptance Criteria

1. `audit/repro/BUG-014.py` exits 0 on the fixed code (it prints expected vs actual).
2. Expected behaviour holds: Progress must be measured on the latest complete reporting year (2023): actual 950 t vs linear target 1000×(1−0.042×3) = 874 t → reduction 5.0 %, **BEHIND TARGET**. The current year should at most be shown as year-to-date, never compared to a full-year target.
3. Full backend suite (`python -m pytest tests/` in `new/server`) and frontend checks (`npm run lint`, `npm run test`) pass.
4. No other open bug's repro changes from fail→pass or pass→fail unexpectedly (re-run `audit/work/rerun/run_all.sh`).

---

# BUG-019 — SBTi "Scope 1+2 (Operational)" view compares Scope 1+2 actuals to the Scope 1+2+3 baseline and target line (inflated reduction %, false ON TRACK)

**Severity:** High · **Category:** SBTi · **Phase:** P8 · **Root cause group:** RC-9 · **Found by:** Agent H (SBTi Auditor) · **Independent confirmations:** 1

**Current status:** **Still present** — `audit/repro/BUG-019.py` re-run on the final code: bug reproduced.

## Problem

SBTi "Scope 1+2 (Operational)" view compares Scope 1+2 actuals to the Scope 1+2+3 baseline and target line (inflated reduction %, false ON TRACK)

- **Actual:** s1_s2: `current_target=874, reduction_achieved_pct=25.0, on_track=true`. s3: `current_target=874, reduction_achieved_pct=80.0, on_track=true`. The chart's "Corporate Target" line and the milestone table "SBTi Target / Variance / Compliance Status" columns likewise compare the S1+S2 actual against the all-scope pathway, so every year looks "Achieved".
- **Expected:** Scope 1+2 view: baseline 800 t, 2023 target 800×(1−0.042×3)=699.2 t, actual 750 t → reduction 6.25 %, BEHIND TARGET. S3 view: baseline 200, target 174.8, actual 200 → 0 %, behind.

## Root Cause

A single all-scope baseline/target is reused for scope-subset actuals; no per-scope baseline (the per-scope base-year totals are available from the same queries at `base_year`).

## Affected Files

- `new/server/routes/dashboard.py`
- `new/server/routes/managedata.py`

## Affected Features

Every organisation with Scope 3 in its baseline sees an overstated operational reduction and a false ON TRACK when toggling to Scope 1+2. SBTi requires separate S1+2 and S3 targets, so this view is the one users would rely on for the S1+2 near-term target.

## Required Changes

Store scope coverage with the target (or per-scope baselines) and, for scope subsets, compute baseline = scope-subset base-year actual (or the stored per-scope baseline) and derive the target line / reduction % / on_track from it.

Implement through the shared fix for RC-9 (SBTi period / scope logic) rather than a local patch.

## Database Changes

Store scope coverage (and optional per-scope baselines) on `sbti_targets`.
 Ship as an Alembic migration (requires BUG-016).

## Backend Changes

Changes in `new/server/routes/dashboard.py`, `new/server/routes/managedata.py` as described above.

## Frontend Changes

None.

## Calculation Changes

None.

## Tests To Add/Change

- Port `audit/repro/BUG-019.py` into a pytest regression test under `new/server/tests/` (assert the Expected value; independent hand-derived numbers, not a second call to the same function).
- Add edge cases: zero, missing, negative, NaN/Inf, boundary values for every field the fix touches.
- Add the group-level invariant tests for RC-9 (see Root-Cause Groups).
- Review existing tests that assert the old behaviour; change an expected value only when the new value is independently derived and documented in the test.

## Browser Verification

- API/backend fix. After the fix, open the page(s) that consume this data (see Affected Features) and confirm the displayed value matches the API and DB.

## Regression Risks

- SBTi progress and on-track status will change; previously shown 'ON TRACK' states may flip.

## Acceptance Criteria

1. `audit/repro/BUG-019.py` exits 0 on the fixed code (it prints expected vs actual).
2. Expected behaviour holds: Scope 1+2 view: baseline 800 t, 2023 target 800×(1−0.042×3)=699.2 t, actual 750 t → reduction 6.25 %, BEHIND TARGET. S3 view: baseline 200, target 174.8, actual 200 → 0 %, behind.
3. Full backend suite (`python -m pytest tests/` in `new/server`) and frontend checks (`npm run lint`, `npm run test`) pass.
4. No other open bug's repro changes from fail→pass or pass→fail unexpectedly (re-run `audit/work/rerun/run_all.sh`).

---

# BUG-028 — SBTi dashboard shows "ON TRACK — Reduction: 100% vs Baseline" when there is no verified data at all in the target window

**Severity:** Medium · **Category:** SBTi · **Phase:** P8 · **Root cause group:** RC-9 · **Found by:** Agent H (SBTi Auditor)

**Current status:** **Still present** — `audit/repro/BUG-028.py` re-run on the final code: bug reproduced.

## Problem

SBTi dashboard shows "ON TRACK — Reduction: 100% vs Baseline" when there is no verified data at all in the target window

- **Actual:** `reduction_achieved_pct=100.0, on_track=true, current_actual=0.0` → green "ON TRACK", "Reduction: 100% vs Baseline". Also reproduced with `?facility_id=4` on a facility without data.
- **Expected:** Progress not evaluable: reduction % null / "No data", status neither ON TRACK nor BEHIND.

## Root Cause

Absence of data is represented as 0 emissions and treated as success instead of "not available".

## Affected Files

- `new/server/routes/dashboard.py`

## Affected Features

A newly configured target (base year = current year before data is verified), or any user whose region has no verified data, sees a false 100 % reduction / ON TRACK headline.

## Required Changes

If no candidate year with data exists (or actual is 0 because no rows exist), return `current_actual=null, reduction_achieved_pct=null, on_track=null`, and render "No data" in the UI.

Implement through the shared fix for RC-9 (SBTi period / scope logic) rather than a local patch.

## Database Changes

None required.

## Backend Changes

Changes in `new/server/routes/dashboard.py` as described above.

## Frontend Changes

None.

## Calculation Changes

None.

## Tests To Add/Change

- Port `audit/repro/BUG-028.py` into a pytest regression test under `new/server/tests/` (assert the Expected value; independent hand-derived numbers, not a second call to the same function).
- Add edge cases: zero, missing, negative, NaN/Inf, boundary values for every field the fix touches.
- Add the group-level invariant tests for RC-9 (see Root-Cause Groups).
- Review existing tests that assert the old behaviour; change an expected value only when the new value is independently derived and documented in the test.

## Browser Verification

- API/backend fix. After the fix, open the page(s) that consume this data (see Affected Features) and confirm the displayed value matches the API and DB.

## Regression Risks

- SBTi progress and on-track status will change; previously shown 'ON TRACK' states may flip.

## Acceptance Criteria

1. `audit/repro/BUG-028.py` exits 0 on the fixed code (it prints expected vs actual).
2. Expected behaviour holds: Progress not evaluable: reduction % null / "No data", status neither ON TRACK nor BEHIND.
3. Full backend suite (`python -m pytest tests/` in `new/server`) and frontend checks (`npm run lint`, `npm run test`) pass.
4. No other open bug's repro changes from fail→pass or pass→fail unexpectedly (re-run `audit/work/rerun/run_all.sh`).

---

# BUG-059 — SBTi target labelled "1.5°C" is not tied to its reduction rate (0.5 %/yr accepted and displayed as 1.5°C); arbitrary pathway strings and future base years accepted; main-dashboard banner hard-codes "SBTi 1.5°C Linear Target"

**Severity:** Medium · **Category:** SBTi · **Phase:** P8 · **Root cause group:** RC-9 · **Found by:** Agent H (SBTi Auditor)

**Current status:** **Still present** — `audit/repro/BUG-059.py` re-run on the final code: bug reproduced.

## Problem

SBTi target labelled "1.5°C" is not tied to its reduction rate (0.5 %/yr accepted and displayed as 1.5°C); arbitrary pathway strings and future base years accepted; main-dashboard banner hard-codes "SBTi 1.5°C Linear Target"

- **Actual:** All accepted; the page and the dashboard banner present a 5 % reduction over 10 years as a "1.5°C" pathway. The main-dashboard banner calls the corporate line "SBTi 1.5°C Linear Target" even for WB2C or custom rates.
- **Expected:** SBTi 1.5°C linear absolute contraction requires ≥ 4.2 %/yr (WB2C ≥ 2.5 %/yr): a 2020→2030 1.5°C target must be ≤ 1000×(1−0.042×10) = 580 t. Pathway must be one of the supported values and consistent with the rate (or the label derived from the rate). Base year should not be in the future (SBTi requires the most recent year with verified data, ≥ 2015).

## Root Cause

No cross-field validation between `pathway_type` and `reduction_rate_pct`; free-text pathway; hard-coded label in DashboardEnhanced.

## Affected Files

- `new/client/src/pages/DashboardEnhanced.jsx`
- `new/client/src/pages/SbtiDashboard.jsx`
- `new/server/routes/managedata.py`

## Affected Features

Misleading claim of 1.5°C alignment on the SBTi page, exports and executive dashboard.

## Required Changes

Whitelist pathway ∈ {1.5C, WB2C, custom}; enforce rate ≥ 4.2 for 1.5C and ≥ 2.5 for WB2C (or label "Custom"); reject base_year > current year; use `sbtiData.pathway_type`/rate in the dashboard banner label.

Implement through the shared fix for RC-9 (SBTi period / scope logic) rather than a local patch.

## Database Changes

None required.

## Backend Changes

Changes in `new/server/routes/managedata.py` as described above.

## Frontend Changes

Changes in `new/client/src/pages/DashboardEnhanced.jsx`, `new/client/src/pages/SbtiDashboard.jsx` as described above.

## Calculation Changes

None.

## Tests To Add/Change

- Port `audit/repro/BUG-059.py` into a pytest regression test under `new/server/tests/` (assert the Expected value; independent hand-derived numbers, not a second call to the same function).
- Add edge cases: zero, missing, negative, NaN/Inf, boundary values for every field the fix touches.
- Add the group-level invariant tests for RC-9 (see Root-Cause Groups).
- Review existing tests that assert the old behaviour; change an expected value only when the new value is independently derived and documented in the test.

## Browser Verification

- Reproduce the steps in AUDIT_FINDINGS.md on an isolated stack (`audit/tools/vite_audit.mjs` + backend on an audit DB copy) and confirm the Expected result on screen.
- Compare the UI value with the API response and the DB row for the same record; refresh and reopen the record.

## Regression Risks

- SBTi progress and on-track status will change; previously shown 'ON TRACK' states may flip.

## Acceptance Criteria

1. `audit/repro/BUG-059.py` exits 0 on the fixed code (it prints expected vs actual).
2. Expected behaviour holds: SBTi 1.5°C linear absolute contraction requires ≥ 4.2 %/yr (WB2C ≥ 2.5 %/yr): a 2020→2030 1.5°C target must be ≤ 1000×(1−0.042×10) = 580 t. Pathway must be one of the supported values and consistent with the rate (or the label derived from the rate). Base year should not be in the future (SBTi requires the most recent year with verified data, ≥ 2015).
3. Full backend suite (`python -m pytest tests/` in `new/server`) and frontend checks (`npm run lint`, `npm run test`) pass.
4. No other open bug's repro changes from fail→pass or pass→fail unexpectedly (re-run `audit/work/rerun/run_all.sh`).

---


# PHASE P9 — UI defects

_Phase regression risk:_ Mostly local UI changes; watch for layout regressions and keyboard focus traps.

---

# BUG-092 — Maker-checker outcome is invisible to the maker: reject/approve send no notification, the Scope 1 list shows Rejected/Pending rows exactly like Verified ones, and the reject dialog claims the record is "permanently deleted" although it is kept as Rejected

**Severity:** Medium · **Category:** UI · **Phase:** P9 · **Root cause group:** RC-2 · **Found by:** Agent L (Browser)

**Current status:** **Confirmed on the post-change code by the browser agent** (`audit/repro/BUG-092.mjs`); not re-run in the final pass (needs a live UI stack).

## Problem

Maker-checker outcome is invisible to the maker: reject/approve send no notification, the Scope 1 list shows Rejected/Pending rows exactly like Verified ones, and the reject dialog claims the record is "permanently deleted" although it is kept as Rejected

- **Actual:** - DB: `emissions.id=753 status='Rejected' approved_by=16` — not deleted; the reason exists only in `activity_log` (id 1354). - `notifications` created after the approve/reject: 0 rows (the submit created 4 "awaiting your approval" notifications for admins). - The user's Recent Activity table shows row 753 ("1,000.00 gal … 10.240") with no status, identical to the Verified rows 752/754. `/api/emissions?scope=1` returned 2 Rejected, 2 Pending, 16 Verified rows in the first page, and none of them is marked.
- **Expected:** The dialog describes what actually happens. The maker is notified of the approval/rejection and the reason. The maker's list distinguishes Verified / Pending / Rejected rows (the API already returns `status`).

## Root Cause

The review workflow notifies only in one direction (maker → checkers). The list UI ignores the `status` field except for Draft, and the modal copy predates the change to soft rejection.

## Affected Files

- `new/client/src/components/Scope1Form.jsx`
- `new/client/src/pages/ManageData.jsx`
- `new/server/routes/emissions.py`

## Affected Features

Makers cannot tell that a figure they entered was excluded from the inventory, or why, so rejected data is not corrected and resubmitted. Users may also double-enter because Pending rows look final. The dialog misstates the data-retention behaviour to the approver.

## Required Changes

Create a Notification for `created_by` on approve/reject including the reason. Add a status badge column (Verified / Pending / Rejected / Draft) to the scope lists. Change the dialog text to "The record will be marked Rejected and excluded from totals".

Implement through the shared fix for RC-2 (Maker-checker / status policy duplicated per route) rather than a local patch.

## Database Changes

None required.

## Backend Changes

Changes in `new/server/routes/emissions.py` as described above.

## Frontend Changes

Changes in `new/client/src/components/Scope1Form.jsx`, `new/client/src/pages/ManageData.jsx` as described above.

## Calculation Changes

None.

## Tests To Add/Change

- Port `audit/repro/BUG-092.mjs` into a Playwright spec under `new/client/e2e/` (or a vitest test where it is pure component logic).
- Add edge cases: zero, missing, negative, NaN/Inf, boundary values for every field the fix touches.
- Add the group-level invariant tests for RC-2 (see Root-Cause Groups).
- Review existing tests that assert the old behaviour; change an expected value only when the new value is independently derived and documented in the test.

## Browser Verification

- Reproduce the steps in AUDIT_FINDINGS.md on an isolated stack (`audit/tools/vite_audit.mjs` + backend on an audit DB copy) and confirm the Expected result on screen.
- Compare the UI value with the API response and the DB row for the same record; refresh and reopen the record.

## Regression Risks

- Status-policy changes alter who can approve and what edits reset records to Pending; re-run the full maker-checker role matrix (user, superuser, admin, it roles) for Scope 1/2/3, CAP and bulk.

## Acceptance Criteria

1. `audit/repro/BUG-092.mjs` exits 0 on the fixed code (it prints expected vs actual).
2. Expected behaviour holds: The dialog describes what actually happens. The maker is notified of the approval/rejection and the reason. The maker's list distinguishes Verified / Pending / Rejected rows (the API already returns `status`).
3. Full backend suite (`python -m pytest tests/` in `new/server`) and frontend checks (`npm run lint`, `npm run test`) pass.
4. No other open bug's repro changes from fail→pass or pass→fail unexpectedly (re-run `audit/work/rerun/run_all.sh`).

---

# BUG-105 — Manage Data and Reference Data swallow API load errors and show them as empty data ("No production record found", empty factor catalog)

**Severity:** Medium · **Category:** UI · **Phase:** P9 · **Root cause group:** — · **Found by:** Agent K (Frontend/UI)

**Current status:** **Confirmed on the post-change code by the browser agent** (`audit/repro/BUG-105.mjs`); not re-run in the final pass (needs a live UI stack).

## Problem

Manage Data and Reference Data swallow API load errors and show them as empty data ("No production record found", empty factor catalog)

- **Actual:** - Manage Data: table shows "No production record found." / "Page 1 of 1"; no toast (toast container empty). - Reference Data: page renders 40 table rows instead of 229 — the whole API emission-factor catalog disappears because the custom-factors call failed; no message.
- **Expected:** An error message/retry ("Failed to load production data") distinct from an empty result; Reference Data should still show the emission-factor catalog that loaded successfully.

## Root Cause

Errors logged to console only; `Promise.all` couples independent loads.

## Affected Files

- `new/client/src/pages/ManageData.jsx`
- `new/client/src/pages/ReferenceData.jsx`

## Affected Features

Users (and approvers) can conclude that production data, factors, goals or surveys do not exist, and may re-enter data (duplicates) or report intensity as "pending production data" during transient backend failures.

## Required Changes

Surface a toast/error panel with retry per section; use `Promise.allSettled` in ReferenceData.

## Database Changes

None required.

## Backend Changes

None beyond the above.

## Frontend Changes

Changes in `new/client/src/pages/ManageData.jsx`, `new/client/src/pages/ReferenceData.jsx` as described above.

## Calculation Changes

None.

## Tests To Add/Change

- Port `audit/repro/BUG-105.mjs` into a Playwright spec under `new/client/e2e/` (or a vitest test where it is pure component logic).
- Add edge cases: zero, missing, negative, NaN/Inf, boundary values for every field the fix touches.
- Review existing tests that assert the old behaviour; change an expected value only when the new value is independently derived and documented in the test.

## Browser Verification

- Reproduce the steps in AUDIT_FINDINGS.md on an isolated stack (`audit/tools/vite_audit.mjs` + backend on an audit DB copy) and confirm the Expected result on screen.
- Compare the UI value with the API response and the DB row for the same record; refresh and reopen the record.

## Regression Risks

- Mostly local UI changes; watch for layout regressions and keyboard focus traps.

## Acceptance Criteria

1. `audit/repro/BUG-105.mjs` exits 0 on the fixed code (it prints expected vs actual).
2. Expected behaviour holds: An error message/retry ("Failed to load production data") distinct from an empty result; Reference Data should still show the emission-factor catalog that loaded successfully.
3. Full backend suite (`python -m pytest tests/` in `new/server`) and frontend checks (`npm run lint`, `npm run test`) pass.
4. No other open bug's repro changes from fail→pass or pass→fail unexpectedly (re-run `audit/work/rerun/run_all.sh`).

---

# BUG-107 — CustomDropdown is not keyboard-operable and form inputs have no programmatic labels: Region, Process Type, Emission Factor and Unit cannot be set without a mouse

**Severity:** Medium · **Category:** UI · **Phase:** P9 · **Root cause group:** — · **Found by:** Agent K (Frontend/UI)

**Current status:** **Confirmed on the post-change code by the browser agent** (`audit/repro/BUG-107.mjs`); not re-run in the final pass (needs a live UI stack).

## Problem

CustomDropdown is not keyboard-operable and form inputs have no programmatic labels: Region, Process Type, Emission Factor and Unit cannot be set without a mouse

- **Actual:** Tab order: Group Name → Equipment ID → Tier 1/2/3 buttons → Quantity → Save as Draft → Submit … — every CustomDropdown is skipped (Region trigger: `tabIndex -1, role null, aria-haspopup null`). Submitting then fails with "Please fill in all identity fields (Year, Month, Region, Process)". Unlabelled form controls (no associated label/aria-label): Scope 1 11/11, Scope 2 6/6, Manage Data 15/15, Reports 12/12, Audit Trail 6/6, Reference Data 2/2.
- **Expected:** Tab order reaches Region, Emission Source, Process Type, factor and Unit pickers; they open with Enter/Space and options are selectable with arrow keys; each input has an accessible name.

## Root Cause

Custom div-based listbox without focus management/ARIA; labels not associated with controls.

## Affected Files

- `new/client/src/components/CustomDropdown.jsx`

## Affected Features

Keyboard and screen-reader users cannot record Scope 1/2 activity data at all (required pickers unreachable); fails WCAG 2.1.1 / 4.1.2 / 1.3.1.

## Required Changes

Make the trigger a `<button aria-haspopup="listbox" aria-expanded>`, options `role="option"` with arrow-key navigation, and associate labels via `htmlFor`/`id` (or `aria-labelledby`).

## Database Changes

None required.

## Backend Changes

None beyond the above.

## Frontend Changes

Changes in `new/client/src/components/CustomDropdown.jsx` as described above.

## Calculation Changes

None.

## Tests To Add/Change

- Port `audit/repro/BUG-107.mjs` into a Playwright spec under `new/client/e2e/` (or a vitest test where it is pure component logic).
- Add edge cases: zero, missing, negative, NaN/Inf, boundary values for every field the fix touches.
- Review existing tests that assert the old behaviour; change an expected value only when the new value is independently derived and documented in the test.

## Browser Verification

- Reproduce the steps in AUDIT_FINDINGS.md on an isolated stack (`audit/tools/vite_audit.mjs` + backend on an audit DB copy) and confirm the Expected result on screen.
- Compare the UI value with the API response and the DB row for the same record; refresh and reopen the record.

## Regression Risks

- Mostly local UI changes; watch for layout regressions and keyboard focus traps.

## Acceptance Criteria

1. `audit/repro/BUG-107.mjs` exits 0 on the fixed code (it prints expected vs actual).
2. Expected behaviour holds: Tab order reaches Region, Emission Source, Process Type, factor and Unit pickers; they open with Enter/Space and options are selectable with arrow keys; each input has an accessible name.
3. Full backend suite (`python -m pytest tests/` in `new/server`) and frontend checks (`npm run lint`, `npm run test`) pass.
4. No other open bug's repro changes from fail→pass or pass→fail unexpectedly (re-run `audit/work/rerun/run_all.sh`).

---

# BUG-021 — Reports search keeps the current page number: "Total Records: 42 | Showing: 0" and no pager to recover

**Severity:** Medium · **Category:** UI · **Phase:** P9 · **Root cause group:** — · **Found by:** Agent K (Frontend/UI)

**Current status:** **Confirmed on the post-change code by the browser agent** (`audit/repro/BUG-021.mjs`); not re-run in the final pass (needs a live UI stack).

## Problem

Reports search keeps the current page number: "Total Records: 42 | Showing: 0" and no pager to recover

- **Actual:** Request `GET /api/emissions?page=2&per_page=50&scope=all&search=Flaring` → `{total: 42, pages: 1, emissions: []}`. The page shows "Total Records: 42 | Showing: 0" and "No emission records found. Adjust your filters…". The pager is not rendered when the list is empty, so there is no way back to page 1 other than clearing the search.
- **Expected:** Request with `page=1&search=Flaring`; table shows the first 42 matches.

## Root Cause

`searchTerm` omitted from the "filter changed → reset page" comparison. (Also: no debounce, one request per keystroke.)

## Affected Files

- `new/client/src/pages/Reports.jsx`

## Affected Features

Users searching from any page other than 1 are told no matching records exist when they do.

## Required Changes

Include `searchTerm` in `prevFiltersRef`/`filterChanged` (and debounce the input); also clamp `page` to `pages` when the response has `page > pages`.

## Database Changes

None required.

## Backend Changes

None beyond the above.

## Frontend Changes

Changes in `new/client/src/pages/Reports.jsx` as described above.

## Calculation Changes

None.

## Tests To Add/Change

- Port `audit/repro/BUG-021.mjs` into a Playwright spec under `new/client/e2e/` (or a vitest test where it is pure component logic).
- Add edge cases: zero, missing, negative, NaN/Inf, boundary values for every field the fix touches.
- Review existing tests that assert the old behaviour; change an expected value only when the new value is independently derived and documented in the test.

## Browser Verification

- Reproduce the steps in AUDIT_FINDINGS.md on an isolated stack (`audit/tools/vite_audit.mjs` + backend on an audit DB copy) and confirm the Expected result on screen.
- Compare the UI value with the API response and the DB row for the same record; refresh and reopen the record.

## Regression Risks

- Mostly local UI changes; watch for layout regressions and keyboard focus traps.

## Acceptance Criteria

1. `audit/repro/BUG-021.mjs` exits 0 on the fixed code (it prints expected vs actual).
2. Expected behaviour holds: Request with `page=1&search=Flaring`; table shows the first 42 matches.
3. Full backend suite (`python -m pytest tests/` in `new/server`) and frontend checks (`npm run lint`, `npm run test`) pass.
4. No other open bug's repro changes from fail→pass or pass→fail unexpectedly (re-run `audit/work/rerun/run_all.sh`).

---

# BUG-095 — Scope 1 "Recent Activity": Export CSV exports only the 10 rows of the current page, and the Year/Process filter options are built from that page only

**Severity:** Medium · **Category:** UI · **Phase:** P9 · **Root cause group:** — · **Found by:** Agent K (Frontend/UI)

**Current status:** **Confirmed on the post-change code by the browser agent** (`audit/repro/BUG-095.mjs`); not re-run in the final pass (needs a live UI stack).

## Problem

Scope 1 "Recent Activity": Export CSV exports only the 10 rows of the current page, and the Year/Process filter options are built from that page only

- **Actual:** - Year options: `All Years, 2026, 2025` only (years present on page 1); 2024 and earlier cannot be selected. - After choosing 2026 the options collapse to `All Years, 2026` (no way to switch to another year without resetting). - Export CSV downloads a file with **10** data rows.
- **Expected:** Year options = all years with Scope 1 data (server `/filters/available`: 2099, 2026, 2025, 2024, 2023, 2022, 2021, 2020, 1800); CSV = all records matching the filter (751 unfiltered).

## Root Cause

Filter option lists and export are derived from the paginated `entries` state instead of server-side facets / a server export (`/api/emissions/export` exists).

## Affected Files

- `new/client/src/components/Scope1Form.jsx`

## Affected Features

Users silently export 10 of 751 records; historic years/processes cannot be filtered from this screen.

## Required Changes

Populate options from `/api/filters/available` (or a facets endpoint) and export through `/api/emissions/export` with the active filters.

## Database Changes

None required.

## Backend Changes

None beyond the above.

## Frontend Changes

Changes in `new/client/src/components/Scope1Form.jsx` as described above.

## Calculation Changes

None.

## Tests To Add/Change

- Port `audit/repro/BUG-095.mjs` into a Playwright spec under `new/client/e2e/` (or a vitest test where it is pure component logic).
- Add edge cases: zero, missing, negative, NaN/Inf, boundary values for every field the fix touches.
- Review existing tests that assert the old behaviour; change an expected value only when the new value is independently derived and documented in the test.

## Browser Verification

- Reproduce the steps in AUDIT_FINDINGS.md on an isolated stack (`audit/tools/vite_audit.mjs` + backend on an audit DB copy) and confirm the Expected result on screen.
- Compare the UI value with the API response and the DB row for the same record; refresh and reopen the record.

## Regression Risks

- Mostly local UI changes; watch for layout regressions and keyboard focus traps.

## Acceptance Criteria

1. `audit/repro/BUG-095.mjs` exits 0 on the fixed code (it prints expected vs actual).
2. Expected behaviour holds: Year options = all years with Scope 1 data (server `/filters/available`: 2099, 2026, 2025, 2024, 2023, 2022, 2021, 2020, 1800); CSV = all records matching the filter (751 unfiltered).
3. Full backend suite (`python -m pytest tests/` in `new/server`) and frontend checks (`npm run lint`, `npm run test`) pass.
4. No other open bug's repro changes from fail→pass or pass→fail unexpectedly (re-run `audit/work/rerun/run_all.sh`).

---

# BUG-115 — Manage Data forms discard the server's validation message and show a generic "Failed to …" toast (negative production, negative factor, facility 500, etc.)

**Severity:** Low · **Category:** UI · **Phase:** P9 · **Root cause group:** — · **Found by:** Agent L (Browser)

**Current status:** **Confirmed on the post-change code by the browser agent** (`audit/repro/BUG-115.mjs`); not re-run in the final pass (needs a live UI stack).

## Problem

Manage Data forms discard the server's validation message and show a generic "Failed to …" toast (negative production, negative factor, facility 500, etc.)

- **Actual:** Generic "Failed to …" with no reason; the user cannot tell whether the value, a permission, a duplicate or a server fault caused it.
- **Expected:** The toast shows the server's reason (as the Scope 1 form does: "Invalid year: must be between 1900 and 2100").

## Root Cause

`catch (err) { toast.error('Failed to …') }` without reading `err.response?.data?.error`.

## Affected Files

- `new/client/src/pages/ManageData.jsx`

## Affected Features

Validation errors look like system failures; users retry or give up instead of correcting data; support cannot distinguish causes.

## Required Changes

Use `err.response?.data?.error || 'Failed to …'` in every catch (a shared helper), as `Scope1Form.jsx` already does.

## Database Changes

None required.

## Backend Changes

None beyond the above.

## Frontend Changes

Changes in `new/client/src/pages/ManageData.jsx` as described above.

## Calculation Changes

None.

## Tests To Add/Change

- Port `audit/repro/BUG-115.mjs` into a Playwright spec under `new/client/e2e/` (or a vitest test where it is pure component logic).
- Add edge cases: zero, missing, negative, NaN/Inf, boundary values for every field the fix touches.
- Review existing tests that assert the old behaviour; change an expected value only when the new value is independently derived and documented in the test.

## Browser Verification

- Reproduce the steps in AUDIT_FINDINGS.md on an isolated stack (`audit/tools/vite_audit.mjs` + backend on an audit DB copy) and confirm the Expected result on screen.
- Compare the UI value with the API response and the DB row for the same record; refresh and reopen the record.

## Regression Risks

- Mostly local UI changes; watch for layout regressions and keyboard focus traps.

## Acceptance Criteria

1. `audit/repro/BUG-115.mjs` exits 0 on the fixed code (it prints expected vs actual).
2. Expected behaviour holds: The toast shows the server's reason (as the Scope 1 form does: "Invalid year: must be between 1900 and 2100").
3. Full backend suite (`python -m pytest tests/` in `new/server`) and frontend checks (`npm run lint`, `npm run test`) pass.
4. No other open bug's repro changes from fail→pass or pass→fail unexpectedly (re-run `audit/work/rerun/run_all.sh`).

---

# BUG-022 — Reports "Group By" selector has no effect (getGroupedData is never called)

**Severity:** Low · **Category:** UI · **Phase:** P9 · **Root cause group:** — · **Found by:** Agent K (Frontend/UI)

**Current status:** **Confirmed on the post-change code by the browser agent** (`audit/repro/BUG-022.mjs`); not re-run in the final pass (needs a live UI stack).

## Problem

Reports "Group By" selector has no effect (getGroupedData is never called)

- **Actual:** DOM rows identical before/after (50 rows, same order). Playwright: `groupBy changes DOM: false`.
- **Expected:** Rows grouped by facility (with group headers) as the control promises.

## Root Cause

Grouping logic not wired to the render.

## Affected Files

- `new/client/src/pages/Reports.jsx`

## Affected Features

Control is a no-op; users may believe they are looking at grouped data.

## Required Changes

Render from `getGroupedData()` with group headers/subtotals, or remove the control.

## Database Changes

None required.

## Backend Changes

None beyond the above.

## Frontend Changes

Changes in `new/client/src/pages/Reports.jsx` as described above.

## Calculation Changes

None.

## Tests To Add/Change

- Port `audit/repro/BUG-022.mjs` into a Playwright spec under `new/client/e2e/` (or a vitest test where it is pure component logic).
- Add edge cases: zero, missing, negative, NaN/Inf, boundary values for every field the fix touches.
- Review existing tests that assert the old behaviour; change an expected value only when the new value is independently derived and documented in the test.

## Browser Verification

- Reproduce the steps in AUDIT_FINDINGS.md on an isolated stack (`audit/tools/vite_audit.mjs` + backend on an audit DB copy) and confirm the Expected result on screen.
- Compare the UI value with the API response and the DB row for the same record; refresh and reopen the record.

## Regression Risks

- Mostly local UI changes; watch for layout regressions and keyboard focus traps.

## Acceptance Criteria

1. `audit/repro/BUG-022.mjs` exits 0 on the fixed code (it prints expected vs actual).
2. Expected behaviour holds: Rows grouped by facility (with group headers) as the control promises.
3. Full backend suite (`python -m pytest tests/` in `new/server`) and frontend checks (`npm run lint`, `npm run test`) pass.
4. No other open bug's repro changes from fail→pass or pass→fail unexpectedly (re-run `audit/work/rerun/run_all.sh`).

---

# BUG-082 — Scope 1 "Live Equation Inspector" states "GWP Standard: IPCC AR6 (CH₄:28, N₂O:265)" — hard-coded, AR5 values mislabelled as AR6, ignores the org GWP setting

**Severity:** Low · **Category:** UI · **Phase:** P9 · **Root cause group:** RC-6 · **Found by:** Agent K (Frontend/UI)

**Current status:** **Confirmed on the post-change code by the browser agent** (`audit/repro/BUG-082.mjs`); not re-run in the final pass (needs a live UI stack).

## Problem

Scope 1 "Live Equation Inspector" states "GWP Standard: IPCC AR6 (CH₄:28, N₂O:265)" — hard-coded, AR5 values mislabelled as AR6, ignores the org GWP setting

- **Actual:** Always "GWP Standard: IPCC AR6 (CO₂:1, CH₄:28, N₂O:265)". Records 754/755 were computed with AR5 (`gwp_version = 'AR5'`, CO2e 1.91303 t = 1.91106 + 3.6017e-5×28 + 3.6017e-6×265).
- **Expected:** Label reflecting the active standard, e.g. "IPCC AR5 (CH₄:28, N₂O:265)"; under AR6 it would be "CH₄:29.8, N₂O:273" (the app's own Settings/Reports list AR6 as 29.8/273).

## Root Cause

Hard-coded label text; not bound to `/auth/settings.gwp_standard` or `constants.js` GWP tables.

## Affected Files

- `new/client/src/components/Scope1Form.jsx`

## Affected Features

Users/verifiers are told the calculation uses AR6 when it uses AR5 (or whatever is configured); misleading audit evidence.

## Required Changes

Render the active standard and its values from settings/`constants.js`.

Implement through the shared fix for RC-6 (Client and server hold separate copies of catalogs, constants and formulas) rather than a local patch.

## Database Changes

None required.

## Backend Changes

None beyond the above.

## Frontend Changes

Changes in `new/client/src/components/Scope1Form.jsx` as described above.

## Calculation Changes

None.

## Tests To Add/Change

- Port `audit/repro/BUG-082.mjs` into a Playwright spec under `new/client/e2e/` (or a vitest test where it is pure component logic).
- Add edge cases: zero, missing, negative, NaN/Inf, boundary values for every field the fix touches.
- Add the group-level invariant tests for RC-6 (see Root-Cause Groups).
- Review existing tests that assert the old behaviour; change an expected value only when the new value is independently derived and documented in the test.

## Browser Verification

- Reproduce the steps in AUDIT_FINDINGS.md on an isolated stack (`audit/tools/vite_audit.mjs` + backend on an audit DB copy) and confirm the Expected result on screen.
- Compare the UI value with the API response and the DB row for the same record; refresh and reopen the record.

## Regression Risks

- Removing a client-side catalog/formula can remove options users rely on; every factor still offered must exist server-side before the switch. Previews will change to server-computed values.

## Acceptance Criteria

1. `audit/repro/BUG-082.mjs` exits 0 on the fixed code (it prints expected vs actual).
2. Expected behaviour holds: Label reflecting the active standard, e.g. "IPCC AR5 (CH₄:28, N₂O:265)"; under AR6 it would be "CH₄:29.8, N₂O:273" (the app's own Settings/Reports list AR6 as 29.8/273).
3. Full backend suite (`python -m pytest tests/` in `new/server`) and frontend checks (`npm run lint`, `npm run test`) pass.
4. No other open bug's repro changes from fail→pass or pass→fail unexpectedly (re-run `audit/work/rerun/run_all.sh`).

---

# BUG-098 — Emission Calculation Result panel rounds gas masses to 3 decimals of a tonne: non-zero CH4/N2O shown as "0.00 tonnes"

**Severity:** Low · **Category:** UI · **Phase:** P9 · **Root cause group:** — · **Found by:** Agent K (Frontend/UI)

**Current status:** **Confirmed on the post-change code by the browser agent** (`audit/repro/BUG-098.mjs`); not re-run in the final pass (needs a live UI stack).

## Problem

Emission Calculation Result panel rounds gas masses to 3 decimals of a tonne: non-zero CH4/N2O shown as "0.00 tonnes"

- **Actual:** "CH₄ METHANE 0.00 tonnes", "N₂O NITROUS OXIDE 0.00 tonnes"; uncertainty tooltip margins are likewise rounded to 0.00.
- **Expected:** A non-zero, readable value (e.g. "0.000036 t" / "36.0 kg"), consistent with the Recent Activity table which shows CH4 with 5 decimals ("0.00004").

## Root Cause

Fixed tonne scale with 3-decimal maximum for all gases.

## Affected Files

- `new/client/src/components/EmissionResult.jsx`

## Affected Features

Methane/N2O from small sources appear to be zero on the confirmation screen (misleading, especially for methane reporting); same record shows different values elsewhere.

## Required Changes

Use significant-figure formatting or switch to kg below 1 t.

## Database Changes

None required.

## Backend Changes

None beyond the above.

## Frontend Changes

Changes in `new/client/src/components/EmissionResult.jsx` as described above.

## Calculation Changes

None.

## Tests To Add/Change

- Port `audit/repro/BUG-098.mjs` into a Playwright spec under `new/client/e2e/` (or a vitest test where it is pure component logic).
- Add edge cases: zero, missing, negative, NaN/Inf, boundary values for every field the fix touches.
- Review existing tests that assert the old behaviour; change an expected value only when the new value is independently derived and documented in the test.

## Browser Verification

- Reproduce the steps in AUDIT_FINDINGS.md on an isolated stack (`audit/tools/vite_audit.mjs` + backend on an audit DB copy) and confirm the Expected result on screen.
- Compare the UI value with the API response and the DB row for the same record; refresh and reopen the record.

## Regression Risks

- Mostly local UI changes; watch for layout regressions and keyboard focus traps.

## Acceptance Criteria

1. `audit/repro/BUG-098.mjs` exits 0 on the fixed code (it prints expected vs actual).
2. Expected behaviour holds: A non-zero, readable value (e.g. "0.000036 t" / "36.0 kg"), consistent with the Recent Activity table which shows CH4 with 5 decimals ("0.00004").
3. Full backend suite (`python -m pytest tests/` in `new/server`) and frontend checks (`npm run lint`, `npm run test`) pass.
4. No other open bug's repro changes from fail→pass or pass→fail unexpectedly (re-run `audit/work/rerun/run_all.sh`).

---

# BUG-108 — Scope 1 entry form does not reflow at phone width (390 px): Field input, Tier selector and factor picker are clipped off-screen

**Severity:** Low · **Category:** UI · **Phase:** P9 · **Root cause group:** — · **Found by:** Agent K (Frontend/UI)

**Current status:** **Confirmed on the post-change code by the browser agent** (`audit/repro/BUG-108.mjs`); not re-run in the final pass (needs a live UI stack).

## Problem

Scope 1 entry form does not reflow at phone width (390 px): Field input, Tier selector and factor picker are clipped off-screen

- **Actual:** Screenshot `audit/work/K/m390__emissions_scope_scope1.png`: "Field" input cut at the right edge, Activity/Division inputs ~45 px wide ("Aut"), "Calculation Methodology" tier buttons and "Select Standard Em…" picker extend past the card edge and are clipped (document scrollWidth stays 390, so the hidden parts cannot be scrolled to).
- **Expected:** Single-column layout; every control fully visible.

## Root Cause

Fixed multi-column grid without a small-screen breakpoint.

## Affected Files

- `new/client/src/components/Scope1Form.jsx`

## Affected Features

Tier 2/3 selection and some fields are unusable on phones.

## Required Changes

Add a `@media (max-width: 600px)` rule collapsing `.form-grid-*`/identity grid to one column and wrapping the tier selector.

## Database Changes

None required.

## Backend Changes

None beyond the above.

## Frontend Changes

Changes in `new/client/src/components/Scope1Form.jsx` as described above.

## Calculation Changes

None.

## Tests To Add/Change

- Port `audit/repro/BUG-108.mjs` into a Playwright spec under `new/client/e2e/` (or a vitest test where it is pure component logic).
- Add edge cases: zero, missing, negative, NaN/Inf, boundary values for every field the fix touches.
- Review existing tests that assert the old behaviour; change an expected value only when the new value is independently derived and documented in the test.

## Browser Verification

- Reproduce the steps in AUDIT_FINDINGS.md on an isolated stack (`audit/tools/vite_audit.mjs` + backend on an audit DB copy) and confirm the Expected result on screen.
- Compare the UI value with the API response and the DB row for the same record; refresh and reopen the record.

## Regression Risks

- Mostly local UI changes; watch for layout regressions and keyboard focus traps.

## Acceptance Criteria

1. `audit/repro/BUG-108.mjs` exits 0 on the fixed code (it prints expected vs actual).
2. Expected behaviour holds: Single-column layout; every control fully visible.
3. Full backend suite (`python -m pytest tests/` in `new/server`) and frontend checks (`npm run lint`, `npm run test`) pass.
4. No other open bug's repro changes from fail→pass or pass→fail unexpectedly (re-run `audit/work/rerun/run_all.sh`).

---


# Excluded entries

**BUG-035** — duplicate of BUG-033 (merged above).

**BUG-100 to BUG-104** were appended to `AUDIT_FINDINGS.md` by a process outside this audit (signed "API GHG Compendium Section 6 Auditor"), during the period when the user had placed emission calculations out of scope. They have no reproduction scripts and were not verified by any audit workstream, and BUG-104 describes missing functionality rather than a defect. They are listed here for traceability and should be triaged by the user (accept into a calculation-methodology backlog, or verify first):

- **BUG-100** (High) — Pneumatic controllers calculator cites obsolete 2009 Section 6.10, conflates hourly bleed with actuation volume, and lacks API 2021 Tables 6-14/6-15 and Eq 6-14 malfunction model
- **BUG-101** (Medium) — Vessel and pipeline blowdown calculation depressurization formula includes residual atmospheric volume, overestimating vented volume by 1.0 physical vessel volume per event
- **BUG-102** (High) — Storage tank flashing emissions evaluate to zero when GOR is omitted, lacking API 2021 Table 6-22/6-24 default factors and engineering correlations (VBE, Standing, EUB)
- **BUG-103** (Medium) — Completion flowback and mud degassing calculators omit offshore exploration and completion emission factors
- **BUG-104** (Critical) — Complete absence of API Compendium 2021 Section 6 venting calculators across upstream, midstream, downstream, and CCUS segments
