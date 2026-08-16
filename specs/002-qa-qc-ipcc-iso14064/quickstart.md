# Quickstart: Testing QA/QC Module

To validate that the QA/QC engine works locally:

1. **Start the Application**:
   Ensure both the Flask backend and the React frontend are running.

2. **Test Automated Data Validation (QC)**:
   - Navigate to any Data Import Wizard (e.g. Scope 1).
   - Enter an extreme outlier value for quantity (e.g., `999999999`).
   - Submit the upload.
   - **Expected Outcome**: The record is saved but marked as "Pending Review" and a flag reason is visible in the UI indicating an anomaly.

3. **Test Audit Trail**:
   - Go to the Pending Review dashboard.
   - Edit the newly uploaded anomalous record to fix the quantity to `100` and approve it.
   - **Expected Outcome**: An entry is immediately created in the `ActivityLog` table capturing the change from `999999999` to `100`, timestamped and tagged with your User ID.

4. **Test Uncertainty Dashboard & Export**:
   - Navigate to the new QA/QC Dashboard tab.
   - View the aggregated Tier 1 Uncertainty percentage for your inventory.
   - Click "Export QA/QC Report".
   - **Expected Outcome**: A CSV or PDF downloads containing the log of anomalies, audit trails, and uncertainty calculations.
