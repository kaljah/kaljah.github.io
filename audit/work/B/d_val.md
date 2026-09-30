# BUG-XXX — Manual Scope 1 entry has no plausibility bound or QA flag: 9 test records (1e13 MMBtu gas, 1e15 t coal) make up about 99.99% of the snapshot's Scope 1 total (3.72e12 t Verified, 4.69e12 t Pending)

**Status:** Confirmed
**Severity:** Medium
**Category:** Emissions
**Discovered by:** Agent B (Emissions Auditor)

## Location
`new/server/routes/emissions.py` `add_emission()` (POST /api/emissions/, ~L2977-3060). It checks only for finite and non-negative values, and applies no upper bound or anomaly check. Compare `background_processor.py` ~L545-575, where bulk rows go through `anomaly_detector.check_scope1` and get `qa_flag`. Admin entries are auto-`Verified` (L3217-3225) with no review.

## Reproduction
1. As admin, send `POST /api/emissions/` with `{"process_type":"Combustion","source_type":"Combustion","facility_id":1,"year":2024,"month":7,"fuel":"Natural Gas","amount":1e13,"unit":"MMBtu"}`. The response is 201. The row is `status='Verified'`, `qa_flag=NULL`, `co2e_total=531,145,000,000` t.
2. Send the same request with `amount: 1e300`. The response is 201 with `totalCo2e = 5.3e298` t.

## Input
1e13 MMBtu natural gas at one facility in one month. That is about 70x world annual gas consumption (~1.5e11 MMBtu/yr).

## Expected
The request is rejected, or at least flagged (`qa_flag`) and kept out of auto-Verified status. The bulk path already applies a z-score anomaly check and a 1e7 outlier flag.

## Actual
The request is accepted and Verified, with no flag. On the snapshot DB this is what drives the dashboard lead:
- Scope 1 Verified sum = 3,723,125,709,415 t. Seven rows (ids 640, 645, 649, 658, 662, 667, 669) contribute 3,718,014,999,999.6 t, which is 99.86%. Each is "Admin test record", NG `quantity` 9,999,999,999,999 MMBtu (from `source_payload`), co2e = 531,145,000,000 t. Hand calc: 9.999999999999e12 x (53.06 + 0.001x28 + 0.0001x265) kg / 1000 = 5.31145e11 t. **The math is correct, but the input is absurd.**
- Scope 1 Pending sum = 4,686,441,566,610 t. Two rows (655, 675) contribute 4,686,441,120,000 t. Each is "User test emission", Coal `quantity` 1e15 tonnes, co2e = 2.343e12 t.
- `pending_stats` in `/api/dashboard/batch-all` = 114 Scope 1 + 14 Scope 2 = **128 records, totalCo2e 4.686e12 t**. The "4.69e15" in the lead is 4.69e12 t; the client renders it with `toLocaleString()`.

## Evidence
`audit/work/B/t3.py` output: `201 [{'status': 'Verified', 'qa_flag': None, 'co2e_total': 531145000000.0}]`, and a second 201 with `totalCo2e 5.311e+298`.
SQL: `select status,count(*),sum(co2e_total) from emissions group by status` gives Pending 114 / 4.686e12 and Verified 630 / 3.723e12. Without the 9 test rows: Verified is about 5.11e9 t and Pending about 446,610 t.

## Root Cause
Only `isfinite`/`>=0` checks are applied to quantity. There is no magnitude or statistical plausibility check on the manual create path, and admin-created rows skip review.

## Impact
One typo (extra zeros) or test entry through the UI/API is instantly Verified and dominates every Scope 1 total, intensity, SBTi trajectory and report. On the snapshot, the dashboard gross Scope 1+2 (3.7 trillion t) is wrong by about 3 orders of magnitude for this reason.

## Affected Components
POST /api/emissions/ (the Scope1Form and scope1/*Form.jsx save path), all dashboard, report and intensity aggregates.

## Recommended Fix
Run the same `anomaly_detector.check_scope1` / outlier threshold used in bulk upload on manual create and PUT. Set `qa_flag` and force `Pending` when flagged, even for admin. Also add a hard sanity cap per unit (e.g. co2e per record > 1e8 t rejected).
