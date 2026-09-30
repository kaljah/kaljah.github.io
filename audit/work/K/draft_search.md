# BUG-XXX — Reports search keeps the current page number: "Total Records: 42 | Showing: 0" and no pager to recover

**Status:** Confirmed
**Severity:** Medium
**Category:** UI
**Discovered by:** Agent K (Frontend/UI)

## Location
`new/client/src/pages/Reports.jsx` — the filter-change effect (≈lines 99-145). `searchTerm` is in the dependency array but is not part of `prevFiltersRef`/`filterChanged`, so a search change never resets `page` to 1.

## Reproduction
1. Log in as audit_admin (:5191), /reports, set Year = All (809 records, 17 pages).
2. Click Next → "Page 2 of 17".
3. Type "Flaring" in the Search box.

## Input
page = 2, search = "Flaring" (42 matches, 1 page).

## Expected
Request with `page=1&search=Flaring`; table shows the first 42 matches.

## Actual
Request `GET /api/emissions?page=2&per_page=50&scope=all&search=Flaring` → `{total: 42, pages: 1, emissions: []}`. The page shows "Total Records: 42 | Showing: 0" and "No emission records found. Adjust your filters…". The pager is not rendered when the list is empty, so there is no way back to page 1 other than clearing the search.

## Evidence
`audit/work/K/t_reports4.mjs` output:
```
Page 2 of 17 (809 records)
search reqs: ['/api/emissions?page=2&per_page=50&scope=all&search=Flaring']
last resp total 42 pages 1 len 0
Total Records: 42 | Showing: 0
no pager
```
Repro: `audit/repro/BUG-<id>.mjs`.

## Root Cause
`searchTerm` omitted from the "filter changed → reset page" comparison. (Also: no debounce, one request per keystroke.)

## Impact
Users searching from any page other than 1 are told no matching records exist when they do.

## Affected Components
Reports "Emission Database" table search.

## Recommended Fix
Include `searchTerm` in `prevFiltersRef`/`filterChanged` (and debounce the input); also clamp `page` to `pages` when the response has `page > pages`.
