# File-by-File Analysis

## Backend (Server)

### `add_indexes.py`
Python Module. Classes: None. Functions: create_indexes.

### `app.py`
Python Module. Classes: None. Functions: set_sqlite_pragmas, receive_after_commit, before_request, after_request, not_found_error, internal_error, get_csrf_token, health_check.

### `background_processor.py`
Python Module. Classes: None. Functions: start_background_upload, get_job_status, _process_file_thread, _build_mapping, _process_row_scope2, _process_row_scope3, _process_row_sources, _process_row_production, _process_row_mitigation, _process_row_custom_factors, _process_row_facilities, _process_row.

### `benchmark_db.py`
Python Module. Classes: None. Functions: benchmark_queries.

### `config.py`
Python Module. Classes: Config. Functions: None.

### `electricity_factors.py`
Python Module. Classes: None. Functions: None.

### `emission_factors.py`
Python Module. Classes: None. Functions: None.

### `emission_factors_api2021.py`
Python Module. Classes: None. Functions: get_factor_by_segment, get_factor_by_process_category, get_factors_by_segment_and_category.

### `extensions.py`
Python Module. Classes: None. Functions: None.

### `generate_10k_csv.py`
Python Module. Classes: None. Functions: generate_csv.

### `generate_10k_scope2.py`
Python Module. Classes: None. Functions: generate_scope2_csv.

### `generate_10k_scope3.py`
Python Module. Classes: None. Functions: generate_scope3_csv.

### `generate_1k_comprehensive.py`
Python Module. Classes: None. Functions: gas_comp, fuel_for, empty_row.

### `generate_1k_csv.py`
Python Module. Classes: None. Functions: generate_1k_csv.

### `generate_1m_csv.py`
Python Module. Classes: None. Functions: generate_1m_csv.

### `generate_1m_excel.py`
Python Module. Classes: None. Functions: generate_1m_excel.

### `generate_scenarios.py`
Python Module. Classes: None. Functions: run_all_scenarios.

### `generate_test_csvs.py`
Python Module. Classes: None. Functions: None.

### `list_all_factors.py`
Python Module. Classes: None. Functions: None.

### `locustfile.py`
Python Module. Classes: GHGUser. Functions: on_start, view_dashboard_stats, view_intensity_stats, view_facilities, view_satellite_layer.

### `migrate_ogmp.py`
Python Module. Classes: None. Functions: migrate_database.

### `models.py`
Python Module. Classes: User, Facility, Emission, ProductionData, EmissionSource, CustomFactor, ActivityLog, Goal, BaseYear, MitigationRecord, Scope3Data, Scope2Emission, Scope3Emission, MitigationProject, BaseYearRecalculation, ReportingMetadata, Notification, CbamProductExport, OgmpSurvey, MethaneSourceType, LevelUpgradeLog. Functions: utc_now, set_password, check_password, create.

### `process_categories.py`
Python Module. Classes: None. Functions: get_process_types_for_segment, get_segments_for_process, get_process_types_by_category.

### `seed_admin.py`
Python Module. Classes: None. Functions: seed_admin.

### `test_csv_uploader.py`
Python Module. Classes: TestCSVUploaderE2E. Functions: setUpClass, tearDownClass, test_upload_csv_end_to_end.

### `test_emission_calculations.py`
Python Module. Classes: TestTier1Combustion, TestTier1CombustionDiesel, TestTier1Flaring, TestTier3Flaring, TestTier1Venting, TestTier3TankFlashing, TestTier3PneumaticDevices, TestTier3LiquidsUnloading, TestTier1DrillingMud, TestTier3Completions, TestTier1FugitiveAverage, TestCO2ECalculation, TestUnitConversions, TestEdgeCases, TestTier3CombustionGasComposition, TestProcessRowIntegration, SummaryResult, MockFacility. Functions: extract_val, setUp, test_structure, test_co2_tier1, test_ch4_tier1, test_n2o_tier1, test_co2e_total, test_unit_m3, setUp, test_co2_diesel, test_ch4_diesel, test_n2o_diesel, test_co2e_diesel, setUp, test_tier1_flaring_fallback_co2, test_tier1_flaring_fallback_ch4, setUp, test_tier3_flaring_ch4, test_tier3_flaring_co2, test_tier3_flaring_co2e, setUp, test_venting_ch4, test_venting_co2e, setUp, test_tank_ch4, test_tank_co2e, setUp, test_pneumatic_ch4, test_pneumatic_co2e, setUp, test_unloading_ch4, test_unloading_co2e, setUp, test_mud_ch4, test_mud_co2e, test_oil_based_mud, setUp, test_completions_ch4, test_completions_co2e, setUp, test_fugitive_average_ch4, test_pure_co2, test_pure_ch4_ar5, test_pure_n2o_ar5, test_mixed, test_ar4_gwp, test_ar6_gwp, test_scf_to_m3, test_m3_to_scf, test_bbl_to_m3, test_scf_m3_roundtrip, test_density_ch4, test_density_co2, test_zero_quantity_combustion, test_negative_quantity_raises, test_mmscf_unit_combustion, test_tank_zero_gor_returns_zero, test_combustion_mscf_unit, setUp, test_tier3_combustion_co2, _make_facility, test_combustion_process_row, test_missing_facility_returns_error, test_missing_date_returns_error, test_flaring_process_row, test_venting_process_row.

### `test_performance.py`
Python Module. Classes: None. Functions: test_benchmark_uncertainty_propagation.

### `test_runner.py`
Python Module. Classes: MockSession, MockDB, DummyFacility. Functions: bulk_save_objects, commit, __init__, __init__.

### `upload_test_s2_s3.py`
Python Module. Classes: None. Functions: test_upload.

### `utils.py`
Python Module. Classes: None. Functions: get_current_user, get_allowed_facility_ids, log_activity_and_notify.

### `calculations\base.py`
Python Module. Classes: BaseCalculator. Functions: __init__, validate_inputs, calculate_uncertainty, format_result.

### `calculations\combustion.py`
Python Module. Classes: CombustionCalculator, FlaringCalculator. Functions: __init__, calculate, __init__, calculate.

### `calculations\constants.py`
Python Module. Classes: None. Functions: get_active_gwp.

### `calculations\dispatcher.py`
Python Module. Classes: CalculationDispatcher. Functions: __init__, _require, _normalize_volume, _require_float, _require_fraction, _optional_fraction, dispatch, _generic_calculation, wrap, safe_frac, safe_frac, _wrap_unc.

### `calculations\fugitive.py`
Python Module. Classes: ComponentFugitiveCalculator, EquipmentFugitiveCalculator, CompressorSealCalculator. Functions: __init__, calculate, __init__, calculate, __init__, calculate.

### `calculations\indirect.py`
Python Module. Classes: IndirectSteamCalculator, CogenAllocationCalculator. Functions: __init__, calculate, __init__, calculate.

### `calculations\legacy_engine.py`
Python Module. Classes: GHGCalculator. Functions: compute_emissions, _to_rankine, _to_psia, _to_density_lb_gal, _to_ft3, _normalize_unit, convert_factor_to_kg, calculate_energy, calculate_default_kg, ef_fugitive_pipeline, ef_fugitive_average, ef_fugitive_screening_range, calculate_completions, calculate_unloading, get_val, _extract, get_factor.

### `calculations\midstream.py`
Python Module. Classes: AGRCalculator, DehydratorCalculator. Functions: __init__, calculate, __init__, calculate.

### `calculations\stoichiometry.py`
Python Module. Classes: StoichiometricCalculator. Functions: __init__, calculate.

### `calculations\uncertainty.py`
Python Module. Classes: Tier. Functions: combine_uncertainties_product, combine_uncertainties_sum, srss_inventory, propagate_uncertainty, resolve_tier, resolve_ef_uncertainty.

### `calculations\units.py`
Python Module. Classes: None. Functions: to_kelvin, to_fahrenheit, to_psia, normalize_gas_volume_to_standard, convert, calculate_co2e.

### `calculations\vented.py`
Python Module. Classes: MudDegassingCalculator, CompletionFlowbackCalculator, LiquidsUnloadingCalculator, BlowdownCalculator, TankFlashingCalculator, PneumaticDeviceCalculator. Functions: __init__, calculate, __init__, calculate, __init__, calculate, __init__, calculate, __init__, calculate, __init__, calculate.

### `calculations\__init__.py`
Python Module. Classes: None. Functions: None.

### `migrations\env.py`
Python Module. Classes: None. Functions: get_engine, get_engine_url, get_metadata, run_migrations_offline, run_migrations_online, process_revision_directives.

### `migrations\versions\2ef6f882b02c_add_ghg_uncertainties_to_customfactor.py`
Python Module. Classes: None. Functions: upgrade, downgrade.

### `migrations\versions\61bacaad00dc_add_uncertainty_ch4_n2o_columns.py`
Python Module. Classes: None. Functions: upgrade, downgrade.

### `migrations\versions\7fe333372c71_add_performance_indexes.py`
Python Module. Classes: None. Functions: upgrade, downgrade.

### `migrations\versions\815d10c5bbe4_add_segment_field_to_facilities_table.py`
Python Module. Classes: None. Functions: upgrade, downgrade.

### `routes\audit.py`
Python Module. Classes: None. Functions: get_audit_logs, get_audit_filters.

### `routes\auth.py`
Python Module. Classes: None. Functions: validate_password_complexity, is_safe_image_url, login_required, admin_required, superuser_required, register, login, logout, me, update_profile, change_password, upload_avatar, recalculate_all_emissions_gwp, get_settings, update_settings, get_users, update_user, delete_user, decorated_function, decorated_function, decorated_function.

### `routes\custom_factors.py`
Python Module. Classes: None. Functions: get_custom_factors, create_custom_factor, update_custom_factor, delete_custom_factor, import_custom_factors.

### `routes\dashboard.py`
Python Module. Classes: None. Functions: clear_dashboard_cache, make_cache_key, _run_in_app_ctx, get_batch_dashboard_data, get_intensity_trend, _query_summary, _query_mitigation, _query_scope3_summary, _query_categorical_breakdown, _query_available_years, get_dashboard_summary, get_available_years, get_mitigation, get_scope3_summary, get_goal, create_goal, get_base_year, get_categorical_breakdown, create_base_year_recalculation, get_ogmp_metrics, get_intensity_stats, _query_intensity_trend_bulk, _query_intensity_stats, get_uncertainty_analysis, _query_uncertainty, get_report_exclusions, cache_key_builder, get_ef_uncertainty.

### `routes\data.py`
Python Module. Classes: None. Functions: get_production, add_production, delete_production, bulk_import_production, get_methane_sources, get_ogmp_surveys, save_ogmp_survey, delete_ogmp_survey, log_level_upgrade, get_level_logs, get_cbam_exports, save_cbam_export, delete_cbam_export.

### `routes\emissions.py`
Python Module. Classes: None. Functions: get_current_user, _escape_like, get_emissions, resolve_gwp_dict, resolve_gwp_standard, add_bulk_upload, get_csv_template, get_excel_template, upload_start, upload_status, upload_errors, add_emission, delete_emission, update_emission, bulk_delete_emissions, import_emissions, export_emissions, apply_filters, _row, hdr_style, sub_hdr, info_cell, req_cell, add_comment.

### `routes\emission_factors_routes.py`
Python Module. Classes: None. Functions: get_all_emission_factors, get_segments, get_factors_for_segment, get_all_process_types, get_process_types_for_seg, get_factors_for_process_category, get_factors_by_seg_and_proc, search_emission_factors, get_factors_with_uncertainties, get_emission_factors_stats, get_database_version.

### `routes\facilities.py`
Python Module. Classes: None. Functions: get_facilities, get_all_regions, add_facility, update_facility, delete_facility, import_facilities.

### `routes\managedata.py`
Python Module. Classes: None. Functions: get_sources, add_source, delete_source, bulk_import_sources, get_mitigations, add_mitigation, delete_mitigation, get_reporting_metadata, save_reporting_metadata, get_production_years, get_available_filters, bulk_import_mitigation, get_all_goals, add_or_update_goal, delete_goal, get_base_years, add_base_year_recalculation, delete_base_year_recalculation.

### `routes\notifications.py`
Python Module. Classes: None. Functions: get_notifications, stream_notifications, mark_read, dismiss_all, delete_notification, delete_all_notifications, generate.

### `routes\reports.py`
Python Module. Classes: None. Functions: _safe_excel_value, create_pdf_report, generate_report, export_emissions, export_ogmp_excel, style_header_row, autofit_columns.

### `routes\satellite.py`
Python Module. Classes: None. Functions: _get_user_copernicus_credentials, test_copernicus_connection, get_satellite_layer_config, get_facility_satellite_data, export_satellite_to_ogmp, poll_new_satellite_passes.

### `routes\scope2.py`
Python Module. Classes: None. Functions: _calc_indirect_steam, _calc_cogen_allocation, get_scope2_emissions, create_scope2_emission, update_scope2_emission, delete_scope2_emission, bulk_import_scope2, get_emission_factors.

### `routes\scope3.py`
Python Module. Classes: None. Functions: get_scope3_emissions, create_scope3_emission, update_scope3_emission, delete_scope3_emission, bulk_import_scope3.

### `routes\__init__.py`
Python Module. Classes: None. Functions: None.

### `services\sentinel5p.py`
Python Module. Classes: Sentinel5PService. Functions: __init__, test_connection, get_token, get_layer_config, query_satellite_observations, estimate_emission_rate_from_anomaly.

### `services\__init__.py`
Python Module. Classes: None. Functions: None.

### `tests\conftest.py`
Python Module. Classes: None. Functions: None.

### `tests\test_all_bulk_imports.py`
Python Module. Classes: None. Functions: app, client, logged_client, wait_for_job, test_bulk_import_facilities, test_bulk_import_custom_factors, test_bulk_import_production, test_bulk_import_sources, test_bulk_import_mitigation, test_bulk_import_scope2, test_bulk_import_scope3, test_bulk_import_scope1.

### `tests\test_api_security.py`
Python Module. Classes: TestUnauthenticatedAccess, TestIDOR, TestInputLimits, TestRateLimiting, TestCalculationIntegrity. Functions: app, client, admin_user, regular_user, login, test_get_emissions_requires_auth, test_delete_emission_requires_auth, test_bulk_delete_requires_auth, test_import_requires_auth, test_export_requires_auth, test_emission_factors_requires_auth, test_audit_post_removed, test_health_does_not_expose_db, test_user_cannot_delete_other_users_emission, test_user_can_delete_own_emission, test_limit_all_capped_at_5000, test_large_payload_rejected, test_wildcard_search_does_not_crash, test_login_rate_limit, test_calculation_error_returns_422_not_zero.

### `tests\test_combustion.py`
Python Module. Classes: None. Functions: test_flaring_calculator_basic, test_flaring_calculator_specific_c1_c10, test_stationary_combustion_calculator.

### `tests\test_dispatcher.py`
Python Module. Classes: None. Functions: test_dispatcher_flaring_routing, test_dispatcher_unit_normalization, test_dispatcher_combustion_fallback, test_tier3_strict_validation_unloading_missing_fields, test_tier3_strict_validation_blowdown_missing_fields, test_tier3_strict_validation_pneumatics_missing_fields, test_tier3_strict_validation_agr_missing_fields, test_tier1_default_pneumatics, test_agr_methane_slip_calculation, test_dehydrator_parametric_solubility, test_blowdown_temperature_correction, test_completions_flowback_methods.

### `tests\test_gwp_dynamic.py`
Python Module. Classes: None. Functions: test_constants_and_helpers, test_calculate_co2e_dynamic, test_legacy_engine_dynamic_gwp.

### `tests\test_satellite.py`
Python Module. Classes: None. Functions: test_sentinel5p_flux_calculation, test_sentinel5p_layer_config_unauthenticated, test_sentinel5p_strict_no_fake_data_when_unconfigured, test_sentinel5p_connection_test_mocked_success, test_sentinel5p_connection_test_mocked_failure.

### `tests\test_vented.py`
Python Module. Classes: None. Functions: test_tanks_calculator, test_pneumatics_calculator, test_blowdown_calculator.

## Frontend (Client)

### `api.js`
JS/React Component. Classes: None. Functions/Components: fetchCsrfToken.

### `App.jsx`
JS/React Component. Classes: None. Functions/Components: PrivateRoute, NonITRoute, App, AdminRoute, ITRoute, AppRoutes.

### `constants.js`
JS/React Component. Classes: None. Functions/Components: getActiveGwpFactors.

### `main.jsx`
JS/React Component. Classes: None. Functions/Components: None.

### `components\BulkImportModal.jsx`
JS/React Component. Classes: None. Functions/Components: handlePreview, downloadTemplate, parseCSV, handleFileChange, BulkImportModal, handleImport, isMappingValid, validateData.

### `components\CalculationDetails.jsx`
JS/React Component. Classes: None. Functions/Components: CalculationDetails, formatNumber.

### `components\ColumnMappingWizard.jsx`
JS/React Component. Classes: None. Functions/Components: IconsSettings, onFileInputChange, downloadTemplate, StepIndicator, MappingRow, handleSubmit, autoDetectMapping, ColumnMappingWizard, onDrop.

### `components\CsvUploader.jsx`
JS/React Component. Classes: None. Functions/Components: CsvUploader.

### `components\CustomDropdown.jsx`
JS/React Component. Classes: None. Functions/Components: handleClickOutside, CustomDropdown, handleSelect.

### `components\EmissionFactorOption.jsx`
JS/React Component. Classes: None. Functions/Components: EmissionFactorOption.

### `components\EmissionResult.jsx`
JS/React Component. Classes: None. Functions/Components: EmissionResult, formatNumber, getConfidenceInterval, formatUncertainty.

### `components\ErrorBoundary.jsx`
JS/React Component. Classes: ErrorBoundary. Functions/Components: None.

### `components\FormField.jsx`
JS/React Component. Classes: None. Functions/Components: SelectField, DateField, TextAreaField, RadioGroupField, CheckboxField, TextField.

### `components\GasCompositionCalculator.jsx`
JS/React Component. Classes: None. Functions/Components: calculate, handleCompChange, handleSave, handleParamChange, GasCompositionCalculator, getStatusText, handleApply, handleModeChange.

### `components\LoadingSpinner.jsx`
JS/React Component. Classes: None. Functions/Components: LoaderContent, LoadingSpinner.

### `components\Modal.jsx`
JS/React Component. Classes: None. Functions/Components: handleBackdropClick, Modal.

### `components\MultiSelectDropdown.jsx`
JS/React Component. Classes: None. Functions/Components: handleClickOutside, MultiSelectDropdown, toggleOption, handleSelectAll.

### `components\NotificationCenter.jsx`
JS/React Component. Classes: None. Functions/Components: relativeTime, handleMarkAllRead, NotificationCenter, getTypeConfig, handleMarkRead, BellButton, handler, handleDelete, handleDeleteAll, NotifRow.

### `components\Scope1Form.jsx`
JS/React Component. Classes: None. Functions/Components: Scope1Form, exportToCSV, getFacilityOptions, updateUncertaintyFromFactor, renderSpecificForm, loadFacilities, loadProcessTypes, getProcessOptions, getEmissionSourceOptions, handleGasApply, handleFormChange, loadCustomFactors, handleDelete, loadEntries, handleAddEntry, renderFactorOption, handleProcessChange, loadEmissionSources.

### `components\Scope1ImportWizard.jsx`
JS/React Component. Classes: None. Functions/Components: StepBar, ModeCard, downloadTemplate, ProcessTile, onFileChange, toggleProcess, Scope1ImportWizard, MappingRow, canGoNext, onDrop, autoDetect, handleSubmit, FieldGroup.

### `components\Scope2Form.jsx`
JS/React Component. Classes: None. Functions/Components: getGridOptions, loadFacilities, handleImportSuccess, handleDuplicate, loadGridFactors, handleDelete, loadEntries, handleAddEntry, getFacilityOptions, Scope2Form.

### `components\Scope2ImportWizard.jsx`
JS/React Component. Classes: None. Functions/Components: StepBar, onFileChange, MappingRow, onDrop, autoDetect, handleSubmit, Scope2ImportWizard, FieldGroup.

### `components\Scope3Form.jsx`
JS/React Component. Classes: None. Functions/Components: getCategoryOptions, loadFacilities, Scope3Form, handleUnitChange, getActivityOptions, handleImportSuccess, handleDelete, loadEntries, handleAddEntry, getFacilityOptions.

### `components\Scope3ImportWizard.jsx`
JS/React Component. Classes: None. Functions/Components: StepBar, Scope3ImportWizard, onFileChange, MappingRow, onDrop, autoDetect, handleSubmit, FieldGroup.

### `components\SkeletonLoader.jsx`
JS/React Component. Classes: None. Functions/Components: SkeletonTable, SkeletonRow, SkeletonCard.

### `components\Toast.jsx`
JS/React Component. Classes: None. Functions/Components: ToastContainer, ToastProvider, Toast, getIcon, useToast.

### `components\UploadProgress.jsx`
JS/React Component. Classes: None. Functions/Components: UploadProgress, categoryFromReason, IconX, IconCheck, Spinner, IconChevron, downloadErrors, IconWarn, IconDownload.

### `components\charts\BarChart.jsx`
JS/React Component. Classes: None. Functions/Components: BarChart, CustomTooltip.

### `components\charts\index.js`
JS/React Component. Classes: None. Functions/Components: None.

### `components\charts\LineChart.jsx`
JS/React Component. Classes: None. Functions/Components: LineChart, CustomTooltip.

### `components\charts\PieChart.jsx`
JS/React Component. Classes: None. Functions/Components: CustomTooltip, PieChart.

### `components\layout\Layout.jsx`
JS/React Component. Classes: None. Functions/Components: Layout.

### `components\layout\Sidebar.jsx`
JS/React Component. Classes: None. Functions/Components: handleClickOutside, handleLogout, Sidebar.

### `components\layout\TopBar.jsx`
JS/React Component. Classes: None. Functions/Components: handleClickOutside, TopBar.

### `components\scope1\AGRForm.jsx`
JS/React Component. Classes: None. Functions/Components: AGRForm.

### `components\scope1\BlowdownForm.jsx`
JS/React Component. Classes: None. Functions/Components: BlowdownForm.

### `components\scope1\CombustionForm.jsx`
JS/React Component. Classes: None. Functions/Components: CombustionForm.

### `components\scope1\CompletionsForm.jsx`
JS/React Component. Classes: None. Functions/Components: CompletionsForm.

### `components\scope1\DehydratorForm.jsx`
JS/React Component. Classes: None. Functions/Components: DehydratorForm.

### `components\scope1\DrillingForm.jsx`
JS/React Component. Classes: None. Functions/Components: DrillingForm.

### `components\scope1\FugitivesForm.jsx`
JS/React Component. Classes: None. Functions/Components: FugitivesForm, handleMethodChange.

### `components\scope1\PneumaticsForm.jsx`
JS/React Component. Classes: None. Functions/Components: PneumaticsForm.

### `components\scope1\TankForm.jsx`
JS/React Component. Classes: None. Functions/Components: TankForm.

### `components\scope1\UnloadingForm.jsx`
JS/React Component. Classes: None. Functions/Components: UnloadingForm.

### `context\AuthContext.jsx`
JS/React Component. Classes: None. Functions/Components: useAuth, updatePreferences, AuthProvider, checkAuth, login, logout, register, applyTheme.

### `context\LayoutContext.jsx`
JS/React Component. Classes: None. Functions/Components: useLayout, LayoutProvider.

### `pages\AuditTrail.jsx`
JS/React Component. Classes: None. Functions/Components: applyFilters, getActionIcon, fetchAuditLogs, formatTimestamp, AuditTrail, fetchFilters, getActionColor.

### `pages\CarbonIntensity.jsx`
JS/React Component. Classes: None. Functions/Components: getHeatmapClass, init, getRegionOptions, getActivityOptions, getDivisionOptions, loadIntensityData, handleActivityChange, getSegmentOptions, loadTrendData, loadCbamData, handleDivisionChange, handleSegmentChange, CarbonIntensity.

### `pages\DashboardEnhanced.jsx`
JS/React Component. Classes: None. Functions/Components: loadDashboardData, calculateForecast, DashboardEnhanced, formatActivityName, toggleDivision, getRegionOptions, getActivityOptions, getDivisionOptions, handleActivityChange, getSegmentOptions, loadInitialData, loadCategoricalData, toggleActivity, getYearOptions, handleDivisionChange, handleSegmentChange.

### `pages\Diagnostics.jsx`
JS/React Component. Classes: None. Functions/Components: analyzeData, Diagnostics, runDiagnostics.

### `pages\Emissions.jsx`
JS/React Component. Classes: None. Functions/Components: goToStage, renderSelectionScreen, Emissions.

### `pages\Login.jsx`
JS/React Component. Classes: None. Functions/Components: animate, Login, handleLogin, handleMouseMove, GhgCloud, handleIntroEnd.

### `pages\ManageData.jsx`
JS/React Component. Classes: None. Functions/Components: fetchFacilities, handleSaveFactor, fetchGoals, getFilteredBaseYears, handleSaveProduction, handleSaveGoal, handleSaveMitigation, getAvailableDivisions, fetchSources, handleSaveCbamExport, exportToCSV, handleTabChange, handleAddFacility, handleImportCSV, getFilteredFacilities, fetchCbamExports, PaginationControls, getFilteredOgmp, ManageData, handleDeleteOgmpSurvey, handleDeleteBaseYearRecalc, getAvailableActivities, handleEditFactor, fetchProduction, handleSaveSource, getFilteredSources, getFilteredCbam, handleSaveOgmpSurvey, fetchBaseYears, fetchOgmpSurveys, handleDeleteGoal, handleDeleteCbamExport, ManageDataInner, handleSaveBaseYear, handleFactorChange, handleEditGoal, handleFacilityChange, getFilteredMitigations, openOilConverter, fetchMitigations, fetchCustomFactors, getFilteredFactors, getFilteredGoals, openGasConverter, handleDeleteFactor, getFilteredProduction.

### `pages\MethaneExplorer.jsx`
JS/React Component. Classes: None. Functions/Components: createSolidIcon, fetchData, handleExportToOgmp, handleSelectFacility, EmissionsMap, createPulsingIcon, getIntensityData, MapController, getPulseClass, formatCompact.

### `pages\MethaneIntensity.jsx`
JS/React Component. Classes: None. Functions/Components: getHeatmapClass, loadRoadmapData, loadOgmpData, init, handleSegmentChange, loadMethaneData, MethaneIntensity, getActivityOptions, getDivisionOptions, getRegionOptions, handleActivityChange, getSegmentOptions, loadTrendData, handleDivisionChange, handleExportExcel.

### `pages\ReferenceData.jsx`
JS/React Component. Classes: None. Functions/Components: ReferenceData, toggleCategory, filterFactors, fetchData.

### `pages\Reports.jsx`
JS/React Component. Classes: None. Functions/Components: Reports, handleExcelExport, handlePDFExport, handleISOReport, handleOGMPExport, formatNumber, handleISOReportWrapper, removeRegion, fetchEmissions, loadInitialData, openConfigModal, resetFilters, getGroupedData.

### `pages\Settings.jsx`
JS/React Component. Classes: None. Functions/Components: Settings, handleFacilityChange, handleThemeChange, handleSaveFacility, applyThemeLive, handleSaveGlobal, loadSettings, handleTestConnection.

### `pages\UncertaintyAssessment.jsx`
JS/React Component. Classes: None. Functions/Components: UncertaintyAssessment, fetchData.

### `pages\UserManagement.jsx`
JS/React Component. Classes: None. Functions/Components: fetchData, handleOpenModal, getRoleMeta, UserManagement, focusProps, inputStyle, handleDelete, handleSubmit.

### `utils\constants.js`
JS/React Component. Classes: None. Functions/Components: None.

### `utils\EmissionFactors.js`
JS/React Component. Classes: None. Functions/Components: None.

### `utils\emissionFactorsAPI.js`
JS/React Component. Classes: None. Functions/Components: getFactorsByProcess, getFactorStats, getFactorUncertainty, getSegmentBgColor, convertActivityData, getFactorsBySegmentAndProcess, getFactorsWithUncertainties, getProcessTypesForSegment, formatUncertainty, getSegments, getSegmentColor, getFactorVersion, searchEmissionFactors, getFactorsBySegment.

### `utils\formatters.js`
JS/React Component. Classes: None. Functions/Components: formatNumber, formatCompactNumber, formatDate, calculateTrend.

### `utils\ModernReportGenerator.js`
JS/React Component. Classes: None. Functions/Components: getScopeInterpretation, addSectionHeader, generateModernPDF, drawFooter, drawBackground, addTextBlock, generateReportCharts, toRgba, loadImage, checkPageBreak, getTrendInterpretation, createChartImage, fetchAllReportData.
