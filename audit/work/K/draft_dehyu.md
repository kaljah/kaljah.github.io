# BUG-XXX — Dehydrator throughput entered under the label "MMscf/yr" is saved with unit "MMscf/day" (record activity unit 365× off)

**Status:** Confirmed
**Severity:** Medium
**Category:** UI
**Discovered by:** Agent K (Frontend/UI)

## Location
`new/client/src/components/Scope1Form.jsx` ≈line 1068-1072: `finalUnit = formData.dehy_unit || formData.unit || "MMscf/day"`; `DehydratorForm.jsx` labels the input "Gas Throughput (MMscf/yr)" and has no unit selector (so `dehy_unit` is never set).

## Reproduction
1. UI :5191 admin → Scope 1 → Dehydrator (Tier 3), Gas Throughput (MMscf/yr) = 1000, other required fields filled; submit.

## Input
1000 under the label "Gas Throughput (MMscf/yr)".

## Expected
Record activity `amount: 1000, unit: "MMscf/yr"` (or "MMscf").

## Actual
POST `amount: 1000, unit: "MMscf/day"`; stored record 756 shows 1000 MMscf/day, i.e. 365,000 MMscf/yr of activity in the record table, exports and anything that reads amount/unit.

## Evidence
`audit/work/K/t_dehy.mjs` output: `throughput label: Gas Throughput (MMscf/yr)*` / `amount/unit: 1000 MMscf/day`. Repro `audit/repro/BUG-<id>.mjs`.

## Root Cause
Hard-coded fallback unit contradicts the form label.

## Impact
Activity data audit trail and exports carry the wrong unit (365×); anyone recalculating from amount/unit gets the wrong result.

## Affected Components
Scope 1 dehydrator entry; Recent Activity table; Reports/exports Qty column.

## Recommended Fix
Use "MMscf/yr" (matching the label) or add an explicit unit selector.
