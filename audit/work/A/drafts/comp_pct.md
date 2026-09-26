# BUG-XXX — Tier 3 combustion/flaring gas composition: each component is converted percent→fraction on its own, so mol% values ≤ 1 (e.g. C4 = 1.0 %, C5 = 0.5 %) become 100 % / 50 %; CO2 inflated 2.7× on the app's own template sample

**Status:** Confirmed
**Severity:** High
**Category:** Calculation
**Discovered by:** Agent A (Calculation Engine Auditor)

## Location
- `new/server/calculations/dispatcher.py` `dispatch()`, Tier 3 combustion and flaring branches. The nested `safe_frac(key)` returns `num / 100.0 if num > 1.0 else num` **per component**.
- `new/server/calculations/combustion.py` `CombustionCalculator.calculate` / `FlaringCalculator.calculate`. The `total_raw > 1.5` check then divides everything by 100 again when the (already mixed) sum exceeds 1.5.

## Reproduction
1. `POST /api/emissions/` with `process_type=combustion, factor_source=specific, fuel="Natural Gas", amount=50000, unit=scf, hhv=1010, combustion_efficiency=0.993, c1=87.5, c2=5.2, c3=2.1, c4=1.0, c5=0.5, co2_mol=1.8, n2_mol=1.9`. This is the exact composition in the "Tier 3 – Natural Gas Combustion" sample row of the app's own CSV template (`routes/emissions.py` `_row(... c1="87.5" ... c5="0.5" ...)`). The template documents c1..c10 as "0–100 mol%".
2. Read back `co2_emissions`.
3. Repro: `audit/repro/BUG-XXX.py`

## Input
50,000 scf (1,415.84 m³ at 60 °F / 14.696 psia), η_c = 0.993. Composition in mol%: C1 87.5, C2 5.2, C3 2.1, C4 1.0, C5 0.5, CO2 1.8, N2 1.9 (sum 100).

## Expected
Carbon number Σ(xᵢ·nᵢ) = 0.875 + 2(0.052) + 3(0.021) + 4(0.010) + 5(0.005) = 1.107 mol C / mol gas.
CO2 = 1415.84 × (1.107 × 0.993 + 0.018) × 1.861 kg/m³ = **2.944 t CO2**. CH4 slip = 1415.84 × 0.875 × 0.007 × 0.6785 = **0.00588 t**. CO2e (AR5) ≈ **3.11 t**.

## Actual
`co2_emissions = 8.021 t`, `ch4_emissions = 0.002386 t`, `co2e_total = 8.089 t` (**2.6× too high**; CH4 2.5× too low).
With the same composition entered as fractions (0.875, 0.052, …) the result is 3.001 t CO2. The remaining +1.9 % error is a separate issue: N2 is left out of the normalisation sum.

## Evidence
`agentA.db` rows: mol% → `co2 8.021332635535375, ch4 0.00238604024792409, co2e 8.08948001247725`; fractions → `co2 3.0008411745485595`.
Trace: safe_frac gives c1 .875, c2 .052, c3 .021, **c4 1.0**, **c5 0.5**, co2 .018 → total_raw 2.471 > 1.5 → everything /100 and renormalised by 0.02471. That leaves C4 = 40 % and C5 = 20 % of the gas.

## Root Cause
Percent-vs-fraction detection is done per value (`> 1.0`) and not per composition. Any component whose mol% is ≤ 1 is misread as a fraction. The calculator then applies a second heuristic on the mixed sum.

## Impact
Every Tier 3 combustion or flaring entry, whether through the API or bulk import, with any minor component between 0 and 1 mol% gets a wrong carbon balance. That describes most real gas analyses (C4–C10, CO2 often < 1 %). CO2 is overstated by up to several times and CH4 slip is wrong. The app's own sample row is affected.

## Affected Components
dispatcher Tier 3 combustion and flaring branches; `CombustionCalculator`, `FlaringCalculator`; CSV/Excel bulk import of `c1..c10, co2_mol, n2_mol`.

## Recommended Fix
Decide the basis once for the whole composition (e.g. the documented mol% basis, or sum > 1.5 ⇒ percent) and apply it to every component, including CO2 and N2. Do not scale components individually.
