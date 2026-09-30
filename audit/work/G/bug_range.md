# BUG-XXX — Stored uncertainty has no range or unit validation: Scope 2/3 accept percent values, negatives, NaN and 1e6, and the Uncertainty dashboard shows ±3600 %

**Status:** Confirmed
**Severity:** Medium
**Category:** Uncertainty
**Discovered by:** Agent G (Uncertainty Auditor)

## Location
- `new/server/routes/scope2.py` L220-222 (POST) and L464-465 (PUT: `float(data["uncertainty"] or 0)`).
- `new/server/routes/scope3.py` L126-128.
- `new/server/routes/dashboard.py` `get_ef_uncertainty()`, which takes any stored value > 0 as a 1σ fraction with no upper bound.
- For comparison, `routes/qaqc.py _norm_unc()` applies a `>1 → /100` heuristic, so the two pages disagree on the same data.

## Reproduction
1. As admin, POST `/api/scope2` (electricity, 100000 kWh, EF 0.5) with `uncertainty` set to 18, then -0.5, then "NaN".
2. GET `/api/dashboard/uncertainty?year=<y>&scope=2`.
Script: `audit/repro/<ID>.py`.

## Input
`uncertainty` = 18 (a user meaning "18 %"), -0.5, "NaN", 1e6.

## Expected
The API rejects with 422 any value that is not a finite fraction in [0, ~2], or explicitly converts a percent value. The dashboard never reports an impossible ±3600 %.

## Actual
- 18 → HTTP 201, stored 18.0, dashboard category and inventory **±3600.0 %**, level "high".
- -0.5 → HTTP 201, stored -0.5. The dashboard silently substitutes its 0.10 default (±20 %).
- "NaN" → HTTP 201. The response body contains the bare token `NaN`, which is not valid JSON. The dashboard substitutes the default.
- 1e6 → HTTP 201, dashboard ±200000000 %.
Scope 3 accepts -3 the same way (HTTP 201).

## Evidence
Repro output above. The snapshot DB already contains 400 Verified Scope 1 rows with `uncertainty = 18.0277` (a percent stored in the fraction column, from test injection). Because of them, `/api/dashboard/uncertainty?year=2020` shows inventory ±818.97 % with contributors ±3605.6 %, while `/api/qaqc/dashboard?year=2020` normalises the same rows to 4.09 %. `?year=2022` shows stationary_combustion ±1249 %.

## Root Cause
No validation or unit contract on uncertainty inputs: the fraction/percent ambiguity is never resolved and there are no finiteness or range checks. The consumers handle out-of-range values inconsistently: the dashboard applies no guard, QAQC applies a heuristic /100, and negatives fall back to a default.

## Impact
A single mis-keyed record, or any percent-valued import, can make the whole-inventory uncertainty meaningless in the Uncertainty page, its CSV and the PDF report. Negative and NaN values are silently replaced. The API also emits invalid JSON.

## Affected Components
POST/PUT `/api/scope2`, POST `/api/scope3`, `emissions.uncertainty*` (no guard on any write path), `/api/dashboard/uncertainty`, `/api/qaqc/dashboard`, `UncertaintyAssessment.jsx`.

## Recommended Fix
Validate that uncertainty is finite and satisfies 0 ≤ u ≤ 2 (fraction, 1σ) on every write path, or accept a clearly named `uncertainty_pct` and convert it. Reject NaN/Inf. Apply one shared normalisation or guard in both dashboard consumers and flag out-of-range stored rows instead of propagating them.
