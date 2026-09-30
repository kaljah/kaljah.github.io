# BUG-XXX — Intensity activity/division filter uses record-level columns that are NULL/inconsistent, so numerator and denominator are filtered differently (Upstream intensity blank, E&P intensity 0.0)

**Status:** Confirmed
**Severity:** High
**Category:** Carbon Intensity
**Discovered by:** Agent E (Carbon-intensity auditor)

## Location
- `new/server/routes/dashboard.py` `_query_intensity_stats` L1690-1693 (production: `ProductionData.activity/division`), L1768-1771 (Scope 1: `Emission.activity/division`), L1912-1915 (Scope 2: `Scope2Emission.activity/division`), L1952-1955 (Scope 3: `Facility.activity/division`)
- Same pattern in `_query_intensity_trend_bulk` L1340-1343, L1408-1411, L1449-1451, L1496-1499, L1531-1537
- Root data cause: `routes/data.py` `add_production` L107-108 stores `activity`/`division` only from the payload (no fallback to `facility.activity`, unlike `background_processor.py` L1395-1396 and `emissions.py` L3163); emissions imported via some paths also carry NULL activity.

## Reproduction
1. `python audit/repro/BUG-004.py` (the number assigned) or manually:
2. `GET /api/dashboard/intensity-stats?year=2025&activity=Upstream` as admin.
3. Compute sum(co2e_S1+S2 Verified)/sum(BOE) for facilities whose `facilities.activity='Upstream'`, same year.

## Input
Snapshot DB (agentE copy). Berkine facilities 169 (HBNS) / 170 (El Merk): `facilities.activity='Upstream'`, their 70 Verified emissions have `emissions.activity='Upstream'`, but their `production_data.activity` is NULL. 160 Verified emissions of 'Activité E&P' facilities have `emissions.activity` NULL while their production rows carry 'Activité E&P'.

## Expected
Same filter applied to numerator and denominator (facility-level):
- activity=Upstream, 2025: 16.355 kg CO2e/BOE over 116.7 M BOE; 2022: 19.554 kg/BOE
- activity=Activité E&P, 2025: 0.772 kg/BOE; 2022: 0.227
- activity=Steel & Iron (Acier DRI), 2022: 85.968 kg/BOE

## Actual
- activity=Upstream: every row has total_boe=0 → co2_intensity 0 for all facilities, weighted KPI undefined (dashboard shows "Pending Production" even though 116.7 M BOE exist)
- activity=Activité E&P: 0.0 kg/BOE (production counted, 160 emissions dropped from numerator)
- Steel & Iron 2022: 0.0 kg/BOE instead of 85.97
- Unfiltered (year=2025) matches expected (10.855) → the discrepancy comes only from the filter.

## Evidence
`audit/work/E/api2.py` output:
```
Upstream 2025 API None B 0 | expected 16.355 B 116715870
Upstream 2022 API None B 0 | expected 19.554 B 118638289
Activité E&P 2025 API 0.0 B 47541331 | expected 0.772
Steel & Iron (Acier DRI) 2022 API 0.0 B 1148671 | expected 85.968
```
SQL: `select coalesce(p.activity,'NULL'), f.activity, count(*) from production_data p join facilities f ... ` → ('NULL','Upstream',10); emissions: ('NULL','Activité E&P',160 Verified), ('Power Generation','Steel & Iron (Acier DRI)',8).

## Root Cause
The activity/division filter is applied to four different columns (record-level on production, Scope 1 and Scope 2; facility-level on Scope 3). Record-level labels are optional, often NULL and can differ from the facility's label, so the numerator and the denominator are filtered on different populations.

## Impact
With the activity or division filter set, the corporate and facility carbon intensity (Dashboard "Performance Intensity" KPI, Carbon Intensity page, Methane Intensity page, intensity trend and PDF report) is wrong or missing. The largest producers (Berkine, about 65% of 2025 BOE) disappear from the "Upstream" view.

## Affected Components
`/api/dashboard/intensity-stats`, `/api/dashboard/intensity-trend`, `/api/dashboard/batch-all` (intensity_stats, intensity_stats_py), DashboardEnhanced KPI, CarbonIntensity.jsx, MethaneIntensity.jsx, MethaneExplorer.jsx, ModernReportGenerator.js.

## Recommended Fix
Filter all numerator and denominator queries by the same facility attribute (join `Facility` and filter `Facility.activity/division`). Alternatively, default record-level activity/division to the facility's value on every write path, including `POST /api/data/production`, and backfill the NULL values.
