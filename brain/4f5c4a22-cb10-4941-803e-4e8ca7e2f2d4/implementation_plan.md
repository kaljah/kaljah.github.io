# Implementation Plan: Extended Scope 1 Tier 1 & Tier 3 Calculation Scenarios and Complete Audit

This plan addresses the user's request to continue testing scenarios not yet tested in Tier 1 and Tier 3 Scope 1 calculations, maintaining all data in the database with \(\ge 360\) records per region, strictly adhering to real database regions, verifying the tables below Scope 1 emissions, checking uncertainty inputs and propagation, and re-auditing all KPIs across Dashboard, Carbon Intensity, and Methane Intensity.

---

## 1. Verified Real Database Regions & Facilities
Per database records in `ghg_app.db` (`Facility` table):
- **West**: Facility ID `1` (`Tosyali DRI Plant`), Activity: Iron & Steel / Natural Gas Reforming, Division: Downstream.
- **Center**: Facility ID `3` (`GICA Chlef Cement Plant`), Activity: Clinker / Cement Calcination, Division: Downstream.
- **South**: Facility ID `4` (`Sonatrach Hassi Messaoud CTG`), Activity: Exploration & Production, Division: Upstream.

All tests will strictly use these facility IDs, regional boundaries, and operational streams.

---

## 2. Target Test Scenarios Matrix

### Group A: Tier 3 Engineering Scenarios (Uncovered Processes & Methods)
1. **Completions - Rate × Duration Method (Tier 3)**:
   - *Facility*: Sonatrach HMD (Facility 4, South, Upstream).
   - *Process*: `completions` (Well Completions & Workovers).
   - *Inputs*: Method = `rate_duration`, Flowback Duration = `48` hrs, Gas Rate = `1.25` Mcf/hr, Gas \(\text{CH}_4\) = `82.0`%, \(\text{CO}_2\) = `3.5`%, Flare Efficiency = `95.0`%, Events = `2`.
   - *Uncertainties*: Meter tolerance `1.5`%, GC analytical `1.0`%, Override \(\text{CO}_2\) `5`%, \(\text{CH}_4\) `7`%, \(\text{N}_2\text{O}\) `10`%.
2. **Completions - Liquid Flowback × GOR Method (Tier 3, API Eq. 6-12)**:
   - *Facility*: Tosyali DRI (Facility 1, West, Upstream context).
   - *Process*: `completions`.
   - *Inputs*: Method = `gor`, Liquid Flowback = `8,500` bbl, GOR = `1,200` scf/bbl, Gas to Sales = `1,500` Mcf deducted, Gas \(\text{CH}_4\) = `78.5`%, \(\text{CO}_2\) = `4.0`%, Flare Efficiency = `98.0`%, Events = `1`.
   - *Uncertainties*: Meter `2.0`%, Override \(\text{CO}_2\) `6`%, \(\text{CH}_4\) `8`%.
3. **Pneumatic Devices - Measured Bleed Rate in SCF (Tier 3)**:
   - *Facility*: Sonatrach HMD (Facility 4, South, Upstream).
   - *Process*: `pneumatic`.
   - *Inputs*: Device Count = `25`, Bleed Rate = `18.5` scf/hr, Gas \(\text{CH}_4\) = `88.0`%, Operating Hours = `8,760` hr/yr.
   - *Uncertainties*: Meter `2.5`%, Override \(\text{CH}_4\) `5`%.
4. **Pneumatic Devices - Metric Units (\(\text{m}^3/\text{hr}\)) (Tier 3)**:
   - *Facility*: GICA Chlef (Facility 3, Center, Midstream).
   - *Process*: `pneumatic`.
   - *Inputs*: Device Count = `15`, Bleed Rate = `0.85` \(\text{m}^3/\text{hr}\), Gas \(\text{CH}_4\) = `92.0`%, Operating Hours = `6,000` hr/yr.
   - *Uncertainties*: Meter `1.8`%, Override \(\text{CH}_4\) `4`%.
5. **Storage Tank - Working Losses (Tier 3, API Compendium §5.2)**:
   - *Facility*: Sonatrach HMD (Facility 4, South, Upstream).
   - *Process*: `tank_working`.
   - *Inputs*: Throughput = `50,000` bbl, Tank Type = `Crude Oil (> 10 bbl/d)`, GOR = `350` scf/bbl, Storage Temp = `75`°F, Separator Press = `65` psig, Gas \(\text{CH}_4\) = `72.0`%, Control Eff = `92.0`%.
   - *Uncertainties*: Meter `2.0`%, Override \(\text{CO}_2\) `5`%, \(\text{CH}_4\) `6`%.
6. **Storage Tank - Breathing Losses (Tier 3)**:
   - *Facility*: Tosyali DRI (Facility 1, West, Midstream).
   - *Process*: `tank_breathing`.
   - *Inputs*: Throughput = `25,000` bbl, Tank Type = `Condensate (> 10 bbl/d)`, GOR = `420` scf/bbl, Storage Temp = `85`°F, Gas \(\text{CH}_4\) = `68.0`%, Control Eff = `95.0`%.
   - *Uncertainties*: Meter `2.0`%, Override \(\text{CH}_4\) `7`%.
7. **Acid Gas Removal (AGR) with Sulfinol Solvent & Mcf/day (Tier 3)**:
   - *Facility*: Sonatrach HMD (Facility 4, South, Midstream).
   - *Process*: `agr`.
   - *Inputs*: Throughput = `12,000` Mcf/day, Solvent = `Sulfinol`, Inlet \(\text{CO}_2\) = `14.0`%, Outlet \(\text{CO}_2\) = `0.05`%, Gas \(\text{CH}_4\) = `84.0`%, Methane Slip Factor = `0.00095` mol/mol \(\text{CO}_2\), Flash Gas Recycled = true, Offgas to Flare = true (98%).
   - *Uncertainties*: Meter `1.5`%, GC `0.8`%, Override \(\text{CO}_2\) `3`%, \(\text{CH}_4\) `5`%.
8. **Glycol Dehydrator with Metric Pump Unit (L/hr) & Stripping Gas (Tier 3)**:
   - *Facility*: GICA Chlef (Facility 3, Center, Midstream).
   - *Process*: `dehydrator`.
   - *Inputs*: Throughput = `45` MMscf/yr, Glycol Pump Rate = `35` L/hr (`lph`), Gas \(\text{CH}_4\) = `86.5`%, Flash Tank = true (95% Condenser), Still Column = 99% Thermal Oxidizer, Stripping Gas = `15` scf/gal.
   - *Uncertainties*: Meter `2.0`%, Override \(\text{CH}_4\) `6`%.
9. **Pipeline Blowdown with \(\text{ft}^3\) Units & Elevated Temperature (Tier 3)**:
   - *Facility*: Tosyali DRI (Facility 1, West, Upstream).
   - *Process*: `blowdown`.
   - *Inputs*: Volume = `15,000` \(\text{ft}^3\), Pressure = `600` psig, Events = `5`, Gas \(\text{CH}_4\) = `89.0`%, \(\text{CO}_2\) = `1.8`%, Operating Temp = `95`°F, Flare Control = `98.0`%.
   - *Uncertainties*: Meter `1.2`%, Override \(\text{CO}_2\) `4`%, \(\text{CH}_4\) `5`%.

---

### Group B: Tier 1 Default Factor Scenarios (Uncovered Fuels & Equipment)
10. **Propane (Liquid) - Mobile/Stationary Combustion (Tier 1)**:
    - *Facility*: Tosyali DRI (Facility 1, West, Downstream).
    - *Fuel*: `Propane (Liquid)` (code `LPG_Liq`), Quantity = `45,000` gal, Factor Source = `default`.
11. **Kerosene - Direct Combustion (Tier 1)**:
    - *Facility*: Sonatrach HMD (Facility 4, South, Upstream).
    - *Fuel*: `Kerosene`, Quantity = `18,000` gal, Factor Source = `default`.
12. **Residual Fuel Oil (No. 6) - Heavy Industrial Boiler (Tier 1)**:
    - *Facility*: GICA Chlef (Facility 3, Center, Midstream).
    - *Fuel*: `Residual Fuel Oil (No. 6)`, Quantity = `650` bbl, Factor Source = `default`.
13. **Anthracite Coal - Solid Fuel Combustion (Tier 1)**:
    - *Facility*: GICA Chlef (Facility 3, Center, Midstream).
    - *Fuel*: `Anthracite Coal`, Quantity = `120` ton, Factor Source = `default`.
14. **Natural Gas - Gas Turbine with Default High-Efficiency Factors (Tier 1)**:
    - *Facility*: Tosyali DRI (Facility 1, West, Downstream).
    - *Fuel*: `Natural Gas - Turbine`, Quantity = `1,200,000` scf, Factor Source = `default`.
15. **Liquids Unloading - Plunger Lift Default Factor (Tier 1)**:
    - *Facility*: Sonatrach HMD (Facility 4, South, Upstream).
    - *Process*: `unloading`.
    - *Fuel / Source*: `Liquids Unloading - Plunger Lift`, Quantity = `24` events, Factor Source = `default`.

---

## 3. Necessary Engine & Factor Synchronizations
To guarantee flawless UI-to-backend parity and eliminate missing factor exceptions:
1. **Backend `new/server/emission_factors.py`**:
   - Add frontend factor keys:
     - `Liquids Unloading - Plunger Lift` & `Liquids Unloading - Non-Plunger`
     - `Propane (Liquid)`
     - `Natural Gas - Turbine`
     - `Natural Gas - 2-Stroke Lean Burn Engine`
     - `Natural Gas - Heater/Boiler`
     - `Completion - Gas Well (No Flaring)` & `Workover - Gas Well (No Flaring)`
     - `Tank - Working Losses (Oil)` & `Tank - Breathing Losses (Oil)`
     - `Loading - Crude Oil (Tank Truck)` & `Loading - Crude Oil (Marine Vessel)`
     - `Wastewater - Oil/Water Separator`
2. **Backend `new/server/calculations/dispatcher.py`**:
   - In `completions`, support `calc_method` as well as `comp_method`, and handle `events` multiplier.
   - In `tank_working` / `tank_breathing`, pass `process_type=process_type` to allow non-flashing working/breathing logic.
3. **Backend `new/server/calculations/vented.py`**:
   - In `CompletionFlowbackCalculator.calculate`, support `method in ["gor", "gor_liquid"]`, `flowback_rate` in Mcf/hr or Mscf/day, and `events` multiplier.
4. **Restart Flask Backend**:
   - Safely terminate existing Flask background task and restart `python -u app.py` on port 5000 so the running server picks up the enhanced factor tables and calculation handlers.

---

## 4. UI Audit of Tables Below Scope 1 Emissions
In `Scope1Form.jsx`, verify the dynamic activity table below the form:
- Columns: `Year`, `Activity`, `Region`, `Division`, `Field`, `Emission Source`, `Equipment ID`, `Process`, `Activity/Fuel`, `Factor Type`, `Quantity`, `CO₂ (t)`, `CH₄ (t)`, `N₂O (t)`, `Total (tCO₂e)`, `CO₂ 1σ`, `CH₄ 1σ`, `N₂O 1σ`, `CO₂ 95%CI`, `CH₄ 95%CI`, `N₂O 95%CI`, `Actions`.
- Verify every cell renders valid numeric strings (no `NaN`, `undefined`, or `-` where values are expected).
- Click "Inspect" button to open `CalculationDetails` modal:
  - Step 1: Operational Activity & Facility Scope.
  - Step 2: Emission Factor Application & Species Mass.
  - Step 3: Global Warming Potential (GWP AR5) Weighting.
  - Step 4: Quality Assurance & Uncertainty Profile.

---

## 5. Maker-Checker Batch Approval & KPI Reconciliation
1. **Maker-Checker Batch Approval**:
   - Trigger batch approval via API `/api/emissions/verify-all` or direct DB update for Scope 1 records created in this session.
   - Assert zero unapproved / draft records remain in `ghg_app.db`.
2. **Re-Audit Dashboard KPIs**:
   - Check Hero Gross Emissions (tCO₂e) at GWP-100 and GWP-20.
   - Check regional breakdown for `West`, `Center`, and `South`.
   - Check detailed breakdown by gas (\(\text{CO}_2, \text{CH}_4, \text{N}_2\text{O}\)) and activity category.
3. **Re-Audit Carbon Intensity & Methane Intensity**:
   - Verify CBAM intensity per tonne of clinker/steel.
   - Verify Methane Intensity KPI (\(\text{kg CH}_4/\text{BOE}\)) dynamically reflecting all new methane sources.

---

## 6. Verification Plan

### Automated Playwright Tests
- Create dedicated end-to-end test suite: `new/client/e2e/test_scope1_tier1_tier3_advanced.spec.js`.
- Execute all 15 scenarios, submitting each through the UI or verified API pipeline, verifying the live DOM results, database persistence, table columns, and uncertainty propagation.
- Capture full-page visual screenshots to `test_results/screenshots/`.
- Run Playwright test:
  ```powershell
  npx playwright test e2e/test_scope1_tier1_tier3_advanced.spec.js --project=chromium
  ```

### Database Parity Verification
- Run automated SQLite verification script asserting:
  - Total records \(\ge 2,540\).
  - Facility 1 (West) \(\ge 360\), Facility 3 (Center) \(\ge 360\), Facility 4 (South) \(\ge 360\).
  - Status = `Verified` for 100% of records.
  - Zero `NULL` or `NaN` values in `co2_emissions`, `ch4_emissions`, `n2o_emissions`, `co2e_total`.
