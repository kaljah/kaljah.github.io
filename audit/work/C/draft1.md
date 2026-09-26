# BUG-XXX — 43 Tier 1 factors offered in the Scope 1 UI do not exist in the server catalog; records save with HTTP 201 and 0 emissions

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
