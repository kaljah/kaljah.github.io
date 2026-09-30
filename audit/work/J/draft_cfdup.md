# BUG-XXX — Custom factor names are not unique, yet bulk import resolves factors by name: the most recently created same-named factor is silently applied

**Status:** Confirmed
**Severity:** Medium
**Category:** Database
**Discovered by:** Agent J (Database)

## Location
- `new/server/models.py` `CustomFactor.name` — `index=True`, no unique constraint.
- `new/server/routes/custom_factors.py` POST (l.84) / PUT (l.164) / `/import` — no duplicate-name check; PUT allows renaming onto an existing name.
- `new/server/background_processor.py:338-339` `cf_name_map = {cf.name.lower(): cf for cf in CustomFactor.query.all()}` (last row wins); `routes/emissions.py:508-509` same pattern (per-user).

## Reproduction
1. `make_db` copy; admin.
2. `POST /api/custom-factors` `{"factor_name":"AuditDupGas","unit":"m3","co2_factor":1}` → 201 (id 102).
3. Same with `co2_factor: 100` → 201 (id 103).
4. Bulk upload Scope 1 CSV `2018-03,RNS,combustion,AuditDupGas,1000,m3,custom,CFDUP` (factor type custom).

## Input
Two factors named "AuditDupGas" (1 and 100 kg CO2/m3), 1000 m3 activity.

## Expected
Second create rejected (409) or the uploader forced to disambiguate; result would be 1.0 t CO2 with the first factor.

## Actual
Both saved. Import silently used factor id 103: `ef_used_co2=100, co2_emissions=100 t` (100× the other factor). Which factor is chosen depends only on row order in the table; the delete-guard (`fuel_type == factor.name`) also cannot tell same-named factors apart.

## Evidence
`audit/repro/BUG-<id>.py` (`audit/work/J/cfdup.py`).

## Root Cause
Custom factors are referenced by free-text name everywhere, but the name has no uniqueness constraint or validation (including case-insensitive collisions, since lookups use `lower()`).

## Impact
Any organisation with two users each saving e.g. "Fuel Gas" (or a superuser saving a revised version under the same name) gets Tier 2 imports computed with whichever was created last, without warning; emissions can be off by the ratio of the two factors.

## Affected Components
Custom factor CRUD and import, Scope 1 bulk import (background processor and `/api/emissions/import` style path), custom-factor delete guard.

## Recommended Fix
Add a (case-insensitive) unique constraint on `custom_factors.name` (or name+unit+version) and reject duplicates on create/rename/import; reference factors by id in records.
