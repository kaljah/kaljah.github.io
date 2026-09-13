# Auto-Create Facilities & Sources Walkthrough

I have enhanced the CSV import features across the application to automatically create missing entities (Facilities## Changes

### Navigation Updates

Updated the sidebar navigation across all pages to include the new "Methane Explorer" link with a "LIVE" badge. The following pages were updated:
- `mars-map.html` (Added navigation bar)
- `dashboard.html`
- `carbon-intensity.html`
- `emission-selection.html`
- `manage-data.html`
- `reports.html`
- `reference-data.html`
- `uncertainty.html`
- `audit-history.html`
- `emissions-calculator.html`

### Verification Results

#### Automated Tests
- Verified that `mars-map.html` contains the correct navigation structure.
- Verified that the "Methane Explorer" link is present and highlighted correctly on the `mars-map.html` page.
- Verified that other pages have the link pointing to `mars-map.html`.

#### Manual Verification
- Confirmed that `profile.html`, `settings.html`, and `audit-trail.html` use a different layout or header-only navigation and thus did not require the sidebar update.g a Sources CSV:
- Checks if the **Facility** column matches an existing facility.
- If not, it **automatically creates** the facility.
- Then creates the source linked to that facility.

### 2. Manage Data > Production Data
**Behavior**: When importing a Production CSV:
- Checks if the **Facility** column matches an existing facility.
- If not, it **automatically creates** the facility.
- Then adds the production record.

### 3. Calculations > Emissions Activity Log
**Behavior**: When importing an Activity CSV (using the new template with `Facility` column):
1.  **Auto-Create Facility**: Checks if the `Facility` column exists; creates it if valid and missing.
2.  **Auto-Create Source**: Checks if an equipment with the name in `Equipment` column exists in that facility.
    - If missing, it creates a new **Emission Source** in the inventory with:
        - Name: `Equipment` value
        - Type: `ProcessType` value
        - Fuel: `Fuel` value
        - Status: `Active`
3.  **Create Record**: Adds the emissions calculation record linked to the facility.

## templates
The **Emissions Activity Template** has been updated to include the `Facility` column as the first column:
`Facility,Date,Group,Equipment,ProcessType,SourceType,Amount,Unit,HHV`

## Testing the Logic
1.  Create a CSV for **Emissions Activity** with a completely new Facility name and Equipment name:
    ```csv
    Facility,Date,Group,Equipment,ProcessType,SourceType,Amount,Unit
    Galaxy Plant,2024-06-01,Power,Generator-X,combustion,Diesel,500,gal
    ```
2.  Import this file in **Calculations > Emissions Activity Log**.
3.  Verify:
    - "Galaxy Plant" appears in your **Facilities** list.
    - "Generator-X" appears in your **Emission Sources** inventory.
    - The record appears in the Activity Log grid.
