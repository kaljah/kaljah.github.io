# Phase 2 — Calculation Engine Inventory

> Audit Date: 2026-09-20  
> Platform: GHG/MRV Platform  
> Methodology: API Compendium 2021 / GHG Protocol / IPCC AR4/AR5/AR6

---

## 1. Calculation Module Overview

All production calculations reside in `new/server/calculations/`:

| Module | Lines | Primary Classes | Standards |
|---|---|---|---|
| `combustion.py` | 565 | `CombustionCalculator`, `FlaringCalculator` | API §5.1, §5.2 |
| `vented.py` | 683 | `PneumaticDeviceCalculator`, `LiquidsUnloadingCalculator`, `MudDegassingCalculator`, `TankFlashingCalculator`, `CompletionFlowbackCalculator`, `BlowdownCalculator` | API §6 |
| `fugitive.py` | 160 | `ComponentFugitiveCalculator`, `EquipmentFugitiveCalculator`, `CompressorSealCalculator` | API §7 |
| `midstream.py` | 358 | `AGRCalculator`, `DehydratorCalculator` | API §6.5, §6.6 |
| `indirect.py` | 167 | `IndirectSteamCalculator`, `CogenAllocationCalculator` | API §8 |
| `stoichiometry.py` | 73 | `StoichiometricCalculator` | API §4.3 |
| `units.py` | 558 | Full conversion registry | API §4.2.1, ISO 13443 |
| `constants.py` | 63 | GWP tables, `get_active_gwp()` | IPCC AR4/AR5/AR6 |
| `uncertainty.py` | 432 | `propagate_uncertainty()`, `resolve_tier()` | IPCC 2006, ISO 14064-1, GUM |
| `dispatcher.py` | 1382 | `CalculationDispatcher` | All above |
| `anomaly.py` | 13123 bytes | Statistical anomaly detection | Z-score, IQR |
| `legacy_engine.py` | 905 | `GHGCalculator` (wrapper) | Backward-compat |

---

## 2. Calculation Inventory by Type

### 2.1 Stationary Combustion
**File**: `calculations/combustion.py` — `CombustionCalculator`  
**Standard**: API Compendium 2021 §5.1 (Tier 1 & 2)  
**Formula**:
```
Emissions_gas = Activity_gas × EF_gas / unit_conversion
CO2e = CO2 × GWP_CO2 + CH4 × GWP_CH4 + N2O × GWP_N2O
```

| Parameter | Description | Unit |
|---|---|---|
| fuel_quantity | Fuel consumed | m³, scf, mscf, gal, bbl, MMBtu, GJ, tonne, kg |
| hhv | Higher heating value | BTU/scf or BTU/gal |
| ef_co2, ef_ch4, ef_n2o | Emission factors | kg/MMBtu, kg/m³, kg/GJ, etc. |
| operating_temp | Actual gas temperature | °C, °F, K, R |
| operating_press | Actual gas pressure | psig, psia, bar, kPa |
| gwp_dict | GWP standard | AR4/AR5/AR6 |

**Thermodynamic normalization**: API §4.2.1 — `V_std = V_meas × (P_meas/P_std) × (T_std/T_meas) × (1/Z)`

**GWP values used** (AR5 default):  
- CO2: 1.0  
- CH4: 28.0  
- N2O: 265.0  

**Rounding**: No explicit rounding — floating point precision  
**Tests**: `test_combustion.py` (3), `test_tier_scope_kpi_numerical.py` (~15), `test_independent_differential.py` (~5), `test_property_invariants.py` (Hypothesis 50 examples each)

---

### 2.2 Mobile Combustion
**File**: `calculations/combustion.py` — `CombustionCalculator` (same class)  
**Standard**: API Compendium 2021 §5.1  
**Note**: Mobile combustion uses the same `CombustionCalculator` as stationary. Dispatcher maps `mobile_combustion` → `CombustionCalculator`. Differentiation is via process_type field only.

**Tests**: `test_all_process_types_matrix.py`, `test_tier_scope_kpi_numerical.py`

---

### 2.3 Flaring
**File**: `calculations/combustion.py` — `FlaringCalculator`  
**Standard**: API Compendium 2021 §5.2 (Dual-Efficiency Model)  
**Formula**:
```
CH4_undestroyed = Vol_std × CH4_fraction × (1 - η_d) × density_CH4
CO2_combusted = Vol_std × Σ(Cn_fraction × n) × η_c × density_CO2
CO2_native = Vol_std × CO2_fraction × density_CO2
N2O = Vol_scf × HHV / 1e6 × EF_n2o / 1000   [if energy-basis EF]
```

**Efficiency defaults by flare type**:
- Elevated/steam-assisted: η_c = 0.984, η_d = 0.98
- Enclosed/ground: η_c = 0.996, η_d = 0.995
- Pit/open: η_c = 0.920, η_d = 0.95

**Gas composition**: Supports full C1–C10 mole fractions  
**Standard gas density** (at 60°F, 14.696 psia): CH4 = 0.6785 kg/m³, CO2 = 1.861 kg/m³

**Tests**: `test_combustion.py` (2), `test_battery_gwp_horizons_regulatory.py`, `test_independent_differential.py` (differential)

---

### 2.4 Pneumatic Devices
**File**: `calculations/vented.py` — `PneumaticDeviceCalculator`  
**Standard**: API Compendium 2021 §6.2  
**Formula**: Count × EF(kg CH4/hr/device) × operating_hours × CH4_content → CO2e  
**Types supported**: High-bleed, Low-bleed, Intermittent  
**Tests**: `test_vented.py`, `test_battery_compressor_fugitives_equipment.py`

---

### 2.5 Liquids Unloading
**File**: `calculations/vented.py` — `LiquidsUnloadingCalculator`  
**Standard**: API Compendium 2021 §6.3  
**Formula**: Events × Tubing volume × CH4_content → CH4 → CO2e  
**Tests**: `test_vented.py`

---

### 2.6 Completions / Workover
**File**: `calculations/vented.py` — `CompletionFlowbackCalculator`  
**Standard**: API Compendium 2021 §6.1  
**Formula**: Volume × CH4_fraction → CH4 → CO2e (with flare partition)  
**Tests**: `test_independent_differential.py`, `test_all_process_types_matrix.py`

---

### 2.7 Drilling / Mud Degassing
**File**: `calculations/vented.py` — `MudDegassingCalculator`  
**Standard**: API Compendium 2021 §6.4  
**Formula**: Drill_rate × CH4_content → CH4 → CO2e  
**Tests**: `test_independent_differential.py`

---

### 2.8 Tank Flashing / Breathing / Working
**File**: `calculations/vented.py` — `TankFlashingCalculator`  
**Standard**: API Compendium 2021 §6.7  
**Formula**: Volume × CH4_fraction → CH4 → CO2e (with split vented/flared partition)  
**Tests**: `test_vented.py`

---

### 2.9 Blowdown / Venting
**File**: `calculations/vented.py` — `BlowdownCalculator`  
**Standard**: API Compendium 2021 §6.4  
**Formula**: Thermodynamic PV/nRT → gas mass → CH4 → CO2e  
**Tests**: `test_vented.py`, `test_independent_differential.py`

---

### 2.10 Component Fugitives
**File**: `calculations/fugitive.py` — `ComponentFugitiveCalculator`  
**Standard**: API Compendium 2021 §7.2 (Average Factor Method)  
**Formula**: Σ(Count_i × EF_i × CH4_scaling) × 8760 → CH4 tonnes/yr → CO2e  
**Tests**: `test_battery_compressor_fugitives_equipment.py`, `test_independent_differential.py`

---

### 2.11 Equipment Fugitives
**File**: `calculations/fugitive.py` — `EquipmentFugitiveCalculator`  
**Standard**: API Compendium 2021 §7.2.2  
**Formula**: Equipment_count × EF × CH4_content × hours → CH4 → CO2e  
**Tests**: `test_battery_compressor_fugitives_equipment.py`

---

### 2.12 Compressor Seal Fugitives
**File**: `calculations/fugitive.py` — `CompressorSealCalculator`  
**Standard**: API Compendium 2021 §7.3  
**Formula**: Compressor_count × EF × hours → CH4 → CO2e  
**Tests**: `test_battery_compressor_fugitives_equipment.py`

---

### 2.13 Acid Gas Removal (AGR)
**File**: `calculations/midstream.py` — `AGRCalculator`  
**Standard**: API Compendium 2021 §6.5, Table 6-5  
**Formula**:
```
CO2_vented = throughput_scf × (CO2_in - CO2_out) × density_CO2
CH4_slip = throughput_scf × CH4_in × CH4_slip_fraction × density_CH4
```
**Tests**: `test_battery_midstream_process_equipment.py`, `test_independent_differential.py`

---

### 2.14 Glycol Dehydrators
**File**: `calculations/midstream.py` — `DehydratorCalculator`  
**Standard**: API Compendium 2021 §6.6 / GRI-GLYCalc parametric model  
**Formula**: Solubility-based CH4 absorption + still column overhead emissions  
**Tests**: `test_battery_midstream_process_equipment.py`

---

### 2.15 Indirect Steam / Heat (Scope 1 or 2 boundary)
**File**: `calculations/indirect.py` — `IndirectSteamCalculator`  
**Standard**: API §8.1, GHG Protocol Scope 2  
**Formula**: `CO2 = (Energy_BTU / 1e6 × EF_CO2) / (η_boiler × (1 - η_loss))`  
**Tests**: `test_battery_stoichiometry_indirect_energy.py`

---

### 2.16 Cogeneration Allocation
**File**: `calculations/indirect.py` — `CogenAllocationCalculator`  
**Standard**: API §8.2  
**Tests**: `test_battery_stoichiometry_indirect_energy.py`

---

### 2.17 Stoichiometric Mass Balance
**File**: `calculations/stoichiometry.py` — `StoichiometricCalculator`  
**Standard**: API §4.3  
**Formula**: `CO2 = mass × carbon_content × (44.01 / 12.011) → tonnes`  
**Tests**: `test_battery_stoichiometry_indirect_energy.py`, `test_independent_differential.py`

---

### 2.18 Scope 2 Electricity
**File**: `routes/scope2.py`, `calculations/units.py`  
**Standard**: GHG Protocol Scope 2 (location-based and market-based)  
**Formula**: `CO2e = kWh × EF / 1000` (EF in kg CO2e/kWh, result in tonnes)  
**Tests**: `test_independent_differential.py`, `test_golden_dataset_validation.py`

---

### 2.19 Scope 3 Categories
**File**: `routes/scope3.py`, `calculations/units.py` — `compute_scope3_co2e()`  
**Standard**: GHG Protocol Scope 3 (15 categories)  
**Methods**: Spend-EEIO, physical activity, hybrid  
**Tests**: `test_independent_differential.py`, `test_golden_dataset_validation.py`

---

### 2.20 GWP Conversion
**File**: `calculations/constants.py`, `calculations/units.py` — `calculate_co2e()`  
**Standard**: IPCC AR4/AR5/AR6, 100-year and 20-year horizons  
**GWP Values**:

| Gas | AR4 | AR5 | AR6 |
|---|---|---|---|
| CO2 | 1.0 | 1.0 | 1.0 |
| CH4 | 25.0 | 28.0 | 27.9 |
| N2O | 298.0 | 265.0 | 273.0 |
| CH4 (20yr) | 72.0 | 82.5 | 82.5 |
| N2O (20yr) | 289.0 | 268.0 | 273.0 |

**Default**: AR5 (configurable via `SystemSetting` in DB)  
**Tests**: `test_battery_gwp_horizons_regulatory.py`, `test_gwp_dynamic.py`

---

### 2.21 Unit Conversions
**File**: `calculations/units.py`  
**Coverage**:
- Volume: m³, scf, mscf, mmscf, bbl, gal, liter
- Mass: kg, g, tonne, lb, short_ton, long_ton
- Energy: MJ, kJ, GJ, BTU, MMBtu, kWh, MWh, therm
- Temperature: °C, °F, K, R
- Pressure: psia, psig, bar, barg, kPa, kPag, MPa, atm, mbar, Pa
- Distance: m, km, mile, ft, yd, nmi
- Freight: tonne-km, ton-mile

**Tests**: `test_unit_conversions_exhaustive.py` (60+ parametrized tests with round-trip invertibility)

---

### 2.22 Uncertainty Propagation
**File**: `calculations/uncertainty.py`  
**Standard**: IPCC 2006 GL Vol.1 §3.3, ISO 14064-1:2018 §7.5, GUM §6.2  
**Method**: SRSS — Square Root of Sum of Squares  
**Formula**: `u_E = √(u_AD² + u_EF²)`, `U95 = 2.0 × u_E`  
**Tier activity uncertainty**: T1=10%, T2=7%, T3=2%  
**Tests**: `test_uncertainty.py`, `test_independent_differential.py`

---

### 2.23 Intensity Metrics
**File**: `routes/dashboard.py`, `calculations/units.py`  
**Metrics**:
- Carbon intensity: tCO2e / boe (barrel of oil equivalent)
- Methane intensity: % methane loss = CH4_emitted / gas_production × 100
- Flaring intensity: volume flared / production

**Tests**: `test_aggregation_reconciliation.py`

---

### 2.24 OGMP 2.0 Level Assessment
**File**: `services/ogmp.py`  
**Standard**: OGMP 2.0 Framework  
**Levels**: 1 (asset-level default) to 5 (source-level direct measurement)  
**Tests**: `test_independent_differential.py`, `test_satellite.py`

---

## 3. Missing Tests and Gaps

| Calculation | Gap |
|---|---|
| Stationary combustion — Tier 3 (CEMS) | No direct test for Tier 3 pathway |
| Flaring with all C1–C10 fractions | Partially tested; C6–C10 have minimal test coverage |
| AGR with thermal oxidizer control | Control efficiency tested; oxidizer-specific path not verified |
| Cogeneration allocation (heat-to-power ratio edge cases) | Not tested |
| Scope 3 Category 15 (investments) | Not present in golden dataset |
| GWP 20-year horizon end-to-end API test | Tested in unit tests; not tested via API |
| Negative emission factors (carbon removal) | Not tested |
| Custom factor unit mismatch detection | Partial test coverage |

---

## 4. Observations & Concerns

### OBS-CALC-01: AR6 N2O Value
- **Coded value**: AR6 N2O = 273.0 (in `constants.py`)
- **IPCC AR6 WGI Table 7.SM.7**: N2O 100-yr GWP = 273
- **Status**: ✅ CORRECT

### OBS-CALC-02: AR5 N2O Value
- **Coded value**: AR5 N2O = 265.0 (in `constants.py`)
- **IPCC AR5 WGI Table 8.7**: N2O 100-yr GWP = 265
- **Status**: ✅ CORRECT

### OBS-CALC-03: AR5 CH4 Value
- **Coded value**: AR5 CH4 = 28.0 (in `constants.py`)
- **IPCC AR5 WGI Table 8.7**: CH4 100-yr GWP (without climate-carbon feedbacks) = 28
- **Status**: ✅ CORRECT

### OBS-CALC-04: Standard Gas Density
- **Coded**: CH4 density = 0.6785 kg/m³ at 60°F, 14.696 psia
- **Reference** (API Compendium 2021): CH4 density = 0.6785 kg/m³
- **Status**: ✅ CORRECT

### OBS-CALC-05: Stoichiometric Ratio CO2/C
- **Coded**: 44.01 / 12.011 = 3.6641...
- **Chemically correct**: MW(CO2) = 44.01, MW(C) = 12.011
- **Status**: ✅ CORRECT

### OBS-CALC-06: Flaring Default Combustion Efficiency
- **Coded**: η_c = 0.984 (elevated), η_d = 0.98
- **API Compendium 2021 §5.2**: Combustion efficiency 98.4% is the API default
- **Status**: ✅ CORRECT

### OBS-CALC-07: Uncertainty Coverage Factor
- **Coded**: k = 2.0 (95% CI)
- **GUM §6.2**: k=2 for normal distribution approximation (95.45% coverage)
- **Status**: ✅ CORRECT (standard GUM value)

### CONCERN-CALC-01: Mobile vs. Stationary Combustion (REQUIRES HUMAN REVIEW)
The dispatcher maps both `mobile_combustion` and `stationary_combustion` to the same `CombustionCalculator`. While the calculation formula is identical, the GHG Protocol treats them differently for Scope classification (Scope 1 in both cases, but different category codes). The distinction should be maintained in reporting metadata, not just the process_type field.

### CONCERN-CALC-02: Flaring N2O Energy-Basis Default
Default `ef_n2o` for flaring is `0.0` if not provided, but `_split_vented_and_flared()` in `vented.py` uses `0.0001 kg/MMBtu` as its default. There is inconsistency between the two implementations' default N2O factors.

---

*Document generated: 2026-09-20 | Status: COMPLETE*
