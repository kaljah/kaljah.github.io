# BUG-XXX — Pending-records banner ignores the GWP-20 toggle: it always shows GWP-100 tCO2e while every other dashboard figure switches to GWP-20

**Status:** Confirmed
**Severity:** Low
**Category:** Dashboard
**Discovered by:** Agent D (Methane Auditor)

## Location
- `new/server/routes/dashboard.py` `get_batch_dashboard_data()` ~lines 290-320: `pending_stats.totalCo2e = sum(Emission.co2e_total) + sum(Scope2Emission.co2e)` for status Pending. `gwp_horizon` is read and is part of the cache key, but it is not applied to this total.
- `new/client/src/pages/DashboardEnhanced.jsx` ~887-889: renders `{pendingCo2e} tCO₂e` in the banner regardless of `gwpHorizon`.

## Reproduction
1. Snapshot copy (agentD), admin.
2. `GET /api/dashboard/batch-all?facilityId=all&activity=all&division=all&year=2025` → `pending_stats`.
3. The same request with `&gwp_horizon=20` → `pending_stats`.
4. Hand-compute the pending GWP-20 figure from DB rows: Σ Pending S1 (CO2 + CH4·GWP20_CH4 + N2O·GWP20_N2O) + Σ Pending S2 CO2e.

## Input
Year 2025: 112 pending records; pending Scope 1 CH4 = 4,246.68 t.

## Expected
In GWP-20 mode the banner figure should be on the same basis as the KPIs next to it: 678,365.0 tCO2e (app's own AR5 20-yr factors, 82.5 / 268; 695,856 with the correct AR5 84 / 264, see BUG-013).

## Actual
`totalCo2e` = 446,919.3 in both horizons (GWP-100). The banner understates pending CO2e by 34 % in GWP-20 mode, so it disagrees with the amount the hero card jumps by when "Preview Pending" is switched on (summary applies GWP-20 to pending rows).

## Evidence
`audit/work/D/s12.py` output (re-run on the current code, baseline2): `banner GWP-100: 446919.3`, `banner GWP-20: 446919.3`, expected GWP-20 678,364.997. Repro: `audit/repro/<ID>.py`.

## Root Cause
The pending summary sums the stored GWP-100 `co2e_total` and never applies the horizon delta that `_query_summary` applies.

## Impact
Misleading figure next to methane-heavy KPIs in GWP-20 mode. The pending backlog looks a third smaller than it is on the chosen basis.

## Affected Components
/api/dashboard/batch-all `pending_stats`, DashboardEnhanced pending banner.

## Recommended Fix
Include CH4/N2O sums in the pending query and apply the same `get_active_gwp` delta as `_query_summary` when `gwp_horizon=20`, or label the banner figure "GWP-100".
