# BUG-XXX — Negative activity amounts are accepted for process types that are not in the dispatcher (e.g. "loading") and saved as negative emissions

**Status:** Confirmed
**Severity:** Medium
**Category:** Calculation
**Discovered by:** Agent A (Calculation Engine Auditor)

## Location
- `new/server/calculations/dispatcher.py` `dispatch()`: `if not calculator: return self._generic_calculation(...)` runs **before** the NaN/Inf/negative quantity checks. `_generic_calculation` has no validation.
- `new/server/routes/emissions.py` `add_emission()` validates only `data["quantity"]`. The calculation reads `amount` first.

## Reproduction
1. `POST /api/emissions/` with `process_type=loading, factor_source=default, fuel="Loading - Crude Oil (Tank Truck)", amount=-1000000, unit=bbl` (no `quantity`).
2. Repro: `audit/repro/BUG-XXX.py`

## Expected
HTTP 422 (negative activity), as returned for dispatcher processes (e.g. `separation` → "Quantity/Amount cannot be negative").

## Actual
HTTP 201. Stored `ch4_emissions = -0.16`, `co2e_total = -4.48`, `quantity = -1000000`, status Verified (admin).

## Evidence
`agentA.db` row: `{'ch4_emissions': -0.16, 'co2e_total': -4.48, 'calc_method': 'api2021_generic', 'quantity': -1000000.0}`.

## Root Cause
Input validation is applied only on the calculator path and only to the `quantity` key.

## Impact
Negative records silently offset real emissions in totals (API and bulk callers). The same path does no NaN/Inf check for unknown process types.

## Affected Components
`dispatch` → `_generic_calculation`; POST `/api/emissions/`; any process_type not in `CalculationDispatcher.calculators` (loading, fccu, custom names).

## Recommended Fix
Validate `amount` and `quantity` (finite, ≥ 0) in the route. Move the dispatcher's quantity validation above the `if not calculator` early return.
