# Methodology Sensitivity Analysis & Impact Ranking

**Document**: `/audit/sensitivity.md`  
**Reference Dataset**: `/reference/comprehensive_golden_cases.xlsx`  
**Calculation Basis**: Clean-room standalone Python Decimal arithmetic (zero application code imports)  
**Auditor Guarantee**: All variations evaluated across candidate values derived from primary standards. Neutral presentation per Absolute Rule #4.

---

## 1. Golden Cases Baseline Inventory Totals

The reference inventory was computed strictly from `/reference/comprehensive_golden_cases.xlsx` using 50-digit Decimal arithmetic:

| Inventory Category | Baseline Emissions ($	ext{tCO}_2	ext{e}$) | Share of Total Inventory (%) | Methodology Standard |
| :--- | :---: | :---: | :--- |
| **Scope 1 (Combustion & Venting)** | **34065.78** | 22.92% | API Compendium 2021 §5.1, §5.2, §6.3 |
| **Scope 1 (Fugitives & Leaks)** | **8659.55** | 5.83% | API Compendium 2021 Table 7-11, Table 6-30 |
| **Scope 1 Total** | **42725.33** | **28.75%** | Direct Operational Emissions |
| **Scope 2 (Electricity & Steam - Location)** | **6750.17** | **4.54%** | GHG Protocol Scope 2 Guidance / MEM 2024 |
| **Scope 3 (Value Chain Categories 1, 4, 6, 11)**| **99146.04** | **66.71%** | USEEIO v1.3.0 / GLEC v3 / IPIECA |
| **Total Baseline Inventory** | **148621.54** | **100.00%** | Comprehensive Corporate Carbon Balance |

---

## 2. Detailed Sensitivity Evaluations per Item

### UNV-01: Gas Header Fugitive Rate
- **Applicable Scope**: Scope 1 (Baseline: 42725.33 $\text{tCO}_2\text{e}$)
- **Maximum Potential Delta**: **390.00 $\text{tCO}_2\text{e}$** (0.91% of Scope 1, 0.26% of Total Inventory)

| Candidate Formulation | Parameter Value | Resulting Emissions ($	ext{tCO}_2	ext{e}$) | $\Delta	ext{tCO}_2	ext{e}$ | Scope Impact (%) | Total Inventory Impact (%) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| Baseline (API Table 7-9: 2.04e-4 t/hr) | `2.04e-4 t/hr` | **500.37** | 0.00 | 0.00% | 0.00% |
| Candidate A (Claimed Survey: 0.045 kg/hr) | `0.0450 kg/hr` | **110.38** | -390.00 | -0.91% | -0.26% |
| Candidate B (EPA Subpart W: 0.11 kg/hr) | `0.1100 kg/hr` | **269.81** | -230.56 | -0.54% | -0.16% |

### UNV-02: Algerian Electricity Grid Factor
- **Applicable Scope**: Scope 2 (Baseline: 6750.17 $\text{tCO}_2\text{e}$)
- **Maximum Potential Delta**: **615.58 $\text{tCO}_2\text{e}$** (9.12% of Scope 2, 0.41% of Total Inventory)

| Candidate Formulation | Parameter Value | Resulting Emissions ($	ext{tCO}_2	ext{e}$) | $\Delta	ext{tCO}_2	ext{e}$ | Scope Impact (%) | Total Inventory Impact (%) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| Baseline (MEM 2024: 0.4979 kg/kWh) | `0.4979 kg/kWh` | **2489.42** | 0.00 | 0.00% | 0.00% |
| Candidate A (IEA 2023 Generation: 0.5180) | `0.5180 kg/kWh` | **2590.00** | +100.58 | +1.49% | +0.07% |
| Candidate B (IGES CDM Combined: 0.5420) | `0.5420 kg/kWh` | **2710.00** | +220.58 | +3.27% | +0.15% |
| Candidate C (Unverified Note: 0.4500) | `0.4500 kg/kWh` | **2250.00** | -239.42 | -3.55% | -0.16% |
| Candidate D (Ecoinvent LCA Market: 0.6210) | `0.6210 kg/kWh` | **3105.00** | +615.58 | +9.12% | +0.41% |

### UNV-03: Drilling Mud Degassing Rate
- **Applicable Scope**: Scope 1 (Baseline: 42725.33 $\text{tCO}_2\text{e}$)
- **Maximum Potential Delta**: **510.99 $\text{tCO}_2\text{e}$** (1.20% of Scope 1, 0.34% of Total Inventory)

| Candidate Formulation | Parameter Value | Resulting Emissions ($	ext{tCO}_2	ext{e}$) | $\Delta	ext{tCO}_2	ext{e}$ | Scope Impact (%) | Total Inventory Impact (%) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| Baseline (Table 6-2 Onshore Water: 0.0458 t/d) | `0.0458 t/day` | **109.00** | 0.00 | 0.00% | 0.00% |
| Candidate A (Table 6-2 Onshore Oil: 0.0103 t/d) | `0.0103 t/day` | **24.51** | -84.49 | -0.20% | -0.06% |
| Candidate B (Table 6-3 Tier 1: 0.0524 t/well) | `0.0524 t/well` | **1.47** | -107.54 | -0.25% | -0.07% |
| Candidate C (Table 6-2 Offshore Water: 0.2605 t/d) | `0.2605 t/day` | **619.99** | +510.99 | +1.20% | +0.34% |

### UNV-04: CBAM Hydrogen Benchmark Factor
- **Applicable Scope**: Scope 1 (Product) (Baseline: 42725.33 $\text{tCO}_2\text{e}$)
- **Maximum Potential Delta**: **42750.00 $\text{tCO}_2\text{e}$** (100.06% of Scope 1 (Product), 28.76% of Total Inventory)

| Candidate Formulation | Parameter Value | Resulting Emissions ($	ext{tCO}_2	ext{e}$) | $\Delta	ext{tCO}_2	ext{e}$ | Scope Impact (%) | Total Inventory Impact (%) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| Baseline (EU 2023/1773 Default: 10.40 tCO2e/t) | `10.40 t/t` | **52000.00** | 0.00 | 0.00% | 0.00% |
| Candidate A (Unverified Note: 1.85 tCO2e/t) | `1.85 t/t` | **9250.00** | -42750.00 | -100.06% | -28.76% |
| Candidate B (EU ETS SMR Benchmark: 6.84 tCO2/t) | `6.84 t/t` | **34200.00** | -17800.00 | -41.66% | -11.98% |
| Candidate C (RED II RFNBO Green: 3.38 tCO2e/t) | `3.38 t/t` | **16900.00** | -35100.00 | -82.15% | -23.62% |

### UNV-05: Flare Wind Decay vs Constant Efficiency
- **Applicable Scope**: Scope 1 (Baseline: 42725.33 $\text{tCO}_2\text{e}$)
- **Maximum Potential Delta**: **445.99 $\text{tCO}_2\text{e}$** (1.04% of Scope 1, 0.30% of Total Inventory)

| Candidate Formulation | Parameter Value | Resulting Emissions ($	ext{tCO}_2	ext{e}$) | $\Delta	ext{tCO}_2	ext{e}$ | Scope Impact (%) | Total Inventory Impact (%) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| Baseline (Compendium Constant: eta_d=0.98) | `eta=0.980` | **245.84** | 0.00 | 0.00% | 0.00% |
| Candidate A (Wind W=5 m/s: eta_d=0.9065) | `eta=0.9065` | **357.34** | +111.50 | +0.26% | +0.08% |
| Candidate B (Wind W=20 m/s: eta_d=0.6860) | `eta=0.6860` | **691.83** | +445.99 | +1.04% | +0.30% |
| Candidate C (Downstream Refinery: eta_d=0.995) | `eta=0.9950` | **223.09** | -22.75 | -0.05% | -0.02% |

### UNV-06/07: Steam Boiler Efficiency & Line Loss
- **Applicable Scope**: Scope 2 (Baseline: 6750.17 $\text{tCO}_2\text{e}$)
- **Maximum Potential Delta**: **29.44 $\text{tCO}_2\text{e}$** (0.44% of Scope 2, 0.02% of Total Inventory)

| Candidate Formulation | Parameter Value | Resulting Emissions ($	ext{tCO}_2	ext{e}$) | $\Delta	ext{tCO}_2	ext{e}$ | Scope Impact (%) | Total Inventory Impact (%) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| Baseline (Exhibit 8.3: 82% boiler, 10% loss -> net 72%) | `net=72%` | **147.22** | 0.00 | 0.00% | 0.00% |
| Candidate A (App Silent Default: 80% boiler, 0% loss -> net 80%) | `net=80%` | **132.50** | -14.72 | -0.22% | -0.01% |
| Candidate B (Aged System: 75% boiler, 15% loss -> net 60%) | `net=60%` | **176.66** | +29.44 | +0.44% | +0.02% |

### UNV-08: Methane GWP Standard & Horizon
- **Applicable Scope**: Scope 1 (Methane) (Baseline: 42725.33 $\text{tCO}_2\text{e}$)
- **Maximum Potential Delta**: **19256.16 $\text{tCO}_2\text{e}$** (45.07% of Scope 1 (Methane), 12.96% of Total Inventory)

| Candidate Formulation | Parameter Value | Resulting Emissions ($	ext{tCO}_2	ext{e}$) | $\Delta	ext{tCO}_2	ext{e}$ | Scope Impact (%) | Total Inventory Impact (%) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| Baseline (AR5 100-yr: CH4 GWP=28) | `GWP=28.0` | **9628.08** | 0.00 | 0.00% | 0.00% |
| Candidate A (AR4 100-yr: CH4 GWP=25) | `GWP=25.0` | **8596.50** | -1031.58 | -2.41% | -0.69% |
| Candidate B (AR6 100-yr: CH4 GWP=29.8) | `GWP=29.8` | **10247.03** | +618.95 | +1.45% | +0.42% |
| Candidate C (AR5 20-yr: CH4 GWP=84) | `GWP=84.0` | **28884.24** | +19256.16 | +45.07% | +12.96% |

---

## 3. Master Impact Rankings

### 3.1 Ranking by Absolute Tonnage Impact ($\Delta	ext{tCO}_2	ext{e}$)

| Rank | Item ID | Parameter / Methodology Area | Impacted Scope | Max $\Delta	ext{tCO}_2	ext{e}$ | Scope Impact (%) | Total Inventory Impact (%) | Core Sensitivity Driver |
| :---: | :---: | :--- | :--- | :---: | :---: | :---: | :--- |
| **#1** | **UNV-04** | CBAM Hydrogen Benchmark Factor | Scope 1 (Product) | **42750.00** | 100.06% | 28.76% | Discrepancy between candidate methodologies |
| **#2** | **UNV-08** | Methane GWP Standard & Horizon | Scope 1 (Methane) | **19256.16** | 45.07% | 12.96% | Discrepancy between candidate methodologies |
| **#3** | **UNV-02** | Algerian Electricity Grid Factor | Scope 2 | **615.58** | 9.12% | 0.41% | Discrepancy between candidate methodologies |
| **#4** | **UNV-03** | Drilling Mud Degassing Rate | Scope 1 | **510.99** | 1.20% | 0.34% | Discrepancy between candidate methodologies |
| **#5** | **UNV-05** | Flare Wind Decay vs Constant Efficiency | Scope 1 | **445.99** | 1.04% | 0.30% | Discrepancy between candidate methodologies |
| **#6** | **UNV-01** | Gas Header Fugitive Rate | Scope 1 | **390.00** | 0.91% | 0.26% | Discrepancy between candidate methodologies |
| **#7** | **UNV-06/07** | Steam Boiler Efficiency & Line Loss | Scope 2 | **29.44** | 0.44% | 0.02% | Discrepancy between candidate methodologies |

### 3.2 Ranking by Relative Inventory Impact (% of Total Inventory)

| Rank | Item ID | Parameter / Methodology Area | Max $\Delta	ext{tCO}_2	ext{e}$ | Scope Impact (%) | Total Inventory Impact (%) | Regulatory & Assurance Severity |
| :---: | :---: | :--- | :---: | :---: | :---: | :--- |
| **#1** | **UNV-04** | CBAM Hydrogen Benchmark Factor | 42750.00 | 100.06% | **28.76%** | CRITICAL (Material) |
| **#2** | **UNV-08** | Methane GWP Standard & Horizon | 19256.16 | 45.07% | **12.96%** | CRITICAL (Material) |
| **#3** | **UNV-02** | Algerian Electricity Grid Factor | 615.58 | 9.12% | **0.41%** | MODERATE (Localized) |
| **#4** | **UNV-03** | Drilling Mud Degassing Rate | 510.99 | 1.20% | **0.34%** | MODERATE (Localized) |
| **#5** | **UNV-05** | Flare Wind Decay vs Constant Efficiency | 445.99 | 1.04% | **0.30%** | MODERATE (Localized) |
| **#6** | **UNV-01** | Gas Header Fugitive Rate | 390.00 | 0.91% | **0.26%** | MODERATE (Localized) |
| **#7** | **UNV-06/07** | Steam Boiler Efficiency & Line Loss | 29.44 | 0.44% | **0.02%** | LOW (Operational) |

---

## 4. Auditor Sensitivity Insights

1. **CBAM Hydrogen Benchmark (UNV-04) & GWP Standard (UNV-08) are Dominant Sensitivity Drivers**:
   - If the unverified 1.85 factor were erroneously applied to a standard 5,000 t/yr hydrogen facility instead of the official EU default (10.40 tCO2e/t), emissions would be **underreported by 42,750 tCO2e (-82.2%)**, leading to severe customs penalties under EU Regulation 2023/956.
   - Shifting methane from AR5 100-yr (GWP=28) to 20-yr (GWP=84) increases reported methane emissions by **+19,256 tCO2e (+13.0% of the entire inventory)**, demonstrating why 20-yr GWPs must never be commingled with statutory filings.
2. **Flare Aerodynamic Decay (UNV-05) Instability**:
   - While constant efficiency provides predictable compliance, applying an uncalibrated wind-decay formula causes unburnt methane to increase by **+384 tCO2e (+156% on flaring)** in high-wind conditions.
3. **Silent Defaults in Steam (UNV-06/07)**:
   - Defaulting transmission loss to 0% creates an invisible **10% undercounting** of Scope 2 steam purchase emissions compared to the API Compendium Exhibit 8.3 example.
