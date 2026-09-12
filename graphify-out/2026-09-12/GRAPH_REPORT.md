# Graph Report - H2  (2026-09-12)

## Corpus Check
- 255 files · ~570,076 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1905 nodes · 3709 edges · 186 communities (145 shown, 41 thin omitted)
- Extraction: 97% EXTRACTED · 3% INFERRED · 0% AMBIGUOUS · INFERRED: 110 edges (avg confidence: 0.57)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `cf4594e3`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- emissions.py
- route
- Scope1Form.jsx
- emission_factors_routes.py
- chart.js
- propagate_uncertainty
- dependencies
- devDependencies
- App.jsx
- compute_emissions
- QADashboard.jsx
- get_current_user
- test_uncertainty.py
- test_api_security.py
- TestTier1Combustion
- models.py
- calculate_co2e
- dispatcher.py
- pages/ManageData.jsx
- CalculationDispatcher
- useToast
- Sentinel5PService
- emissionFactorsAPI.js
- test_calculations_page.py
- dependencies
- Emission
- Scope1ImportWizard.jsx
- GHGCalculator
- Backend (Server)
- auth.py
- get_allowed_facility_ids
- combustion.py
- qaqc.py
- Toast.jsx
- Frontend (Client)
- api.js
- Tasks: [FEATURE NAME]
- extract_val
- TestEdgeCases
- f
- ModernReportGenerator.js
- poll_new_satellite_passes
- Project Metadata
- build
- env.py
- TestUnitConversions
- Desktop App Dev Tools
- TestTier1DrillingMud
- files
- TestTier1Flaring
- login_required
- NPM Scripts
- Pitch Deck Builder
- DashboardEnhanced.jsx
- class-variance-authority
- TestTier3Completions
- Graphify Workflow Tools
- Tasks: [FEATURE NAME]
- Feature Specification: QA/QC Module (IPCC & ISO 14064 Compliant)
- Platform Documentation
- API and UI Routes
- User
- scope2.py
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
- sqlite3
- TestTier3Flaring
- TestTier3TankFlashing
- TestTier3PneumaticDevices
- Feature Specification: Batch Approve/Reject Pending Records
- background_processor.py
- new/.specify/scripts/powershell/common.ps1
- .specify/scripts/powershell/common.ps1
- Facility
- Feature Specification: [FEATURE NAME]
- Feature Specification: [FEATURE NAME]
- AnomalyDetector
- Implementation Tasks: QA/QC Module (IPCC & ISO 14064)
- to_psia
- TestTier1Venting
- Core Principles
- Core Principles
- Core Principles
- Core Principles
- client/package.json
- export_emissions
- TestUnauthenticatedAccess
- Implementation Tasks: Batch Approve/Reject Pending Records
- Implementation Plan: [FEATURE]
- Implementation Plan: [FEATURE]
- Existing Entities to Modify
- framer-motion
- test_runner.py
- test_sbti.py
- test_final.py
- test_final_v3.py
- test_pipeline.py
- generate_1k_comprehensive.py
- new/.specify/scripts/powershell/create-new-feature.ps1
- .specify/scripts/powershell/create-new-feature.ps1
- [CHECKLIST TYPE] Checklist: [FEATURE NAME]
- [CHECKLIST TYPE] Checklist: [FEATURE NAME]
- Research & Design Decisions: Batch Approve/Reject
- Research & Design Decisions: QA/QC Module (IPCC & ISO 14064)
- analyze_all.py
- test_pipeline_robust.py
- TestTier3LiquidsUnloading
- TestTier1FugitiveAverage
- formik
- TestTier3CombustionGasComposition
- papaparse
- react
- react-dom
- tailwind-merge
- @vitejs/plugin-react
- File-by-File Analysis
- jspdf-autotable
- 001-batch-approve-reject/data-model.md
- 001-batch-approve-reject/quickstart.md
- 002-qa-qc-ipcc-iso14064/quickstart.md

## God Nodes (most connected - your core abstractions)
1. `login_required()` - 135 edges
2. `get_current_user()` - 89 edges
3. `Backend (Server)` - 74 edges
4. `get_allowed_facility_ids()` - 73 edges
5. `Frontend (Client)` - 66 edges
6. `CalculationDispatcher` - 57 edges
7. `log_activity_and_notify()` - 47 edges
8. `User` - 46 edges
9. `Facility` - 45 edges
10. `useToast()` - 44 edges

## Surprising Connections (you probably didn't know these)
- `Methane Intensity Analytics UI` --conceptually_related_to--> `Emission Calculation Engines`  [INFERRED]
  deck_assets/ui_methane.png → README.md
- `ManageDataInner()` --indirect_call--> `f()`  [INFERRED]
  new/client/src/pages/ManageData.jsx → temp_old/CarbonIntensity.jsx
- `seed_data()` --calls--> `Facility`  [INFERRED]
  seed_demo_data.py → new/server/models.py
- `seed_data()` --calls--> `Emission`  [INFERRED]
  seed_demo_data.py → new/server/models.py
- `seed_data()` --calls--> `User`  [INFERRED]
  seed_demo_data.py → new/server/models.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Graphify Tooling and Documentation** — agents_rules_graphify, agents_workflows_graphify, agents_rules_graphify_cli, agents_rules_graphify_mcp [EXTRACTED 1.00]
- **Emission Calculation & Visualization Flow** — new_server_calculations, deck_assets_ui_dashboard, deck_assets_chart_industry_emissions [INFERRED 0.80]

## Communities (186 total, 41 thin omitted)

### Community 0 - "emissions.py"
Cohesion: 0.08
Nodes (54): get_job_status(), start_background_upload(), clear_dashboard_cache(), add_bulk_upload(), add_emission(), approve_batch_emissions(), approve_emission(), bulk_delete_emissions() (+46 more)

### Community 1 - "route"
Cohesion: 0.05
Nodes (48): cached, Aggregate uncertainty across multiple sources using SRSS Approach 1. Formula:…, srss_inventory(), get_available_years(), get_base_year(), get_batch_dashboard_data(), get_categorical_breakdown(), get_dashboard_summary() (+40 more)

### Community 2 - "Scope1Form.jsx"
Cohesion: 0.18
Nodes (12): CustomDropdown(), AGRForm(), BlowdownForm(), CombustionForm(), HHV_REQUIRED_PROCESSES, CompletionsForm(), DehydratorForm(), DrillingForm() (+4 more)

### Community 3 - "emission_factors_routes.py"
Cohesion: 0.07
Nodes (39): get_factor_by_process_category(), get_factor_by_segment(), get_factors_by_segment_and_category(), Emission Factors Database - API Compendium 2021 Complete catalog from Sections…, Returns all emission factors applicable to the given segment. Args: segment…, Returns all emission factors for the given process category. Args:…, Returns all emission factors for a specific segment and process category. Args:…, Emission Factors Database - API Compendium 2021 Comprehensive emission factors… (+31 more)

### Community 5 - "propagate_uncertainty"
Cohesion: 0.08
Nodes (29): Dual-efficiency flaring model (API 5-3, 5-4) with API §4.2.1 thermodynamic…, Standard fuel-based combustion calculation with API §4.2.1 thermodynamic…, API Compendium 2021 - Section 7: Fugitive Emissions Implementation of equations…, API Section 7.2.3 - Compressor seals, Average Factor Method - counts * EF component_counts: dict of {type: count}, Average Factor Method for equipment - count * EF, API Compendium 2021 - Section 8: Indirect Emissions Implementation of indirect…, API Section 8.3 - Allocation of Cogeneration Emissions Methods: wri_efficiency,… (+21 more)

### Community 6 - "dependencies"
Cohesion: 0.09
Nodes (23): axios, clsx, jspdf, leaflet, lucide-react, dependencies, axios, clsx (+15 more)

### Community 7 - "devDependencies"
Cohesion: 0.07
Nodes (27): autoprefixer, eslint, @eslint/js, eslint-plugin-react-hooks, eslint-plugin-react-refresh, globals, devDependencies, autoprefixer (+19 more)

### Community 8 - "App.jsx"
Cohesion: 0.12
Nodes (23): fetchCsrfToken(), AdminRoute(), App(), Diagnostics, ITRoute(), NonITRoute(), PrivateRoute(), Reports (+15 more)

### Community 9 - "compute_emissions"
Cohesion: 0.18
Nodes (12): _process_row(), Validates a single mapped row and runs calculation via compute_emissions.…, compute_emissions(), run_all_scenarios(), Tests the full _process_row pipeline to verify data gets into Emission fields…, _process_row should return an Emission object with correct fields., Row with unknown facility should return an error, not crash., Row with no date should return a date error. (+4 more)

### Community 10 - "QADashboard.jsx"
Cohesion: 0.16
Nodes (6): QADashboard, ErrorBoundary, paginationBtnStyle(), QADashboard(), tdStyle, thStyle

### Community 11 - "get_current_user"
Cohesion: 0.22
Nodes (24): EmissionSource, MitigationProject, ReportingMetadata, add_base_year_recalculation(), add_mitigation(), add_or_update_goal(), add_source(), bulk_import_mitigation() (+16 more)

### Community 12 - "test_uncertainty.py"
Cohesion: 0.10
Nodes (21): admin_user(), client(), it_admin_user(), fixture, Test suite for /dashboard/uncertainty endpoint. Covers: auth, RBAC,…, Specifying year= returns that year in the response., scope=1 should only return Scope 1 categories (no Scope 2/3 groups)., export=csv should return text/csv with correct headers. (+13 more)

### Community 13 - "test_api_security.py"
Cohesion: 0.12
Nodes (15): admin_user(), app(), client(), login(), fixture, Security and integration tests for GHG Dashboard API. These test the HTTP layer…, User should not be able to delete an emission record created by another user…, User should be able to delete their own emission record. (+7 more)

### Community 14 - "TestTier1Combustion"
Cohesion: 0.20
Nodes (3): Same calculation using m3 input — should produce same result after conversion., Hand-calc for Natural Gas Tier 1: quantity = 10,000 scf HHV = 1,020 Btu/scf →…, TestTier1Combustion

### Community 15 - "models.py"
Cohesion: 0.09
Nodes (27): errorhandler, listens_for, after_request(), before_request(), get_csrf_token(), health_check(), internal_error(), not_found_error() (+19 more)

### Community 16 - "calculate_co2e"
Cohesion: 0.15
Nodes (14): get_active_gwp(), Global Warming Potential (GWP) Constants & Resolution Engine Supports IPCC AR4…, Dynamically resolve the active GWP factors dictionary based on standard and…, calculate_co2e(), convert(), Simple unit conversion wrapper., Calculates CO2e using dynamically resolved GWPs (AR4/AR5/AR6)., =============================================================================… (+6 more)

### Community 17 - "dispatcher.py"
Cohesion: 0.08
Nodes (28): BaseCalculator, Validates that all required inputs are present and non-negative., Calculates absolute uncertainty and non-negative bounds at 95% CI., Formats the final calculation result into a standard structure., Base class for all API Compendium 2021 calculation modules. Provides common…, ComponentFugitiveCalculator, CompressorSealCalculator, EquipmentFugitiveCalculator (+20 more)

### Community 18 - "pages/ManageData.jsx"
Cohesion: 0.15
Nodes (12): RFC-4180, ManageData, BatchReviewWizard(), detectAnomalies(), QUICK_REJECTION_REASONS, BOUNDARY_OPTIONS, DEFAULT_GWP, getActiveGwpFactors() (+4 more)

### Community 19 - "CalculationDispatcher"
Cohesion: 0.10
Nodes (24): CalculationDispatcher, Strictly extracts a required float parameter without falling back to defaults., Extracts a percentage (0-100) or fraction (0-1) strictly and converts to 0-1., Extracts an optional percentage (0-100) or fraction (0-1) converted to 0-1., Executes the calculation for the given process type. - Tier 1 (default /…, Routes a calculation request to the appropriate API 2021 calculator., Normalizes a volume value to the specified target unit., Standard Quantity * EF fallback with unit handling and tier-aware uncertainty. (+16 more)

### Community 20 - "useToast"
Cohesion: 0.11
Nodes (21): AuditTrail, EmissionsMap, TopBar(), getTypeConfig(), headerActionBtn, iconBtnStyle, NotificationCenter(), NotifRow() (+13 more)

### Community 21 - "Sentinel5PService"
Cohesion: 0.10
Nodes (19): Any, Sentinel-5P (TROPOMI) Satellite Methane Service Connects to ESA Copernicus Data…, Retrieves a valid JWT access token from Copernicus CDSE with caching., Returns tile layer configuration, color ramps, and metadata for Leaflet., Queries Copernicus STAC/OData API for real Sentinel-5P methane data around…, Service for querying ESA Copernicus Sentinel-5P TROPOMI methane measurements., Estimates methane mass emission rate (kg CH4/hr) from a Sentinel-5P column…, Tests authentication against Copernicus Data Space Ecosystem Keycloak endpoint.… (+11 more)

### Community 22 - "emissionFactorsAPI.js"
Cohesion: 0.17
Nodes (9): EmissionFactorOption(), Scope1Form(), API_FACTORS, convertActivityData(), formatUncertainty(), getFactorUncertainty(), getProcessTypesForSegment(), getSegmentBgColor() (+1 more)

### Community 23 - "test_calculations_page.py"
Cohesion: 0.25
Nodes (6): admin_user(), client(), it_admin_user(), fixture, regular_user(), test_facility_id()

### Community 24 - "dependencies"
Cohesion: 0.12
Nodes (16): bcryptjs, body-parser, cors, express, express-rate-limit, dependencies, bcryptjs, body-parser (+8 more)

### Community 25 - "Emission"
Cohesion: 0.11
Nodes (24): Anomaly Detection for GHG Emissions Data. Uses Z-score (against 12-month…, migrate_database(), BaseYear, Emission, MethaneSourceType, SbtiTarget, Scope2Emission, Scope3Emission (+16 more)

### Community 26 - "Scope1ImportWizard.jsx"
Cohesion: 0.06
Nodes (19): autoDetect(), FIELD_GROUPS, Icon, PROCESS_CATALOGUE, Scope1ImportWizard(), STEPS, autoDetect(), FIELD_GROUPS (+11 more)

### Community 28 - "Backend (Server)"
Cohesion: 0.03
Nodes (74): `add_indexes.py`, `app.py`, Backend (Server), `background_processor.py`, `benchmark_db.py`, `calculations\base.py`, `calculations\combustion.py`, `calculations\constants.py` (+66 more)

### Community 29 - "auth.py"
Cohesion: 0.07
Nodes (48): limit, CustomFactor, Persistent key-value store for application-wide settings (GWP standard, OGMP…, SystemSetting, admin_required(), admin_reset_password(), change_password(), delete_user() (+40 more)

### Community 30 - "get_allowed_facility_ids"
Cohesion: 0.25
Nodes (19): CbamProductExport, LevelUpgradeLog, ProductionData, add_production(), bulk_import_production(), delete_cbam_export(), delete_ogmp_survey(), delete_production() (+11 more)

### Community 31 - "combustion.py"
Cohesion: 0.33
Nodes (6): CombustionCalculator, FlaringCalculator, API Compendium 2021 - Section 5: Combustion and Flaring Implementation of…, test_flaring_calculator_basic(), test_flaring_calculator_specific_c1_c10(), test_stationary_combustion_calculator()

### Community 32 - "qaqc.py"
Cohesion: 0.27
Nodes (11): bulk_resolve(), export_qaqc_report(), get_qaqc_dashboard(), _is_admin_or_superuser(), route, Returns True if the user has QA/QC viewing rights (admin or superuser roles)., Exports QA/QC anomaly data as a CSV file. Access: admin, superuser, it_admin…, Returns aggregated uncertainty (IPCC SRSS) and flagged anomaly records. Scoped… (+3 more)

### Community 33 - "Toast.jsx"
Cohesion: 0.13
Nodes (13): UserManagement, BulkImportModal(), COMPONENT_DATA, GasCompositionCalculator(), Modal(), ToastContext, ToastProvider(), getRoleMeta() (+5 more)

### Community 34 - "Frontend (Client)"
Cohesion: 0.03
Nodes (66): `api.js`, `App.jsx`, `components\BulkImportModal.jsx`, `components\CalculationDetails.jsx`, `components\charts\BarChart.jsx`, `components\charts\index.js`, `components\charts\LineChart.jsx`, `components\charts\PieChart.jsx` (+58 more)

### Community 35 - "api.js"
Cohesion: 0.11
Nodes (19): api, Emissions, ReferenceData, CalculationDetails(), autoDetectMapping(), ColumnMappingWizard(), Icons, STEPS (+11 more)

### Community 36 - "Tasks: [FEATURE NAME]"
Cohesion: 0.07
Nodes (26): Dependencies & Execution Order, Format: `[ID] [P?] [Story] Description`, Implementation for User Story 1, Implementation for User Story 2, Implementation for User Story 3, Implementation Strategy, Incremental Delivery, MVP First (User Story 1 Only) (+18 more)

### Community 37 - "extract_val"
Cohesion: 0.31
Nodes (4): extract_val(), Diesel Tier 1: quantity = 500 gal HHV = 138,700 Btu/gal → 500 × 138,700 /…, Extract the central value from a propagated uncertainty dict or bare float., TestTier1CombustionDiesel

### Community 38 - "TestEdgeCases"
Cohesion: 0.20
Nodes (5): Zero quantity should produce zero emissions without crash., Negative quantity must raise ValueError., 1 MMscf = 1,000,000 scf — result should match 1M scf calculation., If GOR=0 and EF=0, result should be zero (no flash gas)., TestEdgeCases

### Community 40 - "ModernReportGenerator.js"
Cohesion: 0.36
Nodes (8): createChartImage(), fetchAllReportData(), generateModernPDF(), generateReportCharts(), loadImage(), NOTE: When regionId is an array (multi-select), do NOT send facility_id param —, THEME, toRgba()

### Community 41 - "poll_new_satellite_passes"
Cohesion: 0.24
Nodes (11): get_facility_satellite_data(), get_satellite_layer_config(), _get_user_copernicus_credentials(), poll_new_satellite_passes(), route, Returns layer metadata, color scale intervals, and connection status for the…, Queries real Sentinel-5P observations for a facility or bounding box. Supports…, Extracts Copernicus credentials from current user preferences or system-… (+3 more)

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

### Community 52 - "login_required"
Cohesion: 0.15
Nodes (23): get_audit_filters(), get_audit_logs(), route, login_required(), add_facility(), delete_facility(), get_all_regions(), get_facilities() (+15 more)

### Community 53 - "NPM Scripts"
Cohesion: 0.33
Nodes (6): scripts, build:exe, start, start:electron, start:web, test

### Community 54 - "Pitch Deck Builder"
Cohesion: 0.40
Nodes (4): add_card(), add_header(), Adds standard Startup Algeria header banner with accent bar and title., Creates a modern rounded rectangular card container.

### Community 55 - "DashboardEnhanced.jsx"
Cohesion: 0.14
Nodes (15): CarbonIntensity, DashboardEnhanced, MethaneIntensity, SbtiDashboard, BarChart(), LineChart(), DEFAULT_COLORS, PieChart() (+7 more)

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
Cohesion: 0.19
Nodes (6): User, seed_admin(), End-to-End Test for the CSV Uploader (Import Emissions Data Wizard) Tests the…, Tests the CSV upload endpoint with a mock CSV containing mixed scenarios.…, TestCSVUploaderE2E, seed_data()

### Community 68 - "scope2.py"
Cohesion: 0.15
Nodes (18): Calculation tier following IPCC 2006 GL Vol.1 §2.4 hierarchy., Tier, bulk_import_scope2(), _calc_cogen_allocation(), _calc_indirect_steam(), create_scope2_emission(), delete_scope2_emission(), get_emission_factors() (+10 more)

### Community 69 - "GHGUser"
Cohesion: 0.31
Nodes (3): HttpUser, GHGUser, task

### Community 91 - "sqlite3"
Cohesion: 0.17
Nodes (4): DummyFacility, MockDB, MockSession, sqlite3

### Community 111 - "Feature Specification: Batch Approve/Reject Pending Records"
Cohesion: 0.08
Nodes (23): Content Quality, Feature Readiness, Notes, Requirement Completeness, Specification Quality Checklist: batch-approve-reject, Complexity Tracking, Constitution Check, Documentation (this feature) (+15 more)

### Community 112 - "background_processor.py"
Cohesion: 0.21
Nodes (13): _build_mapping(), _process_file_thread(), _process_row_custom_factors(), _process_row_facilities(), _process_row_mitigation(), _process_row_production(), _process_row_scope2(), _process_row_scope3() (+5 more)

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

### Community 118 - "AnomalyDetector"
Cohesion: 0.26
Nodes (6): AnomalyDetector, Check a Scope 1 CO2e value against the trailing 12 months for the same facility…, Checks a new emission value against historical data for the same facility and…, Check a Scope 2 CO2e value against the trailing 12 months for the same facility…, Check a Scope 3 CO2e value against the trailing 12 months for the same facility…, Compute Z-score of a value against a list of historical values. Returns…

### Community 119 - "Implementation Tasks: QA/QC Module (IPCC & ISO 14064)"
Cohesion: 0.17
Nodes (11): Dependencies & Execution Order, Implementation for User Story 1, Implementation for User Story 2, Implementation for User Story 3, Implementation Tasks: QA/QC Module (IPCC & ISO 14064), Phase 1: Setup (Shared Infrastructure), Phase 2: Foundational (Blocking Prerequisites), Phase 3: User Story 1 - Automated Data Validation (Priority: P1) ⭐ MVP (+3 more)

### Community 120 - "to_psia"
Cohesion: 0.17
Nodes (10): API Compendium 2021 §6.6 & GRI-GLYCalc Parametric Solubility Model (CALC-02…, normalize_gas_volume_to_standard(), API Compendium 2021 §4.2.1: Converts gas volume measured at actual/operating…, Converts temperature value to Kelvin., Converts temperature value to Fahrenheit., Converts gauge or metric pressure to absolute pressure in psia., to_fahrenheit(), to_kelvin() (+2 more)

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

### Community 127 - "export_emissions"
Cohesion: 0.20
Nodes (11): create_pdf_report(), export_emissions(), export_ogmp_excel(), generate_report(), route, Generate PDF report based on filters, Prevent formula injection (DDE/CSV injection) in Excel cells., Generate PDF report for emissions data (+3 more)

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

### Community 135 - "test_runner.py"
Cohesion: 0.29
Nodes (3): DummyFacility, MockDB, MockSession

### Community 136 - "test_sbti.py"
Cohesion: 0.32
Nodes (4): admin_user(), client(), it_admin_user(), fixture

### Community 137 - "test_final.py"
Cohesion: 0.29
Nodes (3): DummyFacility, MockDB, MockSession

### Community 138 - "test_final_v3.py"
Cohesion: 0.18
Nodes (5): EPA USEEIO Emission Factors v1.3 Maps NAICS codes to kg CO2e per $1,000 spend.…, Emission Factors Package Re-exports everything from root emission_factors.py…, DummyFacility, MockDB, MockSession

### Community 139 - "test_pipeline.py"
Cohesion: 0.29
Nodes (3): DummyFacility, MockDB, MockSession

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

### Community 147 - "analyze_all.py"
Cohesion: 0.83
Nodes (3): analyze_directory(), analyze_js_file(), analyze_python_file()

### Community 149 - "test_pipeline_robust.py"
Cohesion: 0.29
Nodes (3): DummyFacility, MockDB, MockSession

## Knowledge Gaps
- **438 isolated node(s):** `name`, `private`, `version`, `type`, `dev` (+433 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **41 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `sqlite3` connect `sqlite3` to `test_runner.py`, `test_final.py`, `test_final_v3.py`, `test_pipeline.py`, `models.py`, `test_pipeline_robust.py`, `dependencies`, `Emission`?**
  _High betweenness centrality (0.050) - this node is a cross-community bridge._
- **Why does `dependencies` connect `dependencies` to `Project Metadata`?**
  _High betweenness centrality (0.032) - this node is a cross-community bridge._
- **Why does `sqlite3` connect `dependencies` to `sqlite3`?**
  _High betweenness centrality (0.032) - this node is a cross-community bridge._
- **What connects `name`, `private`, `version` to the rest of the system?**
  _438 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `emissions.py` be split into smaller, more focused modules?**
  _Cohesion score 0.07518796992481203 - nodes in this community are weakly interconnected._
- **Should `route` be split into smaller, more focused modules?**
  _Cohesion score 0.054078014184397165 - nodes in this community are weakly interconnected._
- **Should `emission_factors_routes.py` be split into smaller, more focused modules?**
  _Cohesion score 0.0708245243128964 - nodes in this community are weakly interconnected._