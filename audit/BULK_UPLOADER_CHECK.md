# Bulk uploader check (2026-09-29)

Scope: every file import the client offers (they all post to `POST /api/emissions/upload/start`, processed by `background_processor.py`):
- Scope 1 wizard (CSV and Excel templates, all tiers);
- Scope 2 and Scope 3 wizards (activity and spend);
- the column-mapping wizard for sources, production, mitigation, custom factors and facilities.

Method: the templates the app generates, and edge-case files, were uploaded through the API on a copy of the database. Results were compared with the manual form's calculation for the same inputs. The three scope wizards were then run in a browser on throwaway servers.

## Findings and fixes

### File reading and column mapping
| # | Problem | Fix |
|---|---|---|
| 1 | The Scope 1 CSV template's `process_type` column was mapped to the emission-source field `type`, so every template row failed with "Missing process type" | Mapping is per import type (`_MAP_BY_SCOPE`) |
| 2 | The Excel reader looked for a sheet named "Data Entry"; the template names it "📊 Data Entry", so the Facilities sheet was read as data | Data sheet found by name without the icon |
| 3 | Excel title rows were taken as the header row | Header = first row with at least two filled cells |
| 4 | Template tags and unit notes (`[T3-Tank] tank_gor`, `Bleed Rate (scf/hr)`, CamelCase `UnloadDepth`) never reached the calculators under their field names | `_canonical_header` adds the field name of every column |
| 5 | Tier 3 sheet values were merged by raw header text (not mapped) and by equipment ID only | Mapped like the data sheet; keyed by equipment ID and month |
| 6 | The CSV template's description row was imported as data (one error per file) | Skipped |
| 7 | A column list sent by a wizard replaced the automatic mapping, dropping every column the wizard does not list | Wizard choices override the automatic mapping |
| 8 | The delimiter sniffer read the description row ("a \| b") | Delimiter from the header line |
| 9 | `.xls` accepted and read as text; malformed `column_mapping` ignored; unknown import type accepted | 400 errors |

### Scope 1 rows
| # | Problem | Fix |
|---|---|---|
| 10 | Separate calculation code from the manual form: `factor_source` stored the fuel category ("gases"); no `ef_key`, OGMP level or uploader name; no fill-in of the catalog HHV | Rows go through `services.scope1_calc` (canonicalize, validate, resolve_factor, apply_result), as the manual form does |
| 11 | Invented defaults (CH4 85 %, CO2 2 %) were added to every row | Removed; Tier 3 methods ask for their inputs |
| 12 | Any fuel with any process: tank flashing + "Crude Oil" booked crude-oil combustion (433 t per 1,000 bbl) | Catalog factor must list the process in its `usage` (`check_factor_usage`) |
| 13 | Unknown process types were calculated by the generic path | Process key or form label required (`normalize_process_type`, labels kept in sync with the client by a test) |
| 14 | Compendium activity rows (pneumatics, loading, separators, well testing, glycol dehydrator, AGR) could not be named in a file | The row label in the fuel column (or `activity_key`) selects it |
| 15 | Per-hour / per-day factors and leak methods default to a full year (8,760 h) on a monthly record | The file must give the month's operating hours / days |
| 16 | Blank or text quantity was reported as "Invalid quantity" only for some cases | Missing / invalid quantity and unit are row errors |

### Calculation defects found through the templates (also affect manual entry)
| # | Problem | Fix |
|---|---|---|
| 17 | Operating temperature / pressure correction applied to volumes already at standard conditions (scf, Mscf, Sm3) and even to energy quantities: 50,000 scf at 300 psig gave 65.7 t instead of 3.07 t | Correction only for volumes in m3 / cf read at metering conditions |
| 18 | The combustion form labels these fields °F and psia but sent no unit; the engine read °C and psig (the placeholder 14.696 psia doubled the result) | Form sends `temp_unit` F and `press_unit` psia |
| 19 | Drilling used any quantity as drilling days (template: 500 m3 of mud -> 641 t) | Unit must be days (or wells at Tier 1) |

### Scope 2, Scope 3 and Manage Data rows
| # | Problem | Fix |
|---|---|---|
| 20 | Scope 2: blank or text consumption saved as a 0 t record | Positive number required |
| 21 | Scope 2 steam: own formula without the boiler CH4 / N2O added to the manual path | Uses `routes.scope2._calc_indirect_steam`; steam tonnes stored |
| 22 | Scope 2: no uncertainty stored | Same default as the manual form (`default_scope2_uncertainty`) |
| 23 | Scope 3: unparseable amount / factor reported as "Provide activity amount and emission factor" | Specific messages; NAICS `331110.0` (Excel number) accepted |
| 24 | JSON `/api/scope3/bulk-import`: default category 11, year 2024 / month 1, 0 t booked without a factor, admin uploads Verified | Same row validation as the file import; always Pending |
| 25 | JSON `/api/emissions/bulk-upload` (not used by the client) hard-deleted the reviewed record on overwrite | Audited overwrite back to Pending |
| 26 | Production: month 13, year 1850, negative and text volumes, unknown units accepted | Period and non-negative numbers validated; units must be convertible by the intensity KPIs |
| 27 | Mitigation: missing year set to 2024; text / negative quantities and bad dates silently accepted | Required year, validated numbers and dates |
| 28 | Facilities: in-file duplicates created twice; latitude / longitude out of range or text accepted; duplicate codes stopped the whole job | Duplicates and codes checked; coordinate ranges as the manual form |
| 29 | Sources: duplicates registered; any text stored as installation date | Duplicate and date checks |
| 30 | Reviewers notified "0 new records" when nothing was imported; fatal errors did not say whether rows were saved | Notification only when rows were imported; the message states the rows saved |

### Templates and client wizards
| # | Problem | Fix |
|---|---|---|
| 31 | Template example rows did not import (factor names not in the catalog, drilling in m3, dehydrator Tier 3 inputs the calculator no longer uses, fugitive screening of 350 leaking components for a full year, AGR slip 10 %, a Scope 2 steam row, completions rate unit documented as Mscf/day while the engine defaults to Mcf/hr); the "auto" template had Tier 3 rows without Tier 3 columns | Example rows rewritten and checked by hand; auto = Tier 3 columns; rate-unit, hours and leak-count columns added |
| 32 | Excel template: dropdowns and validations one column off (the "quantity" decimal rule sat on Factor Type, so typing "default" was refused); Tier 3 sheet rows referred to equipment not on the data sheet | Validations placed by column name; consistent examples |
| 33 | Scope 2 page: opening the bulk import crashed the page (`Scope2ImportWizard` not imported) | Import added |
| 34 | Wizards required Date and Year and Month together | Date or Year + Month (`utils/importMapping.js`) |
| 35 | Column auto-detection mapped one column to many fields ("Type" to every "... Type" field) | One column per field; exact names first |
| 36 | Scope 1 wizard offered process keys the server does not have (`tank_working_standing`, `fugitives_leaks`, `pneumatic_pump`) and Tier 3 fields no calculator reads | Keys and fields aligned with the server |
| 37 | Template samples: Scope 2 grid "National Grid" (unknown), Scope 3 without an emission factor column, custom factor 53.06 kg per scf | Corrected |

## Results

| Check | Result |
|---|---|
| Scope 1 CSV templates (tier 1 / 3 / auto) | 8 / 13 / 21 rows, all imported |
| Scope 1 Excel templates | Imported, including the Tier 3 sheet parameters |
| Bulk vs manual | Identical stored values for the same inputs: CO2e, gases, factor source, uncertainty, factor key |
| Backend tests | 1,762 passed, 0 failed (new file `tests/test_bulk_uploaders.py`, 19 tests) |
| Client tests | 36 passed, including the new `importMapping.test.js` |
| Browser, Scope 1 wizard | Date-only file: 2 rows imported, the crude-oil tank-flashing row skipped with its reason |
| Browser, Scope 2 wizard | Electricity 100 MWh on the Algerian grid gives 49.79 t; steam 50 MMBtu gives 3.32 t |
| Browser, Scope 3 wizard | Truck 10,000 t-km at 0.12841 kg gives 1.28 t; the row without a factor is skipped |

Test inputs changed because they relied on removed behaviour:
- **Drilling in m3:** Table 6-2 is per drilling day.
- **"Natural Gas" as a flare or vent factor:** the rows now use "Natural Gas (Flaring)" and "Natural Gas (Venting/Blowdown)".
- **Unloading row without CH4 content:** the old code used the invented 85 % default.
- **A misaligned CSV row.**
- **Production gas given in MWh.**

## Still open
- Manual forms show 8,760 h as the default operating time on monthly records (pneumatics, leaks). The bulk path now requires the month's hours, but the manual default is unchanged.
- Records imported before this change keep their stored values, for example rows booked with the injected 85 % CH4 or with the pressure correction on scf.
