# GHG Accounting Software - Phase 0 Comprehensive Audit Manifest

> **Generated for Audit Execution**
> **Standards & Methodologies**: API Compendium (2021), GHG Protocol Corporate Standard, ISO 14064-1
> **Software Architecture**: Flask 3 + SQLAlchemy (SQLite) Backend, React 18 / Vite Frontend

---

## 1. Process Types, Emission Sources, and Categories per Scope

### Scope 1: Direct GHG Emissions
- **Major Emission Categories**: 4 (Combustion, Vented, Fugitive, Process)
- **Standard Process Types (`process_categories.py`)**: 29 types
  - **Combustion** (6 types): `stationary_combustion` (Stationary Combustion), `flaring` (Flaring), `routine_flaring` (Routine Flaring), `non_routine_flaring` (Non-Routine Flaring), `safety_flaring` (Safety Flaring), `mobile_combustion` (Mobile Combustion)
  - **Fugitive Emissions** (10 types): `wellhead_fugitive` (Wellhead Fugitive Emissions), `separator_fugitive` (Separator Fugitive Emissions), `gathering_boosting` (Gathering & Boosting), `gas_processing` (Natural Gas Processing), `transmission_storage` (Transmission & Storage), `compressor_fugitive` (Compressor Fugitive Emissions), `refinery_fugitive` (Refinery Gas Systems), `distribution_fugitive` (Natural Gas Distribution), `lng_operations` (LNG Operations), `fugitive_component` (Fugitive - Component Level)
  - **Process Emissions** (4 types): `chemical_production` (Chemical Production (Process CO₂)), `nitric_acid_production` (Nitric Acid Production (N₂O)), `adipic_acid_production` (Adipic Acid Production (N₂O)), `asphalt_blowing` (Asphalt Blowing)
  - **Vented Emissions** (9 types): `associated_gas_venting` (Associated Gas Venting), `drilling` (Drilling - Mud Degassing), `completions` (Well Completions & Workovers), `liquids_unloading` (Liquids Unloading), `storage_tanks` (Storage Tanks), `pneumatic_devices` (Pneumatic Devices), `blowdown` (Blowdown Events), `dehydrator` (Glycol Dehydrator), `acid_gas_removal` (Acid Gas Removal (AGR))
- **Dispatcher Registered Process Keys / Aliases**: 109 active routes
  - Keys: `acid_gas_removal, adipic_acid_production, agr, air_conditioning, asphalt, asphalt_blowing, associated_gas, associated_gas_venting, associated_venting, blowdown, casing_gas, catalyst_regen, ccus_venting, chemical_production, co2_eor, cogen, cogen_allocation, coke_calcining, combustion, completion_flowback, completions, component_fugitive, compressor_fugitive, compressor_seal, compressor_venting, crude_loading, crude_transport, dehydrator, delayed_coker, desiccant_dehydrator, distribution_fugitive, distribution_non_routine, distribution_pneumatics, drilling, electrical_equipment, electrical_transmission, equipment_fugitive, facility_fugitive, fccu_regen, fire_suppression, flare, flaring, fugitive, fugitive_component, fugitive_facility, fugitive_measurement, fugitive_ogi, fugitive_screening, gas_processing, gathering_boosting, gathering_compressor, gathering_non_routine, gathering_tank, hfc, hydrogen_plant, hydrogen_production, indirect_steam, liquids_unloading, lng_operations, lng_venting, loading, mobile, mobile_combustion, mud_degassing, nitric_acid_production, non_routine_flaring, non_routine_venting, petrochemical, petrochemical_manufacturing, pneumatic, pneumatic_device, pneumatic_devices, pneumatics, processing_blanketed_tank, processing_dehydration, processing_non_routine, refinery_fugitive, refining_coke_calcining, refining_coker, refrigerant, refrigerants, refrigeration, routine_flaring, safety_flaring, separator_fugitive, sf6, smr_hydrogen, sru, stationary_combustion, stoichiometry, storage_tanks, sulfur_recovery, tail_gas, tank, tank_breathing, tank_flashing, tank_working, thermal_oxidizer, transmission_compressor, transmission_non_routine, transmission_storage, unloading, vented_gas, venting, wastewater, wastewater_treatment, well_testing, wellhead_fugitive, workovers`

### Scope 2: Indirect Emissions from Purchased Energy
- **Source Types**: 4 types
  1. `electricity`: Grid electricity consumption (Location-based via eGRID/national grids, Market-based via supplier factors/RECs)
  2. `indirect_steam`: Purchased steam/district heating
  3. `cogen_allocation`: Combined heat and power (CHP) proportional allocation
  4. `cooling`: Purchased chilled water / refrigeration

### Scope 3: Value Chain Indirect Emissions
- **Categories**: 15 GHG Protocol Corporate Value Chain (Scope 3) standard categories
  - 1. Purchased Goods and Services
  - 2. Capital Goods
  - 3. Fuel- and Energy-Related Activities (not included in Scope 1 or Scope 2)
  - 4. Upstream Transportation and Distribution
  - 5. Waste Generated in Operations
  - 6. Business Travel
  - 7. Employee Commuting
  - 8. Upstream Leased Assets
  - 9. Downstream Transportation and Distribution
  - 10. Processing of Sold Products
  - 11. Use of Sold Products
  - 12. End-of-Life Treatment of Sold Products
  - 13. Downstream Leased Assets
  - 14. Franchises
  - 15. Investments

---

## 2. Input Fields per Process Type per Tier

### Field Definitions from `services/scope1_template.py`

#### Core Fields (Required for All Process Types across all Tiers)
- `date`: Required=True, Choices=None. Description: Month of the activity: YYYY-MM (e.g. 2024-03). Rows dated EXAMPLE are not imported.
- `facility_name`: Required=True, Choices=None. Description: Facility name exactly as in Manage Data (see the list).
- `process_type`: Required=True, Choices=None. Description: Process key from the list (e.g. combustion, flaring, tank_flashing).
- `fuel`: Required=False, Choices=None. Description: Fuel or factor name from the list for this process. Tier 2: your saved custom factor name. Leave blank for Tier 3 methods without a factor (e.g. completions).
- `quantity`: Required=True, Choices=None. Description: Activity of the month as a plain number (no unit, no text).
- `unit`: Required=True, Choices=None. Description: Unit of quantity (see the list for this process). Write tonne or short_ton, never ton.
- `tier`: Required=False, Choices=('1', '2', '3'). Description: 1 = catalog factor, 2 = custom factor or site HHV / density, 3 = engineering inputs. Not needed when you choose one tier for the whole file in the import wizard.

#### Identification / Metadata Fields
- `equipment_id`: Required=False. Description: Your tag for the source (e.g. EQ-001). Recommended: keeps two sources apart in the same month.
- `group`: Required=False. Description: Optional grouping for reports (e.g. Compressor Station A).
- `source_ref`: Required=False. Description: Optional meter, survey or document reference.

#### Tier 2 Fields (Custom Factor / Measured Fuel Properties)
- `hhv`: Required=False, Choices=None. Description: Tier 2: your measured heating value, in hhv_unit.
- `hhv_unit`: Required=False, Choices=('Btu/scf', 'Btu/gal', 'MJ/m3', 'MJ/kg', 'kcal/m3', 'MMBtu/bbl'). Description: Unit of hhv.
- `density`: Required=False, Choices=None. Description: Tier 2: fuel density, needed when the quantity is a mass and the factor a volume (or the reverse).
- `density_unit`: Required=False, Choices=('kg/m3', 'kg/L', 'g/cm3', 'lb/gal', 'lb/ft3'). Description: Unit of density.

#### Activity Time Fields
- `operating_hours`: Processes=['compressor_venting', 'fugitive', 'pneumatic']. Description: Hours in the month (e.g. 744) for factors per hour: pneumatic devices, leaks, compressors.
- `activity_days`: Processes=['agr', 'casing_gas']. Description: Days in the month for factors per unit-day (AGR units, casing gas wells).

#### Tier 3 Engineering Fields by Process Type
- Total Tier 3 Specialized Process Schemas: 21
##### Process: `agr` (6 Tier 3 fields)
  - `agr_co2_in`: CO2 mol % in the feed gas.
  - `agr_co2_out`: CO2 mol % in the sweet gas.
  - `agr_unit`, Choices=('MMscf', 'scf', 'm3'): Unit of the throughput. Blank = MMscf.
  - `agr_ch4_in`: CH4 mol % in the feed gas. Blank = 85 %.
  - `agr_ch4_slip`: CH4 slip as a fraction of the inlet CH4 (0-1).
  - `agr_control_eff`: % of the acid gas destroyed. Blank = 0.
##### Process: `associated_gas_venting` (12 Tier 3 fields)
  - `vent_volume`: Measured vented gas volume (method 1).
  - `vent_volume_unit`, Choices=('scf', 'Mscf', 'MMscf', 'm3', 'Sm3', 'Nm3'): Unit of vent_volume.
  - `vent_rate`: Vent rate (method 2), with venting_duration.
  - `vent_rate_unit`, Choices=('scf/hr', 'm3/hr', 'Mcf/day', 'm3/day'): Unit of vent_rate.
  - `venting_duration`: Hours (vent rate) or days (oil production) of venting in the month.
  - `oil_production`: Oil production rate (method 3), with gor and venting_duration.
  - `oil_unit`, Choices=('bbl/day', 'm3/day', 'gal/day'): Unit of oil_production.
  - `gor`: Gas-to-oil ratio.
  - `gor_unit`, Choices=('scf/bbl', 'm3/m3'): Unit of gor.
  - `region`: Basin of the factor table (e.g. Gulf Coast). The record keeps the facility region.
  - `ch4_content`: CH4 mol % of the gas.
  - `co2_content`: CO2 mol % of the gas.
##### Process: `casing_gas` (4 Tier 3 fields)
  - `vent_method`, Choices=('volume',): volume: quantity is the measured vented gas volume.
  - `disposition`, Choices=('vented', 'flared'): Blank = vented; flared applies a 98 % combustion efficiency.
  - `ch4_content`: CH4 mol % of the gas.
  - `co2_content`: CO2 mol % of the gas.
##### Process: `combustion` (13 Tier 3 fields)
  - `c1`: Methane mol % of the gas.
  - `c2`: Ethane mol %.
  - `c3`: Propane mol %.
  - `c4`: Butane mol %.
  - `c5`: Pentane mol %.
  - `c6`: Hexane mol %.
  - `c7`: Heptane mol %.
  - `c8`: Octane mol %.
  - `c9`: Nonane mol %.
  - `c10`: Decane+ mol %.
  - `co2_mol`: CO2 mol % of the gas.
  - `n2_mol`: Nitrogen mol % of the gas.
  - `combustion_efficiency`: Combustion: % of carbon oxidised. Blank = 99.5 %.
##### Process: `completions` (9 Tier 3 fields)
  - `comp_method`, Choices=('metered_volume', 'rate_duration', 'gor_liquid'): Blank = metered_volume (quantity = flowback gas volume).
  - `comp_rate`: rate_duration: flowback gas rate.
  - `comp_rate_unit`, Choices=('Mcf/hr', 'Mcf/day', 'scf/hr', 'm3/hr'): Unit of comp_rate. Blank = Mcf/hr.
  - `comp_duration`: rate_duration: flowback hours.
  - `comp_liquid_bbl`: gor_liquid: flowback liquid (bbl).
  - `comp_gor`: gor_liquid: gas-to-oil ratio (scf/bbl).
  - `comp_flare_eff`: % of the flowback gas flared or controlled.
  - `ch4_content`: CH4 mol % of the gas.
  - `co2_content`: CO2 mol % of the gas.
##### Process: `compressor_venting` (4 Tier 3 fields)
  - `vent_method`, Choices=('volume',): volume: quantity is the measured vented gas volume.
  - `disposition`, Choices=('vented', 'flared'): Blank = vented; flared applies a 98 % combustion efficiency.
  - `ch4_content`: CH4 mol % of the gas.
  - `co2_content`: CO2 mol % of the gas.
##### Process: `dehydrator` (12 Tier 3 fields)
  - `vent_method`, Choices=('volume',): volume: quantity is the measured vented gas volume.
  - `disposition`, Choices=('vented', 'flared'): Blank = vented; flared applies a 98 % combustion efficiency.
  - `ch4_content`: CH4 mol % of the gas.
  - `co2_content`: CO2 mol % of the gas.
  - `dehy_pump_rate`: Glycol circulation rate.
  - `dehy_pump_unit`, Choices=('gph', 'lph'): Unit of dehy_pump_rate. Blank = gph.
  - `dehy_hours`: Operating hours. Blank = 8760.
  - `dehy_ch4_content`: CH4 mol % of the feed gas. Blank = 85 %.
  - `dehy_has_flash`, Choices=('true', 'false'): Flash tank fitted. Blank = true.
  - `dehy_flash_eff`: % of the flash tank vapour recovered.
  - `dehy_still_type`, Choices=('none', 'condenser', 'fired_reboiler'): Still vent control.
  - `dehy_eff`: % overall control. Blank = 0.
##### Process: `drilling` (1 Tier 3 fields)
  - `mud_type`, Choices=('water_based', 'oil_based', 'synthetic'): Drilling mud (quantity = drilling days).
##### Process: `flaring` (15 Tier 3 fields)
  - `c1`: Methane mol % of the gas.
  - `c2`: Ethane mol %.
  - `c3`: Propane mol %.
  - `c4`: Butane mol %.
  - `c5`: Pentane mol %.
  - `c6`: Hexane mol %.
  - `c7`: Heptane mol %.
  - `c8`: Octane mol %.
  - `c9`: Nonane mol %.
  - `c10`: Decane+ mol %.
  - `co2_mol`: CO2 mol % of the gas.
  - `n2_mol`: Nitrogen mol % of the gas.
  - `flare_type`, Choices=('elevated', 'enclosed_ground', 'offshore_boom', 'air_assisted', 'steam_assisted'): Flare design. Blank = elevated.
  - `combustion_efficiency`: Flaring: % of carbon converted to CO2. Blank = 96.5 %.
  - `destruction_efficiency`: Flaring: % of CH4 destroyed. Blank = 98 % (99.5 % at Downstream facilities).
##### Process: `fugitive` (11 Tier 3 fields)
  - `ch4_content`: CH4 mol % of the gas.
  - `co2_content`: CO2 mol % of the gas.
  - `fugitive_method`, Choices=('screening', 'correlation', 'ogi', 'measurement', 'component'): Leak method.
  - `component_type`, Choices=('valve', 'connector', 'flange', 'open_ended_line', 'pump_seal', 'other'): Component type.
  - `service`, Choices=('gas', 'light_oil', 'heavy_oil', 'water_oil'): Service.
  - `m21_below_count`: screening: components below 10,000 ppmv.
  - `m21_above_count`: screening: components at or above 10,000 ppmv.
  - `leakers_count`: ogi: number of leaking components.
  - `measured_rate`: measurement: measured leak rate.
  - `rate_unit`, Choices=('kg/hr', 'lb/hr', 'g/s', 'scf/hr', 'm3/hr'): Unit of measured_rate.
  - `operating_hours`: Hours in the month (e.g. 744).
##### Process: `non_routine_venting` (4 Tier 3 fields)
  - `vent_method`, Choices=('volume',): volume: quantity is the measured vented gas volume.
  - `disposition`, Choices=('vented', 'flared'): Blank = vented; flared applies a 98 % combustion efficiency.
  - `ch4_content`: CH4 mol % of the gas.
  - `co2_content`: CO2 mol % of the gas.
##### Process: `pneumatic` (5 Tier 3 fields)
  - `pneu_count`: Number of devices.
  - `pneu_bleed_rate`: Measured bleed rate per device.
  - `pneu_bleed_unit`, Choices=('scf/hr', 'm3/hr'): Unit of pneu_bleed_rate. Blank = scf/hr.
  - `pneu_hours`: Operating hours per device in the month (e.g. 744).
  - `pneu_ch4_content`: CH4 mol % of the supply gas. Blank = 85 %.
##### Process: `stoichiometry` (1 Tier 3 fields)
  - `carbon_content`: Carbon mass fraction of the fuel (0-1, e.g. 0.75).
##### Process: `tank_breathing` (5 Tier 3 fields)
  - `tank_gor`: Flash gas-to-oil ratio (scf/bbl).
  - `tank_ch4_content`: CH4 mol % of the flash gas.
  - `tank_control_eff`: % of the vapour recovered or destroyed.
  - `tank_unit`, Choices=('bbl', 'm3', 'gal', 'L'): Unit of the throughput. Blank = unit.
  - `tank_api_gravity`: Liquid API gravity (degrees).
##### Process: `tank_flashing` (5 Tier 3 fields)
  - `tank_gor`: Flash gas-to-oil ratio (scf/bbl).
  - `tank_ch4_content`: CH4 mol % of the flash gas.
  - `tank_control_eff`: % of the vapour recovered or destroyed.
  - `tank_unit`, Choices=('bbl', 'm3', 'gal', 'L'): Unit of the throughput. Blank = unit.
  - `tank_api_gravity`: Liquid API gravity (degrees).
##### Process: `tank_working` (5 Tier 3 fields)
  - `tank_gor`: Flash gas-to-oil ratio (scf/bbl).
  - `tank_ch4_content`: CH4 mol % of the flash gas.
  - `tank_control_eff`: % of the vapour recovered or destroyed.
  - `tank_unit`, Choices=('bbl', 'm3', 'gal', 'L'): Unit of the throughput. Blank = unit.
  - `tank_api_gravity`: Liquid API gravity (degrees).
##### Process: `unloading` (9 Tier 3 fields)
  - `unloading_type`, Choices=('plunger', 'non_plunger'): Well type.
  - `unload_depth`: Well depth (ft).
  - `unload_diam`: Casing inner diameter (in).
  - `unload_press`: Shut-in pressure (psig).
  - `unload_freq`: Unloading events in the month. Blank = quantity.
  - `unload_flare_eff`: % of the vented gas flared.
  - `region`: Basin of the factor table (e.g. Gulf Coast). The record keeps the facility region.
  - `ch4_content`: CH4 mol % of the gas.
  - `co2_content`: CO2 mol % of the gas.
##### Process: `vented_gas` (4 Tier 3 fields)
  - `vent_method`, Choices=('volume',): volume: quantity is the measured vented gas volume.
  - `disposition`, Choices=('vented', 'flared'): Blank = vented; flared applies a 98 % combustion efficiency.
  - `ch4_content`: CH4 mol % of the gas.
  - `co2_content`: CO2 mol % of the gas.
##### Process: `venting` (8 Tier 3 fields)
  - `blowdown_pressure`: Vessel pressure before the blowdown.
  - `blowdown_press_unit`, Choices=('psig', 'psia', 'kPa', 'barg', 'bara'): Unit of blowdown_pressure. Blank = psig.
  - `blowdown_temp`: Gas temperature before the blowdown. Blank = standard conditions (60 F).
  - `blowdown_temp_unit`, Choices=('C', 'F', 'K'): Unit of blowdown_temp. Blank = C.
  - `blowdown_events`: Number of blowdowns in the month (quantity = volume of one blowdown).
  - `z_factor`: Gas compressibility. Blank = 1.
  - `ch4_content`: CH4 mol % of the gas.
  - `co2_content`: CO2 mol % of the gas.
##### Process: `well_testing` (4 Tier 3 fields)
  - `vent_method`, Choices=('volume',): volume: quantity is the measured vented gas volume.
  - `disposition`, Choices=('vented', 'flared'): Blank = vented; flared applies a 98 % combustion efficiency.
  - `ch4_content`: CH4 mol % of the gas.
  - `co2_content`: CO2 mol % of the gas.
##### Process: `workovers` (4 Tier 3 fields)
  - `vent_method`, Choices=('volume',): volume: quantity is the measured vented gas volume.
  - `disposition`, Choices=('vented', 'flared'): Blank = vented; flared applies a 98 % combustion efficiency.
  - `ch4_content`: CH4 mol % of the gas.
  - `co2_content`: CO2 mol % of the gas.

#### Optional Context & Uncertainty Fields
- `activity`: Business activity. Blank = the facility's.
- `division`: Division. Blank = the facility's.
- `field`: Field. Blank = the facility's.
- `operating_temperature`: Gas temperature at the meter: only for volumes in m3 / cf at line conditions.
- `temp_unit`, Choices=('C', 'F', 'K'): Unit of operating_temperature. Blank = C.
- `operating_pressure`: Gas pressure at the meter: only for volumes in m3 / cf at line conditions.
- `press_unit`, Choices=('psig', 'psia', 'kPa', 'barg', 'bara'): Unit of operating_pressure. Blank = psig.
- `meter_uncertainty_pct`: Meter uncertainty % (replaces the tier default).
- `user_unc_co2`: CO2 factor uncertainty % override.
- `user_unc_ch4`: CH4 factor uncertainty % override.
- `user_unc_n2o`: N2O factor uncertainty % override.

---

## 3. Units, Dimensions, and Conversion Factors

### Standard Thermodynamic Conditions in Software (`calculations/units.py`)
- Standard Temperature: 60°F (15.56°C, 288.71 K)
- Standard Pressure: 14.696 psia (101.325 kPa, 1.01325 bar, 1 atm)
- Standard Molar Volume: 23.685 m³/kmol (379.3 scf/lb-mol)
- Engine Gas Standard Densities:
  - CH4: `16.04 / 23.685 = 0.67722` kg/m³
  - CO2: `44.01 / 23.685 = 1.85814` kg/m³
  - N2O: `44.013 / 23.685 = 1.85826` kg/m³

### Dimension Mapping Tables (`calculations/units.py`)
#### Volume (to m³): 34 units supported
| Unit Key | Multiplier / Normalizer |
| :--- | :--- |
| `acf` | `0.028316846592` |
| `actual_m3` | `1.0` |
| `actualm3` | `1.0` |
| `am3` | `1.0` |
| `barrel` | `0.158987295` |
| `barrels` | `0.158987295` |
| `bbl` | `0.158987295` |
| `cf` | `0.028316846592` |
| `cubic_meter` | `1.0` |
| `cubic_meters` | `1.0` |
| `ft3` | `0.028316846592` |
| `gal` | `0.003785411784` |
| `gallon` | `0.003785411784` |
| `gallons` | `0.003785411784` |
| `kbbl` | `158.987295` |
| `ksm3` | `1000.0` |
| `l` | `0.001` |
| `liter` | `0.001` |
| `liters` | `0.001` |
| `litre` | `0.001` |
| `litres` | `0.001` |
| `m3` | `1.0` |
| `mbbl` | `158.987295` |
| `mcf` | `28.316846592` |
| `mmbbl` | `158987.295` |
| `mmscf` | `28316.846592` |
| `mmsm3` | `1000000.0` |
| `mscf` | `28.316846592` |
| `m³` | `1.0` |
| `nm3` | `1.056948766449041` |
| `nm³` | `1.056948766449041` |
| `scf` | `0.028316846592` |
| `sm3` | `1.0` |
| `sm³` | `1.0` |

#### Mass (to kg): 22 units supported
| Unit Key | Multiplier / Normalizer |
| :--- | :--- |
| `g` | `0.001` |
| `gram` | `0.001` |
| `grams` | `0.001` |
| `kg` | `1.0` |
| `kgs` | `1.0` |
| `kilogram` | `1.0` |
| `kilograms` | `1.0` |
| `lb` | `0.45359237` |
| `lbs` | `0.45359237` |
| `long_ton` | `1016.0469088` |
| `long_tons` | `1016.0469088` |
| `metric_ton` | `1000.0` |
| `metric_tons` | `1000.0` |
| `mt` | `1000.0` |
| `pound` | `0.45359237` |
| `pounds` | `0.45359237` |
| `short_ton` | `907.18474` |
| `short_tons` | `907.18474` |
| `t` | `1000.0` |
| `tonne` | `1000.0` |
| `tonnes` | `1000.0` |
| `us_ton` | `907.18474` |

#### Energy (to MJ): 22 units supported
| Unit Key | Multiplier / Normalizer |
| :--- | :--- |
| `btu` | `0.00105505585262` |
| `btus` | `0.00105505585262` |
| `gigajoule` | `1000.0` |
| `gigajoules` | `1000.0` |
| `gj` | `1000.0` |
| `kbtu` | `1.05505585262` |
| `kilojoule` | `0.001` |
| `kilojoules` | `0.001` |
| `kilowatt_hour` | `3.6` |
| `kj` | `0.001` |
| `kwh` | `3.6` |
| `megajoule` | `1.0` |
| `megajoules` | `1.0` |
| `megawatt_hour` | `3600.0` |
| `mj` | `1.0` |
| `mm_btu` | `1055.05585262` |
| `mmbtu` | `1055.05585262` |
| `mwh` | `3600.0` |
| `terajoule` | `1000000.0` |
| `therm` | `105.505585262` |
| `therms` | `105.505585262` |
| `tj` | `1000000.0` |

#### Distance (to m): 17 units supported
| Unit Key | Multiplier / Normalizer |
| :--- | :--- |
| `feet` | `0.3048` |
| `foot` | `0.3048` |
| `ft` | `0.3048` |
| `kilometer` | `1000.0` |
| `kilometers` | `1000.0` |
| `km` | `1000.0` |
| `m` | `1.0` |
| `meter` | `1.0` |
| `meters` | `1.0` |
| `mi` | `1609.344` |
| `mile` | `1609.344` |
| `miles` | `1609.344` |
| `nautical_mile` | `1852.0` |
| `nmi` | `1852.0` |
| `yard` | `0.9144` |
| `yards` | `0.9144` |
| `yd` | `0.9144` |

#### Freight (to tonne-km): 7 units supported
| Unit Key | Multiplier / Normalizer |
| :--- | :--- |
| `t-km` | `1.0` |
| `tkm` | `1.0` |
| `ton-mile` | `1.459972` |
| `ton_mile` | `1.459972` |
| `tonmile` | `1.459972` |
| `tonne-km` | `1.0` |
| `tonne_km` | `1.0` |

#### Passenger (to pkm): 8 units supported
| Unit Key | Multiplier / Normalizer |
| :--- | :--- |
| `p-km` | `1.0` |
| `p-mile` | `1.609344` |
| `passenger-km` | `1.0` |
| `passenger-mile` | `1.609344` |
| `passenger_km` | `1.0` |
| `passenger_mile` | `1.609344` |
| `pkm` | `1.0` |
| `pmile` | `1.609344` |

#### Time (to hours): 17 units supported
| Unit Key | Multiplier / Normalizer |
| :--- | :--- |
| `d` | `24.0` |
| `day` | `24.0` |
| `days` | `24.0` |
| `h` | `1.0` |
| `hour` | `1.0` |
| `hours` | `1.0` |
| `hr` | `1.0` |
| `hrs` | `1.0` |
| `min` | `0.016666666666666666` |
| `minute` | `0.016666666666666666` |
| `minutes` | `0.016666666666666666` |
| `sec` | `0.0002777777777777778` |
| `second` | `0.0002777777777777778` |
| `seconds` | `0.0002777777777777778` |
| `year` | `8760.0` |
| `years` | `8760.0` |
| `yr` | `8760.0` |

#### Liquid Flow (to m³/hr): 12 units supported
| Unit Key | Multiplier / Normalizer |
| :--- | :--- |
| `bbl/day` | `0.006624470625` |
| `bbl/hr` | `0.158987295` |
| `bpd` | `0.006624470625` |
| `bph` | `0.158987295` |
| `gal/hr` | `0.003785411784` |
| `gph` | `0.003785411784` |
| `l/hr` | `0.001` |
| `liter/hr` | `0.001` |
| `lph` | `0.001` |
| `m3/h` | `1.0` |
| `m3/hr` | `1.0` |
| `m3_per_hr` | `1.0` |

#### Temperature Units: 14 units supported
| Unit Key | Type |
| :--- | :--- |
| `c` | Standard Recognized Unit |
| `celsius` | Standard Recognized Unit |
| `degc` | Standard Recognized Unit |
| `degf` | Standard Recognized Unit |
| `degr` | Standard Recognized Unit |
| `f` | Standard Recognized Unit |
| `fahrenheit` | Standard Recognized Unit |
| `k` | Standard Recognized Unit |
| `kelvin` | Standard Recognized Unit |
| `r` | Standard Recognized Unit |
| `rankine` | Standard Recognized Unit |
| `°c` | Standard Recognized Unit |
| `°f` | Standard Recognized Unit |
| `°r` | Standard Recognized Unit |

#### Pressure Units (to kPa): 26 units supported
| Unit Key | Type |
| :--- | :--- |
| `atm` | Standard Recognized Unit |
| `bar` | Standard Recognized Unit |
| `bar_g` | Standard Recognized Unit |
| `bara` | Standard Recognized Unit |
| `barg` | Standard Recognized Unit |
| `kpa` | Standard Recognized Unit |
| `kpa_g` | Standard Recognized Unit |
| `kpaa` | Standard Recognized Unit |
| `kpag` | Standard Recognized Unit |
| `mbar` | Standard Recognized Unit |
| `mbar_g` | Standard Recognized Unit |
| `mbara` | Standard Recognized Unit |
| `mbarg` | Standard Recognized Unit |
| `mpa` | Standard Recognized Unit |
| `mpa_g` | Standard Recognized Unit |
| `mpaa` | Standard Recognized Unit |
| `mpag` | Standard Recognized Unit |
| `pa` | Standard Recognized Unit |
| `pa_g` | Standard Recognized Unit |
| `paa` | Standard Recognized Unit |
| `pag` | Standard Recognized Unit |
| `psi` | Standard Recognized Unit |
| `psi_a` | Standard Recognized Unit |
| `psi_g` | Standard Recognized Unit |
| `psia` | Standard Recognized Unit |
| `psig` | Standard Recognized Unit |

### Direct Pairwise Conversions (`CONVERSIONS` in `units.py`): 46 pairs
| Conversion Key | From Unit | To Unit | Factor |
| :--- | :--- | :--- | :--- |
| `GWP_AR4` | `GWP_AR4` | `-` | `{'ch4': 25, 'n2o': 298}` |
| `GWP_AR5` | `GWP_AR5` | `-` | `{'CO2': 1.0, 'CH4': 28.0, 'N2O': 265.0, 'CH4_20': 84.0, 'N2O_20': 264.0}` |
| `GWP_AR6` | `GWP_AR6` | `-` | `{'ch4': 29.8, 'n2o': 273}` |
| `bbl_to_gal` | `bbl` | `gal` | `42.0` |
| `bbl_to_m3` | `bbl` | `m3` | `0.158987295` |
| `btu_to_kj` | `btu` | `kj` | `1.05505585262` |
| `density_c2h6` | `density_c2h6` | `-` | `1.269579902892126` |
| `density_c3h8` | `density_c3h8` | `-` | `1.8619379354021535` |
| `density_c4h10` | `density_c4h10` | `-` | `2.4538737597635634` |
| `density_ch4` | `density_ch4` | `-` | `0.6772218703820984` |
| `density_co2` | `density_co2` | `-` | `1.858138062064598` |
| `density_n2o` | `density_n2o` | `-` | `1.858264724509183` |
| `gal_to_l` | `gal` | `l` | `3.785411784` |
| `gal_to_m3` | `gal` | `m3` | `0.003785411784` |
| `gwp_ch4` | `gwp_ch4` | `-` | `28.0` |
| `gwp_n2o` | `gwp_n2o` | `-` | `265.0` |
| `kg_to_lb` | `kg` | `lb` | `2.2046226218487757` |
| `kwh_to_mj` | `kwh` | `mj` | `3.6` |
| `l_to_gal` | `l` | `gal` | `0.26417205235814845` |
| `lb_to_kg` | `lb` | `kg` | `0.45359237` |
| `liter_to_m3` | `liter` | `m3` | `0.001` |
| `long_ton_to_kg` | `long_ton` | `kg` | `1016.0469088` |
| `m3_to_bbl` | `m3` | `bbl` | `6.28981077` |
| `m3_to_gal` | `m3` | `gal` | `264.1720523581484` |
| `m3_to_liter` | `m3` | `liter` | `1000.0` |
| `m3_to_mcf` | `m3` | `mcf` | `0.035314666721` |
| `m3_to_mmscf` | `m3` | `mmscf` | `3.5314666721e-05` |
| `m3_to_mscf` | `m3` | `mscf` | `0.035314666721` |
| `m3_to_scf` | `m3` | `scf` | `35.314666721` |
| `mcf_to_m3` | `mcf` | `m3` | `28.316846592` |
| `mcf_to_scf` | `mcf` | `scf` | `1000.0` |
| `mj_to_btu` | `mj` | `btu` | `947.8171203133172` |
| `mj_to_kwh` | `mj` | `kwh` | `0.2777777777777778` |
| `mj_to_mmbtu` | `mj` | `mmbtu` | `0.0009478171203133172` |
| `mmbtu_to_mj` | `mmbtu` | `mj` | `1055.05585262` |
| `mmscf_to_m3` | `mmscf` | `m3` | `28316.846592` |
| `mmscf_to_scf` | `mmscf` | `scf` | `1000000.0` |
| `mscf_to_m3` | `mscf` | `m3` | `28.316846592` |
| `mscf_to_scf` | `mscf` | `scf` | `1000.0` |
| `scf_to_m3` | `scf` | `m3` | `0.028316846592` |
| `scf_to_mcf` | `scf` | `mcf` | `0.001` |
| `scf_to_mmscf` | `scf` | `mmscf` | `1e-06` |
| `scf_to_mscf` | `scf` | `mscf` | `0.001` |
| `short_ton_to_kg` | `short_ton` | `kg` | `907.18474` |
| `therm_to_mj` | `therm` | `mj` | `105.505585262` |
| `tonne_to_kg` | `tonne` | `kg` | `1000.0` |

### Frontend Duplicated Unit Conversions & Constants
- `new/client/src/utils/hhv.ts`:
  - `UNIT_CONVERSIONS`: BTU conversions for `scf`, `Mscf`, `MMscf`, `gal`, `bbl`, `therm`, `kWh`, `MJ`, `GJ`, `MMBtu`
- `new/client/src/constants.ts`:
  - `GWP_VALUES`: AR4, AR5 (CH4=28, N2O=265), AR6 (CH4=29.8, N2O=273)
  - `GAS_DENSITIES`: CH4=0.67722, CO2=1.85814
- `new/client/src/utils/EmissionFactors.ts`:
  - Duplicates 71 API factors for client-side previews

---

## 4. Default Emission Factors Catalog

### 1. API Compendium Default Factors (`new/server/emission_factors.py`)
- **Total Factors**: 180 rows
| Fuel / Source Name | Code | Process Category | Unit | CO2 Factor | CH4 Factor | N2O Factor | HHV | Source Reference |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `Acetylene` | `Acetylene` | `-` | `kg/MMBtu` | `71.59` | `0.003` | `0.0006` | `1470` | Table 3-8 (1,470 Btu/scf, 0.0686 lb/ft3, 92.3 wt % C), 100 % oxidation; Table 4-6 |
| `Acrylonitrile` | `ACN_Prod` | `chemical_production` | `tonne CO₂/tonne product` | `1.0` | `0.00018` | `0` | `-` | API Compendium 2021 Table 6-53 |
| `Adipic Acid - Catalytic Abatement` | `AA_Catalytic` | `adipic_acid_production` | `kg N₂O/tonne product` | `0` | `0` | `53.0` | `-` | API Compendium 2021 Table 6-53 |
| `Adipic Acid - Thermal Abatement` | `AA_Thermal` | `adipic_acid_production` | `kg N₂O/tonne product` | `0` | `0` | `13.0` | `-` | API Compendium 2021 Table 6-53 |
| `Adipic Acid - Uncontrolled` | `AA_Uncontrolled` | `adipic_acid_production` | `kg N₂O/tonne product` | `0` | `0` | `300.0` | `-` | API Compendium 2021 Table 6-53 |
| `Anthracite Coal` | `CoalAnth` | `stationary_combustion` | `kg/MMBtu` | `103.69` | `0.011` | `0.0016` | `25090` | API Compendium 2021 Section 5 |
| `Asphalt` | `Asphalt` | `asphalt_blowing` | `kg/short_ton` | `5.61` | `3.07` | `0` | `-` | API Compendium 2021 Section 6, Table 6-52 |
| `Associated Gas (Flaring)` | `AG_Flare` | `flaring` | `kg/m³` | `2.2414` | `0.010836` | `3.736e-06` | `-` | API Compendium 2021 Equations 5-2 / 5-4 / 5-6 (Dec 2025 corrections: 96.5 % combustion, 98 % CH4 destruction); Table 5-1 raw / produced gas |
| `Associated Gas Venting - Anadarko Basin (Basin 360)` | `AGV_ANADARKO` | `associated_gas_venting` | `kg CH4/bbl` | `0.0` | `9.7` | `0.0` | `-` | API Compendium 2021 Section 6.3.1, Table 6-8 |
| `Associated Gas Venting - Gulf Coast Basin (Basin 220)` | `AGV_GULF_COAST` | `associated_gas_venting` | `kg CH4/bbl` | `0.0` | `0.7` | `0.0` | `-` | API Compendium 2021 Section 6.3.1, Table 6-8 |
| `Associated Gas Venting - Other US Basins` | `AGV_OTHER` | `associated_gas_venting` | `kg CH4/bbl` | `0.0` | `0.4` | `0.0` | `-` | API Compendium 2021 Section 6.3.1, Table 6-8 |
| `Associated Gas Venting - Permian Basin (Basin 430)` | `AGV_PERMIAN` | `associated_gas_venting` | `kg CH4/bbl` | `0.0` | `6.5` | `0.0` | `-` | API Compendium 2021 Section 6.3.1, Table 6-8 |
| `Associated Gas Venting - US Average` | `AGV_US_AVG` | `associated_gas_venting` | `kg CH4/bbl` | `0.0` | `1.4` | `0.0` | `-` | API Compendium 2021 Section 6.3.1, Table 6-8 |
| `Associated Gas Venting - Williston Basin (Basin 395)` | `AGV_WILLISTON` | `associated_gas_venting` | `kg CH4/bbl` | `0.0` | `8.9` | `0.0` | `-` | API Compendium 2021 Section 6.3.1, Table 6-8 |
| `Bituminous Coal` | `CoalBit` | `stationary_combustion` | `kg/MMBtu` | `93.28` | `0.011` | `0.0016` | `24930` | API Compendium 2021 Section 5 |
| `Blast Furnace Gas` | `BFG` | `stationary_combustion` | `kg/MMBtu` | `274.32` | `2.2e-05` | `0.0001` | `92` | API Compendium 2021 Section 5 |
| `Butane` | `Butane` | `-` | `kg/MMBtu` | `64.77` | `0.003` | `0.0006` | `103000` | Table 4-5 / 4-6 (liquid) |
| `Butane (Flaring)` | `Butane_Flare` | `-` | `kg/m³` | `7.1724` | `0.0` | `1.1954e-05` | `-` | API Compendium 2021 Section 5.1, Equations 5-3 and 5-6 (96.5 % combustion, Dec 2025 corrections) |
| `Carbon Black` | `CB_Prod` | `chemical_production` | `tonne CO₂/tonne product` | `2.63` | `0.0287` | `0` | `-` | API Compendium 2021 Table 6-53 |
| `Carbon Black (Thermal Abatement)` | `CB_Prod` | `chemical_production` | `tonne CO₂/tonne product` | `2.63` | `6e-05` | `0` | `-` | API Compendium 2021 Table 6-53 |
| `Coke Oven Gas` | `COG` | `stationary_combustion` | `kg/MMBtu` | `46.85` | `0.00048` | `0.0001` | `599` | API Compendium 2021 Section 5 |
| `Completion - Gas Well (No Flaring)` | `CompGasNoFlare` | `-` | `tonnes/event` | `0` | `1.7376` | `0` | `-` | API Compendium 2021 Table 6-6 |
| `Component - Block Valve` | `BlockValve` | `fugitive_component` | `tonne CH₄/hr/source` | `0` | `4.36e-06` | `0` | `-` | API Compendium 2021 Section 7.2.3, Table 7-30 |
| `Component - Block Valve (Gathering)` | `BlockValve` | `fugitive_component` | `tonne CH4/hr/source` | `0.0` | `4.36e-06` | `0.0` | `-` | - |
| `Component - Compressor Seal` | `CompSeal` | `fugitive_component` | `tonne CH₄/hr/source` | `0` | `0.000154` | `0` | `-` | API Compendium 2021 Section 7.2.3, Table 7-30 |
| `Component - Compressor Seal (Gathering)` | `CompSeal` | `fugitive_component` | `tonne CH4/hr/source` | `0.0` | `0.000154` | `0.0` | `-` | - |
| `Component - Connector (Gas Service)` | `-` | `fugitive_component` | `tonne CH4/hr/component` | `0.0` | `1.3e-07` | `0.0` | `-` | - |
| `Component - Connector (Gathering)` | `ConnNonComp` | `fugitive_component` | `tonne CH4/hr/source` | `0.0` | `9.79e-07` | `0.0` | `-` | - |
| `Component - Connector (Heavy Oil Service)` | `-` | `fugitive_component` | `tonne CH4/hr/component` | `0.0` | `4.89e-09` | `0.0` | `-` | - |
| `Component - Connector (Light Oil Service)` | `-` | `fugitive_component` | `tonne CH4/hr/component` | `0.0` | `1.37e-07` | `0.0` | `-` | - |
| `Component - Connector (Non-Compressor)` | `ConnNonComp` | `fugitive_component` | `tonne CH₄/hr/source` | `0` | `9.79e-07` | `0` | `-` | API Compendium 2021 Section 7.2.3, Table 7-30 |
| `Component - Connector (Water/Oil Service)` | `-` | `fugitive_component` | `tonne CH4/hr/component` | `0.0` | `7.18e-08` | `0.0` | `-` | - |
| `Component - Control Valve` | `ControlValve` | `fugitive_component` | `tonne CH₄/hr/source` | `0` | `1.11e-05` | `0` | `-` | API Compendium 2021 Section 7.2.3, Table 7-30 |
| `Component - Control Valve (Gathering)` | `ControlValve` | `fugitive_component` | `tonne CH4/hr/source` | `0.0` | `1.11e-05` | `0.0` | `-` | - |
| `Component - Flange (Gas Service)` | `-` | `fugitive_component` | `tonne CH4/hr/component` | `0.0` | `2.54e-07` | `0.0` | `-` | - |
| `Component - Flange (Heavy Oil Service)` | `-` | `fugitive_component` | `tonne CH4/hr/component` | `0.0` | `2.54e-10` | `0.0` | `-` | - |
| `Component - Flange (Light Oil Service)` | `-` | `fugitive_component` | `tonne CH4/hr/component` | `0.0` | `7.18e-08` | `0.0` | `-` | - |
| `Component - Flange (Water/Oil Service)` | `-` | `fugitive_component` | `tonne CH4/hr/component` | `0.0` | `1.89e-09` | `0.0` | `-` | - |
| `Component - Open-Ended Line (Gas Service)` | `-` | `fugitive_component` | `tonne CH4/hr/component` | `0.0` | `1.3e-06` | `0.0` | `-` | - |
| `Component - Open-Ended Line (Gathering)` | `OELGath` | `fugitive_component` | `tonne CH4/hr/source` | `0.0` | `7.09e-05` | `0.0` | `-` | - |
| `Component - Open-Ended Line (Heavy Oil Service)` | `-` | `fugitive_component` | `tonne CH4/hr/component` | `0.0` | `9.13e-08` | `0.0` | `-` | - |
| `Component - Open-Ended Line (Light Oil Service)` | `-` | `fugitive_component` | `tonne CH4/hr/component` | `0.0` | `9.13e-07` | `0.0` | `-` | - |
| `Component - Open-Ended Line (Water/Oil Service)` | `-` | `fugitive_component` | `tonne CH4/hr/component` | `0.0` | `1.63e-07` | `0.0` | `-` | - |
| `Component - Other / PRV (Gas Service)` | `-` | `fugitive_component` | `tonne CH4/hr/component` | `0.0` | `5.74e-06` | `0.0` | `-` | - |
| `Component - Other / PRV (Heavy Oil Service)` | `-` | `fugitive_component` | `tonne CH4/hr/component` | `0.0` | `2.09e-08` | `0.0` | `-` | - |
| `Component - Other / PRV (Light Oil Service)` | `-` | `fugitive_component` | `tonne CH4/hr/component` | `0.0` | `4.89e-06` | `0.0` | `-` | - |
| `Component - Other / PRV (Water/Oil Service)` | `-` | `fugitive_component` | `tonne CH4/hr/component` | `0.0` | `9.13e-06` | `0.0` | `-` | - |
| `Component - Pressure Regulator` | `Regulator` | `fugitive_component` | `tonne CH₄/hr/source` | `0` | `1.87e-06` | `0` | `-` | API Compendium 2021 Section 7.2.3, Table 7-30 |
| `Component - Pressure Regulator (Gathering)` | `Regulator` | `fugitive_component` | `tonne CH4/hr/source` | `0.0` | `1.87e-06` | `0.0` | `-` | - |
| `Component - Pressure Relief Valve` | `PRV` | `fugitive_component` | `tonne CH₄/hr/source` | `0` | `1.39e-07` | `0` | `-` | API Compendium 2021 Section 7.2.3, Table 7-30 |
| `Component - Pressure Relief Valve (Gathering)` | `PRV` | `fugitive_component` | `tonne CH4/hr/source` | `0.0` | `1.39e-07` | `0.0` | `-` | - |
| `Component - Pump Seal (Light Oil Service)` | `-` | `fugitive_component` | `tonne CH4/hr/component` | `0.0` | `8.48e-06` | `0.0` | `-` | - |
| `Component - Pump Seal (Water/Oil Service)` | `-` | `fugitive_component` | `tonne CH4/hr/component` | `0.0` | `1.57e-08` | `0.0` | `-` | - |
| `Component - Valve (Gas Service)` | `-` | `fugitive_component` | `tonne CH4/hr/component` | `0.0` | `2.94e-06` | `0.0` | `-` | - |
| `Component - Valve (Heavy Oil Service)` | `-` | `fugitive_component` | `tonne CH4/hr/component` | `0.0` | `5.48e-09` | `0.0` | `-` | - |
| `Component - Valve (Light Oil Service)` | `-` | `fugitive_component` | `tonne CH4/hr/component` | `0.0` | `1.63e-06` | `0.0` | `-` | - |
| `Component - Valve (Water/Oil Service)` | `-` | `fugitive_component` | `tonne CH4/hr/component` | `0.0` | `6.39e-08` | `0.0` | `-` | - |
| `Compressed Natural Gas (CNG)` | `CNG` | `-` | `kg/MMBtu` | `53.06` | `0.001` | `0.0001` | `1020` | Natural gas, Tables 3-8 / 4-5 / 4-6 (standard volume) |
| `Compressor - Gas Production Large Recip` | `CompGasLarge` | `compressor_fugitive` | `tonne CH4/compressor/hr` | `0.0` | `0.0122` | `0.0` | `-` | - |
| `Compressor - Gas Production Small Recip` | `CompGasSmall` | `compressor_fugitive` | `tonne CH4/compressor/hr` | `0.0` | `0.000212` | `0.0` | `-` | - |
| `Compressor - Large Reciprocating` | `CompLarge` | `compressor_fugitive` | `tonne CH4/compressor/hr` | `0.0` | `0.0131` | `0.0` | `-` | - |
| `Compressor - Small Reciprocating` | `CompSmall` | `compressor_fugitive` | `tonne CH4/compressor/hr` | `0.0` | `3.69e-05` | `0.0` | `-` | - |
| `Crude Oil` | `Crude` | `stationary_combustion` | `kg/MMBtu` | `74.54` | `0.003` | `0.0006` | `138000` | API Compendium 2021 Section 5 |
| `Dehydrator - Glycol (Uncontrolled)` | `DehyUncont` | `dehydrator` | `tonnes CH4/MMscf` | `0` | `0.0052859` | `0` | `-` | API Compendium 2021 Table 6-17 (78.8 mol % CH4 basis) |
| `Diesel (No. 2 Fuel Oil)` | `DSL` | `stationary_combustion` | `kg/MMBtu` | `73.96` | `0.003` | `0.0006` | `138000` | API Compendium 2021 Section 5, Table 5-1 |
| `Drilling - Mud Degassing (Oil Based)` | `MudOil` | `drilling` | `tonnes CH4/drilling day` | `0` | `0.0103` | `0` | `-` | API Compendium 2021 Section 6.2.1, Table 6-2 |
| `Drilling - Mud Degassing (Synthetic)` | `MudSynthetic` | `drilling` | `tonnes CH4/drilling day` | `0` | `0.0103` | `0` | `-` | API Compendium 2021 Section 6.2.1, Table 6-2 |
| `Drilling - Mud Degassing (Water Based)` | `MudWater` | `drilling` | `tonnes CH4/drilling day` | `0` | `0.0458` | `0` | `-` | API Compendium 2021 Section 6.2.1, Table 6-2 |
| `Ethane` | `Ethane` | `stationary_combustion` | `kg/MMBtu` | `59.6` | `0.003` | `0.0006` | `68000` | API Compendium 2021 Section 5 |
| `Ethane (Gas)` | `EthaneGas` | `-` | `kg/MMBtu` | `59.6` | `0.003` | `0.0006` | `1768.8` | - |
| `Ethylene (Ethane Feedstock)` | `ETH_Prod` | `chemical_production` | `tonne CO₂/tonne product` | `0.77` | `0.006` | `0` | `-` | API Compendium 2021 Table 6-53 |
| `Ethylene (Flaring)` | `Ethylene_Flare` | `-` | `kg/m³` | `3.5862` | `0.0` | `5.977e-06` | `-` | API Compendium 2021 Section 5.1, Equations 5-3 and 5-6 (96.5 % combustion, Dec 2025 corrections) |
| `Ethylene (Other Feedstocks)` | `ETH_Prod` | `chemical_production` | `tonne CO₂/tonne product` | `0.77` | `0.003` | `0` | `-` | API Compendium 2021 Table 6-53 |
| `Ethylene Dichloride` | `EDC_Prod` | `chemical_production` | `tonne CO₂/tonne product` | `0.041` | `0` | `0` | `-` | API Compendium 2021 Table 6-53 |
| `Ethylene Oxide` | `ETO_Prod` | `chemical_production` | `tonne CO₂/tonne product` | `0.46` | `0.00179` | `0` | `-` | API Compendium 2021 Table 6-53 |
| `Ethylene Oxide (Thermal Abatement)` | `ETO_Prod` | `chemical_production` | `tonne CO₂/tonne product` | `0.46` | `0.00079` | `0` | `-` | API Compendium 2021 Table 6-53 |
| `Facility - Onshore Gas Production (Table 7-8)` | `-` | `fugitive_facility` | `tonne CH4/10^6 scf` | `0.0` | `0.02601` | `0.0` | `-` | - |
| `Facility - Onshore Oil Production (Table 7-8)` | `-` | `fugitive_facility` | `tonne CH4/bbl` | `0.0` | `0.0002346` | `0.0` | `-` | - |
| `Gas Dehydrator Unit - Fugitive Leaks` | `DehyFugGas` | `equipment_fugitive` | `tonne CH4/unit/hr` | `0.0` | `7.13e-05` | `0.0` | `-` | - |
| `Gathering - AGRU` | `GathAGRU` | `gathering_boosting` | `tonne CH₄/unit/hr` | `0` | `6.83e-05` | `0` | `-` | API Compendium 2021 Section 7.2.3, Table 7-29 |
| `Gathering - Compressor` | `GathComp` | `gathering_boosting` | `tonne CH4/unit/hr` | `0.0` | `0.00184` | `0.0` | `-` | - |
| `Gathering - Dehydrator` | `GathDehy` | `gathering_boosting` | `tonne CH₄/unit/hr` | `0` | `5.69e-05` | `0` | `-` | API Compendium 2021 Section 7.2.3, Table 7-29 |
| `Gathering - Separator` | `GathSep` | `gathering_boosting` | `tonne CH₄/unit/hr` | `0` | `1.05e-05` | `0` | `-` | API Compendium 2021 Section 7.2.3, Table 7-29 |
| `Gathering - Tank` | `GathTank` | `gathering_boosting` | `tonne CH₄/unit/hr` | `0` | `0.00064` | `0` | `-` | API Compendium 2021 Section 7.2.3, Table 7-29 |
| `Header - Heavy Crude` | `HeaderHeavy` | `equipment_fugitive` | `tonne CH4/header/hr` | `0.0` | `4.72e-07` | `0.0` | `-` | - |
| `Header - Light Crude` | `HeaderLight` | `equipment_fugitive` | `tonne CH4/header/hr` | `0.0` | `0.000162` | `0.0` | `-` | - |
| `Heater - Gas Production` | `HeaterGas` | `equipment_fugitive` | `tonne CH4/heater/hr` | `0.0` | `4.6e-05` | `0.0` | `-` | - |
| `Heater-Treater - Light Crude` | `HeaterLight` | `equipment_fugitive` | `tonne CH4/heater/hr` | `0.0` | `4.77e-05` | `0.0` | `-` | - |
| `Isobutane` | `Isobutane` | `-` | `kg/MMBtu` | `64.94` | `0.003` | `0.0006` | `99000` | Table 4-5 / 4-6 (liquid) |
| `Jet Fuel` | `JET` | `mobile_combustion` | `kg/MMBtu` | `72.22` | `0.003` | `0.0006` | `135000` | API Compendium 2021 Section 5 |
| `Kerosene` | `Kero` | `stationary_combustion` | `kg/MMBtu` | `75.2` | `0.003` | `0.0006` | `135000` | API Compendium 2021 Section 5 |
| `LNG - Export Terminal` | `LNGExport` | `lng_operations` | `tonne CH₄/facility` | `0` | `0.00126` | `0` | `-` | API Compendium 2021 Section 7.3.6, Table 7-76 |
| `LNG - Import Terminal` | `LNGImport` | `lng_operations` | `tonne CH₄/facility` | `0` | `0.000329` | `0` | `-` | API Compendium 2021 Section 7.3.6, Table 7-76 |
| `LNG - Storage Station` | `LNGStorage` | `lng_operations` | `tonne CH₄/facility` | `0` | `0.000439` | `0` | `-` | API Compendium 2021 Section 7.3.6, Table 7-76 |
| `Lignite Coal` | `CoalLig` | `stationary_combustion` | `kg/MMBtu` | `97.72` | `0.011` | `0.0016` | `14210` | API Compendium 2021 Section 5 |
| `Liquefied Natural Gas (LNG)` | `LNG` | `-` | `kg/MMBtu` | `53.06` | `0.001` | `0.0001` | `1020` | Natural gas, Tables 3-8 / 4-5 / 4-6 (regasified standard volume) |
| `Liquids Unloading - Non-Plunger` | `UnloadNonPlunger` | `-` | `tonnes CH4/well-year` | `-` | `2.792` | `-` | `-` | - |
| `Liquids Unloading - Non-Plunger (10-50 events/yr)` | `UnloadNonPlunger_10_50` | `liquids_unloading` | `tonnes CH4/event` | `0.0` | `0.462` | `0.0` | `-` | API Compendium 2021 Section 6.3.4, Table 6-10 |
| `Liquids Unloading - Non-Plunger (>50 events/yr)` | `UnloadNonPlunger_GT50` | `liquids_unloading` | `tonnes CH4/event` | `0.0` | `0.67` | `0.0` | `-` | API Compendium 2021 Section 6.3.4, Table 6-10 |
| `Liquids Unloading - Non-Plunger (Appalachia)` | `UnloadNonPlunger_Appalachia` | `liquids_unloading` | `tonnes CH4/event` | `0.0` | `0.087` | `0.0` | `-` | API Compendium 2021 Section 6.3.4, Table 6-10 |
| `Liquids Unloading - Non-Plunger (Gulf Coast)` | `UnloadNonPlunger_GulfCoast` | `liquids_unloading` | `tonnes CH4/event` | `0.0` | `0.255` | `0.0` | `-` | API Compendium 2021 Section 6.3.4, Table 6-10 |
| `Liquids Unloading - Non-Plunger (Midcontinent)` | `UnloadNonPlunger_Midcontinent` | `liquids_unloading` | `tonnes CH4/event` | `0.0` | `0.916` | `0.0` | `-` | API Compendium 2021 Section 6.3.4, Table 6-10 |
| `Liquids Unloading - Non-Plunger (Rocky Mountain)` | `UnloadNonPlunger_RockyMountain` | `liquids_unloading` | `tonnes CH4/event` | `0.0` | `0.291` | `0.0` | `-` | API Compendium 2021 Section 6.3.4, Table 6-10 |
| `Liquids Unloading - Non-Plunger (Tier 1 Default)` | `UnloadNonPlunger_T1` | `liquids_unloading` | `tonnes CH4/well-year` | `0.0` | `2.792` | `0.0` | `-` | API Compendium 2021 Section 6.3.4, Table 6-11 |
| `Liquids Unloading - Non-Plunger (≤10 events/yr)` | `UnloadNonPlunger_LE10` | `liquids_unloading` | `tonnes CH4/event` | `0.0` | `0.412` | `0.0` | `-` | API Compendium 2021 Section 6.3.4, Table 6-10 |
| `Liquids Unloading - Plunger Lift` | `UnloadPlunger` | `-` | `tonnes CH4/well-year` | `-` | `1.774` | `-` | `-` | - |
| `Liquids Unloading - Plunger Lift (>100 events/yr)` | `UnloadPlunger_GT100` | `liquids_unloading` | `tonnes CH4/event` | `0.0` | `0.024` | `0.0` | `-` | API Compendium 2021 Section 6.3.4, Table 6-10 |
| `Liquids Unloading - Plunger Lift (Appalachia <100 events/yr)` | `UnloadPlunger_Appalachia_LT100` | `liquids_unloading` | `tonnes CH4/event` | `0.0` | `0.098` | `0.0` | `-` | API Compendium 2021 Section 6.3.4, Table 6-10 |
| `Liquids Unloading - Plunger Lift (Appalachia >100 events/yr)` | `UnloadPlunger_Appalachia_GT100` | `liquids_unloading` | `tonnes CH4/event` | `0.0` | `0.024` | `0.0` | `-` | API Compendium 2021 Section 6.3.4, Table 6-10 |
| `Liquids Unloading - Plunger Lift (Gulf Coast <100 events/yr)` | `UnloadPlunger_GulfCoast_LT100` | `liquids_unloading` | `tonnes CH4/event` | `0.0` | `0.185` | `0.0` | `-` | API Compendium 2021 Section 6.3.4, Table 6-10 |
| `Liquids Unloading - Plunger Lift (Gulf Coast >100 events/yr)` | `UnloadPlunger_GulfCoast_GT100` | `liquids_unloading` | `tonnes CH4/event` | `0.0` | `0.024` | `0.0` | `-` | API Compendium 2021 Section 6.3.4, Table 6-10 |
| `Liquids Unloading - Plunger Lift (Midcontinent <100 events/yr)` | `UnloadPlunger_Midcontinent_LT100` | `liquids_unloading` | `tonnes CH4/event` | `0.0` | `0.123` | `0.0` | `-` | API Compendium 2021 Section 6.3.4, Table 6-10 |
| `Liquids Unloading - Plunger Lift (Midcontinent >100 events/yr)` | `UnloadPlunger_Midcontinent_GT100` | `liquids_unloading` | `tonnes CH4/event` | `0.0` | `0.006` | `0.0` | `-` | API Compendium 2021 Section 6.3.4, Table 6-10 |
| `Liquids Unloading - Plunger Lift (Rocky Mountain <100 events/yr)` | `UnloadPlunger_RockyMountain_LT100` | `liquids_unloading` | `tonnes CH4/event` | `0.0` | `0.241` | `0.0` | `-` | API Compendium 2021 Section 6.3.4, Table 6-10 |
| `Liquids Unloading - Plunger Lift (Rocky Mountain >100 events/yr)` | `UnloadPlunger_RockyMountain_GT100` | `liquids_unloading` | `tonnes CH4/event` | `0.0` | `0.027` | `0.0` | `-` | API Compendium 2021 Section 6.3.4, Table 6-10 |
| `Liquids Unloading - Plunger Lift (Tier 1 Default)` | `UnloadPlunger_T1` | `liquids_unloading` | `tonnes CH4/well-year` | `0.0` | `1.774` | `0.0` | `-` | API Compendium 2021 Section 6.3.4, Table 6-11 |
| `Liquids Unloading - Plunger Lift (≤100 events/yr)` | `UnloadPlunger_LE100` | `liquids_unloading` | `tonnes CH4/event` | `0.0` | `0.185` | `0.0` | `-` | API Compendium 2021 Section 6.3.4, Table 6-10 |
| `Lubricants` | `Lube` | `-` | `kg/MMBtu` | `74.27` | `0.003` | `0.0006` | `144000` | Table 4-5 / 4-6 |
| `Marine Diesel Oil` | `MDO` | `stationary_combustion` | `kg/MMBtu` | `73.96` | `0.006857630052775418` | `0.00197499745519932` | `138000` | API Compendium 2021 Table 4-5 (CO2) / Table 4-16 diesel ships (CH4, N2O) |
| `Meter / Piping Run - Gas Production` | `MeterRunGas` | `equipment_fugitive` | `tonne CH4/run/hr` | `0.0` | `3.52e-05` | `0.0` | `-` | - |
| `Methanol` | `MEOH_Prod` | `chemical_production` | `tonne CO₂/tonne product` | `0.67` | `0.0023` | `0` | `-` | API Compendium 2021 Table 6-53 |
| `Motor Gasoline` | `GAS` | `mobile_combustion` | `kg/MMBtu` | `70.22` | `0.003` | `0.0006` | `125000` | API Compendium 2021 Section 5 |
| `Naphtha` | `Naphtha` | `-` | `kg/MMBtu` | `68.02` | `0.003` | `0.0006` | `125000` | Table 4-5 / 4-6, naphtha < 401 F |
| `Natural Gas` | `NG` | `stationary_combustion` | `kg/MMBtu` | `53.06` | `0.001` | `0.0001` | `1020` | API Compendium 2021 Section 5, Table 5-1 |
| `Natural Gas (Flaring - Elevated)` | `NG_Flare_Elev` | `flaring` | `kg/m³` | `1.9039` | `0.012447` | `3.173e-06` | `-` | API Compendium 2021 Equations 5-2 / 5-4 / 5-6 (Dec 2025 corrections: 96.5 % combustion, 98 % CH4 destruction); Table 5-1 processing-plant gas |
| `Natural Gas (Flaring - Enclosed)` | `NG_Flare_Enc` | `flaring` | `kg/m³` | `1.9039` | `0.012447` | `3.173e-06` | `-` | API Compendium 2021 Equations 5-2 / 5-4 / 5-6 (Dec 2025 corrections: 96.5 % combustion, 98 % CH4 destruction); Table 5-1 processing-plant gas |
| `Natural Gas (Flaring)` | `NG_Flare` | `flaring` | `kg/m³` | `1.9039` | `0.012447` | `3.173e-06` | `-` | API Compendium 2021 Equations 5-2 / 5-4 / 5-6 (Dec 2025 corrections: 96.5 % combustion, 98 % CH4 destruction); Table 5-1 processing-plant gas |
| `Natural Gas (Venting/Blowdown)` | `NG_Vent` | `venting` | `kg/m³` | `0.010498` | `0.63029` | `0` | `-` | API Compendium 2021 Table 6-50 (pipeline-quality natural gas), 23.685 Sm3/kgmole |
| `Natural Gas - 2-Stroke Lean Burn Engine` | `NG_2SLB` | `-` | `kg/MMBtu` | `53.06` | `0.6573` | `0.0001` | `1020` | - |
| `Natural Gas - 4-Stroke Lean Burn Engine` | `NG_4SLB` | `-` | `kg/MMBtu` | `53.06` | `0.56656` | `0.0001` | `1020` | - |
| `Natural Gas - 4-Stroke Rich Burn Engine` | `NG_4SRB` | `-` | `kg/MMBtu` | `53.06` | `0.10551` | `0.0001` | `1020` | - |
| `Natural Gas - Heater/Boiler` | `NG_Heater` | `-` | `kg/MMBtu` | `53.06` | `0.001` | `0.0001` | `1020` | - |
| `Natural Gas - Turbine` | `NG_Turbine` | `-` | `kg/MMBtu` | `53.06` | `0.003904` | `0.001372` | `1020` | - |
| `Nitric Acid - With NSCR` | `HNO3_NSCR` | `nitric_acid_production` | `kg N₂O/tonne product` | `0` | `0` | `2.0` | `-` | API Compendium 2021 Table 6-53 |
| `Nitric Acid - Without NSCR` | `HNO3_NoNSCR` | `nitric_acid_production` | `kg N₂O/tonne product` | `0` | `0` | `9.0` | `-` | API Compendium 2021 Table 6-53 |
| `Offshore - Gas Production (Facility)` | `OffshoreGas` | `wellhead_fugitive` | `tonne CH₄/10⁶ scf produced` | `0` | `0.0104` | `0` | `-` | API Compendium 2021 Section 7.2, Table 7-3 |
| `Offshore - Oil Production (Facility)` | `OffshoreOil` | `wellhead_fugitive` | `tonne CH₄/bbl produced` | `0` | `9.386e-05` | `0` | `-` | API Compendium 2021 Section 7.2, Table 7-3 |
| `Petroleum Coke` | `PetCoke` | `stationary_combustion` | `kg/MMBtu` | `102.41` | `0.032` | `0.0042` | `30000` | API Compendium 2021 Section 5 |
| `Pneumatic Controller - Continuous Vent (T&S)` | `ContinuousVentTS` | `-` | `tonnes CH4/yr` | `-` | `3.5` | `-` | `-` | - |
| `Pneumatic Controller - High Bleed` | `HighBleed` | `-` | `tonnes CH4/yr` | `-` | `5.11` | `-` | `-` | - |
| `Pneumatic Controller - High Bleed (>6 scfh)` | `HighBleed` | `pneumatic_devices` | `tonnes CH₄/yr` | `0` | `5.11` | `0` | `-` | API Compendium 2021 Table 6-14 EPA GHGRP production high-bleed (37.3 scf/h) |
| `Pneumatic Controller - Intermittent` | `Intermittent` | `-` | `tonnes CH4/yr` | `-` | `1.85` | `-` | `-` | - |
| `Pneumatic Controller - Low Bleed` | `LowBleed` | `-` | `tonnes CH4/yr` | `-` | `0.191` | `-` | `-` | - |
| `Pneumatic Controller - Low Bleed (<6 scfh)` | `LowBleed` | `pneumatic_devices` | `tonnes CH₄/yr` | `0` | `0.191` | `0` | `-` | API Compendium 2021 Table 6-14 EPA GHGRP production low-bleed (1.39 scf/h) |
| `Processing - Centrifugal Compressor` | `ProcCentComp` | `gas_processing` | `tonne CH₄/compressor/hr` | `0` | `0.017` | `0` | `-` | API Compendium 2021 Section 7.3, Table 7-35 |
| `Processing - Reciprocating Compressor` | `ProcRecipComp` | `gas_processing` | `tonne CH₄/compressor/hr` | `0` | `0.00895` | `0` | `-` | API Compendium 2021 Section 7.3, Table 7-35 |
| `Propane (Flaring)` | `LPG_Flare` | `-` | `kg/m³` | `5.3793` | `0.0` | `8.9655e-06` | `-` | API Compendium 2021 Section 5.1, Equations 5-3 and 5-6 (96.5 % combustion, Dec 2025 corrections) |
| `Propane (Gas)` | `LPG_Gas` | `stationary_combustion` | `kg/MMBtu` | `61.46` | `0.003` | `0.0006` | `2516` | API Compendium 2021 Section 5 |
| `Propane (Liquid)` | `LPG_Liq` | `-` | `kg/MMBtu` | `62.87` | `0.003` | `0.0006` | `91000` | API Compendium 2021 Table 4-5 / Table 4-6 |
| `Propane (Liquid/LPG)` | `LPG_Liq` | `stationary_combustion` | `kg/MMBtu` | `62.87` | `0.003` | `0.0006` | `91000` | API Compendium 2021 Section 5 |
| `Propylene` | `Propylene` | `-` | `kg/MMBtu` | `67.77` | `0.003` | `0.0006` | `91000` | Table 4-5 / 4-6 (liquid) |
| `Propylene (Flaring)` | `Propylene_Flare` | `-` | `kg/m³` | `5.3793` | `0.0` | `8.9655e-06` | `-` | API Compendium 2021 Section 5.1, Equations 5-3 and 5-6 (96.5 % combustion, Dec 2025 corrections) |
| `Refinery - Fuel Gas System (100-199k bbl/day)` | `RefFuelGasLarge` | `refinery_fugitive` | `tonnes CH₄/10³ bbl feedstock` | `0` | `0.00141` | `0` | `-` | API Compendium 2021 Section 7.4.1, Table 7-80 |
| `Refinery - Fuel Gas System (50-99k bbl/day)` | `RefFuelGasSmall` | `refinery_fugitive` | `tonnes CH₄/10³ bbl feedstock` | `0` | `0.000375` | `0` | `-` | API Compendium 2021 Section 7.4.1, Table 7-80 |
| `Refinery Fuel Gas` | `RFG` | `stationary_combustion` | `kg/MMBtu` | `59.0` | `0.003` | `0.0006` | `1388` | API Compendium 2021 Section 5 |
| `Residual Fuel Oil (No. 6)` | `RFO` | `stationary_combustion` | `kg/MMBtu` | `75.1` | `0.003` | `0.0006` | `150000` | API Compendium 2021 Section 5, Table 5-1 |
| `Separator - Gas Production` | `SepGas` | `separator_fugitive` | `tonne CH4/separator/hr` | `0.0` | `4.42e-05` | `0.0` | `-` | - |
| `Separator - Heavy Crude` | `SepHeavy` | `separator_fugitive` | `tonne CH4/separator/hr` | `0.0` | `6.79e-07` | `0.0` | `-` | - |
| `Separator - Light Crude` | `SepLight` | `separator_fugitive` | `tonne CH4/separator/hr` | `0.0` | `4.1e-05` | `0.0` | `-` | - |
| `Storage Tank Fugitive - Light Crude` | `TankFugLight` | `equipment_fugitive` | `tonne CH4/tank/hr` | `0.0` | `2.75e-05` | `0.0` | `-` | - |
| `Sub-Bituminous Coal` | `CoalSub` | `stationary_combustion` | `kg/MMBtu` | `97.17` | `0.011` | `0.0016` | `17250` | API Compendium 2021 Section 5 |
| `Tank - Crude Oil (Large, >10 bbl/d)` | `TankCrudeLarge` | `storage_tanks` | `kg CH₄/bbl` | `0` | `0.193` | `0` | `-` | API Compendium 2021 Table 6-22 |
| `Tank - Crude Oil (Small, ≤10 bbl/d)` | `TankCrudeSmall` | `storage_tanks` | `kg CH₄/bbl` | `0` | `0.0184` | `0` | `-` | API Compendium 2021 Table 6-22 |
| `Tank - Flash Emissions (Oil)` | `TankFlashOil` | `-` | `kg/bbl` | `0` | `0.193` | `0` | `-` | - |
| `Tank - Production Condensate (Large, >10 bbl/d)` | `TankProdLarge` | `storage_tanks` | `kg CH₄/bbl` | `0` | `0.146` | `0` | `-` | API Compendium 2021 Table 6-24 |
| `Tank - Production Condensate (Small, ≤10 bbl/d)` | `TankProdSmall` | `storage_tanks` | `kg CH₄/bbl` | `0` | `0.119` | `0` | `-` | API Compendium 2021 Table 6-24 |
| `Tires` | `Tires` | `-` | `kg/MMBtu` | `85.97` | `0.032` | `0.0042` | `28000` | Table 4-5; CH4 / N2O 40 CFR 98 Table C-2 other solid fuels |
| `UnloadNonPlunger` | `UnloadNonPlunger` | `-` | `tonnes CH4/well-year` | `-` | `2.792` | `-` | `-` | - |
| `UnloadPlunger` | `UnloadPlunger` | `-` | `tonnes CH4/well-year` | `-` | `1.774` | `-` | `-` | - |
| `Waste Oil` | `WasteOil` | `-` | `kg/MMBtu` | `74.0` | `0.003` | `0.0006` | `138000` | Table 4-5 used oil / Table 4-6 |
| `Well Completion - Gas Well with Hydraulic Fracturing (REC with Venting)` | `CompGasHF_REC` | `completions` | `tonnes/completion` | `0.0` | `13.542` | `0.0` | `-` | API Compendium 2021 Section 6.2.3, Table 6-5 |
| `Well Completion - Gas Well with Hydraulic Fracturing (Uncontrolled Venting)` | `CompGasHF_Uncontrolled` | `completions` | `tonnes/completion` | `0.0` | `28.8` | `0.0` | `-` | API Compendium 2021 Section 6.2.3, Table 6-5 |
| `Well Completion - Gas Well without Hydraulic Fracturing (Vented)` | `CompGasNoHF_Vented` | `completions` | `tonnes/completion` | `0.0` | `1.7376` | `0.0` | `-` | API Compendium 2021 Section 6.2.3, Table 6-6 |
| `Well Completion - Oil Well with Hydraulic Fracturing (REC with Venting)` | `CompOilHF_REC` | `completions` | `tonnes/completion` | `0.0` | `0.615` | `0.0` | `-` | API Compendium 2021 Section 6.2.3, Table 6-5 |
| `Well Completion - Oil Well with Hydraulic Fracturing (Uncontrolled Venting)` | `CompOilHF_Uncontrolled` | `completions` | `tonnes/completion` | `0.0` | `14.419` | `0.0` | `-` | API Compendium 2021 Section 6.2.3, Table 6-5 |
| `Well Completion - Oil Well without Hydraulic Fracturing (Vented)` | `CompOilNoHF_Vented` | `completions` | `tonnes/completion` | `0.0` | `0.0141` | `0.0` | `-` | API Compendium 2021 Section 6.2.3, Table 6-6 |
| `Wellhead - Gas` | `WellGas` | `wellhead_fugitive` | `tonne CH4/well/hr` | `0.0` | `1.8e-05` | `0.0` | `-` | - |
| `Wellhead - Oil (Heavy Crude)` | `WellOilHeavy` | `wellhead_fugitive` | `tonne CH4/well/hr` | `0.0` | `6.63e-07` | `0.0` | `-` | - |
| `Wellhead - Oil (Light Crude)` | `WellOilLight` | `wellhead_fugitive` | `tonne CH4/well/hr` | `0.0` | `1.56e-05` | `0.0` | `-` | - |
| `Workover - Gas Well (No Flaring)` | `WorkoverGasNoFlare` | `-` | `tonnes/event` | `0` | `0.047` | `0` | `-` | API Compendium 2021 Table 6-9 |

### 2. Activity-Based Emission Factors (`new/server/calculations/activity_factors.py`)
- **Total Activity Factors**: 105 rows
| Factor Key | Label | Applicable Processes | Unit Basis | Table | CH4 Value | Gas (scf) | CH4 Mol Basis |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `agr_throughput` | AGR vent, per treated gas | `agr` | `mmscf` | `Table 6-19` | `0.0185` | `None` | `None` |
| `agr_unit` | AGR vent, per AGR unit | `agr` | `unit_day` | `Table 6-19` | `0.6482` | `None` | `None` |
| `cg_bitumen` | Crude bitumen casing gas | `casing_gas` | `bbl` | `Table 6-12` | `0.000207` | `12.9` | `0.816` |
| `cg_migration` | Low-pressure well casing gas migration | `casing_gas` | `unit_day` | `Section 6.3.5.2 (CAPP)` | `0.00213` | `135.96146687773108` | `0.816` |
| `cg_primary_heavy` | Primary heavy oil casing gas | `casing_gas` | `bbl` | `Table 6-12` | `0.00328` | `210` | `0.816` |
| `cg_thermal_heavy` | Thermal heavy oil casing gas | `casing_gas` | `bbl` | `Table 6-12` | `0.000223` | `14.2` | `0.816` |
| `cip_avg_api` | Chemical injection pump, type unknown (API study) | `pneumatic` | `unit_hr` | `Table 6-16` | `None` | `14.1` | `0.816` |
| `cip_avg_ghgrp` | Chemical injection pump, type unknown (EPA GHGRP) | `pneumatic` | `unit_hr` | `Table 6-16` | `None` | `34.4` | `0.816` |
| `cip_avg_gri` | Chemical injection pump, type unknown (GRI/EPA) | `pneumatic` | `unit_hr` | `Table 6-16` | `None` | `13.1` | `0.788` |
| `cip_diaphragm_api` | Chemical injection pump, diaphragm (API study) | `pneumatic` | `unit_hr` | `Table 6-16` | `None` | `18.6` | `0.816` |
| `cip_diaphragm_ghgrp` | Chemical injection pump, diaphragm (EPA GHGRP) | `pneumatic` | `unit_hr` | `Table 6-16` | `None` | `37.3` | `0.816` |
| `cip_diaphragm_gri` | Chemical injection pump, diaphragm (GRI/EPA) | `pneumatic` | `unit_hr` | `Table 6-16` | `None` | `23.6` | `0.788` |
| `cip_piston_api` | Chemical injection pump, piston (API study) | `pneumatic` | `unit_hr` | `Table 6-16` | `None` | `2.03` | `0.816` |
| `cip_piston_ghgrp` | Chemical injection pump, piston (EPA GHGRP) | `pneumatic` | `unit_hr` | `Table 6-16` | `None` | `20.9` | `0.816` |
| `cip_piston_gri` | Chemical injection pump, piston (GRI/EPA) | `pneumatic` | `unit_hr` | `Table 6-16` | `None` | `2.59` | `0.788` |
| `dh_glycol_processing` | Glycol dehydrator vent, processing | `dehydrator` | `mmscf` | `Table 6-35` | `0.0023315` | `140.03` | `0.868` |
| `dh_glycol_production` | Glycol dehydrator vent, production (no gas pump) | `dehydrator` | `mmscf` | `Table 6-17` | `0.0052859` | `349.7` | `0.788` |
| `dh_kimray_processing` | Kimray / gas-assisted glycol pump, processing | `dehydrator` | `mmscf` | `Table 6-36` | `0.0034096` | `205` | `0.868` |
| `dh_kimray_production` | Kimray / gas-assisted glycol pump, production | `dehydrator` | `mmscf` | `Table 6-18` | `0.01903` | `1258` | `0.788` |
| `dist_digins` | Distribution pipeline mishaps (dig-ins) | `non_routine_venting` | `unit` | `Table 6-46` | `0.0304` | `1697` | `0.934` |
| `dist_mr` | Distribution M&R station maintenance / upsets | `non_routine_venting` | `unit` | `Table 6-46` | `0.002895` | `159` | `0.948` |
| `dist_odorizer` | Distribution odorizer and gas sampling vents | `non_routine_venting` | `unit` | `Table 6-46` | `0.02275` | `1251` | `0.948` |
| `dist_pipeline_bd` | Distribution pipeline blowdowns | `non_routine_venting` | `unit` | `Table 6-46` | `0.0322` | `1798` | `0.934` |
| `dist_prv` | Distribution pressure relief valves | `non_routine_venting` | `unit` | `Table 6-46` | `0.0009591` | `54` | `0.934` |
| `gb_bd_compressor` | Compressor blowdowns (G&B) | `non_routine_venting` | `unit` | `Table 6-32` | `0.07239` | `4789` | `0.788` |
| `gb_bd_pipeline` | Gathering pipeline blowdowns | `non_routine_venting` | `unit` | `Table 6-32` | `0.00593` | `392` | `0.788` |
| `gb_bd_vessel` | Vessel blowdowns (G&B) | `non_routine_venting` | `unit` | `Table 6-32` | `0.0015` | `99` | `0.788` |
| `gb_cent_wet` | Centrifugal wet seal degassing, G&B / production (GHGRP) | `compressor_venting` | `unit_hr` | `Section 6.4.3` | `0.026` | `1738` | `0.788` |
| `gb_compressor_starts` | Compressor starts (G&B) | `non_routine_venting` | `unit` | `Table 6-33` | `0.16` | `10714` | `0.788` |
| `gb_digins` | Gathering pipeline mishaps (dig-ins) | `non_routine_venting` | `unit` | `Table 6-33` | `0.0128` | `849` | `0.788` |
| `gb_oil_pump_station` | Oil pump station maintenance | `non_routine_venting` | `unit` | `Table 6-33` | `0.00071` | `46.9` | `0.788` |
| `gb_pc_avg` | G&B controller, type and condition unknown | `pneumatic` | `unit_hr` | `Table 6-29` | `0.00014286706920206105` | `9.13` | `0.816` |
| `gb_pc_avg_malf` | G&B controller, type unknown, malfunctioning | `pneumatic` | `unit_hr` | `Table 6-29` | `None` | `19.09` | `0.816` |
| `gb_pc_avg_normal` | G&B controller, type unknown, normal operation | `pneumatic` | `unit_hr` | `Table 6-29` | `None` | `4.98` | `0.816` |
| `gb_pc_high_bleed` | G&B high-bleed controller | `pneumatic` | `unit_hr` | `Table 6-29` | `None` | `19.25` | `0.816` |
| `gb_pc_int_avg` | G&B intermittent, average | `pneumatic` | `unit_hr` | `Table 6-29` | `None` | `11.13` | `0.816` |
| `gb_pc_int_malf` | G&B intermittent, malfunctioning | `pneumatic` | `unit_hr` | `Table 6-29` | `None` | `16.11` | `0.816` |
| `gb_pc_int_normal` | G&B intermittent, normal operation | `pneumatic` | `unit_hr` | `Table 6-29` | `None` | `2.82` | `0.816` |
| `gb_pc_low_bleed_avg` | G&B low-bleed, average | `pneumatic` | `unit_hr` | `Table 6-29` | `None` | `6.42` | `0.816` |
| `gb_pc_low_bleed_malf` | G&B low-bleed, malfunctioning | `pneumatic` | `unit_hr` | `Table 6-29` | `None` | `34` | `0.816` |
| `gb_pc_low_bleed_normal` | G&B low-bleed, normal operation | `pneumatic` | `unit_hr` | `Table 6-29` | `None` | `0.68` | `0.816` |
| `gb_prv` | Pressure relief valve releases (G&B) | `non_routine_venting` | `unit` | `Table 6-33` | `0.00065` | `43` | `0.788` |
| `gb_rp_alberta` | Reciprocating rod packing, G&B / production (Alberta) | `compressor_venting` | `unit_hr` | `Table 6-30` | `0.000139` | `10.2` | `0.816` |
| `gb_rp_ghgrp` | Reciprocating rod packing, G&B / production (GHGRP) | `compressor_venting` | `unit_hr` | `Table 6-30` | `2.07e-05` | `1.37` | `0.788` |
| `gb_rp_us` | Reciprocating rod packing, G&B / production (US) | `compressor_venting` | `unit_hr` | `Table 6-30` | `0.000443` | `28.4` | `0.816` |
| `load_marine_barge` | Marine loading, barges | `loading` | `mgal` | `Table 6-47` | `0.45` | `None` | `None` |
| `load_marine_ship` | Marine loading, ships / ocean barges | `loading` | `mgal` | `Table 6-47` | `0.28` | `None` | `None` |
| `load_splash_dedicated` | Rail/truck splash loading, dedicated service | `loading` | `mgal` | `Table 6-47` | `2.2` | `None` | `None` |
| `load_splash_vapor_balance` | Rail/truck splash loading, vapor balance | `loading` | `mgal` | `Table 6-47` | `1.51` | `None` | `None` |
| `load_submerged_dedicated` | Rail/truck submerged loading, dedicated service | `loading` | `mgal` | `Table 6-47` | `0.91` | `None` | `None` |
| `load_submerged_vapor_balance` | Rail/truck submerged loading, vapor balance | `loading` | `mgal` | `Table 6-47` | `1.51` | `None` | `None` |
| `proc_blowdown_plant` | Gas processing blowdown venting | `non_routine_venting` | `unit` | `Table 6-39` | `54.4` | `3270000.0` | `0.868` |
| `proc_cent_dry` | Centrifugal dry seal, processing | `compressor_venting` | `unit` | `Table 6-38` | `28.19` | `1699440` | `0.868` |
| `proc_cent_wet` | Centrifugal wet seal, processing | `compressor_venting` | `unit` | `Table 6-38` | `86.43` | `5194680` | `0.868` |
| `proc_non_routine` | Gas processing non-routine emissions | `non_routine_venting` | `mmscf` | `Table 6-39` | `0.003524` | `212` | `0.868` |
| `proc_non_routine_m3` | Gas processing non-routine emissions (per 10^6 m3) | `non_routine_venting` | `mm_m3` | `Table 6-39` | `0.1244` | `7486.7093449555805` | `0.868` |
| `proc_pc_continuous` | Processing continuous-bleed controller | `pneumatic` | `unit_hr` | `Table 6-34` | `0.0009479452054794521` | `56.8` | `0.868` |
| `proc_pc_hydraulic_operator` | Processing pneumatic / hydraulic valve operator | `pneumatic` | `unit_hr` | `Table 6-34` | `1.071917808219178e-05` | `0.642` | `0.868` |
| `proc_pc_piston_operator` | Processing piston valve operator | `pneumatic` | `unit_hr` | `Table 6-34` | `9.143835616438356e-08` | `0.00548` | `0.868` |
| `proc_pc_turbine_operator` | Processing turbine valve operator | `pneumatic` | `unit_hr` | `Table 6-34` | `0.00012876712328767123` | `7.72` | `0.868` |
| `proc_recip` | Reciprocating compressor, processing (all modes) | `compressor_venting` | `unit` | `Table 6-37` | `16.3` | `981000.0` | `0.868` |
| `proc_rod_packing` | Reciprocating rod packing, processing | `compressor_venting` | `unit_hr` | `Table 6-37` | `0.0027` | `163.8` | `0.87` |
| `prod_pc_high_bleed_api` | Production high-bleed controller (API study) | `pneumatic` | `unit_hr` | `Table 6-14` | `None` | `16.4` | `0.816` |
| `prod_pc_high_bleed_ghgrp` | Production high-bleed controller (EPA GHGRP) | `pneumatic` | `unit_hr` | `Table 6-14` | `None` | `37.3` | `0.816` |
| `prod_pc_int_avg_api` | Production intermittent controller, average (API study) | `pneumatic` | `unit_hr` | `Table 6-15` | `None` | `9.3` | `0.816` |
| `prod_pc_int_ghgrp` | Production intermittent controller (EPA GHGRP) | `pneumatic` | `unit_hr` | `Table 6-15` | `None` | `13.5` | `0.816` |
| `prod_pc_int_malf_api` | Production intermittent controller, malfunctioning (API study) | `pneumatic` | `unit_hr` | `Table 6-15` | `None` | `24.1` | `0.816` |
| `prod_pc_int_normal_api` | Production intermittent controller, normal operation (API study) | `pneumatic` | `unit_hr` | `Table 6-15` | `None` | `0.28` | `0.816` |
| `prod_pc_low_bleed_api` | Production low-bleed controller (API study) | `pneumatic` | `unit_hr` | `Table 6-14` | `None` | `2.6` | `0.816` |
| `prod_pc_low_bleed_ghgrp` | Production low-bleed controller (EPA GHGRP) | `pneumatic` | `unit_hr` | `Table 6-14` | `None` | `1.39` | `0.816` |
| `pw_1000psi_10salt` | Produced water tank flashing, 1,000 psi separator, 10 % salt | `separation` | `bbl` | `Table 6-26` | `5.36e-05` | `None` | `None` |
| `pw_1000psi_20salt` | Produced water tank flashing, 1,000 psi separator, 20 % salt | `separation` | `bbl` | `Table 6-26` | `3.54e-05` | `None` | `None` |
| `pw_1000psi_2salt` | Produced water tank flashing, 1,000 psi separator, 2 % salt | `separation` | `bbl` | `Table 6-26` | `6.34e-05` | `None` | `None` |
| `pw_1000psi_avg` | Produced water tank flashing, 1,000 psi separator, salt unknown | `separation` | `bbl` | `Table 6-26` | `5.08e-05` | `None` | `None` |
| `pw_250psi_10salt` | Produced water tank flashing, 250 psi separator, 10 % salt | `separation` | `bbl` | `Table 6-26` | `1.5e-05` | `None` | `None` |
| `pw_250psi_20salt` | Produced water tank flashing, 250 psi separator, 20 % salt | `separation` | `bbl` | `Table 6-26` | `9.86e-06` | `None` | `None` |
| `pw_250psi_2salt` | Produced water tank flashing, 250 psi separator, 2 % salt | `separation` | `bbl` | `Table 6-26` | `1.77e-05` | `None` | `None` |
| `pw_250psi_avg` | Produced water tank flashing, 250 psi separator, salt unknown | `separation` | `bbl` | `Table 6-26` | `1.42e-05` | `None` | `None` |
| `pw_50psi_20salt` | Produced water tank flashing, 50 psi separator, 20 % salt | `separation` | `bbl` | `Table 6-26` | `1.5e-06` | `None` | `None` |
| `pw_shallow_gas_well` | Produced water, shallow gas well (76 psi or less) | `separation` | `bbl` | `Table 6-27` | `5.7e-06` | `None` | `None` |
| `sep_dump_valve_condensate` | Malfunctioning separator dump valve, condensate service | `separation` | `bbl` | `Table 6-25` | `2.64e-06` | `None` | `0.816` |
| `sep_dump_valve_crude` | Malfunctioning separator dump valve, crude service | `separation` | `bbl` | `Table 6-25` | `2.7e-06` | `None` | `0.816` |
| `stor_rp_operating` | Reciprocating rod packing, storage, operating | `compressor_venting` | `unit_hr` | `Table 6-40` | `0.00241` | `134` | `0.934` |
| `stor_station_bd` | Storage station blowdowns | `non_routine_venting` | `unit` | `Table 6-43` | `43` | `2400000.0` | `0.934` |
| `trans_rp_operating` | Reciprocating rod packing, transmission, operating | `compressor_venting` | `unit_hr` | `Table 6-40` | `0.00196` | `110` | `0.934` |
| `ts_cent_dry_avg` | Centrifugal dry seal, average | `compressor_venting` | `unit_hr` | `Table 6-41` | `0.00575` | `321` | `0.934` |
| `ts_cent_wet_avg` | Centrifugal wet seal, average | `compressor_venting` | `unit_hr` | `Table 6-41` | `0.0184` | `1028` | `0.934` |
| `ts_cent_wet_degassing` | Centrifugal wet seal degassing vent, operating | `compressor_venting` | `unit_hr` | `Table 6-41` | `0.00287` | `160` | `0.934` |
| `ts_cent_wet_operating` | Centrifugal wet seal, operating | `compressor_venting` | `unit_hr` | `Table 6-41` | `0.0304` | `1696` | `0.934` |
| `ts_compressor_bd` | Transmission compressor blowdowns | `non_routine_venting` | `unit` | `Table 6-43` | `47.14` | `2631000.0` | `0.934` |
| `ts_engine_starts` | Transmission engine starts | `non_routine_venting` | `unit` | `Table 6-43` | `29.06` | `1622000.0` | `0.934` |
| `ts_esd` | Transmission ESD activation | `non_routine_venting` | `unit` | `Table 6-43` | `7.97` | `444000.0` | `0.934` |
| `ts_mr_bd` | Transmission M&R station blowdowns | `non_routine_venting` | `unit` | `Table 6-43` | `13.75` | `756000.0` | `0.934` |
| `ts_pc_avg` | Transmission / storage controller, type unknown | `pneumatic` | `unit_hr` | `Table 6-42` | `0.00034246575342465754` | `19.3` | `0.934` |
| `ts_pc_continuous` | Transmission / storage continuous-vent controller | `pneumatic` | `unit_hr` | `Table 6-42` | `0.0003995433789954338` | `22.3` | `0.934` |
| `ts_pc_intermittent` | Transmission / storage intermittent-vent controller | `pneumatic` | `unit_hr` | `Table 6-42` | `4.5662100456621006e-05` | `2.5` | `0.934` |
| `ts_pipeline_venting` | Transmission pipeline venting | `non_routine_venting` | `unit` | `Table 6-43` | `0.6135` | `34200.0` | `0.934` |
| `ts_prv_lifts` | Transmission PRV lifts | `non_routine_venting` | `unit` | `Table 6-43` | `3.68` | `206000.0` | `0.934` |
| `ts_rp_operating` | Reciprocating rod packing, transmission & storage, operating | `compressor_venting` | `unit_hr` | `Table 6-40` | `0.00472` | `263` | `0.934` |
| `ts_rp_standby` | Reciprocating rod packing, transmission & storage, standby pressurized | `compressor_venting` | `unit_hr` | `Table 6-40` | `0.00691` | `385` | `0.934` |
| `ts_station_bd` | Transmission station blowdowns | `non_routine_venting` | `unit` | `Table 6-43` | `54` | `3014000.0` | `0.934` |
| `wo_gas` | Gas well workover (no HF) | `workovers` | `unit` | `Table 6-9` | `0.047` | `3114` | `0.788` |
| `wo_oil` | Oil well workover (no HF) | `workovers` | `unit` | `Table 6-9` | `0.0018` | `122` | `0.788` |
| `wt_gas` | Gas well test, vented | `well_testing` | `unit` | `Table 6-4` | `0.728` | `46625` | `0.816` |
| `wt_oil` | Oil well test, vented | `well_testing` | `unit` | `Table 6-4` | `0.057` | `3613` | `0.816` |

### 3. Grid Electricity Emission Factors (`new/server/electricity_factors.py`)
- **Total Subregions / Countries**: 61
| Region / Subregion | Country | Year | Factor (kg CO2e / kWh) | Source |
| :--- | :--- | :--- | :--- | :--- |
| `Algerian National Grid` |  |  | `` | Derived: MEM Bilan Energetique National 2024 x IPCC 2006 natural gas defaults |
| `Austria (grid average)` |  |  | `` | API Compendium 2021 Table 8-6 |
| `Belgium (grid average)` |  |  | `` | API Compendium 2021 Table 8-6 |
| `Bulgaria (grid average)` |  |  | `` | API Compendium 2021 Table 8-6 |
| `Croatia (grid average)` |  |  | `` | API Compendium 2021 Table 8-6 |
| `Cyprus (grid average)` |  |  | `` | API Compendium 2021 Table 8-6 |
| `Czech Republic (grid average)` |  |  | `` | API Compendium 2021 Table 8-6 |
| `Denmark (grid average)` |  |  | `` | API Compendium 2021 Table 8-6 |
| `Estonia (grid average)` |  |  | `` | API Compendium 2021 Table 8-6 |
| `Finland (grid average)` |  |  | `` | API Compendium 2021 Table 8-6 |
| `France (grid average)` |  |  | `` | API Compendium 2021 Table 8-6 |
| `Germany (grid average)` |  |  | `` | API Compendium 2021 Table 8-6 |
| `Greece (grid average)` |  |  | `` | API Compendium 2021 Table 8-6 |
| `Hungary (grid average)` |  |  | `` | API Compendium 2021 Table 8-6 |
| `Iceland (grid average)` |  |  | `` | API Compendium 2021 Table 8-6 |
| `Ireland (grid average)` |  |  | `` | API Compendium 2021 Table 8-6 |
| `Italy (grid average)` |  |  | `` | API Compendium 2021 Table 8-6 |
| `Latvia (grid average)` |  |  | `` | API Compendium 2021 Table 8-6 |
| `Lithuania (grid average)` |  |  | `` | API Compendium 2021 Table 8-6 |
| `Luxembourg (grid average)` |  |  | `` | API Compendium 2021 Table 8-6 |
| `Malta (grid average)` |  |  | `` | API Compendium 2021 Table 8-6 |
| `Netherlands (grid average)` |  |  | `` | API Compendium 2021 Table 8-6 |
| `Norway (grid average)` |  |  | `` | API Compendium 2021 Table 8-6 |
| `Poland (grid average)` |  |  | `` | API Compendium 2021 Table 8-6 |
| `Portugal (grid average)` |  |  | `` | API Compendium 2021 Table 8-6 |
| `Romania (grid average)` |  |  | `` | API Compendium 2021 Table 8-6 |
| `Serbia (grid average)` |  |  | `` | API Compendium 2021 Table 8-6 |
| `Slovakia (grid average)` |  |  | `` | API Compendium 2021 Table 8-6 |
| `Slovenia (grid average)` |  |  | `` | API Compendium 2021 Table 8-6 |
| `Spain (grid average)` |  |  | `` | API Compendium 2021 Table 8-6 |
| `Sweden (grid average)` |  |  | `` | API Compendium 2021 Table 8-6 |
| `Switzerland (grid average)` |  |  | `` | API Compendium 2021 Table 8-6 |
| `US Average` |  |  | `` | API Compendium 2021 Table 8-2 |
| `US-AKGD (ASCC Alaska Grid)` |  |  | `` | API Compendium 2021 Table 8-2 |
| `US-AKMS (ASCC Miscellaneous)` |  |  | `` | API Compendium 2021 Table 8-2 |
| `US-AZNM (WECC Southwest)` |  |  | `` | API Compendium 2021 Table 8-2 |
| `US-CAMX (WECC California)` |  |  | `` | API Compendium 2021 Table 8-2 |
| `US-ERCT (ERCOT All)` |  |  | `` | API Compendium 2021 Table 8-2 |
| `US-FRCC (FRCC All)` |  |  | `` | API Compendium 2021 Table 8-2 |
| `US-HIMS (HICC Miscellaneous)` |  |  | `` | API Compendium 2021 Table 8-2 |
| `US-HIOA (HICC Oahu)` |  |  | `` | API Compendium 2021 Table 8-2 |
| `US-MROE (MRO East)` |  |  | `` | API Compendium 2021 Table 8-2 |
| `US-MROW (MRO West)` |  |  | `` | API Compendium 2021 Table 8-2 |
| `US-NEWE (NPCC New England)` |  |  | `` | API Compendium 2021 Table 8-2 |
| `US-NWPP (WECC Northwest)` |  |  | `` | API Compendium 2021 Table 8-2 |
| `US-NYCW (NPCC NYC/Westchester)` |  |  | `` | API Compendium 2021 Table 8-2 |
| `US-NYLI (NPCC Long Island)` |  |  | `` | API Compendium 2021 Table 8-2 |
| `US-NYUP (NPCC Upstate NY)` |  |  | `` | API Compendium 2021 Table 8-2 |
| `US-PRMS (Puerto Rico Miscellaneous)` |  |  | `` | API Compendium 2021 Table 8-2 |
| `US-RFCE (RFC East)` |  |  | `` | API Compendium 2021 Table 8-2 |
| `US-RFCM (RFC Michigan)` |  |  | `` | API Compendium 2021 Table 8-2 |
| `US-RFCW (RFC West)` |  |  | `` | API Compendium 2021 Table 8-2 |
| `US-RMPA (WECC Rockies)` |  |  | `` | API Compendium 2021 Table 8-2 |
| `US-SPNO (SPP North)` |  |  | `` | API Compendium 2021 Table 8-2 |
| `US-SPSO (SPP South)` |  |  | `` | API Compendium 2021 Table 8-2 |
| `US-SRMV (SERC Mississippi Valley)` |  |  | `` | API Compendium 2021 Table 8-2 |
| `US-SRMW (SERC Midwest)` |  |  | `` | API Compendium 2021 Table 8-2 |
| `US-SRSO (SERC South)` |  |  | `` | API Compendium 2021 Table 8-2 |
| `US-SRTV (SERC Tennessee Valley)` |  |  | `` | API Compendium 2021 Table 8-2 |
| `US-SRVC (SERC Virginia/Carolina)` |  |  | `` | API Compendium 2021 Table 8-2 |
| `United Kingdom (grid average)` |  |  | `` | API Compendium 2021 Table 8-6 |

### 4. Scope 3 Activity Factors (`new/server/emission_factors/scope3_activity_factors.py`)
- **Total Activity Factor Items**: 55 rows across 15 categories
| Category ID | Activity / Spend Subcategory | Unit | Factor (kg CO2e / unit) |
| :--- | :--- | :--- | :--- |
| Cat 1 | Iron & steel products (NAICS 331110) | `USD` | `0.787` |
| Cat 1 | Steel pipe & tube (NAICS 331210) | `USD` | `0.36` |
| Cat 1 | Cement (NAICS 327310) | `USD` | `3.924` |
| Cat 1 | Organic chemicals (NAICS 325199) | `USD` | `1.184` |
| Cat 1 | Inorganic chemicals (NAICS 325180) | `USD` | `1.01` |
| Cat 1 | Oil & gas support services (NAICS 213112) | `USD` | `0.372` |
| Cat 1 | Engineering services (NAICS 541330) | `USD` | `0.103` |
| Cat 2 | Oil & gas field machinery (NAICS 333132) | `USD` | `0.219` |
| Cat 2 | Pipeline construction (NAICS 237120) | `USD` | `0.277` |
| Cat 2 | Commercial / industrial buildings (NAICS 236220) | `USD` | `0.224` |
| Cat 2 | Computers (NAICS 334111) | `USD` | `0.058` |
| Cat 3 | Purchased refined fuels, upstream (NAICS 324110) | `USD` | `0.27` |
| Cat 3 | Purchased natural gas, upstream (NAICS 211130) | `USD` | `0.405` |
| Cat 3 | T&D Losses (Electricity) | `kWh` | `None` |
| Cat 4 | Truck Transport | `ton-km` | `0.12841` |
| Cat 4 | Rail Transport | `ton-km` | `0.01451` |
| Cat 4 | Ship Transport | `ton-km` | `0.0537` |
| Cat 4 | Air Freight | `ton-km` | `0.74991` |
| Cat 5 | Landfill (mixed MSW) | `kg` | `0.6393` |
| Cat 5 | Incineration (mixed MSW) | `kg` | `0.474` |
| Cat 5 | Recycling (mixed recyclables) | `kg` | `0.0992` |
| Cat 5 | Composting (mixed organics) | `kg` | `0.1433` |
| Cat 6 | Air - Short Haul (< 300 mi) | `passenger-km` | `0.12982` |
| Cat 6 | Air - Medium Haul (300-2300 mi) | `passenger-km` | `0.08084` |
| Cat 6 | Air - Long Haul (>= 2300 mi) | `passenger-km` | `0.10215` |
| Cat 6 | Passenger Car | `km` | `0.18552` |
| Cat 6 | Light-Duty Truck / SUV | `km` | `0.24646` |
| Cat 6 | Intercity Rail | `passenger-km` | `0.06012` |
| Cat 6 | Bus | `passenger-km` | `0.0414` |
| Cat 7 | Passenger Car | `km` | `0.18552` |
| Cat 7 | Light-Duty Truck / SUV | `km` | `0.24646` |
| Cat 7 | Bus | `passenger-km` | `0.0414` |
| Cat 7 | Commuter Rail | `passenger-km` | `0.08325` |
| Cat 7 | Transit Rail (subway, tram) | `passenger-km` | `0.05808` |
| Cat 8 | Leased buildings (rent) (NAICS 531120) | `USD` | `0.246` |
| Cat 8 | Leased Vehicles (passenger car) | `km` | `0.18552` |
| Cat 9 | Truck Transport | `ton-km` | `0.12841` |
| Cat 9 | Rail Transport | `ton-km` | `0.01451` |
| Cat 9 | Ship Transport | `ton-km` | `0.0537` |
| Cat 9 | Air Freight | `ton-km` | `0.74991` |
| Cat 10 | Processing (Electricity) | `kWh` | `None` |
| Cat 10 | Processing (Natural Gas) | `mcf` | `54.18` |
| Cat 11 | Crude Oil | `bbl` | `433.44` |
| Cat 11 | Natural Gas | `mcf` | `54.18` |
| Cat 11 | NGL - Ethane | `gal` | `4.07` |
| Cat 11 | NGL - Propane | `gal` | `5.74` |
| Cat 11 | NGL - Butane | `gal` | `6.7` |
| Cat 11 | NGL - Mixed (as LPG) | `gal` | `5.7` |
| Cat 12 | Landfill (mixed MSW) | `kg` | `0.6393` |
| Cat 12 | Recycling (mixed recyclables) | `kg` | `0.0992` |
| Cat 12 | Incineration (mixed MSW) | `kg` | `0.474` |
| Cat 13 | Downstream leased buildings (rent) (NAICS 531120) | `USD` | `0.246` |
| Cat 14 | Franchise operations | `USD` | `None` |
| Cat 15 | Equity Investments | `USD` | `None` |
| Cat 15 | Project Finance | `USD` | `None` |

---

## 5. Global Warming Potential (GWP) Sets

| Assessment Report | Time Horizon | CH4 GWP | N2O GWP | Fossil CH4 GWP | Application Spots |
| :--- | :--- | :--- | :--- | :--- | :--- |
| IPCC SAR / AR4 | 100-year | 25.0 | 298.0 | N/A | `constants.py` |
| IPCC AR5 (Default) | 100-year | 28.0 | 265.0 | N/A | Default throughout backend & frontend |
| IPCC AR5 | 20-year | 84.0 | 264.0 | N/A | Dashboard 20-year GWP metrics |
| IPCC AR6 | 100-year | 29.8 | 273.0 | 29.8 | Configurable GWP override |
| IPCC AR6 | 20-year | 82.5 | 273.0 | 82.5 | Configurable GWP override |

---

## 6. Calculation Formulas and Equations per Process Type and Tier

### Tier 1: Catalog Emission Factor Lookup
$$E_i = Activity \times EF_i \times UnitConversion$$
$$CO_2e = \sum_i (E_i \times GWP_i)$$

### Tier 2: Custom Emission Factor / Fuel Heating Value (HHV) / Density
- When activity is mass/volume and factor is energy-based (Btu, MJ, MMBtu):
  $$E_i = Activity \times HHV_{measured} \times EF_{energy, i}$$
- When volume-to-mass or mass-to-volume requires site density:
  $$Mass = Volume \times \rho_{measured}$$

### Tier 3: Engineering Calculations & Physical Models
1. **Combustion Stoichiometry (`combustion.py`)**:
   $$CO_2 = FuelMass \times CarbonMassFraction \times \eta_{comb} \times \frac{44.01}{12.011}$$
   $$CH_4 = FuelMass \times (1 - \eta_{comb}) \times MethaneFraction$$
2. **Flaring (`flaring.py` / `combustion.py`)**:
   - Combusted carbon -> CO2 with combustion efficiency $\eta_{flare}$ (default 98% or 96.5%)
   - Unburned methane slip -> CH4 with destruction removal efficiency (DRE)
3. **Venting / Blowdown (`venting.py`)**:
   $$V_{std} = V_{geom} \times \frac{P_{actual}}{P_{std}} \times \frac{T_{std}}{T_{actual}} \times \frac{1}{Z}$$
4. **Pneumatic Devices (`venting.py`)**:
   $$E_{CH4} = Count \times BleedRate \times Hours \times MolFraction_{CH4} \times \rho_{CH4}$$
5. **Acid Gas Removal (AGR) Units (`fugitive_other.py`)**:
   $$CO_2 = Throughput \times (y_{CO2, in} - y_{CO2, out}) \times (1 - \eta_{control})$$
6. **Dehydrators (`fugitive_other.py`)**:
   - Glycol pump circulation rate model, flash tank vapor recovery, still vent control
7. **Storage Tanks (`fugitive_other.py`)**:
   - Flashing losses via GOR (Vasquez-Beggs empirical correlation or E&P TANKS)
   - Working and breathing losses via API MPMS Chapter 19
8. **Equipment Fugitives (`fugitive_other.py`)**:
   - Method 21 screening ranges (<10,000 ppmv vs >=10,000 ppmv)
   - EPA / API correlation equations
   - OGI leaker count approach
   - Direct measurement rate

---

## 7. Rounding, Formatting, and Aggregation Rules

### Aggregation Hierarchy
1. **Facility Level**: Monthly records -> Annual sums per facility
2. **Period Level**: Monthly activity aggregation -> Annual Scope 1, 2, 3 totals
3. **Corporate Level**: Sum across all facilities, weighted by Equity Share %
4. **Dashboard Breakdown**: Aggregation by Process Type, Gas Species (CO2, CH4, N2O), Scope

### Operational Intensities (`services/intensity.py`, `dashboard_filters.py`)
- **BOE (Barrel of Oil Equivalent) Conversion**:
  - Gas conversion: `GAS_BOE_PER_MSCF = 1020 / 1000 / 5.8 = 0.17586206896551725` BOE/Mscf
  - Total BOE = Crude Oil (bbl) + Condensate (bbl) + NGL (bbl) + LPG (bbl) + (Gas Mscf * 0.175862)
- **GHG Intensity**: `Total tCO2e / Total Production BOE`
- **Methane Intensity**: `Total tCH4 / Total Gas Production tCH4` (or % of gross gas produced)
- **WEC (Waste Emissions Charge)**: Methane intensity threshold comparison (0.20% for production)

### Rounding Implementation in Codebase
- **Backend Calculation**: Native Python 64-bit float IEEE-754 precision throughout calculation modules
- **Backend Storage**: Stored in SQLite as `FLOAT` without truncating decimals
- **Dashboard Response (`routes/dashboard.py` lines 536-538)**:
  - `round(scope1_total, 6)`, `round(scope1_total_gwp100, 6)`, `round(scope1_total_gwp20, 6)`
  - *Observation*: `scope2_total`, `co2_total`, `ch4_total`, `n2o_total` are returned unrounded!
- **Frontend Display (`new/client/src/utils/formatters.ts`)**:
  - `formatNumber(val, decimals=2)`: Uses `toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })`
  - `formatPercent(val)`: Displays with 1 or 2 decimals

---

## 8. API Endpoints and Database Schema

### Total API Endpoints: 214
- **Endpoints with Numeric Data Flow**: 117
Key calculation, ingestion, and reporting routes:
- `POST /api/emissions/`: Scope 1 single activity ingestion & emission calculation
- `POST /api/emissions/bulk-upload`: Scope 1 batch file processing
- `POST /api/scope2`: Scope 2 calculation and creation
- `POST /api/scope3`: Scope 3 calculation and creation
- `POST /api/scope3/eeio-calculate`: Scope 3 EEIO spend-based calculation
- `GET /api/dashboard/summary`: Dashboard corporate aggregates
- `GET /api/dashboard/categorical-breakdown`: Breakdown by source category
- `GET /api/dashboard/granular-intensities`: Facility & corporate production intensity
- `GET /api/dashboard/uncertainty`: Error propagation uncertainty analysis
- `GET /api/emissions/export`: CSV/Excel export of calculated records

### Database Schema: 29 Tables, 204 Numeric Columns
| Table Name | Numeric Column Count | Numeric Columns |
| :--- | :--- | :--- |
| `activity_log` | 3 | `id, user_id, facility_id` |
| `base_year` | 3 | `id, year, locked` |
| `base_year_recalculations` | 6 | `id, year, previous_emissions, adjusted_emissions, approved_by, created_by` |
| `cbam_product_exports` | 13 | `id, facility_id, year, month, quantity_tonnes, specific_embedded_direct, specific_embedded_indirect, captured_co2_tonnes, carbon_price_paid_eur, precursor_ratio, precursor_see_dir, precursor_see_indir, created_by` |
| `component_inventories` | 7 | `id, facility_id, emission_source_id, quantity, operating_hours, factor_value, created_by` |
| `custom_factors` | 14 | `id, co2_factor, ch4_factor, n2o_factor, co_factor, hhv_factor, uncertainty, co2_uncertainty, ch4_uncertainty, n2o_uncertainty, uncertainty_pct, created_by, approved_by, facility_id` |
| `emission_sources` | 3 | `id, facility_id, created_by` |
| `emissions` | 29 | `id, year, month, quantity, ef_used_co2, ef_used_ch4, ef_used_n2o, ef_used_co, co2_emissions, ch4_emissions, n2o_emissions, co_emissions, co2e_total, co2_biogenic, combustion_efficiency, uncertainty, uncertainty_ch4, uncertainty_n2o, uncertainty_pct, uncertainty_ad, uncertainty_ef_co2, uncertainty_ef_ch4, uncertainty_ef_n2o, facility_id, ogmp_level, created_by, updated_by, approved_by, custom_factor_id` |
| `facilities` | 7 | `id, equity_share_pct, ogmp_membership_year, reconciliation_threshold, latitude, longitude, created_by` |
| `facility_equity_shares` | 4 | `id, facility_id, partner_id, equity_share_pct` |
| `flaring_details` | 9 | `id, facility_id, year, month, routine_knm3, non_routine_knm3, safety_knm3, total_knm3, measured_dre_pct` |
| `fugitive_surveys` | 8 | `id, facility_id, component_inventory_id, detection_threshold_ppm, screening_value_ppm, measured_emission_rate, leaking_hours, created_by` |
| `goals` | 2 | `year, target_amount` |
| `import_mappings` | 2 | `id, user_id` |
| `jv_partners` | 1 | `id` |
| `level_upgrade_logs` | 5 | `id, facility_id, old_level, new_level, created_by` |
| `methane_source_types` | 2 | `id, default_level` |
| `mitigation_projects` | 6 | `id, year, quantity_tco2e, investment_amount, facility_id, created_by` |
| `mitigation_records` | 3 | `id, year, quantity_tco2e` |
| `notifications` | 2 | `id, user_id` |
| `ogmp_surveys` | 10 | `id, facility_id, year, measured_rate_kg_hr, operating_hours_year, estimated_annual_tch4, detection_threshold, bottom_up_tch4, variance_pct, created_by` |
| `production_data` | 18 | `id, facility_id, month, year, oil_amount, gas_amount, gross_gas_mmsm3, injected_gas_mmsm3, gas_without_injected_mmsm3, crude_oil_mmboe, condensate_mmboe, lpg_mmboe, ngl_mmboe, total_production_mmboe, total_production_no_injected_mmboe, saleable_production_mmboe, fuel_gas_export_mmsm3, created_by` |
| `reporting_metadata` | 4 | `id, year, has_reduction_target, is_tcfd_aligned` |
| `sbti_targets` | 6 | `id, base_year, base_year_emissions, target_year, reduction_rate_pct, created_by` |
| `scope2_emissions` | 18 | `id, facility_id, year, month, electricity_kwh, steam_ton, heat_mmbtu, cooling_ton, emission_factor, co2e, co2e_location_based, co2e_market_based, market_emission_factor, uncertainty, uncertainty_pct, created_by, approved_by, updated_by` |
| `scope3_data` | 5 | `id, year, volume, emission_factor, emissions_tco2e` |
| `scope3_emissions` | 12 | `id, facility_id, year, month, activity_data, emission_factor, co2e, uncertainty, uncertainty_pct, created_by, approved_by, updated_by` |
| `system_settings` | 0 | `` |
| `users` | 2 | `id, session_version` |

---

## 9. Definition of Tiers and Fallback Logic

### Tier Definitions
- **Tier 1 (Catalog Default)**: Generic emission factors based on activity quantity (API Compendium Tables 3-x, 4-x, 5-x, US EPA, IPCC). Requires only quantity and unit.
- **Tier 2 (Custom / Site-Specific Factor or Fuel Properties)**: User-measured higher heating value (HHV), fuel density, or supplier-specific emission factors.
- **Tier 3 (Engineering Calculations / Direct Measurement)**: Physical process models, detailed gas chromatography / molar compositions, equipment operational parameters, CEMS continuous measurement.

### Fallback Mechanics in `new/server/calculations/legacy_engine.py`
1. If an emission calculation is invoked with Tier 3 inputs missing, invalid, or out-of-range, the engine falls back to Tier 2 if custom factor parameters exist.
2. If custom factor parameters are absent, it falls back to Tier 1 default catalog factors.
3. The fallback is flagged in the record metadata and audit trail (`ogmp_level` or `tier_applied`).

---

## 10. Suspicious Spots and Observations for Testing

These items are potential sources of numerical discrepancy, drift, or calculation bugs. They are cataloged here for test coverage in Phase 3:

1. **Hardcoded / Truncated Physical Constants in `fugitive_other.py`**:
   - `LB_PER_TONNE = 2204.62` (vs NIST exact value `2204.6226218487758...`, error = ~0.001%)
   - `L_PER_GAL = 3.785412` (vs `units.py` `3.785411784`)
   - `FT3_PER_M3 = 35.3147` (vs `units.py` `35.31466672148859`)
   - *Risk*: Multiple internal representations of physical constants leading to path-dependent conversion errors.

2. **Duplicate Factor Catalog & Logic in Frontend**:
   - `new/client/src/utils/EmissionFactors.ts` duplicates 71 emission factors.
   - `new/client/src/components/GasCompositionCalculator.tsx` performs independent stoichiometric calculations (carbon mass fraction, HHV, density, emission factors) directly in the browser.
   - *Risk*: Desynchronization between frontend live previews and backend database-persisted results.

3. **Barrel of Oil Equivalent (BOE) Discrepancy**:
   - `docs/calculation-specification.md` line 301 states: `Gas_mscf * 0.178`
   - `docs/calculation-specification.md` line 332 and `services/dashboard_filters.py` use: `GAS_BOE_PER_MSCF = 1020 / 1000 / 5.8 = 0.17586206896551725`
   - *Risk*: A 1.2% difference in BOE calculation and operational intensity metrics.

4. **Selective / Inconsistent Mid-Chain Rounding in API Responses**:
   - `routes/dashboard.py` lines 536-538 explicitly applies `round(scope1_total, 6)` while leaving `scope2_total`, `co2_total`, `ch4_total`, and `n2o_total` as raw floats.
   - *Risk*: Scope 1 + Scope 2 != Corporate Total due to rounding of one addend but not the other.

5. **Unreachable / Aliased Calculators in `CalculationDispatcher`**:
   - Several specialized calculators in `vented_downstream.py` (`RefiningCokerCalculator`, `RefiningCatalystRegenCalculator`, `SulfurRecoveryTailGasCalculator`) appear to be shadowed or routed to generic stoichiometric calculators.
   - *Risk*: Dead code or wrong engineering equation applied.

6. **Standard Gas Density Basis Differences**:
   - Backend engine constants: `CH4 = 16.04 / 23.685 = 0.67722 kg/m³` at 60°F / 14.696 psia.
   - API Compendium 2021 exhibits: standard conditions often use 16.0 lb/lb-mol / 379.3 scf/lb-mol = 0.04218 lb/scf (= 0.67567 kg/m³), producing a +0.2235% shift.
   - *Risk*: Inherent difference between API exhibit worked examples and theoretical molar volume arithmetic.

7. **Float Arithmetic Drift and Equality Comparisons**:
   - Multiple modules use standard Python IEEE-754 `float` instead of `decimal.Decimal`.
   - Aggregations over thousands of rows may accumulate float precision drift.
