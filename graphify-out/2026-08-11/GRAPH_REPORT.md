# Graph Report - .  (2026-08-11)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 1111 nodes · 2464 edges · 91 communities (69 shown, 22 thin omitted)
- Extraction: 96% EXTRACTED · 4% INFERRED · 0% AMBIGUOUS · INFERRED: 106 edges (avg confidence: 0.56)
- Token cost: 4,863 input · 1,040 output

## Graph Freshness
- Built from commit: `7a870544`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- User and Auth Management
- Dashboard and Goals API
- Emission Source Forms
- Emission Factor Database
- Calculation Base Classes
- Emission Calculation Logic
- Frontend Dependencies
- Development Configurations
- App Routing and Layout
- Background Processing Engine
- Midstream Calculation Modules
- Data Management Services
- Emission Wizard State
- Security and Testing
- Combustion Unit Tests
- Data Visualization Components
- CSV Mapping Wizard
- Scope 2 Management
- Error Handling and GWP
- Calculation Dispatcher Tests
- UI Header and Notifications
- Sentinel-5P Satellite Service
- Bulk Import and Modals
- API Middleware and Health
- Backend Dependencies
- End-to-End Integration Tests
- Satellite and OGMP Integration
- GHG Calculation Utilities
- Custom Factor Management
- Database Models and Audit
- Production and OGMP Data
- Flaring and Pressure Conversion
- Reporting and Export Services
- Scope 3 Management
- Combustion and Flaring Modules
- Fugitive and Tiered Tests
- Notification Services
- Calculation Input Normalization
- Calculation Edge Case Tests
- API Security Tests
- PDF Report Generation
- Satellite Service Tests
- Project Metadata
- Electron Build Configuration
- Database Migration Config
- Unit Conversion Tests
- Desktop App Dev Tools
- Drilling Mud Tests
- Build Artifacts
- Tier 1 Flaring Tests
- Tier 3 Flaring Tests
- NPM Scripts
- Pitch Deck Builder
- Tank Flashing Tests
- Pneumatic Device Tests
- Well Completion Tests
- Graphify Workflow Tools
- Intensity Metrics API
- Venting Calculation Tests
- Platform Documentation
- API and UI Routes
- Input Validation Logic
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

## God Nodes (most connected - your core abstractions)
1. `login_required()` - 117 edges
2. `CalculationDispatcher` - 58 edges
3. `calculate_co2e()` - 44 edges
4. `useToast()` - 34 edges
5. `User` - 33 edges
6. `extract_val()` - 33 edges
7. `useAuth()` - 32 edges
8. `BaseCalculator` - 29 edges
9. `get_allowed_facility_ids()` - 28 edges
10. `propagate_uncertainty()` - 27 edges

## Surprising Connections (you probably didn't know these)
- `Methane Intensity Analytics UI` --conceptually_related_to--> `Emission Calculation Engines`  [INFERRED]
  deck_assets/ui_methane.png → README.md
- `seed_data()` --calls--> `User`  [INFERRED]
  seed_demo_data.py → new/server/models.py
- `seed_data()` --calls--> `Facility`  [INFERRED]
  seed_demo_data.py → new/server/models.py
- `seed_data()` --calls--> `Emission`  [INFERRED]
  seed_demo_data.py → new/server/models.py
- `CombustionCalculator` --uses--> `BaseCalculator`  [INFERRED]
  new/server/calculations/combustion.py → new/server/calculations/base.py

## Import Cycles
- 3-file cycle: `new/server/routes/__init__.py -> new/server/routes/emission_factors_routes.py -> new/server/routes/auth.py -> new/server/routes/__init__.py`
- 3-file cycle: `new/server/routes/__init__.py -> new/server/routes/reports.py -> new/server/routes/auth.py -> new/server/routes/__init__.py`
- 3-file cycle: `new/server/routes/__init__.py -> new/server/routes/scope3.py -> new/server/routes/auth.py -> new/server/routes/__init__.py`
- 3-file cycle: `new/server/routes/__init__.py -> new/server/routes/scope2.py -> new/server/routes/auth.py -> new/server/routes/__init__.py`
- 3-file cycle: `new/server/routes/__init__.py -> new/server/routes/custom_factors.py -> new/server/routes/auth.py -> new/server/routes/__init__.py`
- 3-file cycle: `new/server/routes/__init__.py -> new/server/routes/dashboard.py -> new/server/routes/auth.py -> new/server/routes/__init__.py`
- 3-file cycle: `new/server/routes/__init__.py -> new/server/routes/managedata.py -> new/server/routes/auth.py -> new/server/routes/__init__.py`

## Hyperedges (group relationships)
- **Graphify Tooling and Documentation** — agents_rules_graphify, agents_workflows_graphify, agents_rules_graphify_cli, agents_rules_graphify_mcp [EXTRACTED 1.00]
- **Emission Calculation & Visualization Flow** — new_server_calculations, deck_assets_ui_dashboard, deck_assets_chart_industry_emissions [INFERRED 0.80]

## Communities (91 total, 22 thin omitted)

### Community 0 - "User and Auth Management"
Cohesion: 0.08
Nodes (58): limit, get_job_status(), Notification, admin_required(), change_password(), delete_user(), get_settings(), get_users() (+50 more)

### Community 1 - "Dashboard and Goals API"
Cohesion: 0.07
Nodes (48): cached, BaseYearRecalculation, Goal, create_base_year_recalculation(), create_goal(), get_available_years(), get_base_year(), get_batch_dashboard_data() (+40 more)

### Community 2 - "Emission Source Forms"
Cohesion: 0.09
Nodes (22): CustomDropdown(), EmissionFactorOption(), AGRForm(), BlowdownForm(), CombustionForm(), HHV_REQUIRED_PROCESSES, CompletionsForm(), DehydratorForm() (+14 more)

### Community 3 - "Emission Factor Database"
Cohesion: 0.07
Nodes (39): get_factor_by_process_category(), get_factor_by_segment(), get_factors_by_segment_and_category(), Emission Factors Database - API Compendium 2021 Complete catalog from Sections…, Returns all emission factors applicable to the given segment. Args: segment…, Returns all emission factors for the given process category. Args:…, Returns all emission factors for a specific segment and process category. Args:…, Emission Factors Database - API Compendium 2021 Comprehensive emission factors… (+31 more)

### Community 4 - "Calculation Base Classes"
Cohesion: 0.10
Nodes (23): BaseCalculator, Calculates absolute uncertainty and non-negative bounds at 95% CI., Formats the final calculation result into a standard structure., Base class for all API Compendium 2021 calculation modules. Provides common…, ComponentFugitiveCalculator, CompressorSealCalculator, EquipmentFugitiveCalculator, API Compendium 2021 - Section 7: Fugitive Emissions Implementation of equations… (+15 more)

### Community 5 - "Emission Calculation Logic"
Cohesion: 0.09
Nodes (23): Standard fuel-based combustion calculation with API §4.2.1 thermodynamic…, Standard Quantity * EF fallback with unit handling and tier-aware uncertainty., Average Factor Method - counts * EF component_counts: dict of {type: count}, Average Factor Method for equipment - count * EF, API Section 7.2.3 - Compressor seals, API Equation 8-2: Indirect emissions from steam/heat Emissions = Energy /…, API Section 8.3 - Allocation of Cogeneration Emissions Methods: wri_efficiency,…, API Compendium 2021 §6.5 & Table 6-5: - CO2 mass balance from amine sweetening… (+15 more)

### Community 6 - "Frontend Dependencies"
Cohesion: 0.05
Nodes (39): axios, chart.js, class-variance-authority, clsx, formik, jspdf, jspdf-autotable, leaflet (+31 more)

### Community 7 - "Development Configurations"
Cohesion: 0.06
Nodes (34): autoprefixer, eslint, @eslint/js, eslint-plugin-react-hooks, eslint-plugin-react-refresh, globals, devDependencies, autoprefixer (+26 more)

### Community 8 - "App Routing and Layout"
Cohesion: 0.14
Nodes (20): fetchCsrfToken(), AdminRoute(), App(), ITRoute(), NonITRoute(), PrivateRoute(), Layout(), Sidebar() (+12 more)

### Community 9 - "Background Processing Engine"
Cohesion: 0.15
Nodes (19): _build_mapping(), _process_file_thread(), _process_row(), Validates a single mapped row and runs calculation via compute_emissions.…, start_background_upload(), get_active_gwp(), Global Warming Potential (GWP) Constants & Resolution Engine Supports IPCC AR4…, Dynamically resolve the active GWP factors dictionary based on standard and… (+11 more)

### Community 10 - "Midstream Calculation Modules"
Cohesion: 0.11
Nodes (16): API Compendium 2021 - Section 8: Indirect Emissions Implementation of indirect…, DehydratorCalculator, API Compendium 2021 - Section 6: Midstream & Process Emissions Implementation…, API Compendium 2021 §6.6 & GRI-GLYCalc Parametric Solubility Model (CALC-02…, API Compendium 2021 - Section 4: Calculation Fundamentals Implementation of…, combine_uncertainties_product(), combine_uncertainties_sum(), GHG Inventory Uncertainty Quantification Module… (+8 more)

### Community 11 - "Data Management Services"
Cohesion: 0.17
Nodes (24): BaseYear, EmissionSource, MitigationProject, MitigationRecord, ReportingMetadata, add_base_year_recalculation(), add_mitigation(), add_source() (+16 more)

### Community 12 - "Emission Wizard State"
Cohesion: 0.33
Nodes (7): Emissions(), STAGE_EMISSION_CALCULATOR, STAGE_FACTOR_CALCULATOR, STAGE_SCOPE1_SUB_SELECTION, STAGE_SCOPE2, STAGE_SCOPE3, STAGE_SCOPE_SELECTION

### Community 13 - "Security and Testing"
Cohesion: 0.14
Nodes (14): fixture, User, seed_admin(), admin_user(), app(), client(), login(), Security and integration tests for GHG Dashboard API. These test the HTTP layer… (+6 more)

### Community 14 - "Combustion Unit Tests"
Cohesion: 0.12
Nodes (9): extract_val(), Same calculation using m3 input — should produce same result after conversion., Diesel Tier 1: quantity = 500 gal HHV = 138,700 Btu/gal → 500 × 138,700 /…, Liquids Unloading Tier 3 (API Eq. 6-3): well_depth = 5000 ft diameter = 2.441…, Extract the central value from a propagated uncertainty dict or bare float., Hand-calc for Natural Gas Tier 1: quantity = 10,000 scf HHV = 1,020 Btu/scf →…, TestTier1Combustion, TestTier1CombustionDiesel (+1 more)

### Community 15 - "Data Visualization Components"
Cohesion: 0.16
Nodes (13): BarChart(), LineChart(), DEFAULT_COLORS, PieChart(), Scope2Form(), SkeletonCard(), CarbonIntensity(), calculateForecast() (+5 more)

### Community 16 - "CSV Mapping Wizard"
Cohesion: 0.11
Nodes (10): ALL_FIELDS, autoDetectMapping(), ColumnMappingWizard(), Icons, OPTIONAL_FIELDS, REQUIRED_FIELDS, STEPS, categoryFromReason() (+2 more)

### Community 17 - "Scope 2 Management"
Cohesion: 0.14
Nodes (19): Grid Emission Factors - electricity_factors.py Central registry for indirect…, Scope2Emission, bulk_import_scope2(), _calc_cogen_allocation(), _calc_indirect_steam(), create_scope2_emission(), delete_scope2_emission(), get_emission_factors() (+11 more)

### Community 18 - "Error Handling and GWP"
Cohesion: 0.12
Nodes (10): ErrorBoundary, BOUNDARY_OPTIONS, DEFAULT_GWP, getActiveGwpFactors(), GWP_AR4, GWP_AR5, GWP_AR6, GWP_STANDARDS (+2 more)

### Community 19 - "Calculation Dispatcher Tests"
Cohesion: 0.16
Nodes (18): CalculationDispatcher, Routes a calculation request to the appropriate API 2021 calculator., CALC-03: Verify AGR calculates both CO2 mass balance and CH4 slip per API Table…, CALC-02: Verify Glycol Dehydrator parametric TEG solubility model, CALC-06: Verify Blowdown calculator applies thermodynamic T-correction, CALC-07: Verify completions multi-method calculation (rate/duration & GOR), test_agr_methane_slip_calculation(), test_blowdown_temperature_correction() (+10 more)

### Community 20 - "UI Header and Notifications"
Cohesion: 0.17
Nodes (12): TopBar(), getTypeConfig(), headerActionBtn, iconBtnStyle, NotificationCenter(), NotifRow(), relativeTime(), TYPE_CONFIG (+4 more)

### Community 21 - "Sentinel-5P Satellite Service"
Cohesion: 0.15
Nodes (12): Any, Retrieves a valid JWT access token from Copernicus CDSE with caching., Returns tile layer configuration, color ramps, and metadata for Leaflet., Queries Copernicus STAC/OData API for real Sentinel-5P methane data around…, Estimates methane mass emission rate (kg CH4/hr) from a Sentinel-5P column…, Service for querying ESA Copernicus Sentinel-5P TROPOMI methane measurements., Tests authentication against Copernicus Data Space Ecosystem Keycloak endpoint.…, Sentinel5PService (+4 more)

### Community 22 - "Bulk Import and Modals"
Cohesion: 0.15
Nodes (14): api, BulkImportModal(), COMPONENT_DATA, GasCompositionCalculator(), Modal(), Scope3Form(), ToastContext, ToastProvider() (+6 more)

### Community 23 - "API Middleware and Health"
Cohesion: 0.16
Nodes (13): errorhandler, listens_for, after_request(), before_request(), get_csrf_token(), health_check(), internal_error(), not_found_error() (+5 more)

### Community 24 - "Backend Dependencies"
Cohesion: 0.12
Nodes (16): bcryptjs, body-parser, cors, express, express-rate-limit, dependencies, bcryptjs, body-parser (+8 more)

### Community 25 - "End-to-End Integration Tests"
Cohesion: 0.19
Nodes (9): run_all_scenarios(), Emission, Facility, End-to-End Test for the CSV Uploader (Import Emissions Data Wizard) Tests the…, Tests the CSV upload endpoint with a mock CSV containing mixed scenarios.…, TestCSVUploaderE2E, User A must not be able to delete User B's emission record., User should be able to delete their own emission record. (+1 more)

### Community 26 - "Satellite and OGMP Integration"
Cohesion: 0.21
Nodes (15): ActivityLog, OgmpSurvey, export_satellite_to_ogmp(), get_facility_satellite_data(), get_satellite_layer_config(), _get_user_copernicus_credentials(), poll_new_satellite_passes(), route (+7 more)

### Community 28 - "Custom Factor Management"
Cohesion: 0.23
Nodes (14): CustomFactor, Permits superuser, admin, and it_admin roles, superuser_required(), create_custom_factor(), delete_custom_factor(), get_custom_factors(), import_custom_factors(), route (+6 more)

### Community 29 - "Database Models and Audit"
Cohesion: 0.21
Nodes (8): migrate_database(), MethaneSourceType, # NOTE: Do NOT call db.session.commit() here., Scope3Data, get_audit_filters(), get_audit_logs(), route, seed_data()

### Community 30 - "Production and OGMP Data"
Cohesion: 0.37
Nodes (13): ProductionData, login_required(), add_production(), bulk_import_production(), delete_ogmp_survey(), delete_production(), get_level_logs(), get_methane_sources() (+5 more)

### Community 31 - "Flaring and Pressure Conversion"
Cohesion: 0.21
Nodes (8): Dual-efficiency flaring model (API 5-3, 5-4) with API §4.2.1 thermodynamic…, normalize_gas_volume_to_standard(), Converts gauge or metric pressure to absolute pressure in psia., API Compendium 2021 §4.2.1: Converts gas volume measured at actual/operating…, Converts temperature value to Kelvin., to_kelvin(), to_psia(), API Equation 6-3 - Volume per unloading event with temperature correction:…

### Community 32 - "Reporting and Export Services"
Cohesion: 0.22
Nodes (12): LevelUpgradeLog, create_pdf_report(), export_emissions(), export_ogmp_excel(), generate_report(), route, Generate PDF report based on filters, Prevent formula injection (DDE/CSV injection) in Excel cells. (+4 more)

### Community 33 - "Scope 3 Management"
Cohesion: 0.23
Nodes (12): Scope3Emission, bulk_import_scope3(), create_scope3_emission(), delete_scope3_emission(), get_scope3_emissions(), route, Delete a Scope 3 emission record, Get all Scope 3 emissions (+4 more)

### Community 34 - "Combustion and Flaring Modules"
Cohesion: 0.29
Nodes (8): CombustionCalculator, FlaringCalculator, API Compendium 2021 - Section 5: Combustion and Flaring Implementation of…, Calculation tier following IPCC 2006 GL Vol.1 §2.4 hierarchy., Tier, test_flaring_calculator_basic(), test_flaring_calculator_specific_c1_c10(), test_stationary_combustion_calculator()

### Community 35 - "Fugitive and Tiered Tests"
Cohesion: 0.17
Nodes (7): =============================================================================…, Aggregates test results for a final summary table., Fugitive average — uses _generic_calculation with catalog EF. EF: ch4=0.1…, Tier 3 Combustion with gas composition (carbon mass balance): volume = 1000 scf…, SummaryResult, TestTier1FugitiveAverage, TestTier3CombustionGasComposition

### Community 36 - "Notification Services"
Cohesion: 0.27
Nodes (10): delete_all_notifications(), delete_notification(), dismiss_all(), get_notifications(), mark_read(), route, Permanently delete a single notification., Permanently delete all notifications for the current user. (+2 more)

### Community 37 - "Calculation Input Normalization"
Cohesion: 0.22
Nodes (5): Extracts an optional percentage (0-100) or fraction (0-1) converted to 0-1., Executes the calculation for the given process type. - Tier 1 (default /…, Normalizes a volume value to the specified target unit., Strictly extracts a required float parameter without falling back to defaults., Extracts a percentage (0-100) or fraction (0-1) strictly and converts to 0-1.

### Community 38 - "Calculation Edge Case Tests"
Cohesion: 0.20
Nodes (5): Zero quantity should produce zero emissions without crash., Negative quantity must raise ValueError., 1 MMscf = 1,000,000 scf — result should match 1M scf calculation., If GOR=0 and EF=0, result should be zero (no flash gas)., TestEdgeCases

### Community 40 - "PDF Report Generation"
Cohesion: 0.42
Nodes (8): createChartImage(), fetchAllReportData(), generateModernPDF(), generateReportCharts(), loadImage(), NOTE: When regionId is an array (multi-select), do NOT send facility_id param —, THEME, toRgba()

### Community 41 - "Satellite Service Tests"
Cohesion: 0.22
Nodes (7): Sentinel-5P (TROPOMI) Satellite Methane Service Connects to ESA Copernicus Data…, Verifies the physical 1D box model / mass-divergence plume flux estimation., Layer configuration returns ESA standard legend steps and unauthenticated…, Crucial policy test: Unconfigured / unauthenticated queries MUST return status…, test_sentinel5p_flux_calculation(), test_sentinel5p_layer_config_unauthenticated(), test_sentinel5p_strict_no_fake_data_when_unconfigured()

### Community 42 - "Project Metadata"
Cohesion: 0.22
Nodes (8): author, description, keywords, license, main, name, type, version

### Community 43 - "Electron Build Configuration"
Cohesion: 0.22
Nodes (9): build, appId, directories, productName, win, output, asar, icon (+1 more)

### Community 44 - "Database Migration Config"
Cohesion: 0.39
Nodes (7): get_engine(), get_engine_url(), get_metadata(), Run migrations in 'offline' mode. This configures the context with just a URL…, Run migrations in 'online' mode. In this scenario we need to create an Engine…, run_migrations_offline(), run_migrations_online()

### Community 46 - "Desktop App Dev Tools"
Cohesion: 0.29
Nodes (7): electron, electron-builder, nodemon, devDependencies, electron, electron-builder, nodemon

### Community 48 - "Drilling Mud Tests"
Cohesion: 0.29
Nodes (3): Mud Degassing Tier 1 (water-based mud): mud_volume = 500 m3 EF (water-based) =…, Oil-based mud uses EF=0.35 kg/m3., TestTier1DrillingMud

### Community 49 - "Build Artifacts"
Cohesion: 0.29
Nodes (6): files, main.js, node_modules/**/*, public/**/*, server.js, users_v2.db

### Community 51 - "Tier 1 Flaring Tests"
Cohesion: 0.33
Nodes (3): Flaring Tier 1 (default factor_source → _generic_calculation): Uses API_FACTORS…, Tier 1 flaring falls through to generic EF-based calculation., TestTier1Flaring

### Community 53 - "NPM Scripts"
Cohesion: 0.33
Nodes (6): scripts, build:exe, start, start:electron, start:web, test

### Community 54 - "Pitch Deck Builder"
Cohesion: 0.40
Nodes (4): add_card(), add_header(), Adds standard Startup Algeria header banner with accent bar and title., Creates a modern rounded rectangular card container.

### Community 58 - "Graphify Workflow Tools"
Cohesion: 0.67
Nodes (4): Graphify Rules, Graphify CLI, Graphify MCP, Graphify Workflow

### Community 59 - "Intensity Metrics API"
Cohesion: 0.50
Nodes (4): get_intensity_stats(), _query_intensity_stats(), Get intensity metrics (kg/BOE) per facility. Delegates to…, Pure query logic for /intensity-stats — returns a plain Python list. Get…

### Community 61 - "Platform Documentation"
Cohesion: 0.67
Nodes (3): Methane Intensity Analytics UI, Emission Calculation Engines, GHG Accounting & Reporting Platform README

## Knowledge Gaps
- **113 isolated node(s):** `name`, `private`, `version`, `type`, `dev` (+108 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **22 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `login_required()` connect `Production and OGMP Data` to `User and Auth Management`, `Dashboard and Goals API`, `Reporting and Export Services`, `Emission Factor Database`, `Notification Services`, `Scope 3 Management`, `Data Management Services`, `Scope 2 Management`, `Satellite and OGMP Integration`, `Intensity Metrics API`, `Custom Factor Management`, `Database Models and Audit`?**
  _High betweenness centrality (0.110) - this node is a cross-community bridge._
- **Why does `calculate_co2e()` connect `Emission Calculation Logic` to `User and Auth Management`, `Combustion and Flaring Modules`, `Fugitive and Tiered Tests`, `Calculation Base Classes`, `Calculation Input Normalization`, `Background Processing Engine`, `Midstream Calculation Modules`, `Flaring and Pressure Conversion`?**
  _High betweenness centrality (0.067) - this node is a cross-community bridge._
- **Why does `sqlite3` connect `API Middleware and Health` to `Backend Dependencies`, `Database Models and Audit`?**
  _High betweenness centrality (0.051) - this node is a cross-community bridge._
- **Are the 34 inferred relationships involving `CalculationDispatcher` (e.g. with `CombustionCalculator` and `FlaringCalculator`) actually correct?**
  _`CalculationDispatcher` has 34 INFERRED edges - model-reasoned connections that need verification._
- **Are the 7 inferred relationships involving `User` (e.g. with `TestCSVUploaderE2E` and `TestCalculationIntegrity`) actually correct?**
  _`User` has 7 INFERRED edges - model-reasoned connections that need verification._
- **What connects `name`, `private`, `version` to the rest of the system?**
  _113 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `User and Auth Management` be split into smaller, more focused modules?**
  _Cohesion score 0.07787698412698413 - nodes in this community are weakly interconnected._