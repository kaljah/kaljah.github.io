# BUG-XXX — Custom emission factor with every factor field blank is saved (CO2/CH4/N2O = 0) and Tier 2 records that use it are stored with 0 tCO2e and no warning

**Status:** Confirmed
**Severity:** Medium
**Category:** API
**Discovered by:** Agent L (Browser)

## Location
- `POST /api/custom-factors` (route in `new/server/routes/` custom-factor handler): only rejects negative values (`co2_factor must be a non-negative number`); blank strings are coerced to 0.0 and there is no "at least one factor > 0" rule.
- `new/client/src/pages/ManageData.jsx` `handleSaveFactor` (~L944): only checks `factor_name`.
- Scope 1 Tier 2 path (`calc_method server_custom_factor`) applies the zero factor without flagging it.

## Reproduction
1. :5190 as audit_admin → Manage Data → Emission Factors. Name "AUDIT-L EMPTY", Unit gal, leave CO₂/CH₄/N₂O factor fields empty → "Save Factor" → toast "Factor added!".
2. Calculations → Scope 1 → AUDIT-L Plant, 2025-02, Tier 2 → "Saved Custom Factors Library" → "AUDIT-L EMPTY", 100 gal → Save as Draft.

## Input
`POST /api/custom-factors {"factor_name":"AUDIT-L EMPTY","unit":"gal","co2_factor":"","ch4_factor":"","n2o_factor":"",...}`; then `POST /api/emissions/` with `factor_source:"custom", custom_factor_id:102, quantity:100, unit:"gal"`.

## Expected
The factor is rejected ("enter at least one emission factor"), or at minimum records using an all-zero factor are refused/flagged.

## Actual
- 201 `{"id":102}`; stored row `co2_factor 0.0, ch4_factor 0.0, n2o_factor 0.0`. (Saved twice → ids 102 and 104, same name.)
- Scope 1 record: 201, `emissions {"ch4":0,"co2":0,"n2o":0,"totalCo2e":0}`, `calculation_method server_custom_factor`.
- For comparison the negative case is rejected server-side (400 "co2_factor must be a non-negative number") but the UI shows only "Failed to save factor".

## Evidence
`audit/work/L/w16_cf.mjs`, `w17_t2.mjs` outputs; `custom_factors` ids 102-105 in `audit/db/browser.db`.

## Root Cause
Validation treats blank as zero and zero as valid for all gases simultaneously.

## Impact
Activity data entered against such a factor contributes nothing to the inventory while looking complete (201, success toast, Verified for admin). Because factor names are not unique (BUG-065), an empty duplicate can also be picked by name in bulk import.

## Affected Components
Manage Data → Custom Emission Factors, `POST/PUT /api/custom-factors`, Scope 1 Tier 2 manual and bulk paths.

## Recommended Fix
Require at least one factor > 0 (and non-empty numeric input for each provided gas); reject blank-only factors with 400; surface the server's validation message in the toast.
