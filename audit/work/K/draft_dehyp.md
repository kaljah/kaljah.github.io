# BUG-XXX — Dehydrator form sends "Contactor Pressure" as `dehy_pressure`, but the server reads `dehy_press`: user pressure silently ignored, 800 psig default always used (AGR "routed to flare"/"flash gas recycled" checkboxes also unread)

**Status:** Confirmed
**Severity:** High
**Category:** UI
**Discovered by:** Agent K (Frontend/UI)

## Location
- `new/client/src/components/scope1/DehydratorForm.jsx` — `onChange("dehy_pressure", …)` (Contactor Pressure (psig) input).
- `new/server/calculations/dispatcher.py` dehydrator branch reads `flat_inputs.get("dehy_press") or flat_inputs.get("contactor_pressure") or 800.0`.
- `new/client/src/components/scope1/AGRForm.jsx` — `flash_gas_recycled`, `offgas_to_flare`, `solvent_type` are sent but no server code reads these keys (grep over `new/server/calculations` and `routes/emissions.py`).

## Reproduction
1. UI :5191 as admin → Emissions → Scope 1 → Region = first facility, Process = Dehydrator (Tier 3).
2. Throughput 1000, pump 5, CH4 85 %, hours 8760, temperature 100 °F, **Contactor Pressure = 200**; submit. Repeat with pressure 1000.
3. API check with the server's own key `dehy_press` (`audit/work/K/fields.py`).

## Input
Contactor pressure 200 psig vs 1000 psig, all else equal.

## Expected
Different CH4 (the server calculator is pressure-sensitive: with `dehy_press` it returns 0.363 t CH4 at 200 psig and 1.613 t at 1000 psig).

## Actual
POST body `calc_inputs.dehydrator = {..., "dehy_pressure": 200, ...}` → response CH4 1.30610 t, CO2e 36.571 t; with 1000 psig → identical 1.30610 t / 36.571 t (records 756/757). That is the 800 psig default. At 200 psig the stored CO2e is 3.6× the value the server would compute for the entered pressure.

AGR: toggling "Acid Gas / Offgas Routed to Flare" and "Flash Gas Recycled" gives byte-identical results (2371.39 t CO2 / 16.331 t CH4).

## Evidence
`audit/work/K/t_dehy.mjs` (browser, captured payloads/responses), `audit/work/K/fields.py` (API). Repro: `audit/repro/BUG-<id>.py`.

## Root Cause
Field-name mismatch between the form (`dehy_pressure`) and the dispatcher (`dehy_press`/`contactor_pressure`); AGR checkbox keys have no server counterpart. No warning is shown for an ignored required input.

## Impact
Every UI-entered dehydrator record ignores the contactor pressure the user typed (marked required); AGR control options displayed to the user have no effect.

## Affected Components
Scope 1 Dehydrator and AGR Tier 3 forms; resulting records and totals.

## Recommended Fix
Rename the form key to `dehy_press` (or accept `dehy_pressure` server-side); map the AGR checkboxes to `agr_control_type` / flash handling or remove them; reject/flag unknown calc_inputs keys.
