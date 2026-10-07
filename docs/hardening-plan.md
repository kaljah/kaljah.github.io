# Hardening and cleanup plan

Derived from a read-only review of the codebase (see the System Map artifact). Each phase is independently shippable. Run the backend gate groups and the frontend gates (`CLAUDE.md`, "Commands") after every task; do not start the next task on a red build.

## Ground rules
- One task per commit. Never mix cleanup with behaviour changes.
- Phases 0 and 1 change what is committed or deployed: get an explicit go-ahead before each destructive step (history rewrite, force push, file deletion).
- A task is done when its **Verify** line passes and `CLAUDE.md` is updated if it changed a documented fact.

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
Goal: one calculation path, with the legacy fallback either proven unused or ported.

| # | Task | Verify |
|---|------|--------|
| 4.1 | In `calculations/legacy_engine.py`, log a warning (process type, factor source, `calc_method`) whenever a fallback branch (`server_default`, `server_specific`, `server_custom_factor`) is used. | Warning appears in a test that exercises each branch |
| 4.2 | Query production-like data: count records by `calc_method`. Write the numbers into this file. | Table filled in |
| 4.3 | For each fallback still in use: add a dispatcher calculator that reproduces its numbers, with a golden-dataset test that compares old and new outputs on the same inputs (tolerance 1e-9 relative). | New tests pass; `test_independent_differential` and `test_golden_dataset_validation` still green |
| 4.4 | Route the case to the dispatcher, keep the fallback behind the warning for one release, then delete it once the warning has not fired. | Fallback code removed; full suite green |

Do not do 4.4 without the 4.2 numbers. Existing records keep their stored `calc_method`; nothing is recomputed.

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
3. Phase 4 (medium; needs data from 4.2).
4. Phases 5 and 6 (long-running; interleave, one task per PR).
5. 1.5 only if you want a smaller repository and approve the history rewrite.

## Decisions needed from you
1. Which root file groups in 1.3 to archive versus delete.
2. Whether to rewrite history (1.5).
3. The production `ALLOWED_ORIGINS` value, and whether you run more than one worker (decides how strict 2.4 is).
4. Whether production data exists to run 4.2 against, or whether a representative test dataset should be used.
