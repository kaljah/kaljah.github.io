# BUG-XXX — Onshore fugitives "Tier 1: Facility-Level" form: the on-screen preview says 16,644 tCO2e but the saved record is 1.456 tCO2e — the server ignores the selected facility type and duration and books the facility count as a count of valves

**Status:** Confirmed
**Severity:** High
**Category:** Emissions
**Discovered by:** Agent L (Browser)

## Location
- Client: `new/client/src/components/scope1/FugitivesForm.jsx` (Tier 1 facility-level inputs L650-715; "REAL-TIME CLIENT-SIDE ESTIMATION ENGINE" L317+, banner "ESTIMATED EMISSIONS PREVIEW (REAL-TIME API CALCULATION)" L1258+). Operating duration is displayed as a placeholder (365) and only enters `formData` when the user types in it; facility type/`fuel` only when the dropdown is changed.
- Server: `new/server/calculations/legacy_engine.py` ~L552-571 (`process == "fugitive"`): reads `calc_inputs.fugitive.method` (absent → "average"), `component` (absent → "valves") and `count = amount`; `facility_type`, `fugitive_tier`, `operating_days` are never read. Result tagged `calc_method = "server_fugitive_average"`.

## Reproduction
1. :5190 as audit_admin → Calculations → Scope 1; Region AUDIT-L Plant, 2025-05; Process "Onshore Equipment Leaks / Fugitives (API Chapter 7)" (Tier 1 Facility-Level shown by default).
2. With the visible defaults (Gas Production Facility, count 1, 365 days, preview 8,322 tCO2e) click "Calculate & Submit" → warning "Please select a fuel or emission factor", no request.
3. Re-select "Gas Production Facility (Table 7-1)" and set Facility Count = 2 → preview "16,644.000 t CO₂e (CH₄ 591.3 t, CO₂ 87.6 t)".
4. Submit → `POST /api/emissions/` 201.
Script: `node audit/repro/BUG-NNN.mjs`.

## Input
Request body sent by the UI: `calc_inputs.fugitive = {"facility_type":"gas_production","fuel":"Gas Production Facility (Table 7-1)","unit":"facilities","time_unit":"days","facility_count":2,"amount":2,"fugitive_tier":"tier1","fugitive_method":"component",...}` — no `operating_days`.

## Expected
The stored record matches what the form shows for the same inputs (whatever the correct factor math is, UI preview and server must use the same method, facility type and duration), and visible defaults are the values actually submitted.

## Actual
Saved record 763: `ch4 0.052 t, co2 0, totalCo2e 1.456 t, calculation_method server_fugitive_average` vs preview 16,644 t (591.3 t CH4 + 87.6 t CO2). Ratio ≈ 11,400×. The CO2 component shown in the preview is dropped entirely. The user sees the large preview, gets "Scope 1 entry added successfully", and the dashboard/inventory receive 1.456 t.

## Evidence
`audit/repro/BUG-NNN.mjs` output: `preview 16644 tCO2e vs saved 1.456 tCO2e`, `resp emissions {"ch4":0.052,"co2":0,...} server_fugitive_average`; `audit/work/L/w14_fug.mjs` log including the default-submit warning.

## Root Cause
The facility-level Tier 1 method exists only in the client preview. The server's legacy fugitive branch has no facility-level method and silently falls back to "average component = valves × count". The client preview uses placeholder defaults that are not in the submitted state.

## Impact
The figure a user validates on screen is not what is recorded. Upstream fugitive methane — a key OGMP/methane-intensity input — is recorded orders of magnitude off with no warning, and the facility type/duration chosen are lost from the record.

## Affected Components
Scope 1 form, onshore fugitives Tier 1 facility-level; `compute_emissions` legacy fugitive branch; methane intensity / OGMP / Scope 1 totals. Related: BUG-047 (per-hour fugitive factors ignore hours) — different code path.

## Recommended Fix
Implement the facility-level (Table 7-1/7-2) method on the server using `facility_type`, `facility_count` and duration, or post the preview inputs to a server preview endpoint so both use one implementation. Reject fugitive requests whose method/fields the server does not understand instead of defaulting to valves. Initialise `formData` with the displayed defaults.
