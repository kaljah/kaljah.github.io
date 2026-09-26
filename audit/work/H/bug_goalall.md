# BUG-XXX — Dashboard "% GOAL" badge in the default All-years view divides the cumulative multi-year Scope 1+2 total by the single current-year goal (and ignores region/facility filters)

**Status:** Confirmed
**Severity:** Medium
**Category:** Dashboard
**Discovered by:** Agent H (SBTi Auditor)

## Location
`new/server/routes/dashboard.py` batch-all: `goal_year = int(year) if year and year != "all" else datetime.now().year` (~line 168). `new/client/src/pages/DashboardEnhanced.jsx` totals loop (~290-305, sums every year when `currentYear === "all"`) and "% GOAL" badge (~1136-1150: `stats.totalEmissions / goal.target_amount`). Goal is set via the header "+ Set Target" → ManageData goals tab.

## Reproduction
1. `python C:/Users/samsung/Desktop/H2/audit/repro/<BUG-ID>.py`
2. Verified S1+S2: 2020 = 800 t, 2023 = 750 t, current year 2026 = 0 t. Goal for 2026 = 1000 t.
3. Open the dashboard with Year = All (default) → batch-all returns the 2026 goal; badge = 1550/1000.

## Input
As above.

## Expected
Either no goal badge in the All-years view, or current-year actual / current-year goal = 0 / 1000 = 0 % (YTD).

## Actual
"155.0% GOAL" in red (danger class, >100 %), and the header shows "Target 2026: 1,000 tCO₂e" next to a cumulative 2020-2026 total. The goal is also compared with region/facility-filtered totals although goals are corporate-wide.

## Evidence
API returns `goal = {year: 2026, target_amount: 1000}` for year=all; JSX computes badge from the all-years `totalEmissions` (read directly, replicated in repro).

## Root Cause
Year = "all" is mapped to the current year's goal while the numerator is the all-year sum; no filter-scope awareness.

## Impact
The default dashboard view shows a meaningless and alarming goal attainment percentage once a goal exists for the current year.

## Affected Components
DashboardEnhanced.jsx hero card goal badge; batch-all `goal`.

## Recommended Fix
Hide the badge when Year = All (or compare only the goal year's actual), and hide/scale it when region/facility filters are active.
