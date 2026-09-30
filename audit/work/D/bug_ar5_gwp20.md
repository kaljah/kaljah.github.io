# BUG-XXX — AR5 20-year GWPs are wrong (CH4 82.5 instead of 84, N2O 268 instead of 264); AR6 pairs the fossil CH4 GWP-20 with the non-fossil-weighted GWP-100

**Status:** Confirmed
**Severity:** Medium
**Category:** Methane
**Discovered by:** Agent D (Methane Auditor)

## Location
- `new/server/calculations/constants.py:12`: `GWP_AR5 = {..., "CH4_20": 82.5, "N2O_20": 268.0}`. The module comment cites "AR5 - 2013, WG1 Table 8.7".
- `constants.py:15`: `GWP_AR6 = {"CH4": 27.9, ..., "CH4_20": 82.5}`.
- `constants.py:78-79`: fallback defaults 82.5 / 268.0.
- Mirrors: `new/client/src/constants.js:14-15,22,40-41`, `routes/auth.py:688-689`, `client/src/pages/Settings.jsx:33,44,514`.
- `DashboardEnhanced.jsx:723` toggle tooltip says "20-Year (Near-term, CH4=84 per IPCC AR5/AR6)". That is not the value applied.

## Reproduction
1. Default settings (AR5). `GET /api/dashboard/batch-all?...&gwp_horizon=20`.
2. For 2026: `scope1_total` (GWP-100) = 9,992.41, `ch4_total` = 338.9115 t, and `scope1_total_gwp20` = 28,463.09.
3. (28,463.09 − 9,992.41) / 338.9115 = 54.50 = 82.5 − 28. So CH4 is converted with a GWP-20 of 82.5.

## Input
Any CH4 or N2O quantity with the GWP-20 horizon under AR5 (the application default).

## Expected
IPCC AR5 WG1 Table 8.7 (without climate-carbon feedback, the set whose GWP-100 values 28 / 265 the app uses):
- CH4: GWP-20 = 84, GWP-100 = 28
- N2O: GWP-20 = 264, GWP-100 = 265

IPCC AR6 WG1 Table 7.15:
- CH4, fossil: GWP-20 = 82.5, GWP-100 = 29.8
- CH4, non-fossil: GWP-20 = 80.8, GWP-100 = 27.2
- The app's AR6 GWP-100 of 27.9 is the generic CH4 value, whose matching GWP-20 is 81.2.

For 1 t CH4 under AR5: expected 84 tCO2e (GWP-20); for 1 t N2O: 264 tCO2e.

## Actual
- AR5: 1 t CH4 gives 82.5 tCO2e (−1.8 %); 1 t N2O gives 268 tCO2e (+1.5 %).
- AR6: 27.9 is paired with 82.5, so the 100-yr and 20-yr figures come from different CH4 categories.
- The UI tooltip tells users 84 is used.

## Evidence
`batch-all` summary output (audit/work/D/s1.py): 2026 GWP-100 9,992.41 → GWP-20 28,463.09 with CH4 338.9115 t (Δ/CH4 = 54.50). The 2021 delta is also consistent with (82.5−28)·CH4 + (268−265)·N2O. Repro: `audit/repro/<ID>.py`.

## Root Cause
Wrong literals in the GWP table (82.5 is the AR6 fossil-CH4 GWP-20, copied into AR5; 268 matches no AR5 table value), mirrored into the client constants.

## Impact
With the GWP-20 toggle under the default AR5 standard, every methane CO2e is understated by 1.5 tCO2e per tCH4. For the snapshot's 84.3 Mt Verified CH4 that is ≈126 MtCO2e. The GWP-20 hero total, categorical breakdown, intensity (co2_intensity_gwp20), Settings table and Reports "20yr" option all use these values.

## Affected Components
calculations/constants.py, get_active_gwp(horizon="20"), dashboard `_query_summary`, `_query_categorical_breakdown`, `_query_intensity_stats`, `_query_intensity_trend_bulk`, client constants.js, Settings.jsx GWP table, DashboardEnhanced GWP toggle tooltip.

## Recommended Fix
Set AR5 `CH4_20 = 84`, `N2O_20 = 264`. For AR6, use a consistent CH4 pair (27.9 / 81.2, or fossil 29.8 / 82.5 by source category). Keep constants.js, Settings.jsx and auth.py in sync, and make the tooltip read from the active constants.
