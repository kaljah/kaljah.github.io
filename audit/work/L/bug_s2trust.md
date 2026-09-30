# BUG-XXX — Scope 2 electricity create trusts client-supplied `co2e` / `emission_factor`: 0 kWh can be booked as 12,345 tCO2e, negative Scope 2 (-500 t) is accepted, and any unknown grid region takes the client's factor

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
