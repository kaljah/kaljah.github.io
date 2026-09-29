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

## Follow-up: EPA and IPCC sources (2026-09-29)

**EPA GHG Emission Factors Hub 2025** (`ghg-emission-factors-hub-2025.xlsx`), CO2e at AR5 in the form's units:

| Row | Was | Now |
|---|---|---|
| Truck | 0.062 | 0.1284 kg/t-km (Table 8, short ton-mile, x 1/1.45997) |
| Rail | 0.022 | 0.0145 |
| Ship | 0.011 | 0.0537 |
| Air freight | — | 0.750 (added) |
| Pipeline transport | 0.005 | Removed: no EPA or Compendium factor |
| Air, short / medium / long haul | "Air domestic / international" 0.255 / 0.195 | 0.1298 / 0.0808 / 0.1022 kg per passenger-km (Table 10) |
| Passenger car | 0.192 / km | 0.1855 per vehicle-km |
| Light-duty truck | — | 0.2465 |
| Intercity rail | 0.041 | 0.0601 |
| Bus | — | 0.0414 |
| Commuter rail / transit rail | "Public transit" 0.05 | 0.0833 / 0.0581 |
| "Car - Diesel", "Teleworking" | 0.171 / 1.5 | Removed: no EPA factor |
| Landfill | 0.57 kg/kg | 0.639 (Table 9 WARM, mixed MSW) |
| Incineration | 0.021 | 0.474 (mixed MSW) |
| Recycling | 0.012 | 0.099 (mixed recyclables) |
| Composting | 0.008 | 0.143 (mixed organics) |
| Leased vehicles | 0.2 | 0.1855 (Table 10 passenger car) |

**Purchased steam** (EPA Table 7: 66.33 kg CO2, 1.25 g CH4, 0.125 g N2O per MMBtu of steam at 80 % natural gas):
- The app's CO2 already matched (53.06 / 0.8).
- CH4 and N2O were missing. They are now added in both the Scope 2 route (natural-gas boiler) and the Scope 1 indirect-steam calculator (the selected fuel's Table 4-6 CH4 / N2O), with the active GWP.

**Not covered by EPA or IPCC:**
- **Algeria grid:** the IPCC publishes no grid factors, and the EPA Hub covers US grids only. The standard location-based source is the IEA Emissions Factors database, which is licensed. The only free copy found is ADEME Base Carbone's withdrawn IEA-2017 value of 0.548 kg CO2e/kWh. The UNFCCC harmonized IFI dataset gives combined-margin factors for projects, which are not suitable for location-based Scope 2. So 0.522 remains flagged as unverified; a Sonelgaz or IEA value is needed.
- **Categories 1, 2 and 15** (steel, cement, chemicals, spend-based, investments): the EPA source is the per-dollar USEEIO Supply Chain Factors dataset, which isn't in the Hub. Categories 3, 8 (office space), 10 (electricity), 13 and 14 have no EPA factor. These remain unverified and are listed in `client/src/utils/scope3Factors.js`.
- **IPCC 2006/2019 default combustion factors:** cover the same fuels as Compendium Tables 4-5 / 4-6, which are already used.

**Tests:**
- `client/src/__tests__/scope3Factors.test.js`: the Scope 3 factors, re-derived from the EPA and Compendium table numbers.
- The steam tests and the reference model were re-derived with Table 4-6 CH4 / N2O.
- Results: client 28/28, backend 1,742 passed, validation 128.

## Follow-up: spend factors and the Algerian grid (2026-09-29)

### Spend-based factors: EPA Supply Chain GHG Emission Factors v1.3.0

**Dataset:** NAICS-6, USEEIO v2.2.22-GHG, 2022 US GHG data, AR5, kg CO2e per 2022 USD at purchaser price, "with margins". Downloaded from pasteur.epa.gov and shipped as `server/emission_factors/data/SupplyChainGHGEmissionFactors_v1.3.0_NAICS_CO2e_USD2022.csv`.

**What the old server table got wrong** (`emission_factors/eeio_factors.py`):
- It said "EPA USEEIO v1.3" but held 3-digit codes with values that are not in that dataset. Oil and gas extraction was 3.20 kg/USD; EPA gives 0.405 (211120 / 211130). Utilities were 5.4 kg/USD; EPA does not cover electricity.
- It fell back to a 0.35 kg/USD "generic corporate spend" for any unknown code.

**Replacement:**
- The table now holds all 1,016 EPA codes. Lookup is by exact 6-digit code; a partial or unknown code is rejected with a 422 error, or a row error in bulk imports.
- `GET /api/scope3/eeio-factors?q=` searches codes by number or title, and the form's NAICS field suggests matches.

**Scope 3 form rows** (kg CO2e per USD):

| Category | Rows |
|---|---|
| 1 | Iron and steel 0.787, steel pipe 0.36, cement 3.924, organic chemicals 1.184, inorganic chemicals 1.01, O&G support services 0.372, engineering services 0.103 |
| 2 | O&G field machinery 0.219, pipeline construction 0.277, buildings 0.224, computers 0.058 |
| 3 | Refined fuels 0.27, natural gas 0.405 (cradle-to-gate) |
| 8 and 13 | Building rent 0.246 |

These replace the per-kg steel, cement and chemicals rows and the per-dollar rows, which had no source.

**No published default** (the form asks the user for a factor):
- T&D losses and processing electricity: the site grid factor applies.
- Franchises.
- Investments: EPA has none; PCAF or investee data applies.

### Algerian National Grid: 0.4979 kg CO2e/kWh (2024, direct combustion)

**Inputs**, from the Ministère des Hydrocarbures et des Mines, *Bilan Énergétique National 2024* (oilmines.gov.dz):
- Gas to power plants, including Sonelgaz, independents and self-generators: 23,855 ktep, 25,244 million m3 (Tableau 3).
- The balance's tep are on the gross calorific basis ("pouvoir calorifique supérieur"; 1,000 m3 = 0.945 tep).
- National electricity production: 101,386 GWh, of which 100,684 thermal and 702 renewable (Tableau 1.B).

**Calculation:**
- Energy: 23,855 ktep x 41.868 = 998,761 TJ gross, which is 898,885 TJ net (net = 0.9 x gross, the IPCC convention for gases).
- Emissions, with the IPCC 2006 Vol. 2 Table 2.2 natural-gas factors for energy industries (56,100 kg CO2, 1 kg CH4 and 0.1 kg N2O per TJ net): 50.43 Mt CO2, 899 t CH4 and 89.9 t N2O.
- Factor: 0.4974 kg CO2/kWh, or 0.4979 kg CO2e/kWh at AR5. The app computes CO2e with the active GWP.

**Cross-checks:**
- The Compendium natural-gas factor (53.06 kg/MMBtu, higher heating value) on the same gas gives 0.495.
- Implied fleet efficiency is 40 % (net), with 53 % combined cycle and 41 % gas turbines.
- Algeria's BUR1 inventory (1.A.1.a public generation 2020: 35.3 Mt CO2) implies about 71 TWh of public generation at this rate, consistent with national output minus self-generation.
- The Sonelgaz technology factors quoted in BUR1 (combined cycle 436, simple cycle 549 kg CO2/MWh) bound the value.

**Rejected sources:**
- Ember, 633 g CO2e/kWh: life-cycle basis, including upstream methane.
- ADEME / IEA 2017, 0.548: withdrawn and old.
- IFI combined margin: project-crediting basis.

**Limitations:**
- Diesel units (0.3 % of output) are not in the numerator, understating the result by about 0.2 %.
- Self-generators are included in both numerator and denominator.
- The previous 0.522 had no source; the new value is 4.6 % lower.

### Tests

- New and changed: `test_catalog_factors.py` (EEIO dataset and Algeria derivation), `test_calculations_page.py` and `test_tier_scope_kpi_numerical.py` (EPA EEIO values, 422 on partial codes), and `scope3Factors.test.js` (spend rows and empty defaults).
- Results: backend 1,743 passed, validation 128, client 30/30, build OK.
- Browser check:
  - Category 1 lists the EPA rows.
  - Typing "steel" suggests NAICS 331110 and 331210.
  - NAICS 331110 with USD 100,000 of spend gives 78.7 t.
  - Code "541" is rejected with a message.
  - 100,000 kWh on the Algerian grid gives 49.79 t.
