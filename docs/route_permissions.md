# NeoCarbon API Route Permissions & Authorization Matrix

| HTTP Method | Route URL | Endpoint | Required Role | IDOR / Tenant Scoping | Description |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `GET` | `/` | `index` | **Public** | N/A | index |
| `GET` | `/api/activity-factors` | `factors.get_activity_factors` | **Authenticated User** | N/A | API Compendium activity factors (Section 6 tables), optional |
| `GET` | `/api/audit/` | `audit.get_audit_logs` | **Authenticated User** | N/A | audit.get_audit_logs |
| `GET` | `/api/audit/export` | `audit.export_audit_logs` | **Authenticated User** | N/A | audit.export_audit_logs |
| `GET` | `/api/audit/export/` | `audit.export_audit_logs` | **Authenticated User** | N/A | audit.export_audit_logs |
| `GET` | `/api/audit/filters` | `audit.get_audit_filters` | **Authenticated User** | N/A | audit.get_audit_filters |
| `GET` | `/api/audit/filters/` | `audit.get_audit_filters` | **Authenticated User** | N/A | audit.get_audit_filters |
| `GET` | `/api/audit/stats` | `audit.get_audit_stats` | **Authenticated User** | N/A | audit.get_audit_stats |
| `GET` | `/api/audit/stats/` | `audit.get_audit_stats` | **Authenticated User** | N/A | audit.get_audit_stats |
| `GET` | `/api/audit/verify-chain` | `audit.verify_audit_chain` | **Auditor (Read-Only) / Admin** | N/A | Verifies the audit log's hash chain (services/audit_chain.py |
| `POST` | `/api/audit/verify-checkpoint` | `audit.verify_audit_checkpoint` | **Auditor (Read-Only) / Admin** | N/A | Verifies a third-party auditor's sealed audit manifest check |
| `POST` | `/api/auth/change-password` | `auth.change_password` | **Authenticated User** | N/A | auth.change_password |
| `POST` | `/api/auth/forgot-password` | `auth.forgot_password` | **IT Manager / Admin** | N/A | User triggers a password reset request. |
| `GET` | `/api/auth/keepalive` | `auth.keepalive` | **Authenticated User** | N/A | The browser calls this while the user is active without send |
| `POST` | `/api/auth/login` | `auth.login` | **Public** | N/A | auth.login |
| `POST` | `/api/auth/logout` | `auth.logout` | **Public** | N/A | auth.logout |
| `GET` | `/api/auth/me` | `auth.me` | **Authenticated User** | N/A | auth.me |
| `PUT` | `/api/auth/profile` | `auth.update_profile` | **Authenticated User** | N/A | auth.update_profile |
| `POST` | `/api/auth/register` | `auth.register` | **Admin** | N/A | auth.register |
| `GET` | `/api/auth/sessions/policy` | `auth.get_session_policy` | **Authenticated User** | N/A | Retrieve operational session governance policies and statist |
| `PUT` | `/api/auth/sessions/policy` | `auth.update_session_policy` | **Admin** | N/A | Update idle session timeout configuration. |
| `POST` | `/api/auth/sessions/revoke-all` | `auth.revoke_all_sessions` | **Admin** | N/A | Invalidate all active sessions across the platform by bumpin |
| `GET` | `/api/auth/settings` | `auth.get_settings` | **Authenticated User** | N/A | auth.get_settings |
| `POST, PUT` | `/api/auth/settings` | `auth.update_settings` | **Admin** | N/A | auth.update_settings |
| `POST` | `/api/auth/upload-avatar` | `auth.upload_avatar` | **Authenticated User** | N/A | auth.upload_avatar |
| `GET` | `/api/auth/users` | `auth.get_users` | **Authenticated User** | N/A | auth.get_users |
| `POST` | `/api/auth/users` | `auth.create_user` | **Admin** | N/A | auth.create_user |
| `PUT` | `/api/auth/users/<int:id>` | `auth.update_user` | **Admin** | Protected (Scoped by Facility/Org/Tenant) | auth.update_user |
| `DELETE` | `/api/auth/users/<int:id>` | `auth.delete_user` | **Admin** | Protected (Admin Only) | auth.delete_user |
| `POST` | `/api/auth/users/<int:id>/reset-password` | `auth.admin_reset_password` | **IT Manager / Admin** | Protected (Scoped by Facility/Org/Tenant) | IT Admin resets a user's password directly (global authority |
| `POST` | `/api/auth/users/<int:id>/revoke-sessions` | `auth.revoke_user_sessions` | **Admin** | Protected (Scoped by Facility/Org/Tenant) | Revoke all active sessions for a specific user. |
| `GET` | `/api/base-years` | `managedata.get_base_years` | **IT Manager / Admin** | N/A | managedata.get_base_years |
| `POST` | `/api/base-years` | `managedata.add_base_year_recalculation` | **IT Manager / Admin** | N/A | managedata.add_base_year_recalculation |
| `GET` | `/api/base-years/` | `managedata.get_base_years` | **IT Manager / Admin** | N/A | managedata.get_base_years |
| `POST` | `/api/base-years/` | `managedata.add_base_year_recalculation` | **IT Manager / Admin** | N/A | managedata.add_base_year_recalculation |
| `DELETE` | `/api/base-years/<int:rec_id>` | `managedata.delete_base_year_recalculation` | **IT Manager / Admin** | Protected (Scoped by Facility/Org/Tenant) | managedata.delete_base_year_recalculation |
| `GET` | `/api/csrf-token` | `get_csrf_token` | **Authenticated User** | N/A | Issues a CSRF token for the double-submit cookie pattern. |
| `GET` | `/api/custom-factors` | `custom_factors.get_custom_factors` | **IT Manager / Admin** | N/A | Get all custom emission factors |
| `POST` | `/api/custom-factors` | `custom_factors.create_custom_factor` | **Admin / Superuser** | N/A | Create a new custom emission factor (Super User / Admin only |
| `GET` | `/api/custom-factors/` | `custom_factors.get_custom_factors` | **IT Manager / Admin** | N/A | Get all custom emission factors |
| `POST` | `/api/custom-factors/` | `custom_factors.create_custom_factor` | **Admin / Superuser** | N/A | Create a new custom emission factor (Super User / Admin only |
| `PUT` | `/api/custom-factors/<int:factor_id>` | `custom_factors.update_custom_factor` | **Admin** | Protected (Scoped by Facility/Org/Tenant) | Update a custom emission factor (Super User / Admin only) |
| `DELETE` | `/api/custom-factors/<int:factor_id>` | `custom_factors.delete_custom_factor` | **Admin / Superuser** | Protected (Scoped by Facility/Org/Tenant) | Delete a custom emission factor (Super User / Admin only) |
| `POST` | `/api/custom-factors/<int:factor_id>/approve` | `custom_factors.approve_custom_factor` | **Admin** | Protected (Scoped by Facility/Org/Tenant) | Approve a pending custom emission factor (superuser or admin |
| `POST` | `/api/custom-factors/<int:factor_id>/archive` | `custom_factors.archive_custom_factor` | **Admin / Superuser** | Protected (Scoped by Facility/Org/Tenant) | BUG-056: hide a factor from new entries while keeping it for |
| `GET` | `/api/custom-factors/<int:factor_id>/history` | `custom_factors.get_factor_history` | **Authenticated User** | Review Required / Scoped | Part 2.1: Full audit history and version lineage for a custo |
| `POST` | `/api/custom-factors/<int:factor_id>/reject` | `custom_factors.reject_custom_factor` | **Admin / Superuser** | Protected (Scoped by Facility/Org/Tenant) | Reject a pending custom emission factor (superuser or admin) |
| `GET` | `/api/custom-factors/gwp-standards` | `custom_factors.get_gwp_standards` | **Authenticated User** | N/A | Part 2.1: Versioned IPCC Global Warming Potential (GWP) stan |
| `POST` | `/api/custom-factors/import` | `custom_factors.import_custom_factors` | **Admin / Superuser** | N/A | Bulk import custom factors from CSV/Excel (Super User / Admi |
| `GET` | `/api/dashboard/base-year` | `dashboard.get_base_year` | **Authenticated User** | N/A | Get most recent base year recalculation or baseline |
| `POST` | `/api/dashboard/base-year-recalculation` | `dashboard.create_base_year_recalculation` | **Authenticated User** | N/A | Create a new base year recalculation entry (delegates to can |
| `GET` | `/api/dashboard/batch-all` | `dashboard.get_batch_dashboard_data` | **Authenticated User** | N/A | Consolidated dashboard API — all sub-queries run in parallel |
| `GET` | `/api/dashboard/categorical-breakdown` | `dashboard.get_categorical_breakdown` | **Authenticated User** | N/A | Get emissions breakdown by Activity -> Division -> Region. |
| `GET` | `/api/dashboard/equipment-emissions` | `dashboard.get_equipment_emissions` | **Authenticated User** | N/A | Returns top equipment emissions breakdown for a given proces |
| `GET` | `/api/dashboard/exclusions` | `dashboard.get_report_exclusions` | **Authenticated User** | N/A | Fetches items marked as exclusions for the report. |
| `GET` | `/api/dashboard/flaring-summary` | `dashboard.get_flaring_summary` | **Authenticated User** | N/A | Flaring by operational stream (Routine / Non-Routine / Safet |
| `GET` | `/api/dashboard/goals/<int:year>` | `dashboard.get_goal` | **Authenticated User** | Review Required / Scoped | Get goal for specific year |
| `GET` | `/api/dashboard/granular-intensities` | `dashboard.get_granular_intensities` | **Authenticated User** | N/A | Multi-metric intensities for the Master Report (BUG-044). |
| `GET` | `/api/dashboard/intensity-stats` | `dashboard.get_intensity_stats` | **Authenticated User** | N/A | Get intensity metrics (kg/BOE) per facility. |
| `GET` | `/api/dashboard/intensity-trend` | `dashboard.get_intensity_trend` | **Authenticated User** | N/A | dashboard.get_intensity_trend |
| `GET` | `/api/dashboard/mitigation` | `dashboard.get_mitigation` | **Authenticated User** | N/A | Get all mitigation projects and records with filtering. |
| `GET` | `/api/dashboard/ogmp-metrics` | `dashboard.get_ogmp_metrics` | **Authenticated User** | N/A | OGMP 2.0 Gold Standard roadmap & milestone progress per faci |
| `GET` | `/api/dashboard/sbti-trajectory` | `dashboard.get_sbti_trajectory` | **Authenticated User** | N/A | dashboard.get_sbti_trajectory |
| `GET` | `/api/dashboard/scope3/summary` | `dashboard.get_scope3_summary` | **Authenticated User** | N/A | Get Scope 3 emissions summary with filtering. |
| `GET` | `/api/dashboard/summary` | `dashboard.get_dashboard_summary` | **Authenticated User** | N/A | Get aggregated emissions data for dashboard. |
| `GET` | `/api/dashboard/uncertainty` | `dashboard.get_uncertainty_analysis` | **Authenticated User** | N/A | Quantifies inventory uncertainty per ISO 14064-1 §4.6.5. |
| `GET` | `/api/dashboard/years` | `dashboard.get_available_years` | **Authenticated User** | N/A | Get list of all years present in the emissions and productio |
| `GET` | `/api/dashboard/yoy-bridge` | `dashboard.get_yoy_bridge` | **Authenticated User** | N/A | Scope 1+2 change between the selected year and the closest e |
| `GET` | `/api/data/cbam-exports` | `data.get_cbam_exports` | **Authenticated User** | N/A | data.get_cbam_exports |
| `POST` | `/api/data/cbam-exports` | `data.save_cbam_export` | **Auditor (Read-Only) / Admin** | N/A | data.save_cbam_export |
| `GET` | `/api/data/cbam-exports/` | `data.get_cbam_exports` | **Authenticated User** | N/A | data.get_cbam_exports |
| `POST` | `/api/data/cbam-exports/` | `data.save_cbam_export` | **Auditor (Read-Only) / Admin** | N/A | data.save_cbam_export |
| `DELETE` | `/api/data/cbam-exports/<int:record_id>` | `data.delete_cbam_export` | **Auditor (Read-Only) / Admin** | Review Required / Scoped | data.delete_cbam_export |
| `GET` | `/api/data/methane-sources` | `data.get_methane_sources` | **Authenticated User** | N/A | data.get_methane_sources |
| `GET` | `/api/data/ogmp-surveys` | `data.get_ogmp_surveys` | **Authenticated User** | N/A | data.get_ogmp_surveys |
| `POST` | `/api/data/ogmp-surveys` | `data.save_ogmp_survey` | **Auditor (Read-Only) / Admin** | N/A | data.save_ogmp_survey |
| `GET` | `/api/data/ogmp-surveys/` | `data.get_ogmp_surveys` | **Authenticated User** | N/A | data.get_ogmp_surveys |
| `POST` | `/api/data/ogmp-surveys/` | `data.save_ogmp_survey` | **Auditor (Read-Only) / Admin** | N/A | data.save_ogmp_survey |
| `DELETE` | `/api/data/ogmp-surveys/<int:record_id>` | `data.delete_ogmp_survey` | **Admin / Superuser** | Protected (Scoped by Facility/Org/Tenant) | data.delete_ogmp_survey |
| `GET` | `/api/data/ogmp/level-logs` | `data.get_level_logs` | **Authenticated User** | N/A | data.get_level_logs |
| `POST` | `/api/data/ogmp/level-upgrade` | `data.log_level_upgrade` | **Auditor (Read-Only) / Admin** | N/A | data.log_level_upgrade |
| `GET` | `/api/data/production` | `data.get_production` | **Authenticated User** | N/A | data.get_production |
| `POST` | `/api/data/production` | `data.add_production` | **Admin / Superuser** | N/A | data.add_production |
| `GET` | `/api/data/production/` | `data.get_production` | **Authenticated User** | N/A | data.get_production |
| `POST` | `/api/data/production/` | `data.add_production` | **Admin / Superuser** | N/A | data.add_production |
| `DELETE` | `/api/data/production/<int:record_id>` | `data.delete_production` | **Auditor (Read-Only) / Admin** | Protected (Scoped by Facility/Org/Tenant) | data.delete_production |
| `POST` | `/api/data/production/bulk-import` | `data.bulk_import_production` | **Auditor (Read-Only) / Admin** | N/A | data.bulk_import_production |
| `GET` | `/api/docs/` | `swagger_ui.show` | **Authenticated User** | N/A | swagger_ui.show |
| `GET` | `/api/docs/<path:path>` | `swagger_ui.show` | **Authenticated User** | N/A | swagger_ui.show |
| `GET` | `/api/docs/dist/<path:filename>` | `swagger_ui.static` | **Authenticated User** | N/A | The view function used to serve files from |
| `GET` | `/api/emission-factors` | `factors.get_all_emission_factors` | **Authenticated User** | N/A | Get all emission factors. |
| `GET` | `/api/emission-factors/by-process/<process_category>` | `factors.get_factors_for_process_category` | **Authenticated User** | N/A | Get emission factors for a specific process category. |
| `GET` | `/api/emission-factors/by-segment-and-process` | `factors.get_factors_by_seg_and_proc` | **Authenticated User** | N/A | Get emission factors for a specific segment AND process cate |
| `GET` | `/api/emission-factors/by-segment/<segment>` | `factors.get_factors_for_segment` | **Authenticated User** | N/A | Get emission factors for a specific segment. |
| `GET` | `/api/emission-factors/process-types` | `factors.get_all_process_types` | **Authenticated User** | N/A | Get all available process types. |
| `GET` | `/api/emission-factors/process-types/<segment>` | `factors.get_process_types_for_seg` | **Authenticated User** | N/A | Get process types applicable to a specific segment. |
| `GET` | `/api/emission-factors/search` | `factors.search_emission_factors` | **Authenticated User** | N/A | Search emission factors by name, code, or description. |
| `GET` | `/api/emission-factors/segments` | `factors.get_segments` | **Authenticated User** | N/A | Get all available segments. |
| `GET` | `/api/emission-factors/stats` | `factors.get_emission_factors_stats` | **Authenticated User** | N/A | Get statistics about the emission factors database. |
| `GET` | `/api/emission-factors/uncertainties` | `factors.get_factors_with_uncertainties` | **Authenticated User** | N/A | Get all emission factors that have uncertainty values define |
| `GET` | `/api/emission-factors/version` | `factors.get_database_version` | **Authenticated User** | N/A | Get the version and source information for the emission fact |
| `GET` | `/api/emissions/` | `emissions.get_emissions` | **IT Manager / Admin** | N/A | emissions.get_emissions |
| `POST` | `/api/emissions/` | `emissions.add_emission` | **IT Manager / Admin** | N/A | emissions.add_emission |
| `DELETE` | `/api/emissions/<id>` | `emissions.delete_emission` | **Authenticated User** | Review Required / Scoped | emissions.delete_emission |
| `PUT` | `/api/emissions/<id>` | `emissions.update_emission` | **IT Manager / Admin** | Protected (Scoped by Facility/Org/Tenant) | emissions.update_emission |
| `POST` | `/api/emissions/approve/<int:emission_id>` | `emissions.approve_emission` | **Authenticated User** | Review Required / Scoped | Approve a single record awaiting review (Scope 1, 2 or 3) —  |
| `POST` | `/api/emissions/approve/batch` | `emissions.approve_batch_emissions` | **Authenticated User** | N/A | Approve records awaiting review. Body: {by_scope: {"1": [... |
| `POST` | `/api/emissions/bulk-delete` | `emissions.bulk_delete_emissions` | **Authenticated User** | N/A | emissions.bulk_delete_emissions |
| `POST` | `/api/emissions/bulk-upload` | `emissions.add_bulk_upload` | **IT Manager / Admin** | N/A | emissions.add_bulk_upload |
| `POST` | `/api/emissions/erp/sync` | `emissions.trigger_erp_sync` | **Admin / Superuser** | N/A | ERP integration endpoint. No ERP connector is implemented: t |
| `GET` | `/api/emissions/export` | `emissions.export_emissions` | **IT Manager / Admin** | N/A | Export emissions data as Excel (.xlsx) or JSON format with f |
| `POST` | `/api/emissions/import` | `emissions.import_emissions` | **IT Manager / Admin** | N/A | emissions.import_emissions |
| `GET` | `/api/emissions/pending` | `emissions.get_pending_emissions` | **Admin / Superuser** | N/A | Get all pending emissions across Scope 1, 2, 3 for the revie |
| `POST` | `/api/emissions/reject/<int:emission_id>` | `emissions.reject_emission` | **Authenticated User** | Review Required / Scoped | Reject a single record awaiting review; decided records cann |
| `POST` | `/api/emissions/reject/batch` | `emissions.reject_batch_emissions` | **Authenticated User** | N/A | Reject records awaiting review (soft: status Rejected, exclu |
| `GET` | `/api/emissions/template/csv` | `emissions.get_csv_template` | **Authenticated User** | N/A | Scope 1 CSV template built from services.scope1_template: co |
| `GET` | `/api/emissions/template/excel` | `emissions.get_excel_template` | **Authenticated User** | N/A | Scope 1 Excel template from the same column spec: Data Entry |
| `POST` | `/api/emissions/upload/check` | `emissions.upload_check` | **Authenticated User** | N/A | Check a file before importing it: the first `sample_rows` ro |
| `GET` | `/api/emissions/upload/errors/<job_id>` | `emissions.upload_errors` | **Authenticated User** | N/A | emissions.upload_errors |
| `GET` | `/api/emissions/upload/limits` | `emissions.upload_limits` | **Authenticated User** | N/A | Upload limits the wizard checks when a file is picked (no ro |
| `GET` | `/api/emissions/upload/mappings` | `emissions.list_import_mappings` | **Authenticated User** | N/A | The user's saved column mappings for an import type, most re |
| `POST` | `/api/emissions/upload/mappings` | `emissions.save_import_mapping` | **Authenticated User** | N/A | Save (or replace, by name) a column mapping: {scope, name, h |
| `DELETE` | `/api/emissions/upload/mappings/<int:mapping_id>` | `emissions.delete_import_mapping` | **Authenticated User** | Review Required / Scoped | emissions.delete_import_mapping |
| `POST` | `/api/emissions/upload/mappings/<int:mapping_id>/used` | `emissions.touch_import_mapping` | **Authenticated User** | Review Required / Scoped | Mark a saved mapping as used (it is then offered first). |
| `POST` | `/api/emissions/upload/start` | `emissions.upload_start` | **Authenticated User** | N/A | emissions.upload_start |
| `GET` | `/api/emissions/upload/status/<job_id>` | `emissions.upload_status` | **Authenticated User** | N/A | emissions.upload_status |
| `GET` | `/api/equipment-combustion-factors` | `factors.get_equipment_combustion_factors` | **Authenticated User** | N/A | Equipment-specific combustion CH4 / N2O factors (Tables 4-9, |
| `GET` | `/api/equity/allocation` | `equity.get_equity_allocation` | **IT Manager / Admin** | N/A | Allocates annual GHG (Scope 1 + Scope 2 tCO2e) and methane ( |
| `GET` | `/api/equity/partners` | `equity.get_partners` | **IT Manager / Admin** | N/A | equity.get_partners |
| `GET` | `/api/equity/shares` | `equity.get_equity_shares` | **IT Manager / Admin** | N/A | equity.get_equity_shares |
| `POST` | `/api/equity/shares` | `equity.save_equity_share` | **Admin / Superuser** | N/A | equity.save_equity_share |
| `DELETE` | `/api/equity/shares/<int:share_id>` | `equity.delete_equity_share` | **Admin / Superuser** | Review Required / Scoped | equity.delete_equity_share |
| `GET` | `/api/facilities` | `facilities.get_facilities` | **IT Manager / Admin** | N/A | facilities.get_facilities |
| `POST` | `/api/facilities` | `facilities.add_facility` | **Admin / Superuser** | N/A | facilities.add_facility |
| `GET` | `/api/facilities/` | `facilities.get_facilities` | **IT Manager / Admin** | N/A | facilities.get_facilities |
| `POST` | `/api/facilities/` | `facilities.add_facility` | **Admin / Superuser** | N/A | facilities.add_facility |
| `DELETE` | `/api/facilities/<facility_id>` | `facilities.delete_facility` | **Admin** | Protected (Scoped by Facility/Org/Tenant) | facilities.delete_facility |
| `PUT` | `/api/facilities/<int:facility_id>` | `facilities.update_facility` | **Admin / Superuser** | Protected (Scoped by Facility/Org/Tenant) | facilities.update_facility |
| `GET` | `/api/facilities/all-regions` | `facilities.get_all_regions` | **IT Manager / Admin** | N/A | Return all unique region identifiers — IT personnel only, no |
| `POST` | `/api/facilities/import` | `facilities.import_facilities` | **Admin / Superuser** | N/A | Bulk import facilities |
| `GET` | `/api/filters/available` | `managedata.get_available_filters` | **IT Manager / Admin** | N/A | managedata.get_available_filters |
| `GET` | `/api/goals` | `managedata.get_all_goals` | **IT Manager / Admin** | N/A | managedata.get_all_goals |
| `POST` | `/api/goals` | `managedata.add_or_update_goal` | **IT Manager / Admin** | N/A | managedata.add_or_update_goal |
| `GET` | `/api/goals/` | `managedata.get_all_goals` | **IT Manager / Admin** | N/A | managedata.get_all_goals |
| `POST` | `/api/goals/` | `managedata.add_or_update_goal` | **IT Manager / Admin** | N/A | managedata.add_or_update_goal |
| `DELETE` | `/api/goals/<int:year>` | `managedata.delete_goal` | **IT Manager / Admin** | Protected (Scoped by Facility/Org/Tenant) | managedata.delete_goal |
| `GET` | `/api/health` | `health_check` | **Authenticated User** | N/A | health_check |
| `GET` | `/api/health/live` | `health_liveness` | **Authenticated User** | N/A | Kubernetes / Docker shallow liveness probe. |
| `GET` | `/api/health/ready` | `health_readiness` | **Authenticated User** | N/A | Kubernetes / Docker deep readiness probe verifying DB pool a |
| `GET` | `/api/ldar/components` | `ldar.list_components` | **Authenticated User** | N/A | List component inventories filtered by facility and status. |
| `POST` | `/api/ldar/components` | `ldar.create_component` | **Auditor (Read-Only) / Admin** | N/A | Create a new component inventory item. |
| `GET` | `/api/ldar/components/<int:comp_id>` | `ldar.get_component` | **Authenticated User** | Review Required / Scoped | Retrieve a single component inventory record. |
| `PUT` | `/api/ldar/components/<int:comp_id>` | `ldar.update_component` | **Auditor (Read-Only) / Admin** | Review Required / Scoped | Update an existing component inventory record. |
| `DELETE` | `/api/ldar/components/<int:comp_id>` | `ldar.delete_component` | **Admin / Superuser** | Review Required / Scoped | Delete a component inventory record. |
| `POST` | `/api/ldar/components/bulk-delete` | `ldar.bulk_delete_components` | **Admin / Superuser** | N/A | Bulk delete component inventory records. |
| `POST` | `/api/ldar/components/bulk-update` | `ldar.bulk_update_components` | **Auditor (Read-Only) / Admin** | N/A | Bulk update status, operating hours, or other attributes of  |
| `GET` | `/api/ldar/surveys` | `ldar.list_surveys` | **Authenticated User** | N/A | List leak detection surveys. |
| `POST` | `/api/ldar/surveys` | `ldar.create_survey` | **Auditor (Read-Only) / Admin** | N/A | Create a new fugitive leak survey record. |
| `GET` | `/api/ldar/surveys/<int:survey_id>` | `ldar.get_survey` | **Authenticated User** | Review Required / Scoped | Retrieve a single fugitive survey record. |
| `PATCH, PUT` | `/api/ldar/surveys/<int:survey_id>` | `ldar.update_survey` | **Auditor (Read-Only) / Admin** | Review Required / Scoped | Update a fugitive survey record (e.g. record leak repairs, p |
| `DELETE` | `/api/ldar/surveys/<int:survey_id>` | `ldar.delete_survey` | **Admin / Superuser** | Review Required / Scoped | Delete a fugitive survey record. |
| `POST` | `/api/ldar/surveys/bulk-delete` | `ldar.bulk_delete_surveys` | **Admin / Superuser** | N/A | Bulk delete fugitive survey records. |
| `POST` | `/api/ldar/surveys/bulk-update` | `ldar.bulk_update_surveys` | **Auditor (Read-Only) / Admin** | N/A | Bulk update leak status, repair date, or notes on fugitive s |
| `GET, POST` | `/api/manage/sbti` | `managedata.manage_sbti` | **IT Manager / Admin** | N/A | managedata.manage_sbti |
| `GET` | `/api/map-config` | `map_config` | **Authenticated User** | N/A | Basemap tiles of the Emissions Map (pilot check 2026-10-09,  |
| `GET` | `/api/mitigation` | `managedata.get_mitigations` | **IT Manager / Admin** | N/A | managedata.get_mitigations |
| `POST` | `/api/mitigation` | `managedata.add_mitigation` | **Admin** | N/A | managedata.add_mitigation |
| `GET` | `/api/mitigation/` | `managedata.get_mitigations` | **IT Manager / Admin** | N/A | managedata.get_mitigations |
| `POST` | `/api/mitigation/` | `managedata.add_mitigation` | **Admin** | N/A | managedata.add_mitigation |
| `DELETE` | `/api/mitigation/<string:mitigation_id>` | `managedata.delete_mitigation` | **Admin** | N/A | managedata.delete_mitigation |
| `POST` | `/api/mitigation/bulk-import` | `managedata.bulk_import_mitigation` | **IT Manager / Admin** | N/A | managedata.bulk_import_mitigation |
| `GET` | `/api/notifications/` | `notifications.get_notifications` | **IT Manager / Admin** | N/A | notifications.get_notifications |
| `DELETE` | `/api/notifications/<int:id>` | `notifications.delete_notification` | **Admin** | Protected (Scoped by Facility/Org/Tenant) | Permanently delete a user notification or soft-dismiss a sys |
| `PATCH, PUT` | `/api/notifications/<int:id>/read` | `notifications.mark_read` | **Authenticated User** | Protected (Scoped by Facility/Org/Tenant) | notifications.mark_read |
| `DELETE` | `/api/notifications/all` | `notifications.delete_all_notifications` | **Authenticated User** | N/A | Permanently delete all notifications for the current user an |
| `POST` | `/api/notifications/dismiss-all` | `notifications.dismiss_all` | **Authenticated User** | N/A | notifications.dismiss_all |
| `GET` | `/api/period-locks` | `period_locks.get_period_locks` | **Authenticated User** | N/A | List all period locks. |
| `GET` | `/api/period-locks/` | `period_locks.get_period_locks` | **Authenticated User** | N/A | List all period locks. |
| `POST` | `/api/period-locks/lock` | `period_locks.lock_period` | **Admin / Superuser** | N/A | Part 2.3: Lock a reporting period after formal sign-off (Adm |
| `GET` | `/api/period-locks/status/<int:year>` | `period_locks.get_period_lock_status` | **Authenticated User** | Review Required / Scoped | Check if a specific reporting year is locked. |
| `POST` | `/api/period-locks/unlock` | `period_locks.unlock_period` | **Admin** | N/A | Part 2.3: Unlock a locked reporting period with mandatory ju |
| `GET` | `/api/production/years` | `managedata.get_production_years` | **IT Manager / Admin** | N/A | managedata.get_production_years |
| `POST` | `/api/qaqc/bulk-resolve` | `qaqc_bp.bulk_resolve` | **Admin / Superuser** | N/A | Bulk approve or reject a list of flagged records, under the  |
| `GET` | `/api/qaqc/dashboard` | `qaqc_bp.get_qaqc_dashboard` | **Admin / Superuser** | N/A | Returns aggregated uncertainty (IPCC SRSS) and flagged anoma |
| `GET` | `/api/qaqc/export` | `qaqc_bp.export_qaqc_report` | **IT Manager / Admin** | N/A | Exports QA/QC anomaly data as a CSV file with scope and year |
| `POST` | `/api/qaqc/resolve/<int:record_id>` | `qaqc_bp.resolve_flagged_record` | **Admin / Superuser** | Protected (Scoped by Facility/Org/Tenant) | Approve ("Verified") or reject ("Rejected") one flagged reco |
| `POST` | `/api/recalculate/<int:request_id>/approve` | `recalculate.approve_and_execute_recalculation` | **Admin** | Protected (Scoped by Facility/Org/Tenant) | Part 2.2: Admin maker-checker approval and execution of reca |
| `POST` | `/api/recalculate/<int:request_id>/reject` | `recalculate.reject_recalculation` | **Admin** | Protected (Scoped by Facility/Org/Tenant) | Part 2.2: Reject a recalculation request. |
| `GET` | `/api/recalculate/history` | `recalculate.list_recalculation_history` | **Authenticated User** | N/A | Part 2.2: List granular record-level recalculation history. |
| `POST` | `/api/recalculate/preview` | `recalculate.recalculate_preview` | **Authenticated User** | N/A | Part 2.2: Impact preview for proposed recalculation without  |
| `POST` | `/api/recalculate/request` | `recalculate.submit_recalculation_request` | **Authenticated User** | N/A | Part 2.2: Submit a recalculation request with GHG Protocol b |
| `GET` | `/api/recalculate/requests` | `recalculate.list_recalculation_requests` | **Authenticated User** | N/A | Part 2.2: List recalculation requests. |
| `GET` | `/api/reporting-metadata` | `managedata.get_reporting_metadata` | **IT Manager / Admin** | N/A | managedata.get_reporting_metadata |
| `POST` | `/api/reporting-metadata` | `managedata.save_reporting_metadata` | **IT Manager / Admin** | N/A | managedata.save_reporting_metadata |
| `GET` | `/api/reports/cbam-export` | `reports.export_cbam_report` | **IT Manager / Admin** | N/A | Generates the official EU CBAM Communication Template under  |
| `GET` | `/api/reports/cbam-export/` | `reports.export_cbam_report` | **IT Manager / Admin** | N/A | Generates the official EU CBAM Communication Template under  |
| `GET` | `/api/reports/export` | `reports.export_emissions` | **IT Manager / Admin** | N/A | Export emissions data as PDF - GET version for frontend inte |
| `POST` | `/api/reports/fingerprint` | `reports.record_browser_report` | **IT Manager / Admin** | N/A | reports.record_browser_report |
| `POST` | `/api/reports/generate` | `reports.generate_report` | **IT Manager / Admin** | N/A | Generate PDF report based on filters |
| `GET` | `/api/reports/master-annual-report` | `reports.get_master_annual_report` | **Authenticated User** | N/A | reports.get_master_annual_report |
| `POST` | `/api/reports/master-report` | `reports.generate_master_report_endpoint` | **Authenticated User** | N/A | Generates and streams the publication-grade Master Report PD |
| `POST` | `/api/reports/master-report/benchmark-excel` | `reports.export_benchmark_excel` | **Authenticated User** | N/A | Generates an executive cross-basin benchmark Excel workbook. |
| `GET` | `/api/reports/master-report/regions` | `reports.get_master_report_regions` | **Authenticated User** | N/A | Returns available regions strictly present in the software d |
| `GET` | `/api/reports/national-inventory-export` | `reports.export_national_inventory_report` | **IT Manager / Admin** | N/A | Generates the official Algerian Corporate HSE & National Inv |
| `GET` | `/api/reports/national-inventory-export/` | `reports.export_national_inventory_report` | **IT Manager / Admin** | N/A | Generates the official Algerian Corporate HSE & National Inv |
| `GET` | `/api/reports/ogmp-export` | `reports.export_ogmp_excel` | **IT Manager / Admin** | N/A | Generates the official UNEP / IMEO OGMP 2.0 Standard Annual  |
| `GET, POST` | `/api/sbti` | `managedata.manage_sbti` | **IT Manager / Admin** | N/A | managedata.manage_sbti |
| `GET` | `/api/scope2` | `scope2.get_scope2_emissions` | **IT Manager / Admin** | N/A | Get all Scope 2 emissions, scoped to the requesting user's a |
| `POST` | `/api/scope2` | `scope2.create_scope2_emission` | **IT Manager / Admin** | N/A | scope2.create_scope2_emission |
| `PUT` | `/api/scope2/<int:emission_id>` | `scope2.update_scope2_emission` | **IT Manager / Admin** | Protected (Scoped by Facility/Org/Tenant) | Update a Scope 2 emission record |
| `DELETE` | `/api/scope2/<int:emission_id>` | `scope2.delete_scope2_emission` | **IT Manager / Admin** | Protected (Admin Only) | Delete a Scope 2 emission record |
| `POST` | `/api/scope2/bulk-import` | `scope2.bulk_import_scope2` | **IT Manager / Admin** | N/A | Import Scope 2 emissions from CSV data |
| `GET` | `/api/scope2/emission-factors` | `scope2.get_emission_factors` | **Authenticated User** | N/A | Get emission factors by grid region |
| `GET` | `/api/scope3` | `scope3.get_scope3_emissions` | **IT Manager / Admin** | N/A | Get all Scope 3 emissions scoped to user's allowed facilitie |
| `POST` | `/api/scope3` | `scope3.create_scope3_emission` | **IT Manager / Admin** | N/A | Create a new Scope 3 emission record with Maker-Checker stat |
| `PUT` | `/api/scope3/<int:emission_id>` | `scope3.update_scope3_emission` | **Admin** | Protected (Scoped by Facility/Org/Tenant) | Update a Scope 3 emission record |
| `DELETE` | `/api/scope3/<int:emission_id>` | `scope3.delete_scope3_emission` | **IT Manager / Admin** | Protected (Admin Only) | Delete a Scope 3 emission record |
| `POST` | `/api/scope3/bulk-import` | `scope3.bulk_import_scope3` | **IT Manager / Admin** | N/A | Import Scope 3 emissions from CSV data |
| `POST` | `/api/scope3/eeio-calculate` | `scope3.calculate_eeio` | **IT Manager / Admin** | N/A | Calculate Scope 3 Category 1 emissions based on spend and NA |
| `GET` | `/api/scope3/eeio-factors` | `scope3.search_eeio` | **IT Manager / Admin** | N/A | Six-digit NAICS codes of the EPA supply chain factor dataset |
| `GET` | `/api/sources` | `managedata.get_sources` | **IT Manager / Admin** | N/A | managedata.get_sources |
| `POST` | `/api/sources` | `managedata.add_source` | **IT Manager / Admin** | N/A | managedata.add_source |
| `GET` | `/api/sources/` | `managedata.get_sources` | **IT Manager / Admin** | N/A | managedata.get_sources |
| `POST` | `/api/sources/` | `managedata.add_source` | **IT Manager / Admin** | N/A | managedata.add_source |
| `DELETE` | `/api/sources/<int:source_id>` | `managedata.delete_source` | **IT Manager / Admin** | Protected (Scoped by Facility/Org/Tenant) | managedata.delete_source |
| `POST` | `/api/sources/bulk-import` | `managedata.bulk_import_sources` | **IT Manager / Admin** | N/A | managedata.bulk_import_sources |
| `GET` | `/api/traceability/trace` | `traceability.trace_metric` | **Authenticated User** | N/A | Part 2.4: Trace any metric to its underlying source records, |
| `GET` | `/static/<path:filename>` | `static` | **Public** | N/A | static |
