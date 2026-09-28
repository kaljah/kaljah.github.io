# API Compendium 2021 — exhibit and default-factor check (2026-09-27)

Source: scratch/2021-API-GHG-Compendium.pdf (text via pdftotext). Engine path = POST /api/emissions (services.scope1_calc.resolve_factor + calculations.compute_emissions), AR5 GWP. Regression test: new/server/tests/test_api_compendium_exhibits.py.

## 1. Exhibits run through their process type

| Exhibit | Case | Result | Engine vs exhibit |
|---|---|---|---|
| 4.2 | Natural gas 800e6 scf, default HHV (Tier 1) | PASS | CO2 4.33e+04 vs 4.33e+04 (+0.0%) |
| 4.4a | Natural gas 800e6 scf, known composition (Tier 3) | PASS | CO2 4.344e+04 vs 4.268e+04 (+1.8%) |
| 4.6 | Residual fuel oil No. 6, 4e6 gal (Tier 1) | PASS | CO2 4.506e+04 vs 4.498e+04 (+0.2%); CH4 1.8 vs 1.8 (+0.0%); N2O 0.36 vs 0.36 (+0.0%) |
| 4.13 | Marine diesel 275,498 m3 (fuel basis) | PASS | CO2 7.397e+05 vs 7.426e+05 (-0.4%) |
| 5.1 | Gas flare, known volume and composition | PASS | CH4 6.148 vs 6.1 (+0.8%); CO2 1,096 vs 1,095 (+0.1%) |
| 6-1 | Mud degassing 85 days, water-based (Tier 2+) | PASS | CH4 18.49 vs 18.49 (-0.0%); CO2 6.521 vs 6.54 (-0.3%) |
| 6-3 | Completion with HF, metered flowback to flare (Tier 3) | PASS | CH4 2.377 vs 2.36 (+0.7%); CO2 98.88 vs 98.7 (+0.2%) |
| 6-6 | Associated gas venting, GOR balance (Tier 2) | PASS | CH4 1.784e+04 vs 1.78e+04 (+0.3%); CO2 6,992 vs 6,991 (+0.0%) |
| 6-8 | Liquids unloading, Eq 6-10 (Tier 3) | PASS | CH4 20.44 vs 20.39 (+0.2%); CO2 2.103 vs 2.1 (+0.1%) |
| 6-11 | Pneumatic low-bleed controllers x80 (Table 6-14) | FAIL | CH4 24.51 vs 24.2 (+1.3%); CO2 8.642 vs 7 (+23.5%) |
| 6-12 | Intermittent controllers, monitoring survey (Eq 6-14) | PASS | CH4 5.445 vs 5.41 (+0.7%); CO2 1.92 vs 1.91 (+0.5%) |
| 6-13 | Glycol dehydrator vent, throughput factor (Table 6-17) | PASS | CH4 50.19 vs 50.2 (-0.0%) |
| 6-19 | Tank flashing, GOR 47 scf/bbl (Tier 3) | PASS | CH4 40.73 vs 40.6 (+0.3%) |
| 6-20 | Tank flashing, Table 6-22 large uncontrolled | PASS | CH4 31.77 vs 31.8 (-0.1%) |
| 6-21 | Produced water tank (Table 6-26) | PASS | CH4 0.2591 vs 0.26 (-0.3%) |
| 6-25 | Equipment blowdown, gas law (Eq 6-32) | PASS | CH4 0.01104 vs 0.011 (+0.4%) |
| 6-44 | Hydrogen plant, simple factor (Table 6-51) | PASS | CO2 1.743e+05 vs 1.743e+05 (+0.0%) |
| 6-45 | Asphalt blowing 100,000 tons (Table 6-52) | PASS | CO2 561 vs 561 (+0.0%); CH4 307 vs 307 (+0.0%) |
| 7-4 | Onshore gas equipment: 15 wellheads (Table 7-10) | PASS | CH4 2.365 vs 2.36 (+0.2%) |
| 7-4 | Onshore gas equipment: 4 separators (Table 7-10) | PASS | CH4 1.549 vs 1.55 (-0.1%) |
| 7-4 | Onshore gas equipment: 1 heater (Table 7-10) | PASS | CH4 0.403 vs 0.4 (+0.7%) |
| 6-42 | Hydrogen plant, feedstock carbon balance (Eq 6-49) | PASS | CO2 2.976e+05 vs 2.971e+05 (+0.2%) |
| 6-43 | Hydrogen plant, H2 stoichiometry (Eq 6-50) | PASS | CO2 1.777e+05 vs 1.778e+05 (-0.1%) |

Notes: 4.2 and 4.4(a) expected values are derived (4.2 energy x Table 4-3 factor; 4.4(a) Eq 4-11, the exhibit answer is not in the extracted text). 6-1 uses 0.2605 t CH4/drilling-day, the Table 6-2 value the engine files as offshore. 6-11: the exhibit text says CO2 comes from the whole-gas factor (2.6 scf/h) but its arithmetic uses 2.1 (the CH4-basis value) -> 7.0 t; the engine follows the stated method (8.64 t). Not an engine defect.

## 2. Exhibits not runnable (method not in the engine)

4.1 / 4.3 (energy output and LHV-HHV conversion only), 4.5 (liquid fuel by carbon wt %), 4.7 / 4.8 (equipment-basis CH4/N2O), 4.12 (vehicles by distance), 5.2 (flare from VOC emissions), 5.3 (thermal oxidizer), 6-2 (well testing), 6-5 (coal seam drilling), 6-7 (workovers without HF), 6-9 / 6-10 (casing gas), 6-14 (Kimray gas-assisted pump, Table 6-18), 6-15 (desiccant dehydration), 6-16 (AGR per unit, Table 6-19), 6-17 (CO2 from sour gas processing), 6-22 (CO2 EOR), 6-23 / 6-24 (G&B controllers / compressors), 6-26 (Table 6-32 blowdowns: calculator exists, not routed), 6-27 .. 6-34 (G&B, processing, transmission, distribution non-routine / rod packing / blanketed tanks), 6-35 .. 6-37 (loading, ballasting, transit), 6-38 .. 6-40, 6-61 (FCCU, catalyst regeneration, coker), 7-1 / 7-2 / 7-3 (offshore fugitives), 7-5 (correlation approach), 7-6 / 7-7 (wastewater), 7-8 / 7-9 (HFC, SF6).

## 3. Default factors x equivalent quantities in different units

194 checks: {'PASS': 157, 'SKIP': 37}. Each catalog factor was run under its process with one activity amount expressed in every unit of its dimension (gas: m3, scf, Mcf, MMscf; liquid: gal, bbl, L, m3; mass: kg, tonne, short ton), compared across units and against factor x quantity computed with independent constants (1 m3 = 35.3146667 ft3, 1 bbl = 42 gal, 1 gal = 3.785411784 L, 1 short ton = 907.18474 kg) and the catalog HHV for energy-based factors; wrong-dimension units (gas fuel in gal, liquid fuel in scf or kg without density) must be rejected. SKIP = factors chosen internally by process calculators (per event / well-year / completion); their values were checked against Tables 6-10 / 6-11.

| Factor | Unit | Process | Result | Detail |
|---|---|---|---|---|
| Natural Gas | kg/MMBtu | combustion | PASS | wrong unit 'gal' rejected: 'gal' is a liquid volume but this fuel's heating value is per scf of gas |
| Natural Gas | kg/MMBtu | combustion | PASS | CO2: m3 1.9113, scf 1.9113, Mcf 1.9113, MMscf 1.9113 | expected 1.9113 |
| Landfill Gas | kg/MMBtu | combustion | PASS | wrong unit 'gal' rejected: 'gal' is a liquid volume but this fuel's heating value is per scf of gas |
| Landfill Gas | kg/MMBtu | combustion | PASS | CO2: m3 0.91942, scf 0.91942, Mcf 0.91942, MMscf 0.91942 | expected 0.91942 |
| Coke Oven Gas | kg/MMBtu | combustion | PASS | wrong unit 'gal' rejected: 'gal' is a liquid volume but this fuel's heating value is per scf of gas |
| Coke Oven Gas | kg/MMBtu | combustion | PASS | CO2: m3 0.97615, scf 0.97615, Mcf 0.97615, MMscf 0.97615 | expected 0.97615 |
| Blast Furnace Gas | kg/MMBtu | combustion | PASS | wrong unit 'gal' rejected: 'gal' is a liquid volume but this fuel's heating value is per scf of gas |
| Blast Furnace Gas | kg/MMBtu | combustion | PASS | CO2: m3 0.89125, scf 0.89125, Mcf 0.89125, MMscf 0.89125 | expected 0.89125 |
| Propane (Gas) | kg/MMBtu | combustion | PASS | wrong unit 'gal' rejected: 'gal' is a liquid volume but this fuel's heating value is per scf of gas |
| Propane (Gas) | kg/MMBtu | combustion | PASS | CO2: m3 5.4261, scf 5.4261, Mcf 5.4261, MMscf 5.4261 | expected 5.4261 |
| Refinery Fuel Gas | kg/MMBtu | combustion | PASS | wrong unit 'gal' rejected: 'gal' is a liquid volume but this fuel's heating value is per scf of gas |
| Refinery Fuel Gas | kg/MMBtu | combustion | PASS | CO2: m3 2.8567, scf 2.8567, Mcf 2.8567, MMscf 2.8567 | expected 2.8567 |
| Marine Diesel Oil | kg/MMBtu | mobile | PASS | wrong unit 'kg' rejected: Activity unit 'kg' needs the fuel density to use a heating value tabulated per g |
| Marine Diesel Oil | kg/MMBtu | mobile | PASS | wrong unit 'scf' rejected: 'scf' is a gas volume but this fuel's heating value is per gal of liquid |
| Marine Diesel Oil | kg/MMBtu | mobile | PASS | CO2: gal 10.163, bbl 10.163, L 10.163, m3 10.163 | expected 10.163 |
| Diesel (No. 2 Fuel Oil) | kg/MMBtu | mobile | PASS | wrong unit 'kg' rejected: Activity unit 'kg' needs the fuel density to use a heating value tabulated per g |
| Diesel (No. 2 Fuel Oil) | kg/MMBtu | mobile | PASS | wrong unit 'scf' rejected: 'scf' is a gas volume but this fuel's heating value is per gal of liquid |
| Diesel (No. 2 Fuel Oil) | kg/MMBtu | mobile | PASS | CO2: gal 10.206, bbl 10.206, L 10.206, m3 10.206 | expected 10.206 |
| Residual Fuel Oil (No. 6) | kg/MMBtu | combustion | PASS | wrong unit 'kg' rejected: Activity unit 'kg' needs the fuel density to use a heating value tabulated per g |
| Residual Fuel Oil (No. 6) | kg/MMBtu | combustion | PASS | wrong unit 'scf' rejected: 'scf' is a gas volume but this fuel's heating value is per gal of liquid |
| Residual Fuel Oil (No. 6) | kg/MMBtu | combustion | PASS | CO2: gal 11.265, bbl 11.265, L 11.265, m3 11.265 | expected 11.265 |
| Kerosene | kg/MMBtu | mobile | PASS | wrong unit 'kg' rejected: Activity unit 'kg' needs the fuel density to use a heating value tabulated per g |
| Kerosene | kg/MMBtu | mobile | PASS | wrong unit 'scf' rejected: 'scf' is a gas volume but this fuel's heating value is per gal of liquid |
| Kerosene | kg/MMBtu | mobile | PASS | CO2: gal 10.152, bbl 10.152, L 10.152, m3 10.152 | expected 10.152 |
| Motor Gasoline | kg/MMBtu | mobile | PASS | wrong unit 'kg' rejected: Activity unit 'kg' needs the fuel density to use a heating value tabulated per g |
| Motor Gasoline | kg/MMBtu | mobile | PASS | wrong unit 'scf' rejected: 'scf' is a gas volume but this fuel's heating value is per gal of liquid |
| Motor Gasoline | kg/MMBtu | mobile | PASS | CO2: gal 8.7775, bbl 8.7775, L 8.7775, m3 8.7775 | expected 8.7775 |
| Jet Fuel | kg/MMBtu | mobile | PASS | wrong unit 'kg' rejected: Activity unit 'kg' needs the fuel density to use a heating value tabulated per g |
| Jet Fuel | kg/MMBtu | mobile | PASS | wrong unit 'scf' rejected: 'scf' is a gas volume but this fuel's heating value is per gal of liquid |
| Jet Fuel | kg/MMBtu | mobile | PASS | CO2: gal 9.7497, bbl 9.7497, L 9.7497, m3 9.7497 | expected 9.7497 |
| Propane (Liquid/LPG) | kg/MMBtu | mobile | PASS | wrong unit 'kg' rejected: Activity unit 'kg' needs the fuel density to use a heating value tabulated per g |
| Propane (Liquid/LPG) | kg/MMBtu | mobile | PASS | wrong unit 'scf' rejected: 'scf' is a gas volume but this fuel's heating value is per gal of liquid |
| Propane (Liquid/LPG) | kg/MMBtu | mobile | PASS | CO2: gal 5.7535, bbl 5.7535, L 5.7535, m3 5.7535 | expected 5.7535 |
| Ethane | kg/MMBtu | combustion | PASS | wrong unit 'kg' rejected: Activity unit 'kg' needs the fuel density to use a heating value tabulated per g |
| Ethane | kg/MMBtu | combustion | PASS | wrong unit 'scf' rejected: 'scf' is a gas volume but this fuel's heating value is per gal of liquid |
| Ethane | kg/MMBtu | combustion | PASS | CO2: gal 4.1482, bbl 4.1482, L 4.1482, m3 4.1482 | expected 4.1482 |
| Ethane (Gas) | kg/MMBtu | combustion | PASS | wrong unit 'gal' rejected: 'gal' is a liquid volume but this fuel's heating value is per scf of gas |
| Ethane (Gas) | kg/MMBtu | combustion | PASS | CO2: m3 3.7229, scf 3.7229, Mcf 3.7229, MMscf 3.7229 | expected 3.7229 |
| Crude Oil | kg/MMBtu | combustion | PASS | wrong unit 'kg' rejected: Activity unit 'kg' needs the fuel density to use a heating value tabulated per g |
| Crude Oil | kg/MMBtu | combustion | PASS | wrong unit 'scf' rejected: 'scf' is a gas volume but this fuel's heating value is per gal of liquid |
| Crude Oil | kg/MMBtu | combustion | PASS | CO2: gal 10.287, bbl 10.287, L 10.287, m3 10.287 | expected 10.287 |
| Anthracite Coal | kg/MMBtu | combustion | PASS | wrong unit 'm3' rejected: Activity unit 'm3' needs the fuel density to use a heating value tabulated per s |
| Anthracite Coal | kg/MMBtu | combustion | PASS | wrong unit 'scf' rejected: Activity unit 'scf' needs the fuel density to use a heating value tabulated per  |
| Anthracite Coal | kg/MMBtu | combustion | PASS | CO2: kg 2.8678, tonne 2.8678, ton 2.8678 |
| Bituminous Coal | kg/MMBtu | combustion | PASS | wrong unit 'm3' rejected: Activity unit 'm3' needs the fuel density to use a heating value tabulated per s |
| Bituminous Coal | kg/MMBtu | combustion | PASS | wrong unit 'scf' rejected: Activity unit 'scf' needs the fuel density to use a heating value tabulated per  |
| Bituminous Coal | kg/MMBtu | combustion | PASS | CO2: kg 2.5628, tonne 2.5628, ton 2.5628 |
| Sub-Bituminous Coal | kg/MMBtu | combustion | PASS | wrong unit 'm3' rejected: Activity unit 'm3' needs the fuel density to use a heating value tabulated per s |
| Sub-Bituminous Coal | kg/MMBtu | combustion | PASS | wrong unit 'scf' rejected: Activity unit 'scf' needs the fuel density to use a heating value tabulated per  |
| Sub-Bituminous Coal | kg/MMBtu | combustion | PASS | CO2: kg 1.8477, tonne 1.8477, ton 1.8477 |
| Lignite Coal | kg/MMBtu | combustion | PASS | wrong unit 'm3' rejected: Activity unit 'm3' needs the fuel density to use a heating value tabulated per s |
| Lignite Coal | kg/MMBtu | combustion | PASS | wrong unit 'scf' rejected: Activity unit 'scf' needs the fuel density to use a heating value tabulated per  |
| Lignite Coal | kg/MMBtu | combustion | PASS | CO2: kg 1.5307, tonne 1.5307, ton 1.5307 |
| Petroleum Coke | kg/MMBtu | combustion | PASS | wrong unit 'm3' rejected: Activity unit 'm3' needs the fuel density to use a heating value tabulated per s |
| Petroleum Coke | kg/MMBtu | combustion | PASS | wrong unit 'scf' rejected: Activity unit 'scf' needs the fuel density to use a heating value tabulated per  |
| Petroleum Coke | kg/MMBtu | combustion | PASS | CO2: kg 3.3866, tonne 3.3866, ton 3.3866 |
| Natural Gas (Flaring - Elevated) | kg/m³ | flaring | PASS | CO2: m3 1.92, scf 1.92, Mcf 1.92, MMscf 1.92 | expected 1.92 |
| Natural Gas (Flaring - Ground) | kg/m³ | flaring | PASS | CO2: m3 1.88, scf 1.88, Mcf 1.88, MMscf 1.88 | expected 1.88 |
| Natural Gas (Flaring) | kg/m³ | flaring | PASS | CO2: m3 1.92, scf 1.92, Mcf 1.92, MMscf 1.92 | expected 1.92 |
| Natural Gas (Flaring - Enclosed) | kg/m³ | flaring | PASS | CO2: m3 1.94, scf 1.94, Mcf 1.94, MMscf 1.94 | expected 1.94 |
| Associated Gas (Flaring) | kg/m³ | flaring | PASS | CO2: m3 2.15, scf 2.15, Mcf 2.15, MMscf 2.15 | expected 2.15 |
| Sour Gas (Flaring) | kg/m³ | flaring | PASS | CO2: m3 2.3, scf 2.3, Mcf 2.3, MMscf 2.3 | expected 2.3 |
| Refinery Gas (Flaring) | kg/m³ | flaring | PASS | CO2: m3 2.1, scf 2.1, Mcf 2.1, MMscf 2.1 | expected 2.1 |
| Well Completion - Gas Well with Hydraulic Fracturing (Uncontrolled Venting) | tonnes/completion | venting | SKIP | unit basis not covered |
| Well Completion - Gas Well with Hydraulic Fracturing (REC with Venting) | tonnes/completion | venting | SKIP | unit basis not covered |
| Well Completion - Oil Well with Hydraulic Fracturing (Uncontrolled Venting) | tonnes/completion | venting | SKIP | unit basis not covered |
| Well Completion - Oil Well with Hydraulic Fracturing (REC with Venting) | tonnes/completion | venting | SKIP | unit basis not covered |
| Well Completion - Gas Well without Hydraulic Fracturing (Vented) | tonnes/completion | - | SKIP | factor selected by the process calculator (events / wells / completions) |
| Well Completion - Oil Well without Hydraulic Fracturing (Vented) | tonnes/completion | - | SKIP | factor selected by the process calculator (events / wells / completions) |
| Liquids Unloading - Plunger Lift (Tier 1 Default) | tonnes CH4/well-year | - | SKIP | factor selected by the process calculator (events / wells / completions) |
| Liquids Unloading - Non-Plunger (Tier 1 Default) | tonnes CH4/well-year | - | SKIP | factor selected by the process calculator (events / wells / completions) |
| Liquids Unloading - Plunger Lift (≤100 events/yr) | tonnes CH4/event | - | SKIP | factor selected by the process calculator (events / wells / completions) |
| Liquids Unloading - Plunger Lift (>100 events/yr) | tonnes CH4/event | - | SKIP | factor selected by the process calculator (events / wells / completions) |
| Liquids Unloading - Non-Plunger (≤10 events/yr) | tonnes CH4/event | - | SKIP | factor selected by the process calculator (events / wells / completions) |
| Liquids Unloading - Non-Plunger (10-50 events/yr) | tonnes CH4/event | - | SKIP | factor selected by the process calculator (events / wells / completions) |
| Liquids Unloading - Non-Plunger (>50 events/yr) | tonnes CH4/event | - | SKIP | factor selected by the process calculator (events / wells / completions) |
| Liquids Unloading - Plunger Lift (Appalachia <100 events/yr) | tonnes CH4/event | - | SKIP | factor selected by the process calculator (events / wells / completions) |
| Liquids Unloading - Plunger Lift (Appalachia >100 events/yr) | tonnes CH4/event | - | SKIP | factor selected by the process calculator (events / wells / completions) |
| Liquids Unloading - Plunger Lift (Gulf Coast <100 events/yr) | tonnes CH4/event | - | SKIP | factor selected by the process calculator (events / wells / completions) |
| Liquids Unloading - Plunger Lift (Gulf Coast >100 events/yr) | tonnes CH4/event | - | SKIP | factor selected by the process calculator (events / wells / completions) |
| Liquids Unloading - Plunger Lift (Midcontinent <100 events/yr) | tonnes CH4/event | - | SKIP | factor selected by the process calculator (events / wells / completions) |
| Liquids Unloading - Plunger Lift (Midcontinent >100 events/yr) | tonnes CH4/event | - | SKIP | factor selected by the process calculator (events / wells / completions) |
| Liquids Unloading - Plunger Lift (Rocky Mountain <100 events/yr) | tonnes CH4/event | - | SKIP | factor selected by the process calculator (events / wells / completions) |
| Liquids Unloading - Plunger Lift (Rocky Mountain >100 events/yr) | tonnes CH4/event | - | SKIP | factor selected by the process calculator (events / wells / completions) |
| Liquids Unloading - Non-Plunger (Appalachia) | tonnes CH4/event | - | SKIP | factor selected by the process calculator (events / wells / completions) |
| Liquids Unloading - Non-Plunger (Gulf Coast) | tonnes CH4/event | - | SKIP | factor selected by the process calculator (events / wells / completions) |
| Liquids Unloading - Non-Plunger (Midcontinent) | tonnes CH4/event | - | SKIP | factor selected by the process calculator (events / wells / completions) |
| Liquids Unloading - Non-Plunger (Rocky Mountain) | tonnes CH4/event | - | SKIP | factor selected by the process calculator (events / wells / completions) |
| Liquids Unloading - Plunger Lift | tonnes CH4/well-year | - | SKIP | factor selected by the process calculator (events / wells / completions) |
| Liquids Unloading - Non-Plunger | tonnes CH4/well-year | - | SKIP | factor selected by the process calculator (events / wells / completions) |
| Natural Gas (Venting/Blowdown) | kg/m³ | venting | PASS | CH4: m3 0.67, scf 0.67, Mcf 0.67, MMscf 0.67 | expected 0.67 |
| Asphalt | kg/ton | asphalt_blowing | PASS | CO2: kg 0.006184, tonne 0.006184, ton 0.006184 | expected 0.006184 |
| Acrylonitrile | tonne CO₂/tonne product | chemical_production | PASS | CO2: kg 1, tonne 1, ton 1 | expected 1 |
| Carbon Black | tonne CO₂/tonne product | chemical_production | PASS | CO2: kg 2.63, tonne 2.63, ton 2.63 | expected 2.63 |
| Ethylene | tonne CO₂/tonne product | chemical_production | PASS | CO2: kg 0.77, tonne 0.77, ton 0.77 | expected 0.77 |
| Ethylene Dichloride | tonne CO₂/tonne product | chemical_production | PASS | CO2: kg 0.041, tonne 0.041, ton 0.041 | expected 0.041 |
| Ethylene Oxide | tonne CO₂/tonne product | chemical_production | PASS | CO2: kg 0.46, tonne 0.46, ton 0.46 | expected 0.46 |
| Methanol | tonne CO₂/tonne product | chemical_production | PASS | CO2: kg 0.67, tonne 0.67, ton 0.67 | expected 0.67 |
| Nitric Acid - With NSCR | kg N₂O/tonne product | chemical_production | PASS | N2O: kg 0.002, tonne 0.002, ton 0.002 | expected 0.002 |
| Nitric Acid - Without NSCR | kg N₂O/tonne product | chemical_production | PASS | N2O: kg 0.009, tonne 0.009, ton 0.009 | expected 0.009 |
| Adipic Acid - Thermal Abatement | kg N₂O/tonne product | chemical_production | PASS | N2O: kg 0.013, tonne 0.013, ton 0.013 | expected 0.013 |
| Adipic Acid - Catalytic Abatement | kg N₂O/tonne product | chemical_production | PASS | N2O: kg 0.053, tonne 0.053, ton 0.053 | expected 0.053 |
| Adipic Acid - Uncontrolled | kg N₂O/tonne product | chemical_production | PASS | N2O: kg 0.3, tonne 0.3, ton 0.3 | expected 0.3 |
| Associated Gas Venting - US Average | kg CH4/bbl | venting | PASS | CH4: gal 0.033333, bbl 0.033333, L 0.033333, m3 0.033333 | expected 0.033333 |
| Associated Gas Venting - Gulf Coast Basin (Basin 220) | kg CH4/bbl | venting | PASS | CH4: gal 0.016667, bbl 0.016667, L 0.016667, m3 0.016667 | expected 0.016667 |
| Associated Gas Venting - Anadarko Basin (Basin 360) | kg CH4/bbl | venting | PASS | CH4: gal 0.23095, bbl 0.23095, L 0.23095, m3 0.23095 | expected 0.23095 |
| Associated Gas Venting - Williston Basin (Basin 395) | kg CH4/bbl | venting | PASS | CH4: gal 0.2119, bbl 0.2119, L 0.2119, m3 0.2119 | expected 0.2119 |
| Associated Gas Venting - Permian Basin (Basin 430) | kg CH4/bbl | venting | PASS | CH4: gal 0.15476, bbl 0.15476, L 0.15476, m3 0.15476 | expected 0.15476 |
| Associated Gas Venting - Other US Basins | kg CH4/bbl | venting | PASS | CH4: gal 0.0095238, bbl 0.0095238, L 0.0095238, m3 0.0095238 | expected 0.0095238 |
| Pneumatic Controller - High Bleed (>6 scfh) | tonnes CH₄/yr | combustion | SKIP | unit basis not covered |
| Pneumatic Controller - Low Bleed (<6 scfh) | tonnes CH₄/yr | combustion | SKIP | unit basis not covered |
| Pneumatic Controller - Intermittent | tonnes CH₄/yr | combustion | SKIP | unit basis not covered |
| Pneumatic Controller - Continuous Vent (T&S) | tonnes CH₄/yr | combustion | SKIP | unit basis not covered |
| Tank - Flash Emissions (Oil) | kg/bbl | tank_flashing | PASS | CH4: gal 0.0045952, bbl 0.0045952, L 0.0045952, m3 0.0045952 | expected 0.0045952 |
| Tank - Crude Oil (Small, ≤10 bbl/d) | kg CH₄/bbl | tank_flashing | PASS | CH4: gal 0.0042857, bbl 0.0042857, L 0.0042857, m3 0.0042857 | expected 0.0042857 |
| Tank - Crude Oil (Large, >10 bbl/d) | kg CH₄/bbl | tank_flashing | PASS | CH4: gal 0.0045952, bbl 0.0045952, L 0.0045952, m3 0.0045952 | expected 0.0045952 |
| Tank - Production Condensate (Small, ≤10 bbl/d) | kg CH₄/bbl | tank_flashing | PASS | CH4: gal 0.037143, bbl 0.037143, L 0.037143, m3 0.037143 | expected 0.037143 |
| Tank - Production Condensate (Large, >10 bbl/d) | kg CH₄/bbl | tank_flashing | PASS | CH4: gal 0.027619, bbl 0.027619, L 0.027619, m3 0.027619 | expected 0.027619 |
| Tank - Gas-Well Condensate (Small, ≤10 bbl/d) | kg CH₄/bbl | tank_flashing | PASS | CH4: gal 0.063095, bbl 0.063095, L 0.063095, m3 0.063095 | expected 0.063095 |
| Tank - Gas-Well Condensate (Large, >10 bbl/d) | kg CH₄/bbl | tank_flashing | PASS | CH4: gal 0.04881, bbl 0.04881, L 0.04881, m3 0.04881 | expected 0.04881 |
| Drilling - Mud Degassing (Water Based) | kg CH₄/m³ | combustion | PASS | CH4: m3 0.15, scf 0.15, Mcf 0.15, MMscf 0.15 | expected 0.15 |
| Drilling - Mud Degassing (Oil Based) | kg CH₄/bbl mud | tank_flashing | PASS | CH4: gal 0.89286, bbl 0.89286, L 0.89286, m3 0.89286 | expected 0.89286 |
| Dehydrator - Glycol (Uncontrolled) | scf/MMscf | combustion | SKIP | unit basis not covered |
| Wellhead - Oil (Heavy Crude) | tonne CH4/well/hr | fugitive | PASS | 10 sources x 8760 h: CH4 0.058079 vs 0.058079 |
| Wellhead - Oil (Light Crude) | tonne CH4/well/hr | fugitive | PASS | 10 sources x 8760 h: CH4 1.3666 vs 1.3666 |
| Wellhead - Gas | tonne CH4/well/hr | fugitive | PASS | 10 sources x 8760 h: CH4 1.5768 vs 1.5768 |
| Separator - Heavy Crude | tonne CH4/separator/hr | fugitive | PASS | 10 sources x 8760 h: CH4 0.05948 vs 0.05948 |
| Separator - Light Crude | tonne CH4/separator/hr | fugitive | PASS | 10 sources x 8760 h: CH4 3.5916 vs 3.5916 |
| Separator - Gas Production | tonne CH4/separator/hr | fugitive | PASS | 10 sources x 8760 h: CH4 3.8719 vs 3.8719 |
| Compressor - Small Reciprocating | tonne CH4/compressor/hr | fugitive | PASS | 10 sources x 8760 h: CH4 3.2324 vs 3.2324 |
| Compressor - Large Reciprocating | tonne CH4/compressor/hr | fugitive | PASS | 10 sources x 8760 h: CH4 1147.6 vs 1147.6 |
| Compressor - Gas Production Small Recip | tonne CH4/compressor/hr | fugitive | PASS | 10 sources x 8760 h: CH4 18.571 vs 18.571 |
| Compressor - Gas Production Large Recip | tonne CH4/compressor/hr | fugitive | PASS | 10 sources x 8760 h: CH4 1068.7 vs 1068.7 |
| Gathering - AGRU | tonne CH₄/unit/hr | fugitive | PASS | 10 sources x 8760 h: CH4 5.9831 vs 5.9831 |
| Gathering - Compressor | tonne CH4/unit/hr | fugitive | PASS | 10 sources x 8760 h: CH4 161.18 vs 161.18 |
| Gathering - Dehydrator | tonne CH₄/unit/hr | fugitive | PASS | 10 sources x 8760 h: CH4 4.9844 vs 4.9844 |
| Gathering - Separator | tonne CH₄/unit/hr | fugitive | PASS | 10 sources x 8760 h: CH4 0.9198 vs 0.9198 |
| Gathering - Tank | tonne CH₄/unit/hr | fugitive | PASS | 10 sources x 8760 h: CH4 56.064 vs 56.064 |
| Component - Connector (Non-Compressor) | tonne CH₄/hr/source | fugitive | PASS | 10 sources x 8760 h: CH4 0.08576 vs 0.08576 |
| Component - Block Valve | tonne CH₄/hr/source | fugitive | PASS | 10 sources x 8760 h: CH4 0.38194 vs 0.38194 |
| Component - Control Valve | tonne CH₄/hr/source | fugitive | PASS | 10 sources x 8760 h: CH4 0.97236 vs 0.97236 |
| Component - Pressure Relief Valve | tonne CH₄/hr/source | fugitive | PASS | 10 sources x 8760 h: CH4 0.012176 vs 0.012176 |
| Component - Pressure Regulator | tonne CH₄/hr/source | fugitive | PASS | 10 sources x 8760 h: CH4 0.16381 vs 0.16381 |
| Component - Compressor Seal | tonne CH₄/hr/source | fugitive | PASS | 10 sources x 8760 h: CH4 13.49 vs 13.49 |
| Processing - Reciprocating Compressor | tonne CH₄/compressor/hr | fugitive | PASS | 10 sources x 8760 h: CH4 784.02 vs 784.02 |
| Processing - Centrifugal Compressor | tonne CH₄/compressor/hr | fugitive | PASS | 10 sources x 8760 h: CH4 1489.2 vs 1489.2 |
| LNG - Storage Station | tonne CH₄/facility | fugitive | SKIP | unit basis not covered |
| LNG - Import Terminal | tonne CH₄/facility | fugitive | SKIP | unit basis not covered |
| LNG - Export Terminal | tonne CH₄/facility | fugitive | SKIP | unit basis not covered |
| Refinery - Fuel Gas System (50-99k bbl/day) | tonnes CH₄/10³ bbl feedstock | combustion | SKIP | unit basis not covered |
| Refinery - Fuel Gas System (100-199k bbl/day) | tonnes CH₄/10³ bbl feedstock | combustion | SKIP | unit basis not covered |
| Offshore - Oil Production (Facility) | tonne CH₄/bbl produced | tank_flashing | PASS | CH4: gal 9.1905e-05, bbl 9.1905e-05, L 9.1905e-05, m3 9.1905e-05 | expected 9.1905e-05 |
| Offshore - Gas Production (Facility) | tonne CH₄/10⁶ scf produced | combustion | PASS | CH4: m3 0.00036727, scf 0.00036727, Mcf 0.00036727, MMscf 0.00036727 | expected 0.00036727 |
| Facility - Onshore Oil Production (Table 7-8) | tonne CH4/bbl | tank_flashing | PASS | CH4: gal 0.0055857, bbl 0.0055857, L 0.0055857, m3 0.0055857 | expected 0.0055857 |
| Facility - Onshore Gas Production (Table 7-8) | tonne CH4/10^6 scf | fugitive | PASS | CH4: m3 0.00091853, scf 0.00091853, Mcf 0.00091853, MMscf 0.00091853 | expected 0.00091853 |
| Heater-Treater - Light Crude | tonne CH4/heater/hr | fugitive | PASS | 10 sources x 8760 h: CH4 4.1785 vs 4.1785 |
| Header - Heavy Crude | tonne CH4/header/hr | fugitive | PASS | 10 sources x 8760 h: CH4 0.041347 vs 0.041347 |
| Header - Light Crude | tonne CH4/header/hr | fugitive | PASS | 10 sources x 8760 h: CH4 14.191 vs 14.191 |
| Storage Tank Fugitive - Light Crude | tonne CH4/tank/hr | fugitive | PASS | 10 sources x 8760 h: CH4 2.409 vs 2.409 |
| Heater - Gas Production | tonne CH4/heater/hr | fugitive | PASS | 10 sources x 8760 h: CH4 4.0296 vs 4.0296 |
| Gas Dehydrator Unit - Fugitive Leaks | tonne CH4/unit/hr | fugitive | PASS | 10 sources x 8760 h: CH4 6.2459 vs 6.2459 |
| Meter / Piping Run - Gas Production | tonne CH4/run/hr | fugitive | PASS | 10 sources x 8760 h: CH4 3.0835 vs 3.0835 |
| Component - Valve (Gas Service) | kg TOC/hr/component | fugitive | PASS | 10 sources x 8760 h: CH4 0.00033507 vs 0.00033507 |
| Component - Valve (Light Oil Service) | kg TOC/hr/component | fugitive | PASS | 10 sources x 8760 h: CH4 0.0001314 vs 0.0001314 |
| Component - Valve (Heavy Oil Service) | kg TOC/hr/component | fugitive | PASS | 10 sources x 8760 h: CH4 1.1038e-07 vs 1.1038e-07 |
| Component - Valve (Water/Oil Service) | kg TOC/hr/component | fugitive | PASS | 10 sources x 8760 h: CH4 8.5848e-07 vs 8.5848e-07 |
| Component - Pump Seal (Light Oil Service) | kg TOC/hr/component | fugitive | PASS | 10 sources x 8760 h: CH4 0.00068328 vs 0.00068328 |
| Component - Pump Seal (Heavy Oil Service) | kg TOC/hr/component | fugitive | PASS | 10 sources x 8760 h: CH4 4.2048e-07 vs 4.2048e-07 |
| Component - Pump Seal (Water/Oil Service) | kg TOC/hr/component | fugitive | PASS | 10 sources x 8760 h: CH4 2.1024e-07 vs 2.1024e-07 |
| Component - Connector (Gas Service) | kg TOC/hr/component | fugitive | PASS | 10 sources x 8760 h: CH4 1.4892e-05 vs 1.4892e-05 |
| Component - Connector (Light Oil Service) | kg TOC/hr/component | fugitive | PASS | 10 sources x 8760 h: CH4 1.1038e-05 vs 1.1038e-05 |
| Component - Connector (Heavy Oil Service) | kg TOC/hr/component | fugitive | PASS | 10 sources x 8760 h: CH4 9.855e-08 vs 9.855e-08 |
| Component - Connector (Water/Oil Service) | kg TOC/hr/component | fugitive | PASS | 10 sources x 8760 h: CH4 9.636e-07 vs 9.636e-07 |
| Component - Flange (Gas Service) | kg TOC/hr/component | fugitive | PASS | 10 sources x 8760 h: CH4 2.9039e-05 vs 2.9039e-05 |
| Component - Flange (Light Oil Service) | kg TOC/hr/component | fugitive | PASS | 10 sources x 8760 h: CH4 5.7816e-06 vs 5.7816e-06 |
| Component - Flange (Heavy Oil Service) | kg TOC/hr/component | fugitive | PASS | 10 sources x 8760 h: CH4 5.1246e-09 vs 5.1246e-09 |
| Component - Flange (Water/Oil Service) | kg TOC/hr/component | fugitive | PASS | 10 sources x 8760 h: CH4 2.5404e-08 vs 2.5404e-08 |
| Component - Open-Ended Line (Gas Service) | kg TOC/hr/component | fugitive | PASS | 10 sources x 8760 h: CH4 0.00014892 vs 0.00014892 |
| Component - Open-Ended Line (Light Oil Service) | kg TOC/hr/component | fugitive | PASS | 10 sources x 8760 h: CH4 7.3584e-05 vs 7.3584e-05 |
| Component - Open-Ended Line (Heavy Oil Service) | kg TOC/hr/component | fugitive | PASS | 10 sources x 8760 h: CH4 1.8396e-06 vs 1.8396e-06 |
| Component - Open-Ended Line (Water/Oil Service) | kg TOC/hr/component | fugitive | PASS | 10 sources x 8760 h: CH4 2.19e-06 vs 2.19e-06 |
| Component - Other / PRV (Gas Service) | kg TOC/hr/component | fugitive | PASS | 10 sources x 8760 h: CH4 0.00065525 vs 0.00065525 |
| Component - Other / PRV (Light Oil Service) | kg TOC/hr/component | fugitive | PASS | 10 sources x 8760 h: CH4 0.0003942 vs 0.0003942 |
| Component - Other / PRV (Heavy Oil Service) | kg TOC/hr/component | fugitive | PASS | 10 sources x 8760 h: CH4 4.2048e-07 vs 4.2048e-07 |
| Component - Other / PRV (Water/Oil Service) | kg TOC/hr/component | fugitive | PASS | 10 sources x 8760 h: CH4 1.2264e-06 vs 1.2264e-06 |
| Gathering - Pipeline | tonne CH4/km/hr | fugitive | PASS | 10 km x 8760 h: CH4 3.942 vs 3.942 |
| Component - Block Valve (Gathering) | tonne CH4/hr/source | fugitive | PASS | 10 sources x 8760 h: CH4 0.38194 vs 0.38194 |
| Component - Control Valve (Gathering) | tonne CH4/hr/source | fugitive | PASS | 10 sources x 8760 h: CH4 0.97236 vs 0.97236 |
| Component - Connector (Gathering) | tonne CH4/hr/source | fugitive | PASS | 10 sources x 8760 h: CH4 0.08576 vs 0.08576 |
| Component - Flange (Gathering) | tonne CH4/hr/source | fugitive | PASS | 10 sources x 8760 h: CH4 0.09198 vs 0.09198 |
| Component - Pressure Relief Valve (Gathering) | tonne CH4/hr/source | fugitive | PASS | 10 sources x 8760 h: CH4 0.012176 vs 0.012176 |
| Component - Pressure Regulator (Gathering) | tonne CH4/hr/source | fugitive | PASS | 10 sources x 8760 h: CH4 0.16381 vs 0.16381 |
| Component - Compressor Seal (Gathering) | tonne CH4/hr/source | fugitive | PASS | 10 sources x 8760 h: CH4 13.49 vs 13.49 |
| Component - Open-Ended Line (Gathering) | tonne CH4/hr/source | fugitive | PASS | 10 sources x 8760 h: CH4 1.0512 vs 1.0512 |

## 4. Defects found and fixed

- Dehydrator throughput-only factor 0.266 t CH4/MMscf had no source; API Table 6-17 = 0.0052859 t CH4/MMscf (78.8 % basis, scaled by site CH4) - Exhibit 6-13 now 50.19 vs 50.2 t (was 2,427 t)
- Asphalt blowing catalog factor: CO2 10.43 kg/ton, CH4 0.0227 kg/ton vs Table 6-52 5.61 / 3.07 kg/ton - corrected (server and client catalogs); Exhibit 6-45 561 / 307 t
- Tier 3 completions: the flowback volume unit came from the record unit ("events") and anything unrecognised silently became m3 (x35 on scf input); now reads volume_unit and rejects unknown units; form keeps volume_unit explicitly
- Completions flaring ignored non-methane hydrocarbons in flared CO2 (Exhibit 6-3 counts the rest of the gas as ethane): new optional C2+ content (ethane-equivalent), field added to the Tier 3 form - Exhibit 6-3 CO2 98.88 vs 98.7 t (was 53.25)
- Hydrogen plant rigorous methods (Eq 6-49 feedstock balance, Eq 6-50 H2 stoichiometry) existed in the calculator but were unreachable - routed when feed composition is given (Exhibits 6-42 / 6-43 within 0.2 %)
- Catalog "Ethane" is liquid ethane (HHV per gal) but was typed as a gas; retyped and "Ethane (Gas)" added with API Table 3-7 HHV 1768.8 Btu/scf


## 5. Onshore upstream / midstream exhibits added (2026-09-28)

Scope chosen by the user: onshore upstream + midstream (offshore 7-1..7-3, marine 6-36/6-37, refining,
wastewater and HFC/SF6 excluded). Each exhibit is now a regression case in
`new/server/tests/test_onshore_exhibits.py`, run through resolve_factor + compute_emissions (the POST path).
Inputs are the exhibits' stated inputs; expected values are the printed answers.

| Exhibit | Method (process / key) | Engine (t) | Compendium (t) |
|---|---|---|---|
| 6-2 | well_testing, gas volume from GOR x oil rate x hours | CH4 9.885 · CO2 3.873 | 9.84 · 3.87 |
| 6-5 | vented_gas volume, vented / flared (C2+ as ethane) | 328.1 · 110.6; flared CO2 1,054 · CH4 6.912 | 327 · 110; 1,050 · 6.9 |
| 6-7 | workovers, Table 6-9 | 0.4175 · 0.1477 | 0.42 · 0.15 |
| 6-9 | casing_gas, Table 6-12 | 102.7 · 36.35 | 102.7 · 36.3 |
| 6-10 | casing_gas, CAPP migration | 2.001 · 0.7061 | 2.00 · 0.71 |
| 6-14 | dehydrator Tier 1, Kimray Table 6-18 | 180.7 · 30.25 | 180.7 · 30.3 |
| 6-15 | desiccant_dehydrator, Eq 6-16 | 0.1646 · 0.02508 | 0.16 · 0.025 |
| 6-16 | agr Tier 1, per AGR unit (Table 6-19) | 236.6 | 236.6 |
| 6-17 | agr, sour / sweet balance (Eq 6-18) | CO2 80,630 · CH4 2,775 | 80,506 · 2,775 |
| 6-22 | co2_eor, Eq 6-20 | 23.31 | 23 |
| 6-23 | pneumatic Tier 1, G&B Table 6-29 | 86.05 · 30.35 | 85.7 · 30.3 |
| 6-24 | compressor_venting, GHGRP rod packing | 0.623 · 0.2201 | 0.62 · 0.22 |
| 6-26 | non_routine_venting, Table 6-32 | vessel 0.00666 · 0.00209; compressor 0.0643 · 0.0202; pipeline 0.0263 · 0.00826 | 0.007 · 0.002; 0.064 · 0.020; 0.026 · 0.008 |
| 6-27 | non_routine_venting, Table 6-33 | 0.0039; 0.0768; 0.16; 0.00071 | 0.0039; 0.077; 0.16; 0.00071 |
| 6-28 | dehydrator Tier 1, Tables 6-35 / 6-36 | 22.06; 32.26 · 4.929 | 22.06; 32.26 · 4.93 |
| 6-29 | tank, actual volume at 75 F -> standard | 2.751 · 0.0920 | 2.74 · 0.09 |
| 6-30 | non_routine_venting, per 10^6 m3 (Table 6-39) | 908.1 | 908 |
| 6-31 | compressor_venting, Table 6-40 | 181.2 + 20.97 | 180.5 + 20.9 |
| 6-32 | compressor_venting, Table 6-41 | 491.8 + 102.5 | 491.1 + 102.2 |
| 6-33 | non_routine_venting, Table 6-43 | 108; 30.68 | 108; 31 |
| 6-34 | non_routine_venting, Table 6-46 | 0.008685; 0.06825; 0.644; 0.608; 0.0192 | 0.0087; 0.068; 0.64; 0.61; 0.02 |
| 6-35 | loading, Table 6-47 (TOC x 12 wt % CH4) | 0.5544 | 0.554 |
| 7-5 | fugitive correlation (Tables 7-40/41/42) | 0.4704 | 0.47 |
| 4.5 | combustion, carbon content | 50,930 | 50,966 |
| 4.7 | combustion, equipment basis (Table 4-9) | CH4 0.8256 · N2O 0.2312 | 0.83 · 0.23 |
| 4.8 | combustion, equipment basis (Table 4-11) | 0.6221 · 0.003024 | 0.62 · 0.00303 |
| 4.12 | mobile, distance / fuel economy | 1,297 · 0.04773 · 0.06477 | 1,297 · 0.048 · 0.064 |
| 5.2 | flaring, back-calculated from VOC emitted | 516.3 · 1.027 | 515.7 · 1.03 |
| 5.3 | thermal_oxidizer | 338.7 · 0.08524 | 338.9 · 0.085 |

Differences come from rounding in the printed answers, the exhibits' 379.3 scf/lbmol and 44/12 against the
engine's gas densities and 44.01/12.011 (about 0.4 %), and exhibits that round an intermediate (6-23 uses 7.45 scf/h CH4).

Defects found while adding these:

- Correlation approach (Tables 7-40/41/42): pegged rates were wrong (pump seals 0.16 / 0.68 vs 0.074 / 0.160;
  valves 100k 0.11 vs 0.140; flanges 100k 0.089 vs 0.084; open-ended lines 0.012 / 0.014 vs 0.030 / 0.079), default-zero
  rates were missing, the CH4 fraction defaulted to 0.85 mol instead of 0.564 wt (Table C-1), an unknown component
  silently used the gas-valve curve, `fugitive_method: "correlation"` never reached the correlation branch, and the
  form's `correlation_type` and equation labels did not match any table. All fixed; the form takes non-detect,
  screened and pegged counts.
- Exhibit 4.12 multiplies by 0.0822 t CO2/MMBtu for diesel; Table 4-5 (Part 98) gives 73.96 kg/MMBtu, which is the
  engine default. The test passes the exhibit's own factor and HHV (5.83 MMBtu/bbl) as overrides.
- Tables 4-12 and 4-16 (fuel economy, per-vehicle CH4 / N2O) do not extract with their row labels aligned, so only
  the heavy-duty diesel advanced-control row used by Exhibit 4.12 is built in; other vehicles take user-entered
  factors or the Table 4-6 fuel-basis CH4 / N2O.
