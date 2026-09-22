# System Architecture & Technical Topology Map

**Document**: `docs/validation/00-current-architecture.md`  
**Classification**: Software & Systems Architecture Verification  
**Evaluation Target**: `kaljah/kaljah.github.io` (`c:\Users\samsung\Desktop\H2`)  
**Audit Date**: September 20, 2026  
**Auditor**: Senior QA Engineer, Enterprise Architect & Systems Auditor  

---

## 1. Architectural Reality vs. README Claims

An exhaustive physical inspection of the workspace was conducted to decouple actual production reality from outdated documentation, legacy configurations, and historical README claims:

| Architectural Domain | Historical README / Legacy Claim | Actual Workspace Implementation | Status |
| :--- | :--- | :--- | :--- |
| **Application Runtime** | Desktop Electron application (`main.js`, `server.js` in root) | Modern Client-Server Web Architecture: React SPA + Flask API Server | **ACTIVE ARCHITECTURE DISCOVERED** |
| **Backend Framework** | Node.js / Express or generic Python | Python 3.11/3.12 with Flask 3.0.3, Flask-SQLAlchemy 3.1.1, Flask-WTF, Flask-Limiter | **VERIFIED IMPLEMENTATION** |
| **Frontend Framework** | Static HTML / Vanilla JS or Electron webview | React 19.2.0 + Vite 7.2.4 SPA styled with TailwindCSS 4 and Recharts / Chart.js | **VERIFIED IMPLEMENTATION** |
| **Calculation Engine** | Monolithic script or client-side calculation | Modular server-side calculation package (`new/server/calculations/`) with dynamic dispatcher | **VERIFIED IMPLEMENTATION** |
| **Validation Architecture**| Basic unit tests | Separate pure-Python reference model (`validation/reference_model/`) with zero production dependencies | **INDEPENDENT MODEL ACTIVE** |
| **Database Engine** | SQLite file without concurrency controls | SQLite with WAL mode, busy timeouts, and periodic checkpointing + PostgreSQL 15 support | **VERIFIED IMPLEMENTATION** |
| **Background Processing**| Synchronous CSV uploads | Asynchronous worker threads with in-memory job dictionaries and chunked processing | **VERIFIED IMPLEMENTATION** |

---

## 2. Directory Structure & Lifecycle Classification

The codebase contains 4 major functional directories alongside legacy artifacts. Each directory is classified by operational status:

```
c:\Users\samsung\Desktop\H2\
├── new/
│   ├── server/               [PRODUCTION CODE - ACTIVE]
│   │   ├── app.py            # Primary Flask application entry point
│   │   ├── config.py         # Multi-environment configuration & secrets
│   │   ├── models.py         # SQLAlchemy ORM models (23 domain models)
│   │   ├── calculations/     # Scope 1, 2, 3, GWP, and uncertainty engines
│   │   ├── routes/           # 15 Blueprint API route modules
│   │   ├── services/         # OGMP, Sentinel-5P, Email, ERP services
│   │   ├── migrations/       # Alembic database migration scripts (5 versions)
│   │   └── tests/            # Backend automated test suite (43 modules)
│   └── client/               [PRODUCTION CODE - ACTIVE]
│       ├── src/              # React 19 SPA source (components, pages, context)
│       ├── tests/            # UI stress benchmarks & visual parity test suites
│       ├── package.json      # Client dependencies & Vite build scripts
│       └── vite.config.js    # Vite compilation & proxy configuration
├── validation/               [TEST & VALIDATION INFRASTRUCTURE - ACTIVE]
│   ├── reference_model/      # Pure-Python independent GHG reference calculators
│   ├── golden_dataset/       # Authoritative golden test vectors (Categories A–Q)
│   ├── mutation/             # Mutational fault injection suite (10 mutants)
│   ├── regression/           # Permanent defect regression archive
│   └── scripts/              # Master validation runner (run_full_validation_suite.py)
├── docs/                     [DOCUMENTATION - ACTIVE]
│   ├── calculation-specification.md  # Governing engineering & standard specs
│   └── validation/           # Master audit documentation & verification records
├── Dockerfile                [DEPLOYMENT - ACTIVE] (Multi-stage build)
├── docker-compose.yml        [DEPLOYMENT - ACTIVE] (Flask + PostgreSQL 15)
├── package.json (root)       [LEGACY / UNUSED] (Old Electron config; references nonexistent main.js)
├── server.rar, *.rar         [LEGACY / UNUSED] (Deprecated binary archives)
└── patch*.py, test_final*.py [SCRATCH / UNUSED] (Ad-hoc historical patches)
```

---

## 3. Subsystem Architecture Analysis

### 3.1 Frontend Single-Page Application (SPA)
- **Framework**: React 19.2.0 bundled via Vite 7.2.4.
- **Routing**: `react-router-dom` v7 with role-based routing gates:
  - `PrivateRoute`: Session check redirecting unauthenticated traffic to `/login`.
  - `NonITRoute`: Enforces Segregation of Duties (SoD) by routing `it_admin` and IT staff away from confidential emissions data to `/user-management`.
  - `SuperuserRoute` & `AdminRoute`: Protects QA/QC diagnostics and administrative settings.
  - `AuditRoute`: Restricts audit trails to authorized auditors.
- **State Management & Communication**: Native React Context (`AuthContext`, `LayoutContext`, `ToastProvider`) paired with an Axios instance (`api.js`) handling cookie-based sessions and automated `X-CSRFToken` injection.
- **Visual Analytics**: Dynamic charting powered by Chart.js 4.5 and Recharts 3.7; geographic methane plume mapping powered by Leaflet and React-Leaflet.

### 3.2 Backend API Server
- **Framework**: Flask 3.0.3 using the Application Factory pattern and modular Blueprints.
- **Registered Blueprints (15 endpoints)**:
  1. `/api/auth` (`routes/auth.py`): Authentication, sessions, user management, and operational defaults.
  2. `/api/emissions` (`routes/emissions.py`): Scope 1 CRUD, calculation endpoints, maker-checker approvals, and async file ingestion.
  3. `/api/facilities` (`routes/facilities.py`): Facility hierarchy, metadata, boundary definitions, and regional filtering.
  4. `/api/data` (`routes/data.py`): Production data (oil/gas volumes) and operational metrics.
  5. `/api/reports` (`routes/reports.py`): Multi-format report generation (PDF via ReportLab, Excel via openpyxl, CSV).
  6. `/api/dashboard` (`routes/dashboard.py`): Aggregated executive KPIs, emissions breakdowns, and trends.
  7. `/api/custom-factors` (`routes/custom-factors.py`): Organization-specific Tier 2 emission factors with uncertainty parameters.
  8. `/api/scope2` (`routes/scope2.py`): Indirect electricity, steam, heating, and cooling emissions.
  9. `/api/scope3` (`routes/scope3.py`): Value chain emissions across Scope 3 categories (Categories 1–15).
  10. `/api/managedata` (`routes/managedata.py`): Bulk data management and administrative tabular interfaces.
  11. `/api/emission-factors` (`routes/emission_factors_routes.py`): API Compendium 2021 factor catalog lookup.
  12. `/api/notifications` (`routes/notifications.py`): Real-time user notifications and alert streams.
  13. `/api/audit` (`routes/audit.py`): Immutable audit logging and change tracking.
  14. `/api/satellite` (`routes/satellite.py`): Copernicus Sentinel-5P observation retrieval and OGMP Level 5 survey management.
  15. `/api/qaqc` (`routes/qaqc.py`): Anomaly detection, statistical variance analysis, and data health verification.

### 3.3 Database & Storage Layer
- **ORM**: Flask-SQLAlchemy 3.1.1 on top of SQLAlchemy 2.0.
- **RDBMS Engines**:
  - **Default**: SQLite 3 (`ghg_app.db`). Concurrency is optimized using:
    - `PRAGMA foreign_keys = ON` (referential integrity).
    - `PRAGMA journal_mode = WAL` (Write-Ahead Logging for concurrent readers/writer).
    - `PRAGMA synchronous = NORMAL` (data safety with minimal I/O overhead).
    - `PRAGMA busy_timeout = 5000` (5-second lock waiting before raising lock errors).
    - Automated `PRAGMA wal_checkpoint(TRUNCATE)` every 500 commits to control file size.
  - **Enterprise Production**: PostgreSQL 15 (configured via `DATABASE_URL` with connection pooling).
- **Domain Models**: 23 comprehensive database models capturing users, facilities, emission records, production data, custom factors, activity logs, goals, base years, Scope 2/3 entries, CBAM exports, and OGMP surveys.

### 3.4 Authentication, Authorization & Segregation of Duties
- **Session Lifecycle**: Server-managed cookie sessions (`user_id` stored in session cookie).
  - Secure flags: `HttpOnly=True`, `SameSite=Lax/None`, 8-hour lifetime (`PERMANENT_SESSION_LIFETIME = timedelta(hours=8)`).
  - Session fixation defense: Explicit `session.clear()` invoked upon successful authentication.
  - Account status check: All decorators verify `user.status == 'active'` on every request.
- **Segregation of Duties (SoD)**:
  - `it_admin` / `it_manager`: User account provisioning and password resets. Absolutely zero access to GHG inventory records or facilities.
  - `admin`: Global organizational control, maker-checker approvals, and system-wide configurations.
  - `superuser`: Regional oversight; restricted to facilities matching their assigned `user.location` unless location is `'all'` or `'global'`.
  - `user`: Operational data entry; restricted to assigned regional facilities.
- **Maker-Checker Protocol**:
  - Bulk uploads and regular user submissions default to `status = 'Pending'`.
  - Only authorized Approvers (`admin`, `superuser`) can transition records to `'Verified'`.
  - Editing activity data of an existing record automatically invalidates prior approval, recalculates emissions, and resets status to `'Pending'`.

### 3.5 Calculation Engine Architecture
- **Central Dispatcher**: [`CalculationDispatcher`](file:///c:/Users/samsung/Desktop/H2/new/server/calculations/dispatcher.py) maps process types to specialized calculation engines:
  - `CombustionCalculator`: Stationary and mobile fuel combustion with unit-aware heating value scaling.
  - `FlaringCalculator`: Dual-efficiency combustion ($\eta_c$) and unburnt methane destruction ($\eta_d$) based on API Compendium §5.2.
  - `MudDegassingCalculator`: Drilling and mud gas desorption.
  - `CompletionFlowbackCalculator`: Well completion and hydraulic fracturing venting/flaring.
  - `LiquidsUnloadingCalculator`: Wellbore liquid lifting (with and without plunger lifts).
  - `TankFlashingCalculator`: Crude oil and condensate flash gas, working, and standing losses.
  - `PneumaticDeviceCalculator`: Intermittent, low-bleed, high-bleed pneumatic controllers and chemical pumps.
  - `ComponentFugitiveCalculator` & `EquipmentFugitiveCalculator`: Equipment leaks and component screening.
  - `CompressorSealCalculator`: Centrifugal (wet/dry seal) and reciprocating compressor packings.
  - `AGRCalculator` & `DehydratorCalculator`: Midstream acid gas sweetening and TEG dehydration.
  - `IndirectSteamCalculator` & `CogenAllocationCalculator`: Purchased steam, district heating/cooling, and CHP efficiency allocations.
  - `StoichiometricCalculator`: SMR hydrogen reforming, ammonia, and chemical process stoichiometry.
  - `propagate_uncertainty`: Analytical Gaussian uncertainty propagation (IPCC Tier 1 / ISO GUM).

### 3.6 Background Ingestion & Processing
- **Engine**: [`background_processor.py`](file:///c:/Users/samsung/Desktop/H2/new/server/background_processor.py).
- **Concurrency Model**: Worker threads decoupled from the HTTP request cycle using an in-memory job dictionary.
- **Safety Protections**:
  - File validation against magic numbers and whitelisted extensions (`.csv`, `.xlsx`, `.xls`).
  - Automated file descriptor cleanup (`os.close(fd)`).
  - TTL-based pruning (`_prune_old_jobs(86400)`) removing expired tracking entries and temp files after 24 hours.

### 3.7 Caching & Performance Subsystem
- **Caching Mechanism**: Memory cache (`cachetools.TTLCache`) caching expensive dashboard aggregation queries.
- **Granular Cache Invalidation**: SQLAlchemy `before_commit` event listener inspects modified entities (`Emission`, `Scope2Emission`, `Scope3Emission`, `ProductionData`, `Facility`, `CustomFactor`, `OgmpSurvey`) and triggers cache purging only when GHG-relevant data changes.

### 3.8 Observability & Logging Architecture
- **Logging Pipeline**: Python `RotatingFileHandler` writing structured logs to `trace.log` with a 50 MB threshold and 3-generation backup rotation.
- **Request Tracing**: `X-Request-ID` middleware generates or validates UUID correlation IDs (`^[A-Za-z0-9\-]{1,64}$`) on every inbound request and propagates it to all error payloads and response headers.
- **Error Shielding**: Unhandled 500 exceptions log the full traceback internally while presenting a sanitized JSON error payload to the client (`{"error": "Internal server error", "code": 500, "request_id": "..."}`).

---

## 4. Deployment Architecture

- **Containerized Stack**: Multi-stage production `Dockerfile`:
  - *Stage 1*: Node 20 Alpine frontend build (`npm run build` producing static assets in `dist/`).
  - *Stage 2*: Python 3.11 Slim runtime installing backend dependencies and serving the application via Gunicorn WSGI (`gunicorn --bind 0.0.0.0:5000 --workers 4 --timeout 120 app:app`).
- **Orchestration**: `docker-compose.yml` linking the containerized Flask API with a dedicated PostgreSQL 15 database container featuring healthcheck monitoring.
