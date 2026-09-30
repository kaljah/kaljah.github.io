# BUG-XXX — Recalculating a Tier 2 (custom-factor) Scope 1 record drops the custom factor: emissions become 0 or silently switch to the catalog factor, while factor_source stays "custom"

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
