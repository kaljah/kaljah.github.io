# GHG Platform — Fix Execution Tracker

## PHASE 1 — CRITICAL
- [x] 1.1 Delete import_debug.log + route imports to rotating handler
- [x] 1.2 Remove hard-coded dev credentials (a@a, a) from app.py
- [x] 1.3 Add backend CI job to GitHub Actions

## PHASE 2 — HIGH SECURITY
- [x] 2.1 Rate limiting — global defaults + per-route audit
- [x] 2.2 CSRF — double-submit cookie pattern
- [x] 2.3 WAL journal — force checkpoint + lower interval

## PHASE 3 — HIGH QUALITY (Testing)
- [x] 3.1 Backend test isolation — in-memory SQLite conftest.py
- [x] 3.2 Frontend unit tests — Vitest + React Testing Library
- [x] 3.3 E2E tests — Playwright

## PHASE 4 — CALCULATION FIX
- [x] 4.1 N2O flaring default inconsistency — harmonize to 0.0001 kg/MMBtu

## PHASE 5 — DATABASE
- [x] 5.1 PostgreSQL migration plan + script
- [x] 5.2 Backup/restore procedure
- [x] 5.3 Alembic downgrade paths

## PHASE 6 — MEDIUM FIXES
- [x] 6.1 Deprecation warnings (openpyxl, reportlab)
- [x] 6.2 Custom factor plausibility bounds

## PHASE 7 — SMOKE TESTS
- [x] 7.1 10-step production smoke test suite

## PHASE 8 — CI/CD INTEGRATION
- [x] 8.1 Wire all phases into unified pipeline
