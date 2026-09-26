# BUG-XXX — Decree 21-330 flaring intensity (/flaring-summary) misconverts units: MMscf 1000× too low, scf/kscf 35× too high, UI "m³" gas production 28× too high; compliance verdict flips

**Status:** Confirmed
**Severity:** High
**Category:** Carbon Intensity
**Discovered by:** Agent E (Carbon-intensity auditor)

## Location
`new/server/routes/dashboard.py` `get_flaring_summary`:
- Numerator (flared volume) L2923-2931: `if "k" in unit ... elif "mscf" in unit: *28.3168 elif "mmscf" in unit: *28316.8 else: m3`
  - "mmscf" contains "mscf", so the MMscf branch is unreachable and 1 MMscf becomes 28.3 m3.
  - "kscf" matches `"k" in unit`, so it becomes qty×1000 m3 (1 kscf is 28.3 m3).
  - "scf" falls to the else branch and is treated as m3 (1 scf is 0.0283 m3). Any other unit containing "k" (e.g. "kg") is also treated as thousands of m3.
- Denominator (gas produced) L2986-2993: `elif "m3" in unit` does not match the client's gas unit value `"m³"` (ManageData.jsx L2701 `<option value="m³">`), so m³ volumes fall to the else branch and are multiplied by 28.3168 as if they were mscf.
- Prior-year YoY path L3020-3023 uses a third, different rule: only `"k" in unit`, and no mscf/mmscf conversion.
By contrast, `_query_intensity_stats` L1726-1736 handles "m³" and mmscf correctly, so the two endpoints disagree on the same data.

## Reproduction
1. Run `python audit/repro/BUG-XXX.py` (own db copy). As admin, it sends `POST /api/emissions/` three times: flaring at facility 13, 2026, with 1 mmscf, 1,000,000 scf and 1,000 kscf (each is 28,316.8 m3). The flaring engine accepts all three units (`dispatcher._normalize_volume`).
2. It then sends `POST /api/data/production` with facility 13, 2026-07, gas 1,000,000 with gas_unit "m³" (what the Manage Data form sends).
3. Each step is followed by `GET /api/dashboard/flaring-summary?year=2026&facilityId=13`.

## Input
The records above. Baseline: facility 13 in 2026 has 100,000 m3 flared and 134,733,458 m3 of gas produced.

## Expected
- Each flaring record adds +28,316.8 m3. Total flared = 184,950 m3.
- Gas produced increases by 1,000,000 m3, to 135,733,458 m3.
- Flaring intensity = 0.136%, "COMPLIANT (Under 1.00% Target)".

## Actual
- mmscf: +28.32 m3 (1000× too low)
- scf: +1,000,000 m3 (35.3× too high)
- kscf: +1,000,000 m3 (35.3× too high)
- Production in m³: +28,316,800 m3 to the denominator (28.3× too high)
- Final: `flaring_intensity_pct` 1.288, "EXCEEDS THRESHOLD (> 1.00%)"

## Evidence
`audit/work/E/repro_flare.py` output:
```
flared 1 mmscf: expected +28316.8 m3, actual +28.32 m3 MISMATCH
flared 1000000 scf: expected +28316.8 m3, actual +1000000.00 m3 MISMATCH
flared 1000 kscf: expected +28316.8 m3, actual +1000000.00 m3 MISMATCH
produced 1,000,000 m³ gas: expected +1,000,000 m3 denominator, actual +28,316,800 MISMATCH
final flaring_intensity_pct 1.288 EXCEEDS THRESHOLD (> 1.00%)
```
For the same m³ production row, `/intensity-stats` reports `total_gas_m3` +1,000,000, which is correct.

## Root Cause
Unit detection uses substring tests in the wrong order ("mscf" is checked before "mmscf", and any "k" means kilo-m3). It has no scf branch and does not recognise the "m³" spelling that the client stores. Three separate ad-hoc conversion tables exist, for the flaring-summary numerator, the denominator and the prior year.

## Impact
The regulatory Decree 21-330 Art. 9 flaring-intensity KPI on the Dashboard (DashboardEnhanced L1328-1345) and in the PDF report (ModernReportGenerator `/flaring-summary`) can be wrong by 1000× in either direction. The compliant or non-compliant verdict and the YoY change can be wrong. The volume shown per stream (routine, non-routine, safety) is wrong as well.

## Affected Components
`/api/dashboard/flaring-summary`, DashboardEnhanced "Decree 21-330 Flaring Intensity" bar and badge, ModernReportGenerator flaring section.

## Recommended Fix
Use one shared exact-match unit normaliser, e.g. `calculations/units.py`, for flared volume, produced gas and prior year. Match exact tokens (m3, m³, sm3, knm3, scf, mscf/mcf, mmscf, kscf). Reject or flag unknown units instead of defaulting to m3 or mscf.
