# Graph Report - H2  (2026-09-17)

## Corpus Check
- 286 files · ~631,358 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 2536 nodes · 5328 edges · 211 communities (158 shown, 53 thin omitted)
- Extraction: 91% EXTRACTED · 9% INFERRED · 0% AMBIGUOUS · INFERRED: 487 edges (avg confidence: 0.52)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `0b21e68a`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- emissions.py
- login_required
- Scope1Form.jsx
- emission_factors_routes.py
- Sentinel5PService
- calculate_co2e
- dependencies
- devDependencies
- DashboardEnhanced.jsx
- app.py
- pages/ManageData.jsx
- dashboard.py
- test_uncertainty.py
- test_api_security.py
- satellite.py
- log_activity_and_notify
- NotificationCenter.jsx
- test_tier_scope_kpi_numerical.py
- useToast
- CalculationDispatcher
- App.jsx
- 5. CHANGELOG & DRIFT LOG
- test_csv_engine_matrix.py
- test_audit.py
- dependencies
- TestTier1DrillingMud
- Scope1ImportWizard.jsx
- AnomalyDetector
- Backend (Server)
- Emission
- test_all_apis_health.py
- TestCO2ECalculation
- audit.py
- test_ui_calculation_parity.py
- Frontend (Client)
- Scope2Form.jsx
- Tasks: [FEATURE NAME]
- test_qaqc_diagnostics.py
- TestEdgeCases
- test_audit_remediation.py
- get_allowed_facility_ids
- Project Metadata
- build
- env.py
- test_audit_bug_fixes.py
- Desktop App Dev Tools
- files
- TestTier1Flaring
- test_vented.py
- NPM Scripts
- Pitch Deck Builder
- Reports.jsx
- clear_dashboard_cache
- TestAllProcessTypesTier3
- Graphify Workflow Tools
- Tasks: [FEATURE NAME]
- Feature Specification: QA/QC Module (IPCC & ISO 14064 Compliant)
- Platform Documentation
- API and UI Routes
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
- TestBoundaryResilienceAPI
- test_deep_button_audit.py
- get_active_gwp
- class-variance-authority
- Feature Specification: Batch Approve/Reject Pending Records
- background_processor.py
- new/.specify/scripts/powershell/common.ps1
- .specify/scripts/powershell/common.ps1
- Facility
- Feature Specification: [FEATURE NAME]
- Feature Specification: [FEATURE NAME]
- extract_val
- Implementation Tasks: QA/QC Module (IPCC & ISO 14064)
- chart.js
- Core Principles
- Core Principles
- Core Principles
- Core Principles
- client/package.json
- test_master_button_audit.py
- TestUnauthenticatedAccess
- Implementation Tasks: Batch Approve/Reject Pending Records
- Implementation Plan: [FEATURE]
- Implementation Plan: [FEATURE]
- Existing Entities to Modify
- .test_bidirectional_conversions_exactness
- .test_confidence_interval_bounds_ordering
- status.py
- .test_zero_emission_uncertainty_bounds
- generate_1k_comprehensive.py
- new/.specify/scripts/powershell/create-new-feature.ps1
- .specify/scripts/powershell/create-new-feature.ps1
- [CHECKLIST TYPE] Checklist: [FEATURE NAME]
- [CHECKLIST TYPE] Checklist: [FEATURE NAME]
- Research & Design Decisions: Batch Approve/Reject
- Research & Design Decisions: QA/QC Module (IPCC & ISO 14064)
- @vitejs/plugin-react
- combustion.py
- formik
- .get_token
- papaparse
- react
- react-dom
- tailwind-merge
- File-by-File Analysis
- jspdf-autotable
- .test_scope2_location_based_grid_averages
- .test_scope2_market_based_contractual_instruments
- reports.py
- TestUnitConversions
- .test_scope3_tier2_average_data_transport
- .test_scope3_category11_use_of_sold_products_oil_and_gas
- 001-batch-approve-reject/data-model.md
- 001-batch-approve-reject/quickstart.md
- 002-qa-qc-ipcc-iso14064/quickstart.md
- test_all_process_types_matrix.py
- .test_boe_production_normalization_exactness
- GHGCalculator
- .test_scope3_tier1_spend_based_eeio
- .test_carbon_intensity_metric_equations
- test_deep_injection_matrix.py
- .test_scope3_tier3_supplier_specific_pcf
- sqlite3
- srss_inventory
- .test_coverage_factor_and_non_negative_bounds
- test_ui_audit_visuals.mjs
- .test_methane_loss_rate_ogmp_equation
- .test_flaring_rate_percentage_equation
- .test_epa_wec_part99_fee_schedules_and_thresholds
- User
- disable_limiter_for_tests
- .test_ogmp_facility_level_5_requires_level_4_bottom_up
- TestUnitConversionInvarianceMatrix
- framer-motion
- .test_api_example_4_5_flaring_dual_efficiency
- scope2.py
- .test_scope1_tier1_and_tier3_pneumatic_bleed

## God Nodes (most connected - your core abstractions)
1. `login_required()` - 131 edges
2. `get_current_user()` - 104 edges
3. `CalculationDispatcher` - 99 edges
4. `User` - 96 edges
5. `Facility` - 89 edges
6. `Emission` - 77 edges
7. `Backend (Server)` - 74 edges
8. `get_allowed_facility_ids()` - 71 edges
9. `Frontend (Client)` - 66 edges
10. `log_activity_and_notify()` - 57 edges

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

## Communities (211 total, 53 thin omitted)

### Community 0 - "emissions.py"
Cohesion: 0.09
Nodes (38): Notification, add_bulk_upload(), add_emission(), approve_batch_emissions(), approve_emission(), bulk_delete_emissions(), delete_emission(), _escape_like() (+30 more)

### Community 1 - "login_required"
Cohesion: 0.14
Nodes (40): BaseYear, BaseYearRecalculation, Goal, MitigationRecord, ReportingMetadata, login_required(), create_base_year_recalculation(), Create a new base year recalculation entry (+32 more)

### Community 2 - "Scope1Form.jsx"
Cohesion: 0.09
Nodes (22): CustomDropdown(), EmissionFactorOption(), AGRForm(), BlowdownForm(), CombustionForm(), HHV_REQUIRED_PROCESSES, CompletionsForm(), DehydratorForm() (+14 more)

### Community 3 - "emission_factors_routes.py"
Cohesion: 0.07
Nodes (39): get_factor_by_process_category(), get_factor_by_segment(), get_factors_by_segment_and_category(), Emission Factors Database - API Compendium 2021 Complete catalog from Sections…, Returns all emission factors applicable to the given segment. Args: segment…, Returns all emission factors for the given process category. Args:…, Returns all emission factors for a specific segment and process category. Args:…, Emission Factors Database - API Compendium 2021 Comprehensive emission factors… (+31 more)

### Community 4 - "Sentinel5PService"
Cohesion: 0.10
Nodes (16): Sentinel-5P (TROPOMI) Satellite Methane Service Connects to ESA Copernicus Data…, Service for querying ESA Copernicus Sentinel-5P TROPOMI methane measurements., Estimates methane mass emission rate (kg CH4/hr) from a Sentinel-5P column…, Sentinel5PService, Emission rate Q must scale linearly with delta_ppb and wind_speed., Zero or negative delta_ch4_ppb must return exactly 0.0 kg/hr., Layer configuration returns ESA standard legend steps and unauthenticated…, Crucial policy test: Unconfigured / unauthenticated queries MUST return status… (+8 more)

### Community 5 - "calculate_co2e"
Cohesion: 0.06
Nodes (52): Standard Quantity * EF fallback with unit handling and tier-aware uncertainty., API Compendium 2021 - Section 7: Fugitive Emissions Implementation of equations…, API Section 7.2.3 - Compressor seals, Average Factor Method - counts * EF component_counts: dict of {type: count}, Average Factor Method for equipment - count * EF, API Compendium 2021 - Section 8: Indirect Emissions Implementation of indirect…, API Section 8.3 - Allocation of Cogeneration Emissions Methods: wri_efficiency,…, API Equation 8-2: Indirect emissions from steam/heat Emissions = Energy /… (+44 more)

### Community 6 - "dependencies"
Cohesion: 0.09
Nodes (23): axios, clsx, jspdf, leaflet, lucide-react, dependencies, axios, clsx (+15 more)

### Community 7 - "devDependencies"
Cohesion: 0.07
Nodes (27): autoprefixer, eslint, @eslint/js, eslint-plugin-react-hooks, eslint-plugin-react-refresh, globals, devDependencies, autoprefixer (+19 more)

### Community 8 - "DashboardEnhanced.jsx"
Cohesion: 0.10
Nodes (24): DEFAULT_COLORS, PieChart(), SkeletonCard(), calculateForecast(), DashboardEnhanced(), calculateTrend(), formatCompactNumber(), formatDate() (+16 more)

### Community 9 - "app.py"
Cohesion: 0.18
Nodes (14): errorhandler, listens_for, after_request(), before_request(), get_csrf_token(), health_check(), internal_error(), not_found_error() (+6 more)

### Community 10 - "pages/ManageData.jsx"
Cohesion: 0.07
Nodes (16): RFC-4180, ManageData, autoDetectMapping(), ColumnMappingWizard(), Icons, STEPS, TEMPLATES, ErrorBoundary (+8 more)

### Community 11 - "dashboard.py"
Cohesion: 0.07
Nodes (50): cached, get_available_years(), get_base_year(), get_batch_dashboard_data(), get_categorical_breakdown(), get_dashboard_summary(), _get_global_cache_epoch(), get_goal() (+42 more)

### Community 12 - "test_uncertainty.py"
Cohesion: 0.10
Nodes (21): admin_user(), client(), it_admin_user(), fixture, Test suite for /dashboard/uncertainty endpoint. Covers: auth, RBAC,…, Specifying year= returns that year in the response., scope=1 should only return Scope 1 categories (no Scope 2/3 groups)., export=csv should return text/csv with correct headers. (+13 more)

### Community 13 - "test_api_security.py"
Cohesion: 0.12
Nodes (15): admin_user(), app(), client(), login(), fixture, Security and integration tests for GHG Dashboard API. These test the HTTP layer…, User should not be able to delete an emission record created by another user…, User should be able to delete their own emission record. (+7 more)

### Community 14 - "satellite.py"
Cohesion: 0.18
Nodes (17): ActivityLog, OgmpSurvey, load_settings_from_db(), Loads all system settings from SystemSetting table in DB into _app_settings., export_satellite_to_ogmp(), get_facility_satellite_data(), get_satellite_layer_config(), _get_user_copernicus_credentials() (+9 more)

### Community 15 - "log_activity_and_notify"
Cohesion: 0.08
Nodes (47): limit, Persistent key-value store for application-wide settings (GWP standard, OGMP…, SystemSetting, admin_required(), admin_reset_password(), change_password(), delete_user(), forgot_password() (+39 more)

### Community 16 - "NotificationCenter.jsx"
Cohesion: 0.27
Nodes (7): getTypeConfig(), headerActionBtn, iconBtnStyle, NotificationCenter(), NotifRow(), relativeTime(), TYPE_CONFIG

### Community 17 - "test_tier_scope_kpi_numerical.py"
Cohesion: 0.11
Nodes (50): CombustionCalculator, FlaringCalculator, ComponentFugitiveCalculator, CompressorSealCalculator, EquipmentFugitiveCalculator, CogenAllocationCalculator, IndirectSteamCalculator, AGRCalculator (+42 more)

### Community 18 - "useToast"
Cohesion: 0.10
Nodes (22): api, Diagnostics, EmissionsMap, ReferenceData, BatchReviewWizard(), detectAnomalies(), QUICK_REJECTION_REASONS, BulkImportModal() (+14 more)

### Community 19 - "CalculationDispatcher"
Cohesion: 0.05
Nodes (42): CalculationDispatcher, Normalizes a volume value to the specified target unit., Strictly extracts a required float parameter without falling back to defaults., Cleanly parses a percentage (0-100) or fraction (0-1) into a 0.0 - 1.0 ratio., Extracts a percentage or fraction strictly and normalizes to 0.0 - 1.0., Extracts an optional percentage or fraction normalized to 0.0 - 1.0., Executes the calculation for the given process type. - Tier 1 (default /…, Routes a calculation request to the appropriate API 2021 calculator. (+34 more)

### Community 20 - "App.jsx"
Cohesion: 0.09
Nodes (39): fetchCsrfToken(), AdminRoute(), App(), AuditRoute(), AuditTrail, CarbonIntensity, DashboardEnhanced, ITRoute() (+31 more)

### Community 21 - "5. CHANGELOG & DRIFT LOG"
Cohesion: 0.07
Nodes (26): 1. ARCHITECTURAL MAP & ENTRY POINTS, [2026-09-14T23:44:00Z] - ARCHITECTURAL KNOWLEDGE GRAPH INITIALIZATION, [2026-09-15T00:01:00Z] - SCOPE 1 EMISSION DETAIL VIEWER REMEDIATION & THEME ALIGNMENT, [2026-09-15T00:52:00Z] - FULL-STACK RESILIENCE & RUNTIME VERIFICATION REMEDIATION, [2026-09-15T01:13:00Z] - FULL-STACK BUG REMEDIATION & UX HARDENING, [2026-09-15T01:36:00Z] - E2E PRODUCT EXPERIENCE & FEATURE POLISH REMEDIATION (DEF-09 TO DEF-12), [2026-09-16T01:10:00Z] - COMPREHENSIVE PRODUCT AUDIT REMEDIATION (DEF-01 TO DEF-08 & FINDINGS 2, 5), [2026-09-16T01:20:00Z] - ADVERSARIAL STRESS-TEST & DETERMINISTIC VERIFICATION AUDIT (CSV UPLOADERS & METROLOGICAL ENGINES) (+18 more)

### Community 22 - "test_csv_engine_matrix.py"
Cohesion: 0.05
Nodes (37): BaseCalculator, Validates that all required inputs are present, finite, and non-negative., Calculates absolute uncertainty and non-negative bounds at 95% CI (k=2.0 per…, Formats the final calculation result into a standard structure., Base class for all API Compendium 2021 calculation modules. Provides common…, BlowdownCalculator, API Eq. 6-4: Vessel/Pipeline Blowdown (Depressurization) V_std = V_physical *…, ProductionData (+29 more)

### Community 23 - "test_audit.py"
Cohesion: 0.17
Nodes (6): admin_user(), client(), it_admin_user(), fixture, regular_user(), seed_audit_logs()

### Community 24 - "dependencies"
Cohesion: 0.13
Nodes (15): bcryptjs, body-parser, cors, express, express-rate-limit, dependencies, bcryptjs, body-parser (+7 more)

### Community 25 - "TestTier1DrillingMud"
Cohesion: 0.29
Nodes (3): Mud Degassing Tier 1 (water-based mud): mud_volume = 500 m3 EF (water-based) =…, Oil-based mud uses EF=0.35 kg/m3., TestTier1DrillingMud

### Community 26 - "Scope1ImportWizard.jsx"
Cohesion: 0.06
Nodes (19): autoDetect(), FIELD_GROUPS, Icon, PROCESS_CATALOGUE, Scope1ImportWizard(), STEPS, autoDetect(), FIELD_GROUPS (+11 more)

### Community 27 - "AnomalyDetector"
Cohesion: 0.13
Nodes (12): AnomalyDetector, Check a Scope 1 CO2e value against the trailing 12 months strictly prior to the…, Checks a new emission value against historical data for the same facility and…, Check a Scope 2 CO2e value against the trailing 12 months strictly prior to the…, Check a Scope 3 CO2e value against the trailing 12 months strictly prior to the…, Compute Z-score of a value against a list of historical values. Returns…, Verify that background anomaly detection flags are stored in emission.qa_flag., Finding 9: Verify IQR quantile calculation does not distort on small N >= 4. (+4 more)

### Community 28 - "Backend (Server)"
Cohesion: 0.03
Nodes (74): `add_indexes.py`, `app.py`, Backend (Server), `background_processor.py`, `benchmark_db.py`, `calculations\base.py`, `calculations\combustion.py`, `calculations\constants.py` (+66 more)

### Community 29 - "Emission"
Cohesion: 0.05
Nodes (50): Anomaly Detection for GHG Emissions Data. Uses Z-score (against 12-month…, run_all_scenarios(), migrate_database(), Emission, MethaneSourceType, MitigationProject, # NOTE: Do NOT call db.session.commit() here., SbtiTarget (+42 more)

### Community 30 - "test_all_apis_health.py"
Cohesion: 0.47
Nodes (5): get_sample_payload(), Replace route parameter placeholders cleanly without modifying host., Provide realistic sample payloads for POST/PUT endpoints., resolve_rule(), run_api_health_audit()

### Community 32 - "audit.py"
Cohesion: 0.40
Nodes (10): audit_access_required(), _build_audit_query(), export_audit_logs(), get_audit_filters(), get_audit_logs(), get_audit_stats(), route, Prevent CSV formula injection (DDE/Excel macro execution) including leading… (+2 more)

### Community 33 - "test_ui_calculation_parity.py"
Cohesion: 0.05
Nodes (36): auth_admin(), client(), fixture, test_ui_calculation_parity.py ============================== End-to-End…, Tests exact numerical agreement between Scope 1 engine, API response, and UI…, Tier 1 Natural Gas Combustion: Verify exact digits across DB, API, Table row,…, Flaring calculation with 98% combustion efficiency, methane slip, and carbon…, Hydrogen SMR with CCS: Feedstock + Fuel CO2 minus Capture. (+28 more)

### Community 34 - "Frontend (Client)"
Cohesion: 0.03
Nodes (66): `api.js`, `App.jsx`, `components\BulkImportModal.jsx`, `components\CalculationDetails.jsx`, `components\charts\BarChart.jsx`, `components\charts\index.js`, `components\charts\LineChart.jsx`, `components\charts\PieChart.jsx` (+58 more)

### Community 35 - "Scope2Form.jsx"
Cohesion: 0.19
Nodes (12): Emissions, CalculationDetails(), EmissionResult(), Scope2Form(), Scope3Form(), Emissions(), STAGE_EMISSION_CALCULATOR, STAGE_FACTOR_CALCULATOR (+4 more)

### Community 36 - "Tasks: [FEATURE NAME]"
Cohesion: 0.07
Nodes (26): Dependencies & Execution Order, Format: `[ID] [P?] [Story] Description`, Implementation for User Story 1, Implementation for User Story 2, Implementation for User Story 3, Implementation Strategy, Incremental Delivery, MVP First (User Story 1 Only) (+18 more)

### Community 37 - "test_qaqc_diagnostics.py"
Cohesion: 0.20
Nodes (10): admin_user(), client(), fixture, Test suite for /api/qaqc/dashboard unified diagnostics & QA/QC endpoint.…, Unauthenticated access must be rejected., Admin user receives unified uncertainty, diagnostics, and anomaly queue data., Export endpoint returns CSV with correct Content-Type., test_qaqc_dashboard_unified_payload() (+2 more)

### Community 38 - "TestEdgeCases"
Cohesion: 0.20
Nodes (5): Zero quantity should produce zero emissions without crash., Negative quantity must raise ValueError., 1 MMscf = 1,000,000 scf — result should match 1M scf calculation., If GOR=0 and EF=0, result should be zero (no flash gas)., TestEdgeCases

### Community 39 - "test_audit_remediation.py"
Cohesion: 0.03
Nodes (66): CbamProductExport, client(), fixture, Defect 5: Verify update_emission merges existing process_type and inputs., Defect 6: Verify bulk import for Scope 2 & 3 blocks it_admin and enforces…, Defect 7: Verify IT admin cannot access QA/QC resolve and users cannot verify…, Defect 8: Verify base year recalculation route enforces role, sets created_by,…, Defect 9: Verify save_cbam_export checks facility access for existing records… (+58 more)

### Community 41 - "get_allowed_facility_ids"
Cohesion: 0.15
Nodes (23): add_facility(), delete_facility(), get_all_regions(), get_facilities(), import_facilities(), route, Bulk import facilities, Return all unique region identifiers — IT Admin only, no access filtering.… (+15 more)

### Community 42 - "Project Metadata"
Cohesion: 0.22
Nodes (8): author, description, keywords, license, main, name, type, version

### Community 43 - "build"
Cohesion: 0.22
Nodes (9): build, appId, directories, productName, win, output, asar, icon (+1 more)

### Community 44 - "env.py"
Cohesion: 0.39
Nodes (7): get_engine(), get_engine_url(), get_metadata(), Run migrations in 'offline' mode. This configures the context with just a URL…, Run migrations in 'online' mode. In this scenario we need to create an Engine…, run_migrations_offline(), run_migrations_online()

### Community 45 - "test_audit_bug_fixes.py"
Cohesion: 0.18
Nodes (11): client(), fixture, Verify ComponentFugitiveCalculator handles scalar counts without AttributeError., Verify TankFlashingCalculator handles null or missing GOR without TypeError., Verify delete_mitigation returns 400 Bad Request on malformed ID instead of 500…, Verify get_ogmp_surveys handles records with null measured_rate_kg_hr without…, test_component_fugitive_calculator_scalar_counts(), test_delete_mitigation_invalid_id_format() (+3 more)

### Community 46 - "Desktop App Dev Tools"
Cohesion: 0.29
Nodes (7): electron, electron-builder, nodemon, devDependencies, electron, electron-builder, nodemon

### Community 49 - "files"
Cohesion: 0.29
Nodes (6): files, main.js, node_modules/**/*, public/**/*, server.js, users_v2.db

### Community 51 - "TestTier1Flaring"
Cohesion: 0.33
Nodes (3): Flaring Tier 1 (default factor_source → _generic_calculation): Uses API_FACTORS…, Tier 1 flaring falls through to generic EF-based calculation., TestTier1Flaring

### Community 52 - "test_vented.py"
Cohesion: 0.25
Nodes (7): Verify pneumatic intermittent actuation calculation, Verify liquids unloading accepts depth/diam/press units without error, test_blowdown_calculator(), test_liquids_unloading_units(), test_pneumatics_calculator(), test_pneumatics_intermittent_actuation(), test_tanks_calculator()

### Community 53 - "NPM Scripts"
Cohesion: 0.33
Nodes (6): scripts, build:exe, start, start:electron, start:web, test

### Community 54 - "Pitch Deck Builder"
Cohesion: 0.40
Nodes (4): add_card(), add_header(), Adds standard Startup Algeria header banner with accent bar and title., Creates a modern rounded rectangular card container.

### Community 55 - "Reports.jsx"
Cohesion: 0.20
Nodes (12): Reports, MultiSelectDropdown(), DEFAULT_GWP, Reports(), createChartImage(), fetchAllReportData(), generateModernPDF(), generateReportCharts() (+4 more)

### Community 56 - "clear_dashboard_cache"
Cohesion: 0.12
Nodes (34): LevelUpgradeLog, clear_dashboard_cache(), Updates global epoch in shared DB state and invalidates local worker heap., add_production(), bulk_import_production(), delete_cbam_export(), delete_ogmp_survey(), delete_production() (+26 more)

### Community 57 - "TestAllProcessTypesTier3"
Cohesion: 0.08
Nodes (7): parametrize, Strict verification of physical conservation laws across every process type., Conservation Law: 0 activity MUST produce exactly 0.0 emissions., Monotonicity Law: Doubling activity data MUST double emissions., Verify specific engineering physics for every process type that supports Tier 3., TestAllProcessTypesTier3, TestPhysicalConservationAcrossAllProcesses

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

### Community 68 - "AUDIT MEMORY (living document)"
Cohesion: 0.15
Nodes (12): 0. Conventions and context to respect, 1. CRITICAL security findings, 2. HIGH security findings, 3. Additional security findings (second pass), 4. CALCULATION and LOGIC bugs, 5. Tests and tooling, 6. Decision log, 7. Work log (+4 more)

### Community 69 - "GHGUser"
Cohesion: 0.31
Nodes (3): HttpUser, GHGUser, task

### Community 89 - "TestBoundaryResilienceAPI"
Cohesion: 0.17
Nodes (7): API endpoints under hostile, oversized, or malformed inputs., API endpoints must cleanly reject NaN and Infinity with 400/422 and 0 crashes., 1 MB giant string payload in text fields must not cause server crash or memory…, Formula injection patterns (=cmd|, @SUM, +1+1) must not be executed., Malformed, empty, or non-dictionary JSON payloads must return 400/422 cleanly., Arabic, Chinese, emojis, and special control characters handled cleanly., TestBoundaryResilienceAPI

### Community 92 - "test_deep_button_audit.py"
Cohesion: 0.48
Nodes (6): audit_buttons_on_current_page(), close_any_modal(), is_forbidden(), Wait for lazy-loaded component to finish mounting and spinners to detach., run(), wait_page_loaded()

### Community 93 - "get_active_gwp"
Cohesion: 0.08
Nodes (23): _process_row(), Validates a single mapped row and runs calculation via compute_emissions.…, get_active_gwp(), Global Warming Potential (GWP) Constants & Resolution Engine Supports IPCC AR4…, Dynamically resolve the active GWP factors dictionary based on standard and…, compute_emissions(), Tests the full _process_row pipeline to verify data gets into Emission fields…, _process_row should return an Emission object with correct fields. (+15 more)

### Community 111 - "Feature Specification: Batch Approve/Reject Pending Records"
Cohesion: 0.08
Nodes (23): Content Quality, Feature Readiness, Notes, Requirement Completeness, Specification Quality Checklist: batch-approve-reject, Complexity Tracking, Constitution Check, Documentation (this feature) (+15 more)

### Community 112 - "background_processor.py"
Cohesion: 0.07
Nodes (36): _append_job_list(), _build_mapping(), _clean_float(), get_job_status(), _process_file_thread(), _process_row_custom_factors(), _process_row_facilities(), _process_row_mitigation() (+28 more)

### Community 113 - "new/.specify/scripts/powershell/common.ps1"
Cohesion: 0.23
Nodes (13): Find-SpecifyRoot(), Format-SpecKitCommand(), Get-CurrentBranch(), Get-FeaturePathsEnv(), Get-InvokeSeparator(), Get-NormalizedPriority(), Get-Python3Command(), Get-RepoRoot() (+5 more)

### Community 114 - ".specify/scripts/powershell/common.ps1"
Cohesion: 0.23
Nodes (13): Find-SpecifyRoot(), Format-SpecKitCommand(), Get-CurrentBranch(), Get-FeaturePathsEnv(), Get-InvokeSeparator(), Get-NormalizedPriority(), Get-Python3Command(), Get-RepoRoot() (+5 more)

### Community 115 - "Facility"
Cohesion: 0.14
Nodes (25): Facility, app(), client(), logged_client(), fixture, DEF-04 Verification: Ensure duplicate rows are skipped by default and updated…, Verifies that non-combustion sources (e.g. pneumatics) normalize fuel_k to…, test_bulk_import_custom_factors() (+17 more)

### Community 116 - "Feature Specification: [FEATURE NAME]"
Cohesion: 0.15
Nodes (12): Assumptions, Edge Cases, Feature Specification: [FEATURE NAME], Functional Requirements, Key Entities *(include if feature involves data)*, Measurable Outcomes, Requirements *(mandatory)*, Success Criteria *(mandatory)* (+4 more)

### Community 117 - "Feature Specification: [FEATURE NAME]"
Cohesion: 0.15
Nodes (12): Assumptions, Edge Cases, Feature Specification: [FEATURE NAME], Functional Requirements, Key Entities *(include if feature involves data)*, Measurable Outcomes, Requirements *(mandatory)*, Success Criteria *(mandatory)* (+4 more)

### Community 118 - "extract_val"
Cohesion: 0.05
Nodes (26): extract_val(), =============================================================================…, Aggregates test results for a final summary table., Same calculation using m3 input — should produce same result after conversion., Diesel Tier 1: quantity = 500 gal HHV = 138,700 Btu/gal → 500 × 138,700 /…, Flaring Tier 3 (factor_source='specific') — Dual efficiency model: gas_volume =…, Blowdown Tier 1 (default): vessel volume = 5 m3 physical pressure = 100 psig →…, Tank Tier 3: throughput = 2000 bbl/month GOR = 200 scf/bbl CH4 content = 45%… (+18 more)

### Community 119 - "Implementation Tasks: QA/QC Module (IPCC & ISO 14064)"
Cohesion: 0.17
Nodes (11): Dependencies & Execution Order, Implementation for User Story 1, Implementation for User Story 2, Implementation for User Story 3, Implementation Tasks: QA/QC Module (IPCC & ISO 14064), Phase 1: Setup (Shared Infrastructure), Phase 2: Foundational (Blocking Prerequisites), Phase 3: User Story 1 - Automated Data Validation (Priority: P1) ⭐ MVP (+3 more)

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

### Community 127 - "test_master_button_audit.py"
Cohesion: 0.60
Nodes (5): audit_buttons_on_current_page(), close_any_modal(), is_forbidden(), run_master_audit(), wait_page_loaded()

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

### Community 151 - "combustion.py"
Cohesion: 0.14
Nodes (13): convert_factor_to_kg_per_unit(), _normalize_efficiency(), _normalize_unit_str(), API Compendium 2021 - Section 5: Combustion and Flaring Implementation of…, Standard fuel-based combustion calculation with API §4.2.1 thermodynamic…, Defensively normalizes efficiency inputs provided as either fractional ratios…, Dual-efficiency flaring model (API 5-3, 5-4) with API §4.2.1 thermodynamic…, normalize_gas_volume_to_standard() (+5 more)

### Community 154 - ".get_token"
Cohesion: 0.28
Nodes (5): Any, Retrieves a valid JWT access token from Copernicus CDSE with caching., Returns tile layer configuration, color ramps, and metadata for Leaflet., Queries Copernicus STAC/OData API for real Sentinel-5P methane data around…, Tests authentication against Copernicus Data Space Ecosystem Keycloak endpoint.…

### Community 164 - "reports.py"
Cohesion: 0.16
Nodes (18): create_pdf_report(), export_emissions(), export_ogmp_excel(), generate_report(), route, Generate PDF report based on filters, Prevent formula injection (DDE/CSV injection) in Excel cells including leading…, Export emissions data as PDF - GET version for frontend integration (+10 more)

### Community 181 - "test_all_process_types_matrix.py"
Cohesion: 0.08
Nodes (14): dispatcher(), fixture, test_all_process_types_matrix.py --------------------------------- Exhaustive…, Every single process type in PROCESS_TYPES must calculate successfully in Tier…, Verify compute_emissions pipeline routes and handles all canonical process…, Verify that every process is mapped to valid segments and combustion/non-…, Verify all Scope 2 utility types: Grid Electricity (Location/Market) and…, Exhaustive test of all 15 Scope 3 categories per GHG Protocol Corporate Value… (+6 more)

### Community 186 - "test_deep_injection_matrix.py"
Cohesion: 0.08
Nodes (23): CustomFactor, Defect 4: Verify custom factor with general uncertainty 5.0 is divided by 100…, test_custom_factor_percentage_uncertainty_in_add_emission(), app(), db_session(), dispatcher(), fixture, test_deep_injection_matrix.py ------------------------------ Exhaustive Deep… (+15 more)

### Community 202 - "srss_inventory"
Cohesion: 0.09
Nodes (15): combine_uncertainties_product(), combine_uncertainties_sum(), Combine relative uncertainties for E = Activity × EF (multiplicative). Formula:…, Combine relative uncertainties for E = A + B (additive, independent). Formula:…, Aggregate uncertainty across multiple sources using SRSS Approach 1. Formula:…, srss_inventory(), SRSS uncertainty of independent sources must be less than or equal to linear…, IPCC 2006 Guidelines Vol. 1 Eq. 3.2: SRSS uncertainty aggregation. (+7 more)

### Community 210 - "User"
Cohesion: 0.08
Nodes (21): User, seed_admin(), End-to-End Test for the CSV Uploader (Import Emissions Data Wizard) Tests the…, Tests the CSV upload endpoint with a mock CSV containing mixed scenarios.…, TestCSVUploaderE2E, Verify QA/QC dashboard scopes total and active facilities to the user's allowed…, Verify viewer/auditor blocked from mutate on Scope 2, and creator ownership…, test_qaqc_dashboard_regional_facility_scoping() (+13 more)

### Community 215 - "disable_limiter_for_tests"
Cohesion: 0.50
Nodes (3): disable_limiter_for_tests(), fixture, Ensure Flask-Limiter does not throttle authentication endpoints across large…

### Community 220 - "TestUnitConversionInvarianceMatrix"
Cohesion: 0.14
Nodes (8): Every physical quantity represented across various dimensional units must…, 1000 m3 of natural gas converted across all 13 volume units must yield equal…, 10 tonnes carbon mass converted across all 12 mass units must yield identical…, 1,000 MMBtu of steam converted across all 7 energy units must yield identical…, Blowdown calculation at 20°C expressed in C, F, K, R must produce identical…, Blowdown calculation at 1000 kPa expressed in kPa, MPa, Pa, bar, mbar, psia,…, Exhaustively verifies roundtrip convert(val, u1, u2) -> convert(converted, u2,…, TestUnitConversionInvarianceMatrix

### Community 230 - "scope2.py"
Cohesion: 0.15
Nodes (16): bulk_import_scope2(), _calc_cogen_allocation(), _calc_indirect_steam(), create_scope2_emission(), get_emission_factors(), get_scope2_emissions(), route, Calculate tCO2e for indirect steam / heat entry. (+8 more)

## Knowledge Gaps
- **478 isolated node(s):** `name`, `private`, `version`, `type`, `dev` (+473 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **53 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `CalculationDispatcher` connect `CalculationDispatcher` to `test_ui_calculation_parity.py`, `calculate_co2e`, `TestEdgeCases`, `TestUnitConversions`, `test_audit_remediation.py`, `test_tier_scope_kpi_numerical.py`, `Emission`, `TestTier1Flaring`, `TestUnitConversionInvarianceMatrix`, `test_all_process_types_matrix.py`, `extract_val`, `test_csv_engine_matrix.py`, `TestTier1DrillingMud`, `test_deep_injection_matrix.py`, `TestAllProcessTypesTier3`, `get_active_gwp`, `TestCO2ECalculation`?**
  _High betweenness centrality (0.053) - this node is a cross-community bridge._
- **Why does `User` connect `User` to `emissions.py`, `TestUnauthenticatedAccess`, `test_uncertainty.py`, `test_api_security.py`, `satellite.py`, `log_activity_and_notify`, `test_tier_scope_kpi_numerical.py`, `test_csv_engine_matrix.py`, `test_audit.py`, `Emission`, `test_ui_calculation_parity.py`, `test_qaqc_diagnostics.py`, `test_audit_remediation.py`, `get_allowed_facility_ids`, `test_audit_bug_fixes.py`, `clear_dashboard_cache`, `test_deep_injection_matrix.py`, `TestBoundaryResilienceAPI`, `TestUnitConversionInvarianceMatrix`, `scope2.py`, `background_processor.py`, `Facility`?**
  _High betweenness centrality (0.035) - this node is a cross-community bridge._
- **Why does `Facility` connect `Facility` to `emissions.py`, `login_required`, `TestUnauthenticatedAccess`, `dashboard.py`, `test_uncertainty.py`, `test_api_security.py`, `satellite.py`, `test_tier_scope_kpi_numerical.py`, `test_csv_engine_matrix.py`, `Emission`, `test_ui_calculation_parity.py`, `reports.py`, `test_qaqc_diagnostics.py`, `test_audit_remediation.py`, `get_allowed_facility_ids`, `test_audit_bug_fixes.py`, `clear_dashboard_cache`, `test_deep_injection_matrix.py`, `User`, `TestBoundaryResilienceAPI`, `TestUnitConversionInvarianceMatrix`, `scope2.py`, `background_processor.py`?**
  _High betweenness centrality (0.034) - this node is a cross-community bridge._
- **Are the 57 inferred relationships involving `CalculationDispatcher` (e.g. with `CombustionCalculator` and `FlaringCalculator`) actually correct?**
  _`CalculationDispatcher` has 57 INFERRED edges - model-reasoned connections that need verification._
- **Are the 29 inferred relationships involving `User` (e.g. with `TestCSVUploaderE2E` and `TestCalculationIntegrity`) actually correct?**
  _`User` has 29 INFERRED edges - model-reasoned connections that need verification._
- **Are the 29 inferred relationships involving `Facility` (e.g. with `TestCSVUploaderE2E` and `TestCalculationIntegrity`) actually correct?**
  _`Facility` has 29 INFERRED edges - model-reasoned connections that need verification._
- **What connects `name`, `private`, `version` to the rest of the system?**
  _478 weakly-connected nodes found - possible documentation gaps or missing edges._