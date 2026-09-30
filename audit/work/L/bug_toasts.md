# BUG-XXX — Manage Data forms discard the server's validation message and show a generic "Failed to …" toast (negative production, negative factor, facility 500, etc.)

**Status:** Confirmed
**Severity:** Low
**Category:** UI
**Discovered by:** Agent L (Browser)

## Location
`new/client/src/pages/ManageData.jsx` catch blocks that ignore `err.response.data.error`: L941 `Failed to add region`, L957 `Failed to save factor`, L971 `Failed to delete factor`, L1021 `Failed to save production`, L1031 `Failed to add source`, L1041 `Failed to save mitigation`, L1089 `Failed to delete CBAM record`, L1137 `Failed to delete OGMP survey`, L175 `Failed to save SBTi Target` (9 sites).

## Reproduction
Through the UI on :5190 as audit_admin:
1. Manage Data → Production Data, AUDIT-L Plant 2025-08, Oil −5000 bbl → Save Record → server `400 {"error":"Production amounts cannot be negative"}`; toast "Failed to save production".
2. Manage Data → Emission Factors, CO₂ factor −5 → Save Factor → server `400 {"error":"co2_factor must be a non-negative number"}`; toast "Failed to save factor".
3. Manage Data → Regions → Add Region without coordinates → server 500 (BUG-045); toast "Failed to add region".

## Input
As above.

## Expected
The toast shows the server's reason (as the Scope 1 form does: "Invalid year: must be between 1900 and 2100").

## Actual
Generic "Failed to …" with no reason; the user cannot tell whether the value, a permission, a duplicate or a server fault caused it.

## Evidence
`audit/work/L/w11_prod.mjs` (negative case), `w16_cf.mjs` (negative factor), `w2_facility.mjs` — network responses captured next to the toast text.

## Root Cause
`catch (err) { toast.error('Failed to …') }` without reading `err.response?.data?.error`.

## Impact
Validation errors look like system failures; users retry or give up instead of correcting data; support cannot distinguish causes.

## Affected Components
Manage Data: regions, custom factors, production, sources, mitigation, CBAM, OGMP surveys, SBTi target save.

## Recommended Fix
Use `err.response?.data?.error || 'Failed to …'` in every catch (a shared helper), as `Scope1Form.jsx` already does.
