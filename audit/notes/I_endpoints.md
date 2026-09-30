# Agent I — Endpoint inventory (generated from app.url_map + source decorators)

Columns: auth decorator = decorator on the view; facility scope = scoping helper referenced in the body; inline role = body contains a role comparison.
RBAC GET sweep (anon / it_admin / user West / superuser West): audit/work/I/get_sweep.txt. Anonymous sweep of every non-GET endpoint: all 401 except login, forgot-password, logout (expected).
CSRF: verified with WTF_CSRF_ENABLED=True — POST/PUT/DELETE without X-CSRFToken → 400, with token → 201; only /auth/login and /auth/forgot-password (and swagger) exempt.

## Findings mapped to endpoints
| Endpoint | Bug |
|---|---|
| POST /api/emissions/upload/start (scope=facilities/custom_factors) | BUG-001 (Critical) |
| GET /api/reports/master-annual-report | BUG-020 |
| GET /api/audit/, /export, /filters, /stats | BUG-038 |
| GET /api/equity/allocation, POST /api/equity/shares | BUG-046 |
| POST /api/cap/emissions, GET /api/cap/compliance | BUG-053 |
| POST /api/scope2, /api/scope2/bulk-import | BUG-060 |
| PUT/DELETE /api/emissions/<id>, POST /approve/<id> | BUG-067 |
| POST /api/emissions/reject/<id> | BUG-070 |
| POST /api/emissions/approve|reject/<id> (concurrency) | BUG-074 |
| GET /api/emissions/upload/status|errors/<job_id> | BUG-076 |
| POST scope2/scope3/production/custom-factors/mitigation (non-finite) | BUG-083 |
| ~40 handlers returning str(e) | BUG-087 |

## Timing (admin, snapshot data, in-process)
batch-all 0.43 s cold / 0.03 s cached; qaqc/dashboard 0.8 s; equity/allocation 0.77 s; cap/compliance 0.53 s; others < 0.3 s. Pagination on /api/emissions/ clamps bad page/per_page values (verified).

## Inventory
| path | methods | auth decorator | facility scope | inline role check | src |
|---|---|---|---|---|---|
| / | GET | NONE | - |  | \app.py:432 |
| /api/audit/ | GET | audit_access_required | - |  | \routes\audit.py:158 |
| /api/audit/export | GET | audit_access_required | - |  | \routes\audit.py:289 |
| /api/audit/export/ | GET | audit_access_required | - |  | \routes\audit.py:289 |
| /api/audit/filters | GET | audit_access_required | - |  | \routes\audit.py:245 |
| /api/audit/filters/ | GET | audit_access_required | - |  | \routes\audit.py:245 |
| /api/audit/stats | GET | NONE | - |  | \routes\managedata.py:1077 |
| /api/audit/stats | GET | audit_access_required | - |  | \routes\audit.py:202 |
| /api/audit/stats/ | GET | NONE | - |  | \routes\managedata.py:1077 |
| /api/audit/stats/ | GET | audit_access_required | - |  | \routes\audit.py:202 |
| /api/audit/verify-chain | GET | audit_access_required | - |  | \routes\audit.py:384 |
| /api/auth/change-password | POST | login_required | - |  | \routes\auth.py:586 |
| /api/auth/forgot-password | POST | NONE | - |  | \routes\auth.py:410 |
| /api/auth/login | POST | NONE | - |  | \routes\auth.py:336 |
| /api/auth/logout | POST | NONE | - |  | \routes\auth.py:483 |
| /api/auth/me | GET | NONE | - |  | \routes\auth.py:515 |
| /api/auth/profile | PUT | login_required | - |  | \routes\auth.py:554 |
| /api/auth/register | POST | it_admin_required | - | role | \routes\auth.py:252 |
| /api/auth/settings | GET | login_required | - |  | \routes\auth.py:772 |
| /api/auth/settings | POST,PUT | login_required | - | role | \routes\auth.py:802 |
| /api/auth/upload-avatar | POST | login_required | - |  | \routes\auth.py:640 |
| /api/auth/users | GET | it_access_required | - |  | \routes\auth.py:948 |
| /api/auth/users | POST | it_admin_required | - |  | \routes\auth.py:942 |
| /api/auth/users/<int:id> | DELETE | it_admin_required | - |  | \routes\auth.py:1058 |
| /api/auth/users/<int:id> | PUT | it_admin_required | - | role | \routes\auth.py:976 |
| /api/auth/users/<int:id>/reset-password | POST | it_access_required | - |  | \routes\auth.py:1120 |
| /api/base-years | GET | login_required | - | role | \routes\managedata.py:834 |
| /api/base-years | POST | login_required | - | role | \routes\managedata.py:893 |
| /api/base-years/ | GET | login_required | - | role | \routes\managedata.py:834 |
| /api/base-years/ | POST | login_required | - | role | \routes\managedata.py:893 |
| /api/base-years/<int:rec_id> | DELETE | login_required | - | role | \routes\managedata.py:953 |
| /api/cap/compliance | GET | login_required | get_allowed_facility_ids,allowed_facility |  | \routes\cap_routes.py:186 |
| /api/cap/emissions | GET | login_required | get_allowed_facility_ids,allowed_facility |  | \routes\cap_routes.py:55 |
| /api/cap/emissions | POST | login_required | require_facility_access |  | \routes\cap_routes.py:115 |
| /api/cap/limits | GET | login_required | - |  | \routes\cap_routes.py:36 |
| /api/csrf-token | GET | NONE | - |  | \app.py:410 |
| /api/custom-factors | GET | login_required | - | role | \routes\custom_factors.py:11 |
| /api/custom-factors | POST | superuser_required | - |  | \routes\custom_factors.py:84 |
| /api/custom-factors/ | GET | login_required | - | role | \routes\custom_factors.py:11 |
| /api/custom-factors/ | POST | superuser_required | - |  | \routes\custom_factors.py:84 |
| /api/custom-factors/<int:factor_id> | DELETE | superuser_required | - |  | \routes\custom_factors.py:250 |
| /api/custom-factors/<int:factor_id> | PUT | superuser_required | - |  | \routes\custom_factors.py:164 |
| /api/custom-factors/import | POST | superuser_required | - |  | \routes\custom_factors.py:299 |
| /api/dashboard/base-year | GET | login_required | - |  | \routes\dashboard.py:972 |
| /api/dashboard/base-year-recalculation | POST | login_required | - | role | \routes\dashboard.py:1032 |
| /api/dashboard/batch-all | GET | login_required | get_allowed_facility_ids,_scope,allowed_facility |  | \routes\dashboard.py:122 |
| /api/dashboard/categorical-breakdown | GET | login_required | get_allowed_facility_ids,allowed_facility |  | \routes\dashboard.py:1003 |
| /api/dashboard/exclusions | GET | login_required | - |  | \routes\dashboard.py:2637 |
| /api/dashboard/flaring-summary | GET | login_required | get_allowed_facility_ids,allowed_facility |  | \routes\dashboard.py:2868 |
| /api/dashboard/goals/<int:year> | GET | login_required | - |  | \routes\dashboard.py:951 |
| /api/dashboard/granular-intensities | GET | login_required | get_allowed_facility_ids,allowed_facility |  | \routes\dashboard.py:3075 |
| /api/dashboard/intensity-stats | GET | login_required | get_allowed_facility_ids,allowed_facility |  | \routes\dashboard.py:1269 |
| /api/dashboard/intensity-trend | GET | login_required | get_allowed_facility_ids,allowed_facility |  | \routes\dashboard.py:352 |
| /api/dashboard/mitigation | GET | login_required | get_allowed_facility_ids,allowed_facility |  | \routes\dashboard.py:899 |
| /api/dashboard/ogmp-metrics | GET | login_required | get_allowed_facility_ids,allowed_facility |  | \routes\dashboard.py:1103 |
| /api/dashboard/sbti-trajectory | GET | login_required | get_allowed_facility_ids,allowed_facility |  | \routes\dashboard.py:2669 |
| /api/dashboard/scope3/summary | GET | login_required | get_allowed_facility_ids,_scope,allowed_facility |  | \routes\dashboard.py:924 |
| /api/dashboard/summary | GET | login_required | get_allowed_facility_ids,allowed_facility |  | \routes\dashboard.py:852 |
| /api/dashboard/uncertainty | GET | login_required | get_allowed_facility_ids,allowed_facility |  | \routes\dashboard.py:2261 |
| /api/dashboard/years | GET | login_required | - |  | \routes\dashboard.py:884 |
| /api/data/cbam-exports | GET | login_required | get_allowed_facility_ids,allowed_facility |  | \routes\data.py:682 |
| /api/data/cbam-exports | POST | login_required | require_facility_access |  | \routes\data.py:739 |
| /api/data/cbam-exports/ | GET | login_required | get_allowed_facility_ids,allowed_facility |  | \routes\data.py:682 |
| /api/data/cbam-exports/ | POST | login_required | require_facility_access |  | \routes\data.py:739 |
| /api/data/cbam-exports/<int:record_id> | DELETE | login_required | require_facility_access |  | \routes\data.py:848 |
| /api/data/methane-sources | GET | login_required | - |  | \routes\data.py:356 |
| /api/data/ogmp-surveys | GET | login_required | get_allowed_facility_ids,allowed_facility |  | \routes\data.py:372 |
| /api/data/ogmp-surveys | POST | login_required | require_facility_access |  | \routes\data.py:442 |
| /api/data/ogmp-surveys/ | GET | login_required | get_allowed_facility_ids,allowed_facility |  | \routes\data.py:372 |
| /api/data/ogmp-surveys/ | POST | login_required | require_facility_access |  | \routes\data.py:442 |
| /api/data/ogmp-surveys/<int:record_id> | DELETE | login_required | require_facility_access | role | \routes\data.py:567 |
| /api/data/ogmp/level-logs | GET | login_required | get_allowed_facility_ids,allowed_facility |  | \routes\data.py:646 |
| /api/data/ogmp/level-upgrade | POST | login_required | require_facility_access |  | \routes\data.py:604 |
| /api/data/production | GET | login_required | get_allowed_facility_ids,require_facility_access,allowed_facility |  | \routes\data.py:23 |
| /api/data/production | POST | login_required | require_facility_access | role | \routes\data.py:71 |
| /api/data/production/ | GET | login_required | get_allowed_facility_ids,require_facility_access,allowed_facility |  | \routes\data.py:23 |
| /api/data/production/ | POST | login_required | require_facility_access | role | \routes\data.py:71 |
| /api/data/production/<int:record_id> | DELETE | login_required | require_facility_access | role | \routes\data.py:217 |
| /api/data/production/bulk-import | POST | login_required | get_allowed_facility_ids,allowed_facility | role | \routes\data.py:250 |
| /api/emission-factors | GET | login_required  # NEW-03 FIX | - |  | \routes\emission_factors_routes.py:33 |
| /api/emission-factors/by-process/<process_category> | GET | login_required  # NEW-03 FIX | - |  | \routes\emission_factors_routes.py:149 |
| /api/emission-factors/by-segment-and-process | GET | login_required  # NEW-03 FIX | - |  | \routes\emission_factors_routes.py:182 |
| /api/emission-factors/by-segment/<segment> | GET | login_required  # NEW-03 FIX | - |  | \routes\emission_factors_routes.py:59 |
| /api/emission-factors/process-types | GET | login_required  # NEW-03 FIX | - |  | \routes\emission_factors_routes.py:89 |
| /api/emission-factors/process-types/<segment> | GET | login_required  # NEW-03 FIX | - |  | \routes\emission_factors_routes.py:101 |
| /api/emission-factors/search | GET | login_required  # NEW-03 FIX | - |  | \routes\emission_factors_routes.py:229 |
| /api/emission-factors/segments | GET | login_required  # NEW-03 FIX | - |  | \routes\emission_factors_routes.py:47 |
| /api/emission-factors/stats | GET | login_required  # NEW-03 FIX | - |  | \routes\emission_factors_routes.py:332 |
| /api/emission-factors/uncertainties | GET | login_required  # NEW-03 FIX | - |  | \routes\emission_factors_routes.py:290 |
| /api/emission-factors/version | GET | login_required  # NEW-03 FIX | - |  | \routes\emission_factors_routes.py:375 |
| /api/emissions/ | GET | login_required  # SEC-01 FIX: was missing, route was unauthenticated | get_allowed_facility_ids,allowed_facility | role | \routes\emissions.py:77 |
| /api/emissions/ | POST | login_required | get_allowed_facility_ids,allowed_ids,allowed_facility | role | \routes\emissions.py:2977 |
| /api/emissions/<id> | DELETE | login_required  # SEC-01 FIX: was missing | get_allowed_facility_ids,allowed_facility | role | \routes\emissions.py:3341 |
| /api/emissions/<id> | PUT | login_required  # EXTRA-06 FIX: decorator was present but get_current_user() could return None causing 500 | get_allowed_facility_ids,allowed_facility | role | \routes\emissions.py:3398 |
| /api/emissions/approve/<int:emission_id> | POST | login_required | get_allowed_facility_ids,allowed_facility | role | \routes\emissions.py:4456 |
| /api/emissions/approve/batch | POST | login_required | get_allowed_facility_ids,_scope,allowed_facility | role | \routes\emissions.py:4562 |
| /api/emissions/bulk-delete | POST | login_required  # SEC-01 FIX: was missing | get_allowed_facility_ids,allowed_facility |  | \routes\emissions.py:3659 |
| /api/emissions/bulk-upload | POST | login_required | get_allowed_facility_ids,allowed_facility | role | \routes\emissions.py:472 |
| /api/emissions/erp/sync | POST | login_required | - | role | \routes\emissions.py:4736 |
| /api/emissions/export | GET | login_required  # SEC-01 FIX: was missing | get_allowed_facility_ids,allowed_ids,allowed_facility | role | \routes\emissions.py:4018 |
| /api/emissions/import | POST | login_required  # SEC-01 FIX: was missing | get_allowed_facility_ids,allowed_ids,allowed_facility | role | \routes\emissions.py:3701 |
| /api/emissions/pending | GET | login_required | get_allowed_facility_ids,_scope,allowed_facility | role | \routes\emissions.py:4765 |
| /api/emissions/reject/<int:emission_id> | POST | login_required | get_allowed_facility_ids,allowed_facility | role | \routes\emissions.py:4511 |
| /api/emissions/reject/batch | POST | login_required | get_allowed_facility_ids,_scope,allowed_facility | role | \routes\emissions.py:4648 |
| /api/emissions/template/csv | GET | NONE | - |  | \routes\emissions.py:989 |
| /api/emissions/template/excel | GET | NONE | - |  | \routes\emissions.py:2046 |
| /api/emissions/upload/errors/<job_id> | GET | login_required | - |  | \routes\emissions.py:2962 |
| /api/emissions/upload/start | POST | login_required | - |  | \routes\emissions.py:2881 |
| /api/emissions/upload/status/<job_id> | GET | login_required | - |  | \routes\emissions.py:2953 |
| /api/equity/allocation | GET | login_required | get_allowed_facility_ids,allowed_facility |  | \routes\equity_routes.py:129 |
| /api/equity/partners | GET | login_required | - |  | \routes\equity_routes.py:34 |
| /api/equity/shares | GET | login_required | get_allowed_facility_ids,allowed_facility |  | \routes\equity_routes.py:51 |
| /api/equity/shares | POST | login_required | require_facility_access |  | \routes\equity_routes.py:89 |
| /api/facilities | GET | login_required | get_allowed_facility_ids,allowed_facility | role | \routes\facilities.py:12 |
| /api/facilities | POST | login_required | - | role | \routes\facilities.py:122 |
| /api/facilities/ | GET | login_required | get_allowed_facility_ids,allowed_facility | role | \routes\facilities.py:12 |
| /api/facilities/ | POST | login_required | - | role | \routes\facilities.py:122 |
| /api/facilities/<int:facility_id> | DELETE | login_required | get_allowed_facility_ids,allowed_facility | role | \routes\facilities.py:351 |
| /api/facilities/<int:facility_id> | PUT | login_required | get_allowed_facility_ids,allowed_facility | role | \routes\facilities.py:220 |
| /api/facilities/all-regions | GET | login_required | get_allowed_facility_ids,allowed_facility | role | \routes\facilities.py:73 |
| /api/facilities/import | POST | login_required | - | role | \routes\facilities.py:405 |
| /api/filters/available | GET | login_required | get_allowed_facility_ids,allowed_facility | role | \routes\managedata.py:549 |
| /api/goals | GET | login_required | - | role | \routes\managedata.py:744 |
| /api/goals | POST | login_required | - | role | \routes\managedata.py:769 |
| /api/goals/ | GET | login_required | - | role | \routes\managedata.py:744 |
| /api/goals/ | POST | login_required | - | role | \routes\managedata.py:769 |
| /api/goals/<int:year> | DELETE | login_required | - | role | \routes\managedata.py:811 |
| /api/health | GET | NONE | - |  | \app.py:441 |
| /api/health/live | GET | NONE | - |  | \app.py:447 |
| /api/health/ready | GET | NONE | - |  | \app.py:453 |
| /api/manage/sbti | GET,POST | login_required | - | role | \routes\managedata.py:986 |
| /api/mitigation | GET | login_required | get_allowed_facility_ids,allowed_facility | role | \routes\managedata.py:240 |
| /api/mitigation | POST | login_required | get_allowed_facility_ids,allowed_facility | role | \routes\managedata.py:312 |
| /api/mitigation/ | GET | login_required | get_allowed_facility_ids,allowed_facility | role | \routes\managedata.py:240 |
| /api/mitigation/ | POST | login_required | get_allowed_facility_ids,allowed_facility | role | \routes\managedata.py:312 |
| /api/mitigation/<string:mitigation_id> | DELETE | login_required | get_allowed_facility_ids,allowed_facility | role | \routes\managedata.py:384 |
| /api/mitigation/bulk-import | POST | login_required | get_allowed_facility_ids,allowed_facility | role | \routes\managedata.py:623 |
| /api/notifications/ | GET | login_required | - |  | \routes\notifications.py:32 |
| /api/notifications/<int:id> | DELETE | login_required | - | role | \routes\notifications.py:235 |
| /api/notifications/<int:id>/read | PUT | login_required | - | role | \routes\notifications.py:165 |
| /api/notifications/all | DELETE | login_required | - |  | \routes\notifications.py:259 |
| /api/notifications/dismiss-all | POST | login_required | - | role | \routes\notifications.py:198 |
| /api/notifications/stream | GET | login_required | - |  | \routes\notifications.py:64 |
| /api/production/years | GET | login_required | - | role | \routes\managedata.py:533 |
| /api/qaqc/bulk-resolve | POST | login_required | get_allowed_facility_ids,allowed_facility |  | \routes\qaqc.py:815 |
| /api/qaqc/dashboard | GET | login_required | get_allowed_facility_ids,_scope,allowed_facility |  | \routes\qaqc.py:23 |
| /api/qaqc/export | GET | login_required | get_allowed_facility_ids,allowed_facility |  | \routes\qaqc.py:619 |
| /api/qaqc/resolve/<int:record_id> | POST | login_required | get_allowed_facility_ids,allowed_facility |  | \routes\qaqc.py:741 |
| /api/reporting-metadata | GET | login_required | - | role | \routes\managedata.py:434 |
| /api/reporting-metadata | POST | login_required | - | role | \routes\managedata.py:472 |
| /api/reports/export | GET | login_required | get_allowed_facility_ids,allowed_facility | role | \routes\reports.py:485 |
| /api/reports/generate | POST | login_required | get_allowed_facility_ids,allowed_facility | role | \routes\reports.py:253 |
| /api/reports/master-annual-report | GET | login_required | - |  | \routes\reports.py:454 |
| /api/reports/ogmp-export | GET | login_required | get_allowed_facility_ids,allowed_facility | role | \routes\reports.py:727 |
| /api/satellite/sentinel5p/export-to-ogmp | POST | login_required | get_allowed_facility_ids,allowed_facility | role | \routes\satellite.py:196 |
| /api/satellite/sentinel5p/facility-timeseries | GET,POST | login_required | get_allowed_facility_ids,allowed_facility | role | \routes\satellite.py:123 |
| /api/satellite/sentinel5p/layer-config | GET | login_required | - | role | \routes\satellite.py:102 |
| /api/satellite/sentinel5p/poll-new-passes | POST | login_required | get_allowed_facility_ids,allowed_facility | role | \routes\satellite.py:358 |
| /api/satellite/sentinel5p/query | GET,POST | login_required | get_allowed_facility_ids,allowed_facility | role | \routes\satellite.py:123 |
| /api/satellite/sentinel5p/test-connection | POST | login_required | - |  | \routes\satellite.py:65 |
| /api/sbti | GET,POST | login_required | - | role | \routes\managedata.py:986 |
| /api/scope2 | GET | login_required | get_allowed_facility_ids,_scope,allowed_facility | role | \routes\scope2.py:97 |
| /api/scope2 | POST | login_required | get_allowed_facility_ids,_scope,allowed_facility | role | \routes\scope2.py:159 |
| /api/scope2/<int:emission_id> | DELETE | login_required | require_facility_access,_scope | role | \routes\scope2.py:484 |
| /api/scope2/<int:emission_id> | PUT | login_required | require_facility_access,_scope | role | \routes\scope2.py:355 |
| /api/scope2/bulk-import | POST | login_required | get_allowed_facility_ids,_scope,allowed_facility | role | \routes\scope2.py:539 |
| /api/scope2/emission-factors | GET | login_required | - |  | \routes\scope2.py:689 |
| /api/scope3 | GET | login_required | get_allowed_facility_ids,_scope,allowed_facility | role | \routes\scope3.py:14 |
| /api/scope3 | POST | login_required | get_allowed_facility_ids,_scope,allowed_facility | role | \routes\scope3.py:70 |
| /api/scope3/<int:emission_id> | DELETE | login_required | require_facility_access,_scope | role | \routes\scope3.py:308 |
| /api/scope3/<int:emission_id> | PUT | login_required | require_facility_access,_scope | role | \routes\scope3.py:216 |
| /api/scope3/bulk-import | POST | login_required | get_allowed_facility_ids,_scope,allowed_facility | role | \routes\scope3.py:362 |
| /api/scope3/eeio-calculate | POST | login_required | - |  | \routes\scope3.py:508 |
| /api/sources | GET | login_required | get_allowed_facility_ids,allowed_facility | role | \routes\managedata.py:26 |
| /api/sources | POST | login_required | get_allowed_facility_ids,allowed_facility | role | \routes\managedata.py:63 |
| /api/sources/ | GET | login_required | get_allowed_facility_ids,allowed_facility | role | \routes\managedata.py:26 |
| /api/sources/ | POST | login_required | get_allowed_facility_ids,allowed_facility | role | \routes\managedata.py:63 |
| /api/sources/<int:source_id> | DELETE | login_required | get_allowed_facility_ids,allowed_facility | role | \routes\managedata.py:119 |
| /api/sources/bulk-import | POST | login_required | get_allowed_facility_ids,allowed_facility | role | \routes\managedata.py:155 |
