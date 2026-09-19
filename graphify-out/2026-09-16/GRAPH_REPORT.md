# Graph Report - H2  (2026-09-16)

## Corpus Check
- 281 files · ~624,558 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 2505 nodes · 5275 edges · 228 communities (170 shown, 58 thin omitted)
- Extraction: 91% EXTRACTED · 9% INFERRED · 0% AMBIGUOUS · INFERRED: 487 edges (avg confidence: 0.52)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `0b21e68a`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- get_allowed_facility_ids
- get_current_user
- Scope1Form.jsx
- emission_factors_routes.py
- .estimate_emission_rate_from_anomaly
- calculate_co2e
- dependencies
- devDependencies
- DashboardEnhanced.jsx
- app.py
- pages/ManageData.jsx
- dashboard.py
- test_uncertainty.py
- test_api_security.py
- qaqc.py
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
- custom_factors.py
- Scope1ImportWizard.jsx
- ._z_score_check
- Backend (Server)
- Facility
- TestCSVBufferIngestionMatrix
- TestCO2ECalculation
- audit.py
- ui_format_number
- Frontend (Client)
- Scope2Form.jsx
- Tasks: [FEATURE NAME]
- test_qaqc_diagnostics.py
- TestEdgeCases
- test_audit_remediation.py
- login_required
- utils.py
- Project Metadata
- build
- env.py
- models.py
- Desktop App Dev Tools
- TestTier1DrillingMud
- files
- TestTier1Flaring
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
- TestBulkCSVIngestionAllTiersAndScopes
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
- test_stress_boundary_resilience.py
- test_emission_calculations.py
- get_active_gwp
- .dispatch
- Feature Specification: Batch Approve/Reject Pending Records
- background_processor.py
- new/.specify/scripts/powershell/common.ps1
- .specify/scripts/powershell/common.ps1
- test_all_bulk_imports.py
- Feature Specification: [FEATURE NAME]
- Feature Specification: [FEATURE NAME]
- extract_val
- Implementation Tasks: QA/QC Module (IPCC & ISO 14064)
- get_job_status
- test_vented.py
- Core Principles
- Core Principles
- Core Principles
- Core Principles
- client/package.json
- process_categories.py
- TestUnauthenticatedAccess
- Implementation Tasks: Batch Approve/Reject Pending Records
- Implementation Plan: [FEATURE]
- Implementation Plan: [FEATURE]
- Existing Entities to Modify
- test_satellite.py
- test_combustion.py
- status.py
- AnomalyDetector
- generate_1k_comprehensive.py
- new/.specify/scripts/powershell/create-new-feature.ps1
- .specify/scripts/powershell/create-new-feature.ps1
- [CHECKLIST TYPE] Checklist: [FEATURE NAME]
- [CHECKLIST TYPE] Checklist: [FEATURE NAME]
- Research & Design Decisions: Batch Approve/Reject
- Research & Design Decisions: QA/QC Module (IPCC & ISO 14064)
- @vitejs/plugin-react
- units.py
- formik
- .get_token
- papaparse
- react
- react-dom
- tailwind-merge
- _clean_float
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
- combustion.py
- .test_carbon_intensity_metric_equations
- test_deep_injection_matrix.py
- test_sbti.py
- sqlite3
- srss_inventory
- MockSession
- test_ui_audit_visuals.mjs
- .test_methane_loss_rate_ogmp_equation
- .test_dashboard_summary_identity_and_compact_formatting
- .test_flaring_rate_percentage_equation
- chart.js
- .test_epa_wec_part99_fee_schedules_and_thresholds
- User
- .test_zero_emission_uncertainty_bounds
- .test_confidence_interval_bounds_ordering
- lucide-react
- get_eeio_factor
- .calculate_uncertainty
- .test_scope3_tier3_supplier_specific_pcf
- .test_coverage_factor_and_non_negative_bounds
- .format_result
- .test_ogmp_facility_level_5_requires_level_4_bottom_up
- convert
- class-variance-authority
- .validate_inputs
- electricity_factors.py
- .test_gwp_standards_cross_consistency
- .test_scope3_materials_and_spend_eeio
- _calc_cogen_allocation
- .test_scope2_indirect_steam_thermodynamic_equation

## God Nodes (most connected - your core abstractions)
1. `login_required()` - 131 edges
2. `get_current_user()` - 104 edges
3. `CalculationDispatcher` - 99 edges
4. `User` - 94 edges
5. `Facility` - 87 edges
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
- `seed_data()` --calls--> `Emission`  [INFERRED]
  seed_demo_data.py → new/server/models.py
- `ManageDataInner()` --indirect_call--> `f()`  [INFERRED]
  new/client/src/pages/ManageData.jsx → temp_old/CarbonIntensity.jsx

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Graphify Tooling and Documentation** — agents_rules_graphify, agents_workflows_graphify, agents_rules_graphify_cli, agents_rules_graphify_mcp [EXTRACTED 1.00]
- **Emission Calculation & Visualization Flow** — new_server_calculations, deck_assets_ui_dashboard, deck_assets_chart_industry_emissions [INFERRED 0.80]

## Communities (228 total, 58 thin omitted)

### Community 0 - "get_allowed_facility_ids"
Cohesion: 0.10
Nodes (41): add_bulk_upload(), add_emission(), approve_batch_emissions(), approve_emission(), bulk_delete_emissions(), delete_emission(), _escape_like(), export_emissions() (+33 more)

### Community 1 - "get_current_user"
Cohesion: 0.17
Nodes (30): BaseYear, BaseYearRecalculation, Goal, MitigationProject, MitigationRecord, ReportingMetadata, create_base_year_recalculation(), Create a new base year recalculation entry (+22 more)

### Community 2 - "Scope1Form.jsx"
Cohesion: 0.09
Nodes (22): CustomDropdown(), EmissionFactorOption(), AGRForm(), BlowdownForm(), CombustionForm(), HHV_REQUIRED_PROCESSES, CompletionsForm(), DehydratorForm() (+14 more)

### Community 3 - "emission_factors_routes.py"
Cohesion: 0.09
Nodes (31): get_factor_by_process_category(), get_factor_by_segment(), get_factors_by_segment_and_category(), Emission Factors Database - API Compendium 2021 Complete catalog from Sections…, Returns all emission factors applicable to the given segment. Args: segment…, Returns all emission factors for the given process category. Args:…, Returns all emission factors for a specific segment and process category. Args:…, get_all_emission_factors() (+23 more)

### Community 4 - ".estimate_emission_rate_from_anomaly"
Cohesion: 0.18
Nodes (6): Sentinel-5P (TROPOMI) Satellite Methane Service Connects to ESA Copernicus Data…, Service for querying ESA Copernicus Sentinel-5P TROPOMI methane measurements., Estimates methane mass emission rate (kg CH4/hr) from a Sentinel-5P column…, Sentinel5PService, Emission rate Q must scale linearly with delta_ppb and wind_speed., Zero or negative delta_ch4_ppb must return exactly 0.0 kg/hr.

### Community 5 - "calculate_co2e"
Cohesion: 0.09
Nodes (31): Standard fuel-based combustion calculation with API §4.2.1 thermodynamic…, Dual-efficiency flaring model (API 5-3, 5-4) with API §4.2.1 thermodynamic…, API Compendium 2021 - Section 7: Fugitive Emissions Implementation of equations…, API Section 7.2.3 - Compressor seals, Average Factor Method - counts * EF component_counts: dict of {type: count}, Average Factor Method for equipment - count * EF, API Compendium 2021 - Section 8: Indirect Emissions Implementation of indirect…, API Section 8.3 - Allocation of Cogeneration Emissions Methods: wri_efficiency,… (+23 more)

### Community 6 - "dependencies"
Cohesion: 0.09
Nodes (23): axios, clsx, framer-motion, jspdf, leaflet, dependencies, axios, clsx (+15 more)

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
Cohesion: 0.16
Nodes (12): admin_user(), app(), client(), login(), fixture, Security and integration tests for GHG Dashboard API. These test the HTTP layer…, 6th failed login attempt within the window must be rate-limited., A bad calculation input must return 422, not silently save 0.000 tCO2e. (+4 more)

### Community 14 - "qaqc.py"
Cohesion: 0.27
Nodes (11): bulk_resolve(), export_qaqc_report(), get_qaqc_dashboard(), _is_admin_or_superuser(), route, Returns True if the user has QA/QC viewing rights (admin or superuser roles)., Returns aggregated uncertainty (IPCC SRSS) and flagged anomaly records. Scoped…, Exports QA/QC anomaly data as a CSV file with scope and year filtering. Access:… (+3 more)

### Community 15 - "log_activity_and_notify"
Cohesion: 0.08
Nodes (46): limit, compute_scope3_co2e(), Authoritatively calculates Scope 3 CO2e in metric tonnes from activity amount…, admin_required(), admin_reset_password(), change_password(), delete_user(), forgot_password() (+38 more)

### Community 16 - "NotificationCenter.jsx"
Cohesion: 0.27
Nodes (7): getTypeConfig(), headerActionBtn, iconBtnStyle, NotificationCenter(), NotifRow(), relativeTime(), TYPE_CONFIG

### Community 17 - "test_tier_scope_kpi_numerical.py"
Cohesion: 0.11
Nodes (56): BaseCalculator, Base class for all API Compendium 2021 calculation modules. Provides common…, CombustionCalculator, FlaringCalculator, ComponentFugitiveCalculator, CompressorSealCalculator, EquipmentFugitiveCalculator, CogenAllocationCalculator (+48 more)

### Community 18 - "useToast"
Cohesion: 0.10
Nodes (22): api, Diagnostics, EmissionsMap, ReferenceData, BatchReviewWizard(), detectAnomalies(), QUICK_REJECTION_REASONS, BulkImportModal() (+14 more)

### Community 19 - "CalculationDispatcher"
Cohesion: 0.16
Nodes (18): CalculationDispatcher, Routes a calculation request to the appropriate API 2021 calculator., CALC-03: Verify AGR calculates both CO2 mass balance and CH4 slip per API Table…, CALC-02: Verify Glycol Dehydrator parametric TEG solubility model, CALC-06: Verify Blowdown calculator applies thermodynamic T-correction, CALC-07: Verify completions multi-method calculation (rate/duration & GOR), test_agr_methane_slip_calculation(), test_blowdown_temperature_correction() (+10 more)

### Community 20 - "App.jsx"
Cohesion: 0.09
Nodes (39): fetchCsrfToken(), AdminRoute(), App(), AuditRoute(), AuditTrail, CarbonIntensity, DashboardEnhanced, ITRoute() (+31 more)

### Community 21 - "5. CHANGELOG & DRIFT LOG"
Cohesion: 0.07
Nodes (26): 1. ARCHITECTURAL MAP & ENTRY POINTS, [2026-09-14T23:44:00Z] - ARCHITECTURAL KNOWLEDGE GRAPH INITIALIZATION, [2026-09-15T00:01:00Z] - SCOPE 1 EMISSION DETAIL VIEWER REMEDIATION & THEME ALIGNMENT, [2026-09-15T00:52:00Z] - FULL-STACK RESILIENCE & RUNTIME VERIFICATION REMEDIATION, [2026-09-15T01:13:00Z] - FULL-STACK BUG REMEDIATION & UX HARDENING, [2026-09-15T01:36:00Z] - E2E PRODUCT EXPERIENCE & FEATURE POLISH REMEDIATION (DEF-09 TO DEF-12), [2026-09-16T01:10:00Z] - COMPREHENSIVE PRODUCT AUDIT REMEDIATION (DEF-01 TO DEF-08 & FINDINGS 2, 5), [2026-09-16T01:20:00Z] - ADVERSARIAL STRESS-TEST & DETERMINISTIC VERIFICATION AUDIT (CSV UPLOADERS & METROLOGICAL ENGINES) (+18 more)

### Community 22 - "test_csv_engine_matrix.py"
Cohesion: 0.11
Nodes (14): app(), db_session(), fixture, test_csv_engine_matrix.py ------------------------- Adversarial Stress-Test &…, Verifies numerical determinism, singularity handling, and fixed-point precision., Proves that BaseCalculator.validate_inputs rejects NaN and Inf., Proves that dispatcher.dispatch rejects NaN and Inf quantities., Verifies that z_factor = 0 or negative is safely clamped to 1.0 (no… (+6 more)

### Community 23 - "test_audit.py"
Cohesion: 0.17
Nodes (6): admin_user(), client(), it_admin_user(), fixture, regular_user(), seed_audit_logs()

### Community 24 - "dependencies"
Cohesion: 0.13
Nodes (15): bcryptjs, body-parser, cors, express, express-rate-limit, dependencies, bcryptjs, body-parser (+7 more)

### Community 25 - "custom_factors.py"
Cohesion: 0.23
Nodes (15): CustomFactor, Permits superuser and admin roles for data management operations. NOTE:…, superuser_required(), create_custom_factor(), delete_custom_factor(), import_custom_factors(), _parse_non_negative_float(), route (+7 more)

### Community 26 - "Scope1ImportWizard.jsx"
Cohesion: 0.06
Nodes (19): autoDetect(), FIELD_GROUPS, Icon, PROCESS_CATALOGUE, Scope1ImportWizard(), STEPS, autoDetect(), FIELD_GROUPS (+11 more)

### Community 27 - "._z_score_check"
Cohesion: 0.28
Nodes (4): Check a Scope 1 CO2e value against the trailing 12 months strictly prior to the…, Check a Scope 2 CO2e value against the trailing 12 months strictly prior to the…, Check a Scope 3 CO2e value against the trailing 12 months strictly prior to the…, Compute Z-score of a value against a list of historical values. Returns…

### Community 28 - "Backend (Server)"
Cohesion: 0.03
Nodes (74): `add_indexes.py`, `app.py`, Backend (Server), `background_processor.py`, `benchmark_db.py`, `calculations\base.py`, `calculations\combustion.py`, `calculations\constants.py` (+66 more)

### Community 29 - "Facility"
Cohesion: 0.04
Nodes (80): Anomaly Detection for GHG Emissions Data. Uses Z-score (against 12-month…, run_all_scenarios(), Emission, Facility, ProductionData, SbtiTarget, Scope2Emission, Scope3Emission (+72 more)

### Community 30 - "TestCSVBufferIngestionMatrix"
Cohesion: 0.11
Nodes (9): Runs _process_file_thread synchronously for deterministic assertion., Validates European semicolon-separated CSV parsing., Validates Tab-separated (TSV) and Pipe-separated CSV parsing., Validates UTF-8 with BOM and Windows-1252 / ISO-8859-1 encodings with accented…, Validates Windows CRLF (\r\n) and legacy Mac CR (\r) line terminators., Validates resilient skipping of empty lines and padded whitespace in headers…, Validates zero-byte and header-only empty files., Verifies that rows lacking process type are rejected deterministically with… (+1 more)

### Community 32 - "audit.py"
Cohesion: 0.31
Nodes (12): audit_access_required(), _build_audit_query(), export_audit_logs(), get_audit_filters(), get_audit_logs(), get_audit_stats(), route, Prevent CSV formula injection (DDE/Excel macro execution) including leading… (+4 more)

### Community 33 - "ui_format_number"
Cohesion: 0.06
Nodes (18): Tier 1 Natural Gas Combustion: Verify exact digits across DB, API, Table row,…, Flaring calculation with 98% combustion efficiency, methane slip, and carbon…, Hydrogen SMR with CCS: Feedstock + Fuel CO2 minus Capture., Tier 3: Detailed chromatographic fuel gas composition with carbon mass balance., Fugitive Component Leaks: 150 valves with EPA leak factors and 5 decimal UI…, Location-based Grid Electricity: 50,000 kWh at US Average factor., Indirect Steam / District Heat: 1,200 MMBtu with boiler efficiency., Replicates formatNumber(value, decimals) from formatters.js. (+10 more)

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
Nodes (71): client(), fixture, Defect 5: Verify update_emission merges existing process_type and inputs., Verify _require_fraction handles boundary values and percentages cleanly., Defect 6: Verify bulk import for Scope 2 & 3 blocks it_admin and enforces…, Defect 7: Verify IT admin cannot access QA/QC resolve and users cannot verify…, Defect 8: Verify base year recalculation route enforces role, sets created_by,…, Verify short ton conversion to kg (907.185 kg). (+63 more)

### Community 40 - "login_required"
Cohesion: 0.15
Nodes (23): login_required(), get_custom_factors(), Get all custom emission factors, add_facility(), delete_facility(), get_all_regions(), get_facilities(), import_facilities() (+15 more)

### Community 41 - "utils.py"
Cohesion: 0.19
Nodes (16): ActivityLog, Notification, OgmpSurvey, export_satellite_to_ogmp(), get_facility_satellite_data(), get_satellite_layer_config(), _get_user_copernicus_credentials(), poll_new_satellite_passes() (+8 more)

### Community 42 - "Project Metadata"
Cohesion: 0.22
Nodes (8): author, description, keywords, license, main, name, type, version

### Community 43 - "build"
Cohesion: 0.22
Nodes (9): build, appId, directories, productName, win, output, asar, icon (+1 more)

### Community 44 - "env.py"
Cohesion: 0.39
Nodes (7): get_engine(), get_engine_url(), get_metadata(), Run migrations in 'offline' mode. This configures the context with just a URL…, Run migrations in 'online' mode. In this scenario we need to create an Engine…, run_migrations_offline(), run_migrations_online()

### Community 45 - "models.py"
Cohesion: 0.11
Nodes (12): migrate_database(), MethaneSourceType, # NOTE: Do NOT call db.session.commit() here., Persistent key-value store for application-wide settings (GWP standard, OGMP…, Scope3Data, SystemSetting, Saves a setting to the SystemSetting table and syncs _app_settings., save_setting_to_db() (+4 more)

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
Nodes (34): CbamProductExport, LevelUpgradeLog, clear_dashboard_cache(), Updates global epoch in shared DB state and invalidates local worker heap., add_production(), bulk_import_production(), delete_cbam_export(), delete_ogmp_survey() (+26 more)

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

### Community 67 - "TestBulkCSVIngestionAllTiersAndScopes"
Cohesion: 0.22
Nodes (7): Executes the full asynchronous/synchronous file processing pipeline for all 3…, Tier 1 Bulk CSV: Default catalog factors across combustion, venting, and…, Tier 2 Bulk CSV: Uses regional custom emission factors created in DB., Tier 3 Bulk CSV: Engineering mode with physical parameters (c1, c2, hhv, GOR,…, Scope 2 Bulk CSV: Location-based electricity, Market-based renewable PPA, and…, Scope 3 Bulk CSV: Uploading mass, distance, and spend EEIO units across…, TestBulkCSVIngestionAllTiersAndScopes

### Community 68 - "AUDIT MEMORY (living document)"
Cohesion: 0.15
Nodes (12): 0. Conventions and context to respect, 1. CRITICAL security findings, 2. HIGH security findings, 3. Additional security findings (second pass), 4. CALCULATION and LOGIC bugs, 5. Tests and tooling, 6. Decision log, 7. Work log (+4 more)

### Community 69 - "GHGUser"
Cohesion: 0.31
Nodes (3): HttpUser, GHGUser, task

### Community 89 - "test_stress_boundary_resilience.py"
Cohesion: 0.10
Nodes (13): Emission Factors Package Re-exports everything from root emission_factors.py…, boundary_client(), fixture, test_stress_boundary_resilience.py ================================== Pillar 4:…, API endpoints under hostile, oversized, or malformed inputs., API endpoints must cleanly reject NaN and Infinity with 400/422 and 0 crashes., 1 MB giant string payload in text fields must not cause server crash or memory…, Formula injection patterns (=cmd|, @SUM, +1+1) must not be executed. (+5 more)

### Community 92 - "test_emission_calculations.py"
Cohesion: 0.09
Nodes (11): =============================================================================…, Aggregates test results for a final summary table., Pneumatic Tier 3: count = 10 devices hours = 8760 hr/yr bleed_rate = 6 scf/hr…, Completions Tier 3 (metered_volume): flowback_volume = 50,000 m3 CH4 content =…, Fugitive average — uses _generic_calculation with catalog EF. EF: ch4=0.1…, Tier 3 Combustion with gas composition (carbon mass balance): volume = 1000 scf…, SummaryResult, TestTier1FugitiveAverage (+3 more)

### Community 93 - "get_active_gwp"
Cohesion: 0.10
Nodes (21): _process_row(), Validates a single mapped row and runs calculation via compute_emissions.…, get_active_gwp(), Global Warming Potential (GWP) Constants & Resolution Engine Supports IPCC AR4…, Dynamically resolve the active GWP factors dictionary based on standard and…, compute_emissions(), Tests the full _process_row pipeline to verify data gets into Emission fields…, _process_row should return an Emission object with correct fields. (+13 more)

### Community 94 - ".dispatch"
Cohesion: 0.15
Nodes (7): Normalizes a volume value to the specified target unit., Standard Quantity * EF fallback with unit handling and tier-aware uncertainty., Strictly extracts a required float parameter without falling back to defaults., Cleanly parses a percentage (0-100) or fraction (0-1) into a 0.0 - 1.0 ratio., Extracts a percentage or fraction strictly and normalizes to 0.0 - 1.0., Extracts an optional percentage or fraction normalized to 0.0 - 1.0., Executes the calculation for the given process type. - Tier 1 (default /…

### Community 111 - "Feature Specification: Batch Approve/Reject Pending Records"
Cohesion: 0.08
Nodes (23): Content Quality, Feature Readiness, Notes, Requirement Completeness, Specification Quality Checklist: batch-approve-reject, Complexity Tracking, Constitution Check, Documentation (this feature) (+15 more)

### Community 112 - "background_processor.py"
Cohesion: 0.19
Nodes (18): _append_job_list(), _build_mapping(), _process_file_thread(), _process_row_custom_factors(), _process_row_facilities(), _process_row_mitigation(), _process_row_scope2(), _process_row_scope3() (+10 more)

### Community 113 - "new/.specify/scripts/powershell/common.ps1"
Cohesion: 0.23
Nodes (13): Find-SpecifyRoot(), Format-SpecKitCommand(), Get-CurrentBranch(), Get-FeaturePathsEnv(), Get-InvokeSeparator(), Get-NormalizedPriority(), Get-Python3Command(), Get-RepoRoot() (+5 more)

### Community 114 - ".specify/scripts/powershell/common.ps1"
Cohesion: 0.23
Nodes (13): Find-SpecifyRoot(), Format-SpecKitCommand(), Get-CurrentBranch(), Get-FeaturePathsEnv(), Get-InvokeSeparator(), Get-NormalizedPriority(), Get-Python3Command(), Get-RepoRoot() (+5 more)

### Community 115 - "test_all_bulk_imports.py"
Cohesion: 0.19
Nodes (17): app(), client(), logged_client(), fixture, DEF-04 Verification: Ensure duplicate rows are skipped by default and updated…, Verifies that non-combustion sources (e.g. pneumatics) normalize fuel_k to…, test_bulk_import_custom_factors(), test_bulk_import_duplicate_prevention_and_overwrite() (+9 more)

### Community 116 - "Feature Specification: [FEATURE NAME]"
Cohesion: 0.15
Nodes (12): Assumptions, Edge Cases, Feature Specification: [FEATURE NAME], Functional Requirements, Key Entities *(include if feature involves data)*, Measurable Outcomes, Requirements *(mandatory)*, Success Criteria *(mandatory)* (+4 more)

### Community 117 - "Feature Specification: [FEATURE NAME]"
Cohesion: 0.15
Nodes (12): Assumptions, Edge Cases, Feature Specification: [FEATURE NAME], Functional Requirements, Key Entities *(include if feature involves data)*, Measurable Outcomes, Requirements *(mandatory)*, Success Criteria *(mandatory)* (+4 more)

### Community 118 - "extract_val"
Cohesion: 0.07
Nodes (15): extract_val(), Same calculation using m3 input — should produce same result after conversion., Diesel Tier 1: quantity = 500 gal HHV = 138,700 Btu/gal → 500 × 138,700 /…, Flaring Tier 3 (factor_source='specific') — Dual efficiency model: gas_volume =…, Blowdown Tier 1 (default): vessel volume = 5 m3 physical pressure = 100 psig →…, Tank Tier 3: throughput = 2000 bbl/month GOR = 200 scf/bbl CH4 content = 45%…, Liquids Unloading Tier 3 (API Eq. 6-3): well_depth = 5000 ft diameter = 2.441…, Extract the central value from a propagated uncertainty dict or bare float. (+7 more)

### Community 119 - "Implementation Tasks: QA/QC Module (IPCC & ISO 14064)"
Cohesion: 0.17
Nodes (11): Dependencies & Execution Order, Implementation for User Story 1, Implementation for User Story 2, Implementation for User Story 3, Implementation Tasks: QA/QC Module (IPCC & ISO 14064), Phase 1: Setup (Shared Infrastructure), Phase 2: Foundational (Blocking Prerequisites), Phase 3: User Story 1 - Automated Data Validation (Priority: P1) ⭐ MVP (+3 more)

### Community 120 - "get_job_status"
Cohesion: 0.18
Nodes (8): get_job_status(), bulk_stress_env(), fixture, test_stress_bulk_pipeline.py ============================ Pillar 3: Concurrent…, Stress test concurrent polling via get_job_status across 30 parallel threads., Stress tests the background asynchronous file processor under multi-threaded…, Submit and process 8 distinct CSV upload jobs concurrently in parallel…, TestConcurrentBulkIngestionPipeline

### Community 121 - "test_vented.py"
Cohesion: 0.25
Nodes (7): Verify pneumatic intermittent actuation calculation, Verify liquids unloading accepts depth/diam/press units without error, test_blowdown_calculator(), test_liquids_unloading_units(), test_pneumatics_calculator(), test_pneumatics_intermittent_actuation(), test_tanks_calculator()

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

### Community 127 - "process_categories.py"
Cohesion: 0.29
Nodes (8): Emission Factors Database - API Compendium 2021 Comprehensive emission factors…, get_process_types_by_category(), get_process_types_for_segment(), get_segments_for_process(), Process Categories and Segment Classification API Compendium 2021 - Organized…, Returns all process types applicable to the given segment. Args: segment (str):…, Returns all segments where the given process type is applicable. Args:…, Returns process types organized by category, optionally filtered by segment.…

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

### Community 133 - "test_satellite.py"
Cohesion: 0.18
Nodes (10): Layer configuration returns ESA standard legend steps and unauthenticated…, Crucial policy test: Unconfigured / unauthenticated queries MUST return status…, Tests OAuth2 authentication flow with mock Copernicus Keycloak token endpoint., Verifies the physical 1D box model / mass-divergence plume flux estimation., Tests OAuth2 rejection handling., test_sentinel5p_connection_test_mocked_failure(), test_sentinel5p_connection_test_mocked_success(), test_sentinel5p_flux_calculation() (+2 more)

### Community 134 - "test_combustion.py"
Cohesion: 0.50
Nodes (3): test_flaring_calculator_basic(), test_flaring_calculator_specific_c1_c10(), test_stationary_combustion_calculator()

### Community 136 - "status.py"
Cohesion: 0.50
Nodes (3): normalize_status(), Canonical Status Vocabulary for GHG Platform. Standardizes statuses across…, Normalize input status string to canonical vocabulary.

### Community 139 - "AnomalyDetector"
Cohesion: 0.22
Nodes (6): AnomalyDetector, Checks a new emission value against historical data for the same facility and…, Verify that background anomaly detection flags are stored in emission.qa_flag., test_bulk_anomaly_flag_persistence(), If historical is constant and new value is identical, it must NOT flag., Sample size N < 3 must return insufficient_history without crashing.

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

### Community 151 - "units.py"
Cohesion: 0.09
Nodes (22): convert_pressure(), convert_temperature(), from_psia(), normalize_gas_volume_to_standard(), Converts gauge or metric pressure to absolute pressure in psia., API Compendium 2021 §4.2.1: Converts gas volume measured at actual/operating…, Converts temperature value to Celsius., Converts absolute psia pressure to any target unit (gauge or absolute). (+14 more)

### Community 154 - ".get_token"
Cohesion: 0.28
Nodes (5): Any, Retrieves a valid JWT access token from Copernicus CDSE with caching., Returns tile layer configuration, color ramps, and metadata for Leaflet., Queries Copernicus STAC/OData API for real Sentinel-5P methane data around…, Tests authentication against Copernicus Data Space Ecosystem Keycloak endpoint.…

### Community 159 - "_clean_float"
Cohesion: 0.29
Nodes (5): _clean_float(), _process_row_production(), Robustly parses numbers with currency signs, trailing engineering units,…, parametrize, Mathematically prove that NaN and Infinity are neutralized.

### Community 164 - "reports.py"
Cohesion: 0.16
Nodes (18): create_pdf_report(), export_emissions(), export_ogmp_excel(), generate_report(), route, Generate PDF report based on filters, Prevent formula injection (DDE/CSV injection) in Excel cells including leading…, Export emissions data as PDF - GET version for frontend integration (+10 more)

### Community 181 - "test_all_process_types_matrix.py"
Cohesion: 0.07
Nodes (19): dispatcher(), fixture, parametrize, test_all_process_types_matrix.py --------------------------------- Exhaustive…, Every single process type in PROCESS_TYPES must calculate successfully in Tier…, Verify compute_emissions pipeline routes and handles all canonical process…, Verify that every process is mapped to valid segments and combustion/non-…, Verify all Scope 2 utility types: Grid Electricity (Location/Market) and… (+11 more)

### Community 184 - "combustion.py"
Cohesion: 0.29
Nodes (7): convert_factor_to_kg_per_unit(), _normalize_efficiency(), _normalize_unit_str(), API Compendium 2021 - Section 5: Combustion and Flaring Implementation of…, Defensively normalizes efficiency inputs provided as either fractional ratios…, Finding 6: Verify convert_factor_to_kg_per_unit handles tco2, tch4, tn2o and g/…, test_combustion_factor_prefix_tco2_and_gram()

### Community 186 - "test_deep_injection_matrix.py"
Cohesion: 0.39
Nodes (7): app(), db_session(), dispatcher(), fixture, test_deep_injection_matrix.py ------------------------------ Exhaustive Deep…, test_facility(), test_user()

### Community 187 - "test_sbti.py"
Cohesion: 0.32
Nodes (4): admin_user(), client(), it_admin_user(), fixture

### Community 202 - "srss_inventory"
Cohesion: 0.09
Nodes (18): combine_uncertainties_product(), combine_uncertainties_sum(), Combine relative uncertainties for E = Activity × EF (multiplicative). Formula:…, Combine relative uncertainties for E = A + B (additive, independent). Formula:…, Aggregate uncertainty across multiple sources using SRSS Approach 1. Formula:…, srss_inventory(), Finding 8: Verify combine_uncertainties_sum returns non-negative relative…, test_uncertainty_combine_sum_negative_sinks() (+10 more)

### Community 206 - ".test_dashboard_summary_identity_and_compact_formatting"
Cohesion: 0.50
Nodes (3): Replicates formatCompactNumber(value, decimals) from formatters.js., Verify: Dashboard summary aggregate preserves scope1 + scope2 == total and…, ui_format_compact_number()

### Community 210 - "User"
Cohesion: 0.10
Nodes (17): User, seed_admin(), End-to-End Test for the CSV Uploader (Import Emissions Data Wizard) Tests the…, Tests the CSV upload endpoint with a mock CSV containing mixed scenarios.…, TestCSVUploaderE2E, Defect 9: Verify save_cbam_export checks facility access for existing records…, Verify QA/QC dashboard scopes total and active facilities to the user's allowed…, Verify viewer/auditor blocked from mutate on Scope 2, and creator ownership… (+9 more)

### Community 214 - "get_eeio_factor"
Cohesion: 0.29
Nodes (5): _process_row_scope3_eeio(), get_eeio_factor(), EPA USEEIO Emission Factors v1.3 Maps NAICS codes to kg CO2e per $1,000 spend.…, Returns the EEIO factor for a given 3-digit NAICS code. If exact match not…, Tier 1 Spend-Based: Emissions = Spend ($) × EEIO Factor (kg CO2e / $1,000) /…

### Community 220 - "convert"
Cohesion: 0.12
Nodes (10): convert(), Simple unit conversion wrapper supporting direct keys, dimensional base units,…, API Compendium 2021 §6.3 & EPA Subpart W §98.233(c) Completions & Workovers…, Verify bidirectional mscf, mcf, and mmscf conversions in units.py., test_unit_conversions_mscf_mcf_bidirectional(), 1000 m3 of natural gas converted across all 13 volume units must yield equal…, 10 tonnes carbon mass converted across all 12 mass units must yield identical…, 1,000 MMBtu of steam converted across all 7 energy units must yield identical… (+2 more)

### Community 230 - "_calc_cogen_allocation"
Cohesion: 0.50
Nodes (3): _calc_cogen_allocation(), Calculate heat-allocated tCO2e for CHP / cogeneration entry., Scope 2 Cogeneration (CHP) Allocation Methods: Total Facility Emissions: 10,000…

## Knowledge Gaps
- **478 isolated node(s):** `name`, `private`, `version`, `type`, `dev` (+473 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **58 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `CalculationDispatcher` connect `CalculationDispatcher` to `TestBulkCSVIngestionAllTiersAndScopes`, `TestUnitConversions`, `TestEdgeCases`, `test_audit_remediation.py`, `TestTier1DrillingMud`, `test_tier_scope_kpi_numerical.py`, `Facility`, `TestTier1Flaring`, `test_all_process_types_matrix.py`, `extract_val`, `test_csv_engine_matrix.py`, `TestAllProcessTypesTier3`, `test_deep_injection_matrix.py`, `test_emission_calculations.py`, `get_active_gwp`, `.dispatch`, `TestCO2ECalculation`?**
  _High betweenness centrality (0.050) - this node is a cross-community bridge._
- **Why does `User` connect `User` to `get_allowed_facility_ids`, `TestUnauthenticatedAccess`, `test_uncertainty.py`, `test_api_security.py`, `log_activity_and_notify`, `test_tier_scope_kpi_numerical.py`, `test_csv_engine_matrix.py`, `test_audit.py`, `custom_factors.py`, `Facility`, `test_qaqc_diagnostics.py`, `test_audit_remediation.py`, `login_required`, `utils.py`, `models.py`, `clear_dashboard_cache`, `test_deep_injection_matrix.py`, `test_sbti.py`, `TestBulkCSVIngestionAllTiersAndScopes`, `test_stress_boundary_resilience.py`, `background_processor.py`, `test_all_bulk_imports.py`, `get_job_status`?**
  _High betweenness centrality (0.039) - this node is a cross-community bridge._
- **Why does `Emission` connect `Facility` to `get_allowed_facility_ids`, `get_current_user`, `TestUnauthenticatedAccess`, `AnomalyDetector`, `dashboard.py`, `test_api_security.py`, `qaqc.py`, `log_activity_and_notify`, `test_uncertainty.py`, `test_tier_scope_kpi_numerical.py`, `test_csv_engine_matrix.py`, `custom_factors.py`, `reports.py`, `test_audit_remediation.py`, `utils.py`, `models.py`, `clear_dashboard_cache`, `test_deep_injection_matrix.py`, `test_sbti.py`, `TestBulkCSVIngestionAllTiersAndScopes`, `User`, `test_stress_boundary_resilience.py`, `get_active_gwp`, `background_processor.py`, `test_all_bulk_imports.py`?**
  _High betweenness centrality (0.034) - this node is a cross-community bridge._
- **Are the 57 inferred relationships involving `CalculationDispatcher` (e.g. with `CombustionCalculator` and `FlaringCalculator`) actually correct?**
  _`CalculationDispatcher` has 57 INFERRED edges - model-reasoned connections that need verification._
- **Are the 29 inferred relationships involving `User` (e.g. with `TestCSVUploaderE2E` and `TestCalculationIntegrity`) actually correct?**
  _`User` has 29 INFERRED edges - model-reasoned connections that need verification._
- **Are the 29 inferred relationships involving `Facility` (e.g. with `TestCSVUploaderE2E` and `TestCalculationIntegrity`) actually correct?**
  _`Facility` has 29 INFERRED edges - model-reasoned connections that need verification._
- **What connects `name`, `private`, `version` to the rest of the system?**
  _478 weakly-connected nodes found - possible documentation gaps or missing edges._