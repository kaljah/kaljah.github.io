# Graph Report - H2  (2026-09-14)

## Corpus Check
- 263 files · ~587,814 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 2114 nodes · 4427 edges · 209 communities (156 shown, 53 thin omitted)
- Extraction: 92% EXTRACTED · 8% INFERRED · 0% AMBIGUOUS · INFERRED: 344 edges (avg confidence: 0.52)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `0b21e68a`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- emissions.py
- dashboard.py
- Scope1Form.jsx
- route
- GHGCalculator
- calculate_co2e
- dependencies
- devDependencies
- App.jsx
- app.py
- useToast
- get_current_user
- test_uncertainty.py
- Emission
- extract_val
- audit.py
- test_satellite.py
- test_tier_scope_kpi_numerical.py
- pages/ManageData.jsx
- CalculationDispatcher
- .get_token
- Sentinel5PService
- test_audit.py
- dependencies
- qaqc.py
- Scope1ImportWizard.jsx
- AnomalyDetector
- Backend (Server)
- auth.py
- log_activity_and_notify
- combustion.py
- bulk_resolve
- QADashboard.jsx
- Frontend (Client)
- Emissions.jsx
- Tasks: [FEATURE NAME]
- test_qaqc_diagnostics.py
- TestEdgeCases
- srss_inventory
- ModernReportGenerator.js
- satellite.py
- Project Metadata
- build
- env.py
- TestUnitConversions
- Desktop App Dev Tools
- TestTier1DrillingMud
- files
- TestTier1Flaring
- TestTier1Combustion
- NPM Scripts
- Pitch Deck Builder
- DashboardEnhanced.jsx
- combine_uncertainties_sum
- class-variance-authority
- Graphify Workflow Tools
- Tasks: [FEATURE NAME]
- Feature Specification: QA/QC Module (IPCC & ISO 14064 Compliant)
- Platform Documentation
- API and UI Routes
- User
- AUDIT MEMORY (living document)
- GHGUser
- CBAM Savings Chart
- Competitive Matrix Chart
- Industry Intensity Chart
- Market Sizing Chart
- Reporting Risks Chart
- Dashboard UI Entry
- Docker Configuration
- Platform Assets
- Frontend Entrypoint
- Facility Imagery
- Vite Assets
- Python Requirements
- models.py
- login_required
- TestTier3PneumaticDevices
- Feature Specification: Batch Approve/Reject Pending Records
- background_processor.py
- new/.specify/scripts/powershell/common.ps1
- .specify/scripts/powershell/common.ps1
- Facility
- Feature Specification: [FEATURE NAME]
- Feature Specification: [FEATURE NAME]
- get_allowed_facility_ids
- Implementation Tasks: QA/QC Module (IPCC & ISO 14064)
- to_psia
- .test_scope2_cogen_allocation_wri_efficiency_and_energy_methods
- Core Principles
- Core Principles
- Core Principles
- Core Principles
- client/package.json
- .dispatch
- TestUnauthenticatedAccess
- Implementation Tasks: Batch Approve/Reject Pending Records
- Implementation Plan: [FEATURE]
- Implementation Plan: [FEATURE]
- Existing Entities to Modify
- framer-motion
- BaseCalculator
- .test_scope2_indirect_steam_thermodynamic_equation
- status.py
- test_emission_calculations.py
- generate_1k_comprehensive.py
- new/.specify/scripts/powershell/create-new-feature.ps1
- .specify/scripts/powershell/create-new-feature.ps1
- [CHECKLIST TYPE] Checklist: [FEATURE NAME]
- [CHECKLIST TYPE] Checklist: [FEATURE NAME]
- Research & Design Decisions: Batch Approve/Reject
- Research & Design Decisions: QA/QC Module (IPCC & ISO 14064)
- .test_zero_emission_uncertainty_bounds
- formik
- chart.js
- papaparse
- react
- react-dom
- tailwind-merge
- @vitejs/plugin-react
- File-by-File Analysis
- jspdf-autotable
- .test_scope2_location_based_grid_averages
- .test_scope2_market_based_contractual_instruments
- .test_scope3_tier1_spend_based_eeio
- combine_uncertainties_product
- .test_scope3_tier2_average_data_transport
- .test_scope3_category11_use_of_sold_products_oil_and_gas
- 001-batch-approve-reject/data-model.md
- 001-batch-approve-reject/quickstart.md
- 002-qa-qc-ipcc-iso14064/quickstart.md
- test_audit_remediation.py
- .test_boe_production_normalization_exactness
- .test_carbon_intensity_metric_equations
- .test_methane_loss_rate_ogmp_equation
- .test_flaring_rate_percentage_equation
- .test_epa_wec_part99_fee_schedules_and_thresholds
- .test_coverage_factor_and_non_negative_bounds
- NotificationCenter.jsx
- sqlite3
- .test_scope3_tier3_supplier_specific_pcf
- reports.py
- TestTier3LiquidsUnloading
- .test_bidirectional_conversions_exactness
- .test_confidence_interval_bounds_ordering
- .test_scope1_tier1_and_tier3_pneumatic_bleed

## God Nodes (most connected - your core abstractions)
1. `login_required()` - 131 edges
2. `get_current_user()` - 104 edges
3. `Backend (Server)` - 74 edges
4. `CalculationDispatcher` - 72 edges
5. `get_allowed_facility_ids()` - 71 edges
6. `Frontend (Client)` - 66 edges
7. `User` - 62 edges
8. `log_activity_and_notify()` - 57 edges
9. `Facility` - 54 edges
10. `Emission` - 52 edges

## Surprising Connections (you probably didn't know these)
- `Methane Intensity Analytics UI` --conceptually_related_to--> `Emission Calculation Engines`  [INFERRED]
  deck_assets/ui_methane.png → README.md
- `seed_data()` --calls--> `User`  [INFERRED]
  seed_demo_data.py → new/server/models.py
- `seed_data()` --calls--> `Facility`  [INFERRED]
  seed_demo_data.py → new/server/models.py
- `ManageDataInner()` --indirect_call--> `f()`  [INFERRED]
  new/client/src/pages/ManageData.jsx → temp_old/CarbonIntensity.jsx
- `seed_data()` --calls--> `Emission`  [INFERRED]
  seed_demo_data.py → new/server/models.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Graphify Tooling and Documentation** — agents_rules_graphify, agents_workflows_graphify, agents_rules_graphify_cli, agents_rules_graphify_mcp [EXTRACTED 1.00]
- **Emission Calculation & Visualization Flow** — new_server_calculations, deck_assets_ui_dashboard, deck_assets_chart_industry_emissions [INFERRED 0.80]

## Communities (209 total, 53 thin omitted)

### Community 0 - "emissions.py"
Cohesion: 0.08
Nodes (42): Notification, forgot_password(), User triggers a password reset request. Creates a notification for the IT Role…, add_bulk_upload(), add_emission(), approve_batch_emissions(), approve_emission(), bulk_delete_emissions() (+34 more)

### Community 1 - "dashboard.py"
Cohesion: 0.07
Nodes (46): cached, BaseYear, BaseYearRecalculation, create_base_year_recalculation(), get_available_years(), get_base_year(), get_batch_dashboard_data(), get_categorical_breakdown() (+38 more)

### Community 2 - "Scope1Form.jsx"
Cohesion: 0.09
Nodes (23): CustomDropdown(), EmissionFactorOption(), AGRForm(), BlowdownForm(), CombustionForm(), HHV_REQUIRED_PROCESSES, CompletionsForm(), DehydratorForm() (+15 more)

### Community 3 - "route"
Cohesion: 0.06
Nodes (38): get_factor_by_process_category(), get_factor_by_segment(), get_factors_by_segment_and_category(), Emission Factors Database - API Compendium 2021 Complete catalog from Sections…, Returns all emission factors applicable to the given segment. Args: segment…, Returns all emission factors for the given process category. Args:…, Returns all emission factors for a specific segment and process category. Args:…, Emission Factors Database - API Compendium 2021 Comprehensive emission factors… (+30 more)

### Community 5 - "calculate_co2e"
Cohesion: 0.07
Nodes (36): Standard fuel-based combustion calculation with API §4.2.1 thermodynamic…, Standard Quantity * EF fallback with unit handling and tier-aware uncertainty., API Compendium 2021 - Section 7: Fugitive Emissions Implementation of equations…, API Section 7.2.3 - Compressor seals, Average Factor Method - counts * EF component_counts: dict of {type: count}, Average Factor Method for equipment - count * EF, API Compendium 2021 - Section 8: Indirect Emissions Implementation of indirect…, API Section 8.3 - Allocation of Cogeneration Emissions Methods: wri_efficiency,… (+28 more)

### Community 6 - "dependencies"
Cohesion: 0.09
Nodes (23): axios, clsx, jspdf, leaflet, lucide-react, dependencies, axios, clsx (+15 more)

### Community 7 - "devDependencies"
Cohesion: 0.07
Nodes (27): autoprefixer, eslint, @eslint/js, eslint-plugin-react-hooks, eslint-plugin-react-refresh, globals, devDependencies, autoprefixer (+19 more)

### Community 8 - "App.jsx"
Cohesion: 0.12
Nodes (25): AdminRoute(), AuditRoute(), AuditTrail, ITRoute(), MethaneIntensity, NonITRoute(), PrivateRoute(), ReferenceData (+17 more)

### Community 9 - "app.py"
Cohesion: 0.14
Nodes (16): errorhandler, listens_for, after_request(), before_request(), get_csrf_token(), health_check(), internal_error(), not_found_error() (+8 more)

### Community 10 - "useToast"
Cohesion: 0.09
Nodes (26): api, fetchCsrfToken(), App(), EmissionsMap, Reports, BatchReviewWizard(), detectAnomalies(), QUICK_REJECTION_REASONS (+18 more)

### Community 11 - "get_current_user"
Cohesion: 0.21
Nodes (25): Goal, MitigationProject, ReportingMetadata, add_base_year_recalculation(), add_mitigation(), add_or_update_goal(), add_source(), bulk_import_mitigation() (+17 more)

### Community 12 - "test_uncertainty.py"
Cohesion: 0.10
Nodes (21): admin_user(), client(), it_admin_user(), fixture, Test suite for /dashboard/uncertainty endpoint. Covers: auth, RBAC,…, Specifying year= returns that year in the response., scope=1 should only return Scope 1 categories (no Scope 2/3 groups)., export=csv should return text/csv with correct headers. (+13 more)

### Community 13 - "Emission"
Cohesion: 0.09
Nodes (24): run_all_scenarios(), Emission, admin_user(), app(), client(), login(), fixture, Security and integration tests for GHG Dashboard API. These test the HTTP layer… (+16 more)

### Community 14 - "extract_val"
Cohesion: 0.10
Nodes (10): extract_val(), Diesel Tier 1: quantity = 500 gal HHV = 138,700 Btu/gal → 500 × 138,700 /…, Flaring Tier 3 (factor_source='specific') — Dual efficiency model: gas_volume =…, Tank Tier 3: throughput = 2000 bbl/month GOR = 200 scf/bbl CH4 content = 45%…, Completions Tier 3 (metered_volume): flowback_volume = 50,000 m3 CH4 content =…, Extract the central value from a propagated uncertainty dict or bare float., TestTier1CombustionDiesel, TestTier3Completions (+2 more)

### Community 15 - "audit.py"
Cohesion: 0.40
Nodes (10): audit_access_required(), _build_audit_query(), export_audit_logs(), get_audit_filters(), get_audit_logs(), get_audit_stats(), route, Prevent CSV formula injection (DDE/Excel macro execution) including leading… (+2 more)

### Community 16 - "test_satellite.py"
Cohesion: 0.18
Nodes (10): Layer configuration returns ESA standard legend steps and unauthenticated…, Crucial policy test: Unconfigured / unauthenticated queries MUST return status…, Tests OAuth2 authentication flow with mock Copernicus Keycloak token endpoint., Verifies the physical 1D box model / mass-divergence plume flux estimation., Tests OAuth2 rejection handling., test_sentinel5p_connection_test_mocked_failure(), test_sentinel5p_connection_test_mocked_success(), test_sentinel5p_flux_calculation() (+2 more)

### Community 17 - "test_tier_scope_kpi_numerical.py"
Cohesion: 0.12
Nodes (54): CombustionCalculator, FlaringCalculator, ComponentFugitiveCalculator, CompressorSealCalculator, EquipmentFugitiveCalculator, CogenAllocationCalculator, IndirectSteamCalculator, AGRCalculator (+46 more)

### Community 18 - "pages/ManageData.jsx"
Cohesion: 0.13
Nodes (10): RFC-4180, ManageData, BOUNDARY_OPTIONS, DEFAULT_GWP, GWP_AR4, GWP_AR5, GWP_AR6, GWP_STANDARDS (+2 more)

### Community 19 - "CalculationDispatcher"
Cohesion: 0.08
Nodes (32): CalculationDispatcher, Routes a calculation request to the appropriate API 2021 calculator., Verify _require_fraction handles boundary values and percentages cleanly., Finding 1: Verify fugitive screening calculation handles component count and…, Finding 2: Verify AGR zero removal boundary condition does not create false 99%…, Finding 3: Verify _generic_calculation converts when factor denominator is scf,…, Finding 4: Verify liquid fuel uses ~138,000 Btu/gal HHV under mmbtu factor, not…, Finding 5: Verify factors in g/unit (e.g. g/kWh) are divided by 1,000,000 to… (+24 more)

### Community 20 - ".get_token"
Cohesion: 0.28
Nodes (5): Any, Retrieves a valid JWT access token from Copernicus CDSE with caching., Returns tile layer configuration, color ramps, and metadata for Leaflet., Queries Copernicus STAC/OData API for real Sentinel-5P methane data around…, Tests authentication against Copernicus Data Space Ecosystem Keycloak endpoint.…

### Community 21 - "Sentinel5PService"
Cohesion: 0.18
Nodes (6): Sentinel-5P (TROPOMI) Satellite Methane Service Connects to ESA Copernicus Data…, Service for querying ESA Copernicus Sentinel-5P TROPOMI methane measurements., Estimates methane mass emission rate (kg CH4/hr) from a Sentinel-5P column…, Sentinel5PService, Emission rate Q must scale linearly with delta_ppb and wind_speed., Zero or negative delta_ch4_ppb must return exactly 0.0 kg/hr.

### Community 23 - "test_audit.py"
Cohesion: 0.17
Nodes (6): admin_user(), client(), it_admin_user(), fixture, regular_user(), seed_audit_logs()

### Community 24 - "dependencies"
Cohesion: 0.13
Nodes (15): bcryptjs, body-parser, cors, express, express-rate-limit, dependencies, bcryptjs, body-parser (+7 more)

### Community 25 - "qaqc.py"
Cohesion: 0.21
Nodes (15): CustomFactor, Permits superuser and admin roles for data management operations. NOTE:…, superuser_required(), create_custom_factor(), delete_custom_factor(), import_custom_factors(), _parse_non_negative_float(), route (+7 more)

### Community 26 - "Scope1ImportWizard.jsx"
Cohesion: 0.06
Nodes (19): autoDetect(), FIELD_GROUPS, Icon, PROCESS_CATALOGUE, Scope1ImportWizard(), STEPS, autoDetect(), FIELD_GROUPS (+11 more)

### Community 27 - "AnomalyDetector"
Cohesion: 0.17
Nodes (8): AnomalyDetector, Check a Scope 1 CO2e value against the trailing 12 months strictly prior to the…, Checks a new emission value against historical data for the same facility and…, Check a Scope 2 CO2e value against the trailing 12 months strictly prior to the…, Check a Scope 3 CO2e value against the trailing 12 months strictly prior to the…, Compute Z-score of a value against a list of historical values. Returns…, If historical is constant and new value is identical, it must NOT flag., Sample size N < 3 must return insufficient_history without crashing.

### Community 28 - "Backend (Server)"
Cohesion: 0.03
Nodes (74): `add_indexes.py`, `app.py`, Backend (Server), `background_processor.py`, `benchmark_db.py`, `calculations\base.py`, `calculations\combustion.py`, `calculations\constants.py` (+66 more)

### Community 29 - "auth.py"
Cohesion: 0.12
Nodes (30): limit, admin_required(), admin_reset_password(), change_password(), delete_user(), get_settings(), get_users(), is_safe_image_url() (+22 more)

### Community 30 - "log_activity_and_notify"
Cohesion: 0.09
Nodes (48): LevelUpgradeLog, clear_dashboard_cache(), add_production(), bulk_import_production(), delete_cbam_export(), delete_ogmp_survey(), delete_production(), get_cbam_exports() (+40 more)

### Community 31 - "combustion.py"
Cohesion: 0.16
Nodes (10): convert_factor_to_kg_per_unit(), _normalize_unit_str(), API Compendium 2021 - Section 5: Combustion and Flaring Implementation of…, Dual-efficiency flaring model (API 5-3, 5-4) with API §4.2.1 thermodynamic…, normalize_gas_volume_to_standard(), API Compendium 2021 §4.2.1: Converts gas volume measured at actual/operating…, test_flaring_calculator_basic(), test_flaring_calculator_specific_c1_c10() (+2 more)

### Community 32 - "bulk_resolve"
Cohesion: 0.24
Nodes (11): bulk_resolve(), export_qaqc_report(), get_qaqc_dashboard(), _is_admin_or_superuser(), route, Returns True if the user has QA/QC viewing rights (admin or superuser roles)., Returns aggregated uncertainty (IPCC SRSS) and flagged anomaly records. Scoped…, Exports QA/QC anomaly data as a CSV file with scope and year filtering. Access:… (+3 more)

### Community 33 - "QADashboard.jsx"
Cohesion: 0.16
Nodes (4): Diagnostics, QADashboard, ErrorBoundary, QADashboard()

### Community 34 - "Frontend (Client)"
Cohesion: 0.03
Nodes (66): `api.js`, `App.jsx`, `components\BulkImportModal.jsx`, `components\CalculationDetails.jsx`, `components\charts\BarChart.jsx`, `components\charts\index.js`, `components\charts\LineChart.jsx`, `components\charts\PieChart.jsx` (+58 more)

### Community 35 - "Emissions.jsx"
Cohesion: 0.12
Nodes (17): Emissions, CalculationDetails(), autoDetectMapping(), ColumnMappingWizard(), Icons, STEPS, TEMPLATES, EmissionResult() (+9 more)

### Community 36 - "Tasks: [FEATURE NAME]"
Cohesion: 0.07
Nodes (26): Dependencies & Execution Order, Format: `[ID] [P?] [Story] Description`, Implementation for User Story 1, Implementation for User Story 2, Implementation for User Story 3, Implementation Strategy, Incremental Delivery, MVP First (User Story 1 Only) (+18 more)

### Community 37 - "test_qaqc_diagnostics.py"
Cohesion: 0.20
Nodes (10): admin_user(), client(), fixture, Test suite for /api/qaqc/dashboard unified diagnostics & QA/QC endpoint.…, Unauthenticated access must be rejected., Admin user receives unified uncertainty, diagnostics, and anomaly queue data., Export endpoint returns CSV with correct Content-Type., test_qaqc_dashboard_unified_payload() (+2 more)

### Community 38 - "TestEdgeCases"
Cohesion: 0.20
Nodes (5): Zero quantity should produce zero emissions without crash., Negative quantity must raise ValueError., 1 MMscf = 1,000,000 scf — result should match 1M scf calculation., If GOR=0 and EF=0, result should be zero (no flash gas)., TestEdgeCases

### Community 39 - "srss_inventory"
Cohesion: 0.33
Nodes (4): Aggregate uncertainty across multiple sources using SRSS Approach 1. Formula:…, srss_inventory(), SRSS uncertainty of independent sources must be less than or equal to linear…, IPCC Eq 3.3 / ISO 14064-1 SRSS Aggregation: U_inv = sqrt(sum((E_i * u_i)^2)) /…

### Community 40 - "ModernReportGenerator.js"
Cohesion: 0.36
Nodes (8): createChartImage(), fetchAllReportData(), generateModernPDF(), generateReportCharts(), loadImage(), NOTE: When regionId is an array (multi-select), do NOT send facility_id param —, THEME, toRgba()

### Community 41 - "satellite.py"
Cohesion: 0.24
Nodes (10): ActivityLog, OgmpSurvey, export_satellite_to_ogmp(), _get_user_copernicus_credentials(), Extracts Copernicus credentials from org-level SystemSetting / app settings…, Exports a verified Sentinel-5P observation anomaly into an OGMP Level 4/5 Top-…, Tests connection to the Copernicus Data Space Ecosystem (CDSE) using either…, test_copernicus_connection() (+2 more)

### Community 42 - "Project Metadata"
Cohesion: 0.22
Nodes (8): author, description, keywords, license, main, name, type, version

### Community 43 - "build"
Cohesion: 0.22
Nodes (9): build, appId, directories, productName, win, output, asar, icon (+1 more)

### Community 44 - "env.py"
Cohesion: 0.39
Nodes (7): get_engine(), get_engine_url(), get_metadata(), Run migrations in 'offline' mode. This configures the context with just a URL…, Run migrations in 'online' mode. In this scenario we need to create an Engine…, run_migrations_offline(), run_migrations_online()

### Community 46 - "Desktop App Dev Tools"
Cohesion: 0.29
Nodes (7): electron, electron-builder, nodemon, devDependencies, electron, electron-builder, nodemon

### Community 48 - "TestTier1DrillingMud"
Cohesion: 0.29
Nodes (3): Mud Degassing Tier 1 (water-based mud): mud_volume = 500 m3 EF (water-based) =…, Oil-based mud uses EF=0.35 kg/m3., TestTier1DrillingMud

### Community 49 - "files"
Cohesion: 0.29
Nodes (6): files, main.js, node_modules/**/*, public/**/*, server.js, users_v2.db

### Community 51 - "TestTier1Flaring"
Cohesion: 0.33
Nodes (3): Flaring Tier 1 (default factor_source → _generic_calculation): Uses API_FACTORS…, Tier 1 flaring falls through to generic EF-based calculation., TestTier1Flaring

### Community 52 - "TestTier1Combustion"
Cohesion: 0.20
Nodes (3): Same calculation using m3 input — should produce same result after conversion., Hand-calc for Natural Gas Tier 1: quantity = 10,000 scf HHV = 1,020 Btu/scf →…, TestTier1Combustion

### Community 53 - "NPM Scripts"
Cohesion: 0.33
Nodes (6): scripts, build:exe, start, start:electron, start:web, test

### Community 54 - "Pitch Deck Builder"
Cohesion: 0.40
Nodes (4): add_card(), add_header(), Adds standard Startup Algeria header banner with accent bar and title., Creates a modern rounded rectangular card container.

### Community 55 - "DashboardEnhanced.jsx"
Cohesion: 0.13
Nodes (16): CarbonIntensity, DashboardEnhanced, SbtiDashboard, BarChart(), LineChart(), DEFAULT_COLORS, PieChart(), SkeletonCard() (+8 more)

### Community 56 - "combine_uncertainties_sum"
Cohesion: 0.50
Nodes (3): combine_uncertainties_sum(), Combine relative uncertainties for E = A + B (additive, independent). Formula:…, IPCC Eq 3.2: u_total = sqrt((E1*u1)^2 + (E2*u2)^2) / (E1 + E2). Source 1: 1,000…

### Community 58 - "Graphify Workflow Tools"
Cohesion: 0.67
Nodes (4): Graphify Rules, Graphify CLI, Graphify MCP, Graphify Workflow

### Community 59 - "Tasks: [FEATURE NAME]"
Cohesion: 0.07
Nodes (26): Dependencies & Execution Order, Format: `[ID] [P?] [Story] Description`, Implementation for User Story 1, Implementation for User Story 2, Implementation for User Story 3, Implementation Strategy, Incremental Delivery, MVP First (User Story 1 Only) (+18 more)

### Community 60 - "Feature Specification: QA/QC Module (IPCC & ISO 14064 Compliant)"
Cohesion: 0.07
Nodes (24): Content Quality, Feature Readiness, Notes, Requirement Completeness, Specification Quality Checklist: qa-qc-ipcc-iso14064, Complexity Tracking, Constitution Check, Documentation (this feature) (+16 more)

### Community 61 - "Platform Documentation"
Cohesion: 0.67
Nodes (3): Methane Intensity Analytics UI, Emission Calculation Engines, GHG Accounting & Reporting Platform README

### Community 67 - "User"
Cohesion: 0.09
Nodes (15): User, seed_admin(), End-to-End Test for the CSV Uploader (Import Emissions Data Wizard) Tests the…, Tests the CSV upload endpoint with a mock CSV containing mixed scenarios.…, TestCSVUploaderE2E, admin_user(), client(), it_admin_user() (+7 more)

### Community 68 - "AUDIT MEMORY (living document)"
Cohesion: 0.15
Nodes (12): 0. Conventions and context to respect, 1. CRITICAL security findings, 2. HIGH security findings, 3. Additional security findings (second pass), 4. CALCULATION and LOGIC bugs, 5. Tests and tooling, 6. Decision log, 7. Work log (+4 more)

### Community 69 - "GHGUser"
Cohesion: 0.31
Nodes (3): HttpUser, GHGUser, task

### Community 92 - "models.py"
Cohesion: 0.08
Nodes (30): Anomaly Detection for GHG Emissions Data. Uses Z-score (against 12-month…, Grid Emission Factors - electricity_factors.py Central registry for indirect…, migrate_database(), MethaneSourceType, ProductionData, # NOTE: Do NOT call db.session.commit() here., Persistent key-value store for application-wide settings (GWP standard, OGMP…, SbtiTarget (+22 more)

### Community 93 - "login_required"
Cohesion: 0.16
Nodes (20): login_required(), get_custom_factors(), Get all custom emission factors, delete_all_notifications(), delete_notification(), dismiss_all(), get_notifications(), mark_read() (+12 more)

### Community 111 - "Feature Specification: Batch Approve/Reject Pending Records"
Cohesion: 0.08
Nodes (23): Content Quality, Feature Readiness, Notes, Requirement Completeness, Specification Quality Checklist: batch-approve-reject, Complexity Tracking, Constitution Check, Documentation (this feature) (+15 more)

### Community 112 - "background_processor.py"
Cohesion: 0.07
Nodes (41): _append_job_list(), _build_mapping(), get_job_status(), _process_file_thread(), _process_row(), _process_row_custom_factors(), _process_row_facilities(), _process_row_mitigation() (+33 more)

### Community 113 - "new/.specify/scripts/powershell/common.ps1"
Cohesion: 0.23
Nodes (13): Find-SpecifyRoot(), Format-SpecKitCommand(), Get-CurrentBranch(), Get-FeaturePathsEnv(), Get-InvokeSeparator(), Get-NormalizedPriority(), Get-Python3Command(), Get-RepoRoot() (+5 more)

### Community 114 - ".specify/scripts/powershell/common.ps1"
Cohesion: 0.23
Nodes (13): Find-SpecifyRoot(), Format-SpecKitCommand(), Get-CurrentBranch(), Get-FeaturePathsEnv(), Get-InvokeSeparator(), Get-NormalizedPriority(), Get-Python3Command(), Get-RepoRoot() (+5 more)

### Community 115 - "Facility"
Cohesion: 0.29
Nodes (14): Facility, app(), client(), logged_client(), fixture, test_bulk_import_custom_factors(), test_bulk_import_facilities(), test_bulk_import_mitigation() (+6 more)

### Community 116 - "Feature Specification: [FEATURE NAME]"
Cohesion: 0.15
Nodes (12): Assumptions, Edge Cases, Feature Specification: [FEATURE NAME], Functional Requirements, Key Entities *(include if feature involves data)*, Measurable Outcomes, Requirements *(mandatory)*, Success Criteria *(mandatory)* (+4 more)

### Community 117 - "Feature Specification: [FEATURE NAME]"
Cohesion: 0.15
Nodes (12): Assumptions, Edge Cases, Feature Specification: [FEATURE NAME], Functional Requirements, Key Entities *(include if feature involves data)*, Measurable Outcomes, Requirements *(mandatory)*, Success Criteria *(mandatory)* (+4 more)

### Community 118 - "get_allowed_facility_ids"
Cohesion: 0.15
Nodes (21): add_facility(), delete_facility(), get_all_regions(), get_facilities(), import_facilities(), route, Bulk import facilities, Return all unique region identifiers — IT Admin only, no access filtering.… (+13 more)

### Community 119 - "Implementation Tasks: QA/QC Module (IPCC & ISO 14064)"
Cohesion: 0.17
Nodes (11): Dependencies & Execution Order, Implementation for User Story 1, Implementation for User Story 2, Implementation for User Story 3, Implementation Tasks: QA/QC Module (IPCC & ISO 14064), Phase 1: Setup (Shared Infrastructure), Phase 2: Foundational (Blocking Prerequisites), Phase 3: User Story 1 - Automated Data Validation (Priority: P1) ⭐ MVP (+3 more)

### Community 120 - "to_psia"
Cohesion: 0.21
Nodes (8): Converts gauge or metric pressure to absolute pressure in psia., Converts temperature value to Kelvin., to_kelvin(), to_psia(), D-01 / API Compendium 2021 stoichiometric flaring partition helper. Partitions…, API Equation 6-3 - Volume per unloading event with temperature correction:…, _split_vented_and_flared(), Temperature conversions must agree at physical invariant points (absolute zero,…

### Community 122 - "Core Principles"
Cohesion: 0.18
Nodes (10): Core Principles, Governance, [PRINCIPLE_1_NAME], [PRINCIPLE_2_NAME], [PRINCIPLE_3_NAME], [PRINCIPLE_4_NAME], [PRINCIPLE_5_NAME], [PROJECT_NAME] Constitution (+2 more)

### Community 123 - "Core Principles"
Cohesion: 0.18
Nodes (10): Core Principles, Governance, [PRINCIPLE_1_NAME], [PRINCIPLE_2_NAME], [PRINCIPLE_3_NAME], [PRINCIPLE_4_NAME], [PRINCIPLE_5_NAME], [PROJECT_NAME] Constitution (+2 more)

### Community 124 - "Core Principles"
Cohesion: 0.18
Nodes (10): Core Principles, Governance, [PRINCIPLE_1_NAME], [PRINCIPLE_2_NAME], [PRINCIPLE_3_NAME], [PRINCIPLE_4_NAME], [PRINCIPLE_5_NAME], [PROJECT_NAME] Constitution (+2 more)

### Community 125 - "Core Principles"
Cohesion: 0.18
Nodes (10): Core Principles, Governance, [PRINCIPLE_1_NAME], [PRINCIPLE_2_NAME], [PRINCIPLE_3_NAME], [PRINCIPLE_4_NAME], [PRINCIPLE_5_NAME], [PROJECT_NAME] Constitution (+2 more)

### Community 126 - "client/package.json"
Cohesion: 0.20
Nodes (9): name, private, scripts, build, dev, lint, preview, type (+1 more)

### Community 127 - ".dispatch"
Cohesion: 0.18
Nodes (6): Strictly extracts a required float parameter without falling back to defaults., Cleanly parses a percentage (0-100) or fraction (0-1) into a 0.0 - 1.0 ratio., Extracts a percentage or fraction strictly and normalizes to 0.0 - 1.0., Extracts an optional percentage or fraction normalized to 0.0 - 1.0., Executes the calculation for the given process type. - Tier 1 (default /…, Normalizes a volume value to the specified target unit.

### Community 129 - "Implementation Tasks: Batch Approve/Reject Pending Records"
Cohesion: 0.20
Nodes (9): Dependencies & Execution Order, Implementation for User Story 1, Implementation for User Story 2, Implementation Tasks: Batch Approve/Reject Pending Records, Phase 1: Setup (Shared Infrastructure), Phase 2: Foundational (Blocking Prerequisites), Phase 3: User Story 1 - Bulk Approving Records (Priority: P1) ⭐ MVP, Phase 4: User Story 2 - Bulk Rejecting Records (Priority: P2) (+1 more)

### Community 130 - "Implementation Plan: [FEATURE]"
Cohesion: 0.22
Nodes (8): Complexity Tracking, Constitution Check, Documentation (this feature), Implementation Plan: [FEATURE], Project Structure, Source Code (repository root), Summary, Technical Context

### Community 131 - "Implementation Plan: [FEATURE]"
Cohesion: 0.22
Nodes (8): Complexity Tracking, Constitution Check, Documentation (this feature), Implementation Plan: [FEATURE], Project Structure, Source Code (repository root), Summary, Technical Context

### Community 132 - "Existing Entities to Modify"
Cohesion: 0.22
Nodes (8): 1. `Emission` (Scope 1), 2. `Scope2Emission`, 3. `Scope3Emission`, 4. `CustomFactor`, `ActivityLog`, Data Model: QA/QC Module, Existing Entities to Modify, Existing Entities to Utilize

### Community 134 - "BaseCalculator"
Cohesion: 0.22
Nodes (5): BaseCalculator, Validates that all required inputs are present and non-negative., Calculates absolute uncertainty and non-negative bounds at 95% CI (k=2.0 per…, Base class for all API Compendium 2021 calculation modules. Provides common…, Formats the final calculation result into a standard structure.

### Community 136 - "status.py"
Cohesion: 0.50
Nodes (3): normalize_status(), Canonical Status Vocabulary for GHG Platform. Standardizes statuses across…, Normalize input status string to canonical vocabulary.

### Community 139 - "test_emission_calculations.py"
Cohesion: 0.12
Nodes (9): =============================================================================…, Aggregates test results for a final summary table., Blowdown Tier 1 (default): vessel volume = 5 m3 physical pressure = 100 psig →…, Fugitive average — uses _generic_calculation with catalog EF. EF: ch4=0.1…, Tier 3 Combustion with gas composition (carbon mass balance): volume = 1000 scf…, SummaryResult, TestTier1FugitiveAverage, TestTier1Venting (+1 more)

### Community 140 - "generate_1k_comprehensive.py"
Cohesion: 0.33
Nodes (3): gas_comp(), Generate a comprehensive 1,000-row Scope 1 test CSV that covers: - All 13…, Return a realistic gas composition that sums to ~100%.

### Community 143 - "[CHECKLIST TYPE] Checklist: [FEATURE NAME]"
Cohesion: 0.40
Nodes (4): [Category 1], [Category 2], [CHECKLIST TYPE] Checklist: [FEATURE NAME], Notes

### Community 144 - "[CHECKLIST TYPE] Checklist: [FEATURE NAME]"
Cohesion: 0.40
Nodes (4): [Category 1], [Category 2], [CHECKLIST TYPE] Checklist: [FEATURE NAME], Notes

### Community 145 - "Research & Design Decisions: Batch Approve/Reject"
Cohesion: 0.40
Nodes (4): 1. Technical Context Verification, 2. Identified Issues, 3. Decisions, Research & Design Decisions: Batch Approve/Reject

### Community 146 - "Research & Design Decisions: QA/QC Module (IPCC & ISO 14064)"
Cohesion: 0.40
Nodes (4): 1. Technical Context Verification, 2. Identified Issues & Requirements, 3. Decisions, Research & Design Decisions: QA/QC Module (IPCC & ISO 14064)

### Community 165 - "combine_uncertainties_product"
Cohesion: 0.50
Nodes (3): combine_uncertainties_product(), Combine relative uncertainties for E = Activity × EF (multiplicative). Formula:…, IPCC Eq 3.1: u_E = sqrt(u_AD^2 + u_EF^2). u_AD = 0.07 (7%), u_EF = 0.05 (5%).…

### Community 181 - "test_audit_remediation.py"
Cohesion: 0.04
Nodes (61): CbamProductExport, MitigationRecord, _query_intensity_stats(), _query_intensity_trend_bulk(), Fetches intensity data for ALL requested years in 5 bulk queries instead of 5…, Pure query logic for /intensity-stats — returns a plain Python list. Get…, client(), fixture (+53 more)

### Community 197 - "NotificationCenter.jsx"
Cohesion: 0.28
Nodes (7): getTypeConfig(), headerActionBtn, iconBtnStyle, NotificationCenter(), NotifRow(), relativeTime(), TYPE_CONFIG

### Community 204 - "reports.py"
Cohesion: 0.28
Nodes (7): Prevent formula injection (DDE/CSV injection) in Excel cells including leading…, _safe_excel_value(), compute_facility_ogmp_level(), ogmp_level_label(), OGMP 2.0 Compliance and Hierarchy Classification Service. Canonical…, Formatted label for OGMP level., Canonical determination of facility OGMP 2.0 level (1-5). - Level 5: Both…

## Knowledge Gaps
- **446 isolated node(s):** `name`, `private`, `version`, `type`, `dev` (+441 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **53 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `CalculationDispatcher` connect `CalculationDispatcher` to `calculate_co2e`, `TestEdgeCases`, `test_emission_calculations.py`, `TestTier3LiquidsUnloading`, `extract_val`, `TestUnitConversions`, `background_processor.py`, `test_tier_scope_kpi_numerical.py`, `TestTier1DrillingMud`, `TestTier1Flaring`, `TestTier1Combustion`, `test_audit_remediation.py`, `TestTier3PneumaticDevices`, `.dispatch`?**
  _High betweenness centrality (0.041) - this node is a cross-community bridge._
- **Why does `login_required()` connect `login_required` to `emissions.py`, `dashboard.py`, `bulk_resolve`, `route`, `app.py`, `satellite.py`, `get_current_user`, `reports.py`, `get_allowed_facility_ids`, `qaqc.py`, `auth.py`, `log_activity_and_notify`?**
  _High betweenness centrality (0.036) - this node is a cross-community bridge._
- **Why does `sqlite3` connect `sqlite3` to `background_processor.py`, `app.py`, `models.py`?**
  _High betweenness centrality (0.032) - this node is a cross-community bridge._
- **Are the 38 inferred relationships involving `CalculationDispatcher` (e.g. with `CombustionCalculator` and `FlaringCalculator`) actually correct?**
  _`CalculationDispatcher` has 38 INFERRED edges - model-reasoned connections that need verification._
- **What connects `name`, `private`, `version` to the rest of the system?**
  _446 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `emissions.py` be split into smaller, more focused modules?**
  _Cohesion score 0.0797979797979798 - nodes in this community are weakly interconnected._
- **Should `dashboard.py` be split into smaller, more focused modules?**
  _Cohesion score 0.07092198581560284 - nodes in this community are weakly interconnected._