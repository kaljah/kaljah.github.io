# BUG-XXX — Emission goals API ("+ Set Target") has no value validation: negative, year 1, and NaN goals are accepted; a NaN goal for the current year makes the main dashboard batch return 500

**Status:** Confirmed
**Severity:** Medium
**Category:** API
**Discovered by:** Agent H (SBTi Auditor)

## Location
`new/server/routes/managedata.py` `add_or_update_goal()` (POST `/api/goals`, ~line 770); consumers `new/server/routes/dashboard.py` batch-all (`float(goal.target_amount)` ~line 258) and `get_goal()` `/dashboard/goals/<year>` (~line 951).

## Reproduction
1. `python C:/Users/samsung/Desktop/H2/audit/repro/<BUG-ID>.py`
2. As admin: `POST /api/goals {"year":1,"target_amount":-5}` → 200 (stored).
3. `POST /api/goals` raw body `{"year":2026,"target_amount":NaN}` → 200; SQLite stores NULL.
4. `GET /api/dashboard/batch-all` (default dashboard, year=all → goal of current year) → **500** `float() argument must be ... not 'NoneType'`; `GET /api/dashboard/goals/2026` → 500.

## Input
As above.

## Expected
400 for non-finite, negative/zero targets and for years outside a sane range (e.g. 1990-2100).

## Actual
All accepted. The snapshot already contains goals up to year 2126 (100 rows 2027-2126), showing there is no range check. With the NaN goal the main dashboard fails to load for every user for that year (for the current year: the default view).

## Evidence
Repro output: `year=1/-5 t -> 200; NaN -> 200; /dashboard/batch-all -> 500; /dashboard/goals/2026 -> 500`.

## Root Cause
Only presence checks (`data.get("year")`, `target_amount is not None`) and `float()` conversion; no `isfinite`, sign or range check. Readers call `float(goal.target_amount)` without None-guard (`/goals` list guards it, the other two do not).

## Impact
An API-only (UI sends `null` for NaN, which is rejected) admin/superuser input can take down the main dashboard; negative goals make the "% GOAL" badge nonsensical. Medium: requires privileged API use, but the effect is platform-wide.

## Affected Components
`/api/goals` POST; `/api/dashboard/batch-all`; `/api/dashboard/goals/<year>`; DashboardEnhanced.jsx top-bar goal badge and "% GOAL" badge.

## Recommended Fix
Validate `math.isfinite(target) and target > 0` and a year range; guard `target_amount is None` in the readers.
