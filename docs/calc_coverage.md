# NeoCarbon Calculation Coverage & Methodology Matrix
**Standard Compliance:** API Compendium 2021, GHG Protocol Corporate Standard, GHG Protocol Scope 3 Standard, ISO 14064-1:2018, IPCC Guidelines (2006/2019 Refinement), OGMP 2.0.

---

## 1. Scope 1: Direct GHG Emissions

| Process Category | Specific Process / Source Type | Tier 1 (Default / Population) | Tier 2 (Regional / Composition / Engineering) | Tier 3 (Measurement / GC / CEMS) | Supported Activity Units | Emission Outputs & Factors |
|---|---|---|---|---|---|---|
| **Stationary Combustion** | Boilers, Turbines, Reciprocating Engines, Heaters, Incinerators | Fuel Volume/Energy × Tabulated API Compendium Table 4-3/4-6 EFs | Site Fuel Analysis (Heating Value HHV + Fuel Carbon % + API Stoichiometry) | Continuous Emission Monitoring Systems (CEMS) / Direct Fuel Gas Chromatography | `scf`, `mscf`, `mmscf`, `m3`, `sm3`, `gal`, `bbl`, `l`, `tonne`, `short_ton`, `MMBtu`, `GJ`, `MJ` | $\text{CO}_2, \text{CH}_4, \text{N}_2\text{O}$ |
| **Flaring** | HP Flares, LP Flares, Acid Gas Flares, Assist Flares | Flare Gas Volume × Default EF (or standard 98% combustion efficiency) | Measured Flare Volume + Stream Composition (mol% $\text{CH}_4, \text{CO}_2, \text{C}_2+$) + Flare Efficiency (e.g. 98.0% or 99.2%) | Ultrasonic flare meter + Online Gas Chromatograph (GC) | `m3`, `sm3`, `ksm3`, `mmsm3`, `scf`, `mscf`, `mmscf` | $\text{CO}_2, \text{CH}_4, \text{N}_2\text{O}$ |
| **Venting: Pneumatics** | High-bleed, Low-bleed, Intermittent, Chemical Injection Pumps | Device Count × Operating Hours × API Table 5-15 Population Factors | Controller Supply Pressure + Stroke Rate / Manufacturer Discharge Curve | Calibrated Bagging / Ultrasonic Leak Flow Meter | `device-hours`, `count`, `scf`, `m3` | $\text{CH}_4, \text{CO}_2$ |
| **Venting: Storage Tanks** | Atmospheric Crude Oil & Condensate Storage Tanks | Production Throughput × Regional Flashing Factor | Vasquez-Beggs / Peng-Robinson Equation of State simulation / E&P TANKS | Direct Vapor Recovery Metering / Calibrated Vent Meter | `bbl`, `m3`, `scf`, `mscf` | $\text{CH}_4, \text{CO}_2, \text{VOC}$ |
| **Venting: Liquids Unloading** | Wellbore Liquids Unloading (with & without Plunger Lift) | Event Count × Well Depth × Casing Diameter Default Factor | Gas Well Flow Equation (Turners / Coleman Critical Velocity, Vent Time × Pressure) | Calibrated Orifice Meter during blowdown flow | `events`, `hours`, `mscf`, `m3` | $\text{CH}_4, \text{CO}_2$ |
| **Venting: Blowdowns** | Compressors, Pipeline Blowdowns, Vessel Purging | Component Count × API Event Factor | Physical Void Volume $V \times \frac{P \cdot T_{\text{std}}}{P_{\text{std}} \cdot T \cdot Z} \times \text{mol}\%\ \text{CH}_4$ | Flow meter on flare/vent header during shutdown | `events`, `scf`, `m3`, `mscf` | $\text{CH}_4, \text{CO}_2$ |
| **Venting: Associated Gas** | Casinghead Gas Venting | Oil Production × GOR (Gas-Oil Ratio) × Vented Fraction | Measured GOR + Field Gas Composition Analysis | Gas Flow Meter on Separator Vent Line | `bbl`, `m3`, `mscf`, `scf` | $\text{CH}_4, \text{CO}_2$ |
| **Venting: Mud Degassing** | Drilling Mud Circulation Gas Extraction | Drilling Days × Mud Weight Factor | Gas-cut mud volume × Separator efficiency × mud gas analysis | Continuous degasser exhaust sensor / GC | `drilling_days`, `bbl`, `m3` | $\text{CH}_4, \text{CO}_2$ |
| **Fugitives: Equipment Leaks** | Valves, Pump Seals, Flanges, Connectors, Compressor Seals, PRVs | Component Count × EPA/API Average Emission Factors | EPA Method 21 Screening (ppmv) with EPA Correlation Equations / OGI Protocol | Calibrated High-Flow Sampler / Bagging measurement of leaks | `component_count`, `hours`, `kg/hr` | $\text{CH}_4, \text{CO}_2, \text{VOC}$ |
| **Process: Acid Gas Removal (AGR)** | Amine Sweetening Units | Gas Throughput × Feed $\text{CO}_2\ \text{mol}\%$ | Process Simulator (ProMax/HYSYS) / Stoichiometric Feed-Product Differential | Inlet & Outlet CEMS or GC | `mscf`, `mmscf`, `m3`, `sm3` | $\text{CO}_2$ |
| **Process: Glycol Dehydration** | TEG / DEG Dehydrators | Gas Throughput × Default Glycol Vent Factor | GRI-GLYCalc simulation / Rich-Lean Glycol circulation mass balance | Regenerator overhead condenser flow measurement | `mscf`, `mmscf`, `m3`, `sm3` | $\text{CH}_4, \text{CO}_2, \text{VOC}$ |
| **Process: Sulfur Recovery** | Claus Units / Tail Gas Incinerators | Sulfur Production × Default Combustion Factor | Feed $\text{H}_2\text{S} / \text{CO}_2$ Stoichiometric Mass Balance | Tail gas stack CEMS | `tonne`, `short_ton`, `kg` | $\text{CO}_2$ |
| **Drilling Operations** | Onshore/Offshore Drilling Rigs | Rig Days × Default Rig Daily Emission Factor | Fuel Metering (Diesel) by Engine Load Factor | Direct Engine Fuel Meter + Dynamometer / CEMS | `rig_days`, `gal`, `bbl`, `l`, `tonne` | $\text{CO}_2, \text{CH}_4, \text{N}_2\text{O}$ |
| **Completions & Workovers** | Well Hydraulic Fracturing & Flowback | Well Count × Default Completion Emission Factor | Flowback Separator Volume + Gas-to-Liquid Ratio Equation | Orifice Meter on Completion Flowback Line | `completions`, `mscf`, `m3` | $\text{CO}_2, \text{CH}_4$ |

---

## 2. Scope 2: Indirect Emissions from Purchased Energy

| Source Type | Calculation Method | Tiers / Data Sources | Activity Units | Primary Reference |
|---|---|---|---|---|
| **Purchased Electricity (Location-based)** | $\text{Electricity (kWh)} \times \text{Grid EF}_{\text{loc}}$ | National / Subregional Grid Average (e.g. Algerian National Grid 0.4974 kg $\text{CO}_2/\text{kWh}$, US eGRID2019, AIB 2020) | `kWh`, `MWh`, `GWh` | API Compendium §8.1, GHG Protocol Scope 2 Guidance |
| **Purchased Electricity (Market-based)** | $\text{Electricity (kWh)} \times \text{Supplier / Contract EF}$ | Contractual Instruments (PPA, EAC/REC, Guarantees of Origin, Supplier-specific emission factor, Residual Mix) | `kWh`, `MWh`, `GWh` | GHG Protocol Scope 2 Guidance Table 6.3 |
| **Purchased Steam / District Heat** | $\frac{\text{Heat Delivered (MMBtu)}}{\text{Boiler Efficiency} - \text{Transmission Loss}} \times \text{Fuel EF}$ | Enthalpy calculation from steam temperature and pressure, boiler efficiency (default 80%), transmission loss (default 5%) | `MMBtu`, `GJ`, `lb`, `klb`, `tonne` | API Compendium Exhibit 8.3 |
| **Cogeneration (CHP Allocation)** | Efficiency / Energy Allocation of CHP fuel between power and heat | API Compendium Equation 8-4 (Efficiency Method allocating fuel by work and heat output) | `kWh`, `MMBtu`, `GJ` | API Compendium §8.2 |

---

## 3. Scope 3: Value Chain Greenhouse Gas Emissions

| Scope 3 Category | Activity Description | Tier / Calculation Method | Activity Units | Default Emission Factors | Source Reference |
|---|---|---|---|---|---|
| **Cat 1: Purchased Goods & Services** | Direct materials (steel, cement, chemicals) and services | Spend-based (EEIO) or Mass-based (supplier cradle-to-gate) | `USD`, `kg`, `tonne` | Steel: 0.787 kg/USD, Cement: 3.924 kg/USD, Chemicals: 1.184 kg/USD | EPA Supply Chain GHG Factors v1.3.0 |
| **Cat 2: Capital Goods** | Drilling rigs, compressors, pipelines, buildings | Spend-based (EEIO) | `USD` | Machinery: 0.219 kg/USD, Pipelines: 0.277 kg/USD | EPA Supply Chain GHG Factors v1.3.0 |
| **Cat 3: Fuel- & Energy-Related Activities** | Well-to-tank (WTT) upstream fuel extraction and T&D electrical grid losses | Activity fuel/electricity × upstream lifecycle factor | `USD`, `kWh` | Upstream gas: 0.405 kg/USD, Upstream fuel: 0.270 kg/USD | DEFRA / IEA / EPA Hub |
| **Cat 4: Upstream Transportation** | Freight transit of purchased goods by truck, rail, marine, air | Mass-Distance ($\text{tonne} \cdot \text{km}$) × Modal Factor | `ton-km`, `tonne-km` | Truck: 0.12841, Rail: 0.01451, Ship: 0.05370, Air: 0.74991 kg $\text{CO}_2\text{e}/\text{t-km}$ | EPA Emission Factors Hub 2025 |
| **Cat 5: Waste Generated in Operations** | Industrial & municipal solid waste disposal | Waste Mass × Treatment Method EF | `kg`, `tonne` | Landfill: 0.6393, Incineration: 0.4740, Recycling: 0.0992 kg $\text{CO}_2\text{e}/\text{kg}$ | EPA Emission Factors Hub 2025 |
| **Cat 6: Business Travel** | Commercial air travel, car rental, rail | Passenger-Distance ($\text{passenger} \cdot \text{km}$) × Mode | `passenger-km`, `km` | Short flight: 0.12982, Long flight: 0.10215, Car: 0.18552 kg $\text{CO}_2\text{e}/\text{p-km}$ | EPA Emission Factors Hub 2025 |
| **Cat 7: Employee Commuting** | Employee daily commute transit | Commute distance × Vehicle type EF | `km`, `passenger-km` | Passenger car: 0.18552, Bus: 0.04140, Subway: 0.05808 kg $\text{CO}_2\text{e}/\text{km}$ | EPA Emission Factors Hub 2025 |
| **Cat 8: Upstream Leased Assets** | Leased real estate and vehicles | Spend-based or Floor Area / Vehicle km | `USD`, `km` | Leased buildings: 0.246 kg/USD, Passenger car: 0.18552 kg/km | EPA Supply Chain GHG Factors |
| **Cat 9: Downstream Transportation** | Marine tanker & pipeline transport of sold crude/gas | Mass-Distance ($\text{tonne} \cdot \text{km}$) × Mode | `ton-km` | Marine tanker: 0.05370, Pipeline: 0.01451 kg $\text{CO}_2\text{e}/\text{t-km}$ | EPA Emission Factors Hub 2025 |
| **Cat 10: Processing of Sold Products** | Third-party refining of crude oil or fractionation of gas | Product Volume × Refining / Processing Energy Intensity | `bbl`, `mcf`, `MMBtu` | Natural gas processing: 54.18 kg $\text{CO}_2\text{e}/\text{MMBtu}$ | API Compendium Table 4-5 |
| **Cat 11: Use of Sold Products** | Direct end-user combustion of crude oil, natural gas, NGLs | Sold Fuel Volume × Heating Value × Carbon Oxidation EF | `bbl`, `mcf`, `mscf`, `gal`, `MMBtu` | Crude: 433.44 kg/bbl; Gas: 54.18 kg/MMBtu ($= 55.26\ \text{kg}/\text{mcf}$ @ 1.02 MMBtu/mcf); Propane: 5.74 kg/gal | API Compendium Table 4-3/4-6 |
| **Cat 12: End-of-Life of Sold Products** | Disposal of finished lubricant and plastic derivatives | Sold volume × waste disposal factor | `kg`, `tonne` | Landfill: 0.6393, Incineration: 0.4740 kg $\text{CO}_2\text{e}/\text{kg}$ | EPA Emission Factors Hub 2025 |
| **Cat 13: Downstream Leased Assets** | Sublet facilities | Spend-based | `USD` | Leased buildings: 0.246 kg/USD | EPA Supply Chain GHG Factors |
| **Cat 14: Franchises** | Franchise fuel retail operations | Spend-based | `USD` | Commercial retail services | EPA Supply Chain GHG Factors |
| **Cat 15: Investments** | Financed emissions in joint ventures and midstream infrastructure | GHG Protocol Scope 3 Cat 15 / PCAF equity share of investee emissions | `USD`, `tCO2e` | Proportional share of asset inventory emissions | PCAF Global GHG Standard |

---

## 4. Global Warming Potentials (GWP) Matrix

The system provides complete dynamic GWP configuration across all three IPCC Assessment Reports and both 100-year and 20-year horizons:

| IPCC Standard | Time Horizon | $\text{CO}_2$ | $\text{CH}_4$ (Methane) | $\text{N}_2\text{O}$ (Nitrous Oxide) | Citation & Basis |
|---|---|---|---|---|---|
| **IPCC AR4 (2007)** | 100-Year | 1.0 | **25.0** | **298.0** | IPCC AR4 Working Group I, Chapter 2 |
| **IPCC AR4 (2007)** | 20-Year | 1.0 | **72.0** | **289.0** | IPCC AR4 Working Group I, Chapter 2 |
| **IPCC AR5 (2013) [Default]** | 100-Year | 1.0 | **28.0** | **265.0** | IPCC AR5 WG1 Table 8.7 (Without climate-carbon feedback) |
| **IPCC AR5 (2013)** | 20-Year | 1.0 | **84.0** | **264.0** | IPCC AR5 WG1 Table 8.7 |
| **IPCC AR6 (2021)** | 100-Year | 1.0 | **29.8** | **273.0** | IPCC AR6 WG1 Table 7.15 (Fossil methane for oil & gas) |
| **IPCC AR6 (2021)** | 20-Year | 1.0 | **82.5** | **273.0** | IPCC AR6 WG1 Table 7.15 (Fossil methane for oil & gas) |

---

## 5. Physical Unit Dimensions and Standard Conversions

### 5.1 Canonical Energy & BOE Constants
- **Natural Gas Gross Heating Value (HHV):** $1,020\ \text{Btu/scf} = 1.020\ \text{MMBtu/mscf}$
- **Barrel of Oil Equivalent (BOE) Energy Basis:** $5.80\ \text{MMBtu/BOE}$
- **Natural Gas to BOE Conversion Constant:**
  $$\text{BOE per mscf} = \frac{1.020\ \text{MMBtu/mscf}}{5.80\ \text{MMBtu/BOE}} = 0.17586206896551725\ \text{BOE/mscf}$$
  $$\text{scf per BOE} = \frac{5,800,000\ \text{Btu/BOE}}{1,020\ \text{Btu/scf}} = 5,686.2745098\ \text{scf/BOE}$$
- **Energy Conversion:** $1\ \text{BOE} = 6.119323945\ \text{GJ} = 6,119.323945\ \text{MJ}$
- **Crude Oil Volume-to-Mass:** $1\ \text{m}^3 = 6.28981\ \text{bbl}$; $1\ \text{tonne crude} = 7.33\ \text{bbl}$

---

## 6. Uncertainty Propagation Methodology

Compliant with **ISO 14064-1:2018 §7.5**, **IPCC 2006 GL Vol. 1 §3.3 (Approach 1)**, and **ISO/IEC Guide 98-3 (GUM)**:

1. **Source Level (Product of Independent Variables):**
   $$E = A \times EF$$
   $$u_{\text{rel}}(E) = \sqrt{u_{\text{rel}}(A)^2 + u_{\text{rel}}(EF)^2}$$
2. **Confidence Interval (95% Two-Sided CI):**
   $$U_{95\%} = k \times u_{\text{rel}}(E) \quad \text{where } k = 2.0\ (\text{coverage factor for Gaussian distribution})$$
3. **Category and Inventory Aggregation (Sum of Independent Sources):**
   $$E_{\text{total}} = \sum_{i=1}^n E_i$$
   $$U_{\text{total}} = \frac{\sqrt{\sum_{i=1}^n (U_{95\%, i} \times E_i)^2}}{E_{\text{total}}}$$
