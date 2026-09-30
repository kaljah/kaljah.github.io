# BUG-XXX — Scope 1 form saves an entry with no Unit selected: the client silently assumes m³ (10 → 2,641.72 gal stored) while the server calculates from the raw 10 in calc_inputs, so the stored activity and its emissions disagree 264×

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
