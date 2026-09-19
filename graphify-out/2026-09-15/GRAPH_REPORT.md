# Graph Report - H2  (2026-09-15)

## Corpus Check
- 264 files · ~598,721 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 2145 nodes · 4487 edges · 197 communities (155 shown, 42 thin omitted)
- Extraction: 92% EXTRACTED · 8% INFERRED · 0% AMBIGUOUS · INFERRED: 345 edges (avg confidence: 0.52)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `0b21e68a`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- emissions.py
- dashboard.py
- Scope1Form.jsx
- emission_factors_routes.py
- GHGCalculator
- calculate_co2e
- dependencies
- devDependencies
- App.jsx
- app.py
- useToast
- get_current_user
- test_uncertainty.py
- test_api_security.py
- extract_val
- audit.py
- Sentinel5PService
- test_tier_scope_kpi_numerical.py
- pages/ManageData.jsx
- CalculationDispatcher
- emissionFactorsAPI.js
- SYSTEM MEMORY & KNOWLEDGE GRAPH
- test_audit.py
- dependencies
- custom_factors.py
- api.js
- AnomalyDetector
- Backend (Server)
- auth.py
- log_activity_and_notify
- TestCO2ECalculation
- get_allowed_facility_ids
- lucide-react
- Frontend (Client)
- Emissions.jsx
- Tasks: [FEATURE NAME]
- test_qaqc_diagnostics.py
- TestEdgeCases
- srss_inventory
- ModernReportGenerator.js
- export_satellite_to_ogmp
- Project Metadata
- build
- env.py
- TestUnitConversions
- Desktop App Dev Tools
- TestTier1DrillingMud
- files
- TestTier1Flaring
- FlaringCalculator
- NPM Scripts
- Pitch Deck Builder
- DashboardEnhanced.jsx
- login_required
- test_vented.py
- Graphify Workflow Tools
- Tasks: [FEATURE NAME]
- Feature Specification: QA/QC Module (IPCC & ISO 14064 Compliant)
- Platform Documentation
- API and UI Routes
- test_satellite.py
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
- get_active_gwp
- .get_token
- Feature Specification: Batch Approve/Reject Pending Records
- background_processor.py
- new/.specify/scripts/powershell/common.ps1
- .specify/scripts/powershell/common.ps1
- Facility
- Feature Specification: [FEATURE NAME]
- Feature Specification: [FEATURE NAME]
- NotificationCenter.jsx
- Implementation Tasks: QA/QC Module (IPCC & ISO 14064)
- vented.py
- _calc_cogen_allocation
- Core Principles
- Core Principles
- Core Principles
- Core Principles
- client/package.json
- ogmp.py
- TestUnauthenticatedAccess
- Implementation Tasks: Batch Approve/Reject Pending Records
- Implementation Plan: [FEATURE]
- Implementation Plan: [FEATURE]
- Existing Entities to Modify
- framer-motion
- BaseCalculator
- _calc_indirect_steam
- status.py
- class-variance-authority
- generate_1k_comprehensive.py
- new/.specify/scripts/powershell/create-new-feature.ps1
- .specify/scripts/powershell/create-new-feature.ps1
- [CHECKLIST TYPE] Checklist: [FEATURE NAME]
- [CHECKLIST TYPE] Checklist: [FEATURE NAME]
- Research & Design Decisions: Batch Approve/Reject
- Research & Design Decisions: QA/QC Module (IPCC & ISO 14064)
- formik
- papaparse
- react
- react-dom
- tailwind-merge
- @vitejs/plugin-react
- File-by-File Analysis
- jspdf-autotable
- .test_scope2_location_based_grid_averages
- .test_scope2_market_based_contractual_instruments
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
- User

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

## Communities (197 total, 42 thin omitted)

### Community 0 - "emissions.py"
Cohesion: 0.08
Nodes (42): get_job_status(), add_bulk_upload(), add_emission(), approve_batch_emissions(), approve_emission(), bulk_delete_emissions(), delete_emission(), _escape_like() (+34 more)

### Community 1 - "dashboard.py"
Cohesion: 0.07
Nodes (50): cached, get_available_years(), get_base_year(), get_batch_dashboard_data(), get_categorical_breakdown(), get_dashboard_summary(), _get_global_cache_epoch(), get_goal() (+42 more)

### Community 2 - "Scope1Form.jsx"
Cohesion: 0.14
Nodes (16): CalculationDetails(), CustomDropdown(), EmissionResult(), AGRForm(), BlowdownForm(), CombustionForm(), HHV_REQUIRED_PROCESSES, CompletionsForm() (+8 more)

### Community 3 - "emission_factors_routes.py"
Cohesion: 0.07
Nodes (39): get_factor_by_process_category(), get_factor_by_segment(), get_factors_by_segment_and_category(), Emission Factors Database - API Compendium 2021 Complete catalog from Sections…, Returns all emission factors applicable to the given segment. Args: segment…, Returns all emission factors for the given process category. Args:…, Returns all emission factors for a specific segment and process category. Args:…, Emission Factors Database - API Compendium 2021 Comprehensive emission factors… (+31 more)

### Community 5 - "calculate_co2e"
Cohesion: 0.06
Nodes (41): convert_factor_to_kg_per_unit(), _normalize_efficiency(), _normalize_unit_str(), API Compendium 2021 - Section 5: Combustion and Flaring Implementation of…, Standard fuel-based combustion calculation with API §4.2.1 thermodynamic…, Defensively normalizes efficiency inputs provided as either fractional ratios…, Dual-efficiency flaring model (API 5-3, 5-4) with API §4.2.1 thermodynamic…, Standard Quantity * EF fallback with unit handling and tier-aware uncertainty. (+33 more)

### Community 6 - "dependencies"
Cohesion: 0.09
Nodes (23): axios, chart.js, clsx, jspdf, leaflet, dependencies, axios, chart.js (+15 more)

### Community 7 - "devDependencies"
Cohesion: 0.07
Nodes (27): autoprefixer, eslint, @eslint/js, eslint-plugin-react-hooks, eslint-plugin-react-refresh, globals, devDependencies, autoprefixer (+19 more)

### Community 8 - "App.jsx"
Cohesion: 0.10
Nodes (31): fetchCsrfToken(), AdminRoute(), App(), AuditRoute(), AuditTrail, ITRoute(), MethaneIntensity, NonITRoute() (+23 more)

### Community 9 - "app.py"
Cohesion: 0.13
Nodes (15): errorhandler, listens_for, after_request(), before_request(), get_csrf_token(), health_check(), internal_error(), not_found_error() (+7 more)

### Community 10 - "useToast"
Cohesion: 0.11
Nodes (17): Diagnostics, EmissionsMap, QADashboard, UserManagement, COMPONENT_DATA, GasCompositionCalculator(), Modal(), ToastContext (+9 more)

### Community 11 - "get_current_user"
Cohesion: 0.16
Nodes (31): BaseYear, BaseYearRecalculation, EmissionSource, Goal, MitigationProject, MitigationRecord, ReportingMetadata, create_base_year_recalculation() (+23 more)

### Community 12 - "test_uncertainty.py"
Cohesion: 0.10
Nodes (21): admin_user(), client(), it_admin_user(), fixture, Test suite for /dashboard/uncertainty endpoint. Covers: auth, RBAC,…, Specifying year= returns that year in the response., scope=1 should only return Scope 1 categories (no Scope 2/3 groups)., export=csv should return text/csv with correct headers. (+13 more)

### Community 13 - "test_api_security.py"
Cohesion: 0.12
Nodes (15): admin_user(), app(), client(), login(), fixture, Security and integration tests for GHG Dashboard API. These test the HTTP layer…, User should not be able to delete an emission record created by another user…, User should be able to delete their own emission record. (+7 more)

### Community 14 - "extract_val"
Cohesion: 0.05
Nodes (26): extract_val(), =============================================================================…, Aggregates test results for a final summary table., Same calculation using m3 input — should produce same result after conversion., Diesel Tier 1: quantity = 500 gal HHV = 138,700 Btu/gal → 500 × 138,700 /…, Flaring Tier 3 (factor_source='specific') — Dual efficiency model: gas_volume =…, Blowdown Tier 1 (default): vessel volume = 5 m3 physical pressure = 100 psig →…, Tank Tier 3: throughput = 2000 bbl/month GOR = 200 scf/bbl CH4 content = 45%… (+18 more)

### Community 15 - "audit.py"
Cohesion: 0.40
Nodes (10): audit_access_required(), _build_audit_query(), export_audit_logs(), get_audit_filters(), get_audit_logs(), get_audit_stats(), route, Prevent CSV formula injection (DDE/Excel macro execution) including leading… (+2 more)

### Community 16 - "Sentinel5PService"
Cohesion: 0.18
Nodes (6): Sentinel-5P (TROPOMI) Satellite Methane Service Connects to ESA Copernicus Data…, Service for querying ESA Copernicus Sentinel-5P TROPOMI methane measurements., Estimates methane mass emission rate (kg CH4/hr) from a Sentinel-5P column…, Sentinel5PService, Emission rate Q must scale linearly with delta_ppb and wind_speed., Zero or negative delta_ch4_ppb must return exactly 0.0 kg/hr.

### Community 17 - "test_tier_scope_kpi_numerical.py"
Cohesion: 0.17
Nodes (44): CombustionCalculator, ComponentFugitiveCalculator, CompressorSealCalculator, EquipmentFugitiveCalculator, CogenAllocationCalculator, IndirectSteamCalculator, AGRCalculator, DehydratorCalculator (+36 more)

### Community 18 - "pages/ManageData.jsx"
Cohesion: 0.08
Nodes (14): RFC-4180, ManageData, BatchReviewWizard(), detectAnomalies(), QUICK_REJECTION_REASONS, ErrorBoundary, BOUNDARY_OPTIONS, DEFAULT_GWP (+6 more)

### Community 19 - "CalculationDispatcher"
Cohesion: 0.06
Nodes (38): CalculationDispatcher, Strictly extracts a required float parameter without falling back to defaults., Cleanly parses a percentage (0-100) or fraction (0-1) into a 0.0 - 1.0 ratio., Extracts a percentage or fraction strictly and normalizes to 0.0 - 1.0., Extracts an optional percentage or fraction normalized to 0.0 - 1.0., Executes the calculation for the given process type. - Tier 1 (default /…, Routes a calculation request to the appropriate API 2021 calculator., Normalizes a volume value to the specified target unit. (+30 more)

### Community 20 - "emissionFactorsAPI.js"
Cohesion: 0.17
Nodes (9): EmissionFactorOption(), Scope1Form(), API_FACTORS, convertActivityData(), formatUncertainty(), getFactorUncertainty(), getProcessTypesForSegment(), getSegmentBgColor() (+1 more)

### Community 21 - "SYSTEM MEMORY & KNOWLEDGE GRAPH"
Cohesion: 0.09
Nodes (21): 1. ARCHITECTURAL MAP & ENTRY POINTS, [2026-09-14T23:44:00Z] - ARCHITECTURAL KNOWLEDGE GRAPH INITIALIZATION, [2026-09-15T00:01:00Z] - SCOPE 1 EMISSION DETAIL VIEWER REMEDIATION & THEME ALIGNMENT, [2026-09-15T00:52:00Z] - FULL-STACK RESILIENCE & RUNTIME VERIFICATION REMEDIATION, 2. MODULE & FILE REGISTRY, 3. COMPONENT & ENTITY GRAPH (NODES & EDGES), 4. CRITICAL INVARIANTS & BUSINESS RULES, 5. CHANGELOG & DRIFT LOG (+13 more)

### Community 23 - "test_audit.py"
Cohesion: 0.17
Nodes (6): admin_user(), client(), it_admin_user(), fixture, regular_user(), seed_audit_logs()

### Community 24 - "dependencies"
Cohesion: 0.12
Nodes (16): bcryptjs, body-parser, cors, express, express-rate-limit, dependencies, bcryptjs, body-parser (+8 more)

### Community 25 - "custom_factors.py"
Cohesion: 0.20
Nodes (17): CustomFactor, Permits superuser and admin roles for data management operations. NOTE:…, superuser_required(), create_custom_factor(), delete_custom_factor(), get_custom_factors(), import_custom_factors(), _parse_non_negative_float() (+9 more)

### Community 26 - "api.js"
Cohesion: 0.05
Nodes (29): api, ReferenceData, BulkImportModal(), autoDetectMapping(), ColumnMappingWizard(), Icons, STEPS, TEMPLATES (+21 more)

### Community 27 - "AnomalyDetector"
Cohesion: 0.13
Nodes (12): AnomalyDetector, Check a Scope 1 CO2e value against the trailing 12 months strictly prior to the…, Checks a new emission value against historical data for the same facility and…, Check a Scope 2 CO2e value against the trailing 12 months strictly prior to the…, Check a Scope 3 CO2e value against the trailing 12 months strictly prior to the…, Compute Z-score of a value against a list of historical values. Returns…, Verify that background anomaly detection flags are stored in emission.qa_flag., Finding 9: Verify IQR quantile calculation does not distort on small N >= 4. (+4 more)

### Community 28 - "Backend (Server)"
Cohesion: 0.03
Nodes (74): `add_indexes.py`, `app.py`, Backend (Server), `background_processor.py`, `benchmark_db.py`, `calculations\base.py`, `calculations\combustion.py`, `calculations\constants.py` (+66 more)

### Community 29 - "auth.py"
Cohesion: 0.11
Nodes (30): limit, Persistent key-value store for application-wide settings (GWP standard, OGMP…, SystemSetting, admin_required(), admin_reset_password(), change_password(), delete_user(), forgot_password() (+22 more)

### Community 30 - "log_activity_and_notify"
Cohesion: 0.12
Nodes (36): LevelUpgradeLog, update_settings(), clear_dashboard_cache(), Updates global epoch in shared DB state and invalidates local worker heap., add_production(), bulk_import_production(), delete_cbam_export(), delete_ogmp_survey() (+28 more)

### Community 32 - "get_allowed_facility_ids"
Cohesion: 0.10
Nodes (28): delete_facility(), get_all_regions(), get_facilities(), route, Return all unique region identifiers — IT Admin only, no access filtering.…, update_facility(), bulk_resolve(), export_qaqc_report() (+20 more)

### Community 34 - "Frontend (Client)"
Cohesion: 0.03
Nodes (66): `api.js`, `App.jsx`, `components\BulkImportModal.jsx`, `components\CalculationDetails.jsx`, `components\charts\BarChart.jsx`, `components\charts\index.js`, `components\charts\LineChart.jsx`, `components\charts\PieChart.jsx` (+58 more)

### Community 35 - "Emissions.jsx"
Cohesion: 0.29
Nodes (8): Emissions, Emissions(), STAGE_EMISSION_CALCULATOR, STAGE_FACTOR_CALCULATOR, STAGE_SCOPE1_SUB_SELECTION, STAGE_SCOPE2, STAGE_SCOPE3, STAGE_SCOPE_SELECTION

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

### Community 41 - "export_satellite_to_ogmp"
Cohesion: 0.19
Nodes (13): export_satellite_to_ogmp(), get_facility_satellite_data(), get_satellite_layer_config(), _get_user_copernicus_credentials(), poll_new_satellite_passes(), route, Returns layer metadata, color scale intervals, and connection status for the…, Queries real Sentinel-5P observations for a facility or bounding box. Supports… (+5 more)

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

### Community 52 - "FlaringCalculator"
Cohesion: 0.22
Nodes (6): FlaringCalculator, test_flaring_calculator_basic(), test_flaring_calculator_specific_c1_c10(), test_stationary_combustion_calculator(), API §5.2: Flared hydrocarbons must partition into unburnt slip and…, Tier 2 Flaring: Dual efficiency model (combustion efficiency vs destruction…

### Community 53 - "NPM Scripts"
Cohesion: 0.33
Nodes (6): scripts, build:exe, start, start:electron, start:web, test

### Community 54 - "Pitch Deck Builder"
Cohesion: 0.40
Nodes (4): add_card(), add_header(), Adds standard Startup Algeria header banner with accent bar and title., Creates a modern rounded rectangular card container.

### Community 55 - "DashboardEnhanced.jsx"
Cohesion: 0.13
Nodes (16): CarbonIntensity, DashboardEnhanced, SbtiDashboard, BarChart(), LineChart(), DEFAULT_COLORS, PieChart(), SkeletonCard() (+8 more)

### Community 56 - "login_required"
Cohesion: 0.16
Nodes (21): login_required(), delete_all_notifications(), delete_notification(), dismiss_all(), get_notifications(), mark_read(), route, Permanently delete a single notification. (+13 more)

### Community 57 - "test_vented.py"
Cohesion: 0.25
Nodes (7): Verify pneumatic intermittent actuation calculation, Verify liquids unloading accepts depth/diam/press units without error, test_blowdown_calculator(), test_liquids_unloading_units(), test_pneumatics_calculator(), test_pneumatics_intermittent_actuation(), test_tanks_calculator()

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

### Community 67 - "test_satellite.py"
Cohesion: 0.18
Nodes (10): Layer configuration returns ESA standard legend steps and unauthenticated…, Crucial policy test: Unconfigured / unauthenticated queries MUST return status…, Tests OAuth2 authentication flow with mock Copernicus Keycloak token endpoint., Verifies the physical 1D box model / mass-divergence plume flux estimation., Tests OAuth2 rejection handling., test_sentinel5p_connection_test_mocked_failure(), test_sentinel5p_connection_test_mocked_success(), test_sentinel5p_flux_calculation() (+2 more)

### Community 68 - "AUDIT MEMORY (living document)"
Cohesion: 0.15
Nodes (12): 0. Conventions and context to respect, 1. CRITICAL security findings, 2. HIGH security findings, 3. Additional security findings (second pass), 4. CALCULATION and LOGIC bugs, 5. Tests and tooling, 6. Decision log, 7. Work log (+4 more)

### Community 69 - "GHGUser"
Cohesion: 0.31
Nodes (3): HttpUser, GHGUser, task

### Community 92 - "models.py"
Cohesion: 0.07
Nodes (40): Anomaly Detection for GHG Emissions Data. Uses Z-score (against 12-month…, Grid Emission Factors - electricity_factors.py Central registry for indirect…, run_all_scenarios(), migrate_database(), ActivityLog, Emission, MethaneSourceType, Notification (+32 more)

### Community 93 - "get_active_gwp"
Cohesion: 0.11
Nodes (19): _process_row(), Validates a single mapped row and runs calculation via compute_emissions.…, get_active_gwp(), Global Warming Potential (GWP) Constants & Resolution Engine Supports IPCC AR4…, Dynamically resolve the active GWP factors dictionary based on standard and…, compute_emissions(), Tests the full _process_row pipeline to verify data gets into Emission fields…, _process_row should return an Emission object with correct fields. (+11 more)

### Community 94 - ".get_token"
Cohesion: 0.28
Nodes (5): Any, Retrieves a valid JWT access token from Copernicus CDSE with caching., Returns tile layer configuration, color ramps, and metadata for Leaflet., Queries Copernicus STAC/OData API for real Sentinel-5P methane data around…, Tests authentication against Copernicus Data Space Ecosystem Keycloak endpoint.…

### Community 111 - "Feature Specification: Batch Approve/Reject Pending Records"
Cohesion: 0.08
Nodes (23): Content Quality, Feature Readiness, Notes, Requirement Completeness, Specification Quality Checklist: batch-approve-reject, Complexity Tracking, Constitution Check, Documentation (this feature) (+15 more)

### Community 112 - "background_processor.py"
Cohesion: 0.13
Nodes (26): _append_job_list(), _build_mapping(), _clean_float(), _process_file_thread(), _process_row_custom_factors(), _process_row_facilities(), _process_row_mitigation(), _process_row_production() (+18 more)

### Community 113 - "new/.specify/scripts/powershell/common.ps1"
Cohesion: 0.23
Nodes (13): Find-SpecifyRoot(), Format-SpecKitCommand(), Get-CurrentBranch(), Get-FeaturePathsEnv(), Get-InvokeSeparator(), Get-NormalizedPriority(), Get-Python3Command(), Get-RepoRoot() (+5 more)

### Community 114 - ".specify/scripts/powershell/common.ps1"
Cohesion: 0.23
Nodes (13): Find-SpecifyRoot(), Format-SpecKitCommand(), Get-CurrentBranch(), Get-FeaturePathsEnv(), Get-InvokeSeparator(), Get-NormalizedPriority(), Get-Python3Command(), Get-RepoRoot() (+5 more)

### Community 115 - "Facility"
Cohesion: 0.13
Nodes (21): Facility, add_facility(), import_facilities(), Bulk import facilities, End-to-End Test for the CSV Uploader (Import Emissions Data Wizard) Tests the…, Tests the CSV upload endpoint with a mock CSV containing mixed scenarios.…, TestCSVUploaderE2E, app() (+13 more)

### Community 116 - "Feature Specification: [FEATURE NAME]"
Cohesion: 0.15
Nodes (12): Assumptions, Edge Cases, Feature Specification: [FEATURE NAME], Functional Requirements, Key Entities *(include if feature involves data)*, Measurable Outcomes, Requirements *(mandatory)*, Success Criteria *(mandatory)* (+4 more)

### Community 117 - "Feature Specification: [FEATURE NAME]"
Cohesion: 0.15
Nodes (12): Assumptions, Edge Cases, Feature Specification: [FEATURE NAME], Functional Requirements, Key Entities *(include if feature involves data)*, Measurable Outcomes, Requirements *(mandatory)*, Success Criteria *(mandatory)* (+4 more)

### Community 118 - "NotificationCenter.jsx"
Cohesion: 0.28
Nodes (7): getTypeConfig(), headerActionBtn, iconBtnStyle, NotificationCenter(), NotifRow(), relativeTime(), TYPE_CONFIG

### Community 119 - "Implementation Tasks: QA/QC Module (IPCC & ISO 14064)"
Cohesion: 0.17
Nodes (11): Dependencies & Execution Order, Implementation for User Story 1, Implementation for User Story 2, Implementation for User Story 3, Implementation Tasks: QA/QC Module (IPCC & ISO 14064), Phase 1: Setup (Shared Infrastructure), Phase 2: Foundational (Blocking Prerequisites), Phase 3: User Story 1 - Automated Data Validation (Priority: P1) ⭐ MVP (+3 more)

### Community 120 - "vented.py"
Cohesion: 0.09
Nodes (25): API Compendium 2021 - Section 6: Midstream & Process Emissions Implementation…, API Compendium 2021 §6.6 & GRI-GLYCalc Parametric Solubility Model (CALC-02…, convert(), normalize_efficiency(), normalize_gas_volume_to_standard(), Converts gauge or metric pressure to absolute pressure in psia., API Compendium 2021 §4.2.1: Converts gas volume measured at actual/operating…, Simple unit conversion wrapper. (+17 more)

### Community 121 - "_calc_cogen_allocation"
Cohesion: 0.50
Nodes (3): _calc_cogen_allocation(), Calculate heat-allocated tCO2e for CHP / cogeneration entry., Scope 2 Cogeneration (CHP) Allocation Methods: Total Facility Emissions: 10,000…

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

### Community 127 - "ogmp.py"
Cohesion: 0.50
Nodes (3): ogmp_level_label(), OGMP 2.0 Compliance and Hierarchy Classification Service. Canonical…, Formatted label for OGMP level.

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
Cohesion: 0.20
Nodes (5): BaseCalculator, Validates that all required inputs are present and non-negative., Calculates absolute uncertainty and non-negative bounds at 95% CI (k=2.0 per…, Base class for all API Compendium 2021 calculation modules. Provides common…, Formats the final calculation result into a standard structure.

### Community 135 - "_calc_indirect_steam"
Cohesion: 0.50
Nodes (3): _calc_indirect_steam(), Calculate tCO2e for indirect steam / heat entry., Scope 2 Indirect Steam & Heat: Formula: CO2 (t) = (Energy MMBtu × EF_boiler) /…

### Community 136 - "status.py"
Cohesion: 0.50
Nodes (3): normalize_status(), Canonical Status Vocabulary for GHG Platform. Standardizes statuses across…, Normalize input status string to canonical vocabulary.

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

### Community 181 - "test_audit_remediation.py"
Cohesion: 0.04
Nodes (52): CbamProductExport, client(), fixture, Defect 5: Verify update_emission merges existing process_type and inputs., Defect 6: Verify bulk import for Scope 2 & 3 blocks it_admin and enforces…, Defect 7: Verify IT admin cannot access QA/QC resolve and users cannot verify…, Defect 8: Verify base year recalculation route enforces role, sets created_by,…, Defect 9: Verify save_cbam_export checks facility access for existing records… (+44 more)

### Community 210 - "User"
Cohesion: 0.11
Nodes (14): User, seed_admin(), Verify viewer/auditor blocked from mutate on Scope 2, and creator ownership…, test_scope2_rbac_and_creator_ownership(), admin_user(), client(), it_admin_user(), fixture (+6 more)

## Knowledge Gaps
- **461 isolated node(s):** `name`, `private`, `version`, `type`, `dev` (+456 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **42 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `login_required()` connect `login_required` to `emissions.py`, `dashboard.py`, `get_allowed_facility_ids`, `emission_factors_routes.py`, `export_satellite_to_ogmp`, `get_current_user`, `background_processor.py`, `Facility`, `custom_factors.py`, `models.py`, `auth.py`, `log_activity_and_notify`?**
  _High betweenness centrality (0.043) - this node is a cross-community bridge._
- **Why does `User` connect `User` to `emissions.py`, `TestUnauthenticatedAccess`, `test_qaqc_diagnostics.py`, `test_uncertainty.py`, `test_api_security.py`, `background_processor.py`, `test_tier_scope_kpi_numerical.py`, `Facility`, `test_audit_remediation.py`, `test_audit.py`, `custom_factors.py`, `models.py`, `auth.py`, `log_activity_and_notify`?**
  _High betweenness centrality (0.034) - this node is a cross-community bridge._
- **Why does `CalculationDispatcher` connect `CalculationDispatcher` to `calculate_co2e`, `TestEdgeCases`, `TestUnitConversions`, `extract_val`, `TestTier1DrillingMud`, `test_tier_scope_kpi_numerical.py`, `TestTier1Flaring`, `FlaringCalculator`, `test_audit_remediation.py`, `get_active_gwp`, `TestCO2ECalculation`?**
  _High betweenness centrality (0.032) - this node is a cross-community bridge._
- **Are the 38 inferred relationships involving `CalculationDispatcher` (e.g. with `CombustionCalculator` and `FlaringCalculator`) actually correct?**
  _`CalculationDispatcher` has 38 INFERRED edges - model-reasoned connections that need verification._
- **What connects `name`, `private`, `version` to the rest of the system?**
  _461 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `emissions.py` be split into smaller, more focused modules?**
  _Cohesion score 0.08456659619450317 - nodes in this community are weakly interconnected._
- **Should `dashboard.py` be split into smaller, more focused modules?**
  _Cohesion score 0.06561085972850679 - nodes in this community are weakly interconnected._