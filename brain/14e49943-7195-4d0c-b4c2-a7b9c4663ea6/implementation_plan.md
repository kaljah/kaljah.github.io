# Implementation Plan - Activity Log Dashboard Replica

## Goal
Replicate the "Emissions Activity Log" dashboard from the provided design reference. This involves a unified form layout ("New Activity Entry") and a consolidated data table ("Activity Log").

## User Review Required
> [!IMPORTANT]
> This change introduces new fields (`Group`, `Equipment`, `Uncertainty`) that will require a database migration. Existing records will have empty values for these fields.

## Proposed Changes

### Backend
#### [MODIFY] [backend/emissions/models.py](file:///c:/Users/samsung/Desktop/cement/backend/emissions/models.py)
*   Update `ActivityData` (abstract model) to include:
    *   `group_name` (CharField, max_length=100, blank=True)
    *   `equipment_identifier` (CharField, max_length=100, blank=True)
    *   `uncertainty_percentage` (DecimalField, default=0.0)

#### [MODIFY] [backend/emissions/serializers.py](file:///c:/Users/samsung/Desktop/cement/backend/emissions/serializers.py)
*   Add new fields to serializers (via `__all__`).

### Frontend

#### [MODIFY] [src/components/emissions/ProtocolCalculator.tsx](file:///c:/Users/samsung/Desktop/cement/frontend/src/components/emissions/ProtocolCalculator.tsx)
*   **Redesign Layout**: 
    *   Switch to a 4-row grid layout matching the screenshot.
    *   **Row 1**: Facility | Year | Month | Group | Equipment
    *   **Row 2**: Process Type (Select) | Fuel Type (Select) | HHV (Auto) | Specific Factors (Toggle)
    *   **Row 3**: Quantity | Unit
    *   **Row 4**: Uncertainty
*   **Process Type Logic**: The "Process Type" dropdown will now be the primary switcher (Stationary Combustion, Clinker, Electricity) instead of clear tabs.

#### [MODIFY] [src/components/emissions/EmissionList.tsx](file:///c:/Users/samsung/Desktop/cement/frontend/src/components/emissions/EmissionList.tsx)
*   **Unified Table**: Flatten all API responses into a single list of rows.
*   **Columns**: Facility | Year | Month | Group | Equipment | Process | Activity | EF | Source | CO2 | Total CO2e | Uncertainty | Status | Actions.
*   **Footer**: Add floating "Total CO2e" badge.

## Verification Plan
1.  **Form Layout**: Verify the form matches the screenshot's grid density and field order.
2.  **Data Persistence**: Verify Group/Equipment fields are saved to the backend.
3.  **Table**: Verify all emission types (Scope 1 & 2) appear in the single table.
