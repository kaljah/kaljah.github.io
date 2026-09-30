# BUG-XXX — Activity-data write endpoints accept "NaN" / "1e999" (±Infinity): a Scope 3 record with activity_data=Infinity makes /dashboard/batch-all, /scope3/summary and /api/scope3 emit invalid JSON ("Infinity")

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
