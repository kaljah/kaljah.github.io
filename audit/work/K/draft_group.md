# BUG-XXX — Reports "Group By" selector has no effect (getGroupedData is never called)

**Status:** Confirmed
**Severity:** Low
**Category:** UI
**Discovered by:** Agent K (Frontend/UI)

## Location
`new/client/src/pages/Reports.jsx` — `getGroupedData()` (≈line 352) is defined but never referenced; the grid renders `emissions.map(...)` directly.

## Reproduction
1. /reports as admin, Year = All.
2. Change "No Grouping" to "By Facility" (or process / month / scope).

## Input
groupBy = "facility"

## Expected
Rows grouped by facility (with group headers) as the control promises.

## Actual
DOM rows identical before/after (50 rows, same order). Playwright: `groupBy changes DOM: false`.

## Evidence
`audit/work/K/t_reports4.mjs`; `grep -n getGroupedData Reports.jsx` → only the definition.

## Root Cause
Grouping logic not wired to the render.

## Impact
Control is a no-op; users may believe they are looking at grouped data.

## Affected Components
Reports page table.

## Recommended Fix
Render from `getGroupedData()` with group headers/subtotals, or remove the control.
