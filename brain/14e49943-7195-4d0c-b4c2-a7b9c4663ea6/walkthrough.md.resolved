# Walkthrough - Activity Log Dashboard

I have completely transformed the Emissions page into an "Activities Log" dashboard, replicating the design you provided.

## Key Changes

### 1. New Activity Log Table
- **Unified View**: All emission data (Fuel, Clinker, Electricity) is now displayed in a single, high-density table.
- **Detailed Columns**: The table now includes:
    - Group Name & Equipment ID
    - Emission Factor Source & Value
    - Uncertainty %
    - Status (e.g. Verified)
- **Total CO2e Footer**: A distinct footer row displays the total calculated CO2e emissions.

### 2. "New Activity Entry" Form
- **Grid Layout**: The form is now a compact 4-row grid, allowing for rapid data entry.
- **Context Fields**: Added fields for **Group Name**, **Equipment ID**, and **Uncertainty**.
- **Dynamic Process Switching**: The "Process Type" dropdown dynamically changes the form fields (e.g., hiding Fuel options when "Electricity" is selected).

### 3. Backend Enhancements
- Added `group_name`, `equipment_identifier`, and `uncertainty_percentage` to the database schema to support the new form fields.
