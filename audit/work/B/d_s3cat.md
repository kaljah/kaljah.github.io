# BUG-XXX — Scope 3 category is stored as "6" by the UI/API and as "Category 6" by bulk import: cross-channel duplicates are not detected (double counting) and category breakdowns split

**Status:** Confirmed
**Severity:** Medium
**Category:** Emissions
**Discovered by:** Agent B (Emissions Auditor)

## Location
- `new/client/src/components/Scope3Form.jsx:304` sends `category: parseInt(category)`.
- `new/server/routes/scope3.py` `create_scope3_emission()` stores `data.get("category", "Category 11")` as-is, so the result is `"6"`. The default is in the other format.
- `background_processor._process_row_scope3` normalises to `f"Category {cat}"`, so the result is `"Category 6"`.
- The bulk dedup key (`_process_file_thread` L390-403) compares the raw category string.
- `routes/dashboard.py` `_query_uncertainty` (L2419-2433) groups Scope 3 by the raw category, and the reports and QA lists show it raw.

## Reproduction
1. Run `python audit/repro/BUG-086.py` (own db).
2. As admin, `POST /api/scope3` `{"facility_id":5,"year":2037,"month":3,"category":6,"sub_category":"Air travel","activity_data":1000,"emission_factor":0.2}`, which is the payload shape Scope3Form sends.
3. Bulk-upload the same line: `2037-03,ADR,6,Air travel,1000,0.2,kg` (scope 3).

## Input
The same 0.2 t Category 6 air-travel line, entered once by form and once by import.

## Expected
One canonical category label. The bulk row is reported as a duplicate of the existing record, which is what happens for Scope 1 and for bulk-vs-bulk Scope 3.

## Actual
```
UI create: 201 ; bulk skipped: 0
rows: [{'id': 29, 'category': '6', ... 'co2e': 0.2, 'status': 'Verified'}, {'id': 30, 'category': 'Category 6', ... 'co2e': 0.2, 'status': 'Pending'}]
```
Once the bulk row is approved, the activity is counted twice. The snapshot already mixes labels: category `'11'` (1 row, 216.85 t, the only material Verified Scope 3 row) next to `'Category 11'`, and `'Category 1'`...`'Category 15'` from other paths. Per-category views (uncertainty items, reports, exports) show "11" and "Category 11" as different categories.

## Evidence
Output above. `select category,count(*) from scope3_emissions group by category` on `snapshot_original.db` returns both `'11'` and `'Category 11'`.

## Root Cause
There is no canonical category representation. The API accepts any string or integer, and only the bulk path normalises it.

## Impact
Scope 3 records entered through different channels are double counted, because the duplicate protection is bypassed. Category-level totals, uncertainty groupings and GHG-Protocol category reporting are fragmented. There is also no validation that the category is 1-15 (see also BUG-085).

## Affected Components
POST/PUT /api/scope3, Scope3Form, Scope 3 bulk import, uncertainty dashboard, reports/exports.

## Recommended Fix
Normalise the category to a single canonical form (e.g. integer 1-15 or "Category N") in every create, update and bulk path. Reject values outside 1-15. Migrate existing rows.
