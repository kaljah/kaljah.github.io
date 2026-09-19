# Carbon Intensity Dashboard - Deep Analysis

# Carbon Intensity Dashboard - Deep Analysis

## 1. Logic Audit & Bug Hunt

### [BUG] Missing Backend Filters
The `/intensity-stats` endpoint in `dashboard.py` currently ignores `activity` and `division` parameters. 
- **Impact**: Filtering the dashboard by Activity (e.g., "EP") or Division (e.g., "Production") does not update the KPIs or charts unless a specific Region is selected. This results in misleading aggregate data.
- **Fix**: Join `ProductionData`, `Emission`, and `Scope2Emission` tables with the `Facility` table to apply organizational filters.

### [BUG] Major Unit Inconsistency
There is a 1000x mismatch between backend calculations and frontend labels.
- **Backend**: Returns values in **kg CO₂e / BOE**.
- **Frontend**: Labels the Hero Card as **tCO₂e / bbl**.
- **Impact**: A value of "25.0 kg/BOE" is displayed as "25.000 tCO2e/bbl", which is physically impossible and orders of magnitude off.
- **Fix**: Update frontend labels to "kg CO₂e / BOE" and ensure decimal precision is appropriate for the unit.

### [BUG] Methane Intensity Labeling
Similar to Carbon Intensity, Methane is returned as **kg CH₄ / BOE** but labeled as **tCH₄ / BOE**.
- **Fix**: Standardize to "kg CH₄ / BOE" or "g CH₄ / BOE" for more readable figures.

### [PERFORMANCE] Redundant Trend Calls
`CarbonIntensity.jsx` makes **5 separate API calls** to fetch the 5-year trend data.
- **Impact**: Increased server load and slower UI response time.
- **Fix**: Optimize the `/intensity-stats` endpoint to accept a `range` or return all years when no specific year is provided.

## 2. Calculation Verification

| Metric | Calculation | Status |
| :--- | :--- | :--- |
| **BOE Conversion** | `Oil (bbl) + Gas (Mcf) * 0.166` | ✅ (Standard) |
| **Weighted Average** | `Σ(Intensity * Prod) / Σ(Prod)` | ✅ (Accurate) |
| **Flaring Intensity** | `(Flaring Emissions / Total BOE) * 1000` | ✅ (Consistent) |

## 3. Proposed Action Plan
1. **Backend**: Update `get_intensity_stats` to support joining and filtering by `activity` and `division`.
2. **Frontend**: Correct all unit labels in the Hero Card and Charts.
3. **Frontend**: Refactor `loadTrendData` to use a single aggregate call if possible, or at least handle the unit correction.
4. **Backend**: Optimize production query to include per-year breakdown in a single response.

