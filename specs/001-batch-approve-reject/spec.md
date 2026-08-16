# Feature Specification: Batch Approve/Reject Pending Records

## 1. Feature Description
**What are we building?**
We are making the "Approve All" and "Reject All" buttons on the Pending Review dashboard fully functional so that they successfully approve or reject all pending records across Scope 1, Scope 2, and Scope 3 simultaneously or per-tab.

**Why are we building it? (Business Value)**
Reviewers (Admins and Superusers) often need to process hundreds of pending records uploaded via bulk import or ERP sync. Clicking "Approve" individually on 850 records is impossible. Fully functional bulk action buttons save significant time and make the review workflow scalable.

## 2. User Scenarios & Acceptance Criteria

### Scenario 1: Bulk Approving Records
- **Given** I am an admin on the Pending Review dashboard with multiple pending records
- **When** I click the "Approve All" button for a specific scope
- **Then** the system should immediately approve all pending records for that scope
- **And** the UI should update to remove the approved records and update the notification counts

### Scenario 2: Bulk Rejecting Records
- **Given** I am an admin on the Pending Review dashboard with multiple pending records
- **When** I click the "Reject All" button and provide an optional reason
- **Then** the system should immediately reject (delete/dismiss) all pending records for that scope
- **And** the UI should update to remove those records from my queue

## 3. Functional Requirements
1. **ID Collection**: The UI must accurately gather the IDs of all currently pending records in the active scope when a bulk action is triggered.
2. **Batch API Integration**: The UI must send these IDs in a single request to the backend `approve/batch` or `reject/batch` API endpoints.
3. **State Management**: Upon a successful batch action, the frontend must immediately remove the processed items from the local state to avoid requiring a full page refresh.
4. **Error Handling**: If the batch operation fails (e.g., partial failure or network error), the system must show a user-friendly error toast message and retain the pending items in the UI.

## 4. Non-Functional Requirements
- **Performance**: The batch action should execute smoothly even if there are 1,000+ pending records.
- **Feedback**: The user should see a loading state (e.g., a spinner or disabled button) while the bulk action is processing.

## 5. Success Criteria
- **Efficiency Goal**: An admin can clear a backlog of 500 pending records in exactly 1 click and under 5 seconds.
- **Reliability Goal**: 100% of the IDs sent in the batch request are successfully processed by the backend.
- **UX Goal**: The user receives immediate visual confirmation of the successful batch action.

## 6. Assumptions & Dependencies
- **Assumptions**: 
  - The backend endpoints for `/approve/batch` and `/reject/batch` already exist and are properly configured to accept an array of IDs.
  - The user has the appropriate authorization to perform these actions.
- **Dependencies**: 
  - Relies on the frontend state management (React) to hold the lists of pending records.

## 7. Open Questions / Needs Clarification
*(None at this time)*
