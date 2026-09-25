# Walkthrough — API Compendium 2021 Gap Remediation

All 8 gaps and discrepancies identified in the **API Compendium 2021 End-to-End Audit Report** (`api_compendium_2021_audit_report.md`) have been implemented, verified, and compiled.

---

## 1. Summary of Changes

### GAP-01: Chemical Production (Process CO₂)
- **New Component:** Created [`ChemicalProductionForm.jsx`](file:///c:/Users/samsung/Desktop/H2/new/client/src/components/scope1/ChemicalProductionForm.jsx) for the 6 API Table 6-167 petrochemical products:
  - Acrylonitrile ($1.00\text{ t CO}_2\text{/t}$)
  - Carbon Black ($2.63\text{ t CO}_2\text{/t}$)
  - Ethylene ($0.77\text{ t CO}_2\text{/t}$)
  - Ethylene Dichloride ($0.041\text{ t CO}_2\text{/t}$)
  - Ethylene Oxide ($0.46\text{ t CO}_2\text{/t}$)
  - Methanol ($0.67\text{ t CO}_2\text{/t}$, $2.3\text{ kg CH}_4\text{/t}$)
- **Factor Resolution:** Added factors to [`EmissionFactors.js`](file:///c:/Users/samsung/Desktop/H2/new/client/src/utils/EmissionFactors.js) and merged `CHEMICAL_PRODUCTION_FACTORS` into `ALL_EMISSION_FACTORS` in [`emission_factors_api2021.py`](file:///c:/Users/samsung/Desktop/H2/new/server/emission_factors_api2021.py).
- **UI Integration:** Registered `chemical_production` under the Downstream segment in `PROCESS_GROUPS`.

### GAP-02 & GAP-03: Nitric Acid & Adipic Acid Production (Process N₂O)
- **New Components:**
  - [`NitricAcidForm.jsx`](file:///c:/Users/samsung/Desktop/H2/new/client/src/components/scope1/NitricAcidForm.jsx): Options for Non-Selective Catalytic Reduction (NSCR: $2.0\text{ kg N}_2\text{O/t}$) vs. Uncontrolled ($9.0\text{ kg N}_2\text{O/t}$).
  - [`AdipicAcidForm.jsx`](file:///c:/Users/samsung/Desktop/H2/new/client/src/components/scope1/AdipicAcidForm.jsx): Options for Thermal Abatement ($13.0\text{ kg/t}$), Catalytic Abatement ($53.0\text{ kg/t}$), and Uncontrolled ($300.0\text{ kg/t}$).
- **Server Support:** Merged `N2O_PRODUCTION_FACTORS` into `ALL_EMISSION_FACTORS` and mapped in `_lookup_api_factor()`.
- **UI Integration:** Registered in `PROCESS_TYPES` and `PROCESS_GROUPS` under Downstream.

### GAP-04: Asphalt Blowing Missing from UI & Dispatcher
- **New Component:** [`AsphaltBlowingForm.jsx`](file:///c:/Users/samsung/Desktop/H2/new/client/src/components/scope1/AsphaltBlowingForm.jsx) with direct throughput inputs in tonnes, short tons, or kg.
- **Dispatcher & Categories:** Registered `"asphalt_blowing"` and `"asphalt"` in [`dispatcher.py`](file:///c:/Users/samsung/Desktop/H2/new/server/calculations/dispatcher.py) and [`process_categories.py`](file:///c:/Users/samsung/Desktop/H2/new/server/process_categories.py) (including `NON_COMBUSTION_PROCESSES`).

### GAP-05: Storage Tank Flashing Tier 1 Default Factor Mismatch
- **Root Cause Fixed:** Client and server now share the exact factor name `"Tank - Flash Emissions (Oil)"`.
- **Factor Value Updated:** Changed default methane factor from $0.15\text{ kg/bbl}$ to **$0.193\text{ kg CH}_4\text{/bbl}$** (API Table 6-4 / Table 5-16 for large crude oil tanks $>10\text{ bbl/d}$).
- **Results:** 10,000 bbl in Tier 1 now yields **$1.93\text{ t CH}_4$** and **$54.16\text{ tCO}_2\text{e}$** (previously returned $0.00$).

### GAP-06: AGR & Dehydrator Tier 1 Form Mismatch (OGMP 2.0 Level 4/5)
- **Lock-down:** Removed "Default" and "Custom" buttons for `agr` and `dehydrator` in [`Scope1Form.jsx`](file:///c:/Users/samsung/Desktop/H2/new/client/src/components/Scope1Form.jsx), strictly locking them to "Specific" (Tier 3).
- **Compliance Badge:** Added an inline OGMP 2.0 blue informational banner explaining: *"OGMP 2.0 Level 4/5: Engineering model (Tier 3) required. No static Tier 1 factors exist for this process."*
- **Fallback Removed:** Removed AGR and Dehydrator from the generic `CombustionForm` fallback array.

### GAP-07: Result Modal Top Close Button Pointer Interception
- **CSS Fix:** Raised `.result-overlay` `z-index` from `1000` to `9999` in [`EmissionResult.css`](file:///c:/Users/samsung/Desktop/H2/new/client/src/components/EmissionResult.css).
- **Result:** Modal now floats above the sticky top bar (`z-index: 1100`), ensuring the top-right close button is immediately clickable.

### GAP-08: Database Region Column Persistence
- **ORM Update:** In [`emissions.py`](file:///c:/Users/samsung/Desktop/H2/new/server/routes/emissions.py), `Emission` instantiation now resolves `region=data.get("region") or (facility.region or facility.name)`.
- **Database Backfill:** Ran a migration script updating all 23 historical records in SQLite where `region IS NULL` to `"RNS"`. Current count of NULL regions in database is **0**.

---

## 2. Verification Results

### Automated Backend Tests
Ran `scratch/test_factors.py`:
```
=== 1. Checking Tank Flash Factor ===
Tank - Flash Emissions (Oil): ch4=0.193, co2=0.012 kg/bbl, unit=kg/bbl

=== 2. Checking Chemical Factors ===
Acrylonitrile: co2=1.0, ch4=0, unit=tonne CO₂/tonne product
Carbon Black: co2=2.63, ch4=0, unit=tonne CO₂/tonne product
Ethylene: co2=0.77, ch4=0, unit=tonne CO₂/tonne product
Ethylene Dichloride: co2=0.041, ch4=0, unit=tonne CO₂/tonne product
Ethylene Oxide: co2=0.46, ch4=0, unit=tonne CO₂/tonne product
Methanol: co2=0.67, ch4=0.0023, unit=tonne CO₂/tonne product

=== 3. Checking N2O Acid Factors ===
Nitric Acid - With NSCR: n2o=2.0, unit=kg N₂O/tonne product
Nitric Acid - Without NSCR: n2o=9.0, unit=kg N₂O/tonne product
Adipic Acid - Thermal Abatement: n2o=13.0, unit=kg N₂O/tonne product
Adipic Acid - Uncontrolled: n2o=300.0, unit=kg N₂O/tonne product

=== 4. Checking Asphalt Factor ===
Asphalt: co2=10.4326 kg/ton, ch4=0.02268 kg/ton

=== 5. Testing Dispatcher for Asphalt Blowing ===
Asphalt blowing result (1000 tonnes): 11.50 tCO2, 0.025 tCH4, totalCo2e = 12.20 tCO2e

=== 6. Testing Dispatcher for Tank Flash Tier 1 ===
Tank flash Tier 1 result (10,000 bbl): 1.93 tCH4, totalCo2e = 54.16 tCO2e

=== ALL SERVER TESTS PASSED! ===
```

### Database Persistence Check
```
Facilities: ID 13 -> RNS (Field GF)
Emissions with NULL region: 0
Updated: 23 records backfilled
```

### Frontend Production Build
```
✓ 3207 modules transformed.
✓ built in 33.44s with 0 errors.
```
