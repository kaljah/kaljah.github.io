# BUG-XXX — Custom factors used by Tier 2 records can be deleted: the reference check matches `fuel_type == factor name`, but UI records store the factor id, which SQLite then reuses for the next factor

**Status:** Confirmed
**Severity:** Medium
**Category:** Database
**Discovered by:** Agent C (Tier / Factor Auditor)

## Location
- `new/server/routes/custom_factors.py` `delete_custom_factor()`: `Emission.query.filter(Emission.fuel_type == factor.name)` and `Scope2Emission.source_type == factor.name`.
- `new/client/src/components/Scope1Form.jsx`: in Tier 2 "custom_factor" mode it sends `fuel = fuel_type = String(customFactor.id)` plus `custom_factor_id`.
- `models.py` `CustomFactor.id` is a plain Integer PK (SQLite rowid, no AUTOINCREMENT), so ids are reused.

## Reproduction
1. `python audit/repro/BUG-<ID>.py` (own db).
2. Create a custom factor and a Tier 2 record that uses it, exactly as the UI does.
3. DELETE `/api/custom-factors/<id>`.
4. Create another custom factor.

## Input
Custom factor "Site flare gas EF" (2.0 kg CO2/m3), referenced by record 752 (`fuel_type="102"`, `source_payload.custom_factor_id=102`).

## Expected
409 "referenced by 1 emission records", as the route intends.

## Actual
The DELETE returns 200 and the factor row is removed. The next custom factor created gets id 102 again, so the record's stored fuel_type / custom_factor_id now point to an unrelated factor ("Unrelated diesel EF").

## Evidence
Repro output:
- `DELETE /api/custom-factors/102 -> 200 {'message': 'Custom factor deleted'}`.
- `next custom factor created gets id 102 (same as deleted id)`.

## Root Cause
The reference check compares by name, but the UI links records by id. There is also no FK from emissions to custom_factors, and ids are reused.

## Impact
- The audit trail for Tier 2 records breaks: the factor behind a reported number disappears, or is replaced by another factor under the same id.
- A later recalculation (see the Tier 2 recalculation bug) or an audit lookup resolves the wrong factor.
- The dashboards shared with Tier 2 records cannot be traced to their EF.

## Affected Components
- Custom factor delete (Reference Data / Manage Data pages).
- Tier 2 Scope 1 records created from the UI.
- Scope 2 records referencing custom factors by id, if any.

## Recommended Fix
- Store `custom_factor_id` as a real FK column on emissions.
- Block deletion by id reference (and by the name for legacy rows), or soft-archive factors.
- Use AUTOINCREMENT, or never reuse ids.
