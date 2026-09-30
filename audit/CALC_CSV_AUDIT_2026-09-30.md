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
