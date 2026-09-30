# AUDIT SCOPE — GHG Accounting & Reporting Platform

Audit started 2026-09-25. Lead auditor: Claude (Opus 5.5) with 12 specialist workstreams (A–L).
Mode: **discovery only.** No application source, test, or live-database changes.

## 0. Audited baseline

| Item | Value |
|---|---|
| Git commit | see `audit/BASELINE_COMMIT.txt` (branch `main`) |
| Uncommitted working tree | **Audited as-is.** Full diff is in `audit/baseline_uncommitted.diff`; file list in `audit/baseline_status.txt`. It touches calculation-engine files (`combustion.py`, `dispatcher.py`, `constants.py`, `uncertainty.py`, `units.py`, `vented.py`, …) and UI pages. |
| Data | Read-only SQLite backup of `new/server/ghg_app.db`, saved as `audit/db/snapshot_original.db`. Each workstream works on its own copy (`audit/db/<agent>.db`). The live DB is never written. |
| Snapshot contents | 744 Scope 1 emissions, 37 Scope 2, 28 Scope 3, 974 production rows, 170 facilities, 101 custom factors, 3 SBTi targets, 1 base year, 100 OGMP surveys, 200 CAP rows, 15 users |
| Isolated runtime | Backend: `python app.py` on **:5055** (DB `audit/db/browser.db`). Frontend: real client source served by Vite on **:5190** (`audit/tools/vite_audit.mjs`), proxying `/api` to :5055. The user's own servers on :5000, :5173 and :5174 are untouched. |
| Browser | Playwright with the local Chromium 1208 (headless). No browser MCP tool is available in this session. |
| Harness | `audit/tools/auditlib.py`: per-agent DB copy, logged-in in-process API client per role, direct SQL. `audit/tools/report_bug.py` appends findings with atomic, locked BUG-ID allocation. |
| Audit accounts | `audit_{admin,superuser,user,itadmin}@audit.local` / `AuditPass!2026` (exist only in the audit DB copies) |

## 1. Architecture (verified from source)

- **Backend** — `new/server`, Flask 3, module-level `app` in `app.py`.
  - 17 blueprints with about 190 endpoints. Largest: `emissions.py` (4860 lines), `dashboard.py` (3172), `managedata.py` (1082), `reports.py` (1393), `qaqc.py`.
  - SQLAlchemy models in `models.py`. The schema is created by `db.create_all()` at import; Alembic holds only 2 revisions.
  - SQLite in WAL mode by default, Postgres optional.
- **Auth** — session cookie plus Flask-WTF CSRF (`/api/csrf-token`, `X-CSRFToken` header).
  - Roles: `user`, `it`, `superuser`, `admin`, `it_admin`, `it_manager`.
  - Decorators live in `routes/auth.py`. Facility scoping uses `utils.get_allowed_facility_ids` and `utils.require_facility_access`.
- **Calculation engine** — `calculations/`.
  - Entry point: `compute_emissions` (`legacy_engine.py`). It calls `dispatcher.dispatch` (`dispatcher.py`, API Compendium 2021 calculators) and falls back to the legacy `GHGCalculator` factor math.
  - Supporting modules: `units.py` (conversions, gas volume normalisation, Scope 3 CO2e), `constants.py` (GWP AR4/AR5/AR6, 100/20-yr), `uncertainty.py` (tiers, IPCC propagation, SRSS, Monte Carlo), `anomaly.py`.
- **Reference data** — `emission_factors.py`, `emission_factors_api2021.py`, `electricity_factors.py`, the `custom_factors` table, `/api/emission-factors*`. The client also carries its own catalogs: `utils/EmissionFactors.js`, `constants/officialFuelPresets.js`, `constants.js`.
- **Bulk ingestion** — `background_processor.py` (thread per job, in-memory `upload_jobs`). Handles Scope 1/2/3, production, sources, mitigation, custom factors and facilities.
- **Frontend** — React 19 + Vite. The axios instance is `src/api.js`.
  - Routes: dashboard, emissions, manage-data, qa-dashboard, reports, carbon-intensity, methane-intensity, methane-explorer, sbti, uncertainty, reference-data, diagnostics, audit-trail, user-management, settings.
  - The client performs its own calculations and PDF generation: `Scope1Form.jsx` (3023 lines), `Scope2Form`, `Scope3Form`, the `scope1/*Form.jsx` process forms, `ModernReportGenerator.js`, `MethaneIntensity.jsx`, `CarbonIntensity.jsx`, `SbtiDashboard.jsx`, `UncertaintyAssessment.jsx`.
- **Tests** — about 55 pytest modules in `new/server/tests`, 2 vitest files, 9 Playwright specs. None of them is trusted as proof of correctness.

## 2. Application areas → workstream ownership

| Area | Primary | Secondary |
|---|---|---|
| Authentication, authorization/RBAC, facility scoping, security | I (Backend) | K, L |
| Organization / facility management, equity, CAP | I | J |
| Activity data entry (Scope 1/2/3 forms, bulk import) | B (Emissions) | K, L |
| Emission factors / reference data / custom factors / tiers | C (Tier/Factor) | A |
| Calculation engine (every process pathway) | A (Calculation) | B, C |
| Scope 1 / Scope 2 / Scope 3 classification and aggregation | B | F |
| Methane (CH4 mass, CO2e, % loss, methane intensity, explorer, OGMP) | D (Methane) | F |
| Carbon intensity (all intensity metrics, production denominators) | E (Carbon intensity) | F |
| Dashboards, KPI cards, charts, filters | F (Dashboard) | L |
| Uncertainty (per-record, aggregate, page) | G (Uncertainty) | F |
| SBTi (targets, base year, trajectory, page) | H (SBTi) | F |
| Reports / exports / PDF | F | K |
| Date/year logic, filters | F | E, H |
| Backend/API validation, errors, pagination, concurrency, idempotency | I | J |
| Database schema, precision, integrity, migrations, orphans | J (Database) | — |
| Frontend/UI (forms, units, rounding, state, empty/error states) | K (UI) | L |
| Real browser workflows | L (Browser) | K |
| Performance | I | J |

## 3. Calculation inventory (module level; per-calculation detail in Appendix A)

| # | Process / source | Scope | Gases | Code (server) | Client-side counterpart |
|---|---|---|---|---|---|
| 1 | Stationary / mobile combustion (Tier 1 catalog, Tier 2 custom, Tier 3 composition/carbon content) | 1 | CO2, CH4, N2O | `combustion.py:CombustionCalculator`, `convert_factor_to_kg_per_unit`; legacy `GHGCalculator.calculate_default_kg / convert_factor_to_kg / calculate_energy` | `scope1/CombustionForm.jsx`, `Scope1Form.jsx`, `utils/EmissionFactors.js`, `officialFuelPresets.js` |
| 2 | Flaring (routine / non-routine / safety; DRE, composition) | 1 | CO2, CH4, N2O | `combustion.py:FlaringCalculator`; dashboard `/flaring-summary` | Scope1Form, DashboardEnhanced flaring panel |
| 3 | Venting: blowdown | 1 | CH4, CO2 | `vented.py:BlowdownCalculator` | Scope1Form |
| 4 | Tank flashing / working / breathing | 1 | CH4, CO2 | `vented.py:TankFlashingCalculator` | `scope1/TankForm.jsx` |
| 5 | Pneumatic devices | 1 | CH4, CO2 | `vented.py:PneumaticDeviceCalculator` | Scope1Form |
| 6 | Well completions / flowback | 1 | CH4, CO2 | `vented.py:CompletionFlowbackCalculator`; legacy `calculate_completions` | `scope1/CompletionsForm.jsx` |
| 7 | Liquids unloading | 1 | CH4, CO2 | `vented.py:LiquidsUnloadingCalculator`; legacy `calculate_unloading` | Scope1Form |
| 8 | Drilling / mud degassing | 1 | CH4 | `vented.py:MudDegassingCalculator` | Scope1Form |
| 9 | Component fugitives (counts × EF) | 1 | CH4, CO2 | `fugitive.py:ComponentFugitiveCalculator`; legacy `ef_fugitive_average / ef_fugitive_screening_range / ef_fugitive_pipeline` | Scope1Form |
| 10 | Equipment / segment fugitives (wellhead, separator, gathering, processing, transmission, refinery, distribution, LNG) | 1 | CH4, CO2 | `fugitive.py:EquipmentFugitiveCalculator` | Scope1Form |
| 11 | Compressor seals | 1 | CH4 | `fugitive.py:CompressorSealCalculator` | Scope1Form |
| 12 | Acid gas removal | 1 | CO2, CH4 | `midstream.py:AGRCalculator` | `scope1/AGRForm.jsx` |
| 13 | Glycol dehydrators | 1 | CH4, CO2 | `midstream.py:DehydratorCalculator` | `scope1/DehydratorForm.jsx` |
| 14 | Stoichiometric process emissions (chemical production, asphalt blowing) | 1 | CO2 | `stoichiometry.py:StoichiometricCalculator` | Scope1Form |
| 15 | Nitric / adipic acid | 1 | N2O | `stoichiometry.py:NitricAcidCalculator` | `scope1/NitricAcidForm.jsx` |
| 16 | Indirect steam / heat; cogeneration allocation | 2 / 1 | CO2, CH4, N2O | `indirect.py:IndirectSteamCalculator, CogenAllocationCalculator` | Scope2Form |
| 17 | Purchased electricity (location- and market-based) | 2 | CO2e | `routes/scope2.py`, `electricity_factors.py`, `background_processor._process_row_scope2` | `Scope2Form.jsx` |
| 18 | Scope 3 (15 categories; spend/EEIO, activity, supplier-specific) | 3 | CO2e | `units.compute_scope3_co2e`, `routes/scope3.py`, `background_processor._process_row_scope3(_eeio)` | `Scope3Form.jsx` |
| 19 | CO2e aggregation and GWP (AR4/5/6, 100/20-yr; global GWP recalculation) | all | — | `units.calculate_co2e`, `constants.get_active_gwp`, `auth.recalculate_all_emissions_gwp` | `constants.js`, GWP-100/20 toggle |
| 20 | Unit conversions (volume, mass, energy, temperature, pressure, standard gas conditions) | all | — | `units.py` (`CONVERSIONS`, `convert`, `normalize_gas_volume_to_standard`, …), `dispatcher._normalize_volume` | client form converters |
| 21 | Uncertainty (per-gas, tier-based, IPCC Approach 1 product/sum, SRSS inventory, Monte Carlo) | all | — | `uncertainty.py`, `base.calculate_uncertainty`, dashboard `/uncertainty` | `UncertaintyAssessment.jsx` |
| 22 | Carbon intensity (kg CO2e/boe etc., facility/corporate, trend) | 1+2 | — | dashboard `/intensity-stats`, `/intensity-trend`, `/summary` | `CarbonIntensity.jsx`, dashboard KPI |
| 23 | Methane intensity / % methane loss / OGMP 2.0 reconciliation | 1 | CH4 | dashboard routes, `services/ogmp.py`, `routes/satellite.py`, `services/sentinel5p.py` | `MethaneIntensity.jsx`, `MethaneExplorer.jsx` |
| 24 | SBTi targets / trajectory / progress | 1+2(+3) | — | dashboard `/sbti-trajectory`, managedata `/sbti`, base year tables | `SbtiDashboard.jsx` |
| 25 | Net emissions / mitigation, flaring intensity (Decree 21-330) | 1 | — | dashboard routes, mitigation tables | DashboardEnhanced |
| 26 | Equity-share / JV consolidation, CAP limits | all | — | `equity_routes.py`, `cap_routes.py` | — |
| 27 | Anomaly detection | 1/2/3 | — | `anomaly.py` | QA dashboard |
| 28 | Report totals (server PDF and client PDF) | all | — | `routes/reports.py` (reportlab) | `ModernReportGenerator.js` |

## 4. Initial observations that need explanation (seeded to workstreams)

Seen on the first browser load of `/dashboard` as audit admin, all filters at "All":
- Gross Scope 1+2 = **3.7T tCO2e**; 128 pending records = **4,686,441,566,968.31 tCO2e**; intensity **627.53K kg/BOE**; CH4 **84.3M t**. These could be data or code; that is not yet determined.
- Flaring panel: total 100 kNm³ = 210.2 tCO2e, but the three sub-category cards show 0 tCO2e each.

## Appendix A — Per-calculation detail

Maintained by Agent A (Calculation Engine Auditor). Each row gives: process · scope · gas · methodology · tier · inputs · units · conversions · formula · factors/constants · intermediates · output · persistence · endpoint · UI · tests.

**Status: not completed.** Agent A (Calculation Engine) was stopped by usage limits and then placed out of scope by the
user ("continue the audit without the emission calculation") before this appendix was written. The module-level inventory
in §3 is complete. Per-calculation detail exists only for the pathways covered by confirmed bugs (see BUG-011, 012, 023, 024,
027, 047, 048, 049, 050, 051, 063, 066, 090, 091, 096, 097, 110 in `AUDIT_FINDINGS.md`).

## Appendix B — Scope changes during the audit

| When | Change | Effect |
|---|---|---|
| 2026-09-25 ~15:19–15:32 and ~22:48–22:54 | Calculation engine and client forms edited outside the audit | Baseline re-pinned: `audit/baseline2_uncommitted.diff`; all repros re-run against final code |
| 2026-09-25 | Agent E (carbon intensity) stopped by the user | Intensity metrics not reached by E are unverified |
| 2026-09-26 ~00:55 | User: continue without the emission calculation | Agents A, C not resumed; B, D, K, L restricted to non-formula checks |
| 2026-09-26 | BUG-100–104 appended by an external process ("API GHG Compendium Section 6 Auditor") | Not verified by this audit; excluded from the plan pending triage |
