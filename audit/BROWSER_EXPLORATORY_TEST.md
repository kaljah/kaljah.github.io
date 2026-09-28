# Exploratory browser test — findings and fixes (2026-09-28)

## How it was run

- **Setup:** throwaway servers on a copy of `ghg_app.db`:
  - backend on port 5055;
  - Vite on port 5174 with a temporary config;
  - headless Chromium driven by Playwright;
  - an admin test user.
- **First pass:** used the software as a user, without fixing anything. Every page was opened, and every Tier 1 factor list was submitted for every process type. Scope 2, Scope 3, custom factors, production data, edit/delete, the settings GWP switch and the four report exports were also exercised. Saved values were checked against the database and the Compendium.
- **Second pass:** after the fixes, the same flows were repeated through the browser on a fresh database copy.
- **Out of scope:** the "2025 Master Report" (a fixed Groupement Berkine / El Merk document) was left unchanged at the user's request.

## Wrong values saved

| # | Finding | Fix | Check |
|---|---|---|---|
| F3 | **Mud degassing Tier 1.** "Water based" 0.15 and "Oil based" 37.5, read as tonnes per drilling day. Compendium Table 6-2 onshore gives 0.0458 and 0.0103 t CH4/day, so oil-based was about 3,600× high. This produced the 660,430 t record already in the real database (id 9). A "Synthetic" row was also offered, and its results were saved as 0. | The catalog rows now carry the mud type, and the drilling calculator applies Table 6-2 by mud type and location. A saved library factor is converted from kg to t. A Synthetic row was added. | 100 days of oil-based mud: 1.03 t CH4 (was 3,750 t). |
| F2 | **Tier 1 engine CH4 factors** did not match Table 4-7. 4-stroke rich burn used the boiler value (100× low); 4-stroke lean 0.3 against 0.567 kg/MMBtu; 2-stroke lean 0.6 against 0.657. The turbine used the t/10^12 J number as kg/MMBtu (5 % low). | Table 4-7 converted at 1.05506 kg/MMBtu per t/10^12 J (HHV), on the server and in the client. | 1,000 scf rich burn: 0.108 kg CH4. |
| F4 | **Separation / wastewater.** "Separator Venting – Gas Well", "Separator Venting – Oil Well" and "Wastewater – Open System" were all computed with the crude-tank flashing factor, because the legacy engine renamed "separation" to "tank". 100 m3 gave 121 kg CH4, more methane than 100 m3 of gas contains. | The rename was removed. Separation Tier 1 now uses the Compendium rows for Table 6-25 (dump valves), Table 6-26 (produced-water flashing by pressure and salt) and Table 6-27 (shallow gas wells). A catalog name without a factor is rejected. | Exhibit 6-21: 18,250 bbl gives 0.259 t. |
| F5 | **Pneumatic Tier 1** offered "Pneumatic Controller – High/Low/Intermittent" (8.304 / 0.0939 / 0.4 t/yr), which are gas-processing and T&S values, to production sites. | Pneumatic Tier 1 now uses Compendium rows by segment: Table 6-14 continuous and Table 6-15 intermittent (API study and GHGRP), Table 6-16 chemical injection pumps, Table 6-29 G&B, Table 6-34 processing, Table 6-42 T&S. The mislabelled catalog rows are no longer offered. | 10 production high-bleed controllers: 22.5 t (Table 6-14: 2.25 t each). |

## Offered but could not be saved

| # | Finding | Fix | Check |
|---|---|---|---|
| F1 | **Factors listed by the form but unknown to the server** ("No emission factor found"):<br>• Combustion: 13 of 31<br>• Flaring: 7 of 13<br>• Mobile: 4<br>• Blowdown: 3<br>• Pneumatic: 5 | **Added on the server with Compendium values:**<br>• Propylene, butane, isobutane, naphtha, ethanol, biodiesel, lubricants, used oil, wood, tires: Table 4-5 (40 CFR 98 C-1) heating value and CO2; Table 4-6 CH4/N2O.<br>• Acetylene: Table 3-8 (1,470 Btu/scf, 92.3 wt % C).<br>• CNG and LNG: natural gas at standard volume.<br>• Pure-gas flares (propane, butane, ethylene, propylene): Eq 5-3 carbon balance at 98 %, N2O by Eq 5-6.<br>**Removed from the client:** the invented blowdown, pump and "Pneumatic Device" rows (no source). Blowdowns and pumps are now Compendium rows. | Every factor in the five lists saves (201). |
| 6 | **Loading Losses Tier 1** always failed with an internal message. | Loading uses the Table 6-47 rows only; the unsourced catalog rows were removed. | 10^6 bbl gives 5.73 t (0.91 t TOC/10^6 gal × 15 % CH4). |
| 7 | **Routine, Non-Routine and Safety Flaring Tier 1** showed an empty factor list. | These variants now list the flaring factors. | All 10 flaring factors save under Routine Flaring. |
| 8 | **Chemical, Nitric, Adipic and Asphalt** said "Please select a unit" while the unit box showed "tonne". | The product and unit shown by default are now written into the form data. | Submits on the first try. |
| F6 | **The unit list was not filtered by factor** (coal offered m3, gases offered kg and events). | Units are filtered by the factor's heating-value basis (gas, liquid or solid). | Coal: kg / ton / tonne only. |

## Displays and exports

| # | Finding | Fix |
|---|---|---|
| 10 | **OGMP export.** Loss rate 161,966 % against 3.479 % on the Methane page. The export read raw `gas_amount`; the page uses gross gas. Reconciliation said "PASS – within acceptable variance" with no survey. The roadmap tab showed "Level 3" against "Level 2" in the summary, with a hard-coded 2026. | Same gas definition as the page (`production_gas_m3`). "NOT ASSESSED" when there is no top-down measurement. The roadmap uses the summary's level and the reporting year. |
| 11 | **Excel export.** The Scope 2 steam row read "Grid Electricity, 0 kWh", and the totals row added quantities in different units. The PDF report had the same steam problem: it read tonnes of steam where MMBtu is stored. | Shared helper `services/scope2_activity.py`: 1,000 MMBtu, "Purchased steam / heat". Quantity total removed; Scope 2 is labelled "indirect energy". |
| 12 | **PDF export.** Large quantities printed over the fuel column, and names were cut to 12 characters. | Text cells wrap; quantities of 10^7 and above print in scientific notation. |
| 13 | **Library-factor records** showed the fuel as "2" (the factor id) and the type as "Specific". | The factor name is stored, and older records are resolved when listed. The type shows "Custom" (or "Tier 2" for site properties). Activity-row records store their source label. |
| 14 | **SBTi:** "Current year target 0 / Actual 0 (2026)". | The target is taken from the pathway (139,500 t), and the actual shows year-to-date for a partial year. |
| 15 | **WEC card:** a green "$0" when all years are selected. | Shows "—" with "Select a single year". |
| 16 | Fugitive Tier 1 units | **Not a bug.** My script read the list before switching the facility type. |
| D3 | **Filters stacked vertically** on Carbon and Methane Intensity when those pages were loaded directly: the filter CSS only came with the Dashboard. | Shared `TopBarFilters.css`, imported by all three pages. |
| D5 | **QA/QC:** "0 flagged" while the queue listed one record. | Stored-scan outliers are now counted. |

## Audit trail and data integrity

| # | Finding | Fix |
|---|---|---|
| 17 | **SQLite reused a deleted record's id**, so the audit "Ref #98" pointed at two records. | `id_guard.py`: an id high-water mark per table on SQLite, seeded from ids already in the audit log. It is one atomic write per insert, and the concurrency test passes 5 of 5 runs. PostgreSQL sequences never reuse ids, so it is not affected. |
| 18 | **Scope 2 entries left no audit row.** The commit only ran for pending records, updates were never logged, and bulk import called an unimported function. | Commits for every status; updates are logged; the import was fixed. |
| 19 | **Audit times were 2 hours behind** ("2h ago" for new events): naive UTC timestamps were read as local time. | `iso_utc()` sends an explicit +00:00. The hash chain's string format is unchanged. |

## Minor

- **Drafts in the Pending Review queue:** drafts are excluded until submitted.
- **"Goal exceeded" notification kept its first total:** the unread notice is now updated.
- **Glycol Dehydrator and AGR** are now also listed under Upstream.
- **Calculation-details popup:** Escape closes it, and it shows the process name instead of the internal key.
- **Dialogs:** they have `role="dialog"`, `aria-modal` and a label, and close on Escape.
- **Scope 2 table showed "—" for uncertainty:** the list endpoint now returns uncertainty and status.
- **"1KkNm³" dashboard label:** now reads "1,006 kNm³".
- **Found while fixing:**
  - In `add_emission`, a local `from flask import current_app` turned every earlier error path into an UnboundLocalError. Removed.
  - The dispatcher skipped activity rows for processes without a calculator. Now routed.

## Not changed

- The 2025 Master Report (user request).
- **Existing records keep their stored values** (data policy: formula fixes apply to new data). The following are corrected only when the record is edited and recalculated:
  - record 9 (660,430 t, oil-based mud);
  - the zero-emission acetylene, propylene, isobutane and pneumatic records;
  - the earlier separator records.

## Tests

- **New regression suite:** `tests/test_browser_exploratory_fixes.py`, with 45 cases derived from the tables and exhibits above.
- **Backend:** 1,684 passed, 0 failed.
- **Validation:** 128 passed.
- **Client:** vitest 24/24, build OK, lint 0 errors (40 existing warnings).
- **Browser re-run (fresh database copy):**
  - every Tier 1 factor in Combustion, Flaring, Routine Flaring, Mobile and Blowdown saves;
  - activity forms: pneumatics, loading, separation;
  - drilling and the chemical forms;
  - SBTi, WEC, filter layout, QA count, Scope 2 uncertainty, library-factor label, Escape on dialogs, drafts out of the queue;
  - audit times ("2m ago" at the right local time).
