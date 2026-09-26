# BUG-XXX — Meter (activity-data) and GC (composition) uncertainty inputs are accepted but silently ignored by every calculator

**Status:** Confirmed
**Severity:** Medium
**Category:** Uncertainty
**Discovered by:** Agent G (Uncertainty Auditor)

## Location
- `new/server/calculations/dispatcher.py` L242-257 stores `meter_uncertainty_pct` / `gc_uncertainty_pct` as `uncertainties["_activity_uncertainty"]` / `["_composition_uncertainty"]`.
- `calculations/uncertainty.py propagate_uncertainty()` reads them only from its `uncertainties_dict=` argument (L389-393).
- `grep -rn "uncertainties_dict" calculations/` finds **no** caller that passes it. Every `propagate_uncertainty(...)` call in combustion/vented/fugitive/midstream/indirect/stoichiometry/dispatcher omits it.

## Reproduction
1. POST `/api/emissions/` stationary_combustion / Natural Gas / 1000 m3 with no override. Then POST the same with `meter_uncertainty_pct: 40`, and with `meter_uncertainty_pct: 40, gc_uncertainty_pct: 30`.
2. Compare `emissions.uncertainty.co2` in each response.
Script: `audit/repro/<ID>.py`.

## Input
meter 40 % and GC 30 % (95 % half-widths, the same convention the dispatcher uses for `user_uncertainty`).

## Expected
Hand calculation (1σ = U95/2):
- meter 40 %: √(0.025² + 0.20²) = **0.2016**
- meter 40 % + GC 30 %: √(0.025² + 0.20² + 0.15²) = **0.2512**

## Actual
All three records store **0.0559**, the tier default (AD 10 %, EF 5 %). By contrast, `user_uncertainty` does work (50 % gives 0.2550).

## Evidence
Repro output: `expected 0.2016 actual 0.0559`, `expected 0.2512 actual 0.0559`.

## Root Cause
The dispatcher writes the overrides into the `uncertainties` dict. The calculators pass that dict's per-gas entries to `resolve_ef_uncertainty` but never pass the dict itself to `propagate_uncertainty(..., uncertainties_dict=uncertainties)`. As a result, `_activity_uncertainty` and `_composition_uncertainty` are dead.

## Impact
The Scope1Form "specific" mode fields (Meter Uncertainty %, GC Uncertainty %), the bulk-import columns `[Unc] meter_uncertainty_pct` / `gc_uncertainty_pct` (template text: "overrides Tier default"), and the ColumnMappingWizard/BulkImportModal mappings are no-ops. A user who records a poor meter (e.g. ±40 %) still gets the Tier default (±2 % for Tier 3, ±10 % for Tier 1). Their persisted and reported uncertainty is understated with no warning.

## Affected Components
All dispatcher calculators, the Scope1Form specific inputs, bulk import (`background_processor`, `/bulk-upload`), and the stored `emissions.uncertainty*` columns, and through them the Uncertainty dashboard.

## Recommended Fix
Pass `uncertainties_dict=uncertainties` in every `propagate_uncertainty` call, or have the dispatcher apply the overrides centrally after the calculator returns. Add a test asserting that a meter override changes `relative_uncertainty`.
