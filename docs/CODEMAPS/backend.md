<!-- Generated: 2026-10-27 | Files scanned: 637 | Token estimate: ~850 -->
# Backend Architecture

Flask 3.1 REST API backend with modular blueprints, calculation engines, and asynchronous processing.

## Middleware Pipeline

Incoming HTTP Request
  │
  ├─► `app.before_request`: Security Headers (HSTS, CSP, X-Frame-Options, Cache-Control)
  ├─► `limiter`: Rate limiting (Flask-Limiter) per IP/User
  ├─► `csrf.protect()`: CSRF token verification for mutating calls (POST/PUT/DELETE)
  ├─► `auth.session`: Session validation & identity extraction
  ├─► `id_guard.py`: Numeric ID boundary validation & SQL injection prevention
  └─► Blueprint Handler Execution
        │
        └─► `app.after_request`: Auditing, response header normalization, DB session cleanup

## REST Route Blueprints

| Blueprint | URL Prefix | Key Endpoints & Handlers |
|---|---|---|
| `auth_bp` | `/api/auth` | `POST /login`, `POST /logout`, `GET /me`, `POST /change-password`, `GET /csrf-token` |
| `emissions_bp` | `/api/emissions` | `GET/POST /`, `GET/PUT/DELETE /<id>`, `/bulk-upload`, `/export`, `/mappings` |
| `facilities_bp` | `/api/facilities` | `GET/POST /`, `GET/PUT/DELETE /<id>`, `/equity-shares` |
| `dashboard_bp` | `/api/dashboard` | `GET /summary`, `GET /trends`, `GET /flaring`, `GET /ogmp`, `GET /sbti` |
| `reports_bp` | `/api/reports` | `GET /master-report`, `POST /generate-pdf`, `/cbam`, `/national`, `/ogmp` |
| `scope2_bp` | `/api/scope2` | `GET/POST /`, `GET /factors` (Market vs. Location based) |
| `scope3_bp` | `/api/scope3` | `GET/POST /`, Spend-based screening & GHG Protocol category estimates |
| `custom_factors_bp` | `/api/custom-factors` | `GET/POST /`, factor overrides per facility/fuel type |
| `audit_bp` | `/api/audit` | `GET /logs`, `GET /recalculations`, filtering by date/actor |
| `qaqc_bp` | `/api/qaqc` | `GET /anomalies`, `POST /validate`, `GET /confidence-score` |
| `equity_bp` | `/api/equity` | `GET/POST /partners`, JV ownership calculations |
| `ldar_bp` | `/api/ldar` | `GET/POST /surveys`, component leak repair tracking |
| `managedata_bp` | `/api` | `/db-status`, `/schema-sync`, `/backup` |

## Calculation Engines (`new/server/calculations/`)

Deterministic stoichiometric and factor calculation pipeline:
- `dispatcher.py`: Master calculation router; selects engine by scope, category, and source type.
- `combustion.py`: Fuel consumption, HHV energy density, thermal oxidation, flaring stoichiometry.
- `vented.py` & `vented_*.py`: Tank flashing, pneumatic controllers, blowdown, glycol dehydrators.
- `fugitive.py` & `fugitive_onshore.py`: API Compendium component counts, EPA correlations, LDAR screening.
- `uncertainty.py`: Basic error propagation (Monte Carlo planned) for GHG confidence intervals.
- `activity_factors.py` & `gas_analysis.py`: Molecular weight normalization and hydrocarbon gas speciation.

## Key Backend Source Files

- `new/server/app.py` (716 lines): App factory, extension configuration, blueprint registration.
- `new/server/models.py` (880 lines): SQLAlchemy declarative schema (29 models).
- `new/server/config.py` (183 lines): Environment configuration, database URLs, Redis params, secret keys.
- `new/server/background_processor.py` (3096 lines): In-process background processing batch importer and file processor.
- `new/server/calculations/dispatcher.py` (1189 lines): Scope 1/2/3 dispatcher logic and factor assignment.
- `new/server/routes/dashboard.py` (1272 lines): High-performance cached analytics queries and rollups.
- `new/server/routes/emissions.py` (1194 lines): Core CRUD and lifecycle endpoints for emissions data.
- `new/server/routes/auth.py` (733 lines): RBAC security, session handling, user credentials.
