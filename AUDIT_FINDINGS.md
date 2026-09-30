# AUDIT FINDINGS

Live defect log. Each entry is appended (via `audit/tools/report_bug.py`, atomic ID allocation) the moment it is confirmed.
Classes: **Confirmed** bugs get `# BUG-NNN` entries. Suspected issues and design questions are listed in `audit/SUSPECTED_AND_QUESTIONS.md`.
Reproduction scripts: `audit/repro/BUG-NNN.*`


---

# BUG-001 — Bulk upload job API lets any logged-in role (user, it_admin) create/overwrite facilities and custom factors, bypassing RBAC and region scoping

**Status:** Confirmed
**Severity:** Critical
**Category:** Security
**Discovered by:** Agent I (Backend/API/Security)

## Location
- `new/server/routes/emissions.py:2881` `upload_start()` — only `@login_required`, no role check, `scope` taken verbatim from form data.
- `new/server/background_processor.py:494-500` dispatches `scope=custom_factors` → `_process_row_custom_factors` (l.1520) and `scope=facilities` → `_process_row_facilities` (l.1550). Neither checks the uploader's role; `_process_row_facilities` looks up `Facility.query.filter_by(name=name)` across ALL facilities (not the uploader's allowed set) and overwrites fields when `overwrite_duplicates=true`.

## Reproduction
1. Log in as `audit_user@audit.local` (role `user`, location West) or `audit_itadmin@audit.local` (role `it_admin`).
2. `POST /api/emissions/upload/start` multipart: `file=f.csv`, `scope=facilities`, `overwrite_duplicates=true`, CSV:
   `name,location,region,description` / `Cimenterie Industrielle de Chlef (GICA),HACKED_user,Center,pwned` / `NEWFAC_user,X,East,created by user`
3. Poll `/api/emissions/upload/status/<job_id>` until `completed`.
4. Repeat with `scope=custom_factors`, CSV `name,co2_factor,ch4_factor,unit` / `EVIL_user,999,1,scf`.
Script: `audit/repro/<BUG-ID>.py`.

## Input
Role `user` (West) and role `it_admin`; target facility id 3 (region Center — outside West).

## Expected
403 (the direct routes are protected: `POST /api/facilities/import` → 403 and `POST /api/custom-factors` → 403 for both roles; it_admin must have zero business-data write access; a West user must not touch a Center facility).

## Actual
Both jobs complete (`status=completed, processed=2`). Facility 3 (Center) `location` overwritten to `HACKED_user` / `HACKED_it_admin`; new facilities `NEWFAC_user` (created_by 18) and `NEWFAC_it_admin` (created_by 19) created in region East; custom factors `EVIL_user` / `EVIL_it_admin` with `co2_factor=999` created. Same calls to the direct endpoints return 403.

## Evidence
```
user 200 {'job_id': '064f85cb-...'}  -> {'status': 'completed', 'processed': 2}
[{'id': 3, 'name': 'Cimenterie Industrielle de Chlef (GICA)', 'location': 'HACKED_user', 'region': 'Center'}, {'id': 171, 'name': 'NEWFAC_user', 'region': 'East', 'created_by': 18}]
[{'id': 102, 'name': 'EVIL_user', 'co2_factor': 999.0, 'created_by': 18}]
user direct POST custom-factors: 403 direct facilities import: 403
it_admin ... identical (facility 3 location HACKED_it_admin, NEWFAC_it_admin, EVIL_it_admin)
```

## Root Cause
Authorization is enforced per-route on the dedicated endpoints but the generic job endpoint accepts an arbitrary `scope` and the background processor trusts it. No role / facility-scope checks exist in the facilities/custom-factor row handlers. (Also applies to `scope=sources|production|mitigation` for it_admin — those use the facility map, which is empty for IT roles, so they fail; facilities/custom_factors do not use it.)

## Impact
Privilege escalation: any authenticated account, including IT administrators who are supposed to have zero business-data access, can create facilities, rename/relocate/re-region any facility in any region (which also changes which users can see it via region scoping), and inject custom emission factors that feed Scope 1 calculations (factor lookup by name in `cf_name_map`). Custom factors created this way have no maker-checker step.

## Affected Components
`/api/emissions/upload/start`, `background_processor._process_row_facilities`, `_process_row_custom_factors`; downstream: facility scoping, custom-factor-based Scope 1 calculations, dashboards.

## Recommended Fix
In `upload_start`, whitelist `scope` per role: reject IT roles entirely; allow `facilities` / `custom_factors` only for admin/superuser (and apply the same region restriction as `/api/facilities/import`); in `_process_row_facilities` restrict the existing-name lookup to the uploader's allowed facility ids.


---

# BUG-002 — Reports "2025 Master Report (PDF)" button sends facility_id=[object Object]; facility selection ignored

**Status:** Confirmed
**Severity:** Medium
**Category:** UI
**Discovered by:** Agent K (Frontend/UI)

## Location
`new/client/src/pages/Reports.jsx` — `handleMasterReportDownload(targetFacilityId = null)` (≈line 296) wired as `onClick={handleMasterReportDownload}` (≈line 575).

## Reproduction
1. Log in as audit_admin on the UI stack (:5191), open /reports.
2. In the "All Regions" table filter choose facility 170 (El Merk).
3. Click "2025 Master Report (PDF)".
4. Observe the network request and downloaded file name.

## Input
Region filter = 170, click the header button.

## Expected
Request `GET /api/reports/master-annual-report?facility_id=170` and the El Merk report (the handler's own logic falls back to `regionId` when no target is passed).

## Actual
Request `GET /api/reports/master-annual-report?facility_id=[object%20Object]`; downloaded file is `Groupement_Berkine_2025_Annual_GHG_Report.pdf` regardless of the selected facility. The toast also says "Downloading Groupement Berkine Master Report".

## Evidence
Playwright capture (audit/work/K/t_reports2.mjs):
```
download filename: Groupement_Berkine_2025_Annual_GHG_Report.pdf
GET /api/reports/master-annual-report?facility_id=[object%20Object]
```
Repro: `audit/repro/BUG-<id>.mjs`.

## Root Cause
React passes the click event as the first argument. `targetFacilityId || ...` is truthy for the event object, so `selectedId` becomes the SyntheticEvent, which is stringified into the URL; the `reportSelectedRegions`/`regionId` fallbacks are never reached.

## Impact
The facility-specific master report can never be obtained from this button; the user silently receives a different organisation's consolidated report. (Only the "Create New Report" modal path passes no argument and works.)

## Affected Components
Reports page header button "2025 Master Report (PDF)". (Related observation: title/filename are hard-coded to 2025 and to two named assets, and the backend endpoint serves static PDFs.)

## Recommended Fix
`onClick={() => handleMasterReportDownload()}` and/or guard `typeof targetFacilityId === "string" || typeof targetFacilityId === "number"`.


---

# BUG-003 — Editing a Scope 1 record's quantity via PUT /api/emissions/<id> does not recalculate emissions (stale `amount` from source_payload wins)

**Status:** Confirmed
**Severity:** High
**Category:** Emissions
**Discovered by:** Agent B (Emissions Auditor)

## Location
`new/server/routes/emissions.py` `update_emission()` (~L3398-3530): builds `calc_payload = json.loads(record.source_payload)`, then `calc_payload.update(data)`.
`new/server/calculations/legacy_engine.py:395` `compute_emissions`: `raw_amt = payload.get("amount") if payload.get("amount") not in [None, ""] else payload.get("quantity")`.

## Reproduction
1. As admin, `POST /api/emissions/` with the payload shape the real Scope1Form sends (it sends both `amount` and `quantity`): `{"process_type":"Combustion","source_type":"Combustion","facility_id":1,"year":2024,"month":7,"fuel":"Natural Gas","fuel_type":"Natural Gas","amount":1000,"quantity":1000,"unit":"MMBtu"}`.
2. `PUT /api/emissions/<id>` with `{"quantity": 2000}` (the field the PUT handler documents/uses for `record.quantity`).
3. Read the row back.

## Input
1000 MMBtu natural gas, then edited to 2000 MMBtu.

## Expected
Hand calc (EPA NG 53.06 kg CO2/MMBtu, 1 g CH4, 0.1 g N2O, AR5 28/265): 2000 MMBtu -> 106.12 t CO2 + 0.002 t CH4 + 0.0002 t N2O = **106.229 tCO2e**, and `quantity`=2000.

## Actual
`quantity` = 2000.0 but `co2e_total` = **53.1145** (the value for 1000 MMBtu). The API returns 200 "Record updated". The stored row now says 2000 MMBtu but reports emissions for 1000 MMBtu; the saved `source_payload` then has `quantity:2000, amount:1000`.

## Evidence
`audit/work/B/t2.py` output:
```
[{'quantity': 1000.0, 'co2e_total': 53.1145}]
200 {'message': 'Record updated'}
after PUT quantity=2000: [{'quantity': 2000.0, 'co2e_total': 53.1145}] expected co2e ~106.23
```

## Root Cause
`recalc_keys` includes `quantity`, so recalculation runs. But the merged payload starts from the stored `source_payload`, which already has the old `amount`. `calc_payload.update({"quantity":2000})` leaves `amount` at 1000, and `compute_emissions` prefers `amount` over `quantity`. The same thing happens the other way round (fuel/fuel_type): a PUT of `fuel_type` leaves the old `fuel` in the payload. `_lookup_api_factor` uses the new fuel_type, but the dispatcher reads `inputs['fuel']`.

## Impact
Any API/integration edit of activity quantity silently keeps the old emissions while showing the new quantity. The inventory and the audit trail disagree (the ActivityLog "after" state shows quantity 2000 with co2e 53.11). The record stays Verified for an admin.

## Affected Components
PUT /api/emissions/<id>; every Scope 1 record created via the UI form or bulk path whose source_payload contains `amount`/`fuel`.

## Recommended Fix
Canonicalise in `update_emission`: when `quantity` or `amount` is in `data`, set both `calc_payload["amount"]` and `calc_payload["quantity"]` to the new value (same for `fuel`/`fuel_type`) before calling `compute_emissions`.


---

# BUG-004 — Intensity activity/division filter uses record-level columns that are NULL/inconsistent, so numerator and denominator are filtered differently (Upstream intensity blank, E&P intensity 0.0)

**Status:** Confirmed
**Severity:** High
**Category:** Carbon Intensity
**Discovered by:** Agent E (Carbon-intensity auditor)

## Location
- `new/server/routes/dashboard.py` `_query_intensity_stats` L1690-1693 (production: `ProductionData.activity/division`), L1768-1771 (Scope 1: `Emission.activity/division`), L1912-1915 (Scope 2: `Scope2Emission.activity/division`), L1952-1955 (Scope 3: `Facility.activity/division`)
- Same pattern in `_query_intensity_trend_bulk` L1340-1343, L1408-1411, L1449-1451, L1496-1499, L1531-1537
- Root data cause: `routes/data.py` `add_production` L107-108 stores `activity`/`division` only from the payload (no fallback to `facility.activity`, unlike `background_processor.py` L1395-1396 and `emissions.py` L3163); emissions imported via some paths also carry NULL activity.

## Reproduction
1. `python audit/repro/BUG-004.py` (the number assigned) or manually:
2. `GET /api/dashboard/intensity-stats?year=2025&activity=Upstream` as admin.
3. Compute sum(co2e_S1+S2 Verified)/sum(BOE) for facilities whose `facilities.activity='Upstream'`, same year.

## Input
Snapshot DB (agentE copy). Berkine facilities 169 (HBNS) / 170 (El Merk): `facilities.activity='Upstream'`, their 70 Verified emissions have `emissions.activity='Upstream'`, but their `production_data.activity` is NULL. 160 Verified emissions of 'Activité E&P' facilities have `emissions.activity` NULL while their production rows carry 'Activité E&P'.

## Expected
Same filter applied to numerator and denominator (facility-level):
- activity=Upstream, 2025: 16.355 kg CO2e/BOE over 116.7 M BOE; 2022: 19.554 kg/BOE
- activity=Activité E&P, 2025: 0.772 kg/BOE; 2022: 0.227
- activity=Steel & Iron (Acier DRI), 2022: 85.968 kg/BOE

## Actual
- activity=Upstream: every row has total_boe=0 → co2_intensity 0 for all facilities, weighted KPI undefined (dashboard shows "Pending Production" even though 116.7 M BOE exist)
- activity=Activité E&P: 0.0 kg/BOE (production counted, 160 emissions dropped from numerator)
- Steel & Iron 2022: 0.0 kg/BOE instead of 85.97
- Unfiltered (year=2025) matches expected (10.855) → the discrepancy comes only from the filter.

## Evidence
`audit/work/E/api2.py` output:
```
Upstream 2025 API None B 0 | expected 16.355 B 116715870
Upstream 2022 API None B 0 | expected 19.554 B 118638289
Activité E&P 2025 API 0.0 B 47541331 | expected 0.772
Steel & Iron (Acier DRI) 2022 API 0.0 B 1148671 | expected 85.968
```
SQL: `select coalesce(p.activity,'NULL'), f.activity, count(*) from production_data p join facilities f ... ` → ('NULL','Upstream',10); emissions: ('NULL','Activité E&P',160 Verified), ('Power Generation','Steel & Iron (Acier DRI)',8).

## Root Cause
The activity/division filter is applied to four different columns (record-level on production, Scope 1 and Scope 2; facility-level on Scope 3). Record-level labels are optional, often NULL and can differ from the facility's label, so the numerator and the denominator are filtered on different populations.

## Impact
With the activity or division filter set, the corporate and facility carbon intensity (Dashboard "Performance Intensity" KPI, Carbon Intensity page, Methane Intensity page, intensity trend and PDF report) is wrong or missing. The largest producers (Berkine, about 65% of 2025 BOE) disappear from the "Upstream" view.

## Affected Components
`/api/dashboard/intensity-stats`, `/api/dashboard/intensity-trend`, `/api/dashboard/batch-all` (intensity_stats, intensity_stats_py), DashboardEnhanced KPI, CarbonIntensity.jsx, MethaneIntensity.jsx, MethaneExplorer.jsx, ModernReportGenerator.js.

## Recommended Fix
Filter all numerator and denominator queries by the same facility attribute (join `Facility` and filter `Facility.activity/division`). Alternatively, default record-level activity/division to the facility's value on every write path, including `POST /api/data/production`, and backfill the NULL values.


---

# BUG-005 — GWP-20 conversion in intensity-stats / intensity-trend hard-codes AR5 GWP-100 (28 / 265), so GWP-20 CO2e is wrong whenever the active standard is AR4 or AR6

**Status:** Confirmed
**Severity:** Medium
**Category:** Methane
**Discovered by:** Agent D (Methane Auditor)

## Location
- `new/server/routes/dashboard.py` `_query_intensity_stats` (~line 2030): `delta_gwp = (ed["total_ch4"] * (ch4_gwp20 - 28.0)) + (ed["total_n2o"] * (n2o_gwp20 - 265.0))`
- `new/server/routes/dashboard.py` `_query_intensity_trend_bulk` (~line 1592): same expression.
- Contrast: `_query_summary` (~line 476) and `_query_categorical_breakdown` (~line 789) correctly use `get_active_gwp(horizon="100")`.

## Reproduction
1. Fresh audit DB copy; log in as admin.
2. `PUT /api/auth/settings {"gwp_standard":"AR4"}` (this triggers `recalculate_all_emissions_gwp`, so stored `co2e_total` = CO2 + 25·CH4 + 298·N2O).
3. `GET /api/dashboard/batch-all?...&gwp_horizon=20` → `summary[year].scope1_total_gwp20`.
4. `GET /api/dashboard/intensity-stats?year=<year>` → sum of `total_scope1_gwp20`.
5. Compare both with a hand calculation from DB rows: Σ(CO2 + CH4·72 + N2O·289) (the app's own AR4 20-yr values).

## Input
Snapshot data, Verified Scope 1 rows, year 2021 (CH4 ≈ 14.3 Mt) and 2023.

## Expected
GWP-20 CO2e = CO2 + CH4·GWP20_CH4 + N2O·GWP20_N2O for the active standard. Equivalently, the delta applied to the stored GWP-100 total must be CH4·(GWP20_CH4 − GWP100_CH4_active) + N2O·(GWP20_N2O − GWP100_N2O_active). For AR4 that is CH4·47 − N2O·9.
- 2021: 5,736,270,170 tCO2e
- 2023: 2,423,600.75 tCO2e

## Actual
- `/summary` (hero card): 5,736,270,170.28 (2021) and 2,423,600.75 (2023). These are correct.
- `/intensity-stats` Σ total_scope1_gwp20: **5,697,952,104** (2021, −38.3 Mt, −0.67 %) and **2,406,187.46** (2023, −17.4 kt, −0.72 %).
Under AR4 the code applies CH4·44 + N2O·24 instead of CH4·47 − N2O·9. Under AR6 it applies CH4·54.5 + N2O·8 instead of CH4·54.6 + N2O·0; the 2023 overstatement is 187.7 t.

## Evidence
`audit/work/D/s2.py AR4 2021`, `s2.py AR4 2023` and `s2.py AR6 2023` outputs. Repro: `audit/repro/<ID>.py`.

## Root Cause
The 100-year base in the GWP-20 delta is the literal AR5 value (28 / 265), not `get_active_gwp(horizon="100")`. `recalculate_all_emissions_gwp()` restates stored `co2e_total` with the active standard's GWP-100, so the literal subtraction no longer matches the stored basis.

## Impact
With AR4 or AR6 selected, every GWP-20 value derived from intensity-stats or intensity-trend is wrong. That covers `co2_intensity_gwp20`, `scope1_intensity_gwp20`, `total_co2e_gwp20` and `total_scope1_gwp20`: the dashboard Performance Intensity KPI in GWP-20 mode, Carbon/Methane intensity pages and trend charts. They then disagree with the dashboard hero total, which is computed correctly.

## Affected Components
`_query_intensity_stats`, `_query_intensity_trend_bulk`, `/api/dashboard/intensity-stats`, `/api/dashboard/intensity-trend`, `batch-all.intensity_stats(_py)`, DashboardEnhanced intensity KPI (GWP-20), CarbonIntensity/MethaneIntensity pages.

## Recommended Fix
Use `gwp100 = get_active_gwp(horizon="100")` and compute `delta = ch4*(g20["CH4"]-g100["CH4"]) + n2o*(g20["N2O"]-g100["N2O"])`, or better, compute GWP-20 directly as CO2 + CH4·g20 + N2O·g20. Share one helper across all four call sites.


---

# BUG-006 — Reports Excel/PDF exports drop the Division, Field, Method and Search filters shown on screen

**Status:** Confirmed
**Severity:** Medium
**Category:** UI
**Discovered by:** Agent K (Frontend/UI)

## Location
`new/client/src/pages/Reports.jsx` — `handleExcelExport` (≈line 195) and `handlePDFExport` (≈line 228) build their params from `scope/year/month/regionId/processType` only.

## Reproduction
1. Log in as audit_admin (:5191), open /reports, set the table Year filter to "All", Division = "Upstream".
2. The table shows "Total Records: 61".
3. Click "Excel Export" and then "PDF Report"; capture the requests.

## Input
Division = Upstream (same for Field, Method, and the search box).

## Expected
`/api/emissions/export?...&division=Upstream&format=excel` and `/api/reports/export?...&division=Upstream` — both backend endpoints accept `division`, `field`, `method`, `search` (routes/emissions.py ≈4047-4050, routes/reports.py `export_emissions`).

## Actual
```
GET /api/emissions/export?scope=all&format=excel
GET /api/reports/export?scope=all
```
The division filter is silently dropped. Via the API, the unfiltered export contains 660 rows vs 63 with `division=Upstream`, so the downloaded file contains ~10x the records the user was looking at.

## Evidence
Playwright capture `audit/work/K/t_reports3.mjs`; repro `audit/repro/BUG-<id>.mjs`.

## Root Cause
Export param builders were not updated when the Division/Field/Method/Search filters were added to the list query (`fetchEmissions` sends them).

## Impact
Exported spreadsheets/PDFs do not match the on-screen filtered table; a user exporting "Upstream" data submits/uses the whole-company dataset without any warning.

## Affected Components
Reports page: Excel Export, PDF Report buttons.

## Recommended Fix
Build one shared params object (the one used by `fetchEmissions`, minus page/per_page) and reuse it for both exports.


---

# BUG-007 — Manual Scope 1 entry has no plausibility bound or QA flag: 9 test records (1e13 MMBtu gas, 1e15 t coal) make up about 99.99% of the snapshot's Scope 1 total (3.72e12 t Verified, 4.69e12 t Pending)

**Status:** Confirmed
**Severity:** Medium
**Category:** Emissions
**Discovered by:** Agent B (Emissions Auditor)

## Location
`new/server/routes/emissions.py` `add_emission()` (POST /api/emissions/, ~L2977-3060). It checks only for finite and non-negative values, and applies no upper bound or anomaly check. Compare `background_processor.py` ~L545-575, where bulk rows go through `anomaly_detector.check_scope1` and get `qa_flag`. Admin entries are auto-`Verified` (L3217-3225) with no review.

## Reproduction
1. As admin, send `POST /api/emissions/` with `{"process_type":"Combustion","source_type":"Combustion","facility_id":1,"year":2024,"month":7,"fuel":"Natural Gas","amount":1e13,"unit":"MMBtu"}`. The response is 201. The row is `status='Verified'`, `qa_flag=NULL`, `co2e_total=531,145,000,000` t.
2. Send the same request with `amount: 1e300`. The response is 201 with `totalCo2e = 5.3e298` t.

## Input
1e13 MMBtu natural gas at one facility in one month. That is about 70x world annual gas consumption (~1.5e11 MMBtu/yr).

## Expected
The request is rejected, or at least flagged (`qa_flag`) and kept out of auto-Verified status. The bulk path already applies a z-score anomaly check and a 1e7 outlier flag.

## Actual
The request is accepted and Verified, with no flag. On the snapshot DB this is what drives the dashboard lead:
- Scope 1 Verified sum = 3,723,125,709,415 t. Seven rows (ids 640, 645, 649, 658, 662, 667, 669) contribute 3,718,014,999,999.6 t, which is 99.86%. Each is "Admin test record", NG `quantity` 9,999,999,999,999 MMBtu (from `source_payload`), co2e = 531,145,000,000 t. Hand calc: 9.999999999999e12 x (53.06 + 0.001x28 + 0.0001x265) kg / 1000 = 5.31145e11 t. **The math is correct, but the input is absurd.**
- Scope 1 Pending sum = 4,686,441,566,610 t. Two rows (655, 675) contribute 4,686,441,120,000 t. Each is "User test emission", Coal `quantity` 1e15 tonnes, co2e = 2.343e12 t.
- `pending_stats` in `/api/dashboard/batch-all` = 114 Scope 1 + 14 Scope 2 = **128 records, totalCo2e 4.686e12 t**. The "4.69e15" in the lead is 4.69e12 t; the client renders it with `toLocaleString()`.

## Evidence
`audit/work/B/t3.py` output: `201 [{'status': 'Verified', 'qa_flag': None, 'co2e_total': 531145000000.0}]`, and a second 201 with `totalCo2e 5.311e+298`.
SQL: `select status,count(*),sum(co2e_total) from emissions group by status` gives Pending 114 / 4.686e12 and Verified 630 / 3.723e12. Without the 9 test rows: Verified is about 5.11e9 t and Pending about 446,610 t.

## Root Cause
Only `isfinite`/`>=0` checks are applied to quantity. There is no magnitude or statistical plausibility check on the manual create path, and admin-created rows skip review.

## Impact
One typo (extra zeros) or test entry through the UI/API is instantly Verified and dominates every Scope 1 total, intensity, SBTi trajectory and report. On the snapshot, the dashboard gross Scope 1+2 (3.7 trillion t) is wrong by about 3 orders of magnitude for this reason.

## Affected Components
POST /api/emissions/ (the Scope1Form and scope1/*Form.jsx save path), all dashboard, report and intensity aggregates.

## Recommended Fix
Run the same `anomaly_detector.check_scope1` / outlier threshold used in bulk upload on manual create and PUT. Set `qa_flag` and force `Pending` when flagged, even for admin. Also add a hard sanity cap per unit (e.g. co2e per record > 1e8 t rejected).


---

# BUG-008 — Inventory uncertainty shrinks by √N when the same emissions are split into N records (shared EF uncertainty treated as independent)

**Status:** Confirmed
**Severity:** High
**Category:** Uncertainty
**Discovered by:** Agent G (Uncertainty Auditor)

## Location
`new/server/routes/dashboard.py` `_query_uncertainty()` (~L2370-2615): Scope 1/2/3 queries group by (process, fuel, method, stored uncertainty) and compute `u_eff = u * sqrt(Σe²)/Σe`, then `srss_inventory()` sums every record in quadrature.

## Reproduction
1. As admin, POST 12 monthly `stationary_combustion` / Natural Gas / 1000 m3 / factor_source=default records for year 2041 (facility 4).
2. POST one record of 12000 m3 for year 2042 (same facility / fuel / factor).
3. GET `/api/dashboard/uncertainty?year=2041` and `?year=2042`.
Script: `audit/repro/<ID>.py`.

## Input
Identical annual inventory (22.9588 tCO2e, same emission factor, same stored per-record uncertainties) entered as 12 records vs 1 record.

## Expected
Identical inventory uncertainty for both years. The EF (±5 % @95 %) is a single value shared by all 12 records, so its error is fully correlated; IPCC 2006 Vol.1 Ch.3 Approach 1 applies the EF uncertainty to the category total. Hand calculation for this category: √(5² + 10²) = ±11.18 % (95 %).

## Actual
- 12 monthly records: ±6.45 %
- 1 annual record: ±22.36 %
The ratio is exactly √12 = 3.464.
(The ±22.36 % is itself 2× too high because of a separate cross-gas max issue.)

## Evidence
`u_eff = u·√(Σe²)/Σe` combined in `srss_inventory` gives relative σ = u·√(Σe²)/Σe. With 12 equal records this equals u/√12. The repro prints both results and the ratio.

## Root Cause
Every record (or group of records) is treated as an independent source. That holds for random activity-data metering error, but not for the emission-factor component, which is common to every record using the same factor. The EF and AD components are never separated. Only a single combined per-record 1σ is stored, so the dashboard cannot correlate them.

## Impact
The reported inventory and category uncertainty depends on data-entry granularity rather than on data quality. Monthly entry, which is the normal workflow, understates uncertainty by about √12 ≈ 3.5×. Facilities with many small records look far more certain than they are. For example, snapshot 2022 fuel_gas shows ±21.3 % while every contributor is ±30 %. The figure on the Uncertainty Assessment page, in its CSV export and in the Master Report is therefore not ISO 14064-1 / IPCC-defensible.

## Affected Components
`/api/dashboard/uncertainty` (JSON and CSV), `UncertaintyAssessment.jsx`, `ModernReportGenerator.js` (uses the same endpoint), `/api/qaqc/dashboard` `tier1_uncertainty` (same per-record quadrature sum, `routes/qaqc.py` ~L175-222).

## Recommended Fix
Aggregate emissions per source category / emission factor first. Apply the EF uncertainty to the category total, fully correlated. Combine only the independent activity-data components in quadrature within a category. Then combine categories with IPCC Eq. 3.2. This requires persisting the EF and AD components separately, or recomputing them from tier/factor at query time.


---

# BUG-009 — Deleting a facility that has any OGMP level-upgrade log fails with 500 (FK violation) and leaks raw SQL

**Status:** Confirmed
**Severity:** Medium
**Category:** Database
**Discovered by:** Agent J (Database)

## Location
- `new/server/models.py` `LevelUpgradeLog` (line ~567): `facility_id` FK `nullable=False`, `facility = db.relationship("Facility")` with no backref/cascade; `Facility` (line ~41) declares cascades for emissions, production, scope2/3, sources, mitigation, CBAM, OGMP, (backref) CAP, flaring, equity — but not level-upgrade logs.
- `new/server/routes/facilities.py:351` `delete_facility` — returns `f"Failed to delete facility: {str(e)}"`.

## Reproduction
1. `make_db("agentJ", overwrite=True)`; log in as admin.
2. `DELETE /api/facilities/1` (facility 1 has one row in `level_upgrade_logs`, created through `POST /api/data/ogmp/level-upgrade`).
3. Compare with `DELETE /api/facilities/2` (no level-upgrade log).

## Input
Snapshot data; facility 1 and 4 each have one `level_upgrade_logs` row.

## Expected
Either the facility and its dependent rows are deleted (as for every other child table), or a clear 409 "facility has dependent OGMP level logs" is returned.

## Actual
`500 {"error": "Failed to delete facility: (sqlite3.IntegrityError) FOREIGN KEY constraint failed\n[SQL: DELETE FROM facilities WHERE facilities.id = ?]..."}`. Facility 2 (no log) deletes fine with 200.

## Evidence
`audit/repro/BUG-<id>.py`; `audit/work/J/cascade.py` output: facility 1 → 500, facility 4 → 500, facility 2 → 200, facility 169 → 200 (CAP/flaring/equity cascades work).
`PRAGMA foreign_keys` = 1 on every connection (NullPool + connect hook), so the FK is enforced.

## Root Cause
`LevelUpgradeLog` is the only facility child table without a delete cascade (or `ondelete`), and its `facility_id` is NOT NULL, so SQLAlchemy cannot null it and SQLite rejects the parent delete.

## Impact
Once anyone logs an OGMP level upgrade for a facility (normal OGMP workflow), that facility can never be deleted through the app. The error body exposes internal SQL text to the client. (On Postgres the same FK error occurs.)

## Affected Components
Facility delete endpoint, Manage Data / facility admin UI, OGMP level-upgrade workflow.

## Recommended Fix
Add `level_upgrade_logs = db.relationship("LevelUpgradeLog", backref=..., cascade="all, delete-orphan")` on Facility (or `ondelete="CASCADE"` + passive_deletes), or explicitly block with a 409 and a clean message; never echo `str(e)` to the client.


---

# BUG-010 — Deleting a user who created production data, SBTi targets or OGMP level logs fails with 500 (FK cleanup list incomplete)

**Status:** Confirmed
**Severity:** Medium
**Category:** Database
**Discovered by:** Agent J (Database)

## Location
`new/server/routes/auth.py:1058` `delete_user` — hard-coded `tables_to_clean` list (emissions, scope2/3, mitigation_projects, mitigation_records, facilities, emission_sources, custom_factors, cbam_product_exports, base_year_recalculations, ogmp_surveys).

## Reproduction
1. `make_db("agentJ", overwrite=True)`; log in as `it_admin`.
2. `DELETE /api/auth/users/1` (user 1 created 864 production_data rows, 3 sbti_targets, 2 level_upgrade_logs).
3. Compare `DELETE /api/auth/users/9` (only emissions references) → 200.

## Input
Snapshot data.

## Expected
User is deleted and every `created_by` reference is nulled (as the endpoint does for other tables), or a clean 409 explaining why deletion is blocked.

## Actual
`500 {"error": "Internal server error"}`; server log: `sqlite3.IntegrityError: FOREIGN KEY constraint failed [SQL: DELETE FROM users WHERE users.id = ?]`. User still exists.

## Evidence
`audit/repro/BUG-<id>.py`, `audit/work/J/userdel.py`. PRAGMA foreign_keys = 1 on every connection (verified), so FKs are enforced.

## Root Cause
Tables with `created_by → users.id` missing from the clean-up list: `production_data`, `sbti_targets`, `level_upgrade_logs`, `cap_emissions`. (`mitigation_records` in the list has no such columns — the try/except silently swallows that.) No `ondelete` on any users FK.

## Impact
IT admins cannot remove accounts of any user who ever entered production data, an SBTi target, or an OGMP level log — i.e. most real operational users (offboarding / access-revocation workflow broken). Also, the preceding UPDATEs are part of the same failed transaction so nothing is changed, but the client only sees a generic 500.

## Affected Components
User management (IT admin), `/api/auth/users/<id>` DELETE.

## Recommended Fix
Derive the clean-up list from `db.metadata` (all FKs referencing `users.id`), or declare `ondelete="SET NULL"` on those FKs; alternatively prefer deactivation (`status='inactive'`) over hard delete.


---

# BUG-011 — Well-completion "Rate × Duration" method divides the Mcf/hr rate by 24 (treats it as Mcf/day): CH4 understated 24×

**Status:** Confirmed
**Severity:** High
**Category:** Calculation
**Discovered by:** Agent A (Calculation Engine Auditor)

## Location
- `new/server/calculations/vented.py` `CompletionFlowbackCalculator.calculate` — `rate_unit="mscf/day"` default and branch `rate_scf_hr = (float(flowback_rate) * multiplier) / 24.0`
- `new/server/calculations/dispatcher.py` `dispatch()` `elif process_type == "completions"` — calls the calculator without `rate_unit`
- `new/client/src/components/scope1/CompletionsForm.jsx` — the field is labelled **"Avg Gas Rate (Mcf/hr)"**, and `Scope1Form.jsx` also treats it as Mcf/hr (`finalAmount = rateMcfHr * durationHr * 28.3168`)

## Reproduction
1. As admin, send `POST /api/emissions/` with the payload the Scope 1 form builds for Completions (Tier 3, method "Rate × Duration"):
   `process_type=completions, factor_source=specific, amount=339.8016, unit=m3, calc_inputs.completions={calc_method:"rate_duration", comp_rate:0.5, comp_duration:24, ch4_content:80, amount:2}`
2. Read `emissions.ch4_emissions` / `co2e_total` for the new id.
3. Repro: `audit/repro/BUG-044.py`

## Input
Rate 0.5 Mcf/hr, duration 24 h, 2 events, 80 mol% CH4, vented (no flare). AR5.

## Expected
Gas = 0.5 Mcf/hr × 1000 scf/Mcf × 24 h × 2 events = 24,000 scf = 679.60 m³ (60 °F, 14.696 psia).
CH4 = 679.60 × 0.80 × 0.6785 kg/m³ = 368.9 kg = **0.3689 t CH4** → 10.33 tCO2e (GWP 28).

## Actual
`ch4_emissions = 0.015370 t`, `co2e_total = 0.4304 t`. That is exactly 1/24 of the expected value.

## Evidence
The DB row from the audit copy (`agentA.db`): `{'ch4_emissions': 0.015370384330137602, 'co2e_total': 0.4303707612438529, 'calc_method': 'Well Completion Flowback'}`. Ratio 0.3689/0.01537 = 24.0.

## Root Cause
The calculator assumes the rate is in Mcf/**day** unless `rate_unit` contains "hr". The dispatcher never passes a rate unit, but the UI collects Mcf/**hr**. The multiplier logic is also order-dependent: `"mscf" in "mmscf/day"` is true, so an MMscf rate would get ×1000 instead of ×1e6.

## Impact
Every Tier 3 completion or flowback record entered with the Rate × Duration method (the form's default) under-reports CH4 and CO2e by 24×. This feeds Scope 1, methane intensity and OGMP totals.

## Affected Components
dispatcher `completions` branch; `CompletionFlowbackCalculator`; Scope 1 form (Completions); bulk import rows that use `comp_rate`.

## Recommended Fix
Pass an explicit `rate_unit` (UI: "mcf/hr") from the dispatcher, and make the calculator's default match the UI label. Test "mmscf" before "mscf" in the multiplier. Add a regression test against the hand value above.


---

# BUG-012 — Well-completion Tier 3 uses `amount` as both the flowback volume and the event count (volume squared), and ignores rate × duration when the method dropdown is left at its default

**Status:** Confirmed
**Severity:** High
**Category:** Calculation
**Discovered by:** Agent A (Calculation Engine Auditor)

## Location
`new/server/calculations/dispatcher.py`, `dispatch()`, `elif process_type == "completions"`:
- `events_val = float(flat_inputs.get("amount") or flat_inputs.get("events") or 1.0)`
- `comp_method = flat_inputs.get("comp_method") or flat_inputs.get("calc_method") or flat_inputs.get("calculation_method", "metered_volume")`
- `vol_raw = self._require_float(flat_inputs, ["amount", "quantity", "flowback_volume", "comp_volume"], ...)`

`CompletionFlowbackCalculator` (metered branch) then computes `total_gas_m3 = flowback_volume * num_events`.

`new/client/src/components/scope1/CompletionsForm.jsx` shows "Rate × Duration" as the selected method (`value={data.calc_method || "rate_duration"}`) but does not put `calc_method` into formData until the user changes the dropdown. It also sends the **event count** as `amount`.

## Reproduction
1. `POST /api/emissions/` with `process_type=completions, factor_source=specific, amount=1000, unit=m3, ch4_content=80, comp_method=metered_volume` (1,000 m³ metered flowback).
2. `POST /api/emissions/` with the UI payload when the method dropdown was not touched: `calc_inputs.completions={comp_duration:24, comp_rate:0.5, ch4_content:80, amount:2}` (no `calc_method`).
3. Repro: `audit/repro/BUG-044.py`

## Input
(1) 1,000 m³ metered, 80 % CH4. (2) 0.5 Mcf/hr × 24 h × 2 events, 80 % CH4.

## Expected
(1) 1000 × 0.80 × 0.6785 / 1000 = **0.5428 t CH4** (15.20 tCO2e AR5).
(2) 24,000 scf = 679.6 m³ → **0.3689 t CH4**.

## Actual
(1) `ch4_emissions = 542.8 t` (**1000× too high**: volume 1000 × "events" 1000).
(2) `ch4_emissions = 0.002171 t` (**170× too low**). The server fell back to `metered_volume`, took `amount`=2 (the event count) as 2 m³ of gas, and multiplied by 2 events. Rate and duration were ignored.

## Evidence
DB rows in `agentA.db`: (1) `ch4_emissions 542.8, co2e_total 15198.4`; (2) `ch4_emissions 0.0021712, co2e_total 0.0608`.

## Root Cause
The single field `amount` is read both as the event multiplier and as the metered volume. The server defaults the method to `metered_volume`, while the UI displays `rate_duration` as its default and never sends it.

## Impact
Metered completions submitted through the API or bulk import are inflated by a factor equal to the volume (quadratic). UI entries where the method dropdown was left at its default are understated by orders of magnitude. Both errors flow into Scope 1 CH4, methane intensity and OGMP.

## Affected Components
dispatcher completions branch; `CompletionFlowbackCalculator`; `CompletionsForm.jsx` / `Scope1Form.jsx`; bulk import (`background_processor`) rows for completions.

## Recommended Fix
Use a dedicated `events` field (never `amount`) for the event count, and a dedicated volume field for metered flowback. Default the server method to the one the UI shows, or have the UI always send `calc_method`. Reject ambiguous payloads.


---

# BUG-013 — AR5 20-year GWPs are wrong (CH4 82.5 instead of 84, N2O 268 instead of 264); AR6 pairs the fossil CH4 GWP-20 with the non-fossil-weighted GWP-100

**Status:** Confirmed
**Severity:** Medium
**Category:** Methane
**Discovered by:** Agent D (Methane Auditor)

## Location
- `new/server/calculations/constants.py:12`: `GWP_AR5 = {..., "CH4_20": 82.5, "N2O_20": 268.0}`. The module comment cites "AR5 - 2013, WG1 Table 8.7".
- `constants.py:15`: `GWP_AR6 = {"CH4": 27.9, ..., "CH4_20": 82.5}`.
- `constants.py:78-79`: fallback defaults 82.5 / 268.0.
- Mirrors: `new/client/src/constants.js:14-15,22,40-41`, `routes/auth.py:688-689`, `client/src/pages/Settings.jsx:33,44,514`.
- `DashboardEnhanced.jsx:723` toggle tooltip says "20-Year (Near-term, CH4=84 per IPCC AR5/AR6)". That is not the value applied.

## Reproduction
1. Default settings (AR5). `GET /api/dashboard/batch-all?...&gwp_horizon=20`.
2. For 2026: `scope1_total` (GWP-100) = 9,992.41, `ch4_total` = 338.9115 t, and `scope1_total_gwp20` = 28,463.09.
3. (28,463.09 − 9,992.41) / 338.9115 = 54.50 = 82.5 − 28. So CH4 is converted with a GWP-20 of 82.5.

## Input
Any CH4 or N2O quantity with the GWP-20 horizon under AR5 (the application default).

## Expected
IPCC AR5 WG1 Table 8.7 (without climate-carbon feedback, the set whose GWP-100 values 28 / 265 the app uses):
- CH4: GWP-20 = 84, GWP-100 = 28
- N2O: GWP-20 = 264, GWP-100 = 265

IPCC AR6 WG1 Table 7.15:
- CH4, fossil: GWP-20 = 82.5, GWP-100 = 29.8
- CH4, non-fossil: GWP-20 = 80.8, GWP-100 = 27.2
- The app's AR6 GWP-100 of 27.9 is the generic CH4 value, whose matching GWP-20 is 81.2.

For 1 t CH4 under AR5: expected 84 tCO2e (GWP-20); for 1 t N2O: 264 tCO2e.

## Actual
- AR5: 1 t CH4 gives 82.5 tCO2e (−1.8 %); 1 t N2O gives 268 tCO2e (+1.5 %).
- AR6: 27.9 is paired with 82.5, so the 100-yr and 20-yr figures come from different CH4 categories.
- The UI tooltip tells users 84 is used.

## Evidence
`batch-all` summary output (audit/work/D/s1.py): 2026 GWP-100 9,992.41 → GWP-20 28,463.09 with CH4 338.9115 t (Δ/CH4 = 54.50). The 2021 delta is also consistent with (82.5−28)·CH4 + (268−265)·N2O. Repro: `audit/repro/<ID>.py`.

## Root Cause
Wrong literals in the GWP table (82.5 is the AR6 fossil-CH4 GWP-20, copied into AR5; 268 matches no AR5 table value), mirrored into the client constants.

## Impact
With the GWP-20 toggle under the default AR5 standard, every methane CO2e is understated by 1.5 tCO2e per tCH4. For the snapshot's 84.3 Mt Verified CH4 that is ≈126 MtCO2e. The GWP-20 hero total, categorical breakdown, intensity (co2_intensity_gwp20), Settings table and Reports "20yr" option all use these values.

## Affected Components
calculations/constants.py, get_active_gwp(horizon="20"), dashboard `_query_summary`, `_query_categorical_breakdown`, `_query_intensity_stats`, `_query_intensity_trend_bulk`, client constants.js, Settings.jsx GWP table, DashboardEnhanced GWP toggle tooltip.

## Recommended Fix
Set AR5 `CH4_20 = 84`, `N2O_20 = 264`. For AR6, use a consistent CH4 pair (27.9 / 81.2, or fossil 29.8 / 82.5 by source category). Keep constants.js, Settings.jsx and auth.py in sync, and make the tooltip read from the active constants.


---

# BUG-014 — SBTi progress KPI uses the current, incomplete year (and any future year) as the "current" year, so the dashboard reports ~95-99% reduction and ON TRACK

**Status:** Confirmed
**Severity:** High
**Category:** SBTi
**Discovered by:** Agent H (SBTi Auditor)

## Location
`new/server/routes/dashboard.py` `get_sbti_trajectory()` lines ~2816-2843 (`candidate_years` / `latest_actual_year` / `current_actual` / `reduction_achieved_pct` / `on_track`). Consumed by `new/client/src/pages/SbtiDashboard.jsx` KPI cards "Current Year Target", "Pathway Status" (ON TRACK / BEHIND TARGET, "Reduction: X% vs Baseline").

## Reproduction
1. `python C:/Users/samsung/Desktop/H2/audit/repro/<BUG-ID>.py` (own db copy; controlled data).
2. Scenario: base year 2020 = 1000 t (S1+S2+S3), full year 2023 = 950 t, target 4.2 %/yr linear 2020→2030.
3. Add a single Verified January record of the current year (2026) = 50 t.
4. `GET /api/dashboard/sbti-trajectory`.

## Input
Target `{base_year:2020, base_year_emissions:1000, target_year:2030, reduction_rate_pct:4.2}`; Verified rows as above.

## Expected
Progress must be measured on the latest complete reporting year (2023): actual 950 t vs linear target 1000×(1−0.042×3) = 874 t → reduction 5.0 %, **BEHIND TARGET**. The current year should at most be shown as year-to-date, never compared to a full-year target.

## Actual
`latest_actual_year=2026, current_actual=50, current_target=748, reduction_achieved_pct=95.0, on_track=true` → page shows "ON TRACK — Reduction: 95% vs Baseline".
On the unmodified snapshot (admin): `latest_actual_year=2026`, `current_actual=10,261.46 t` (2026 data only through Sept; 2025 full year = 1,954,194 t), `reduction_achieved_pct=98.63`, `on_track=true` although the full year 2025 (1.95 Mt) is 2.7× above its 718,500 t target.

## Evidence
`candidate_years = [y for y in range(base_year, end_year+1) if y in actuals]; latest_actual_year = max(candidate_years)` — no check that the year is complete or ≤ the last closed reporting year. Snapshot DB: 2026 Verified Scope 1 = 9,992 t across months 1–10 (month 10 is in the future), 2025 Verified = 1,636,882 t.

## Root Cause
"Current" year is simply the max year having any Verified row within [base_year, target_year]. Partial current-year data, or mis-dated future-year data (the snapshot has Verified rows in 2099 and in 2026-10), becomes the progress year and is compared to a full-year target.

## Impact
The headline SBTi status and "% reduction vs baseline" on the SBTi page (and any consumer of `on_track`/`reduction_achieved_pct`) is grossly overstated for most of every calendar year; a company that is off-track is shown as ON TRACK. The CSV export marks the current year "Achieved".

## Affected Components
`/api/dashboard/sbti-trajectory` summary fields; `SbtiDashboard.jsx` KPI cards, milestone table row for the current year, CSV export status; `DashboardEnhanced.jsx` SBTi banner (actual line drops to near zero in current year).

## Recommended Fix
Select the progress year as the latest year ≤ (current_year − 1) (or the last year flagged as closed/complete, e.g. 12 months of data), ignore years > current year, and label the current year as YTD / exclude it from on-track evaluation.


---

# BUG-015 — 43 Tier 1 factors offered in the Scope 1 UI do not exist in the server catalog; records save with HTTP 201 and 0 emissions

**Status:** Confirmed
**Severity:** Critical
**Category:** Emissions
**Discovered by:** Agent C (Tier / Factor Auditor)

## Location
- `new/client/src/utils/EmissionFactors.js` `API_FACTORS` (121 entries). `Scope1Form.jsx` lines ~205-231 build the Tier 1 fuel dropdown from it and send `fuel: <key>`.
- `new/server/routes/emissions.py` `_lookup_api_factor()` (line ~38) returns `{}` for unknown names. The create route never rejects an empty factor.
- `new/server/calculations/legacy_engine.py` `compute_emissions`: the dispatcher returns all zeros, then the fallback branches (`server_default`, `server_pneumatic_factor`, `server_tank_factor`, `server_dehydrator_factor`) multiply by a factor of `0`.

## Reproduction
1. `python audit/repro/BUG-<ID>.py`. It exports the live client catalog with node and POSTs one Tier 1 (`factor_source=default`) record per client-only factor to `/api/emissions/` as admin.
2. Or manually: POST `/api/emissions/` with `{"process_type":"combustion","fuel":"Butane","factor_source":"default","amount":1000,"unit":"scf","facility_id":1,"year":2025,"month":1}`.

## Input
59 of the 121 client dropdown factors have no key in the server `API_FACTORS`. 56 of them carry a non-zero client EF. Examples:
- Butane 1000 scf: client EF 65 kg CO2/MMBtu, HHV 3280 Btu/scf.
- CNG / LNG.
- Naphtha, Ethanol, Biodiesel, Wood, Tires.
- "Pneumatic Device - High Bleed" (37.3 scf/hr/device).
- "Blowdown - Pipeline" (1.5 t CH4/event).
- "Methane Flashing - Production Condensate" (1.56 kg CH4/bbl).
- "Dehydrator - TEG (No Controls)".

## Expected
The client factor is applied. For Butane 1000 scf: 3.28 MMBtu × 65 = 213.2 kg CO2 = 0.213 t. Otherwise the server rejects the request with 4xx "factor not found".

## Actual
43 of the 56 are stored with `co2e_total = 0` and HTTP 201, with calc_method `server_default` or a `server_*_factor` fallback. Admin records are stored as `Verified`, so they count in dashboards and reports as zero-emission sources.

The other 13 are non-zero only because a hard-coded legacy fallback, such as the fugitive average table, computes something unrelated to the selected factor.

## Evidence
Repro output (db `agentC_repro_zero`):
- "saved with HTTP 2xx and co2e_total == 0: 43".
- Includes ('Butane','combustion','scf',201,0.0,'server_default').
- Includes ('Pneumatic Device - High Bleed','pneumatic','devices',201,0.0,'server_pneumatic_factor').
- Includes ('Blowdown - Pipeline','venting','event',201,0.0,'server_default').

## Root Cause
There are two independent factor catalogs. The UI lists client keys, but the server looks the factor up by name in its own catalog. On a miss, `factor_data={}` flows into the calculators, and a missing factor is treated as 0 instead of an error. Only the bulk-upload path rejects a missing standard factor, and only for combustion processes (`emissions.py` ~line 666).

## Impact
Whole emission sources silently vanish from inventories. Examples: pneumatic devices, blowdowns, tank flashing, CNG/LNG and biofuel combustion. The user sees a success toast, and no QA flag is raised.

## Affected Components
- Scope 1 manual entry (POST `/api/emissions/`) and recalculation (PUT).
- The bulk upload for non-combustion processes (`is_non_comb` branch uses `API_FACTORS.get(fuel, {})` without an error).
- Dashboards and reports aggregating these records.

## Recommended Fix
- Serve the Tier 1 dropdown from the server catalog (`/api/emission-factors`), or merge the catalogs into one source.
- In `compute_emissions`/`create_emission`, reject `factor_source` default/custom when no factor is resolved, instead of computing with 0.


---

# BUG-016 — Alembic migration chain is unusable: `flask db upgrade` fails on both the existing DB and a fresh DB

**Status:** Confirmed
**Severity:** Medium
**Category:** Database
**Discovered by:** Agent J (Database)

## Location
- `new/server/migrations/versions/` (base `815d10c5bbe4` → `61bacaad00dc` → `2ef6f882b02c` → `7fe333372c71` → head `52c620a620d2`)
- `new/server/app.py` module-level `db.create_all()`; `new/server/add_columns.py` (ad-hoc ALTERs outside Alembic)

## Reproduction
1. Copy `audit/db/snapshot_original.db` → `audit/work/J/mig.db`; `DATABASE_URL=sqlite:///.../mig.db FLASK_APP=app.py`.
2. `flask db current` → `7fe333372c71`; `flask db heads` → `52c620a620d2 (head)`.
3. `flask db upgrade` → `OperationalError: duplicate column name: uncertainty_pct`.
4. Point `DATABASE_URL` at a non-existent file and run `flask db upgrade` → `OperationalError: duplicate column name: segment`.

## Input
Snapshot DB; empty DB.

## Expected
The DB stamped revision matches its actual schema, and `flask db upgrade` brings any DB to head.

## Actual
- Existing DB: stamped at `7fe333372c71` but already contains the columns that `52c620a620d2` adds (added by `add_columns.py` / create_all), so upgrade aborts.
- Fresh DB: importing `app` runs `db.create_all()` (full current schema) before Alembic runs, and the base revision is an `add_column("segment")` (no initial create-table revision), so upgrade aborts at the first revision.
- Schema diff create_all-fresh vs snapshot: identical columns/FKs/indexes except server defaults (`facilities.equity_share_pct`, 11 `production_data.*` columns have `DEFAULT 0.0/100.0` in the snapshot but none in a fresh DB) — so today's schema is held together by create_all, not migrations.

## Evidence
Commands above, output captured in this audit session; `audit/work/J/schema_diff.py`; repro `audit/repro/BUG-<id>.py`.

## Root Cause
Schema is managed three ways (create_all at import, ad-hoc ALTER scripts / connect hook, Alembic) with no reconciliation; no baseline revision; `add_columns.py` adds columns without stamping.

## Impact
No working migration path: any future column added to a model will not reach existing DBs (create_all never ALTERs existing tables) and cannot be applied via Alembic without manual stamping. Postgres deployments (docker-compose/Render CMD run only `create_all`) will silently miss new columns → runtime `no such column` errors after upgrades. `server_default` drift means raw-SQL inserts behave differently on fresh vs old DBs.

## Affected Components
All deployments (SQLite and Postgres), `migrations/`, `add_columns.py`, `add_indexes.py`, the custom_factors.description connect hook.

## Recommended Fix
Create a baseline revision matching the current models, `flask db stamp head` existing DBs after verifying, remove create_all/ad-hoc ALTERs from import-time code and run `flask db upgrade` in the container entrypoint.


---

# BUG-017 — Intensity with year="all" (default view) pairs each facility's emissions from every year with production from other years; KPI mixes periods

**Status:** Confirmed
**Severity:** High
**Category:** Carbon Intensity
**Discovered by:** Agent E (Carbon-intensity auditor)

## Location
- `new/server/routes/dashboard.py` `_query_intensity_stats` L1682-1683 / L1760-1761 / L1904-1905: with year="all" (or absent) no year filter is applied, and production (L1695) and emissions (L1774) are grouped by **facility only**, not by (facility, year). Intensity is then computed per facility at L2035-2044.
- Client: `new/client/src/pages/DashboardEnhanced.jsx` L104 (`currentYear` defaults to "all") and L343-364 (weighted KPI). `CarbonIntensity.jsx` L37 has the same "all" default.

## Reproduction
1. `GET /api/dashboard/intensity-stats` (no year), as admin, on the snapshot copy.
2. For facility 2 (Fertial), compare `co2_intensity` with Σ emissions / Σ BOE restricted to the years that have production.
3. Run `python audit/repro/BUG-044.py`.

## Input
Facility 2 has production in 2022-2026 only, plus 73,202 tCO2e of Verified emissions in 2020 (a year with no production). Facilities 9 (OHT) and 10 (STAH) have production in 2022-2026 only, plus 2.1e9 t and 1.2e9 t of Verified emissions in 2021.

## Expected
Year-matched (only (facility, year) pairs with production > 0), all years:
- Facility 2: 1.225 kg CO2e/BOE
- Facility 9: 0.0 kg/BOE (it has no verified emissions in its production years)
- Facility 10: 0.0 kg/BOE

## Actual
- Facility 2: 13.61 kg/BOE (11× too high, because the 2020 emissions are divided by 2022-26 production)
- Facility 9: 203,285 kg/BOE; facility 10: 105,601 kg/BOE
- Many facilities with 2026 emissions and only 2025 production are also mixed (fid 46-141).
- The corporate KPI in the default dashboard view becomes 627,530 kg/BOE, which is the "627.53K kg/BOE" on the snapshot. The year-matched value on the same data is 621,561. See Impact for why the rest of the 627K comes from absurd seed records.

## Evidence
`audit/work/E/api3.py` and `exp_all.py`:
```
2 Fertial  API int 13.61  prod years [2022..2026] emission yrs w/o prod {2020: 73202.1}
9 OHT      API int 203285.5  prod years [2022..2026] emission yrs w/o prod {2021: 2147516109.6}
10 STAH    API int 105601.4  prod years [2022..2026] emission yrs w/o prod {2021: 1244427746.7}
year-matched: fid2 1.2248, fid9 0.0, fid10 0.0
```

## Root Cause
Intensity must be computed from emissions and production that cover the same period. With year="all" the server aggregates each facility across all years separately for the numerator and the denominator. Emissions from years without production (and years such as 1800 or 2099) enter the numerator but have no denominator. The client then BOE-weights these mixed per-facility ratios.

## Impact
The default dashboard KPI "Performance Intensity" and the Carbon Intensity page, which also default to "All years", show period-inconsistent intensities. For the snapshot KPI of 627.53K kg/BOE: most of the value comes from 7 Verified 2024 "Combustion" records of 5.31e11 tCO2e each, which have quantity NULL and unit MMBtu. Facility 1 (Tosyali) holds one of them against 5.46 M BOE. Those records are bad seed data (or a validation gap) and are reported separately if they are not already. The period mixing adds to that value and independently distorts facility-level results, such as Fertial being 11× too high.

## Affected Components
`/api/dashboard/intensity-stats`, `/api/dashboard/batch-all` (intensity_stats), Dashboard Performance Intensity KPI, CarbonIntensity.jsx facility table and cards, MethaneIntensity.jsx (the same stats with year=all), ModernReportGenerator.js.

## Recommended Fix
For year="all", group production and emissions by (facility_id, year) and include a (facility, year) pair in both the numerator and the denominator only when it has production. Alternatively, do not offer an "all years" intensity and require a single reporting year.


---

# BUG-018 — Uncertainty dashboard applies max(u_CO2, u_CH4, u_N2O) to each record's total CO2e instead of CO2e-weighting the per-gas uncertainties

**Status:** Confirmed
**Severity:** High
**Category:** Uncertainty
**Discovered by:** Agent G (Uncertainty Auditor)

## Location
`new/server/routes/dashboard.py` `_query_uncertainty.get_ef_uncertainty()` (~L2433-2446): `valid_u = [u_co2,u_ch4,u_n2o]` → `return max(valid_u)`. The result is applied to `co2e_total`.

## Reproduction
1. As admin, POST one `stationary_combustion` / Natural Gas / 12000 m3 / factor_source=default record for year 2043.
2. GET `/api/dashboard/uncertainty?year=2043`.
Script: `audit/repro/<ID>.py`.

## Input
The stored record uncertainties (1σ) are CO2 0.0559, CH4 0.1118 and N2O 0.1118. CO2 makes up 99.897 % of the record's CO2e.

## Expected
Weight the per-gas uncertainty by each gas's CO2e contribution. Activity data (±10 % @95 %) is common to all gases. The EFs are CO2 ±5 %, CH4 ±20 % and N2O ±20 % (95 %). Hand calculation: U95 = 2·√((0.05·E)² + Σ(u_EF,g·E_g)²)/E = **±11.18 %**.

## Actual
The dashboard shows **±22.36 %**. This is 2× the expected value: the CH4 value of 0.1118 was applied to 100 % of the CO2e. Each top contributor is also labelled ±22.4 %.

## Evidence
The repro prints the expected and actual values. In the snapshot DB, 110 rows store (0.05, 0.20, 0.20). For those rows the CO2-dominated CO2e is assigned a 1σ of 0.20 instead of about 0.05, which is a 4× overstatement.

## Root Cause
The gases are aggregated without CO2e weighting. The docstring says "use max of those (conservative)". That is not IPCC Approach 1 propagation.

## Impact
Category and inventory uncertainty are overstated by 2 to 4× for every combustion and flaring category whose CH4 and N2O uncertainty exceeds its CO2 uncertainty. This is almost all of them. Categories are pushed into the "medium"/"high" level and the tier breakdown is distorted, because tier classification uses the same inflated `u`. The same inflated number appears on the Uncertainty page, in its CSV export and in the PDF report.

## Affected Components
`/api/dashboard/uncertainty` (JSON + CSV), `UncertaintyAssessment.jsx` (badge, levels, tier cards), `ModernReportGenerator.js`.

## Recommended Fix
Per record: u_rec = √((u_AD·E)² + Σ_g (u_EF,g · GWP_g · m_g)²) / E. At minimum use Σ_g u_g·E_g,CO2e combined in quadrature, not the max. This requires the per-gas CO2e amounts, which are already stored as co2/ch4/n2o_emissions.


---

# BUG-019 — SBTi "Scope 1+2 (Operational)" view compares Scope 1+2 actuals to the Scope 1+2+3 baseline and target line (inflated reduction %, false ON TRACK)

**Status:** Confirmed
**Severity:** High
**Category:** SBTi
**Discovered by:** Agent H (SBTi Auditor)

## Location
`new/server/routes/dashboard.py` `get_sbti_trajectory()` (~2764-2843): `sbti_target`, `current_target`, `reduction_achieved_pct`, `on_track` always use `target.base_year_emissions`, whatever `scope` is. `new/server/routes/managedata.py` `manage_sbti()` GET builds the auto-fill baseline as S1+S2+S3; `SbtiTarget` (models.py:583) has no scope-coverage field. UI: `SbtiDashboard.jsx` scope toggle "Scope 1+2 (Operational)".

## Reproduction
1. `python C:/Users/samsung/Desktop/H2/audit/repro/<BUG-ID>.py`
2. Base year 2020 Verified: S1 700, S2 100, S3 200 (total 1000; S1+S2 800). 2023: S1 650, S2 100, S3 200.
3. Save target via the page's Auto-Fill (1000 t = S1+S2+S3), 4.2 %/yr, 2030.
4. `GET /api/dashboard/sbti-trajectory?scope=s1_s2` (the page's "Scope 1+2" button) and `?scope=s3`.

## Input
Target `{base_year:2020, base_year_emissions:1000, target_year:2030, reduction_rate_pct:4.2}`.

## Expected
Scope 1+2 view: baseline 800 t, 2023 target 800×(1−0.042×3)=699.2 t, actual 750 t → reduction 6.25 %, BEHIND TARGET. S3 view: baseline 200, target 174.8, actual 200 → 0 %, behind.

## Actual
s1_s2: `current_target=874, reduction_achieved_pct=25.0, on_track=true`. s3: `current_target=874, reduction_achieved_pct=80.0, on_track=true`. The chart's "Corporate Target" line and the milestone table "SBTi Target / Variance / Compliance Status" columns likewise compare the S1+S2 actual against the all-scope pathway, so every year looks "Achieved".

## Evidence
Code: `reduction_achieved_pct = (target.base_year_emissions - current_actual)/target.base_year_emissions*100` with `current_actual` = S1+S2 when scope=s1_s2. Baseline auto-fill (`managedata.py` GET) sums S1+S2+S3. The reduction shown is simply the Scope 3 share of the baseline plus the real reduction.

## Root Cause
A single all-scope baseline/target is reused for scope-subset actuals; no per-scope baseline (the per-scope base-year totals are available from the same queries at `base_year`).

## Impact
Every organisation with Scope 3 in its baseline sees an overstated operational reduction and a false ON TRACK when toggling to Scope 1+2. SBTi requires separate S1+2 and S3 targets, so this view is the one users would rely on for the S1+2 near-term target.

## Affected Components
`/api/dashboard/sbti-trajectory?scope=s1_s2|s3`; `SbtiDashboard.jsx` KPI cards, trajectory chart, milestone table, CSV export (Status column).

## Recommended Fix
Store scope coverage with the target (or per-scope baselines) and, for scope subsets, compute baseline = scope-subset base-year actual (or the stored per-scope baseline) and derive the target line / reduction % / on_track from it.


### Additional confirmation (BUG-007)

Independently confirmed by Agent E (Carbon-intensity auditor). This bug explains most of the dashboard's "Performance Intensity 627.53K kg/BOE" on the snapshot.
- With year=all, `/api/dashboard/batch-all` `intensity_stats` BOE-weighted KPI = 627,530.40 kg/BOE (Σ BOE 854.55 M). Facility 1 (Tosyali) alone reports co2_intensity 97,655,260 kg/BOE, because its Verified total of 5.33e11 t includes test row 645 (5.31e11 t). Its 5.46 M BOE carries 5.33e14 kg / 854.55e6 BOE ≈ 623,500 kg/BOE of the corporate KPI. The other six test rows sit at facilities with no production and are excluded from the ratio.
- year=2024: KPI = 2,989,929 kg/BOE (facility 1: 434.8 M kg/BOE). Without the test rows, 2022/2023/2025 give 14.01 / 13.31 / 10.86 kg/BOE, which is plausible for upstream O&G.
- The rest of the distortion in the default year=all view comes from period mixing (filed as BUG-017).
Additional affected components: DashboardEnhanced "Performance Intensity" KPI and YoY badge, CarbonIntensity.jsx, the MethaneIntensity CH4 intensity for facility 1, and the report generator intensity pages.


---

# BUG-020 — /api/reports/master-annual-report serves full annual GHG report PDFs to any logged-in role (incl. it_admin and out-of-region users) and returns a static, pre-generated file regardless of facility_id

**Status:** Confirmed
**Severity:** High
**Category:** Security
**Discovered by:** Agent I (Backend/API/Security)

## Location
`new/server/routes/reports.py:454-482` `get_master_annual_report()` — only `@login_required`; no role check, no `get_allowed_facility_ids` / `require_facility_access`.

## Reproduction
1. Log in as `audit_user@audit.local` (role user, West; allowed facility ids 1,2,158,160,168...) or `audit_itadmin@audit.local`.
2. `GET /api/reports/master-annual-report?facility_id=170` and `GET /api/reports/master-annual-report`.
Script: `audit/repro/<BUG-ID>.py`.

## Input
facility_id=170 (El Merk, region "El Merk", outside West) and no facility_id (consolidated).

## Expected
403 for it_admin (IT roles have zero business-data access, cf. `get_allowed_facility_ids` → []) and for a West user requesting El Merk / consolidated data. The report should also reflect the requested facility and the current database.

## Actual
All four requests return 200 `application/pdf` (1,901,139 bytes El Merk report; 1,912,094 bytes Groupement Berkine report). Additionally:
- Any `facility_id` other than 170/"elm" (e.g. a West facility the user owns) returns the *Groupement Berkine* report — a different facility's data.
- The PDF is read from a hard-coded absolute path `c:/Users/samsung/Desktop/H2/*.pdf` and only regenerated if missing, so the numbers are frozen at the time the file was generated (files dated 2026-09-24), not the current DB; on any other host/path it would try to generate into the developer's desktop path.

## Evidence
```
user: 170 in scope=False; GET ...?facility_id=170 -> 200 application/pdf 1901139 bytes
user: GET ... (no facility) -> 200 application/pdf 1912094 bytes
it_admin: ... -> 200 application/pdf 1901139 bytes / 1912094 bytes
```

## Root Cause
Demo endpoint wired to static files with no authorization or facility scoping.

## Impact
Cross-region data exposure of full annual GHG/CAP reports (emissions, production, compliance) to any authenticated user and to IT administrators; logically wrong report content for any facility other than El Merk; stale figures.

## Affected Components
`/api/reports/master-annual-report`; client report download UI that calls it.

## Recommended Fix
Require business role + `require_facility_access(user, facility_id)` (and unrestricted access for the consolidated report); generate from current DB per request (or cache keyed by facility/DB version) instead of a hard-coded desktop path; 404 for unsupported facility ids.


---

# BUG-021 — Reports search keeps the current page number: "Total Records: 42 | Showing: 0" and no pager to recover

**Status:** Confirmed
**Severity:** Medium
**Category:** UI
**Discovered by:** Agent K (Frontend/UI)

## Location
`new/client/src/pages/Reports.jsx` — the filter-change effect (≈lines 99-145). `searchTerm` is in the dependency array but is not part of `prevFiltersRef`/`filterChanged`, so a search change never resets `page` to 1.

## Reproduction
1. Log in as audit_admin (:5191), /reports, set Year = All (809 records, 17 pages).
2. Click Next → "Page 2 of 17".
3. Type "Flaring" in the Search box.

## Input
page = 2, search = "Flaring" (42 matches, 1 page).

## Expected
Request with `page=1&search=Flaring`; table shows the first 42 matches.

## Actual
Request `GET /api/emissions?page=2&per_page=50&scope=all&search=Flaring` → `{total: 42, pages: 1, emissions: []}`. The page shows "Total Records: 42 | Showing: 0" and "No emission records found. Adjust your filters…". The pager is not rendered when the list is empty, so there is no way back to page 1 other than clearing the search.

## Evidence
`audit/work/K/t_reports4.mjs` output:
```
Page 2 of 17 (809 records)
search reqs: ['/api/emissions?page=2&per_page=50&scope=all&search=Flaring']
last resp total 42 pages 1 len 0
Total Records: 42 | Showing: 0
no pager
```
Repro: `audit/repro/BUG-<id>.mjs`.

## Root Cause
`searchTerm` omitted from the "filter changed → reset page" comparison. (Also: no debounce, one request per keystroke.)

## Impact
Users searching from any page other than 1 are told no matching records exist when they do.

## Affected Components
Reports "Emission Database" table search.

## Recommended Fix
Include `searchTerm` in `prevFiltersRef`/`filterChanged` (and debounce the input); also clamp `page` to `pages` when the response has `page > pages`.


---

# BUG-022 — Reports "Group By" selector has no effect (getGroupedData is never called)

**Status:** Confirmed
**Severity:** Low
**Category:** UI
**Discovered by:** Agent K (Frontend/UI)

## Location
`new/client/src/pages/Reports.jsx` — `getGroupedData()` (≈line 352) is defined but never referenced; the grid renders `emissions.map(...)` directly.

## Reproduction
1. /reports as admin, Year = All.
2. Change "No Grouping" to "By Facility" (or process / month / scope).

## Input
groupBy = "facility"

## Expected
Rows grouped by facility (with group headers) as the control promises.

## Actual
DOM rows identical before/after (50 rows, same order). Playwright: `groupBy changes DOM: false`.

## Evidence
`audit/work/K/t_reports4.mjs`; `grep -n getGroupedData Reports.jsx` → only the definition.

## Root Cause
Grouping logic not wired to the render.

## Impact
Control is a no-op; users may believe they are looking at grouped data.

## Affected Components
Reports page table.

## Recommended Fix
Render from `getGroupedData()` with group headers/subtotals, or remove the control.


### Additional confirmation (BUG-019)

Independently confirmed by Agent H (SBTi Auditor) — same root cause (single corporate baseline reused against a subset of actuals), second affected dimension: **region / facility scoping**.

- Regional users (role `user`/`superuser`, location West) automatically get `allowed_fids` filtering of the actuals in `/api/dashboard/sbti-trajectory`, but `base_year_emissions`, the target line and `reduction_achieved_pct` stay corporate-wide.
- Controlled data (repro scenario of this bug, `audit/repro/_H_scenario.py`): corporate 2020 = 1000 t, West 2020 = 500 t, West 2023 = 450 t. West user gets `current_actual=450, current_target=874, reduction_achieved_pct=55.0, on_track=true`; expected (West baseline 500, 4.2 %/yr) target 437, reduction 10 %, **behind**. The base year row itself shows actual 500 vs target 1000 → "Achieved", -500 t variance.
- `?facility_id=<id>` (admin) behaves the same way.
- Additional affected components: SbtiDashboard.jsx for every region-restricted login; DashboardEnhanced.jsx SBTi banner for region-restricted users.


---

# BUG-023 — Tier 3 combustion/flaring gas composition: each component is converted percent→fraction on its own, so mol% values ≤ 1 (e.g. C4 = 1.0 %, C5 = 0.5 %) become 100 % / 50 %; CO2 inflated 2.7× on the app's own template sample

**Status:** Confirmed
**Severity:** High
**Category:** Calculation
**Discovered by:** Agent A (Calculation Engine Auditor)

## Location
- `new/server/calculations/dispatcher.py` `dispatch()`, Tier 3 combustion and flaring branches. The nested `safe_frac(key)` returns `num / 100.0 if num > 1.0 else num` **per component**.
- `new/server/calculations/combustion.py` `CombustionCalculator.calculate` / `FlaringCalculator.calculate`. The `total_raw > 1.5` check then divides everything by 100 again when the (already mixed) sum exceeds 1.5.

## Reproduction
1. `POST /api/emissions/` with `process_type=combustion, factor_source=specific, fuel="Natural Gas", amount=50000, unit=scf, hhv=1010, combustion_efficiency=0.993, c1=87.5, c2=5.2, c3=2.1, c4=1.0, c5=0.5, co2_mol=1.8, n2_mol=1.9`. This is the exact composition in the "Tier 3 – Natural Gas Combustion" sample row of the app's own CSV template (`routes/emissions.py` `_row(... c1="87.5" ... c5="0.5" ...)`). The template documents c1..c10 as "0–100 mol%".
2. Read back `co2_emissions`.
3. Repro: `audit/repro/BUG-044.py`

## Input
50,000 scf (1,415.84 m³ at 60 °F / 14.696 psia), η_c = 0.993. Composition in mol%: C1 87.5, C2 5.2, C3 2.1, C4 1.0, C5 0.5, CO2 1.8, N2 1.9 (sum 100).

## Expected
Carbon number Σ(xᵢ·nᵢ) = 0.875 + 2(0.052) + 3(0.021) + 4(0.010) + 5(0.005) = 1.107 mol C / mol gas.
CO2 = 1415.84 × (1.107 × 0.993 + 0.018) × 1.861 kg/m³ = **2.944 t CO2**. CH4 slip = 1415.84 × 0.875 × 0.007 × 0.6785 = **0.00588 t**. CO2e (AR5) ≈ **3.11 t**.

## Actual
`co2_emissions = 8.021 t`, `ch4_emissions = 0.002386 t`, `co2e_total = 8.089 t` (**2.6× too high**; CH4 2.5× too low).
With the same composition entered as fractions (0.875, 0.052, …) the result is 3.001 t CO2. The remaining +1.9 % error is a separate issue: N2 is left out of the normalisation sum.

## Evidence
`agentA.db` rows: mol% → `co2 8.021332635535375, ch4 0.00238604024792409, co2e 8.08948001247725`; fractions → `co2 3.0008411745485595`.
Trace: safe_frac gives c1 .875, c2 .052, c3 .021, **c4 1.0**, **c5 0.5**, co2 .018 → total_raw 2.471 > 1.5 → everything /100 and renormalised by 0.02471. That leaves C4 = 40 % and C5 = 20 % of the gas.

## Root Cause
Percent-vs-fraction detection is done per value (`> 1.0`) and not per composition. Any component whose mol% is ≤ 1 is misread as a fraction. The calculator then applies a second heuristic on the mixed sum.

## Impact
Every Tier 3 combustion or flaring entry, whether through the API or bulk import, with any minor component between 0 and 1 mol% gets a wrong carbon balance. That describes most real gas analyses (C4–C10, CO2 often < 1 %). CO2 is overstated by up to several times and CH4 slip is wrong. The app's own sample row is affected.

## Affected Components
dispatcher Tier 3 combustion and flaring branches; `CombustionCalculator`, `FlaringCalculator`; CSV/Excel bulk import of `c1..c10, co2_mol, n2_mol`.

## Recommended Fix
Decide the basis once for the whole composition (e.g. the documented mol% basis, or sum > 1.5 ⇒ percent) and apply it to every component, including CO2 and N2. Do not scale components individually.


---

# BUG-024 — Tier 3 flaring/combustion renormalises the gas composition without N2 (and without unspecified components), inflating CH4 and CO2 by 1/(1 − x_inert)

**Status:** Confirmed
**Severity:** Medium
**Category:** Calculation
**Discovered by:** Agent A (Calculation Engine Auditor)

## Location
`new/server/calculations/combustion.py`:
- `FlaringCalculator.calculate`: `total_raw = sum(raw_c.values()) + raw_co2`, then `c_fractions[k] /= total_sum`
- `CombustionCalculator.calculate`: the same block

The dispatcher passes `n2_comp`, but neither calculator reads it.

## Reproduction
1. `POST /api/emissions/` with `process_type=flaring, factor_source=specific, fuel="Natural Gas (Flaring)", amount=1000, unit=m3, c1=90, n2_mol=10` (default elevated flare: η_d 0.98, η_c 0.984).
2. Repro: `audit/repro/BUG-044.py`

## Input
1000 m³ flare gas at standard conditions, 90 mol% CH4 and 10 mol% N2.

## Expected
CH4 = 1000 × 0.90 × (1 − 0.98) × 0.6785 kg/m³ = **0.012213 t**.
CO2 = 1000 × 0.90 × 1 × 0.984 × 1.861 kg/m³ = **1.6481 t**.

## Actual
`ch4_emissions = 0.013570 t`, `co2_emissions = 1.831224 t`. Both are **+11.1 %**: the gas was renormalised to 100 % CH4.

## Evidence
`agentA.db` row: `{'co2_emissions': 1.831224, 'ch4_emissions': 0.013570000000000013, 'calc_method': 'Flaring Dual-Efficiency'}`.
The same effect makes Tier 3 combustion with the template composition (N2 1.9 %) 1.9 % high. The UI sends only `c1` and `co2_content`, so any user-entered CH4 % below 100 is scaled up to fill the missing share (e.g. 85 % CH4 + 2 % CO2 → treated as 97.7 % CH4).

## Root Cause
Normalisation to 1.0 uses only C1–C10 and CO2. N2, H2S and any unspecified components are dropped, and the composition is forced to sum to 1.

## Impact
Flared and combusted CH4 and CO2 are overstated in proportion to the inert/unspecified fraction. The typical range is 2–15 %, and more for high-N2 associated gas.

## Affected Components
`FlaringCalculator`, `CombustionCalculator` (Tier 3); UI Tier 3 flaring (sends only CH4 % and CO2 %); bulk import.

## Recommended Fix
Include N2 (and other inerts) in the sum. Renormalise only when the analysis is complete (sum close to 100 %, within a tolerance). Otherwise use the stated mole fractions as given, and warn.


### Additional confirmation (BUG-015)

Independently confirmed by Agent B (Emissions Auditor), `audit/work/B/t6.py`. Every client API_FACTORS key whose usage is combustion, flaring or venting was POSTed with process_type = that usage. 23 of 54 combos returned 201 with totalCo2e 0 (`server_default`).
- The zeros include all the **flaring** fuels: `Propane (Flaring)`, `Butane (Flaring)`, `Ethylene (Flaring)`, `Propylene (Flaring)`, and Butane/Isobutane/Propylene under flaring.
- **Biogenic** fuels (Ethanol, Biodiesel, Wood) also come out at zero. Their fossil CH4/N2O is lost too, not only the biogenic CO2 that should be reported separately.
- The snapshot's 24 seeded `Butane`/`stationary_combustion` rows carry non-zero co2e only because they were inserted with precomputed values (source_payload has `co2`/`co2e` keys, created_by=1). Re-creating any of them through the API yields 0.


---

# BUG-025 — Meter (activity-data) and GC (composition) uncertainty inputs are accepted but silently ignored by every calculator

**Status:** Confirmed
**Severity:** Medium
**Category:** Uncertainty
**Discovered by:** Agent G (Uncertainty Auditor)

## Location
- `new/server/calculations/dispatcher.py` L242-257 stores `meter_uncertainty_pct` / `gc_uncertainty_pct` as `uncertainties["_activity_uncertainty"]` / `["_composition_uncertainty"]`.
- `calculations/uncertainty.py propagate_uncertainty()` reads them only from its `uncertainties_dict=` argument (L389-393).
- `grep -rn "uncertainties_dict" calculations/` finds **no** caller that passes it. Every `propagate_uncertainty(...)` call in combustion/vented/fugitive/midstream/indirect/stoichiometry/dispatcher omits it.

## Reproduction
1. POST `/api/emissions/` stationary_combustion / Natural Gas / 1000 m3 with no override. Then POST the same with `meter_uncertainty_pct: 40`, and with `meter_uncertainty_pct: 40, gc_uncertainty_pct: 30`.
2. Compare `emissions.uncertainty.co2` in each response.
Script: `audit/repro/<ID>.py`.

## Input
meter 40 % and GC 30 % (95 % half-widths, the same convention the dispatcher uses for `user_uncertainty`).

## Expected
Hand calculation (1σ = U95/2):
- meter 40 %: √(0.025² + 0.20²) = **0.2016**
- meter 40 % + GC 30 %: √(0.025² + 0.20² + 0.15²) = **0.2512**

## Actual
All three records store **0.0559**, the tier default (AD 10 %, EF 5 %). By contrast, `user_uncertainty` does work (50 % gives 0.2550).

## Evidence
Repro output: `expected 0.2016 actual 0.0559`, `expected 0.2512 actual 0.0559`.

## Root Cause
The dispatcher writes the overrides into the `uncertainties` dict. The calculators pass that dict's per-gas entries to `resolve_ef_uncertainty` but never pass the dict itself to `propagate_uncertainty(..., uncertainties_dict=uncertainties)`. As a result, `_activity_uncertainty` and `_composition_uncertainty` are dead.

## Impact
The Scope1Form "specific" mode fields (Meter Uncertainty %, GC Uncertainty %), the bulk-import columns `[Unc] meter_uncertainty_pct` / `gc_uncertainty_pct` (template text: "overrides Tier default"), and the ColumnMappingWizard/BulkImportModal mappings are no-ops. A user who records a poor meter (e.g. ±40 %) still gets the Tier default (±2 % for Tier 3, ±10 % for Tier 1). Their persisted and reported uncertainty is understated with no warning.

## Affected Components
All dispatcher calculators, the Scope1Form specific inputs, bulk import (`background_processor`, `/bulk-upload`), and the stored `emissions.uncertainty*` columns, and through them the Uncertainty dashboard.

## Recommended Fix
Pass `uncertainties_dict=uncertainties` in every `propagate_uncertainty` call, or have the dispatcher apply the overrides centrally after the calculator returns. Add a test asserting that a meter override changes `relative_uncertainty`.


---

# BUG-026 — Flaring panel treats "All Years" as the current calendar year and ignores the Supply-Chain/Activity/Division/Preview-Pending filters, so it contradicts the dashboard it sits in

**Status:** Confirmed
**Severity:** High
**Category:** Dashboard
**Discovered by:** Agent F (Dashboard reconciliation auditor)

## Location
- `new/server/routes/dashboard.py` `get_flaring_summary()` (~L2868-3072): `yr = int(year) if year and year != "all" else datetime.now().year`; it reads only `year` and `facilityId`. `activity`, `division`, `segment`, `includePending` and `gwp_horizon` are sent by the client but ignored.
- `new/client/src/pages/DashboardEnhanced.jsx` ~L262 (`/dashboard/flaring-summary?${filterParams}`), flaring banner ~L1225-1330, Detailed Breakdown sub-rows ~L1640-1665 (Routine / Non-Routine / Safety rows rendered under the all-years "Flaring" row).

## Reproduction
1. `python audit/repro/BUG-NNN.py` (db copy `repro_F`).
2. Or: log in as admin on the dashboard, keep "All Years". Read the "Operational Flaring" banner and the "Detailed Breakdown" table.
3. Select Supply Chain = "Heavy Industry" (only the Tosyali steel plant, which has no flaring) and Year 2025.

## Input
Snapshot DB. Verified flaring records exist for 2021-2026. The only 2026 flaring is two generic `flaring` rows (100,000 m3, 210.22 t).

## Expected
- With "All Years", the panel covers all years, like every other card. Independent SQL: `sum(co2e_total)` of Verified rows whose process_type contains "flar" = **2,199,048.57 tCO2e**. This equals the Detailed Breakdown "Flaring" row (2.2M).
- The Routine + Non-Routine + Safety sub-rows add up to their parent "Flaring" row.
- Segment "Heavy Industry", 2025: 0 flaring (SQL = 0).

## Actual
- `flaring-summary` returns `year: 2026` for "All Years": total 100 kNm3 / **210.2 tCO2e**, and a YoY of -99.92% (2026 vs 2025).
- In the same table, "Flaring = 2.2M" sits above "Routine 0 / Non-Routine 0 / Safety 0". The children add up to 0 and come from another year.
- Supply Chain = Heavy Industry, 2025: the panel still shows **119,346 kNm3 / 306,015 tCO2e** (company-wide Berkine flaring). The Activity and Division filters behave the same way. The Preview-Pending toggle does not change it.

## Evidence
UI (Playwright DOM, `audit/work/F/dash_text.txt`): "TOTAL FLARED VOLUME 100kNm³ 210.2 tCO₂e … -99.92% YoY" next to "Flaring 2.2M ↳ Routine (56%) 0 ↳ Non-Routine (40%) 0 ↳ Safety & Purge (4%) 0".
Repro output:
```
All Years: flaring-summary.year=2026  total_tco2e=210.22  streams sum=0.0
Detailed Breakdown 'Flaring' (batch summary, all years)=2199048.57  independent SQL=2199048.57
segment=Heavy Industry, 2025: flaring-summary total=306015.22 tCO2e, 119346.0 kNm3; expected (SQL)=0.0
```

## Root Cause
`get_flaring_summary` was written as a single-year and single-facility endpoint. It maps "all" to `datetime.now().year` and never reads the other filter parameters. The client renders its result inside the all-years, filtered dashboard with no year label.

## Impact
The headline flaring volume, flaring tCO2e, Decree 21-330 intensity/compliance badge and YoY on the default dashboard view describe only the current, partial calendar year (2026). Every other card shows all years. Under any Supply-Chain, Activity or Division filter the panel still shows company-wide flaring. The compliance verdict ("COMPLIANT 0.003%") is therefore computed on the wrong population.

## Affected Components
`GET /api/dashboard/flaring-summary`; DashboardEnhanced flaring banner, the Detailed Breakdown flaring sub-rows, and the Decree 21-330 intensity bar.

## Recommended Fix
Support `year=all` (sum all years, or show "select a year" for the compliance ratio) and apply `activity/division/segment` through `Facility`, plus `includePending`. Label the panel with the year it actually covers. Do not render stream sub-rows under a parent computed from a different population.


---

# BUG-027 — Tier 1 combustion applies the catalog HHV in the wrong basis when the activity unit is mass or the other phase (diesel/crude per tonne ×3.6, natural gas per tonne ÷40, ethane per scf ×39)

**Status:** Confirmed
**Severity:** High
**Category:** Calculation
**Discovered by:** Agent C (Tier / Factor Auditor)

## Location
- `new/server/calculations/combustion.py` `convert_factor_to_kg_per_unit()`, lines ~84-135 (the `kg/MMBtu` branch).
  - `is_solid_fuel` is set true for any mass activity unit (`a_unit in [tonne, kg, lb ...]`). The fuel's HHV is then read as kBtu/short ton, even for diesel (138000 Btu/gal) or natural gas (1020 Btu/scf).
  - For volume units, liquid/gas is decided by keyword. "propane" and "ethane" are not in the liquid list, so gal-basis HHVs are multiplied by scf (35.3147 per m3).
- `new/server/emission_factors_api2021.py`: `Ethane` is typed `gases`, yet its `hhv` 69600 is Btu/gal.
- The client allows the combination. `CombustionForm.jsx` offers every unit (m3, scf, gal, bbl, L, kg, ton, tonne) for every fuel. In `Scope1Form.jsx`, `convertActivityData()` has no kg/tonne↔gal or scf↔gal pair, so the unit is sent unchanged.

## Reproduction
1. `python audit/repro/BUG-<ID>.py` (own db). It POSTs Tier 1 (`factor_source=default`) combustion records to `/api/emissions/`.

## Input
| Fuel | Quantity |
|---|---|
| Diesel (No. 2 Fuel Oil) | 1 tonne |
| Crude Oil | 1 tonne |
| Natural Gas | 1 tonne |
| Ethane | 1000 scf |
| Propane (Liquid) | 1 m3 (API/bulk path; the UI converts m3→gal for this fuel) |

## Expected (t CO2, independent)
- Diesel 1 t ≈ 3.17 (IPCC 2006 cross-check: 43.0 TJ/Gg × 74,100 kg/TJ = 3.19).
- Crude 1 t ≈ 3.10 (IPCC: 42.3 × 73,300).
- Natural gas 1 t ≈ 2.4–2.7.
- Ethane gas 1000 scf ≈ 1.77 MMBtu × 59.6 = 0.105.
- Propane liquid 1 m3 = 264.17 gal × 0.0915 × 62.88 = 1.52.

## Actual
| Case | Actual (t CO2) | Ratio to expected |
|---|---|---|
| Diesel | 11.25 | 3.55× |
| Crude | 11.34 | 3.66× |
| Natural gas | 0.0597 | 0.025× |
| Ethane | 4.148 | 39.5× (identical to 1000 gal) |
| Propane (Liquid) | 0.203 | 0.13× |

All cases return HTTP 201, with calc_method "Stationary Combustion" and no warning.

## Evidence
Repro output: every case is flagged WRONG. Diesel 1 tonne gives 11.2507 t. 138000/1000 = 138 MMBtu/short ton × 1.10231 × 73.96 kg/MMBtu = 11.25 t. This confirms that the Btu/gal HHV is used as kBtu/short ton.

## Root Cause
The catalog HHV carries no unit. Its basis is implied by `baseUnit` (gal, scf or ton). The converter infers the basis from the activity unit, and from fuel-name keywords, instead of from the factor's basis. It has no density bridge between volume-basis HHV and mass activity.

## Impact
Tier 1 combustion totals are wrong by 3.5× to 40× whenever a liquid or gaseous fuel is reported in kg or tonnes. Mass reporting is common outside the US. The same applies to ethane reported in scf, and to liquid propane in m3 or L via bulk upload/API.

## Affected Components
- Manual Scope 1 entry, bulk upload and recalculation.
- The same function is used for Tier 2 custom factors with kg/MMBtu units.

## Recommended Fix
- Store the HHV unit explicitly (Btu/gal, Btu/scf, MMBtu/short ton).
- Convert activity to the HHV basis using density when crossing mass↔volume, or reject units incompatible with the fuel's basis.
- Fix `Ethane` to a liquid basis, or add a gaseous HHV.


---

# BUG-028 — SBTi dashboard shows "ON TRACK — Reduction: 100% vs Baseline" when there is no verified data at all in the target window

**Status:** Confirmed
**Severity:** Medium
**Category:** SBTi
**Discovered by:** Agent H (SBTi Auditor)

## Location
`new/server/routes/dashboard.py` `get_sbti_trajectory()`: `latest_actual_year = max(candidate_years, default=base_year)`, `current_actual = actuals.get(latest_actual_year, actuals.get(current_year, 0.0))`, `reduction_achieved_pct = (base - current_actual)/base*100`, `on_track = current_actual <= current_target if current_actual > 0 else True`. UI `SbtiDashboard.jsx` "Pathway Status" card (`isOnTrack = sbtiData?.on_track ?? true`).

## Reproduction
1. `python C:/Users/samsung/Desktop/H2/audit/repro/<BUG-ID>.py`
2. Save a target with base year 2024 (baseline 1000 t) where no Verified S1/S2/S3 rows exist for 2024-2030 (same happens for a regional user/facility with no data, or scope=s1_s2 with only S3 data).
3. `GET /api/dashboard/sbti-trajectory`.

## Input
`{base_year:2024, base_year_emissions:1000, target_year:2030, reduction_rate_pct:4.2}`, no actuals in window.

## Expected
Progress not evaluable: reduction % null / "No data", status neither ON TRACK nor BEHIND.

## Actual
`reduction_achieved_pct=100.0, on_track=true, current_actual=0.0` → green "ON TRACK", "Reduction: 100% vs Baseline". Also reproduced with `?facility_id=4` on a facility without data.

## Evidence
See code above: missing data is coerced to 0 t, which the formula turns into a 100 % reduction, and `on_track` is hard-coded `True` when actual is 0.

## Root Cause
Absence of data is represented as 0 emissions and treated as success instead of "not available".

## Impact
A newly configured target (base year = current year before data is verified), or any user whose region has no verified data, sees a false 100 % reduction / ON TRACK headline.

## Affected Components
`/api/dashboard/sbti-trajectory` summary; `SbtiDashboard.jsx` KPI cards.

## Recommended Fix
If no candidate year with data exists (or actual is 0 because no rows exist), return `current_actual=null, reduction_achieved_pct=null, on_track=null`, and render "No data" in the UI.


### Additional confirmation (BUG-015)

Correction (Agent B): the snapshot has 27 (not 24) seeded rows with fuel_type='Butane'.


---

# BUG-029 — Manage Data page crashes for every user when any facility has a NULL name; POST /api/facilities accepts facilities with no name

**Status:** Confirmed
**Severity:** High
**Category:** UI
**Discovered by:** Agent L (Browser)

## Location
- `new/client/src/pages/ManageData.jsx:1306-1307` (`getFilteredFacilities`: `f.name.toLowerCase()` with no null guard)
- `new/server/routes/facilities.py:121-170` (`add_facility`: no required-field validation; `name=data.get("name")`)
- `new/server/models.py:44` (`Facility.name = db.Column(db.String(120))` — nullable)

## Reproduction
1. Log in to the UI (:5190) as any non-IT role (verified: audit_admin, audit_user).
2. Open `/manage-data`.
3. The page renders the ErrorBoundary "Something went wrong" screen; console: `TypeError: Cannot read properties of null (reading 'toLowerCase') at getFilteredFacilities (ManageData.jsx:1362)`.
4. To create the trigger from a clean DB: as admin, `POST /api/facilities` with `{"region":"West"}` → `201 {"id":172,"message":"Facility added"}` and the stored row has `name = NULL`.

## Input
`POST /api/facilities {"region": "West"}` (no name). The audit snapshot already contains 8 facilities with `name IS NULL` (ids 149,151,153,156,159,161,163,166) and 5 with `name = ''`.

## Expected
The API rejects a facility without a name (400), and the page tolerates a missing name instead of crashing.

## Actual
The API returns 201 and stores `name=NULL`. The whole Manage Data page (facilities, production data, emission sources, mitigation tabs) is unusable for every user while such a row exists. The snapshot DB already has such rows, so in the audited state Manage Data is always broken.

## Evidence
- Playwright run `audit/work/L/w_md_crash.mjs`: `POST /api/facilities {region:West} -> 201 {"id":172}`, `user manage-data crashed: true`; screenshot `audit/work/L/md_crash_user.png`.
- `select id,name from facilities where name is null` → 8 rows in `snapshot_original.db`.

## Root Cause
The server has no required-field validation for facility name (and the column is nullable). The client assumes `f.name` is always a string (`f.name.toLowerCase()`), while it guards `f.location?.` and `f.field?.` on the same line.

## Impact
A core data-management workflow is blocked: users cannot create or edit facilities, production data (carbon-intensity denominators) or emission sources through the UI. Any admin/superuser (or a bulk import) can cause this with one blank facility.

## Affected Components
ManageData page (all tabs); `POST /api/facilities`; probably also the bulk facility import path (not verified separately).

## Recommended Fix
Require a non-empty `name` in `add_facility`/update (and bulk import), make `Facility.name` NOT NULL after cleaning the data, and use `(f.name || '').toLowerCase()` in `getFilteredFacilities`.


---

# BUG-030 — POST /api/emissions/ calculates from `quantity`/`fuel_type` but stores only `amount`/`fuel`: records keep emissions with NULL activity quantity and fuel

**Status:** Confirmed
**Severity:** Medium
**Category:** Emissions
**Discovered by:** Agent B (Emissions Auditor)

## Location
`new/server/routes/emissions.py` `add_emission()`:
- the validation block checks `data["quantity"]`;
- `_lookup_api_factor(data.get("fuel") or data.get("fuel_type"))`;
- `compute_emissions` reads `amount` or `quantity` (`legacy_engine.py:395`).

But the ORM row is built with `fuel_type=data.get("fuel")` and `quantity=data.get("amount")` (~L3165-3166).

## Reproduction
1. As admin, `POST /api/emissions/` with `{"process_type":"Combustion","source_type":"Combustion","facility_id":1,"year":2024,"month":7,"fuel_type":"Coal","quantity":1000,"unit":"tonnes"}`. These are the column names of the model and of the PUT endpoint.
2. `select fuel_type, quantity, co2e_total from emissions where id=<new id>`.

## Input
1000 t coal.

## Expected
`fuel_type='Coal'`, `quantity=1000`, co2e = 2582.96 t. Hand check: 1000 t x 1.10231 st/t x 24.93 MMBtu/st x 93.28 kg/MMBtu = 2563.4 t CO2, plus CH4/N2O.

## Actual
co2e_total = 2582.96 t (correct), but `fuel_type=NULL` and `quantity=NULL` (row id 752 in agentB db). Sending the same payload with `fuel`/`amount` stores both fields.

## Evidence
`audit/work/B/t1.py`:
```
{'id': 752, 'process_type': 'Combustion', 'fuel_type': None, 'quantity': None, 'unit': 'tonnes', ... 'co2e_total': 2582.9554554936003, 'status': 'Verified'}
{'id': 753, ... 'fuel_type': 'Coal', 'quantity': 1000.0, ... 'co2e_total': 2582.9554554936003}
```
The snapshot's nine giant test rows (ids 640-675, see BUG-007) have exactly this signature: `quantity`/`fuel_type` NULL in the columns, but `source_payload` has `"fuel_type":"Natural Gas","quantity":9999999999999`. The absurd input is therefore invisible in the emissions grid, exports and the audit log line ("Added Combustion emission: None tonnes of None").

## Root Cause
Key-name mismatch between the fields used for the calculation (either alias accepted) and the fields persisted (only `amount`/`fuel`).

## Impact
Verified emissions with no stored activity data or fuel. Reviewers cannot see or verify what was entered, activity-based QA and outlier checks cannot see the quantity, and fuel-level breakdowns and exports drop these rows into "blank".

## Affected Components
POST /api/emissions/ (any API/integration client and any form that sends `fuel_type`/`quantity` only), emissions list/export, the activity log, and BUG-007 detection.

## Recommended Fix
Persist `fuel_type=data.get("fuel") or data.get("fuel_type")` and `quantity=` the same parsed `amount`/`quantity` value that `compute_emissions` used.


---

# BUG-031 — Facility OGMP 2.0 level counts Draft, Pending and Rejected emission records, so a rejected record can raise a facility's level

**Status:** Confirmed
**Severity:** Medium
**Category:** Methane
**Discovered by:** Agent D (Methane Auditor)

## Location
`new/server/services/ogmp.py` `compute_facility_ogmp_level()`, ~lines 88-97:
```python
q = Emission.query.filter_by(facility_id=facility.id)
if year ...: q = q.filter_by(year=int(year))
records = q.all()
bottom_up_level = max((ogmp_level_for(r) for r in records), default=2)
```
No `status == "Verified"` filter. Callers: `/api/dashboard/ogmp-metrics` (`highest_ogmp_level`, shown on MethaneIntensity OGMP roadmap) and `/api/reports/ogmp-export` (Excel "Current Level" column).

## Reproduction
1. Fresh DB copy. Facility 169, year 2025 has 7 Verified records, all `ogmp_level` 3 (772.46 tCH4).
2. `GET /api/dashboard/ogmp-metrics?year=2025&facilityId=169` returns `highest_ogmp_level` = 3.
3. Add one **Rejected** record for the same facility/year with `factor_source='specific'`, `ogmp_level=4`, CH4 0.001 t. The admin reject flow sets `status="Rejected"`, `routes/emissions.py:4541`.
4. Clear the cache and call again: `highest_ogmp_level` = **4**.

## Input
One rejected 0.001 tCH4 Tier-3 record next to 772 t of Verified Level-3 inventory.

## Expected
Only Verified records form the reported bottom-up inventory. The same Verified filter is already applied to the CH4 totals in the same endpoint. Level should stay 3.

## Actual
Level 4. In the same way, a Draft/Pending/Rejected Tier-3 record also removes the "bottom-up must be L4" cap on Level 5 (Gold Standard), which the code itself describes as mandatory.

## Evidence
`audit/work/D/s5.py` output: `before 3` → `after adding one REJECTED 0.001 t specific record: 4`. Repro: `audit/repro/<ID>.py`.

## Root Cause
The record query in `compute_facility_ogmp_level` lacks the status filter. It also takes the **max** level over records rather than the level of the material share of emissions. For example, facility 13 (2026) has 236.6 t of its 338.9 tCH4 at Level 2 and is still reported as Level 4.

## Impact
OGMP 2.0 levels and Gold-Standard status on the dashboard OGMP roadmap and in the regulator-facing OGMP Excel export can be overstated by unapproved or rejected data.

## Affected Components
services/ogmp.py, /api/dashboard/ogmp-metrics, /api/reports/ogmp-export (Summary sheet), MethaneIntensity.jsx OGMP roadmap table.

## Recommended Fix
Filter `Emission.status == "Verified"`. Derive the facility bottom-up level from the emission-weighted (materiality) share at L4, not the maximum over any single record.


---

# BUG-032 — GET /api/manage/sbti ignores facility/region scoping: region-restricted users can read organisation-wide Verified emission totals for any year

**Status:** Confirmed
**Severity:** Medium
**Category:** Security
**Discovered by:** Agent H (SBTi Auditor)

## Location
`new/server/routes/managedata.py` `manage_sbti()` GET branch (~lines 996-1033): `Emission.query.filter_by(status="Verified", year=calc_year)` (and Scope2/Scope3) without `get_allowed_facility_ids(user)`.

## Reproduction
1. `python C:/Users/samsung/Desktop/H2/audit/repro/<BUG-ID>.py`
2. Log in as `audit_user@audit.local` (role user, location West).
3. `GET /api/manage/sbti?base_year=2023` (any year 2015-9999 can be queried).

## Input
Controlled data: 2023 Verified West (facility 1) S1 350 + S2 100 = 450 t; Center (facility 3) S1 300 + S3 200 = 500 t.

## Expected
Either scoped to the caller's allowed facilities (450 t) or forbidden for non-admin roles — the sibling endpoint `/api/dashboard/sbti-trajectory` does apply `allowed_fids`.

## Actual
`suggested_base_year_emissions = 950.0` (includes the Center facility the user cannot access). Looping `base_year` over years yields the full org-wide annual total series.

## Evidence
Response above; code has no `allowed_fids` filter in the GET branch.

## Root Cause
Missing `get_allowed_facility_ids` scoping in the baseline suggestion query.

## Impact
Aggregate cross-region disclosure (org-wide yearly S1+S2+S3 totals) to region-restricted users. Limited to aggregate totals (no record detail), hence Medium.

## Affected Components
`/api/manage/sbti` and `/api/sbti` GET; SbtiDashboard "Auto-Fill Verified" and ManageData SBTi tab.

## Recommended Fix
Apply `allowed_fids` to the three queries (or restrict the suggestion to admins), consistent with `/dashboard/sbti-trajectory`.


---

# BUG-033 — Decree 21-330 flaring intensity (/flaring-summary) misconverts units: MMscf 1000× too low, scf/kscf 35× too high, UI "m³" gas production 28× too high; compliance verdict flips

**Status:** Confirmed
**Severity:** High
**Category:** Carbon Intensity
**Discovered by:** Agent E (Carbon-intensity auditor)

## Location
`new/server/routes/dashboard.py` `get_flaring_summary`:
- Numerator (flared volume) L2923-2931: `if "k" in unit ... elif "mscf" in unit: *28.3168 elif "mmscf" in unit: *28316.8 else: m3`
  - "mmscf" contains "mscf", so the MMscf branch is unreachable and 1 MMscf becomes 28.3 m3.
  - "kscf" matches `"k" in unit`, so it becomes qty×1000 m3 (1 kscf is 28.3 m3).
  - "scf" falls to the else branch and is treated as m3 (1 scf is 0.0283 m3). Any other unit containing "k" (e.g. "kg") is also treated as thousands of m3.
- Denominator (gas produced) L2986-2993: `elif "m3" in unit` does not match the client's gas unit value `"m³"` (ManageData.jsx L2701 `<option value="m³">`), so m³ volumes fall to the else branch and are multiplied by 28.3168 as if they were mscf.
- Prior-year YoY path L3020-3023 uses a third, different rule: only `"k" in unit`, and no mscf/mmscf conversion.
By contrast, `_query_intensity_stats` L1726-1736 handles "m³" and mmscf correctly, so the two endpoints disagree on the same data.

## Reproduction
1. Run `python audit/repro/BUG-044.py` (own db copy). As admin, it sends `POST /api/emissions/` three times: flaring at facility 13, 2026, with 1 mmscf, 1,000,000 scf and 1,000 kscf (each is 28,316.8 m3). The flaring engine accepts all three units (`dispatcher._normalize_volume`).
2. It then sends `POST /api/data/production` with facility 13, 2026-07, gas 1,000,000 with gas_unit "m³" (what the Manage Data form sends).
3. Each step is followed by `GET /api/dashboard/flaring-summary?year=2026&facilityId=13`.

## Input
The records above. Baseline: facility 13 in 2026 has 100,000 m3 flared and 134,733,458 m3 of gas produced.

## Expected
- Each flaring record adds +28,316.8 m3. Total flared = 184,950 m3.
- Gas produced increases by 1,000,000 m3, to 135,733,458 m3.
- Flaring intensity = 0.136%, "COMPLIANT (Under 1.00% Target)".

## Actual
- mmscf: +28.32 m3 (1000× too low)
- scf: +1,000,000 m3 (35.3× too high)
- kscf: +1,000,000 m3 (35.3× too high)
- Production in m³: +28,316,800 m3 to the denominator (28.3× too high)
- Final: `flaring_intensity_pct` 1.288, "EXCEEDS THRESHOLD (> 1.00%)"

## Evidence
`audit/work/E/repro_flare.py` output:
```
flared 1 mmscf: expected +28316.8 m3, actual +28.32 m3 MISMATCH
flared 1000000 scf: expected +28316.8 m3, actual +1000000.00 m3 MISMATCH
flared 1000 kscf: expected +28316.8 m3, actual +1000000.00 m3 MISMATCH
produced 1,000,000 m³ gas: expected +1,000,000 m3 denominator, actual +28,316,800 MISMATCH
final flaring_intensity_pct 1.288 EXCEEDS THRESHOLD (> 1.00%)
```
For the same m³ production row, `/intensity-stats` reports `total_gas_m3` +1,000,000, which is correct.

## Root Cause
Unit detection uses substring tests in the wrong order ("mscf" is checked before "mmscf", and any "k" means kilo-m3). It has no scf branch and does not recognise the "m³" spelling that the client stores. Three separate ad-hoc conversion tables exist, for the flaring-summary numerator, the denominator and the prior year.

## Impact
The regulatory Decree 21-330 Art. 9 flaring-intensity KPI on the Dashboard (DashboardEnhanced L1328-1345) and in the PDF report (ModernReportGenerator `/flaring-summary`) can be wrong by 1000× in either direction. The compliant or non-compliant verdict and the YoY change can be wrong. The volume shown per stream (routine, non-routine, safety) is wrong as well.

## Affected Components
`/api/dashboard/flaring-summary`, DashboardEnhanced "Decree 21-330 Flaring Intensity" bar and badge, ModernReportGenerator flaring section.

## Recommended Fix
Use one shared exact-match unit normaliser, e.g. `calculations/units.py`, for flared volume, produced gas and prior year. Match exact tokens (m3, m³, sm3, knm3, scf, mscf/mcf, mmscf, kscf). Reject or flag unknown units instead of defaulting to m3 or mscf.


---

# BUG-034 — SBTi target POST accepts NaN / Infinity (range checks pass for non-finite floats); trajectory endpoint then returns 500 or invalid JSON for all users

**Status:** Confirmed
**Severity:** Medium
**Category:** SBTi
**Discovered by:** Agent H (SBTi Auditor)

## Location
`new/server/routes/managedata.py` `manage_sbti()` POST validation (~1040-1057); `new/server/routes/dashboard.py` `get_sbti_trajectory()` line 2764 `rate = target.reduction_rate_pct / 100.0`.

## Reproduction
1. `python C:/Users/samsung/Desktop/H2/audit/repro/<BUG-ID>.py`
2. As admin: `POST /api/manage/sbti` body `{"base_year":2020,"base_year_emissions":1000,"target_year":2030,"reduction_rate_pct":NaN}` → 201.
3. `GET /api/dashboard/sbti-trajectory` → 500 (`TypeError: unsupported operand type(s) for /: 'NoneType' and 'float'`; SQLite stores NaN as NULL).
4. POST `base_year_emissions: Infinity` → 201; trajectory → 200 with body containing bare `Infinity`/`NaN` tokens (not valid JSON; browsers' JSON.parse rejects it).
5. `base_year_emissions: NaN` → 400 but with the raw SQLAlchemy IntegrityError text (SQL statement and parameters) in the response.

## Input
Non-finite JSON numbers (Python's json parser accepts `NaN`, `Infinity`).

## Expected
400 "must be a finite number". Checks such as `reduction_rate_pct <= 0 or > 25` are all False for NaN, so they do not reject it.

## Actual
Stored; the latest target is used by `/sbti-trajectory`, so the SBTi page and the main dashboard SBTi banner break for every user until another target is posted (there is no delete/edit endpoint).

## Evidence
Repro output: `rate NaN: POST 201; trajectory GET 500` / `baseline Infinity: POST 201; trajectory GET 200 INVALID JSON (Infinity)`.

## Root Cause
No `math.isfinite` check; range comparisons against NaN are always False.

## Impact
One API call (admin/superuser) disables SBTi tracking platform-wide; error text leaks SQL. The UI form itself cannot produce NaN (parseFloat || 0), so it is an API-level validation gap.

## Affected Components
`/api/manage/sbti`, `/api/sbti` POST; `/api/dashboard/sbti-trajectory`; SbtiDashboard.jsx; DashboardEnhanced.jsx SBTi banner.

## Recommended Fix
Reject non-finite values (`math.isfinite`) for all numeric fields; return generic errors instead of `str(e)`; guard `reduction_rate_pct is None` in the trajectory.


---

# BUG-035 — Flaring-summary volume conversion: "mmscf" hits the "mscf" branch (1000× understated), "scf" is read as m³, and the prior-year path uses a different, cruder conversion (YoY +2,732 % for identical volumes)

**Status:** Confirmed
**Severity:** Medium
**Category:** Dashboard
**Discovered by:** Agent F (Dashboard reconciliation auditor)

## Location
`new/server/routes/dashboard.py` `get_flaring_summary()`:
- Current-year conversion (~L2920-2928): `if "k" in unit … elif "mscf" in unit: ×28.3168 elif "mmscf" in unit: ×28316.8 else: qty`. The `mmscf` branch can never run, because "mmscf" contains "mscf".
- Prior-year conversion (~L3005-3008): `prev_total_m3 += p_qty * 1000.0 if "k" in p_u else p_qty`. mscf, mmscf and scf are all taken as m3.

## Reproduction
1. `python audit/repro/BUG-NNN.py`. It uses its own db copy `repro_F3` and inserts one Verified `routine_flaring` row of 1 mmscf in 2030 and one in 2031 at facility 169.
2. It then calls `GET /api/dashboard/flaring-summary?year=2031&facilityId=169`.

## Input
1.0 mmscf routine flaring in each of 2030 and 2031.

## Expected
1 MMscf = 10^6 ft3 × 0.0283168 m3/ft3 = **28,316.8 m3** (28.3 kNm3). With the same volume in both years, YoY = **0 %**.

## Actual
`routine_flaring.volume_m3 = 28.32` (1000× low) and `yoy_change_pct = 2731.68`. The prior year is read as 1 m3.
The snapshot data hits the same paths: a Pending `flaring` row of 1,000,000 **scf** would be counted as 1,000,000 m3 (35.3× high). Verified `flaring` rows in **mscf** (2025) are converted correctly in the current year but taken as m3 when 2025 is the prior year.
Also, `process_type` is matched with an exact, case-sensitive `IN ('routine_flaring',…,'flaring','flare')`. The Verified row id with `process_type='Flaring'` (2024, unit MMBtu) is therefore left out of the panel, but it is counted as flaring in the dashboard summary, which uses a lower-cased substring match.

## Evidence
```
1 MMscf routine flaring -> expected 28316.8 m3 ; API routine volume_m3 = 28.32
YoY 2031 vs 2030 with identical 1 MMscf -> expected 0.0 % ; API yoy_change_pct = 2731.68
```

## Root Cause
The unit is matched with substring checks in the wrong order (`mscf` before `mmscf`, and `"k" in unit` catches any unit containing a k). There is no scf branch. The YoY denominator is converted by separate code that knows only "k" units.

## Impact
Flared volume, the Decree 21-330 flaring intensity (% of gas produced), the compliance badge and the YoY % are wrong by ×1000 (mmscf), ×35 (scf) or an arbitrary ratio (YoY) whenever flaring is recorded in field-gas units. The compliance verdict can flip.

## Affected Components
`GET /api/dashboard/flaring-summary`; DashboardEnhanced flaring banner, intensity bar and YoY badge.

## Recommended Fix
Use the central `calculations/units.py` gas-volume normalisation with exact unit keys for both current and prior year. Reject or flag unknown units instead of treating them as m3. Match process types case-insensitively and in the same way as `_query_summary`.


---

# BUG-036 — Flaring panel invents a 56 % / 40 % / 4 % Routine / Non-Routine / Safety split for generic "flaring" records and shows 0 tCO₂e for every stream (and a 2.5 t/kNm³ proxy when CO₂e is 0)

**Status:** Confirmed
**Severity:** Medium
**Category:** Dashboard
**Discovered by:** Agent F (Dashboard reconciliation auditor)

## Location
`new/server/routes/dashboard.py` `get_flaring_summary()`:
- ~L2945-2951: `if r_m3 == 0 and nr_m3 == 0 and s_m3 == 0 and em_general_m3 > 0: r_m3 = em_general_m3 * 0.56; nr_m3 = … * 0.40; s_m3 = … * 0.04`
- per-stream `tco2e` is taken only from `em_routine_tco2e / em_non_routine_tco2e / em_safety_tco2e`. The general-flaring CO2e is added only to the total.
- ~L2954-2956: if the total CO2e is 0, it is replaced by `(total_m3/1000) * 2.5`.
Rendered in `DashboardEnhanced.jsx` flaring banner and the Detailed Breakdown sub-rows.

## Reproduction
1. Dashboard as admin, default "All Years" (the endpoint uses 2026, see BUG-026). Or call `GET /api/dashboard/flaring-summary?year=2026`.
2. DB: `select process_type, unit, quantity, co2e_total from emissions where year=2026 and status='Verified' and process_type like '%flar%'`.

## Input
2026 has only two Verified rows with generic `process_type='flaring'` (50,000 m3 each; 210.22 tCO2e in total). There are no FlaringDetail rows for 2026.

## Expected
The stream breakdown is unknown. The panel should show the 100 kNm3 / 210.2 t as "unclassified flaring", or refuse to split it. If a split is shown, the tCO2e must be split the same way (117.7 / 84.1 / 8.4 t) so that the streams add up to the total.

## Actual
The panel shows Routine **56 kNm3 (56 %) • 0 tCO2e**, Non-Routine **40 kNm3 (40 %) • 0 tCO2e**, Safety **4 kNm3 (4 %) • 0 tCO2e** and Total **100 kNm3 • 210.2 tCO2e**. The percentages look measured but are a hard-coded "industry benchmark". The streams add up to 0 t against a 210.2 t total.
When a generic flaring row has `co2e_total = 0` (e.g. the 2025 Verified `mscf` rows), the total CO2e is replaced by a 2.5 t/kNm3 proxy and presented as a result.

## Evidence
API: `{"routine_flaring":{"percentage":56.0,"tco2e":0.0,"volume_knm3":56.0},"non_routine_flaring":{"percentage":40.0,"tco2e":0.0,"volume_knm3":40.0},"safety_flaring":{"percentage":4.0,"tco2e":0.0,"volume_knm3":4.0},"total_flaring":{"tco2e":210.22,"volume_knm3":100.0}}`
UI: "ROUTINE FLARING 56kNm³ 56% of total • 0 tCO₂e … SAFETY & PURGE FLARING 4kNm³ 4% of total • 0 tCO₂e".

## Root Cause
A fallback allocates the volume by fixed benchmark ratios but does not allocate the CO2e. There is no indicator that the figures are modeled.

## Impact
Routine-flaring volume is the quantity regulated by Decree 21-330, Zero Routine Flaring and OGMP. The dashboard reports a routine volume that was never measured or entered, and zero emissions for every stream. Users can take fabricated routine-flaring figures into disclosures.

## Affected Components
`GET /api/dashboard/flaring-summary`, DashboardEnhanced flaring banner and Detailed Breakdown flaring sub-rows.

## Recommended Fix
Remove the fixed 56/40/4 split. Report generic flaring as "Unclassified". If modeled values are kept, allocate the CO2e with them and label them as estimated. Do not substitute a 2.5 t/kNm3 proxy without a flag.


---

# BUG-037 — Editing a Scope 1 record replaces its propagated 1σ uncertainty with the raw catalog EF half-width (95 %, EF-only); user_uncertainty is stored unpropagated

**Status:** Confirmed
**Severity:** High
**Category:** Uncertainty
**Discovered by:** Agent G (Uncertainty Auditor)

## Location
`new/server/routes/emissions.py` `update_emission()` ~L3571-3597. After `compute_emissions()` the code sets `record.uncertainty/_ch4/_n2o = factor_data["uncertainty"][gas]` (raw catalog value) and `user_uncertainty[g]/100`. It ignores the propagated `_full_api_res.results[gas].uncertainty` that POST (L3131-3153) and bulk upload (L838-858, background_processor L1808-1826) persist.
The same raw-EF pattern is used by `/api/emissions/import` (L3949: `factor_data["uncertainty"]["co2"]`, CO2 only, CH4/N2O left null). That path was found by code reading and was not executed.

## Reproduction
1. As admin, POST stationary_combustion / Natural Gas / 1000 m3 / default, year 2045.
2. GET `/api/dashboard/uncertainty?year=2045`.
3. PUT `/api/emissions/<id>` `{"recalculate": true}`. No input changes, so co2e is unchanged.
4. Repeat GET. Script: `audit/repro/<ID>.py`.

## Input
Natural Gas catalog EF uncertainty: CO2 0.05, CH4 0.20, N2O 0.20 (95 % half-widths). Tier-1 AD ±10 %.

## Expected
Stored values are unchanged by a no-op recalculation. By hand, u_CO2 (1σ) = √(0.025² + 0.05²) = 0.0559 and u_CH4 = u_N2O = 0.1118. The same holds for `user_uncertainty co2=50 %`: POST stores √(0.25² + 0.05²) = 0.2550, and PUT should store the same.

## Actual
- After POST: (0.0559, 0.1118, 0.1118). Dashboard ±22.36 %.
- After PUT: **(0.05, 0.20, 0.20)**. Dashboard **±40.0 %**, with CO2e unchanged.
- user_uncertainty 50 %: POST stores 0.2550, PUT stores **0.5000**. The dashboard then shows ±100 %.

## Evidence
Repro output above. The snapshot DB already holds 110 records with exactly (0.05, 0.20, 0.20). These are edited records whose uncertainty column now has 95 %/EF-only semantics, while the column is documented and consumed as a 1σ combined value (`models.py`, `dashboard.get_ef_uncertainty`, `CalculationDetails.jsx` "1σ Uncertainty").

## Root Cause
Two code paths persist different quantities in the same column. The POST/bulk paths store the 1σ combined EF+AD value from `propagate_uncertainty`. The PUT and `/import` paths store the unpropagated 95 % EF-only half-width, which omits the AD term and the /k conversion. Consumers then apply k=2 again.

## Impact
Any edit, including a no-op recalculation, changes a record's reported uncertainty with no change in data. The reported 95 % interval roughly doubles for EF-dominated gases (0.05 read as 1σ is 10 % at 95 %, against the correct 11.18 %; 0.20 read as 1σ is 40 %, against the correct 22.4 %). User-supplied uncertainties are doubled. Persisted values mix two incompatible semantics, which corrupts the Uncertainty page, the CSV/PDF outputs and CalculationDetails.

## Affected Components
PUT `/api/emissions/<id>`, POST `/api/emissions/import`, the `emissions.uncertainty*` columns, `/api/dashboard/uncertainty`, `/api/qaqc/dashboard`, `CalculationDetails.jsx`.

## Recommended Fix
In `update_emission` and `import_emissions`, persist `calculated_em["_full_api_res"]["results"][gas]["uncertainty"]`, as `add_emission` does, and drop the post-hoc `user_uncertainty/100` override (the dispatcher already propagates it). Back-fill the existing rows by recomputing them.


### Additional confirmation (BUG-029)

Independently confirmed by Agent J (Database).

New evidence / additional affected component: **every bulk upload (Scope 1/2/3, production, sources, ...) by a Global-scope user fails with a fatal error** while any facility has a NULL name.
- `background_processor.py:332` `fac_name_map = {fac.name.lower(): fac for fac in all_facilities}` raises `AttributeError: 'NoneType' object has no attribute 'lower'`; job ends `status="error"`, `errors=["Fatal error: 'NoneType' object has no attribute 'lower'"]`, nothing imported.
- Reproduced on agentJ copy of the snapshot (admin, POST /api/emissions/upload/start with a 1-row Scope 1 CSV) — `audit/work/J/bulk.py`.
- DB state: 13 facilities (ids 149,151-154,156,157,159,161,163,164,166,167) have name NULL or '' — schema has `facilities.name` nullable with no CHECK, and `code` is the only unique column (NULLs allowed).
- Fix should include `nullable=False` + non-empty validation on `Facility.name` (and ideally a unique constraint), plus a data clean-up of the 13 existing rows.


---

# BUG-038 — Audit trail (/api/audit/, /api/audit/export) is not facility/region-scoped: a region-restricted superuser reads activity entries for every region's records

**Status:** Confirmed
**Severity:** Medium
**Category:** Security
**Discovered by:** Agent I (Backend/API/Security)

## Location
`new/server/routes/audit.py:52` `_build_audit_query()` — only IT roles are filtered (to security actions); superusers with a restricted `location` get the unfiltered `ActivityLog` table. Same for `/export`, `/filters`, `/stats`.

## Reproduction
1. Log in as `audit_superuser@audit.local` (superuser, location West; `/api/facilities` returns ids 1, 2, 158, 160, 168).
2. `GET /api/audit/?limit=500&entity=Emission` and `GET /api/audit/export`.
3. Map each entry's `entityId` to `emissions.facility_id`.
Script: `audit/repro/<BUG-ID>.py`.

## Input
Snapshot data, West superuser.

## Expected
Only entries about records in the superuser's allowed facilities (the same scoping applied to `/api/emissions`, dashboards etc.).

## Actual
144 of the returned Emission entries concern facilities outside West (e.g. log 1249 → emission 671, facility 165 "North Africa": "Added Combustion emission: … for Updated Facility (1/2099)"). `/api/audit/export` returns the full 211 KB CSV incl. before/after diffs (`old_values`/`new_values`) of all regions.

## Evidence
```
superuser (West) allowed facilities: [1, 2, 158, 160, 168]
actual: 144 entries, e.g. [(1249, (165, 'North Africa'), 'Added Combustion emission: ...'), ...]; /api/audit/export -> 200, 211509 bytes
```

## Root Cause
Audit queries apply role-based action filtering for IT only; no `get_allowed_facility_ids` scoping for regional roles. ActivityLog has no facility column, so scoping requires joining via entity/entity_id.

## Impact
Cross-region disclosure of activity (facility names, quantities, fuels, users, IPs, value diffs) to regional superusers, defeating the region isolation enforced elsewhere.

## Affected Components
`/api/audit/`, `/api/audit/export`, `/api/audit/filters`, `/api/audit/stats`; Audit Trail page.

## Recommended Fix
Store facility_id on ActivityLog (or resolve through entity/entity_id) and filter by `get_allowed_facility_ids(user)` for non-unrestricted roles; or restrict the audit trail to admin/unrestricted superusers.


---

# BUG-039 — Emission goals API ("+ Set Target") has no value validation: negative, year 1, and NaN goals are accepted; a NaN goal for the current year makes the main dashboard batch return 500

**Status:** Confirmed
**Severity:** Medium
**Category:** API
**Discovered by:** Agent H (SBTi Auditor)

## Location
`new/server/routes/managedata.py` `add_or_update_goal()` (POST `/api/goals`, ~line 770); consumers `new/server/routes/dashboard.py` batch-all (`float(goal.target_amount)` ~line 258) and `get_goal()` `/dashboard/goals/<year>` (~line 951).

## Reproduction
1. `python C:/Users/samsung/Desktop/H2/audit/repro/<BUG-ID>.py`
2. As admin: `POST /api/goals {"year":1,"target_amount":-5}` → 200 (stored).
3. `POST /api/goals` raw body `{"year":2026,"target_amount":NaN}` → 200; SQLite stores NULL.
4. `GET /api/dashboard/batch-all` (default dashboard, year=all → goal of current year) → **500** `float() argument must be ... not 'NoneType'`; `GET /api/dashboard/goals/2026` → 500.

## Input
As above.

## Expected
400 for non-finite, negative/zero targets and for years outside a sane range (e.g. 1990-2100).

## Actual
All accepted. The snapshot already contains goals up to year 2126 (100 rows 2027-2126), showing there is no range check. With the NaN goal the main dashboard fails to load for every user for that year (for the current year: the default view).

## Evidence
Repro output: `year=1/-5 t -> 200; NaN -> 200; /dashboard/batch-all -> 500; /dashboard/goals/2026 -> 500`.

## Root Cause
Only presence checks (`data.get("year")`, `target_amount is not None`) and `float()` conversion; no `isfinite`, sign or range check. Readers call `float(goal.target_amount)` without None-guard (`/goals` list guards it, the other two do not).

## Impact
An API-only (UI sends `null` for NaN, which is rejected) admin/superuser input can take down the main dashboard; negative goals make the "% GOAL" badge nonsensical. Medium: requires privileged API use, but the effect is platform-wide.

## Affected Components
`/api/goals` POST; `/api/dashboard/batch-all`; `/api/dashboard/goals/<year>`; DashboardEnhanced.jsx top-bar goal badge and "% GOAL" badge.

## Recommended Fix
Validate `math.isfinite(target) and target > 0` and a year range; guard `target_amount is None` in the readers.


---

# BUG-040 — Supply Chain filter is not applied to the emissions-by-source split: "Emissions by Source" donut and Detailed Breakdown rows show company-wide values (sources add up to 7× Scope 1)

**Status:** Confirmed
**Severity:** High
**Category:** Dashboard
**Discovered by:** Agent F (Dashboard reconciliation auditor)

## Location
`new/server/routes/dashboard.py` `_query_summary()`. The Scope 1 and Scope 2 queries (~L415-420, ~L450-455) join `Facility` and filter `Facility.segment == segment`. The per-source `activity_query` (~L530-545) applies facility, activity, division, year and status but **no segment filter**. Its rows are then added to `yearly_data[(year, fid)]` for every year that exists in the segment-filtered Scope 1 set.
Consumed by `DashboardEnhanced.jsx` (`totals.combustion/flaring/venting/other` → `sourceChartData` donut and the Detailed Breakdown rows "Stationary Combustion / Flaring / Venting / Other Sources").

## Reproduction
1. `python audit/repro/BUG-NNN.py`
2. Or in the UI, set Supply Chain = "Heavy Industry" and compare the Scope 1 pill with the Detailed Breakdown source rows.

## Input
Snapshot DB. Segment "Heavy Industry" = the Tosyali steel plant (facility 1). Its only flaring row is 15.93 t.

## Expected
Source rows add up to Scope 1 (independent SQL on `facilities.segment`):
- Heavy Industry: Scope 1 = 532,854,262,072.39 t. Flaring = 15.93 t.
- Upstream: Scope 1 = 3,190,271,328,984.07 t. Flaring = 2,199,032.63 t.

## Actual
- Heavy Industry: Scope 1 KPI 532.85 B (correct), but the sum of sources is **3,723,125,709,361.93 t** and flaring is **2,199,048.57 t** (company-wide Berkine flaring on a steel plant).
- Upstream: sum of sources is 3.723 T against a Scope 1 of 3.190 T.
The donut and the table therefore show 7× (Heavy Industry) or 1.17× (Upstream) more emissions than the Scope 1 KPI above them.

## Evidence
```
segment=Heavy Industry: Scope1 KPI=532,854,262,072.39 (SQL 532,854,262,072.39) | sum of sources=3,723,125,709,361.93 | flaring shown=2,199,048.57 expected 15.93
segment=Upstream: Scope1 KPI=3,190,271,328,984.07 (SQL 3,190,271,328,984.07) | sum of sources=3,723,125,527,259.75 | flaring shown=2,199,048.57 expected 2,199,032.63
```

## Root Cause
The `segment` join and filter were added to the Scope 1 and Scope 2 queries of `_query_summary` but not to the third (source-split) query. The merge loop only checks `key in yearly_data` and does not check that the populations match.

## Impact
With any Supply Chain filter selected, the "Emissions by Source" donut and the Stationary Combustion / Flaring / Venting / Other rows show the whole company's emissions. The dashboard's source mix does not reconcile with its own Scope 1 figure.

## Affected Components
`/api/dashboard/batch-all` (summary), `/api/dashboard/summary`; DashboardEnhanced source donut and Detailed Breakdown.

## Recommended Fix
Apply the same `Facility` join and `Facility.segment == segment` filter to `activity_query`. Better, derive all three queries from one filtered base query. Add an invariant test that the source sum equals Scope 1.


---

# BUG-041 — Dashboard "% GOAL" badge in the default All-years view divides the cumulative multi-year Scope 1+2 total by the single current-year goal (and ignores region/facility filters)

**Status:** Confirmed
**Severity:** Medium
**Category:** Dashboard
**Discovered by:** Agent H (SBTi Auditor)

## Location
`new/server/routes/dashboard.py` batch-all: `goal_year = int(year) if year and year != "all" else datetime.now().year` (~line 168). `new/client/src/pages/DashboardEnhanced.jsx` totals loop (~290-305, sums every year when `currentYear === "all"`) and "% GOAL" badge (~1136-1150: `stats.totalEmissions / goal.target_amount`). Goal is set via the header "+ Set Target" → ManageData goals tab.

## Reproduction
1. `python C:/Users/samsung/Desktop/H2/audit/repro/<BUG-ID>.py`
2. Verified S1+S2: 2020 = 800 t, 2023 = 750 t, current year 2026 = 0 t. Goal for 2026 = 1000 t.
3. Open the dashboard with Year = All (default) → batch-all returns the 2026 goal; badge = 1550/1000.

## Input
As above.

## Expected
Either no goal badge in the All-years view, or current-year actual / current-year goal = 0 / 1000 = 0 % (YTD).

## Actual
"155.0% GOAL" in red (danger class, >100 %), and the header shows "Target 2026: 1,000 tCO₂e" next to a cumulative 2020-2026 total. The goal is also compared with region/facility-filtered totals although goals are corporate-wide.

## Evidence
API returns `goal = {year: 2026, target_amount: 1000}` for year=all; JSX computes badge from the all-years `totalEmissions` (read directly, replicated in repro).

## Root Cause
Year = "all" is mapped to the current year's goal while the numerator is the all-year sum; no filter-scope awareness.

## Impact
The default dashboard view shows a meaningless and alarming goal attainment percentage once a goal exists for the current year.

## Affected Components
DashboardEnhanced.jsx hero card goal badge; batch-all `goal`.

## Recommended Fix
Hide the badge when Year = All (or compare only the goal year's actual), and hide/scale it when region/facility filters are active.


---

# BUG-042 — Recalculating a Tier 2 (custom-factor) Scope 1 record drops the custom factor: emissions become 0 or silently switch to the catalog factor, while factor_source stays "custom"

**Status:** Confirmed
**Severity:** High
**Category:** Emissions
**Discovered by:** Agent C (Tier / Factor Auditor)

## Location
`new/server/routes/emissions.py`, the update route (PUT `/api/emissions/<id>`), lines ~3473-3530.
- `factor_data = _lookup_api_factor(data.get("fuel") or ... or record.fuel_type)`.
- The custom factor is applied only when `custom_factor_id` is in the PUT body (`cf_id = data.get("custom_factor_id")`). It is never read from the record's stored `source_payload`, even though that payload is merged into `calc_payload` a few lines later.

## Reproduction
1. `python audit/repro/BUG-<ID>.py` (own db).
2. Create a custom factor: 2.0 kg CO2/m3, 0.01 kg CH4/m3, unit kg/m3.
3. POST a Tier 2 record the way Scope1Form does it: `factor_source=custom`, `custom_factor_id=<id>`, `fuel=str(id)`, 1000 m3.
4. PUT `/api/emissions/<rid>` with `{"recalculate": true}`. Any edit that touches quantity, unit, fuel or process_type gives the same result.

## Input
Custom factor 2.0 kg CO2/m3 and 0.01 kg CH4/m3; activity 1000 m3.

## Expected
Recalculation re-applies the record's custom factor: 2.0 t CO2 and 0.01 t CH4 (2.28 t CO2e at AR5).

## Actual
- The record becomes co2 = 0, ch4 = 0, co2e_total = 0, with calc_method `server_default` and factor_source still `custom`. HTTP 200.
- If the record's fuel is a catalog name (API/bulk path, e.g. `fuel="Natural Gas"`), the recalculation silently switches to the Tier 1 catalog factor instead. In the test, 2.0 t became 1.911 t (53.06 kg/MMBtu × 1020 Btu/scf). The record still claims Tier 2, and its uncertainty is replaced by the catalog's 0.05.

## Evidence
Repro output:
- `before: co2 2.0, ch4 0.01, co2e 2.28, api2021_generic, custom`.
- `after: co2 0.0, ch4 0.0, co2e 0.0, server_default, custom`.
- Second scenario (work/C/t4.py): record 805 changed from 2.0 to 1.9113 t CO2 after PUT recalculate.

## Root Cause
The update route rebuilds `factor_data` only from the request body. The custom factor linkage (`custom_factor_id` in `source_payload`) is ignored. The fallback lookup by `fuel_type` (the custom factor id as a string) finds nothing, and a missing factor is treated as 0.

## Impact
Any API/ERP edit or recalculation of a Tier 2 record zeroes it, or re-tiers it to catalog defaults without notice. Records edited by an admin stay `Verified`. The tier label ("custom") no longer matches the factor applied, which breaks audit traceability.

## Affected Components
- PUT `/api/emissions/<id>`.
- Any batch or recalculation workflow that calls it.
- Dashboards and reports aggregating the changed records.
- Uncertainty, since the tier-based uncertainty is resolved against the wrong factor.

## Recommended Fix
- On recalculation, resolve `custom_factor_id` from the request, else from `source_payload`, and fail if the factor no longer exists.
- Never fall back to the catalog, or to 0, for a record whose `factor_source` is `custom`.


---

# BUG-043 — Stored uncertainty has no range or unit validation: Scope 2/3 accept percent values, negatives, NaN and 1e6, and the Uncertainty dashboard shows ±3600 %

**Status:** Confirmed
**Severity:** Medium
**Category:** Uncertainty
**Discovered by:** Agent G (Uncertainty Auditor)

## Location
- `new/server/routes/scope2.py` L220-222 (POST) and L464-465 (PUT: `float(data["uncertainty"] or 0)`).
- `new/server/routes/scope3.py` L126-128.
- `new/server/routes/dashboard.py` `get_ef_uncertainty()`, which takes any stored value > 0 as a 1σ fraction with no upper bound.
- For comparison, `routes/qaqc.py _norm_unc()` applies a `>1 → /100` heuristic, so the two pages disagree on the same data.

## Reproduction
1. As admin, POST `/api/scope2` (electricity, 100000 kWh, EF 0.5) with `uncertainty` set to 18, then -0.5, then "NaN".
2. GET `/api/dashboard/uncertainty?year=<y>&scope=2`.
Script: `audit/repro/<ID>.py`.

## Input
`uncertainty` = 18 (a user meaning "18 %"), -0.5, "NaN", 1e6.

## Expected
The API rejects with 422 any value that is not a finite fraction in [0, ~2], or explicitly converts a percent value. The dashboard never reports an impossible ±3600 %.

## Actual
- 18 → HTTP 201, stored 18.0, dashboard category and inventory **±3600.0 %**, level "high".
- -0.5 → HTTP 201, stored -0.5. The dashboard silently substitutes its 0.10 default (±20 %).
- "NaN" → HTTP 201. The response body contains the bare token `NaN`, which is not valid JSON. The dashboard substitutes the default.
- 1e6 → HTTP 201, dashboard ±200000000 %.
Scope 3 accepts -3 the same way (HTTP 201).

## Evidence
Repro output above. The snapshot DB already contains 400 Verified Scope 1 rows with `uncertainty = 18.0277` (a percent stored in the fraction column, from test injection). Because of them, `/api/dashboard/uncertainty?year=2020` shows inventory ±818.97 % with contributors ±3605.6 %, while `/api/qaqc/dashboard?year=2020` normalises the same rows to 4.09 %. `?year=2022` shows stationary_combustion ±1249 %.

## Root Cause
No validation or unit contract on uncertainty inputs: the fraction/percent ambiguity is never resolved and there are no finiteness or range checks. The consumers handle out-of-range values inconsistently: the dashboard applies no guard, QAQC applies a heuristic /100, and negatives fall back to a default.

## Impact
A single mis-keyed record, or any percent-valued import, can make the whole-inventory uncertainty meaningless in the Uncertainty page, its CSV and the PDF report. Negative and NaN values are silently replaced. The API also emits invalid JSON.

## Affected Components
POST/PUT `/api/scope2`, POST `/api/scope3`, `emissions.uncertainty*` (no guard on any write path), `/api/dashboard/uncertainty`, `/api/qaqc/dashboard`, `UncertaintyAssessment.jsx`.

## Recommended Fix
Validate that uncertainty is finite and satisfies 0 ≤ u ≤ 2 (fraction, 1σ) on every write path, or accept a clearly named `uncertainty_pct` and convert it. Reject NaN/Inf. Apply one shared normalisation or guard in both dashboard consumers and flag out-of-range stored rows instead of propagating them.


---

# BUG-044 — /granular-intensities (Master Report "Multi-Metric Intensities") divides all-facility emissions by only the facilities with granular MMboe fields, and fabricates NGSI methane (0.05 %) and saleable production (85 %)

**Status:** Confirmed
**Severity:** High
**Category:** Carbon Intensity
**Discovered by:** Agent E (Carbon-intensity auditor)

## Location
`new/server/routes/dashboard.py` `get_granular_intensities` L3075-3172:
- L3133 `total_boe = Σ total_production_mmboe×1e6`. The oil/gas fallback (L3138-3141) runs only when that sum is **0 for the whole query**. Rows without MMboe fields are therefore dropped whenever any row has them. The numerator (L3102-3121) is not restricted in the same way.
- L3140 fallback `gas_amount/5.8` ignores `gas_unit` (m³ or mmscf rows are treated as mscf) and `oil_unit`. It also uses 5.8 mscf/BOE, while `/intensity-stats` uses 0.178 BOE/mscf (5.62 mscf/BOE), so the two endpoints use different BOE definitions.
- L3143 `saleable_boe = total_boe × 0.85` when unrecorded: an invented "typical saleable fraction". The OGCI comparison (L3154, L3170) is made on this saleable value.
- L3150-3151: when `gross_gas_mmsm3` is empty, `methane_intensity_ngsi_wt_pct` returns the constant **0.05**, even though gas production exists in `gas_amount`.
- Client `new/client/src/utils/ModernReportGenerator.js` L1232-1242:
  - fallbacks 11.18 / 30.84 / 0.018
  - hard-coded "2.02 Sm³ / BOE" flaring row
  - fixed verdict texts "Far below global 0.20% methane intensity ceiling" and "COMPLIANT with ≤ 1.00% statutory ceiling", which are printed whatever the values are
- The endpoint has no activity, division or segment filter and no IT-role check.

## Reproduction
1. Run `python audit/repro/BUG-044.py` (own db copy).
2. `GET /api/dashboard/granular-intensities?year=2025` as admin.
3. Independently: Σ Verified S1+S2 2025 / Σ BOE per production row, using `total_production_mmboe` when it is present and otherwise oil + gas/5.8 with unit conversion.
4. `GET /api/dashboard/granular-intensities?year=2026&facilityId=13`.

## Input
Snapshot. 2025 has 254 production rows over 78 facilities. Only the 2 Berkine rows (169, 170) carry `total_production_mmboe`. The other 252 rows (61.7 M BOE of oil and gas) carry `oil_amount`/`gas_amount` only. Facility 13 in 2026: 4.76 M mscf gas (= 134.7 M m3) and 338.91 t CH4.

## Expected
- 2025 CI (total production) = 1,954,194 t × 1000 / 192,634,702 BOE = **10.14 kg CO2e/BOE**. The endpoint's own OGCI test on saleable volume gives about 17.9 kg/BOE.
- Facility 13, 2026, NGSI CH4 wt% = 338.91 t / (134.7 M m3 × 0.0008 t/m3) = **0.31 %**. That is above the 0.20 % ceiling the report cites.

## Actual
- 2025: `ci_by_total_production_kg_boe` = **14.93** over 130,930,000 BOE (Berkine only, 47 % too high). `ci_by_saleable_production_kg_boe` = 34.51, reported as "2.0x ABOVE TARGET".
- Facility 13, 2026: `methane_intensity_ngsi_wt_pct` = **0.05** (a constant). The report then prints "Far below global 0.20% methane intensity ceiling".
- Corporate 2026 also returns 0.05.

## Evidence
`audit/repro/BUG-044.py` output:
```
2025 CI total production: expected 10.14 kg/BOE over 192,634,702 BOE; actual 14.93 over 130,930,000 BOE MISMATCH
2026 fid13 NGSI CH4 wt%: gross gas 0 (gas recorded in mscf), CH4 338.91 t -> API returns fabricated 0.05 MISMATCH
```
Same data through `/intensity-stats?year=2025`: 10.86 kg/BOE. The two report sections contradict each other.

## Root Cause
The fallback is decided all-or-nothing on the aggregate instead of per row, and it is unit-blind. Missing inputs are replaced by invented constants (0.85 saleable, 0.05 % CH4) rather than being reported as "not available". The report template also hard-codes values and verdicts.

## Impact
The Master Report "Multi-Metric Intensities Matrix" (Chapter 8) shows a carbon intensity that is 47 % too high for 2025. It shows a methane intensity that is invented, and in the facility 13 case hides a breach of the 0.20 % threshold. It also shows a flaring Sm³/BOE value and compliance statements that do not come from data.

## Affected Components
`/api/dashboard/granular-intensities`, ModernReportGenerator.js Chapter 8 (and the flaring row in the compliance table, L1139, which falls back to 0.865).

## Recommended Fix
Compute BOE per production row: use `total_production_mmboe` when it is present, otherwise unit-converted oil + gas with a single shared BOE factor. Use the same factor in every endpoint. Return null / "insufficient data" instead of 0.85 or 0.05. For NGSI, fall back to `gas_amount` converted to m³. Compute the report's flaring Sm³/BOE and its verdict strings from data.


---

# BUG-045 — "Add Region" (create facility) form fails with HTTP 500 unless the optional Latitude/Longitude fields are filled

**Status:** Confirmed
**Severity:** Medium
**Category:** Backend
**Discovered by:** Agent L (Browser)

## Location
- `new/server/routes/facilities.py:176-177` (`latitude=data.get("latitude")`, `longitude=data.get("longitude")` passed straight to Float columns); same pattern at `:286-289` in the update route
- `new/client/src/pages/ManageData.jsx:920-941` (`handleAddFacility` posts the form with `latitude: ""`, `longitude: ""`; catch shows the generic "Failed to add region")

## Reproduction
1. Log in as audit_admin on :5190 and open Manage Data → Regions.
2. Fill Region Name, Activity, Division, Field, Location. Leave Latitude/Longitude empty (the UI does not mark them as required).
3. Click "Add Region".

## Input
Request body sent by the UI: `{"name":"AUDIT-L Plant","activity":"EP","division":"Production","field":"AUDIT-L Field","location":"West","boundary_type":"","boundary_detail":"","equity_share_pct":"","segment":"","latitude":"","longitude":"","boundary_notes":""}`

## Expected
Facility created (201) with NULL coordinates, or a clear 400 validation message.

## Actual
`POST /api/facilities` → `500 {"error":"Internal server error"}`. Server log: `sqlalchemy.exc.StatementError: (builtins.ValueError) could not convert string to float: ''` on the INSERT into facilities. The UI shows only "Failed to add region". The same form with Latitude=31.5 / Longitude=5.2 → 201 (facility id 173).

## Evidence
`audit/work/L/w2_facility.mjs` run 1 (no coordinates): `POST 500 ... request_id 77a570e5-...`; `audit/work/backend_5055.log` line ~1721 traceback. Run 2 with coordinates: `POST 201 {"id":173}`.

## Root Cause
The route does not coerce empty strings for the Float columns latitude/longitude (unlike `equity_share_pct`/`reconciliation_threshold`, which use `float(x or default)`), and the form always sends them as "".

## Impact
The only UI path for creating a facility fails in the default case (coordinates are optional and usually unknown). Users see a non-actionable error. The side effect also shows the 500 handler is reached for plain input-type errors.

## Affected Components
Manage Data → Regions → Add Region; `PUT /api/facilities/<id>` has the same pattern (assigns `data["latitude"]` directly), not separately exercised.

## Recommended Fix
Parse latitude/longitude as `float(v) if v not in (None, "") else None` (with range checks -90..90 / -180..180) in both create and update, and return 400 on invalid values. The client should also omit empty numeric fields.


---

# BUG-046 — Equity-share allocation ignores effective dates (time-sliced ownership never applied) and POST /api/equity/shares accepts any percentage (500, -50, inf) from any business role

**Status:** Confirmed
**Severity:** High
**Category:** API
**Discovered by:** Agent I (Backend/API/Security)

## Location
- `new/server/routes/equity_routes.py:129-205` `get_equity_allocation()` — `shares = FacilityEquityShare.query.filter_by(facility_id=fac.id).all()` then `next(s for s in shares if s.partner_id == p.id)`: the comment says "Find active share for the year" but `effective_start_date` / `effective_end_date` are never compared with `year`; the first row (lowest id) wins.
- `equity_routes.py:89-126` `save_equity_share()` — no range/finite check on `equity_share_pct`, no check that shares per facility/period sum to ≤100 %, `float("abc")` / NaN → unhandled 500; only `@login_required` + `require_facility_access`, so role `user` can rewrite ownership of its own facilities.

## Reproduction
1. Admin: end Sonatrach's 51 % share at facility 169 on 2023-12-31 and `POST /api/equity/shares {"facility_id":169,"partner_id":1,"equity_share_pct":70,"effective_start_date":"2024-01-01"}` (the model docstring: "Time-sliced equity ownership percentages … supports mid-year ownership shifts").
2. `GET /api/equity/allocation?year=2025&facility_id=169`.
3. `POST /api/equity/shares` with `equity_share_pct` 500, -50, "inf", "nan", "abc".
Script: `audit/repro/<BUG-ID>.py`.

## Input
Facility 169 (HBNS), 2025 Verified Scope 1 total 705,943.67 tCO2e (SQL).

## Expected
2025 Sonatrach share = 70 % → 494,160.57 tCO2e. Percentages outside 0–100 or non-numeric rejected with 400.

## Actual
Sonatrach pct 51.0, allocated 360,031.27 tCO2e (uses the expired 2021 slice). 500 and -50 and inf saved with 200; "nan" and "abc" → HTTP 500. A `user`-role account got 200 setting a 99 % partner share on its own facility 1.

## Evidence
```
2025 total verified co2e (SQL) = 705943.67
expected Sonatrach pct 70 (share effective 2024-01-01), alloc = 494160.57
actual   Sonatrach pct 51.0, alloc = 360031.27
expected 400 for equity_share_pct=500 / -50; actual 200 / 200
```

## Root Cause
Missing date filter when selecting the active slice; no input validation on the write endpoint.

## Impact
Equity-share (JV partner) emission allocations are wrong for any facility whose ownership changed, and allocations can exceed 100 % / go negative; ownership data can be modified by data-entry users without review.

## Affected Components
`/api/equity/allocation`, `/api/equity/shares` (GET/POST), any UI/report using partner allocations.

## Recommended Fix
Select shares where `effective_start_date <= year-end` and (`effective_end_date` is null or `>= year-start`), pro-rating mid-year changes; validate 0 ≤ pct ≤ 100, finite, and per-period sum ≤ 100; restrict writes to admin/superuser; return 400 on parse errors.


### Additional confirmation (BUG-033)

Independently confirmed by Agent F (Dashboard reconciliation auditor). **BUG-035 was filed at the same time and has the same root cause. Treat BUG-035 as a duplicate of BUG-033.**
New evidence (`audit/repro/BUG-035.py`, db `repro_F3`): one Verified `routine_flaring` row of 1 mmscf was inserted in 2030 and another in 2031. `flaring-summary?year=2031` returns `routine volume_m3 = 28.32` (expected 28,316.8) and `yoy_change_pct = +2731.68 %` for identical volumes (expected 0 %), because the prior-year path reads mmscf as m3 while the current-year path reads it as mscf.
Additional affected behaviour: process types are matched by an exact, case-sensitive `IN (...)`. The Verified `process_type='Flaring'` row (2024, facility 1, 15.93 t) is left out of the flaring panel but counted as flaring in `_query_summary`, which matches substrings in lower case.


### Additional confirmation (BUG-004)

Independently confirmed by Agent F (Dashboard reconciliation auditor). The same root cause also affects the **headline dashboard totals**, not only intensity.
`_query_summary` (Scope 1 and 2 KPI, CH4 KPI, source split) and `_query_categorical_breakdown` filter by record-level `Emission.activity/division` and `Scope2Emission.activity/division`. The Activity and Division dropdowns are built from `Facility.activity/division`, and Scope 3 is filtered by `Facility.*`. On the snapshot, 403 of 630 Verified Scope 1 rows have `emissions.activity` NULL, although their facility has an activity.
Evidence (`audit/work/F/api2.py`, `/api/dashboard/batch-all`):
- activity="Steel & Iron (Acier DRI)": Gross (S1+S2) = **106.84 t**, CH4 = 0 t, Scope 3 = 216.85 t. Filtering by facility (facilityId=1, the only Steel facility) gives **532,854,090,929 t**. 120 facility-1 rows with NULL activity, and the 3 rows tagged 'Production', are dropped.
- activity="Activité E&P": 9,990.5 t. By facility activity, 3,392,147,653.7 t (160 rows with NULL activity are dropped).
- activity="Production" (a record-level label that is not a facility activity for facility 1) pulls in 531 B t of Steel-plant emissions.
- division="DP": 9,990.5 t against 3.39 B t by facility.
Additional affected components: DashboardEnhanced KPI cards (Gross, Net, CH4, Scope pills), the activity donut, the Categorical overview and the Organizational Breakdown. The categorical view groups by `Facility.activity` but filters by `Emission.activity`. The pending banner is also affected.


### Additional confirmation (BUG-007)

Independently confirmed by Agent F (Dashboard reconciliation auditor). The dashboard figures follow the stored values end to end (`audit/work/F/api1.py` and the Playwright DOM `audit/work/F/dash_text.txt`):
- UI "Gross 3.7T" = API summary S1 3,723,125,709,415.04 + S2 1,539,702.62 = 3,723,127,249,117.66. SQL gives the same.
- UI "CH4 84.3M tCH4" = SQL `sum(ch4_emissions)` Verified = 84,338,950.2 t. 70,000,000 t of that (83 %) comes from the 7 test rows (each 1e7 t CH4 = 1e13 MMBtu × 0.001 kg/MMBtu).
- Pending banner "128 records 4,686,441,566,968.31 tCO2e" = 114 S1 (4,686,441,566,610.25) + 14 S2 (358.06). This is 4.69e12, not 4.69e15. Two coal test rows account for 99.99 % of it.
The aggregation code is correct. The wrong magnitude comes only from the unvalidated inputs.


### Additional confirmation (BUG-013)

Independently confirmed by Agent F (Dashboard reconciliation auditor). The Dashboard GWP-20 toggle uses these constants.
`batch-all?gwp_horizon=20` Scope 1 = 3,727,743,605,006.12 t. This exactly matches an independent recompute with Δ(CH4) = 82.5-28 and Δ(N2O) = 268-265 per year (3,727,743,605,006.118). With the published AR5 values 84 and 264 the result would be 3,727,841,549,691.38 t.
The toggle tooltip in DashboardEnhanced.jsx says "CH4=84 per IPCC AR5/AR6", so the UI states a value the backend does not use.
Additional affected components: `_query_summary` and `_query_categorical_breakdown` GWP-20 paths (Gross KPI, source split, activity donut, categorical view).


---

# BUG-047 — Tier 1 fugitive and equipment factors in "per hour" units are multiplied only by the source count (no operating hours): annual CH4 understated 8,760×, and Tier 1 disagrees with Tier 3 for the same factor

**Status:** Confirmed
**Severity:** High
**Category:** Calculation
**Discovered by:** Agent A (Calculation Engine Auditor)

## Location
- `new/server/calculations/dispatcher.py` `_generic_calculation()`. It computes `quantity × factor`, with a denominator conversion only for volume/mass units. Time denominators ("/hr") are ignored and no hours are applied.
- It is reached for `factor_source` default/custom for every fugitive alias (`fugitive`, `wellhead_fugitive`, `separator_fugitive`, `gathering_boosting`, `gas_processing`, `compressor_fugitive`, `fugitive_component`, …).
- Catalog units (`emission_factors*.py`): `tonne CH₄/hr/source`, `tonne CH₄/well/hr`, `tonne CH₄/separator/hr`, `tonne CH₄/compressor/hr`, `tonne CH₄/unit/hr`.
- The UI (`FugitivesForm.jsx`) asks only for "Count (Number of Sources)" and sends it as `amount`. There is no hours field.

## Reproduction
1. `POST /api/emissions/` with `process_type=fugitive, factor_source=default, fuel="Component - Block Valve", amount=10`.
2. `POST /api/emissions/` with `process_type=wellhead_fugitive, factor_source=default, fuel="Wellhead - Gas", amount=10`.
3. Repro: `audit/repro/BUG-XXX.py`

## Input
10 block valves (4.36e-6 t CH4/hr/source); 10 gas wellheads (1.8e-5 t CH4/well/hr).

## Expected
Annual (8,760 h): valves 10 × 4.36e-6 × 8760 = **0.3819 t CH4**; wellheads 10 × 1.8e-5 × 8760 = **1.577 t CH4**. Even for a one-month record (744 h) the values are 0.0324 t and 0.134 t.

## Actual
Valves `ch4_emissions = 4.36e-5 t`; wellheads `1.8e-4 t`. That is the emission for **one hour**, 8,760× below annual.
For comparison, Tier 3 (`factor_source=specific`) with the same factor gives 1.340 t for the wellheads, because `EquipmentFugitiveCalculator` multiplies by 8760. It also applies a separate 0.85 error.

## Evidence
`agentA.db` rows (`calc_method = api2021_generic`): `ch4 4.3599999999999996e-05, co2e 0.0012208` and `ch4 0.00018, co2e 0.00504`.

## Root Cause
The generic calculator treats every factor as "per activity unit". Per-hour factors need count × hours, but no hours input is collected or applied.

## Impact
All Tier 1 equipment/component fugitive CH4 (usually the largest methane source in upstream inventories) is understated by about 4 orders of magnitude. This affects methane intensity, OGMP and Scope 1 totals.

## Affected Components
`_generic_calculation`; Tier 1 fugitive UI; bulk import of fugitive rows.

## Recommended Fix
Parse the time denominator. Require operating hours (default to hours in the reporting period) for "/hr" factors and multiply. Share one implementation between Tier 1 and Tier 3.


---

# BUG-048 — Tier 3 fugitive calculators misread catalog factor units: "CH₄" (Unicode subscript) is not recognised as methane (×0.85 applied), and ComponentFugitiveCalculator treats tonne/hr factors as kg/hr (1000× too low)

**Status:** Confirmed
**Severity:** High
**Category:** Calculation
**Discovered by:** Agent A (Calculation Engine Auditor)

## Location
- `new/server/calculations/fugitive.py` `EquipmentFugitiveCalculator.calculate`: `is_methane = any(x in u_low for x in ["ch4", "methane", "ch_4"])`
- `new/server/calculations/fugitive.py` `ComponentFugitiveCalculator.calculate`: the same check, plus `total_ch4_tonnes_year = (total_ch4_kg_hr * 8760) / 1000.0`, which always assumes kg/hr
- The catalog units use the subscript character U+2084, e.g. `tonne CH₄/well/hr`, `tonne CH₄/hr/source`

## Reproduction
1. `POST /api/emissions/` with `process_type=wellhead_fugitive, factor_source=specific, fuel="Wellhead - Gas", amount=10`.
2. `POST /api/emissions/` with `process_type=fugitive_component, factor_source=specific, fuel="Component - Block Valve", amount=10`.
3. Repro: `audit/repro/BUG-XXX.py`

## Expected
Wellheads: 10 × 1.8e-5 t/h × 8760 = **1.5768 t CH4** (the factor is already CH4, so no gas fraction applies).
Valves: 10 × 4.36e-6 t/h × 8760 = **0.3819 t CH4**.

## Actual
Wellheads `1.34028 t` (= × 0.85, −15 %). Valves `3.246e-4 t` (= × 0.85 / 1000, **1,176× too low**).

## Evidence
`agentA.db` rows: `Equipment-Level Fugitive ch4 1.3402800000000001`; `Component-Level Fugitive ch4 0.0003246455999999999`.
The lowercased unit `tonne ch₄/well/hr` contains no "ch4" substring, so the 0.85 default CH4 content is applied to a factor already expressed as CH4. The component calculator never reads the numerator unit.

## Root Cause
String matching on units does not normalise the Unicode subscript. The component calculator hard-codes kg.

## Impact
Every Tier 3 equipment-level fugitive is 15 % low. Every Tier 3 component-level fugitive using catalog factors is about 1000× low.

## Affected Components
`EquipmentFugitiveCalculator`, `ComponentFugitiveCalculator`, dispatcher branches for `equipment_fugitive` / `wellhead_fugitive` / … / `fugitive_component`.

## Recommended Fix
Normalise units before matching (map subscript digits to ASCII, strip spaces). Parse the numerator mass unit explicitly (t/kg/g/lb) in both calculators. Add regression tests with the real catalog strings.


---

# BUG-049 — Generic factor math ignores the 10³ / 10⁶ multiplier in factor denominators: offshore gas fugitives 1,000,000× and refinery fuel-gas fugitives 1,000× overstated

**Status:** Confirmed
**Severity:** High
**Category:** Calculation
**Discovered by:** Agent A (Calculation Engine Auditor)

## Location
`new/server/calculations/dispatcher.py` `_generic_calculation()`. `matched_v_denom` is picked by substring (`k in f_denom`), so `"10⁶ scf produced"` matches `scf` and `"10³ bbl feedstock"` matches `bbl`. The 10ⁿ scale is discarded.
Catalog: `Offshore - Gas Production (Facility)` = 0.0104 `tonne CH₄/10⁶ scf produced`; `Refinery - Fuel Gas System (50-99k bbl/day)` = 0.000375 `tonnes CH₄/10³ bbl feedstock` (and the 100-199k variant).

## Reproduction
1. `POST /api/emissions/` with `process_type=wellhead_fugitive, factor_source=default, fuel="Offshore - Gas Production (Facility)", amount=5, unit=mmscf`.
2. `POST /api/emissions/` with `process_type=refinery_fugitive, factor_source=default, fuel="Refinery - Fuel Gas System (50-99k bbl/day)", amount=50000, unit=bbl`.
3. Repro: `audit/repro/BUG-XXX.py`

## Expected
Offshore: 5 MMscf × 0.0104 t/MMscf = **0.052 t CH4**. Refinery: 50 kbbl × 0.000375 = **0.01875 t CH4**.

## Actual
Offshore `ch4_emissions = 52,000 t` (co2e 1,456,000 t). Refinery `18.75 t`. No unit choice gives the right answer: entering scf also multiplies by 1e6.

## Evidence
`agentA.db` rows, `calc_method = api2021_generic`: `ch4 52000.0, co2e 1456000.0`; `ch4 18.75, co2e 525.0`.

## Root Cause
Denominator parsing takes the first unit-name substring and ignores numeric scale prefixes (10³, 10⁶, "per thousand").

## Impact
A single offshore gas facility-month can inject 10⁶ t CO2e into Scope 1. Refinery fuel-gas fugitives are 1000× high.

## Affected Components
`_generic_calculation` (Tier 1/custom for any process); catalog entries with scaled denominators; the Tier 3 `EquipmentFugitiveCalculator` for the same entries, which applies ×8760 to these non-hourly factors.

## Recommended Fix
Parse scale prefixes (10³/10⁶/k/M/MM) in denominators and divide accordingly. Better still, store factors in canonical units with an explicit denominator unit field.


---

# BUG-050 — Negative activity amounts are accepted for process types that are not in the dispatcher (e.g. "loading") and saved as negative emissions

**Status:** Confirmed
**Severity:** Medium
**Category:** Calculation
**Discovered by:** Agent A (Calculation Engine Auditor)

## Location
- `new/server/calculations/dispatcher.py` `dispatch()`: `if not calculator: return self._generic_calculation(...)` runs **before** the NaN/Inf/negative quantity checks. `_generic_calculation` has no validation.
- `new/server/routes/emissions.py` `add_emission()` validates only `data["quantity"]`. The calculation reads `amount` first.

## Reproduction
1. `POST /api/emissions/` with `process_type=loading, factor_source=default, fuel="Loading - Crude Oil (Tank Truck)", amount=-1000000, unit=bbl` (no `quantity`).
2. Repro: `audit/repro/BUG-XXX.py`

## Expected
HTTP 422 (negative activity), as returned for dispatcher processes (e.g. `separation` → "Quantity/Amount cannot be negative").

## Actual
HTTP 201. Stored `ch4_emissions = -0.16`, `co2e_total = -4.48`, `quantity = -1000000`, status Verified (admin).

## Evidence
`agentA.db` row: `{'ch4_emissions': -0.16, 'co2e_total': -4.48, 'calc_method': 'api2021_generic', 'quantity': -1000000.0}`.

## Root Cause
Input validation is applied only on the calculator path and only to the `quantity` key.

## Impact
Negative records silently offset real emissions in totals (API and bulk callers). The same path does no NaN/Inf check for unknown process types.

## Affected Components
`dispatch` → `_generic_calculation`; POST `/api/emissions/`; any process_type not in `CalculationDispatcher.calculators` (loading, fccu, custom names).

## Recommended Fix
Validate `amount` and `quantity` (finite, ≥ 0) in the route. Move the dispatcher's quantity validation above the `if not calculator` early return.


---

# BUG-051 — Energy activity units kWh / MJ / Btu with a kg/MMBtu factor are treated as scf of gas (× 1020 Btu/scf): 1000 kWh of natural gas is 3.3× too low, MJ 7.6 % too high

**Status:** Confirmed
**Severity:** Medium
**Category:** Calculation
**Discovered by:** Agent A (Calculation Engine Auditor)

## Location
- `new/server/calculations/combustion.py` `convert_factor_to_kg_per_unit()`, `kg/MMBtu` branch. Only `mmbtu`, `gj` and `therm` are handled as energy. Any other unit falls through to `return val * ((hhv or ...) / 1_000_000.0)`, i.e. per-scf.
- `dispatcher._generic_calculation()` has the same gap: an unknown unit goes to the gas branch with `scf = quantity`.
- `units.ENERGY_UNITS_TO_MJ` already defines kwh, mwh, mj, kj, btu, but it is not used here.

## Reproduction
1. `POST /api/emissions/` with `process_type=combustion, factor_source=default, fuel="Natural Gas", amount=1000, unit=kwh`, and again with `amount=1000000, unit=mj`.
2. Repro: `audit/repro/BUG-XXX.py`

## Expected
1000 kWh = 3.412142 MMBtu × 53.06 = **0.18105 t CO2**. 1,000,000 MJ = 947.817 MMBtu × 53.06 = **50.29 t CO2** (as the app correctly returns for 1000 GJ).

## Actual
kWh → `0.054121 t` (0.30×). MJ → `54.121 t` (1.076×). Both are computed as if the number were scf × 1020 Btu/scf.

## Evidence
`agentA.db` rows: kwh `co2 0.05412120000000001`; mj `co2 54.12120000000001`; gj `co2 50.29117002` (correct).

## Root Cause
Energy units are hard-coded to a short list, and the fallback silently assumes a gas volume.

## Impact
Fuel reported by energy in kWh, MWh, MJ or Btu (common for metered gas and for purchased-fuel invoices) gives wrong CO2/CH4/N2O.

## Affected Components
`convert_factor_to_kg_per_unit`, `_generic_calculation`, legacy `GHGCalculator.calculate_energy`.

## Recommended Fix
Convert all energy units through `ENERGY_UNITS_TO_MJ`. Raise an error for unrecognised units instead of assuming scf.


---

# BUG-052 — OGMP survey reconciliation status defaults to "Reconciled" whatever the computed variance; a +354 % discrepancy is stored and shown as Reconciled, and a zero bottom-up case is shown as "+0.0 %"

**Status:** Confirmed
**Severity:** Medium
**Category:** Methane
**Discovered by:** Agent D (Methane Auditor)

## Location
- `new/server/routes/data.py` `save_ogmp_survey()`, ~line 457: `reconciliation_status = (data.get('reconciliation_status') or ... or 'Reconciled')`. It is stored as given, independently of the `variance_pct` / `variance_flag` the same function computes.
- `get_ogmp_surveys()`: `'variance_pct': d.variance_pct or 0.0` and `'reconciliation_status': d.reconciliation_status or 'Reconciled'`.
- UI: `MethaneIntensity.jsx` ~1341-1400 (survey table: status badge green when "Reconciled"; variance shown green when |v| ≤ threshold); `MethaneExplorer.jsx:1537`.

## Reproduction
1. Fresh DB copy, admin. Facility 169 has Verified bottom-up CH4 of 772.46 t for 2025.
2. `POST /api/data/ogmp-surveys {"facility_id":169,"year":2025,"survey_date":"2025-06-01","measured_rate_kg_hr":400}` (no status given, as the "Export to OGMP" and manual forms may do).
3. `GET /api/data/ogmp-surveys?facilityId=169`.
4. Repeat for a year with no bottom-up inventory (2010, 50 kg/h).

## Input
Top-down 400 kg/h × 8760 h = 3,504 tCH4 against bottom-up 772.46 tCH4.

## Expected
Variance = (3504 − 772.46)/772.46 = +353.6 %, which exceeds the 20 % threshold. Status should be "Discrepancy Flagged", derived server-side. With a zero bottom-up, variance should be null/"N/A" and the status "Discrepancy Flagged", as `/ogmp-metrics` itself reports.

## Actual
- Case 1: stored and returned `variance_pct 353.62, variance_flag true, reconciliation_status "Reconciled"`.
- Case 2 (zero bottom-up): `bottom_up_tch4 0.0, variance_pct 0.0, variance_flag true, reconciliation_status "Reconciled"`. The survey table then shows a green "+0.0 %" and a green "Reconciled" badge.
- The seed data has the same contradiction (e.g. survey id 2: flag 1, status "Reconciled").

## Evidence
`audit/work/D/s8.py` output. Repro: `audit/repro/<ID>.py`.

## Root Cause
The reconciliation status is a free-text client field with a "Reconciled" default and is never tied to the computed flag. `None` variance is coerced to 0.0 on read. The stored `bottom_up_tch4` / `variance_pct` are also a snapshot taken at save time and never refreshed when emissions change.

## Impact
The OGMP 2.0 top-down/bottom-up reconciliation evidence shown to users (and available for disclosure) can claim reconciliation for large discrepancies. This contradicts `/api/dashboard/ogmp-metrics`, which flags the same facility.

## Affected Components
routes/data.py (POST/GET /api/data/ogmp-surveys), MethaneIntensity.jsx survey table, MethaneExplorer.jsx survey list, ManageData OGMP form (default 'Reconciled').

## Recommended Fix
Derive `reconciliation_status` server-side from the variance and threshold ("Discrepancy Flagged" / "Reconciled" / "No Bottom-Up"). Only allow an explicit override with a justification. Return `null` variance as null, and recompute bottom-up on read.


---

# BUG-053 — CAP (air-pollutant) emissions bypass maker-checker: POST /api/cap/emissions stores records as "Verified" by default (client-controlled status) for role user; negative mass/concentration accepted

**Status:** Confirmed
**Severity:** High
**Category:** API
**Discovered by:** Agent I (Backend/API/Security)

## Location
`new/server/routes/cap_routes.py:115-183` `create_or_update_cap_emission()` — `record.status = data.get("status", "Verified")` (l.179); no role check beyond `require_facility_access`; no numeric validation (`float(mass_val or 0.0)`, `float(concentration)`). Updating an existing record via `id` also keeps/sets Verified. `/api/cap/compliance` (l.186) sums every CAP record regardless of status.

## Reproduction
1. Log in as `audit_user@audit.local` (role user, West; facility 1 is in scope).
2. `POST /api/cap/emissions {"facility_id":1,"year":2025,"source_module":"combustion","pollutant":"NO2","concentration_mg_nm3":150,"flue_gas_volume_nm3":1e6}`
3. `POST /api/cap/emissions {"facility_id":1,"year":2025,"source_module":"flaring","pollutant":"SO2","mass_tonnes":-5000,"concentration_mg_nm3":-1}`
Script: `audit/repro/<BUG-ID>.py`.

## Expected
Data-entry records created as Pending (the platform's maker-checker rule: only admin entries are auto-Verified; bulk/non-admin entries are Pending), `status` not client-settable, negative mass/concentration rejected with 400.

## Actual
All 200; stored rows: `(NO2, 0.15 t, Verified, created_by 18)`, `(SO2, -5000.0 t, conc -1.0, Verified)`, `(CO, 1.0 t, Verified)`.

## Evidence
```
role=user responses: 200 200 200
{'id': 202, 'source_module': 'flaring', 'pollutant': 'SO2', 'mass_tonnes': -5000.0, 'concentration_mg_nm3': -1.0, 'status': 'Verified', 'created_by': 18}
```

## Root Cause
Status defaulted/taken from the payload; no validation.

## Impact
Unreviewed (and negative) air-pollutant masses enter regulatory CAP totals and Decree 06-138 compliance results as Verified; a user can also overwrite an existing verified CAP record by passing its `id`.

## Affected Components
`/api/cap/emissions` POST, `/api/cap/emissions` GET, `/api/cap/compliance`, CAP report content.

## Recommended Fix
Ignore client `status`; set Pending for non-admin (Verified only via an approval step); validate finite, non-negative numbers; make `/compliance` use Verified records only.


---

# BUG-054 — "Preview Pending Data" and the pending banner are inconsistent with the rest of the dashboard: the toggle changes only the KPIs (categorical/org breakdown and Scope 3 stay Verified-only), and the banner ignores the Supply Chain, Activity and Division filters and omits Scope 3

**Status:** Confirmed
**Severity:** Medium
**Category:** Dashboard
**Discovered by:** Agent F (Dashboard reconciliation auditor)

## Location
`new/server/routes/dashboard.py` `get_batch_dashboard_data()`:
- `include_pending` is passed only to `_query_summary`. `_query_categorical_breakdown`, `_query_scope3_summary`, `_query_intensity_stats` and `get_flaring_summary` hard-code `status == "Verified"`.
- `pending_stats` (~L285-310) filters only `allowed_fids`, `facility_id` and `year`. It ignores `activity`, `division` and `segment`, and it counts Scope 1 and 2 but not Scope 3 Pending rows.
Client: `DashboardEnhanced.jsx` pending banner (~L870-930), `activityChartData` and `getHierarchicalData` (from `categorical_breakdown`).

## Reproduction
1. `python audit/repro/BUG-NNN.py`
2. UI: turn on "Preview Pending Data". Compare the Gross KPI with the Organizational Breakdown rows and the activity donut.
3. UI: set Supply Chain = "Heavy Industry" (or any activity). The banner still says "128 records … 4,686,441,566,968.31 tCO2e".

## Input
Snapshot DB: 114 Pending Scope 1, 14 Pending Scope 2 and 21 Pending Scope 3 rows.

## Expected
- With the toggle on, every panel shows Verified + Pending. SQL V+P: S1+S2 = 8,409,568,816,085.97 t and Scope 3 = 366.85 t. The organizational breakdown equals the Gross KPI.
- The banner describes the filtered population. For Supply Chain = Heavy Industry: 13 S1 + 3 S2 = **16 records**, 4,686,441,120,049 t. For Upstream: 101 S1 rows, 446,561 t. Scope 3 Pending rows are included, or the banner says they are excluded.

## Actual
- Toggle on: Gross KPI = 8,409,568,816,085.97 (correct). Categorical/organizational-breakdown sum = **3,723,127,249,117.66** (Verified only). Scope 3 stays 216.85. Activity donut, categorical overview and flaring panel do not change.
- The banner shows 128 records / 4,686,441,566,968.31 t for every Supply Chain, Activity and Division selection (verified via API for activity=Steel & Iron, division=Metallurgy, segment=Heavy Industry and segment=Upstream). Only the Year and Region (facility) filters change it. The 21 Pending Scope 3 rows are never counted.

## Evidence
```
includePending: Gross KPI=8,409,568,816,085.97 (SQL V+P 8,409,568,816,085.97) | categorical/org-breakdown sum=3,723,127,249,117.66 | Scope3=216.85 (SQL V+P 366.85)
```
The filter matrix is in `audit/work/F/filter_matrix.json` (`pend` stays `{'count': 128, …}` for every activity, division and segment case).

## Root Cause
The `includePending` flag and the filter set are applied per sub-query and not shared. Only `_query_summary` received the flag, and the pending-stats query was written with a subset of the filters.

## Impact
In preview mode the same screen shows two different totals (8.41 T vs 3.72 T) for the same scope. The pending banner overstates or understates the pending volume for filtered views, e.g. it tells an Upstream reviewer there are 4.69 T t pending when their view has 446,561 t.

## Affected Components
`/api/dashboard/batch-all` (pending_stats, categorical_breakdown, scope3_summary, intensity_stats); DashboardEnhanced banner, activity donut, categorical overview, organizational breakdown, Scope 3 pill, flaring panel.

## Recommended Fix
Pass `include_pending` to every sub-query, or show a clear "verified-only" label on panels that ignore it. Apply the same Facility-level activity, division and segment filters to `pending_stats`, and add Scope 3 Pending rows.


---

# BUG-055 — QA Dashboard "IPCC Tier 1 Uncertainty" reports 1σ as ±%, uses only the CO2 column, and includes Draft and Pending records, so it contradicts the Uncertainty page

**Status:** Confirmed
**Severity:** Medium
**Category:** Uncertainty
**Discovered by:** Agent G (Uncertainty Auditor)

## Location
- `new/server/routes/qaqc.py` ~L160-222 (`_norm_unc`, s1/s2/s3 `unc_var`, `overall_uncertainty`) and L598-606 (`tier1_uncertainty`).
- `new/client/src/pages/QADashboard.jsx` L530-548, which displays `±{overall*100}%` with no confidence level.

## Reproduction
1. As admin, POST a Verified stationary_combustion / Natural Gas / 12000 m3 record for 2047.
2. POST the same fuel with `status: "Draft"`, 120000 m3.
3. Compare GET `/api/qaqc/dashboard?year=2047` `tier1_uncertainty` with GET `/api/dashboard/uncertainty?year=2047`.
Script: `audit/repro/<ID>.py`.

## Input
The Verified record totals 22.959 tCO2e. Its stored u_CO2 (1σ) is 0.0559. The Draft record is 10× larger.

## Expected
Both pages report the same inventory quantity. For the Verified inventory at 95 % (IPCC Eq. 3.1): √(5² + 10²) = ±11.18 % on 22.959 t.

## Actual
- QA card: **±5.11 %** on **252.547 t**. The value is 1σ (no k=2), and the total includes the Draft record.
- Uncertainty page: ±22.36 % on 22.959 t. That figure is itself inflated by BUG-018.
On the snapshot, year 2022 shows QA ±2.08 % against the Uncertainty page ±57.18 %, and year 2020 shows 4.09 % against 818.97 %.

## Evidence
Repro output above. `overall_uncertainty = sqrt(Σ(u·E)²)/ΣE`, with `u` taken from `uncertainty_pct` or the CO2 `uncertainty` column only (CH4 and N2O are ignored). The status filter is `status != 'rejected'`, so Draft and Pending are included. No coverage factor is applied.

## Root Cause
The QA dashboard reimplements the aggregation independently. It uses a different subset (all non-rejected records instead of Verified), a different confidence level (1σ instead of 95 %), and a different gas basis (CO2 column only). Its default for missing values is 0.05 for S1/S2 and 0.10 for S3, against the Uncertainty page's 0.10–0.40. The UI labels the result "IPCC Tier 1 Uncertainty ±x%", which reads as a 95 % figure.

## Impact
The two pages give contradictory inventory uncertainty for the same year and facilities, often by more than 10×. The QA figure understates the 95 % uncertainty by about half and covers unapproved data. For CH4-dominated sources (venting, fugitive), where only `uncertainty_ch4` is stored, it falls back to 5 %.

## Affected Components
`/api/qaqc/dashboard` `tier1_uncertainty`, `QADashboard.jsx` KPI card (overall and S1/S2/S3).

## Recommended Fix
Reuse `_query_uncertainty`, or a shared service, for the QA card: Verified status, 95 % (k=2), and CO2e-weighted per-gas uncertainty. Label the confidence level in the UI.


---

# BUG-056 — Custom factors used by Tier 2 records can be deleted: the reference check matches `fuel_type == factor name`, but UI records store the factor id, which SQLite then reuses for the next factor

**Status:** Confirmed
**Severity:** Medium
**Category:** Database
**Discovered by:** Agent C (Tier / Factor Auditor)

## Location
- `new/server/routes/custom_factors.py` `delete_custom_factor()`: `Emission.query.filter(Emission.fuel_type == factor.name)` and `Scope2Emission.source_type == factor.name`.
- `new/client/src/components/Scope1Form.jsx`: in Tier 2 "custom_factor" mode it sends `fuel = fuel_type = String(customFactor.id)` plus `custom_factor_id`.
- `models.py` `CustomFactor.id` is a plain Integer PK (SQLite rowid, no AUTOINCREMENT), so ids are reused.

## Reproduction
1. `python audit/repro/BUG-<ID>.py` (own db).
2. Create a custom factor and a Tier 2 record that uses it, exactly as the UI does.
3. DELETE `/api/custom-factors/<id>`.
4. Create another custom factor.

## Input
Custom factor "Site flare gas EF" (2.0 kg CO2/m3), referenced by record 752 (`fuel_type="102"`, `source_payload.custom_factor_id=102`).

## Expected
409 "referenced by 1 emission records", as the route intends.

## Actual
The DELETE returns 200 and the factor row is removed. The next custom factor created gets id 102 again, so the record's stored fuel_type / custom_factor_id now point to an unrelated factor ("Unrelated diesel EF").

## Evidence
Repro output:
- `DELETE /api/custom-factors/102 -> 200 {'message': 'Custom factor deleted'}`.
- `next custom factor created gets id 102 (same as deleted id)`.

## Root Cause
The reference check compares by name, but the UI links records by id. There is also no FK from emissions to custom_factors, and ids are reused.

## Impact
- The audit trail for Tier 2 records breaks: the factor behind a reported number disappears, or is replaced by another factor under the same id.
- A later recalculation (see the Tier 2 recalculation bug) or an audit lookup resolves the wrong factor.
- The dashboards shared with Tier 2 records cannot be traced to their EF.

## Affected Components
- Custom factor delete (Reference Data / Manage Data pages).
- Tier 2 Scope 1 records created from the UI.
- Scope 2 records referencing custom factors by id, if any.

## Recommended Fix
- Store `custom_factor_id` as a real FK column on emissions.
- Block deletion by id reference (and by the name for legacy rows), or soft-archive factors.
- Use AUTOINCREMENT, or never reuse ids.


---

# BUG-057 — Bulk upload with "Overwrite Duplicates" enabled inserts every in-file duplicate row as a separate record (double counting)

**Status:** Confirmed
**Severity:** High
**Category:** Database
**Discovered by:** Agent J (Database)

## Location
`new/server/background_processor.py` — duplicate-key logic in `_process_row` (Scope 1, ~l.1862-1899), `_process_row_scope2` (~l.1024-1047), `_process_row_scope3_eeio` (~l.1130-1151), `_process_row_scope3` (~l.1259-1281).

## Reproduction
1. `make_db` copy; log in as admin (facility names NULL renamed first to avoid BUG-029).
2. `POST /api/emissions/upload/start` scope=1, `overwrite_duplicates=true`, CSV with the same row three times:
   `2019-05,RNS,mobile,Motor Gasoline,1000,gal,default,DUPTEST`
3. Repeat with `overwrite_duplicates=false`.

## Input
Header `date,facility,process,fuel,quantity,unit,factor type,equipment`; one row repeated 3×.

## Expected
Overwrite mode: the key (facility, year, month, process, fuel, equipment) ends with exactly one record (last row wins). Non-overwrite mode: 1 inserted, 2 rejected as duplicates.

## Actual
- overwrite=true → **3 records inserted** (3 × 8.81 = 26.42 t CO2e instead of 8.81).
- overwrite=false → 1 inserted, 2 rejected "Duplicate record…" (correct).

## Evidence
`audit/repro/BUG-<id>.py` prints `expected: 1 record; actual: 3 records`. Same code shape in Scope 2 and Scope 3 row processors (code inspection).

## Root Cause
A newly-seen key is stored as `batch_keys[key] = None` (the new object has no id yet). On a later in-file hit with overwrite enabled, `existing_id` is None → `existing_obj` is None → the `if existing_obj:` branch is skipped and execution falls through to creating another new record. The "overwrite" option is thus less safe than the default.

## Impact
Users who enable "Overwrite Duplicates" precisely to make re-uploads idempotent get duplicated emissions whenever a file contains a repeated key (common with re-exported spreadsheets); once approved, the Scope 1/2/3 totals are double counted. The DB has no unique constraint on emissions to catch it (only production_data has one). The snapshot already contains 16 Scope 1 duplicate groups (51 rows), 2 Scope 2 and 2 Scope 3 groups, e.g. facility 5 2025-03 flaring 15000 ×5 inserted in the same second.

## Affected Components
Bulk import for Scope 1, Scope 2, Scope 3 (activity-based and EEIO); dashboards/reports summing these tables.

## Recommended Fix
Store the pending object itself in `batch_keys` (as `_process_row_production` does with `batch_prod_map`) and update it in place on in-file repeats; add a DB unique index on the natural key (or at least a QA duplicate check).


---

# BUG-058 — Bulk-upload overwrite rewrites approved records without an audit trail and leaves them "Pending" but still marked approved

**Status:** Confirmed
**Severity:** Medium
**Category:** Database
**Discovered by:** Agent J (Database)

## Location
`new/server/background_processor.py` overwrite branches (Scope 1 ~l.1874-1893, Scope 2 ~l.1036-1045, Scope 3 ~l.1141-1150 and ~l.1270-1279) set `existing_obj.status = "Pending"` but never touch `approved_by`/`approved_at`; the whole `_process_file_thread` never calls `log_activity_and_notify` (no ActivityLog for any bulk import).

## Reproduction
1. `make_db` copy; admin. Record id 7 (RNS, pneumatic, 10 devices, eq 7) is Verified, `approved_by=1`, `approved_at=2026-09-22 19:15`.
2. Upload scope=1 CSV with `overwrite_duplicates=true`: `2026-09,RNS,pneumatic,Pneumatic Controller - High Bleed,20,devices,default,7`.
3. Inspect record 7 and `activity_log`.

## Input
As above.

## Expected
Status reset to Pending **and** `approved_by`/`approved_at` cleared (as the manual edit paths do: `emissions.py:3426/3481`, `scope2.py:379`, `scope3.py:240/283`); an ActivityLog UPDATE/IMPORT entry with old and new values.

## Actual
Record 7: `status=Pending, approved_by=1, approved_at=2026-09-22 19:15:13, quantity 10→20, co2e 2325.12→4650.24`. **Zero** activity_log rows were written for the upload (only notifications to admins).

## Evidence
`audit/repro/BUG-<id>.py`; `audit/work/J/bulk.py`. `grep log_activity background_processor.py` → no matches.

## Root Cause
Overwrite branches only partially reset maker-checker state; bulk processor has no audit logging at all.

## Impact
Verified inventory values can be replaced in bulk with no record of the previous value or who changed it (verifier/ISO 14064 audit-trail gap). Records end in a contradictory state (Pending yet carrying an approver and approval time), so any report/QA logic using `approved_by IS NOT NULL` treats them as approved; the approval evidence refers to numbers that no longer exist.

## Affected Components
Bulk import Scope 1/2/3 (all scopes, incl. production/sources/facilities/custom-factor uploads, which also write no ActivityLog); Audit Trail page; QA/approval views.

## Recommended Fix
In overwrite branches clear `approved_by`/`approved_at` (and set `updated_by`), capture old values, and write one ActivityLog per overwritten record plus one IMPORT summary per job, committed in the same transaction as the data.


---

# BUG-059 — SBTi target labelled "1.5°C" is not tied to its reduction rate (0.5 %/yr accepted and displayed as 1.5°C); arbitrary pathway strings and future base years accepted; main-dashboard banner hard-codes "SBTi 1.5°C Linear Target"

**Status:** Confirmed
**Severity:** Medium
**Category:** SBTi
**Discovered by:** Agent H (SBTi Auditor)

## Location
`new/server/routes/managedata.py` `manage_sbti()` POST validation (pathway_type is `str(...)` with no whitelist; rate range 0-25 independent of pathway; base_year allowed up to 2035 regardless of current year). `new/client/src/pages/SbtiDashboard.jsx` (rate input editable independently of the pathway buttons; header "SBTi Decarbonization Pathway (1.5C)"). `new/client/src/pages/DashboardEnhanced.jsx` ~1532: series `sbti_target` named "SBTi 1.5°C Linear Target" regardless of `pathway_type`/`reduction_rate_pct`.

## Reproduction
1. `python C:/Users/samsung/Desktop/H2/audit/repro/<BUG-ID>.py`
2. POST `{base_year:2020, base_year_emissions:1000, target_year:2030, reduction_rate_pct:0.5, pathway_type:"1.5C"}` → 201.
3. POST with `pathway_type:"foo"` → 201; with `base_year:2030,target_year:2031` (future base year, no data possible) → 201.
4. `GET /api/dashboard/sbti-trajectory` → `pathway_type "1.5C"`, `target_emissions_final 950`.

## Input
As above.

## Expected
SBTi 1.5°C linear absolute contraction requires ≥ 4.2 %/yr (WB2C ≥ 2.5 %/yr): a 2020→2030 1.5°C target must be ≤ 1000×(1−0.042×10) = 580 t. Pathway must be one of the supported values and consistent with the rate (or the label derived from the rate). Base year should not be in the future (SBTi requires the most recent year with verified data, ≥ 2015).

## Actual
All accepted; the page and the dashboard banner present a 5 % reduction over 10 years as a "1.5°C" pathway. The main-dashboard banner calls the corporate line "SBTi 1.5°C Linear Target" even for WB2C or custom rates.

## Evidence
Repro output: three `expected 400, actual 201` lines; `pathway shown '1.5C', target_emissions_final 950.0`.

## Root Cause
No cross-field validation between `pathway_type` and `reduction_rate_pct`; free-text pathway; hard-coded label in DashboardEnhanced.

## Impact
Misleading claim of 1.5°C alignment on the SBTi page, exports and executive dashboard.

## Affected Components
`/api/manage/sbti` POST; SbtiDashboard.jsx header/legend/CSV; DashboardEnhanced.jsx SBTi banner; ManageData.jsx SBTi tab (same POST).

## Recommended Fix
Whitelist pathway ∈ {1.5C, WB2C, custom}; enforce rate ≥ 4.2 for 1.5C and ≥ 2.5 for WB2C (or label "Custom"); reject base_year > current year; use `sbtiData.pathway_type`/rate in the dashboard banner label.


---

# BUG-060 — Scope 2 manual entries and Scope 2 bulk imports by a superuser are auto-Verified, while Scope 1 and Scope 3 require admin approval (inconsistent maker-checker)

**Status:** Confirmed
**Severity:** Medium
**Category:** API
**Discovered by:** Agent I (Backend/API/Security)

## Location
- `new/server/routes/scope2.py:236-241` — `initial_status = "Verified" if user.role in ["admin", "superuser"] else "Pending"` (comment cites "D-04").
- `new/server/routes/scope2.py:567` — bulk import: `bulk_status = "Verified" if user.role in ["admin", "superuser"] else "Pending"`.
- Compare `routes/scope3.py:94` / `:389` and `routes/emissions.py:3196` — "only admin role auto-verifies; all other roles (superuser, user) require admin approval"; project rule: bulk imports → Pending.

## Reproduction
1. Log in as `audit_superuser@audit.local`.
2. `POST /api/scope2` (facility 1, 1,000,000 kWh), `POST /api/scope3`, `POST /api/emissions/`, `POST /api/scope2/bulk-import` (1 record).
3. Read back statuses.
Script: `audit/repro/<BUG-ID>.py`.

## Expected
Superuser entries Pending in all scopes (and bulk imports always Pending), awaiting a second person's approval.

## Actual
Scope 1 id 752 → Pending, Scope 3 id 29 → Pending, Scope 2 ids 38 (manual) and 39 (bulk) → **Verified, approved_by = 17 (the superuser themself)**.

## Evidence
```
actual: scope1 [{'id': 752, 'status': 'Pending'}] scope3 [{'id': 29, 'status': 'Pending'}] scope2 [{'id': 38, 'status': 'Verified', 'approved_by': 17}, {'id': 39, 'status': 'Verified', 'approved_by': 17}]
```

## Root Cause
Scope 2 routes use a different role list for auto-verification than Scope 1/3 and than the documented bulk-import rule.

## Impact
A superuser self-approves Scope 2 data (including whole bulk files) straight into Verified dashboard/report totals with no second reviewer — segregation of duties is violated for Scope 2 only. If D-04 truly intends superuser auto-verification, Scope 1/3 are wrong instead; either way the workflow is inconsistent.

## Affected Components
`POST /api/scope2`, `POST /api/scope2/bulk-import`; Scope 2 dashboard/report totals.

## Recommended Fix
Use one shared status policy helper for all scopes (admin → Verified, others → Pending; bulk → Pending).


---

# BUG-061 — Dashboard "Emissions by Source" mis-classifies process types: fuel-gas combustion (6.47 M t) shown as "Other", pneumatics/tanks/dehydrators/unloading/completions as "Other" instead of Venting, fugitives merged into "Venting", mobile combustion labelled "Stationary Combustion"

**Status:** Confirmed
**Severity:** Medium
**Category:** Dashboard
**Discovered by:** Agent F (Dashboard reconciliation auditor)

## Location
- `new/server/routes/dashboard.py` `_query_summary()` `SOURCE_MAP` (~L555-570). It matches substrings for "combustion", "flaring"/"flare", "vent" and "fugitive" (the last mapped to **venting**), and sends everything else to "other".
- `new/client/src/pages/DashboardEnhanced.jsx` Detailed Breakdown labels the `combustion` bucket "Stationary Combustion" (~L1630).

## Reproduction
1. `python audit/repro/BUG-NNN.py`
2. UI: Dashboard, All Years. Look at the "Emissions by Source" donut and the Detailed Breakdown rows.

## Input
Snapshot Verified Scope 1 rows. Process types present: `fuel_gas` (10 rows, 6,467,367.87 t), `pneumatic`, `tank_flashing`/`tank_working`/`tank_breathing`, `dehydrator`, `agr`, `unloading`, `completions`, `drilling`, `loading`, `mobile`, `mobile_combustion`, `fugitive_equipment_leaks`, `fugitive`.

## Expected
Classification by source category, as in the platform's own dispatcher and the API Compendium: fuel gas is combustion; pneumatic, tank, dehydrator, AGR, unloading, completion and drilling are vented; fugitives are a separate category, or at least not called "Venting"; mobile combustion is not "Stationary".
Independent split: Combustion 3,723,123,046,693.43 · Flaring 2,199,048.57 · Venting 140,187.52 · Fugitive 323,458.97 · Other **26.56**.

## Actual
API/UI: Combustion 3,723,116,579,281.52 · Flaring 2,199,048.57 · Venting 460,645.31 (includes fugitives) · Other **6,470,439.64**. The UI "Other Sources 6.5M" is 99.95 % fuel-gas combustion. Vented CH4 sources (pneumatics, tanks, dehydrator, unloading) are hidden in "Other". `mobile_combustion` is shown in the "Stationary Combustion" row, while `mobile` goes to "Other".

## Evidence
```
expected: {'other': 26.56, 'combustion': 3723123046693.43, 'flaring': 2199048.57, 'venting': 140187.52, 'fugitive': 323458.97}
API     : {'combustion': 3723116579281.52, 'flaring': 2199048.57, 'venting': 460645.31, 'other': 6470439.64}
fuel_gas combustion CO2e=6,467,367.87 reported under 'Other Sources'
```

## Root Cause
A hand-written, incomplete substring map is used instead of the dispatcher's process-type to category mapping. The client relabels the combustion bucket as "Stationary".

## Impact
The source mix on the dashboard (and in the Detailed Breakdown) misreports where emissions come from. Venting and fugitives, the key methane categories for OGMP and methane regulation, are mixed together or hidden in "Other", and a large combustion source is shown as "Other".

## Affected Components
`/api/dashboard/batch-all` and `/summary` (combustion/flaring/venting/other fields); DashboardEnhanced "Emissions by Source" donut and Detailed Breakdown.

## Recommended Fix
Classify with the dispatcher's canonical process-type categories (combustion stationary/mobile, flaring, vented, fugitive, process). Add a `fugitive` bucket, and label the combustion row "Combustion", or split it into stationary and mobile.


### Additional confirmation (BUG-029)

Independently confirmed by Agent B (Emissions Auditor). The same NULL-name facilities also **break every server-side bulk import** for Global-scope users (admin), for all scopes.
- `background_processor._process_file_thread` L332 `fac_name_map = {fac.name.lower(): fac ...}` raises on the first NULL name. POST /api/emissions/upload/start jobs for scope 1, 2 and 3 all end with `status: error, errors: ["Fatal error: 'NoneType' object has no attribute 'lower'"]`, processed 0 (`audit/work/B/t11.py`, `t12.py`, db agentB_bulk = pristine snapshot copy).
- `POST /api/emissions/bulk-upload` (routes/emissions.py L505, same pattern) returns **500 Internal server error**.
- Region-scoped users (West) are unaffected, because the NULL-name facilities have region NULL and are filtered out by `get_allowed_facility_ids`.
Additional affected components: background_processor.py:332 and routes/emissions.py:505. `cf.name.lower()` on L339/L509 has the same hazard for custom factors with NULL names.
Severity note: on the audited snapshot, admin cannot bulk-import any Scope 1/2/3 data at all.


---

# BUG-062 — Uncertainty display inconsistencies: EmissionResult shows the ±1σ (68 %) band as the "Confidence Interval", Scope 2/3 tables use k=1.96 while everything else uses k=2, and the Uncertainty page badge thresholds contradict its legend

**Status:** Confirmed
**Severity:** Low
**Category:** UI
**Discovered by:** Agent G (Uncertainty Auditor)

## Location
- `new/client/src/components/EmissionResult.jsx` L19-32 and L86-100 (`margin = value * uncertainty`, tooltip "Confidence Interval: lo - hi"). This component is shown after every Scope 1/2/3 save.
- `Scope2Form.jsx` L755 and `Scope3Form.jsx` L751 (`entry.uncertainty * 1.96 * 100`). Compare `calculations/uncertainty.py COVERAGE_FACTOR_95 = 2.0`, `CalculationDetails.jsx` (`* 200`), and `/api/dashboard/uncertainty` (k=2).
- `pages/UncertaintyAssessment.jsx` L150-154 (`<0.1` low, `<0.2` medium, else high). The legend in the same file (L284-296) and the backend `level` (dashboard.py ~L2590) use ≤10 % / ≤30 %.

## Reproduction
1. POST a stationary_combustion / Natural Gas / 1000 m3 record. The API returns `uncertainty.co2 = 0.0559` (1σ).
2. The result panel renders "±0.1068 t" with the tooltip "Confidence Interval: 1.8044 - 2.0181 tonnes".
Script: `audit/repro/<ID>.py` (API call plus source assertions).

## Expected
Label the interval as 1σ, or show the 95 % CI (k=2): 1.6976 - 2.1250 t. Use one coverage factor everywhere. Use the same level thresholds in the badge, the legend and the backend.

## Actual
- The result panel shows a 68 % interval as the CI, about half the width of the 95 % CI the rest of the app reports.
- The Scope 2/3 "95 % CI" column uses 1.96, which differs by 2 % relative from the k=2 value shown elsewhere for the same record.
- An inventory at ±25 % gets a red "high" badge, while the legend and the backend category level call it "medium".

## Evidence
Repro output. Source lines are cited above.

## Root Cause
There is no shared convention for confidence level, coverage factor or level thresholds between components.

## Impact
Users are shown an uncertainty range that is too narrow on the result panel, and the pages disagree on confidence levels. The effect is cosmetic or misleading rather than a stored-data error.

## Affected Components
EmissionResult (Scope1/2/3 forms), Scope2Form and Scope3Form history tables, UncertaintyAssessment badge.

## Recommended Fix
Render `value ± 2·u·value` and label it "95 % CI (k=2)". Replace 1.96 with the shared constant. Use the backend-provided `level` or the same thresholds for the inventory badge.


---

# BUG-063 — Tier 2 custom factors whose unit is not "kg/<unit>" are misapplied (Manage Data form stores a bare activity unit): tonne factors ×1000 (×10⁶ with kg activity), no volume/mass conversion at all; unknown units such as kg/TJ or kg/GJ are applied 1:1

**Status:** Confirmed
**Severity:** High
**Category:** Calculation
**Discovered by:** Agent C (Tier / Factor Auditor)

## Location
- `new/client/src/pages/ManageData.jsx` (~line 2241). The "Custom Factor" form stores `unit` as the bare activity unit (`scf | m³ | gal | bbl | kg | tonne`), with the values labelled "CO₂ Factor (kg/unit)".
- `QuickAddCustomFactorModal.jsx`, by contrast, stores `kg/scf`, `kg/MMBtu` and so on. Two conventions exist for the same column.
- `new/server/routes/custom_factors.py` create/update/import accept any `unit` string without validation.
- `new/server/calculations/dispatcher.py` `_generic_calculation()` (~1305-1420):
  - `f_denom` is `""` when the unit has no "/", so no activity→factor unit conversion is done.
  - `f_num == "tonne"` is read as a tonne numerator (`is_tonne`), so kg/tonne values are taken as t/tonne.
  - Any unrecognised unit (kg/GJ, kg/TJ, kg/MJ, t/TJ) is silently applied 1:1 to whatever the activity unit is.

## Reproduction
1. `python audit/repro/BUG-<ID>.py` (own db). It creates Manage-Data-style factors and Tier 2 records with `custom_factor_id`, as Scope1Form does.
2. Additional cases are in work/C/t3.py:
   - factor `kg/TJ` = 56,100 with activity 10 GJ;
   - factor `kg/GJ` = 56.1 with activity 1000 m3.

## Input / Expected / Actual (t CO2)
| Factor | Activity | Expected | Actual | Ratio |
|---|---|---|---|---|
| 3170 kg/tonne ("tonne") | 1 tonne | 3.17 | 3170 | ×1000 |
| 3170 kg/tonne ("tonne") | 1000 kg | 3.17 | 3,170,000 | ×10⁶ |
| 3.17 kg/kg ("kg") | 1 tonne | 3.17 | 0.00317 | ÷1000 |
| 10.21 kg/gal ("gal") | 1 bbl | 0.4288 | 0.01021 | ÷42 |
| 0.0541 kg/scf ("scf") | 1000 m3 | 1.9105 | 0.0541 | ÷35.3 |
| 1.9 kg/m3 ("m³") | 1000 scf | 0.0538 | 1.9 | ×35.3 |
| 56,100 kg/TJ | 10 GJ | 0.561 | 0.000561 | ÷1000 |
| 56.1 kg/GJ | 1000 m3 | needs HHV; should be rejected | 56.1 (m3 treated as GJ) | — |

## Evidence
- Every row of the repro is flagged WRONG, with HTTP 201 and calc_method `api2021_generic`.
- The ManageData `tonne` case is wrong even when the activity is in the same unit (×1000).
- The seed snapshot already contains a factor stored this way (custom_factors id 1, unit `scf`).

## Root Cause
There is no canonical unit format for custom factors, and the calculator does not validate units. It parses the numerator from the text before "/", and treats a unit without a "/" as having no denominator. Units it does not recognise fall through unconverted, with no error.

## Impact
Tier 2 emissions are wrong by factors of 35 up to 10⁶, depending on the unit chosen in the app's own Manage Data form. An IPCC-style factor (kg/TJ, kg/GJ) is off by 1000×, or is dimensionally meaningless without an error.

## Affected Components
- Manage Data custom-factor form, Reference Data, and custom factor import.
- Tier 2 manual entry and bulk upload.
- Any dashboard or report built on those records.

## Recommended Fix
- Store custom factors with an explicit numerator/denominator unit from a whitelist, and migrate bare units to `kg/<unit>`.
- In the calculator, reject factor units it cannot convert to the activity unit instead of applying them 1:1.
- Add GJ/TJ/MJ energy denominators, and require an HHV for energy ↔ volume conversion.


---

# BUG-064 — Categorical Emissions Overview groups facilities by name instead of id: six distinct facilities are merged into one "Updated Facility" card (3.19 T t)

**Status:** Confirmed
**Severity:** Low
**Category:** Dashboard
**Discovered by:** Agent F (Dashboard reconciliation auditor)

## Location
`new/server/routes/dashboard.py` `_query_categorical_breakdown()`: `group_by(Facility.activity, Facility.division, Facility.name, Facility.field)` for Scope 1, 2 and 3, and `output_map` is keyed on the same tuple. `Facility.id` is never included.
Rendered by `DashboardEnhanced.jsx` (Categorical overview region cards, Organizational Breakdown).

## Reproduction
1. `python audit/repro/BUG-NNN.py`
2. UI: Dashboard, Categorical Emissions Overview, Production. There is one "Updated Facility 3.2T tCO₂e" card.

## Input
Facilities 150, 155, 158, 160, 162 and 165 all have name "Updated Facility", activity Production, division Upstream and field NULL. Facility names are not unique; the create/update API allows duplicates.

## Expected
One card per facility (6 cards, each 531,145,000,044 t approx.), or names disambiguated.

## Actual
The API returns one merged row, total 3,186,870,000,265.25 t. The UI shows a single "Updated Facility 3.2T" card.

## Evidence
`facilities named 'Updated Facility' with Verified emissions: 6 ids=[150, 155, 158, 160, 165, 162]; categorical cards returned: 1 -> [3186870000265.25]`

## Root Cause
The group key uses display attributes instead of the facility primary key.

## Impact
Per-facility drill-down is wrong whenever two facilities share a name and field, which the data model does not prevent. The merged card overstates one "facility" by the number of namesakes.

## Affected Components
`/api/dashboard/batch-all` (categorical_breakdown), `/api/dashboard/categorical-breakdown`; DashboardEnhanced categorical cards and organizational breakdown.

## Recommended Fix
Group by `Facility.id`, return `facility_id`, and key `output_map` on it. Consider a uniqueness constraint or warning on facility names.


---

# BUG-065 — Custom factor names are not unique, yet bulk import resolves factors by name: the most recently created same-named factor is silently applied

**Status:** Confirmed
**Severity:** Medium
**Category:** Database
**Discovered by:** Agent J (Database)

## Location
- `new/server/models.py` `CustomFactor.name` — `index=True`, no unique constraint.
- `new/server/routes/custom_factors.py` POST (l.84) / PUT (l.164) / `/import` — no duplicate-name check; PUT allows renaming onto an existing name.
- `new/server/background_processor.py:338-339` `cf_name_map = {cf.name.lower(): cf for cf in CustomFactor.query.all()}` (last row wins); `routes/emissions.py:508-509` same pattern (per-user).

## Reproduction
1. `make_db` copy; admin.
2. `POST /api/custom-factors` `{"factor_name":"AuditDupGas","unit":"m3","co2_factor":1}` → 201 (id 102).
3. Same with `co2_factor: 100` → 201 (id 103).
4. Bulk upload Scope 1 CSV `2018-03,RNS,combustion,AuditDupGas,1000,m3,custom,CFDUP` (factor type custom).

## Input
Two factors named "AuditDupGas" (1 and 100 kg CO2/m3), 1000 m3 activity.

## Expected
Second create rejected (409) or the uploader forced to disambiguate; result would be 1.0 t CO2 with the first factor.

## Actual
Both saved. Import silently used factor id 103: `ef_used_co2=100, co2_emissions=100 t` (100× the other factor). Which factor is chosen depends only on row order in the table; the delete-guard (`fuel_type == factor.name`) also cannot tell same-named factors apart.

## Evidence
`audit/repro/BUG-<id>.py` (`audit/work/J/cfdup.py`).

## Root Cause
Custom factors are referenced by free-text name everywhere, but the name has no uniqueness constraint or validation (including case-insensitive collisions, since lookups use `lower()`).

## Impact
Any organisation with two users each saving e.g. "Fuel Gas" (or a superuser saving a revised version under the same name) gets Tier 2 imports computed with whichever was created last, without warning; emissions can be off by the ratio of the two factors.

## Affected Components
Custom factor CRUD and import, Scope 1 bulk import (background processor and `/api/emissions/import` style path), custom-factor delete guard.

## Recommended Fix
Add a (case-insensitive) unique constraint on `custom_factors.name` (or name+unit+version) and reject duplicates on create/rename/import; reference factors by id in records.


---

# BUG-066 — AGR form throughput units MMscfd / Mcf/day / m³/yr are ignored by the server (read as MMscf/yr): CO2 365× low, 2.7× high, or 28,317× high

**Status:** Confirmed
**Severity:** Critical
**Category:** Calculation
**Discovered by:** Agent K (Frontend/UI)

## Location
- `new/client/src/components/scope1/AGRForm.jsx` (unit dropdown: MMscf/yr, MMscfd, Mcf/day, m³/yr → `agr_unit`)
- `new/client/src/components/Scope1Form.jsx` ≈lines 803-819 (every formData key incl. raw `agr_throughput`/`agr_unit` copied into `calc_inputs.agr`) and ≈lines 943-950 (client-side conversion to top-level `amount`, with an extra `/1000` for m³/yr)
- `new/server/calculations/dispatcher.py` AGR branch (≈line 1018) reads `agr_throughput` + `agr_unit` and calls `_normalize_volume(..., "mmscf")` (≈line 122), which only knows scf/mcf/m3/bbl and returns the value unchanged for "mmscf/day", "mcf/day", "m3/yr".

## Reproduction
1. UI (:5191) as admin → Emissions → Scope 1, Region = first facility, Process = Acid Gas Removal (AGR).
2. Gas Throughput = 28316800, unit "m³/yr" (= 1000 MMscf/yr), Inlet CO2 5 %, Outlet CO2 0.5 %; Calculate & Submit.
3. Same via API with equivalent throughputs in each unit (`audit/repro/BUG-<id>.py`).

## Input
1000 MMscf/yr expressed in each unit offered by the dropdown; CO2 5 % in, 0.5 % out.

## Expected
Hand calculation: 1000 MMscf × (5 − 0.5) % = 45 MMscf CO2 = 4.5e7 scf ÷ 379.5 scf/lbmol × 44.01 lb/lbmol × 0.4536 kg/lb ≈ **2,367 t CO2** — identical for every unit.

## Actual
| Input | CO2 (t) | totalCo2e (t) |
|---|---|---|
| 1000 MMscf/yr | 2,371.4 | 2,828.7 (correct) |
| 2.740 MMscfd | 6.5 | 7.7 (365× low) |
| 2,739.7 Mcf/day | 6,497.0 | 7,749.8 (2.74× high) |
| 28,316,847 m³/yr | 67,150,409 | 80,098,823 (28,317× high) |

Browser submission (record id 752 in audit/db/ui.db): request `amount: 1, unit: "MMscf"`, `calc_inputs.agr = {agr_throughput: 28316800, agr_unit: "m3/yr", ...}`; response/record `co2e_total = 80,436,130 t` for a 1000 MMscf/yr unit, and stored activity `amount = 1 MMscf` (client conversion divides m³ by 28,316.8 **and** by 1000; correct is ÷28,316.8 → 1000 MMscf).

## Evidence
Playwright capture `audit/work/K/t_agr.mjs` (POST body + 201 response above); API run `audit/work/K/agr2.py`; `_normalize_volume("28316800","m3/yr","mmscf")` returns 28316800.

## Root Cause
Client converts the throughput only into `amount`, but also forwards the raw throughput and unit string in `calc_inputs`; the dispatcher prefers `agr_throughput` and its `_normalize_volume` has no rate units (`/day`, `/yr`) and no `m3/yr`, falling through to "already MMscf". The client's m³/yr branch additionally has a spurious `/1000`.

## Impact
Any AGR record entered in three of the four offered units is wrong by 2.7× to 28,000×; a single m³/yr entry adds ~80 Mt CO2e to the inventory and is auto-Verified for admin. Stored activity amount is also 1000× wrong for m³/yr.

## Affected Components
Scope 1 AGR manual entry (Tier 3; AGR is only offered as Tier 3), dashboard/intensity/SBTi totals that include these records.

## Recommended Fix
Server: handle rate/annual units explicitly (`mmscf/day`×365, `mcf/day`×0.365, `m3/yr`/`m3`÷28,316.85 etc.) and reject unknown units instead of passing through. Client: send one canonical value (MMscf/yr) in both `amount` and `calc_inputs.agr.agr_throughput`, and remove the extra `/1000`.


---

# BUG-067 — Maker-checker bypass through edit and delete: a superuser can approve a record they just edited, silently re-date/re-assign Verified records, and a user can hard-delete their own Verified records

**Status:** Confirmed
**Severity:** High
**Category:** Security
**Discovered by:** Agent I (Backend/API/Security)

## Location
- `new/server/routes/emissions.py:3423-3480` `update_emission()` — status reset to Pending only when a *non-admin/superuser* edits a Verified record, or when "physical" keys change and user ≠ admin. `year`, `month`, `facility_id` edits by a superuser leave the record Verified. No `updated_by`/last-maker is recorded.
- `emissions.py:4488` `approve_emission()` — segregation check compares only `created_by == user.id`, so the person who last changed the values can approve them.
- `emissions.py:3341-3395` `delete_emission()` — a `user` may delete any record it created regardless of status (Verified included); no review step. (Same patterns exist in `scope2.py` / `scope3.py` PUT/DELETE.)

## Reproduction
1. Superuser (West) `PUT /api/emissions/145 {"year":2019}` (Verified record, facility 2).
2. User creates Scope 1 record (Pending, created_by=user); superuser `PUT /api/emissions/<id> {"quantity":999999}`; superuser `POST /api/emissions/approve/<id>`.
3. User `DELETE /api/emissions/<id>` of that now-Verified record.
Script: `audit/repro/<BUG-ID>.py`.

## Expected
(1) Record returns to Pending (a year change moves emissions between reporting periods). (2) 403 — the superuser is the maker of the approved values. (3) Deleting Verified data requires reviewer action (or 403).

## Actual
(1) `{'year': 2019, 'status': 'Verified'}`. (2) 200, record `quantity 999999, status Verified, approved_by 17` (the editor). (3) 200, row deleted.

## Evidence
```
1) superuser changes year 2020->2019 on Verified #145: expected Pending, actual {'year': 2019, 'status': 'Verified'}
2) superuser edits qty then approves own edit: expected 403, actual 200 [{'quantity': 999999.0, 'status': 'Verified', 'approved_by': 17}]
3) user deletes own Verified record #752: expected 403 / deletion request pending review, actual 200, rows left=0
```
Activity log for #752 shows CREATE (Audit user) → UPDATE quantity (Audit superuser) → approved by Audit superuser.

## Root Cause
Segregation of duties keyed only on `created_by`; the status-reset rule exempts superusers for non-quantity fields; delete has no status gate.

## Impact
One person can put arbitrary values into Verified totals (edit + self-approve), move Verified emissions between reporting years/facilities without review, and remove Verified data — defeats the maker-checker control that dashboards rely on (they aggregate Verified only).

## Affected Components
`PUT/DELETE /api/emissions/<id>`, `POST /api/emissions/approve/<id>`, `/approve/batch`; Scope 2/3 equivalents.

## Recommended Fix
Track `last_modified_by`; block approval when approver is creator OR last modifier; any edit by non-admin (incl. superuser) to a Verified record → Pending; forbid deleting Verified records for non-admins (or route via a pending-deletion review).


---

# BUG-068 — Purchased steam/heat (`indirect_steam`) and CHP allocation (`cogen_allocation`) are accepted as Scope 1 process types and added to Scope 1 totals (Scope 2 counted as Scope 1; CHP double counting)

**Status:** Confirmed
**Severity:** High
**Category:** Emissions
**Discovered by:** Agent B (Emissions Auditor)

## Location
- `new/server/routes/emissions.py` `add_emission()`: any `process_type` is accepted; no check against Scope 2 categories.
- The Scope 1 CSV template (`emissions.py` ~L1023 lists `indirect_steam` as a Scope 1 `process_type`; sample row 17 at ~L1966 is "Tier 3 – Indirect Steam").
- `background_processor._process_row` (scope 1).
- `client/src/utils/EmissionFactors.js` PROCESS_TYPES (L1358-1359) offers `indirect_steam` / `cogen_allocation` to Scope 1 forms, and BulkImportModal.jsx:534 does the same.
- `routes/dashboard.py` `_query_summary` sums every `emissions` row into `scope1_total` (the unmatched ones go to the "other" bucket).

## Reproduction
1. Admin `POST /api/emissions/` `{"process_type":"indirect_steam","facility_id":1,"year":2030,"month":1,"amount":1000,"quantity":1000,"unit":"MMBtu","heat_unit":"mmbtu","boiler_eff":0.8,"fuel":"Natural Gas"}`. The response is 201 and the record is Verified.
2. In a fresh process, `GET /api/dashboard/summary?year=2030`.
3. Scope 1 CSV bulk upload row `2038-05,ADR,indirect_steam,Natural Gas,1000,MMBtu,default` also stores an `emissions` (Scope 1) row with co2e 53.11 t.

## Input
1000 MMBtu of purchased steam/heat (NG boiler, 80 % efficiency).

## Expected
Purchased steam/heat is Scope 2 (GHG Protocol Scope 2 Guidance). It should be stored in `scope2_emissions` via /api/scope2, which has a dedicated `indirect_steam` path. Hand calc: 1000 / 0.8 x 53.06 kg = **66.33 t CO2, reported as Scope 2**, with Scope 1 unchanged.

A CHP owned by the reporter is Scope 1 in full, via its fuel combustion. The heat-share allocation is not an additional Scope 1 emission.

## Actual
- `summary` → `scope1_total: 53.1145, other: 53.1145, scope2_total: 0` (`audit/work/B/t7.py` + `t8.py`). The purchased steam is booked as **Scope 1**.
- It was also computed as plain fuel combustion (`calc_method api2021_generic`): boiler efficiency was ignored, and CH4/N2O were added.
- `cogen_allocation` entered through the Scope 1 route is stored in Scope 1 too. The snapshot contains 4 such Pending rows (ids 620-623, "total_emissions 1000 tCO2e", allocated 346.6-562.5 t each, 2034 t in total). These would be added to Scope 1 on approval, on top of the CHP's fuel combustion, which is double counting. It would also be double counting if the same CHP heat is entered in the Scope 2 form.
- The snapshot also holds 6 `indirect_steam` rows in the Scope 1 table (all 0 t, Pending).

## Evidence
```
201 {'calculation_method': 'api2021_generic', 'emissions': {... 'totalCo2e': 53.1145}, 'record': {'process_type': 'indirect_steam', ...}}
[{'... 'other': 53.1145, 'scope1_total': 53.1145, 'scope2_total': 0, 'year': 2030}]
bulk: {'process_type': 'indirect_steam', 'calc_method': 'api2021_generic', 'co2e_total': 53.1145, 'status': 'Pending'}
```

## Root Cause
Scope is implied only by which table a row lands in. The Scope 1 create and bulk paths accept Scope 2 process types (documented as Scope 1 in the template and UI), and the aggregations never exclude them.

## Impact
Scope 1 is overstated and Scope 2 understated for any site recording purchased steam or CHP allocation through the Scope 1 forms or template. With the Scope 2 form also used, emissions are double counted. SBTi, intensity and report splits by scope are wrong.

## Affected Components
POST /api/emissions/, Scope 1 bulk upload/template, Scope1Form process list, dashboard summary/batch-all, reports, intensity.

## Recommended Fix
Reject `indirect_steam`, `cogen_allocation` and `cogen` in Scope 1 create, PUT and bulk, or redirect them to `scope2_emissions`. Remove them from the Scope 1 process list and template. Exclude any legacy rows with these process types from Scope 1 aggregates.


---

# BUG-069 — Deleting a user wipes approved_by/created_by on every record they approved or entered: Verified records lose their maker-checker evidence

**Status:** Confirmed
**Severity:** Low
**Category:** Database
**Discovered by:** Agent J (Database)

## Location
`new/server/routes/auth.py:1090-1112` `delete_user` — `UPDATE <table> SET created_by/approved_by/updated_by = NULL WHERE ... = :uid` across emissions, scope2/3, facilities, custom factors, etc. `ActivityLog.user_id` also nulled (only the free-text `user_name` survives).

## Reproduction
1. `make_db` copy; log in as `it_admin`.
2. User 8 (`test_admin@ghg-test.com`) is `approved_by` on 19 Verified Scope 1 records.
3. `DELETE /api/auth/users/8` → 200.
4. `select count(*) from emissions where status='Verified' and approved_by is null`.

## Input
Snapshot data.

## Expected
Approval provenance stays attached to the record (soft-delete/deactivate the user, or keep an immutable approver name/id), so a Verified record can always show who approved it.

## Actual
Count goes 470 → 489: the 19 records are now "Verified" with `approved_by = NULL` but `approved_at` still set — indistinguishable from records that were never approved through maker-checker (the snapshot already holds 470 such rows; 70 are seed rows, the rest have app-generated UUIDs and cannot be traced to an approver). Only the approval ActivityLog entry's `user_name` text remains, and its `user_id` is also nulled.

## Evidence
`audit/repro/BUG-<id>.py`.

## Root Cause
Hard delete of users combined with nulling every FK to satisfy SQLite FK enforcement; the schema has no user soft-delete or denormalised approver name on records.

## Impact
Verification / assurance (ISO 14064-3, OGMP) needs to prove who approved each figure; after routine staff off-boarding the record-level evidence is gone and `status` contradicts `approved_by`. `created_by` also becomes NULL, so creator-ownership checks for role `user` (`created_by is not None and ...`) no longer apply to those records.

## Affected Components
User deletion; Scope 1/2/3 records, facilities, custom factors, CBAM, OGMP, base-year recalcs; Audit Trail.

## Recommended Fix
Replace hard delete with deactivation (`status='inactive'`), or keep the FKs and block deletion when the user owns approvals; if deletion is required, store approver name/email on the record at approval time.


### Additional confirmation (BUG-047)

Independently confirmed by Agent D (Methane Auditor).
New evidence (own DB copy `agentD_fug`, via real `POST /api/emissions/`, admin, `factor_source=default`, amount 100, unit "count"):
- `process_type=fugitive`, fuel "Fugitive - Valve (Gas/Vapor)" (catalog 0.0045 kg/hr): stored CH4 = 0.00045 t. Expected annual: 100 × 0.0045 × 8760 / 1000 = 3.942 t.
- `process_type=fugitive_component`, fuel "Component - Control Valve" (1.11e-5 t/hr): stored CH4 = 0.00111 t. Expected 100 × 1.11e-5 × 8760 = 9.724 t.
- The snapshot already has Verified rows with this defect: ids 20 and 21 ("Fugitive - Valve (Gas/Vapor)", 50 and 10 sources give 0.000225 t and 0.000045 t CH4).
Additional affected components: methane loss rate %, ch4_intensity and OGMP bottom-up reconciliation (`/ogmp-metrics`, `/intensity-stats`, OGMP export). Understated fugitive CH4 makes top-down/bottom-up variance look like a large "discrepancy". Script: `audit/work/D/s11.py`.


### Additional confirmation (BUG-061)

Independently confirmed by Agent D (Methane Auditor). The same substring-classification root cause also breaks the **methane** process split in `_query_intensity_stats` (`routes/dashboard.py` ~1814-1823):
`if "vent" in ptype → ch4_venting; elif "fugitive"/"leak" → ch4_fugitive; elif "flare" in ptype → ch4_flaring; else → ch4_combustion`.
- `"flare"` is not a substring of `routine_flaring` / `non_routine_flaring` / `safety_flaring` / `flaring`, so **`ch4_flaring` is 0 for every facility**.
- Flaring CH4 slip (6,765.3 t Verified in the snapshot) is reported as `ch4_combustion`.
- Pneumatics, tanks, completions, blowdown, dehydrator, unloading, AGR and drilling CH4 (vented sources) are also reported as `ch4_combustion`.
Evidence (`GET /api/dashboard/intensity-stats?year=all`, admin, `audit/work/D/s3.py`): API gives `ch4_venting 5,196.3`, `ch4_fugitive 12,872.7`, `ch4_flaring 0`, `ch4_combustion 84,320,881`. Hand classification of Verified DB rows gives vented 5,294.1, fugitive 12,872.7, flaring 6,765.3 and combustion 84,314,018.
Additional affected components: `/api/dashboard/intensity-stats` fields `ch4_venting/ch4_fugitive/ch4_flaring/ch4_combustion`, which are not rendered by the current client but are part of the API contract, and the batch-all `intensity_stats` payload.


---

# BUG-070 — POST /api/emissions/reject/<id> has no status check: a superuser can flip an admin-Verified record to Rejected (removing it from all totals) and overwrite its approver

**Status:** Confirmed
**Severity:** Medium
**Category:** API
**Discovered by:** Agent I (Backend/API/Security)

## Location
`new/server/routes/emissions.py:4511-4559` `reject_emission()` — unlike `approve_emission()` (l.4485 `if emission.status not in ["Pending","Draft","Pending Approval"]: 400`) and `reject_batch_emissions()` (filters on pending statuses), the single reject path changes any record's status.

## Reproduction
1. Superuser (West) `POST /api/emissions/reject/24 {"reason":"x"}` — record 24 is Verified, approved_by=1 (admin).
2. Compare `POST /api/emissions/reject/batch {"ids":[24],"scope":"1"}`.
Script: `audit/repro/<BUG-ID>.py`.

## Expected
400 "Record is not pending approval" (consistent with approve and batch reject).

## Actual
200; record becomes `status=Rejected, approved_by=17 (superuser), qa_flag='Rejected: x'`; the admin's approval is overwritten. Batch reject on the same id returns `deleted_count=0`. Repeating the reject also returns 200.

## Evidence
```
before: {'id': 24, 'status': 'Verified', 'approved_by': 1}
actual: 200, after={'status': 'Rejected', 'approved_by': 17, 'qa_flag': 'Rejected: x'}; /reject/batch on a non-pending id deleted_count=0
```

## Root Cause
Missing pending-status guard on the single-record reject.

## Impact
Verified inventory data can be withdrawn from dashboards/reports by a superuser without admin involvement; the audit field `approved_by` loses who originally verified it. Double-submits are not idempotent-safe (each re-reject rewrites approver/time).

## Affected Components
`/api/emissions/reject/<id>` (scope 1/2/3 via `scope` param).

## Recommended Fix
Apply the same pending-status check as `approve_emission`; return 409/400 for already-decided records.


---

# BUG-071 — Dashboard cache is not invalidated after a manual Scope 1 create or a bulk upload: new records are missing from the dashboard for up to 5 minutes (per worker)

**Status:** Confirmed
**Severity:** Medium
**Category:** Dashboard
**Discovered by:** Agent B (Emissions Auditor)

## Location
- `new/server/app.py` L93-116. The `before_commit` hook sets `has_relevant_changes` only if an Emission/Scope2/... object is in `session.new | dirty | deleted` at commit time. `after_commit` clears `DASHBOARD_CACHE` only when that flag is set.
- `routes/emissions.py` `add_emission()` L3218-3221 calls `db.session.flush()` and then `commit()`. After the flush the new row is no longer in `session.new`, so the flag is False. Unlike scope2/scope3/PUT/approve/delete, this route never calls `clear_dashboard_cache()` explicitly.
- `background_processor.py` L578/594 uses `db.session.bulk_save_objects(chunk)`, which never places objects in `session.new`, so there is no invalidation there either.

## Reproduction
1. Run `python audit/repro/BUG-069.py` (own db).
2. `GET /api/dashboard/summary?year=2024` gives total T0.
3. As admin, `POST /api/emissions/` with 1000 MMBtu natural gas, year 2024 (Verified, 53.1145 t).
4. `GET /api/dashboard/summary?year=2024` again, then compare with `SUM(co2e_total)` in the DB.

## Input
One Verified record of 53.1145 tCO2e. Separately, a 5-row Scope 1 CSV upload for year 2038.

## Expected
The summary increases by 53.1145 t right away, as it does after approve, delete and Scope 2/3 creates. Hand calc: 1000 x (53.06 + 0.001x28 + 0.0001x265) / 1000.

## Actual
```
before=3718016910467.4102 after=3718016910467.4102 db=3718016910520.5249 actual diff=0.0000
```
After a completed bulk upload of 5 rows (year 2038), `summary?year=2038&includePending=true` in the same process still returned `[]`. A fresh process returned scope1_total 129.26 t (`audit/work/B/t11.py`, `t13.py`).

## Evidence
See above. Approve and delete in the same session did update the summary immediately (+53.11 / -53.11, `audit/work/B/t9.py`), which isolates the create and bulk paths.

## Root Cause
Cache invalidation depends on detecting pending ORM objects in `before_commit`. This does not work when rows were flushed earlier or written with `bulk_save_objects`.

## Impact
Users who add data, or finish an import, and then open the dashboard see stale totals, KPIs, pending counts and charts (DASHBOARD_CACHE TTL 300 s, every cached query and batch-all). This looks like data loss or a failed upload.

## Affected Components
POST /api/emissions/, all background bulk uploads (scope 1/2/3/production...), /api/dashboard/* cached queries.

## Recommended Fix
Call `clear_dashboard_cache()` explicitly in `add_emission` and at the end of `_process_file_thread`. Alternatively, track changes in an `after_flush` listener, or set `session.info["has_relevant_changes"]=True` at flush time, instead of inspecting `session.new` in `before_commit`.


### Additional confirmation (BUG-029)

Re-test by Agent L (Browser) on baseline2 (audit/baseline2_uncommitted.diff): the client half is fixed — `ManageData.jsx:1313` now uses `(f.name || '').toLowerCase()` and /manage-data renders with a NULL-name facility present. The server half still reproduces: `POST /api/facilities {"region":"West"}` → 201 and the row is stored with `name = NULL`; such facilities appear as blank options in every facility dropdown (Scope 1 "Region" list, dashboard region filter). Repro `audit/repro/BUG-029.mjs` updated to fail only on the API acceptance.


---

# BUG-072 — Pending-records banner ignores the GWP-20 toggle: it always shows GWP-100 tCO2e while every other dashboard figure switches to GWP-20

**Status:** Confirmed
**Severity:** Low
**Category:** Dashboard
**Discovered by:** Agent D (Methane Auditor)

## Location
- `new/server/routes/dashboard.py` `get_batch_dashboard_data()` ~lines 290-320: `pending_stats.totalCo2e = sum(Emission.co2e_total) + sum(Scope2Emission.co2e)` for status Pending. `gwp_horizon` is read and is part of the cache key, but it is not applied to this total.
- `new/client/src/pages/DashboardEnhanced.jsx` ~887-889: renders `{pendingCo2e} tCO₂e` in the banner regardless of `gwpHorizon`.

## Reproduction
1. Snapshot copy (agentD), admin.
2. `GET /api/dashboard/batch-all?facilityId=all&activity=all&division=all&year=2025` → `pending_stats`.
3. The same request with `&gwp_horizon=20` → `pending_stats`.
4. Hand-compute the pending GWP-20 figure from DB rows: Σ Pending S1 (CO2 + CH4·GWP20_CH4 + N2O·GWP20_N2O) + Σ Pending S2 CO2e.

## Input
Year 2025: 112 pending records; pending Scope 1 CH4 = 4,246.68 t.

## Expected
In GWP-20 mode the banner figure should be on the same basis as the KPIs next to it: 678,365.0 tCO2e (app's own AR5 20-yr factors, 82.5 / 268; 695,856 with the correct AR5 84 / 264, see BUG-013).

## Actual
`totalCo2e` = 446,919.3 in both horizons (GWP-100). The banner understates pending CO2e by 34 % in GWP-20 mode, so it disagrees with the amount the hero card jumps by when "Preview Pending" is switched on (summary applies GWP-20 to pending rows).

## Evidence
`audit/work/D/s12.py` output (re-run on the current code, baseline2): `banner GWP-100: 446919.3`, `banner GWP-20: 446919.3`, expected GWP-20 678,364.997. Repro: `audit/repro/<ID>.py`.

## Root Cause
The pending summary sums the stored GWP-100 `co2e_total` and never applies the horizon delta that `_query_summary` applies.

## Impact
Misleading figure next to methane-heavy KPIs in GWP-20 mode. The pending backlog looks a third smaller than it is on the chosen basis.

## Affected Components
/api/dashboard/batch-all `pending_stats`, DashboardEnhanced pending banner.

## Recommended Fix
Include CH4/N2O sums in the pending query and apply the same `get_active_gwp` delta as `_query_summary` when `gwp_horizon=20`, or label the banner figure "GWP-100".


---

# BUG-073 — Scope 2 and Scope 3 create accept a missing or non-numeric year: one year-less Scope 2 record makes the main dashboard (summary/batch-all) return 500, and year-less Scope 3 is in the total but missing from by-year

**Status:** Confirmed
**Severity:** High
**Category:** Emissions
**Discovered by:** Agent B (Emissions Auditor)

## Location
- `new/server/routes/scope2.py` `create_scope2_emission()` (~L159-260) and `routes/scope3.py` `create_scope3_emission()` (~L70-125). They validate only `facility_id`. `year=data.get("year")` and `month=data.get("month")` are stored unvalidated: None, "abc" and 13 are all accepted. Scope 1 POST, by contrast, enforces 1900-2100 and 1-12.
- `routes/dashboard.py` `_query_summary` L508 `yr = int(row.year)` has no None guard, for both the Scope 1 and the Scope 2 loop.
- `routes/dashboard.py` `_query_scope3_summary`: `by_year` skips `y is None`, but `total` (year=all) sums every row.

## Reproduction
1. Run `python audit/repro/BUG-073.py` (own db). Manually:
2. As admin, `POST /api/scope2` with `{"facility_id":1,"source_type":"electricity","electricity_kwh":1000,"emission_factor":0.5}` (no year or month). The response is 201 and the row is Verified with year NULL.
3. `GET /api/dashboard/summary` and `GET /api/dashboard/batch-all`, as admin and as a West-region user.
4. `POST /api/scope3` with `{"facility_id":1,"category":"Category 1","activity_data":1000,"emission_factor":0.5}` (no year), then `GET /api/dashboard/scope3/summary`.

## Input
One 0.5 t Scope 2 row without a year. One 0.5 t Scope 3 row without a year. Also `year:"abc", month:13` for Scope 2, which is accepted (201).

## Expected
Create returns 422 for a missing, non-integer or out-of-range year or month, as Scope 1 does. Aggregations never crash on one bad row. Scope 3 `total` equals the sum of `by_year`.

## Actual
- Scope 2 create returns 201 for no year, and for `year:"abc", month:13`.
- After that, `/api/dashboard/summary` and `/api/dashboard/batch-all` return **500** for admin and for the West-region user (`TypeError: int() argument must be ... not 'NoneType'` at dashboard.py:508). The main dashboard is unusable for every user whose facility scope includes that facility.
- Scope 3 summary: `total 217.35` vs `sum(by_year) 216.85`. The year-less 0.5 t is counted in the headline total but is in no year, so the year chart does not add up to the KPI, and the row drops out of every year-filtered view.

## Evidence
```
scope2 without year -> 201 (expected 422)
batch-all before=200; after: summary=500 batch-all=500 (admin), batch-all as West user=500; expected 200
scope3 without year -> 201 ; scope3 total 217.35 sum(by_year) 216.85
```
(`audit/work/B/t14.py` also shows `year:'abc', month:13` stored as Verified.)

## Root Cause
Scope 2 and Scope 3 create have no date validation, and the summary aggregation casts `row.year` without a guard.

## Impact
Any user with Scope 2 create rights (the admin or superuser auto-Verify path, BUG-060) can take down the organisation dashboard with one API call or one client bug. Year-less Scope 2/3 emissions silently disappear from every year-filtered total, SBTi and intensity figure, while still inflating the all-years Scope 3 KPI.

## Affected Components
POST /api/scope2, POST /api/scope3 (and their PUT paths, which have the same pattern and were not separately verified), dashboard summary/batch-all, scope3 summary, year-filtered reports.

## Recommended Fix
Apply the Scope 1 year/month validation, ideally a shared helper, to the Scope 2 and Scope 3 create, update and bulk paths. Guard `int(row.year)` in the aggregations, skipping or bucketing NULL years as "Unknown" and surfacing them.


---

# BUG-074 — Approve/reject endpoints are not concurrency-safe: two simultaneous approvals of the same record both return 200 (duplicate audit entries; approve+reject race ends in an arbitrary final state)

**Status:** Confirmed
**Severity:** Low
**Category:** Backend
**Discovered by:** Agent I (Backend/API/Security)

## Location
`new/server/routes/emissions.py` `approve_emission()` (~l.4456) and `reject_emission()` — read `emission.status`, check it in Python, then assign and commit; no conditional `UPDATE … WHERE status IN (pending)`, no row lock / version column.

## Reproduction
1. Two admin sessions POST `/api/emissions/approve/<id>` at the same time (threads) for 30 Pending records.
Script: `audit/repro/<BUG-ID>.py`.

## Expected
One 200 and one 400 "Record is not pending approval" per record; one approval activity-log row per record.

## Actual
17 of 30 records got 200 for both requests; 47 approval log rows for 30 records (and duplicate notifications). In a variant where an admin approves while a superuser rejects the same record, both calls returned 200 for 18/20 records and the final status (7 Rejected / 13 Verified) depended on commit order, while both users were told their decision succeeded.

## Evidence
```
actual: 17/30 records approved twice (both 200); approval log rows = 47
```

## Root Cause
Check-then-act without atomic conditional update (the batch endpoints use `query.filter(status.in_(pending)).update(...)`, which is atomic; the single-record endpoints do not).

## Impact
Non-idempotent double submits; audit trail shows two approvals by different people; conflicting reviewer decisions both acknowledged.

## Affected Components
`/api/emissions/approve/<id>`, `/api/emissions/reject/<id>` (all scopes).

## Recommended Fix
Use `UPDATE … SET status='Verified' WHERE id=:id AND status IN (…)` and check `rowcount == 1` (or optimistic version column), returning 409 otherwise.


---

# BUG-075 — Sentinel-5P "Export to OGMP" stores a 1-hour CH4 mass as the survey's "estimated annual tCH4" (default operating_hours = 1): top-down understated 8,760× and reconciliation always flagged

**Status:** Confirmed
**Severity:** Medium
**Category:** Methane
**Discovered by:** Agent D (Methane Auditor)

## Location
- `new/server/routes/satellite.py` `export_satellite_to_ogmp()` ~lines 258-270: `operating_hours = 8760.0 if is_continuous else 1.0`, then `estimated_annual_tch4 = measured_rate_kg_hr * operating_hours / 1000`. The value is saved in `OgmpSurvey.estimated_annual_tch4` / `operating_hours_year`.
- `new/client/src/pages/MethaneExplorer.jsx` `handleExportToOgmp` (~line 430): posts `facility_id, observation_date, anomaly_ppb, estimated_emission_rate_kg_hr, ...`. It sends no `is_continuous`, `operating_hours` or duration, so the 1-hour default always applies.
- Contrast: the manual survey path (`routes/data.py save_ogmp_survey`) annualises the same kg/h rate with 8,760 h by default.

## Reproduction
1. Fresh DB copy, admin. Facility 169 has Verified bottom-up CH4 of 772.46 t for 2025.
2. `POST /api/satellite/sentinel5p/export-to-ogmp` with exactly the MethaneExplorer payload: `{"facility_id":169,"observation_date":"2025-07-01","anomaly_ppb":10,"estimated_emission_rate_kg_hr":100.0,...}`.
3. Inspect the stored survey and `GET /api/dashboard/ogmp-metrics?year=2025&facilityId=169`.

## Input
Satellite flux 100 kg CH4/h.

## Expected
The field is named, displayed and reconciled as an **annual** quantity against the annual bottom-up inventory, so the rate must be annualised on the same basis as manual surveys: 100 × 8,760 / 1000 = 876 tCH4/yr. Variance vs 772.46 t = +13.4 %, which is within the 20 % threshold: "Reconciled". Otherwise the export must require the user to state an emission duration.

## Actual
`operating_hours_year = 1.0`, `estimated_annual_tch4 = 0.1`, `variance_pct = −99.99`, `reconciliation_status = "Discrepancy Flagged"`. `/ogmp-metrics` then reports −99.99 % "Discrepancy Flagged". The survey is saved as `status "Verified"` for admin/superuser, and the API response tells the user it was "reconciled".

## Evidence
`audit/work/D/s13.py` output (current code, baseline2). Repro: `audit/repro/<ID>.py`.

## Root Cause
There is a 1-hour default duration in the export path, and the UI never provides a duration. Top-down averaging (`func.avg(estimated_annual_tch4)` in `/ogmp-metrics`, `/intensity-stats` and the OGMP export) then mixes 1-hour masses with 8,760-hour annualised manual surveys.

## Impact
Every satellite survey exported from Methane Explorer is 8,760× too small as an annual estimate. Top-down/bottom-up reconciliation (the OGMP Level 5 criterion) is systematically falsified toward "discrepancy". Averaged top-down values for facilities with both survey types are meaningless.

## Affected Components
routes/satellite.py export-to-ogmp, MethaneExplorer "Export to OGMP", /api/dashboard/ogmp-metrics, /api/dashboard/intensity-stats (top_down_tch4, variance), /api/reports/ogmp-export, MethaneIntensity survey table.

## Recommended Fix
Annualise consistently (8,760 h or facility operating hours), or make duration a required, explicit input in the UI. Store the observed rate separately from any annualised figure, and do not average surveys that were annualised on different bases.


---

# BUG-076 — Bulk-upload job status and error CSV have no owner check: any logged-in account (incl. it_admin) can read another user's job rows; absolute server temp path is disclosed

**Status:** Confirmed
**Severity:** Low
**Category:** Security
**Discovered by:** Agent I (Backend/API/Security)

## Location
`new/server/routes/emissions.py:2953-2975` `upload_status()` / `upload_errors()` — `@login_required` only; `background_processor.upload_jobs[job_id]` does not store the uploader's user id, so ownership cannot be checked. `get_job_status()` returns `error_csv_path` (absolute server path).

## Reproduction
1. Role `user` starts `POST /api/emissions/upload/start` (scope 1 CSV with an unknown facility).
2. Role `it_admin` calls `GET /api/emissions/upload/status/<job_id>` and `GET /api/emissions/upload/errors/<job_id>`.
Script: `audit/repro/<BUG-ID>.py`.

## Expected
403/404 for anyone but the uploader (and admins); no server filesystem path in the response.

## Actual
Both 200 for it_admin: `skipped_preview` contains the uploaded rows (facility, quantity, reason), `error_csv_path = C:\Users\samsung\AppData\Local\Temp\tmp….csv_errors.csv`, error CSV downloaded (228 bytes).

## Evidence
```
actual: status 200 skipped_preview=[{'facility': 'NoSuchFacility', 'month': '1', 'quantity': '10', 'reason': "Region 'NoSuchFacility' not found..."}] error_csv_path=C:\Users\samsung\AppData\Local\Temp\tmpdzg0i8h2.csv_errors.csv; errors csv 200 228 bytes
```

## Root Cause
Job records lack an owner field; endpoints don't authorize.

## Impact
Exploitation requires the job UUID (uuid4, not guessable), so severity is Low; but job ids appear in logs/URLs and IT roles are meant to have zero business-data access. Path disclosure aids other attacks.

## Affected Components
`/api/emissions/upload/status/<job_id>`, `/api/emissions/upload/errors/<job_id>`, `background_processor.upload_jobs`.

## Recommended Fix
Store `user_id` in the job dict; return 404 unless `session user == owner` (or admin); drop `error_csv_path` from the response.


---

# BUG-077 — Dashboard "Export Executive Brief (PDF)" in the default All-Years view reports every year and every Pending record as "FISCAL YEAR 2026" / "Total verified records": PDF total 8.41 T tCO2e vs 3.72 T on the dashboard

**Status:** Confirmed
**Severity:** Critical
**Category:** Dashboard
**Discovered by:** Agent F (Dashboard reconciliation auditor)

## Location
- `new/client/src/pages/DashboardEnhanced.jsx` `handleExportPDF` (~L855): `year: currentYear !== "all" ? currentYear : undefined`.
- `new/client/src/utils/ModernReportGenerator.js` `generateModernPDF`:
  - `selectedYear = year && year !== "all" ? year : new Date().getFullYear()` (L78). The cover says `year === "all" ? "All Historical Records" : "FISCAL YEAR " + selectedYear` (L494). Because the year arrives as `undefined`, not "all", the cover says "FISCAL YEAR 2026". L784 prints "The reporting period is for the year 2026".
  - The emissions request `GET /api/emissions?limit=5000` omits the year, so all years are returned. It has no status filter; `/api/emissions/` returns Verified, Pending (and Draft/Rejected) rows. `fetchAllReportData` sums every row.
  - L1522 prints "Total verified records: N", where N is the count of all rows fed in.
  - `fetchAllReportData` also recomputes each row's CO2e from the gas columns × GWP instead of using the stored `co2e_total`, so even the same row set differs from the dashboard (Scope 1 8,409,567,617,747.49 in the PDF vs 8,409,567,276,025.29 stored).

## Reproduction
1. Dashboard as admin, default filters (All Years). Click "Export Executive Brief (PDF)". Capture script: `audit/work/F/pdf1.mjs`, output `audit/work/F/exec_brief_allyears.pdf`, text in `brief.txt`.
2. `python audit/repro/BUG-NNN.py` replays the generator's data request and checks the source.

## Input
Snapshot DB: 630 Verified + 114 Pending Scope 1, 23 + 14 Scope 2 and 7 + 21 Scope 3 rows, covering years 1800 and 2020-2026 plus 2099.

## Expected
The PDF matches the dashboard it was exported from (Verified only, All Years): Scope 1 3,723,125,709,415.04, Scope 2 1,539,702.62, total S1+S2 **3,723,127,249,117.66**, Scope 3 216.85, and a cover that says "All Historical Records". Or, if the report is for FY2026, only 2026 Verified data: S1+S2 = 9,992.41 + S2 2026.

## Actual
The PDF cover says "FISCAL YEAR 2026" and "The reporting period is for the year 2026". Table 5.1 shows Scope 1 **8,409,567,617,747.49**, Scope 2 **1,540,060.68** (Verified + Pending), Scope 3 **366.85** (Verified + Pending) and a Total of **8,409,569,158,175.02**. The Annex footer says "Total verified records: 809 | Fiscal Year: 2026", although 149 of the 809 rows are Pending. The Chapter 6 flaring table in the same PDF covers 2026 only (100 kNm3 / 210.2 t, see BUG-026).

## Evidence
`brief.txt` lines 5, 51, 98, 812-816 and 1138. Repro output:
```
records fed to PDF: 809 statuses={'Verified': 660, 'Pending': 149} years=[1800, 2020, 2021, 2022, 2023, 2024, 2025, 2026, 2099]
PDF S1+S2 basis (stored co2e) = 8,409,568,816,085.97 ; dashboard Verified S1+S2 = 3,723,127,249,117.66
generator filters Verified: False ; dashboard passes year=undefined for All Years (-> 'FISCAL YEAR 2026'): True
```

## Root Cause
The dashboard sends `undefined` instead of "all", and the generator defaults a missing year to the current year for labels only, not for data. The generator never filters by approval status and trusts `/api/emissions`, which is a data-management listing and not an inventory query. The generator also re-derives CO2e client-side.

## Impact
The one-click "Executive Brief" from the main dashboard presents multi-year totals, including unapproved Pending records, as a single fiscal year of verified data. Reported emissions are overstated by 2.26× on the snapshot, and by roughly the number of reporting years on any normal dataset. The labels ("verified", "FY2026", ISO 14064-1 table) give it the look of an official disclosure.

## Affected Components
DashboardEnhanced "Export Executive Brief (PDF)"; ModernReportGenerator (cover, Table 5.1/5.2, executive highlights, Annex). The Reports page calls the same generator; there, the year and status handling depend on its own parameters.

## Recommended Fix
Pass "all" explicitly and label it correctly, or require a single year for the brief. Request only `status=Verified` (add a status filter to `/api/emissions` or use the dashboard aggregate endpoints). Use the stored `co2e_total` so the PDF reconciles with the dashboard. Count Verified rows only in the "verified records" footer.


---

# BUG-078 — Executive Brief / Master PDF prints hard-coded performance claims ("15.9 % reduction… on track for -30 %", "65.9 % methane reduction", "Lowest annual flaring on record (-38.0 %)", "VISR camera verified" DRE) regardless of the data

**Status:** Confirmed
**Severity:** High
**Category:** Dashboard
**Discovered by:** Agent F (Dashboard reconciliation auditor)

## Location
`new/client/src/utils/ModernReportGenerator.js`:
- L675-680 `execHighlights`: fixed strings "15.9% reduction achieved relative to 2021-2023 baseline average; on track for -30% by 2030.", "65.9% reduction from baseline following flare optimization and comprehensive OGI LDAR campaigns.", "Lowest annual flaring on record (-38.0% vs baseline); compliant with Executive Decree 21-330 Art. 9.", "Multi-spectral VISR camera verified; eliminates default 98% uncertainty."
- Numeric fallbacks presented as data: `volume_knm3 || 117898`, `measured_dre_pct || 99.85`, `?? 73986 / 36369 / 7543` kNm3 (L1097-1100), and `scope1Total * 0.20` as flaring (L1055).
- The L1144 compliance row reads "VISR Infrared Multi-Spectral Camera … VERIFIED EFFICIENT" whatever `dre_method` says.

## Reproduction
1. Dashboard as admin, click "Export Executive Brief (PDF)" (`audit/work/F/pdf1.mjs`), then `pdftotext -layout` gives `audit/work/F/brief.txt`.
2. `python audit/repro/BUG-NNN.py`

## Input
Snapshot DB (any data gives the same sentences).

## Expected
Narrative percentages are computed from the inventory, or omitted. Independent SQL on Verified data: S1+S2 2025 vs the 2021-2023 average = **-99.89 %**, CH4 = **-99.96 %** (both driven by bad seed data, but they are the platform's numbers); flaring YoY from the API = -99.92 %. `/flaring-summary` returns `dre_method: "Standard 98% Default"`, so the DRE must not be described as camera-measured.

## Actual
The PDF page 3 "2030 Decarbonization Roadmap & Operational Milestones" prints "15.9% reduction achieved… on track for -30% by 2030", "65.9% reduction from baseline…", "Lowest annual flaring on record (-38.0% vs baseline); compliant…" and "98% **Measured** — Multi-spectral VISR camera verified". The DRE value is the 98 % default. Chapter 6 marks the DRE "VISR Infrared Multi-Spectral Camera … VERIFIED EFFICIENT".

## Evidence
`brief.txt` L51-63 and L866-873. Repro output:
```
hard-coded claims present in ModernReportGenerator.js: ['15.9% reduction achieved', '65.9% reduction from baseline', 'Lowest annual flaring on record (-38.0% vs baseline)', 'Multi-spectral VISR camera verified', '|| 117898', '|| 99.85', 'VERIFIED EFFICIENT']
captured PDF contains '15.9% reduction': True | '98% Measured': True
```

## Root Cause
Demo or marketing copy, and sample figures from one reference dataset, were left in the report template as literals and fallbacks instead of being computed.

## Impact
Every exported brief makes specific quantitative reduction and compliance claims that the data does not support, and presents default assumptions as measured and verified. This is a greenwashing and disclosure-integrity risk for any report shared externally.

## Affected Components
ModernReportGenerator (Dashboard "Export Executive Brief", Reports page PDF), executive highlights table, Chapter 5.2 SANGEA table fallbacks, Chapter 6 flaring and DRE compliance table.

## Recommended Fix
Compute each milestone (base-year average, YoY, CH4 change, flaring vs baseline) from the fetched data, or drop the sentences. Show "n/a" instead of numeric fallbacks. Derive DRE wording from `dre_method`.


### Additional confirmation (BUG-071)

Independently confirmed by Agent L (Browser) on baseline2 through the real UI stack (:5190 → :5055, db browser).
- `audit/repro/BUG-071-browser.mjs`: new facility 175; batch-all (facility 175, 2025) primed → scope1_total 0; admin `POST /api/emissions` (1000 gal diesel, Verified, 10.24 t) → 201; batch-all 3 s later and after a full page reload still 0.
- Also affects the maker-checker banner: after `audit_user` submitted record 754 (Pending, 5.12 t) through the Scope 1 form, `batch-all?facilityId=173&year=2025` kept returning `pending_stats {"count":1,"totalCo2e":10.24}` while the DB had 2 Pending rows (15.36 t); an un-cached key (year=all) returned count 2. So an admin opening the dashboard right after a submission does not see it in "Pending Records Awaiting Review".
- Additional affected paths with the same flush-before-commit pattern: `routes/facilities.py:182` (create facility — new facility missing from cached dashboard filters/intensity), `:294`, `:376`; `routes/emissions.py:3672, 3745` (need an explicit clear, not verified individually).


---

# BUG-079 — OGMP reconciliation in the default "All years" view compares the AVERAGE of annual top-down surveys with the SUM of multi-year bottom-up CH4, so perfectly reconciled facilities are flagged (−80 %)

**Status:** Confirmed
**Severity:** Medium
**Category:** Methane
**Discovered by:** Agent D (Methane Auditor)

## Location
- `new/server/routes/dashboard.py` `get_ogmp_metrics()` ~1146-1172: `func.avg(OgmpSurvey.estimated_annual_tch4)` against `func.sum(Emission.ch4_emissions)`. When `year` is "all", neither side is year-filtered.
- `_query_intensity_stats()` ~1961-1980 and 2128-2130: the same avg-vs-sum pairing (`top_down_tch4`, `variance_pct`, `reconciliation_status`, `current_ogmp_level`).
- `new/server/routes/reports.py` OGMP export (~897-922, ~1212-1226) when no year filter is given.
- `MethaneIntensity.jsx` defaults `selectedYear` to "all" (line 43) and shows the `/ogmp-metrics` variance/status in the OGMP roadmap.

## Reproduction
1. Fresh DB copy, admin. Facility 169 Verified bottom-up CH4 by year: 2021 2,891.59 · 2022 2,765.88 · 2023 2,568.91 · 2024 1,350.04 · 2025 772.46 t.
2. For each year, `POST /api/data/ogmp-surveys` with a rate that exactly matches that year's inventory (`measured_rate_kg_hr = t×1000/8760`).
3. `GET /api/dashboard/ogmp-metrics?year=<Y>&facilityId=169` for each year, then with `year=all`. Do the same for `/intensity-stats`.

## Input
Five annual surveys, each equal to its year's bottom-up CH4.

## Expected
Every year reconciles (0 %). The multi-year view should compare like with like: Σ top-down (10,348.88) vs Σ bottom-up (10,348.88), which is 0 % and "Reconciled", or it should reconcile year by year.

## Actual
- Per year: 0.0 %, "Reconciled".
- `year=all`: top-down 2,069.78 (the mean) vs bottom-up 10,348.88 (the sum) gives **−80.0 %, "Discrepancy Flagged"** on both `/ogmp-metrics` and `/intensity-stats`. `intensity-stats.current_ogmp_level` drops from 5 to 4.

## Evidence
`audit/work/D/s14.py` output (current code, baseline2). Repro: `audit/repro/<ID>.py`.

## Root Cause
Aggregation mismatch. The mean of annual surveys is an annual rate, while the unfiltered sum is a multi-year total. Averaging is meant for multiple surveys within one facility-year (Decision D-02), but it is applied across years.

## Impact
The OGMP Gold-Standard roadmap on the Methane Intensity page, which opens in "All years" by default, flags reconciliation discrepancies and understates levels for every facility with more than one year of inventory. The same mismatch applies in the OGMP Excel export without a year filter.

## Affected Components
/api/dashboard/ogmp-metrics, /api/dashboard/intensity-stats (top_down_tch4, variance_pct, reconciliation_status, current_ogmp_level), /api/reports/ogmp-export (no year), MethaneIntensity.jsx OGMP roadmap.

## Recommended Fix
Average surveys per (facility, year), then sum across years, or reconcile per year and report the multi-year view as per-year statuses. Never pair an average with an unfiltered sum.


---

# BUG-080 — Two contradictory OGMP facility-level algorithms: /intensity-stats reports Level 5 (Gold Standard) where the canonical service (/ogmp-metrics, OGMP export) reports Level 4 for the same facility and year

**Status:** Confirmed
**Severity:** Low
**Category:** Methane
**Discovered by:** Agent D (Methane Auditor)

## Location
- `new/server/routes/dashboard.py` `_query_intensity_stats()` ~2150-2161: its own level logic.
  - Level 5 if top-down exists and |variance| ≤ threshold. There is no requirement that the bottom-up inventory is Level 4.
  - Otherwise Level 4 if ≥50 % of CO2e is non-"default".
  - Otherwise Level 3 as soon as any CH4 exists.
  - `factor_source == "default"` counts as L3.
- `new/server/services/ogmp.py` `compute_facility_ogmp_level()` (used by `/ogmp-metrics` and `/reports/ogmp-export`) caps reconciliation at Level 4 unless the bottom-up level is ≥4, and maps `default` factors to L2.

## Reproduction
1. Fresh DB copy. Add a survey for facility 169 / 2021 equal to its bottom-up CH4 (2,891.59 t). Its inventory is L3 API-Compendium factors.
2. `GET /api/dashboard/ogmp-metrics?year=2021&facilityId=169` → `highest_ogmp_level`.
3. `GET /api/dashboard/intensity-stats?year=2021&facilityId=169` → `current_ogmp_level`.
4. Also, on the untouched snapshot, compare the two endpoints for all facilities for 2024.

## Input
Snapshot data, plus one reconciled survey.

## Expected
One level per facility-year. Per the code's own OGMP 2.0 note, reconciliation with an L2/L3 inventory is capped at Level 4.

## Actual
- Facility 169 / 2021: `/ogmp-metrics` gives 4; `/intensity-stats` gives **5**.
- Snapshot 2024: 9 of 25 facilities differ (e.g. facilities 1, 150, 155: 2 vs 3; facility 169: 3 vs 4).
- 2025: 5 of 80 differ.

## Evidence
`audit/work/D/s14.py` and `s4.py` outputs (current code). Repro: `audit/repro/<ID>.py`.

## Root Cause
The OGMP level logic is duplicated in `_query_intensity_stats` instead of calling `services.ogmp.compute_facility_ogmp_level` / `ogmp_level_for`.

## Impact
API consumers of `/intensity-stats` and `batch-all.intensity_stats` get a Gold-Standard Level 5 claim that the roadmap page and the regulatory export deny. The current client renders `highest_ogmp_level` first, so the UI impact is limited.

## Affected Components
/api/dashboard/intensity-stats (`current_ogmp_level`, `gold_pathway_status`, `ogmp_l3_pct`/`ogmp_l4_pct`), batch-all `intensity_stats`.

## Recommended Fix
Use the canonical service in `_query_intensity_stats`, and fix the service itself as described in BUG-031.


---

# BUG-081 — Scope 2/3 bulk import duplicate key is too coarse: separate meters and sub-categories in the same facility-month are rejected as "duplicates", or with Overwrite they replace a different existing record

**Status:** Confirmed
**Severity:** High
**Category:** Emissions
**Discovered by:** Agent B (Emissions Auditor)

## Location
`new/server/background_processor.py`:
- `_process_file_thread` L374-403 pre-loads existing keys. Scope 2: `(facility_id, year, month, source_type)`. Scope 3: `(facility_id, year, month, category)`. Every status is included.
- `_process_row_scope2` (key ~L1016), `_process_row_scope3` (key `(fac, year, month, category)`, ~L1259) and `_process_row_scope3_eeio` (key `(fac, year, month, "category 1")`, ~L1129). The sub_category, grid_region/meter, NAICS code, amount and unit are not part of the key.

## Reproduction
Run `python audit/repro/BUG-081.py` (own db). It uploads through `POST /api/emissions/upload/start` as admin:
1. Scope 3 CSV with two rows for ADR 2037-03, Category 6: "Air travel" (1000 x 0.2 kg) and "Hotel nights" (1000 x 0.03 kg).
2. Scope 2 CSV with two electricity rows (two meters) for ADR 2037-03: 1000 kWh and 2000 kWh.
3. Scope 3 "Air travel" for 2037-05 is uploaded, then a second file with "Hotel nights" for 2037-05 is uploaded with `overwrite_duplicates=true`.

## Input
See above.

## Expected
The rows are distinct activity lines, not duplicates. Scope 3 2037-03 gives 2 rows and 0.23 t. Scope 2 2037-03 gives 2 rows and 3000 kWh. Scope 3 2037-05 gives 2 rows and 0.23 t.

## Actual
```
S3 same cat/month two sub-categories: expected 2 rows 0.23 t, actual {'n': 1, 's': 0.2}
S2 two meters same month: expected 2 rows 3000 kWh, actual {'n': 1, 's': 1000.0}
S3 2nd upload w/ overwrite, other sub-category: expected 2 rows 0.23 t, actual {'n': 1, 's': 0.03}
```
- Without overwrite, the second line is skipped: "Duplicate record: Scope 3 emission for facility 'ADR' (2037-03, Category 6) already exists".
- With overwrite, the existing Air-travel record is silently turned into Hotel nights (0.2 t becomes 0.03 t, and it is set back to Pending).
- The EEIO spend path allows only one Category 1 line per facility per month across all NAICS codes.
- The pre-load also includes Rejected and Draft rows, so a corrected re-upload of a rejected month is blocked unless Overwrite is used.

## Evidence
Output above. Also see `audit/work/B/t15.py` and `t16.py`.

## Root Cause
The dedup key identifies a Scope 2/3 record by facility, month and category/source type only. Real inventories have many lines per category per month: purchased goods by commodity, business travel by mode, multiple meters and suppliers. Scope 1 by contrast includes fuel and equipment_id in its key.

## Impact
Bulk-imported Scope 2 and Scope 3 inventories are silently incomplete: only the first line per category-month survives. With "Overwrite Duplicates" on, unrelated existing records are replaced, which destroys data. Scope 3 Category 1 spend-based (EEIO) inventories can hold only one NAICS line per month.

## Affected Components
Scope 2 bulk import, Scope 3 bulk import (activity- and spend-based), totals and reports derived from them.

## Recommended Fix
Include sub_category, meter/grid_region, NAICS code (and ideally unit and an optional external row id) in the key. Exclude Rejected and Draft rows from the pre-loaded duplicate set, or handle them explicitly. Never overwrite a record whose descriptive fields differ.


---

# BUG-082 — Scope 1 "Live Equation Inspector" states "GWP Standard: IPCC AR6 (CH₄:28, N₂O:265)" — hard-coded, AR5 values mislabelled as AR6, ignores the org GWP setting

**Status:** Confirmed
**Severity:** Low
**Category:** UI
**Discovered by:** Agent K (Frontend/UI)

## Location
`new/client/src/components/Scope1Form.jsx` ≈line 2598 (static string inside the Live Equation Inspector).

## Reproduction
1. Log in as admin (:5191) → Emissions → Scope 1; scroll to "Live Equation Inspector".
2. Submit a Tier 3 combustion entry (1000 m³, CO2 53.06 / CH4 0.001 / N2O 0.0001 kg/MMBtu, HHV 38 MJ/m³).
3. Check the stored record's `gwp_version` and CO2e.

## Input
Organisation GWP setting = AR5 (default).

## Expected
Label reflecting the active standard, e.g. "IPCC AR5 (CH₄:28, N₂O:265)"; under AR6 it would be "CH₄:29.8, N₂O:273" (the app's own Settings/Reports list AR6 as 29.8/273).

## Actual
Always "GWP Standard: IPCC AR6 (CO₂:1, CH₄:28, N₂O:265)". Records 754/755 were computed with AR5 (`gwp_version = 'AR5'`, CO2e 1.91303 t = 1.91106 + 3.6017e-5×28 + 3.6017e-6×265).

## Evidence
`audit/work/K/t_hhv.mjs` (screenshot `audit/work/K/hhv.png`, POST/201 capture); DB rows 754/755 in audit/db/ui.db.

## Root Cause
Hard-coded label text; not bound to `/auth/settings.gwp_standard` or `constants.js` GWP tables.

## Impact
Users/verifiers are told the calculation uses AR6 when it uses AR5 (or whatever is configured); misleading audit evidence.

## Affected Components
Scope 1 entry form (all process types).

## Recommended Fix
Render the active standard and its values from settings/`constants.js`.


---

# BUG-083 — Activity-data write endpoints accept "NaN" / "1e999" (±Infinity): a Scope 3 record with activity_data=Infinity makes /dashboard/batch-all, /scope3/summary and /api/scope3 emit invalid JSON ("Infinity")

**Status:** Confirmed
**Severity:** High
**Category:** API
**Discovered by:** Agent I (Backend/API/Security)

## Location
Numeric fields are parsed with bare `float(...)` and only range-checked with `< 0` (which NaN/inf pass) or not at all:
- `routes/scope3.py:96` `activity_data = float(data.get("activity_data") or data.get("amount", 0))`, `emission_factor`
- `routes/scope2.py` `electricity_kwh`, `steam_ton`, `heat_mmbtu`, `cooling_ton`
- `routes/data.py:92-100` production `oil_amount` / `gas_amount` / `gross_production` (`< 0` check only)
- `routes/custom_factors.py` `co2_factor` etc.; `routes/managedata.py` mitigation `quantity_tco2e`
(Distinct fields from BUG-034 SBTi, BUG-039 goals, BUG-043 uncertainty, BUG-046 equity pct.)

## Reproduction
Admin posts (script `audit/repro/<BUG-ID>.py`):
1. `POST /api/scope3 {"facility_id":1,"year":2025,"month":1,"category":"Purchased Goods and Services","activity_data":"1e999","unit":"USD","emission_factor":0.5}`
2. `POST /api/scope2 {... "electricity_kwh":"NaN"}`, `POST /api/data/production {... "oil_amount":"NaN"}`, `POST /api/custom-factors {"name":"CF_NAN","co2_factor":"NaN"}`, `POST /api/mitigation {... "quantity_tco2e":"1e999"}`
3. `GET /api/dashboard/batch-all?year=2025`, `/api/dashboard/scope3/summary?year=2025`, `/api/scope3`.

## Expected
400 for non-finite numbers (the fuzz found the same for 1e999/NaN across these 5 endpoints).

## Actual
All 5 → 201. Stored: scope3 id 29 `activity_data=inf, co2e=inf, status=Verified`; scope2 `electricity_kwh=NULL, co2e=NULL` (SQLite turns NaN into NULL, so a "created" record silently has no value); custom factor `co2_factor=NULL`. Afterwards `batch-all` returns `"scope3_emissions":Infinity`, `scope3/summary` returns `"2025":Infinity`, `/api/scope3` returns `"activity_data":Infinity` — all HTTP 200 with bodies that are not valid JSON (browser `JSON.parse` rejects `Infinity`), so the main dashboard batch and Scope 3 pages fail to load for every user who can see that facility.

## Evidence
```
scope2 electricity_kwh=NaN: HTTP 201 ... mitigation quantity_tco2e=1e999: HTTP 201
stored: scope2 {'electricity_kwh': None, 'co2e': None}; scope3 {'activity_data': inf, 'co2e': inf}; custom_factors {'co2_factor': None}
batch-all (200, True); scope3/summary (200, True); GET /api/scope3 (200, True)   # body contains Infinity
```

## Root Cause
No `math.isfinite` validation on numeric inputs; Flask's JSON provider serialises inf as `Infinity`.

## Impact
One entry (any business role can create Scope 3 data for its facility; admin entries are auto-Verified) breaks the dashboard/Scope 3 views for all users in scope; NaN inputs create records with NULL activity/emissions that pass as successful saves.

## Affected Components
`POST /api/scope2`, `/api/scope3`, `/api/data/production`, `/api/custom-factors`, `/api/mitigation` (and their PUT/bulk-import variants); dashboard batch-all, scope3 summary, Scope 3 list.

## Recommended Fix
Central numeric parser rejecting non-finite / out-of-range values with 400 in all write paths (manual, PUT, JSON bulk, file bulk).


---

# BUG-084 — QA/QC Dashboard shows "Zero Anomalies Detected… The inventory is fully verified and audit-compliant" with 149 Pending records and 11 records more than 10^6 × the median; the anomaly queue only lists a stored `qa_flag`, which is never computed for existing data

**Status:** Confirmed
**Severity:** Medium
**Category:** Dashboard
**Discovered by:** Agent F (Dashboard reconciliation auditor)

## Location
- `new/server/routes/qaqc.py` `get_qaqc_dashboard()` (~L63-160, L346-375): the flagged and anomaly counts are `qa_flag IS NOT NULL` only. No statistical check runs over the stored inventory.
- `new/client/src/pages/QADashboard.jsx` L722-740: when `total_flagged_count === 0` it prints "No statistical outliers or data quality flags detected… The inventory is fully verified and audit-compliant."

## Reproduction
1. Open `/qa-dashboard` as admin (Playwright text: `audit/work/F/qa_text.txt`).
2. `python audit/repro/BUG-NNN.py`

## Input
Snapshot DB: 149 Pending records (114 S1, 14 S2, 21 S3). Scope 1 median co2e is 404.17 t, and 11 records exceed 4.04e8 t (for example the 1e13 MMBtu and 1e15 t coal test rows of BUG-007).

## Expected
With Pending records the page must not claim the inventory is "fully verified". Obvious outliers (10^6 × the median) should be flagged by the page's "statistical outlier" check, or the text should say that only import-time flags are shown.

## Actual
"FLAGGED ANOMALIES 0 active", "Zero Anomalies Detected", "The inventory is fully verified and audit-compliant." "INVENTORY COVERAGE 809 entries" counts all statuses.

## Evidence
`QA API total_flagged=0 ; independent: Pending records=149, records > 1e6 x median (404.17 t) = 11`

## Root Cause
The QA page reflects only `qa_flag` values written by the bulk-import anomaly detector. Manual entries are never flagged (BUG-007), and nothing re-scans stored data. The empty-state copy asserts verification status without checking record status.

## Impact
Reviewers and assurers are told the inventory is clean and fully verified while a small number of records inflate totals by about 1000× and 149 records are still unapproved.

## Affected Components
`/api/qaqc/dashboard`, `/api/qaqc/export`; QADashboard anomaly card, empty state and export.

## Recommended Fix
Run the anomaly detector (z-score or ratio to median, per process type and unit) over stored records when building the QA dashboard, or on a schedule. Base the "verified" wording on the actual count of non-Verified records.


---

# BUG-085 — Scope 2/3 bulk import silently books rows with a blank or non-ISO date to January 2024, and stores a blank Scope 3 category as "Category "

**Status:** Confirmed
**Severity:** High
**Category:** Emissions
**Discovered by:** Agent B (Emissions Auditor)

## Location
`new/server/background_processor.py`:
- `_process_row_scope2` ~L884-895, `_process_row_scope3` ~L1195-1206 and `_process_row_scope3_eeio` ~L1097-1110: `year = int(row.get("year") or 2024)`, `month = int(row.get("month") or 1)`, then `date.split("-")` inside `try/except: pass`. The EEIO `if not year or not month` check can never fire because of the defaults.
- `_process_row_scope3` ~L1223: `cat = row.get("category", "11")` returns `""` for an empty cell, and the row is stored as `"Category "`. Free-text categories are never checked against the 15 GHG Protocol categories.
- Scope 1 (`_process_row`) by contrast rejects a missing date/year and a missing month.

## Reproduction
1. Run `python audit/repro/BUG-085.py` (own db).
2. Scope 3 CSV rows: `,ADR,4,no date,...` (blank Date), `03/2037,ADR,7,slash date,...` (MM/YYYY date), `2037-04,ADR,,blank category,...`.
3. Scope 2 CSV row: `,ADR,electricity,3000,kWh,...` (blank Date).

## Input
See above. `03/2037` is a common spreadsheet date format.

## Expected
Rows with a missing or unparseable date, or a missing or invalid category, are rejected with a row error, as Scope 1 bulk does.

## Actual
All rows are accepted (skipped 0):
```
scope3 stored: [{'year': 2024, 'month': 1, 'category': 'Category 4', 'sub_category': 'no date'}, {'year': 2024, 'month': 1, 'category': 'Category 7', 'sub_category': 'slash date'}, {'year': 2037, 'month': 4, 'category': 'Category ', 'sub_category': 'blank category'}]
scope2 stored: [{'year': 2024, 'month': 1, 'electricity_kwh': 3000.0}]
```
The 2037 data is moved into the 2024 inventory, and the upload reports success. Because the fabricated 2024-01 key then collides with other undated rows, subsequent undated or mis-formatted rows for the same facility and category are dropped as "duplicates" (seen in `audit/work/B/t16.py`).

## Evidence
Output above. Also see `audit/work/B/t15.py` and `t16.py`.

## Root Cause
Hard-coded fallback year and month, a swallowed parse exception, and no category validation in the Scope 2/3 row processors.

## Impact
Emissions are silently shifted between reporting years. 2024 is inflated and the true year understated, which affects SBTi base/target years, YoY and intensity. Unclassified Scope 3 records ("Category ") fall outside every per-category breakdown.

## Affected Components
Scope 2, Scope 3 and Scope 3 EEIO bulk import; year-filtered dashboards, reports and SBTi.

## Recommended Fix
Remove the 2024/1 defaults. Parse the accepted date formats explicitly (YYYY-MM, YYYY-MM-DD, MM/YYYY), otherwise return a row error. Validate year and month ranges. Require a category that maps to Category 1-15, rejecting blank or unknown values.


---

# BUG-086 — Methane loss-rate segment classification differs between the KPI cards, the trend chart and the server: "Downstream / Processing" counts as Midstream in the trend, and "Upstream / Extraction" is dropped from the Upstream KPI

**Status:** Confirmed
**Severity:** Low
**Category:** Methane
**Discovered by:** Agent D (Methane Auditor)

## Location
- `new/client/src/pages/MethaneIntensity.jsx` `loadStats` (~213-229): exact match. `seg === "midstream"` counts as Midstream and `seg === "upstream"` as Upstream; everything else is excluded.
- Same file, `trendChartData` (~620-645): substring match. "processing", "lng", "lsh", "gnl" and "gpl" count as Midstream; "upstream", "production" and "exploration" count as Upstream.
- `new/server/routes/dashboard.py` `_query_intensity_stats` / `_query_intensity_trend_bulk`: `ogmp_target = 0.20 if "upstream" in segment else 0.05`. A facility with segment "Oil & Gas" or NULL therefore gets the 0.05 % midstream target. WEC uses yet another rule ("processing"/"midstream"/"lng" → midstream threshold).

## Reproduction
1. Snapshot copy, admin. The facility segments stored are "Upstream" (37), "Upstream / Extraction" (42), "Midstream" (6), "Downstream / Processing" (60), "Oil & Gas" (1), "Heavy Industry" (3) and NULL (15).
2. `GET /api/dashboard/intensity-stats?year=2025` and `GET /api/dashboard/intensity-trend?years=...`.
3. Apply the page's two aggregation routines (transcribed in `audit/work/D/s15.py`).

## Input
Year 2025, all facilities.

## Expected
The same year, filters and facilities give the same Upstream/Midstream gas denominators and loss rates in the KPI cards and in the 5-year trend chart. Refinery ("Downstream / Processing") gas should not count toward the Midstream OGMP rate.

## Actual
For 2025:
- KPI midstream gas = **0 m³**, and the Midstream card shows no rate. The trend's midstream gas = **122,158,675 m³**, all from "Downstream / Processing" facilities.
- KPI upstream gas = 15,490,256,856 m³; trend upstream gas = 15,548,277,980 m³. The KPI omits the "Upstream / Extraction" facilities.
- Loss rates therefore differ between the card and the chart point for the same year.

## Evidence
`audit/work/D/s15.py` output (current code). Repro: `audit/repro/<ID>.py`.

## Root Cause
Three independent, inconsistent segment-to-category mappings. There is no canonical segment enum; the facility data uses free-text composites.

## Impact
Segment-level methane loss rates and OGMP targets (0.20 % vs 0.05 %) are applied to different facility sets depending on which widget is read. With the current data the numeric difference is small, but it grows with the volume of refinery or "Upstream / Extraction" gas.

## Affected Components
MethaneIntensity.jsx KPI cards and trend chart; server `ogmp_target` / `ogmp_target_status`, WEC threshold selection.

## Recommended Fix
Add one server-side canonical segment classifier (and return `segment_category` in the API), then use it in all three places. Validate the facility segment against an enum.


---

# BUG-087 — Malformed input on create endpoints returns HTTP 500/409 with raw exception and SQL text (≈40 handlers return `str(e)`)

**Status:** Confirmed
**Severity:** Low
**Category:** API
**Discovered by:** Agent I (Backend/API/Security)

## Location
Handlers that catch `Exception` and return `jsonify({"error": ... str(e)})` — 41 occurrences, e.g. `routes/emissions.py:962,3187`, `routes/scope2.py:156,287,475,666`, `routes/scope3.py:155,299,473`, `routes/data.py:343,563,642,846,880`, `routes/managedata.py:102,138,222,347,372,426,516,724,766,808,830,890,950,983,1073`, `routes/qaqc.py:616,738,812,906`, `routes/dashboard.py:341,972,1103`. The global handler in `app.py` correctly hides details, but these local handlers bypass it. Types are not validated before the DB insert. (BUG-009 is the facility-delete instance of the same leak; this covers the create/validation paths.)

## Reproduction
Admin (script `audit/repro/<BUG-ID>.py`):
1. `POST /api/emissions/ {"process_type": [] ...}`
2. `POST /api/scope2 {"facility_id": "abc", ...}`
3. `POST /api/data/production {"year": null, ...}`
4. `POST /api/goals {"year": "abc"}`
5. `POST /api/sources {"facility_id": -1e308, "name": "S"}`

## Expected
400 with a field-level validation message; no internals.

## Actual
```
/api/emissions/: HTTP 500 "(sqlite3.ProgrammingError) Error binding parameter 7: type 'list' is not supported\n[SQL: INSERT INTO e..."
/api/scope2: HTTP 500 "(sqlite3.IntegrityError) FOREIGN KEY constraint failed\n[SQL: INSERT INTO scope2_emissions (fac..."
/api/data/production: HTTP 409 "Concurrency conflict: (sqlite3.IntegrityError) NOT NULL constraint failed: production_data.year\n[SQL: ..."
/api/goals: HTTP 500 "invalid literal for int() with base 10: 'abc'"
/api/sources: HTTP 500 "Failed to add source: Python int too large to convert to SQLite INTEGER"
```
A fuzz of 15 create endpoints × 8 bad values produced 149 HTTP 500s and 71 responses containing internal exception/SQL text (`audit/work/I/fuzz.out`). Missing `year` on production is misreported as a "Concurrency conflict" (409).

## Root Cause
No schema validation of request types; broad `except Exception` handlers echo the exception.

## Impact
Schema/table/column disclosure; wrong status codes (500/409 instead of 400) hamper clients and monitoring.

## Affected Components
Most create/update/bulk endpoints in emissions, scope2, scope3, data, managedata, qaqc, dashboard.

## Recommended Fix
Validate types/required fields up front (400); log exceptions server-side and return a generic message with request id.


---

# BUG-088 — Facilities with CH4 emissions but no gas production get methane_loss_rate_pct = 0 and ogmp_target_status "Compliant"

**Status:** Confirmed
**Severity:** Low
**Category:** Methane
**Discovered by:** Agent D (Methane Auditor)

## Location
`new/server/routes/dashboard.py` `_query_intensity_stats` (~2014-2018, 2214-2220) and `_query_intensity_trend_bulk` (~1584-1585, 1626-1634):
`methane_loss_rate_pct = ... if gas_m3 > 0 else 0.0`, then `"Compliant" if methane_loss_rate_pct <= ogmp_target`.

## Reproduction
1. Snapshot copy, admin. `GET /api/dashboard/intensity-stats?year=2025`.
2. Select the rows where `total_ch4 > 0` and `total_gas_m3 == 0`.

## Input
Facility 147 (2025): 0.026 tCH4 Verified, no production data.

## Expected
The loss rate is undefined (null), with a status such as "Missing Production Data" or "N/A". The OGMP Excel export handles this case correctly with "Non-Compliant (Missing Production Data)" in `reports.py` ~933-936, and the MethaneIntensity page KPI shows "Pending Production".

## Actual
`methane_loss_rate_pct: 0.0`, `ogmp_target_status: "Compliant"` (facilities 146 and 147). The per-facility bar chart and heatmap show 0 / "-" for them.

## Evidence
`audit/work/D/s6.py` output (current code). Repro: `audit/repro/<ID>.py`.

## Root Cause
A zero denominator is coerced to a 0 % rate, which then passes the ≤ target test.

## Impact
The API reports compliance for facilities that emit methane but have no production denominator. This is inconsistent with the OGMP export and the page-level KPI.

## Affected Components
/api/dashboard/intensity-stats, /api/dashboard/intensity-trend (`methane_loss_rate_pct`, `ogmp_target_status`), MethaneIntensity per-facility loss chart and heatmap.

## Recommended Fix
Return `null` and a "Missing Production Data" status when gas = 0 and CH4 > 0.


---

# BUG-089 — Scope 3 category is stored as "6" by the UI/API and as "Category 6" by bulk import: cross-channel duplicates are not detected (double counting) and category breakdowns split

**Status:** Confirmed
**Severity:** Medium
**Category:** Emissions
**Discovered by:** Agent B (Emissions Auditor)

## Location
- `new/client/src/components/Scope3Form.jsx:304` sends `category: parseInt(category)`.
- `new/server/routes/scope3.py` `create_scope3_emission()` stores `data.get("category", "Category 11")` as-is, so the result is `"6"`. The default is in the other format.
- `background_processor._process_row_scope3` normalises to `f"Category {cat}"`, so the result is `"Category 6"`.
- The bulk dedup key (`_process_file_thread` L390-403) compares the raw category string.
- `routes/dashboard.py` `_query_uncertainty` (L2419-2433) groups Scope 3 by the raw category, and the reports and QA lists show it raw.

## Reproduction
1. Run `python audit/repro/BUG-089.py` (own db).
2. As admin, `POST /api/scope3` `{"facility_id":5,"year":2037,"month":3,"category":6,"sub_category":"Air travel","activity_data":1000,"emission_factor":0.2}`, which is the payload shape Scope3Form sends.
3. Bulk-upload the same line: `2037-03,ADR,6,Air travel,1000,0.2,kg` (scope 3).

## Input
The same 0.2 t Category 6 air-travel line, entered once by form and once by import.

## Expected
One canonical category label. The bulk row is reported as a duplicate of the existing record, which is what happens for Scope 1 and for bulk-vs-bulk Scope 3.

## Actual
```
UI create: 201 ; bulk skipped: 0
rows: [{'id': 29, 'category': '6', ... 'co2e': 0.2, 'status': 'Verified'}, {'id': 30, 'category': 'Category 6', ... 'co2e': 0.2, 'status': 'Pending'}]
```
Once the bulk row is approved, the activity is counted twice. The snapshot already mixes labels: category `'11'` (1 row, 216.85 t, the only material Verified Scope 3 row) next to `'Category 11'`, and `'Category 1'`...`'Category 15'` from other paths. Per-category views (uncertainty items, reports, exports) show "11" and "Category 11" as different categories.

## Evidence
Output above. `select category,count(*) from scope3_emissions group by category` on `snapshot_original.db` returns both `'11'` and `'Category 11'`.

## Root Cause
There is no canonical category representation. The API accepts any string or integer, and only the bulk path normalises it.

## Impact
Scope 3 records entered through different channels are double counted, because the duplicate protection is bypassed. Category-level totals, uncertainty groupings and GHG-Protocol category reporting are fragmented. There is also no validation that the category is 1-15 (see also BUG-085).

## Affected Components
POST/PUT /api/scope3, Scope3Form, Scope 3 bulk import, uncertainty dashboard, reports/exports.

## Recommended Fix
Normalise the category to a single canonical form (e.g. integer 1-15 or "Category N") in every create, update and bulk path. Reject values outside 1-15. Migrate existing rows.


### Additional confirmation (BUG-075)

Scope clarification by Agent D (Methane Auditor), the original reporter, after further tracing on the current code (baseline2):
- `services/sentinel5p.py query_satellite_observations()` currently always returns `"summary": None` (status `metadata_only` / `no_acquisitions` / `unconfigured`, Decision D-06). `MethaneExplorer.handleExportToOgmp` returns early when `satelliteObservation.summary` is missing, so **the Explorer button cannot reach the export in the current build**. The defect is reachable via `POST /api/sentinel5p/export-to-ogmp` (any non-IT role, within facility scope), and it becomes reachable from the UI as soon as pixel retrieval is configured.
- Related: the Explorer's "Annualized Satellite Flux" tile and `reconciliationAnalysis` read `summary.annualized_ch4_tonnes`, which no server code produces. They also use a ±35 % band against `intensity-stats.total_ch4` with the Explorer's default `year: "all"` (multi-year sum), whereas the server uses the facility threshold (20 %) per year.
The severity was set before this was known. The coordinator may downgrade it to Low if UI reachability is required.


### Additional confirmation (BUG-075)

Correction by Agent D: the endpoint path in the note above is `POST /api/satellite/sentinel5p/export-to-ogmp`.


---

# BUG-090 — Dehydrator form sends "Contactor Pressure" as `dehy_pressure`, but the server reads `dehy_press`: user pressure silently ignored, 800 psig default always used (AGR "routed to flare"/"flash gas recycled" checkboxes also unread)

**Status:** Confirmed
**Severity:** High
**Category:** UI
**Discovered by:** Agent K (Frontend/UI)

## Location
- `new/client/src/components/scope1/DehydratorForm.jsx` — `onChange("dehy_pressure", …)` (Contactor Pressure (psig) input).
- `new/server/calculations/dispatcher.py` dehydrator branch reads `flat_inputs.get("dehy_press") or flat_inputs.get("contactor_pressure") or 800.0`.
- `new/client/src/components/scope1/AGRForm.jsx` — `flash_gas_recycled`, `offgas_to_flare`, `solvent_type` are sent but no server code reads these keys (grep over `new/server/calculations` and `routes/emissions.py`).

## Reproduction
1. UI :5191 as admin → Emissions → Scope 1 → Region = first facility, Process = Dehydrator (Tier 3).
2. Throughput 1000, pump 5, CH4 85 %, hours 8760, temperature 100 °F, **Contactor Pressure = 200**; submit. Repeat with pressure 1000.
3. API check with the server's own key `dehy_press` (`audit/work/K/fields.py`).

## Input
Contactor pressure 200 psig vs 1000 psig, all else equal.

## Expected
Different CH4 (the server calculator is pressure-sensitive: with `dehy_press` it returns 0.363 t CH4 at 200 psig and 1.613 t at 1000 psig).

## Actual
POST body `calc_inputs.dehydrator = {..., "dehy_pressure": 200, ...}` → response CH4 1.30610 t, CO2e 36.571 t; with 1000 psig → identical 1.30610 t / 36.571 t (records 756/757). That is the 800 psig default. At 200 psig the stored CO2e is 3.6× the value the server would compute for the entered pressure.

AGR: toggling "Acid Gas / Offgas Routed to Flare" and "Flash Gas Recycled" gives byte-identical results (2371.39 t CO2 / 16.331 t CH4).

## Evidence
`audit/work/K/t_dehy.mjs` (browser, captured payloads/responses), `audit/work/K/fields.py` (API). Repro: `audit/repro/BUG-<id>.py`.

## Root Cause
Field-name mismatch between the form (`dehy_pressure`) and the dispatcher (`dehy_press`/`contactor_pressure`); AGR checkbox keys have no server counterpart. No warning is shown for an ignored required input.

## Impact
Every UI-entered dehydrator record ignores the contactor pressure the user typed (marked required); AGR control options displayed to the user have no effect.

## Affected Components
Scope 1 Dehydrator and AGR Tier 3 forms; resulting records and totals.

## Recommended Fix
Rename the form key to `dehy_press` (or accept `dehy_pressure` server-side); map the AGR checkboxes to `agr_control_type` / flash handling or remove them; reject/flag unknown calc_inputs keys.


---

# BUG-091 — Dehydrator throughput entered under the label "MMscf/yr" is saved with unit "MMscf/day" (record activity unit 365× off)

**Status:** Confirmed
**Severity:** Medium
**Category:** UI
**Discovered by:** Agent K (Frontend/UI)

## Location
`new/client/src/components/Scope1Form.jsx` ≈line 1068-1072: `finalUnit = formData.dehy_unit || formData.unit || "MMscf/day"`; `DehydratorForm.jsx` labels the input "Gas Throughput (MMscf/yr)" and has no unit selector (so `dehy_unit` is never set).

## Reproduction
1. UI :5191 admin → Scope 1 → Dehydrator (Tier 3), Gas Throughput (MMscf/yr) = 1000, other required fields filled; submit.

## Input
1000 under the label "Gas Throughput (MMscf/yr)".

## Expected
Record activity `amount: 1000, unit: "MMscf/yr"` (or "MMscf").

## Actual
POST `amount: 1000, unit: "MMscf/day"`; stored record 756 shows 1000 MMscf/day, i.e. 365,000 MMscf/yr of activity in the record table, exports and anything that reads amount/unit.

## Evidence
`audit/work/K/t_dehy.mjs` output: `throughput label: Gas Throughput (MMscf/yr)*` / `amount/unit: 1000 MMscf/day`. Repro `audit/repro/BUG-<id>.mjs`.

## Root Cause
Hard-coded fallback unit contradicts the form label.

## Impact
Activity data audit trail and exports carry the wrong unit (365×); anyone recalculating from amount/unit gets the wrong result.

## Affected Components
Scope 1 dehydrator entry; Recent Activity table; Reports/exports Qty column.

## Recommended Fix
Use "MMscf/yr" (matching the label) or add an explicit unit selector.


### Additional confirmation (BUG-072)

Additional affected component, from Agent D (Methane Auditor), the original reporter, on the current code: **`/api/dashboard/flaring-summary` also ignores `gwp_horizon`**. DashboardEnhanced sends `filterParams` including `gwp_horizon=20`, but the endpoint returns identical output in both horizons (`audit/work/D/s16.py`: `a == b → True`).
For 2025, the routine-flaring tCO2e stays 192,566.34. The expected GWP-20 value, using the app's own delta (CH4 73.23 t × 54.5 + N2O 19.25 t × 3), is 196,614.8. For non-routine it is 96,932.57 → 98,808.1, and for safety 16,516.31 → 16,873.3. The flaring panel therefore stays on GWP-100 while the hero KPIs switch to GWP-20, the same unapplied-horizon pattern as the pending banner.


### Additional confirmation (BUG-085)

Additional evidence from Agent B (Emissions Auditor), `audit/work/B/t18.py`, current code. Bulk date parsing also has **no range validation, and this includes Scope 1**:
- Scope 1 CSV rows `1800-01`, `9999-01` and `2030-13` were all imported (skipped 0) as Pending records with year 1800, year 9999, and month 13.
- Scope 2 `1800-01` and `2030-13` were imported the same way.

Manual POST /api/emissions/ rejects 1800 (422) but accepts year 2099 and auto-Verifies it for admin. The snapshot already holds 4 Verified year-2099 rows and 1 Verified year-1800 row, and `/api/dashboard/years` lists 2099 and 1800.

Additional affected component: `background_processor._process_row` (Scope 1 bulk). Fix: validate year (e.g. 1990 to current year + 1) and month (1-12) in every bulk row processor.


### Additional confirmation (BUG-072)

Arithmetic correction (Agent D): the expected GWP-20 routine-flaring value is 192,566.34 + 73.23×54.5 + 19.25×3 = **196,615.13** (not 196,614.8).


---

# BUG-092 — Maker-checker outcome is invisible to the maker: reject/approve send no notification, the Scope 1 list shows Rejected/Pending rows exactly like Verified ones, and the reject dialog claims the record is "permanently deleted" although it is kept as Rejected

**Status:** Confirmed
**Severity:** Medium
**Category:** UI
**Discovered by:** Agent L (Browser)

## Location
- `new/client/src/pages/ManageData.jsx` reject modal (text "Rejecting will permanently delete the staged record from the pending queue")
- `new/server/routes/emissions.py` `reject_emission` (~L4515-4560: sets `status="Rejected"`, `approved_by=<rejecter>`; logs activity; creates no Notification for `created_by`) and `approve_emission` (same, no maker notification)
- `new/client/src/components/Scope1Form.jsx` "Recent Activity (Scope 1)" table (~L2900-2960): renders a marker only for `status === "Draft"`; no status column although `/api/emissions?scope=1` returns `status`

## Reproduction
1. As audit_user, enter a Scope 1 record through the Scope 1 form (AUDIT-L Plant, 2025-07, Diesel 1000 gal) → id 753, Pending.
2. As audit_admin, Manage Data → Pending Review → Reject #753; the dialog says the record will be permanently deleted; enter reason "Audit L: wrong quantity" → `POST /api/emissions/reject/753` 200 `{"status":"Rejected"}`.
3. As audit_user, reopen Calculations → Scope 1 and check the Recent Activity table and the bell notifications.

## Input
Record 753 (Pending → Rejected), record 754 (Pending → Verified via Approve in the same queue).

## Expected
The dialog describes what actually happens. The maker is notified of the approval/rejection and the reason. The maker's list distinguishes Verified / Pending / Rejected rows (the API already returns `status`).

## Actual
- DB: `emissions.id=753 status='Rejected' approved_by=16` — not deleted; the reason exists only in `activity_log` (id 1354).
- `notifications` created after the approve/reject: 0 rows (the submit created 4 "awaiting your approval" notifications for admins).
- The user's Recent Activity table shows row 753 ("1,000.00 gal … 10.240") with no status, identical to the Verified rows 752/754. `/api/emissions?scope=1` returned 2 Rejected, 2 Pending, 16 Verified rows in the first page, and none of them is marked.

## Evidence
`audit/work/L/w4_maker.mjs`, `w4_approve.mjs approve`, `w4_reject.mjs`, `w4_uview.mjs` output; screenshot `audit/work/L/w4_reject_modal.png`.

## Root Cause
The review workflow notifies only in one direction (maker → checkers). The list UI ignores the `status` field except for Draft, and the modal copy predates the change to soft rejection.

## Impact
Makers cannot tell that a figure they entered was excluded from the inventory, or why, so rejected data is not corrected and resubmitted. Users may also double-enter because Pending rows look final. The dialog misstates the data-retention behaviour to the approver.

## Affected Components
Manage Data Pending Review (approve/reject), Scope 1 form list (Scope 2/3 lists not checked separately), notifications.

## Recommended Fix
Create a Notification for `created_by` on approve/reject including the reason. Add a status badge column (Verified / Pending / Rejected / Draft) to the scope lists. Change the dialog text to "The record will be marked Rejected and excluded from totals".


---

# BUG-093 — Region-restricted superuser can re-region its own facility (PUT /api/facilities/<id>), pushing the facility and all its emissions into another region's scope and out of its own

**Status:** Confirmed
**Severity:** Medium
**Category:** Security
**Discovered by:** Agent I (Backend/API/Security)

## Location
`new/server/routes/facilities.py:220-350` `update_facility()` — checks that the facility is currently in the caller's allowed set, then assigns `facility.region` / `location` / `name` from the payload with no check that the new values stay within the caller's region. `add_facility()` (l.137) and `import_facilities()` do enforce the superuser's region, so behaviour is inconsistent.

## Reproduction
1. Log in as `audit_superuser@audit.local` (superuser, location West).
2. `POST /api/facilities {"name":"ZZ_SOUTH","region":"South",...}` → 403 (correct).
3. `PUT /api/facilities/1 {"region":"South"}`.
Script: `audit/repro/<BUG-ID>.py`.

## Expected
403 — a West-restricted superuser must not assign a facility to another region (same rule as create).

## Actual
200 "Facility updated"; facility 1 region is now "South", carrying its 153 emission rows into South users' scope and dashboards; the West superuser loses access to it (it no longer appears in their `/api/facilities`). Pulling a Center facility into West is correctly denied (403), because the current-region check runs first.

## Evidence
```
create facility in South as West superuser: 403 (correctly denied)
expected: PUT region West->South denied (403) like create; actual: 200, facility 1 region now 'South' with its 153 emission rows
```

## Root Cause
Missing target-region validation in `update_facility`. Region membership (`get_allowed_facility_ids`) is derived from the editable `region` / `location` / `name` columns.

## Impact
A regional superuser can inject its region's data (including Pending/Verified emissions it entered) into another region's inventory and reports, or hide a facility from its own region's reviewers. Region-level totals change without an admin.

## Affected Components
`PUT /api/facilities/<id>` (fields region, location, name); every region-scoped endpoint.

## Recommended Fix
For non-unrestricted superusers, reject updates whose new `region` / `location` / `name` would move the facility outside `user.location` (reuse the create-path check); log old and new values.


---

# BUG-094 — "Net Emissions" KPI subtracts company-wide mitigation whatever the Activity/Division filter (Steel & Iron view: Net = −1,027,393 t) and counts "Planned" projects as achieved reductions

**Status:** Confirmed
**Severity:** High
**Category:** Dashboard
**Discovered by:** Agent F (Dashboard reconciliation auditor)

## Location
- `new/server/routes/dashboard.py` `_query_mitigation(facility_id, year, allowed_fids, segment)`. It has no `activity`/`division` parameters (`get_batch_dashboard_data` does not pass them) and no status filter, so `Planned` projects are returned together with `Active` ones.
- `new/client/src/pages/DashboardEnhanced.jsx` ~L355-360: `totals.mitigation += item.quantity_tco2e` for every item. `netEmissions = totalEmissions - mitigation`. Detailed Breakdown "Net Footprint" uses the same logic.

## Reproduction
1. `python audit/repro/BUG-NNN.py`
2. UI: Activity = "Steel & Iron (Acier DRI)". The Net Emissions card shows a negative value, with "Less 1M Mitigation".

## Input
Snapshot DB: 100 `mitigation_projects` rows, all year 2026: 70 Active (715,500 t) and 30 Planned (312,000 t). None is at a Steel & Iron facility.

## Expected
- Mitigation follows the same facility filter as the gross figure. Steel & Iron: 0 t, Net = Gross = 106.84 t. (The gross value itself is affected by BUG-004.)
- Only implemented or achieved reductions are subtracted. All filters: 715,500 t, not 1,027,500 t.

## Actual
- activity = Steel & Iron: mitigation used = **1,027,500 t**, Net = **−1,027,393.16 t**.
- All filters: mitigation = 1,027,500 t, which includes 312,000 t from Planned projects.

## Evidence
```
activity=Steel & Iron (Acier DRI): gross=106.84 mitigation used=1,027,500.00 (incl. Planned 312,000.00) -> Net=-1,027,393.16 ; expected mitigation (facility activity, implemented only)=0.00
activity=all: gross=3,723,127,249,117.66 mitigation used=1,027,500.00 (incl. Planned 312,000.00) -> Net=3,723,126,221,617.66 ; expected mitigation (facility activity, implemented only)=715,500.00
```

## Root Cause
The mitigation sub-query was not given the Activity or Division filters that the other sub-queries receive. The status of a project is ignored when netting.

## Impact
The Net Emissions KPI and the "Net Footprint" row are wrong for every Activity or Division view and can become negative. Every view overstates reductions by the Planned pipeline (+44 % on the snapshot).

## Affected Components
`/api/dashboard/batch-all` (mitigation), `/api/dashboard/mitigation`; DashboardEnhanced Net Emissions card, Detailed Breakdown "Net Footprint"; ModernReportGenerator mitigation section (same endpoint).

## Recommended Fix
Pass `activity` and `division` to `_query_mitigation` and filter through `Facility`. Exclude `Planned` (and any not-implemented) projects from netting, or show them separately.


---

# BUG-095 — Scope 1 "Recent Activity": Export CSV exports only the 10 rows of the current page, and the Year/Process filter options are built from that page only

**Status:** Confirmed
**Severity:** Medium
**Category:** UI
**Discovered by:** Agent K (Frontend/UI)

## Location
`new/client/src/components/Scope1Form.jsx` — Recent Activity toolbar (≈lines 2700-2790): Year options `[...new Set(entries.map(e => e.year))]`, Process options from `entries`, and `exportToCSV(entries.filter(...))`; `entries` holds only the current server page (`limit=10`).

## Reproduction
1. UI :5191 as admin → Emissions → Scope 1, scroll to "Recent Activity (Scope 1)" (pager "Page 1 of 76", 751 records).
2. Open the Year filter; click "↓ Export CSV".
3. Pick Year = 2026, reopen the Year filter.

## Input
Default view, then Year = 2026.

## Expected
Year options = all years with Scope 1 data (server `/filters/available`: 2099, 2026, 2025, 2024, 2023, 2022, 2021, 2020, 1800); CSV = all records matching the filter (751 unfiltered).

## Actual
- Year options: `All Years, 2026, 2025` only (years present on page 1); 2024 and earlier cannot be selected.
- After choosing 2026 the options collapse to `All Years, 2026` (no way to switch to another year without resetting).
- Export CSV downloads a file with **10** data rows.

## Evidence
`audit/work/K/t_recent3.mjs` output (above); file `audit/work/K/s1export.csv`. Repro `audit/repro/BUG-<id>.mjs`.

## Root Cause
Filter option lists and export are derived from the paginated `entries` state instead of server-side facets / a server export (`/api/emissions/export` exists).

## Impact
Users silently export 10 of 751 records; historic years/processes cannot be filtered from this screen.

## Affected Components
Scope 1 Recent Activity table (Year filter, Process filter, Export CSV).

## Recommended Fix
Populate options from `/api/filters/available` (or a facets endpoint) and export through `/api/emissions/export` with the active filters.


---

# BUG-096 — Scope 2 form: switching Source Type to Steam/Heat or CHP leaves the hidden unit at "kWh" — dropdown shows "Select..." but the request sends unit "kWh" (1000 "MMBtu" of steam booked as 3.41 MMBtu)

**Status:** Confirmed
**Severity:** Medium
**Category:** UI
**Discovered by:** Agent K (Frontend/UI)

## Location
`new/client/src/components/Scope2Form.jsx` — `const [unit, setUnit] = useState("kWh")` (line ≈36); the Unit `CustomDropdown` swaps its options by `sourceType` (Btu/MMBtu/MJ for steam) but `unit` is never reset when `sourceType` changes and `handleAddEntry` does not validate it against the current options.

## Reproduction
1. UI :5191 as admin → Emissions → Scope 2, pick a facility.
2. Source Type = "Indirect Steam / Heat"; Boiler Efficiency 0.8, Transmission Loss 0; Usage Amount 1000; leave Unit (it displays "Select...").
3. Submit.

## Input
1000, Unit shown as "Select..." (the only choices offered are Btu / MMBtu / MJ).

## Expected
Either the form forces a unit choice, or the default is one of the displayed steam units.

## Actual
POST `/api/scope2` body contains `"amount":1000,"unit":"kWh"`; server converts 1000 kWh → `heat_mmbtu 3.412142`, `co2e 0.2263 t` (record 39). Had the user meant MMBtu (the record inspector for steam labels the amount "MMBtu") the correct value is 66.3 t (1000 × 53.06 / 0.8 / 1000) — 293× understated, with no warning. CHP entries also show "Select..." for Unit.

## Evidence
`audit/work/K/t_s2.mjs steam` — `unit displayed: "Select..."`, POST body and 201 response above. Repro `audit/repro/BUG-<id>.mjs`.

## Root Cause
Stale unit state from the electricity option set; no validation that `unit` belongs to the current option list.

## Impact
Silent, invisible unit on Scope 2 steam/heat records; large understatement if the user assumes MMBtu.

## Affected Components
Scope 2 manual entry (Indirect Steam / Heat, CHP).

## Recommended Fix
Reset `unit` in the Source Type `onChange` (e.g. to "mmbtu" for steam) and block submit when `unit` is not one of the displayed options.


---

# BUG-097 — CHP allocation form labels Power Output "MWh" but the server uses the number as MMBtu: heat share (and Scope 2 tCO2e) overstated ~2.7× with WRI efficiency method

**Status:** Confirmed
**Severity:** Medium
**Category:** UI
**Discovered by:** Agent K (Frontend/UI)

## Location
- `new/client/src/components/Scope2Form.jsx` — "Power Output (MWh)" input → `calc_inputs.cogen_allocation.power_output`.
- `new/server/routes/scope2.py` `_calc_cogen_allocation`: `power_output = float(data.get("power_output_mwh") or ci.get("power_output", 0)); power_mmbtu = power_output` (no ×3.412142).

## Reproduction
1. UI :5191 admin → Scope 2 → Source Type "CHP / Cogeneration Allocation".
2. Heat Output (MMBtu) 100, Power Output (MWh) 100, Method WRI Efficiency, Total Facility Emissions 1000 tCO2e; submit.

## Input
Heat 100 MMBtu, power 100 MWh (= 341.21 MMBtu), 1000 tCO2e total.

## Expected
WRI efficiency method (e_H 0.8, e_P 0.33, the server's own constants): heat share = (100/0.8) / (100/0.8 + 341.21/0.33) = 125 / 1158.98 = 10.79 % → **107.9 tCO2e**.

## Actual
Response/record 40: `co2e 292.04 tCO2e` = 125 / (125 + 100/0.33) — power treated as 100 MMBtu. 2.71× overstated. (Energy-content method: 50 % instead of 22.7 %.)

## Evidence
`audit/work/K/t_s2.mjs cogen` — POST `{"cogen_allocation":{"total_emissions":1000,"heat_output":100,"power_output":100,"allocation_method":"wri_efficiency"}}` → 201 `co2e 292.035`. Repro `audit/repro/BUG-<id>.mjs`.

## Root Cause
Unit contract mismatch: the UI asks for MWh, the server variable is named `power_mmbtu` but is never converted (even the explicit `power_output_mwh` key is not converted).

## Impact
Every CHP allocation entered through the UI over-allocates emissions to heat (Scope 2) by a factor that depends on the power/heat ratio.

## Affected Components
Scope 2 CHP / Cogeneration Allocation entry; Scope 2 totals.

## Recommended Fix
Convert MWh → MMBtu (×3.412142) on the server (or send MMBtu from the client and relabel), and name the payload key with its unit.


---

# BUG-098 — Emission Calculation Result panel rounds gas masses to 3 decimals of a tonne: non-zero CH4/N2O shown as "0.00 tonnes"

**Status:** Confirmed
**Severity:** Low
**Category:** UI
**Discovered by:** Agent K (Frontend/UI)

## Location
`new/client/src/components/EmissionResult.jsx` local `formatNumber` (min 2 / max 3 fraction digits) used for CO2, CH4, N2O, CO and the confidence-interval tooltips.

## Reproduction
1. UI :5191 admin → Scope 1 → Tier 3 Stationary Combustion, 1000 m³, factors CO2 53.06 / CH4 0.001 / N2O 0.0001 kg/MMBtu, HHV 38 MJ/m³, efficiency 99.5 %; submit.
2. Read the result panel that opens.

## Input
Server response `emissions.ch4 = 3.6017e-05`, `n2o = 3.6017e-06` (t).

## Expected
A non-zero, readable value (e.g. "0.000036 t" / "36.0 kg"), consistent with the Recent Activity table which shows CH4 with 5 decimals ("0.00004").

## Actual
"CH₄ METHANE 0.00 tonnes", "N₂O NITROUS OXIDE 0.00 tonnes"; uncertainty tooltip margins are likewise rounded to 0.00.

## Evidence
`audit/work/K/t_hhv.mjs` output: `RESULT PANEL: … CO₂ 1.911 tonnes CH₄ METHANE 0.00 tonnes N₂O NITROUS OXIDE 0.00 tonnes …` (record 759).

## Root Cause
Fixed tonne scale with 3-decimal maximum for all gases.

## Impact
Methane/N2O from small sources appear to be zero on the confirmation screen (misleading, especially for methane reporting); same record shows different values elsewhere.

## Affected Components
EmissionResult modal (Scope 1 and Scope 2 submissions).

## Recommended Fix
Use significant-figure formatting or switch to kg below 1 t.


---

# BUG-099 — Scope 2 electricity create trusts client-supplied `co2e` / `emission_factor`: 0 kWh can be booked as 12,345 tCO2e, negative Scope 2 (-500 t) is accepted, and any unknown grid region takes the client's factor

**Status:** Confirmed
**Severity:** High
**Category:** API
**Discovered by:** Agent L (Browser)

## Location
`new/server/routes/scope2.py` `POST /api/scope2` (~L176-203): `co2e = float(data.get("co2e", 0))`, `emission_factor = float(data.get("emission_factor", 0))`; the server recomputes only `if emission_factor > 0 and (electricity_kwh > 0 or co2e == 0)`, and uses the client EF when `grid_region` is not in `GRID_FACTORS`. No sign/range check on `co2e`, `electricity_kwh` or `emission_factor`. The UI (`Scope2Form.jsx` ~L175-190) computes and sends `co2e` and `emission_factor` itself.

## Reproduction
Run `node audit/repro/BUG-098.mjs` (renamed below) or, logged in on :5190 as audit_user / audit_superuser, `POST /api/scope2` with:
1. `{"year":2025,"month":9,"facility_id":173,"source_type":"electricity","grid_region":"Algerian National Grid","electricity_kwh":0,"emission_factor":0,"co2e":12345}`
2. `{"...":"...","grid_region":"My Supplier","electricity_kwh":0,"emission_factor":0,"co2e":-500}`
3. `{"...":"...","grid_region":"My Supplier","electricity_kwh":1000,"emission_factor":0.001,"co2e":999}`

## Input
See above (facility 173 "AUDIT-L Plant", region West).

## Expected
The server derives Scope 2 CO2e only from activity data × a server-resolved factor. It rejects zero/negative consumption with a non-zero CO2e, rejects negative CO2e, and rejects unknown grid regions (or requires a documented supplier/market factor with validation).

## Actual
All return 201. DB (`scope2_emissions`):
- id 42 (user, Pending): `electricity_kwh=0, emission_factor=0.522, co2e=12345.0`
- id 41 (user, Pending): `electricity_kwh=0, co2e=-500.0`
- id 40 (user, Pending): `electricity_kwh=1000, emission_factor=0.001, co2e=0.001` (client factor on an unknown region)
- ids 43-46: the same payloads as audit_superuser are stored **Verified** directly (BUG-060), e.g. id 46 `0 kWh → 12345 t`, id 45 `-500 t`, and are counted in dashboard totals.

## Evidence
`audit/work/L/s2trust.mjs` output (user and superuser runs) and the SQL above. The normal UI flow (id 38: 1000 kWh × 0.522 = 0.522 t) matches the server result, so the UI path hides the problem.

## Root Cause
The endpoint was written to accept a client-calculated result and only overrides it when its own inputs are positive. There is no input validation for the direct `co2e` path, and `GRID_FACTORS` lookups that miss fall back to the client EF.

## Impact
Scope 2 totals, the dashboard, SBTi Scope 1+2 progress and intensity can be set to arbitrary values (including negative, which offsets real emissions) without any consumption data. For superusers this is immediately Verified. Integrity of the reported Scope 2 inventory cannot be guaranteed.

## Affected Components
`POST /api/scope2` (electricity; update path not checked), Scope 2 aggregation in dashboard/SBTi/intensity/reports.

## Recommended Fix
Ignore client `co2e`/`emission_factor` for electricity; require `electricity_kwh > 0` (or amount+unit) and a known grid region, or a separately validated market-based instrument (supplier factor with evidence field, 0 ≤ EF ≤ plausible max). Reject negative/non-finite values with 400.


### Additional confirmation (BUG-099)

Correction by Agent L: the repro for this bug is `audit/repro/BUG-099.mjs` (the draft text referred to BUG-098 by mistake).

---

# BUG-100 — Pneumatic controllers calculator cites obsolete 2009 Section 6.10, conflates hourly bleed with actuation volume, and lacks API 2021 Tables 6-14/6-15 and Eq 6-14 malfunction model

**Status:** Confirmed
**Severity:** High
**Category:** Calculation / Methodology
**Discovered by:** API GHG Compendium Section 6 Auditor

## Location
- `new/server/calculations/vented.py:2149` `PneumaticDeviceCalculator.__init__` cites "Section 6.10" (which in 2021 Compendium is Crude Oil Transport). In 2021 Compendium, Pneumatic Controllers are covered in §6.3.6 (Production), §6.4.1 (Gathering & Boosting), §6.5.1 (Processing), §6.6.3 (Transmission & Storage), and §6.8.1 (Distribution).
- `new/server/calculations/vented.py:2184-2195` `PneumaticDeviceCalculator.calculate()` treats 13.5 as "scf/event", whereas API Table 6-15 establishes 13.5 scfh as the whole gas emission factor per hour for intermittent controllers.
- Lacks Tier 1 defaults for continuous low-bleed (1.39 scfh / 0.207 t CH4/yr) and high-bleed (37.3 scfh / 5.56 t CH4/yr) per Table 6-14, and intermittent normal (13.5 scfh / 2.01 t CH4/yr) and malfunctioning (24.0 scfh / 3.58 t CH4/yr) per Table 6-15, as well as EPA Subpart W Eq W-30 / API Eq 6-14 for operating hours with malfunction periods.

## Input
Pneumatic device inventory with continuous low-bleed controllers or intermittent controllers with documented malfunction hours.

## Expected
Compliance with API Compendium 2021 §6.3.6:
- Tier 1: Selection of controller type (Continuous Low-Bleed, Continuous High-Bleed, Intermittent Vent) applying Table 6-14 and Table 6-15 factors.
- Tier 2: Engineering calculation supporting Eq 6-12 (pressure-based bleed), Eq 6-13 (actuation volume * actuations), and Eq 6-14 (EPA W-30 accounting for normal hours T - T_mf and stuck/malfunctioning hours T_mf).
- Site gas composition scaling (x_CH4 / 0.816 and native CO2 conversion).

## Actual
Falls back to a single hard-coded formula that forces user-entered bleed rate or misinterprets 13.5 scfh as scf/actuation.

## Fix
Update `PneumaticDeviceCalculator` to fully implement API Compendium 2021 §6.3.6 (Tables 6-14, 6-15, Equations 6-12, 6-13, 6-14), add chemical injection pumps (§6.3.7 Table 6-16), and update references.


---

# BUG-101 — Vessel and pipeline blowdown calculation depressurization formula includes residual atmospheric volume, overestimating vented volume by 1.0 physical vessel volume per event

**Status:** Confirmed
**Severity:** Medium
**Category:** Physics / Calculation
**Discovered by:** API GHG Compendium Section 6 Auditor

## Location
- `new/server/calculations/vented.py:1928-1960` `BlowdownCalculator.calculate()`:
  `p_initial_psia = to_psia(pressure, press_unit)` (which adds 14.696 to psig)
  `p_factor = p_initial_psia / STD_PRESSURE_PSIA`
  `v_std_per_event = blowdown_volume * p_factor * t_factor * (1.0 / z)`

## Root Cause
When an operational vessel or pipeline is blown down to atmospheric pressure (P_atm = 14.696 psia), the residual gas remaining inside the physical volume after depressurization is V_physical at atmospheric pressure (1.0 atm). The vented volume released to the atmosphere is governed by Delta P = P_initial - P_final = P_gauge.
By multiplying V_physical by P_psia / P_std = (P_gauge + 14.696) / 14.696 = (P_gauge / P_std) + 1.0, the calculator incorrectly assumes the vessel is evacuated to absolute zero vacuum (0 psia), thereby overstating emissions by 1.0 * V_physical for every depressurization event.

## Expected
Per API Compendium 2021 Appendix B.6.1 and Exhibit 6-25:
n = ((P_initial - P_final) * V_physical) / (Z * R * T) where P_final = P_std = 14.696 psia (i.e. P_initial - P_final = P_gauge).

## Fix
Correct the pressure factor to use differential blowdown pressure (P_initial_abs - P_final_abs) / P_std (defaulting P_final_abs = P_std when blowing down to atmosphere).


---

# BUG-102 — Storage tank flashing emissions evaluate to zero when GOR is omitted, lacking API 2021 Table 6-22/6-24 default factors and engineering correlations (VBE, Standing, EUB)

**Status:** Confirmed
**Severity:** High
**Category:** Calculation / Missing Methodology
**Discovered by:** API GHG Compendium Section 6 Auditor

## Location
- `new/server/calculations/vented.py:2044-2100` `TankFlashingCalculator.calculate()`:
  `total_gas_scf = float(throughput) * float(gas_oil_ratio or 0.0)`
  When `gas_oil_ratio` is not explicitly provided by the user, `total_gas_scf` evaluates to 0.0 and zero emissions are reported.

## Root Cause
The calculator does not integrate API Compendium 2021 Section 6.3.9 Tier 1 flashing factors:
- Table 6-22: Crude oil flashing loss emission factors (Small wells <= 10 bbl/day: 33.7 scf CH4/bbl; Large wells > 10 bbl/day: 41.5 scf CH4/bbl; Average: 38.3 scf CH4/bbl).
- Table 6-24: Production condensate flashing loss factors (Small wells <= 10 bbl/day: 124.7 scf CH4/bbl; Large wells > 10 bbl/day: 205.9 scf CH4/bbl).
Nor does it support Tier 2 Vasquez-Beggs Equations (Eq 6-20, 6-21, Table 6-20), Standing Correlation (Eq 6-22, 6-23, Table 6-21), or EUB Rule-of-Thumb (Eq 6-24).

## Expected
Seamless tier support:
- Tier 1: Fallback to Table 6-22 / Table 6-24 emission factors based on liquid type (crude oil vs condensate) and well production size (<= 10 vs > 10 bbl/day).
- Tier 2: Engineering calculation using VBE, Standing, EUB, or site GOR.
- In addition, handle separator dump valve malfunctions (Eq 6-25, Table 6-25) and produced water tanks (Table 6-26, 6-27).

## Fix
Enhance `TankFlashingCalculator` with complete API Section 6.3.9 methodology and reference data.


---

# BUG-103 — Completion flowback and mud degassing calculators omit offshore exploration and completion emission factors

**Status:** Confirmed
**Severity:** Medium
**Category:** Completeness / Regulatory
**Discovered by:** API GHG Compendium Section 6 Auditor

## Location
- `new/server/calculations/vented.py:136-140` `MudDegassingCalculator.TABLE_6_2_ONSHORE` omits the API Table 6-2 offshore drilling emission factor of 0.0034 tonnes CH4 / drilling day.
- `new/server/calculations/vented.py:347-867` `CompletionFlowbackCalculator` contains zero references or logic for API Compendium 2021 Table 6-7 (Offshore Well Completions: Gas well 136.2 tonnes CH4 / completion-day, Oil well 0.005 tonnes CH4 / well).

## Expected
Full coverage of onshore and offshore exploration activities per API Compendium 2021 Table 6-2 and Table 6-7.

## Fix
Integrate offshore factors and well types into `MudDegassingCalculator` and `CompletionFlowbackCalculator`.


---

# BUG-104 — Complete absence of API Compendium 2021 Section 6 venting calculators across upstream, midstream, downstream, and CCUS segments

**Status:** Confirmed
**Severity:** Critical
**Category:** Completeness / Missing Modules
**Discovered by:** API GHG Compendium Section 6 Auditor

## Location
`new/server/calculations/`, `new/server/emission_factors_api2021.py`, `new/client/src/components/scope1/`

## Missing Sources Identified
The repository lacks implementations for the following authoritative API Compendium 2021 Section 6 venting/process sources:
1. §6.2.2 Well Testing (Eq 6-1, Eq 6-2, Eq 6-3, Table 6-4, Exhibit 6-2)
2. §6.2.4 Coal Seam Exploratory Drilling and Well Testing (Exhibit 6-5)
3. §6.3.2 Workovers without Hydraulic Fracturing (Table 6-9, Exhibit 6-7)
4. §6.3.5 Casing Gas Vents (Table 6-12, Table 6-13, Exhibit 6-9, Exhibit 6-10)
5. §6.3.7 Gas-Driven Pneumatic Pumps (Chemical Injection Pumps, Eq 6-15, Eq 6-16, Table 6-16)
6. §6.3.8.2 Desiccant Dehydration (Eq 6-17, Exhibit 6-15) & SRU Claus Tail Gas CO2 (Eq 6-19)
7. §6.3.9.2 Separator Dump Valve Failures (Eq 6-25, Table 6-25) & Produced Water Tanks (Table 6-26, 6-27, Exhibit 6-21)
8. §6.3.10 CO2-EOR Production-Related Venting Operations (Eq 6-26, Eq 6-27, Exhibit 6-22)
9. §6.3.11 Other Production-Related Non-Routine Venting (Eq 6-28, Table 6-28)
10. §6.4 Gathering & Boosting Venting: Compressors (Table 6-30 rod packing/seals, Table 6-32 blowdowns), Tanks (Table 6-31), Pig Traps (Eq 6-30), Non-routine (Table 6-33, Exhibit 6-27)
11. §6.5 Natural Gas Processing: Compressors (Table 6-37, Table 6-38), Blanketed Tanks (Exhibit 6-29), Non-routine (Table 6-39)
12. §6.6 Natural Gas Transmission & Storage: Compressors (Table 6-40, Table 6-41), Pipeline blowdowns (Table 6-43, Table B-17, Exhibit 6-33)
13. §6.7 LNG Operations: Boil-off gas venting vs re-liquefaction, loading losses, shipping, terminals (Table 6-44)
14. §6.8 Natural Gas Distribution: Controllers (Table 6-45), M&R stations, Mains/Services blowdowns (Table 6-46, Exhibit 6-34)
15. §6.9 Enhanced Oil Recovery, Carbon Capture, and Geological Storage
16. §6.10 Crude Oil Transport: Loading Losses (Eq 6-31, Table 6-47, Exhibit 6-35), Ballasting (Eq 6-32, Table 6-48, Exhibit 6-36), Marine Transit (Eq 6-33, Table 6-49, Exhibit 6-37)
17. §6.11 Refining: Catalyst Regeneration (FCCU Eq 6-34 to 6-37, Exhibit 6-38; CCR Exhibit 6-39; Semi-regen Exhibit 6-40), Cokers (DCU Eq 6-42 to 6-47; Fluid coker Exhibit 6-41), Refinery Hydrogen Plants (SMR/POX Eq 6-49, 6-50, Table 6-50, 6-51, Exhibit 6-42, 6-43, 6-44), Asphalt Blowing (Eq 6-51, 6-52, Table 6-52, Exhibit 6-45), Coke Calcining (Eq 6-53)
18. §6.12 Petrochemical Manufacturing: Chemical Production Emission Factors (Table 6-53)
19. §6.14 Fire Suppression Clean Agent Releases (Eq 6-46)

## Fix
Implement all missing Section 6 calculation engines, populate reference data, integrate with dispatcher and frontend, and verify against API golden cases.


### Additional confirmation (BUG-033)

Independently confirmed by Agent K (Frontend/UI).

New affected component: the OGMP 2.0 Excel export (`GET /api/reports/ogmp-export`, `routes/reports.py` ≈L814-913) builds gas production with
`GAS_UNIT_TO_M3.get(str(p.gas_unit or "mscf").lower(), 28.3168)`; the table has "m3" but not the "m³" spelling that the Manage Data production form stores
(`ManageData.jsx` gas/oil unit `<option value="m³">`), so m³ production rows are multiplied by 28.3168 in the export as well (methane intensity denominator 28× too high → intensity 28× too low).
The Manage Data "Convert m³" helper converts to mscf correctly (×0.0353147) — only rows saved with the m³ unit option are affected.
Client-side fix option: send the ASCII value "m3" from the unit `<select>` (display label can stay "m³").


---

# BUG-105 — Manage Data and Reference Data swallow API load errors and show them as empty data ("No production record found", empty factor catalog)

**Status:** Confirmed
**Severity:** Medium
**Category:** UI
**Discovered by:** Agent K (Frontend/UI)

## Location
- `new/client/src/pages/ManageData.jsx` ≈lines 740-820: `fetchFacilities`, `fetchCustomFactors`, `fetchProduction`, `fetchSources`, `fetchMitigations`, `fetchCbamExports`, `fetchOgmpSurveys`, `fetchGoals`, `fetchBaseYears` all end in `catch (err) { console.error(err); }` — no toast, no error state.
- `new/client/src/pages/ReferenceData.jsx` `fetchData` (≈line 33): `Promise.all([/custom-factors, /emission-factors])` with `catch → console.error`, so one failing endpoint also discards the other.

## Reproduction
1. Playwright, admin on :5191; intercept `GET /api/data/production` → HTTP 500; open Manage Data → Production Data.
2. Intercept `GET /api/custom-factors` → HTTP 500; open Reference Data.

## Input
Server error (500) on a list endpoint.

## Expected
An error message/retry ("Failed to load production data") distinct from an empty result; Reference Data should still show the emission-factor catalog that loaded successfully.

## Actual
- Manage Data: table shows "No production record found." / "Page 1 of 1"; no toast (toast container empty).
- Reference Data: page renders 40 table rows instead of 229 — the whole API emission-factor catalog disappears because the custom-factors call failed; no message.

## Evidence
`audit/work/K/t_err.mjs`, `audit/work/K/t_err2.mjs` output: `normal: {"rows":229}` vs `custom-factors 500: {"rows":40,"toast":""}`. Repro `audit/repro/BUG-<id>.mjs`.

## Root Cause
Errors logged to console only; `Promise.all` couples independent loads.

## Impact
Users (and approvers) can conclude that production data, factors, goals or surveys do not exist, and may re-enter data (duplicates) or report intensity as "pending production data" during transient backend failures.

## Affected Components
Manage Data tabs (Regions, Factors, Production, Sources, Goals/Base years, Mitigation, OGMP surveys, CBAM); Reference Data library.

## Recommended Fix
Surface a toast/error panel with retry per section; use `Promise.allSettled` in ReferenceData.


---

# BUG-106 — User Management actions are missing from the Audit Trail: account creation and logout logs are never committed, and user deletion is not logged at all

**Status:** Confirmed
**Severity:** Medium
**Category:** Security
**Discovered by:** Agent K (Frontend/UI)

## Location
`new/server/routes/auth.py`:
- `register()` (also used by `POST /api/auth/users`, the User Management "Create user" button): `db.session.commit()` at ≈L297 happens **before** `log_activity_and_notify(action="REGISTER", …)` (≈L301); no commit follows, so the ActivityLog/Notification rows are discarded.
- `logout()` (≈L485-512): `log_activity_and_notify(action="LOGOUT")` then `session.clear()` and return — never committed.
- `delete_user()` (≈L1060-1117): no `log_activity_and_notify` call at all.
(`utils.log_activity_and_notify` adds to the session without committing, per the project's own convention.)

## Reproduction
1. As it_admin: `POST /api/auth/register` (or create a user in User Management), then `DELETE /api/auth/users/<id>`, then `POST /api/auth/logout` (`audit/work/K/reg2.py`, own db copy).
2. Query `activity_log` for the new user's email / REGISTER / LOGOUT; open Audit Trail in the UI.

## Input
Create user k…@audit.local (id 22), delete it, log out.

## Expected
Audit Trail entries for REGISTER/CREATE user, DELETE user and LOGOUT.

## Actual
`register 201`, `delete 200`, `logout 200`; `activity_log` contains no row mentioning the user's email and `select count(*) … where action='LOGOUT'` = 0. The UI DB (audit/db/ui.db) after a full day of activity has actions CREATE/DELETE/EXPORT/LOGIN/UPDATE only — never REGISTER or LOGOUT.

## Evidence
`audit/work/K/reg2.py` output above; repro `audit/repro/BUG-<id>.py`.

## Root Cause
Log helper called after the only commit (register, logout); missing call (delete_user).

## Impact
Privileged account lifecycle (who created or removed which account, when) cannot be reconstructed from the Audit Trail; the Audit Trail page gives an incomplete record for IT/security review.

## Affected Components
Audit Trail page and export, User Management (create/delete), logout.

## Recommended Fix
Call the logger before the commit (or commit again afterwards) in register/logout, and log DELETE in delete_user with the deleted user's identity.


### Additional confirmation (BUG-044)

Related evidence from Agent L (Browser), the converse side of the same inconsistent BOE derivation: the main Carbon Intensity page and dashboard intensity (`/api/dashboard/intensity-stats`, `/intensity-trend`) ignore the MMBOE fields that the Manage Data → Production Data form collects.
- Through the UI I saved production for AUDIT-L Plant (facility 173) 2025-06 with Crude Oil 1000 MMBOE and Total Production 0.5 MMBOE, Oil/Gas amount left 0 → `POST /api/data/production` 201, row 975 stored `crude_oil_mmboe=1000, total_production_mmboe=0.5, oil_amount=0, gas_amount=0`.
- `/carbon-intensity` filtered to AUDIT-L Plant / 2025 shows "GHG INTENSITY: Pending Production", "COMBINED PRODUCTION (BOE) 0", and `intensity-stats?year=2025&facilityId=173` (uncached key) returns `total_boe 0.0`, while `/granular-intensities` would use 0.5 MMBOE for the same row. The same production record therefore yields "no production" on one page and 500,000 BOE on the Master Report.
- The form also accepts components larger than the total (crude 1000 MMBOE vs total 0.5 MMBOE) with no consistency check.
Screenshot `audit/work/L/w11_ci.png`; scripts `audit/work/L/w11_prod.mjs`, `w11_ci.mjs`.


---

# BUG-107 — CustomDropdown is not keyboard-operable and form inputs have no programmatic labels: Region, Process Type, Emission Factor and Unit cannot be set without a mouse

**Status:** Confirmed
**Severity:** Medium
**Category:** UI
**Discovered by:** Agent K (Frontend/UI)

## Location
- `new/client/src/components/CustomDropdown.jsx` — trigger is `<div className="dropdown-selected" onClick={handleToggle}>` (≈L114): no `tabIndex`, `role`, `aria-haspopup/expanded`, or key handlers; options are clickable `<div>`s.
- Forms use `<label>` without `htmlFor` and inputs without `id`/`aria-label` (Scope1Form, Scope2Form, ManageData, Reports, AuditTrail, ReferenceData).

## Reproduction
1. UI :5191 admin → Emissions → Scope 1; focus "Group Name" and press Tab repeatedly (`audit/work/K/t_kbd.mjs`).
2. Count visible inputs/selects without an accessible name on each page (`audit/work/K/t_mobile.mjs`).

## Input
Keyboard only.

## Expected
Tab order reaches Region, Emission Source, Process Type, factor and Unit pickers; they open with Enter/Space and options are selectable with arrow keys; each input has an accessible name.

## Actual
Tab order: Group Name → Equipment ID → Tier 1/2/3 buttons → Quantity → Save as Draft → Submit … — every CustomDropdown is skipped (Region trigger: `tabIndex -1, role null, aria-haspopup null`). Submitting then fails with "Please fill in all identity fields (Year, Month, Region, Process)". Unlabelled form controls (no associated label/aria-label): Scope 1 11/11, Scope 2 6/6, Manage Data 15/15, Reports 12/12, Audit Trail 6/6, Reference Data 2/2.

## Evidence
`t_kbd.mjs` focus sequence and `t_mobile.mjs` output. Repro `audit/repro/BUG-<id>.mjs`.

## Root Cause
Custom div-based listbox without focus management/ARIA; labels not associated with controls.

## Impact
Keyboard and screen-reader users cannot record Scope 1/2 activity data at all (required pickers unreachable); fails WCAG 2.1.1 / 4.1.2 / 1.3.1.

## Affected Components
All pages using CustomDropdown (Scope 1/2/3 forms, dashboard filters, import wizards) and all forms listed above.

## Recommended Fix
Make the trigger a `<button aria-haspopup="listbox" aria-expanded>`, options `role="option"` with arrow-key navigation, and associate labels via `htmlFor`/`id` (or `aria-labelledby`).


---

# BUG-108 — Scope 1 entry form does not reflow at phone width (390 px): Field input, Tier selector and factor picker are clipped off-screen

**Status:** Confirmed
**Severity:** Low
**Category:** UI
**Discovered by:** Agent K (Frontend/UI)

## Location
`new/client/src/components/Scope1Form.jsx` / `Scope1Form.css` — identity grid keeps 4 columns (Activity / Division / Region / Field) and the process section keeps 2 columns at 390 px; the card clips overflow.

## Reproduction
1. Playwright viewport 390×844, admin, open /emissions?scope=scope1 (`audit/work/K/t_mobile.mjs`).

## Input
390 px viewport.

## Expected
Single-column layout; every control fully visible.

## Actual
Screenshot `audit/work/K/m390__emissions_scope_scope1.png`: "Field" input cut at the right edge, Activity/Division inputs ~45 px wide ("Aut"), "Calculation Methodology" tier buttons and "Select Standard Em…" picker extend past the card edge and are clipped (document scrollWidth stays 390, so the hidden parts cannot be scrolled to).

## Evidence
Screenshot above.

## Root Cause
Fixed multi-column grid without a small-screen breakpoint.

## Impact
Tier 2/3 selection and some fields are unusable on phones.

## Affected Components
Scope 1 form (and Scope 2 form grids, same pattern).

## Recommended Fix
Add a `@media (max-width: 600px)` rule collapsing `.form-grid-*`/identity grid to one column and wrapping the tier selector.


---

# BUG-109 — Scope 1 form saves an entry with no Unit selected: the client silently assumes m³ (10 → 2,641.72 gal stored) while the server calculates from the raw 10 in calc_inputs, so the stored activity and its emissions disagree 264×

**Status:** Confirmed
**Severity:** Medium
**Category:** UI
**Discovered by:** Agent L (Browser)

## Location
- `new/client/src/components/Scope1Form.jsx` `handleAddEntry` (~L820-850): `let finalUnit = formData.unit || "m3";` then the Tier 1 `baseUnit` auto-conversion rewrites `quantity/amount/unit` (10 "m3" → 2641.72 gal). The validation block (~L659-690) checks year/month/facility/process/fuel/amount > 0 but not the unit. `calc_inputs[processType]` is built from raw `formData` (amount 10, no unit).
- Server `POST /api/emissions/` computes from `calc_inputs.combustion` (amount 10, unit absent → factor base unit) but stores the top-level `quantity`/`unit` (2641.72 gal).

## Reproduction
1. Log in on :5190 as audit_admin → Calculations → Scope 1.
2. Region AUDIT-L Plant, 2025-03, Stationary Combustion, Tier 1 "Diesel (No. 2 Fuel Oil)", quantity 10, leave Unit at "Select...".
3. Save as Draft (or Submit). No warning; toast "Entry saved as draft".
4. Repeat with quantity 2641.72 and Unit gal for comparison.
Script: `node audit/repro/BUG-NNN.mjs`.

## Input
Quantity 10, Unit not selected; comparison 2641.72 gal.

## Expected
The form refuses to submit without a unit ("Please select a unit"), and in any case the stored activity quantity/unit and the stored emissions describe the same activity.

## Actual
Request: `quantity 2641.72, unit "gal", calc_inputs {"combustion":{"fuel":"Diesel (No. 2 Fuel Oil)","amount":10}}` → 201. Record 759 stores `quantity=2641.72 gal, co2e_total=0.1024 t`. The same 2641.72 gal entered explicitly gives 27.05 t. The Recent Activity table, CSV export and reports show "2,641.72 gal … 0.102 tCO2e".

## Evidence
`audit/repro/BUG-NNN.mjs` output:
```
no unit: request 2641.72 gal (calc_inputs {"combustion":{"fuel":"Diesel (No. 2 Fuel Oil)","amount":10}}) -> record 2641.72 gal, 0.10240014 t
same stored activity entered explicitly: 2641.72 gal -> 27.051249784079996 t
```
DB `emissions.id=759`.

## Root Cause
A hidden default unit ("m3") on the client instead of a required-field check. The client sends two different representations of the activity (converted top-level vs raw calc_inputs), and the server calculates from one and persists the other without checking they agree.

## Impact
Silent data-quality defect: an entry the user never gave a unit for is saved, and its recorded activity data cannot be reconciled with its emissions (264× here). Auditors comparing activity × factor against CO2e find unexplainable records; the user may believe they entered 10 gal or 10 m³ and either reading is wrong in one of the two fields.

## Affected Components
Scope 1 form (all Tier 1 fuels with a `baseUnit`), `POST /api/emissions/` persistence of quantity/unit.

## Recommended Fix
Require a unit in `handleAddEntry` (no "m3" fallback). Send one activity representation. On the server, reject a request whose top-level quantity/unit and calc_inputs amount/unit disagree, or persist exactly the values used in the calculation.


### Additional confirmation (BUG-109)

Repro path: `audit/repro/BUG-109.mjs` (the draft said BUG-NNN.mjs). Added by Agent L.


---

# BUG-110 — Onshore fugitives "Tier 1: Facility-Level" form: the on-screen preview says 16,644 tCO2e but the saved record is 1.456 tCO2e — the server ignores the selected facility type and duration and books the facility count as a count of valves

**Status:** Confirmed
**Severity:** High
**Category:** Emissions
**Discovered by:** Agent L (Browser)

## Location
- Client: `new/client/src/components/scope1/FugitivesForm.jsx` (Tier 1 facility-level inputs L650-715; "REAL-TIME CLIENT-SIDE ESTIMATION ENGINE" L317+, banner "ESTIMATED EMISSIONS PREVIEW (REAL-TIME API CALCULATION)" L1258+). Operating duration is displayed as a placeholder (365) and only enters `formData` when the user types in it; facility type/`fuel` only when the dropdown is changed.
- Server: `new/server/calculations/legacy_engine.py` ~L552-571 (`process == "fugitive"`): reads `calc_inputs.fugitive.method` (absent → "average"), `component` (absent → "valves") and `count = amount`; `facility_type`, `fugitive_tier`, `operating_days` are never read. Result tagged `calc_method = "server_fugitive_average"`.

## Reproduction
1. :5190 as audit_admin → Calculations → Scope 1; Region AUDIT-L Plant, 2025-05; Process "Onshore Equipment Leaks / Fugitives (API Chapter 7)" (Tier 1 Facility-Level shown by default).
2. With the visible defaults (Gas Production Facility, count 1, 365 days, preview 8,322 tCO2e) click "Calculate & Submit" → warning "Please select a fuel or emission factor", no request.
3. Re-select "Gas Production Facility (Table 7-1)" and set Facility Count = 2 → preview "16,644.000 t CO₂e (CH₄ 591.3 t, CO₂ 87.6 t)".
4. Submit → `POST /api/emissions/` 201.
Script: `node audit/repro/BUG-NNN.mjs`.

## Input
Request body sent by the UI: `calc_inputs.fugitive = {"facility_type":"gas_production","fuel":"Gas Production Facility (Table 7-1)","unit":"facilities","time_unit":"days","facility_count":2,"amount":2,"fugitive_tier":"tier1","fugitive_method":"component",...}` — no `operating_days`.

## Expected
The stored record matches what the form shows for the same inputs (whatever the correct factor math is, UI preview and server must use the same method, facility type and duration), and visible defaults are the values actually submitted.

## Actual
Saved record 763: `ch4 0.052 t, co2 0, totalCo2e 1.456 t, calculation_method server_fugitive_average` vs preview 16,644 t (591.3 t CH4 + 87.6 t CO2). Ratio ≈ 11,400×. The CO2 component shown in the preview is dropped entirely. The user sees the large preview, gets "Scope 1 entry added successfully", and the dashboard/inventory receive 1.456 t.

## Evidence
`audit/repro/BUG-NNN.mjs` output: `preview 16644 tCO2e vs saved 1.456 tCO2e`, `resp emissions {"ch4":0.052,"co2":0,...} server_fugitive_average`; `audit/work/L/w14_fug.mjs` log including the default-submit warning.

## Root Cause
The facility-level Tier 1 method exists only in the client preview. The server's legacy fugitive branch has no facility-level method and silently falls back to "average component = valves × count". The client preview uses placeholder defaults that are not in the submitted state.

## Impact
The figure a user validates on screen is not what is recorded. Upstream fugitive methane — a key OGMP/methane-intensity input — is recorded orders of magnitude off with no warning, and the facility type/duration chosen are lost from the record.

## Affected Components
Scope 1 form, onshore fugitives Tier 1 facility-level; `compute_emissions` legacy fugitive branch; methane intensity / OGMP / Scope 1 totals. Related: BUG-047 (per-hour fugitive factors ignore hours) — different code path.

## Recommended Fix
Implement the facility-level (Table 7-1/7-2) method on the server using `facility_type`, `facility_count` and duration, or post the preview inputs to a server preview endpoint so both use one implementation. Reject fugitive requests whose method/fields the server does not understand instead of defaulting to valves. Initialise `formData` with the displayed defaults.


### Additional confirmation (BUG-110)

Repro path: `audit/repro/BUG-110.mjs` (draft said BUG-NNN.mjs). Agent L.


### Additional confirmation (BUG-029)

Additional impact found by Agent L (Browser), baseline2: a single NULL-name facility also breaks **every Scope 1 bulk import** for every user. Through the UI wizard (Scope 1 → Bulk Import → CSV, columns mapped) `POST /api/emissions/upload/start` returns 200, then the job ends `status:"error"`, `errors:["Fatal error: 'NoneType' object has no attribute 'lower'"]`, 0 rows processed, even for a file with one valid row. Traceback: `background_processor.py:332 fac_name_map = {fac.name.lower(): fac for fac in all_facilities}`. The facility that triggers it is created by the still-open API half of this bug (`POST /api/facilities {"region":"West"}` → 201, name NULL). The UI shows "Upload Failed — A fatal error occurred… 'NoneType' object has no attribute 'lower'" with no hint about the cause. Evidence: `audit/work/L/w15_import.mjs` runs with `imp_ok.csv`, `audit/work/backend_5055.log` ~L2085-2089. Suggest raising severity consideration: core ingestion path is blocked by one bad master-data row.


---

# BUG-111 — Scope 1 bulk import books a row with a blank Unit as m³ and accepts year 1800, both of which the manual form/API reject

**Status:** Confirmed
**Severity:** Medium
**Category:** Emissions
**Discovered by:** Agent L (Browser)

## Location
- `new/server/background_processor.py:1698` — `unit = str(row.get("unit") or "m3").strip()`
- `new/server/background_processor.py` Scope 1 row path — no year range check, while `routes/emissions.py:3005-3006` rejects `yr < 1900 or yr > 2100` with 422 for manual entries.

## Reproduction
1. :5190 as audit_admin → Calculations → Scope 1 → "Bulk Import (Wizard)" → Next → Next → upload `audit/work/L/imp1.csv` (headers Date, Site, Process, Fuel, Qty, UOM, Year, Month).
2. Auto-mapping picks Date/Process/Fuel/Year/Month; map Region/Facility=Site, Quantity=Qty, Unit=UOM → "Start Import".
3. Job completes: 4 imported, 4 skipped.

## Input
Row 5: `2025-12-01,AUDIT-L Plant,combustion,Diesel (No. 2 Fuel Oil),200,,2025,12` (Unit blank).
Row 6: `1800-01-01,AUDIT-L Plant,combustion,Diesel (No. 2 Fuel Oil),10,gal,1800,1`.

## Expected
Both rows are skipped with a reason ("Unit is required", "Year out of range 1900-2100"), as the manual path does for the year (422 "Invalid year") and as the wizard marks Unit as a required field.

## Actual
- Row 5 imported as record 767: `quantity 200, unit 'm3'`, 72.32 tCO2e (Pending) — the file never said m³.
- Row 6 imported as record 768: `year 1800` (Pending). Once approved it appears as a separate year in dashboards/filters (the snapshot already contains a year-1800 record).
Job status: `processed 8, skipped_count 4` — the skip list (unknown region, negative, "abc", duplicate) contains neither row.

## Evidence
`audit/work/L/w15_import.mjs admin imp1.csv` run; `GET /api/emissions/upload/status/191dbc0f-…` skipped_preview; DB `emissions` ids 767, 768.

## Root Cause
The bulk processor substitutes a default for a missing unit instead of rejecting the row, and it does not share the manual route's year validation.

## Impact
Silent unit assumption changes the magnitude of imported emissions (a blank unit on a gal/bbl/tonne row is booked as m³); out-of-range years enter the inventory. Channel inconsistency: the same data is rejected manually but accepted in bulk.

## Affected Components
Scope 1 bulk import (CSV/XLSX), Scope 1 totals after approval, year filters.

## Recommended Fix
Treat a blank unit as a row error (no default). Apply the same year (1900-2100, or reporting-period) and month validation in `background_processor` as in `POST /api/emissions/`.


### Additional confirmation (BUG-081)

Agent L (Browser) — same coarse duplicate key also applies to **Scope 1** bulk import through the UI wizard. In `imp1.csv` two diesel rows for AUDIT-L Plant 2025-12 (200 with blank unit, and "1,000" gal) differ in quantity/unit, but the second was skipped: "Duplicate record: Scope 1 emission for facility 'AUDIT-L Plant' (2025-12, process 'combustion', fuel 'Diesel (No. 2 Fuel Oil)') already exists. Enable 'Overwrite Duplicates' to replace it." The key is facility + year-month + process + fuel only, so two genuine deliveries/meters of the same fuel in a month cannot both be imported, and Overwrite would replace the first. Evidence: job 191dbc0f-… skipped_preview row 7 (`audit/work/L/w15_import.mjs admin imp1.csv`).


---

# BUG-112 — Custom emission factor with every factor field blank is saved (CO2/CH4/N2O = 0) and Tier 2 records that use it are stored with 0 tCO2e and no warning

**Status:** Confirmed
**Severity:** Medium
**Category:** API
**Discovered by:** Agent L (Browser)

## Location
- `POST /api/custom-factors` (route in `new/server/routes/` custom-factor handler): only rejects negative values (`co2_factor must be a non-negative number`); blank strings are coerced to 0.0 and there is no "at least one factor > 0" rule.
- `new/client/src/pages/ManageData.jsx` `handleSaveFactor` (~L944): only checks `factor_name`.
- Scope 1 Tier 2 path (`calc_method server_custom_factor`) applies the zero factor without flagging it.

## Reproduction
1. :5190 as audit_admin → Manage Data → Emission Factors. Name "AUDIT-L EMPTY", Unit gal, leave CO₂/CH₄/N₂O factor fields empty → "Save Factor" → toast "Factor added!".
2. Calculations → Scope 1 → AUDIT-L Plant, 2025-02, Tier 2 → "Saved Custom Factors Library" → "AUDIT-L EMPTY", 100 gal → Save as Draft.

## Input
`POST /api/custom-factors {"factor_name":"AUDIT-L EMPTY","unit":"gal","co2_factor":"","ch4_factor":"","n2o_factor":"",...}`; then `POST /api/emissions/` with `factor_source:"custom", custom_factor_id:102, quantity:100, unit:"gal"`.

## Expected
The factor is rejected ("enter at least one emission factor"), or at minimum records using an all-zero factor are refused/flagged.

## Actual
- 201 `{"id":102}`; stored row `co2_factor 0.0, ch4_factor 0.0, n2o_factor 0.0`. (Saved twice → ids 102 and 104, same name.)
- Scope 1 record: 201, `emissions {"ch4":0,"co2":0,"n2o":0,"totalCo2e":0}`, `calculation_method server_custom_factor`.
- For comparison the negative case is rejected server-side (400 "co2_factor must be a non-negative number") but the UI shows only "Failed to save factor".

## Evidence
`audit/work/L/w16_cf.mjs`, `w17_t2.mjs` outputs; `custom_factors` ids 102-105 in `audit/db/browser.db`.

## Root Cause
Validation treats blank as zero and zero as valid for all gases simultaneously.

## Impact
Activity data entered against such a factor contributes nothing to the inventory while looking complete (201, success toast, Verified for admin). Because factor names are not unique (BUG-065), an empty duplicate can also be picked by name in bulk import.

## Affected Components
Manage Data → Custom Emission Factors, `POST/PUT /api/custom-factors`, Scope 1 Tier 2 manual and bulk paths.

## Recommended Fix
Require at least one factor > 0 (and non-empty numeric input for each provided gas); reject blank-only factors with 400; surface the server's validation message in the toast.


---

# BUG-113 — Reports "PDF Report" prints every unit and gas name with a missing-glyph box: "tCO■e", "CO■", "CH■", "N■O"

**Status:** Confirmed
**Severity:** Low
**Category:** UI
**Discovered by:** Agent L (Browser)

## Location
`new/server/routes/reports.py` (`GET /api/reports/export`, reportlab; e.g. L141-142 `f"{scope1_total:,.2f} tCO₂e"`) — Unicode subscript digits (U+2082 ₂, U+2084 ₄) are drawn with the built-in Helvetica font, which has no glyphs for them.

## Reproduction
1. :5190 as audit_admin → Reports → Filter & Group Data: Year 2025, Region AUDIT-L Plant.
2. Click "PDF Report" → `GET /api/reports/export?scope=all&year=2025&facility_id=173` 200 → `emissions_2025_all.pdf`.
3. Open the PDF.

## Input
Any data.

## Expected
"tCO₂e", "CO₂", "CH₄", "N₂O" (or ASCII "tCO2e") in the summary table and detail headers.

## Actual
Rendered page shows "58.54 tCO■e", "Total CO■ Gas Mass", "tonnes CH■", "N■O" (screenshot `audit/work/L/rep_pdf.png`; text extraction gives "tCOne", "CHn", "NnO"). The numbers themselves match the DB/dashboard (S1 58.54, S2 11,845.52, S3 1.85 for facility 173 / 2025, Verified only).

## Evidence
`audit/work/L/rep.pdf`, `rep_pdf.png`; `audit/work/L/w22_export.mjs`.

## Root Cause
reportlab standard Type 1 fonts only cover Latin-1; subscript characters need an embedded TTF (e.g. DejaVuSans) or `<sub>` markup in Paragraphs.

## Impact
The regulatory-facing PDF export looks broken on every unit label; recipients cannot tell CO₂ from CH₄ columns reliably in the detail table.

## Affected Components
`/api/reports/export` PDF; possibly other reportlab outputs using the same strings (not checked individually).

## Recommended Fix
Register and use a Unicode TTF font in the PDF styles, or render subscripts with `<sub>2</sub>` / ASCII "CO2e".


---

# BUG-114 — Logout does not invalidate the session: a session cookie captured before logout keeps full API access (client-side signed cookie, no server-side revocation)

**Status:** Confirmed
**Severity:** Medium
**Category:** Security
**Discovered by:** Agent L (Browser)

## Location
- `new/server/routes/auth.py` login (L355 `session["user_id"] = user.id`) and logout (~L485-512: `session.clear()` + expire cookie). Flask's default session is a signed client-side cookie; there is no server-side session store, session id, or per-user token/version that logout could revoke.
- `new/server/config.py:97` `PERMANENT_SESSION_LIFETIME = timedelta(hours=8)`.

## Reproduction
1. On :5190 log in as audit_superuser (Playwright context A); copy the `session` cookie.
2. Click the UI Logout (`#logout-btn-drop` / top-bar logout) → redirected to /login; in context A `GET /api/auth/me` → 401.
3. In a new context B, add the copied pre-logout cookies and call `GET /api/auth/me` and `GET /api/emissions?scope=1&limit=1&offset=0`.
Script: `node audit/repro/BUG-NNN.mjs`.

## Input
Pre-logout `session` + `csrf_token` cookies.

## Expected
After logout the old session is dead everywhere: 401 for any reuse of the cookie.

## Actual
Context B: `/api/auth/me` → **200** `{"authenticated":true,...}` for audit_superuser; `/api/emissions…` → **200**. Logout only removes the cookie from the browser that clicked it.

## Evidence
`audit/work/L/w23_logout.mjs` output:
```
after logout url: http://127.0.0.1:5190/login clicked UI: true
same ctx /me: 401
replayed pre-logout cookie /me: 200 {"authenticated":true,...
replayed cookie data access: 200
```

## Root Cause
Stateless signed-cookie sessions without a revocation list or server-side session id; logout cannot invalidate copies of the cookie.

## Impact
A stolen or shared cookie (shared workstation, proxy logs, XSS, browser sync) stays usable after the user logs out, for the session lifetime; the same applies after an admin deactivates/changes the role only if the per-request user reload does not catch it (not tested here). For an emissions-reporting system with maker-checker roles this undermines the "log out ends access" control expected by ISO 27001-style reviews.

## Affected Components
All authenticated API routes; `POST /api/auth/logout`.

## Recommended Fix
Use a server-side session store (Flask-Session with Redis/DB) or add a per-user `session_version`/random session id stored server-side that is checked on every request and rotated on logout, password change and deactivation.


### Additional confirmation (BUG-114)

Repro path: `audit/repro/BUG-114.mjs` (draft said BUG-NNN.mjs). Agent L.


---

# BUG-115 — Manage Data forms discard the server's validation message and show a generic "Failed to …" toast (negative production, negative factor, facility 500, etc.)

**Status:** Confirmed
**Severity:** Low
**Category:** UI
**Discovered by:** Agent L (Browser)

## Location
`new/client/src/pages/ManageData.jsx` catch blocks that ignore `err.response.data.error`: L941 `Failed to add region`, L957 `Failed to save factor`, L971 `Failed to delete factor`, L1021 `Failed to save production`, L1031 `Failed to add source`, L1041 `Failed to save mitigation`, L1089 `Failed to delete CBAM record`, L1137 `Failed to delete OGMP survey`, L175 `Failed to save SBTi Target` (9 sites).

## Reproduction
Through the UI on :5190 as audit_admin:
1. Manage Data → Production Data, AUDIT-L Plant 2025-08, Oil −5000 bbl → Save Record → server `400 {"error":"Production amounts cannot be negative"}`; toast "Failed to save production".
2. Manage Data → Emission Factors, CO₂ factor −5 → Save Factor → server `400 {"error":"co2_factor must be a non-negative number"}`; toast "Failed to save factor".
3. Manage Data → Regions → Add Region without coordinates → server 500 (BUG-045); toast "Failed to add region".

## Input
As above.

## Expected
The toast shows the server's reason (as the Scope 1 form does: "Invalid year: must be between 1900 and 2100").

## Actual
Generic "Failed to …" with no reason; the user cannot tell whether the value, a permission, a duplicate or a server fault caused it.

## Evidence
`audit/work/L/w11_prod.mjs` (negative case), `w16_cf.mjs` (negative factor), `w2_facility.mjs` — network responses captured next to the toast text.

## Root Cause
`catch (err) { toast.error('Failed to …') }` without reading `err.response?.data?.error`.

## Impact
Validation errors look like system failures; users retry or give up instead of correcting data; support cannot distinguish causes.

## Affected Components
Manage Data: regions, custom factors, production, sources, mitigation, CBAM, OGMP surveys, SBTi target save.

## Recommended Fix
Use `err.response?.data?.error || 'Failed to …'` in every catch (a shared helper), as `Scope1Form.jsx` already does.
