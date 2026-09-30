# BUG-XXX — CHP allocation form labels Power Output "MWh" but the server uses the number as MMBtu: heat share (and Scope 2 tCO2e) overstated ~2.7× with WRI efficiency method

**Status:** Confirmed
**Severity:** Medium
**Category:** UI
**Discovered by:** Agent K (Frontend/UI)

## Location
- `new/client/src/components/Scope2Form.jsx` — "Power Output (MWh)" input → `calc_inputs.cogen_allocation.power_output`.
- `new/server/routes/scope2.py` `_calc_cogen_allocation`: `power_output = float(data.get("power_output_mwh") or ci.get("power_output", 0)); power_mmbtu = power_output` (no ×3.412142).

## Reproduction
1. UI :5191 admin → Scope 2 → Source Type "CHP / Cogeneration Allocation".
2. Heat Output (MMBtu) 100, Power Output (MWh) 100, Method WRI Efficiency, Total Facility Emissions 1000 tCO2e; submit.

## Input
Heat 100 MMBtu, power 100 MWh (= 341.21 MMBtu), 1000 tCO2e total.

## Expected
WRI efficiency method (e_H 0.8, e_P 0.33, the server's own constants): heat share = (100/0.8) / (100/0.8 + 341.21/0.33) = 125 / 1158.98 = 10.79 % → **107.9 tCO2e**.

## Actual
Response/record 40: `co2e 292.04 tCO2e` = 125 / (125 + 100/0.33) — power treated as 100 MMBtu. 2.71× overstated. (Energy-content method: 50 % instead of 22.7 %.)

## Evidence
`audit/work/K/t_s2.mjs cogen` — POST `{"cogen_allocation":{"total_emissions":1000,"heat_output":100,"power_output":100,"allocation_method":"wri_efficiency"}}` → 201 `co2e 292.035`. Repro `audit/repro/BUG-<id>.mjs`.

## Root Cause
Unit contract mismatch: the UI asks for MWh, the server variable is named `power_mmbtu` but is never converted (even the explicit `power_output_mwh` key is not converted).

## Impact
Every CHP allocation entered through the UI over-allocates emissions to heat (Scope 2) by a factor that depends on the power/heat ratio.

## Affected Components
Scope 2 CHP / Cogeneration Allocation entry; Scope 2 totals.

## Recommended Fix
Convert MWh → MMBtu (×3.412142) on the server (or send MMBtu from the client and relabel), and name the payload key with its unit.
