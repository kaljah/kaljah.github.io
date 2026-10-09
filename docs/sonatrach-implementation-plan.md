# Sonatrach implementation plan (Claude-executed)

Companion to `docs/sonatrach-readiness-plan.md` (the what and why). This file is the how: the ordered task list Claude works through, one task per pull request, with the files each task touches and the check that proves it is done.

## How the work runs

**One task = one branch = one pull request.** Each task below is sized for one working session. Claude:
1. Reads this file and the status table first (sessions do not share memory; this table is the memory).
2. Branches from the latest `main`, implements the task, adds tests.
3. Runs the local gates before pushing: backend `python -m pytest -x --timeout=300`, `python scripts/loc_ratchet.py --check`; frontend `npm run lint`, `typecheck`, `check:ts`, `lint:css`, `ui:metrics -- --check`, `test`; plus the task's own **Verify** line.
4. Opens the PR, drives CI to green, updates the status table and `CLAUDE.md` in the same PR.
5. Never mixes two tasks, never merges its own PR (you review and merge).

**Inputs from people.** Tasks marked **[needs: X]** depend on an answer from you or Sonatrach. Where a safe default exists Claude builds it and keeps it switchable, so waiting for the answer does not block the work. Where no default is safe, the task waits.

**What Claude cannot do** (it prepares the material, people do the act): answer or sign the methodology questions, install on Sonatrach servers, run the Sonatrach security test, approve go-live gates, deliver training, sign the support contract.

## Status
| Milestone | State | PRs |
|-----------|-------|-----|
| Recovery of unmerged branches | Done 2026-10-08 | Audit 2026-10-01 (security fixes and owner decisions) and the Scope 1 100k import audit (S1K-F1..F37) ported from `ccr-669f6fbd-pew7ww` and `ccr-b93733a1-u3m8s8`; the other branches' work was already on main or superseded. Reports in `docs/validation/FULL_AUDIT_2026-10-01.md` and `SCOPE1_100K_BULK_AUDIT_2026-10-01.md`. |
| M0 Kick-off pack | Not started | |
| M1 Deployment package | Not started | |
| M2 Offline operation | Not started | |
| M3 Backups, releases, upgrades | Not started | |
| M4 Security hardening | Not started | |
| M5 Single sign-on | Not started | |
| M6 Organisation scope | T6.1 done (wildcards escaped, ported audit A-04) | |
| M7 French | Not started | |
| M8 Framework reports and methodology changes | Not started | |
| M9 Scale and quality | Not started | |
| M10 Handover pack | Not started | |

## Findings this plan fixes (found while planning, 2026-10-08)
- **Facility scoping matches strings with `ILIKE`** (wildcards fixed 2026-10-08; explicit scope assignments, T6.2, still to do) (`utils.get_allowed_facility_ids`, `new/server/utils.py:39-49`). `user.location` is compared to facility region, location and name, unescaped, so `%` or `_` in a location act as wildcards: a location of `%` grants a `user` or `superuser` every facility. Only IT roles set `location`, but IT must have no data access, and an IT admin can create a `user` account with `location="%"`. Fixed in M6 (T6.1 is the quick patch, T6.2 the real fix).
- **No deployment package**: `Dockerfile` and `docker-compose.yml` were removed in `9ac7e65` (and on branch `ccr-669f6fbd-pew7ww` by owner decision for the Render deployment; on-premise needs a new package). The old Dockerfile had two concatenated builds (the second, Render-specific one wins and does not include the frontend) and the compose file hard-coded `SECRET_KEY` and `test/test` database credentials.
- **Internet dependencies**: Google Fonts, Google and NASA GIBS map tiles, Copernicus/Sentinel-5P APIs. Sonatrach servers will likely have no outbound internet.
- **Number parsing in bulk upload** uses `float()` directly in `routes/emissions_bulk_upload.py`; the file import (`background_processor.py`) handles semicolon files with decimal commas and thousands separators, but T7.4 must cover every entry path.
- **Size of the French work**: about 1,100 JSX text strings and 170 toast/alert messages in `new/client/src`, about 350 backend error messages in `routes/`, and the 1,780-line PDF generator (`src/utils/ModernReportGenerator.ts`).

## M0 - Kick-off pack (week 1, no code)
Material for people to answer; Claude can write all of it from the code.

| # | Task | Output | Verify |
|---|------|--------|--------|
| T0.1 | Questionnaire for Sonatrach IT: OS, container runtime (Docker/Podman/Kubernetes), PostgreSQL provided or bundled, outbound internet, certificates, monitoring, backup storage, sign-in standard and directory groups, SMTP relay. | `docs/sonatrach/questions-it.md` | You can send it unedited |
| T0.2 | Questionnaire for Sonatrach security: test scope, timeline, acceptance criteria, required documents. | `docs/sonatrach/questions-security.md` | Same |
| T0.3 | HSE answer sheets for HR-01 to HR-10: for each, what the code does today (file and line), the options, a recommendation, and a blank for HSE's answer and signature. Plus the group-size, JV-boundary, base-year and regulator-template questions. | `docs/sonatrach/hse-answer-sheets.md` | Every HR item cites code; you review |
| T0.4 | Glossary seed for French: about 150 domain terms (torchage, ventage, émissions fugitives, facteur d'émission, ...) for HSE to correct before translation starts. | `docs/sonatrach/glossary-fr.csv` | HSE returns it |

## M1 - Deployment package
| # | Task | Files | Verify |
|---|------|-------|--------|
| T1.1 | Multi-stage image: build the SPA (`VITE_API_URL=/api`, base path `/`), runtime on `python:3.11-slim` without build tools, non-root user, pinned base images, `flask db upgrade` then gunicorn. Separate entrypoint for `background_processor.py` if it runs as its own process (check first). | `deploy/Dockerfile`, `.dockerignore`, `deploy/entrypoint.sh` | `docker build` succeeds; image runs as non-root; `/api/health` answers |
| T1.2 | nginx in front: serves the SPA and proxies `/api` on the **same origin**, TLS with mounted certificates, security headers (CSP, HSTS, frame-ancestors), upload size limit matching `MAX_CONTENT_LENGTH`. | `deploy/nginx/` | Headers present; SPA deep links reload correctly |
| T1.3 | Compose stack: nginx, app, PostgreSQL 15, Redis, volumes, health checks; secrets from an env file, no defaults in the file. `CORS_STRICT=true`, `ALLOWED_ORIGINS` set to the Sonatrach hostname. | `deploy/compose.yml`, `deploy/.env.example` | Fresh `docker compose up` on a clean clone; e2e smoke tier passes against it |
| T1.4 | CI job that builds the image, starts the stack and runs the smoke tier against it, so the package can never silently break. | `.github/workflows/package.yml` | Green on the PR |
| T1.5 | Separate the GitHub Pages demo from production: the Pages build keeps its settings; the onrender fallback in `deploy-pages.yml` is removed or marked demo-only. [needs: whether the public demo stays online] | `deploy-pages.yml`, `config.py` | Production build contains no `github.io` or `onrender` string |

## M2 - Offline operation
| # | Task | Files | Verify |
|---|------|-------|--------|
| T2.1 | Self-host fonts; remove Google Fonts calls. | client `index.html`/CSS | No external request on first load (Playwright network log) |
| T2.2 | Map tiles configurable (`MAP_TILE_URL`), default off on-premise with a plain basemap; Sonatrach can point it at an internal tile server. | Methane explorer components, `config.py` | Explorer loads with network blocked |
| T2.3 | Done 2026-10-09 by removal (owner decision): the Copernicus integration is gone. (Originally planned as a `SATELLITE_ENABLED` switch.) | `routes/satellite.py`, `services/sentinel5p.py`, `routes.config.ts` | Tests for both settings |
| T2.4 | Offline bundle: script that saves the images (`docker save`) with checksums and the install guide into one archive. | `deploy/make-bundle.sh` | Stack starts from the bundle in `docker run --network none` style isolation (no registry, no internet) |

## M3 - Backups, releases, upgrades
| # | Task | Files | Verify |
|---|------|-------|--------|
| T3.1 | Backup service in compose: scheduled `scripts/backup.py`, retention setting, backups to a mounted volume; PostgreSQL WAL archiving for point-in-time recovery. | `deploy/compose.yml`, `scripts/backup.py` | Backup files appear on schedule; retention deletes old ones |
| T3.2 | Automated restore drill: seed data, back up, destroy the database, restore, compare row counts and run the audit-chain verification. Runs in CI. | `deploy/tests/restore-drill.sh`, workflow | Drill passes; time to restore printed |
| T3.3 | Releases: version file, `CHANGELOG.md`, tag-triggered workflow that builds the offline bundle, SBOM (CycloneDX for Python and npm) and checksums as release assets. | `.github/workflows/release.yml` | A test tag produces all assets |
| T3.4 | Upgrade rehearsal in CI: start release N with data, upgrade to N+1, migrations run, audit chain still verifies, rollback steps documented. | workflow, `docs/sonatrach/upgrade.md` | Passes from the previous tag |

## M4 - Security hardening
| # | Task | Files | Verify |
|---|------|-------|--------|
| T4.1 | Done 2026-10-09. Remove `@csrf.exempt` from `/api/auth/login` and `/forgot-password` (same origin makes the token work); the client fetches the token before login. | `routes/auth.py`, `src/api.ts`, `Login.tsx`, security tests | Login without token gets 400; e2e login passes |
| T4.2 | Per-account lockout: failed-attempt counter and lock-until time, unlock by IT, audited. | migration, `models.py`, `routes/auth.py`, `auth_users.py` | Tests: lock after N failures, unlock, audit rows |
| T4.3 | TOTP two-factor sign-in for local accounts (`pyotp`): enrolment with QR code, recovery codes, IT reset, enforced for `admin` and IT roles, optional for others (setting). | migration, `routes/auth*.py`, Settings and Login pages | Tests for enrolment, login, recovery, reset |
| T4.4 | Idle session timeout (default 30 minutes, setting) alongside the 8-hour absolute limit. | `app.py`, `config.py`, client idle handler | Test: idle session rejected |
| T4.5 | Vendor role on-premise: `VENDOR_ACCESS_ENABLED=false` by default disables `it_manager` sign-in; document how Sonatrach enables a time-limited support account. | `routes/auth.py`, `utils.py`, docs | Tests for both settings |
| T4.6 | Security pack: architecture and data-flow diagram, threat model, role/permission matrix generated from the decorators, list of every setting and secret, dependency audit results, SBOM. | `docs/sonatrach/security-pack.md` | You review; matrix matches `app.url_map` |
| T4.7 | Pre-test sweep: run an automated web scan (OWASP ZAP baseline in Docker, if the network allows) and the existing security suites against the compose stack; fix what it finds. | findings log in the security pack | No high/critical left open |
| T4.8 | Fix findings from the Sonatrach security test, one PR per finding or group. [needs: their report] | as found | Their retest passes |

## M5 - Single sign-on
[needs: Sonatrach sign-in standard (T0.1)]. Default built now: OpenID Connect, which Entra ID (Azure AD) and ADFS both support.

| # | Task | Files | Verify |
|---|------|-------|--------|
| T5.1 | OIDC sign-in (authorization code + PKCE, Authlib): settings for issuer, client, secret; creates the account on first sign-in; local login switchable to break-glass only. | `routes/auth_oidc.py`, `config.py`, Login page | Tests against a stub provider; e2e against a Keycloak container in CI |
| T5.2 | Directory groups to roles and scopes: a mapping table admins edit; IT cannot map to `admin`/`superuser` (keeps the existing rule). | migration, admin page | Tests: group change updates role on next sign-in |
| T5.3 | SAML or LDAP, only if T0.1 says OIDC is not available. | | |

## M6 - Organisation scope
| # | Task | Files | Verify |
|---|------|-------|--------|
| T6.1 | **Quick fix, first PR of the project:** escape `%`, `_` and `\` in the `ILIKE` comparisons, or switch to case-insensitive equality; reject wildcard characters in `location` on save. | `utils.py`, `auth.py`, `auth_users.py`, tests | Test: `location="%"` gets no facilities |
| T6.2 | Explicit scope assignments replace string matching: a `user_scopes` table (user, level group/division/region/facility, target id). Migration converts existing `location` values and reports any that match nothing or several facilities. | migration, `models.py`, `utils.get_allowed_facility_ids` | All RBAC and IT-isolation suites pass; migration report on seeded data |
| T6.3 | Segregation of duties on scope: IT creates accounts, but data scope takes effect only after an `admin` approves it (maker-checker, audited). [needs: HSE/IT agree; default on] | routes, User Management page | Tests: IT-assigned scope inactive until approved |
| T6.4 | Division-level leads: allow a `superuser` scope at division level if HSE decides so. [needs: E2 decision] | `utils.py`, tests | Tests for the chosen rule |
| T6.5 | Group consolidation with JV equity shares (uses `FacilityEquityShare`): group, division and region totals under operational-control and equity-share approaches. [needs: A3 boundary rule] | dashboard/report services | Totals reconcile across levels (property test) |

## M7 - French
| # | Task | Files | Verify |
|---|------|-------|--------|
| T7.1 | i18n framework: `i18next` + `react-i18next`, language switch in Settings saved in user preferences, `fr` and `en` resources, a lint rule or script that counts untranslated literals and joins the `ui:metrics` ratchet. | client setup, `scripts/` | Ratchet counts drop with each later PR |
| T7.2 | Extract and translate, one PR per area: shell and login; data entry forms (Scope 1/2/3, ~5,000 lines); Manage Data and review; reports and dashboards; user management and settings. French uses the HSE-corrected glossary (T0.4). | pages and components | Untranslated count for the area reaches 0; screenshots in French |
| T7.3 | Backend messages: error and notification strings get codes; the client translates the code, the backend keeps the English text as fallback. | `routes/*`, `src/api.ts` | No raw English error shown in French mode |
| T7.4 | French number and date formats in display (`Intl`), and in CSV/Excel import: detect decimal comma per file, reject ambiguous values instead of guessing. | `emissions_bulk_upload.py`, import wizards | Tests: `1,5` and `1 234,5` parse right; `1,234` with no other hint is flagged |
| T7.5 | French templates and exports: CSV/Excel templates, PDF reports (`ModernReportGenerator.ts`), Excel exports. | as named | HSE accepts samples |

## M8 - Framework reports and methodology changes
[needs: HSE answers (T0.3) and the official templates]. Code changes follow the signed answers, never Claude's own judgement on methodology.

| # | Task | Verify |
|---|------|--------|
| T8.1 | Apply each HR answer (one PR per item): e.g. N2O flaring default, mobile vs stationary boundary, OGMP level mapping, Scope 3 categories, GWP-uncertainty default, custom-factor bounds. | Tests encode the signed answer and cite it |
| T8.2 | Reference cases traced to API Compendium 2021 worked examples (at least 3 per calculation family) in `validation/golden_dataset/`, each citing exhibit and page. [needs: a copy of the Compendium, or HSE supplies the examples] | Cases pass; citations present |
| T8.3 | Regulator report in the official template format (layout, units, GWP set). | HSE accepts a sample |
| T8.4 | OGMP 2.0 report in the template Sonatrach submits (builds on `routes/reports_ogmp.py`). | HSE accepts a sample |
| T8.5 | ISO 14064-1 / GHG Protocol inventory report: boundaries, base year, categories, uncertainty, exclusions. | HSE accepts a sample |
| T8.6 | Base-year handling for an empty start (A7): HSE-entered base-year totals or first-year lock. | Year-over-year and SBTi views work with either |

## M9 - Scale and quality
| # | Task | Verify |
|---|------|--------|
| T9.1 | Synthetic whole-group dataset generator (facilities, users, several years of records) sized from T0.1/E1 answers, default 500 facilities and 5 million records. | Loads into the compose stack |
| T9.2 | Load test (Locust or k6) on the compose stack with several gunicorn workers: dashboard, reports, bulk upload, review. Fix the slow paths found (indexes, query shape, cache). | Agreed response times met at target concurrency |
| T9.3 | Full 124-test e2e matrix nightly in CI (`schedule:`), plus against the compose stack. | Nightly green for a week |
| T9.4 | UAT scripts per role, in French, matching the e2e specs, for HSE users to run per wave. | `docs/sonatrach/uat/` |
| T9.5 | Parallel-run reconciliation report: compare app totals with an uploaded spreadsheet of the current method, per facility and gas, with differences listed. | Works on a test spreadsheet |

## M10 - Handover pack
| # | Task | Output |
|---|------|--------|
| T10.1 | Install and configuration guide for Sonatrach IT (every setting, from T1.3 and T4.6). | `docs/sonatrach/install.md` |
| T10.2 | Runbooks: upgrade, backup and restore, incident (lost admin, locked accounts, failed migration), user administration, log locations. | `docs/sonatrach/runbooks/` |
| T10.3 | User guides and training material in French per role (reuses UAT scripts and screenshots). | `docs/sonatrach/training/` |
| T10.4 | Support process: severity definitions, what to send with a bug report, release cadence. | `docs/sonatrach/support.md` |

## Order of work
Ordered so nothing waits on answers that have not come back yet.

| Weeks | Claude works on | Waiting on people |
|-------|-----------------|-------------------|
| 1 | T6.1 (security fix), M0 | Sonatrach answers to M0 |
| 2-4 | M1, M2, T4.1-T4.5 | |
| 4-6 | M3, T7.1, T7.4, T6.2-T6.3, T5.1-T5.2 (OIDC default) | HSE glossary, sign-in standard |
| 6-10 | T7.2-T7.3, T7.5, T4.6-T4.7, T9.1-T9.3, M8 as answers arrive | HSE answers and templates |
| 8-12 | T4.8, T5.3 if needed, T6.4-T6.5, T9.4-T9.5, M10 | Security test, installation on Sonatrach test servers |
| 12-24 | Fixes from each rollout wave; M8 follow-ups | Wave sign-offs |

About 60 pull requests in total. The critical path is not the code: it is the HSE answers (M8) and the Sonatrach security test (T4.8). Sending M0 in week 1 is what keeps the 24-week timeline possible.

## Decisions Claude will ask for when it reaches them
1. Keep the public GitHub Pages demo online? (T1.5)
2. Sonatrach sign-in standard. (M5; OIDC built by default)
3. Maker-checker on data scope. (T6.3; on by default)
4. Division-level superuser scope. (T6.4)
5. JV boundary approach. (T6.5)
6. Load test targets: facilities, users, response times. (T9.1-T9.2)
