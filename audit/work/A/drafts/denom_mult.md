# BUG-XXX — Generic factor math ignores the 10³ / 10⁶ multiplier in factor denominators: offshore gas fugitives 1,000,000× and refinery fuel-gas fugitives 1,000× overstated

**Status:** Confirmed
**Severity:** High
**Category:** Calculation
**Discovered by:** Agent A (Calculation Engine Auditor)

## Location
`new/server/calculations/dispatcher.py` `_generic_calculation()`. `matched_v_denom` is picked by substring (`k in f_denom`), so `"10⁶ scf produced"` matches `scf` and `"10³ bbl feedstock"` matches `bbl`. The 10ⁿ scale is discarded.
Catalog: `Offshore - Gas Production (Facility)` = 0.0104 `tonne CH₄/10⁶ scf produced`; `Refinery - Fuel Gas System (50-99k bbl/day)` = 0.000375 `tonnes CH₄/10³ bbl feedstock` (and the 100-199k variant).

## Reproduction
1. `POST /api/emissions/` with `process_type=wellhead_fugitive, factor_source=default, fuel="Offshore - Gas Production (Facility)", amount=5, unit=mmscf`.
2. `POST /api/emissions/` with `process_type=refinery_fugitive, factor_source=default, fuel="Refinery - Fuel Gas System (50-99k bbl/day)", amount=50000, unit=bbl`.
3. Repro: `audit/repro/BUG-XXX.py`

## Expected
Offshore: 5 MMscf × 0.0104 t/MMscf = **0.052 t CH4**. Refinery: 50 kbbl × 0.000375 = **0.01875 t CH4**.

## Actual
Offshore `ch4_emissions = 52,000 t` (co2e 1,456,000 t). Refinery `18.75 t`. No unit choice gives the right answer: entering scf also multiplies by 1e6.

## Evidence
`agentA.db` rows, `calc_method = api2021_generic`: `ch4 52000.0, co2e 1456000.0`; `ch4 18.75, co2e 525.0`.

## Root Cause
Denominator parsing takes the first unit-name substring and ignores numeric scale prefixes (10³, 10⁶, "per thousand").

## Impact
A single offshore gas facility-month can inject 10⁶ t CO2e into Scope 1. Refinery fuel-gas fugitives are 1000× high.

## Affected Components
`_generic_calculation` (Tier 1/custom for any process); catalog entries with scaled denominators; the Tier 3 `EquipmentFugitiveCalculator` for the same entries, which applies ×8760 to these non-hourly factors.

## Recommended Fix
Parse scale prefixes (10³/10⁶/k/M/MM) in denominators and divide accordingly. Better still, store factors in canonical units with an explicit denominator unit field.
