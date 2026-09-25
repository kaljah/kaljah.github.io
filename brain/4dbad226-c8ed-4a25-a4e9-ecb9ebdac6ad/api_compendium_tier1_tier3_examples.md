# API Compendium 2021 — Tier 1 & Tier 3 Calculation Examples by Process Type

**Sources:**
- [`emission_factors_api2021.py`](file:///c:/Users/samsung/Desktop/H2/new/server/emission_factors_api2021.py) — Sections 5, 6 & 7 emission factor catalog
- [`calculation-specification.md`](file:///c:/Users/samsung/Desktop/H2/docs/calculation-specification.md) — Formal calculation specification
- [`calculation-inventory.md`](file:///c:/Users/samsung/Desktop/H2/docs/validation/calculation-inventory.md) — Full process inventory
- [`dataset_generator.py`](file:///c:/Users/samsung/Desktop/H2/validation/golden_dataset/dataset_generator.py) — Golden dataset worked examples
- [`api_compendium_exhibits.md`](file:///c:/Users/samsung/Desktop/H2/brain/cb1e2599-6eda-488f-8f5a-372c19ceca8f/api_compendium_exhibits.md) — Exhibit index

> [!NOTE]
> **Tier 1** = Default catalog emission factors (activity × EF). Activity uncertainty ±10 %, EF uncertainty ±5 %–60 %.
> **Tier 3** = Engineering / stoichiometric / direct measurement. Activity uncertainty ±2 %, EF uncertainty ±1 %–20 %.

---

## 1. Stationary Combustion (API §5.1, CALC-001 / CALC-002)

### Tier 1 — Fuel-Based (Default EF Catalog)
**Exhibit 4.2 / §5.1 Eq. 5-1**

**Formula:**
$$\text{Energy (MMBtu)} = Q_{fuel} \times \frac{\text{HHV}}{10^6}$$
$$\text{Emissions}_g \text{ (tonnes)} = \frac{\text{Energy (MMBtu)} \times \text{EF}_g}{1000}$$
$$\text{CO}_2\text{e} = \text{CO}_2 + (\text{CH}_4 \times 28) + (\text{N}_2\text{O} \times 265)$$

**Golden Dataset Example — GOLD-A01-COMB-NG-NORM:**

| Parameter | Value | Unit |
|---|---|---|
| Fuel | Natural Gas | — |
| Fuel Quantity | 100,000 | m³ |
| HHV | 1,020 | Btu/scf |
| CO₂ EF (Table 5-1) | 53.06 | kg CO₂/MMBtu |
| CH₄ EF | 0.001 | kg CH₄/MMBtu |
| N₂O EF | 0.0001 | kg N₂O/MMBtu |

**Intermediate:**
$$\text{Energy} = 100{,}000 \times 35.315 \times \frac{1{,}020}{10^6} = 3{,}602.1 \text{ MMBtu}$$

**Results:**
- CO₂ = 3,602.1 × 53.06 / 1,000 = **191.2 t**
- CH₄ = 3,602.1 × 0.001 / 1,000 = **0.003602 t**
- N₂O = 3,602.1 × 0.0001 / 1,000 = **0.000360 t**
- Total CO₂e ≈ **191.3 tCO₂e**

**Other Tier 1 fuel factors from the catalog (all kg/MMBtu):**

| Fuel | CO₂ EF | CH₄ EF | N₂O EF | Source |
|---|---|---|---|---|
| Natural Gas | 53.06 | 0.001 | 0.0001 | Table 5-1 |
| Diesel (No. 2) | 73.96 | 0.003 | 0.0006 | Table 5-1 |
| Residual Fuel Oil | 75.10 | 0.003 | 0.0006 | Table 5-1 |
| Anthracite Coal | 103.69 | 0.011 | 0.0016 | §5 |
| Bituminous Coal | 93.26 | 0.011 | 0.0016 | §5 |
| Petroleum Coke | 102.41 | 0.003 | 0.0006 | §5 |
| Motor Gasoline | 70.22 | 0.003 | 0.0006 | §5 |
| Propane (Liquid) | 62.88 | 0.003 | 0.0006 | §5 |
| Refinery Fuel Gas | 57.78 | 0.0028 | 0.0001 | §5 |

---

### Tier 3 — Gas Chromatographic Carbon Balance (§5.1.2, CALC-002)
**Exhibits 4.4(a), 4.4(b)**

**Formula:**
$$\text{MW}_{mix} = \sum(x_i \cdot \text{MW}_i)$$
$$w_C = \frac{\sum(x_i \cdot n_{C,i} \cdot 12.011)}{\text{MW}_{mix}}$$
$$m_{fuel} = \frac{P \cdot V}{Z \cdot R \cdot T} \cdot \text{MW}_{mix}$$
$$\text{CO}_2 = \frac{m_{fuel} \cdot w_C \cdot \eta_c \cdot (44.01/12.011) + \text{CO}_{2,\text{native}}}{1000} \text{ (tonnes)}$$
$$\text{CH}_{4,\text{slip}} = \frac{m_{fuel} \cdot w_{CH_4} \cdot (1 - \eta_c)}{1000} \text{ (tonnes)}$$

**Inputs:**
- `volume_m3` — measured gas volume
- `gas_composition` — mole fractions x(C1)…x(C10), x(CO₂), x(N₂)
- `P` (kPa), `T` (°C), `Z` (compressibility factor)
- `η_c` = combustion efficiency (default **0.995**)

**Example (§5.1.2):**

| Component | Mole Fraction |
|---|---|
| C1 (methane) | 0.88 |
| C2 (ethane) | 0.05 |
| CO₂ (native) | 0.02 |
| N₂ | 0.05 |

$$\text{Moles C per Mole Fuel} = (1 \times 0.88) + (2 \times 0.05) = 0.98$$
$$\text{CO}_{2,\text{combusted}} = V_{std} \times 0.98 \times \eta_c \times 1.8610\ \text{kg/m}^3$$
$$\text{CO}_{2,\text{native}} = V_{std} \times 0.02 \times 1.8610\ \text{kg/m}^3$$

---

## 2. Flaring (API §5.2, CALC-003)

### Tier 1 — Default EF Factors (Elevated Flare)

| Flare Type | CO₂ EF | CH₄ EF | η_c (CO₂) | η_d (CH₄) | Source |
|---|---|---|---|---|---|
| Natural Gas – Elevated | 1.92 kg/m³ | 0.012 kg/m³ | 0.98 | 0.98 | §5.2, Eq. 5-3&4 |
| Natural Gas – Ground | 1.88 kg/m³ | 0.024 kg/m³ | 0.98 | 0.96 | §5.2 |
| Natural Gas – Enclosed | 1.94 kg/m³ | 0.006 kg/m³ | 0.98 | 0.99 | §5.2 |
| Associated Gas | 2.15 kg/m³ | 0.018 kg/m³ | 0.98 | 0.98 | §5.2 |
| Sour Gas | 2.30 kg/m³ | 0.015 kg/m³ | 0.98 | 0.98 | §5.2 |
| Refinery Gas | 2.10 kg/m³ | 0.025 kg/m³ | 0.98 | 0.95 | §5.2, Eq. 5-4 |

**Exhibit 5.1 / 5.2 Worked Example — GOLD-A02-FLARE-ELEV-NORM:**

| Parameter | Value |
|---|---|
| Gas Volume | 50,000 m³ |
| Flare Type | Elevated |
| C1 (methane) | 0.88 mol fr. |
| C2 (ethane) | 0.05 mol fr. |
| CO₂ (native) | 0.02 mol fr. |
| η_c | 0.984 |
| η_d | 0.980 |
| N₂O EF | 0.0001 kg/MMBtu |

### Tier 3 — Dual-Efficiency Stoichiometric Combustion (§5.2, Eqs. 5-3 & 5-4)

**Formulas:**
$$\text{CH}_{4,\text{unburnt}} = \frac{V_{std} \times x_{CH_4} \times (1 - \eta_d) \times \rho_{CH_4}}{1000} \text{ (tonnes)}$$
$$\text{CO}_{2,\text{total}} = \frac{V_{std} \times \left[\sum_{i=1}^{10}(i \cdot x_{Ci}) \cdot \eta_c + x_{CO_{2,\text{native}}}\right] \times \rho_{CO_2}}{1000} \text{ (tonnes)}$$
$$\text{N}_2\text{O} = \frac{\text{Flared}_{MMBtu} \times \text{EF}_{N_2O}}{1000} \text{ (tonnes)}$$

**Default efficiencies by flare type:**

| Flare Type | η_c (combustion) | η_d (destruction) |
|---|---|---|
| Elevated / Pipe | 0.984 | 0.980 |
| Enclosed Ground | 0.996 | 0.995 |
| Open Pit / Candle | 0.920 | 0.950 |

---

## 3. Vented / Blowdown (API §6.4, CALC-007)

### Tier 1 — Default Venting Factor (§6)

| Source | CO₂ EF | CH₄ EF | Unit | Source |
|---|---|---|---|---|
| Natural Gas (Venting/Blowdown) | 0.054 kg/m³ | 0.67 kg/m³ | kg/m³ | §6 |

### Tier 3 — Engineering Blowdown (§6.4, Eq. 6-4)

$$V_{total,std} = V_{physical} \times \frac{P_{vessel,abs}}{P_{std}} \times \frac{T_{std}}{T_{vessel,abs}} \times \frac{1}{Z} \times N_{events}$$
$$m_{gas} = \frac{V_{vessel} \times (P_1 - P_2)}{Z \cdot R \cdot T} \times \text{MW}_{gas}$$

**If routed to flare:** Apply Dual-Efficiency flaring partition (D-01).

---

## 4. Liquids Unloading (API §6.3/6.4, CALC-006)

### Tier 1 — Not applicable (process-specific calculation only)

### Tier 3 — Wellbore Geometric Expansion (§6.3, Eq. 6-3)

**Golden Dataset Example — GOLD-A03-UNLOAD-NORM:**

$$V_{event} = \frac{\pi}{4} D^2 \times H \times \frac{P_{tubing,abs}}{P_{std}} \times \frac{T_{std}}{T_{well,abs}}$$
$$V_{total,std} = V_{event} \times N_{events}$$
$$\text{CH}_4 \text{ (tonnes)} = \frac{V_{total,std} \times x_{CH_4} \times \rho_{CH_4}}{1000}$$

| Parameter | Value | Unit |
|---|---|---|
| Well Depth (H) | 5,000 | ft |
| Tubing Diameter (D) | 2.441 | in |
| Shut-in Pressure | 150 | psig |
| Events/yr | 12 | — |
| CH₄ content | 0.85 | mol fr. |

---

## 5. Storage Tanks — GOR Flash Gas (API §6.7/6.8, CALC-008)

### Tier 1 — GOR Method with Table Default EF

**Golden Dataset Example — GOLD-A04-TANK-FLASH-NORM:**

$$\text{Flash Gas Volume (scf)} = Q_{oil,bbl} \times \text{GOR (scf/bbl)}$$
$$\text{CH}_4 = \frac{\text{convert}(\text{Flash Gas} \times x_{CH_4}, \text{scf, m}^3) \times \rho_{CH_4}}{1000} \text{ (tonnes)}$$

| Parameter | Value | Unit |
|---|---|---|
| Oil Throughput | 10,000 | bbl |
| GOR | 50 | scf/bbl |
| CH₄ content | 0.80 | mol fr. |

**Tier 1 equipment EF catalog (§6, Table 6-4):**

| Tank Type | CH₄ EF | Unit |
|---|---|---|
| Crude – Small (≤10 bbl/d) | 0.18 | kg CH₄/bbl |
| Crude – Large (>10 bbl/d) | 0.193 | kg CH₄/bbl |
| Production Condensate – Small | 1.56 | kg CH₄/bbl |
| Production Condensate – Large | 1.16 | kg CH₄/bbl |
| Gas-Well Condensate – Small | 2.65 | kg CH₄/bbl |
| Gas-Well Condensate – Large | 2.05 | kg CH₄/bbl |

### Tier 3 — Vasquez-Beggs Empirical Flash Model (§6.8)

$$\text{Flash CH}_4 = \frac{\text{convert}(\text{Gas}_{scf} \cdot x_{CH_4}, \text{scf, m}^3) \times \rho_{CH_4}}{1000}$$

With Vasquez-Beggs GOR correlation for unknown GOR cases.

---

## 6. Pneumatic Devices (API §6.8/6.10, CALC-009)

### Tier 1 — Default Bleed Rate Factors (Table 6-8, Table 6-34)

| Device Type | Default EF | Unit | Segment | Source |
|---|---|---|---|---|
| High Bleed Controller (>6 scfh) | 8.304 t CH₄/yr | tonnes/controller/yr | Upstream | Table 6-34 |
| Low Bleed Controller (<6 scfh) | 0.0939 t CH₄/yr | tonnes/controller/yr | Upstream | Table 6-34 |
| Intermittent Vent (T&S) | 0.4 t CH₄/yr | tonnes/controller/yr | Midstream | Table 6-42 |
| Continuous Vent (T&S) | 3.5 t CH₄/yr | tonnes/controller/yr | Midstream | Table 6-42 |

**Platform defaults (§6.8):**
- High bleed: **37.3 scf/hr**
- Low bleed: **1.39 scf/hr**
- Intermittent: **13.5 scf/hr**

**Formula:**
$$\text{CH}_4 \text{ (tonnes)} = \frac{\text{Count} \times \text{Hours} \times \text{convert}(\text{Bleed}_{scf/hr}, \text{scf, m}^3) \times x_{CH_4} \times \rho_{CH_4}}{1000}$$

**Golden Dataset Example — GOLD-G01 (Tier 1, high-bleed):**

| Parameter | Value |
|---|---|
| Device count | 10 |
| Bleed rate | 15.0 scf/hr |
| Operating hours | 8,760 (default full-year) |
| CH₄ content | 0.85 mol fr. |

Expected result: **5.074 t CH₄**

### Tier 3 — Direct Measured Bleed Rate (Coriolis / LDAR)

**Golden Dataset Example — GOLD-A01 Tier 3 sub-case:**

| Parameter | Value |
|---|---|
| Device count | 5 (low-bleed) |
| Bleed rate | 2.1 scf/hr (Coriolis-measured) |
| Hours | 8,760 |

Expected result: **0.1428 t CH₄**

$$\text{CH}_4 = \frac{5 \times 8760 \times 0.0000595 \times 0.85 \times 0.6785}{1000} = 0.1428 \text{ t}$$

---

## 7. Fugitive Equipment Leaks (API §7.1/7.2, CALC-010 / CALC-011)

### Tier 1 — Equipment-Level Screening Factors (Tables 7-9, 7-10)

**Upstream Wellheads:**

| Equipment | CH₄ EF | Unit | Source |
|---|---|---|---|
| Wellhead – Heavy Crude (API <20°) | 6.63×10⁻⁷ | t CH₄/well/hr | Table 7-9 |
| Wellhead – Light Crude (API ≥20°) | 1.56×10⁻⁵ | t CH₄/well/hr | Table 7-9 |
| Wellhead – Gas | 1.80×10⁻⁵ | t CH₄/well/hr | Table 7-10 |

**Upstream Separators:**

| Equipment | CH₄ EF | Unit | Source |
|---|---|---|---|
| Separator – Heavy Crude | 6.79×10⁻⁷ | t CH₄/sep/hr | Table 7-9 |
| Separator – Light Crude | 4.10×10⁻⁵ | t CH₄/sep/hr | Table 7-9 |
| Separator – Gas Production | 4.42×10⁻⁵ | t CH₄/sep/hr | Table 7-10 |

**Upstream Compressors:**

| Equipment | CH₄ EF | Unit | Source |
|---|---|---|---|
| Small Reciprocating | 3.69×10⁻⁵ | t CH₄/comp/hr | Table 7-9 |
| Large Reciprocating | 1.31×10⁻² | t CH₄/comp/hr | Table 7-9 |
| Gas Production Small Recip | 2.12×10⁻⁴ | t CH₄/comp/hr | Table 7-10 |
| Gas Production Large Recip | 1.22×10⁻² | t CH₄/comp/hr | Table 7-10 |

**Midstream Gathering & Boosting (Table 7-29):**

| Equipment | CH₄ EF | Unit |
|---|---|---|
| AGRU | 6.83×10⁻⁵ | t CH₄/unit/hr |
| Compressor | 1.84×10⁻³ | t CH₄/unit/hr |
| Dehydrator | 5.69×10⁻⁵ | t CH₄/unit/hr |
| Separator | 1.05×10⁻⁵ | t CH₄/unit/hr |
| Tank | 6.4×10⁻⁴ | t CH₄/unit/hr |

**Midstream Component-Level (Table 7-30):**

| Component | CH₄ EF | Unit |
|---|---|---|
| Connector (non-compressor) | 9.79×10⁻⁷ | t CH₄/hr/source |
| Block Valve | 4.36×10⁻⁶ | t CH₄/hr/source |
| Control Valve | 1.11×10⁻⁵ | t CH₄/hr/source |
| Pressure Relief Valve | 1.39×10⁻⁷ | t CH₄/hr/source |
| Pressure Regulator | 1.87×10⁻⁶ | t CH₄/hr/source |
| Compressor Seal | 1.54×10⁻⁴ | t CH₄/hr/source |

**Midstream Gas Processing (Table 7-35):**

| Equipment | CH₄ EF | Unit |
|---|---|---|
| Reciprocating Compressor | 8.95×10⁻³ | t CH₄/comp/hr |
| Centrifugal Compressor | 1.70×10⁻² | t CH₄/comp/hr |

**Downstream LNG (Table 7-76):**

| Facility | CH₄ EF | Unit |
|---|---|---|
| LNG Storage Station | 4.39×10⁻⁴ | t CH₄/facility |
| LNG Import Terminal | 3.29×10⁻⁴ | t CH₄/facility |
| LNG Export Terminal | 1.26×10⁻³ | t CH₄/facility |

**Downstream Refinery (Table 7-80):**

| Facility | CH₄ EF | Unit |
|---|---|---|
| Fuel Gas System (50–99k bbl/d) | 3.75×10⁻⁴ | t CH₄/10³ bbl feedstock |
| Fuel Gas System (100–199k bbl/d) | 1.41×10⁻³ | t CH₄/10³ bbl feedstock |

**Offshore Production (Table 7-3):**

| Facility | CH₄ EF | Unit |
|---|---|---|
| Offshore Oil Production | 3.86×10⁻⁶ | t CH₄/bbl produced |
| Offshore Gas Production | 1.04×10⁻² | t CH₄/10⁶ scf produced |

**Formula:**
$$\text{CH}_4 \text{ (tonnes/yr)} = \frac{\sum_k(\text{Count}_k \times \text{EF}_k \times \text{Hours}) \times x_{CH_4}}{1000}$$

### Tier 3 — Screening Correlation Equations (§7.3.1.6)

$$\text{Emission Rate (kg/hr)} = A \times (\text{Screening Value, ppm})^B$$

**Correlation coefficients:**

| Service | A | B | Pegged at 10k ppm | Pegged at 100k ppm |
|---|---|---|---|---|
| Gas Valve | 2.29×10⁻⁶ | 0.746 | 0.064 kg/hr | 0.11 kg/hr |
| Light Liquid Valve | 6.41×10⁻⁶ | 0.797 | 0.074 kg/hr | 0.15 kg/hr |
| Light Liquid Pump | 5.03×10⁻⁵ | 0.610 | 0.16 kg/hr | 0.68 kg/hr |
| Connector | 1.53×10⁻⁶ | 0.735 | 0.028 kg/hr | 0.030 kg/hr |
| Flange | 4.61×10⁻⁶ | 0.703 | 0.085 kg/hr | 0.089 kg/hr |
| Open-Ended Line | 2.20×10⁻⁶ | 0.704 | 0.012 kg/hr | 0.014 kg/hr |
| Other | 1.36×10⁻⁵ | 0.589 | 0.073 kg/hr | 0.11 kg/hr |

**Compressor Seal Factors (Tier 3, §7.3):**

| Seal Type | EF |
|---|---|
| Centrifugal Wet | 15.0 kg/hr |
| Centrifugal Dry | 1.5 kg/hr |
| Reciprocating Packing | 1.2 kg/hr |

---

## 8. Acid Gas Removal / Amine Sweetening (API §6.5, CALC-013)

### Tier 1 — Table 6-5 Slip Fraction Default

$$\text{CO}_2 \text{ (tonnes)} = \frac{Q_{scf} \times (x_{CO_2,in} - x_{CO_2,out}) \times \rho_{CO_2} \times (1 - \eta_{capture})}{1000}$$
$$\text{CH}_{4,slip} \text{ (tonnes)} = \frac{Q_{scf} \times x_{CH_4,in} \times f_{slip} \times \rho_{CH_4} \times (1 - \eta_{abatement})}{1000}$$

- Default slip fraction `f_slip` = **0.1%** (API Table 6-5)

### Tier 3 — Stoichiometric Gas Balance with Known Composition

Mole-fraction-based mass balance accounting for actual treated gas analysis.

---

## 9. Glycol Dehydrators (API §6.6, CALC-014)

### Tier 1 — Throughput-Based Default Factor

**Golden Dataset Example — GOLD-P01-DEFAULT-DEHY-FACTOR:**

$$\text{CH}_4 \text{ (tonnes)} = Q_{MMscf} \times \text{EF}_{default}$$

| Parameter | Value | Unit |
|---|---|---|
| Throughput | 100 | MMscf |
| API Table 6-6 default EF | 0.266 | t CH₄/MMscf |

Expected: **26.6 t CH₄**

Also: Glycol Dehydrator (Uncontrolled) — **0.177 scf/MMscf** (§6.11, equipment-based)

### Tier 3 — Henry's Law Glycol Solubility (§6.6, GRI-GLYCalc)

**Golden Dataset Example — GOLD-Q01 Tier 3 sub-case:**

$$S_{CH_4} \text{ (scf/gal)} = 0.0032 \times P_{psia}^{0.96} \times \exp(-0.0022 \times (T_{^{\circ}F} - 60)) \times x_{CH_4}$$
$$V_{dissolved,CH_4} = \text{Pump Rate}_{gph} \times S_{CH_4} \times \text{Hours}$$

| Parameter | Value | Unit |
|---|---|---|
| Glycol pump rate | 15.0 | gph |
| Operating hours | 8,760 | hr/yr |
| CH₄ content | 0.85 | mol fr. |
| Contactor pressure | 800 | psia |
| Contactor temperature | 100 | °F |

**Partitioning:** 80% to flash tank separator, 20% to still column regenerator vent.

**Methodology comparison (GOLD-Q01):**
| Method | Throughput Input | Result |
|---|---|---|
| Tier 1 default | 50 MMscf | `res_q_t1` |
| Tier 3 Henry's Law | 15 gph pump, 8760 hr | `res_q_t3` |

---

## 10. Chemical Production (API §6, Table 6-167)

### Tier 1 — Default Process Factor

| Product | CO₂ EF | Unit | Uncertainty | Source |
|---|---|---|---|---|
| Acrylonitrile | 1.00 | t CO₂/t product | ±15% | Table 6-167 |
| Carbon Black | 2.63 | t CO₂/t product | ±15% | Table 6-167 |
| Ethylene | 0.77 | t CO₂/t product | ±10% | Table 6-167 |
| Ethylene Dichloride | 0.041 | t CO₂/t product | ±15% | Table 6-167 |
| Ethylene Oxide | 0.46 | t CO₂/t product | ±10% | Table 6-167 |
| Methanol | 0.67 | t CO₂/t product | ±10% | Table 6-167 |

$$\text{CO}_2 \text{ (tonnes)} = \text{Production (tonnes)} \times \text{EF (t CO}_2\text{/t product)}$$

### Tier 3 — Stoichiometric Carbon Mass Balance (CALC-015, §4.1 Eqs. 4-3, 4-4)

**Exhibit 6-42, 6-43, 6-44 (Hydrogen Plant):**

$$\text{CO}_2 = \frac{m_{feed,kg} \times w_C \times (44.01/12.011)}{1000} \times \eta_{conv} \times (1 - \eta_{CCUS})$$

For **Steam Methane Reforming (SMR):** CH₄ + 2H₂O → CO₂ + 4H₂

$$\text{Theoretical CO}_2 = \text{Feedstock Moles} \times \frac{\text{MW}_{CO_2}}{\text{MW}_{feed}} \times n_C \times \text{Conversion}$$

---

## 11. N₂O Production (API §6, pg. 407)

### Tier 1 — Default Process EF

| Process | N₂O EF | Unit | Uncertainty |
|---|---|---|---|
| Nitric Acid – With NSCR | 2.0 | kg N₂O/t HNO₃ | ±10% |
| Nitric Acid – Without NSCR | 9.0 | kg N₂O/t HNO₃ | ±20% |
| Adipic Acid – Thermal Abatement | 13.0 | kg N₂O/t product | ±10% |
| Adipic Acid – Catalytic Abatement | 53.0 | kg N₂O/t product | ±15% |
| Adipic Acid – Uncontrolled | 300.0 | kg N₂O/t product | ±30% |

### Tier 3 — Continuous Emissions Monitoring (CEMS)

Direct stack measurement of N₂O concentration × flow rate.

---

## 12. Asphalt Blowing (API §6, Table 6-52)

### Tier 1

| Parameter | Value | Unit |
|---|---|---|
| CH₄ EF | 0.022 | kg CH₄/ton asphalt |
| CO₂ EF | 10.43 | kg CO₂/ton asphalt |
| Uncertainty (CO₂, CH₄) | ±30% | — |

**Exhibit 6-45:**
$$\text{Emissions} = Q_{asphalt,tons} \times \text{EF}$$

---

## 13. Mud Degassing / Well Drilling (API §6.1/6.2, CALC-004)

### Tier 1 — Default Table 6-1 Rates

| Mud Type | Default Rate | Unit | Source |
|---|---|---|---|
| Water-Based | 28.3 | m³/day | Table 6-1 |
| Oil-Based (diesel) | 141.6 | m³/day | Table 6-1 |

$$\text{CH}_4 = \frac{\text{Drilling Days} \times \text{EF}_{mud} \times x_{CH_4} \times \rho_{CH_4}}{1000}$$

### Tier 3 — Measured Mud Volume

Direct measurement of mud volume degassed per m³ of mud:
- Water-based: **0.15 kg CH₄/m³ mud** (§6.2.1)
- Oil-based: **37.5 kg CH₄/bbl mud** (§6.2)

---

## 14. Well Completion Flowback (API §6.2, CALC-005)

### Tier 1 — API Table 6-2 Defaults

$$V_{vented,scf} = \text{Flowback Days} \times \text{Daily Flow Rate (default)}$$

**Exhibit 6-3:**
$$\text{Emissions partitioned if flared:}\ \eta_{flare} = 0.98$$
Reduced Emissions Completion (REC) captures **90–95%** of gas.

### Tier 3 — Measured Flowback Rate

Direct measurement of flowback gas volume and composition throughout the flowback period.

---

## 15. Scope 2 — Indirect Purchased Electricity (CALC-016)

### Tier 1 — Grid EF (Location-Based)

**Exhibit 8.1/8.2 — GOLD-A05-SCOPE2-GRID-NORM:**

$$\text{CO}_2\text{e (tonnes)} = \frac{Q_{kWh} \times \text{EF}_{grid}}{1000}$$

| Grid | EF (kg CO₂e/kWh) |
|---|---|
| Algerian National Grid | 0.522 |
| Algerian North | 0.510 |
| Algerian South (Isolated) | 0.650 |
| US Average | 0.385 |
| EU Average | 0.295 |
| UK National Grid | 0.233 |

**Example:** 500,000 kWh × 0.522 / 1,000 = **261 tCO₂e**

### Tier 3 — Market-Based (Supplier-Specific EF / RECs)

Use contractual EF from renewable energy certificate or power purchase agreement.

---

## 16. Scope 3 — Value Chain (CALC-019/020)

### Tier 1 — USEEIO Spend-Based EEIO (GOLD-A06 / GOLD-Q01)

**Exhibit §8 / GHG Protocol Scope 3:**

$$\text{CO}_2\text{e (tonnes)} = \frac{\text{Spend}_{USD} \times \text{EF}_{kg\ CO_2e/\$1000}}{1{,}000{,}000}$$

| NAICS Code | Sector | EF (kg CO₂e/\$1k) |
|---|---|---|
| 211 | Oil & Gas Extraction | 3,200.1 |

**Example:** \$500,000 spend → 500 × 3.2001 = **1,600.05 tCO₂e**

### Tier 3 — Physical Activity-Based

$$\text{CO}_2\text{e (tonnes)} = \frac{Q_{activity} \times \text{EF}_{physical}}{1000}$$

Uses supplier-specific EPD factors (kg CO₂e/unit) per GHG Protocol Scope 3 Cat. 1.

---

## Uncertainty Summary by Tier (IPCC GL Vol. 1 Table 3.1)

| Tier | Activity Uncertainty | EF Uncertainty |
|---|---|---|
| **Tier 1** (Default Catalog) | ±10% | ±5%–60% |
| **Tier 2** (Custom/Regional) | ±7% | ±3%–40% |
| **Tier 3** (CEMS/Engineering) | ±2% | ±1%–20% |
| Fugitive Process Baseline | ±20% | — |
| Vented Process Baseline | ±15% | — |

**Error Propagation (IPCC 2006 Eq. 3.1):**
$$u_E = \sqrt{u_{AD}^2 + u_{EF}^2}$$

**95% Confidence Interval (GUM, k=2.0):**
$$U_{95} = 2.0 \times u_E, \quad \text{Bounds} = E \pm U_{95}$$
