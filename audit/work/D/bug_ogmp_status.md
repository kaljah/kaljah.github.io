# BUG-XXX — Facility OGMP 2.0 level counts Draft, Pending and Rejected emission records, so a rejected record can raise a facility's level

**Status:** Confirmed
**Severity:** Medium
**Category:** Methane
**Discovered by:** Agent D (Methane Auditor)

## Location
`new/server/services/ogmp.py` `compute_facility_ogmp_level()`, ~lines 88-97:
```python
q = Emission.query.filter_by(facility_id=facility.id)
if year ...: q = q.filter_by(year=int(year))
records = q.all()
bottom_up_level = max((ogmp_level_for(r) for r in records), default=2)
```
No `status == "Verified"` filter. Callers: `/api/dashboard/ogmp-metrics` (`highest_ogmp_level`, shown on MethaneIntensity OGMP roadmap) and `/api/reports/ogmp-export` (Excel "Current Level" column).

## Reproduction
1. Fresh DB copy. Facility 169, year 2025 has 7 Verified records, all `ogmp_level` 3 (772.46 tCH4).
2. `GET /api/dashboard/ogmp-metrics?year=2025&facilityId=169` returns `highest_ogmp_level` = 3.
3. Add one **Rejected** record for the same facility/year with `factor_source='specific'`, `ogmp_level=4`, CH4 0.001 t. The admin reject flow sets `status="Rejected"`, `routes/emissions.py:4541`.
4. Clear the cache and call again: `highest_ogmp_level` = **4**.

## Input
One rejected 0.001 tCH4 Tier-3 record next to 772 t of Verified Level-3 inventory.

## Expected
Only Verified records form the reported bottom-up inventory. The same Verified filter is already applied to the CH4 totals in the same endpoint. Level should stay 3.

## Actual
Level 4. In the same way, a Draft/Pending/Rejected Tier-3 record also removes the "bottom-up must be L4" cap on Level 5 (Gold Standard), which the code itself describes as mandatory.

## Evidence
`audit/work/D/s5.py` output: `before 3` → `after adding one REJECTED 0.001 t specific record: 4`. Repro: `audit/repro/<ID>.py`.

## Root Cause
The record query in `compute_facility_ogmp_level` lacks the status filter. It also takes the **max** level over records rather than the level of the material share of emissions. For example, facility 13 (2026) has 236.6 t of its 338.9 tCH4 at Level 2 and is still reported as Level 4.

## Impact
OGMP 2.0 levels and Gold-Standard status on the dashboard OGMP roadmap and in the regulator-facing OGMP Excel export can be overstated by unapproved or rejected data.

## Affected Components
services/ogmp.py, /api/dashboard/ogmp-metrics, /api/reports/ogmp-export (Summary sheet), MethaneIntensity.jsx OGMP roadmap table.

## Recommended Fix
Filter `Emission.status == "Verified"`. Derive the facility bottom-up level from the emission-weighted (materiality) share at L4, not the maximum over any single record.
