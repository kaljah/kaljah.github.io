# BUG-XXX — Scope 1 bulk import books a row with a blank Unit as m³ and accepts year 1800, both of which the manual form/API reject

**Status:** Confirmed
**Severity:** Medium
**Category:** Emissions
**Discovered by:** Agent L (Browser)

## Location
- `new/server/background_processor.py:1698` — `unit = str(row.get("unit") or "m3").strip()`
- `new/server/background_processor.py` Scope 1 row path — no year range check, while `routes/emissions.py:3005-3006` rejects `yr < 1900 or yr > 2100` with 422 for manual entries.

## Reproduction
1. :5190 as audit_admin → Calculations → Scope 1 → "Bulk Import (Wizard)" → Next → Next → upload `audit/work/L/imp1.csv` (headers Date, Site, Process, Fuel, Qty, UOM, Year, Month).
2. Auto-mapping picks Date/Process/Fuel/Year/Month; map Region/Facility=Site, Quantity=Qty, Unit=UOM → "Start Import".
3. Job completes: 4 imported, 4 skipped.

## Input
Row 5: `2025-12-01,AUDIT-L Plant,combustion,Diesel (No. 2 Fuel Oil),200,,2025,12` (Unit blank).
Row 6: `1800-01-01,AUDIT-L Plant,combustion,Diesel (No. 2 Fuel Oil),10,gal,1800,1`.

## Expected
Both rows are skipped with a reason ("Unit is required", "Year out of range 1900-2100"), as the manual path does for the year (422 "Invalid year") and as the wizard marks Unit as a required field.

## Actual
- Row 5 imported as record 767: `quantity 200, unit 'm3'`, 72.32 tCO2e (Pending) — the file never said m³.
- Row 6 imported as record 768: `year 1800` (Pending). Once approved it appears as a separate year in dashboards/filters (the snapshot already contains a year-1800 record).
Job status: `processed 8, skipped_count 4` — the skip list (unknown region, negative, "abc", duplicate) contains neither row.

## Evidence
`audit/work/L/w15_import.mjs admin imp1.csv` run; `GET /api/emissions/upload/status/191dbc0f-…` skipped_preview; DB `emissions` ids 767, 768.

## Root Cause
The bulk processor substitutes a default for a missing unit instead of rejecting the row, and it does not share the manual route's year validation.

## Impact
Silent unit assumption changes the magnitude of imported emissions (a blank unit on a gal/bbl/tonne row is booked as m³); out-of-range years enter the inventory. Channel inconsistency: the same data is rejected manually but accepted in bulk.

## Affected Components
Scope 1 bulk import (CSV/XLSX), Scope 1 totals after approval, year filters.

## Recommended Fix
Treat a blank unit as a row error (no default). Apply the same year (1900-2100, or reporting-period) and month validation in `background_processor` as in `POST /api/emissions/`.
