# Hardening and cleanup plan

Derived from a read-only review of the codebase (see the System Map artifact). Each phase is independently shippable. Run the backend gate groups and the frontend gates (`CLAUDE.md`, "Commands") after every task; do not start the next task on a red build.

## Ground rules
- One task per commit. Never mix cleanup with behaviour changes.
- Phases 0 and 1 change what is committed or deployed: get an explicit go-ahead before each destructive step (history rewrite, force push, file deletion).
- A task is done when its **Verify** line passes and `CLAUDE.md` is updated if it changed a documented fact.

## Status (updated 2026-10-07)
| Phase | State | Notes |
|-------|-------|-------|
| 0 Safety net | Done | Baseline: backend 2,528 passed / 1 skipped; frontend lint, typecheck, lint:css, vitest (103) green after fixing 5 lint errors and re-baselining the UI ratchet. `.git` backed up outside the repo. |
| 1 Repo hygiene | 1.1-1.4 and 1.6 done; 1.5 prepared, **push pending** | Loose root files and Antigravity state deleted/untracked; CI rejects tracked machine-local files. The history rewrite was run on a scratch mirror (581 MB to 85 MB, tip-of-`main` tree identical) but **nothing is pushed**: the force-push was blocked and needs you to run it. GitHub `main` also holds 56 later "Antigravity Sync" commits (state files only) that the rewrite drops. Databases were never tracked (`*.db` is ignored). |
| 2 Production config | Done | Fail-closed environment detection, CORS checks, shared rate-limit store required in production. 14 tests. Needs `REDIS_URL` set in production before deploy. |
| 3 Cache and docs | Done | Found and fixed a real bug: `batch-all` never checked the shared invalidation epoch, so with several workers a cache hit could serve stale data for up to 5 minutes. Counters added. `schema_sync.py` docstring fixed. |
| 4 Calculation fallback | Measured; retirement dropped | See Phase 4 below. |
| 5 Module splits | 5.1-5.5 done | `routes/emissions.py` 4,178 to 1,138 lines (10 modules), `reports.py` 1,541 to 608, `dashboard.py` 1,779 to 1,188, `calculations/vented.py` 2,571 to 186, `vented_production.py` 1,935 to 187, `dispatcher.py` 2,395 to 1,090 (the 17 branches of `_dispatch_impl` moved into three `dispatcher_branches_*` modules as functions taking the dispatcher). Route table identical (189 rules) after every route split; CSV template output byte-identical; 1,132 calculation tests and the full suite (2,549) pass after every split. `auth.py` 1,264 to 741 (settings and user-management routes in `auth_settings.py` and `auth_users.py`; moved names stay importable from `routes.auth` through a lazy module `__getattr__`, so import order never matters). Left: single large classes (`vented_unloading.py` 1,061, `CalculationDispatcher` itself), which the size ratchet records as maxima. |
| 6 Frontend finish | 6.1, 6.2 done; 6.3 ongoing | Also fixed `ui-metrics` so it scans `.ts/.tsx` (five metrics were reading 0 because they scanned nothing). True debt now visible and ratcheted: 120 inline style objects, 281 hex colors in JS, 3 inline SVGs, 2 native selects, 122 hex colors and 18 `!important` in CSS. The CSS conversion itself (6.3) is a long-running migration per `docs/ui-modernization-plan.md`, not finished here. |
| 7 CI on GitHub | Done | After the push the backend job failed: a committed test imported `psutil`, which was not in `requirements.txt` (found by running CI's commands in a `python:3.11` container; fixed). Frontend job verified in `node:20` (lint, check:ts, lint:css, ui:metrics, tests, build). The e2e workflow had never passed and cannot on a clean machine (needs seeded accounts and `storageState.json`), so it is manual-only until CI seeds them. |

## Phase 0 - Safety net (before touching anything)
| # | Task | Verify |
|---|------|--------|
| 0.1 | Record a baseline: full backend run (`python -m pytest -x --timeout=300` in `new/server`), `npm run lint`, `typecheck`, `lint:css`, `ui:metrics -- --check`, `test`. Save the pass/fail counts in the PR description. | Counts written down; all green or known failures listed |
| 0.2 | Make a full backup of the repo folder and `.git` (the history is about 565 MiB). | Backup opens and `git fsck` passes on it |
| 0.3 | Commit or stash the current uncommitted state in separate commits: (a) the working-tree deletions of root files, (b) the code changes under `new/`, (c) `CLAUDE.md` and `.claude/commands`. | `git status` clean; three reviewable commits |

## Phase 1 - Repository hygiene
Goal: stop tracking generated and unrelated files. Databases are already ignored (`*.db`), so no credential purge is needed for them.

| # | Task | Verify |
|---|------|--------|
| 1.1 | Add to `.gitignore`: `brain/`, `annotations/`, `conversations/`, `agyhub_summaries_proto.pb`, `antigravity_state.pbtxt`, `.antigravity/`, `*.rar`, `*.log`, `new/server/audit_*_bugs*.json`, `new/server/upload_jobs/`, `new/server/backups/`. | `git status --ignored` shows them ignored |
| 1.2 | `git rm -r --cached` those paths (about 15,700 files under `brain/` alone) plus `new/server.rar` and `new/server/calculations/calculations.rar`. Files stay on disk. | `git ls-files` has none of them |
| 1.3 | Decide per group what to do with the loose root files (patches `cbam_*.patch`, `patch*.py`, `fix_ui*.py`, flyers and PNG previews, `*_v2.csv`, `old_ManageData.jsx`, `temp_old/`, `deck_assets/`, `site_assets/`): move to a git-ignored `archive/` folder, or delete. List them first and get a yes/no per group. | Root contains only app, docs and config |
| 1.4 | Fix `CLAUDE.md`: remove the "archived into `archive/`" sentence or make it true. | Matches the tree |
| 1.5 | **Optional, needs your approval:** shrink history with `git filter-repo` (remove `brain/`, `annotations/`, `conversations/`, the `.rar` files). Only if the repo is private and every clone can be redone. | `git count-objects -vH` pack size drops; fresh clone builds |
| 1.6 | Add a CI step that fails if a tracked path matches the ignore patterns above. | Step fails on a test commit that adds a `.rar` |

Rollback: 1.1-1.4 are plain commits and revert cleanly. 1.5 is not reversible; keep the 0.2 backup.

## Phase 2 - Production configuration safety
All in `new/server/config.py` unless noted. Add a test for each in `tests/test_security_hardening.py` (or a new `test_config_safety.py`).

| # | Task | Verify |
|---|------|--------|
| 2.1 | **Environment detection.** Treat any `FLASK_ENV`/`APP_ENV`/`ENVIRONMENT` value that is not `development`, `dev`, `testing` or `test` as production. Today an unknown name such as `live` gets the dev secret. | Test: `FLASK_ENV=live` without `SECRET_KEY` raises at import |
| 2.2 | **Dev secret.** Outside production keep the fallback, but log a warning once. Stop shipping the real-looking value in `.env.example`; use `SECRET_KEY=` with a comment. | `.env.example` has no usable secret; warning appears in dev log |
| 2.3 | **CORS.** Remove the unconditional append of `https://kaljah.github.io`. Add it to the production environment's `ALLOWED_ORIGINS` instead. In production, fail at start if the list is empty or contains `*`. | Test: origin not in the env list is rejected; `*` in production raises |
| 2.4 | **Rate-limit storage.** If production and the storage URI is `memory://`, log an error at start (hard fail behind `REQUIRE_SHARED_LIMITER=true`). Document `REDIS_URL` in `.env.example`. | Test covers both settings; with Redis, two workers share one counter |
| 2.5 | Update `CLAUDE.md` Config bullets and the System Map. | Matches code |

Rollout note: set the new `ALLOWED_ORIGINS` value in the deployment **before** deploying 2.3, or the GitHub Pages frontend loses API access.

## Phase 3 - Small correctness and documentation fixes
| # | Task | Verify |
|---|------|--------|
| 3.1 | Fix the stale docstring in `new/server/schema_sync.py` (schema is Alembic-managed, not `create_all()` at import). | Reads true |
| 3.2 | Dashboard cache: add a counter for hits and misses (log at info every 1000 requests). Do not change invalidation yet. | Numbers visible in the log |
| 3.3 | Decide from 3.2 data whether to scope invalidation by facility and year. Only implement if the hit rate is poor. | Decision recorded in this file |

## Phase 4 - Calculation path consolidation
Original goal: retire the legacy fallback. **Outcome: the measurement showed it should stay.**

| # | Task | Result |
|---|------|--------|
| 4.1 | Report each fallback use with branch, process and factor source. | Done (`_note_fallback`, logged at DEBUG; `tests/test_legacy_fallback_logging.py`). |
| 4.2 | Count fallback uses on the API Compendium exhibit data and the whole suite. | Done, below. |
| 4.3 | Port fallback cases into the dispatcher. | Dropped: the remaining cases are the intended behaviour of the legacy path. |
| 4.4 | Delete the fallback. | Dropped. |

**Measurement.** The 214 tests in `test_api_compendium_exhibits.py`, `test_api2021_chapter7_onshore.py` and `test_all_process_types_matrix.py` use the fallback **0** times: the exhibit calculators are served entirely by the dispatcher. Across the whole suite (2,546 tests, which also exercise every route and bulk import) it ran **11** times:

| Branch | Process | Uses | What triggers it |
|--------|---------|------|------------------|
| `server_default` | combustion | 6 | zero quantity, zero factor (rejected, not booked as zero), hostile CSV fuzz, unknown factor |
| `server_specific` | combustion | 2 | entered Tier 3 factors (`factor_source=specific`) |
| `server_custom_factor` | combustion | 1 | microscopic quantities |
| `server_default` | separation | 1 | catalog factor for a process the dispatcher does not model |
| `server_default` | fugitive | 1 | unrecognised fugitive request (rejected) |

Entered Tier 3 factors are applied by the legacy path by design (see the comment above `_tier3_zero` in `legacy_engine.py`). Existing records keep their stored `calc_method`; nothing is recomputed.

**Caveat.** This is test data, not production data: real usage may exercise the fallback more (for example entered factors on many records). If you want that number, count rows by `calc_method` in the production database: `SELECT calc_method, COUNT(*) FROM emissions GROUP BY calc_method;`.

## Phase 5 - Break up the large modules
Behaviour-preserving moves only. Keep every public import path working by re-exporting from the old module until the last task.

| # | Task | Verify |
|---|------|--------|
| 5.1 | Add a line-count ratchet script (like `ui:metrics`) with a baseline file; CI fails if a Python file in `new/server/routes` or `calculations` grows past its baseline. | Script runs in CI |
| 5.2 | `routes/emissions.py` (4,178 lines): move the per-process validation blocks (e.g. associated-gas checks in `add_emission`) into `services/scope1_calc.py`. | Same HTTP responses; emissions tests green |
| 5.3 | Split by seam into `emissions_crud.py`, `emissions_import.py`, `emissions_export.py`, `emissions_review.py` under one blueprint; `emissions.py` re-exports. | `app.url_map` route list identical before and after (diff it) |
| 5.4 | Repeat 5.2-5.3 for `dashboard.py` (1,743), `reports.py` (1,541), `auth.py` (1,264). | Same route-list diff; suites green |
| 5.5 | `calculations/dispatcher.py` (2,395): move calculator classes into the existing `vented_*`, `combustion*`, `fugitive*` modules; leave the registry and `dispatch` in place. | Differential and golden tests unchanged |
| 5.6 | Lower the ratchet baselines after each split. | Baselines decrease |

## Phase 6 - Frontend migration finish
| # | Task | Verify |
|---|------|--------|
| 6.1 | Convert the 5 remaining test files to TypeScript: `filterStore.test`, `auditFixes.test`, `importMapping.test`, `mathParityAndFormatters.test`, `scope3Factors.test`. | `npm run test`, `typecheck` green |
| 6.2 | Add a lint rule or CI check that fails on new `.js`/`.jsx` under `src/`. | Fails on a test file |
| 6.3 | Continue the CSS conversion per `docs/ui-modernization-plan.md`, ratcheted by `npm run ui:metrics -- --check`; use `scripts/probe/` for visual parity. | Ratchet baseline drops; probes match |
| 6.4 | Update `CLAUDE.md` once no legacy files remain. | Matches tree |

## Order and effort
1. Phase 0, then 1.1-1.4 and 1.6 (small, safe).
2. Phase 2 and 3 (small, high value).
3. Phase 4 (done; fallback kept).
4. Phases 5 and 6 (long-running; interleave, one task per PR).
5. 1.5 only if you want a smaller repository and approve the history rewrite.

## Decisions needed from you
1. Which root file groups in 1.3 to archive versus delete.
2. Whether to rewrite history (1.5).
3. The production `ALLOWED_ORIGINS` value, and whether you run more than one worker (decides how strict 2.4 is).
4. Whether production data exists to run 4.2 against, or whether a representative test dataset should be used.
