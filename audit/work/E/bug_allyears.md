# BUG-XXX — Intensity with year="all" (default view) pairs each facility's emissions from every year with production from other years; KPI mixes periods

**Status:** Confirmed
**Severity:** High
**Category:** Carbon Intensity
**Discovered by:** Agent E (Carbon-intensity auditor)

## Location
- `new/server/routes/dashboard.py` `_query_intensity_stats` L1682-1683 / L1760-1761 / L1904-1905: with year="all" (or absent) no year filter is applied, and production (L1695) and emissions (L1774) are grouped by **facility only**, not by (facility, year). Intensity is then computed per facility at L2035-2044.
- Client: `new/client/src/pages/DashboardEnhanced.jsx` L104 (`currentYear` defaults to "all") and L343-364 (weighted KPI). `CarbonIntensity.jsx` L37 has the same "all" default.

## Reproduction
1. `GET /api/dashboard/intensity-stats` (no year), as admin, on the snapshot copy.
2. For facility 2 (Fertial), compare `co2_intensity` with Σ emissions / Σ BOE restricted to the years that have production.
3. Run `python audit/repro/BUG-XXX.py`.

## Input
Facility 2 has production in 2022-2026 only, plus 73,202 tCO2e of Verified emissions in 2020 (a year with no production). Facilities 9 (OHT) and 10 (STAH) have production in 2022-2026 only, plus 2.1e9 t and 1.2e9 t of Verified emissions in 2021.

## Expected
Year-matched (only (facility, year) pairs with production > 0), all years:
- Facility 2: 1.225 kg CO2e/BOE
- Facility 9: 0.0 kg/BOE (it has no verified emissions in its production years)
- Facility 10: 0.0 kg/BOE

## Actual
- Facility 2: 13.61 kg/BOE (11× too high, because the 2020 emissions are divided by 2022-26 production)
- Facility 9: 203,285 kg/BOE; facility 10: 105,601 kg/BOE
- Many facilities with 2026 emissions and only 2025 production are also mixed (fid 46-141).
- The corporate KPI in the default dashboard view becomes 627,530 kg/BOE, which is the "627.53K kg/BOE" on the snapshot. The year-matched value on the same data is 621,561. See Impact for why the rest of the 627K comes from absurd seed records.

## Evidence
`audit/work/E/api3.py` and `exp_all.py`:
```
2 Fertial  API int 13.61  prod years [2022..2026] emission yrs w/o prod {2020: 73202.1}
9 OHT      API int 203285.5  prod years [2022..2026] emission yrs w/o prod {2021: 2147516109.6}
10 STAH    API int 105601.4  prod years [2022..2026] emission yrs w/o prod {2021: 1244427746.7}
year-matched: fid2 1.2248, fid9 0.0, fid10 0.0
```

## Root Cause
Intensity must be computed from emissions and production that cover the same period. With year="all" the server aggregates each facility across all years separately for the numerator and the denominator. Emissions from years without production (and years such as 1800 or 2099) enter the numerator but have no denominator. The client then BOE-weights these mixed per-facility ratios.

## Impact
The default dashboard KPI "Performance Intensity" and the Carbon Intensity page, which also default to "All years", show period-inconsistent intensities. For the snapshot KPI of 627.53K kg/BOE: most of the value comes from 7 Verified 2024 "Combustion" records of 5.31e11 tCO2e each, which have quantity NULL and unit MMBtu. Facility 1 (Tosyali) holds one of them against 5.46 M BOE. Those records are bad seed data (or a validation gap) and are reported separately if they are not already. The period mixing adds to that value and independently distorts facility-level results, such as Fertial being 11× too high.

## Affected Components
`/api/dashboard/intensity-stats`, `/api/dashboard/batch-all` (intensity_stats), Dashboard Performance Intensity KPI, CarbonIntensity.jsx facility table and cards, MethaneIntensity.jsx (the same stats with year=all), ModernReportGenerator.js.

## Recommended Fix
For year="all", group production and emissions by (facility_id, year) and include a (facility, year) pair in both the numerator and the denominator only when it has production. Alternatively, do not offer an "all years" intensity and require a single reporting year.
