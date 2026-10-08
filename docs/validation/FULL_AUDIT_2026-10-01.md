# Full platform audit — 2026-10-01

Scope: UI (React client), backend (Flask API), database (models / Alembic / SQLite + Postgres paths),
API authorisation and input handling, the bulk-upload pipeline, and the CI/CD / container pipelines.
The calculation engine was not re-derived. It had nine audit passes between 09-28 and 10-01 (see
AUDIT_MEMORY.md §7). This pass covered the layers around it.

## Method

1. Baseline:
   - backend suite: 1,965 passed / 0 failed;
   - `validation/`: 128 passed;
   - vitest: 38 passed;
   - lint: 0 errors, 38 warnings;
   - production build: OK;
   - `npm audit`: 10 vulnerable runtime packages (1 critical);
   - `pip-audit`: Flask 3.0.3 and python-dotenv 1.0.1 vulnerable.
2. Code review of `app.py`, `config.py`, `extensions.py`, `utils.py`, `models.py`, every blueprint
   (auth decorators, object-level scope checks, audit logging per mutating route), the upload
   pipeline, the dashboard cache, the SSE stream, the client API layer, route guards and Settings,
   the Dockerfile / docker-compose and `.github/workflows/deploy-pages.yml`.
3. Each suspected bug was reproduced over HTTP with the Flask test client on a scratch database
   before it was fixed. Each fix has a regression test in `new/server/tests/test_full_audit_2026_10_01.py`
   (20 tests; 14 fail on the pre-fix code, 6 pin the still-allowed cases).

## Fixed in this pass

| ID | Sev | Area | Finding (reproduced) | Fix |
|----|-----|------|----------------------|-----|
| A-01 | Critical | API / auth | `POST /api/auth/users/<id>/reset-password` was open to the `it` role with no check on the target. An IT user could reset an **admin's** (or IT admin's) password, then log in as that admin. | Only a strictly higher role may reset a password. Own password goes through `/change-password`. |
| A-02 | High | API / auth | Separation of duties bypass: an `it_admin` was refused when promoting an account to `superuser` (`PUT /users/<id>`), but could create a new `superuser` through `POST /users`. | `register` applies the same rule as `update_user` (only `admin` / `it_manager` grant business roles; no role above the creator's own). |
| A-03 | High | API / DB | When an admin saved Settings, the whole payload was copied into `users.preferences`. That stored the **Copernicus password / client secret in plain text** (C4 regression) and pinned that admin's `gwp_standard`. After another admin changed the global standard, `GET /settings` (and `useGwpStandard` across the app) still showed the old one, and saving again would revert it org-wide and recalculate every record. | Organisation-wide keys (`GLOBAL_SETTING_KEYS`) are never stored in or merged from preferences. Legacy copies are dropped on the user's next save and ignored on read. |
| A-04 | High | DB / scope | `get_allowed_facility_ids` used `user.location` as an `ILIKE` pattern. `West_Field` also matched `WestXField`, and a location of `%` matched every facility (another region's data). | Wildcards escaped, so it is case-insensitive equality, the same as `facility_in_user_scope`. |
| A-05 | Medium | API / audit | A region-restricted superuser could not **save** an org-wide goal but could **delete** one, and could move the org-wide base year. Goal deletion and base-year changes were not audited. | Delete goal and create/delete base year now require org-wide scope, and each writes an ActivityLog entry in the same commit. |
| A-06 | Low | Auth | Login skipped password hashing for an unknown e-mail, so response time revealed which accounts exist (forgot-password already equalised this). | Dummy hash check on unknown e-mail. |
| A-07 | Medium | Cache | The `batch-all` dashboard key had no shared invalidation epoch. On Postgres with several workers, another worker's commit did not invalidate it, so approved data stayed stale for up to 5 minutes. | Epoch added to the key. |
| A-08 | Low | Config | Swagger UI was gated on `FLASK_ENV` only. Production detected via `APP_ENV` / `ENVIRONMENT` / `staging` exposed `/api/docs`. | Uses `app.config["IS_PRODUCTION"]`. |
| A-09 | Medium | Pipeline | No cap on parallel bulk uploads: each job is a thread holding up to 50,000 parsed rows. One account could exhaust worker memory. | `MAX_CONCURRENT_UPLOADS_PER_USER` (default 3), 429 beyond it. |
| A-10 | High | Supply chain | `npm audit`: jspdf (critical), axios, react-router, lodash, form-data (high), dompurify, fflate, follow-redirects. | `npm audit fix` (semver-compatible only): 0 vulnerabilities; lint / tests / build unchanged. |
| A-11 | Medium | Supply chain | Flask 3.0.3 (PYSEC-2026-2151), python-dotenv 1.0.1 (PYSEC-2026-2270). | Flask 3.1.3, python-dotenv 1.2.2; full suite green. |
| A-12 | High | CI/CD | Single workflow-wide concurrency group `pages` with `cancel-in-progress: true`: any PR push cancelled a running **main** deploy. | Per-ref group (cancel only on PRs). Deploy job has its own non-cancelling `pages` group. |
| A-13 | Medium | CI/CD | `pages: write` / `id-token: write` granted to every job (incl. PR test jobs). | Workflow `contents: read`; write scopes only on `deploy`. |
| A-14 | Medium | CI/CD | `pip-audit ... \|\| true` could never fail; there was no npm audit; `validation/` never ran in CI. | pip-audit fails the build; `npm audit --omit=dev --audit-level=high` added; `validation/` step added. |
| A-15 | Low | UI | Settings treated `it_admin` as able to edit operational settings the server refuses (unreachable today behind `NonITRoute`). | Same rule as the API. |

Results after the fixes:
- backend: 1,985 passed / 0 failed (Flask 3.1.3);
- `validation/`: 128 passed;
- vitest: 38 passed;
- lint: 0 errors;
- build: OK;
- `npm audit`: 0 vulnerabilities;
- `pip-audit`: 0 vulnerabilities.

## Open — need an owner decision or work beyond this pass

| ID | Sev | Area | Finding | Recommendation |
|----|-----|------|---------|----------------|
| O-01 | High | Container | The root `Dockerfile` has **two final stages**. Docker builds the last one (the Render stage), so the multi-stage stage (frontend build, `FLASK_ENV=production`) is dead. The shipped image does not set production mode itself. If the hosting environment does not set `FLASK_ENV=production`, the dev `SECRET_KEY` fallback is accepted (forgeable sessions), cookies are not `Secure`, `/api/docs` is public and migrations run automatically. Nobody serves `static/dist`; the SPA ships via GitHub Pages. | Keep one runtime stage with `FLASK_ENV=production` and the Render `PORT` binding. Confirm `SECRET_KEY` / `DATABASE_URL` are set on Render first, or the container will refuse to start (by design). Not changed here because it alters the live deploy. |
| O-02 | High | Scalability | `/api/notifications/stream` (SSE) keeps one gunicorn worker thread per open browser tab, in 45 s cycles. The Render image runs `--workers 2 --threads 4` = 8 slots, so about 8 open tabs starve every other API request. | Poll `/api/notifications` every 30–60 s instead of SSE, or run an async worker (gevent) for the stream. |
| O-03 | Medium | Multi-worker | Under SQLite, `_get_global_cache_epoch` returns the local epoch, so dashboards in the other worker stay stale for up to 5 minutes. The rate limiter (`memory://`) and in-memory upload job dict are also per worker. | Run Postgres (as docker-compose does), or a single worker with SQLite; `RATELIMIT_STORAGE_URI=redis://…` for multi-worker. |
| O-04 | Medium | Data integrity | A custom factor's values can be edited while emission records reference it. Records keep the old values, with no version and no recalculation, and the audit entry names the factor without the old/new values. Its audit commit is separate from the data commit. | Refuse value edits on a referenced factor (create a new version / archive the old one, as delete already does), or recalculate the referencing records through maker-checker. Log old → new values in the same commit. |
| O-05 | Medium | Authorisation policy | Region-restricted superusers may change org-wide settings: GWP standard (recalculates every record), Copernicus credentials, OGMP thresholds, and org-wide custom factors. Goals / base year now require org-wide scope (A-05). | Decide whether the same org-wide rule applies to these settings and factors. |
| O-06 | Medium | Container | `docker-compose.yml` hard-codes `SECRET_KEY` and Postgres `test/test`, and publishes 5432 on all interfaces. | `env_file` / secrets; drop the 5432 port mapping or bind it to 127.0.0.1. |
| O-07 | Medium | Repo hygiene | Tracked in the repo: 374 MB of assistant conversation logs (`conversations/*.pb`), `brain/` (210 MB), `agyhub_summaries_proto.pb`, `new/server.rar`, `calculations/calculations.rar`, PDFs and patch scripts. If the repository is public, these logs may expose internal data. No credentials were found in `mcp_config*.json` or `.env.production`. | Remove from the tree (and history if sensitive), and add them to `.gitignore`. |
| O-08 | Low | Audit trail | `POST /api/emissions/bulk-delete` logs only a count, not the deleted record ids. | Include the ids / record_ids in the details or metadata. |
| O-09 | Low | Input validation | `PUT /profile`, `PUT /users/<id>` (any `status` string, no length limits, empty body → 500), and `PUT /settings` numeric casts (`int()` / `float()` on bad input → 500) return 500 instead of 400. | Use `input_validation.parse_number` and explicit enums. |
| O-10 | Low | Pipeline | Upload job snapshots default to a shared, predictable `/tmp/ghg_upload_jobs`. `error_csv_path` is read back from the JSON and passed to `send_file`. | Set `UPLOAD_JOB_DIR` to a private directory, and check that the path stays inside the job dir before sending it. |
| O-11 | Info | Code health | 38 `react-hooks/exhaustive-deps` warnings; legacy `Query.get()` calls; Flask-SQLAlchemy `get_engine` deprecation in `migrations/env.py`; CI has no Postgres job (production DB engine untested). | Clean up when touching the files; add a Postgres service job to CI. |

## Verified OK (spot checks)

- Maker-checker: atomic conditional update; maker / last modifier cannot approve; scope enforced.
- Every route with an `<id>` loads the record and checks scope. Custom factors / goals are org-wide
  by design (see O-05).
- No string-built SQL from user input; dynamic SQL in `delete_user` uses schema names only.
- CSV / Excel exports neutralise formula prefixes. The CSRF double-submit flow works, and the API
  retries once when the token has expired.
- No `dangerouslySetInnerHTML` or `eval`.
- Unauthenticated routes are limited to login / forgot-password / logout / me / CSV & Excel
  templates / health / csrf-token.
- Session revocation (`session_version`) on logout, password change, reset and deactivation.

## Owner decisions applied (2026-10-01, second commit)

| Item | Decision | Change |
|------|----------|--------|
| O-01, O-06 | Remove Docker | `Dockerfile`, `docker-compose.yml` and `.dockerignore` deleted. Render (or any host) runs the API as a Python service: build `pip install -r new/server/requirements.txt`, start `flask db upgrade && gunicorn app:app` in `new/server`, with `FLASK_ENV=production`, `SECRET_KEY` and `DATABASE_URL` set. |
| O-02 | Switch notifications | The client polls `GET /api/notifications` every 30 s and when the tab becomes visible; new unread items raise toasts. `/api/notifications/stream` removed. |
| O-04 | Lock referenced custom factors | A value edit (unit, gas factors, HHV, parent fuel, uncertainties) on a factor used by records returns 409. Metadata edits are allowed. Each edit logs old → new values in the same commit. |
| O-05 | Superuser limited to one region | No organisation-wide superuser (a "Global" / "all" / blank location gives no data access). A region is required when creating a superuser or changing its role / location. Global settings, custom factors (incl. bulk import), goals, base year, SBTi and reporting metadata are admin only. The UI is updated to match. |
| O-07 | Remove | `conversations/`, `brain/`, `annotations/`, `*.pb` / `*.pbtxt`, `new/server.rar`, `calculations/calculations.rar` removed from the tree and added to `.gitignore`. They remain in git history. |

Results: backend 1,990 passed / 0 failed; `validation/` 128; vitest 38; lint 0 errors; build OK.

## Port to main (2026-10-08)

This audit was done on branch `ccr-669f6fbd-pew7ww`, which never reached `main` (main was rebuilt from a snapshot on 2026-10-04). Its changes were re-applied to the current module layout (`routes/auth_users.py`, `auth_settings.py`, `emissions_import.py`, TypeScript client):

| Item | State on main |
|------|---------------|
| A-01 ... A-06, A-09 ... A-14 | Ported, with the regression tests in `new/server/tests/test_full_audit_2026_10_01.py`. A-01 keeps main's stricter rule that client IT never resets business accounts. |
| A-07 | Already on main in another form (`get_batch_dashboard_data` checks the shared epoch before trusting the cache). |
| A-08 | Already on main. |
| A-15 | Ported: Settings edits are admin only, matching the API. |
| O-01, O-06 | Docker was removed on main too. The Sonatrach on-premise plan brings back a new, fixed package (`docs/sonatrach-implementation-plan.md`, M1). |
| O-02 | Ported: the client polls; the stream endpoint is gone. |
| O-04 | Ported. In addition, a non-admin value edit sends an approved factor back to `Pending`, so maker-checker cannot be bypassed by editing. |
| O-05 | Ported for settings, reporting metadata, goals, base year and SBTi. Custom factors follow main's later maker-checker design instead (superusers may propose, only admins approve). Superusers also no longer receive notifications outside their own location. |
| O-07 | Done on main (hardening plan phase 1). |
| O-03, O-08 ... O-11 | Still open. |
