# Data Model: QA/QC Module

## Existing Entities to Modify
We need to add new fields to the existing models to support uncertainty and QC flagging.

### 1. `Emission` (Scope 1)
- **Add field**: `uncertainty_pct` (Float, nullable)
- **Add field**: `qa_flag` (String/Text, nullable) - stores the reason it was flagged (e.g. "Value > 10,000 anomaly")

### 2. `Scope2Emission`
- **Add field**: `uncertainty_pct` (Float, nullable)
- **Add field**: `qa_flag` (String/Text, nullable)

### 3. `Scope3Emission`
- **Add field**: `uncertainty_pct` (Float, nullable)
- **Add field**: `qa_flag` (String/Text, nullable)

### 4. `CustomFactor`
- **Add field**: `uncertainty_pct` (Float, nullable)

## Existing Entities to Utilize
### `ActivityLog`
- Used extensively to store the "Before" and "After" states for full traceability.
- `metadata_json` will contain a serialized dictionary of `{ "before": {...}, "after": {...} }`.
