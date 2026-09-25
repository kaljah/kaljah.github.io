# API Compendium 2021 — Software Implementation Status

**Legend:**
- ✅ Fully implemented (backend calculator + dispatcher routing + frontend form)
- ⚠️ Partially implemented (backend only, no dedicated UI form, or routing-only)
- ❌ Not implemented

---

## Process-by-Process Status

| # | Process Type | Backend Calculator | Dispatcher Key(s) | Frontend Form | Status |
|---|---|---|---|---|---|
| 1 | **Stationary Combustion** | `CombustionCalculator` in [`combustion.py`](file:///c:/Users/samsung/Desktop/H2/new/server/calculations/combustion.py) | `stationary_combustion`, `combustion`, `mobile_combustion` | [`CombustionForm.jsx`](file:///c:/Users/samsung/Desktop/H2/new/client/src/CombustionForm.jsx) | ✅ |
| 2 | **Flaring** | `FlaringCalculator` in [`combustion.py`](file:///c:/Users/samsung/Desktop/H2/new/server/calculations/combustion.py) | `flaring`, `flare` | [`CombustionForm.jsx`](file:///c:/Users/samsung/Desktop/H2/new/client/src/CombustionForm.jsx) (flare mode) | ✅ |
| 3 | **Venting / Blowdown** | `BlowdownCalculator` in [`vented.py`](file:///c:/Users/samsung/Desktop/H2/new/server/calculations/vented.py) | `venting`, `blowdown` | [`BlowdownForm.jsx`](file:///c:/Users/samsung/Desktop/H2/new/client/src/BlowdownForm.jsx) | ✅ |
| 4 | **Liquids Unloading** | `LiquidsUnloadingCalculator` in [`vented.py`](file:///c:/Users/samsung/Desktop/H2/new/server/calculations/vented.py) | `liquids_unloading`, `unloading` | [`UnloadingForm.jsx`](file:///c:/Users/samsung/Desktop/H2/new/client/src/UnloadingForm.jsx) | ✅ |
| 5 | **Storage Tanks** | `TankFlashingCalculator` in [`vented.py`](file:///c:/Users/samsung/Desktop/H2/new/server/calculations/vented.py) | `storage_tanks`, `tank_flashing`, `tank_working`, `tank_breathing`, `tank` | [`TankForm.jsx`](file:///c:/Users/samsung/Desktop/H2/new/client/src/TankForm.jsx) | ✅ |
| 6 | **Pneumatic Devices** | `PneumaticDeviceCalculator` in [`vented.py`](file:///c:/Users/samsung/Desktop/H2/new/server/calculations/vented.py) | `pneumatic_devices`, `pneumatic_device`, `pneumatics`, `pneumatic` | [`PneumaticsForm.jsx`](file:///c:/Users/samsung/Desktop/H2/new/client/src/PneumaticsForm.jsx) | ✅ |
| 7 | **Fugitive Equipment Leaks — Component Level** | `ComponentFugitiveCalculator` in [`fugitive.py`](file:///c:/Users/samsung/Desktop/H2/new/server/calculations/fugitive.py) | `fugitive_component`, `component_fugitive` | [`FugitivesForm.jsx`](file:///c:/Users/samsung/Desktop/H2/new/client/src/FugitivesForm.jsx) | ✅ |
| 7b | **Fugitive — Equipment Level (Wellhead, Separator, Gathering, Processing, T&S, Refinery, Distribution, LNG, Offshore)** | `EquipmentFugitiveCalculator` in [`fugitive.py`](file:///c:/Users/samsung/Desktop/H2/new/server/calculations/fugitive.py) | `wellhead_fugitive`, `separator_fugitive`, `gathering_boosting`, `gas_processing`, `transmission_storage`, `refinery_fugitive`, `distribution_fugitive`, `lng_operations`, `fugitive`, `equipment_fugitive` | [`FugitivesForm.jsx`](file:///c:/Users/samsung/Desktop/H2/new/client/src/FugitivesForm.jsx) | ✅ |
| 7c | **Compressor Seals** | `CompressorSealCalculator` in [`fugitive.py`](file:///c:/Users/samsung/Desktop/H2/new/server/calculations/fugitive.py) | `compressor_seal`, `compressor_fugitive` | [`FugitivesForm.jsx`](file:///c:/Users/samsung/Desktop/H2/new/client/src/FugitivesForm.jsx) | ✅ |
| 8 | **Acid Gas Removal (AGR / Amine)** | `AGRCalculator` in [`midstream.py`](file:///c:/Users/samsung/Desktop/H2/new/server/calculations/midstream.py) | `agr`, `acid_gas_removal` | [`AGRForm.jsx`](file:///c:/Users/samsung/Desktop/H2/new/client/src/AGRForm.jsx) | ✅ |
| 9 | **Glycol Dehydrators (TEG)** | `DehydratorCalculator` in [`midstream.py`](file:///c:/Users/samsung/Desktop/H2/new/server/calculations/midstream.py) | `dehydrator` | [`DehydratorForm.jsx`](file:///c:/Users/samsung/Desktop/H2/new/client/src/DehydratorForm.jsx) | ✅ |
| 10 | **Chemical Production (Process CO₂)** | `StoichiometricCalculator` in [`stoichiometry.py`](file:///c:/Users/samsung/Desktop/H2/new/server/calculations/stoichiometry.py) | `chemical_production`, `stoichiometry` | [`Scope1Form.jsx`](file:///c:/Users/samsung/Desktop/H2/new/client/src/Scope1Form.jsx) (stoich mode) | ✅ |
| 11 | **N₂O — Nitric Acid Production** | `StoichiometricCalculator` in [`stoichiometry.py`](file:///c:/Users/samsung/Desktop/H2/new/server/calculations/stoichiometry.py) | `nitric_acid_production` | [`Scope1Form.jsx`](file:///c:/Users/samsung/Desktop/H2/new/client/src/Scope1Form.jsx) | ✅ |
| 11b | **N₂O — Adipic Acid Production** | `StoichiometricCalculator` in [`stoichiometry.py`](file:///c:/Users/samsung/Desktop/H2/new/server/calculations/stoichiometry.py) | `adipic_acid_production` | [`Scope1Form.jsx`](file:///c:/Users/samsung/Desktop/H2/new/client/src/Scope1Form.jsx) | ✅ |
| 12 | **Asphalt Blowing** | ❌ No dedicated calculator | ❌ Not in dispatcher | ❌ No form | ⚠️ EF data-only |
| 13 | **Mud Degassing / Drilling** | `MudDegassingCalculator` in [`vented.py`](file:///c:/Users/samsung/Desktop/H2/new/server/calculations/vented.py) | `drilling`, `mud_degassing` | [`DrillingForm.jsx`](file:///c:/Users/samsung/Desktop/H2/new/client/src/DrillingForm.jsx) | ✅ |
| 14 | **Well Completion Flowback** | `CompletionFlowbackCalculator` in [`vented.py`](file:///c:/Users/samsung/Desktop/H2/new/server/calculations/vented.py) | `completions`, `completion_flowback` | [`CompletionsForm.jsx`](file:///c:/Users/samsung/Desktop/H2/new/client/src/CompletionsForm.jsx) | ✅ |
| 15 | **Scope 2 — Purchased Electricity** | `IndependentScope2Model` / routes in [`routes/scope2.py`](file:///c:/Users/samsung/Desktop/H2/new/server/routes) | `scope2_electricity` | [`Scope2Form.jsx`](file:///c:/Users/samsung/Desktop/H2/new/client/src/Scope2Form.jsx) | ✅ |
| 15b | **Scope 2 — Purchased Steam / Heat** | `IndirectSteamCalculator` in [`indirect.py`](file:///c:/Users/samsung/Desktop/H2/new/server/calculations/indirect.py) | `indirect_steam` | [`Scope2Form.jsx`](file:///c:/Users/samsung/Desktop/H2/new/client/src/Scope2Form.jsx) | ✅ |
| 15c | **Scope 2 — CHP / Cogeneration** | `CogenAllocationCalculator` in [`indirect.py`](file:///c:/Users/samsung/Desktop/H2/new/server/calculations/indirect.py) | `cogen_allocation`, `cogen` | [`Scope2Form.jsx`](file:///c:/Users/samsung/Desktop/H2/new/client/src/Scope2Form.jsx) | ✅ |
| 16 | **Scope 3 — Spend-Based EEIO** | `compute_scope3_co2e` in [`units.py`](file:///c:/Users/samsung/Desktop/H2/new/server/calculations/units.py) | `scope3_spend` | [`Scope3Form.jsx`](file:///c:/Users/samsung/Desktop/H2/new/client/src/Scope3Form.jsx) | ✅ |
| 16b | **Scope 3 — Physical Activity** | `compute_scope3_co2e` in [`units.py`](file:///c:/Users/samsung/Desktop/H2/new/server/calculations/units.py) | `scope3_physical` | [`Scope3Form.jsx`](file:///c:/Users/samsung/Desktop/H2/new/client/src/Scope3Form.jsx) | ✅ |

---

## Summary

| Status | Count | Processes |
|---|---|---|
| ✅ **Fully implemented** | **20/21** | All core Scope 1, 2, and 3 process types |
| ⚠️ **Partial — EF data only** | **1/21** | Asphalt Blowing |
| ❌ **Not implemented** | **0** | — |

---

## The One Gap: Asphalt Blowing

**Asphalt Blowing** (API §6, Table 6-52, Exhibit 6-45) has its emission factors defined in [`emission_factors_api2021.py`](file:///c:/Users/samsung/Desktop/H2/new/server/emission_factors_api2021.py):

```python
"Asphalt": {
    "co2": 10.43,   # kg CO₂/ton asphalt
    "ch4": 0.022,   # kg CH₄/ton asphalt
    "process_category": "asphalt_blowing",
    "source": "API Compendium 2021 Section 6, Table 6-52",
}
```

But:
- ❌ No entry in `PROCESS_TYPES` dict in [`process_categories.py`](file:///c:/Users/samsung/Desktop/H2/new/server/process_categories.py)
- ❌ No key `asphalt_blowing` in [`dispatcher.py`](file:///c:/Users/samsung/Desktop/H2/new/server/calculations/dispatcher.py)
- ❌ No dedicated UI form

It **could** be calculated via the generic `stoichiometry` or `chemical_production` path with manual factor entry, but it is not a named/selectable process type in the UI.

---

## What Each Tier Has per Implemented Process

| Process | Tier 1 in Software | Tier 3 in Software |
|---|---|---|
| Stationary Combustion | ✅ `calculate_tier1_2()` — default EF catalog | ✅ `calculate_tier3()` — GC carbon balance |
| Flaring | ✅ Default EF per flare type | ✅ Dual-efficiency stoichiometric |
| Venting / Blowdown | ✅ Default NG vent factor | ✅ Real-gas depressurization |
| Liquids Unloading | ✅ / ✅ Wellbore geometry (Tier 3 only; no simpler default path needed) | ✅ |
| Storage Tanks | ✅ GOR EF table factors | ✅ Vasquez-Beggs + GOR |
| Pneumatic Devices | ✅ Default bleed rate factors | ✅ Coriolis/direct measured rate |
| Fugitive — Component | ✅ Average EF tables 7-1 to 7-8 | ✅ Correlation equation (A × ppm^B) |
| Fugitive — Equipment | ✅ Equipment-level tables 7-9, 7-10, 7-29, 7-30, 7-35, 7-76, 7-80 | ✅ Direct measurement |
| Acid Gas Removal | ✅ Default 0.1% slip fraction | ✅ Full gas mass balance |
| Glycol Dehydrator | ✅ 0.266 t CH₄/MMscf default | ✅ Henry's Law solubility |
| Chemical Production | ✅ Table 6-167 product factors | ✅ Stoichiometric carbon balance |
| Nitric/Adipic Acid | ✅ pg. 407 N₂O factors | ✅ CEMS (via direct input) |
| Mud Degassing | ✅ Table 6-1 default rates | ✅ Measured m³/day |
| Well Completions | ✅ Table 6-2 defaults | ✅ Measured flowback rate |
| Scope 2 Electricity | ✅ Grid EF location-based | ✅ Market-based (user EF) |
| Scope 2 Steam / CHP | ✅ Boiler efficiency model | ✅ Efficiency allocation |
| Scope 3 | ✅ USEEIO spend-based | ✅ Physical activity EPD |
