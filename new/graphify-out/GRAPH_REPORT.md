# Graph Report - new  (2026-08-15)

## Corpus Check
- 152 files · ~236,705 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1169 nodes · 2609 edges · 86 communities (75 shown, 11 thin omitted)
- Extraction: 96% EXTRACTED · 4% INFERRED · 0% AMBIGUOUS · INFERRED: 97 edges (avg confidence: 0.55)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `0cb8d849`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- Facility
- dashboard.py
- emission_factors_routes.py
- dispatcher.py
- dependencies
- devDependencies
- Scope1ImportWizard.jsx
- auth.py
- calculate_co2e
- DashboardEnhanced.jsx
- models.py
- useToast
- App.jsx
- propagate_uncertainty
- Scope1Form.jsx
- Sentinel5PService
- emissions.py
- login_required
- CalculationDispatcher
- ManageData.jsx
- test_emission_calculations.py
- app.py
- extract_val
- emissionFactorsAPI.js
- satellite.py
- data.py
- get_active_gwp
- ModernReportGenerator.js
- combustion.py
- GHGCalculator
- scope3.py
- background_processor.py
- superuser_required
- notifications.py
- export_emissions
- TestTier1Combustion
- TestEdgeCases
- NotificationCenter.jsx
- Emissions.jsx
- GHGUser
- to_psia
- env.py
- TestUnitConversions
- test_final.py
- test_final_v2.py
- test_final_v3.py
- test_pipeline.py
- test_pipeline_robust.py
- TestTier1DrillingMud
- generate_1k_comprehensive.py
- TestTier1Flaring
- TestTier3TankFlashing
- TestTier3PneumaticDevices
- TestTier3Completions
- .dispatch
- ._require_float
- TestTier3LiquidsUnloading
- TestTier1FugitiveAverage
- TestTier3CombustionGasComposition
- .calculate_uncertainty

## God Nodes (most connected - your core abstractions)
1. `login_required()` - 120 edges
2. `CalculationDispatcher` - 57 edges
3. `calculate_co2e()` - 44 edges
4. `Facility` - 36 edges
5. `useToast()` - 34 edges
6. `log_activity_and_notify()` - 34 edges
7. `propagate_uncertainty()` - 33 edges
8. `extract_val()` - 33 edges
9. `useAuth()` - 32 edges
10. `User` - 31 edges

## Surprising Connections (you probably didn't know these)
- `_process_file_thread()` --indirect_call--> `compute_emissions()`  [INFERRED]
  server/background_processor.py → server/calculations/legacy_engine.py
- `CombustionCalculator` --uses--> `BaseCalculator`  [INFERRED]
  server/calculations/combustion.py → server/calculations/base.py
- `FlaringCalculator` --uses--> `BaseCalculator`  [INFERRED]
  server/calculations/combustion.py → server/calculations/base.py
- `DehydratorCalculator` --uses--> `BaseCalculator`  [INFERRED]
  server/calculations/midstream.py → server/calculations/base.py
- `CalculationDispatcher` --uses--> `CombustionCalculator`  [INFERRED]
  server/calculations/dispatcher.py → server/calculations/combustion.py

## Import Cycles
- None detected.

## Communities (86 total, 11 thin omitted)

### Community 0 - "Facility"
Cohesion: 0.06
Nodes (38): run_all_scenarios(), Emission, Facility, User, seed_admin(), End-to-End Test for the CSV Uploader (Import Emissions Data Wizard) Tests the…, Tests the CSV upload endpoint with a mock CSV containing mixed scenarios.…, TestCSVUploaderE2E (+30 more)

### Community 1 - "dashboard.py"
Cohesion: 0.07
Nodes (48): cached, BaseYearRecalculation, create_base_year_recalculation(), get_available_years(), get_base_year(), get_batch_dashboard_data(), get_categorical_breakdown(), get_dashboard_summary() (+40 more)

### Community 2 - "emission_factors_routes.py"
Cohesion: 0.07
Nodes (39): get_factor_by_process_category(), get_factor_by_segment(), get_factors_by_segment_and_category(), Emission Factors Database - API Compendium 2021 Complete catalog from Sections…, Returns all emission factors applicable to the given segment. Args: segment…, Returns all emission factors for the given process category. Args:…, Returns all emission factors for a specific segment and process category. Args:…, Emission Factors Database - API Compendium 2021 Comprehensive emission factors… (+31 more)

### Community 3 - "dispatcher.py"
Cohesion: 0.10
Nodes (23): BaseCalculator, Validates that all required inputs are present and non-negative., Formats the final calculation result into a standard structure., Base class for all API Compendium 2021 calculation modules. Provides common…, ComponentFugitiveCalculator, CompressorSealCalculator, EquipmentFugitiveCalculator, API Compendium 2021 - Section 7: Fugitive Emissions Implementation of equations… (+15 more)

### Community 4 - "dependencies"
Cohesion: 0.05
Nodes (41): axios, chart.js, class-variance-authority, dependencies, axios, chart.js, class-variance-authority, clsx (+33 more)

### Community 5 - "devDependencies"
Cohesion: 0.05
Nodes (38): autoprefixer, devDependencies, autoprefixer, eslint, @eslint/js, eslint-plugin-react-hooks, eslint-plugin-react-refresh, globals (+30 more)

### Community 6 - "Scope1ImportWizard.jsx"
Cohesion: 0.06
Nodes (18): autoDetect(), FIELD_GROUPS, Icon, PROCESS_CATALOGUE, Scope1ImportWizard(), STEPS, autoDetect(), FIELD_GROUPS (+10 more)

### Community 7 - "auth.py"
Cohesion: 0.12
Nodes (31): limit, admin_required(), change_password(), delete_user(), get_settings(), get_users(), is_safe_image_url(), login() (+23 more)

### Community 8 - "calculate_co2e"
Cohesion: 0.10
Nodes (19): API Section 7.2.3 - Compressor seals, Average Factor Method - counts * EF component_counts: dict of {type: count}, Average Factor Method for equipment - count * EF, API Equation 8-2: Indirect emissions from steam/heat Emissions = Energy /…, API Section 8.3 - Allocation of Cogeneration Emissions Methods: wri_efficiency,…, API Compendium 2021 §6.5 & Table 6-5: - CO2 mass balance from amine sweetening…, API Equation 4-3/4-4: CO2 from carbon content CO2 = Mass * Carbon_Content *…, Map factor_source string to a Tier integer. factor_source values: 'default' |… (+11 more)

### Community 9 - "DashboardEnhanced.jsx"
Cohesion: 0.13
Nodes (19): BarChart(), LineChart(), DEFAULT_COLORS, PieChart(), LoadingSpinner(), Scope2Form(), SkeletonCard(), getActiveGwpFactors() (+11 more)

### Community 10 - "models.py"
Cohesion: 0.09
Nodes (26): Grid Emission Factors - electricity_factors.py Central registry for indirect…, migrate_database(), Goal, MethaneSourceType, # NOTE: Do NOT call db.session.commit() here., Scope2Emission, Scope3Data, create_goal() (+18 more)

### Community 11 - "useToast"
Cohesion: 0.13
Nodes (17): api, EmissionsMap, BulkImportModal(), COMPONENT_DATA, GasCompositionCalculator(), Modal(), Scope3Form(), ToastContext (+9 more)

### Community 12 - "App.jsx"
Cohesion: 0.12
Nodes (19): fetchCsrfToken(), AdminRoute(), App(), ITRoute(), NonITRoute(), PrivateRoute(), Reports, Layout() (+11 more)

### Community 13 - "propagate_uncertainty"
Cohesion: 0.11
Nodes (19): API Compendium 2021 - Section 8: Indirect Emissions Implementation of indirect…, DehydratorCalculator, API Compendium 2021 - Section 6: Midstream & Process Emissions Implementation…, API Compendium 2021 §6.6 & GRI-GLYCalc Parametric Solubility Model (CALC-02…, API Compendium 2021 - Section 4: Calculation Fundamentals Implementation of…, combine_uncertainties_product(), combine_uncertainties_sum(), propagate_uncertainty() (+11 more)

### Community 14 - "Scope1Form.jsx"
Cohesion: 0.15
Nodes (15): CustomDropdown(), AGRForm(), BlowdownForm(), CombustionForm(), HHV_REQUIRED_PROCESSES, CompletionsForm(), DehydratorForm(), DrillingForm() (+7 more)

### Community 15 - "Sentinel5PService"
Cohesion: 0.10
Nodes (19): Any, Sentinel-5P (TROPOMI) Satellite Methane Service Connects to ESA Copernicus Data…, Retrieves a valid JWT access token from Copernicus CDSE with caching., Returns tile layer configuration, color ramps, and metadata for Leaflet., Queries Copernicus STAC/OData API for real Sentinel-5P methane data around…, Service for querying ESA Copernicus Sentinel-5P TROPOMI methane measurements., Estimates methane mass emission rate (kg CH4/hr) from a Sentinel-5P column…, Tests authentication against Copernicus Data Space Ecosystem Keycloak endpoint.… (+11 more)

### Community 16 - "emissions.py"
Cohesion: 0.19
Nodes (25): get_job_status(), add_bulk_upload(), add_emission(), bulk_delete_emissions(), delete_emission(), _escape_like(), export_emissions(), get_csv_template() (+17 more)

### Community 17 - "login_required"
Cohesion: 0.22
Nodes (25): BaseYear, MitigationProject, MitigationRecord, ReportingMetadata, login_required(), add_base_year_recalculation(), add_mitigation(), add_or_update_goal() (+17 more)

### Community 18 - "CalculationDispatcher"
Cohesion: 0.13
Nodes (20): CalculationDispatcher, Extracts an optional percentage (0-100) or fraction (0-1) converted to 0-1., Routes a calculation request to the appropriate API 2021 calculator., Normalizes a volume value to the specified target unit., CALC-03: Verify AGR calculates both CO2 mass balance and CH4 slip per API Table…, CALC-02: Verify Glycol Dehydrator parametric TEG solubility model, CALC-06: Verify Blowdown calculator applies thermodynamic T-correction, CALC-07: Verify completions multi-method calculation (rate/duration & GOR) (+12 more)

### Community 19 - "ManageData.jsx"
Cohesion: 0.11
Nodes (8): autoDetectMapping(), ColumnMappingWizard(), Icons, STEPS, TEMPLATES, ErrorBoundary, ManageData(), ManageDataInner()

### Community 20 - "test_emission_calculations.py"
Cohesion: 0.17
Nodes (13): _process_row(), Validates a single mapped row and runs calculation via compute_emissions.…, compute_emissions(), =============================================================================…, Tests the full _process_row pipeline to verify data gets into Emission fields…, _process_row should return an Emission object with correct fields., Row with unknown facility should return an error, not crash., Row with no date should return a date error. (+5 more)

### Community 21 - "app.py"
Cohesion: 0.15
Nodes (16): errorhandler, listens_for, after_request(), before_request(), get_csrf_token(), health_check(), internal_error(), not_found_error() (+8 more)

### Community 22 - "extract_val"
Cohesion: 0.14
Nodes (8): extract_val(), Diesel Tier 1: quantity = 500 gal HHV = 138,700 Btu/gal → 500 × 138,700 /…, Flaring Tier 3 (factor_source='specific') — Dual efficiency model: gas_volume =…, Blowdown Tier 1 (default): vessel volume = 5 m3 physical pressure = 100 psig →…, Extract the central value from a propagated uncertainty dict or bare float., TestTier1CombustionDiesel, TestTier1Venting, TestTier3Flaring

### Community 23 - "emissionFactorsAPI.js"
Cohesion: 0.18
Nodes (8): EmissionFactorOption(), Scope1Form(), convertActivityData(), formatUncertainty(), getFactorUncertainty(), getProcessTypesForSegment(), getSegmentBgColor(), getSegmentColor()

### Community 24 - "satellite.py"
Cohesion: 0.18
Nodes (16): ActivityLog, Notification, OgmpSurvey, export_satellite_to_ogmp(), get_facility_satellite_data(), get_satellite_layer_config(), _get_user_copernicus_credentials(), poll_new_satellite_passes() (+8 more)

### Community 25 - "data.py"
Cohesion: 0.22
Nodes (17): CbamProductExport, LevelUpgradeLog, ProductionData, add_production(), bulk_import_production(), delete_cbam_export(), delete_ogmp_survey(), delete_production() (+9 more)

### Community 26 - "get_active_gwp"
Cohesion: 0.16
Nodes (9): get_active_gwp(), Global Warming Potential (GWP) Constants & Resolution Engine Supports IPCC AR4…, Dynamically resolve the active GWP factors dictionary based on standard and…, DummyFacility, MockDB, MockSession, test_calculate_co2e_dynamic(), test_constants_and_helpers() (+1 more)

### Community 27 - "ModernReportGenerator.js"
Cohesion: 0.17
Nodes (14): BOUNDARY_OPTIONS, DEFAULT_GWP, GWP_AR4, GWP_AR5, GWP_AR6, GWP_STANDARDS, createChartImage(), fetchAllReportData() (+6 more)

### Community 28 - "combustion.py"
Cohesion: 0.19
Nodes (10): CombustionCalculator, FlaringCalculator, API Compendium 2021 - Section 5: Combustion and Flaring Implementation of…, Dual-efficiency flaring model (API 5-3, 5-4) with API §4.2.1 thermodynamic…, Standard fuel-based combustion calculation with API §4.2.1 thermodynamic…, normalize_gas_volume_to_standard(), API Compendium 2021 §4.2.1: Converts gas volume measured at actual/operating…, test_flaring_calculator_basic() (+2 more)

### Community 30 - "scope3.py"
Cohesion: 0.19
Nodes (14): Calculation tier following IPCC 2006 GL Vol.1 §2.4 hierarchy., Tier, Scope3Emission, bulk_import_scope3(), create_scope3_emission(), delete_scope3_emission(), get_scope3_emissions(), route (+6 more)

### Community 31 - "background_processor.py"
Cohesion: 0.29
Nodes (12): _build_mapping(), _process_file_thread(), _process_row_custom_factors(), _process_row_facilities(), _process_row_mitigation(), _process_row_production(), _process_row_scope2(), _process_row_scope3() (+4 more)

### Community 32 - "superuser_required"
Cohesion: 0.19
Nodes (13): Permits superuser, admin, and it_admin roles, superuser_required(), create_custom_factor(), delete_custom_factor(), get_custom_factors(), import_custom_factors(), route, Get all custom emission factors (+5 more)

### Community 33 - "notifications.py"
Cohesion: 0.27
Nodes (10): delete_all_notifications(), delete_notification(), dismiss_all(), get_notifications(), mark_read(), route, Permanently delete a single notification., Permanently delete all notifications for the current user. (+2 more)

### Community 34 - "export_emissions"
Cohesion: 0.20
Nodes (11): create_pdf_report(), export_emissions(), export_ogmp_excel(), generate_report(), route, Generate PDF report based on filters, Prevent formula injection (DDE/CSV injection) in Excel cells., Export emissions data as PDF - GET version for frontend integration (+3 more)

### Community 35 - "TestTier1Combustion"
Cohesion: 0.20
Nodes (3): Same calculation using m3 input — should produce same result after conversion., Hand-calc for Natural Gas Tier 1: quantity = 10,000 scf HHV = 1,020 Btu/scf →…, TestTier1Combustion

### Community 36 - "TestEdgeCases"
Cohesion: 0.20
Nodes (5): Zero quantity should produce zero emissions without crash., Negative quantity must raise ValueError., 1 MMscf = 1,000,000 scf — result should match 1M scf calculation., If GOR=0 and EF=0, result should be zero (no flash gas)., TestEdgeCases

### Community 37 - "NotificationCenter.jsx"
Cohesion: 0.28
Nodes (7): getTypeConfig(), headerActionBtn, iconBtnStyle, NotificationCenter(), NotifRow(), relativeTime(), TYPE_CONFIG

### Community 38 - "Emissions.jsx"
Cohesion: 0.33
Nodes (7): Emissions(), STAGE_EMISSION_CALCULATOR, STAGE_FACTOR_CALCULATOR, STAGE_SCOPE1_SUB_SELECTION, STAGE_SCOPE2, STAGE_SCOPE3, STAGE_SCOPE_SELECTION

### Community 39 - "GHGUser"
Cohesion: 0.31
Nodes (3): HttpUser, GHGUser, task

### Community 40 - "to_psia"
Cohesion: 0.31
Nodes (5): Converts temperature value to Kelvin., Converts gauge or metric pressure to absolute pressure in psia., to_kelvin(), to_psia(), API Equation 6-3 - Volume per unloading event with temperature correction:…

### Community 41 - "env.py"
Cohesion: 0.39
Nodes (7): get_engine(), get_engine_url(), get_metadata(), Run migrations in 'offline' mode. This configures the context with just a URL…, Run migrations in 'online' mode. In this scenario we need to create an Engine…, run_migrations_offline(), run_migrations_online()

### Community 43 - "test_final.py"
Cohesion: 0.29
Nodes (3): DummyFacility, MockDB, MockSession

### Community 44 - "test_final_v2.py"
Cohesion: 0.29
Nodes (3): DummyFacility, MockDB, MockSession

### Community 45 - "test_final_v3.py"
Cohesion: 0.29
Nodes (3): DummyFacility, MockDB, MockSession

### Community 46 - "test_pipeline.py"
Cohesion: 0.29
Nodes (3): DummyFacility, MockDB, MockSession

### Community 47 - "test_pipeline_robust.py"
Cohesion: 0.29
Nodes (3): DummyFacility, MockDB, MockSession

### Community 49 - "TestTier1DrillingMud"
Cohesion: 0.29
Nodes (3): Mud Degassing Tier 1 (water-based mud): mud_volume = 500 m3 EF (water-based) =…, Oil-based mud uses EF=0.35 kg/m3., TestTier1DrillingMud

### Community 50 - "generate_1k_comprehensive.py"
Cohesion: 0.33
Nodes (3): gas_comp(), Generate a comprehensive 1,000-row Scope 1 test CSV that covers: - All 13…, Return a realistic gas composition that sums to ~100%.

### Community 51 - "TestTier1Flaring"
Cohesion: 0.33
Nodes (3): Flaring Tier 1 (default factor_source → _generic_calculation): Uses API_FACTORS…, Tier 1 flaring falls through to generic EF-based calculation., TestTier1Flaring

## Knowledge Gaps
- **74 isolated node(s):** `name`, `private`, `version`, `type`, `dev` (+69 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **11 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `login_required()` connect `login_required` to `superuser_required`, `dashboard.py`, `emission_factors_routes.py`, `notifications.py`, `export_emissions`, `auth.py`, `models.py`, `emissions.py`, `app.py`, `satellite.py`, `data.py`, `scope3.py`?**
  _High betweenness centrality (0.097) - this node is a cross-community bridge._
- **Why does `calculate_co2e()` connect `calculate_co2e` to `dispatcher.py`, `to_psia`, `propagate_uncertainty`, `emissions.py`, `test_emission_calculations.py`, `.dispatch`, `get_active_gwp`, `combustion.py`, `background_processor.py`?**
  _High betweenness centrality (0.048) - this node is a cross-community bridge._
- **Why does `get_active_gwp()` connect `get_active_gwp` to `dashboard.py`, `dispatcher.py`, `calculate_co2e`, `test_final.py`, `propagate_uncertainty`, `test_pipeline_robust.py`, `emissions.py`, `test_emission_calculations.py`, `.dispatch`, `background_processor.py`?**
  _High betweenness centrality (0.045) - this node is a cross-community bridge._
- **Are the 33 inferred relationships involving `CalculationDispatcher` (e.g. with `CombustionCalculator` and `FlaringCalculator`) actually correct?**
  _`CalculationDispatcher` has 33 INFERRED edges - model-reasoned connections that need verification._
- **Are the 6 inferred relationships involving `Facility` (e.g. with `TestCSVUploaderE2E` and `TestCalculationIntegrity`) actually correct?**
  _`Facility` has 6 INFERRED edges - model-reasoned connections that need verification._
- **What connects `name`, `private`, `version` to the rest of the system?**
  _74 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Facility` be split into smaller, more focused modules?**
  _Cohesion score 0.0629800307219662 - nodes in this community are weakly interconnected._