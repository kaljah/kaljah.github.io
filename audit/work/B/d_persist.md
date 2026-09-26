# BUG-XXX — POST /api/emissions/ calculates from `quantity`/`fuel_type` but stores only `amount`/`fuel`: records keep emissions with NULL activity quantity and fuel

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
