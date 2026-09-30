# BUG-XXX — Scope 1 "Live Equation Inspector" states "GWP Standard: IPCC AR6 (CH₄:28, N₂O:265)" — hard-coded, AR5 values mislabelled as AR6, ignores the org GWP setting

**Status:** Confirmed
**Severity:** Low
**Category:** UI
**Discovered by:** Agent K (Frontend/UI)

## Location
`new/client/src/components/Scope1Form.jsx` ≈line 2598 (static string inside the Live Equation Inspector).

## Reproduction
1. Log in as admin (:5191) → Emissions → Scope 1; scroll to "Live Equation Inspector".
2. Submit a Tier 3 combustion entry (1000 m³, CO2 53.06 / CH4 0.001 / N2O 0.0001 kg/MMBtu, HHV 38 MJ/m³).
3. Check the stored record's `gwp_version` and CO2e.

## Input
Organisation GWP setting = AR5 (default).

## Expected
Label reflecting the active standard, e.g. "IPCC AR5 (CH₄:28, N₂O:265)"; under AR6 it would be "CH₄:29.8, N₂O:273" (the app's own Settings/Reports list AR6 as 29.8/273).

## Actual
Always "GWP Standard: IPCC AR6 (CO₂:1, CH₄:28, N₂O:265)". Records 754/755 were computed with AR5 (`gwp_version = 'AR5'`, CO2e 1.91303 t = 1.91106 + 3.6017e-5×28 + 3.6017e-6×265).

## Evidence
`audit/work/K/t_hhv.mjs` (screenshot `audit/work/K/hhv.png`, POST/201 capture); DB rows 754/755 in audit/db/ui.db.

## Root Cause
Hard-coded label text; not bound to `/auth/settings.gwp_standard` or `constants.js` GWP tables.

## Impact
Users/verifiers are told the calculation uses AR6 when it uses AR5 (or whatever is configured); misleading audit evidence.

## Affected Components
Scope 1 entry form (all process types).

## Recommended Fix
Render the active standard and its values from settings/`constants.js`.
