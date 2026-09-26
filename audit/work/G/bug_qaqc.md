# BUG-XXX — QA Dashboard "IPCC Tier 1 Uncertainty" reports 1σ as ±%, uses only the CO2 column, and includes Draft and Pending records, so it contradicts the Uncertainty page

**Status:** Confirmed
**Severity:** Medium
**Category:** Uncertainty
**Discovered by:** Agent G (Uncertainty Auditor)

## Location
- `new/server/routes/qaqc.py` ~L160-222 (`_norm_unc`, s1/s2/s3 `unc_var`, `overall_uncertainty`) and L598-606 (`tier1_uncertainty`).
- `new/client/src/pages/QADashboard.jsx` L530-548, which displays `±{overall*100}%` with no confidence level.

## Reproduction
1. As admin, POST a Verified stationary_combustion / Natural Gas / 12000 m3 record for 2047.
2. POST the same fuel with `status: "Draft"`, 120000 m3.
3. Compare GET `/api/qaqc/dashboard?year=2047` `tier1_uncertainty` with GET `/api/dashboard/uncertainty?year=2047`.
Script: `audit/repro/<ID>.py`.

## Input
The Verified record totals 22.959 tCO2e. Its stored u_CO2 (1σ) is 0.0559. The Draft record is 10× larger.

## Expected
Both pages report the same inventory quantity. For the Verified inventory at 95 % (IPCC Eq. 3.1): √(5² + 10²) = ±11.18 % on 22.959 t.

## Actual
- QA card: **±5.11 %** on **252.547 t**. The value is 1σ (no k=2), and the total includes the Draft record.
- Uncertainty page: ±22.36 % on 22.959 t. That figure is itself inflated by BUG-018.
On the snapshot, year 2022 shows QA ±2.08 % against the Uncertainty page ±57.18 %, and year 2020 shows 4.09 % against 818.97 %.

## Evidence
Repro output above. `overall_uncertainty = sqrt(Σ(u·E)²)/ΣE`, with `u` taken from `uncertainty_pct` or the CO2 `uncertainty` column only (CH4 and N2O are ignored). The status filter is `status != 'rejected'`, so Draft and Pending are included. No coverage factor is applied.

## Root Cause
The QA dashboard reimplements the aggregation independently. It uses a different subset (all non-rejected records instead of Verified), a different confidence level (1σ instead of 95 %), and a different gas basis (CO2 column only). Its default for missing values is 0.05 for S1/S2 and 0.10 for S3, against the Uncertainty page's 0.10–0.40. The UI labels the result "IPCC Tier 1 Uncertainty ±x%", which reads as a 95 % figure.

## Impact
The two pages give contradictory inventory uncertainty for the same year and facilities, often by more than 10×. The QA figure understates the 95 % uncertainty by about half and covers unapproved data. For CH4-dominated sources (venting, fugitive), where only `uncertainty_ch4` is stored, it falls back to 5 %.

## Affected Components
`/api/qaqc/dashboard` `tier1_uncertainty`, `QADashboard.jsx` KPI card (overall and S1/S2/S3).

## Recommended Fix
Reuse `_query_uncertainty`, or a shared service, for the QA card: Verified status, 95 % (k=2), and CO2e-weighted per-gas uncertainty. Label the confidence level in the UI.
