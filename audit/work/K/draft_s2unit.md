# BUG-XXX — Scope 2 form: switching Source Type to Steam/Heat or CHP leaves the hidden unit at "kWh" — dropdown shows "Select..." but the request sends unit "kWh" (1000 "MMBtu" of steam booked as 3.41 MMBtu)

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
