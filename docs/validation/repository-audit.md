# Complete Repository Audit & Architecture Baseline

**Platform**: Greenhouse Gas (GHG) Accounting, Emissions Analytics, MRV and Reporting Platform  
**Repository**: `https://github.com/kaljah/kaljah.github.io`  
**Audit Date**: September 20, 2026  
**Status**: ACTIVE / REMEDIATED  
**Audit Scope**: Full Stack (Backend, Frontend, Calculation Engine, Database Models, Test Infrastructure, Data Ingestion, CI/CD)

---

## 1. System Architecture Overview

The platform is designed as an enterprise MRV (Measurement, Reporting, and Verification) system for greenhouse gas accounting across upstream, midstream, and downstream industrial facilities, compliant with API Compendium (2021), GHG Protocol, IPCC Guidelines, and OGMP 2.0.

```
┌────────────────────────────────────────────────────────────────────────┐
│                        React 19 + Vite Frontend                        │
│   (Dashboard, Emissions Entry, Batch Review, Reports, Methane Explorer)│
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ REST API / JSON (Axios, CSRF)
┌───────────────────────────────────▼────────────────────────────────────┐
│                    Flask 3.0.3 Web Application Layer                   │
│   (Routes: emissions, scope2, scope3, managedata, dashboard, reports)  │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
       ┌────────────────────────────┼────────────────────────────┐
       ▼                            ▼                            ▼
┌──────────────┐          ┌───────────────────┐        ┌─────────────────┐
│ Auth & RBAC  │          │   Async Worker    │        │  Audit Logger   │
│  (Session,   │          │ (Threaded Ingest, │        │ (activity_log,  │
│  Role check, │          │  CSV/XLSX Bulk)   │        │  diff tracking, │
│  Facility RLS│          │                   │        │  notifications) │
└──────┬───────┘          └─────────┬─────────┘        └────────┬────────┘
       │                            │                           │
       └────────────────────────────┼───────────────────────────┘
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                 Authoritative Calculation Engine                       │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │    CalculationDispatcher (new/server/calculations/dispatcher.py) │  │
│  └──────┬────────────────────────────────────────────────────┬──────┘  │
│         │                                                    │         │
│         ▼                                                    ▼         │
│  ┌───────────────┐ ┌───────────────┐ ┌────────────────┐ ┌───────────┐  │
│  │ Combustion &  │ │ Vented & Proc │ │ Fugitive Leaks │ │ Midstream │  │
│  │ Flaring (Sec5)│ │ (Section 6)   │ │  (Section 7)   │ │  (Sec 6/8)│  │
│  └───────────────┘ └───────────────┘ └────────────────┘ └───────────┘  │
│  ┌───────────────┐ ┌───────────────┐ ┌────────────────┐ ┌───────────┐  │
│  │ Indirect &    │ │ Stoichiometry │ │ Thermodynamic  │ │Analytical │  │
│  │ Scope 2 (CHP) │ │ Mass Balance  │ │ Units & GWP    │ │Uncertainty│  │
│  └───────────────┘ └───────────────┘ └────────────────┘ └───────────┘  │
└───────────────────────────────────┬────────────────────────────────────┘
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│               Relational Database (SQLAlchemy 3 / SQLite / Postgres)   │
│    (emissions, scope2_emissions, scope3_emissions, facilities, users)  │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Active Calculation Paths

All operational GHG emissions calculations are orchestrated by `CalculationDispatcher` located in `new/server/calculations/dispatcher.py`. The dispatcher resolves 42 distinct process aliases and routes them to dedicated calculator classes:

| Process Subsystem | Implementation File | Primary Calculator Class | Standard Citation |
| :--- | :--- | :--- | :--- |
| **Stationary Combustion** | `new/server/calculations/combustion.py` | `CombustionCalculator` | API Compendium 2021 §5.1, Tables 5-1 to 5-10 |
| **Flaring (Dual-Efficiency)** | `new/server/calculations/combustion.py` | `FlaringCalculator` | API Compendium 2021 §5.2, Table 5-11 |
| **Mud Degassing & Drilling** | `new/server/calculations/vented.py` | `MudDegassingCalculator` | API Compendium 2021 §6.1 |
| **Completion Flowback** | `new/server/calculations/vented.py` | `CompletionFlowbackCalculator` | API Compendium 2021 §6.2 |
| **Liquids Unloading** | `new/server/calculations/vented.py` | `LiquidsUnloadingCalculator` | API Compendium 2021 §6.3 |
| **Vessel Blowdown & Venting** | `new/server/calculations/vented.py` | `BlowdownCalculator` | API Compendium 2021 §6.4 |
| **Storage Tanks (Flash & Working)** | `new/server/calculations/vented.py` | `TankFlashingCalculator` | API Compendium 2021 §6.7, Table 6-7 |
| **Pneumatic Devices & Pumps** | `new/server/calculations/vented.py` | `PneumaticDeviceCalculator` | API Compendium 2021 §6.8 |
| **Component Fugitives** | `new/server/calculations/fugitive.py` | `ComponentFugitiveCalculator` | API Compendium 2021 §7.1 |
| **Equipment Fugitives (Screening)**| `new/server/calculations/fugitive.py` | `EquipmentFugitiveCalculator` | API Compendium 2021 §7.2 |
| **Compressor Seals (Wet & Dry)** | `new/server/calculations/fugitive.py` | `CompressorSealCalculator` | API Compendium 2021 §7.3 |
| **Acid Gas Removal (AGR)** | `new/server/calculations/midstream.py` | `AGRCalculator` | API Compendium 2021 §6.5, Table 6-5 |
| **Glycol Dehydrators** | `new/server/calculations/midstream.py` | `DehydratorCalculator` | API Compendium 2021 §6.6 |
| **Indirect Steam & Heat** | `new/server/calculations/indirect.py` | `IndirectSteamCalculator` | GHG Protocol Scope 2 Guidance |
| **CHP Cogeneration Allocation** | `new/server/calculations/indirect.py` | `CogenAllocationCalculator` | GHG Protocol Scope 2 Guidance §6 |
| **Chemical Stoichiometry / SMR** | `new/server/calculations/stoichiometry.py` | `StoichiometricCalculator` | Stoichiometric Mass Balance |
| **Scope 2 Grid & Market** | `new/server/routes/scope2.py` | Route Controller | GHG Protocol Scope 2 Standard |
| **Scope 3 Value Chain (Cat 1-15)** | `new/server/calculations/units.py` | `compute_scope3_co2e` | GHG Protocol Scope 3 Standard |
| **Uncertainty Propagation** | `new/server/calculations/uncertainty.py` | `propagate_uncertainty` | IPCC 2006 Vol. 1 Ch. 3 / GUM $k=2$ |
| **OGMP 2.0 Level & Reconciliation**| `new/server/services/ogmp.py` | `compute_facility_ogmp_level` | OGMP 2.0 Guidance 2021 |

---

## 3. Inactive, Legacy & Duplicate Calculation Paths

During the audit, several legacy, duplicate, and transitional components were identified:

### 3.1 `new/server/calculations/legacy_engine.py` (Facade & Legacy Fallback)
- **Status**: HYBRID / PASS-THROUGH.
- **Role**: `legacy_engine.py` exports `compute_emissions(payload, factor_data, ...)`. Lines 428–448 attempt routing to `api2021_dispatcher.dispatch(...)` first. If the dispatcher successfully returns results, the dispatcher's output is returned.
- **Risk**: If dispatcher returns 0 or does not recognize a legacy process name, execution falls through to lines 450–905 which contain legacy hand-coded formulas. 
- **Action**: All production routes (`emissions.py`, `background_processor.py`) have been aligned with standard process keys so the primary dispatcher handles all valid input payloads.

### 3.2 Obsolete Scratch Scripts & Archive Files
- Root-level Node/Electron prototype remnants: `package.json` at root mentions `main.js`, `server.js`, `electron`, and `express`, while the actual production frontend lives in `new/client/` and backend in `new/server/`.
- Compressed binary archives: `new/server.rar` and `new/server/calculations/calculations.rar` are dormant binary archives.
- Deprecated patch scripts in root: `patch.py`, `patch_ci.py`, `patch_ci_css.py`, `patch_manage_data.py`, `patch_manage_data_ui.py`, `patch_ui.py`, `fix_ui.py`, `fix_ui_2.py`, `fix_ui_tab.py`, `old_ManageData.jsx`.
- In-tree client patch scripts: `new/client/src/components/patch_s3.py`, `new/client/src/components/patch_s3_form.py`.
- **Verdict**: These files are inert, have no active imports in `new/server` or `new/client`, and must remain excluded from production builds.

---

## 4. Data Sources & Storage Models

The system persists data via SQLAlchemy declarative models defined in `new/server/models.py`:

| Model Name | Primary Keys & Indexes | Description |
| :--- | :--- | :--- |
| `Emission` | `id`, `ix_emissions_fac_yr_status`, `ix_emissions_yr_status_proc` | Scope 1 direct emissions by process, activity, fuel, CO2, CH4, N2O, and CO2e. |
| `Scope2Emission` | `id`, `ix_scope2_fac_yr_status`, `ix_scope2_status_yr_co2e` | Scope 2 indirect emissions (electricity, steam, heat, cooling) with location/market factors. |
| `Scope3Emission` | `id`, `facility_id`, `year`, `status` | Scope 3 value chain emissions with category (1–15), activity data, and spend/mass EF. |
| `Facility` | `id`, `name`, `region`, `location`, `code` | Facility hierarchy, operating status, reconciliation threshold, and location metadata. |
| `ProductionData` | `id`, `facility_id`, `month`, `year` (unique constraint) | Monthly crude oil (bbl) and natural gas (mscf) production for intensity normalization. |
| `EmissionSource` | `id`, `code` (unique), `facility_id` | Equipment registry, fuel type, design capacity, and installation records. |
| `CustomFactor` | `id`, `name`, `parent_fuel`, `unit` | User-defined Tier 2 emission factors with gas split, uncertainty percentage, and usage flags. |
| `OgmpSurvey` | `id`, `facility_id`, `survey_date`, `survey_type` | Level 4/5 top-down aerial/drone/satellite surveys with annualized rate ($t\text{CH}_4/\text{yr}$). |
| `ActivityLog` | `id`, `action`, `user_id`, `timestamp` | Immutable audit log recording before/after JSON diffs, user ID, IP address, and metadata. |
| `SystemSetting` | `id`, `key` (unique), `value` | Global configuration: authoritative GWP standard (`AR5`/`AR6`), Copernicus credentials. |

---

## 5. Test Infrastructure Audit

The repository contains a multi-tiered test infrastructure:

- **Runner**: `pytest 9.1.1` configured via `new/server/pytest.ini` with plugins `hypothesis 6.168.0`, `mock 3.15.1`, and `benchmark 5.2.3`.
- **Database Isolation**: `new/server/tests/conftest.py` spins up an in-memory SQLite database (`sqlite:///:memory:`) with session teardown per test function.
- **Validation Batteris**:
  - `validation/regression/test_regression_archive.py`: 9 verified historical fixes (B1-B14, L1).
  - `new/server/tests/test_independent_differential.py`: 16 differential tests comparing production vs reference model.
  - `new/server/tests/test_golden_dataset_validation.py`: 25 golden vectors across all statutory processes.
  - `new/server/tests/test_unit_conversions_exhaustive.py`: 277 conversion round-trip and transitivity tests.
  - `new/server/tests/test_property_invariants.py`: 6 property invariant tests using Hypothesis.
  - `new/server/tests/test_emission_factor_selection.py`: 10 factor resolution tests.
  - `new/server/tests/test_boundary_and_negative.py`: 13 resilience and boundary condition tests.
  - `new/server/tests/test_aggregation_reconciliation.py`: 6 hierarchy rollup and OGMP reconciliation tests.
  - Specialized subsystem batteries: Midstream, Stoichiometry, Anomaly detection, Fugitives, GWP horizons, Concurrency stress.
- **Master Orchestrator**: `validation/scripts/run_full_validation_suite.py` executing all 14 validation batteries with aggregated timing and metrics.

---

## 6. Dependency & Security Posture

### 6.1 Backend Dependencies (`new/server/requirements.txt`)
- `Flask==3.0.3`, `Werkzeug>=3.0.6`, `Flask-Cors>=5.0.0`
- `Flask-SQLAlchemy>=3.1.0`, `SQLAlchemy>=2.0.0`
- `Flask-WTF>=1.2.0` (CSRF protection)
- `Flask-Limiter>=3.5.0` (Rate limiting)
- `cachetools>=5.3.0` (In-memory caching)
- `requests>=2.31.0`
- `gunicorn>=21.2.0`, `psycopg2-binary>=2.9.9`
- `openpyxl>=3.1.0`, `reportlab>=4.0.0` (Export generation)

### 6.2 Frontend Dependencies (`new/client/package.json`)
- `react@19.2.0`, `react-dom@19.2.0`
- `vite@7.2.4`, `react-router-dom@7.13.0`
- `axios@1.13.5` (Configured with cookie sessions and `X-CSRFToken`)
- `chart.js@4.5.1`, `recharts@3.7.0`
- `tailwindcss@4.1.18`, `lucide-react@0.563.0`

### 6.3 Security Hardening Verified
- **Maker-Checker Protocol**: Non-admin manual entries and all bulk uploads queue as `Pending`; only admins can verify records into official dashboards.
- **Role-Based Access Control (RBAC)**: IT Administrators are blocked from reading or altering operational emissions data (Segregation of Duties).
- **Facility-Level Scoping (RLS)**: Users restricted to assigned regional facilities cannot view or modify other facilities.
- **SQL & CSV Formula Injection**: Wildcard characters escaped in LIKE queries (`_escape_like`); CSV string values beginning with `=`, `+`, `-`, `@` prefixed with quote.

---

## 7. Potential Calculation Duplication & Conflicting Implementations

1. **Frontend vs Backend Precision**:
   - `new/client/src/utils/formatters.js` formats emissions to 3 decimal places for display (`formatNumber(v, 3)`).
   - Database stores full floating point / double precision numbers in metric tonnes.
   - Finding: Client-side rounding is display-only; calculations performed on the backend preserve full IEEE-754 precision.
2. **GWP Regulatory Harmonization**:
   - Global standard is strictly dictated by `SystemSetting` (`AR5` default: $\text{CH}_4=28, \text{N}_2\text{O}=265$; `AR6`: $\text{CH}_4=27.9, \text{N}_2\text{O}=273$).
   - Per-user preferences are display-only and cannot alter persisted emissions.
3. **Scope 3 Implementation Boundary**:
   - Platform implements generalized Tier 1/2 factor calculation across all 15 categories, not 15 bespoke models. This is mathematically sound for corporate inventories but requires transparent disclosure.
