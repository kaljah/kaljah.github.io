# BUG-XXX — Purchased steam/heat (`indirect_steam`) and CHP allocation (`cogen_allocation`) are accepted as Scope 1 process types and added to Scope 1 totals (Scope 2 counted as Scope 1; CHP double counting)

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
