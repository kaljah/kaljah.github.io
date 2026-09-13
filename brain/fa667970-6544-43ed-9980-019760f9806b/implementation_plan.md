# Organizational Boundaries Implementation Plan

This plan addresses the "Limited Scope Definition" gap in ISO 14064-1 compliance by allowing users to declare their consolidation approach and document facility-specific boundaries.

## Proposed Changes

### Backend (server.js)
*   [MODIFY] `server.js`:
    *   Add `consolidationApproach` column to `users` table.
    *   Add `boundary_notes` column to `facilities` table.
    *   Update `PUT /api/users/:id` to save `consolidationApproach`.
    *   Update `POST /api/facilities` to save `boundary_notes`.
    *   Update `GET /api/facilities` to return `boundary_notes`.

### Frontend (Settings)
*   [MODIFY] `public/settings.html`:
    *   Add "Inventory Consolidation Approach" dropdown to the "Reporting Prefs" tab.
*   [MODIFY] `public/settings.js`:
    *   Add logic to fetch current consolidation approach on load.
    *   Add logic to include consolidation approach in the save request.

### Frontend (Management)
*   [MODIFY] `public/manage-data.html`:
    *   Add "Boundary Notes" textarea to the "Add Facility" form.
    *   Update the facility list display to show boundary notes.
    *   Update inline JavaScript to handle the new field in `saveFacility` and `loadFacilities`.

## Verification Plan

### Manual Verification
1.  **Settings**:
    *   Navigate to Settings -> Reporting Prefs.
    *   Change "Inventory Consolidation Approach" to "Equity Share" and save.
    *   Refresh page/dashboard and verify setting persists.
2.  **Facilities**:
    *   Navigate to Manage Data -> Facilities.
    *   Add a new facility with boundary notes (e.g., "Owned 100% - Operational Control").
    *   Verify the facility appears in the list with its notes.
    *   Check API responses to ensure data is correctly stored in SQLite.
