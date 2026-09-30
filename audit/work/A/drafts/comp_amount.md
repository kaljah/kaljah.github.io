# BUG-XXX — Well-completion Tier 3 uses `amount` as both the flowback volume and the event count (volume squared), and ignores rate × duration when the method dropdown is left at its default

**Status:** Confirmed
**Severity:** High
**Category:** Calculation
**Discovered by:** Agent A (Calculation Engine Auditor)

## Location
`new/server/calculations/dispatcher.py`, `dispatch()`, `elif process_type == "completions"`:
- `events_val = float(flat_inputs.get("amount") or flat_inputs.get("events") or 1.0)`
- `comp_method = flat_inputs.get("comp_method") or flat_inputs.get("calc_method") or flat_inputs.get("calculation_method", "metered_volume")`
- `vol_raw = self._require_float(flat_inputs, ["amount", "quantity", "flowback_volume", "comp_volume"], ...)`

`CompletionFlowbackCalculator` (metered branch) then computes `total_gas_m3 = flowback_volume * num_events`.

`new/client/src/components/scope1/CompletionsForm.jsx` shows "Rate × Duration" as the selected method (`value={data.calc_method || "rate_duration"}`) but does not put `calc_method` into formData until the user changes the dropdown. It also sends the **event count** as `amount`.

## Reproduction
1. `POST /api/emissions/` with `process_type=completions, factor_source=specific, amount=1000, unit=m3, ch4_content=80, comp_method=metered_volume` (1,000 m³ metered flowback).
2. `POST /api/emissions/` with the UI payload when the method dropdown was not touched: `calc_inputs.completions={comp_duration:24, comp_rate:0.5, ch4_content:80, amount:2}` (no `calc_method`).
3. Repro: `audit/repro/BUG-XXX.py`

## Input
(1) 1,000 m³ metered, 80 % CH4. (2) 0.5 Mcf/hr × 24 h × 2 events, 80 % CH4.

## Expected
(1) 1000 × 0.80 × 0.6785 / 1000 = **0.5428 t CH4** (15.20 tCO2e AR5).
(2) 24,000 scf = 679.6 m³ → **0.3689 t CH4**.

## Actual
(1) `ch4_emissions = 542.8 t` (**1000× too high**: volume 1000 × "events" 1000).
(2) `ch4_emissions = 0.002171 t` (**170× too low**). The server fell back to `metered_volume`, took `amount`=2 (the event count) as 2 m³ of gas, and multiplied by 2 events. Rate and duration were ignored.

## Evidence
DB rows in `agentA.db`: (1) `ch4_emissions 542.8, co2e_total 15198.4`; (2) `ch4_emissions 0.0021712, co2e_total 0.0608`.

## Root Cause
The single field `amount` is read both as the event multiplier and as the metered volume. The server defaults the method to `metered_volume`, while the UI displays `rate_duration` as its default and never sends it.

## Impact
Metered completions submitted through the API or bulk import are inflated by a factor equal to the volume (quadratic). UI entries where the method dropdown was left at its default are understated by orders of magnitude. Both errors flow into Scope 1 CH4, methane intensity and OGMP.

## Affected Components
dispatcher completions branch; `CompletionFlowbackCalculator`; `CompletionsForm.jsx` / `Scope1Form.jsx`; bulk import (`background_processor`) rows for completions.

## Recommended Fix
Use a dedicated `events` field (never `amount`) for the event count, and a dedicated volume field for metered flowback. Default the server method to the one the UI shows, or have the UI always send `calc_method`. Reject ambiguous payloads.
