# BUG-XXX — Scope 1 "Recent Activity": Export CSV exports only the 10 rows of the current page, and the Year/Process filter options are built from that page only

**Status:** Confirmed
**Severity:** Medium
**Category:** UI
**Discovered by:** Agent K (Frontend/UI)

## Location
`new/client/src/components/Scope1Form.jsx` — Recent Activity toolbar (≈lines 2700-2790): Year options `[...new Set(entries.map(e => e.year))]`, Process options from `entries`, and `exportToCSV(entries.filter(...))`; `entries` holds only the current server page (`limit=10`).

## Reproduction
1. UI :5191 as admin → Emissions → Scope 1, scroll to "Recent Activity (Scope 1)" (pager "Page 1 of 76", 751 records).
2. Open the Year filter; click "↓ Export CSV".
3. Pick Year = 2026, reopen the Year filter.

## Input
Default view, then Year = 2026.

## Expected
Year options = all years with Scope 1 data (server `/filters/available`: 2099, 2026, 2025, 2024, 2023, 2022, 2021, 2020, 1800); CSV = all records matching the filter (751 unfiltered).

## Actual
- Year options: `All Years, 2026, 2025` only (years present on page 1); 2024 and earlier cannot be selected.
- After choosing 2026 the options collapse to `All Years, 2026` (no way to switch to another year without resetting).
- Export CSV downloads a file with **10** data rows.

## Evidence
`audit/work/K/t_recent3.mjs` output (above); file `audit/work/K/s1export.csv`. Repro `audit/repro/BUG-<id>.mjs`.

## Root Cause
Filter option lists and export are derived from the paginated `entries` state instead of server-side facets / a server export (`/api/emissions/export` exists).

## Impact
Users silently export 10 of 751 records; historic years/processes cannot be filtered from this screen.

## Affected Components
Scope 1 Recent Activity table (Year filter, Process filter, Export CSV).

## Recommended Fix
Populate options from `/api/filters/available` (or a facets endpoint) and export through `/api/emissions/export` with the active filters.
