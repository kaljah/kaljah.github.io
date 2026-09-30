# Upload scenario audit (2026-09-29), no fixes

## Method
- **Data:** a copy of the live database; the live database was not touched.
- **Uploads:** everything went through the browser UI: the Manage Data wizard and the Scope 1, Scope 2 and Scope 3 (activity and spend) wizards.
- **Records:** approved by a second admin through the Pending Review screen.
- **Expected values:** derived independently from the catalog / source factors, my own unit conversions and hand formulas for Tier 3, with AR5 GWPs (CH4 28, N2O 265).
- **Checked against:**
  - the stored records;
  - every row of the Scope 1, 2 and 3 record tables, scraped from the UI;
  - the dashboard totals, for all facilities and per facility.

| File | Rows | Imported | Rejected |
|---|---|---|---|
| Facilities (3 regions) | 5 | 3 | 2 (bad latitude, duplicate) |
| Custom factors | 6 | 5 | 1 (no factor) |
| Production | 16 | 14 | 2 (month 13, negative) |
| Sources | 5 | blocked by the wizard (bug 8); 3 with extra columns | 2 (duplicate, bad date) |
| Mitigation | 4 | 2 | 2 (no year, end before start) |
| Scope 1: every process, Tier 1 (all catalog fuels x units, 104 Compendium activity rows), Tier 2 (5 custom factors x units), Tier 3 (every method x units), invalid rows | 511 | 493 | 18 (all expected) |
| Scope 1 batch 2: date formats, facility by ID / case / region, padding, number formats, Nm3, duplicate, year range | 18 | 13 | 5 (all expected) |
| Scope 2: all 61 grids x kWh / MWh / GWh, supplier and 0 factors, steam in 11 units, boiler efficiency, loss, CHP, invalid rows | 83 | 77 | 6 (all expected) |
| Scope 3: every activity of the 15 categories, unit mismatch, explicit factors in kg / t / g / per $1,000, supplier total, invalid rows | 67 | 59 | 8 (all expected) |
| Scope 3 spend (NAICS) | 6 | 4 | 2 (all expected) |

Results:
- **Correct:** 652 of the 667 calculated scenarios matched the expected value to 0.1 %.
- **Dashboard:** Scope 1, 2 and 3, methane, flared volume and mitigation totals matched the stored sums, for all facilities and for each facility.

## Bugs

| # | Severity | Area | Bug | Evidence |
|---|---|---|---|---|
| 1 | High | Engine: liquids unloading, Tier 1 | The selected factor is ignored; every row gets the plunger-lift default (0.185 t/event, 1.774 t/well-year). Non-plunger and regional rows are never used unless separate type / region inputs are sent | "Non-Plunger (Gulf Coast)" 0.255 t/event x 12 = 3.06 t CH4 expected, 2.22 t stored. "Non-Plunger" 2.792 t/well-yr gave the plunger 1.774 |
| 2 | High | Engine: per well-year catalog rows | A monthly record books a full year (12x over a year of records). The activity-row fix did not cover catalog rows | 4 wells, July: 0.60 t CH4 expected (31/365), 7.10 t stored |
| 3 | High | UI: Pending Review, approve | Approving records one cannot approve (self-submitted) shows "Successfully approved 340 records" while 0 were approved. The code falls back to the selection size when approved_count is 0 | Toast shown; database unchanged (all Pending) |
| 4 | Medium | UI / API: Pending Review | The queue loads at most 200 records per scope (`/emissions/pending` limit=200). Counters and "Select All" show 340 while 646 are pending | S1 badge 200 with 506 pending |
| 5 | Medium | Engine: Tier 3 combustion by gas composition | An energy quantity (MMBtu) is accepted and computed as if it were a volume | 51 MMBtu (about 50,500 scf) gives 0.112 t CO2 instead of about 2.99 t (or a rejection) |
| 6 | Medium | Engine: CHP allocation | Default power efficiency is 33 % (the Compendium example's plant value). Compendium section 8 gives 35 % (power) / 80 % (heat) as defaults. Actual efficiencies cannot be entered | 1,000 t, 5,000 MMBtu heat, 1,000 MWh: 390.6 t expected, 376.7 t stored |
| 7 | Medium | Units | Nm3 (0 C) is treated as Sm3 (60 F); 1 Nm3 = 1.057 Sm3 | 1,000 Nm3 natural gas: 2.022 t expected, 1.913 t stored (-5.4 %) |
| 8 | Medium | UI: Sources import | The wizard requires Activity and Division columns that the server does not need, so a sources file without them cannot be started | "2 required fields not mapped: Activity, Division" |
| 9 | Medium | UI: Scope 1/2/3 wizards | No "Overwrite duplicates" option (only the Manage Data wizard has one), so a corrected file cannot replace records | Option absent in the three scope wizards |
| 10 | Medium | Facilities import | The equity share % cannot be imported; an "Equity Share" facility is stored at 100 % | AUD Offshore Block: boundary Equity Share, equity_share_pct 100 |
| 11 | Low | Engine: tank flashing catalog | The CO2 of "Tank - Flash Emissions (Oil)" (0.012 kg/bbl) is dropped | 9,500 bbl: CO2 0.114 t expected, 0 stored |
| 12 | Low | UI: Scope 1 table | Fixed decimals hide small non-zero values (0.000 / 0.00000) | 217 cells, e.g. 2.7e-4 t CO2 shown 0.000 |
| 13 | Low | UI: Scope 3 table | Column "EF (kg/unit)" shows the factor in whatever unit it was entered, so values are mislabelled | t/t factor 1.8 shown "1.80" (kg/unit); per $1,000 787 shown "787"; 180 g/pkm shown "180" |
| 14 | Low | UI: Scope 2 table | A supplier factor of 0 (renewable PPA) is shown as "—" | 5,000 MWh at 0 kg/kWh: EF "—" |
| 15 | Low | UI: Scope 1 table | A zero quantity is shown as "-" | Record with 0 MMBtu: Quantity "-" |
| 16 | Low | UI: Scope 1 table | The stoichiometry process is shown as the raw key "stoichiometry" | 3 rows |
| 17 | Low | UI: Scope 1 table | Uncertainty shows "±0%" for gases with no emission on some rows, "—" on others | Mud degassing: CO2 / N2O ±0 % |
| 18 | Low | Records | The factor name is stored as typed, not as the catalog name | "natural gas" / "mmbtu" stored instead of Natural Gas / MMBtu |
| 19 | Low | Error file | Blank cells are written as "None" | errors CSV: `...,None,None,...` |
| 20 | Low | Dashboard | Flared volume is labelled kNm3 but the volumes are standard m3 (60 F) | "1,301 kNm3" |
| 21 | Low | UI: record tables | The period column shows only the year; the month of a monthly record is not visible | Scope 1 / 2 / 3 tables "YEAR" |
| 22 | Low | API rate limit | About 6 dashboard loads in a minute hit the 200/min limit (HTTP 429 on notifications) | console: 429 Failed to fetch notifications |

## Working as expected (checked)
- **Tier 1 combustion:** every catalog fuel; gases in scf / Mscf / MMscf / m3 / MMBtu / GJ; liquids in gal / bbl / L / m3 / MMBtu; solids in short ton / tonne / kg / MMBtu.
- **Other Tier 1 catalog rows:**
  - mobile, flare, vent, associated-gas, tank, drilling, completion, component (hours of the month), dehydrator;
  - chemical production, nitric / adipic acid, asphalt;
  - pneumatic catalog rows (per device-year, month share applied).
- **Compendium activity rows:** all 104, with the month basis.
- **Tier 2 custom factors:** units converted to the factor unit.
- **Tier 3 methods:**
  - composition combustion and flaring (scf / m3 / Mscf);
  - completions (metered volume, and rate x duration in Mcf/day, Mcf/hr, m3/hr);
  - pneumatic bleed (scf/h, m3/h, month hours);
  - tank GOR, AGR, vent volume, Method 21, carbon balance (kg / t / lb), GOR x rate, carbon content.
- **Scope 2:**
  - all 61 grids;
  - kWh / MWh / GWh;
  - supplier factor and the 2 kg/kWh cap;
  - steam in 11 units, boiler efficiency and loss, boiler factor.
- **Scope 3:**
  - the form's factors for all activities;
  - unit aliases;
  - explicit factors in kg / t / g / per $1,000;
  - supplier total;
  - spend (NAICS).
- **Rejections:** every expected invalid row was rejected with a clear reason. This covers unknown fuel / process / unit / facility / grid / NAICS, negative, text, blank, out-of-range years, wrong factor for a process, Scope 2 process in Scope 1, missing Tier 3 inputs, duplicates, and implausible totals.
- **Displayed values:** apart from rows 12-17 above, the displayed Scope 1 / 2 / 3 values equal the stored values, and the dashboard totals equal the stored sums.

Files: CSVs, expectations (`expected.json`), comparison scripts and screenshots are in the session scratchpad `aud/` folder.

## Fixes (2026-09-29)

| # | Fix |
|---|---|
| 1 | Unloading: the selected Table 6-10 / 6-11 row sets type, frequency class and basin (`dispatcher.unloading_row_selection`); an explicit frequency class wins in the regional table |
| 2 | Per well-year: the record's share of a year (`record_period`) |
| 3 | Approve / reject messages report the server's count and why records were skipped (`utils/reviewResult.js`) |
| 4 | `/emissions/pending` returns whole-queue `pending_counts` and `pending_co2e`; the page shows them and notes when only the first rows are listed |
| 5 | Gas-composition methods need a gas volume (`units.gas_volume_m3`); every gas volume unit (Sm3, Nm3, Mscf...) is recognised (Sm3 used to fall back to the catalog factor) |
| 6 | CHP defaults 80 % / 35 % (Compendium 8.2.2); plant efficiencies can be entered (form, JSON, bulk) |
| 7 | Nm3 = 288.706 / 273.15 standard m3 |
| 8 | Manage Data wizard: required columns match the server (sources: facility and name; facilities: name; mitigation: facility, name, year, quantity) |
| 9 | "Overwrite records that already exist" in the Scope 1 / 2 / 3 wizards |
| 10 | Facility import: equity share %, operator status (and region / code fields in the wizard) |
| 11 | The engine was right (Table 6-22 is CH4 only); the stale legacy catalog row (CO2 0.012) is aligned |
| 12 | Small non-zero emissions shown in scientific notation (`formatEmission`) |
| 13 | Scope 3 factors stored as kg CO2e per activity unit (bulk, JSON, manual create and edit; EEIO per USD). Manual edit of a t/unit factor recalculated 1,000x low; a manual record without factor or allowed supplier total is refused (was 0 t) |
| 14 | A 0 factor is shown as 0 (CHP rows: "—") |
| 15 | A zero quantity is shown as 0 |
| 16 | Readable label for process keys outside the form list |
| 17 | Uncertainty shown only for gases the record emits |
| 18 | Catalog factor names stored canonically; common unit spellings normalised |
| 19 | Blank cells stay blank in the error file |
| 20 | Dashboard flared volume labelled kSm3 (the 2025 Master Report is unchanged) |
| 21 | Record tables show the period (year-month) |
| 22 | Root cause: the notification component re-fetched and reconnected its stream on every re-render (217 requests / minute); the effect now depends on the user ID. The rate limit counts per signed-in user instead of per IP |

Re-run of the whole audit through the UI on a fresh copy:
- **Scenarios:** 666 of 667 as expected. The remaining one is a deliberately absurd quantity (155 Mt in one record), rejected by the plausibility check.
- **Display:** 0 issues across all Scope 1, 2 and 3 table rows.
- **Review screen:**
  - the whole queue (632) is counted;
  - the pending impact equals the database sum;
  - the uploader gets "No records approved".
- **Notifications:** at most 14 requests a minute, no HTTP 429.
- **Tests:** backend 1,804 passed (`tests/test_scenario_audit_fixes.py`: 20); validation 128; vitest 38.
