# BUG-XXX — Two contradictory OGMP facility-level algorithms: /intensity-stats reports Level 5 (Gold Standard) where the canonical service (/ogmp-metrics, OGMP export) reports Level 4 for the same facility and year

**Status:** Confirmed
**Severity:** Low
**Category:** Methane
**Discovered by:** Agent D (Methane Auditor)

## Location
- `new/server/routes/dashboard.py` `_query_intensity_stats()` ~2150-2161: its own level logic.
  - Level 5 if top-down exists and |variance| ≤ threshold. There is no requirement that the bottom-up inventory is Level 4.
  - Otherwise Level 4 if ≥50 % of CO2e is non-"default".
  - Otherwise Level 3 as soon as any CH4 exists.
  - `factor_source == "default"` counts as L3.
- `new/server/services/ogmp.py` `compute_facility_ogmp_level()` (used by `/ogmp-metrics` and `/reports/ogmp-export`) caps reconciliation at Level 4 unless the bottom-up level is ≥4, and maps `default` factors to L2.

## Reproduction
1. Fresh DB copy. Add a survey for facility 169 / 2021 equal to its bottom-up CH4 (2,891.59 t). Its inventory is L3 API-Compendium factors.
2. `GET /api/dashboard/ogmp-metrics?year=2021&facilityId=169` → `highest_ogmp_level`.
3. `GET /api/dashboard/intensity-stats?year=2021&facilityId=169` → `current_ogmp_level`.
4. Also, on the untouched snapshot, compare the two endpoints for all facilities for 2024.

## Input
Snapshot data, plus one reconciled survey.

## Expected
One level per facility-year. Per the code's own OGMP 2.0 note, reconciliation with an L2/L3 inventory is capped at Level 4.

## Actual
- Facility 169 / 2021: `/ogmp-metrics` gives 4; `/intensity-stats` gives **5**.
- Snapshot 2024: 9 of 25 facilities differ (e.g. facilities 1, 150, 155: 2 vs 3; facility 169: 3 vs 4).
- 2025: 5 of 80 differ.

## Evidence
`audit/work/D/s14.py` and `s4.py` outputs (current code). Repro: `audit/repro/<ID>.py`.

## Root Cause
The OGMP level logic is duplicated in `_query_intensity_stats` instead of calling `services.ogmp.compute_facility_ogmp_level` / `ogmp_level_for`.

## Impact
API consumers of `/intensity-stats` and `batch-all.intensity_stats` get a Gold-Standard Level 5 claim that the roadmap page and the regulatory export deny. The current client renders `highest_ogmp_level` first, so the UI impact is limited.

## Affected Components
/api/dashboard/intensity-stats (`current_ogmp_level`, `gold_pathway_status`, `ogmp_l3_pct`/`ogmp_l4_pct`), batch-all `intensity_stats`.

## Recommended Fix
Use the canonical service in `_query_intensity_stats`, and fix the service itself as described in BUG-031.
