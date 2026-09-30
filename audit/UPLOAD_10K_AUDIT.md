# 10,000-row upload audit (2026-09-29), no fixes

## Method
- **Data:** a copy of the live database; the old test records were removed from the copy only.
- **Uploads**, all through the browser as admin:
  - Manage Data wizard: 8 facilities in 5 regions with coordinates and equity shares, 6 custom factors, and 384 production months in mixed oil and gas units.
  - Scope 1 file: 10,000 rows, each with a unique equipment ID.
  - Scope 2 file: 10,000 rows.
  - Scope 3 files: 8,000 activity rows and 2,000 spend (NAICS) rows.
- **Scope 1 coverage:**
  - Every process type, Tier 1, 2 and 3.
  - Every catalog fuel and unit family.
  - Actual-volume gas with pressure (psig, psia, kPa, barg), temperature (C, F) and Z.
  - Random gas compositions and flare types / efficiencies.
  - All Compendium activity rows.
  - All Tier 3 methods: completions, unloading Eq 6-10, pneumatic bleed, tank GOR, AGR, vented volumes (volume, GOR, rate x days, actual conditions, desiccant), blowdown, Method 21, carbon balance, carbon content.
- **Scope 2 coverage:** 61 grids x kWh / MWh / GWh, supplier factors, steam in 11 units with boiler efficiency and loss, and CHP with plant efficiencies.
- **Scope 3 coverage:** every form activity with unit aliases; explicit factors in kg, t, g and per $1,000; supplier totals; 1,016 NAICS codes.
- **Approval:** records were approved by a second admin through the Review Wizard.
- **Expected values** were derived independently:
  - catalog numbers, with my own unit conversions;
  - the carbon balance at 379.3 scf/lbmol;
  - the Compendium equations;
  - AR5 GWPs.
- **Checked against:**
  - every stored record (30,000 scenarios);
  - the Scope 1 table (9,623 records), the Scope 2 table (5,749) and a 3,000-row Scope 3 sample, all scraped from the UI;
  - 97 API views (all years, each year, each facility, segments);
  - the Dashboard, Carbon Intensity, Methane Intensity, Uncertainty, Emissions Map and SBTi pages.

| File | Rows | Stored | Rejected |
|---|---|---|---|
| Scope 1 | 10,000 | 9,973 | 27: generator quantities above 100 Mt, correctly refused |
| Scope 2 | 10,000 | 9,993 | 7: see bug 3 |
| Scope 3 activity | 8,000 | 8,000 | 0 |
| Scope 3 spend | 2,000 | 2,000 | 0 |

## Results
- **Stored records:** 28,876 of 30,000 matched the expected value. The differences are bugs 1 to 3, bug 11, and the composition note below.
- **Tables:** the displayed values (CO2, CH4, N2O, total, quantity, unit, EF, process, tier) equal the stored values in every row checked.
- **Pages matched the independent aggregates:**
  - the dashboard totals, source split, CH4, flared volumes, streams and facility cards;
  - carbon intensity, Scope 1, Scope 2, flaring and Scope 3 intensities, BOE, and oil and gas production;
  - methane intensity, overall, upstream and midstream loss rates, and the flaring rate;
  - the uncertainty totals;
  - methane per facility on the map;
  - the SBTi trajectory, baseline and targets.

  The exceptions are bugs 7 and 8.

## Errors

| # | Severity | Area | Error | Evidence |
|---|---|---|---|---|
| 1 | High | Engine: Tier 3 flaring | `control_efficiency` is ignored. The template documents it for flaring and its sample row uses it, but the flare model only reads `combustion_efficiency` / `destruction_efficiency` and falls back to the flare-type default (98 % / 99.5 %) | 414 Tier 3 flare rows. 10,000 m3 elevated flare at 90 %, 98 % and 99.5 % all give 0.1153 t CH4; CH4 is 0.05x to 10x the expected value |
| 2 | High | Engine: Tier 3 carbon balance | "short ton" is not recognised. The conversion fails and the mass is silently used as kg, which also applies to any other unknown mass unit | 16 rows at 1/907 of the expected value (`calculations/stoichiometry.py` falls back to `norm_mass = fuel_mass`) |
| 3 | Medium | Scope 2 bulk: steam | Transmission loss (and boiler efficiency) values of 1 or less are read as fractions, above 1 as percent. A 0.9 % loss becomes 90 %, and exactly 1 % is rejected. The template gives no unit | 45 rows 1.1x to 9.9x too high (0.9 % gives 9.9x); 7 rows rejected "transmission loss in [0, 1)" |
| 4 | Medium | UI: Pending Review, "Approve All Scope N" | The toast says "Approved all Scope 1 records" when the server approved 0 (uploader's own records). The per-scope button ignores `approved_count` | API `{"approved_count":0}`; toast shown 3x; 9,973 still Pending |
| 5 | Medium | Notifications | A batch approval creates one notification per record, and the uploader's screen fills with toasts that cover the page and block clicks | 29,966 approvals gave 29,970 notifications for one user; pagination clicks intercepted by `.toast-container` |
| 6 | Medium | UI: Scope 2 / Scope 3 tables | Every page change downloads the whole record list (4.3 MB at 10k rows) to show 10 rows. Loads intermittently fail ("Network Error") and the table then says "No entries yet" | 1,195 `GET /api/scope2` calls while paging; Scope 3 empty with 10,000 Verified records |
| 7 | Medium | Dashboard / Methane Intensity | `well_testing`, `workovers` and `separation` are classified "other". Their emissions show as Other instead of Venting, and their CH4 is counted as combustion methane | 225 records: 231,235 tCO2e in Other; 8,139 t CH4 in "combustion" |
| 8 | Low | Uncertainty page | The "Tier 1/2/3 (Data Quality)" split is uncertainty bands (at most ±10 % is called "Tier 3"), not the records' tiers | 2025: shown 6.6 / 80.7 / 12.7 %, actual tiers 57.7 / 29.1 / 8.7 % (+4.5 % Scope 2/3) |
| 9 | Low | Scope 3 bulk | Imported records store no uncertainty, so the table shows "—" and the Uncertainty page assumes 15 %. Manual entries get 22.3 % | 10,000 of 10,000 Scope 3 records have uncertainty NULL (Scope 2: 0 of 9,993) |
| 10 | Low | API `/dashboard/batch-all` | The uncertainty block ignores the facility, segment, activity and division filters. It is not displayed on the page | facilityId 5, 2024: 157.8 Mt (company) instead of 4.72 Mt |
| 11 | Low | Engine: pneumatic per device-year | A month share is days/365 even in a leap year. Unloading per well-year uses /366 | Feb 2024, 10 high-bleed: 4.060 t instead of 4.049 t (+0.27 %, 47 rows) |
| 12 | Low | Uncertainty page | Categories show raw process keys | "combustion", "tank_flashing", "adipic_acid_production" |

## Not errors (checked)
- **Tier 3 gas composition totalling 98 to 100 %:** it is renormalised to 100 % by design (`units.composition_fractions`). My compositions left 1 to 2 % unspecified, which gave up to +2.2 %.
- **Empty "E&P (Upstream)" group on the dashboard:** it belongs to the pre-existing "EP" facilities, which have no records in this copy.
- **The dashboard SBTi widget does not follow the facility filter:** it is labelled as the corporate trajectory.

Files: generator, expectations, scrapes and screenshots are in the session scratchpad `big/` folder.

## Fixes (2026-09-30)

| # | Fix |
|---|---|
| 1 | A single flare efficiency (`control_efficiency`, `flare_efficiency`) sets both the carbon conversion and the CH4 destruction; separate `combustion_efficiency` / `destruction_efficiency` still win (`calculations/dispatcher.py`) |
| 2 | Mass units go through `stoichiometry.mass_to_kg`: "short ton", "Short-Ton", "long ton" recognised, an unknown unit is refused (was read as kg). `units.convert` accepts spaced unit names |
| 3 | Bulk steam: transmission loss is always a percentage (0.9 = 0.9 %, "5%" accepted); boiler efficiency 0.85 or 85; text refused instead of defaulted; header aliases; the Scope 2 wizard lists the steam / CHP columns with their units |
| 4 | "Approve All Scope N" reports the server's count (`showReviewResult`) |
| 5 | One notification per maker and decision (summary with count and ids) instead of one per record; the notification centre shows one toast for a burst of more than 3 |
| 6 | `GET /api/scope2` and `/api/scope3` take `limit` / `offset` (`{data, total}`); the tables load one page; a failed load shows an error with Retry instead of "No entries yet" |
| 7 | `well_testing`, `workovers`, `separation`, `co2_eor` classified as vented and `thermal_oxidizer` as combustion (dashboard source split, methane split) |
| 8 | Uncertainty page: `tier_breakdown` is the Scope 1 calculation tier (factor source); the uncertainty bands are a separate `uncertainty_bands` block |
| 9 | Bulk Scope 3 (activity and spend) stores the form's default uncertainty, or the file's `uncertainty` column |
| 10 | Dashboard batch uncertainty uses the facility / activity / division / segment filters (with the facility access check) |
| 11 | Per-year factors use the hours of the record's year (a leap-year month is days / 366) |
| 12 | Uncertainty categories and contributors use the process labels |
| 13 | Found while fixing: an upload job was marked "completed" before its error file was written, so an immediate "Download full CSV" could 404; the job now completes last |

Re-run through the browser on a fresh copy (same 30,000 rows):
- **Imports:** Scope 1 stored 9,973 (27 generator rows above 100 Mt refused); Scope 2 stored 10,000 (the 1 % loss rows were refused before); Scope 3 activity 8,000 and spend 2,000.
- **Stored values:** every value matches the expectation except 212 Tier 3 composition rows. Those analyses total 98–100 %, and the engine renormalises them to 100 % by design.
- **Review:** the uploader's "Approve All Scope 1" now says "No records approved: …". The reviewer's Review Wizard approved 29,973 records, and the uploader received 3 notifications (one per scope) instead of 29,973.
- **Tables:** 10 rows (about 4.4 KB) per page request, 1,000 pages.
- **Tests:** `tests/test_upload_10k_audit_fixes.py` (25). Backend 1,829 passed / 0 failed, validation 128, CI gates 448, vitest 38, lint 0 errors, build OK.
