# BUG-XXX — Scope 2 and Scope 3 create accept a missing or non-numeric year: one year-less Scope 2 record makes the main dashboard (summary/batch-all) return 500, and year-less Scope 3 is in the total but missing from by-year

**Status:** Confirmed
**Severity:** High
**Category:** Emissions
**Discovered by:** Agent B (Emissions Auditor)

## Location
- `new/server/routes/scope2.py` `create_scope2_emission()` (~L159-260) and `routes/scope3.py` `create_scope3_emission()` (~L70-125). They validate only `facility_id`. `year=data.get("year")` and `month=data.get("month")` are stored unvalidated: None, "abc" and 13 are all accepted. Scope 1 POST, by contrast, enforces 1900-2100 and 1-12.
- `routes/dashboard.py` `_query_summary` L508 `yr = int(row.year)` has no None guard, for both the Scope 1 and the Scope 2 loop.
- `routes/dashboard.py` `_query_scope3_summary`: `by_year` skips `y is None`, but `total` (year=all) sums every row.

## Reproduction
1. Run `python audit/repro/BUG-073.py` (own db). Manually:
2. As admin, `POST /api/scope2` with `{"facility_id":1,"source_type":"electricity","electricity_kwh":1000,"emission_factor":0.5}` (no year or month). The response is 201 and the row is Verified with year NULL.
3. `GET /api/dashboard/summary` and `GET /api/dashboard/batch-all`, as admin and as a West-region user.
4. `POST /api/scope3` with `{"facility_id":1,"category":"Category 1","activity_data":1000,"emission_factor":0.5}` (no year), then `GET /api/dashboard/scope3/summary`.

## Input
One 0.5 t Scope 2 row without a year. One 0.5 t Scope 3 row without a year. Also `year:"abc", month:13` for Scope 2, which is accepted (201).

## Expected
Create returns 422 for a missing, non-integer or out-of-range year or month, as Scope 1 does. Aggregations never crash on one bad row. Scope 3 `total` equals the sum of `by_year`.

## Actual
- Scope 2 create returns 201 for no year, and for `year:"abc", month:13`.
- After that, `/api/dashboard/summary` and `/api/dashboard/batch-all` return **500** for admin and for the West-region user (`TypeError: int() argument must be ... not 'NoneType'` at dashboard.py:508). The main dashboard is unusable for every user whose facility scope includes that facility.
- Scope 3 summary: `total 217.35` vs `sum(by_year) 216.85`. The year-less 0.5 t is counted in the headline total but is in no year, so the year chart does not add up to the KPI, and the row drops out of every year-filtered view.

## Evidence
```
scope2 without year -> 201 (expected 422)
batch-all before=200; after: summary=500 batch-all=500 (admin), batch-all as West user=500; expected 200
scope3 without year -> 201 ; scope3 total 217.35 sum(by_year) 216.85
```
(`audit/work/B/t14.py` also shows `year:'abc', month:13` stored as Verified.)

## Root Cause
Scope 2 and Scope 3 create have no date validation, and the summary aggregation casts `row.year` without a guard.

## Impact
Any user with Scope 2 create rights (the admin or superuser auto-Verify path, BUG-060) can take down the organisation dashboard with one API call or one client bug. Year-less Scope 2/3 emissions silently disappear from every year-filtered total, SBTi and intensity figure, while still inflating the all-years Scope 3 KPI.

## Affected Components
POST /api/scope2, POST /api/scope3 (and their PUT paths, which have the same pattern and were not separately verified), dashboard summary/batch-all, scope3 summary, year-filtered reports.

## Recommended Fix
Apply the Scope 1 year/month validation, ideally a shared helper, to the Scope 2 and Scope 3 create, update and bulk paths. Guard `int(row.year)` in the aggregations, skipping or bucketing NULL years as "Unknown" and surfacing them.
