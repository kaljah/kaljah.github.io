# F — Dashboard reconciliation (Agent F)

Stack: UI :5192 → API :5057 → `audit/db/dashboard.db`. Repros run against the repro copies `repro_F` and `repro_F3`.
Stored co2e/ch4/n2o values are taken as given; the emission calculation is out of scope.
Evidence:
- `audit/work/F/`: `dash_text.txt`, `ui_*.json`/`.png` (Playwright DOM), `batch_all.json`, `filter_matrix.json`
- PDF captures: `exec_brief_allyears.pdf`/`brief.txt`, and `gen_all.txt`/`gen_2025.txt` (server `/reports/generate`)
All repros were re-run on the baseline2 code and all still fail (bugs present).

## Default view (All Years, all filters, GWP-100, Verified)

| Metric | UI (DOM) | Frontend transform | API | Backend logic | DB (SQL) | Independent | Result |
|---|---|---|---|---|---|---|---|
| Gross S1+S2 | 3.7T | Σ summary rows (scope1_total+scope2_total), year-filtered client-side | 3,723,127,249,117.66 | `_query_summary` Σco2e_total Verified by year + Σ S2 co2e | 3,723,125,709,415.04 + 1,539,702.62 | same | OK. The magnitude comes from 7 test rows (BUG-007) |
| Scope 1 / 2 / 3 pills | 3.7T / 1.5M / 216.9 | S3 from scope3_summary.total | 3,723,125,709,415.04 / 1,539,702.62 / 216.85 | Verified filter | same | same | OK |
| Net emissions | 3.7T, "Less 1M" | gross − Σmitigation | mitigation 1,027,500 | `_query_mitigation`: no status/activity filter | 715,500 Active + 312,000 Planned | 715,500 | **BUG-094** |
| CH4 | 84.3M tCH4 | Σ ch4_total | 84,338,950.20 | Σ ch4_emissions | 84,338,950.20 | same | OK. 70 M t from test rows (BUG-007) |
| Intensity | 627.53K kg/BOE | BOE-weighted | — | `_query_intensity_stats` | — | — | Agent E scope (BUG-004/017) |
| Pending banner | 128 / 4,686,441,566,968.31 | toLocaleString | same | S1+S2 Pending only | 114+14; 4,686,441,566,610.25+358.06 | same (4.69e12, not e15) | Count OK. Ignores Supply Chain/Activity/Division filters and Scope 3: **BUG-054**. Ignores GWP-20: BUG-072 |
| Source split C/F/V/O | 3.7T / 2.2M / 460.6K / 6.5M | Σ per source | 3,723,116,579,281.52 / 2,199,048.57 / 460,645.31 / 6,470,439.64 | SOURCE_MAP substring | sum = S1 ✔ | mis-classified (fuel_gas → Other, 6.47M) | Sum OK; classification **BUG-061** |
| Flaring panel total | 100 kNm³ / 210.2 t, −99.92% YoY | flaringData | year=2026 | "all" → current year | 2026: 2 rows, 100,000 m³, 210.22 t | All-years flaring 2,199,048.57 | **BUG-026** |
| Flaring streams | 56/40/4 kNm³, 0 t each | — | 0.0 tco2e | 56/40/4 benchmark split of generic "flaring" | no typed rows or FlaringDetail in 2026 | unknown split | **BUG-036** |
| Flaring YoY −99.92% | — | — | −99.92 | 2026 Emission m³ (100k) vs 2025 FlaringDetail total_knm3 (121,487k) | yes | (1e5 − 1.21487e8)/1.21487e8 = −99.918% | Arithmetic reproduces. Wrong because of BUG-026 (partial year); unit path BUG-033/035 |
| Detailed Breakdown Flaring vs sub-rows | 2.2M vs 0/0/0 | two different endpoints | — | all-years vs 2026 | — | children ≠ parent | BUG-026 |
| Activity donut / org breakdown | 3.2T Production, 532.9B Steel, … | Σ categorical by activity | Σ = 3,723,127,249,117.66 | grouped by Facility.name | = KPI ✔ | — | Sum OK. Six facilities merged by name: **BUG-064** |
| Total footprint S1+2+3 | 3.7T | s1+s2+s3 | — | — | 3,723,127,249,334.51 | same | OK |

## Filter matrix (API `batch-all`, `audit/work/F/filter_matrix.json`)

| Filter | Gross KPI | Σ sources | Σ categorical | Scope 3 | Pending count | Result |
|---|---|---|---|---|---|---|
| year=2025 | 1,954,194.33 (UI "2M", S1 1.6M, S2 317.3K) | = S1 | = KPI | 0 | 112 | OK. UI flaring 2025 = 306,015 t = Σ streams ✔ |
| year=2024 | 3,718,017,236,744.02 | = S1 | = KPI | 0 | 16 | OK |
| facilityId=1 | 532,854,090,929.16 | = S1 | = KPI | 216.85 | 16 | OK |
| segment=Heavy Industry | 532,854,262,124.59 | **3,723,125,709,361.93** | = KPI | 216.85 | **128** | **BUG-040**, BUG-054 |
| segment=Upstream | 3,190,272,868,634.49 | **3,723,125,527,259.75** | = KPI | 0 | **128** | **BUG-040**, BUG-054 |
| activity=Steel & Iron | **106.84** (by facility: 532,854,090,929) | = S1 | = KPI | 216.85 (facility-based) | 128 | BUG-004 (confirmed, dashboard KPIs added) |
| activity=Activité E&P | **9,990.5** (by facility: 3,392,147,653.7) | = S1 | = KPI | 0 | 128 | BUG-004 |
| division=DP / Metallurgy | 9,990.5 / 531,145,000,159.91 | = S1 | = KPI | — | 128 | BUG-004 |
| includePending | 8,409,568,816,085.97 (= SQL V+P) | = S1 | **3,723,127,249,117.66** | 216.85 (V+P = 366.85) | 128 | **BUG-054** |
| GWP-20 (all) | 3,727,745,144,708.74 | = S1 | = KPI | — | — | Reproduces Δ with CH4 82.5 / N2O 268 exactly. Published AR5 84/264 gives 3,727,841,549,691.38: BUG-013 (confirmed) |
| GWP-20 2025 (UI) | 2.1M (API 2,051,616.88) | | | | | OK vs code constants |

## Reports / PDF

| Output | Figure | Independent | Result |
|---|---|---|---|
| Server `POST /reports/generate` all | Grand total 3,723,127,249,334.51 | S1+S2+S3 Verified 3,723,127,249,334.51 | OK |
| Server `/reports/generate` 2025 | 1,954,194.33 | same | OK |
| Client Executive Brief (dashboard, All Years) | "FISCAL YEAR 2026", S1 8,409,567,617,747.49, S2 1,540,060.68, S3 366.85, "Total verified records: 809" | Verified S1+S2 3,723,127,249,117.66; 149 of 809 rows are Pending | **BUG-077** |
| Client Executive Brief narrative | "15.9% reduction…", "65.9% CH4…", "−38.0% flaring", "98% Measured VISR" | −99.89% / −99.96% / −99.92%; DRE = default | **BUG-078** |

## QA dashboard

"0 anomalies… fully verified and audit-compliant", although there are 149 Pending records and 11 rows above 1e6 × median: **BUG-084**.
Coverage 809 = all statuses (744+37+28).

## Lead root causes

- **Gross 3.7T / CH4 84.3M**: 7 admin test rows, 1e13 MMBtu NG each (5.31145e11 t CO2e, 1e7 t CH4). The aggregation is correct (BUG-007; BUG-030 for the NULL quantity).
- **Flaring 100 kNm³ = 210.2 t, streams 0 t**: "All Years" is mapped to 2026 (BUG-026). In 2026 there are only generic "flaring" rows, so a fixed 56/40/4 volume split is shown with no CO2e allocated (BUG-036). The −99.92 % YoY compares partial 2026 with full 2025.
- **Pending 128 = 4.69e15**: the real value is 4.686e12 t (displayed with toLocaleString, "4,686,441,566,968.31"). Two coal test rows of 1e15 t (BUG-007).
