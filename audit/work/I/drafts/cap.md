# BUG-XXX — CAP (air-pollutant) emissions bypass maker-checker: POST /api/cap/emissions stores records as "Verified" by default (client-controlled status) for role user; negative mass/concentration accepted

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
