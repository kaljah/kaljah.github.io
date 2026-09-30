# BUG-XXX — Well-completion "Rate × Duration" method divides the Mcf/hr rate by 24 (treats it as Mcf/day): CH4 understated 24×

**Status:** Confirmed
**Severity:** High
**Category:** Calculation
**Discovered by:** Agent A (Calculation Engine Auditor)

## Location
- `new/server/calculations/vented.py` `CompletionFlowbackCalculator.calculate` — `rate_unit="mscf/day"` default and branch `rate_scf_hr = (float(flowback_rate) * multiplier) / 24.0`
- `new/server/calculations/dispatcher.py` `dispatch()` `elif process_type == "completions"` — calls the calculator without `rate_unit`
- `new/client/src/components/scope1/CompletionsForm.jsx` — the field is labelled **"Avg Gas Rate (Mcf/hr)"**, and `Scope1Form.jsx` also treats it as Mcf/hr (`finalAmount = rateMcfHr * durationHr * 28.3168`)

## Reproduction
1. As admin, send `POST /api/emissions/` with the payload the Scope 1 form builds for Completions (Tier 3, method "Rate × Duration"):
   `process_type=completions, factor_source=specific, amount=339.8016, unit=m3, calc_inputs.completions={calc_method:"rate_duration", comp_rate:0.5, comp_duration:24, ch4_content:80, amount:2}`
2. Read `emissions.ch4_emissions` / `co2e_total` for the new id.
3. Repro: `audit/repro/BUG-XXX.py`

## Input
Rate 0.5 Mcf/hr, duration 24 h, 2 events, 80 mol% CH4, vented (no flare). AR5.

## Expected
Gas = 0.5 Mcf/hr × 1000 scf/Mcf × 24 h × 2 events = 24,000 scf = 679.60 m³ (60 °F, 14.696 psia).
CH4 = 679.60 × 0.80 × 0.6785 kg/m³ = 368.9 kg = **0.3689 t CH4** → 10.33 tCO2e (GWP 28).

## Actual
`ch4_emissions = 0.015370 t`, `co2e_total = 0.4304 t`. That is exactly 1/24 of the expected value.

## Evidence
The DB row from the audit copy (`agentA.db`): `{'ch4_emissions': 0.015370384330137602, 'co2e_total': 0.4303707612438529, 'calc_method': 'Well Completion Flowback'}`. Ratio 0.3689/0.01537 = 24.0.

## Root Cause
The calculator assumes the rate is in Mcf/**day** unless `rate_unit` contains "hr". The dispatcher never passes a rate unit, but the UI collects Mcf/**hr**. The multiplier logic is also order-dependent: `"mscf" in "mmscf/day"` is true, so an MMscf rate would get ×1000 instead of ×1e6.

## Impact
Every Tier 3 completion or flowback record entered with the Rate × Duration method (the form's default) under-reports CH4 and CO2e by 24×. This feeds Scope 1, methane intensity and OGMP totals.

## Affected Components
dispatcher `completions` branch; `CompletionFlowbackCalculator`; Scope 1 form (Completions); bulk import rows that use `comp_rate`.

## Recommended Fix
Pass an explicit `rate_unit` (UI: "mcf/hr") from the dispatcher, and make the calculator's default match the UI label. Test "mmscf" before "mscf" in the multiplier. Add a regression test against the hand value above.
