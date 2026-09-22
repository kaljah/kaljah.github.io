# Phase 0 — Repository Discovery & Audit

> Audit Date: 2026-09-20  
> Auditor: Antigravity QA Engine  
> Repository: `https://github.com/kaljah/kaljah.github.io`  
> Local Path: `C:\Users\samsung\Desktop\H2`

---

## 1. Repository Structure Overview

```
H2/                                    ← Root workspace
├── new/
│   ├── server/                        ← ACTIVE: Flask 3.0 Python backend
│   │   ├── app.py                     ← Application factory + middleware
│   │   ├── config.py                  ← Environment-driven configuration
│   │   ├── models.py                  ← SQLAlchemy ORM (592 lines, 18 models)
│   │   ├── extensions.py              ← db, limiter singletons
│   │   ├── utils.py                   ← RLS helpers, audit logging
│   │   ├── background_processor.py   ← Async CSV/Excel ingestion (1938 lines)
│   │   ├── emission_factors.py        ← Default EF catalog (API 2021)
│   │   ├── emission_factors_api2021.py← Extended API 2021 factor catalog
│   │   ├── process_categories.py      ← Process type registry
│   │   ├── calculations/              ← ACTIVE: Calculation engine
│   │   │   ├── __init__.py
│   │   │   ├── base.py                ← BaseCalculator
│   │   │   ├── combustion.py          ← CombustionCalculator, FlaringCalculator
│   │   │   ├── vented.py              ← Pneumatics, Completions, Blowdown, Tanks
│   │   │   ├── fugitive.py            ← Component & Equipment fugitives
│   │   │   ├── midstream.py           ← AGR, Dehydrator
│   │   │   ├── indirect.py            ← Indirect Steam, Cogeneration
│   │   │   ├── stoichiometry.py       ← Stoichiometric mass balance
│   │   │   ├── units.py               ← Full unit conversion registry (558 lines)
│   │   │   ├── constants.py           ← GWP AR4/AR5/AR6 constants
│   │   │   ├── uncertainty.py         ← IPCC uncertainty propagation (432 lines)
│   │   │   ├── dispatcher.py          ← Calculation router (1382 lines, 60+ types)
│   │   │   ├── anomaly.py             ← Statistical anomaly detection
│   │   │   └── legacy_engine.py       ← ACTIVE (imported): Backward-compat wrapper
│   │   ├── routes/                    ← ACTIVE: 17 Flask blueprints
│   │   │   ├── auth.py                ← Login/register/RBAC (1121 lines)
│   │   │   ├── emissions.py           ← Scope 1 CRUD + calculations (4774 lines)
│   │   │   ├── scope2.py              ← Scope 2 endpoints
│   │   │   ├── scope3.py              ← Scope 3 endpoints
│   │   │   ├── dashboard.py           ← Analytics + cached KPIs (111930 bytes)
│   │   │   ├── reports.py             ← PDF/Excel/CSV report generation
│   │   │   ├── audit.py               ← Audit trail endpoints
│   │   │   ├── custom_factors.py      ← Custom emission factor CRUD
│   │   │   ├── facilities.py          ← Facility CRUD
│   │   │   ├── data.py                ← Production data CRUD
│   │   │   ├── qaqc.py                ← QA/QC diagnostics
│   │   │   ├── satellite.py           ← Satellite methane overlay
│   │   │   ├── notifications.py       ← SSE notification stream
│   │   │   ├── managedata.py          ← Data management / bulk ops
│   │   │   └── emission_factors_routes.py
│   │   ├── migrations/                ← Alembic migrations (5 version files)
│   │   ├── services/                  ← OGMP level assessment service
│   │   ├── tests/                     ← 43 test files, 880 tests
│   │   ├── ghg_app.db                 ← LIVE SQLite DB (2.3 GB)
│   │   └── import_debug.log           ← 4.1 GB unbounded log (CRITICAL ISSUE)
│   └── client/                        ← ACTIVE: React 19 + Vite SPA
│       ├── src/
│       │   ├── pages/                 ← 31 page components
│       │   ├── components/            ← 46+ UI components
│       │   ├── context/               ← AuthContext, LayoutContext
│       │   └── utils/                 ← EF catalog, PDF generators
│       ├── tests/                     ← 6 Node.js stress test files (.mjs)
│       ├── vite.config.js
│       └── package.json
├── validation/                        ← ACTIVE: Independent reference model
│   ├── reference_model/               ← 12 independent calculation modules
│   ├── golden_dataset/                ← Golden test cases (JSON)
│   ├── regression/                    ← Regression test registry
│   └── mutation/                      ← Mutation test artifacts
├── docs/
│   ├── calculation-specification.md
│   └── validation-report.md
├── .github/workflows/
│   └── deploy-pages.yml               ← CI: Frontend build + GitHub Pages only
├── 1k_scope1_comprehensive_test.csv   ← 183 KB test dataset
├── emission_sources.csv               ← 971 KB master EF catalog
├── emission_sources_v2.csv            ← 816 KB (updated version)
├── custom_factors.csv                 ← 41 KB custom EF seed data
├── mitigation_projects.csv            ← 1.3 MB mitigation seed data
├── production_data.csv                ← 781 KB production seed data
├── regions_upload.csv                 ← 4 KB region registry
├── Dockerfile                         ← ACTIVE but for backend only
├── docker-compose.yml                 ← ACTIVE
├── pytest.ini                         ← Root-level pytest config
└── old_ManageData.jsx                 ← LEGACY (in new/ directory)
```

---

## 2. File Classification

### 2.1 Active Production Files

| File / Directory | Status | Notes |
|---|---|---|
| `new/server/app.py` | **ACTIVE** | Main Flask application factory |
| `new/server/calculations/` | **ACTIVE** | Full calculation engine |
| `new/server/routes/` | **ACTIVE** | All 17 blueprint routes registered |
| `new/server/models.py` | **ACTIVE** | 18 ORM models |
| `new/server/background_processor.py` | **ACTIVE** | Async CSV/Excel ingestion thread |
| `new/client/src/` | **ACTIVE** | React 19 SPA frontend |
| `validation/reference_model/` | **ACTIVE** | Independent reference model |

### 2.2 Legacy / Obsolete Files

| File | Status | Notes |
|---|---|---|
| `old_ManageData.jsx` (root) | **LEGACY** | 304 KB old component at root level — NOT imported |
| `new/ManageData_old.jsx` | **LEGACY** | 138-byte stub placeholder |
| `new/server/calculations/legacy_engine.py` | **ACTIVE** | Re-exports from dispatcher — still imported by routes |
| `cbam_removal.patch`, `cbam_removal_utf8.patch` | **ARCHIVED** | CBAM feature removal patches (770 KB) |
| `cbam_diff_*.patch` | **ARCHIVED** | CSS/data diff patches |
| `patch.py`, `patch_ci.py`, `patch_manage_data.py`, etc. | **MAINTENANCE** | One-time patch scripts — no longer relevant |
| `fix_ui.py`, `fix_ui_2.py`, `fix_ui_tab.py` | **MAINTENANCE** | One-time UI fixes |
| `temp_old/` | **LEGACY** | Legacy directory (needs audit) |
| `import_debug.log` (4.1 GB) | **CRITICAL** | Unbounded log file consuming disk — see findings |
| `new/server/ghg_app.db` (2.3 GB) | **LIVE** | Production SQLite database |
| `new/server/ghg_app.db-wal` (233 MB) | **LIVE** | WAL journal — excessive, needs checkpoint |

### 2.3 v2 Files Assessment

| File | v1 | v2 | Status |
|---|---|---|---|
| `emission_sources.csv` | 971 KB | 816 KB | v2 is active seed; v1 may be superset |
| `production_data.csv` | 781 KB | 600 KB | v2 is active seed |
| `mitigation_projects.csv` | 1.3 MB | 1.2 MB | v2 is active seed |
| `generate_mock_data.py` | ✓ | v2 exists | Both present — v2 used for seeding |

### 2.4 Test Files Status

| File | Location | Status |
|---|---|---|
| `new/test_all_apis_health.py` | `new/` | Integration test (requires live server) |
| `new/test_deep_button_audit.py` | `new/` | UI button audit (Playwright-style) |
| `new/test_master_button_audit.py` | `new/` | UI master button audit |
| `new/test_final.py` (64 bytes) | `new/` | Stub — empty |
| `new/test_final_v2.py` (64 bytes) | `new/` | Stub — empty |
| `new/test_final_v3.py` (64 bytes) | `new/` | Stub — empty |
| `new/test_pipeline.py` (64 bytes) | `new/` | Stub — empty |
| `new/test_pipeline_robust.py` (64 bytes) | `new/` | Stub — empty |
| `new/server/tests/` | `new/server/tests/` | **ACTIVE** — 43 test files, 880 tests |
| `new/client/tests/` | `new/client/tests/` | Node.js stress tests (.mjs) — no test runner configured |

---

## 3. Key Architecture Findings

### 3.1 Backend Architecture
- **Framework**: Flask 3.0.3 (Python)  
- **Database**: SQLite (development/default) OR PostgreSQL (production via `DB_TYPE=postgres`)  
- **ORM**: Flask-SQLAlchemy 3.1.1 with Alembic migrations  
- **Authentication**: Session-based (Flask sessions, HTTP-only cookies)  
- **Authorization**: Decorator-based RBAC (5 roles: `admin`, `superuser`, `user`, `it_admin`, `it_manager`)  
- **Rate Limiting**: Flask-Limiter 3.5.0 (memory:// by default — not Redis)  
- **CSRF**: Flask-WTF CSRFProtect (auth blueprint explicitly exempted)  
- **Background Jobs**: Threading-based (not Celery) — `upload_jobs` dict in memory  
- **No email system**: No SMTP, no Flask-Mail, no email sending code found  
- **No Redis**: Rate limiting uses in-memory backend  
- **No SSO/OAuth**: Local password authentication only  

### 3.2 Frontend Architecture
- **Framework**: React 19 + Vite 7 SPA  
- **State**: React Context (`AuthContext`, `LayoutContext`)  
- **Charts**: Recharts + Chart.js  
- **Maps**: Leaflet + react-leaflet  
- **PDF**: jsPDF + jsPDF-autotable  
- **Forms**: Formik + Yup validation  
- **CSS**: Tailwind CSS 4 + custom CSS modules  
- **No SSR**: Pure SPA — Server-Side Rendering is **NOT APPLICABLE**  
- **No Next.js**: No Next.js or server components — **NOT APPLICABLE**  
- **No frontend unit test framework**: No Vitest/Jest configured in `package.json`  
- **Frontend tests**: 6 Node.js `.mjs` stress test files (state machine simulation, no browser automation)  

### 3.3 CI/CD
- **Only one workflow**: `.github/workflows/deploy-pages.yml`
- **Purpose**: Build React SPA and deploy to GitHub Pages
- **No backend CI**: Backend tests NOT run in CI
- **No security scanning**: No dependency audit, SAST, or secret scanning in CI
- **No E2E in CI**: No Playwright/Cypress pipeline step

### 3.4 Deployment Architecture
- **Frontend**: GitHub Pages (static SPA)
- **Backend**: Render.com (inferred from `ghg-accounting.onrender.com` in CI config)
- **Database**: SQLite on local disk (development) — no managed DB service confirmed
- **Container**: Dockerfile present for backend (single-stage)

---

## 4. Critical Observations

### CRITICAL-01: 4.1 GB Unbounded Log File
- **File**: `new/server/import_debug.log` (4.1 GB)
- **Impact**: Disk exhaustion risk; this file is NOT governed by the rotating handler
- **Note**: `app.py` implements rotating handler for `trace.log` (50 MB, 3 backups), but `import_debug.log` is separate and unbounded
- **Status**: CRITICAL — must be addressed

### CRITICAL-02: 233 MB WAL Journal
- **File**: `new/server/ghg_app.db-wal` (233 MB)
- **Impact**: Indicates WAL checkpoint has not run recently or the batch import is ongoing
- **Note**: App implements periodic WAL checkpoint every 500 commits
- **Status**: HIGH — investigate

### CRITICAL-03: No Backend Tests in CI
- **Finding**: CI pipeline only builds and deploys the frontend
- **Impact**: Backend bugs, calculation errors, and security regressions are NOT caught in CI
- **Status**: HIGH

### CRITICAL-04: Rate Limiting Scope Gap
- **Finding**: `extensions.py` sets `default_limits=[]` — no global default rate limit
- **Impact**: Only endpoints explicitly decorated with `@limiter.limit(...)` are protected
- **Status**: HIGH — requires audit of each route to confirm rate limit coverage

### CRITICAL-05: No Frontend Unit Test Framework
- **Finding**: `package.json` has no Vitest or Jest dependency. The 6 `.mjs` files in `client/tests/` are custom Node.js scripts that simulate state changes in-process without a browser
- **Impact**: No automated frontend component testing, no rendering tests, no DOM testing
- **Status**: HIGH — DOCUMENTED BUT NOT FULLY IMPLEMENTED (automated frontend unit tests)

### CRITICAL-06: RLS is Application-Level, Not Database-Level
- **Finding**: Row-Level Security is implemented via `get_allowed_facility_ids()` in `utils.py`, which is called by routes. There is NO PostgreSQL RLS policy, no SQLite ATTACH-level restriction
- **Impact**: If any route accidentally omits the filter, data from other organizations leaks
- **Status**: MEDIUM-HIGH — application-level RLS is weaker than database-level RLS

### CRITICAL-07: Auth Blueprint CSRF-Exempt
- **Finding**: `csrf.exempt(auth_bp)` in `app.py` — the entire authentication blueprint is exempt from CSRF
- **Justification**: GitHub Pages SPA cannot share a CSRF token domain with Render backend
- **Risk**: Login/logout/register endpoints are CSRF-vulnerable (relies on SameSite=None + HTTPS in production)
- **Status**: MEDIUM — architectural constraint, document for human review

### CRITICAL-08: Default Admin Credentials in README
- **Finding**: README explicitly documents `admin@ghg.com` as default email; `seed_admin.py` uses `ADMIN_EMAIL`/`ADMIN_PASSWORD` env vars with no documented forced-change mechanism
- **Status**: HIGH — Production deployments must verify admin password is changed

---

## 5. Feature Verification vs. README Claims

| Claimed Feature | Implementation Verified | Notes |
|---|---|---|
| Scope 1 combustion | ✅ **IMPLEMENTED** | `calculations/combustion.py` — CombustionCalculator |
| Scope 1 flaring | ✅ **IMPLEMENTED** | `calculations/combustion.py` — FlaringCalculator |
| Scope 1 venting | ✅ **IMPLEMENTED** | `calculations/vented.py` — BlowdownCalculator |
| Scope 1 fugitives | ✅ **IMPLEMENTED** | `calculations/fugitive.py` — Component + Equipment |
| Pneumatic devices | ✅ **IMPLEMENTED** | `calculations/vented.py` — PneumaticDeviceCalculator |
| Completions | ✅ **IMPLEMENTED** | `calculations/vented.py` — CompletionFlowbackCalculator |
| Drilling | ✅ **IMPLEMENTED** | `calculations/vented.py` — MudDegassingCalculator |
| OGMP 2.0 | ✅ **IMPLEMENTED** | `services/ogmp.py`, `OgmpSurvey` model |
| Scope 2 | ✅ **IMPLEMENTED** | `routes/scope2.py`, `calculations/indirect.py` |
| Scope 3 | ✅ **IMPLEMENTED** | `routes/scope3.py`, `calculations/units.py` |
| Uncertainty | ✅ **IMPLEMENTED** | `calculations/uncertainty.py` — IPCC SRSS method |
| RBAC | ✅ **IMPLEMENTED** | 5 roles with decorators |
| RLS | ✅ **IMPLEMENTED** (app-level only) | `utils.py` `get_allowed_facility_ids()` |
| Audit logs | ✅ **IMPLEMENTED** | `ActivityLog` model + `log_activity_and_notify()` |
| Rate limiting | ✅ **PARTIALLY IMPLEMENTED** | Flask-Limiter configured; coverage per-route not fully verified |
| CSRF | ✅ **PARTIALLY IMPLEMENTED** | Enabled globally; auth blueprint exempt |
| Async ingestion | ✅ **IMPLEMENTED** | `background_processor.py` threading model |
| Email | ❌ **NOT IMPLEMENTED** | No Flask-Mail, no SMTP code found |
| SSR | ❌ **NOT APPLICABLE** | Vite SPA only |
| Redis cache | ❌ **NOT IMPLEMENTED** | In-memory rate limit only |
| E2E browser tests | ⚠️ **PARTIAL** | 6 Node.js state simulation scripts, no Playwright/Cypress |
| Frontend unit tests | ❌ **NOT IMPLEMENTED** | No Vitest/Jest; only ESLint configured |

---

## 6. Database Schema Summary

Models confirmed in `models.py`:
1. `User` — with RBAC role field and password hash
2. `Facility` — with segment, region, division, field
3. `Emission` — Scope 1 records with full calculation fields
4. `ProductionData` — Oil/gas volumes per facility/month
5. `EmissionSource` — Equipment registry
6. `CustomFactor` — User-defined emission factors
7. `ActivityLog` — Immutable audit log
8. `Goal` — Reduction targets
9. `BaseYear` — Singleton base year record
10. `MitigationRecord` — Mitigation entries
11. `Scope3Data` — Legacy Scope 3 data
12. `Scope2Emission` — Scope 2 records
13. `Scope3Emission` — Scope 3 records
14. `MitigationProject` — Project-level mitigation
15. `BaseYearRecalculation` — Recalculation audit records
16. `ReportingMetadata` — Annual reporting metadata
17. `Notification` — In-app notification system
18. `CbamProductExport` — CBAM export data (retained post-patch)
19. `OgmpSurvey` — OGMP measurement surveys
20. `MethaneSourceType` — Methane source type registry
21. `LevelUpgradeLog` — OGMP level upgrade audit
22. `SbtiTarget` — Science-Based Targets initiative records
23. `SystemSetting` — Key-value app settings store

---

## 7. Dependency Summary

### Backend (Python)
| Package | Version | Notes |
|---|---|---|
| Flask | 3.0.3 | Current stable |
| Flask-SQLAlchemy | 3.1.1 | Current stable |
| Flask-CORS | >=5.0.0 | Current |
| Flask-Migrate | 4.0.5 | Current |
| Flask-WTF | 1.2.1 | CSRF protection |
| Flask-Limiter | 3.5.0 | Rate limiting |
| Werkzeug | >=3.0.6 | Security fix version |
| reportlab | 4.0.7 | PDF generation |
| openpyxl | 3.1.2 | Excel I/O |
| gunicorn | >=21.2.0 | Production WSGI |
| psycopg2-binary | >=2.9.9 | PostgreSQL driver |
| cachetools | >=5.3.0 | In-memory caching |
| hypothesis | (in .hypothesis/) | Property-based testing |

### Frontend (Node.js)
| Package | Version | Notes |
|---|---|---|
| React | 19.2.0 | Latest major |
| Vite | 7.2.4 | Latest major |
| react-router-dom | 7.13.0 | Latest |
| axios | 1.13.5 | HTTP client |
| chart.js | 4.5.1 | Charts |
| recharts | 3.7.0 | Charts |
| formik | 2.4.9 | Form management |
| yup | 1.7.1 | Validation |
| jsPDF | 4.1.0 | PDF export |
| tailwindcss | 4.1.18 | CSS framework |
| **No Vitest/Jest** | — | **Frontend unit tests NOT installed** |
| **No Playwright/Cypress** | — | **E2E tests NOT installed** |

---

*Document generated: 2026-09-20 | Status: COMPLETE*
