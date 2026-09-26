# BUG-XXX — Tier 3 fugitive calculators misread catalog factor units: "CH₄" (Unicode subscript) is not recognised as methane (×0.85 applied), and ComponentFugitiveCalculator treats tonne/hr factors as kg/hr (1000× too low)

**Status:** Confirmed
**Severity:** High
**Category:** Calculation
**Discovered by:** Agent A (Calculation Engine Auditor)

## Location
- `new/server/calculations/fugitive.py` `EquipmentFugitiveCalculator.calculate`: `is_methane = any(x in u_low for x in ["ch4", "methane", "ch_4"])`
- `new/server/calculations/fugitive.py` `ComponentFugitiveCalculator.calculate`: the same check, plus `total_ch4_tonnes_year = (total_ch4_kg_hr * 8760) / 1000.0`, which always assumes kg/hr
- The catalog units use the subscript character U+2084, e.g. `tonne CH₄/well/hr`, `tonne CH₄/hr/source`

## Reproduction
1. `POST /api/emissions/` with `process_type=wellhead_fugitive, factor_source=specific, fuel="Wellhead - Gas", amount=10`.
2. `POST /api/emissions/` with `process_type=fugitive_component, factor_source=specific, fuel="Component - Block Valve", amount=10`.
3. Repro: `audit/repro/BUG-XXX.py`

## Expected
Wellheads: 10 × 1.8e-5 t/h × 8760 = **1.5768 t CH4** (the factor is already CH4, so no gas fraction applies).
Valves: 10 × 4.36e-6 t/h × 8760 = **0.3819 t CH4**.

## Actual
Wellheads `1.34028 t` (= × 0.85, −15 %). Valves `3.246e-4 t` (= × 0.85 / 1000, **1,176× too low**).

## Evidence
`agentA.db` rows: `Equipment-Level Fugitive ch4 1.3402800000000001`; `Component-Level Fugitive ch4 0.0003246455999999999`.
The lowercased unit `tonne ch₄/well/hr` contains no "ch4" substring, so the 0.85 default CH4 content is applied to a factor already expressed as CH4. The component calculator never reads the numerator unit.

## Root Cause
String matching on units does not normalise the Unicode subscript. The component calculator hard-codes kg.

## Impact
Every Tier 3 equipment-level fugitive is 15 % low. Every Tier 3 component-level fugitive using catalog factors is about 1000× low.

## Affected Components
`EquipmentFugitiveCalculator`, `ComponentFugitiveCalculator`, dispatcher branches for `equipment_fugitive` / `wellhead_fugitive` / … / `fugitive_component`.

## Recommended Fix
Normalise units before matching (map subscript digits to ASCII, strip spaces). Parse the numerator mass unit explicitly (t/kg/g/lb) in both calculators. Add regression tests with the real catalog strings.
