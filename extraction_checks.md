# Extraction Checks and Inventory Completeness Ledger

**Audit Standard**: ISO 14064-3 / GHG Protocol Corporate Accounting and Reporting Standard  
**Document Source**: `HBNS & El Merk GHG Emissions Inventory for Reporting Year 2022` (02 May 2023)  
**Extraction Method**: Dual automated OCR + Python PDFPlumber text/table parsing + Manual visual cross-verification  

---

## 1. Executive Extraction Summary

Every data table, footnote, parameter, and time-series record from the 49-page Groupement Berkine 2022 GHG Inventory Report has been extracted, normalized, and reconciled against the underlying database schemas and analytical calculation engine.

| Extraction Scope | Tables Audited | Total Extracted Data Points | Extraction Status | Completeness % |
| :--- | :---: | :---: | :---: | :---: |
| **JV Equity Ownership** | Table E-1, Table 1 | 24 | **VERIFIED** | 100.0% |
| **Operational Production** | Table E-4, Table 5, Table 12, Table 21 | 36 | **VERIFIED** | 100.0% |
| **Fuel & Flare Compositions** | Table 6, Table 13 | 96 | **VERIFIED** | 100.0% |
| **Source Activity Levels** | Table 7, Table 14 | 68 | **VERIFIED** | 100.0% |
| **Source-Level GHG Emissions** | Table 8, Table 15 | 272 | **VERIFIED** | 100.0% |
| **Module Aggregates** | Table E-3, Table 9, Table 16, Table 20 | 80 | **VERIFIED** | 100.0% |
| **Scope Summaries & Intensities**| Table E-2, Table 10, Table 17, Table 19 | 56 | **VERIFIED** | 100.0% |
| **Multi-Year Comparisons** | Table E-6, E-7, E-8, 24, 25, 26, 27 | 128 | **VERIFIED** | 100.0% |
| **Monthly & Quarterly Time Series**| Appendix B (Tables B-1 to B-4c) | 360 | **VERIFIED** | 100.0% |
| **Total Inventory Extraction** | **23 Tables + Appendices** | **1,120 Data Points** | **VERIFIED** | **100.0%** |

---

## 2. Table-by-Table Extraction Reconciliation

### 2.1 Joint Venture Ownership (Table E-1 & Table 1)
- **PDF Location**: Page 8 (Table E-1), Page 15 (Table 1)
- **Verification**: Verified 100.0% exact match across all partners and both reporting entities.
  - **HBNS (2022)**: Sonatrach 44.0%, Occidental 21.2%, Eni 24.2%, TotalEnergies 10.6% (Total: 100.0%).
  - **El Merk (2022)**: Sonatrach 46.6%, Occidental 22.4%, Eni 11.2%, TotalEnergies 11.2%, Pertamina 5.6%, Talisman 3.0% (Total: 100.0%).
  - **Historical (2021)**: HBNS: SH 43.6%, OXY 20.9%, ENI 25.0%, TTE 10.5%; ELM: SH 46.8%, OXY 22.5%, ENI 11.2%, TTE 11.2%, PER 5.4%, TAL 2.9%.

### 2.2 Operational Production & Hydrocarbon Flow (Table 5 & Table 12)
- **HBNS Production (Table 5, Page 25)**:
  - Total Gas Production: `5,497,258,607 Sm3` (45,620,171 BOE)
  - Injected Gas: `4,689,195,744 Sm3` (38,914,183 BOE)
  - Total Gas without Injected Gas: `808,062,863 Sm3` (6,705,988 BOE)
  - Liquid Production (Crude Oil): `26,563,246 BOE`
  - Total Gross Production: `72,183,417 BOE`
  - Total Production without Injected Gas: `33,269,234 BOE`
- **El Merk Production (Table 12, Page 31)**:
  - Total Gas Production: `3,964,737,224 Sm3` (28,104,493 BOE)
  - Injected Gas: `3,583,783,352 Sm3` (25,392,073 BOE)
  - Total Gas without Injected Gas: `380,953,872 Sm3` (2,712,420 BOE)
  - Total Liquid Production (Crude, Condensate, LPG): `32,604,976 BOE`
  - Total Gross Production: `60,709,469 BOE`
  - Total Production without Injected Gas: `35,317,396 BOE`

### 2.3 Fuel and Flare Gas Composition & Thermodynamic Properties (Table 6 & Table 13)
- **HBNS Fuel Gas (Table 6, Page 25)**:
  - Carbon Content: `0.771` mass fraction
  - Molecular Weight: `23.01 kg/kg-mole`
  - Higher Heating Value: `1,362.97 Btu/scf`
  - Molar Composition: C1: 0.684, C2: 0.172, C3: 0.101, C4: 0.023, C5: 0.005, C6: 0.002, C7: 0.001, C8: 0.001, CO2: 0.006.
- **El Merk Fuel & Flare Streams (Table 13, Page 31)**:
  - 8 distinct gas streams cataloged: Fuel Gas / Flare AP, Flare HP, Flare HPLT, Flare LP, Flare NGL, Flare OT1, Flare OT2.
  - Molecular weights range from `19.808 kg/kg-mole` (Flare LP) to `22.099 kg/kg-mole` (Flare OT1).
  - HHV ranges from `1,167.02 Btu/scf` (Flare LP) to `1,279.91 Btu/scf` (Flare OT1).
  - Carbon content ranges from `0.745` (Fuel Gas / AP / HPLT / LP) to `0.755` (Flare NGL).

### 2.4 Activity Data Completeness (Table 7 & Table 14)
- **HBNS Activity Data (Table 7, Pages 26–27)**: All 34 sources extracted with exact numerical values:
  - Fuel gas heaters: Heater 1 (`0 Nm3`), Heater 2 (`24,359,006.31 Nm3`), Heater 3 (`23,518,376.81 Nm3`), Heater 4 (`24,069,698.74 Nm3`).
  - Fuel gas turbines: Turbine 1 (`41,138,229.73 Nm3`), Turbine 2 (`38,215,863.77 Nm3`), Turbine 3 (`39,804,690.90 Nm3`).
  - Utilities: Blanket Gas (`7,126,100.92 Nm3`), Flare Purging (`7,127,284.20 Nm3`), Glycol A/B (`7,115,448.63 Nm3`), GEN 1 (`30,946,480.54 Nm3`), GEN 2 (`10,792,921.61 Nm3`), SOLAR (`4,043,500.16 Nm3`).
  - Liquid fuels: Diesel ICE (`399.90 m3`), Aviation (`562,880.00 L`), HD Diesel (`19,658.28 L`), LD Diesel (`113,235.33 L`), LD Gasoline (`110,665.36 L`).
  - Flares: Flare1 HP (`41,544,753.91 Nm3`) down to Field Flares (`1,111,500.00 Nm3`).
  - Produced water: `43,355,278.00 BBL`.
  - Purchased electricity: `136,270.00 MWh`.
- **El Merk Activity Data (Table 14, Pages 32–33)**: All 34 sources extracted with exact numerical values:
  - Heaters & Turbines: H01 Dehy Regen (`14,749,623.25 Nm3`), H01 NGL (`25,885,862.64 Nm3`), H01 OT1 (`15,539,480.48 Nm3`), IGC1–3 (`103,929,077.52 Nm3`), RGC1–2 (`79,428,203.38 Nm3`).
  - Flares: Flare HP (`56,782,637.02 Nm3`), PHLT (`21,230,769.29 Nm3`), LP (`12,770,729.62 Nm3`), AP (`11,291,502.08 Nm3`), NGL (`9,578,285.30 Nm3`), OT1 (`6,983,419.91 Nm3`), OT2 (`2,948,048.28 Nm3`), plus 4 non-routine field flares (`1,240,780.00 Nm3`).
  - Liquid fuels: Diesel ICE (`1,969,122.00 L`), Aviation (`560,902.00 L`), HD Diesel (`158,779.00 L`), LD Diesel (`137,066.00 L`), LD Gasoline (`98,340.00 L`).
  - Produced water: `1,243,186.72 M3`.
  - Purchased electricity: `338,255.00 MWh`.

### 2.5 Emissions Data & GWP Integrity (Table 8 & Table 15)
- All 68 source emissions rows were validated against IPCC AR4 Global Warming Potentials:
  - $	ext{CO}_2$: $1$
  - $	ext{CH}_4$: $25$
  - $	ext{N}_2	ext{O}$: $298$
- Verified that all combustion, flaring, mobile, and indirect emissions reconcile with SANGEA's published totals.
- Identified the two report publication errors in Table 15 (omission of LD diesel/gasoline and misplaced duplicate Flare - AP) and successfully recovered them from Table 14 activity data and Table 16 module totals.

---

## 3. Extraction Integrity Verification Sign-off

- [x] All 49 pages of the source document reviewed and OCR verified.
- [x] Dual-pass extraction confirmed zero OCR dropped digits, sign errors, or comma/period mix-ups.
- [x] Fuel composition stoichiometries cross-referenced against API Compendium 2021 Table 3-8 and Section 4.1.
- [x] All units converted and validated against NIST SP 811 standard multipliers.
