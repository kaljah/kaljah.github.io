# BUG-XXX — OGMP survey reconciliation status defaults to "Reconciled" whatever the computed variance; a +354 % discrepancy is stored and shown as Reconciled, and a zero bottom-up case is shown as "+0.0 %"

**Status:** Confirmed
**Severity:** Medium
**Category:** Methane
**Discovered by:** Agent D (Methane Auditor)

## Location
- `new/server/routes/data.py` `save_ogmp_survey()`, ~line 457: `reconciliation_status = (data.get('reconciliation_status') or ... or 'Reconciled')`. It is stored as given, independently of the `variance_pct` / `variance_flag` the same function computes.
- `get_ogmp_surveys()`: `'variance_pct': d.variance_pct or 0.0` and `'reconciliation_status': d.reconciliation_status or 'Reconciled'`.
- UI: `MethaneIntensity.jsx` ~1341-1400 (survey table: status badge green when "Reconciled"; variance shown green when |v| ≤ threshold); `MethaneExplorer.jsx:1537`.

## Reproduction
1. Fresh DB copy, admin. Facility 169 has Verified bottom-up CH4 of 772.46 t for 2025.
2. `POST /api/data/ogmp-surveys {"facility_id":169,"year":2025,"survey_date":"2025-06-01","measured_rate_kg_hr":400}` (no status given, as the "Export to OGMP" and manual forms may do).
3. `GET /api/data/ogmp-surveys?facilityId=169`.
4. Repeat for a year with no bottom-up inventory (2010, 50 kg/h).

## Input
Top-down 400 kg/h × 8760 h = 3,504 tCH4 against bottom-up 772.46 tCH4.

## Expected
Variance = (3504 − 772.46)/772.46 = +353.6 %, which exceeds the 20 % threshold. Status should be "Discrepancy Flagged", derived server-side. With a zero bottom-up, variance should be null/"N/A" and the status "Discrepancy Flagged", as `/ogmp-metrics` itself reports.

## Actual
- Case 1: stored and returned `variance_pct 353.62, variance_flag true, reconciliation_status "Reconciled"`.
- Case 2 (zero bottom-up): `bottom_up_tch4 0.0, variance_pct 0.0, variance_flag true, reconciliation_status "Reconciled"`. The survey table then shows a green "+0.0 %" and a green "Reconciled" badge.
- The seed data has the same contradiction (e.g. survey id 2: flag 1, status "Reconciled").

## Evidence
`audit/work/D/s8.py` output. Repro: `audit/repro/<ID>.py`.

## Root Cause
The reconciliation status is a free-text client field with a "Reconciled" default and is never tied to the computed flag. `None` variance is coerced to 0.0 on read. The stored `bottom_up_tch4` / `variance_pct` are also a snapshot taken at save time and never refreshed when emissions change.

## Impact
The OGMP 2.0 top-down/bottom-up reconciliation evidence shown to users (and available for disclosure) can claim reconciliation for large discrepancies. This contradicts `/api/dashboard/ogmp-metrics`, which flags the same facility.

## Affected Components
routes/data.py (POST/GET /api/data/ogmp-surveys), MethaneIntensity.jsx survey table, MethaneExplorer.jsx survey list, ManageData OGMP form (default 'Reconciled').

## Recommended Fix
Derive `reconciliation_status` server-side from the variance and threshold ("Discrepancy Flagged" / "Reconciled" / "No Bottom-Up"). Only allow an explicit override with a justification. Return `null` variance as null, and recompute bottom-up on read.
