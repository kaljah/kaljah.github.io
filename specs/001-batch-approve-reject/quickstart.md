# Quickstart: Testing Batch Approve/Reject

To validate that the bulk approve and reject functionality works locally:

1. **Start the Application**:
   Ensure both the Flask backend and the React frontend are running.

2. **Generate Pending Data**:
   Upload dummy emission records via the Import Scope 1/2/3 wizards, or run a backend seeding script to generate pending records.

3. **Navigate to the Review Page**:
   - Log in as an admin or superuser.
   - Go to "Manage Data" -> "Pending Review" tab.

4. **Test "Approve All"**:
   - Note the number of pending records in Scope 1.
   - Click the green "Approve All" button for Scope 1.
   - **Expected Outcome**: A success toast appears, the Scope 1 list clears immediately without a page refresh, and the records are marked as "Verified" in the database.

5. **Test "Reject All"**:
   - Note the number of pending records in Scope 2.
   - Click the red "Reject All" button for Scope 2.
   - **Expected Outcome**: A success toast appears, the Scope 2 list clears immediately, and the records are removed from the database.
