# Tier 3 browser test — every Scope 1 process type (2026-09-28)

## Method

- Throwaway backend (port 5055) on a copy of the development database and a Vite dev server
  (port 5174); headless Chromium driven by Playwright, logged in as an admin test user.
- Every process in the Scope 1 process list was selected, switched to Tier 3, and every
  method switch was walked to record the fields (27 of 33 processes have a Tier 3).
- 51 submissions were made through the form with inputs taken from API Compendium 2021 exhibits
  where one exists, otherwise inputs simple enough to derive the result by hand from the stated
  equation. Each case carries a unique Equipment ID so the record can be traced.
- For every case three values were compared against the independent expectation: the POST
  response, the Recent Activity table row, and the `emissions` row in the database.
- Expected values use the Compendium convention (379.3 scf/lbmol, MW 16.04 / 44.01, 2,204.62 lb/t);
  the engine's gas densities differ by about 0.4 %.

POST response, table and database always agreed with each other: every defect below is in the
form payload or the engine, not in storage or display rounding.

## Results before fixes

### Wrong results or impossible to save

| # | Process / method | Observed | Expected | Cause |
|---|---|---|---|---|
| 1 | Well completions, Tier 3 metered (Ex 6-3) | rejected: 245,000,000 tCO2e (scf chosen); 246,000,000,000 tCO2e (default unit) | CH4 2.36, CO2 98.7 t | the form sends the metered volume as `calc_inputs.amount`, which the engine takes as the event count (BUG-012 mapping); the volume unit defaults to Mcf |
| 2 | Associated gas venting, rate x duration | CH4 4.227 t | 0.176 t | the field reads "Venting time (h)" but the form sends `duration_unit: "days"` (x 24) |
| 3 | Fugitives, Method 21 screening ranges | CH4 37.23 t, CO2 0.438 t for 5 valves | Table 7-26 factors | `fugitive_method: "method21"` falls through to the direct-measurement branch: 5 components read as 5 kg/h |
| 4 | Fugitives, Method 21 factors | gas valve 5.5E-05 / 0.045 kg TOC/h (cited "Table 7-15") | Table 7-26: 2.5E-05 / 9.8E-02 | wrong source table (7-15 is the Canadian oil-facility average table) |
| 5 | Fugitives, OGI leaker survey | 2.470 t CH4 (2 valve leakers) | Table 7-23: 2 x 7.7E-05 t/h x 8,760 = 1.349 t | leaker factors (0.141 kg CH4/h for valves) match no Compendium table; cited "Table 7-19 / W-1E" |
| 6 | Fugitives, correlation (Ex 7-5) | blocked: "Please enter a valid activity amount/quantity greater than 0" | 0.47 t | the client requires an amount the correlation form does not have |
| 7 | Fugitives, direct measurement | blocked unless the shown 0.5 is retyped; then CH4 3.723 t with 85 % and CO2 0.0438 t | 0.5 kg/h x 8,760 h x CH4 mass fraction of the entered stream | the shown rate and 78.8 mol % are not in form state; engine applies mol % as mass fraction and adds CO2 nobody entered |
| 8 | Routine / non-routine / safety flaring | section 3 shows "Select a process type" in every tier | volume form like "Flaring" | the form switch has no case for these process types |
| 9 | AGR throughput & CO2 in/out | CH4 6.532 t | slip 0.0004 mol CH4 / mol CO2 removed: 0.380 t | the field is "CH4 slip (mol/mol CO2)" but the engine applies it to all CH4 in the treated gas |
| 10 | Stationary combustion Tier 3, HHV only | saved a Verified record of 0 tCO2e for 800e6 scf | rejected (no composition, no factors) | Tier 3 is exempt from the zero-result check; the engine silently returns zeros |
| 11 | Storage tank working / breathing losses Tier 3 | 40.73 t each (identical to flashing) | not a flashing calculation | the working and breathing process types run the flashing (GOR) method: triple counting |
| 12 | Dehydrator Tier 3 (Ex 6-28 inputs) | 42.21 t CH4 | Compendium table method: 22.06 t | the "parametric solubility" formula S = 0.0032 P^0.96 exp(-0.0022 (T-60)) has no source in the Compendium; a flash tank is assumed that the form never asks about |

### Values shown on the form but not sent

| # | Process | Effect |
|---|---|---|
| 13 | Liquids unloading (all three methods) | blocked "Gas CH4 content (%) is required" while 80 % / 85 % is shown; CO2 shown (3 %) is not sent, so CO2 = 0 (Ex 6-8: 2.10 t expected) |
| 14 | Liquids unloading, well decompression | CO2 = 1 (mol %) read as the fraction 1.0 = 100 %: rejected |
| 15 | Venting (blowdown) | the unit select shows m3; the client converts the stored quantity as scf, the engine uses the raw volume in the shown unit: 83.8 ft3 stored as "83.8 m3", 83.8 m3 stored as 2.37 m3 |

### Table and record

| # | Issue |
|---|---|
| 16 | Process column shows raw keys ("associated_gas_venting"): the table reads `PROCESS_TYPES[k].label` but the values are strings |
| 17 | Activity/Fuel column shows stale Tier 1 selections on Tier 3 records; the AGV Tier 3 payload carried the Tier 1 specific factor 1.4 kg CH4/bbl |
| 18 | Records from the gas-volume / combustion methods store no quantity or unit (Quantity column "-") |
| 19 | Combustion Tier 3 with entered factors stores no uncertainty (table "—") |
| 20 | Inputs of a method tried earlier stay in the payload of the next method (OGI record carried correlation counts) |

### Working (within 0.5 % of the exhibit / hand value; POST = table = database)

Gas-volume methods on every process (measured, GOR, rate x days, actual T/P, vented and flared —
Ex 6-2, 6-5, 6-15, 6-22, 6-29), AGV total volume, AGR sour/sweet balance (Ex 6-17), combustion
entered factors / carbon content (Ex 4.5) / equipment basis (Ex 4.7, 4.8, turbine), flaring CH4-only
metered, flaring from VOC (Ex 5.2), blowdown with ft3 (Ex 6-25), pneumatic bleed rate, tank flashing
(Ex 6-19), mobile by distance (Ex 4.12), thermal oxidizer (Ex 5.3), unloading Eq 6-10 CH4 (Ex 6-8) and
Eq 6-11 (the PDF has the square root; the text extract dropped it).

## Fixes

| # | Fix | Where |
|---|---|---|
| 1 | Completions: `calc_inputs.amount` becomes the event count only when no Tier 3 flowback volume is given; Tier 3 events are explicit or 1 | `calculations/legacy_engine.py` |
| 2 | AGV Tier 3 sends `duration_unit: "hours"` (the field is in hours); oil production only for Tier 1 / 2; the record stores the vented volume (rate x hours) | `Scope1Form.jsx` |
| 3 | Fugitive Tier 3 routes on the explicit method; screening ranges have their own branch (counts below / at or above 10,000 ppmv; older one-value payloads still read) | `calculations/dispatcher.py` |
| 4 | Screening-range factors replaced by Table 7-26 (23 component / service rows, NA rows rejected); CH4 weight fraction of TOC defaults to Table C-1 by service (gas 0.920, light oil 0.613, heavy oil 0.942; water/oil must be entered) | `emission_factors_chapter7_onshore.py`, `calculations/fugitive_onshore.py` |
| 5 | Leaker survey = Table 7-23 whole-gas leaker factors (scf/h) x site CH4 / CO2 (81.6 mol % basis when no composition); no non-leaker term (the table has none) | same |
| 6 | Fugitive Tier 3 does not require a generic amount; the record amount / unit follows the method (components, leakers, measured rate) | `Scope1Form.jsx` |
| 7 | Direct measurement: volumetric units are whole gas x mole fractions (CH4 required); mass units are CH4 mass; CO2 only when entered; unknown / missing unit rejected. Tier 3 fugitive form rebuilt: every field is in form state (placeholders only), unsourced client factor tables removed | `fugitive_onshore.py`, `FugitivesForm.jsx` |
| 8 | Routine / non-routine / safety flaring use the flaring form (volume, HHV, CH4) in every tier | `Scope1Form.jsx`, `CombustionForm.jsx` |
| 9 | AGR: CH4 slip is a fraction of the inlet CH4 (label corrected); without a slip the Table 6-19 factor 0.0185 t CH4 / 10^6 scf applies (the 0.1 % default had no source); the form CO2 in / out are always percentages; outlet > inlet is rejected (was silently clamped) | `midstream.py`, `dispatcher.py`, `AGRForm.jsx` |
| 10 | Tier 3 fuel analysis without a gas composition or measured factors is rejected (was a Verified 0 tCO2e record) | `dispatcher.py` |
| 11 | Working / breathing losses: total hydrocarbon loss (AP-42 Ch. 7 or simulation) x vent CH4 / CO2 wt % (Section 6.3.9.3); flashing inputs are rejected for these process types | `vented_gas.py`, `dispatcher.py`, method choices |
| 12 | Dehydrator Tier 3: measured vent volume, or simulation (GRI-GLYCalc) / measured result less control (Section 6.3.8.1); the unsourced solubility model is rejected with guidance; Tier 1 keeps Tables 6-17/6-18/6-35/6-36 | `vented_gas.py`, `dispatcher.py`, method choices |
| 13 | Unloading forms: shown defaults replaced by empty inputs with "e.g." placeholders, so what is shown is what is sent | `UnloadingForm.jsx` |
| 14 | One percent / fraction decision per gas analysis (CH4 / CO2 / C2+ groups) in the legacy branches; well decompression = Eq 6-10 casing term with gauge pressure (0.37e-3 x D^2 x Depth x P psig, Exhibit 6-8); the former P_abs / 14.696 counted the gas left in the well and cited "Eq 6-3" | `dispatcher.py`, `vented.py`, `validation/reference_model/vented_processes.py` |
| 15 | Blowdown: the entered volume and the unit shown are sent as they are (the server converts) | `Scope1Form.jsx` |
| 16 | Process column shows the process name | `Scope1Form.jsx` |
| 17 / 20 | Form inputs reset when the process or tier changes; switching a calculation method clears the previous method fields; specific factors are sent only where their fields are shown | `Scope1Form.jsx`, `methodChoices.js`, `FugitivesForm.jsx` |
| 18 | A record without an activity amount stores the activity the engine used (gas volume, energy, fuel mass, TOC, hydrocarbon loss, volume released) | `services/scope1_calc.py`, `vented_gas.py` |
| 19 | A gas with emissions always gets an uncertainty (Tier default for the process when the calculator or factor gives none) | `services/scope1_calc.py` |
| - | An entered operating time of 0 h stays 0 (was silently 8,760 h) | `dispatcher.py` |

Tests changed (re-derived; reasons in the test docstrings):

- Seven unloading references (battery, differential, two qfull files, golden GOLD-A03 in
  `validation/golden_dataset/golden_cases.json` and `validation/expected_results/expected_results.json`)
  re-derived with the Eq 6-10 casing term; the blowdown references stay absolute (Exhibit 6-25).
- Four dehydrator tests of the removed solubility model now assert the rejection or the
  simulation / measured result path.
- `test_api2021_chapter7_onshore.py`: four Tier 3 tests marked "RC-17 open, to be re-derived" are
  re-derived from Tables 7-23 / 7-26 and pass (xfail removed).
- `test_audit_remediation.py::test_fugitive_screening_count_and_fraction` (failing since the baseline,
  unsourced "x 2.5 screening multiplier") re-derived from Table 7-26.
- New: `tests/test_tier3_browser_findings.py` (19 tests, one or more per finding).

## Re-run after the fixes (fresh database copy)

50 submissions through the form: the 46 cases above, plus blowdown in m3 and ft3, AGR with and
without a slip, measurement in kg CH4/h and scf/h, dehydrator measured volume and simulation
result; working / breathing losses and the dehydrator use their new methods; the HHV-only
combustion case must be rejected. Result: **50 of 50 as expected**. Every value is within the
exhibit / hand tolerance, POST = table = database, the HHV-only case is rejected with 422, the
Process column shows names, no stale Activity/Fuel, and every record with emissions has an
uncertainty and a quantity.

Selected values (engine / Compendium): completions 2.377 / 98.9 t (Ex 6-3: 2.36 / 98.7); AGV rate
0.1761 t CH4 on 10,800 scf; unloading Eq 6-10 20.44 / 2.10 t (Ex 6-8: 20.39 / 2.10); decompression
0.3409 t (Eq 6-10 term 0.3393); screening ranges 3.968 t; leaker survey 1.346 t (Table 7-23: 1.349);
correlation 0.470 t (Ex 7-5: 0.47); direct measurement 4.38 t; AGR slip 6.53 t, Table 6-19 18.5 t;
working losses 1.000 / 0.125 t; blowdown ft3 0.0109 t (Ex 6-25: 0.011); routine / non-routine /
safety flaring 6.148 / 829.7 t.

Suites: backend 1,628 passed; the only failures are the pre-existing GOLD-E01 and the throughput
SLA timing test (also fails on a clean HEAD checkout on this machine). `validation/`: 3 GWP-constant
failures, identical on a clean HEAD checkout. vitest 24/24, production build OK, lint: only the
pre-existing errors.

Not changed: Tier 2B fugitive xfails (outside Tier 3); Exhibit 4.4a differs by 1.8 % as recorded in
COMPENDIUM_EXHIBIT_CHECK.md.

## Remaining issues fixed (follow-up, 2026-09-28)

| Issue | Fix |
|---|---|
| 3 `validation/` GWP tests failing | The reference model, `ref_constants` and the tests held non-IPCC GWP-20 values (82.5 / 268). Corrected to AR5 WG1 Table 8.7 (CH4 84, N2O 264) and AR6 Table 7.15 (CH4 27.9 pairs with 81.2), as the app already used (BUG-013) |
| GOLD-E01 failing | A non-CH4 ("kg/hr", TOC) equipment factor is converted with the CH4 weight fraction (Eq 7-6) and rejected without one; it was used as pure CH4 |
| Tier 2B component leaks (4 xfail tests) | Bare component counts use Table 7-12 (EPA protocol, by component / service) scaled to the site CH4 mol % with CO2 from the whole-gas factor; the dispatcher's invented 0.0045 kg/hr fallback, the TOC x CO2-mole-fraction CO2 and the unsourced 0.85 default are removed; no component type is rejected. Form rebuilt (state-backed inputs, no client factor tables); the "select a fuel" check no longer blocks it. Browser: 100 gas valves at 70 % CH4 saved 2.2093 t = 100 x 2.94E-06 x 8,760 x 70/81.6 |
| Exhibit 4.4a 1.8 % high | `n2_content` was not read, the 98.4 % analysis was renormalised to 100 % (+1.63 % on every hydrocarbon). N2 / H2S aliases added: 42,748 vs 42,684 t (0.15 %, 379.3 scf/lbmol convention). The Gas analysis modal sent c1 as a fraction and CO2 as a percent and dropped C2+ / N2; it now sends the whole analysis in mol % with an explicit basis |
| Throughput SLA test | Throughput was measured under tracemalloc (profiler overhead); now measured on a separate untraced loop |
| Zero Tier 3 result | A real zero engineering result (e.g. 0 operating hours) is saved as zero instead of falling through to "request not understood" (entered specific factors keep their route) |
| Lint | Project-wide lint now has 0 errors (was 102): dead code, unused imports / state / catch bindings removed; set-state-in-effect uses that sync with URL / DOM / storage / server annotated; provider hooks allowed by config; Node globals for config and e2e files |
| Scope 3 import wizard crashed on open | `FIELD_GROUPS` was undefined after an unfinished split into activity / EEIO groups: the wizard now has an Activity / Spend (EEIO) switch and uploads with scope "3" or "3_eeio" (browser: opens, both modes) |
| PDF report: hard-coded figures | Chapter 7 (CAP) printed fixed tonnages and a fixed "NON-COMPLIANT" verdict; Chapter 4 fell back to another operator's 2025 production figures; Annex A printed fixed 2021-2025 production, flaring, decree status and intensity tables. All are now built from the records (verified CAP records, production records, per-year flaring / intensity endpoints); missing data shows "—". Gas BOE uses the platform definition (0.178 BOE/Mcf) instead of 0.0083 MMBOE/MMSm3 (+32 %). Subscript characters jsPDF cannot draw replaced. Browser: report generated, CAP rows 123.45 t NO2 / 67.89 t CO from the records, Hassi R'Mel NO2 250 vs 200 mg/Nm3 NON-COMPLIANT, no borrowed figures, no garbled glyphs |
| CAP compliance endpoint | A pollutant without a verified concentration is "NOT MEASURED" (was "COMPLIANT"); overall NON-COMPLIANT / COMPLIANT / NOT ASSESSED |
| Reports page, SBTi load | Load errors show the server message; the SBTi target load failure is shown instead of swallowed |

Suites: backend 1,639 passed, 0 failed, 0 xfailed; `validation/` 128 passed; vitest 24/24; build OK;
lint 0 errors (40 warnings, mostly `react-hooks/exhaustive-deps`).
