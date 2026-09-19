# Implementation Plan - Auto-Create Facilities from CSV

This plan addresses the user requirement to automatically create facilities when they are referenced in CSV imports (Emission Sources or Production Data) but do not exist in the system.

## User Review Required
> [!NOTE]
> I will implement this logic on the **frontend**. When parsing the CSV, if a facility name is not found in the loaded list, the script will first call the `create facility` API, get the new ID, and then proceed with the original record creation.

## Proposed Changes

### Frontend
#### [MODIFY] [manage-data.html](file:///C:/Users/samsung/Desktop/h/public/manage-data.html)
- Update `importSourcesCSV` function:
    - Check if facility exists.
    - If not, `await fetch('/api/facilities', ...)` to create it.
- Update `importProductionCSV` function:
    - Apply similar logic.

#### [MODIFY] [emissions-calc.js](file:///C:/Users/samsung/Desktop/h/public/emissions-calc.js)
- Locate the CSV import logic (likely event listener on `csv-upload`).
- Update parsing loop:
    - **Facilities**: Check/Create if missing.
    - **Sources**: For "Group/Equipment" columns, check/create `emission_sources` if missing (linking to the facility).
    - Map fields: `Facility`, `Group` (Source Name), `Equipment`, `Process`, `Fuel` to create a Basic Source if needed.

## Verification Plan
### Manual Verification
1.  Create a CSV for Emission Sources with a **NEW** facility name.
2.  Import the CSV.
3.  Verify:
    - The Facility is created.
    - The Emission Source is created and linked to the new Facility.
