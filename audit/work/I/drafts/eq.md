# BUG-XXX — Equity-share allocation ignores effective dates (time-sliced ownership never applied) and POST /api/equity/shares accepts any percentage (500, -50, inf) from any business role

**Status:** Confirmed
**Severity:** High
**Category:** API
**Discovered by:** Agent I (Backend/API/Security)

## Location
- `new/server/routes/equity_routes.py:129-205` `get_equity_allocation()` — `shares = FacilityEquityShare.query.filter_by(facility_id=fac.id).all()` then `next(s for s in shares if s.partner_id == p.id)`: the comment says "Find active share for the year" but `effective_start_date` / `effective_end_date` are never compared with `year`; the first row (lowest id) wins.
- `equity_routes.py:89-126` `save_equity_share()` — no range/finite check on `equity_share_pct`, no check that shares per facility/period sum to ≤100 %, `float("abc")` / NaN → unhandled 500; only `@login_required` + `require_facility_access`, so role `user` can rewrite ownership of its own facilities.

## Reproduction
1. Admin: end Sonatrach's 51 % share at facility 169 on 2023-12-31 and `POST /api/equity/shares {"facility_id":169,"partner_id":1,"equity_share_pct":70,"effective_start_date":"2024-01-01"}` (the model docstring: "Time-sliced equity ownership percentages … supports mid-year ownership shifts").
2. `GET /api/equity/allocation?year=2025&facility_id=169`.
3. `POST /api/equity/shares` with `equity_share_pct` 500, -50, "inf", "nan", "abc".
Script: `audit/repro/<BUG-ID>.py`.

## Input
Facility 169 (HBNS), 2025 Verified Scope 1 total 705,943.67 tCO2e (SQL).

## Expected
2025 Sonatrach share = 70 % → 494,160.57 tCO2e. Percentages outside 0–100 or non-numeric rejected with 400.

## Actual
Sonatrach pct 51.0, allocated 360,031.27 tCO2e (uses the expired 2021 slice). 500 and -50 and inf saved with 200; "nan" and "abc" → HTTP 500. A `user`-role account got 200 setting a 99 % partner share on its own facility 1.

## Evidence
```
2025 total verified co2e (SQL) = 705943.67
expected Sonatrach pct 70 (share effective 2024-01-01), alloc = 494160.57
actual   Sonatrach pct 51.0, alloc = 360031.27
expected 400 for equity_share_pct=500 / -50; actual 200 / 200
```

## Root Cause
Missing date filter when selecting the active slice; no input validation on the write endpoint.

## Impact
Equity-share (JV partner) emission allocations are wrong for any facility whose ownership changed, and allocations can exceed 100 % / go negative; ownership data can be modified by data-entry users without review.

## Affected Components
`/api/equity/allocation`, `/api/equity/shares` (GET/POST), any UI/report using partner allocations.

## Recommended Fix
Select shares where `effective_start_date <= year-end` and (`effective_end_date` is null or `>= year-start`), pro-rating mid-year changes; validate 0 ≤ pct ≤ 100, finite, and per-period sum ≤ 100; restrict writes to admin/superuser; return 400 on parse errors.
