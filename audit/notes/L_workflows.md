# Agent L — browser workflows covered

Stack: UI http://127.0.0.1:5190 → API :5055 → `audit/db/browser.db` (Playwright + local Chromium 1208, headless).
Scripts and screenshots: `audit/work/L/` (`lib.mjs` = login/session reuse, CustomDropdown picker, network capture).
Scope rule from the coordinator (after the first restart): stored calculation results are taken as given; I checked
UI ↔ API ↔ DB agreement, persistence, refresh, filters, validation and error paths, not the physics.
(Two natural-gas / diesel combustion hand-checks were done before that rule and matched.)

Test data I created: facility 173 "AUDIT-L Plant" (location West, via the UI), facility 175 (repro), Scope 1 ids 752-762,
Scope 2 ids 38-46, Scope 3 id 29 (+probe rows), production rows 975-977, SBTi target row 4 → restored (row 5).

| # | Workflow | Steps exercised | Result / findings |
|---|---|---|---|
| 1 | Login / logout / session expiry / role navigation (admin, superuser, user, it_admin) | open, initial state, nav links per role, direct URL to every route per role, wrong password, cookie cleared → protected route | Route guards match sidebar (user: no audit-trail/qa; it_admin: only audit-trail + user-management). Bad password → "Invalid credentials". Cleared session → /login. Login rate limit 20/15 min per IP is enforced (hit it during the audit). OK |
| 2 | Manage Data page load | open as admin/user | BUG-029 (crash on NULL facility name; client half fixed in baseline2, API half still open) |
| 3 | Create facility ("Add Region") | empty submit (validation toast), valid submit, without/with coordinates, DB check | BUG-045 (500 unless lat/long filled). Form has no Region field → facility.region NULL; boundary_type stored "" |
| 4 | Scope 1 Tier 1 combustion (natural gas scf, diesel gal) | select region/year/month/factor/qty/unit, submit, response vs DB vs list vs dashboard | UI = API = DB = dashboard (54.18 t, 10.24 t). Values consistent |
| 5 | Maker-checker: user submits → admin approves/rejects → dashboard | user submit (Pending), pending banner, Manage Data → Pending Review approve/reject, dashboard after | Approve updates dashboard immediately (54.18 → 59.30). Reject keeps record as Rejected. BUG-092 (maker never told; list shows no status; dialog says "permanently delete"). BUG-071 confirmed (pending banner / totals stale after create) |
| 6 | SBTi page + Set Target | KPI row, Scope 1+2 toggle, milestone table, Configure Target invalid (target<base, negative/zero/empty/100 % rate) and valid save, reload | Agent H's [FOR-BROWSER] expectations all confirmed (see SUSPECTED file). Invalid values blocked by HTML5 min/max (no request). Valid save persists; UI = API after reload. Target restored |
| 7 | Scope 2 entry (location-based) | UI entry 1000 kWh Algerian grid; API probes | UI = API = DB (0.522 t). BUG-099 (server trusts client co2e/EF: 0 kWh → 12,345 t, −500 t; superuser rows Verified and visible on dashboard). No market-based method in UI → DESIGN-Q |
| 8 | Scope 3 entry | Cat 1 Steel 1000 kg; API probes co2e mismatch / negatives | UI = API = DB (1.85 t). Server recomputes co2e (client value ignored). Negative activity/EF stored with co2e 0 (201) — minor |
| 9 | Delete record | Scope 1 list → Delete → confirm → reload → dashboard | Row gone after reload; dashboard Scope 1 59.30 → 54.18 immediately. OK. No edit UI exists for emission records (EmissionResult `onEdit` never passed) |
| 10 | Production data → Carbon Intensity | Production form (activity/division/region), MMBOE fields, oil bbl, duplicate month, negative, year 1800; Carbon Intensity page filtered to the facility/year | MMBOE-only production ignored by intensity page ("Pending Production") → added to BUG-044. Duplicate facility-month silently overwrites (same id). Negative → 400 but UI shows generic "Failed to save production". Year 1800 accepted for production (Scope 1 rejects <1900) |
| 11 | GWP-100 / GWP-20 toggle | toggle on dashboard, API params, reload | batch-all/flaring re-queried with gwp_horizon=20; summary switches to GWP-20 figures. Filters and toggle reset to defaults on page reload (not persisted) |
| 12 | Scope 1 validation / boundary / error paths | year 1800 / 2099, qty 0 / negative / empty / 1e15, no unit, no facility | 1800 → 422 shown to user; 0/neg/empty/no-facility blocked client-side with warnings; 1e15 accepted (BUG-007); 2099 accepted; **no unit accepted → BUG-109** |
| 13 | Scope 1 other processes | flaring T1 (1 MMscf), blowdown T1 (5 events), onshore fugitives facility-level T1 | Flaring: UI = API = DB (stored 28,316.85 m³ = 1 MMscf, 63.96 t). Blowdown "Blowdown - Pipeline" saved Verified with 0 t (BUG-015). Fugitive: preview 16,644 t vs saved 1.456 t → **BUG-110**; visible defaults not submitted ("Please select a fuel") |
| 14 | Tier 2 (custom factor created first in Manage Data) | invalid (negative → 400; all blank → 201), valid factor, Scope 1 Tier 2 "Saved Custom Factors Library" with both | Valid: 100 gal × 10.5 kg/gal = 1.05 t, UI = API = DB. Blank factor → 0 t record → **BUG-112**. Factor list paginated (new factors on page 7) |
| 15 | Tier 3 combustion | CO2/CH4/N2O factors kg/m³, HHV, efficiency, 1000 m³ | 201, 2.0545 t, consistent with entered factors (physics not audited) |
| 16 | CSV bulk import wizard with column mapping | template download, upload CSV with non-standard headers, auto-mapping (Date/Process/Fuel/Year/Month), manual mapping (Site/Qty/UOM), start, progress, skip reasons, DB check | First runs: every import fails "Fatal error: 'NoneType' object has no attribute 'lower'" because of a NULL-name facility → added to **BUG-029**. After that: 4 imported / 4 skipped (unknown region, negative, "abc", duplicate). Blank unit → m³ and year 1800 imported → **BUG-111**. Scope 1 duplicate key too coarse → added to **BUG-081** |
| 17 | Uncertainty page | default view, year 2025, facility filter, UI vs `/api/dashboard/uncertainty` | Default year is 2099 (DESIGN-Q). Filtered UI equals API categories/percentages |
| 18 | Methane intensity / explorer | load as admin+user, facility+year filter, UI vs intensity-stats | UI equals API (0.0079 kg CH4/BOE, 0.157 t). Known issues seen: Compliant with no gas production (BUG-088), level mismatch (BUG-080) |
| 19 | Reports / exports | default load, year+facility filter, Excel Export, PDF Report, parsed files vs DB/dashboard | Totals equal DB Verified sums (S1 58.54, S2 11,845.52, S3 1.85). Exports are Verified-only while the list shows all statuses (DESIGN-Q). PDF glyph boxes → **BUG-113** |
| 20 | Logout | UI logout, reuse of pre-logout cookie | Cookie replay still authenticated → **BUG-114** |
| 21 | Error surfacing | negative production, negative factor, facility 500 | Server reasons replaced by generic toasts → **BUG-115** |
| 22 | Page smoke (admin, user) | 10 pages: API status ≥400, console errors, NaN/undefined/Infinity/[object Object] text | No failures after the data fixes; user redirected from qa-dashboard/audit-trail |
| 23 | [FOR-BROWSER] Agent H SBTi check | see row 6 | Done, result line appended to SUSPECTED_AND_QUESTIONS.md |

## Not covered / limits
- XLSX import path, Scope 2/3 import wizards, CBAM / OGMP survey / mitigation forms, Settings page edits, User Management (IT admin) flows.
- Session idle expiry at 8 h (only cookie removal and replay tested).
- Physics of any calculation (out of scope after the coordinator's instruction).
- My DB was patched twice to give NULL-name facilities a placeholder name (`(unnamed <id>)`) so Manage Data and bulk import could be exercised; BUG-029 repro recreates the condition.

