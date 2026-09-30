# BUG-XXX — Editing a Scope 1 record's quantity via PUT /api/emissions/<id> does not recalculate emissions (stale `amount` from source_payload wins)

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
