# Graph Report - H2  (2026-09-08)

## Corpus Check
- 250 files · ~560,073 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1838 nodes · 3563 edges · 187 communities (147 shown, 40 thin omitted)
- Extraction: 97% EXTRACTED · 3% INFERRED · 0% AMBIGUOUS · INFERRED: 110 edges (avg confidence: 0.57)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `cf4594e3`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- emissions.py
- dashboard.py
- Scope1Form.jsx
- emission_factors_routes.py
- propagate_uncertainty
- calculate_co2e
- dependencies
- devDependencies
- App.jsx
- test_emission_calculations.py
- QADashboard.jsx
- login_required
- useToast
- User
- TestTier1Combustion
- scope2.py
- api.js
- to_psia
- pages/ManageData.jsx
- CalculationDispatcher
- NotificationCenter.jsx
- Sentinel5PService
- qaqc.py
- models.py
- dependencies
- app.py
- Scope1ImportWizard.jsx
- GHGCalculator
- Backend (Server)
- auth.py
- get_allowed_facility_ids
- combustion.py
- export_emissions
- Toast.jsx
- Frontend (Client)
- emission_factors.py
- Tasks: [FEATURE NAME]
- extract_val
- TestEdgeCases
- dispatcher.py
- ModernReportGenerator.js
- get_facility_satellite_data
- Project Metadata
- build
- env.py
- TestUnitConversions
- Desktop App Dev Tools
- TestTier1DrillingMud
- files
- TestTier1Flaring
- bulk_import_scope2
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
- useLayout
- TestTier1Venting
- Core Principles
- Core Principles
- Core Principles
- Core Principles
- client/package.json
- facilities.py
- TestUnauthenticatedAccess
- Implementation Tasks: Batch Approve/Reject Pending Records
- Implementation Plan: [FEATURE]
- Implementation Plan: [FEATURE]
- Existing Entities to Modify
- framer-motion
- test_runner.py
- test_final.py
- test_final_v3.py
- test_pipeline.py
- test_pipeline_robust.py
- pages/CarbonIntensity.jsx
- generate_1k_comprehensive.py
- new/.specify/scripts/powershell/create-new-feature.ps1
- .specify/scripts/powershell/create-new-feature.ps1
- [CHECKLIST TYPE] Checklist: [FEATURE NAME]
- [CHECKLIST TYPE] Checklist: [FEATURE NAME]
- Research & Design Decisions: Batch Approve/Reject
- Research & Design Decisions: QA/QC Module (IPCC & ISO 14064)
- analyze_all.py
- chart.js
- TestTier3LiquidsUnloading
- TestTier1FugitiveAverage
- formik
- TestTier3CombustionGasComposition
- jspdf-autotable
- papaparse
- react
- react-dom
- tailwind-merge
- @vitejs/plugin-react
- File-by-File Analysis
- 001-batch-approve-reject/data-model.md
- 001-batch-approve-reject/quickstart.md
- 002-qa-qc-ipcc-iso14064/quickstart.md

## God Nodes (most connected - your core abstractions)
1. `login_required()` - 135 edges
2. `get_current_user()` - 87 edges
3. `Backend (Server)` - 74 edges
4. `get_allowed_facility_ids()` - 72 edges
5. `Frontend (Client)` - 66 edges
6. `CalculationDispatcher` - 57 edges
7. `log_activity_and_notify()` - 47 edges
8. `calculate_co2e()` - 44 edges
9. `useToast()` - 42 edges
10. `useAuth()` - 40 edges

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

## Communities (187 total, 40 thin omitted)

### Community 0 - "emissions.py"
Cohesion: 0.08
Nodes (53): get_job_status(), clear_dashboard_cache(), add_bulk_upload(), add_emission(), approve_batch_emissions(), approve_emission(), bulk_delete_emissions(), delete_emission() (+45 more)

### Community 1 - "dashboard.py"
Cohesion: 0.06
Nodes (52): cached, BaseYearRecalculation, Goal, create_base_year_recalculation(), create_goal(), get_available_years(), get_base_year(), get_batch_dashboard_data() (+44 more)

### Community 2 - "Scope1Form.jsx"
Cohesion: 0.09
Nodes (22): CustomDropdown(), EmissionFactorOption(), AGRForm(), BlowdownForm(), CombustionForm(), HHV_REQUIRED_PROCESSES, CompletionsForm(), DehydratorForm() (+14 more)

### Community 3 - "emission_factors_routes.py"
Cohesion: 0.11
Nodes (26): get_factor_by_segment(), Returns all emission factors applicable to the given segment. Args: segment…, get_all_emission_factors(), get_all_process_types(), get_database_version(), get_emission_factors_stats(), get_factors_by_seg_and_proc(), get_factors_for_process_category() (+18 more)

### Community 4 - "propagate_uncertainty"
Cohesion: 0.10
Nodes (22): API Compendium 2021 - Section 7: Fugitive Emissions Implementation of equations…, API Compendium 2021 - Section 8: Indirect Emissions Implementation of indirect…, DehydratorCalculator, API Compendium 2021 - Section 6: Midstream & Process Emissions Implementation…, API Compendium 2021 §6.6 & GRI-GLYCalc Parametric Solubility Model (CALC-02…, API Compendium 2021 - Section 4: Calculation Fundamentals Implementation of…, combine_uncertainties_product(), combine_uncertainties_sum() (+14 more)

### Community 5 - "calculate_co2e"
Cohesion: 0.09
Nodes (21): Dual-efficiency flaring model (API 5-3, 5-4) with API §4.2.1 thermodynamic…, Standard fuel-based combustion calculation with API §4.2.1 thermodynamic…, API Section 7.2.3 - Compressor seals, Average Factor Method - counts * EF component_counts: dict of {type: count}, Average Factor Method for equipment - count * EF, API Equation 8-2: Indirect emissions from steam/heat Emissions = Energy /…, API Section 8.3 - Allocation of Cogeneration Emissions Methods: wri_efficiency,…, API Compendium 2021 §6.5 & Table 6-5: - CO2 mass balance from amine sweetening… (+13 more)

### Community 6 - "dependencies"
Cohesion: 0.09
Nodes (23): axios, clsx, jspdf, leaflet, lucide-react, dependencies, axios, clsx (+15 more)

### Community 7 - "devDependencies"
Cohesion: 0.07
Nodes (27): autoprefixer, eslint, @eslint/js, eslint-plugin-react-hooks, eslint-plugin-react-refresh, globals, devDependencies, autoprefixer (+19 more)

### Community 8 - "App.jsx"
Cohesion: 0.11
Nodes (24): fetchCsrfToken(), AdminRoute(), App(), Diagnostics, ITRoute(), NonITRoute(), PrivateRoute(), ReferenceData (+16 more)

### Community 9 - "test_emission_calculations.py"
Cohesion: 0.14
Nodes (19): _process_row(), Validates a single mapped row and runs calculation via compute_emissions.…, get_active_gwp(), Global Warming Potential (GWP) Constants & Resolution Engine Supports IPCC AR4…, Dynamically resolve the active GWP factors dictionary based on standard and…, compute_emissions(), =============================================================================…, Tests the full _process_row pipeline to verify data gets into Emission fields… (+11 more)

### Community 10 - "QADashboard.jsx"
Cohesion: 0.16
Nodes (6): QADashboard, ErrorBoundary, paginationBtnStyle(), QADashboard(), tdStyle, thStyle

### Community 11 - "login_required"
Cohesion: 0.24
Nodes (26): MitigationRecord, ReportingMetadata, login_required(), get_custom_factors(), Get all custom emission factors, add_base_year_recalculation(), add_mitigation(), add_or_update_goal() (+18 more)

### Community 12 - "useToast"
Cohesion: 0.21
Nodes (14): Emissions, Scope2Form(), Scope3Form(), useToast(), Emissions(), MethaneIntensity(), SbtiDashboard(), STAGE_EMISSION_CALCULATOR (+6 more)

### Community 13 - "User"
Cohesion: 0.09
Nodes (20): User, seed_admin(), End-to-End Test for the CSV Uploader (Import Emissions Data Wizard) Tests the…, Tests the CSV upload endpoint with a mock CSV containing mixed scenarios.…, TestCSVUploaderE2E, admin_user(), app(), client() (+12 more)

### Community 14 - "TestTier1Combustion"
Cohesion: 0.20
Nodes (3): Same calculation using m3 input — should produce same result after conversion., Hand-calc for Natural Gas Tier 1: quantity = 10,000 scf HHV = 1,020 Btu/scf →…, TestTier1Combustion

### Community 15 - "scope2.py"
Cohesion: 0.18
Nodes (10): Grid Emission Factors - electricity_factors.py Central registry for indirect…, ActivityLog, Notification, OgmpSurvey, export_satellite_to_ogmp(), Exports a verified Sentinel-5P observation anomaly into an OGMP Level 4/5 Top-…, _calc_cogen_allocation(), _calc_indirect_steam() (+2 more)

### Community 16 - "api.js"
Cohesion: 0.15
Nodes (8): api, EmissionsMap, autoDetectMapping(), ColumnMappingWizard(), Icons, STEPS, TEMPLATES, EmissionsMap()

### Community 17 - "to_psia"
Cohesion: 0.25
Nodes (7): normalize_gas_volume_to_standard(), API Compendium 2021 §4.2.1: Converts gas volume measured at actual/operating…, Converts temperature value to Kelvin., Converts gauge or metric pressure to absolute pressure in psia., to_kelvin(), to_psia(), API Equation 6-3 - Volume per unloading event with temperature correction:…

### Community 18 - "pages/ManageData.jsx"
Cohesion: 0.17
Nodes (10): ManageData, BatchReviewWizard(), detectAnomalies(), QUICK_REJECTION_REASONS, BOUNDARY_OPTIONS, DEFAULT_GWP, GWP_AR4, GWP_AR5 (+2 more)

### Community 19 - "CalculationDispatcher"
Cohesion: 0.10
Nodes (24): CalculationDispatcher, Strictly extracts a required float parameter without falling back to defaults., Extracts a percentage (0-100) or fraction (0-1) strictly and converts to 0-1., Extracts an optional percentage (0-100) or fraction (0-1) converted to 0-1., Executes the calculation for the given process type. - Tier 1 (default /…, Routes a calculation request to the appropriate API 2021 calculator., Normalizes a volume value to the specified target unit., Standard Quantity * EF fallback with unit handling and tier-aware uncertainty. (+16 more)

### Community 20 - "NotificationCenter.jsx"
Cohesion: 0.28
Nodes (7): getTypeConfig(), headerActionBtn, iconBtnStyle, NotificationCenter(), NotifRow(), relativeTime(), TYPE_CONFIG

### Community 21 - "Sentinel5PService"
Cohesion: 0.10
Nodes (19): Any, Sentinel-5P (TROPOMI) Satellite Methane Service Connects to ESA Copernicus Data…, Retrieves a valid JWT access token from Copernicus CDSE with caching., Returns tile layer configuration, color ramps, and metadata for Leaflet., Queries Copernicus STAC/OData API for real Sentinel-5P methane data around…, Service for querying ESA Copernicus Sentinel-5P TROPOMI methane measurements., Estimates methane mass emission rate (kg CH4/hr) from a Sentinel-5P column…, Tests authentication against Copernicus Data Space Ecosystem Keycloak endpoint.… (+11 more)

### Community 22 - "qaqc.py"
Cohesion: 0.27
Nodes (11): bulk_resolve(), export_qaqc_report(), get_qaqc_dashboard(), _is_admin_or_superuser(), route, Returns True if the user has QA/QC viewing rights (admin or superuser roles)., Exports QA/QC anomaly data as a CSV file. Access: admin, superuser, it_admin…, Returns aggregated uncertainty (IPCC SRSS) and flagged anomaly records. Scoped… (+3 more)

### Community 23 - "models.py"
Cohesion: 0.15
Nodes (17): Anomaly Detection for GHG Emissions Data. Uses Z-score (against 12-month…, run_all_scenarios(), migrate_database(), BaseYear, Emission, MethaneSourceType, MitigationProject, ProductionData (+9 more)

### Community 24 - "dependencies"
Cohesion: 0.12
Nodes (16): bcryptjs, body-parser, cors, express, express-rate-limit, dependencies, bcryptjs, body-parser (+8 more)

### Community 25 - "app.py"
Cohesion: 0.15
Nodes (16): errorhandler, listens_for, after_request(), before_request(), get_csrf_token(), health_check(), internal_error(), not_found_error() (+8 more)

### Community 26 - "Scope1ImportWizard.jsx"
Cohesion: 0.06
Nodes (19): autoDetect(), FIELD_GROUPS, Icon, PROCESS_CATALOGUE, Scope1ImportWizard(), STEPS, autoDetect(), FIELD_GROUPS (+11 more)

### Community 28 - "Backend (Server)"
Cohesion: 0.03
Nodes (74): `add_indexes.py`, `app.py`, Backend (Server), `background_processor.py`, `benchmark_db.py`, `calculations\base.py`, `calculations\combustion.py`, `calculations\constants.py` (+66 more)

### Community 29 - "auth.py"
Cohesion: 0.06
Nodes (55): limit, Persistent key-value store for application-wide settings (GWP standard, OGMP…, SystemSetting, admin_required(), admin_reset_password(), change_password(), delete_user(), forgot_password() (+47 more)

### Community 30 - "get_allowed_facility_ids"
Cohesion: 0.22
Nodes (19): CbamProductExport, LevelUpgradeLog, add_production(), bulk_import_production(), delete_cbam_export(), delete_ogmp_survey(), delete_production(), get_cbam_exports() (+11 more)

### Community 31 - "combustion.py"
Cohesion: 0.33
Nodes (6): CombustionCalculator, FlaringCalculator, API Compendium 2021 - Section 5: Combustion and Flaring Implementation of…, test_flaring_calculator_basic(), test_flaring_calculator_specific_c1_c10(), test_stationary_combustion_calculator()

### Community 32 - "export_emissions"
Cohesion: 0.25
Nodes (9): create_pdf_report(), export_emissions(), export_ogmp_excel(), generate_report(), route, Generate PDF report based on filters, Export emissions data as PDF - GET version for frontend integration, Generate PDF report for emissions data (+1 more)

### Community 33 - "Toast.jsx"
Cohesion: 0.14
Nodes (12): UserManagement, BulkImportModal(), COMPONENT_DATA, GasCompositionCalculator(), Modal(), ToastContext, ToastProvider(), getRoleMeta() (+4 more)

### Community 34 - "Frontend (Client)"
Cohesion: 0.03
Nodes (66): `api.js`, `App.jsx`, `components\BulkImportModal.jsx`, `components\CalculationDetails.jsx`, `components\charts\BarChart.jsx`, `components\charts\index.js`, `components\charts\LineChart.jsx`, `components\charts\PieChart.jsx` (+58 more)

### Community 35 - "emission_factors.py"
Cohesion: 0.16
Nodes (13): get_factor_by_process_category(), get_factors_by_segment_and_category(), Emission Factors Database - API Compendium 2021 Complete catalog from Sections…, Returns all emission factors for the given process category. Args:…, Returns all emission factors for a specific segment and process category. Args:…, Emission Factors Database - API Compendium 2021 Comprehensive emission factors…, get_process_types_by_category(), get_process_types_for_segment() (+5 more)

### Community 36 - "Tasks: [FEATURE NAME]"
Cohesion: 0.07
Nodes (26): Dependencies & Execution Order, Format: `[ID] [P?] [Story] Description`, Implementation for User Story 1, Implementation for User Story 2, Implementation for User Story 3, Implementation Strategy, Incremental Delivery, MVP First (User Story 1 Only) (+18 more)

### Community 37 - "extract_val"
Cohesion: 0.31
Nodes (4): extract_val(), Diesel Tier 1: quantity = 500 gal HHV = 138,700 Btu/gal → 500 × 138,700 /…, Extract the central value from a propagated uncertainty dict or bare float., TestTier1CombustionDiesel

### Community 38 - "TestEdgeCases"
Cohesion: 0.20
Nodes (5): Zero quantity should produce zero emissions without crash., Negative quantity must raise ValueError., 1 MMscf = 1,000,000 scf — result should match 1M scf calculation., If GOR=0 and EF=0, result should be zero (no flash gas)., TestEdgeCases

### Community 39 - "dispatcher.py"
Cohesion: 0.10
Nodes (23): BaseCalculator, Validates that all required inputs are present and non-negative., Calculates absolute uncertainty and non-negative bounds at 95% CI., Formats the final calculation result into a standard structure., Base class for all API Compendium 2021 calculation modules. Provides common…, ComponentFugitiveCalculator, CompressorSealCalculator, EquipmentFugitiveCalculator (+15 more)

### Community 40 - "ModernReportGenerator.js"
Cohesion: 0.36
Nodes (8): createChartImage(), fetchAllReportData(), generateModernPDF(), generateReportCharts(), loadImage(), NOTE: When regionId is an array (multi-select), do NOT send facility_id param —, THEME, toRgba()

### Community 41 - "get_facility_satellite_data"
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

### Community 52 - "bulk_import_scope2"
Cohesion: 0.18
Nodes (11): bulk_import_scope2(), delete_scope2_emission(), get_emission_factors(), get_scope2_emissions(), route, Update a Scope 2 emission record, Delete a Scope 2 emission record, Import Scope 2 emissions from CSV data (+3 more)

### Community 53 - "NPM Scripts"
Cohesion: 0.33
Nodes (6): scripts, build:exe, start, start:electron, start:web, test

### Community 54 - "Pitch Deck Builder"
Cohesion: 0.40
Nodes (4): add_card(), add_header(), Adds standard Startup Algeria header banner with accent bar and title., Creates a modern rounded rectangular card container.

### Community 55 - "DashboardEnhanced.jsx"
Cohesion: 0.26
Nodes (6): DashboardEnhanced, SkeletonCard(), calculateForecast(), DashboardEnhanced(), calculateTrend(), formatCompactNumber()

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
Cohesion: 0.18
Nodes (16): _build_mapping(), _process_file_thread(), _process_row_custom_factors(), _process_row_facilities(), _process_row_mitigation(), _process_row_production(), _process_row_scope2(), _process_row_scope3() (+8 more)

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

### Community 120 - "useLayout"
Cohesion: 0.19
Nodes (8): AuditTrail, TopBar(), LayoutContext, LayoutProvider(), useLayout(), AuditTrail(), ManageDataInner(), f()

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

### Community 127 - "facilities.py"
Cohesion: 0.36
Nodes (7): add_facility(), get_all_regions(), get_facilities(), import_facilities(), route, Bulk import facilities, Return all unique region identifiers — IT Admin only, no access filtering.…

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

### Community 134 - "test_runner.py"
Cohesion: 0.29
Nodes (3): DummyFacility, MockDB, MockSession

### Community 135 - "test_final.py"
Cohesion: 0.29
Nodes (3): DummyFacility, MockDB, MockSession

### Community 136 - "test_final_v3.py"
Cohesion: 0.29
Nodes (3): DummyFacility, MockDB, MockSession

### Community 137 - "test_pipeline.py"
Cohesion: 0.29
Nodes (3): DummyFacility, MockDB, MockSession

### Community 138 - "test_pipeline_robust.py"
Cohesion: 0.29
Nodes (3): DummyFacility, MockDB, MockSession

### Community 139 - "pages/CarbonIntensity.jsx"
Cohesion: 0.22
Nodes (9): CarbonIntensity, MethaneIntensity, SbtiDashboard, BarChart(), LineChart(), DEFAULT_COLORS, PieChart(), getActiveGwpFactors() (+1 more)

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

## Knowledge Gaps
- **436 isolated node(s):** `name`, `private`, `version`, `type`, `dev` (+431 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **40 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `sqlite3` connect `sqlite3` to `test_runner.py`, `test_final.py`, `test_final_v3.py`, `test_pipeline.py`, `test_pipeline_robust.py`, `models.py`, `dependencies`, `app.py`?**
  _High betweenness centrality (0.034) - this node is a cross-community bridge._
- **Why does `dependencies` connect `dependencies` to `Project Metadata`?**
  _High betweenness centrality (0.026) - this node is a cross-community bridge._
- **Why does `sqlite3` connect `dependencies` to `sqlite3`?**
  _High betweenness centrality (0.026) - this node is a cross-community bridge._
- **What connects `name`, `private`, `version` to the rest of the system?**
  _436 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `emissions.py` be split into smaller, more focused modules?**
  _Cohesion score 0.07727272727272727 - nodes in this community are weakly interconnected._
- **Should `dashboard.py` be split into smaller, more focused modules?**
  _Cohesion score 0.0649895178197065 - nodes in this community are weakly interconnected._
- **Should `Scope1Form.jsx` be split into smaller, more focused modules?**
  _Cohesion score 0.09292929292929293 - nodes in this community are weakly interconnected._