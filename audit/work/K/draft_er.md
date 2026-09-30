# BUG-XXX — Emission Calculation Result panel rounds gas masses to 3 decimals of a tonne: non-zero CH4/N2O shown as "0.00 tonnes"

**Status:** Confirmed
**Severity:** Low
**Category:** UI
**Discovered by:** Agent K (Frontend/UI)

## Location
`new/client/src/components/EmissionResult.jsx` local `formatNumber` (min 2 / max 3 fraction digits) used for CO2, CH4, N2O, CO and the confidence-interval tooltips.

## Reproduction
1. UI :5191 admin → Scope 1 → Tier 3 Stationary Combustion, 1000 m³, factors CO2 53.06 / CH4 0.001 / N2O 0.0001 kg/MMBtu, HHV 38 MJ/m³, efficiency 99.5 %; submit.
2. Read the result panel that opens.

## Input
Server response `emissions.ch4 = 3.6017e-05`, `n2o = 3.6017e-06` (t).

## Expected
A non-zero, readable value (e.g. "0.000036 t" / "36.0 kg"), consistent with the Recent Activity table which shows CH4 with 5 decimals ("0.00004").

## Actual
"CH₄ METHANE 0.00 tonnes", "N₂O NITROUS OXIDE 0.00 tonnes"; uncertainty tooltip margins are likewise rounded to 0.00.

## Evidence
`audit/work/K/t_hhv.mjs` output: `RESULT PANEL: … CO₂ 1.911 tonnes CH₄ METHANE 0.00 tonnes N₂O NITROUS OXIDE 0.00 tonnes …` (record 759).

## Root Cause
Fixed tonne scale with 3-decimal maximum for all gases.

## Impact
Methane/N2O from small sources appear to be zero on the confirmation screen (misleading, especially for methane reporting); same record shows different values elsewhere.

## Affected Components
EmissionResult modal (Scope 1 and Scope 2 submissions).

## Recommended Fix
Use significant-figure formatting or switch to kg below 1 t.
