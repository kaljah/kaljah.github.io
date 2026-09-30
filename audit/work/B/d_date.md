# BUG-XXX — Scope 2/3 bulk import silently books rows with a blank or non-ISO date to January 2024, and stores a blank Scope 3 category as "Category "

**Status:** Confirmed
**Severity:** High
**Category:** Emissions
**Discovered by:** Agent B (Emissions Auditor)

## Location
`new/server/background_processor.py`:
- `_process_row_scope2` ~L884-895, `_process_row_scope3` ~L1195-1206 and `_process_row_scope3_eeio` ~L1097-1110: `year = int(row.get("year") or 2024)`, `month = int(row.get("month") or 1)`, then `date.split("-")` inside `try/except: pass`. The EEIO `if not year or not month` check can never fire because of the defaults.
- `_process_row_scope3` ~L1223: `cat = row.get("category", "11")` returns `""` for an empty cell, and the row is stored as `"Category "`. Free-text categories are never checked against the 15 GHG Protocol categories.
- Scope 1 (`_process_row`) by contrast rejects a missing date/year and a missing month.

## Reproduction
1. Run `python audit/repro/BUG-082.py` (own db).
2. Scope 3 CSV rows: `,ADR,4,no date,...` (blank Date), `03/2037,ADR,7,slash date,...` (MM/YYYY date), `2037-04,ADR,,blank category,...`.
3. Scope 2 CSV row: `,ADR,electricity,3000,kWh,...` (blank Date).

## Input
See above. `03/2037` is a common spreadsheet date format.

## Expected
Rows with a missing or unparseable date, or a missing or invalid category, are rejected with a row error, as Scope 1 bulk does.

## Actual
All rows are accepted (skipped 0):
```
scope3 stored: [{'year': 2024, 'month': 1, 'category': 'Category 4', 'sub_category': 'no date'}, {'year': 2024, 'month': 1, 'category': 'Category 7', 'sub_category': 'slash date'}, {'year': 2037, 'month': 4, 'category': 'Category ', 'sub_category': 'blank category'}]
scope2 stored: [{'year': 2024, 'month': 1, 'electricity_kwh': 3000.0}]
```
The 2037 data is moved into the 2024 inventory, and the upload reports success. Because the fabricated 2024-01 key then collides with other undated rows, subsequent undated or mis-formatted rows for the same facility and category are dropped as "duplicates" (seen in `audit/work/B/t16.py`).

## Evidence
Output above. Also see `audit/work/B/t15.py` and `t16.py`.

## Root Cause
Hard-coded fallback year and month, a swallowed parse exception, and no category validation in the Scope 2/3 row processors.

## Impact
Emissions are silently shifted between reporting years. 2024 is inflated and the true year understated, which affects SBTi base/target years, YoY and intensity. Unclassified Scope 3 records ("Category ") fall outside every per-category breakdown.

## Affected Components
Scope 2, Scope 3 and Scope 3 EEIO bulk import; year-filtered dashboards, reports and SBTi.

## Recommended Fix
Remove the 2024/1 defaults. Parse the accepted date formats explicitly (YYYY-MM, YYYY-MM-DD, MM/YYYY), otherwise return a row error. Validate year and month ranges. Require a category that maps to Category 1-15, rejecting blank or unknown values.
