# GHG Emissions & MRV Platform — Formal Calculation Specification

**Document Version:** 1.0.0  
**Status:** Canonical Engineering Specification  
**Governing Standards:**
- API Compendium of Greenhouse Gas Emissions Methodologies for the Oil and Natural Gas Industry (4th Edition, November 2021)
- The Greenhouse Gas Protocol: A Corporate Accounting and Reporting Standard (Revised Edition)
- GHG Protocol Scope 2 Guidance (2015) & Corporate Value Chain (Scope 3) Standard (2011)
- 2006 IPCC Guidelines for National Greenhouse Gas Inventories (Volume 1: General Guidance and Reporting; Volume 2: Energy)
- ISO 14064-1:2018 Specification with guidance at the organization level for quantification and reporting of greenhouse gas emissions and removals
- ISO/IEC Guide 98-3:2008 (GUM) Uncertainty of measurement — Part 3: Guide to the expression of uncertainty in measurement
- UNEP / OGMP 2.0 Reporting Framework (Levels 1 through 5 and Gold Standard Pathway)
- US EPA 40 CFR Part 98 (Subpart W) & Part 99 (Waste Emissions Charge / Inflation Reduction Act §136)

---

## 1. Thermodynamic Reference Conditions and Dimensional Standard

All standard volume calculations across the platform are normalized to the API Compendium §4.2.1 and ISO 13443 reference conditions:

| Parameter | Imperial Standard | Metric Standard | SI Absolute |
|---|---|---|---|
| **Standard Temperature ($T_{std}$)** | 60.0 °F | 15.556 °C | 288.706 K (519.67 °R) |
| **Standard Pressure ($P_{std}$)** | 14.696 psia | 1.01325 bar | 101.325 kPa (1.0 atm) |
| **Compressibility Factor ($Z_{std}$)** | 1.0 | 1.0 | 1.0 |

### Standard Thermodynamic Densities ($\rho_{std}$ at 60 °F, 14.696 psia):
- $\rho_{CH4} = 0.6785\ \text{kg/m}^3\ (0.042358\ \text{lb/ft}^3)$
- $\rho_{CO2} = 1.8610\ \text{kg/m}^3\ (0.116179\ \text{lb/ft}^3)$
- $\rho_{N2O} = 1.8600\ \text{kg/m}^3\ (0.116117\ \text{lb/ft}^3)$
- $\rho_{C2H6} = 1.2820\ \text{kg/m}^3\ (0.080033\ \text{lb/ft}^3)$
- $\rho_{C3H8} = 1.8820\ \text{kg/m}^3\ (0.117490\ \text{lb/ft}^3)$
- $\rho_{C4H10} = 2.5190\ \text{kg/m}^3\ (0.157256\ \text{lb/ft}^3)$

---

## 2. Core Unit Conversions Specification

### 2.1 Volume Conversions
Exact conversion factors to cubic meters ($\text{m}^3$):
- $1\ \text{scf} = 0.028316846592\ \text{m}^3$ (API Compendium 2021 §4.2)
- $1\ \text{mscf} = 1\ \text{mcf} = 1,000\ \text{scf} = 28.316846592\ \text{m}^3$
- $1\ \text{mmscf} = 1,000,000\ \text{scf} = 28,316.846592\ \text{m}^3$
- $1\ \text{bbl (barrel)} = 42\ \text{US gal} = 0.158987294928\ \text{m}^3$
- $1\ \text{US gal} = 0.003785411784\ \text{m}^3$
- $1\ \text{liter} = 0.001\ \text{m}^3$

### 2.2 Mass Conversions
Exact NIST Avoirdupois standards to kilograms ($\text{kg}$):
- $1\ \text{lb} = 0.45359237\ \text{kg}$
- $1\ \text{metric tonne (t)} = 1,000.0\ \text{kg}$
- $1\ \text{short ton (US ton)} = 2,000\ \text{lb} = 907.18474\ \text{kg}$
- $1\ \text{long ton (Imperial ton)} = 2,240\ \text{lb} = 1,016.0469088\ \text{kg}$
- $1\ \text{gram (g)} = 0.001\ \text{kg}$

### 2.3 Energy Conversions
Standard ISO 31-4 & NIST definitions to megajoules ($\text{MJ}$):
- $1\ \text{BTU} = 1.05505585262\ \text{kJ} = 0.00105505585262\ \text{MJ}$
- $1\ \text{MMBtu} = 1,000,000\ \text{BTU} = 1,055.05585262\ \text{MJ}$
- $1\ \text{kWh} = 3.6\ \text{MJ}$
- $1\ \text{MWh} = 3,600.0\ \text{MJ}$
- $1\ \text{therm} = 100,000\ \text{BTU} = 105.4804\ \text{MJ}$
- $1\ \text{GJ} = 1,000.0\ \text{MJ}$

---

## 3. Global Warming Potentials (GWP) and CO2e Normalization

All greenhouse gas masses are converted to Carbon Dioxide Equivalent ($\text{tCO}_2\text{e}$) according to:

$$\text{CO}_2\text{e} = (\text{Mass}_{\text{CO}_2} \times \text{GWP}_{\text{CO}_2}) + (\text{Mass}_{\text{CH}_4} \times \text{GWP}_{\text{CH}_4}) + (\text{Mass}_{\text{N}_2\text{O}} \times \text{GWP}_{\text{N}_2\text{O}})$$

### Registry of Supported GWP Profiles:
1. **IPCC 5th Assessment Report (AR5 - 2013, WG1 Table 8.7) — Platform Default**:
   - 100-Year Horizon: $\text{CO}_2 = 1.0$, $\text{CH}_4 = 28.0$, $\text{N}_2\text{O} = 265.0$
   - 20-Year Horizon: $\text{CO}_2 = 1.0$, $\text{CH}_4 = 82.5$, $\text{N}_2\text{O} = 268.0$
2. **IPCC 6th Assessment Report (AR6 - 2021, WG1 Table 7.15)**:
   - 100-Year Horizon: $\text{CO}_2 = 1.0$, $\text{CH}_4 = 27.9$, $\text{N}_2\text{O} = 273.0$
   - 20-Year Horizon: $\text{CO}_2 = 1.0$, $\text{CH}_4 = 82.5$, $\text{N}_2\text{O} = 273.0$
3. **IPCC 4th Assessment Report (AR4 - 2007)**:
   - 100-Year Horizon: $\text{CO}_2 = 1.0$, $\text{CH}_4 = 25.0$, $\text{N}_2\text{O} = 298.0$
   - 20-Year Horizon: $\text{CO}_2 = 1.0$, $\text{CH}_4 = 72.0$, $\text{N}_2\text{O} = 289.0$

---

## 4. Formal Specifications for Scope 1 Direct Emissions

### 4.1 Stationary Combustion (Tier 1 & Tier 2)
- **Calculation Name:** Fuel-Based Stationary Combustion (Tier 1/2 Catalog Multiplication)
- **Purpose:** Quantifies direct combustion emissions from stationary devices (boilers, turbines, engines, heaters) using activity data and fuel emission factors.
- **Applicable Methodology:** API Compendium 2021 §5.1, IPCC 2006 Vol. 2 Chapter 2.
- **Scope / Category:** Scope 1 / Stationary Combustion.
- **Formulas:**
  - If Factor is Energy-Based ($\text{kg/MMBtu}$):
    $$\text{Energy}_{\text{MMBtu}} = \text{Fuel}_{\text{Quantity}} \times \frac{\text{HHV}}{10^6}$$
    $$\text{Emissions}_{\text{gas}} (\text{tonnes}) = \frac{\text{Energy}_{\text{MMBtu}} \times \text{EF}_{\text{gas}}}{1000}$$
  - If Factor is Physical Unit-Based ($\text{kg/unit}$):
    $$\text{Emissions}_{\text{gas}} (\text{tonnes}) = \frac{\text{Fuel}_{\text{Quantity}} \times \text{EF}_{\text{gas}}}{1000}$$
- **Inputs:** `fuel_quantity` (float $> 0$), `fuel_unit` (str), `fuel_type` (str), `emission_factors` (dict with `co2`, `ch4`, `n2o`), `hhv` (float, required if factor is energy-based).
- **Valid Range:** `fuel_quantity` $\in (0, 10^{12})$, `combustion_efficiency` $\in [0.0, 1.0]$.
- **Invalid Range:** `fuel_quantity` $< 0$, `fuel_quantity` is `NaN` or `Infinity`.
- **Missing Data Handling:** If `hhv` is missing for gaseous fuel, default to $1,020\ \text{Btu/scf}$; for liquid fuel, default to $138,000\ \text{Btu/gal}$. Missing `n2o` evaluates to $0.0$.
- **Missing Factor Behavior:** Strict error raised if no factor is available; silent zero substitution prohibited.

### 4.2 Stationary Combustion (Tier 3 Engineering Carbon Mass Balance)
- **Calculation Name:** Tier 3 Gas Chromatographic Combustion Carbon Balance
- **Purpose:** High-accuracy carbon balance from fuel gas molar composition (C1–C10, CO2, N2).
- **Applicable Methodology:** API Compendium 2021 §5.1.2.
- **Scope / Category:** Scope 1 / Stationary Combustion (Tier 3).
- **Formulas:**
  $$\text{Moles Carbon per Mole Fuel} = \sum_{i=1}^{10} (i \times x_{Ci})$$
  $$V_{std} = \text{normalize\_gas\_volume\_to\_standard}(V_{meas}, T_{meas}, P_{meas}, Z)$$
  $$\text{CO}_{2,\text{combusted}} (\text{kg}) = V_{std} \times \text{Moles Carbon} \times \eta_c \times \rho_{\text{CO2}}$$
  $$\text{CO}_{2,\text{native}} (\text{kg}) = V_{std} \times x_{\text{CO2}} \times \rho_{\text{CO2}}$$
  $$\text{CO}_{2,\text{total}} (\text{tonnes}) = \frac{\text{CO}_{2,\text{combusted}} + \text{CO}_{2,\text{native}}}{1000}$$
  $$\text{CH}_{4,\text{slip}} (\text{tonnes}) = \frac{V_{std} \times x_{\text{C1}} \times (1 - \eta_c) \times \rho_{\text{CH4}}}{1000}$$
- **Inputs:** `fuel_quantity` ($V_{meas}$), `c1` (mole fraction $>0$), `c2`..`c10` (mole fractions), `co2_mol` (mole fraction), `combustion_efficiency` ($\eta_c$, default 0.995).
- **Precision Requirement:** IEEE 754 float64; gas fractions normalized to sum $\le 1.0$.

### 4.3 Flaring Dual-Efficiency Model
- **Calculation Name:** Flaring Dual-Efficiency Combustion & Destruction
- **Purpose:** Separates flaring into hydrocarbon destruction efficiency ($\eta_d$) for unburnt methane and combustion efficiency ($\eta_c$) for carbon dioxide.
- **Applicable Methodology:** API Compendium 2021 §5.2 (Equations 5-3, 5-4).
- **Scope / Category:** Scope 1 / Flaring.
- **Default Efficiencies by Flare Type:**
  - Elevated / Pipe Flare: $\eta_c = 0.984$, $\eta_d = 0.980$
  - Enclosed Ground Flare: $\eta_c = 0.996$, $\eta_d = 0.995$
  - Open Pit / Candle Flare: $\eta_c = 0.920$, $\eta_d = 0.950$
- **Formulas:**
  $$\text{CH}_{4,\text{unburnt}} (\text{tonnes}) = \frac{V_{std} \times x_{\text{CH4}} \times (1 - \eta_d) \times \rho_{\text{CH4}}}{1000}$$
  $$\text{CO}_{2,\text{total}} (\text{tonnes}) = \frac{V_{std} \times \left( \sum_{i=1}^{10} (i \cdot x_{Ci}) \cdot \eta_c + x_{\text{CO2,native}} \right) \times \rho_{\text{CO2}}}{1000}$$
  $$\text{N}_2\text{O} (\text{tonnes}) = \frac{\text{Flared}_{\text{MMBtu}} \times \text{EF}_{\text{N2O}}}{1000}$$

### 4.4 Vented Process Stoichiometric Flaring Partition (Decision D-01)
- **Calculation Name:** Vented & Flared Abatement Partition
- **Purpose:** Partitions gross episodic or process vented gas into an uncombusted vented stream ($1 - \eta_{ctrl}$) and an abated flared stream ($\eta_{ctrl}$).
- **Applicable Methodology:** API Compendium 2021 §5.2 & §6.1.
- **Scope / Category:** Scope 1 / Vented & Flared Operations.
- **Formulas:**
  $$\text{Vented CH}_4 = \text{Gross CH}_4 \times (1 - \eta_{ctrl})$$
  $$\text{Vented CO}_2 = \text{Gross CO}_2 \times (1 - \eta_{ctrl})$$
  $$\text{Flared Combusted CO}_2 = \left(\text{Gross CH}_4 \times \eta_{ctrl} \times 0.98 \times \frac{44.01}{16.04}\right) + (\text{Gross CO}_2 \times \eta_{ctrl})$$
  $$\text{Flared Unburnt CH}_4 = \text{Gross CH}_4 \times \eta_{ctrl} \times 0.02$$
  $$\text{Flared N}_2\text{O} = \frac{\text{Flared}_{\text{MMBtu}} \times \text{EF}_{\text{N2O}}}{1000}$$

### 4.5 Liquids Unloading
- **Calculation Name:** Wellbore Liquids Unloading (API Eq. 6-3)
- **Purpose:** Calculates gas vented during wellbore deliquification based on casing geometry and shut-in pressure.
- **Applicable Methodology:** API Compendium 2021 §6.4 (Equation 6-3).
- **Formulas:**
  $$V_{event} = \frac{\pi}{4} D^2 \times \text{Depth} \times \left(\frac{P_{tubing\_abs}}{P_{std}}\right) \times \left(\frac{T_{std}}{T_{well\_abs}}\right)$$
  $$V_{total\_std} = V_{event} \times \text{Events}$$
  $$\text{CH}_4 (\text{tonnes}) = \frac{V_{total\_std} \times x_{\text{CH4}} \times \rho_{\text{CH4}}}{1000}$$

### 4.6 Vessel and Pipeline Blowdown
- **Calculation Name:** Depressurization and Blowdown (API Eq. 6-4)
- **Purpose:** Gas released during scheduled or emergency depressurization of process vessels and pipe sections.
- **Applicable Methodology:** API Compendium 2021 §6.4 (Equation 6-4).
- **Formulas:**
  $$V_{total\_std} = V_{physical} \times \left(\frac{P_{vessel\_abs}}{P_{std}}\right) \times \left(\frac{T_{std}}{T_{vessel\_abs}}\right) \times \frac{1}{Z} \times \text{Events}$$

### 4.7 Storage Tank Flashing, Breathing, and Working Losses
- **Calculation Name:** Liquid Hydrocarbon Storage Tanks
- **Purpose:** Vapors released from crude oil/condensate flashing into atmospheric storage tanks and diurnal breathing/working losses.
- **Applicable Methodology:** API Compendium 2021 §6.8, EPA Subpart W §98.233(j).
- **Formulas:**
  - Flashing:
    $$\text{Gas}_{\text{scf}} = \text{Throughput}_{\text{bbl}} \times \text{GOR}_{\text{scf/bbl}}$$
    $$\text{CH}_4 (\text{tonnes}) = \frac{\text{convert}(\text{Gas}_{\text{scf}} \cdot x_{\text{CH4}}, \text{'scf'}, \text{'m3'}) \times \rho_{\text{CH4}}}{1000}$$
  - Working / Breathing:
    $$\text{CH}_4 (\text{tonnes}) = \frac{\text{Throughput} \times \text{EF}_{\text{tank}}}{1000}$$

### 4.8 Pneumatic Devices
- **Calculation Name:** Pneumatic Actuators and Controllers
- **Purpose:** Natural gas driven pneumatic instruments.
- **Applicable Methodology:** API Compendium 2021 §6.10, EPA Subpart W §98.233(a).
- **Formulas:**
  - Continuous Bleed:
    $$\text{CH}_4 (\text{tonnes}) = \frac{\text{Count} \times \text{Hours} \times \text{convert}(\text{Bleed}_{\text{scf/hr}}, \text{'scf'}, \text{'m3'}) \times x_{\text{CH4}} \times \rho_{\text{CH4}}}{1000}$$
  - Intermittent Vent:
    $$\text{CH}_4 (\text{tonnes}) = \frac{\text{Count} \times \text{Actuations} \times \text{convert}(\text{Bleed}_{\text{scf/act}}, \text{'scf'}, \text{'m3'}) \times x_{\text{CH4}} \times \rho_{\text{CH4}}}{1000}$$

### 4.9 Fugitive Equipment Leaks
- **Calculation Name:** Component and Equipment Fugitives
- **Purpose:** Unintentional diffuse emissions from valves, flanges, connectors, pumps, and compressor seals.
- **Applicable Methodology:** API Compendium 2021 §7.2.
- **Formulas:**
  $$\text{CH}_{4,\text{annual}} (\text{tonnes}) = \frac{\sum (\text{Count}_i \times \text{EF}_i \times \text{Hours}) \times x_{\text{CH4}}}{1000}$$
  - Compressor Seal Factors: Centrifugal Wet: $15.0\ \text{kg/hr}$; Centrifugal Dry: $1.5\ \text{kg/hr}$; Reciprocating: $1.2\ \text{kg/hr}$.

### 4.10 Acid Gas Removal (AGR / Amine Sweetening)
- **Calculation Name:** Amine Sweetening Plant Emissions
- **Purpose:** Stripped acid gas CO2 and methane co-absorption slip.
- **Applicable Methodology:** API Compendium 2021 §6.5, Table 6-5.
- **Formulas:**
  $$\text{CO}_2 (\text{tonnes}) = \frac{\text{convert}(\text{Throughput}_{\text{scf}} \cdot (x_{\text{CO2,in}} - x_{\text{CO2,out}}), \text{'scf'}, \text{'m3'}) \times \rho_{\text{CO2}}}{1000} \times (1 - \eta_{ctrl})$$
  $$\text{CH}_{4,\text{slip}} (\text{tonnes}) = \frac{\text{convert}(\text{Throughput}_{\text{scf}} \cdot x_{\text{CH4,in}} \cdot \text{Slip}, \text{'scf'}, \text{'m3'}) \times \rho_{\text{CH4}}}{1000} \times (1 - \eta_{ctrl})$$

### 4.11 Glycol Dehydrator (TEG)
- **Calculation Name:** TEG Dehydration Unit Henry's Law Solubility
- **Purpose:** Dissolved methane off-gassing from glycol circulation.
- **Applicable Methodology:** API Compendium 2021 §6.6, GRI-GLYCalc.
- **Formulas:**
  $$S_{\text{CH4}} (\text{scf/gal}) = 0.0032 \times (P_{\text{psia}})^{0.96} \times \exp(-0.0022 \times (T_{^{\circ}\text{F}} - 60)) \times x_{\text{CH4}}$$
  $$\text{Total Dissolved CH}_4 (\text{scf}) = \text{Pump Rate}_{\text{gph}} \times S_{\text{CH4}} \times \text{Operating Hours}$$
  - Partitioning: 80% to Flash Tank separator, 20% to Still Column regenerator vent.

### 4.12 Stoichiometric Chemical Reactions
- **Calculation Name:** Stoichiometric Carbon Mass Balance
- **Purpose:** Chemical transformation processes (calcination, cracking, sulfur recovery).
- **Applicable Methodology:** API Compendium 2021 §4.1 (Equations 4-3, 4-4).
- **Formula:**
  $$\text{CO}_2 (\text{tonnes}) = \frac{\text{Mass}_{\text{kg}} \times \text{Carbon Content} \times \frac{44.01}{12.011}}{1000}$$

---

## 5. Formal Specifications for Scope 2 Indirect Emissions

### 5.1 Grid Purchased Electricity
- **Calculation Name:** Location-Based Grid Electricity
- **Applicable Methodology:** GHG Protocol Scope 2 Guidance (Location-Based Method).
- **Formula:**
  $$\text{CO}_2\text{e} (\text{tonnes}) = \frac{\text{Electricity}_{\text{kWh}} \times \text{EF}_{\text{grid}}}{1000}$$
- **Registry of Grid Factors ($\text{kg CO}_2\text{e/kWh}$):**
  - Algerian National Grid: $0.522$
  - Algerian Grid North: $0.510$
  - Algerian Grid South (Isolated): $0.650$
  - US Average: $0.385$
  - US WECC: $0.3132$
  - US ERCOT: $0.4345$
  - EU Average: $0.295$
  - UK National Grid: $0.233$

### 5.2 Indirect Purchased Steam / Heat
- **Calculation Name:** Net Efficiency Steam/Heat Accounting
- **Applicable Methodology:** API Compendium 2021 §8.1 (Equation 8-2).
- **Formula:**
  $$\text{Net Efficiency} = \text{Boiler Efficiency} \times (1 - \text{Transmission Loss})$$
  $$\text{CO}_2 (\text{tonnes}) = \frac{\text{Energy}_{\text{MMBtu}} \times \text{EF}_{\text{boiler}}}{1000 \times \text{Net Efficiency}}$$

### 5.3 Combined Heat and Power (CHP) Cogeneration Allocation
- **Calculation Name:** WRI/WBCSD CHP Efficiency Allocation
- **Applicable Methodology:** API Compendium 2021 §8.3 (Equation 8-5), GHG Protocol Allocation.
- **Formula:**
  $$\text{Denominator} = \frac{\text{Heat Output}}{0.80} + \frac{\text{Power Output}}{0.33}$$
  $$\text{Allocated Heat Emissions} = \frac{\frac{\text{Heat Output}}{0.80}}{\text{Denominator}} \times \text{Total Facility Emissions}$$

---

## 6. Formal Specifications for Scope 3 Value Chain Emissions

### 6.1 Spend-Based / EEIO Method
- **Calculation Name:** Environmentally-Extended Input-Output (USEEIO v1.3)
- **Applicable Methodology:** GHG Protocol Scope 3 Category 1.
- **Formula:**
  $$\text{CO}_2\text{e} (\text{tonnes}) = \frac{\text{Spend}_{\text{USD}} \times \text{EF}_{\text{kg CO2e/\$1,000}}}{1,000,000}$$

### 6.2 Physical Activity-Based Method
- **Calculation Name:** Physical Goods & Freight Transport
- **Applicable Methodology:** GHG Protocol Scope 3 Categories 1 & 4.
- **Formulas:**
  - Mass-based factor ($\text{kg CO}_2\text{e/unit}$):
    $$\text{CO}_2\text{e} (\text{tonnes}) = \frac{\text{Activity} \times \text{EF}}{1000}$$
  - Tonne-based factor ($\text{tCO}_2\text{e/unit}$):
    $$\text{CO}_2\text{e} (\text{tonnes}) = \text{Activity} \times \text{EF}$$

---

## 7. Formal Specifications for Uncertainty Quantification

### 7.1 Tier Hierarchy and Standard Uncertainties (IPCC GL Vol. 1 Table 3.1)
- **Tier 1 (Default Catalog Factors):** Activity Uncertainty $\pm 10\%$, EF Uncertainty $\pm 5\%\text{--}60\%$.
- **Tier 2 (Custom / Regional Factors):** Activity Uncertainty $\pm 7\%$, EF Uncertainty $\pm 3\%\text{--}40\%$.
- **Tier 3 (Calibrated Meters / CEMS):** Activity Uncertainty $\pm 2\%$, EF Uncertainty $\pm 1\%\text{--}20\%$.
- **Fugitive Process Baseline:** Activity Uncertainty $\pm 20\%$.
- **Vented Process Baseline:** Activity Uncertainty $\pm 15\%$.

### 7.2 Standard Error Propagation Equations
- **Multiplicative Product Rule (IPCC 2006 Eq. 3.1):**
  $$u_E = \sqrt{u_{\text{AD}}^2 + u_{\text{EF}}^2}$$
- **Additive Independent Sum Rule (IPCC 2006 Eq. 3.2):**
  $$u_{\text{total}} = \frac{\sqrt{\sum_{i=1}^n (E_i \times u_i)^2}}{\left| \sum_{i=1}^n E_i \right|}$$
- **GUM 95% Confidence Interval Expansion ($k=2.0$):**
  $$U_{95} = 2.0 \times u_E$$
  $$\text{Lower Bound} = \max(0, E - U_{95})$$
  $$\text{Upper Bound} = E + U_{95}$$

---

## 8. Formal Specifications for Operational Intensities & Compliance

### 8.1 Production Normalization (Barrels of Oil Equivalent - BOE)
$$\text{BOE} = \text{Oil}_{\text{bbl}} + (\text{Gas}_{\text{mscf}} \times 0.178)$$

### 8.2 Operational Carbon & Methane Intensities
$$\text{Carbon Intensity} = \frac{\text{Total CO}_2\text{e} (\text{tonnes}) \times 1000}{\text{BOE}}\ (\text{kg CO}_2\text{e/BOE})$$
$$\text{Methane Loss Rate (\%)} = \frac{\frac{\text{CH}_4 (\text{tonnes}) \times 1000}{\rho_{\text{CH4}}}}{\text{Gross Gas Production} (\text{m}^3)} \times 100$$
$$\text{Flaring Rate (\%)} = \frac{\text{Flared Gas Volume} (\text{m}^3)}{\text{Gross Gas Production} (\text{m}^3)} \times 100$$

### 8.3 EPA Waste Emissions Charge (40 CFR Part 99 / IRA §136)
$$\text{Allowed CH}_4 (\text{tonnes}) = \frac{\text{Gross Gas} (\text{m}^3) \times \text{WEC Threshold} \times \rho_{\text{CH4}}}{1000}$$
$$\text{Excess CH}_4 (\text{tonnes}) = \max(0, \text{Total CH}_4 - \text{Allowed CH}_4)$$
$$\text{WEC Fee (USD)} = \text{Excess CH}_4 \times \text{Rate}_{\text{year}}$$
- Rates: 2024: \$900/tonne; 2025: \$1,200/tonne; 2026+: \$1,500/tonne.

### 8.4 OGMP 2.0 Level 1–5 Classification
- **Level 1:** Venture-level top-down estimate.
- **Level 2:** National / generic emission factors.
- **Level 3:** Equipment-level generic factors (API Table factors).
- **Level 4:** Source-level direct measurements or engineering calculation.
- **Level 5:** Reconciled site-level top-down survey with bottom-up inventory within $\le 20\%$ variance:
  $$\text{Variance (\%)} = \frac{\text{Top Down} - \text{Bottom Up}}{\text{Bottom Up}} \times 100$$
