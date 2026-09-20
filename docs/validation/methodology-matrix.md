# Authoritative Methodology Matrix & Regulatory Alignment

**Platform**: Greenhouse Gas (GHG) Accounting & MRV Engine  
**Document**: Authoritative Methodology Matrix  
**Status**: VERIFIED & RECONCILED  
**Governing Standards**:
1. **API Compendium (2021)**: Compendium of Greenhouse Gas Emissions Methodologies for the Natural Gas and Oil Industry (4th Edition, November 2021).
2. **GHG Protocol**: A Corporate Accounting and Reporting Standard (Revised Edition) + Scope 2 Guidance (2015) + Corporate Value Chain (Scope 3) Standard (2011).
3. **IPCC Guidelines (2006 / 2019 Refinement)**: Volume 1 (General Guidance and Reporting) and Volume 2 (Energy).
4. **OGMP 2.0**: Oil and Gas Methane Partnership 2.0 Reporting Framework (Guidance Document 2021).
5. **EPA Subpart W & Part 99**: Mandatory Greenhouse Gas Reporting (40 CFR Part 98 Subpart W) & Waste Emissions Charge (40 CFR Part 99 WEC).
6. **ISO 14064-1 / GUM (JCGM 100:2008)**: Specification with guidance at the organization level for quantification and reporting of greenhouse gas emissions; Evaluation of measurement data — Guide to the expression of uncertainty in measurement.

---

## 1. Master Regulatory Alignment Matrix

| Subsystem / Equation | Governing Methodology | Edition / Version | Canonical Citation | Emission Factor Catalog | GWP Horizon | Validation Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Gas Normalization** | API Compendium / ISO 13443 | 2021 | Section 4.2.1, Eq. 4-1 | Thermodynamic Constants ($Z, R$) | N/A | **PASS** |
| **Combustion (Tier 1/2)** | API Compendium / GHG Protocol | 2021 / 2004 | Section 5.1.1, Eq. 5-1 | API Tables 5-1 to 5-10 | AR5 (28/265) | **PASS** |
| **Combustion (Tier 3)** | API Compendium | 2021 | Section 5.1.2, Eq. 5-3 to 5-7 | Stoichiometric Carbon Balance | AR5 (28/265) | **PASS** |
| **Flaring (Dual Eff.)** | API Compendium (Remediated D-01) | 2021 | Section 5.2, Table 5-11 | Table 5-11 + Stoichiometric | AR5 (28/265) | **PASS** |
| **Mud Degassing** | API Compendium | 2021 | Section 6.1, Table 6-1 | API Table 6-1 | AR5 | **PASS** |
| **Completions** | API / EPA Subpart W | 2021 / 2024 | Section 6.2 / 40 CFR 98.233(g) | REC or Table 6-2 | AR5 | **PASS** |
| **Liquids Unloading** | API / EPA Subpart W | 2021 / 2024 | Section 6.3 / 40 CFR 98.233(c) | Wellbore Expansion Eq. 6-5 | AR5 | **PASS** |
| **Blowdown / Venting** | API Compendium | 2021 | Section 6.4, Eq. 6-8 | Polytropic / Ideal Gas Law | AR5 | **PASS** |
| **Tanks (Flash & Loss)**| API Compendium | 2021 | Section 6.7, Table 6-7 | Vasquez-Beggs / Table 6-7 | AR5 | **PASS** |
| **Pneumatics** | API / EPA Subpart W | 2021 / 2024 | Section 6.8, Table 6-8 | Table 6-8 Bleed Rates | AR5 | **PASS** |
| **Component Fugitives**| API Compendium | 2021 | Section 7.1, Tables 7-1 to 7-4 | API 2021 Component Factors | AR5 | **PASS** |
| **Equipment Fugitives**| API Compendium | 2021 | Section 7.2, Tables 7-5 to 7-10 | API 2021 Equipment Factors | AR5 | **PASS** |
| **Compressor Seals** | API / EPA Subpart W | 2021 / 2024 | Section 7.3, Table 7-11 | Table 7-11 Packing Factors | AR5 | **PASS** |
| **Acid Gas Removal** | API Compendium | 2021 | Section 6.5, Table 6-5 | Stripping Balance + 0.1% Slip | AR5 | **PASS** |
| **Glycol Dehydrators** | API / GRI-GLYCalc | 2021 | Section 6.6, Eq. 6-10 | Henry's Law Solubility | AR5 | **PASS** |
| **Chemical Synthesis** | IPCC IPPU Guidelines | 2006 | Volume 3, Chapter 3 | Molecular Weight Balance | AR5 | **PASS** |
| **Scope 2 Grid** | GHG Protocol Scope 2 | 2015 | Location-Based Standard | Regional Grid Average Factor | AR5 | **PASS** |
| **Scope 2 Steam (D-03)**| GHG Protocol Scope 2 | 2015 | Guidance Section 6.2 | Boiler Enthalpy Net Eff. | AR5 | **PASS** |
| **Scope 2 CHP Cogen** | GHG Protocol Scope 2 | 2015 | Guidance Section 6.3 | Efficiency / Exergetic Method | AR5 | **PASS** |
| **Scope 3 Spend EEIO**| GHG Protocol Scope 3 | 2011 | Corporate Value Chain Std | USEEIO v2.0 ($1,000 basis) | AR5 | **PASS** |
| **Scope 3 Physical** | GHG Protocol Scope 3 | 2011 | Category 1-15 Technical Guidance| Supplier Mass / Volume Factors| AR5 | **PASS** |
| **Uncertainty (SRSS)** | IPCC Guidelines | 2006 | Vol. 1 Ch. 3, Eq. 3.1 & 3.2 | Tier 1/2/3 Default Ranges | N/A | **PASS** |
| **Uncertainty (95% CI)**| GUM (JCGM 100:2008) | 2008 | Section 6.2 ($k=2$) | Gaussian Analytical Expansion | N/A | **PASS** |
| **Carbon Intensity** | IOGP / API Standards | 2021 | Sustainability Reporting Guidance| Thermal Equivalence (5.8 mscf)| AR5 | **PASS** |
| **Methane Intensity** | OGMP 2.0 Guidance | 2021 | Section 2.3 | Direct Methane Mass Ratio | N/A | **PASS** |
| **EPA Part 99 WEC** | EPA Clean Air Act §136 | 2024 | 40 CFR Part 99 | Statutory Fee Schedule | N/A | **PASS** |
| **OGMP Levels 1-5** | OGMP 2.0 Guidance | 2021 | Tiered Quantification Protocol | L1-L5 Decision Tree | N/A | **PASS** |
| **Top-Down Recon (D-02)**| OGMP 2.0 Guidance | 2021 | Annual Survey Reconciliation | Annual Average of Aerial Passes| N/A | **PASS** |

---

## 2. Detailed Methodological Analysis by Subsystem

### 2.1 Flaring & Stoichiometric Partitioning (Decision D-01)
- **Methodological Conflict Discovered & Resolved**:
  - Legacy implementations often multiplied flared volume by an unadjusted combustion emission factor or applied boiler factors ($kg/\text{MMBtu}$), causing up to 28x overestimation.
  - Furthermore, process flaring (completions, unloading, blowdown) must split the incoming gas into vented fraction $(1 - \eta_{\text{ctrl}})$ and flared fraction $\eta_{\text{ctrl}}$.
- **Authoritative Resolution (D-01)**:
  - Flared methane undergoes $98\%$ stoichiometric combustion to $\text{CO}_2$:
    $$\text{CO}_{2,\text{combusted}} = \text{CH}_{4,\text{flared}} \times 0.98 \times \left(\frac{44.01}{16.04}\right)$$
  - Native $\text{CO}_2$ passes through unreacted: $\text{CO}_{2,\text{native}} = \text{Native Stream } \text{CO}_2 \times \eta_{\text{ctrl}}$.
  - Unburnt methane emitted: $\text{CH}_{4,\text{unburnt}} = \text{CH}_{4,\text{flared}} \times 0.02$.
  - Nitrous oxide from flared energy: $\text{N}_2\text{O} = \frac{\text{Flared MMBtu} \times 0.0001\text{ kg/MMBtu}}{1000}$.

### 2.2 Indirect Steam Net Efficiency (Decision D-03)
- **Methodological Conflict Discovered & Resolved**:
  - Ambiguity existed on whether transmission losses should be subtracted from boiler efficiency ($\eta_{\text{boiler}} - L_{\text{trans}}$) or multiplied ($\eta_{\text{boiler}} \times (1 - L_{\text{trans}})$).
  - Subtraction allowed negative or zero net efficiency when losses were high, yielding infinite or inverted emissions.
- **Authoritative Resolution (D-03)**:
  - Enforced multiplicative net efficiency: $\eta_{\text{net}} = \eta_{\text{boiler}} \times (1 - L_{\text{trans}})$.
  - Any input resulting in $\eta_{\text{net}} \le 0$ is strictly rejected with HTTP 422 Unprocessable Entity.

### 2.3 Top-Down OGMP Survey Reconciliation (Decision D-02)
- **Methodological Conflict Discovered & Resolved**:
  - Multiple top-down surveys (e.g. drone, airplane, satellite) occurring in a single facility-year were previously summed, falsely multiplying annualized emission rates.
- **Authoritative Resolution (D-02)**:
  - Each survey represents an annualized snapshot ($t\text{CH}_4/\text{yr}$).
  - Multi-survey reconciliation computes the annual mean: $\bar{T} = \frac{1}{N}\sum_{i=1}^N T_i$.
  - If bottom-up emissions $B=0$ while $\bar{T}>0$, the variance is not reported as zero, but flagged with status `"Discrepancy Flagged"` and `variance_flag=True` (Decision L-6).

### 2.4 Scope 3 Spend vs Physical Activity
- **Methodological Conflict Discovered & Resolved**:
  - In spend-based EEIO calculations, factors are expressed per $\$1,000$ or $\$1k$ spend. A naive multiplication by activity amount without dividing by $\$1,000$ yields a $1,000\times$ calculation defect.
- **Authoritative Resolution**:
  - `compute_scope3_co2e` explicitly inspects the unit string for `$1000`, `$1,000`, `$1k`, or method `eeio` and scales by $1,000,000$ ($1,000$ for kg-to-tonne and $1,000$ for unit spend basis).

---

## 3. Global Standard Harmonization (GWP & Reference States)

### 3.1 Global Warming Potentials
The platform strictly decouples user presentation preferences from inventory calculation truth:
- **Calculation Authority**: Persisted records must strictly use the organization-level `SystemSetting` standard.
- **Standard Values Supported**:
  - **IPCC AR5 (Default)**: $\text{CH}_4 = 28$, $\text{N}_2\text{O} = 265$ (100-year); $\text{CH}_4 = 82.5$, $\text{N}_2\text{O} = 268$ (20-year).
  - **IPCC AR6**: $\text{CH}_4 = 27.9$, $\text{N}_2\text{O} = 273$ (100-year); $\text{CH}_4 = 81.2$, $\text{N}_2\text{O} = 273$ (20-year).
  - **IPCC AR4 (Historical)**: $\text{CH}_4 = 25$, $\text{N}_2\text{O} = 298$ (100-year); $\text{CH}_4 = 72$, $\text{N}_2\text{O} = 289$ (20-year).

### 3.2 Standard Gas Temperature and Pressure
- All volumetric gas equations are normalized to standard conditions:
  - Temperature: $T_{\text{std}} = 60.0^\circ\text{F} = 288.706\text{ K} = 15.556^\circ\text{C}$
  - Pressure: $P_{\text{std}} = 14.696\text{ psia} = 101.325\text{ kPa} = 1.01325\text{ bar}$
  - Molar Volume: $379.3\text{ scf/lb-mol} = 23.685\text{ m}^3/\text{kg-mol}$
  - Gas Densities at Std Conditions:
    - Methane ($\text{CH}_4$): $0.6785\text{ kg/m}^3 = 0.04235\text{ lb/scf}$
    - Carbon Dioxide ($\text{CO}_2$): $1.8610\text{ kg/m}^3 = 0.1162\text{ lb/scf}$
    - Nitrous Oxide ($\text{N}_2\text{O}$): $1.8600\text{ kg/m}^3 = 0.1161\text{ lb/scf}$
