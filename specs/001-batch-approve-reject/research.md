# Research & Design Decisions: Batch Approve/Reject

## 1. Technical Context Verification
The current frontend code in `ManageData.jsx` already contains buttons for "Approve All" and "Reject All" that successfully map over the IDs for the given scope and make `POST` requests to `/emissions/approve/batch` and `/emissions/reject/batch`.

## 2. Identified Issues
- **State Management**: Currently, the code calls `fetchPendingEmissions()` after a successful bulk action. This requires a full network roundtrip to re-fetch the data. The requirement explicitly states we should "remove the processed items from the local state".
- **UX Feedback**: While the action is processing, there is no loading state. For large batches (e.g. 1000 items), the user might click the button multiple times because it doesn't disable or show a spinner.

## 3. Decisions
1. **Local State Mutation**: Instead of relying purely on `fetchPendingEmissions()`, we will update the React state (`setPendingEmissions`) to instantly clear the array for the processed scope upon a successful 200 OK response from the server.
2. **Loading States**: We will introduce a local loading state (`isProcessingBatch`) specifically for these bulk action buttons to disable them while the API request is in flight.
3. **Backend API**: The backend API for these routes already exists and I have previously patched it to safely handle missing JSON headers. No backend changes are required.

All technical ambiguities have been resolved.
