# Graph Report - H2  (2026-08-11)

## Corpus Check
- 159 files · ~486,716 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1184 nodes · 2558 edges · 111 communities (84 shown, 27 thin omitted)
- Extraction: 96% EXTRACTED · 4% INFERRED · 0% AMBIGUOUS · INFERRED: 108 edges (avg confidence: 0.57)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `7e1af9f3`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- emissions.py
- dashboard.py
- Scope1Form.jsx
- emission_factors_routes.py
- dispatcher.py
- propagate_uncertainty
- dependencies
- devDependencies
- App.jsx
- test_emission_calculations.py
- api.js
- managedata.py
- Emissions.jsx
- User
- extract_val
- DashboardEnhanced.jsx
- UploadProgress.jsx
- scope2.py
- pages/ManageData.jsx
- CalculationDispatcher
- NotificationCenter.jsx
- Sentinel5PService
- Toast.jsx
- app.py
- dependencies
- models.py
- satellite.py
- GHGCalculator
- log_activity_and_notify
- auth.py
- login_required
- to_psia
- reports.py
- scope3.py
- combustion.py
- TestTier1FugitiveAverage
- emissionFactorsAPI.js
- ._require_float
- TestEdgeCases
- vented.py
- ModernReportGenerator.js
- calculate_co2e
- Project Metadata
- Electron Build Configuration
- env.py
- TestUnitConversions
- Desktop App Dev Tools
- TestTier1DrillingMud
- Build Artifacts
- TestTier1Flaring
- TestTier3Flaring
- NPM Scripts
- Pitch Deck Builder
- TestTier3TankFlashing
- TestTier3PneumaticDevices
- TestTier3Completions
- Graphify Workflow Tools
- facilities.py
- TestTier1Venting
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
- TestTier3LiquidsUnloading
- TestTier3CombustionGasComposition
- f

## God Nodes (most connected - your core abstractions)
1. `login_required()` - 120 edges
2. `CalculationDispatcher` - 57 edges
3. `calculate_co2e()` - 44 edges
4. `Facility` - 36 edges
5. `useToast()` - 34 edges
6. `propagate_uncertainty()` - 33 edges
7. `extract_val()` - 33 edges
8. `log_activity_and_notify()` - 33 edges
9. `useAuth()` - 32 edges
10. `User` - 31 edges

## Surprising Connections (you probably didn't know these)
- `Methane Intensity Analytics UI` --conceptually_related_to--> `Emission Calculation Engines`  [INFERRED]
  deck_assets/ui_methane.png → README.md
- `ManageDataInner()` --indirect_call--> `f()`  [INFERRED]
  new/client/src/pages/ManageData.jsx → temp_old/CarbonIntensity.jsx
- `seed_data()` --calls--> `User`  [INFERRED]
  seed_demo_data.py → new/server/models.py
- `seed_data()` --calls--> `Facility`  [INFERRED]
  seed_demo_data.py → new/server/models.py
- `seed_data()` --calls--> `Emission`  [INFERRED]
  seed_demo_data.py → new/server/models.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Graphify Tooling and Documentation** — agents_rules_graphify, agents_workflows_graphify, agents_rules_graphify_cli, agents_rules_graphify_mcp [EXTRACTED 1.00]
- **Emission Calculation & Visualization Flow** — new_server_calculations, deck_assets_ui_dashboard, deck_assets_chart_industry_emissions [INFERRED 0.80]

## Communities (111 total, 27 thin omitted)

### Community 0 - "emissions.py"
Cohesion: 0.13
Nodes (35): _build_mapping(), get_job_status(), _process_file_thread(), _process_row_custom_factors(), _process_row_facilities(), _process_row_mitigation(), _process_row_production(), _process_row_scope2() (+27 more)

### Community 1 - "dashboard.py"
Cohesion: 0.07
Nodes (49): cached, create_base_year_recalculation(), create_goal(), get_available_years(), get_base_year(), get_batch_dashboard_data(), get_categorical_breakdown(), get_dashboard_summary() (+41 more)

### Community 2 - "Scope1Form.jsx"
Cohesion: 0.15
Nodes (15): CustomDropdown(), AGRForm(), BlowdownForm(), CombustionForm(), HHV_REQUIRED_PROCESSES, CompletionsForm(), DehydratorForm(), DrillingForm() (+7 more)

### Community 3 - "emission_factors_routes.py"
Cohesion: 0.07
Nodes (39): get_factor_by_process_category(), get_factor_by_segment(), get_factors_by_segment_and_category(), Emission Factors Database - API Compendium 2021 Complete catalog from Sections…, Returns all emission factors applicable to the given segment. Args: segment…, Returns all emission factors for the given process category. Args:…, Returns all emission factors for a specific segment and process category. Args:…, Emission Factors Database - API Compendium 2021 Comprehensive emission factors… (+31 more)

### Community 4 - "dispatcher.py"
Cohesion: 0.08
Nodes (27): BaseCalculator, Validates that all required inputs are present and non-negative., Calculates absolute uncertainty and non-negative bounds at 95% CI., Formats the final calculation result into a standard structure., Base class for all API Compendium 2021 calculation modules. Provides common…, ComponentFugitiveCalculator, CompressorSealCalculator, EquipmentFugitiveCalculator (+19 more)

### Community 5 - "propagate_uncertainty"
Cohesion: 0.10
Nodes (23): API Section 7.2.3 - Compressor seals, Average Factor Method - counts * EF component_counts: dict of {type: count}, Average Factor Method for equipment - count * EF, API Equation 8-2: Indirect emissions from steam/heat Emissions = Energy /…, API Section 8.3 - Allocation of Cogeneration Emissions Methods: wri_efficiency,…, API Compendium 2021 §6.6 & GRI-GLYCalc Parametric Solubility Model (CALC-02…, API Compendium 2021 §6.5 & Table 6-5: - CO2 mass balance from amine sweetening…, API Equation 4-3/4-4: CO2 from carbon content CO2 = Mass * Carbon_Content *… (+15 more)

### Community 6 - "dependencies"
Cohesion: 0.05
Nodes (41): axios, chart.js, class-variance-authority, clsx, formik, framer-motion, jspdf, jspdf-autotable (+33 more)

### Community 7 - "devDependencies"
Cohesion: 0.05
Nodes (38): autoprefixer, eslint, @eslint/js, eslint-plugin-react-hooks, eslint-plugin-react-refresh, globals, devDependencies, autoprefixer (+30 more)

### Community 8 - "App.jsx"
Cohesion: 0.12
Nodes (25): AdminRoute(), App(), EmissionsMap, ITRoute(), NonITRoute(), PrivateRoute(), Layout(), Sidebar() (+17 more)

### Community 9 - "test_emission_calculations.py"
Cohesion: 0.16
Nodes (16): _process_row(), Validates a single mapped row and runs calculation via compute_emissions.…, get_active_gwp(), Global Warming Potential (GWP) Constants & Resolution Engine Supports IPCC AR4…, Dynamically resolve the active GWP factors dictionary based on standard and…, compute_emissions(), =============================================================================…, Tests the full _process_row pipeline to verify data gets into Emission fields… (+8 more)

### Community 10 - "api.js"
Cohesion: 0.13
Nodes (14): api, fetchCsrfToken(), Reports, autoDetectMapping(), ColumnMappingWizard(), Icons, STEPS, TEMPLATES (+6 more)

### Community 11 - "managedata.py"
Cohesion: 0.16
Nodes (27): BaseYear, BaseYearRecalculation, EmissionSource, Goal, MitigationProject, MitigationRecord, ReportingMetadata, add_base_year_recalculation() (+19 more)

### Community 12 - "Emissions.jsx"
Cohesion: 0.27
Nodes (9): Scope2Form(), Scope3Form(), STAGE_EMISSION_CALCULATOR, STAGE_FACTOR_CALCULATOR, STAGE_SCOPE1_SUB_SELECTION, STAGE_SCOPE2, STAGE_SCOPE3, STAGE_SCOPE_SELECTION (+1 more)

### Community 13 - "User"
Cohesion: 0.06
Nodes (31): User, seed_admin(), Tests the CSV upload endpoint with a mock CSV containing mixed scenarios.…, TestCSVUploaderE2E, app(), client(), logged_client(), fixture (+23 more)

### Community 14 - "extract_val"
Cohesion: 0.15
Nodes (7): extract_val(), Same calculation using m3 input — should produce same result after conversion., Diesel Tier 1: quantity = 500 gal HHV = 138,700 Btu/gal → 500 × 138,700 /…, Extract the central value from a propagated uncertainty dict or bare float., Hand-calc for Natural Gas Tier 1: quantity = 10,000 scf HHV = 1,020 Btu/scf →…, TestTier1Combustion, TestTier1CombustionDiesel

### Community 15 - "DashboardEnhanced.jsx"
Cohesion: 0.16
Nodes (11): BarChart(), LineChart(), DEFAULT_COLORS, PieChart(), SkeletonCard(), LayoutContext, LayoutProvider(), calculateForecast() (+3 more)

### Community 17 - "scope2.py"
Cohesion: 0.14
Nodes (19): Grid Emission Factors - electricity_factors.py Central registry for indirect…, Scope2Emission, bulk_import_scope2(), _calc_cogen_allocation(), _calc_indirect_steam(), create_scope2_emission(), delete_scope2_emission(), get_emission_factors() (+11 more)

### Community 18 - "pages/ManageData.jsx"
Cohesion: 0.13
Nodes (8): ErrorBoundary, BOUNDARY_OPTIONS, getActiveGwpFactors(), GWP_AR4, GWP_AR5, GWP_AR6, GWP_STANDARDS, ManageData()

### Community 19 - "CalculationDispatcher"
Cohesion: 0.11
Nodes (22): CalculationDispatcher, Extracts an optional percentage (0-100) or fraction (0-1) converted to 0-1., Routes a calculation request to the appropriate API 2021 calculator., Normalizes a volume value to the specified target unit., Aggregates test results for a final summary table., SummaryResult, CALC-03: Verify AGR calculates both CO2 mass balance and CH4 slip per API Table…, CALC-02: Verify Glycol Dehydrator parametric TEG solubility model (+14 more)

### Community 20 - "NotificationCenter.jsx"
Cohesion: 0.32
Nodes (6): getTypeConfig(), headerActionBtn, iconBtnStyle, NotifRow(), relativeTime(), TYPE_CONFIG

### Community 21 - "Sentinel5PService"
Cohesion: 0.10
Nodes (19): Any, Sentinel-5P (TROPOMI) Satellite Methane Service Connects to ESA Copernicus Data…, Retrieves a valid JWT access token from Copernicus CDSE with caching., Returns tile layer configuration, color ramps, and metadata for Leaflet., Queries Copernicus STAC/OData API for real Sentinel-5P methane data around…, Service for querying ESA Copernicus Sentinel-5P TROPOMI methane measurements., Estimates methane mass emission rate (kg CH4/hr) from a Sentinel-5P column…, Tests authentication against Copernicus Data Space Ecosystem Keycloak endpoint.… (+11 more)

### Community 22 - "Toast.jsx"
Cohesion: 0.17
Nodes (9): BulkImportModal(), COMPONENT_DATA, GasCompositionCalculator(), Modal(), ToastContext, ToastProvider(), getRoleMeta(), ROLE_META (+1 more)

### Community 23 - "app.py"
Cohesion: 0.16
Nodes (15): errorhandler, listens_for, after_request(), before_request(), get_csrf_token(), health_check(), internal_error(), not_found_error() (+7 more)

### Community 24 - "dependencies"
Cohesion: 0.13
Nodes (15): bcryptjs, body-parser, cors, express, express-rate-limit, dependencies, bcryptjs, body-parser (+7 more)

### Community 25 - "models.py"
Cohesion: 0.17
Nodes (13): run_all_scenarios(), migrate_database(), CbamProductExport, Emission, Facility, MethaneSourceType, # NOTE: Do NOT call db.session.commit() here., Scope3Data (+5 more)

### Community 26 - "satellite.py"
Cohesion: 0.18
Nodes (16): ActivityLog, Notification, OgmpSurvey, export_satellite_to_ogmp(), get_facility_satellite_data(), get_satellite_layer_config(), _get_user_copernicus_credentials(), poll_new_satellite_passes() (+8 more)

### Community 28 - "log_activity_and_notify"
Cohesion: 0.23
Nodes (15): CustomFactor, Permits superuser, admin, and it_admin roles, superuser_required(), create_custom_factor(), delete_custom_factor(), get_custom_factors(), import_custom_factors(), route (+7 more)

### Community 29 - "auth.py"
Cohesion: 0.17
Nodes (21): limit, admin_required(), change_password(), delete_user(), get_settings(), get_users(), is_safe_image_url(), login() (+13 more)

### Community 30 - "login_required"
Cohesion: 0.17
Nodes (27): LevelUpgradeLog, ProductionData, login_required(), add_production(), bulk_import_production(), delete_cbam_export(), delete_ogmp_survey(), delete_production() (+19 more)

### Community 31 - "to_psia"
Cohesion: 0.21
Nodes (8): Dual-efficiency flaring model (API 5-3, 5-4) with API §4.2.1 thermodynamic…, normalize_gas_volume_to_standard(), API Compendium 2021 §4.2.1: Converts gas volume measured at actual/operating…, Converts temperature value to Kelvin., Converts gauge or metric pressure to absolute pressure in psia., to_kelvin(), to_psia(), API Equation 6-3 - Volume per unloading event with temperature correction:…

### Community 32 - "reports.py"
Cohesion: 0.24
Nodes (11): create_pdf_report(), export_emissions(), export_ogmp_excel(), generate_report(), route, Generate PDF report based on filters, Prevent formula injection (DDE/CSV injection) in Excel cells., Export emissions data as PDF - GET version for frontend integration (+3 more)

### Community 33 - "scope3.py"
Cohesion: 0.19
Nodes (14): Calculation tier following IPCC 2006 GL Vol.1 §2.4 hierarchy., Tier, Scope3Emission, bulk_import_scope3(), create_scope3_emission(), delete_scope3_emission(), get_scope3_emissions(), route (+6 more)

### Community 34 - "combustion.py"
Cohesion: 0.26
Nodes (7): CombustionCalculator, FlaringCalculator, API Compendium 2021 - Section 5: Combustion and Flaring Implementation of…, Standard fuel-based combustion calculation with API §4.2.1 thermodynamic…, test_flaring_calculator_basic(), test_flaring_calculator_specific_c1_c10(), test_stationary_combustion_calculator()

### Community 36 - "emissionFactorsAPI.js"
Cohesion: 0.18
Nodes (8): EmissionFactorOption(), Scope1Form(), convertActivityData(), formatUncertainty(), getFactorUncertainty(), getProcessTypesForSegment(), getSegmentBgColor(), getSegmentColor()

### Community 38 - "TestEdgeCases"
Cohesion: 0.20
Nodes (5): Zero quantity should produce zero emissions without crash., Negative quantity must raise ValueError., 1 MMscf = 1,000,000 scf — result should match 1M scf calculation., If GOR=0 and EF=0, result should be zero (no flash gas)., TestEdgeCases

### Community 39 - "vented.py"
Cohesion: 0.19
Nodes (8): BlowdownCalculator, PneumaticDeviceCalculator, API Compendium 2021 - Section 6: Vented and Process Emissions Implementation of…, API Eq. 6-4: Vessel/Pipeline Blowdown (Depressurization) V_std = V_physical *…, TankFlashingCalculator, test_blowdown_calculator(), test_pneumatics_calculator(), test_tanks_calculator()

### Community 40 - "ModernReportGenerator.js"
Cohesion: 0.36
Nodes (9): DEFAULT_GWP, createChartImage(), fetchAllReportData(), generateModernPDF(), generateReportCharts(), loadImage(), NOTE: When regionId is an array (multi-select), do NOT send facility_id param —, THEME (+1 more)

### Community 41 - "calculate_co2e"
Cohesion: 0.19
Nodes (7): Executes the calculation for the given process type. - Tier 1 (default /…, Standard Quantity * EF fallback with unit handling and tier-aware uncertainty., calculate_co2e(), Calculates CO2e using dynamically resolved GWPs (AR4/AR5/AR6)., Verify the CO2e aggregation function is internally consistent., TestCO2ECalculation, test_calculate_co2e_dynamic()

### Community 42 - "Project Metadata"
Cohesion: 0.22
Nodes (8): author, description, keywords, license, main, name, type, version

### Community 43 - "Electron Build Configuration"
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

### Community 49 - "Build Artifacts"
Cohesion: 0.29
Nodes (6): files, main.js, node_modules/**/*, public/**/*, server.js, users_v2.db

### Community 51 - "TestTier1Flaring"
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

### Community 59 - "facilities.py"
Cohesion: 0.26
Nodes (10): clear_dashboard_cache(), add_facility(), delete_facility(), get_all_regions(), get_facilities(), import_facilities(), route, Bulk import facilities (+2 more)

### Community 61 - "Platform Documentation"
Cohesion: 0.67
Nodes (3): Methane Intensity Analytics UI, Emission Calculation Engines, GHG Accounting & Reporting Platform README

### Community 69 - "GHGUser"
Cohesion: 0.31
Nodes (3): HttpUser, GHGUser, task

## Knowledge Gaps
- **114 isolated node(s):** `name`, `private`, `version`, `type`, `dev` (+109 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **27 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `login_required()` connect `login_required` to `emissions.py`, `dashboard.py`, `reports.py`, `emission_factors_routes.py`, `scope3.py`, `managedata.py`, `scope2.py`, `app.py`, `satellite.py`, `facilities.py`, `log_activity_and_notify`, `auth.py`?**
  _High betweenness centrality (0.084) - this node is a cross-community bridge._
- **Why does `sqlite3` connect `sqlite3` to `models.py`, `app.py`?**
  _High betweenness centrality (0.065) - this node is a cross-community bridge._
- **Why does `calculate_co2e()` connect `calculate_co2e` to `emissions.py`, `combustion.py`, `dispatcher.py`, `propagate_uncertainty`, `vented.py`, `test_emission_calculations.py`, `to_psia`?**
  _High betweenness centrality (0.058) - this node is a cross-community bridge._
- **Are the 33 inferred relationships involving `CalculationDispatcher` (e.g. with `CombustionCalculator` and `FlaringCalculator`) actually correct?**
  _`CalculationDispatcher` has 33 INFERRED edges - model-reasoned connections that need verification._
- **Are the 7 inferred relationships involving `Facility` (e.g. with `TestCSVUploaderE2E` and `TestCalculationIntegrity`) actually correct?**
  _`Facility` has 7 INFERRED edges - model-reasoned connections that need verification._
- **What connects `name`, `private`, `version` to the rest of the system?**
  _114 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `emissions.py` be split into smaller, more focused modules?**
  _Cohesion score 0.13063063063063063 - nodes in this community are weakly interconnected._