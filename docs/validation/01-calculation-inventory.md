# Complete Calculation Inventory

**Platform**: Greenhouse Gas (GHG) Accounting & MRV Engine  
**Standard Compliance**: API Compendium (2021), GHG Protocol, IPCC (2006), ISO 14064-1, GUM, OGMP 2.0, EPA Subpart W / Part 99  
**Inventory Scope**: All mathematical, conversion, factor, and aggregation equations across Backend and Frontend

---

## Master Calculation Register

### Scope 1: Combustion & Energy Processes

#### CALC-001: Stationary Combustion — Tier 1 / Tier 2 Fuel-Based
- **Function/File**: `CombustionCalculator.calculate_tier1_2` in `new/server/calculations/combustion.py`
- **Description**: Computes greenhouse gas mass from fuel consumption and default or custom emission factors.
- **Equation**:  
  $$\text{Energy (MMBtu)} = \text{Fuel Quantity} \times \text{HHV}$$  
  $$\text{Emissions}_g (\text{tonnes}) = \frac{\text{Fuel Quantity} \times \text{EF}_g}{1000} \quad (\text{or } \frac{\text{Energy} \times \text{EF}_g}{1000})$$  
  $$\text{CO}_2\text{e} = \text{CO}_2 + (\text{CH}_4 \times \text{GWP}_{\text{CH}_4}) + (\text{N}_2\text{O} \times \text{GWP}_{\text{N}_2\text{O}})$$
- **Inputs**: `fuel_quantity`, `fuel_unit`, `fuel_type`, `emission_factors` (`co2`, `ch4`, `n2o`), `hhv`
- **Units**: Input: `scf`, `m3`, `gal`, `bbl`, `MMBtu`, `tonnes`. Output: Metric tonnes of $\text{CO}_2, \text{CH}_4, \text{N}_2\text{O}, \text{CO}_2\text{e}$.
- **Methodology**: API Compendium (2021) §5.1 / GHG Protocol Corporate Standard.
- **Emission Factor Source**: API Tables 5-1 to 5-10; CustomFactor table.
- **GWP Version**: Dynamically resolved (`AR5` default: 28 / 265; `AR6`: 27.9 / 273).
- **Assumptions**: Complete oxidation unless combustion efficiency specified; standard temperature & pressure ($60^\circ\text{F}, 14.696\text{ psia}$).
- **Precision / Rounding**: IEEE-754 double precision stored in DB; formatted to 3 decimal places in UI.
- **Applicable Scope / Category**: Scope 1 — Stationary Combustion.
- **Independently Validated**: YES (`IndependentCombustionModel.calculate_tier1_2`).
- **Existing Tests**: `test_diff_stationary_combustion_tier1`, `test_property_invariants.py`.
- **Missing Tests**: None.
- **Risk Level**: HIGH.
- **Frontend vs Backend Flag**: Authoritative on backend; frontend displays results via `EmissionResult.jsx`.

---

#### CALC-002: Stationary Combustion — Tier 3 Gas Chromatographic Carbon Balance
- **Function/File**: `CombustionCalculator.calculate_tier3` in `new/server/calculations/combustion.py`
- **Description**: Direct stoichiometric mass balance from fuel molar gas composition ($C_1$–$C_{10}$, $\text{CO}_2$, $\text{N}_2$).
- **Equation**:  
  $$\text{MW}_{\text{mix}} = \sum (x_i \cdot \text{MW}_i)$$  
  $$w_c = \frac{\sum (x_i \cdot n_{c,i} \cdot 12.011)}{\text{MW}_{\text{mix}}}$$  
  $$\text{Total Fuel Mass (kg)} = \frac{P \cdot V}{Z \cdot R \cdot T} \cdot \text{MW}_{\text{mix}}$$  
  $$\text{CO}_2 (\text{tonnes}) = \frac{\text{Total Fuel Mass} \cdot w_c \cdot \eta_{\text{comb}} \cdot (44.01 / 12.011) + \text{Native CO}_2}{1000}$$  
  $$\text{CH}_4 (\text{tonnes}) = \frac{\text{Total Fuel Mass} \cdot w_{\text{CH}_4} \cdot (1 - \eta_{\text{comb}})}{1000}$$
- **Inputs**: `volume_m3`, `gas_composition` ($x_{C1} \dots x_{C10}, x_{\text{CO}_2}, x_{\text{N}_2}$), $P, T, Z$, $\eta_{\text{comb}}$
- **Units**: Input: $\text{m}^3, \text{kPa}, ^\circ\text{C}$. Output: Metric tonnes.
- **Methodology**: API Compendium (2021) §5.1.2 Eq. 5-3 to 5-7.
- **Emission Factor Source**: Stoichiometric molecular weights (NIST / CRC).
- **GWP Version**: Dynamic (`AR5`/`AR6`).
- **Assumptions**: Ideal/Real gas equation of state with compressibility $Z$; 99.5% combustion efficiency default.
- **Precision / Rounding**: Full precision.
- **Applicable Scope / Category**: Scope 1 — Tier 3 Engineering Combustion.
- **Independently Validated**: YES (`IndependentCombustionModel.calculate_tier3`).
- **Existing Tests**: `test_diff_stationary_combustion_tier3`, `test_stoichiometry_dispatcher_gwp_propagation`.
- **Missing Tests**: None.
- **Risk Level**: CRITICAL.
- **Frontend vs Backend Flag**: Backend authoritative.

---

#### CALC-003: Flaring — API Compendium Dual-Efficiency Stoichiometric Combustion
- **Function/File**: `FlaringCalculator.calculate` in `new/server/calculations/combustion.py`
- **Description**: Dual-efficiency flaring model partitioning stream into combusted $\text{CO}_2$, unburnt $\text{CH}_4$ slip, and flared $\text{N}_2\text{O}$.
- **Equation**:  
  $$\text{Combustion Efficiency } \eta = \text{flare\_type lookup or user override } (98\% \text{ default})$$  
  $$\text{CO}_2 (\text{tonnes}) = \frac{\text{Flared Mass}_{\text{HC}} \cdot w_c \cdot \eta \cdot (44.01 / 12.011) + \text{Native CO}_2}{1000}$$  
  $$\text{CH}_4 (\text{tonnes}) = \frac{\text{Flared Mass}_{\text{CH}_4} \cdot (1 - \eta)}{1000}$$  
  $$\text{N}_2\text{O} (\text{tonnes}) = \frac{\text{Flared MMBtu} \times 0.0001\text{ kg/MMBtu}}{1000}$$
- **Inputs**: `volume`, `unit`, `composition`, `flare_type`, `combustion_efficiency`, `hhv`
- **Units**: Input: $\text{m}^3, \text{scf}, \text{MMBtu}$. Output: Metric tonnes.
- **Methodology**: API Compendium (2021) §5.2 Table 5-11, Remediated via Decision D-01.
- **Emission Factor Source**: Stoichiometric reaction + Table 5-11 default factors.
- **GWP Version**: Dynamic (`AR5`/`AR6`).
- **Assumptions**: Steam/Air/Unassisted flares meet 40 CFR 60.18 operational specs.
- **Precision / Rounding**: Full precision.
- **Applicable Scope / Category**: Scope 1 — Flaring.
- **Independently Validated**: YES (`IndependentFlaringModel.calculate`).
- **Existing Tests**: `test_diff_flaring_dual_efficiency`, `test_battery_stoichiometry_indirect_energy.py`.
- **Missing Tests**: None.
- **Risk Level**: CRITICAL.
- **Frontend vs Backend Flag**: Backend authoritative.

---

### Scope 1: Vented & Process Emissions

#### CALC-004: Mud Degassing / Well Drilling
- **Function/File**: `MudDegassingCalculator.calculate` in `new/server/calculations/vented.py`
- **Description**: Methane liberated from drilling mud during drilling and circulation operations.
- **Equation**:  
  $$\text{CH}_4 (\text{tonnes}) = \frac{\text{Drilling Days} \times \text{EF}_{\text{mud}} \times x_{\text{CH}_4} \times \rho_{\text{CH}_4}}{1000}$$
- **Inputs**: `drilling_days`, `gas_composition` ($x_{\text{CH}_4}$), `mud_type` (water-based vs oil-based)
- **Units**: Days, volume fraction, tonnes.
- **Methodology**: API Compendium (2021) §6.1.
- **Emission Factor Source**: API Table 6-1 (Water-based: 28.3 $\text{m}^3/\text{day}$, Oil-based: 141.6 $\text{m}^3/\text{day}$).
- **GWP Version**: Dynamic (`AR5`/`AR6`).
- **Assumptions**: Constant degassing rate throughout active circulation.
- **Precision / Rounding**: Full precision.
- **Applicable Scope / Category**: Scope 1 — Drilling / Mud Degassing.
- **Independently Validated**: YES (`IndependentMudDegassing.calculate`).
- **Existing Tests**: `test_diff_mud_degassing`.
- **Missing Tests**: None.
- **Risk Level**: MEDIUM.
- **Frontend vs Backend Flag**: Backend only.

---

#### CALC-005: Well Completion Flowback
- **Function/File**: `CompletionFlowbackCalculator.calculate` in `new/server/calculations/vented.py`
- **Description**: Emissions from fracturing fluid flowback prior to permanent production hookup.
- **Equation**:  
  $$\text{Vented Gas } V (\text{scf}) = \text{Flowback Days} \times \text{Daily Flow Rate}$$  
  $$\text{Emissions partitioned per D-01 if flared: } \eta = 0.98$$
- **Inputs**: `completion_type` (open vent vs flare vs green completion), `days`, `rate`, `ch4_mol`
- **Units**: $\text{scf}, \text{m}^3$, days, tonnes.
- **Methodology**: API Compendium (2021) §6.2 / EPA Subpart W §98.233(g).
- **Emission Factor Source**: Flowback rate or API Table 6-2 defaults.
- **GWP Version**: Dynamic.
- **Assumptions**: Reduced Emissions Completion (REC) captures 90–95% of gas.
- **Precision / Rounding**: Full precision.
- **Applicable Scope / Category**: Scope 1 — Completions.
- **Independently Validated**: YES (`IndependentCompletions.calculate`).
- **Existing Tests**: `test_diff_completions`.
- **Missing Tests**: None.
- **Risk Level**: HIGH.
- **Frontend vs Backend Flag**: Backend only.

---

#### CALC-006: Liquids Unloading
- **Function/File**: `LiquidsUnloadingCalculator.calculate` in `new/server/calculations/vented.py`
- **Description**: Gas purged during well cleanout events (plunger lift vs non-plunger automated venting).
- **Equation**:  
  $$\text{Volume per event } V = \left[\frac{\pi \cdot D^2}{4} \cdot H \cdot \frac{P \cdot 519.67}{14.696 \cdot T \cdot Z}\right] + (\text{Sales Flow Rate} \times \text{Venting Hours})$$
- **Inputs**: `well_depth`, `tubing_diameter`, `casing_pressure`, `hours_vented`, `events`
- **Units**: Feet, inches, psia, hours, tonnes.
- **Methodology**: API Compendium (2021) §6.3 / EPA Subpart W §98.233(c).
- **Emission Factor Source**: Thermodynamic wellbore geometric expansion.
- **GWP Version**: Dynamic.
- **Assumptions**: Wellbore fluid column purged to atmospheric pressure.
- **Precision / Rounding**: Full precision.
- **Applicable Scope / Category**: Scope 1 — Liquids Unloading.
- **Independently Validated**: YES (`IndependentLiquidsUnloading.calculate`).
- **Existing Tests**: `test_diff_liquids_unloading`.
- **Missing Tests**: None.
- **Risk Level**: HIGH.
- **Frontend vs Backend Flag**: Backend only.

---

#### CALC-007: Vessel Blowdown & Equipment Depressurization
- **Function/File**: `BlowdownCalculator.calculate` in `new/server/calculations/vented.py`
- **Description**: Purging compressors, pipelines, and treaters for maintenance or emergency ESD.
- **Equation**:  
  $$\text{Gas Mass } m (\text{kg}) = \frac{V_{\text{vessel}} \cdot (P_1 - P_2)}{Z \cdot R \cdot T} \cdot \text{MW}_{\text{gas}}$$  
  $$\text{If routed to flare: apply D-01 stoichiometric flaring partition.}$$
- **Inputs**: `vessel_volume_m3`, `initial_pressure`, `final_pressure`, `temperature`, `composition`, `control_eff`
- **Units**: $\text{m}^3, \text{kPa}, \text{bar}, ^\circ\text{C}$, tonnes.
- **Methodology**: API Compendium (2021) §6.4.
- **Emission Factor Source**: Thermodynamic ideal gas with real gas $Z$ factor correction.
- **GWP Version**: Dynamic.
- **Assumptions**: Gas cools during expansion; isothermal equilibrium achieved at termination.
- **Precision / Rounding**: Full precision.
- **Applicable Scope / Category**: Scope 1 — Blowdown / Venting.
- **Independently Validated**: YES (`IndependentBlowdown.calculate`).
- **Existing Tests**: `test_diff_blowdown`.
- **Missing Tests**: None.
- **Risk Level**: HIGH.
- **Frontend vs Backend Flag**: Backend only.

---

#### CALC-008: Storage Tanks — GOR Flash Gas & Breathing Losses
- **Function/File**: `TankFlashingCalculator.calculate` in `new/server/calculations/vented.py`
- **Description**: Dissolved gas flashing upon crude depressurization from separator into atmospheric tanks, plus working and standing losses.
- **Equation**:  
  $$\text{Flash Gas Volume (scf)} = \text{Oil Throughput (bbl)} \times \text{GOR (scf/bbl)}$$  
  $$\text{Emissions} = \text{Flash Gas} \times \text{Gas Density} \times x_g \times (1 - \eta_{\text{VRU}})$$
- **Inputs**: `throughput_bbl`, `gor`, `ch4_mol`, `co2_mol`, `control_efficiency` (VRU/flare)
- **Units**: $\text{bbl}, \text{scf/bbl}$, tonnes.
- **Methodology**: API Compendium (2021) §6.7 Eq. 6-12 / API Table 6-7.
- **Emission Factor Source**: GOR correlation or Vasquez-Beggs empirical model.
- **GWP Version**: Dynamic.
- **Assumptions**: Stock tank oil density $35^\circ\text{API}$; VRU operating uptime $98\%$.
- **Precision / Rounding**: Full precision.
- **Applicable Scope / Category**: Scope 1 — Storage Tanks.
- **Independently Validated**: YES (`IndependentStorageTanks.calculate`).
- **Existing Tests**: `test_diff_storage_tanks`, `test_tank_flashing_calculator_null_gor`.
- **Missing Tests**: None.
- **Risk Level**: CRITICAL.
- **Frontend vs Backend Flag**: Backend only.

---

#### CALC-009: Pneumatic Controllers & Chemical Injection Pumps
- **Function/File**: `PneumaticDeviceCalculator.calculate` in `new/server/calculations/vented.py`
- **Description**: Continuous high-bleed, low-bleed, intermittent venting controllers, and diaphragm pumps powered by pressurized natural gas.
- **Equation**:  
  $$\text{CH}_4 (\text{tonnes}) = \sum \left(\text{Device Count}_i \times \text{Bleed Rate}_i \times \text{Operating Hours} \times x_{\text{CH}_4} \times \rho_{\text{CH}_4} \times 10^{-3}\right)$$
- **Inputs**: `device_type` (`high_bleed`, `low_bleed`, `intermittent`, `pump`), `count`, `hours`, `bleed_rate`
- **Units**: Count, $\text{scf/hr}$ or $\text{m}^3/\text{hr}$, hours, tonnes.
- **Methodology**: API Compendium (2021) §6.8 Table 6-8 / EPA Subpart W §98.233(a).
- **Emission Factor Source**: Default rates (High bleed: 37.3 scf/hr; Low bleed: 1.39 scf/hr; Intermittent: 13.5 scf/hr; Pump: 13.3 scf/gal).
- **GWP Version**: Dynamic.
- **Assumptions**: 8,760 annual hours unless explicitly specified.
- **Precision / Rounding**: Full precision.
- **Applicable Scope / Category**: Scope 1 — Pneumatic Devices.
- **Independently Validated**: YES (`IndependentPneumatics.calculate`).
- **Existing Tests**: `test_diff_pneumatics`.
- **Missing Tests**: None.
- **Risk Level**: HIGH.
- **Frontend vs Backend Flag**: Backend only.

---

### Scope 1: Fugitive Emissions

#### CALC-010: Component-Level Fugitive Leaks
- **Function/File**: `ComponentFugitiveCalculator.calculate` in `new/server/calculations/fugitive.py`
- **Description**: Leaks from valves, flanges, connectors, open-ended lines, and pressure relief valves.
- **Equation**:  
  $$\text{CH}_4 (\text{tonnes}) = \sum \left(N_j \times \text{EF}_j \times \text{Hours} \times x_{\text{CH}_4} \times 10^{-3}\right)$$
- **Inputs**: `component_counts` (dict of component types), `service_stream` (gas, light liquid, heavy liquid), `hours`, `ch4_mol`
- **Units**: Component count, $\text{kg/hr/component}$, hours, tonnes.
- **Methodology**: API Compendium (2021) §7.1 Table 7-1 to 7-4 / EPA Protocol for Equipment Leak Emission Estimates.
- **Emission Factor Source**: API 2021 average component emission factors.
- **GWP Version**: Dynamic.
- **Assumptions**: Uniform service stream composition.
- **Precision / Rounding**: Full precision.
- **Applicable Scope / Category**: Scope 1 — Fugitive Leaks.
- **Independently Validated**: YES (`IndependentFugitiveModel.calculate_components`).
- **Existing Tests**: `test_diff_component_fugitives`, `test_component_fugitive_calculator_scalar_counts`.
- **Missing Tests**: None.
- **Risk Level**: HIGH.
- **Frontend vs Backend Flag**: Backend only.

---

#### CALC-011: Facility & Equipment-Level Screening Fugitives
- **Function/File**: `EquipmentFugitiveCalculator.calculate` in `new/server/calculations/fugitive.py`
- **Description**: Macro-level fugitive screening using major equipment counts (wellheads, separators, heater treaters).
- **Equation**:  
  $$\text{CH}_4 (\text{tonnes}) = \sum \left(\text{Equipment Count}_k \times \text{EF}_k \times \text{Hours} \times x_{\text{CH}_4} \times 10^{-3}\right)$$
- **Inputs**: `equipment_type`, `count`, `hours`, `ch4_mol`
- **Units**: Equipment count, $\text{kg/hr/equipment}$, hours, tonnes.
- **Methodology**: API Compendium (2021) §7.2 Table 7-5 to 7-10.
- **Emission Factor Source**: API 2021 facility-level equipment factors.
- **GWP Version**: Dynamic.
- **Assumptions**: 8,760 operating hours default.
- **Precision / Rounding**: Full precision.
- **Applicable Scope / Category**: Scope 1 — Equipment Fugitives.
- **Independently Validated**: YES (`IndependentFugitiveModel.calculate_equipment`).
- **Existing Tests**: `test_diff_equipment_fugitives`, `test_fugitive_screening_count_and_fraction`.
- **Missing Tests**: None.
- **Risk Level**: MEDIUM.
- **Frontend vs Backend Flag**: Backend only.

---

#### CALC-012: Compressor Seals (Centrifugal & Reciprocating)
- **Function/File**: `CompressorSealCalculator.calculate` in `new/server/calculations/fugitive.py`
- **Description**: Venting from centrifugal wet/dry compressor seals and reciprocating compressor rod packing.
- **Equation**:  
  $$\text{Emissions} = \text{Compressor Count} \times \text{Seals per Compressor} \times \text{EF}_{\text{seal}} \times \text{Hours} \times (1 - \eta_{\text{capture}})$$
- **Inputs**: `compressor_type` (`centrifugal_wet`, `centrifugal_dry`, `reciprocating_packing`), `count`, `seals`, `hours`, `control_eff`
- **Units**: Count, $\text{scf/hr}$ or $\text{kg/hr}$, tonnes.
- **Methodology**: API Compendium (2021) §7.3 Table 7-11 / EPA Subpart W §98.233(p),(q).
- **Emission Factor Source**: Default seal factors (Wet seal: 47.7 scf/min; Dry seal: 6.0 scf/min; Rod packing: 24.0 scf/hr).
- **GWP Version**: Dynamic.
- **Assumptions**: Degradation factor applied if operating hours exceed 24,000 without overhaul.
- **Precision / Rounding**: Full precision.
- **Applicable Scope / Category**: Scope 1 — Compressor Fugitives.
- **Independently Validated**: YES (`IndependentFugitiveModel.calculate_compressor_seals`).
- **Existing Tests**: `test_diff_compressor_seals`, `test_compressor_seal_and_storage_tank_uncertainty_mapping`.
- **Missing Tests**: None.
- **Risk Level**: HIGH.
- **Frontend vs Backend Flag**: Backend only.

---

### Scope 1: Midstream & Process Emissions

#### CALC-013: Acid Gas Removal (AGR / Amine Sweetening)
- **Function/File**: `AGRCalculator.calculate` in `new/server/calculations/midstream.py`
- **Description**: $\text{CO}_2$ stripped from sour natural gas by chemical solvent (MEA/DEA/MDEA) plus methane physical co-absorption slip.
- **Equation**:  
  $$\text{CO}_2 (\text{tonnes}) = \frac{\text{Throughput (scf)} \cdot (x_{\text{CO}_2,\text{in}} - x_{\text{CO}_2,\text{out}}) \cdot \rho_{\text{CO}_2} \cdot (1 - \eta_{\text{capture}})}{1000}$$  
  $$\text{CH}_4 (\text{tonnes}) = \frac{\text{Throughput (scf)} \cdot x_{\text{CH}_4,\text{in}} \cdot f_{\text{slip}} \cdot \rho_{\text{CH}_4} \cdot (1 - \eta_{\text{abatement}})}{1000}$$  
  $$\text{If routed to Claus/Thermal Oxidizer: } \text{combusted CH}_4 \rightarrow \text{CO}_2 \text{ stoichiometrically}.$$
- **Inputs**: `throughput_mmscf`, `co2_in`, `co2_out`, `ch4_in`, `ch4_slip_fraction`, `control_type`, `control_eff`
- **Units**: $\text{MMscf/yr}$, mole fractions, tonnes.
- **Methodology**: API Compendium (2021) §6.5 & Table 6-5.
- **Emission Factor Source**: Stoichiometric gas balance; Table 6-5 slip fraction ($0.1\%$).
- **GWP Version**: Dynamic.
- **Assumptions**: Treated gas meeting pipeline specification ($\le 2\%\text{ CO}_2$).
- **Precision / Rounding**: Full precision.
- **Applicable Scope / Category**: Scope 1 — Acid Gas Removal.
- **Independently Validated**: YES (`IndependentAGRModel.calculate`).
- **Existing Tests**: `test_diff_agr`, `test_agr_zero_removal_boundary`.
- **Missing Tests**: None.
- **Risk Level**: CRITICAL.
- **Frontend vs Backend Flag**: Backend only.

---

#### CALC-014: Glycol Dehydrators (TEG Units)
- **Function/File**: `DehydratorCalculator.calculate` in `new/server/calculations/midstream.py`
- **Description**: Methane and VOC emissions dissolved in circulating triethylene glycol and released from regenerator still column.
- **Equation**:  
  $$\text{CH}_4 (\text{tonnes}) = \frac{\text{Throughput} \times \text{EF}_{\text{solubility}}(P, T) \times (1 - \eta_{\text{flash\_recycle}}) \times (1 - \eta_{\text{condenser}})}{1000}$$
- **Inputs**: `throughput_mmscf`, `pressure_psia`, `temperature_f`, `glycol_pump_rate`, `control_type`, `control_eff`
- **Units**: $\text{MMscf/day}, \text{psia}, ^\circ\text{F}$, tonnes.
- **Methodology**: API Compendium (2021) §6.6 / GRI-GLYCalc parametric correlations.
- **Emission Factor Source**: Henry's Law absorption coefficient as function of contactor pressure.
- **GWP Version**: Dynamic.
- **Assumptions**: Pure triethylene glycol (TEG); stripping gas rate accounted for if used.
- **Precision / Rounding**: Full precision.
- **Applicable Scope / Category**: Scope 1 — Dehydrators.
- **Independently Validated**: YES (`IndependentDehydratorModel.calculate`).
- **Existing Tests**: `test_diff_dehydrator`, `test_dehydrator_stoichiometric_co2_combustion`.
- **Missing Tests**: None.
- **Risk Level**: HIGH.
- **Frontend vs Backend Flag**: Backend only.

---

#### CALC-015: Chemical Stoichiometry & SMR Hydrogen
- **Function/File**: `StoichiometricCalculator.calculate` in `new/server/calculations/stoichiometry.py`
- **Description**: Molar reaction balance for industrial processes (Steam Methane Reforming $\text{CH}_4 + 2\text{H}_2\text{O} \rightarrow \text{CO}_2 + 4\text{H}_2$).
- **Equation**:  
  $$\text{Theoretical CO}_2 = \text{Feedstock Moles} \times \left(\frac{\text{MW}_{\text{CO}_2}}{\text{MW}_{\text{feed}}}\right) \times n_c \times \text{Conversion Rate}$$  
  $$\text{Net CO}_2 = \text{Theoretical CO}_2 \times (1 - \eta_{\text{CCUS}})$$
- **Inputs**: `production_tons`, `feedstock_mass`, `molecular_weight_feed`, `carbon_atoms`, `ccus_efficiency`
- **Units**: Metric tonnes, g/mol, fractional efficiencies.
- **Methodology**: IPCC 2006 Industrial Processes and Product Use (IPPU) / Stoichiometry.
- **Emission Factor Source**: Molecular weight constants (C: 12.011, H: 1.008, O: 15.999).
- **GWP Version**: Dynamic.
- **Assumptions**: Stoichiometric conversion efficiency per engineering design.
- **Precision / Rounding**: Full precision.
- **Applicable Scope / Category**: Scope 1 — Process / Chemical Stoichiometry.
- **Independently Validated**: YES (`IndependentStoichiometryModel.calculate_reaction`).
- **Existing Tests**: `test_diff_stoichiometry`, `test_stoichiometry_short_ton`.
- **Missing Tests**: None.
- **Risk Level**: HIGH.
- **Frontend vs Backend Flag**: Backend only.

---

### Scope 2: Indirect Energy Emissions

#### CALC-016: Scope 2 — Location-Based Grid Electricity
- **Function/File**: `routes/scope2.py`
- **Description**: Grid consumption multiplied by regional/national average grid emission factor.
- **Equation**:  
  $$\text{CO}_2\text{e (tonnes)} = \frac{\text{Consumption (kWh)} \times \text{Grid EF (kg CO}_2\text{e/kWh)}}{1000}$$
- **Inputs**: `electricity_kwh`, `grid_factor`
- **Units**: $\text{kWh}, \text{MWh}, \text{kg/kWh}$, tonnes $\text{CO}_2\text{e}$.
- **Methodology**: GHG Protocol Scope 2 Guidance (Location-based).
- **Emission Factor Source**: eGRID / IEA / Country Grid Factors.
- **GWP Version**: Standard 100-year.
- **Assumptions**: Physical grid average factor represents power generation mix.
- **Precision / Rounding**: Full precision in calculation; rounded to 3 decimal places in UI.
- **Applicable Scope / Category**: Scope 2 — Purchased Electricity.
- **Independently Validated**: YES (`IndependentScope2Model.calculate_location_based`).
- **Existing Tests**: `test_diff_scope2_location`, `test_scope2_authoritative_calculation_overrides_injected_co2e`.
- **Missing Tests**: None.
- **Risk Level**: HIGH.
- **Frontend vs Backend Flag**: Frontend emulates multiplication in `Scope2Form.jsx`; backend authoritatively recalculates on submit.

---

#### CALC-017: Scope 2 — Purchased Steam & Thermal Energy
- **Function/File**: `_calc_indirect_steam` in `new/server/routes/scope2.py` / `IndirectSteamCalculator` in `indirect.py`
- **Description**: Steam or hot water consumption normalized by boiler thermal efficiency and transmission losses per Decision D-03.
- **Equation**:  
  $$\eta_{\text{net}} = \eta_{\text{boiler}} \times (1 - L_{\text{trans}})$$  
  $$\text{Fuel Energy Required (MMBtu)} = \frac{\text{Delivered Thermal Energy}}{\eta_{\text{net}}}$$  
  $$\text{CO}_2\text{e (tonnes)} = \frac{\text{Fuel Energy} \times \text{Fuel EF (kg/MMBtu)}}{1000}$$
- **Inputs**: `delivered_steam_tonnes`, `enthalpy_mmbtu_per_ton`, `boiler_eff`, `trans_loss`, `fuel_ef`
- **Units**: Tonnes steam, $\text{MMBtu}$, fractional efficiency, tonnes $\text{CO}_2\text{e}$.
- **Methodology**: GHG Protocol Scope 2 Guidance §6.2.
- **Emission Factor Source**: Fuel combustion factors + boiler vendor datasheets.
- **GWP Version**: Dynamic.
- **Assumptions**: Enthalpy difference between delivered steam and boiler feedwater; $\eta_{\text{net}} > 0$ strictly enforced (422 rejection if $\le 0$).
- **Precision / Rounding**: Full precision.
- **Applicable Scope / Category**: Scope 2 — Purchased Steam / Heat.
- **Independently Validated**: YES (`IndependentScope2Model.calculate_steam`).
- **Existing Tests**: `test_diff_scope2_steam`, `test_scope2_steam_recalculation_enthalpy`.
- **Missing Tests**: None.
- **Risk Level**: HIGH.
- **Frontend vs Backend Flag**: Backend authoritative.

---

#### CALC-018: Scope 2 — Combined Heat and Power (CHP) Allocation
- **Function/File**: `CogenAllocationCalculator.calculate` in `new/server/calculations/indirect.py`
- **Description**: Fuel attribution between electric power and thermal output from cogeneration units.
- **Equation**:  
  $$\text{Efficiency Method: } F_e = \frac{E / \eta_e}{(E / \eta_e) + (H / \eta_h)} \times F_{\text{total}}, \quad F_h = F_{\text{total}} - F_e$$  
  $$\text{Work-Potential Method: } F_h = \frac{H \times (1 - T_0/T_h)}{E + H \times (1 - T_0/T_h)} \times F_{\text{total}}$$
- **Inputs**: `electric_output_mwh`, `thermal_output_mmbtu`, `total_fuel_mmbtu`, `eff_electric`, `eff_thermal`
- **Units**: $\text{MWh}, \text{MMBtu}$, efficiencies, tonnes $\text{CO}_2\text{e}$.
- **Methodology**: GHG Protocol Scope 2 Guidance / Combined Heat and Power Standard.
- **Emission Factor Source**: Plant operational records.
- **GWP Version**: Dynamic.
- **Assumptions**: Constant generator and heat-recovery boiler efficiency.
- **Precision / Rounding**: Full precision.
- **Applicable Scope / Category**: Scope 2 — Cogeneration.
- **Independently Validated**: YES (`IndependentScope2Model.calculate_cogen_allocation`).
- **Existing Tests**: `test_diff_cogen_allocation`.
- **Missing Tests**: None.
- **Risk Level**: HIGH.
- **Frontend vs Backend Flag**: Backend only.

---

### Scope 3: Value Chain Emissions

#### CALC-019: Scope 3 — Category 1 Purchased Goods (Spend-Based EEIO)
- **Function/File**: `compute_scope3_co2e` in `new/server/calculations/units.py`
- **Description**: Economic Input-Output spend factors per \$1,000 procurement spend.
- **Equation**:  
  $$\text{CO}_2\text{e (tonnes)} = \frac{\text{Spend (\$) } \times \text{EEIO Factor (kg CO}_2\text{e / \$1,000)}}{1,000,000}$$
- **Inputs**: `spend_amount`, `eeio_factor` (contains `$1000` or `$1k` in unit string)
- **Units**: Currency (\$), $\text{kg CO}_2\text{e/\$1k}$, Metric tonnes $\text{CO}_2\text{e}$.
- **Methodology**: GHG Protocol Scope 3 Standard / USEEIO v2.0.
- **Emission Factor Source**: EPA USEEIO Supply Chain GHG Emission Factors.
- **GWP Version**: 100-year.
- **Assumptions**: Constant price indices without inflation adjustment.
- **Precision / Rounding**: Full precision.
- **Applicable Scope / Category**: Scope 3 — Category 1 (Spend-based).
- **Independently Validated**: YES (`IndependentScope3Model.calculate_spend_eeio`).
- **Existing Tests**: `test_diff_scope3_eeio`, `test_scope3_eeio_per_thousand_scaling_defect`.
- **Missing Tests**: None.
- **Risk Level**: HIGH.
- **Frontend vs Backend Flag**: Backend authoritative.

---

#### CALC-020: Scope 3 — Physical Activity & Generic Categories (Cat 1–15)
- **Function/File**: `compute_scope3_co2e` in `new/server/calculations/units.py`
- **Description**: Mass, volume, or unit-based value chain calculations supporting Categories 1 through 15.
- **Equation**:  
  $$\text{If factor unit in tonnes: } \text{CO}_2\text{e} = \text{Activity} \times \text{EF}$$  
  $$\text{If factor unit in kg: } \text{CO}_2\text{e} = \frac{\text{Activity} \times \text{EF}}{1000}$$
- **Inputs**: `activity_amount`, `emission_factor`, `factor_unit`, `calculation_method`
- **Units**: Activity (tonnes, litres, $\text{m}^3$, passenger-km), EF, tonnes $\text{CO}_2\text{e}$.
- **Methodology**: GHG Protocol Corporate Value Chain (Scope 3) Standard.
- **Emission Factor Source**: DEFRA / Ecoinvent / Supplier Environmental Product Declarations (EPD).
- **GWP Version**: Dynamic.
- **Assumptions**: Linear proportionality of supplier emissions to purchased volume.
- **Precision / Rounding**: Full precision.
- **Applicable Scope / Category**: Scope 3 — Categories 1–15.
- **Independently Validated**: YES (`IndependentScope3Model.calculate_physical_activity`).
- **Existing Tests**: `test_diff_scope3_physical`, `test_scope3_tonne_factor_handling`.
- **Missing Tests**: None.
- **Risk Level**: HIGH.
- **Frontend vs Backend Flag**: Frontend form provides quick calculation; backend enforces recalculation.

---

### Uncertainty & Statistical Modeling

#### CALC-021: Analytical Uncertainty Propagation — Product Combination
- **Function/File**: `propagate_uncertainty` in `new/server/calculations/uncertainty.py`
- **Description**: Root-sum-of-squares (SRSS) combination of independent activity data and emission factor uncertainties.
- **Equation**:  
  $$u_{\text{rel}} = \sqrt{u_{\text{activity}}^2 + u_{\text{ef}}^2}$$  
  $$U_{95\%} = k \times u_{\text{rel}} \quad (k=2 \text{ for 95\% confidence interval})$$  
  $$\text{Lower Bound} = \text{Emission} \times (1 - U_{95\%}), \quad \text{Upper Bound} = \text{Emission} \times (1 + U_{95\%})$$
- **Inputs**: `emission_value`, `ef_uncertainty`, `activity_uncertainty`, `tier`, `process_category`
- **Units**: Fractions (e.g. 0.05 = 5%), tonnes.
- **Methodology**: IPCC 2006 Guidelines Vol. 1 Ch. 3 Eq. 3.1 / GUM (JCGM 100:2008).
- **Emission Factor Source**: Tier 1/2/3 uncertainty tables in `uncertainty.py`.
- **GWP Version**: N/A.
- **Assumptions**: Uncorrelated, normally distributed parameter errors; small relative uncertainties ($<30\%$).
- **Precision / Rounding**: Full precision.
- **Applicable Scope / Category**: All Scopes (1, 2, 3).
- **Independently Validated**: YES (`IndependentUncertaintyModel.propagate_product`).
- **Existing Tests**: `test_diff_uncertainty_product`, `test_base_calculator_uncertainty_k_factor`.
- **Missing Tests**: None.
- **Risk Level**: MEDIUM.
- **Frontend vs Backend Flag**: Backend authoritative; displayed in UI inspector modals.

---

#### CALC-022: Analytical Uncertainty Propagation — Summation Across Inventory
- **Function/File**: `combine_uncertainties_sum` in `new/server/calculations/uncertainty.py`
- **Description**: Combined uncertainty for aggregation across multiple sources, facilities, or scopes.
- **Equation**:  
  $$u_{\text{total}} = \frac{\sqrt{\sum \left(x_i \cdot u_i\right)^2}}{\sum x_i}$$
- **Inputs**: List of tuples $(x_i, u_i)$ (value, relative uncertainty).
- **Units**: Tonnes, fractions.
- **Methodology**: IPCC 2006 Guidelines Vol. 1 Ch. 3 Eq. 3.2.
- **Emission Factor Source**: Individual source uncertainties.
- **GWP Version**: N/A.
- **Assumptions**: Mutually independent emissions sources; zero cross-source covariance.
- **Precision / Rounding**: Full precision.
- **Applicable Scope / Category**: Rollups & Aggregations.
- **Independently Validated**: YES (`IndependentUncertaintyModel.combine_sum`).
- **Existing Tests**: `test_diff_uncertainty_sum`, `test_uncertainty_combine_sum_negative_sinks`.
- **Missing Tests**: None.
- **Risk Level**: MEDIUM.
- **Frontend vs Backend Flag**: Backend only.

---

#### CALC-023: Statistical Anomaly Detection
- **Function/File**: `detect_emission_anomalies` in `new/server/calculations/anomaly.py`
- **Description**: Time-series outlier detection using rolling trailing 12-month window Z-score and Interquartile Range (IQR).
- **Equation**:  
  $$Z = \frac{x - \mu_{\text{trailing}}}{\sigma_{\text{trailing}}}, \quad \text{IQR} = Q_3 - Q_1$$  
  $$\text{Anomaly Flag} = \text{True if } |Z| > 3.0 \text{ or } x > Q_3 + 1.5 \cdot \text{IQR}$$
- **Inputs**: Current record $(x, \text{year}, \text{month})$, historical facility records.
- **Units**: Metric tonnes.
- **Methodology**: ISO 14064-3 / Statistical Process Control (SPC).
- **Emission Factor Source**: Historical company records.
- **GWP Version**: N/A.
- **Assumptions**: Trailing window strictly precedes evaluated period (Decision B-10).
- **Precision / Rounding**: Full precision.
- **Applicable Scope / Category**: QA/QC Data Diagnostics.
- **Independently Validated**: YES (Verified in `test_battery_statistical_anomaly_detection.py`).
- **Existing Tests**: `test_anomaly_iqr_quantile_interpolation`, `test_bulk_anomaly_flag_persistence`.
- **Missing Tests**: None.
- **Risk Level**: LOW.
- **Frontend vs Backend Flag**: Backend generates flag; frontend displays warning badges.

---

### Intensity & Performance Metrics

#### CALC-024: Production-Normalized Carbon Intensity
- **Function/File**: `get_intensity_trend` in `new/server/routes/dashboard.py`
- **Description**: Gross Scope 1 + Scope 2 emissions normalized per barrel of oil equivalent (BOE) produced.
- **Equation**:  
  $$\text{BOE} = \text{Oil Volume (bbl)} + \left(\frac{\text{Gas Volume (mscf)}}{5.8}\right)$$  
  $$\text{Carbon Intensity} = \frac{\text{Total Emissions (kg CO}_2\text{e)}}{\text{Total BOE}}$$
- **Inputs**: `scope1_tonnes`, `scope2_tonnes`, `oil_bbl`, `gas_mscf`
- **Units**: $\text{kg CO}_2\text{e / BOE}$ or $\text{tCO}_2\text{e / 1,000 BOE}$.
- **Methodology**: IOGP / API Sustainability Reporting Guidance.
- **Emission Factor Source**: Standard thermal equivalence (5.8 mscf natural gas = 1 boe).
- **GWP Version**: Consistent with inventory.
- **Assumptions**: Zero denominator handled gracefully (returns 0 or null, no ZeroDivisionError).
- **Precision / Rounding**: Full precision; displayed to 2 decimals.
- **Applicable Scope / Category**: Corporate KPIs / Intensity.
- **Independently Validated**: YES (`IndependentIntensityModel.calculate_carbon_intensity`).
- **Existing Tests**: `test_diff_carbon_intensity`, `test_dashboard_intensity_mmscf_scaling`.
- **Missing Tests**: None.
- **Risk Level**: HIGH.
- **Frontend vs Backend Flag**: Backend calculates; frontend renders charts.

---

#### CALC-025: Methane Loss Intensity & EPA WEC Fee
- **Function/File**: `routes/dashboard.py` & `validation/reference_model/aggregation_intensity.py`
- **Description**: Methane emissions as a percentage of gross produced natural gas, and statutory Waste Emissions Charge evaluation.
- **Equation**:  
  $$\text{Methane Intensity \%} = \frac{\text{Vented + Flared + Fugitive CH}_4\text{ Volume (scf)}}{\text{Gross Gas Production (scf)}} \times 100$$  
  $$\text{EPA WEC Methane Threshold} = 0.0020 \times \text{Sales Gas Production}$$  
  $$\text{WEC Fee (\$) } = \max(0, \text{Emitted CH}_4 - \text{Threshold}) \times \text{Fee Rate (\$/tonne)}$$
- **Inputs**: `ch4_tonnes`, `gas_production_mscf`, `fee_rate` (\$900/t in 2024, \$1,200/t in 2025, \$1,500/t in 2026+)
- **Units**: Percentage (%), Currency (\$).
- **Methodology**: OGMP 2.0 / EPA Clean Air Act §136 (40 CFR Part 99 WEC).
- **Emission Factor Source**: Statutory schedule.
- **GWP Version**: N/A (Methane mass directly).
- **Assumptions**: Threshold applies to petroleum and natural gas facilities exceeding 25,000 tCO2e.
- **Precision / Rounding**: Full precision.
- **Applicable Scope / Category**: Regulatory Compliance & Methane Targets.
- **Independently Validated**: YES (`IndependentIntensityModel.calculate_methane_intensity_and_wec`).
- **Existing Tests**: `test_diff_methane_intensity_wec`.
- **Missing Tests**: None.
- **Risk Level**: HIGH.
- **Frontend vs Backend Flag**: Backend authoritative.

---

### Regulatory & Framework Reconciliations

#### CALC-026: OGMP 2.0 Facility Level Quantification & Survey Reconciliation
- **Function/File**: `compute_facility_ogmp_level` in `new/server/services/ogmp.py`
- **Description**: Classifies facility monitoring into OGMP 2.0 Level 1–5, and reconciles bottom-up source estimates against top-down aerial/satellite surveys.
- **Equation**:  
  $$\text{Annualized Top-Down Rate } T = \frac{1}{N} \sum_{i=1}^N \text{Survey}_i \quad (\text{per Decision D-02})$$  
  $$\text{Variance \%} = \frac{|T - B|}{T} \times 100 \quad (B = \text{bottom-up annual sum})$$  
  $$\text{Status} = \text{"Reconciled" if Variance} \le \text{Threshold, else "Discrepancy Flagged"}$$
- **Inputs**: `bottom_up_ch4_tonnes`, `top_down_surveys`, `reconciliation_threshold` (default 20%)
- **Units**: Metric tonnes $\text{CH}_4$, percentage.
- **Methodology**: OGMP 2.0 Reporting Framework (Guidance 2021).
- **Emission Factor Source**: Survey annualized estimates.
- **GWP Version**: N/A.
- **Assumptions**: When $B=0$ and $T>0$, variance is flagged as discrepancy (Decision L-6).
- **Precision / Rounding**: Full precision.
- **Applicable Scope / Category**: OGMP 2.0 Voluntary Framework.
- **Independently Validated**: YES (`IndependentOGMPModel.reconcile_surveys`).
- **Existing Tests**: `test_diff_ogmp_reconciliation`, `test_ogmp_survey_zero_top_down_no_false_discrepancy`.
- **Missing Tests**: None.
- **Risk Level**: HIGH.
- **Frontend vs Backend Flag**: Backend authoritative.
