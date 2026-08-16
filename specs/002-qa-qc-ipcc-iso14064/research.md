# Research & Design Decisions: QA/QC Module (IPCC & ISO 14064)

## 1. Technical Context Verification
The current application already features an `ActivityLog` model which we can use to fulfill the Audit Trail requirements of ISO 14064-1 without needing a completely new table.
The current `Emission`, `Scope2Emission`, and `Scope3Emission` models lack fields for Uncertainty Assessment.

## 2. Identified Issues & Requirements
- **Uncertainty Data Fields**: We need to add an `uncertainty_pct` (Float) field to the emission tables and the custom factor table.
- **Automated QA Validation (QC)**: We need an engine that intercepts data uploads (Scope 1/2/3 wizards). It must detect outliers (e.g. comparing the input against historical averages or fixed bounds). If an outlier is detected, it should be saved but its `status` forced to "Pending Review" and a `qa_flag` field should be set with the reason.
- **Reporting**: We need to generate a PDF and CSV export of the QA/QC dashboard.

## 3. Decisions
1. **Uncertainty**: We will use standard Tier 1 Error Propagation (root sum of squares) on the frontend/backend to combine uncertainty percentages.
2. **Validation Rules**: Since historical averages might be sparse in a new app, we will also allow static bounds checking (e.g., fuel consumption > 1,000,000 units is flagged) alongside basic Z-score anomaly detection if enough historical data exists.
3. **Audit Trail Integration**: The existing `ActivityLog` model will be utilized. Every API endpoint that modifies data will be hooked to log the before/after state (saved in `metadata_json`).
4. **Report Exporting**: We will use Python's `csv` module for CSV exports and `ReportLab` (or similar) for PDF generation on the backend.

All technical ambiguities have been resolved.
