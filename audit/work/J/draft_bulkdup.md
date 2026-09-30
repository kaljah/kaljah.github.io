# BUG-XXX — Bulk upload with "Overwrite Duplicates" enabled inserts every in-file duplicate row as a separate record (double counting)

**Status:** Confirmed
**Severity:** High
**Category:** Database
**Discovered by:** Agent J (Database)

## Location
`new/server/background_processor.py` — duplicate-key logic in `_process_row` (Scope 1, ~l.1862-1899), `_process_row_scope2` (~l.1024-1047), `_process_row_scope3_eeio` (~l.1130-1151), `_process_row_scope3` (~l.1259-1281).

## Reproduction
1. `make_db` copy; log in as admin (facility names NULL renamed first to avoid BUG-029).
2. `POST /api/emissions/upload/start` scope=1, `overwrite_duplicates=true`, CSV with the same row three times:
   `2019-05,RNS,mobile,Motor Gasoline,1000,gal,default,DUPTEST`
3. Repeat with `overwrite_duplicates=false`.

## Input
Header `date,facility,process,fuel,quantity,unit,factor type,equipment`; one row repeated 3×.

## Expected
Overwrite mode: the key (facility, year, month, process, fuel, equipment) ends with exactly one record (last row wins). Non-overwrite mode: 1 inserted, 2 rejected as duplicates.

## Actual
- overwrite=true → **3 records inserted** (3 × 8.81 = 26.42 t CO2e instead of 8.81).
- overwrite=false → 1 inserted, 2 rejected "Duplicate record…" (correct).

## Evidence
`audit/repro/BUG-<id>.py` prints `expected: 1 record; actual: 3 records`. Same code shape in Scope 2 and Scope 3 row processors (code inspection).

## Root Cause
A newly-seen key is stored as `batch_keys[key] = None` (the new object has no id yet). On a later in-file hit with overwrite enabled, `existing_id` is None → `existing_obj` is None → the `if existing_obj:` branch is skipped and execution falls through to creating another new record. The "overwrite" option is thus less safe than the default.

## Impact
Users who enable "Overwrite Duplicates" precisely to make re-uploads idempotent get duplicated emissions whenever a file contains a repeated key (common with re-exported spreadsheets); once approved, the Scope 1/2/3 totals are double counted. The DB has no unique constraint on emissions to catch it (only production_data has one). The snapshot already contains 16 Scope 1 duplicate groups (51 rows), 2 Scope 2 and 2 Scope 3 groups, e.g. facility 5 2025-03 flaring 15000 ×5 inserted in the same second.

## Affected Components
Bulk import for Scope 1, Scope 2, Scope 3 (activity-based and EEIO); dashboards/reports summing these tables.

## Recommended Fix
Store the pending object itself in `batch_keys` (as `_process_row_production` does with `batch_prod_map`) and update it in place on in-file repeats; add a DB unique index on the natural key (or at least a QA duplicate check).
