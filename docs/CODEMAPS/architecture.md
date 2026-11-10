<!-- Generated: 2026-10-27 | Files scanned: 637 | Token estimate: ~750 -->
# System Architecture

Enterprise Greenhouse Gas (GHG) Accounting & Reporting Platform.
Built on API Compendium (2021), GHG Protocol, OGMP 2.0, and IPCC AR5/AR6 methodologies.

## System Topology

```
[ Browser / Client SPA ]
       │  (HTTPS / REST / JSON)
       ▼
[ Flask App Factory (app.py) ]
  ├── Security Layer: CSRF Token + CORS + Flask-Limiter + IdGuard
  ├── Auth & Session: Session Cookie + RBAC (Superuser, Admin, Auditor, Ops, IT)
  │
  ├── REST Blueprint Router (/api/*)
  │     ├── /api/auth             → Authentication & Password lifecycle
  │     ├── /api/emissions        → Scope 1, 2, 3 CRUD & Calculations
  │     ├── /api/facilities       → Facility assets & equity share mapping
  │     ├── /api/reports          → Master, OGMP 2.0, CBAM, and PDF generation
  │     ├── /api/dashboard        → Cached aggregations & KPIs
  │     ├── /api/managedata       → Schema sync, bulk upload, backup
  │     └── /api/qaqc             → Anomaly detection & confidence scoring
  │
  ├── Calculation Engine (calculations/dispatcher.py)
  │     ├── Combustion Engine     → Fuel stoichiometry & API Compendium
  │     ├── Venting Engine        → Tanks, pneumatics, blowdown, acid gas
  │     ├── Fugitive Engine       → Component counts & leak detection (LDAR)
  │     ├── Scope 2 Engine        → Market & location-based electricity
  │     └── Scope 3 Engine        → Spend-based screening & GHG Protocol categories
  │
  ├── Background Processor (background_processor.py)
  │     └── In-process background processing (threading; optional Redis queue) for batch imports & reports
  │
  └── Persistence Layer (SQLAlchemy ORM)
        ├── SQLite / PostgreSQL (Relational Database)
        └── Immutable Audit Trail (ActivityLog table)
```

## Service Boundaries

| Service Boundary | Responsibility | Primary Entrypoint |
|---|---|---|
| **Client SPA** | React 18 + Vite dashboard, wizards, interactive forms, analytics | `new/client/src/main.tsx` |
| **API Server** | Flask 3.1 app, route dispatching, auth, session middleware | `new/server/app.py` |
| **Calculation Dispatcher** | Deterministic stoichiometry, emission factor lookup, units | `new/server/calculations/dispatcher.py` |
| **Batch Worker** | Async chunk processing for massive CSV/Excel ingestion | `new/server/background_processor.py` |
| **Report Engine** | Multi-standard export generator (PDF, Excel, CBAM, OGMP) | `new/server/routes/reports.py` |
| **Audit Subsystem** | Append-only event logging for all mutations and recalculations | `new/server/routes/audit.py` |

## Core Data Flow

```
1. Input:      Raw Activity Data (Manual form / CSV / Excel bulk upload)
                   │
2. Ingestion:  Validation (input_validation.py) → Column Mapping Wizard → Schema Normalizer
                   │
3. Calculation: Dispatcher → Specific Method Engine → GWP Conversion (CO2e, CH4, N2O)
                   │
4. Storage:    Emissions Record + Production Data + Audit Log Entry
                   │
5. Aggregations: Facility Totals → Scope 1/2/3 Breakdown → Intensity Metrics (kg CO2e/boe)
                   │
6. Export:     Executive PDF / CBAM XML / OGMP 2.0 Templates / SBTi Progress
```
