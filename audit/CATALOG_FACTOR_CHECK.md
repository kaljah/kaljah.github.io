# Catalog factor check against the API Compendium 2021 (2026-09-28)

## Scope and method

**Checked:**
- the server catalogs: `emission_factors.py`, `emission_factors_api2021.py` and `emission_factors_chapter7_onshore.py` (197 rows);
- the client catalog, `client/src/utils/EmissionFactors.js` (101 rows);
- the Scope 2 grid factors, `electricity_factors.py`;
- the Scope 3 fuel factors in `Scope3Form.jsx`.

**Method:**
- Each value was compared with the Compendium table named in the row, read from `scratch/2021-API-GHG-Compendium.pdf`.
- A row whose value is not in any Compendium table was either replaced by the Compendium value or equation, or removed.
- Where a row is a derived value (flares, venting), it is now computed from the Compendium's own default composition and equation.

**Existing records** keep their stored values (data policy). The new values apply to new records and to recalculated ones. Your database uses none of the removed rows. It does use two corrected ones:
- "Completion - Gas Well (No Flaring)";
- "Workover - Gas Well (No Flaring)".

## Corrected

**Combustion fuels** (Table 4-5 = 40 CFR 98 Table C-1; Table 4-6):

| Row | Was | Now |
|---|---|---|
| Propane (Gas) | HHV 2,500 Btu/scf | 2,516 |
| Propane (Liquid), Propane (Liquid/LPG) | 91,500 Btu/gal; 62.88 kg/MMBtu | 91,000; 62.87 |
| Ethane (liquid) | 69,600 Btu/gal | 68,000 |
| Bituminous Coal | 93.26 kg CO2/MMBtu | 93.28 |
| Petroleum Coke | CH4 0.003, N2O 0.0006 kg/MMBtu | 0.032, 0.0042 |
| Coke Oven Gas | 590 Btu/scf | 599 |
| Landfill Gas | 500 Btu/scf | 485 |
| Refinery Fuel Gas | 1,400 Btu/scf; 57.78 kg/MMBtu; CH4 0.0028, N2O 0.0001 | 1,388; 59.00; 0.003, 0.0006 (C-2 fuel gas) |
| Marine Diesel Oil | 138,858 Btu/gal; 73.19 kg/MMBtu (no source) | distillate No. 2: 138,000; 73.96 |

**Flaring and venting** (kg per Sm3; Equations 5-2, 5-4 and 5-6 at 23.685 Sm3/kgmole):

| Row | Was | Now |
|---|---|---|
| Natural Gas (Flaring), (Elevated) | CO2 1.92, CH4 0.012 | Table 5-1 processing gas at 98 %: 1.9334, 0.012447 |
| Natural Gas (Flaring - Enclosed) | 1.94, 0.006 | Same gas at 99.5 %: 1.9628, 0.003112 |
| Associated Gas (Flaring) | 2.15, 0.018 | Table 5-1 raw gas at 98 %: 2.2762, 0.010836 |
| N2O on these rows | 1e-5 | Equation 5-6 ratio (about 3.2e-6) |
| Natural Gas (Venting/Blowdown) | CH4 0.67, CO2 0.054 (sums to over 100 %) | Table 6-50 pipeline gas: 0.63029, 0.010498 |
| Pure-gas flares | 23.679 Sm3/kmol | The Compendium's 23.685 |

**Tanks, dehydration, completions:**

| Row | Was | Now |
|---|---|---|
| Tank – Crude Oil (Small) | 0.18 kg CH4/bbl | Table 6-22: 0.0184 |
| Tank – Production Condensate (Large / Small) | 1.16 / 1.56 | Table 6-24: 0.146 / 0.119 |
| Tank – Flash Emissions (Oil) | CO2 0.012 kg/bbl (no source) | 0: Table 6-22 is CH4 only |
| Dehydrator – Glycol (Uncontrolled) | 0.177 "scf/MMscf" | Table 6-17: 0.0052859 t CH4/MMscf |
| Completion – Gas Well (No Flaring) | 0.7 t/event | Table 6-6: 1.7376 |
| Workover – Gas Well (No Flaring) | 0.05 t/event | Table 6-9: 0.0470 |

**Pneumatic controllers:** the generic names were repointed to the production tables.

| Row | Was | Now |
|---|---|---|
| High Bleed, High Bleed (>6 scfh) | 8.304 (gas-processing Table 6-34) | Table 6-14 GHGRP: 5.11 t/yr |
| Low Bleed, Low Bleed (<6 scfh) | 0.0939 (Table 6-34) | Table 6-14 GHGRP: 0.191 |
| Intermittent | 0.4 (T&S Table 6-42) | Table 6-15 GHGRP: 1.85 |

Processing and T&S factors remain available as the Table 6-34 and Table 6-42 activity rows, and "Continuous Vent (T&S)" keeps 3.5 t/yr.

**Chemicals** (Table 6-53): the CH4 factors were missing.

| Row | CH4, kg per tonne |
|---|---|
| Acrylonitrile | 0.18 |
| Carbon Black | 28.7 (0.06 with thermal abatement, new row) |
| Ethylene | Split into ethane feedstock (6) and other feedstocks (3) |
| Ethylene Oxide | 1.79 (0.79 with thermal abatement, new row) |

The nitric and adipic acid values were correct, but cited "pg 407"; they now cite Table 6-53.

**Chapter 7:**

| Row | Was | Now |
|---|---|---|
| Offshore – Oil Production (Facility) | 3.86E-06 t/bbl | Table 7-3: 9.386E-05 |
| Component – Open-Ended Line (Gathering) | 1.2E-05 t/h | Table 7-30: 7.09E-05 |
| Component rows (by service) | CH4 from assumed fractions of 85 / 60 / 15 / 10 wt %, labelled "kg TOC" | Table 7-12 converted CH4 (e.g. gas valve 2.94E-06 t/h, was 3.83E-06) |
| Component – Other / PRV (Water/Oil) | THC 1.4E-04 kg/h | Table 7-12: 1.4E-02 |

**Scope 2 grids** (Tables 8-2 and 8-6):
- The grid rows now store CO2, CH4 and N2O separately, and CO2e is computed with the active GWP set, so AR6 now applies to Scope 2.

| Row | Was | Now |
|---|---|---|
| US Average | 0.385 kg/kWh | Table 8-2: 0.401 t CO2 + 3.40E-05 CH4 + 4.99E-06 N2O per MWh (0.4033 at AR5) |
| US-ERCOT | 0.4345, the short-ton figure | "US-ERCT (ERCOT All)" 0.394 t CO2 + CH4/N2O; old name kept as an alias |
| UK | 0.233 | "United Kingdom (grid average)" 0.1964, Table 8-6; old name kept as an alias |
| US-WECC 0.3132, EU Grid Average 0.295 | Not in the tables | Removed. All 27 eGRID subregions and 32 Table 8-6 countries added. |
| Algerian Grid North 0.510 / South 0.650 | Marked "estimated" | Removed |

**Scope 3, Category 10 and 11 fuels** (Table 4-5 heating value and CO2 plus Table 4-6 CH4 / N2O, kg CO2e at AR5):

| Row | Was | Now |
|---|---|---|
| Crude oil | 433.7 /bbl | 433.44 |
| Natural gas | 54.6 /Mcf | 54.18 |
| Ethane | 3.93 /gal | 4.07 |
| Propane | 5.74 /gal | 5.74 (unchanged) |
| Butane | 6.38 /gal | 6.70 |
| NGL mixed | 5.5 /gal | Taken as LPG: 5.70 |

## Removed (no Compendium source)

**Server:**
- flaring: "Natural Gas (Flaring - Ground)", "Sour Gas (Flaring)", "Refinery Gas (Flaring)";
- tanks: "Tank - Working Losses (Oil)" (0.05 kg/bbl), "Tank - Breathing Losses (Oil)" (0.001 kg/bbl-yr), "Tank - Gas-Well Condensate" (2.05 / 2.65);
- loading: "Loading - Crude Oil (Tank Truck / Marine Vessel)" (Table 6-47 rows are used instead);
- other: "Wastewater - Oil/Water Separator", "Fugitive - Valve / Connector / Flange (Gas/Vapor)", "Gathering - Pipeline" (cited Table 7-29, which has no pipeline row), "Component - Pump Seal (Heavy Oil Service)" (Table 7-12 has no such row).

**Client:**
- tanks: "Methane Flashing" crude, condensate and produced-water rows (0.12 to 1.56 kg/bbl, not table values);
- dehydration: TEG 3.0 / 1.2 / 0.3 scf/gal, cited "Table 6-5", which is completions; the glycol controlled row; the "Glycol Dehydrator" and "Desiccant Dehydrator" zero placeholders;
- "Amine Unit - Venting (Generic)";
- the made-up CO2 on the completion rows, and the completions form's unused CO2 / whole-gas numbers (the server computes completions from Tables 6-5 and 6-6).

## Verified unchanged

- **Fuels:** natural gas, diesel, No. 6, kerosene, jet fuel, gasoline, crude, coals, blast furnace gas (Table 4-5), and the Table 4-7 engine rows.
- **Section 6 tables:** drilling (Table 6-2, 6-3), completions (Table 6-5, 6-6), associated gas venting (Table 6-8), unloading (Tables 6-10 and 6-11, all 20 rows), crude tank large (Table 6-22), asphalt (Table 6-52).
- **Chapter 7:** onshore facility / equipment (Tables 7-8, 7-9, 7-10), gathering (Tables 7-29 and 7-30), processing compressors (Table 7-35), LNG (Table 7-76), refinery (Table 7-80), offshore gas (Table 7-3).
- **Previously verified:** the activity-factor rows (Tables 6-4 to 6-47).

## Not verified (outside the Compendium)

- **Algerian National Grid 0.522 kg/kWh:** kept, because it is the grid your sites use, but flagged `verified: False`. Replace it with the published Sonelgaz or IEA factor, or enter a supplier factor.
- **Scope 3 categories 1 to 9 and 12 to 15:** steel, cement, transport, travel, waste, spend-based and similar factors. These are life-cycle or EEIO values; the Compendium does not cover them, and no reference was available here to check them.

## Tests

- **New suite:** `tests/test_catalog_factors.py`, 58 cases. It checks each corrected row against its table value and the removed rows' absence. It also checks that every client row that isn't a server calculator choice exists on the server with the same values, by reading the client file through node.
- **Re-derived tests:** the flare test in `test_browser_exploratory_fixes.py` (Equation 5-2); the grid tests in `test_emission_factor_selection.py`, `test_tier_scope_kpi_numerical.py` and `test_ui_calculation_parity.py` (Table 8-2). The client TEG "parity" test, which asserted invented values, was removed.
- **Results:** backend 1,742 passed, 0 failed; validation 128 passed; client 23/23; build OK.
- **Browser check (database copy):**
  - The flaring list no longer offers the removed rows.
  - 100 t of carbon black: 263 t CO2 and 2.87 t CH4.
  - 100,000 kWh on the US average grid: 40.33 t.
  - The Scope 3 crude factor shows 433.44.
