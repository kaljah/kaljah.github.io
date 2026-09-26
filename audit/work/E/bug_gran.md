# BUG-XXX — /granular-intensities (Master Report "Multi-Metric Intensities") divides all-facility emissions by only the facilities with granular MMboe fields, and fabricates NGSI methane (0.05 %) and saleable production (85 %)

**Status:** Confirmed
**Severity:** High
**Category:** Carbon Intensity
**Discovered by:** Agent E (Carbon-intensity auditor)

## Location
`new/server/routes/dashboard.py` `get_granular_intensities` L3075-3172:
- L3133 `total_boe = Σ total_production_mmboe×1e6`. The oil/gas fallback (L3138-3141) runs only when that sum is **0 for the whole query**. Rows without MMboe fields are therefore dropped whenever any row has them. The numerator (L3102-3121) is not restricted in the same way.
- L3140 fallback `gas_amount/5.8` ignores `gas_unit` (m³ or mmscf rows are treated as mscf) and `oil_unit`. It also uses 5.8 mscf/BOE, while `/intensity-stats` uses 0.178 BOE/mscf (5.62 mscf/BOE), so the two endpoints use different BOE definitions.
- L3143 `saleable_boe = total_boe × 0.85` when unrecorded: an invented "typical saleable fraction". The OGCI comparison (L3154, L3170) is made on this saleable value.
- L3150-3151: when `gross_gas_mmsm3` is empty, `methane_intensity_ngsi_wt_pct` returns the constant **0.05**, even though gas production exists in `gas_amount`.
- Client `new/client/src/utils/ModernReportGenerator.js` L1232-1242:
  - fallbacks 11.18 / 30.84 / 0.018
  - hard-coded "2.02 Sm³ / BOE" flaring row
  - fixed verdict texts "Far below global 0.20% methane intensity ceiling" and "COMPLIANT with ≤ 1.00% statutory ceiling", which are printed whatever the values are
- The endpoint has no activity, division or segment filter and no IT-role check.

## Reproduction
1. Run `python audit/repro/BUG-XXX.py` (own db copy).
2. `GET /api/dashboard/granular-intensities?year=2025` as admin.
3. Independently: Σ Verified S1+S2 2025 / Σ BOE per production row, using `total_production_mmboe` when it is present and otherwise oil + gas/5.8 with unit conversion.
4. `GET /api/dashboard/granular-intensities?year=2026&facilityId=13`.

## Input
Snapshot. 2025 has 254 production rows over 78 facilities. Only the 2 Berkine rows (169, 170) carry `total_production_mmboe`. The other 252 rows (61.7 M BOE of oil and gas) carry `oil_amount`/`gas_amount` only. Facility 13 in 2026: 4.76 M mscf gas (= 134.7 M m3) and 338.91 t CH4.

## Expected
- 2025 CI (total production) = 1,954,194 t × 1000 / 192,634,702 BOE = **10.14 kg CO2e/BOE**. The endpoint's own OGCI test on saleable volume gives about 17.9 kg/BOE.
- Facility 13, 2026, NGSI CH4 wt% = 338.91 t / (134.7 M m3 × 0.0008 t/m3) = **0.31 %**. That is above the 0.20 % ceiling the report cites.

## Actual
- 2025: `ci_by_total_production_kg_boe` = **14.93** over 130,930,000 BOE (Berkine only, 47 % too high). `ci_by_saleable_production_kg_boe` = 34.51, reported as "2.0x ABOVE TARGET".
- Facility 13, 2026: `methane_intensity_ngsi_wt_pct` = **0.05** (a constant). The report then prints "Far below global 0.20% methane intensity ceiling".
- Corporate 2026 also returns 0.05.

## Evidence
`audit/repro/BUG-XXX.py` output:
```
2025 CI total production: expected 10.14 kg/BOE over 192,634,702 BOE; actual 14.93 over 130,930,000 BOE MISMATCH
2026 fid13 NGSI CH4 wt%: gross gas 0 (gas recorded in mscf), CH4 338.91 t -> API returns fabricated 0.05 MISMATCH
```
Same data through `/intensity-stats?year=2025`: 10.86 kg/BOE. The two report sections contradict each other.

## Root Cause
The fallback is decided all-or-nothing on the aggregate instead of per row, and it is unit-blind. Missing inputs are replaced by invented constants (0.85 saleable, 0.05 % CH4) rather than being reported as "not available". The report template also hard-codes values and verdicts.

## Impact
The Master Report "Multi-Metric Intensities Matrix" (Chapter 8) shows a carbon intensity that is 47 % too high for 2025. It shows a methane intensity that is invented, and in the facility 13 case hides a breach of the 0.20 % threshold. It also shows a flaring Sm³/BOE value and compliance statements that do not come from data.

## Affected Components
`/api/dashboard/granular-intensities`, ModernReportGenerator.js Chapter 8 (and the flaring row in the compliance table, L1139, which falls back to 0.865).

## Recommended Fix
Compute BOE per production row: use `total_production_mmboe` when it is present, otherwise unit-converted oil + gas with a single shared BOE factor. Use the same factor in every endpoint. Return null / "insufficient data" instead of 0.85 or 0.05. For NGSI, fall back to `gas_amount` converted to m³. Compute the report's flaring Sm³/BOE and its verdict strings from data.
