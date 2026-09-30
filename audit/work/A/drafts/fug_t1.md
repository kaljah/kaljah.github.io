# BUG-XXX — Tier 1 fugitive and equipment factors in "per hour" units are multiplied only by the source count (no operating hours): annual CH4 understated 8,760×, and Tier 1 disagrees with Tier 3 for the same factor

**Status:** Confirmed
**Severity:** High
**Category:** Calculation
**Discovered by:** Agent A (Calculation Engine Auditor)

## Location
- `new/server/calculations/dispatcher.py` `_generic_calculation()`. It computes `quantity × factor`, with a denominator conversion only for volume/mass units. Time denominators ("/hr") are ignored and no hours are applied.
- It is reached for `factor_source` default/custom for every fugitive alias (`fugitive`, `wellhead_fugitive`, `separator_fugitive`, `gathering_boosting`, `gas_processing`, `compressor_fugitive`, `fugitive_component`, …).
- Catalog units (`emission_factors*.py`): `tonne CH₄/hr/source`, `tonne CH₄/well/hr`, `tonne CH₄/separator/hr`, `tonne CH₄/compressor/hr`, `tonne CH₄/unit/hr`.
- The UI (`FugitivesForm.jsx`) asks only for "Count (Number of Sources)" and sends it as `amount`. There is no hours field.

## Reproduction
1. `POST /api/emissions/` with `process_type=fugitive, factor_source=default, fuel="Component - Block Valve", amount=10`.
2. `POST /api/emissions/` with `process_type=wellhead_fugitive, factor_source=default, fuel="Wellhead - Gas", amount=10`.
3. Repro: `audit/repro/BUG-XXX.py`

## Input
10 block valves (4.36e-6 t CH4/hr/source); 10 gas wellheads (1.8e-5 t CH4/well/hr).

## Expected
Annual (8,760 h): valves 10 × 4.36e-6 × 8760 = **0.3819 t CH4**; wellheads 10 × 1.8e-5 × 8760 = **1.577 t CH4**. Even for a one-month record (744 h) the values are 0.0324 t and 0.134 t.

## Actual
Valves `ch4_emissions = 4.36e-5 t`; wellheads `1.8e-4 t`. That is the emission for **one hour**, 8,760× below annual.
For comparison, Tier 3 (`factor_source=specific`) with the same factor gives 1.340 t for the wellheads, because `EquipmentFugitiveCalculator` multiplies by 8760. It also applies a separate 0.85 error.

## Evidence
`agentA.db` rows (`calc_method = api2021_generic`): `ch4 4.3599999999999996e-05, co2e 0.0012208` and `ch4 0.00018, co2e 0.00504`.

## Root Cause
The generic calculator treats every factor as "per activity unit". Per-hour factors need count × hours, but no hours input is collected or applied.

## Impact
All Tier 1 equipment/component fugitive CH4 (usually the largest methane source in upstream inventories) is understated by about 4 orders of magnitude. This affects methane intensity, OGMP and Scope 1 totals.

## Affected Components
`_generic_calculation`; Tier 1 fugitive UI; bulk import of fugitive rows.

## Recommended Fix
Parse the time denominator. Require operating hours (default to hours in the reporting period) for "/hr" factors and multiply. Share one implementation between Tier 1 and Tier 3.
