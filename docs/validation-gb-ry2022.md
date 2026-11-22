# Real-inventory validation: Groupement Berkine HBNS & El Merk, RY 2022

Source: *HBNS & El Merk GHG Emissions Inventory for Reporting Year 2022*. Occidental of Algeria / Groupement Berkine,
2023-05-02, version 01. The report was computed in API SANGEA with AR4 GWPs.
Cases: `new/server/tests/gb_ry2022_cases.py`. Test: `new/server/tests/test_gb_inventory_ry2022.py` (65 tests).
Table: `python scripts/compare_gb_ry2022.py [--csv out.csv]`.

## Phase 1: calculation engine (2026-11-21)

Every source whose inputs the report prints was run through `compute_emissions` with AR4. The figures below are
platform results against the report's printed ones.

| Result | HBNS | El Merk |
|---|---|---|
| Site total, printed (t CO2e) | 1,061,968.60 | 1,153,205.84 |
| Platform: reproduced sources plus the report's figure for the implied ones | 1,065,241 (+0.31 %) | 1,156,554 (+0.29 %) |
| Stationary combustion | +0.42 % | +0.74 % |
| Flares | +0.07 % | -0.30 % |
| Venting | +0.04 % | +0.01 % |
| Mobile and aviation | -0.26 % | -0.11 % |
| Scope 2, report factor entered | -0.00 % | -0.00 % |

**Reproduced within 1.2 %:**
- every heater, turbine, generator, fuel-gas and flare source (CO2 and CH4)
- diesel engines (equipment method)
- aviation gasoline and on-road vehicles (Table 4-16)
- CPF maintenance venting (Table 6-39)
- fire suppressant
- Scope 2 with the report's 0.419 t/MWh

**Not reproducible from the report:** leaks, tanks and STP. The report does not print their inputs (equipment
counts, separator pressure, BOD5).

### Platform differences and bugs

| ID | Finding | Effect |
|---|---|---|
| GB-001 | Flare N2O default is Eq 5-6; SANGEA uses 3.716e-5 kg N2O per Nm3. The factor can be entered | N2O -87 to -91 % on every flare |
| GB-002 | The Tier 1 diesel row uses stationary CH4; the equipment method `ic_diesel` matches | CH4 -79 % |
| GB-003 | Catalog Algerian grid 0.4974 against IEA 2019 0.419. Location-based Scope 2 cannot take an entered grid factor | Scope 2 +18.7 % |
| GB-004 | NGSI gas ratio uses a fixed 1.235 MMBtu/Mcf; the report uses the gas HHV, which reproduces its figures | 0.131 % / 0.185 % against 0.141 % / 0.176 % |
| GB-005 | Per-BOE intensity divides by production without injected gas. Total production including injected gas is refused as "discordant" | 0.0319 / 0.0327 against 0.0147 / 0.0190 t/BOE |
| GB-006 | No facility-level leak shortcut for gas processing plants (per MMscf). The report's equipment-count method is supported; only its counts are missing | low (alternative method only) |
| GB-007 | No aviation gasoline catalog row (custom factor needed) | capability gap |
| GB-008 | Unit "liters" / "litres" refused (only l / L / liter) | entry friction |
| GB-009 | The provenance trail labels AR4 results as AR5 (GWP-005): `legacy_engine` does not pass `gwp_standard` to `dispatch()` | bug, label only |
| GB-010 | Gasoline 8.78 kg CO2/gal (Table C-1) against SANGEA 8.93 | -1.7 % |
| GB-011 | Fuel-gas CO2 +0.41 % at HBNS (Nm3 basis and rounding); El Merk varies by source, because SANGEA used monthly compositions | info |
| GB-012 to GB-015 | Venting CO2 basis, tank Table 6-26 row (+2.7 %), STP needs BOD5, turbine N2O +1.0 % | low / info |

### Errors in the report itself

- **GB-R01:** the column headers of Tables E-9 / 27 (JV partners, 2021 against 2022) are out of order.
- **GB-R02:** El Merk's processed gas (194,132.66 MMscf) is copied from HBNS. Its own gas (140,012 MMscf) reproduces
  the venting CH4 to 0.01 %.
- **GB-R03:** El Merk's on-road row (425.84 t) is the heavy-duty diesel alone. The module total does include the
  light-duty vehicles.
- **GB-R04:** a duplicate "Flare – AP" row appears under Miscellaneous.
- **GB-R05:** HBNS's gas-production leak row shows the CO2 of another row.
- **GB-R06:** typos "26,29.75" and "136,270,00".
- **GB-R07:** Table 13 has 8 headers over 7 columns.
- **GB-R08:** the EMK "HP" well-site flare was computed with the fuel-gas composition.
- **GB-R09:** Appendix B BOE differs from Table 5.
- **GB-R10:** the HBNS STP row's CO2e does not equal its gases at AR4.
- **GB-R11:** the report names both SANGEA 4 and SANGEA 5.

The full tracker with evidence and code locations is `GB_VALIDATION_RY2022/FINDINGS.csv` (git-ignored working
folder).

## Phase 2: CSV upload (2026-11-21)

Driver: `new/server/scripts/gb_ry2022_phase2_csv.py --db <new sqlite file> --out <folder>`. It runs on a throw-away
SQLite database, seeds two admins with `seed_admin.py`, then works only through the HTTP API (CSRF on), as the
import wizard does:
- settings (AR4, operational control)
- facilities, emission sources, production and custom factors (with approval by the second admin)
- Scope 1 (52 rows) and Scope 2 (2 rows)
- reading back the records, the dashboard summary and the intensity figures

Comparison: `scripts/gb_ry2022_phase2_compare.py <folder>`.

**Stored values against the engine:**
- **Match:** combustion CO2 and CH4, flares (CO2, CH4), venting, diesel engines (equipment method through extra
  columns), on-road vehicles and fire suppressant.
- **Differences:**
  - heater N2O −64 % (catalog row, GB-017)
  - aviation CH4 / N2O −96 / −92 % (Table 4-16 ignored at Tier 2, GB-020)
  - Scope 2 +18.7 % (catalog grid only for location-based, GB-021)
  - flare N2O, still −86 % against the report (GB-019)

**Bugs found:**
- GB-016: custom factors imported by file are stored Approved, bypassing maker-checker.
- GB-022: the production consistency error prints 1.3 % for a 128 % difference.
- GB-023: the venting throughput is counted as vented gas, so marketed gas = 0 and the loss rate is blank.
- GB-026: the template's "20%" salt content is refused.
- GB-029, GB-030: misleading import feedback.

**Gaps:**
- GB-024: NGSI ignores the site gas CH4 content.
- GB-028: no JV partner entry.
- GB-031: template columns are missing for methods that work.
- GB-032: there is no annual period.

**Data-entry friction:**
- GB-027: an equity share under 50 % silently sets the facility to non-operated.
- GB-033: a second approver needs `seed_admin.py`.

**Confirmed:** GB-034, the STP CO2 reproduces exactly with BOD5 25 mg/L.

## Phase 3: browser (2026-11-21)

Fresh SQLite database, two admins from `seed_admin.py`, backend `python app.py` and frontend `npm run dev`, driven
in Chrome (DevTools protocol).

**Done by hand in the browser:**
- Settings: GWP AR4.
- Regions: HBNS and El Merk.
- JV share: TotalEnergies 10.6 %. It is the only real partner in the list.
- Production: 2022 for both sites.
- Custom factor: aviation gasoline per litre, approved by the second admin.
- Scope 1 forms, one record per method:
  - heater
  - turbine
  - flare with the gas analysis
  - diesel engine (equipment basis)
  - Table 6-39 venting
  - LD gasoline vehicle
  - aviation (custom factor)
- Scope 2 form for HBNS.

**Through the browser wizards:**
- The other 45 Scope 1 rows (Phase 2 file).
- El Merk Scope 2.

Stored values: `GB_VALIDATION_RY2022/phase3/`.

**Parity between the three pipelines:**
- **Match:** diesel engine, vehicles, aviation and Scope 2 are identical in all three. Heater and turbine through the
  form differ by -0.20 % CO2 (C7 / C8 lumped into C6+ in the calculator, GB-051). Heater N2O through the form matches
  the report exactly (equipment factors can be typed).
- **Differ:**
  - GB-035: the flare calculator applies 96.5 % to CO2 and CH4 and ignores the entered efficiencies (CH4 +75 %).
  - GB-036: a flare without the calculator gets CO2 from methane only (-54 %).
  - GB-037: venting has no gas content field (CH4 +27 %).

**Full manual entry (second run, fresh database):**

Every source that can be entered through the forms was typed by hand: 52 Scope 1 records and 2 Scope 2 records.
This included regions, production, JV shares and the custom factor (approved by the second admin).

| Site | Printed (t CO2e) | Browser (t CO2e) | Difference |
|---|---|---|---|
| HBNS | 1,061,968.60 | 1,044,350.90 | -1.66 % |
| El Merk | 1,153,205.84 | 1,114,663.03 | -3.34 % |

**Missing**, because the forms cannot take them:
- equipment leaks (no counts printed)
- fire suppressant
- STP

**Above the report:**
- Scope 2: +10.7 kt (HBNS) and +26.5 kt (El Merk), from the catalog grid factor.
- Venting CH4: +27 % (HBNS) and +11 % (El Merk), because there is no gas content field.

**Matching:**
- Flares match within 0.5 % once the calculator's Oxidation Factor is set to 0.98 by hand (its default is 0.965,
  GB-035), and flare N2O typed per m3 matches the report on all 18 flares.
- El Merk combustion equals the engine. HBNS is -0.20 % (C7 / C8 lumped).

New findings: GB-056 to GB-061.

**Gaps and bugs:**
- GB-038: no Nm3 unit.
- GB-039: the annual production option is refused, and total production is silently ignored.
- GB-041: the facility form has no country.
- GB-044: the methane page says "Compliant" without a loss rate.
- GB-045: no fire suppression or STP process in the form.
- GB-040, GB-042, GB-043, GB-046 to GB-051, GB-053 to GB-055: UI, accessibility and labelling issues.

## Re-run after the fixes (2026-11-21)

- **Engine:** the validation suite (`tests/test_gb_inventory_ry2022.py`, 72 checks) passes. The site totals are
  unchanged within 0.3 %. Entering SANGEA's flare N2O factor (`n2o_factor` 3.716e-5 kg/Nm3) reproduces the report.
- **CSV import (Phase 2 script, fresh database):**
  - 52 Scope 1 and 2 Scope 2 rows were imported, with no row refused.
  - Every reproduced source now equals the engine result exactly: HBNS 1,029,672.4 t and El Merk 1,085,906.0 t
    CO2e.
  - The heaters' N2O had been -64 % in the CSV because the file could not carry the equipment factors. It now
    matches, using the `ch4_factor` / `n2o_factor` columns (GB-017).
  - The custom factor import needs a source and goes through approval (GB-016).
- **Browser (fresh database):**
  - A facility was saved with its own gas analysis (68.4 mol % CH4, 1,362.97 Btu/scf) and read back in the edit form.
  - A JV partner (Sonatrach) was added and another archived; the archived partner is no longer offered for shares.
  - An IEA 2019 Algeria grid factor was added, approved by the admin, and is offered in the Scope 2 grid list.
  - A wastewater record (aerobic, 1,000 m3 at 25 mg/L BOD5) was saved through the new form: 0.04911 t CO2, as by
    hand.
  - HBNS 136,270 MWh in 2022 on the Algerian grid gives 57,163.9 t CO2e location-based at AR5. That is the IEA 2019
    vintage, equal to the report's 57,165.28 t at AR4.
  - One form bug was found and fixed in the run: the wastewater form did not set the record's unit, so the save was
    refused with "Please select a unit".

### Browser import re-run (2026-11-22)

The Phase 2 files were uploaded through the import wizards on a fresh database (regions, custom factor with approval,
production, Scope 1 with tiers per row, Scope 2). All 52 Scope 1 and 2 Scope 2 rows were stored, and each one equals the
CSV/API run record for record: Scope 1 1,916,515.4 t CO2e, Scope 2 location-based 57,165.20 / 141,897.80 t (AR4). The
production file whose total includes reinjected gas was accepted (GB-022).

One gap was found and fixed. The production wizard did not recognise the `facility_name` and `date` columns that the
server reads, so the required fields stayed unmapped. Its template now uses them, adds the routine / non-routine /
safety flared columns, and has a sample row that lines up with its columns again.
