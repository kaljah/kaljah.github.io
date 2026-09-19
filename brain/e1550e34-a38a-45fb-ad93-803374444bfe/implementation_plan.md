# Refactor Facility to Region Hierarchy

## Goal Description
Rename "Facilities" to "Region" across the application and implement a hierarchical data structure: **Activity -> Division -> Region -> Field**. This involves updating the database schema, backend API, and User Interfaces in both "Manage Data" and "Emissions Calculator".

## Proposed Changes

### Database Schema
#### [MODIFY] `server.js`
- Add `field` column to `facilities` table via migration.
- `facilities` table will now effectively represent:
    - `activity`
    - `division`
    - `name` (Region)
    - `field`
    - `location` (Keep as auxiliary)

### Backend API
#### [MODIFY] `server.js`
- Update `POST /api/facilities` to accept and save `field`, `activity`, `division`.
- Ensure `GET /api/facilities` returns these columns (already covered by `SELECT *`).

### Frontend UI

#### [MODIFY] [manage-data.html](file:///c:/Users/samsung/Desktop/h/public/manage-data.html)
- **Rename**: "Facilities" tab/labels to "Region Management" / "Regions".
- **Form Update**:
    - Reorder inputs:
        1.  **Activity** (Input)
        2.  **Division** (Input)
        3.  **Region** (Renamed from Facility Name)
        4.  **Field** (New Input)
        5.  Location / Boundary Notes (Below)
- **Table/List Update**: Display the new columns in the list of active regions.

#### [MODIFY] [emissions-calculator.html](file:///c:/Users/samsung/Desktop/h/public/emissions-calculator.html)
- **Rename**: "Facility" dropdown label to "Region".
- **Order**: Ensure the "Region" selection is prominent.
- *Note*: Since Activity/Division/Field are properties of the selected Region, selecting the "Region" (Facility ID) implicitly selects them. I will update the UI to reflect this terminology.

#### [MODIFY] [manage-data.html](file:///c:/Users/samsung/Desktop/h/public/manage-data.html) (Script Section / attributes)
- Ensure JS functions (`saveFacility`) allow collecting and sending new fields.

## Verification Plan
### Manual Verification
1.  **Manage Data**:
    - Go to "Manage Data" -> "Regions".
    - Create a new entry with Activity="Upstream", Division="West", Region="Permian", Field="Alpha".
    - Save and Verify it appears in the list.
2.  **Emissions Calculator**:
    - Go to Calculator.
    - Verify "Facility" label is now "Region".
    - Select the newly created "Permian" region.
    - Add a record.
3.  **Database**:
    - Verify data is saved in `facilities` table with correct values.
