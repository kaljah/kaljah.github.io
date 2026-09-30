# BUG-XXX — SBTi target POST accepts NaN / Infinity (range checks pass for non-finite floats); trajectory endpoint then returns 500 or invalid JSON for all users

**Status:** Confirmed
**Severity:** Medium
**Category:** SBTi
**Discovered by:** Agent H (SBTi Auditor)

## Location
`new/server/routes/managedata.py` `manage_sbti()` POST validation (~1040-1057); `new/server/routes/dashboard.py` `get_sbti_trajectory()` line 2764 `rate = target.reduction_rate_pct / 100.0`.

## Reproduction
1. `python C:/Users/samsung/Desktop/H2/audit/repro/<BUG-ID>.py`
2. As admin: `POST /api/manage/sbti` body `{"base_year":2020,"base_year_emissions":1000,"target_year":2030,"reduction_rate_pct":NaN}` → 201.
3. `GET /api/dashboard/sbti-trajectory` → 500 (`TypeError: unsupported operand type(s) for /: 'NoneType' and 'float'`; SQLite stores NaN as NULL).
4. POST `base_year_emissions: Infinity` → 201; trajectory → 200 with body containing bare `Infinity`/`NaN` tokens (not valid JSON; browsers' JSON.parse rejects it).
5. `base_year_emissions: NaN` → 400 but with the raw SQLAlchemy IntegrityError text (SQL statement and parameters) in the response.

## Input
Non-finite JSON numbers (Python's json parser accepts `NaN`, `Infinity`).

## Expected
400 "must be a finite number". Checks such as `reduction_rate_pct <= 0 or > 25` are all False for NaN, so they do not reject it.

## Actual
Stored; the latest target is used by `/sbti-trajectory`, so the SBTi page and the main dashboard SBTi banner break for every user until another target is posted (there is no delete/edit endpoint).

## Evidence
Repro output: `rate NaN: POST 201; trajectory GET 500` / `baseline Infinity: POST 201; trajectory GET 200 INVALID JSON (Infinity)`.

## Root Cause
No `math.isfinite` check; range comparisons against NaN are always False.

## Impact
One API call (admin/superuser) disables SBTi tracking platform-wide; error text leaks SQL. The UI form itself cannot produce NaN (parseFloat || 0), so it is an API-level validation gap.

## Affected Components
`/api/manage/sbti`, `/api/sbti` POST; `/api/dashboard/sbti-trajectory`; SbtiDashboard.jsx; DashboardEnhanced.jsx SBTi banner.

## Recommended Fix
Reject non-finite values (`math.isfinite`) for all numeric fields; return generic errors instead of `str(e)`; guard `reduction_rate_pct is None` in the trajectory.
