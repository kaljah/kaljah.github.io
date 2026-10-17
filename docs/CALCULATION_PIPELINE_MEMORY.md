# Calculation pipeline memory map

Written from the code (not from older docs). Server paths are under `new/server/`. Update it when a path below changes.

## 1. Entry points and who calls what

| Input path | Route / function | Row processing | Calculation | Storage |
|---|---|---|---|---|
| Scope 1 single record | `POST /api/emissions/` (`routes/emissions.py`) | `services/scope1_calc`: `canonicalize` → `validate_activity` → `resolve_factor` | `calculations.legacy_engine.compute_emissions` → `CalculationDispatcher.dispatch` (legacy factor math as fallback) | `apply_result` |
| Scope 1 file (CSV/XLSX) | `POST /api/emissions/upload/start` (+ `/upload/check` dry run, `/upload/status/<id>`, `/upload/errors/<id>`) | `background_processor._process_row` | same | `apply_result` |
| Scope 1 JSON | `POST /api/emissions/import` | own loop, same `scope1_calc` functions | same | `apply_result` |
| Scope 1 legacy JSON | `POST /api/emissions/bulk-upload` (preview / `confirm`) | **delegates to `_process_row`** (since this audit) | same | `apply_result` |
| Scope 2 single | `POST /api/scope2` | inline in `routes/scope2.py` | `resolve_electricity_factor`, `_calc_indirect_steam`, `_calc_cogen_allocation`, cooling inline (no `compute_emissions`) | `Scope2Emission` |
| Scope 2 file / JSON | `/upload/start` scope `2`; `POST /api/scope2/bulk-import` (electricity only, field `consumption`) | `background_processor._process_row_scope2` | the same helpers | `Scope2Emission` |
| Scope 3 single | `POST /api/scope3` (needs an emission factor; the form fills the catalog factor in) | inline | `compute_scope3_co2e` (`calculations/units.py`) | `Scope3Emission` |
| Scope 3 file / JSON | `/upload/start` scope `3`; `POST /api/scope3/bulk-import` (calls `_process_row_scope3`) | looks the factor up with `scope3_activity_factor` when none is given | same | `Scope3Emission` |

Review: `routes/emissions_review.py` (`approve/<id>`, `reject/<id>`, `approve/batch` with `{by_scope:{"1":[ids],...}}`). Statuses `Pending` → `Verified` / `Rejected`; a maker cannot approve their own record. Admin entries are `Verified` immediately. Audit: `GET /api/audit/verify-chain`. Equity: `GET /api/equity/allocation` (Verified Scope 1 + 2 times the effective share). Intensity: `/api/dashboard/intensity-stats` (kg CO2e per BOE). Uncertainty: `/api/dashboard/uncertainty` (95 %, k = 2; IPCC Approach 1 with factor correlation, `services/inventory_uncertainty.py`).

## 2. Calculation engine facts

- Process types: `process_categories.PROCESS_TYPES` has 29 keys; the dispatcher accepts more aliases (`indirect_steam`, `cogen_allocation`, `hydrogen_plant`/`smr_hydrogen`, `mud_degassing`, `vented_gas`, `well_testing`, `workovers`, `tank_*`, `fugitive_*`). There is no fixed table of 25.
- `dispatcher._dispatch_impl` is an `if/elif` chain; bodies live in `dispatcher_branches_{combustion,venting,fugitive}.py`.
- Compendium activity rows (`calculations/activity_factors.ACTIVITY_FACTORS`, 105 rows) are selected by `activity_key`; the file upload also accepts the row label in the Fuel column.
- Fuel catalog: `emission_factors.API_FACTORS` (181 entries; `usage` lists the processes a factor applies to).
- Shares (`dispatcher._parse_fraction_value`): `50%`, `0.5` and `50` are all 0.5; a value above 1 is a percentage. **Out of 0–100 % now raises `ValueError`** (150 % used to pass as 1.5; a negative share was clamped to 0).
- CCS capture (`ccs_capture_rate` / `capture_rate`, a 0-100 % share): `CalculationDispatcher.dispatch` applies it to **every** process (`_apply_capture`: the CO2 value and its bounds are scaled, the total loses only the captured CO2; CH4 and N2O are unchanged), and `compute_emissions` applies it on its factor-math fallbacks (custom factor, entered Tier 3 factor). Files take it as a column (`CCS Capture Rate`, `60%` works). Out of 0-100 % is refused.
- Hydrogen: Table 6-51, 13.41 t CO2 per 10^6 scf H2; tonnes of H2 → scf with 2204.62 lb/t ÷ 2.016 lb/lbmol × 379.3 scf/lbmol.
- Nitric acid: N2O kg = tonnes × EF × (1 − abatement); defaults 9 kg/t (nitric), 300 kg/t (adipic); abatement above 1 is read as a percentage.
- GWP: `calculations/constants.py` `GWP_AR4/AR5/AR6` (100-year CH4 25 / 28 / 29.8, N2O 298 / 265 / 273; 20-year CH4 72 / 84 / 82.5, N2O 289 / 264 / 273). Standards are `AR4`, `AR5`, `AR6` with `horizon` "100" or "20"; there is no "AR5-CC" or "AR6-20" key. The organisation-wide standard comes from `/api/auth/settings` (`gwp_standard`).
- Units: `calculations/units.convert` (legacy `CONVERSIONS` table first, then the dimension maps in `ALL_DIMENSION_MAPS`). Client `utils/hhv.ts` uses the same factors (parity test `src/__tests__/hhvParity.test.ts`).
- Uncertainty: `propagate_uncertainty` (k = 2.0), `srss_inventory` (quadrature over total), `combine_uncertainties_product/sum`; there are no `aggregate_unc_*` functions.

## 3. Intentional differences between paths (not bugs)

- A bare `ton` / `tons` unit is refused everywhere (`scope1_calc.validate_activity`, the Scope 2 steam calculation, files): write `short_ton` (2,000 lb) or `tonne`. The Scope 1 forms send `short_ton` (label "short ton"). The calculators themselves still read `ton` as the short ton.
- Single Scope 1 uses `activity_key` / `activity_hours`; files use the activity label in Fuel and an "Operating Hours" column.
- Admin uploads are `Verified`, others `Pending` (`bulk_status_fields`); the single form uses `initial_record_status`.
- Files take a per-file `decimal_mark`; JSON routes take numbers as given.
- The JSON Scope 2 import is electricity only.

## 4. Divergences found by the parity tests and fixed

1. **Legacy `/bulk-upload`** had its own factor lookup, Tier-3 detection and uncertainty code: it stored a default N2O uncertainty (0.15) others leave empty, skipped `ef_used_*` and uncertainty components, did not resolve activity labels (43 catalog rows rejected), and accepted LNG factors for the wrong process. It now runs every row through `_process_row`.
2. **Scope 2 JSON import** stored the market-based figure as `co2e` for rows with an instrument; the form, the edit and the file store the location-based figure (market is in `co2e_market_based`). Fixed to match.
3. **Scope 3 file / JSON import** left `calculation_method` empty; the form stores `Scope 3 - Category N`. Fixed.
4. **Share parsing** accepted 150 % (a 150 % capture rate produced negative CO2e) and clamped negatives to 0. Now refused.
5. **Gallon conversions** `m3_to_gal` and `l_to_gal` were rounded to six digits and were not the reciprocal of `gal_to_m3` / `gal_to_l` (1.4e-9 round-trip error). Now exact.
6. **Client `hhv.ts`** used constants rounded to 6 digits (up to 1.2e-6 off the server). Now the server's factors.

## 5. Test index (new in this audit)

- `tests/test_bulk_upload_pipeline_parity.py`: four Scope 1 paths, representative rows.
- `tests/test_bulk_catalog_parity.py`: every catalog fuel and activity row through single / file / JSON / legacy (200 of 280 candidates are valid; all four paths accept the same set and store identical values).
- `tests/test_scope2_scope3_parity.py`: Scope 2 (kWh, MWh, supplier factor, REC, market factor, steam) and all 57 Scope 3 catalog rows.
- `tests/test_bulk_edge_cases.py`: GWP standard in batch, custom factor, number and percent formats, invalid-row isolation, dry run, outlier.
- `tests/test_template_roundtrip.py`: CSV and XLSX templates (all tiers) re-dated and uploaded; no column dropped.
- `tests/test_full_pipeline_e2e.py`: facilities, equity, maker uploads (single, CSV, XLSX, JSON, Scope 2, Scope 3), self-approval blocked, reject + approve, audit chain, dashboards, equity, intensity, uncertainty, export.
- `tests/test_calc_gap_matrix.py`: nitric/adipic acid, hydrogen + capture, share parsing, unit round trips (every pair in every dimension map), GWP horizons, uncertainty.
- Client: `src/__tests__/hhvParity.test.ts`.
- `tests/test_scope1_entry_matrix.py` (2026-10-16): admin / superuser / user through the single POST, JSON import and file upload, Tiers 1-3, all-pairs over quantity boundaries, month, year bounds and facility (104 rows, 331/331 pairs, every case x role x path triple). Oracles: the admin's single POST of the same input and, where the tables give one, the hand value. Also out-of-region refusal on every path, 27 invalid single-entry rules with no record or audit entry left behind, mixed valid / invalid files and JSON batches, duplicates, drafts. `SCOPE1_VOLUME_ROWS=10000` runs 10,000 unique file rows per role (opt-in). Cases live in `tests/scope1_matrix_data.py`; `scripts/gen_scope1_test_data.py` writes the same cases as files for manual / e2e testing.
- `tests/test_scope1_coverage_gaps.py` (2026-10-16, from a branch-coverage run of the whole suite): every unit the import template offers is accepted by some row; the record lifecycle for every account x owner x status x region x action (864 cases: edit, delete, approve, reject); associated-gas input checks; statistical outlier and failed-check review; plausibility bounds on entry and edit; goal notifications; record list and export filters and region scope; review queue scope; Excel Tier 3 parameter sheets; upload request checks; file / JSON / legacy-upload refusals; custom factor edit, reject, archive and import; QA/QC resolve; a null `factor_source`.

## 6. Known limits

- Catalog parity covers the 200 rows whose guessed unit is valid; the rest are rejected identically by every path.
- Scope 2 and Scope 3 do not go through `compute_emissions`, so engine-level checks for them are in their own routes/helpers.
- The full-year dashboards (`ogmp`, `sbti`, flaring) are only smoke-checked in the end-to-end flow.

## 7. Later changes in this audit

- CCS capture now applies to all processes (it only worked for the hydrogen plant).
- Bare `ton` refused on the API (forms now send `short_ton`).
- `scripts/loc_baseline.json` was reset to the current sizes (46 files had grown past it in earlier commits).
- Entered Tier 3 factors (`specific_factors`) were ignored whenever a catalog fuel was also sent (the form always sends it): the dispatcher answered first with the catalog factor (combustion), or refused the record for missing engineering inputs (flaring: `c1`; venting: `blowdown_pressure`). `compute_emissions` now skips the dispatcher when entered factors are present (`tests/test_tier3_browser_findings.py::test_12`). Records saved before 2026-10-16 with entered factors carry catalog values; recalculate them.
- The dispatcher read `factor_source` with a default that only applied when the key was absent: a stored or sent null (169 of 355 records in the development database, from older imports) was calculated as Tier 3, so editing such a record's quantity was refused. A null is now Tier 1.
- Tier 3 completions accept Nm3 (converted with `NM3_TO_SM3`). The import template no longer offers units no calculator accepts: stoichiometry takes masses only, associated-gas rates go in `oil_production` / `oil_unit`, dehydrators have no `units` activity.
- Unreachable calculators (no dispatcher route; only `tests/test_vented_downstream_compendium.py` uses some): `WellTestingCalculator`, `CoalSeamDrillingCalculator` (`vented_exploration.py`), and the refining catalyst regeneration, coker, coke calcining, sulfur recovery, petrochemical, fire suppression and asphalt blowing calculators in `vented_downstream.py` (asphalt blowing and chemicals go to `StoichiometricCalculator`).
- Second pass (2026-10-16, `tests/test_scope1_residual.py`, `tests/test_vented_exploration_compendium.py`):
  - Numeric method inputs are checked centrally in `services/scope1_calc.validate_activity` (every path): a finite number, never a boolean; HHV, density and z-factor > 0; contents, compositions and efficiencies 0-100 %; counts, hours, rates and volumes >= 0; only temperatures, gauge pressure and API gravity may be negative. A negative HHV or operating hours stored negative emissions, 15 other negative inputs were accepted, and text reached the user as a raw Python error.
  - Zero activity is zero: the dispatcher's all-zero result is accepted when the amount is 0 (it fell through to the factor math, which refused drilling, pneumatics and component fugitives), and an entered 0 completions is 0 events (it became 1: a month without completions stored hundreds of tonnes). Tier 3 rows whose activity is a method input (unloading events, pneumatic device count, screening counts) still calculate from that input when quantity is 0.
  - Approve-all / reject-all (`scope: "all"`, the batch review wizard) answered 400 "Invalid scope: cap" since CAP records were removed from the maker-checker; batches now use `maker_checker.RECORD_TYPES`. A batch body naming no records is refused (400) instead of answering success.
  - PostgreSQL: two concurrent sign-ins of one account deadlocked (`users.last_login` autoflushed before the LOGIN audit row, so the user row and the audit-chain advisory lock were taken in opposite orders); `last_login` is now set just before the commit. Found with `tests/test_stress_concurrency.py` on PostgreSQL 16; the whole suite passes there.
  - `WellTestingCalculator` raised NameError (missing `normalize_efficiency` import); it and `CoalSeamDrillingCalculator` have no dispatcher route but are now tested against sections 6.2.2 / 6.2.4.
