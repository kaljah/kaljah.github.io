# BUG-XXX — Uncertainty display inconsistencies: EmissionResult shows the ±1σ (68 %) band as the "Confidence Interval", Scope 2/3 tables use k=1.96 while everything else uses k=2, and the Uncertainty page badge thresholds contradict its legend

**Status:** Confirmed
**Severity:** Low
**Category:** UI
**Discovered by:** Agent G (Uncertainty Auditor)

## Location
- `new/client/src/components/EmissionResult.jsx` L19-32 and L86-100 (`margin = value * uncertainty`, tooltip "Confidence Interval: lo - hi"). This component is shown after every Scope 1/2/3 save.
- `Scope2Form.jsx` L755 and `Scope3Form.jsx` L751 (`entry.uncertainty * 1.96 * 100`). Compare `calculations/uncertainty.py COVERAGE_FACTOR_95 = 2.0`, `CalculationDetails.jsx` (`* 200`), and `/api/dashboard/uncertainty` (k=2).
- `pages/UncertaintyAssessment.jsx` L150-154 (`<0.1` low, `<0.2` medium, else high). The legend in the same file (L284-296) and the backend `level` (dashboard.py ~L2590) use ≤10 % / ≤30 %.

## Reproduction
1. POST a stationary_combustion / Natural Gas / 1000 m3 record. The API returns `uncertainty.co2 = 0.0559` (1σ).
2. The result panel renders "±0.1068 t" with the tooltip "Confidence Interval: 1.8044 - 2.0181 tonnes".
Script: `audit/repro/<ID>.py` (API call plus source assertions).

## Expected
Label the interval as 1σ, or show the 95 % CI (k=2): 1.6976 - 2.1250 t. Use one coverage factor everywhere. Use the same level thresholds in the badge, the legend and the backend.

## Actual
- The result panel shows a 68 % interval as the CI, about half the width of the 95 % CI the rest of the app reports.
- The Scope 2/3 "95 % CI" column uses 1.96, which differs by 2 % relative from the k=2 value shown elsewhere for the same record.
- An inventory at ±25 % gets a red "high" badge, while the legend and the backend category level call it "medium".

## Evidence
Repro output. Source lines are cited above.

## Root Cause
There is no shared convention for confidence level, coverage factor or level thresholds between components.

## Impact
Users are shown an uncertainty range that is too narrow on the result panel, and the pages disagree on confidence levels. The effect is cosmetic or misleading rather than a stored-data error.

## Affected Components
EmissionResult (Scope1/2/3 forms), Scope2Form and Scope3Form history tables, UncertaintyAssessment badge.

## Recommended Fix
Render `value ± 2·u·value` and label it "95 % CI (k=2)". Replace 1.96 with the shared constant. Use the backend-provided `level` or the same thresholds for the inventory badge.
