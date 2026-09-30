# BUG-XXX — Energy activity units kWh / MJ / Btu with a kg/MMBtu factor are treated as scf of gas (× 1020 Btu/scf): 1000 kWh of natural gas is 3.3× too low, MJ 7.6 % too high

**Status:** Confirmed
**Severity:** Medium
**Category:** Calculation
**Discovered by:** Agent A (Calculation Engine Auditor)

## Location
- `new/server/calculations/combustion.py` `convert_factor_to_kg_per_unit()`, `kg/MMBtu` branch. Only `mmbtu`, `gj` and `therm` are handled as energy. Any other unit falls through to `return val * ((hhv or ...) / 1_000_000.0)`, i.e. per-scf.
- `dispatcher._generic_calculation()` has the same gap: an unknown unit goes to the gas branch with `scf = quantity`.
- `units.ENERGY_UNITS_TO_MJ` already defines kwh, mwh, mj, kj, btu, but it is not used here.

## Reproduction
1. `POST /api/emissions/` with `process_type=combustion, factor_source=default, fuel="Natural Gas", amount=1000, unit=kwh`, and again with `amount=1000000, unit=mj`.
2. Repro: `audit/repro/BUG-XXX.py`

## Expected
1000 kWh = 3.412142 MMBtu × 53.06 = **0.18105 t CO2**. 1,000,000 MJ = 947.817 MMBtu × 53.06 = **50.29 t CO2** (as the app correctly returns for 1000 GJ).

## Actual
kWh → `0.054121 t` (0.30×). MJ → `54.121 t` (1.076×). Both are computed as if the number were scf × 1020 Btu/scf.

## Evidence
`agentA.db` rows: kwh `co2 0.05412120000000001`; mj `co2 54.12120000000001`; gj `co2 50.29117002` (correct).

## Root Cause
Energy units are hard-coded to a short list, and the fallback silently assumes a gas volume.

## Impact
Fuel reported by energy in kWh, MWh, MJ or Btu (common for metered gas and for purchased-fuel invoices) gives wrong CO2/CH4/N2O.

## Affected Components
`convert_factor_to_kg_per_unit`, `_generic_calculation`, legacy `GHGCalculator.calculate_energy`.

## Recommended Fix
Convert all energy units through `ENERGY_UNITS_TO_MJ`. Raise an error for unrecognised units instead of assuming scf.
