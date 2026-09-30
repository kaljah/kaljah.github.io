# BUG-XXX — Scope 2/3 bulk import duplicate key is too coarse: separate meters and sub-categories in the same facility-month are rejected as "duplicates", or with Overwrite they replace a different existing record

**Status:** Confirmed
**Severity:** High
**Category:** Emissions
**Discovered by:** Agent B (Emissions Auditor)

## Location
`new/server/background_processor.py`:
- `_process_file_thread` L374-403 pre-loads existing keys. Scope 2: `(facility_id, year, month, source_type)`. Scope 3: `(facility_id, year, month, category)`. Every status is included.
- `_process_row_scope2` (key ~L1016), `_process_row_scope3` (key `(fac, year, month, category)`, ~L1259) and `_process_row_scope3_eeio` (key `(fac, year, month, "category 1")`, ~L1129). The sub_category, grid_region/meter, NAICS code, amount and unit are not part of the key.

## Reproduction
Run `python audit/repro/BUG-080.py` (own db). It uploads through `POST /api/emissions/upload/start` as admin:
1. Scope 3 CSV with two rows for ADR 2037-03, Category 6: "Air travel" (1000 x 0.2 kg) and "Hotel nights" (1000 x 0.03 kg).
2. Scope 2 CSV with two electricity rows (two meters) for ADR 2037-03: 1000 kWh and 2000 kWh.
3. Scope 3 "Air travel" for 2037-05 is uploaded, then a second file with "Hotel nights" for 2037-05 is uploaded with `overwrite_duplicates=true`.

## Input
See above.

## Expected
The rows are distinct activity lines, not duplicates. Scope 3 2037-03 gives 2 rows and 0.23 t. Scope 2 2037-03 gives 2 rows and 3000 kWh. Scope 3 2037-05 gives 2 rows and 0.23 t.

## Actual
```
S3 same cat/month two sub-categories: expected 2 rows 0.23 t, actual {'n': 1, 's': 0.2}
S2 two meters same month: expected 2 rows 3000 kWh, actual {'n': 1, 's': 1000.0}
S3 2nd upload w/ overwrite, other sub-category: expected 2 rows 0.23 t, actual {'n': 1, 's': 0.03}
```
- Without overwrite, the second line is skipped: "Duplicate record: Scope 3 emission for facility 'ADR' (2037-03, Category 6) already exists".
- With overwrite, the existing Air-travel record is silently turned into Hotel nights (0.2 t becomes 0.03 t, and it is set back to Pending).
- The EEIO spend path allows only one Category 1 line per facility per month across all NAICS codes.
- The pre-load also includes Rejected and Draft rows, so a corrected re-upload of a rejected month is blocked unless Overwrite is used.

## Evidence
Output above. Also see `audit/work/B/t15.py` and `t16.py`.

## Root Cause
The dedup key identifies a Scope 2/3 record by facility, month and category/source type only. Real inventories have many lines per category per month: purchased goods by commodity, business travel by mode, multiple meters and suppliers. Scope 1 by contrast includes fuel and equipment_id in its key.

## Impact
Bulk-imported Scope 2 and Scope 3 inventories are silently incomplete: only the first line per category-month survives. With "Overwrite Duplicates" on, unrelated existing records are replaced, which destroys data. Scope 3 Category 1 spend-based (EEIO) inventories can hold only one NAICS line per month.

## Affected Components
Scope 2 bulk import, Scope 3 bulk import (activity- and spend-based), totals and reports derived from them.

## Recommended Fix
Include sub_category, meter/grid_region, NAICS code (and ideally unit and an optional external row id) in the key. Exclude Rejected and Draft rows from the pre-loaded duplicate set, or handle them explicitly. Never overwrite a record whose descriptive fields differ.
