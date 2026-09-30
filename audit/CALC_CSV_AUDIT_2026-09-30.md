# Calculation and CSV uploader audit - 2026-09-30

Scope: the calculation engine (units, GWPs, catalog factors, dispatcher entry point), the shared
Scope 1 service, the Scope 2 / Scope 3 calculations, and the bulk CSV / Excel uploader
(`background_processor.py`).

Method:
- Constants checked against their definitions: GWP AR4 / AR5 / AR6 (server and client), volume,
  mass, energy, pressure and temperature conversions, standard conditions, gas densities.
- Metamorphic run over the whole factor catalog through `compute_emissions`: every factor with the
  same physical quantity in 4-7 equivalent units (volume, mass, energy), 2x the activity, and
  CO2e = CO2 + GWP x CH4 + GWP x N2O. Before the fixes: 539 differences in 35 factors; after: 0
  (110 valid factor / unit combinations; incompatible units are rejected).
- The uploader's number parser probed with locale formats (French, European, Excel, Unicode).
- Code reading of the Scope 1 / 2 / 3 bulk row processors against the manual routes.

## Fixed

| # | Where | Error | Size |
|---|-------|-------|------|
| 1 | `units.compute_scope3_co2e` | A method containing "EEIO" made every factor "per $1,000". EEIO records store kg CO2e **per USD**, so editing the amount of a bulk-imported spend record, or a Scope 3 CSV row with a `calculation_method` column, was 1000x low. | 1000x low |
| 2 | `units.compute_scope3_co2e` | The per-1,000 test ran before the numerator test: "t CO2e/1000 km" was read as kg per 1,000 km. "kg CO2e/1kWh" was read as per 1,000 ("1k"). | 1000x low |
| 3 | uploader, `;` CSV | French / European Excel writes `;`-separated CSV with a decimal comma. "1,500" (1.5) was stored as 1500. Now every number cell of a `;` file is read with a decimal comma ("1,5", "1.250,75", "12 345,6"); `,` files keep "1,500" = 1500. | 1000x high |
| 4 | Scope 1 catalog factors | Per-event, per-completion, per-well-year (29 factors: completions, workovers, liquids unloading) and per-bbl associated-gas-venting factors (6) used the amount whatever its unit: 1,000 m3 of a completion factor = 1,000 completions, 1,000 MMBtu of AGV = 1,000 bbl. A catalog row's activity must now have the factor's dimension (`services.scope1_calc.check_activity_unit`, on the manual create / edit, import and CSV paths). | unbounded |
| 5 | uploader, Scope 1 | `user_unc_co2/ch4/n2o` overwrote the stored propagated 1-sigma uncertainty with the raw input. They now feed the calculation as the manual form's `user_uncertainty` does, so both paths store the same value. | uncertainty |
| 6 | uploader, Scope 2 / 3 | "2%" uncertainty was 2.0 (200 %): the sign was dropped before the "above 2 = percent" test. An explicit % is now always a percentage. | 100x |
| 7 | `units.normalize_efficiency` | "1%" was 100 % and "0.5%" 50 % (same pattern). | 100x |
| 8 | uploader, Scope 2 | An unknown `source_type` ("district cooling", "purchased steam") was booked as electricity. Known aliases are mapped (purchased steam / heat -> indirect_steam; grid / market -> electricity), anything else is a row error, as on the manual route. | wrong source |
| 9 | `units` | 1 therm was 105.4804 MJ (the older US therm) next to the IT Btu of MMBtu: 10 therm != 1 MMBtu. Now 100,000 Btu = 105.505585262 MJ, as in `indirect.py`. | 0.02 % |

Regression tests: `new/server/tests/test_calc_audit_2026_09_30.py` (44). 26 of them fail on the
code before the fixes.

## Checked, no error found

- GWP tables (AR4 / AR5 / AR6, 100- and 20-year) on server and client.
- Volume, mass, energy, distance, freight, pressure and temperature conversions; Nm3 -> Sm3; CH4 /
  CO2 densities at 60 F / 14.696 psia.
- Every catalog factor: linear in the activity, CO2e identity holds, no silent zero.
- Scope 2 electricity (grid factor policy, kWh / MWh / GWh) and indirect steam (boiler efficiency,
  transmission loss, Table 4-6 CH4 / N2O).
- Uploader: blank or non-numeric quantity and blank unit are row errors (never 0 or an assumed unit);
  dates are range-checked; unknown facilities, processes and factors are row errors.

## Open (not changed)

- A bare `ton` / `tons` is a **short ton** (907 kg) everywhere, as the forms label it. In a CSV from
  an operator who means metric tonnes it is 9.3 % low. Rejecting it would break re-imports of the
  app's own records, which store `ton`; decide whether files should have to say `tonne` or `short_ton`.
- In a `,`-separated CSV, "1.500" is read as 1.5 (a European thousands separator is ambiguous
  there). Unchanged: Excel writes decimal-comma numbers only in `;` files.

# Part 2 - whole pipeline, per process (2026-09-30)

Each stage checked on a fresh database, with records entered through the real routes:

| Stage | Check | Result |
|-------|-------|--------|
| Calculation | 10 Scope 1 records (Tier 1 combustion by energy and by volume, flaring, completions, unloading, AGV, stationary and mobile diesel, chemical process, Tier 3 flaring), 2 Scope 2, 1 Scope 3 against hand calculations | all equal after fix 12 |
| Calculation, Tier 3 | flaring and combustion carbon balance by hand; the same gas at operating conditions in C / F / K / R and psig / barg / kPag / psia | equal (1e-6); standard-condition ratio exact |
| Calculation, Tier 2 | custom factors in kg/scf, bare "scf", kg/MMBtu + HHV (gas and liquid), t/bbl (in bbl and m3), g/m3, kg/tonne | all equal after fix 13 |
| Input | the same rows through the manual form and a CSV upload, field by field | identical after fix 10 (leap-year month share differs by design) |
| Edit | no-op save, 2x the amount, GWP AR5 -> AR6 -> AR5 | Scope 1 exact; Scope 2 steam fixed (10, 11) |
| Aggregation | dashboard summary (totals, source split, GWP-20), categorical breakdown, intensity, flaring, uncertainty, equity, Scope 3 summary, PDF export and report, OGMP workbook against the database | all reconcile |

## Fixed

| # | Where | Error | Size |
|---|-------|-------|------|
| 10 | `POST /api/scope2` steam | the amount was stored as steam tonnage whatever the unit (5,000 MMBtu -> steam_ton 5,000) | wrong stored activity |
| 11 | `PUT /api/scope2/<id>` steam | the edit recalculated from steam_ton as short tons (MMBtu entries 2x, tonne entries 0.907x), ignored an edited heat_mmbtu and reset the boiler efficiency to 80 %. Now from the delivered energy, keeping the record's own net efficiency unless new inputs are given. | 2x |
| 12 | dispatcher, Tier 3 flaring | no catalog factor -> an explicit N2O factor of 0; the Table 5-3 default now applies (as Tier 1). Golden cases F01 / F02 updated. | small (N2O) |
| 13 | custom factors | a kg/MMBtu factor of a liquid fuel (parent Diesel) was refused for gallons: its HHV was read per scf. The HHV basis now comes from the parent fuel. | blocked entry |
| 14 | `POST /api/scope3` | method label "Scope 3 - Category Category 4" | label |

Tests: `new/server/tests/test_pipeline_audit_2026_09_30.py` (7, all fail before the fixes).

## Open (not changed)

- A GWP switch recalculates Scope 1 only; stored Scope 2 values keep the CH4 / N2O of the grid
  factor and of the default steam boiler at the previous GWP (0.001 % of grid electricity here).
- `calculations.constants.invalidate_gwp_cache()` is never called; records created right after a
  switch were on the new GWP in the test, so no effect was observed.
- A custom kg/MMBtu factor without a parent fuel has its HHV in Btu/scf (as the form says); a liquid
  fuel needs its parent fuel set.

# Part 3 - Tier 3 engineering, Excel uploads, percent cells, production (2026-09-30)

Checked:
- One Tier 3 row per engineering process through the CSV uploader with the template's own headers,
  against hand calculations: pneumatics, tank flashing (with and without vapour control), blowdown,
  completions (rate x duration), liquids unloading (Eq. 6-3 geometry = Eq. 6-10 constant within its
  0.3 % rounding), AGR (CO2 removed, CH4 slip), drilling (Table 6-2), flaring with a single
  efficiency, Tier 3 combustion. All equal.
- Excel uploads: real date cells, numbers, percent-formatted cells; typed "%" in CSV cells.
- Production data, BOE, gas volumes, intensities; Scope 3 default factors (unit must match);
  overwrite on re-upload copies every calculated field.

## Fixed

| # | Where | Error | Size |
|---|-------|-------|------|
| 15 | uploader, Excel | a percent-formatted cell arrives as its fraction: 5 % in user_unc_co2, meter_uncertainty_pct or Scope 2 trans_loss was read as 0.05 % (steam 5 % low). Percent cells are now read as the text Excel shows ("5%"). | 100x on those inputs |
| 16 | uploader, Scope 1 | a typed "2.5%" in a Tier 3 column reached the calculator as text; the row failed with a raw conversion error. "X%" is now X in percentage columns (`*_pct`, `user_unc_*`) and X/100 elsewhere. | row refused |
| 17 | rate units on monthly records | "MMscf/d", "m3/hr", "Mscf/yr" were annualised (365 days) on monthly Tier 3 flaring / blowdown / AGR records, on production rows (intensities, methane loss rate, WEC) and on the flaring volume KPI. A rate now covers the record's month (`units.period_volume_m3`). | 11.8x (March) |

Tests: `new/server/tests/test_upload_percent_rates_2026_09_30.py` (7, all fail before the fixes).

## Open (not changed)

- Biogenic CO2: `Emission.co2_biogenic` is never set; CO2 from wood, biodiesel, ethanol and landfill
  gas is counted in Scope 1 CO2e, and the biogenic KPI is always 0. The GHG Protocol and ISO 14064-1
  report biomass CO2 outside the scopes; changing it changes the Scope 1 boundary.
- Two CH4 mass constants: 0.6785 kg/m3 (units.py) and 16.04 / 379.3 lb/scf (vented.py, 0.6774
  kg/m3); 0.16 % apart.
