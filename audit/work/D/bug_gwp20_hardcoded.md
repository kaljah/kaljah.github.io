# BUG-XXX — GWP-20 conversion in intensity-stats / intensity-trend hard-codes AR5 GWP-100 (28 / 265), so GWP-20 CO2e is wrong whenever the active standard is AR4 or AR6

**Status:** Confirmed
**Severity:** Medium
**Category:** Methane
**Discovered by:** Agent D (Methane Auditor)

## Location
- `new/server/routes/dashboard.py` `_query_intensity_stats` (~line 2030): `delta_gwp = (ed["total_ch4"] * (ch4_gwp20 - 28.0)) + (ed["total_n2o"] * (n2o_gwp20 - 265.0))`
- `new/server/routes/dashboard.py` `_query_intensity_trend_bulk` (~line 1592): same expression.
- Contrast: `_query_summary` (~line 476) and `_query_categorical_breakdown` (~line 789) correctly use `get_active_gwp(horizon="100")`.

## Reproduction
1. Fresh audit DB copy; log in as admin.
2. `PUT /api/auth/settings {"gwp_standard":"AR4"}` (this triggers `recalculate_all_emissions_gwp`, so stored `co2e_total` = CO2 + 25·CH4 + 298·N2O).
3. `GET /api/dashboard/batch-all?...&gwp_horizon=20` → `summary[year].scope1_total_gwp20`.
4. `GET /api/dashboard/intensity-stats?year=<year>` → sum of `total_scope1_gwp20`.
5. Compare both with a hand calculation from DB rows: Σ(CO2 + CH4·72 + N2O·289) (the app's own AR4 20-yr values).

## Input
Snapshot data, Verified Scope 1 rows, year 2021 (CH4 ≈ 14.3 Mt) and 2023.

## Expected
GWP-20 CO2e = CO2 + CH4·GWP20_CH4 + N2O·GWP20_N2O for the active standard. Equivalently, the delta applied to the stored GWP-100 total must be CH4·(GWP20_CH4 − GWP100_CH4_active) + N2O·(GWP20_N2O − GWP100_N2O_active). For AR4 that is CH4·47 − N2O·9.
- 2021: 5,736,270,170 tCO2e
- 2023: 2,423,600.75 tCO2e

## Actual
- `/summary` (hero card): 5,736,270,170.28 (2021) and 2,423,600.75 (2023). These are correct.
- `/intensity-stats` Σ total_scope1_gwp20: **5,697,952,104** (2021, −38.3 Mt, −0.67 %) and **2,406,187.46** (2023, −17.4 kt, −0.72 %).
Under AR4 the code applies CH4·44 + N2O·24 instead of CH4·47 − N2O·9. Under AR6 it applies CH4·54.5 + N2O·8 instead of CH4·54.6 + N2O·0; the 2023 overstatement is 187.7 t.

## Evidence
`audit/work/D/s2.py AR4 2021`, `s2.py AR4 2023` and `s2.py AR6 2023` outputs. Repro: `audit/repro/<ID>.py`.

## Root Cause
The 100-year base in the GWP-20 delta is the literal AR5 value (28 / 265), not `get_active_gwp(horizon="100")`. `recalculate_all_emissions_gwp()` restates stored `co2e_total` with the active standard's GWP-100, so the literal subtraction no longer matches the stored basis.

## Impact
With AR4 or AR6 selected, every GWP-20 value derived from intensity-stats or intensity-trend is wrong. That covers `co2_intensity_gwp20`, `scope1_intensity_gwp20`, `total_co2e_gwp20` and `total_scope1_gwp20`: the dashboard Performance Intensity KPI in GWP-20 mode, Carbon/Methane intensity pages and trend charts. They then disagree with the dashboard hero total, which is computed correctly.

## Affected Components
`_query_intensity_stats`, `_query_intensity_trend_bulk`, `/api/dashboard/intensity-stats`, `/api/dashboard/intensity-trend`, `batch-all.intensity_stats(_py)`, DashboardEnhanced intensity KPI (GWP-20), CarbonIntensity/MethaneIntensity pages.

## Recommended Fix
Use `gwp100 = get_active_gwp(horizon="100")` and compute `delta = ch4*(g20["CH4"]-g100["CH4"]) + n2o*(g20["N2O"]-g100["N2O"])`, or better, compute GWP-20 directly as CO2 + CH4·g20 + N2O·g20. Share one helper across all four call sites.
