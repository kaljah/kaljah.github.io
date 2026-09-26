# BUG-XXX — Tier 2 custom factors whose unit is not "kg/<unit>" are misapplied (Manage Data form stores a bare activity unit): tonne factors ×1000 (×10⁶ with kg activity), no volume/mass conversion at all; unknown units such as kg/TJ or kg/GJ are applied 1:1

**Status:** Confirmed
**Severity:** High
**Category:** Calculation
**Discovered by:** Agent C (Tier / Factor Auditor)

## Location
- `new/client/src/pages/ManageData.jsx` (~line 2241). The "Custom Factor" form stores `unit` as the bare activity unit (`scf | m³ | gal | bbl | kg | tonne`), with the values labelled "CO₂ Factor (kg/unit)".
- `QuickAddCustomFactorModal.jsx`, by contrast, stores `kg/scf`, `kg/MMBtu` and so on. Two conventions exist for the same column.
- `new/server/routes/custom_factors.py` create/update/import accept any `unit` string without validation.
- `new/server/calculations/dispatcher.py` `_generic_calculation()` (~1305-1420):
  - `f_denom` is `""` when the unit has no "/", so no activity→factor unit conversion is done.
  - `f_num == "tonne"` is read as a tonne numerator (`is_tonne`), so kg/tonne values are taken as t/tonne.
  - Any unrecognised unit (kg/GJ, kg/TJ, kg/MJ, t/TJ) is silently applied 1:1 to whatever the activity unit is.

## Reproduction
1. `python audit/repro/BUG-<ID>.py` (own db). It creates Manage-Data-style factors and Tier 2 records with `custom_factor_id`, as Scope1Form does.
2. Additional cases are in work/C/t3.py:
   - factor `kg/TJ` = 56,100 with activity 10 GJ;
   - factor `kg/GJ` = 56.1 with activity 1000 m3.

## Input / Expected / Actual (t CO2)
| Factor | Activity | Expected | Actual | Ratio |
|---|---|---|---|---|
| 3170 kg/tonne ("tonne") | 1 tonne | 3.17 | 3170 | ×1000 |
| 3170 kg/tonne ("tonne") | 1000 kg | 3.17 | 3,170,000 | ×10⁶ |
| 3.17 kg/kg ("kg") | 1 tonne | 3.17 | 0.00317 | ÷1000 |
| 10.21 kg/gal ("gal") | 1 bbl | 0.4288 | 0.01021 | ÷42 |
| 0.0541 kg/scf ("scf") | 1000 m3 | 1.9105 | 0.0541 | ÷35.3 |
| 1.9 kg/m3 ("m³") | 1000 scf | 0.0538 | 1.9 | ×35.3 |
| 56,100 kg/TJ | 10 GJ | 0.561 | 0.000561 | ÷1000 |
| 56.1 kg/GJ | 1000 m3 | needs HHV; should be rejected | 56.1 (m3 treated as GJ) | — |

## Evidence
- Every row of the repro is flagged WRONG, with HTTP 201 and calc_method `api2021_generic`.
- The ManageData `tonne` case is wrong even when the activity is in the same unit (×1000).
- The seed snapshot already contains a factor stored this way (custom_factors id 1, unit `scf`).

## Root Cause
There is no canonical unit format for custom factors, and the calculator does not validate units. It parses the numerator from the text before "/", and treats a unit without a "/" as having no denominator. Units it does not recognise fall through unconverted, with no error.

## Impact
Tier 2 emissions are wrong by factors of 35 up to 10⁶, depending on the unit chosen in the app's own Manage Data form. An IPCC-style factor (kg/TJ, kg/GJ) is off by 1000×, or is dimensionally meaningless without an error.

## Affected Components
- Manage Data custom-factor form, Reference Data, and custom factor import.
- Tier 2 manual entry and bulk upload.
- Any dashboard or report built on those records.

## Recommended Fix
- Store custom factors with an explicit numerator/denominator unit from a whitelist, and migrate bare units to `kg/<unit>`.
- In the calculator, reject factor units it cannot convert to the activity unit instead of applying them 1:1.
- Add GJ/TJ/MJ energy denominators, and require an HHV for energy ↔ volume conversion.
