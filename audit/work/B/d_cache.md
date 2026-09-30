# BUG-XXX — Dashboard cache is not invalidated after a manual Scope 1 create or a bulk upload: new records are missing from the dashboard for up to 5 minutes (per worker)

**Status:** Confirmed
**Severity:** Medium
**Category:** Dashboard
**Discovered by:** Agent B (Emissions Auditor)

## Location
- `new/server/app.py` L93-116. The `before_commit` hook sets `has_relevant_changes` only if an Emission/Scope2/... object is in `session.new | dirty | deleted` at commit time. `after_commit` clears `DASHBOARD_CACHE` only when that flag is set.
- `routes/emissions.py` `add_emission()` L3218-3221 calls `db.session.flush()` and then `commit()`. After the flush the new row is no longer in `session.new`, so the flag is False. Unlike scope2/scope3/PUT/approve/delete, this route never calls `clear_dashboard_cache()` explicitly.
- `background_processor.py` L578/594 uses `db.session.bulk_save_objects(chunk)`, which never places objects in `session.new`, so there is no invalidation there either.

## Reproduction
1. Run `python audit/repro/BUG-069.py` (own db).
2. `GET /api/dashboard/summary?year=2024` gives total T0.
3. As admin, `POST /api/emissions/` with 1000 MMBtu natural gas, year 2024 (Verified, 53.1145 t).
4. `GET /api/dashboard/summary?year=2024` again, then compare with `SUM(co2e_total)` in the DB.

## Input
One Verified record of 53.1145 tCO2e. Separately, a 5-row Scope 1 CSV upload for year 2038.

## Expected
The summary increases by 53.1145 t right away, as it does after approve, delete and Scope 2/3 creates. Hand calc: 1000 x (53.06 + 0.001x28 + 0.0001x265) / 1000.

## Actual
```
before=3718016910467.4102 after=3718016910467.4102 db=3718016910520.5249 actual diff=0.0000
```
After a completed bulk upload of 5 rows (year 2038), `summary?year=2038&includePending=true` in the same process still returned `[]`. A fresh process returned scope1_total 129.26 t (`audit/work/B/t11.py`, `t13.py`).

## Evidence
See above. Approve and delete in the same session did update the summary immediately (+53.11 / -53.11, `audit/work/B/t9.py`), which isolates the create and bulk paths.

## Root Cause
Cache invalidation depends on detecting pending ORM objects in `before_commit`. This does not work when rows were flushed earlier or written with `bulk_save_objects`.

## Impact
Users who add data, or finish an import, and then open the dashboard see stale totals, KPIs, pending counts and charts (DASHBOARD_CACHE TTL 300 s, every cached query and batch-all). This looks like data loss or a failed upload.

## Affected Components
POST /api/emissions/, all background bulk uploads (scope 1/2/3/production...), /api/dashboard/* cached queries.

## Recommended Fix
Call `clear_dashboard_cache()` explicitly in `add_emission` and at the end of `_process_file_thread`. Alternatively, track changes in an `after_flush` listener, or set `session.info["has_relevant_changes"]=True` at flush time, instead of inspecting `session.new` in `before_commit`.
