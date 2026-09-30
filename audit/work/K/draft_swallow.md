# BUG-XXX — Manage Data and Reference Data swallow API load errors and show them as empty data ("No production record found", empty factor catalog)

**Status:** Confirmed
**Severity:** Medium
**Category:** UI
**Discovered by:** Agent K (Frontend/UI)

## Location
- `new/client/src/pages/ManageData.jsx` ≈lines 740-820: `fetchFacilities`, `fetchCustomFactors`, `fetchProduction`, `fetchSources`, `fetchMitigations`, `fetchCbamExports`, `fetchOgmpSurveys`, `fetchGoals`, `fetchBaseYears` all end in `catch (err) { console.error(err); }` — no toast, no error state.
- `new/client/src/pages/ReferenceData.jsx` `fetchData` (≈line 33): `Promise.all([/custom-factors, /emission-factors])` with `catch → console.error`, so one failing endpoint also discards the other.

## Reproduction
1. Playwright, admin on :5191; intercept `GET /api/data/production` → HTTP 500; open Manage Data → Production Data.
2. Intercept `GET /api/custom-factors` → HTTP 500; open Reference Data.

## Input
Server error (500) on a list endpoint.

## Expected
An error message/retry ("Failed to load production data") distinct from an empty result; Reference Data should still show the emission-factor catalog that loaded successfully.

## Actual
- Manage Data: table shows "No production record found." / "Page 1 of 1"; no toast (toast container empty).
- Reference Data: page renders 40 table rows instead of 229 — the whole API emission-factor catalog disappears because the custom-factors call failed; no message.

## Evidence
`audit/work/K/t_err.mjs`, `audit/work/K/t_err2.mjs` output: `normal: {"rows":229}` vs `custom-factors 500: {"rows":40,"toast":""}`. Repro `audit/repro/BUG-<id>.mjs`.

## Root Cause
Errors logged to console only; `Promise.all` couples independent loads.

## Impact
Users (and approvers) can conclude that production data, factors, goals or surveys do not exist, and may re-enter data (duplicates) or report intensity as "pending production data" during transient backend failures.

## Affected Components
Manage Data tabs (Regions, Factors, Production, Sources, Goals/Base years, Mitigation, OGMP surveys, CBAM); Reference Data library.

## Recommended Fix
Surface a toast/error panel with retry per section; use `Promise.allSettled` in ReferenceData.
