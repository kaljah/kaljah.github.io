# BUG-XXX — Tier 3 flaring/combustion renormalises the gas composition without N2 (and without unspecified components), inflating CH4 and CO2 by 1/(1 − x_inert)

**Status:** Confirmed
**Severity:** Medium
**Category:** Calculation
**Discovered by:** Agent A (Calculation Engine Auditor)

## Location
`new/server/calculations/combustion.py`:
- `FlaringCalculator.calculate`: `total_raw = sum(raw_c.values()) + raw_co2`, then `c_fractions[k] /= total_sum`
- `CombustionCalculator.calculate`: the same block

The dispatcher passes `n2_comp`, but neither calculator reads it.

## Reproduction
1. `POST /api/emissions/` with `process_type=flaring, factor_source=specific, fuel="Natural Gas (Flaring)", amount=1000, unit=m3, c1=90, n2_mol=10` (default elevated flare: η_d 0.98, η_c 0.984).
2. Repro: `audit/repro/BUG-XXX.py`

## Input
1000 m³ flare gas at standard conditions, 90 mol% CH4 and 10 mol% N2.

## Expected
CH4 = 1000 × 0.90 × (1 − 0.98) × 0.6785 kg/m³ = **0.012213 t**.
CO2 = 1000 × 0.90 × 1 × 0.984 × 1.861 kg/m³ = **1.6481 t**.

## Actual
`ch4_emissions = 0.013570 t`, `co2_emissions = 1.831224 t`. Both are **+11.1 %**: the gas was renormalised to 100 % CH4.

## Evidence
`agentA.db` row: `{'co2_emissions': 1.831224, 'ch4_emissions': 0.013570000000000013, 'calc_method': 'Flaring Dual-Efficiency'}`.
The same effect makes Tier 3 combustion with the template composition (N2 1.9 %) 1.9 % high. The UI sends only `c1` and `co2_content`, so any user-entered CH4 % below 100 is scaled up to fill the missing share (e.g. 85 % CH4 + 2 % CO2 → treated as 97.7 % CH4).

## Root Cause
Normalisation to 1.0 uses only C1–C10 and CO2. N2, H2S and any unspecified components are dropped, and the composition is forced to sum to 1.

## Impact
Flared and combusted CH4 and CO2 are overstated in proportion to the inert/unspecified fraction. The typical range is 2–15 %, and more for high-N2 associated gas.

## Affected Components
`FlaringCalculator`, `CombustionCalculator` (Tier 3); UI Tier 3 flaring (sends only CH4 % and CO2 %); bulk import.

## Recommended Fix
Include N2 (and other inerts) in the sum. Renormalise only when the analysis is complete (sum close to 100 %, within a tolerance). Otherwise use the stated mole fractions as given, and warn.
