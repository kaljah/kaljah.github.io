# BUG-XXX — Inventory uncertainty shrinks by √N when the same emissions are split into N records (shared EF uncertainty treated as independent)

**Status:** Confirmed
**Severity:** High
**Category:** Uncertainty
**Discovered by:** Agent G (Uncertainty Auditor)

## Location
`new/server/routes/dashboard.py` `_query_uncertainty()` (~L2370-2615): Scope 1/2/3 queries group by (process, fuel, method, stored uncertainty) and compute `u_eff = u * sqrt(Σe²)/Σe`, then `srss_inventory()` sums every record in quadrature.

## Reproduction
1. As admin, POST 12 monthly `stationary_combustion` / Natural Gas / 1000 m3 / factor_source=default records for year 2041 (facility 4).
2. POST one record of 12000 m3 for year 2042 (same facility / fuel / factor).
3. GET `/api/dashboard/uncertainty?year=2041` and `?year=2042`.
Script: `audit/repro/<ID>.py`.

## Input
Identical annual inventory (22.9588 tCO2e, same emission factor, same stored per-record uncertainties) entered as 12 records vs 1 record.

## Expected
Identical inventory uncertainty for both years. The EF (±5 % @95 %) is a single value shared by all 12 records, so its error is fully correlated; IPCC 2006 Vol.1 Ch.3 Approach 1 applies the EF uncertainty to the category total. Hand calculation for this category: √(5² + 10²) = ±11.18 % (95 %).

## Actual
- 12 monthly records: ±6.45 %
- 1 annual record: ±22.36 %
The ratio is exactly √12 = 3.464.
(The ±22.36 % is itself 2× too high because of a separate cross-gas max issue.)

## Evidence
`u_eff = u·√(Σe²)/Σe` combined in `srss_inventory` gives relative σ = u·√(Σe²)/Σe. With 12 equal records this equals u/√12. The repro prints both results and the ratio.

## Root Cause
Every record (or group of records) is treated as an independent source. That holds for random activity-data metering error, but not for the emission-factor component, which is common to every record using the same factor. The EF and AD components are never separated. Only a single combined per-record 1σ is stored, so the dashboard cannot correlate them.

## Impact
The reported inventory and category uncertainty depends on data-entry granularity rather than on data quality. Monthly entry, which is the normal workflow, understates uncertainty by about √12 ≈ 3.5×. Facilities with many small records look far more certain than they are. For example, snapshot 2022 fuel_gas shows ±21.3 % while every contributor is ±30 %. The figure on the Uncertainty Assessment page, in its CSV export and in the Master Report is therefore not ISO 14064-1 / IPCC-defensible.

## Affected Components
`/api/dashboard/uncertainty` (JSON and CSV), `UncertaintyAssessment.jsx`, `ModernReportGenerator.js` (uses the same endpoint), `/api/qaqc/dashboard` `tier1_uncertainty` (same per-record quadrature sum, `routes/qaqc.py` ~L175-222).

## Recommended Fix
Aggregate emissions per source category / emission factor first. Apply the EF uncertainty to the category total, fully correlated. Combine only the independent activity-data components in quadrature within a category. Then combine categories with IPCC Eq. 3.2. This requires persisting the EF and AD components separately, or recomputing them from tier/factor at query time.
