# Fix plan: GB RY 2022 validation findings (GB-001 to GB-061)

Source: `GB_VALIDATION_RY2022/FINDINGS.csv` (72 rows: 61 platform findings, 11 errors in the report itself) and
`docs/validation-gb-ry2022.md`.

Ground rules, carried over from the previous audits unless a decision below changes them:
- One batch per area. Each fix gets a regression test whose expected value is worked from the standard or from the
  report, never read from the engine.
- Stored records are not recalculated (code only).
- The full backend suite, the validation suite, the client checks (`lint`, `typecheck`, `check:ts`, `lint:css`,
  `ui:metrics`, `test`) and `loc_ratchet --check` are green before each commit.
- Earlier decisions stand and are not reopened here:
  - BOE uses 5,647.52 scf/BOE (calc audit Q3).
  - The location-based method uses the catalog grid factor and a supplier factor is market-based only (BA-007).
  - There are two methane KPIs, NGSI and OGCI/OGMP (BA-053/054).
  - Marketed gas = gross - injected - flared - vented - fuel - shrinkage (BA-053).
- Errors in the report itself (GB-R01 to GB-R11) are not platform work. They go back to the report's authors as a
  list (see the last section).

At the end:
- `tests/test_gb_inventory_ry2022.py` is updated so each fixed difference becomes a "matches the report" check.
- The Phase 2 script (`scripts/gb_ry2022_phase2_csv.py`) and a browser re-run on a fresh database are repeated.
- The findings tracker gets an `outcome` per row: fixed / no change (documented) / decision.

## Status (2026-11-21): batches 1 to 7 done

Regression tests: `tests/test_gb_ry2022_fixes_batch1.py`, `_batch2.py`, `_batch3_7.py`; client
`src/__tests__/GasCompositionFlareDefaults.test.tsx`, `OtherSourcesForm.test.tsx`. Migration `n9e4a2b6c1d7`
(facility gas, flared split, partner archive, `grid_factors`). Note for the report's authors:
`docs/validation-gb-ry2022-report-authors-note.md`.

Where the implementation differs from the table below:
- **GB-036:** the server still accepts a lone CH4 content on a Tier 3 flare. That is the 2026-10-22 decision (a CH4
  content is a content, not an analysis) and golden case A02. The Tier 3 flare **form** now requires the full
  analysis (C1 to C10, CO2, N2 at 99.5 to 100.5 %), which is where the GB-036 error was made.
- **D4 "year nearest":** a record uses the most recent vintage **at or before** its reporting year (the earliest
  one when none is earlier). The GHG Protocol uses the inventory year's factor or the latest published before it, and
  a 2024 factor did not exist in 2022. HBNS 2022 therefore gets IEA 2019 0.419 and reproduces 57,165.28 t.
- **GB-022 / D5:** a file's total production that includes reinjected gas is no longer refused when the row gives the
  injected volume; the intensity uses the total excluding reinjected gas.
- **GB-012:** no code change; the CO2 basis is documented in `docs/calculation-specification.md`.
- **GB-050:** no change (IPCC 2006 Table 2.12 N2O uncertainty, BA-052).

---

## Decisions (all answered 2026-11-21)

| # | Question | Findings | Decision |
|---|---|---|---|
| D1 | Git | all | **Decided 2026-11-21:** straight on `main`, one commit per batch, push only when asked |
| D2 | Flare N2O default | GB-001, GB-019 | **Decided 2026-11-21: do exactly as the API Compendium says.** That is Eq 5-6 (E_N2O = E_CO2 x EmF_N2O / 60) with the December 2025 corrected defaults: 1.0e-4 kg/MMBtu for natural gas and 6.0e-4 for fuel gas (corrections p.2, which replace the printed 1e-3 / 3e-3). The code already does this when no factor is entered. A catalog fuel's N2O must not replace Eq 5-6. SANGEA's 3.716e-5 kg/Nm3 is not a Compendium 2021 method: documented difference |
| D3 | Location-based Scope 2 with a factor the user can cite | GB-003, GB-021 | **Decided 2026-11-21: follow the GHG Protocol Scope 2 Guidance exactly** (see the rules below) |
| D4 | Algerian catalog grid factor | GB-003 | **Settled by D3:** the MEM 2024 factor stays as one dated national-production factor, and the IEA national factor is added as another. The one used is the best level of Table 6.2 whose year is nearest the reporting year |
| D5 | BOE denominator for CO2e/BOE | GB-005, GB-025, GB-039 | **Decided 2026-11-21: follow the standard exactly.** API Guidance Document for GHG Reporting 2.0 (Jan 2023, after IPIECA-API-IOGP 2020): operated basis = gross (wellhead) production of crude, condensate, NGLs and dry gas, including flared gas and gas used for fuel, excluding gas reinjected into the reservoir (s4, operated); equity basis = liquids and gas produced as reported in financial disclosures, i.e. marketable gas as sold, flared / injected / own-use gas omitted (s4, equity). The platform's operated basis already excludes reinjection; the report's headline (incl. reinjected gas) is not the standard basis (its Appendix B 0.032 t/BOE is). Fixes: no silent drop of an entered total (show it with a warning), the 1.3 % message, and the equity-share consolidation uses the marketable (saleable) production as its denominator |
| D6 | Gas BOE conversion | GB-005 | **Settled by calc-audit Q3:** 5,647.52 scf/BOE (Compendium Table 3-4); the API guidance does not set another. GB-005 HHV basis: documented difference |
| D7 | NGSI inputs | GB-004, GB-024 | **Decided 2026-11-21:** per NGSI Protocol v3, the facility's own gas methane content (mol %) and heating value (Btu/scf) are used when entered; when nothing is entered, the NGSI defaults (1.235 MMBtu/Mscf; 83.3 / 87 / 93.4 %). The page shows which values were used |
| D8 | Annual activity records | GB-032, GB-039 | **Decided 2026-11-21:** monthly records only; a year is the sum of its months (already how every yearly total works). Remove the production form's "Annual / Whole Year" option and say in the forms and template that annual-only data goes into one month |
| D9 | JV partners | GB-028 | **Decided 2026-11-21:** admins add, edit and archive partners (name, code, country, operator flag) in Manage Data, every change audited; demo partners seeded only in demo installs |
| D10 | Approving custom factors | GB-033 | **Decided 2026-11-21 ("make them acceptable by the admin"):** an admin may approve custom factors, their own included (second-approver default changed to allow admins; every approval audited). Factors of users / superusers still need a superuser or admin. Account creation unchanged |
| D11 | Mobile factors with a custom fuel | GB-020 | **Decided 2026-11-21: follow the Compendium exactly.** Section 4.6.1: CO2 comes from the fuel (carbon content, or HHV x the fuel factor, so a custom fuel factor gives the CO2); CH4 and N2O come from Table 4-16 by vehicle / mode (or a CH4 mass balance). So whenever a vehicle type is chosen, Table 4-16 CH4 / N2O are applied at any tier, and the custom factor supplies the CO2 only |
| D12 | Facility-level leak factor for gas plants | GB-006, GB-060 | **Decided 2026-11-21:** add Compendium Table 7-34 (natural gas processing plants: 99.2 lb CH4 / 10^6 scf processed = 4.507e-2 t CH4/MMscf at 86.8 % CH4; or 22,984.25 kg CH4 per plant-year), scaled to the gas CH4 content, in the form, CSV and API, labelled as the screening (facility-level) method |

**Rules D3 / D4 apply, from the GHG Protocol Scope 2 Guidance (2015, corrected 2025):**
- **Location-based = grid-average factors only** (s4.1.1, s6.5). A supplier or utility-specific rate is
  market-based data, even from a sole utility (s4.1.1), so BA-007 stays.
- **Table 6.2 hierarchy, most precise first:**
  1. regional / subnational grid average (eGRID subregion, Defra)
  2. national production factor (IEA national, national statistics)
- **Factors are combustion-only (direct)**, in t per MWh or kWh, and their CO2 / CH4 / N2O are applied. The April
  2025 correction notes that IEA publishes CH4 and N2O.
- **Pick the most appropriate, accurate and recent factor** (s6.5, data quality: geographic and temporal
  representativeness). The delay between the generation year and the publication year is reported (s6.10).
- **Implementation:**
  - The grid catalog gets a `level` (regional / national), `data_year`, `source` and gases per entry. Admins can add
    cited grid-average entries in Manage Data (maker-checker, source required, labelled "grid average" only;
    supplier rates are refused there).
  - Resolution for a record: the facility's grid region (regional level) first, else its country's national
    factor, choosing the entry whose year is nearest the reporting year.
  - The record stores the factor's name, level, year and source.
  - The Algerian grid gets the IEA national factor (the report's 0.419 t CO2/MWh, IEA 2019, with its CH4 / N2O)
    next to the MEM 2024 derivation. RY 2022 then resolves to the year-nearest entry.

---

## Batch 1: security and data integrity (do first)

| ID | Fix | Where | Test |
|---|---|---|---|
| GB-016 | File import of custom factors goes through `services.custom_factor_policy.governance` like the form and the JSON import: status Pending, source required, bounds / justification; approval as decided in D10 (an admin may approve their own) | `background_processor._process_row_custom_factors` | CSV import by an admin leaves the factor Pending with its source checked; approval recorded in the audit log |
| GB-036 | A Tier 3 flare with neither a composition (C1..C10), a carbon content nor an entered CO2 factor is refused ("needs the gas composition"), instead of CO2 from methane only | `calculations/dispatcher_branches_combustion.calc_flaring` / `FlaringCalculator` | Form payload with CH4 % and HHV only returns 400 / 422 |
| GB-023 | Marketed-gas deductions take vented volume only from volume-based venting records (metered / vented-gas volume), never from activity-factor rows whose quantity is a throughput (Table 6-39 MMscf processed, counts, events) | `services/intensity.py` (`_add_scope1` vented_m3, line ~285) | HBNS case: marketed gas > 0, loss rate computed |
| GB-044 | The Methane page header shows Compliant / Non-compliant only from computed loss rates; "Pending production data" when none | client Methane Intensity page | Vitest: no "Compliant" badge with blank loss rates |
| GB-046 | `unit` required for every tier when a quantity is given | `services/scope1_calc.validate_activity`; client resets the Unit picker consistently | API: Tier 3 without unit returns 400 |
| GB-058 | Confirmation toast names the facility and month. Region stays (convenient) but is visibly highlighted after submit | client Scope 1 / 2 forms | Vitest snapshot of toast |
| GB-027 | Facility import: an equity share under 50 % without `operator_status` no longer flips the facility silently. Keep the status and add a job warning ("set operator_status if not operated") | `background_processor._process_row_facilities` | Import 21.2 % keeps `operated`, warning listed |

## Batch 2: calculation engine

| ID | Fix | Where | Test |
|---|---|---|---|
| GB-001 / 019 | Per D2: Eq 5-6 with the corrected defaults stays the method (no change to the default). A catalog fuel row (e.g. "Natural Gas", whose Table C-2 N2O is 1e-4 kg/MMBtu x HHV) no longer replaces Eq 5-6 on a Tier 3 flare; only a factor the user enters (measured / site, the form's N2O field or an `n2o_factor` CSV column) does. GB-001 outcome: documented difference from SANGEA | `calculations/combustion.py` (N2O block ~629), `flare_defaults`, `background_processor`, `scope1_template` | HBNS HP flare: 0.197 t with and without fuel "Natural Gas" (Eq 5-6, natural gas, worked by hand: combustion CO2 x 1e-4 / 60); `fuel_type` "fuel gas" gives x 6 |
| GB-002 | Tier 1 "Diesel" on a stationary engine: add catalog rows "Diesel - IC engine" (Table 4-11 TOC x 9 %) and "Diesel - large bore", and a hint in the form | `emission_factors` catalog, form hint | Diesel ICE 399.9 m3 gives 0.2076 t CH4 at Tier 1 |
| GB-007 | Catalog row "Aviation Gasoline" (Table C-1: 69.25 kg/MMBtu, 0.120 MMBtu/gal, type liquids) and its link to `vehicle_type=aviation_gasoline` | catalog, `mobile_factors` | 562,880 L gives 1,235.7 t CO2, 1.238 / 0.129 t CH4 / N2O |
| GB-008 | Accept `liters`, `litres`, `litre` (and `Liter`) everywhere liquid units are read | `calculations/units`, `mobile_factors.LIQ_TO_GAL`, `combustion_methods.LIQ_TO_GAL` | parametrised unit test |
| GB-009 | `legacy_engine` passes `gwp_standard` to `dispatch()` so the provenance trail names the GWP used | `calculations/legacy_engine.py:205` | lineage lists GWP-003 for AR4 |
| GB-015 / 018 | One turbine N2O factor. Table 4-11 0.0013 t/10^12 J = 1.3716e-6 t/MMBtu (exact). Align the catalog row "Natural Gas - Turbine" (1.3608e-3 kg/MMBtu) or document which table each cites | `emission_factors`, `combustion_methods.EQUIPMENT_FACTORS` | both paths give the same turbine N2O |
| GB-017 | Tier 3 combustion accepts equipment CH4 / N2O factors next to the composition in the API and CSV (`ch4_factor`, `n2o_factor`, unit kg/MMBtu), as the form already does. The catalog row "Natural Gas - Heater/Boiler" N2O is reviewed against Table 4-9 (low-NOx 2.8e-4 vs C-2 1e-4) and its label says which applies | `background_processor` / template, catalog | CSV heater row gives N2O 0.347 t |
| GB-020 | Per D11: `vehicle_type` applies Table 4-16 CH4 / N2O at Tier 2 / custom too | `calculations/mobile_factors.apply_mobile_factors`, legacy custom path | Tier 2 aviation row gives 1.234 / 0.129 t |
| GB-026 | Salt content "20%", "20 %", 20, 20.0 all read as the 20 % row. Normalise before the method | `vented_production_tank._produced_water_factor`, `background_processor._percent_text_to_number` | parametrised |
| GB-012 | Check the Table 6-39 CO2 scaling (CO2 per MMscf against the gas CO2 content) against the printed table; fix or document | `calculations/activity_factors.py:145` | value from the table by hand |
| GB-006 / 060 | Per D12: `fugitive_facility` gains `facility_type=gas_processing` (Table 7-34, per MMscf or Mm3 processed, or per plant-year with the period) | `calculations/fugitive_onshore.py`, client Tier 1 facility types, template | 194,132.66 MMscf x 0.04507 x 68.4 / 86.8 = 6,895 t CH4 (by hand) |
| GB-010, 011, 013, 014 | No code change: document (Table C-1 gasoline, 60 F standard volume, Table 6-26 rows, BOD5 required) in `docs/calculation-specification.md` | docs | none |

## Batch 3: Scope 2

| ID | Fix | Where | Test |
|---|---|---|---|
| GB-003 / 021 | Per D3 / D4: the GHG Protocol Table 6.2 hierarchy with dated, cited grid-average entries (catalog plus admin-added, maker-checker), year-nearest resolution, stored factor provenance; IEA national factor for Algeria added. Market-based: a supplier factor stays market-based; its CH4 / N2O are applied when the instrument gives them | `electricity_factors`, `services/scope2_policy.py`, `routes/scope2.py`, `background_processor._process_row_scope2`, Manage Data UI | 136,270 MWh at 0.419 / 8.0e-6 / 1.0e-6 gives 57,165.28 t CO2e location-based |

## Batch 4: intensity, methane and flaring KPIs

| ID | Fix | Where | Test |
|---|---|---|---|
| GB-022 | Production consistency message prints the real percentage (diff x 100). Rule per D5: total incl. injected gas is accepted when the intensity basis says so | `background_processor.py` ~2550, `services/dashboard_filters.validate_production_mmboe_consistency` | message says 128.3 % |
| GB-005 / 025 / 039 | Per D5: operated intensity = Scope 1+2 / gross wellhead production excluding reinjected gas (today's basis, labelled "API 2023 operated basis"); an entered total outside tolerance is kept and flagged, never replaced silently; with equity-share consolidation the denominator is the equity share of marketable (saleable) production | `services/dashboard_filters.production_boe`, `services/intensity.py`, `services/consolidation.py`, client Performance page | HBNS operated 1,061,969 / 33.27 MMBOE = 0.0319 t/BOE (report Appendix B 0.032); equity uses saleable_production_mmboe |
| GB-004 / 024 | Per D7: facility fields "gas CH4 content (mol %)" and "gas HHV (Btu/scf)". `_methane_loss` passes the analysed content to `ngsi_ch4_content`, and `gas_ratio` uses the HHV when given | `models.Facility` (migration), `services/intensity.py:449`, `services/methane_intensity.gas_ratio` | HBNS 0.141 %, El Merk 0.176 % |
| GB-044 / 061 | One NGSI figure everywhere (Methane page = per-facility API). The flaring rate states its denominator and uses gross gas (or offers flared / BOE, Table E-5 style). The regional benchmark renders when data exist. The OGMP level rule is explained in the UI and the two sites' 3 vs 4 is checked against the materiality rule | client Methane page, `services/intensity.py`, `dashboard_flaring` | Vitest and API values agree |
| GB-054 | Production form and CSV take routine / non-routine / safety flared volumes; the dashboard split uses them when records are unclassified | `models.ProductionData` (migration), form, import, `dashboard_flaring` | HBNS split 23.107 / 33.061 / 11.977 |
| GB-055 | Fire suppressant shown under "Other sources", not Equipment Leaks | `routes/dashboard.py` category map | category test |

## Batch 5: CSV import and template

| ID | Fix | Where | Test |
|---|---|---|---|
| GB-031 | Template gains the columns that already work: `combustion_method`, `equipment_type`, `activity_key`, `agent_type`, `wastewater_method`, `bod5_mg_l`, `cod_kg_m3`, `n_effluent_mg_l`, `ch4_factor` / `n2o_factor` (+ units), `n2o_factor` for flares. The processes `fire_suppression`, `wastewater`, `refrigerant`, `electrical_equipment` are added; `fugitive_method` lists `equipment` | `services/scope1_template.py` | template coverage test (`test_scope1_coverage_gaps`) |
| GB-029 | Skip-reason grouping does not match on the word "facility" for method errors; titles keep chemical formulas (no digit to N inside CH4, N2O, m3, Table numbers) | `services/import_feedback.py` | unit tests |
| GB-030 | The file check summary shows period / facility / process counts only for emission imports | `background_processor._preview_summary` | facilities check has no "unknown process" |
| GB-032 | Per D8 | import, forms, models | |

## Batch 6: browser forms and UI

| ID | Fix | Where |
|---|---|---|
| GB-035 | Gas calculator, flaring mode: separate "carbon to CO2" (default 98 %, per CLAUDE.md flare rule) and "CH4 destroyed" (default 98 %) instead of one oxidation factor of 0.965 applied to both. Applied factors no longer make the form ignore its efficiency fields: the form's efficiencies win, or the applied values fill them | `client/src/components/GasCompositionCalculator.tsx`, `scope1/SectionMethods.tsx` |
| GB-037 | Activity-factor venting (Table 6-39 and the other per-throughput rows) shows CH4 % and CO2 % fields | client Scope 1 form |
| GB-038 | Gas units Nm3 and Sm3 (15 C) offered and converted by the server (`NM3_TO_SM3`; Sm3 15 C to 60 F) | client unit lists, `calculations/units.py` |
| GB-040 | Production form resets every field when opened for a new record; "Gas (MMBOE)" is stored (`gas_mmboe` column) or removed | client production form, model |
| GB-041 | Facility form: Country field (default from settings), labels "Region" / "Facility (field / block)", no pre-fill from the list filter, Edit action in the list | client Regions page |
| GB-042 | Settings page clears its "unsaved" state after the confirmed GWP change | client Settings |
| GB-043 | Scope 1 preview and Master Report wizard read the active GWP standard | client |
| GB-045 | Scope 1 form: Fire suppression, Wastewater (aerobic / anaerobic / IPCC), Refrigerant, Electrical equipment processes with their method inputs | client Scope 1 form |
| GB-047 | Custom factor form keeps its values and shows the server error inline on 4xx | client |
| GB-048 | Remove or route the polled `/api/qa/dashboard` and `/api/ogmp/surveys` calls | `client/src/components/NotificationCenter.tsx` |
| GB-049 | Picker component exposes `role=option` / `aria-selected`, typeahead; icon buttons (approve, delete share) get accessible names | `client/src/ui` Select component |
| GB-050 | Fuel list shows the catalog uncertainty correctly (no ±900 %) | client fuel picker / catalog uncertainty field |
| GB-051 | Calculator: inputs C7, C8, C9, C10+ (iC4 / nC4, iC5 / nC5 kept); "N2O" removed from gas components; applying does not overwrite CH4 / N2O factors already typed (asks first) | `GasCompositionCalculator.tsx` |
| GB-052 | Admin submit toast says "Saved as Verified" when the record is Verified | client |
| GB-053 | Master report basin list built from facilities only (no "Demo Operator Group") | `routes/reports_master.py` /master-report/regions |
| GB-059 | Produced-water rows (Table 6-26) also listed under "Storage Tank - Flashing/Events" | client process / source lists |

Tests: Vitest per component change; Playwright smoke for the Scope 1 flare and production forms (`e2e/`), run
against a fresh DB.

## Batch 7: accounts and JV

| ID | Fix | Where |
|---|---|---|
| GB-028 | Per D9: `POST / PUT / DELETE /api/equity/partners` (admin), audited; Manage Data partner list editable; demo partners only seeded in demo installs | `routes/equity_routes.py`, client JV dialog |
| GB-033 | Per D10: `CUSTOM_FACTOR_SECOND_APPROVER` defaults to allowing an admin to approve their own factor (audit entry names it a self-approval); CLAUDE.md and the custom-factor policy docstring updated | `services/custom_factor_policy.py`, `routes/custom_factors.py` approve |

## Errors in the report (no platform change)

GB-R01 to GB-R11 are compiled as a one-page note for the report's authors (Groupement Berkine / Oxy HSE):
- E-9 / 27 headers
- El Merk processed gas 194,132.66 → 140,012 MMscf
- El Merk on-road row
- the duplicate Flare-AP row
- the leak-row CO2 cell
- the typos
- Table 13 columns
- EMK HP well-site flare composition
- the Appendix B BOE
- the STP CO2e
- the SANGEA version
- the headline CO2e/BOE (0.0147 / 0.0190) includes reinjected gas, against the API 2023 operated basis (D5); its Appendix B 0.032 is the standard figure
- the flare N2O and NGSI figures follow SANGEA / own gas values rather than Compendium Eq 5-6 and the NGSI defaults (D2, D7)

The platform's own figures for those rows are attached.

## Order and size (rough)

1. **D1 to D12 answered (2026-11-21).**
2. **Batch 1, about 1 day.** Security and integrity first.
3. **Batch 2, about 2 days.** Engine.
4. **Batch 3, about 1 day.** Needs D3 / D4.
5. **Batch 4, about 2 days.** Two migrations: facility gas fields, production flaring split.
6. **Batch 5, about 1 day.**
7. **Batch 6, about 3 days.** Client.
8. **Batch 7, about 1 day.**
9. **Re-run the three validation phases.** Update the tracker outcomes and the findings page.
