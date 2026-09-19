# Correcting Organizational Hierarchy & Syncing Data

The user identified incorrect Activity-Division mappings. This plan corrects those mappings globally and ensures existing database records are updated to match.

## User Review Required

> [!IMPORTANT]
> This change will update existing "Facility/Region" records in the database. Any record with an old division (e.g., "Oil" or "Gas" under EP) will be migrated to the new mapping if possible, or may require manual adjustment if the mapping is ambiguous.

## Proposed Changes

### [Frontend] Hierarchy Correction

#### [MODIFY] [ManageData.jsx](file:///c:/Users/samsung/Desktop/h/new/client/src/pages/ManageData.jsx)
- Update `HIERARCHY` constant to:
    - EP: Production, Association
    - LQS: LNG, LPG
    - RPC: Refining, Petrochemicals
    - TRC: TRC
- Ensure `ACTIVITY_MAP` and other UI references reflect the user's naming convention.

#### [MODIFY] [BulkImportModal.jsx](file:///c:/Users/samsung/Desktop/h/new/client/src/components/BulkImportModal.jsx)
- Update `HIERARCHY` constant to match `ManageData.jsx`.
- Update `downloadTemplate` logic to use the new sample data (Production/Association instead of Oil/Gas).

### [Backend] Data Synchronization

#### [NEW] [Sync Hierarchy Script](file:///c:/Users/samsung/Desktop/h/sync_hierarchy.py) [DELETE]
- A one-time script (or temporary route/task) to scan existing `Region` (Facilities) and `EmissionSource` records.
- Rename Divisions:
    - `Oil` -> `Production`
    - `Gas` -> `Association` (or as per user specific intent if disambiguation is needed)
    - `Transport` -> `TRC`
- Update Activity names if necessary.

---
The user reported that the Activity, Division, and Region dropdowns on the Manage Data page (Production tab) don't match the rest of the tool. Additionally, the field order in Region Management needs to be updated to match the requested flow: Activity -> Division -> Region.

## User Review Required

> [!IMPORTANT]
> I will be implementing a **Bulk CSV Import** feature. Users will need to follow a specific CSV template to ensure data (Regions, Equipment, Activity) is mapped correctly.

> [!NOTE]
> The automated calculation will use the **latest available emission factors** in the database for each imported record. If a factor is missing, the record will be flagged for review.

## Proposed Changes

### [ManageData.jsx](file:///c:/Users/samsung/Desktop/h/new/client/src/pages/ManageData.jsx)

#### [NEW] [BulkImportModal.jsx](file:///c:/Users/samsung/Desktop/h/new/client/src/components/BulkImportModal.jsx)
- Added `downloadTemplate` function to provide users with example CSV structures with all process types.
- **Expanded Schema**: Updated templates and preview tables to include mandatory fields: **Activity, Division, Region, Field, Year, Month, Quantity (Amount), and Unit**.
- **Engineering Parameters**: Added optional fields for high-accuracy calculations:
    - **Flaring**: Flare Type (Elevated/Enclosed), CH4 %
    - **Combustion**: HHV, Combustion Efficiency
    - **Equipment**: Device Count, Operating Hours
    - **Tanks**: GOR, API Gravity
- **Validation Logic**: Added logic to scan mapped data for invalid fuel/process types and organizational hierarchy mismatches.
- **Reference UI**: Added a "System Identifiers" toggle to show valid names for CSV preparation.

### [General Components]

#### [MODIFY] [BulkImportModal.jsx](file:///c:/Users/samsung/Desktop/h/new/client/src/components/BulkImportModal.jsx)
- Correct the default import endpoint from `/import` to `/emissions/import` to match the backend blueprint.
- Ensure all other bulk endpoints (`/sources/bulk-import`, `/scope2/bulk-import`, etc.) are correctly routed.

### [Calculation Engine Fixes]
#### [MODIFY] [BulkImportModal.css](file:///c:/Users/samsung/Desktop/h/new/client/src/components/BulkImportModal.css)
- Styled validation error states (red highlights) and the reference guide container.
- A reusable modal for uploading and parsing CSV files.
- Visual mapping of CSV columns to database fields.
- Preview of records before final submission.

#### [MODIFY] [ManageData.jsx](file:///c:/Users/samsung/Desktop/h/new/client/src/pages/ManageData.jsx)
- Add "Import CSV" buttons to **Sources** and **Activity Data** tabs.
- Integrate the `BulkImportModal` for both inventory and emissions data.

#### [MODIFY] [managedata.py](file:///c:/Users/samsung/Desktop/h/new/server/routes/managedata.py)
- Add `/api/sources/bulk-import` endpoint to handle bulk equipment inventory uploads.

- **Bulk Import Calculation Support**:
    - [x] Update `import_emissions` in `server/routes/emissions.py` to resolve facility names.
    - [x] Modify `compute_emissions` in `server/calculations/legacy_engine.py` to support flat payloads.
    - [x] Implement `/api/scope2/bulk-import` and `/api/scope3/bulk-import` for automated calculations.
    - [x] Integrate `BulkImportModal` into `Scope1Form`, `Scope2Form`, and `Scope3Form`.
- **UI Performance**:

#### [MODIFY] [emissions.py](file:///c:/Users/samsung/Desktop/h/new/server/routes/emissions.py)
- Update `import_emissions` to lookup `facility_id` by name if the CSV provides a string.
- Ensure the payload passed to `compute_emissions` matches the structure expected by Tier 3 calculators.

#### [MODIFY] [legacy_engine.py](file:///c:/Users/samsung/Desktop/h/new/server/calculations/legacy_engine.py)
- Update `compute_emissions` to merge root payload into `inputs` if `calc_inputs` is missing, allowing flat CSV data to drive engineering calculations.

### [Debug Support]

#### [MODIFY] [emissions.py](file:///c:/Users/samsung/Desktop/h/new/server/routes/emissions.py)
- Redirect all debug `print` statements to a file `import_debug.log` to capture backend context.

#### [MODIFY] [BulkImportModal.jsx](file:///c:/Users/samsung/Desktop/h/new/client/src/components/BulkImportModal.jsx)
- Enhance `handleImport` error handling to correctly display the `details` array from the 400 response.

## Dashboard Summary and CORS Fixes

### [Backend] [dashboard.py](file:///c:/Users/samsung/Desktop/h/new/server/routes/dashboard.py)

#### [MODIFY] [dashboard.py](file:///c:/Users/samsung/Desktop/h/new/server/routes/dashboard.py)
Fix `KeyError` in `get_dashboard_summary` where `year` was used as a key instead of `(year, fid)`.

### [Backend] [app.py](file:///c:/Users/samsung/Desktop/h/new/server/app.py)

#### [MODIFY] [app.py](file:///c:/Users/samsung/Desktop/h/new/server/app.py)
Ensure CORS headers are appended to all responses, including error responses, for better debugging in the frontend.

## ReferenceData and Metadata Fixes

### [Frontend] [ReferenceData.jsx](file:///c:/Users/samsung/Desktop/h/new/client/src/pages/ReferenceData.jsx)

#### [MODIFY] [ReferenceData.jsx](file:///c:/Users/samsung/Desktop/h/new/client/src/pages/ReferenceData.jsx)
- Add optional chaining to `f.name.toLowerCase()` at line 69 to prevent `TypeError` if name is missing.

### [Backend] [data.py](file:///c:/Users/samsung/Desktop/h/new/server/routes/data.py)

#### [MODIFY] [data.py](file:///c:/Users/samsung/Desktop/h/new/server/routes/data.py)
- Update `add_production` and `get_production` to include `activity`, `division`, and `field` fields.

### [Frontend] [ManageData.jsx](file:///c:/Users/samsung/Desktop/h/new/client/src/pages/ManageData.jsx)

#### [MODIFY] [ManageData.jsx](file:///c:/Users/samsung/Desktop/h/new/client/src/pages/ManageData.jsx)
- Update `metadata` state to include `is_tcfd_aligned` and `notes`.
- Add UI inputs for these fields in the "Reporting Metadata" tab.

---

## ISO 14064-1 Uncertainty Implementation

### [Backend] [dashboard.py](file:///c:/Users/samsung/Desktop/h/new/server/routes/dashboard.py)

#### [NEW] [/api/dashboard/uncertainty]
Implement a route to calculate rolled-up uncertainty for the entire inventory:
- **Emission Factor Uncertainty Quantification**:
    - If `uncertainty` is explicitly stored in the `Emission` or `EmissionFactor` record, use it.
    - Otherwise, derive based on `calc_method`:
        - **Tier 3 / Direct Measurement**: ±2-5%
        - **Tier 2 / Regional Factors**: ±5-15%
        - **Tier 1 / IPCC Defaults**: ±30-50%
- **Aggregation Logic (ISO 14064-1 / IPCC)**:
    - Group emissions by process type (Stationary Combustion, Flaring, etc.).
    - For each group, calculate uncertainty: $U_{group} = \frac{\sqrt{\sum (E_i \cdot U_i)^2}}{\sum E_i}$
    - Total inventory uncertainty: $U_{total} = \frac{\sqrt{\sum (U_{group} \cdot E_{group})^2}}{\sum E_{group}}$

### [Frontend] [UncertaintyAssessment.jsx](file:///c:/Users/samsung/Desktop/h/new/client/src/pages/UncertaintyAssessment.jsx)

#### [MODIFY] [UncertaintyAssessment.jsx](file:///c:/Users/samsung/Desktop/h/new/client/src/pages/UncertaintyAssessment.jsx)
- Remove hardcoded example data.
- Fetch calculated uncertainty from the new API.
- Remove ISO 14064-1 text blocks as requested.
- Display a dynamic grid of sources with their actual calculated uncertainty contributions.

### [Frontend] [Dashboard.jsx](file:///c:/Users/samsung/Desktop/h/new/client/src/pages/Dashboard.jsx)
- Update the `uncertainty` card to fetch dynamic data from `/api/dashboard/uncertainty` instead of using a hardcoded placeholder.
- Ensure the Dashboard properly handles empty states or error responses from current `/emissions` endpoint.

### [Frontend/Backend] EF Uncertainty Calculation Enhancement

#### [Backend] [models.py](file:///c:/Users/samsung/Desktop/h/new/server/models.py) & [custom_factors.py](file:///c:/Users/samsung/Desktop/h/new/server/routes/custom_factors.py)
- Ensure the `CustomFactor` model and its CRUD routes support saving detailed uncertainty metadata (e.g., source of uncertainty, instrument precision).

#### [Frontend] [ManageData.jsx](file:///c:/Users/samsung/Desktop/h/new/client/src/pages/ManageData.jsx)
- Add an "Uncertainty Workbench" to the Custom Factors tab.
- Users can input:
    - Flow Meter Precision (±%)
    - Lab Analysis Precision (±%)
    - Global warming potential uncertainty
- Output: Calculated EF Uncertainty using SRSS, which is then saved to the factor.

---

---

## Unified Emissions Database & Reporting

### [Backend] [emissions.py](file:///c:/Users/samsung/Desktop/h/new/server/routes/emissions.py)

#### [MODIFY] [emissions.py](file:///c:/Users/samsung/Desktop/h/new/server/routes/emissions.py)
Update the `get_emissions` route to support a `scope` filter:
- If `scope=all` or unspecified, it should perform a unified query across `Emission` (Scope 1), `Scope2Emission`, and `Scope3Emission`.
- Since these models have different fields, the response needs to be normalized into a standard format:
    - `scope`: 1, 2, or 3
    - `id`: Unique record ID
    - `date`: Combined month/year
    - `category`: Process type (S1), Source type (S2), or Category (S3)
    - `fuel_source`: Fuel (S1), Grid (S2), or Sub-category (S3)
    - `amount`: Quantity
    - `co2e`: Total CO2e
- Support filtering by `scope`, `year`, `month`, `facility_id`, and `process_type`.

### [Frontend] [Reports.jsx](file:///c:/Users/samsung/Desktop/h/new/client/src/pages/Reports.jsx)

#### [MODIFY] [Reports.jsx](file:///c:/Users/samsung/Desktop/h/new/client/src/pages/Reports.jsx)
- **Scope Filter**: Add a Scope dropdown (All, Scope 1, Scope 2, Scope 3).
- **Dynamic Table Columns**: Update the table rendering to handle the normalized emission data.
- **Enhanced Search**: Ensure the search term filters across all scopes.
- **Improved Filtering**: Update `fetchEmissions` to include the `scope` parameter in API requests.

## Verification Plan

### Automated Tests
- Verify that selecting "Scope 2" only shows electricity/steam records.
- Verify that "All Scopes" correctly merges records from all three tables.
- Verify pagination works correctly across the unified dataset.

### Manual Verification
- Check if the "Total (t)" column in the reports table matches the sum of individual gas columns where applicable.
- Ensure Scope 2/3 rows display "N/A" or appropriate placeholders for fields they don't have (like Fuel Oil).
