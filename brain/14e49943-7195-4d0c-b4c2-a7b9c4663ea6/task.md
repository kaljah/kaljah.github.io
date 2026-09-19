# Tasks

- [x] Analyze current facility page implementation <!-- id: 0 -->
- [x] Analyze backend facility API and models <!-- id: 1 -->
- [x] Create implementation plan <!-- id: 2 -->
- [x] Implement frontend types (`Facility`, `FacilityType`) <!-- id: 7 -->
- [x] Implement `FacilityList` component <!-- id: 8 -->
- [x] Implement `FacilityForm` component <!-- id: 9 -->
- [x] integrate components into `FacilitiesPage` <!-- id: 10 -->
- [x] Verify functionality <!-- id: 6 -->
- [x] Debug "Create First Facility" button issue <!-- id: 11 -->

## Emission Data Page (Completed Initial Version)
- [x] Create Types for `FuelConsumption` and `ClinkerProduction` <!-- id: 12 -->
- [x] Implement `EmissionList` component <!-- id: 13 -->
- [x] Implement `EmissionForm` component (Tabs for Fuel/Clinker) <!-- id: 14 -->
- [x] Integrate into `EmissionsPage` <!-- id: 15 -->
- [x] Verify functionality <!-- id: 16 -->

## WBCSD Protocol Upgrade (Completed)
- [x] Create Implementation Plan for Protocol Upgrade <!-- id: 17 -->
- [x] **Backend**: Add `ElectricityConsumption` model (Scope 2) <!-- id: 18 -->
- [x] **Backend**: Update `ClinkerProduction` (add MgO non-carbonate) <!-- id: 19 -->
- [x] **Backend**: Update `FuelConsumption` (add Biomass %) <!-- id: 20 -->
- [x] **Backend**: Add `RawMaterialConsumption` (Method B) <!-- id: 21 -->
- [x] **Backend**: Implement calculation signals/logic <!-- id: 22 -->
- [x] **Frontend**: Create new `EmissionCalculator` component (Wizard/Accordion style) <!-- id: 23 -->
- [x] **Frontend**: Integrate all new data types <!-- id: 24 -->
- [x] Verify WBCSD Compliance <!-- id: 25 -->

## UI/UX Modernization & Functional Enhancement (Completed)
- [x] Create Implementation Plan <!-- id: 26 -->
- [x] **Frontend**: Create `constants/emissionFactors.ts` (Default values) <!-- id: 27 -->
- [x] **Frontend**: Implement Unit Conversion Logic (UI -> Backend units) <!-- id: 28 -->
- [x] **Frontend**: Redesign `ProtocolCalculator` (Modern UI + Unit Selectors + Auto-fill) <!-- id: 29 -->
- [x] **Frontend**: Update `EmissionsPage` to show Calculator and List simultaneously <!-- id: 30 -->
- [x] **Refinement**: Polish styling and interactivity <!-- id: 31 -->

## Activity Log Dashboard Replica (Completed)
- [x] **Backend**: Add `group_name`, `equipment_identifier`, `uncertainty` to schema <!-- id: 32 -->
- [x] **Backend**: Migration <!-- id: 33 -->
- [x] **Frontend**: Update `ProtocolCalculator` to match "New Activity Entry" Form (Row layout) <!-- id: 34 -->
- [x] **Frontend**: Refactor `EmissionList` to a Unified "Activity Log" Table <!-- id: 35 -->
- [x] **Frontend**: Integrate Filters and Total CO2e Footer <!-- id: 36 -->
