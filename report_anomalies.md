# Forensic Audit: Discrepancies, Anomalies, and Typographical Errors in the 2022 GHG Inventory Report

**Document Audited**: `HBNS & El Merk GHG Emissions Inventory for Reporting Year 2022`  
**Operating Entity**: Groupement Berkine (Sonatrach / Occidental of Algeria, LLC)  
**Publication Date**: 02 May 2023 | **Version**: 01 (Proprietary & Confidential)  
**Standard Benchmarks**: API Compendium (2009/2021), ISO 14064-1:2018, IPCC AR4 (100-yr GWP)  

---

## Executive Summary of Report Integrity

A thorough mathematical, stoichiometric, and layout audit of the 49-page Groupement Berkine 2022 Greenhouse Gas Inventory Report revealed multiple significant clerical, mathematical, and data transposition errors. While the underlying calculation engine (SANGEA 4/5) executed sound stoichiometric and emission-factor calculations based on the API Compendium, multiple severe anomalies occurred during report compilation, table formatting, and document publishing.

The most severe finding is a structural corruption of **Table 15** (El Merk Annual GHG Emissions by Sources), where:
1. The **STP (Sewage Treatment Plant)** wastewater source was replaced by an erroneous duplicate copy of **Flare – AP** under "Miscellaneous".
2. Two major on-road mobile categories (**Light Duty Diesel** and **Light Duty Gasoline**) were completely omitted from the source rows.
3. The printed source rows sum to **1,031,885.64 t CO₂**, failing to reconcile with the printed table total of **1,032,493.53 t CO₂** by **-607.89 t CO₂**.

Furthermore, **Table E-9** and **Table 27** suffer from a complete header permutation where facility columns and multi-facility totals were swapped, creating extreme ambiguity regarding JV partner liability.

---

## Anomaly Classification Matrix

| Anomaly ID | Classification | Severity | Affected Report Section | Page(s) | Description Summary |
| :--- | :--- | :---: | :--- | :---: | :--- |
| **ANO-01** | Structural Corruption | **MAJOR** | Table 15 (El Merk Emissions) | 33–34 | Duplicate `Flare – AP` inserted under Misc; `STP` omitted. |
| **ANO-02** | Omission & Sum Discrepancy | **MAJOR** | Table 15 (El Merk Emissions) | 33–34 | LD Diesel & LD Gasoline omitted; table rows fail to sum to table Total (-607.89 t CO₂). |
| **ANO-03** | Data Transposition | **MAJOR** | Table E-9 & Table 27 | 12, 42 | Column headers swapped between Facility and Combined Totals. |
| **ANO-04** | Arithmetic Omission | **MEDIUM** | Table 8 (HBNS Emissions) | 27 | `Leak – Gas Production` CO₂e (27.12 t) omits CO₂ term (13.97 t). True sum: 41.07 t. |
| **ANO-05** | Math / Formula Error | **MEDIUM** | Table E-5 & Table 22 | 10, 25 | Total Methane Intensity (0.00015 t/BOE) calculated by summing facility rates instead of weighted average. |
| **ANO-06** | Activity Data Replication | **MEDIUM** | Table 7 & Table 14 | 26, 32 | HBNS gross gas volume (194,132.66 MMscf) duplicated into El Merk leak and venting activity. |
| **ANO-07** | Unit Inconsistency | **LOW** | Table 7 & Table 14 | 27, 33 | Produced water reported in BBL for HBNS, but M3 for El Merk, using identical volumetric factor. |
| **ANO-08** | Thermodynamic Truncation | **LOW** | Table 7 Footnote | 27 | Integer Kelvin ratio (273/288) used instead of standard (273.15/288.15). |
| **ANO-09** | Residual Cover Page Header | **LOW** | Cover Page | 1 | Header from 2021 Board Strategy Session left on 2022 Annual Report. |
| **ANO-10** | Typographical Glitches | **LOW** | Figure 8, Table 24, Table 7 | 23, 27, 40 | "VJ" instead of "JV", "CH4 I Intensity", and comma instead of decimal point (`136,270,00`). |

---

## Detailed Anomaly Dossiers

### ANO-01: Table 15 Structural Corruption — Duplicate Flare AP & Displaced STP
- **Affected Location**: Table 15 (*El Merk Annual GHG Emissions by Sources (tonne/year) – RY 2022*), Page 34.
- **Observed Defect**: Under the category **Miscellaneous**, the second row is listed as:
  $$	ext{Flare - AP}: \quad 	ext{CO}_2 = 26,670.68,\ 	ext{CH}_4 = 125.95,\ 	ext{N}_2	ext{O} = 0.42,\ 	ext{CO}_2	ext{e} = 29,944.46$$
  This is a verbatim duplicate of `Flare – AP` listed on Page 33 under the **Flare** category.
- **Omission**: In Table 14 (Activity Data, Page 32), the source `STP` is provided with activity `73,952.70 M3`. In Table 15, `STP` does not appear anywhere in the source breakdown.
- **Mathematical Impact**: If an auditor sums Table 15 as printed with the duplicate Flare - AP, the total is:
  $$\sum 	ext{CO}_2 = 1,058,556.32\ 	ext{tonnes} \quad (+26,062.79\ 	ext{t over reported Total})$$
- **Resolution & Reconciliation**: The printed table Total at the bottom of Page 34 is **1,032,493.53 t CO₂**, which excludes the duplicate row. Table 16 confirms Miscellaneous Total CO₂ is **9.50 t** ($	ext{Fire Suppressant } 1.22\ 	ext{t} + 	ext{STP } 8.28\ 	ext{t}$). The duplicate row was an unedited copy-paste error in the publication layout.

---

### ANO-02: Table 15 Omission of Light-Duty Mobile Sources & Internal Sum Discrepancy
- **Affected Location**: Table 15, Page 33, Category: *Mobile & Transportation*.
- **Observed Defect**: Table 14 provides activity data for three vehicle fuel streams:
  - Heavy Duty Diesel: $158,779.00\ 	ext{L}$
  - Light Duty Diesel: $137,066.00\ 	ext{L}$
  - Light Duty Gasoline: $98,340.00\ 	ext{L}$
  However, Table 15 lists only a single row labeled `On-Road Mobile`:
  $$	ext{CO}_2 = 425.84\ 	ext{t}, \quad 	ext{CH}_4 = 0.02\ 	ext{t}, \quad 	ext{N}_2	ext{O} = 0.01\ 	ext{t}, \quad 	ext{CO}_2	ext{e} = 430.27\ 	ext{t}$$
  Multiplying the Heavy Duty Diesel activity by the standard diesel EF ($158,779 	imes 0.00268196 = 425.84\ 	ext{t}$) confirms that this row contains **only** Heavy Duty Diesel. Light Duty Diesel ($367.61\ 	ext{t CO}_2$) and Light Duty Gasoline ($231.99\ 	ext{t CO}_2$) were completely dropped from Table 15.
- **Sum Discrepancy**: Summing all legitimate printed source rows in Table 15 yields:
  $$\sum 	ext{CO}_2 = 1,031,885.64\ 	ext{t} \quad 	ext{vs. Printed Total: } 1,032,493.53\ 	ext{t} \quad (\Delta = -607.89\ 	ext{t})$$
  $$\Delta = 367.61\ (	ext{LD Diesel}) + 231.99\ (	ext{LD Gasoline}) + 8.28\ (	ext{STP}) = 607.88\ 	ext{t CO}_2$$
- **Resolution**: SANGEA's underlying module aggregation in Table 16 correctly includes all mobile sources ($2,259.22\ 	ext{t CO}_2$) and STP ($9.50\ 	ext{t CO}_2$). The individual rows were inadvertently suppressed in Table 15.

---

### ANO-03: Table E-9 & Table 27 Scrambled / Transposed Column Headers
- **Affected Location**: Table E-9 (Page 12) and Table 27 (Page 42): *Total CO2e Emissions by JV Partner Equity Share (tonne/year)*.
- **Observed Defect**: The printed column headers are:
  `HBNS 2021 | ELM 2021 | Total 2021 | HBNS 2022 | ELM 2022 | Total 2022`
  However, examining the data values in each column reveals a complete header-data mismatch:
  - Column 1 (labeled *HBNS 2021*) sums to **2,118,398 t CO₂e** $ightarrow$ This is the **Combined 2021 Total**!
  - Column 2 (labeled *ELM 2021*) sums to **2,215,174 t CO₂e** $ightarrow$ This is the **Combined 2022 Total**!
  - Column 3 (labeled *Total 2021*) sums to **1,085,648 t CO₂e** $ightarrow$ This is **HBNS 2021**!
  - Column 4 (labeled *HBNS 2022*) sums to **1,032,750 t CO₂e** $ightarrow$ This is **El Merk 2021**!
  - Column 5 (labeled *ELM 2022*) sums to **1,061,969 t CO₂e** $ightarrow$ This is **HBNS 2022**!
  - Column 6 (labeled *Total 2022*) sums to **1,153,206 t CO₂e** $ightarrow$ This is **El Merk 2022**!
- **Proof of Error**:
  1. Figure E-3 (Page 13) and Figure 12 (Page 42) explicitly plot Sonatrach RY 2021 as $956,670\ 	ext{t}$ and RY 2022 as $1,004,660\ 	ext{t}$ (the exact numbers in Columns 1 & 2).
  2. Table 23 (Page 39) gives the correct uncorrupted breakdown for 2022: HBNS = $467,266.18\ 	ext{t}$, ELM = $537,393.92\ 	ext{t}$, Total = $1,004,660.11\ 	ext{t}$.

---

### ANO-04: Table 8 HBNS Leak – Gas Production CO₂e Arithmetic Omission
- **Affected Location**: Table 8 (Page 27), Category: *Equipment Leaks*.
- **Reported Values**:
  $$	ext{CO}_2 = 13.97\ 	ext{t}, \quad 	ext{CH}_4 = 1.084\ 	ext{t}, \quad 	ext{N}_2	ext{O} = 0.000\ 	ext{t}, \quad 	ext{CO}_2	ext{e} = 27.12\ 	ext{t}$$
- **Analysis**:
  Applying AR4 GWPs ($1.0 	imes 	ext{CO}_2 + 25.0 	imes 	ext{CH}_4$):
  $$13.97 	imes 1.0 + 1.084 	imes 25.0 = 13.97 + 27.10 = 41.07\ 	ext{t CO}_2	ext{e}$$
  The reported value ($27.12\ 	ext{t}$) reflects **only** the methane contribution ($1.084 	imes 25 pprox 27.10\ 	ext{t}$), entirely dropping the $13.97\ 	ext{t}$ of carbon dioxide.
- **Comparison**: For all other leak rows (`Leak – Oil Production` and `Leak – CPF Gas Processing`), the $	ext{CO}_2$ term was correctly added to $	ext{CO}_2	ext{e}$.

---

### ANO-05: Table E-5 & Table 22 Total Methane Intensity Arithmetic Error
- **Affected Location**: Table E-5 (Page 10) and Table 22 (Page 25): *Production & Intensity by Total Production*.
- **Reported Values**:
  - HBNS Methane Intensity: `0.000036 tCH4/BOE` ($2,629.75\ 	ext{t} / 72,183,417\ 	ext{BOE} = 0.0000364$)
  - El Merk Methane Intensity: `0.000076 tCH4/BOE` ($4,629.72\ 	ext{t} / 60,709,469\ 	ext{BOE} = 0.0000763$)
  - Total Methane Intensity (Printed): `0.00015 tCH4/BOE`
- **Analysis**:
  Total production across both facilities is $132,892,886\ 	ext{BOE}$, and total methane emissions are $7,259.47\ 	ext{t CH}_4$. The true weighted average intensity is:
  $$	ext{True Aggregate Intensity} = rac{7,259.47\ 	ext{t CH}_4}{132,892,886\ 	ext{BOE}} = 0.0000546\ 	ext{t CH}_4/	ext{BOE}$$
  The printed figure of `0.00015` appears to have been obtained by incorrectly adding the two facility intensities ($0.000036 + 0.000076 = 0.000112$) and erroneously rounding or applying an erroneous conversion factor.

---

### ANO-06: Activity Data Replication (Processed Gas Volume)
- **Affected Location**: Table 7 (Page 26) and Table 14 (Page 32).
- **Observation**: Both HBNS and El Merk report the exact identical processed gas volume of `194,132.66 MMscf` for:
  1. `Leak - CPF Gas Processing`
  2. `Non-Routine Venting – CPF equipment maintenance`
- **Analysis**: $194,132.66\ 	ext{MMscf}$ converts to $5,497,258,607\ 	ext{Sm}^3$, which is HBNS's exact gross annual gas production (Table 5). However, El Merk's actual gross gas production was $3,964,737,224\ 	ext{Sm}^3$ ($140,013\ 	ext{MMscf}$). El Merk appears to have copied HBNS's throughput into its SANGEA model for these two throughput-dependent sources.

---

### ANO-07: Unit Inconsistency in Produced Water Activity
- **Affected Location**: Table 7 (Page 27) vs. Table 14 (Page 33).
- **Observation**: HBNS reports Produced Water Volume as `43,355,278.00 BBL`, whereas El Merk reports `1,243,186.72 M3`.
- **Analysis**: Both facilities utilize an identical emission factor per barrel ($1.4603 	imes 10^{-6}\ 	ext{t CH}_4/	ext{bbl}$). To obtain El Merk's reported methane emissions ($11.42\ 	ext{t CH}_4$), the volume in $	ext{m}^3$ was internally multiplied by $6.28981\ 	ext{bbl/m}^3$ ($7,819,409\ 	ext{bbl} 	imes 1.4603 	imes 10^{-6} = 11.42\ 	ext{t}$), but the unit header was left as `M3` in Table 14.

---

### ANO-08: Thermodynamic Conversion Truncation (273K / 288K)
- **Affected Location**: Table 7 Footnote (Page 27).
- **Observation**: Footnote states: `* SANGEA gas volume unit in Nm3 is converted from source data in Sm3 by multiplying 273K/288K`.
- **Analysis**: Using integer Kelvin ($273 / 288 = 0.94791667$) introduces a 28.6 ppm difference compared to the standard thermodynamic ratio ($273.15 / 288.15 = 0.94794378$). For a multi-billion cubic meter inventory, this truncation shifts volume by ~150,000 m³.

---

### ANO-09 & ANO-10: Publication, Title, and Typographical Glitches
1. **Stray Cover Header (Page 1)**: `SEPTEMBER 2021 BOARD STRATEGY SESSION / 2021 BOARD STRATEGY SESSION 0` appears across the top margin of the May 2023 report.
2. **Figure 8 Title Typo (Page 23 / 36)**: Titled `Figure 8. El Merk CO2e Emissions by VJ Equity Share` ("VJ" instead of "JV").
3. **Table 24 Header Typo (Page 40)**: The last column is labeled `2022 NGSI CH4 I Intensity (wt.%)` containing an extraneous capital letter "I".
4. **Table 7 Punctuation Typo (Page 27)**: HBNS imported electricity is printed as `136,270,00` with a comma rather than a decimal point.
