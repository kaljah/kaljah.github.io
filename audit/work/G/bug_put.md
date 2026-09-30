# BUG-XXX — Editing a Scope 1 record replaces its propagated 1σ uncertainty with the raw catalog EF half-width (95 %, EF-only); user_uncertainty is stored unpropagated

**Status:** Confirmed
**Severity:** High
**Category:** Uncertainty
**Discovered by:** Agent G (Uncertainty Auditor)

## Location
`new/server/routes/emissions.py` `update_emission()` ~L3571-3597. After `compute_emissions()` the code sets `record.uncertainty/_ch4/_n2o = factor_data["uncertainty"][gas]` (raw catalog value) and `user_uncertainty[g]/100`. It ignores the propagated `_full_api_res.results[gas].uncertainty` that POST (L3131-3153) and bulk upload (L838-858, background_processor L1808-1826) persist.
The same raw-EF pattern is used by `/api/emissions/import` (L3949: `factor_data["uncertainty"]["co2"]`, CO2 only, CH4/N2O left null). That path was found by code reading and was not executed.

## Reproduction
1. As admin, POST stationary_combustion / Natural Gas / 1000 m3 / default, year 2045.
2. GET `/api/dashboard/uncertainty?year=2045`.
3. PUT `/api/emissions/<id>` `{"recalculate": true}`. No input changes, so co2e is unchanged.
4. Repeat GET. Script: `audit/repro/<ID>.py`.

## Input
Natural Gas catalog EF uncertainty: CO2 0.05, CH4 0.20, N2O 0.20 (95 % half-widths). Tier-1 AD ±10 %.

## Expected
Stored values are unchanged by a no-op recalculation. By hand, u_CO2 (1σ) = √(0.025² + 0.05²) = 0.0559 and u_CH4 = u_N2O = 0.1118. The same holds for `user_uncertainty co2=50 %`: POST stores √(0.25² + 0.05²) = 0.2550, and PUT should store the same.

## Actual
- After POST: (0.0559, 0.1118, 0.1118). Dashboard ±22.36 %.
- After PUT: **(0.05, 0.20, 0.20)**. Dashboard **±40.0 %**, with CO2e unchanged.
- user_uncertainty 50 %: POST stores 0.2550, PUT stores **0.5000**. The dashboard then shows ±100 %.

## Evidence
Repro output above. The snapshot DB already holds 110 records with exactly (0.05, 0.20, 0.20). These are edited records whose uncertainty column now has 95 %/EF-only semantics, while the column is documented and consumed as a 1σ combined value (`models.py`, `dashboard.get_ef_uncertainty`, `CalculationDetails.jsx` "1σ Uncertainty").

## Root Cause
Two code paths persist different quantities in the same column. The POST/bulk paths store the 1σ combined EF+AD value from `propagate_uncertainty`. The PUT and `/import` paths store the unpropagated 95 % EF-only half-width, which omits the AD term and the /k conversion. Consumers then apply k=2 again.

## Impact
Any edit, including a no-op recalculation, changes a record's reported uncertainty with no change in data. The reported 95 % interval roughly doubles for EF-dominated gases (0.05 read as 1σ is 10 % at 95 %, against the correct 11.18 %; 0.20 read as 1σ is 40 %, against the correct 22.4 %). User-supplied uncertainties are doubled. Persisted values mix two incompatible semantics, which corrupts the Uncertainty page, the CSV/PDF outputs and CalculationDetails.

## Affected Components
PUT `/api/emissions/<id>`, POST `/api/emissions/import`, the `emissions.uncertainty*` columns, `/api/dashboard/uncertainty`, `/api/qaqc/dashboard`, `CalculationDetails.jsx`.

## Recommended Fix
In `update_emission` and `import_emissions`, persist `calculated_em["_full_api_res"]["results"][gas]["uncertainty"]`, as `add_emission` does, and drop the post-hoc `user_uncertainty/100` override (the dispatcher already propagates it). Back-fill the existing rows by recomputing them.
