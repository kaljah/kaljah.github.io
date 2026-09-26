# BUG-XXX — Methane loss-rate segment classification differs between the KPI cards, the trend chart and the server: "Downstream / Processing" counts as Midstream in the trend, and "Upstream / Extraction" is dropped from the Upstream KPI

**Status:** Confirmed
**Severity:** Low
**Category:** Methane
**Discovered by:** Agent D (Methane Auditor)

## Location
- `new/client/src/pages/MethaneIntensity.jsx` `loadStats` (~213-229): exact match. `seg === "midstream"` counts as Midstream and `seg === "upstream"` as Upstream; everything else is excluded.
- Same file, `trendChartData` (~620-645): substring match. "processing", "lng", "lsh", "gnl" and "gpl" count as Midstream; "upstream", "production" and "exploration" count as Upstream.
- `new/server/routes/dashboard.py` `_query_intensity_stats` / `_query_intensity_trend_bulk`: `ogmp_target = 0.20 if "upstream" in segment else 0.05`. A facility with segment "Oil & Gas" or NULL therefore gets the 0.05 % midstream target. WEC uses yet another rule ("processing"/"midstream"/"lng" → midstream threshold).

## Reproduction
1. Snapshot copy, admin. The facility segments stored are "Upstream" (37), "Upstream / Extraction" (42), "Midstream" (6), "Downstream / Processing" (60), "Oil & Gas" (1), "Heavy Industry" (3) and NULL (15).
2. `GET /api/dashboard/intensity-stats?year=2025` and `GET /api/dashboard/intensity-trend?years=...`.
3. Apply the page's two aggregation routines (transcribed in `audit/work/D/s15.py`).

## Input
Year 2025, all facilities.

## Expected
The same year, filters and facilities give the same Upstream/Midstream gas denominators and loss rates in the KPI cards and in the 5-year trend chart. Refinery ("Downstream / Processing") gas should not count toward the Midstream OGMP rate.

## Actual
For 2025:
- KPI midstream gas = **0 m³**, and the Midstream card shows no rate. The trend's midstream gas = **122,158,675 m³**, all from "Downstream / Processing" facilities.
- KPI upstream gas = 15,490,256,856 m³; trend upstream gas = 15,548,277,980 m³. The KPI omits the "Upstream / Extraction" facilities.
- Loss rates therefore differ between the card and the chart point for the same year.

## Evidence
`audit/work/D/s15.py` output (current code). Repro: `audit/repro/<ID>.py`.

## Root Cause
Three independent, inconsistent segment-to-category mappings. There is no canonical segment enum; the facility data uses free-text composites.

## Impact
Segment-level methane loss rates and OGMP targets (0.20 % vs 0.05 %) are applied to different facility sets depending on which widget is read. With the current data the numeric difference is small, but it grows with the volume of refinery or "Upstream / Extraction" gas.

## Affected Components
MethaneIntensity.jsx KPI cards and trend chart; server `ogmp_target` / `ogmp_target_status`, WEC threshold selection.

## Recommended Fix
Add one server-side canonical segment classifier (and return `segment_category` in the API), then use it in all three places. Validate the facility segment against an enum.
