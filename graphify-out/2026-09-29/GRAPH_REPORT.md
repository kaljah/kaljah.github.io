# Graph Report - H2  (2026-09-29)

## Corpus Check
- 1335 files · ~4,027,560 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 12401 nodes · 19708 edges · 918 communities (806 shown, 112 thin omitted)
- Extraction: 93% EXTRACTED · 7% INFERRED · 0% AMBIGUOUS · INFERRED: 1300 edges (avg confidence: 0.52)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `3f7a96b9`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- Facility
- calculate_co2e
- extensions.py
- CalculationDispatcher
- background_processor.py
- dashboard.py
- test_browser_exploratory_fixes.py
- test_tier_scope_kpi_numerical.py
- routes/scope2.py
- auditlib.py
- MudDegassingCalculator
- parse_number
- CompletionFlowbackCalculator
- reference_model/__init__.py
- App.jsx
- Backend (Server)
- test_independent_differential.py
- Frontend (Client)
- K/lib.mjs
- sqlite3
- Scope1Form.jsx
- compute_emissions
- log_activity_and_notify
- server/app.py
- resolve_tier
- test_tier3_browser_findings.py
- has_table
- useToast
- DistributionNonRoutineCalculator
- combustion_methods.py
- sql
- DehydratorCalculator
- Authentication and User-Specific Database Implementation Walkthrough
- TestRegressionArchive
- ghg_tool/app.py
- Comprehensive Gap Analysis: SolarEPC-Pro
- test_onshore_well_completions_audit.py
- 75f2d6f4-9958-4818-85e3-afee007ac5ca/implementation_plan.md
- Scope1ImportWizard.jsx
- Solar PV Calculator - Complete Feature Implementation Plan
- 2. Calculation Inventory by Type
- test_audit_rc6_scope1_paths.py
- CSV Spreadsheet Pro - Enhanced Features Walkthrough
- 4. Formal Specifications for Scope 1 Direct Emissions
- Master Calculation Register
- Master Calculation Register
- LiquidsUnloadingCalculator
- AUDIT_FINDINGS.md
- TestAllProcessTypesTier3
- test_associated_gas_venting.py
- models.py
- test_aggregation_reconciliation.py
- ui_format_number
- Detailed Implementation Walkthrough
- antigravity_guide/SKILL.md
- k_uilib.mjs
- TestBoundaryConditions
- Reports.jsx
- ref_co2e
- TestOATSensitivity
- devDependencies
- dependencies
- test_audit_rc14_schema.py
- session
- DashboardEnhanced.jsx
- 5. CHANGELOG & DRIFT LOG
- 4. Critical Observations
- test_deep_injection_matrix.py
- test_it_role_security.py
- ._run
- Tasks: [FEATURE NAME]
- Tasks: [FEATURE NAME]
- Feature Specification: QA/QC Module (IPCC & ISO 14064 Compliant)
- sleep
- 🎨 HIGH-TIER 3D CAD RENDERING COMPLETE!
- BUG-070 — POST /api/emissions/reject/<id> has no status check: a superuser can flip an admin-Verified record to Rejected (removing it from all totals) and overwrite its approver
- test_uncertainty.py
- make_user
- reports.py
- test_qfull_unit_conversions.py
- Feature Specification: Batch Approve/Reject Pending Records
- PVGIS Data Analyzer - Walkthrough
- Comprehensive GHG Engine & MRV Platform Independent Validation Report
- CCUSVentingCalculator
- README.md
- Proposed Changes
- Dashboard Categorical Overview Fixes - Walkthrough
- Complete CAD/Design View - All 12 Gaps
- CAD Enhancements: Dimensions & Module Overlay - Complete
- 🎨 SolarEPC-Pro UI/UX Enhancement - Complete
- custom_factors.py
- test_stress_boundary_resilience.py
- test_production_smoke.py
- UI
- Solar PV Calculator - Advanced Features Implementation Summary
- 3. Security, Authorization & RBAC
- TestCalculationMutations
- TestStatisticalZScoreAndIQRBattery
- Examples
- TestCombustionTier1
- SolarEPC-Pro v3.0 - Complete Implementation
- RTK Commands by Workflow
- get_active_gwp
- test_audit_remediation.py
- test_audit_rc11_sbti.py
- CAD/Design View - Gap Analysis
- IMPLEMENTATION_PLAN.md
- SectionMethods.jsx
- emission_factors_routes.py
- What Will Be DELETED
- Performance Optimization Walkthrough
- 🎉 ALL CAD FEATURES COMPLETE - 12/12 IMPLEMENTED!
- Phase 1 — Testing Inventory
- FINAL VALIDATION REPORT
- Tier 3 browser test — every Scope 1 process type (2026-09-28)
- audit.py
- Exploratory browser test — findings and fixes (2026-09-28)
- test_audit_rc17_methodology.py
- L/lib.mjs
- toasts
- 4. HTTP & Application Layer Hardening
- test_audit_rc10_uncertainty.py
- dependencies
- Backend Components
- Database Contents
- Client Application & Routing
- Implementation: All 27 Gaps ✅
- GHGCalculator
- test_audit_rc9_dashboard.py
- test_all_bulk_imports.py
- new/.specify/scripts/powershell/common.ps1
- .specify/scripts/powershell/common.ps1
- TestCleanUncertainty
- BUG-046 — Equity-share allocation ignores effective dates (time-sliced ownership never applied) and POST /api/equity/shares accepts any percentage (500, -50, inf) from any business role
- Critical Bugs (Data-Affecting)
- CO & Combustion Efficiency Implementation Plan
- Comprehensive Database Architecture, ACID Integrity & Concurrency Audit
- Enterprise Production Readiness, Deployment & Disaster Recovery Audit
- Calculation Validation Report
- 3. Dimensional Consistency & Physical Equations
- .calculate_co2e
- test_audit.py
- TestPropertyInvariantsHypothesis
- test_audit_rc7_rc8.py
- BUG-091 — Dehydrator throughput entered under the label "MMscf/yr" is saved with unit "MMscf/day" (record activity unit 365× off)
- make_db
- Key Improvements
- Frontend UI
- 🎉 Final CAD Implementation Complete
- Proposed Changes
- 3. Subsystem Architecture Analysis
- Phase 49 — Human Review Required
- Complete Repository Audit & Architecture Baseline
- BUG-016 — Alembic migration chain is unusable: `flask db upgrade` fails on both the existing DB and a fresh DB
- BUG-011 — Well-completion "Rate × Duration" method divides the Mcf/hr rate by 24 (treats it as Mcf/day): CH4 understated 24×
- BUG-012 — Well-completion Tier 3 uses `amount` as both the flowback volume and the event count (volume squared), and ignores rate × duration when the method dropdown is left at its default
- BUG-023 — Tier 3 combustion/flaring gas composition: each component is converted percent→fraction on its own, so mol% values ≤ 1 (e.g. C4 = 1.0 %, C5 = 0.5 %) become 100 % / 50 %; CO2 inflated 2.7× on the app's own template sample
- BUG-027 — Tier 1 combustion applies the catalog HHV in the wrong basis when the activity unit is mass or the other phase (diesel/crude per tonne ×3.6, natural gas per tonne ÷40, ethane per scf ×39)
- BUG-047 — Tier 1 fugitive and equipment factors in "per hour" units are multiplied only by the source count (no operating hours): annual CH4 understated 8,760×, and Tier 1 disagrees with Tier 3 for the same factor
- BUG-048 — Tier 3 fugitive calculators misread catalog factor units: "CH₄" (Unicode subscript) is not recognised as methane (×0.85 applied), and ComponentFugitiveCalculator treats tonne/hr factors as kg/hr (1000× too low)
- BUG-049 — Generic factor math ignores the 10³ / 10⁶ multiplier in factor denominators: offshore gas fugitives 1,000,000× and refinery fuel-gas fugitives 1,000× overstated
- BUG-063 — Tier 2 custom factors whose unit is not "kg/<unit>" are misapplied (Manage Data form stores a bare activity unit): tonne factors ×1000 (×10⁶ with kg activity), no volume/mass conversion at all; unknown units such as kg/TJ or kg/GJ are applied 1:1
- BUG-110 — Onshore fugitives "Tier 1: Facility-Level" form: the on-screen preview says 16,644 tCO2e but the saved record is 1.456 tCO2e — the server ignores the selected facility type and duration and books the facility count as a count of valves
- BUG-090 — Dehydrator form sends "Contactor Pressure" as `dehy_pressure`, but the server reads `dehy_press`: user pressure silently ignored, 800 psig default always used (AGR "routed to flare"/"flash gas recycled" checkboxes also unread)
- BUG-003 — Editing a Scope 1 record's quantity via PUT /api/emissions/<id> does not recalculate emissions (stale `amount` from source_payload wins)
- BUG-030 — POST /api/emissions/ calculates from `quantity`/`fuel_type` but stores only `amount`/`fuel`: records keep emissions with NULL activity quantity and fuel
- BUG-037 — Editing a Scope 1 record replaces its propagated 1σ uncertainty with the raw catalog EF half-width (95 %, EF-only); user_uncertainty is stored unpropagated
- BUG-042 — Recalculating a Tier 2 (custom-factor) Scope 1 record drops the custom factor: emissions become 0 or silently switch to the catalog factor, while factor_source stays "custom"
- BUG-068 — Purchased steam/heat (`indirect_steam`) and CHP allocation (`cogen_allocation`) are accepted as Scope 1 process types and added to Scope 1 totals (Scope 2 counted as Scope 1; CHP double counting)
- BUG-024 — Tier 3 flaring/combustion renormalises the gas composition without N2 (and without unspecified components), inflating CH4 and CO2 by 1/(1 − x_inert)
- BUG-001 — Bulk upload job API lets any logged-in role (user, it_admin) create/overwrite facilities and custom factors, bypassing RBAC and region scoping
- BUG-051 — Energy activity units kWh / MJ / Btu with a kg/MMBtu factor are treated as scf of gas (× 1020 Btu/scf): 1000 kWh of natural gas is 3.3× too low, MJ 7.6 % too high
- BUG-050 — Negative activity amounts are accepted for process types that are not in the dispatcher (e.g. "loading") and saved as negative emissions
- BUG-013 — AR5 20-year GWPs are wrong (CH4 82.5 instead of 84, N2O 268 instead of 264); AR6 pairs the fossil CH4 GWP-20 with the non-fossil-weighted GWP-100
- BUG-005 — GWP-20 conversion in intensity-stats / intensity-trend hard-codes AR5 GWP-100 (28 / 265), so GWP-20 CO2e is wrong whenever the active standard is AR4 or AR6
- BUG-109 — Scope 1 form saves an entry with no Unit selected: the client silently assumes m³ (10 → 2,641.72 gal stored) while the server calculates from the raw 10 in calc_inputs, so the stored activity and its emissions disagree 264×
- BUG-091 — Dehydrator throughput entered under the label "MMscf/yr" is saved with unit "MMscf/day" (record activity unit 365× off)
- BUG-096 — Scope 2 form: switching Source Type to Steam/Heat or CHP leaves the hidden unit at "kWh" — dropdown shows "Select..." but the request sends unit "kWh" (1000 "MMBtu" of steam booked as 3.41 MMBtu)
- BUG-097 — CHP allocation form labels Power Output "MWh" but the server uses the number as MMBtu: heat share (and Scope 2 tCO2e) overstated ~2.7× with WRI efficiency method
- BUG-007 — Manual Scope 1 entry has no plausibility bound or QA flag: 9 test records (1e13 MMBtu gas, 1e15 t coal) make up about 99.99% of the snapshot's Scope 1 total (3.72e12 t Verified, 4.69e12 t Pending)
- BUG-029 — Manage Data page crashes for every user when any facility has a NULL name; POST /api/facilities accepts facilities with no name
- BUG-073 — Scope 2 and Scope 3 create accept a missing or non-numeric year: one year-less Scope 2 record makes the main dashboard (summary/batch-all) return 500, and year-less Scope 3 is in the total but missing from by-year
- BUG-015 — 43 Tier 1 factors offered in the Scope 1 UI do not exist in the server catalog; records save with HTTP 201 and 0 emissions
- BUG-085 — Scope 2/3 bulk import silently books rows with a blank or non-ISO date to January 2024, and stores a blank Scope 3 category as "Category "
- BUG-111 — Scope 1 bulk import books a row with a blank Unit as m³ and accepts year 1800, both of which the manual form/API reject
- BUG-112 — Custom emission factor with every factor field blank is saved (CO2/CH4/N2O = 0) and Tier 2 records that use it are stored with 0 tCO2e and no warning
- BUG-034 — SBTi target POST accepts NaN / Infinity (range checks pass for non-finite floats); trajectory endpoint then returns 500 or invalid JSON for all users
- BUG-039 — Emission goals API ("+ Set Target") has no value validation: negative, year 1, and NaN goals are accepted; a NaN goal for the current year makes the main dashboard batch return 500
- BUG-045 — "Add Region" (create facility) form fails with HTTP 500 unless the optional Latitude/Longitude fields are filled
- BUG-060 — Scope 2 manual entries and Scope 2 bulk imports by a superuser are auto-Verified, while Scope 1 and Scope 3 require admin approval (inconsistent maker-checker)
- BUG-070 — POST /api/emissions/reject/<id> has no status check: a superuser can flip an admin-Verified record to Rejected (removing it from all totals) and overwrite its approver
- BUG-074 — Approve/reject endpoints are not concurrency-safe: two simultaneous approvals of the same record both return 200 (duplicate audit entries; approve+reject race ends in an arbitrary final state)
- BUG-093 — Region-restricted superuser can re-region its own facility (PUT /api/facilities/<id>), pushing the facility and all its emissions into another region's scope and out of its own
- BUG-077 — Dashboard "Export Executive Brief (PDF)" in the default All-Years view reports every year and every Pending record as "FISCAL YEAR 2026" / "Total verified records": PDF total 8.41 T tCO2e vs 3.72 T on the dashboard
- BUG-032 — GET /api/manage/sbti ignores facility/region scoping: region-restricted users can read organisation-wide Verified emission totals for any year
- BUG-038 — Audit trail (/api/audit/, /api/audit/export) is not facility/region-scoped: a region-restricted superuser reads activity entries for every region's records
- BUG-046 — Equity-share allocation ignores effective dates (time-sliced ownership never applied) and POST /api/equity/shares accepts any percentage (500, -50, inf) from any business role
- BUG-076 — Bulk-upload job status and error CSV have no owner check: any logged-in account (incl. it_admin) can read another user's job rows; absolute server temp path is disclosed
- BUG-106 — User Management actions are missing from the Audit Trail: account creation and logout logs are never committed, and user deletion is not logged at all
- BUG-087 — Malformed input on create endpoints returns HTTP 500/409 with raw exception and SQL text (≈40 handlers return `str(e)`)
- BUG-057 — Bulk upload with "Overwrite Duplicates" enabled inserts every in-file duplicate row as a separate record (double counting)
- BUG-081 — Scope 2/3 bulk import duplicate key is too coarse: separate meters and sub-categories in the same facility-month are rejected as "duplicates", or with Overwrite they replace a different existing record
- BUG-089 — Scope 3 category is stored as "6" by the UI/API and as "Category 6" by bulk import: cross-channel duplicates are not detected (double counting) and category breakdowns split
- BUG-058 — Bulk-upload overwrite rewrites approved records without an audit trail and leaves them "Pending" but still marked approved
- BUG-020 — /api/reports/master-annual-report serves full annual GHG report PDFs to any logged-in role (incl. it_admin and out-of-region users) and returns a static, pre-generated file regardless of facility_id
- BUG-065 — Custom factor names are not unique, yet bulk import resolves factors by name: the most recently created same-named factor is silently applied
- BUG-056 — Custom factors used by Tier 2 records can be deleted: the reference check matches `fuel_type == factor name`, but UI records store the factor id, which SQLite then reuses for the next factor
- BUG-009 — Deleting a facility that has any OGMP level-upgrade log fails with 500 (FK violation) and leaks raw SQL
- BUG-010 — Deleting a user who created production data, SBTi targets or OGMP level logs fails with 500 (FK cleanup list incomplete)
- BUG-069 — Deleting a user wipes approved_by/created_by on every record they approved or entered: Verified records lose their maker-checker evidence
- BUG-044 — /granular-intensities (Master Report "Multi-Metric Intensities") divides all-facility emissions by only the facilities with granular MMboe fields, and fabricates NGSI methane (0.05 %) and saleable production (85 %)
- BUG-084 — QA/QC Dashboard shows "Zero Anomalies Detected… The inventory is fully verified and audit-compliant" with 149 Pending records and 11 records more than 10^6 × the median; the anomaly queue only lists a stored `qa_flag`, which is never computed for existing data
- BUG-002 — Reports "2025 Master Report (PDF)" button sends facility_id=[object Object]; facility selection ignored
- BUG-006 — Reports Excel/PDF exports drop the Division, Field, Method and Search filters shown on screen
- BUG-053 — CAP (air-pollutant) emissions bypass maker-checker: POST /api/cap/emissions stores records as "Verified" by default (client-controlled status) for role user; negative mass/concentration accepted
- BUG-113 — Reports "PDF Report" prints every unit and gas name with a missing-glyph box: "tCO■e", "CO■", "CH■", "N■O"
- BUG-031 — Facility OGMP 2.0 level counts Draft, Pending and Rejected emission records, so a rejected record can raise a facility's level
- BUG-052 — OGMP survey reconciliation status defaults to "Reconciled" whatever the computed variance; a +354 % discrepancy is stored and shown as Reconciled, and a zero bottom-up case is shown as "+0.0 %"
- BUG-075 — Sentinel-5P "Export to OGMP" stores a 1-hour CH4 mass as the survey's "estimated annual tCH4" (default operating_hours = 1): top-down understated 8,760× and reconciliation always flagged
- BUG-040 — Supply Chain filter is not applied to the emissions-by-source split: "Emissions by Source" donut and Detailed Breakdown rows show company-wide values (sources add up to 7× Scope 1)
- BUG-004 — Intensity activity/division filter uses record-level columns that are NULL/inconsistent, so numerator and denominator are filtered differently (Upstream intensity blank, E&P intensity 0.0)
- BUG-017 — Intensity with year="all" (default view) pairs each facility's emissions from every year with production from other years; KPI mixes periods
- BUG-026 — Flaring panel treats "All Years" as the current calendar year and ignores the Supply-Chain/Activity/Division/Preview-Pending filters, so it contradicts the dashboard it sits in
- BUG-094 — "Net Emissions" KPI subtracts company-wide mitigation whatever the Activity/Division filter (Steel & Iron view: Net = −1,027,393 t) and counts "Planned" projects as achieved reductions
- BUG-033 — Decree 21-330 flaring intensity (/flaring-summary) misconverts units: MMscf 1000× too low, scf/kscf 35× too high, UI "m³" gas production 28× too high; compliance verdict flips
- BUG-067 — Maker-checker bypass through edit and delete: a superuser can approve a record they just edited, silently re-date/re-assign Verified records, and a user can hard-delete their own Verified records
- BUG-036 — Flaring panel invents a 56 % / 40 % / 4 % Routine / Non-Routine / Safety split for generic "flaring" records and shows 0 tCO₂e for every stream (and a 2.5 t/kNm³ proxy when CO₂e is 0)
- BUG-054 — "Preview Pending Data" and the pending banner are inconsistent with the rest of the dashboard: the toggle changes only the KPIs (categorical/org breakdown and Scope 3 stay Verified-only), and the banner ignores the Supply Chain, Activity and Division filters and omits Scope 3
- BUG-041 — Dashboard "% GOAL" badge in the default All-years view divides the cumulative multi-year Scope 1+2 total by the single current-year goal (and ignores region/facility filters)
- BUG-061 — Dashboard "Emissions by Source" mis-classifies process types: fuel-gas combustion (6.47 M t) shown as "Other", pneumatics/tanks/dehydrators/unloading/completions as "Other" instead of Venting, fugitives merged into "Venting", mobile combustion labelled "Stationary Combustion"
- BUG-071 — Dashboard cache is not invalidated after a manual Scope 1 create or a bulk upload: new records are missing from the dashboard for up to 5 minutes (per worker)
- BUG-079 — OGMP reconciliation in the default "All years" view compares the AVERAGE of annual top-down surveys with the SUM of multi-year bottom-up CH4, so perfectly reconciled facilities are flagged (−80 %)
- BUG-064 — Categorical Emissions Overview groups facilities by name instead of id: six distinct facilities are merged into one "Updated Facility" card (3.19 T t)
- BUG-072 — Pending-records banner ignores the GWP-20 toggle: it always shows GWP-100 tCO2e while every other dashboard figure switches to GWP-20
- BUG-080 — Two contradictory OGMP facility-level algorithms: /intensity-stats reports Level 5 (Gold Standard) where the canonical service (/ogmp-metrics, OGMP export) reports Level 4 for the same facility and year
- BUG-086 — Methane loss-rate segment classification differs between the KPI cards, the trend chart and the server: "Downstream / Processing" counts as Midstream in the trend, and "Upstream / Extraction" is dropped from the Upstream KPI
- BUG-099 — Scope 2 electricity create trusts client-supplied `co2e` / `emission_factor`: 0 kWh can be booked as 12,345 tCO2e, negative Scope 2 (-500 t) is accepted, and any unknown grid region takes the client's factor
- BUG-088 — Facilities with CH4 emissions but no gas production get methane_loss_rate_pct = 0 and ogmp_target_status "Compliant"
- BUG-008 — Inventory uncertainty shrinks by √N when the same emissions are split into N records (shared EF uncertainty treated as independent)
- BUG-018 — Uncertainty dashboard applies max(u_CO2, u_CH4, u_N2O) to each record's total CO2e instead of CO2e-weighting the per-gas uncertainties
- BUG-025 — Meter (activity-data) and GC (composition) uncertainty inputs are accepted but silently ignored by every calculator
- BUG-043 — Stored uncertainty has no range or unit validation: Scope 2/3 accept percent values, negatives, NaN and 1e6, and the Uncertainty dashboard shows ±3600 %
- BUG-055 — QA Dashboard "IPCC Tier 1 Uncertainty" reports 1σ as ±%, uses only the CO2 column, and includes Draft and Pending records, so it contradicts the Uncertainty page
- BUG-062 — Uncertainty display inconsistencies: EmissionResult shows the ±1σ (68 %) band as the "Confidence Interval", Scope 2/3 tables use k=1.96 while everything else uses k=2, and the Uncertainty page badge thresholds contradict its legend
- BUG-014 — SBTi progress KPI uses the current, incomplete year (and any future year) as the "current" year, so the dashboard reports ~95-99% reduction and ON TRACK
- BUG-019 — SBTi "Scope 1+2 (Operational)" view compares Scope 1+2 actuals to the Scope 1+2+3 baseline and target line (inflated reduction %, false ON TRACK)
- BUG-028 — SBTi dashboard shows "ON TRACK — Reduction: 100% vs Baseline" when there is no verified data at all in the target window
- BUG-083 — Activity-data write endpoints accept "NaN" / "1e999" (±Infinity): a Scope 3 record with activity_data=Infinity makes /dashboard/batch-all, /scope3/summary and /api/scope3 emit invalid JSON ("Infinity")
- BUG-059 — SBTi target labelled "1.5°C" is not tied to its reduction rate (0.5 %/yr accepted and displayed as 1.5°C); arbitrary pathway strings and future base years accepted; main-dashboard banner hard-codes "SBTi 1.5°C Linear Target"
- BUG-092 — Maker-checker outcome is invisible to the maker: reject/approve send no notification, the Scope 1 list shows Rejected/Pending rows exactly like Verified ones, and the reject dialog claims the record is "permanently deleted" although it is kept as Rejected
- BUG-105 — Manage Data and Reference Data swallow API load errors and show them as empty data ("No production record found", empty factor catalog)
- BUG-107 — CustomDropdown is not keyboard-operable and form inputs have no programmatic labels: Region, Process Type, Emission Factor and Unit cannot be set without a mouse
- BUG-021 — Reports search keeps the current page number: "Total Records: 42 | Showing: 0" and no pager to recover
- BUG-095 — Scope 1 "Recent Activity": Export CSV exports only the 10 rows of the current page, and the Year/Process filter options are built from that page only
- BUG-115 — Manage Data forms discard the server's validation message and show a generic "Failed to …" toast (negative production, negative factor, facility 500, etc.)
- BUG-022 — Reports "Group By" selector has no effect (getGroupedData is never called)
- BUG-082 — Scope 1 "Live Equation Inspector" states "GWP Standard: IPCC AR6 (CH₄:28, N₂O:265)" — hard-coded, AR5 values mislabelled as AR6, ignores the org GWP setting
- BUG-098 — Emission Calculation Result panel rounds gas masses to 3 decimals of a tonne: non-zero CH4/N2O shown as "0.00 tonnes"
- BUG-114 — Logout does not invalidate the session: a session cookie captured before logout keeps full API access (client-side signed cookie, no server-side revocation)
- BUG-108 — Scope 1 entry form does not reflow at phone width (390 px): Field input, Tier selector and factor picker are clipped off-screen
- BUG-078 — Executive Brief / Master PDF prints hard-coded performance claims ("15.9 % reduction… on track for -30 %", "65.9 % methane reduction", "Lowest annual flaring on record (-38.0 %)", "VISR camera verified" DRE) regardless of the data
- BUG-066 — AGR form throughput units MMscfd / Mcf/day / m³/yr are ignored by the server (read as MMscf/yr): CO2 365× low, 2.7× high, or 28,317× high
- test_qfull_boundary_sensitivity.py
- test_bulk_uploaders.py
- make_facility
- BUG-069 — Deleting a user wipes approved_by/created_by on every record they approved or entered: Verified records lose their maker-checker evidence
- BUG-089 — Scope 3 category is stored as "6" by the UI/API and as "Category 6" by bulk import: cross-channel duplicates are not detected (double counting) and category breakdowns split
- BUG-110 — Onshore fugitives "Tier 1: Facility-Level" form: the on-screen preview says 16,644 tCO2e but the saved record is 1.456 tCO2e — the server ignores the selected facility type and duration and books the facility count as a count of valves
- AUDIT MEMORY (living document)
- _agentA_common.py
- build_plan.py
- Frontend Enhancements
- Global Responsive Design Optimization
- GHG Tracker - Major Feature Expansion
- CAD Enhancement: Sun Path Animation - Complete
- scripts
- a11yAndErrors.test.jsx
- BUG-062 — Uncertainty display inconsistencies: EmissionResult shows the ±1σ (68 %) band as the "Confidence Interval", Scope 2/3 tables use k=1.96 while everything else uses k=2, and the Uncertainty page badge thresholds contradict its legend
- emissions.py
- compute_scope3_co2e
- extract_val
- Feature Specification: [FEATURE NAME]
- Feature Specification: [FEATURE NAME]
- BUG-022 — Reports "Group By" selector has no effect (getGroupedData is never called)
- BUG-024 — Tier 3 flaring/combustion renormalises the gas composition without N2 (and without unspecified components), inflating CH4 and CO2 by 1/(1 − x_inert)
- BUG-028 — SBTi dashboard shows "ON TRACK — Reduction: 100% vs Baseline" when there is no verified data at all in the target window
- BUG-037 — Editing a Scope 1 record replaces its propagated 1σ uncertainty with the raw catalog EF half-width (95 %, EF-only); user_uncertainty is stored unpropagated
- BUG-061 — Dashboard "Emissions by Source" mis-classifies process types: fuel-gas combustion (6.47 M t) shown as "Other", pneumatics/tanks/dehydrators/unloading/completions as "Other" instead of Venting, fugitives merged into "Venting", mobile combustion labelled "Stationary Combustion"
- BUG-071 — Dashboard cache is not invalidated after a manual Scope 1 create or a bulk upload: new records are missing from the dashboard for up to 5 minutes (per worker)
- BUG-078 — Executive Brief / Master PDF prints hard-coded performance claims ("15.9 % reduction… on track for -30 %", "65.9 % methane reduction", "Lowest annual flaring on record (-38.0 %)", "VISR camera verified" DRE) regardless of the data
- BUG-099 — Scope 2 electricity create trusts client-supplied `co2e` / `emission_factor`: 0 kWh can be booked as 12,345 tCO2e, negative Scope 2 (-500 t) is accepted, and any unknown grid region takes the client's factor
- BUG-106 — User Management actions are missing from the Audit Trail: account creation and logout logs are never committed, and user deletion is not logged at all
- BUG-109 — Scope 1 form saves an entry with no Unit selected: the client silently assumes m³ (10 → 2,641.72 gal stored) while the server calculates from the raw 10 in calc_inputs, so the stored activity and its emissions disagree 264×
- BUG-111 — Scope 1 bulk import books a row with a blank Unit as m³ and accepts year 1800, both of which the manual form/API reject
- BUG-114 — Logout does not invalidate the session: a session cookie captured before logout keeps full API access (client-side signed cookie, no server-side revocation)
- BUG-019 — SBTi "Scope 1+2 (Operational)" view compares Scope 1+2 actuals to the Scope 1+2+3 baseline and target line (inflated reduction %, false ON TRACK)
- test_battery_concurrency_stress_invariants.py
- BUG-XXX — Well-completion Tier 3 uses `amount` as both the flowback volume and the event count (volume squared), and ignores rate × duration when the method dropdown is left at its default
- BUG-XXX — Tier 3 flaring/combustion renormalises the gas composition without N2 (and without unspecified components), inflating CH4 and CO2 by 1/(1 − x_inert)
- BUG-XXX — Tier 3 combustion/flaring gas composition: each component is converted percent→fraction on its own, so mol% values ≤ 1 (e.g. C4 = 1.0 %, C5 = 0.5 %) become 100 % / 50 %; CO2 inflated 2.7× on the app's own template sample
- BUG-XXX — Well-completion "Rate × Duration" method divides the Mcf/hr rate by 24 (treats it as Mcf/day): CH4 understated 24×
- BUG-XXX — Tier 1 fugitive and equipment factors in "per hour" units are multiplied only by the source count (no operating hours): annual CH4 understated 8,760×, and Tier 1 disagrees with Tier 3 for the same factor
- BUG-XXX — Dashboard cache is not invalidated after a manual Scope 1 create or a bulk upload: new records are missing from the dashboard for up to 5 minutes (per worker)
- BUG-XXX — Scope 2/3 bulk import silently books rows with a blank or non-ISO date to January 2024, and stores a blank Scope 3 category as "Category "
- BUG-XXX — Scope 2/3 bulk import duplicate key is too coarse: separate meters and sub-categories in the same facility-month are rejected as "duplicates", or with Overwrite they replace a different existing record
- BUG-XXX — Scope 2 and Scope 3 create accept a missing or non-numeric year: one year-less Scope 2 record makes the main dashboard (summary/batch-all) return 500, and year-less Scope 3 is in the total but missing from by-year
- BUG-XXX — POST /api/emissions/ calculates from `quantity`/`fuel_type` but stores only `amount`/`fuel`: records keep emissions with NULL activity quantity and fuel
- BUG-XXX — Editing a Scope 1 record's quantity via PUT /api/emissions/<id> does not recalculate emissions (stale `amount` from source_payload wins)
- BUG-XXX — Scope 3 category is stored as "6" by the UI/API and as "Category 6" by bulk import: cross-channel duplicates are not detected (double counting) and category breakdowns split
- BUG-XXX — Purchased steam/heat (`indirect_steam`) and CHP allocation (`cogen_allocation`) are accepted as Scope 1 process types and added to Scope 1 totals (Scope 2 counted as Scope 1; CHP double counting)
- BUG-XXX — Manual Scope 1 entry has no plausibility bound or QA flag: 9 test records (1e13 MMBtu gas, 1e15 t coal) make up about 99.99% of the snapshot's Scope 1 total (3.72e12 t Verified, 4.69e12 t Pending)
- BUG-XXX — 43 Tier 1 factors offered in the Scope 1 UI do not exist in the server catalog; records save with HTTP 201 and 0 emissions
- BUG-XXX — Tier 1 combustion applies the catalog HHV in the wrong basis when the activity unit is mass or the other phase (diesel/crude per tonne ×3.6, natural gas per tonne ÷40, ethane per scf ×39)
- BUG-XXX — Recalculating a Tier 2 (custom-factor) Scope 1 record drops the custom factor: emissions become 0 or silently switch to the catalog factor, while factor_source stays "custom"
- BUG-XXX — Custom factors used by Tier 2 records can be deleted: the reference check matches `fuel_type == factor name`, but UI records store the factor id, which SQLite then reuses for the next factor
- BUG-XXX — AR5 20-year GWPs are wrong (CH4 82.5 instead of 84, N2O 268 instead of 264); AR6 pairs the fossil CH4 GWP-20 with the non-fossil-weighted GWP-100
- BUG-XXX — GWP-20 conversion in intensity-stats / intensity-trend hard-codes AR5 GWP-100 (28 / 265), so GWP-20 CO2e is wrong whenever the active standard is AR4 or AR6
- BUG-XXX — Two contradictory OGMP facility-level algorithms: /intensity-stats reports Level 5 (Gold Standard) where the canonical service (/ogmp-metrics, OGMP export) reports Level 4 for the same facility and year
- BUG-XXX — OGMP reconciliation in the default "All years" view compares the AVERAGE of annual top-down surveys with the SUM of multi-year bottom-up CH4, so perfectly reconciled facilities are flagged (−80 %)
- BUG-XXX — Facility OGMP 2.0 level counts Draft, Pending and Rejected emission records, so a rejected record can raise a facility's level
- BUG-XXX — Pending-records banner ignores the GWP-20 toggle: it always shows GWP-100 tCO2e while every other dashboard figure switches to GWP-20
- BUG-XXX — Sentinel-5P "Export to OGMP" stores a 1-hour CH4 mass as the survey's "estimated annual tCH4" (default operating_hours = 1): top-down understated 8,760× and reconciliation always flagged
- BUG-XXX — Methane loss-rate segment classification differs between the KPI cards, the trend chart and the server: "Downstream / Processing" counts as Midstream in the trend, and "Upstream / Extraction" is dropped from the Upstream KPI
- BUG-XXX — OGMP survey reconciliation status defaults to "Reconciled" whatever the computed variance; a +354 % discrepancy is stored and shown as Reconciled, and a zero bottom-up case is shown as "+0.0 %"
- BUG-XXX — Facilities with CH4 emissions but no gas production get methane_loss_rate_pct = 0 and ogmp_target_status "Compliant"
- BUG-XXX — Intensity activity/division filter uses record-level columns that are NULL/inconsistent, so numerator and denominator are filtered differently (Upstream intensity blank, E&P intensity 0.0)
- BUG-XXX — Intensity with year="all" (default view) pairs each facility's emissions from every year with production from other years; KPI mixes periods
- BUG-XXX — Decree 21-330 flaring intensity (/flaring-summary) misconverts units: MMscf 1000× too low, scf/kscf 35× too high, UI "m³" gas production 28× too high; compliance verdict flips
- BUG-XXX — /granular-intensities (Master Report "Multi-Metric Intensities") divides all-facility emissions by only the facilities with granular MMboe fields, and fabricates NGSI methane (0.05 %) and saleable production (85 %)
- BUG-XXX — Flaring panel treats "All Years" as the current calendar year and ignores the Supply-Chain/Activity/Division/Preview-Pending filters, so it contradicts the dashboard it sits in
- BUG-XXX — Flaring panel invents a 56 % / 40 % / 4 % Routine / Non-Routine / Safety split for generic "flaring" records and shows 0 tCO₂e for every stream (and a 2.5 t/kNm³ proxy when CO₂e is 0)
- BUG-XXX — Flaring-summary volume conversion: "mmscf" hits the "mscf" branch (1000× understated), "scf" is read as m³, and the prior-year path uses a different, cruder conversion (YoY +2,732 % for identical volumes)
- BUG-XXX — Supply Chain filter is not applied to the emissions-by-source split: "Emissions by Source" donut and Detailed Breakdown rows show company-wide values (sources add up to 7× Scope 1)
- BUG-XXX — "Preview Pending Data" and the pending banner are inconsistent with the rest of the dashboard: the toggle changes only the KPIs (categorical/org breakdown and Scope 3 stay Verified-only), and the banner ignores the Supply Chain, Activity and Division filters and omits Scope 3
- BUG-XXX — Dashboard "Emissions by Source" mis-classifies process types: fuel-gas combustion (6.47 M t) shown as "Other", pneumatics/tanks/dehydrators/unloading/completions as "Other" instead of Venting, fugitives merged into "Venting", mobile combustion labelled "Stationary Combustion"
- BUG-XXX — Categorical Emissions Overview groups facilities by name instead of id: six distinct facilities are merged into one "Updated Facility" card (3.19 T t)
- BUG-XXX — "Net Emissions" KPI subtracts company-wide mitigation whatever the Activity/Division filter (Steel & Iron view: Net = −1,027,393 t) and counts "Planned" projects as achieved reductions
- BUG-XXX — Dashboard "Export Executive Brief (PDF)" in the default All-Years view reports every year and every Pending record as "FISCAL YEAR 2026" / "Total verified records": PDF total 8.41 T tCO2e vs 3.72 T on the dashboard
- BUG-XXX — Executive Brief / Master PDF prints hard-coded performance claims ("15.9 % reduction… on track for -30 %", "65.9 % methane reduction", "Lowest annual flaring on record (-38.0 %)", "VISR camera verified" DRE) regardless of the data
- BUG-XXX — QA/QC Dashboard shows "Zero Anomalies Detected… The inventory is fully verified and audit-compliant" with 149 Pending records and 11 records more than 10^6 × the median; the anomaly queue only lists a stored `qa_flag`, which is never computed for existing data
- BUG-XXX — Uncertainty dashboard applies max(u_CO2, u_CH4, u_N2O) to each record's total CO2e instead of CO2e-weighting the per-gas uncertainties
- BUG-XXX — Inventory uncertainty shrinks by √N when the same emissions are split into N records (shared EF uncertainty treated as independent)
- BUG-XXX — Meter (activity-data) and GC (composition) uncertainty inputs are accepted but silently ignored by every calculator
- BUG-XXX — Editing a Scope 1 record replaces its propagated 1σ uncertainty with the raw catalog EF half-width (95 %, EF-only); user_uncertainty is stored unpropagated
- BUG-XXX — QA Dashboard "IPCC Tier 1 Uncertainty" reports 1σ as ±%, uses only the CO2 column, and includes Draft and Pending records, so it contradicts the Uncertainty page
- BUG-XXX — Stored uncertainty has no range or unit validation: Scope 2/3 accept percent values, negatives, NaN and 1e6, and the Uncertainty dashboard shows ±3600 %
- BUG-XXX — Emission goals API ("+ Set Target") has no value validation: negative, year 1, and NaN goals are accepted; a NaN goal for the current year makes the main dashboard batch return 500
- BUG-XXX — Dashboard "% GOAL" badge in the default All-years view divides the cumulative multi-year Scope 1+2 total by the single current-year goal (and ignores region/facility filters)
- BUG-XXX — GET /api/manage/sbti ignores facility/region scoping: region-restricted users can read organisation-wide Verified emission totals for any year
- BUG-XXX — SBTi target POST accepts NaN / Infinity (range checks pass for non-finite floats); trajectory endpoint then returns 500 or invalid JSON for all users
- BUG-XXX — SBTi dashboard shows "ON TRACK — Reduction: 100% vs Baseline" when there is no verified data at all in the target window
- BUG-XXX — SBTi progress KPI uses the current, incomplete year (and any future year) as the "current" year, so the dashboard reports ~95-99% reduction and ON TRACK
- BUG-XXX — SBTi target labelled "1.5°C" is not tied to its reduction rate (0.5 %/yr accepted and displayed as 1.5°C); arbitrary pathway strings and future base years accepted; main-dashboard banner hard-codes "SBTi 1.5°C Linear Target"
- BUG-XXX — SBTi "Scope 1+2 (Operational)" view compares Scope 1+2 actuals to the Scope 1+2+3 baseline and target line (inflated reduction %, false ON TRACK)
- BUG-XXX — Audit trail (/api/audit/, /api/audit/export) is not facility/region-scoped: a region-restricted superuser reads activity entries for every region's records
- BUG-XXX — Equity-share allocation ignores effective dates (time-sliced ownership never applied) and POST /api/equity/shares accepts any percentage (500, -50, inf) from any business role
- BUG-XXX — /api/reports/master-annual-report serves full annual GHG report PDFs to any logged-in role (incl. it_admin and out-of-region users) and returns a static, pre-generated file regardless of facility_id
- BUG-XXX — Bulk upload job API lets any logged-in role (user, it_admin) create/overwrite facilities and custom factors, bypassing RBAC and region scoping
- BUG-XXX — Alembic migration chain is unusable: `flask db upgrade` fails on both the existing DB and a fresh DB
- BUG-XXX — Deleting a user wipes approved_by/created_by on every record they approved or entered: Verified records lose their maker-checker evidence
- BUG-XXX — Bulk-upload overwrite rewrites approved records without an audit trail and leaves them "Pending" but still marked approved
- BUG-XXX — Bulk upload with "Overwrite Duplicates" enabled inserts every in-file duplicate row as a separate record (double counting)
- BUG-XXX — Custom factor names are not unique, yet bulk import resolves factors by name: the most recently created same-named factor is silently applied
- BUG-XXX — Deleting a facility that has any OGMP level-upgrade log fails with 500 (FK violation) and leaks raw SQL
- BUG-XXX — Deleting a user who created production data, SBTi targets or OGMP level logs fails with 500 (FK cleanup list incomplete)
- BUG-XXX — CustomDropdown is not keyboard-operable and form inputs have no programmatic labels: Region, Process Type, Emission Factor and Unit cannot be set without a mouse
- BUG-XXX — AGR form throughput units MMscfd / Mcf/day / m³/yr are ignored by the server (read as MMscf/yr): CO2 365× low, 2.7× high, or 28,317× high
- BUG-XXX — User Management actions are missing from the Audit Trail: account creation and logout logs are never committed, and user deletion is not logged at all
- BUG-XXX — CHP allocation form labels Power Output "MWh" but the server uses the number as MMBtu: heat share (and Scope 2 tCO2e) overstated ~2.7× with WRI efficiency method
- BUG-XXX — Dehydrator form sends "Contactor Pressure" as `dehy_pressure`, but the server reads `dehy_press`: user pressure silently ignored, 800 psig default always used (AGR "routed to flare"/"flash gas recycled" checkboxes also unread)
- BUG-XXX — Dehydrator throughput entered under the label "MMscf/yr" is saved with unit "MMscf/day" (record activity unit 365× off)
- BUG-XXX — Emission Calculation Result panel rounds gas masses to 3 decimals of a tonne: non-zero CH4/N2O shown as "0.00 tonnes"
- BUG-XXX — Reports Excel/PDF exports drop the Division, Field, Method and Search filters shown on screen
- BUG-XXX — Reports "Group By" selector has no effect (getGroupedData is never called)
- BUG-XXX — Scope 1 "Live Equation Inspector" states "GWP Standard: IPCC AR6 (CH₄:28, N₂O:265)" — hard-coded, AR5 values mislabelled as AR6, ignores the org GWP setting
- BUG-XXX — Reports "2025 Master Report (PDF)" button sends facility_id=[object Object]; facility selection ignored
- BUG-XXX — Scope 1 "Recent Activity": Export CSV exports only the 10 rows of the current page, and the Year/Process filter options are built from that page only
- BUG-XXX — Scope 1 entry form does not reflow at phone width (390 px): Field input, Tier selector and factor picker are clipped off-screen
- BUG-XXX — Scope 2 form: switching Source Type to Steam/Heat or CHP leaves the hidden unit at "kWh" — dropdown shows "Select..." but the request sends unit "kWh" (1000 "MMBtu" of steam booked as 3.41 MMBtu)
- BUG-XXX — Reports search keeps the current page number: "Total Records: 42 | Showing: 0" and no pager to recover
- BUG-XXX — Manage Data and Reference Data swallow API load errors and show them as empty data ("No production record found", empty factor catalog)
- BUG-XXX — Scope 1 bulk import books a row with a blank Unit as m³ and accepts year 1800, both of which the manual form/API reject
- BUG-XXX — Custom emission factor with every factor field blank is saved (CO2/CH4/N2O = 0) and Tier 2 records that use it are stored with 0 tCO2e and no warning
- BUG-XXX — "Add Region" (create facility) form fails with HTTP 500 unless the optional Latitude/Longitude fields are filled
- BUG-XXX — Onshore fugitives "Tier 1: Facility-Level" form: the on-screen preview says 16,644 tCO2e but the saved record is 1.456 tCO2e — the server ignores the selected facility type and duration and books the facility count as a count of valves
- BUG-XXX — Logout does not invalidate the session: a session cookie captured before logout keeps full API access (client-side signed cookie, no server-side revocation)
- BUG-XXX — Manage Data page crashes for every user when any facility has a NULL name; POST /api/facilities accepts facilities with no name
- BUG-XXX — Scope 1 form saves an entry with no Unit selected: the client silently assumes m³ (10 → 2,641.72 gal stored) while the server calculates from the raw 10 in calc_inputs, so the stored activity and its emissions disagree 264×
- BUG-XXX — Reports "PDF Report" prints every unit and gas name with a missing-glyph box: "tCO■e", "CO■", "CH■", "N■O"
- BUG-XXX — Maker-checker outcome is invisible to the maker: reject/approve send no notification, the Scope 1 list shows Rejected/Pending rows exactly like Verified ones, and the reject dialog claims the record is "permanently deleted" although it is kept as Rejected
- BUG-XXX — Scope 2 electricity create trusts client-supplied `co2e` / `emission_factor`: 0 kWh can be booked as 12,345 tCO2e, negative Scope 2 (-500 t) is accepted, and any unknown grid region takes the client's factor
- BUG-XXX — Manage Data forms discard the server's validation message and show a generic "Failed to …" toast (negative production, negative factor, facility 500, etc.)
- Implementation Plan - Activity Log Dashboard Replica
- Modern "Glassy" PDF Report Overhaul
- Compliance Gap Analysis: API Guidance 2.0 (2023)
- Implementation Plan: API Guidance 2.0 Compliance
- SolarEPC-Pro: Walkthrough & Verification
- [Component] Emissions Calculator UI
- Critical Findings (Require Action)
- Implementation Plan - Cement Industry GHG Emissions Calculator
- [Server] Calculation Engine Fixes
- 3. Test Quality & Rigor Audit
- Enterprise Performance, Stress & Latency Benchmark Audit
- 3. Critical Flaws in the Legacy Test Suite
- ctx
- test_emission_calculations.py
- test_security_hardening.py
- test_audit_bug_fixes.py
- test_tier2_api_e2e.py
- files
- Implementation Tasks: QA/QC Module (IPCC & ISO 14064)
- BUG-001 — Bulk upload job API lets any logged-in role (user, it_admin) create/overwrite facilities and custom factors, bypassing RBAC and region scoping
- BUG-021 — Reports search keeps the current page number: "Total Records: 42 | Showing: 0" and no pager to recover
- BUG-023 — Tier 3 combustion/flaring gas composition: each component is converted percent→fraction on its own, so mol% values ≤ 1 (e.g. C4 = 1.0 %, C5 = 0.5 %) become 100 % / 50 %; CO2 inflated 2.7× on the app's own template sample
- BUG-025 — Meter (activity-data) and GC (composition) uncertainty inputs are accepted but silently ignored by every calculator
- BUG-026 — Flaring panel treats "All Years" as the current calendar year and ignores the Supply-Chain/Activity/Division/Preview-Pending filters, so it contradicts the dashboard it sits in
- BUG-003 — Editing a Scope 1 record's quantity via PUT /api/emissions/<id> does not recalculate emissions (stale `amount` from source_payload wins)
- BUG-027 — Tier 1 combustion applies the catalog HHV in the wrong basis when the activity unit is mass or the other phase (diesel/crude per tonne ×3.6, natural gas per tonne ÷40, ethane per scf ×39)
- BUG-029 — Manage Data page crashes for every user when any facility has a NULL name; POST /api/facilities accepts facilities with no name
- BUG-030 — POST /api/emissions/ calculates from `quantity`/`fuel_type` but stores only `amount`/`fuel`: records keep emissions with NULL activity quantity and fuel
- BUG-031 — Facility OGMP 2.0 level counts Draft, Pending and Rejected emission records, so a rejected record can raise a facility's level
- BUG-032 — GET /api/manage/sbti ignores facility/region scoping: region-restricted users can read organisation-wide Verified emission totals for any year
- BUG-033 — Decree 21-330 flaring intensity (/flaring-summary) misconverts units: MMscf 1000× too low, scf/kscf 35× too high, UI "m³" gas production 28× too high; compliance verdict flips
- BUG-034 — SBTi target POST accepts NaN / Infinity (range checks pass for non-finite floats); trajectory endpoint then returns 500 or invalid JSON for all users
- BUG-035 — Flaring-summary volume conversion: "mmscf" hits the "mscf" branch (1000× understated), "scf" is read as m³, and the prior-year path uses a different, cruder conversion (YoY +2,732 % for identical volumes)
- BUG-036 — Flaring panel invents a 56 % / 40 % / 4 % Routine / Non-Routine / Safety split for generic "flaring" records and shows 0 tCO₂e for every stream (and a 2.5 t/kNm³ proxy when CO₂e is 0)
- BUG-004 — Intensity activity/division filter uses record-level columns that are NULL/inconsistent, so numerator and denominator are filtered differently (Upstream intensity blank, E&P intensity 0.0)
- BUG-038 — Audit trail (/api/audit/, /api/audit/export) is not facility/region-scoped: a region-restricted superuser reads activity entries for every region's records
- BUG-039 — Emission goals API ("+ Set Target") has no value validation: negative, year 1, and NaN goals are accepted; a NaN goal for the current year makes the main dashboard batch return 500
- BUG-040 — Supply Chain filter is not applied to the emissions-by-source split: "Emissions by Source" donut and Detailed Breakdown rows show company-wide values (sources add up to 7× Scope 1)
- BUG-041 — Dashboard "% GOAL" badge in the default All-years view divides the cumulative multi-year Scope 1+2 total by the single current-year goal (and ignores region/facility filters)
- BUG-042 — Recalculating a Tier 2 (custom-factor) Scope 1 record drops the custom factor: emissions become 0 or silently switch to the catalog factor, while factor_source stays "custom"
- BUG-043 — Stored uncertainty has no range or unit validation: Scope 2/3 accept percent values, negatives, NaN and 1e6, and the Uncertainty dashboard shows ±3600 %
- BUG-044 — /granular-intensities (Master Report "Multi-Metric Intensities") divides all-facility emissions by only the facilities with granular MMboe fields, and fabricates NGSI methane (0.05 %) and saleable production (85 %)
- BUG-045 — "Add Region" (create facility) form fails with HTTP 500 unless the optional Latitude/Longitude fields are filled
- BUG-047 — Tier 1 fugitive and equipment factors in "per hour" units are multiplied only by the source count (no operating hours): annual CH4 understated 8,760×, and Tier 1 disagrees with Tier 3 for the same factor
- BUG-005 — GWP-20 conversion in intensity-stats / intensity-trend hard-codes AR5 GWP-100 (28 / 265), so GWP-20 CO2e is wrong whenever the active standard is AR4 or AR6
- BUG-052 — OGMP survey reconciliation status defaults to "Reconciled" whatever the computed variance; a +354 % discrepancy is stored and shown as Reconciled, and a zero bottom-up case is shown as "+0.0 %"
- BUG-054 — "Preview Pending Data" and the pending banner are inconsistent with the rest of the dashboard: the toggle changes only the KPIs (categorical/org breakdown and Scope 3 stay Verified-only), and the banner ignores the Supply Chain, Activity and Division filters and omits Scope 3
- BUG-055 — QA Dashboard "IPCC Tier 1 Uncertainty" reports 1σ as ±%, uses only the CO2 column, and includes Draft and Pending records, so it contradicts the Uncertainty page
- BUG-056 — Custom factors used by Tier 2 records can be deleted: the reference check matches `fuel_type == factor name`, but UI records store the factor id, which SQLite then reuses for the next factor
- BUG-057 — Bulk upload with "Overwrite Duplicates" enabled inserts every in-file duplicate row as a separate record (double counting)
- BUG-058 — Bulk-upload overwrite rewrites approved records without an audit trail and leaves them "Pending" but still marked approved
- BUG-006 — Reports Excel/PDF exports drop the Division, Field, Method and Search filters shown on screen
- BUG-059 — SBTi target labelled "1.5°C" is not tied to its reduction rate (0.5 %/yr accepted and displayed as 1.5°C); arbitrary pathway strings and future base years accepted; main-dashboard banner hard-codes "SBTi 1.5°C Linear Target"
- BUG-064 — Categorical Emissions Overview groups facilities by name instead of id: six distinct facilities are merged into one "Updated Facility" card (3.19 T t)
- BUG-065 — Custom factor names are not unique, yet bulk import resolves factors by name: the most recently created same-named factor is silently applied
- BUG-066 — AGR form throughput units MMscfd / Mcf/day / m³/yr are ignored by the server (read as MMscf/yr): CO2 365× low, 2.7× high, or 28,317× high
- BUG-068 — Purchased steam/heat (`indirect_steam`) and CHP allocation (`cogen_allocation`) are accepted as Scope 1 process types and added to Scope 1 totals (Scope 2 counted as Scope 1; CHP double counting)
- BUG-007 — Manual Scope 1 entry has no plausibility bound or QA flag: 9 test records (1e13 MMBtu gas, 1e15 t coal) make up about 99.99% of the snapshot's Scope 1 total (3.72e12 t Verified, 4.69e12 t Pending)
- BUG-072 — Pending-records banner ignores the GWP-20 toggle: it always shows GWP-100 tCO2e while every other dashboard figure switches to GWP-20
- BUG-073 — Scope 2 and Scope 3 create accept a missing or non-numeric year: one year-less Scope 2 record makes the main dashboard (summary/batch-all) return 500, and year-less Scope 3 is in the total but missing from by-year
- BUG-075 — Sentinel-5P "Export to OGMP" stores a 1-hour CH4 mass as the survey's "estimated annual tCH4" (default operating_hours = 1): top-down understated 8,760× and reconciliation always flagged
- BUG-077 — Dashboard "Export Executive Brief (PDF)" in the default All-Years view reports every year and every Pending record as "FISCAL YEAR 2026" / "Total verified records": PDF total 8.41 T tCO2e vs 3.72 T on the dashboard
- BUG-008 — Inventory uncertainty shrinks by √N when the same emissions are split into N records (shared EF uncertainty treated as independent)
- BUG-079 — OGMP reconciliation in the default "All years" view compares the AVERAGE of annual top-down surveys with the SUM of multi-year bottom-up CH4, so perfectly reconciled facilities are flagged (−80 %)
- BUG-080 — Two contradictory OGMP facility-level algorithms: /intensity-stats reports Level 5 (Gold Standard) where the canonical service (/ogmp-metrics, OGMP export) reports Level 4 for the same facility and year
- BUG-081 — Scope 2/3 bulk import duplicate key is too coarse: separate meters and sub-categories in the same facility-month are rejected as "duplicates", or with Overwrite they replace a different existing record
- BUG-082 — Scope 1 "Live Equation Inspector" states "GWP Standard: IPCC AR6 (CH₄:28, N₂O:265)" — hard-coded, AR5 values mislabelled as AR6, ignores the org GWP setting
- BUG-084 — QA/QC Dashboard shows "Zero Anomalies Detected… The inventory is fully verified and audit-compliant" with 149 Pending records and 11 records more than 10^6 × the median; the anomaly queue only lists a stored `qa_flag`, which is never computed for existing data
- BUG-085 — Scope 2/3 bulk import silently books rows with a blank or non-ISO date to January 2024, and stores a blank Scope 3 category as "Category "
- BUG-086 — Methane loss-rate segment classification differs between the KPI cards, the trend chart and the server: "Downstream / Processing" counts as Midstream in the trend, and "Upstream / Extraction" is dropped from the Upstream KPI
- BUG-009 — Deleting a facility that has any OGMP level-upgrade log fails with 500 (FK violation) and leaks raw SQL
- BUG-088 — Facilities with CH4 emissions but no gas production get methane_loss_rate_pct = 0 and ogmp_target_status "Compliant"
- BUG-090 — Dehydrator form sends "Contactor Pressure" as `dehy_pressure`, but the server reads `dehy_press`: user pressure silently ignored, 800 psig default always used (AGR "routed to flare"/"flash gas recycled" checkboxes also unread)
- BUG-092 — Maker-checker outcome is invisible to the maker: reject/approve send no notification, the Scope 1 list shows Rejected/Pending rows exactly like Verified ones, and the reject dialog claims the record is "permanently deleted" although it is kept as Rejected
- BUG-094 — "Net Emissions" KPI subtracts company-wide mitigation whatever the Activity/Division filter (Steel & Iron view: Net = −1,027,393 t) and counts "Planned" projects as achieved reductions
- BUG-095 — Scope 1 "Recent Activity": Export CSV exports only the 10 rows of the current page, and the Year/Process filter options are built from that page only
- BUG-096 — Scope 2 form: switching Source Type to Steam/Heat or CHP leaves the hidden unit at "kWh" — dropdown shows "Select..." but the request sends unit "kWh" (1000 "MMBtu" of steam booked as 3.41 MMBtu)
- BUG-010 — Deleting a user who created production data, SBTi targets or OGMP level logs fails with 500 (FK cleanup list incomplete)
- BUG-097 — CHP allocation form labels Power Output "MWh" but the server uses the number as MMBtu: heat share (and Scope 2 tCO2e) overstated ~2.7× with WRI efficiency method
- BUG-098 — Emission Calculation Result panel rounds gas masses to 3 decimals of a tonne: non-zero CH4/N2O shown as "0.00 tonnes"
- BUG-105 — Manage Data and Reference Data swallow API load errors and show them as empty data ("No production record found", empty factor catalog)
- BUG-107 — CustomDropdown is not keyboard-operable and form inputs have no programmatic labels: Region, Process Type, Emission Factor and Unit cannot be set without a mouse
- BUG-011 — Well-completion "Rate × Duration" method divides the Mcf/hr rate by 24 (treats it as Mcf/day): CH4 understated 24×
- BUG-108 — Scope 1 entry form does not reflow at phone width (390 px): Field input, Tier selector and factor picker are clipped off-screen
- BUG-112 — Custom emission factor with every factor field blank is saved (CO2/CH4/N2O = 0) and Tier 2 records that use it are stored with 0 tCO2e and no warning
- BUG-113 — Reports "PDF Report" prints every unit and gas name with a missing-glyph box: "tCO■e", "CO■", "CH■", "N■O"
- BUG-115 — Manage Data forms discard the server's validation message and show a generic "Failed to …" toast (negative production, negative factor, facility 500, etc.)
- BUG-012 — Well-completion Tier 3 uses `amount` as both the flowback volume and the event count (volume squared), and ignores rate × duration when the method dropdown is left at its default
- BUG-013 — AR5 20-year GWPs are wrong (CH4 82.5 instead of 84, N2O 268 instead of 264); AR6 pairs the fossil CH4 GWP-20 with the non-fossil-weighted GWP-100
- BUG-014 — SBTi progress KPI uses the current, incomplete year (and any future year) as the "current" year, so the dashboard reports ~95-99% reduction and ON TRACK
- BUG-015 — 43 Tier 1 factors offered in the Scope 1 UI do not exist in the server catalog; records save with HTTP 201 and 0 emissions
- BUG-016 — Alembic migration chain is unusable: `flask db upgrade` fails on both the existing DB and a fresh DB
- BUG-017 — Intensity with year="all" (default view) pairs each facility's emissions from every year with production from other years; KPI mixes periods
- BUG-002 — Reports "2025 Master Report (PDF)" button sends facility_id=[object Object]; facility selection ignored
- BUG-018 — Uncertainty dashboard applies max(u_CO2, u_CH4, u_N2O) to each record's total CO2e instead of CO2e-weighting the per-gas uncertainties
- BUG-020 — /api/reports/master-annual-report serves full annual GHG report PDFs to any logged-in role (incl. it_admin and out-of-region users) and returns a static, pre-generated file regardless of facility_id
- BUG-XXX — Generic factor math ignores the 10³ / 10⁶ multiplier in factor denominators: offshore gas fugitives 1,000,000× and refinery fuel-gas fugitives 1,000× overstated
- BUG-XXX — Energy activity units kWh / MJ / Btu with a kg/MMBtu factor are treated as scf of gas (× 1020 Btu/scf): 1000 kWh of natural gas is 3.3× too low, MJ 7.6 % too high
- BUG-XXX — Tier 3 fugitive calculators misread catalog factor units: "CH₄" (Unicode subscript) is not recognised as methane (×0.85 applied), and ComponentFugitiveCalculator treats tonne/hr factors as kg/hr (1000× too low)
- BUG-XXX — Negative activity amounts are accepted for process types that are not in the dispatcher (e.g. "loading") and saved as negative emissions
- BUG-XXX — Uncertainty display inconsistencies: EmissionResult shows the ±1σ (68 %) band as the "Confidence Interval", Scope 2/3 tables use k=1.96 while everything else uses k=2, and the Uncertainty page badge thresholds contradict its legend
- BUG-XXX — CAP (air-pollutant) emissions bypass maker-checker: POST /api/cap/emissions stores records as "Verified" by default (client-controlled status) for role user; negative mass/concentration accepted
- BUG-XXX — Region-restricted superuser can re-region its own facility (PUT /api/facilities/<id>), pushing the facility and all its emissions into another region's scope and out of its own
- BUG-XXX — Bulk-upload job status and error CSV have no owner check: any logged-in account (incl. it_admin) can read another user's job rows; absolute server temp path is disclosed
- BUG-XXX — Maker-checker bypass through edit and delete: a superuser can approve a record they just edited, silently re-date/re-assign Verified records, and a user can hard-delete their own Verified records
- BUG-XXX — Activity-data write endpoints accept "NaN" / "1e999" (±Infinity): a Scope 3 record with activity_data=Infinity makes /dashboard/batch-all, /scope3/summary and /api/scope3 emit invalid JSON ("Infinity")
- BUG-XXX — Approve/reject endpoints are not concurrency-safe: two simultaneous approvals of the same record both return 200 (duplicate audit entries; approve+reject race ends in an arbitrary final state)
- BUG-XXX — POST /api/emissions/reject/<id> has no status check: a superuser can flip an admin-Verified record to Rejected (removing it from all totals) and overwrite its approver
- BUG-XXX — Scope 2 manual entries and Scope 2 bulk imports by a superuser are auto-Verified, while Scope 1 and Scope 3 require admin approval (inconsistent maker-checker)
- Expanded Emissions MAP & Refined Data Entry
- Tasks
- Proposed Changes
- [Frontend Optimizations]
- Comprehensive System Audit Report
- 📸 Photorealistic 3D Rendering Upgrade
- 2. Detailed Methodological Analysis by Subsystem
- test_qaqc_diagnostics.py
- TestTier1DrillingMud
- BUG-053 — CAP (air-pollutant) emissions bypass maker-checker: POST /api/cap/emissions stores records as "Verified" by default (client-controlled status) for role user; negative mass/concentration accepted
- Core Principles
- Core Principles
- Core Principles
- Core Principles
- BUG-048 — Tier 3 fugitive calculators misread catalog factor units: "CH₄" (Unicode subscript) is not recognised as methane (×0.85 applied), and ComponentFugitiveCalculator treats tonne/hr factors as kg/hr (1000× too low)
- BUG-049 — Generic factor math ignores the 10³ / 10⁶ multiplier in factor denominators: offshore gas fugitives 1,000,000× and refinery fuel-gas fugitives 1,000× overstated
- TestEdgeCases
- BUG-051 — Energy activity units kWh / MJ / Btu with a kg/MMBtu factor are treated as scf of gas (× 1020 Btu/scf): 1000 kWh of natural gas is 3.3× too low, MJ 7.6 % too high
- TestIntermediateValues
- BUG-060 — Scope 2 manual entries and Scope 2 bulk imports by a superuser are auto-Verified, while Scope 1 and Scope 3 require admin approval (inconsistent maker-checker)
- QADashboard.jsx
- BUG-067 — Maker-checker bypass through edit and delete: a superuser can approve a record they just edited, silently re-date/re-assign Verified records, and a user can hard-delete their own Verified records
- .get_token
- BUG-076 — Bulk-upload job status and error CSV have no owner check: any logged-in account (incl. it_admin) can read another user's job rows; absolute server temp path is disclosed
- BUG-083 — Activity-data write endpoints accept "NaN" / "1e999" (±Infinity): a Scope 3 record with activity_data=Infinity makes /dashboard/batch-all, /scope3/summary and /api/scope3 emit invalid JSON ("Infinity")
- BUG-093 — Region-restricted superuser can re-region its own facility (PUT /api/facilities/<id>), pushing the facility and all its emissions into another region's scope and out of its own
- BUG-XXX — Tier 2 custom factors whose unit is not "kg/<unit>" are misapplied (Manage Data form stores a bare activity unit): tonne factors ×1000 (×10⁶ with kg activity), no volume/mass conversion at all; unknown units such as kg/TJ or kg/GJ are applied 1:1
- BUG-XXX — Malformed input on create endpoints returns HTTP 500/409 with raw exception and SQL text (≈40 handlers return `str(e)`)
- Key Accomplishments
- 1. Logic Audit & Bug Hunt
- Auto-Create Facilities & Sources Walkthrough
- Walkthrough - Carbon Intensity & Hierarchical Filtering
- Key Changes by Layer
- New Capabilities
- Implementation Plan - GHG Emissions Tool (API Compendium)
- Implementation Plan - 3D Layout Overhaul & Interaction
- TestMissingAndEmptyInputs
- TestTier1Combustion
- TestCatalogFactorIntegrity
- test_audit_rc3_targets.py
- User
- test_audit_forms_payload.py
- BUG-050 — Negative activity amounts are accepted for process types that are not in the dispatcher (e.g. "loading") and saved as negative emissions
- FlaringCalculator
- Implementation Tasks: Batch Approve/Reject Pending Records
- send_email
- test_satellite.py
- BUG-087 — Malformed input on create endpoints returns HTTP 500/409 with raw exception and SQL text (≈40 handlers return `str(e)`)
- Findings and fixes
- AUDIT SCOPE — GHG Accounting & Reporting Platform
- w2_facility.mjs
- ISO 14064-1 Uncertainty Implementation
- PVGIS Data Analyzer - Implementation Tasks
- Implementation Plan - Auto-Create Facilities from CSV
- Changes Required
- Changes
- ✅ Enhancements Completed
- New Features
- 🌟 Key Features Implemented
- MCP Servers (`mcp_config.json`)
- Antigravity Customization System Guide
- 2. Key WCAG 2.1 Level AA Compliance Findings
- Cross-Browser Compatibility & Responsive Viewport Audit
- NumberedCanvas
- GHGUser
- CalculationDispatcher
- TestCleanGWPStandards
- BUG-074 — Approve/reject endpoints are not concurrency-safe: two simultaneous approvals of the same record both return 200 (duplicate audit entries; approve+reject race ends in an arbitrary final state)
- login_required
- Implementation Plan: [FEATURE]
- package.json
- Implementation Plan: [FEATURE]
- Existing Entities to Modify
- TestGWPValidation
- build_master_pdf
- Proposed Changes
- API Guidance 2.0 Compliance Upgrade
- Implementation Steps
- PVGIS CSV Parsing Support
- Key Accomplishments
- CSV to Spreadsheet Converter
- GHG Tracker - Feature Expansion Walkthrough
- Dashboard Display
- Methane Hotspot Explorer Implementation Plan
- API Compendium 2021 - List of Exhibits
- Goal Description
- CAD Enhancements Complete: Layer Control & Setbacks
- Proposed Changes
- Lifecycle Hooks (`hooks.json`)
- agy-customizations/SKILL.md
- Independent GHG Emissions & MRV Calculation Validation Report
- test_scope1_tier1_tier3_advanced.spec.js
- BUG-013.py
- env.py
- TestUnitConversions
- TestMudVolumeUnits
- BatchAnomalyDetector
- test_audit_rc3_validation.py
- TestCleanStoichiometry
- TestCogenAllocationBattery
- UserManagement.jsx
- Emissions.jsx
- test_clean_emission_factors.py
- API Compendium 2021 — exhibit and default-factor check (2026-09-27)
- F — Dashboard reconciliation (Agent F)
- NotificationCenter.jsx
- w10_gwp.mjs
- w15_import.mjs
- Correcting Organizational Hierarchy & Syncing Data
- ReferenceData and Metadata Fixes
- 4135d1c7-8dfd-43ce-af15-f9dd1ab24a49/task.md
- New Features
- Comprehensive Security, Compliance & IT Audit Report
- ✅ CAD Layer Control Complete - Fixed & Ready
- GHG Emissions Calculator Compliance Report
- Input/Output Contract
- Generative UI
- devDependencies
- Catalog factor check against the API Compendium 2021 (2026-09-28)
- TestConstantHistoryBattery
- repro_flare.py
- TestDataStarvationBattery
- TestFieldCoercionAndSanitization
- test_library_factor_mode.py
- test_deep_button_audit.py
- test_definitions.py
- Audit Agent Protocol (mandatory for every workstream)
- BUG-092.mjs
- E/api2.py
- w19_unc.mjs
- [Frontend] Hierarchy Correction
- [Calculation Engine Fixes]
- Tasks
- Key Changes
- Dashboard and Calculator Fixes
- 6f3b0214-86d8-4c32-ae7b-51068644ff56/task.md
- Comprehensive Software Hardening Walkthrough
- Walkthrough: Cement GHG Emissions Calculator
- Verification Walkthrough: Region Hierarchy Refactor
- Configuration Schema
- Plugins
- Workspace Skills
- Instructions for the Agent
- BUG-043.py
- TestConcurrentBulkIngestionPipeline
- generate_1k_comprehensive.py
- TestTier1Flaring
- TestTier3Flaring
- test_log_handler.py
- TestExhaustiveUnitInvertibility
- new/.specify/scripts/powershell/create-new-feature.ps1
- test_all_apis_health.py
- test_master_button_audit.py
- scripts
- .specify/scripts/powershell/create-new-feature.ps1
- RTK - Rust Token Killer (Google Antigravity)
- Agent I — Endpoint inventory (generated from app.url_map + source decorators)
- w24_meth.mjs
- Investigation Plan: PDF Report Generation Issues
- Task: Investigate Report Generation Issue
- Workspace Cleanup Plan
- Changes Made
- Dashboard Summary and CORS Fixes
- Unified Emissions Database & Reporting
- Task: Authentication and Database Restructuring
- Walkthrough: API Compendium Verification
- Realistic Pitch Deck Complete
- Walkthrough - API GHG Emissions Tool
- build_pitch_deck.py
- Mandatory Human Review & Domain Expert Governance Register
- test_bulk_csv_uploader.spec.js
- TestTier3TankFlashing
- TestTier3PneumaticDevices
- TestTier3Completions
- scope3Factors.test.js
- BUG-067.py
- BUG-070.py
- [CHECKLIST TYPE] Checklist: [FEATURE NAME]
- [CHECKLIST TYPE] Checklist: [FEATURE NAME]
- Research & Design Decisions: Batch Approve/Reject
- Research & Design Decisions: QA/QC Module (IPCC & ISO 14064)
- run_full_validation_suite.py
- BUG-086.py
- BUG-111.mjs
- BUG-115.mjs
- ef_client.mjs
- dash2.mjs
- Task: Test GHG Platform UI
- Task: Investigate PDF Report Download Issue
- Task List
- Task: Implement Specific Emission Factor Calculator
- Revamped Pitch Deck Plan
- Fix NameError in app.py
- fa667970-6544-43ed-9980-019760f9806b/task.md
- BUG-087.py
- test_ui_audit_visuals.mjs
- generate_bulk_test_csvs.py
- repro_fac.py
- status.py
- TestTier1Venting
- test_battery_stoichiometry_indirect_energy.py
- TestExhaustiveTransitivity
- postcss
- calculations/dispatcher.py
- ctx
- ctx
- IndependentUncertaintyModel
- build
- test_bug046_allocation_is_time_weighted_by_effective_dates
- FIX LOG
- Agent L — browser workflows covered
- BUG-001.py
- BUG-063.py
- BUG-071.py
- BUG-074.py
- BUG-083.py
- BUG-090.py
- BUG-097.mjs
- browser_smoke.mjs
- t_batch2.py
- presets.mjs
- dash1.mjs
- e3230fa3-8bd0-4c24-b227-11579e2fb81e/task.md
- generate_storage_state.js
- eslint-plugin-react-hooks
- @playwright/test
- BUG-003.py
- BUG-005.py
- BUG-007.py
- BUG-015.py
- BUG-025.py
- BUG-030.py
- BUG-033.py
- BUG-046.py
- BUG-052.py
- BUG-053.py
- BUG-055.py
- BUG-056.py
- BUG-060.py
- BUG-066.py
- BUG-068.py
- BUG-072.py
- BUG-073.py
- BUG-076.py
- BUG-078.py
- BUG-079.py
- BUG-081.py
- BUG-085.py
- BUG-089.py
- BUG-093.py
- BUG-096.mjs
- BUG-098.mjs
- BUG-113.py
- SUSPECTED_AND_QUESTIONS.md
- dumpjs.mjs
- keys.mjs
- client_only_repro.py
- build_elm_master_pdf
- pdf1.mjs
- combine_uncertainties_sum
- run_all.sh
- t.md
- 00831633-e548-4e2d-9163-99f846b6739b/task.md
- 0f30d407-23dc-43d5-887f-01bb0dd3312f/task.md
- 180ff968-ccbc-46fc-95d3-05bcd6d6c4ec/task.md
- 391ed0fe-f334-4c3f-9d49-8af290439877/task.md
- 728c160e-6960-47fb-9ca4-ab7b205e5744/task.md
- 75f2d6f4-9958-4818-85e3-afee007ac5ca/task.md
- 77a5e62d-3cc2-4808-9aa1-78b205cdc8e5/task.md
- 9ee12848-4ff1-4ff9-9975-9ad017574be8/task.md
- a2d7a921-655f-490f-bea7-dd5f91bb8697/task.md
- b72262e7-bc20-4f3c-9b82-82b303d0f9f1/task.md
- c9768850-e325-4576-9c89-09f39787fb7c/task.md
- cb1e2599-6eda-488f-8f5a-372c19ceca8f/task.md
- d9e613de-bfed-4e7c-b6f4-e6c436fce153/task.md
- jspdf-autotable
- leaflet
- papaparse
- @radix-ui/react-slot
- react-leaflet
- react-router-dom
- prettier
- rollup-plugin-visualizer
- vitest
- playwright.config.js
- File-by-File Analysis
- 001-batch-approve-reject/data-model.md
- 001-batch-approve-reject/quickstart.md
- 002-qa-qc-ipcc-iso14064/quickstart.md
- validation/__init__.py
- BUG-008.py
- regression/__init__.py
- .test_dashboard_summary_identity_and_compact_formatting
- CombustionCalculator

## God Nodes (most connected - your core abstractions)
1. `User` - 170 edges
2. `compute_emissions()` - 162 edges
3. `Facility` - 160 edges
4. `Emission` - 156 edges
5. `login_required()` - 147 edges
6. `calculate_co2e()` - 119 edges
7. `get_current_user()` - 117 edges
8. `CalculationDispatcher` - 109 edges
9. `BaseCalculator` - 95 edges
10. `CalculationDispatcher` - 94 edges

## Surprising Connections (you probably didn't know these)
- `TestGWPHorizonsAndProfilesBattery` --uses--> `CombustionCalculator`  [INFERRED]
  new/server/tests/test_battery_gwp_horizons_regulatory.py → audit/work/A/base/combustion.py
- `TestCSVBufferIngestionMatrix` --uses--> `CombustionCalculator`  [INFERRED]
  new/server/tests/test_csv_engine_matrix.py → audit/work/A/base/combustion.py
- `TestFieldCoercionAndSanitization` --uses--> `CombustionCalculator`  [INFERRED]
  new/server/tests/test_csv_engine_matrix.py → audit/work/A/base/combustion.py
- `TestMetrologyAndEngineeringPrecision` --uses--> `CombustionCalculator`  [INFERRED]
  new/server/tests/test_csv_engine_matrix.py → audit/work/A/base/combustion.py
- `TestCleanScope1Combustion` --uses--> `CombustionCalculator`  [INFERRED]
  validation/calculation/test_clean_scope1.py → audit/work/A/base/combustion.py

## Import Cycles
- None detected.

## Communities (918 total, 112 thin omitted)

### Community 0 - "Facility"
Cohesion: 0.02
Nodes (127): NumberedCanvas, Groupement Berkine Master Publication Report Generator Compiles an exhaustive…, Two-pass canvas to dynamically compute and print 'Page X of Y' and running…, NumberedCanvas, El Merk (Block 208) Master Publication Report Generator Compiles an exhaustive…, Two-pass canvas to dynamically compute and print 'Page X of Y' and running…, run_all_scenarios(), _before_insert() (+119 more)

### Community 1 - "calculate_co2e"
Cohesion: 0.02
Nodes (117): _frac(), API Compendium 2021 activity-based emission factors (onshore upstream +…, Site composition inputs are percentages (0-100)., BaseCalculator, Validates that all required inputs are present, finite, and non-negative., Calculates absolute uncertainty and non-negative bounds at 95% CI (k=2.0 per…, Formats the final calculation result into a standard structure., Base class for all API Compendium 2021 calculation modules. Provides common… (+109 more)

### Community 2 - "extensions.py"
Cohesion: 0.08
Nodes (19): Shared fixtures-as-functions for the audit regression tests…, app(), client(), disable_limiter_for_tests(), init_test_db(), fixture, Ensure Flask-Limiter does not throttle endpoints during tests., BUG-087: 5xx responses never carry exception text. (+11 more)

### Community 3 - "CalculationDispatcher"
Cohesion: 0.02
Nodes (121): CalculationDispatcher, Routes a calculation request to the appropriate API 2021 calculator., Normalise a gas/liquid volume or volume RATE to `target_unit` (m3 or mmscf).…, Strictly extracts a required float parameter without falling back to defaults., Extracts an optional float parameter from flat_inputs, returning default if…, Cleanly parses a percentage (0-100) or fraction (0-1) into a 0.0 - 1.0 ratio., Extracts a percentage or fraction strictly and normalizes to 0.0 - 1.0., API Compendium 2021 section 6.11.3 via RefiningHydrogenPlantCalculator. -… (+113 more)

### Community 4 - "background_processor.py"
Cohesion: 0.05
Nodes (76): _append_job_list(), _bulk_overwrite(), _clean_float(), _clean_sheet_name(), _data_sheet(), _dedupe(), _find_header_row(), _first() (+68 more)

### Community 5 - "dashboard.py"
Cohesion: 0.03
Nodes (114): cached, BaseYearRecalculation, create_base_year_recalculation(), _finite_or_none(), get_available_years(), get_base_year(), get_batch_dashboard_data(), get_categorical_breakdown() (+106 more)

### Community 6 - "test_browser_exploratory_fixes.py"
Cohesion: 0.19
Nodes (25): activity(), calc(), login(), parametrize, Regression tests for the exploratory browser test findings…, s1(), test_11_excel_export_scope2_steam_row(), test_13_library_factor_record_named() (+17 more)

### Community 7 - "test_tier_scope_kpi_numerical.py"
Cohesion: 0.04
Nodes (100): CombustionCalculator, FlaringCalculator, AGRCalculator, DehydratorCalculator, Calculation tier following IPCC 2006 GL Vol.1 §2.4 hierarchy., Tier, BlowdownCalculator, CompletionFlowbackCalculator (+92 more)

### Community 8 - "routes/scope2.py"
Cohesion: 0.07
Nodes (34): grid_entry(), grid_factor_kg_co2e_per_kwh(), Grid Emission Factors - electricity_factors.py Central registry for location-…, (canonical name, entry) of a grid region, case-insensitive, aliases resolved;…, kg CO2e / kWh of a grid entry with the given (or the active) GWP set., EPA Supply Chain Greenhouse Gas Emission Factors v1.3.0 by NAICS-6 (USEEIO…, Codes whose number starts with, or whose title contains, the query., search_eeio_factors() (+26 more)

### Community 9 - "auditlib.py"
Cohesion: 0.02
Nodes (12): Repro: dashboard per-record uncertainty uses max(u_CO2,u_CH4,u_N2O) instead of…, Agent C repro: catalog HHV (Btu/gal or Btu/scf) is applied to mass / wrong-…, BUG-031: rejected record raises facility OGMP level. Exits 1 while bug exists., Repro: PUT /api/emissions/<id> (recalculate) overwrites the propagated 1-sigma…, Superuser restricted to West can read audit-log entries about other regions'…, Agent C repro: PUT /api/emissions/<id> recalculation drops the record's Tier 2…, Repro (API + source check): EmissionResult shows the 1-sigma band as the…, BUG-075: S5P export stores 1-hour mass as annual tCH4. Exits 1 while bug exists. (+4 more)

### Community 10 - "MudDegassingCalculator"
Cohesion: 0.04
Nodes (74): MudDegassingCalculator, AcidGasRemovalCalculator, BlowdownCalculator, CasingGasVentCalculator, CO2EORVentingCalculator, GasDehydrationCalculator, PneumaticDeviceCalculator, PneumaticPumpCalculator (+66 more)

### Community 11 - "parse_number"
Cohesion: 0.08
Nodes (40): _process_row_facilities(), parse_number(), ValueError, Central input validation (audit root cause RC-1). - ``ValidationError`` is…, Parse a finite number. Blank/None -> ``default`` when not required., require_text(), ValidationError, add_facility() (+32 more)

### Community 12 - "CompletionFlowbackCalculator"
Cohesion: 0.04
Nodes (55): AssociatedGasVentingCalculator, CompletionFlowbackCalculator, AsphaltBlowingCalculator, FireSuppressionCalculator, PetrochemicalManufacturingCalculator, _propagate_results(), API Compendium 2021 - Sections 6.11, 6.12, 6.14: Downstream Refining,…, API Compendium 2021 §6.11.1 - Catalyst Regeneration: - FCCU Coke Burn Rate… (+47 more)

### Community 13 - "reference_model/__init__.py"
Cohesion: 0.06
Nodes (53): CLEAN-SLATE VALIDATION: Scope 1 Direct Emissions Validates all implemented…, parametrize, CLEAN-SLATE VALIDATION: Differential Testing Suite Executes Production…, generate_all_golden_cases(), INDEPENDENT GOLDEN DATASET GENERATOR Generates independent golden test cases…, CLEAN-SLATE VALIDATION: Mutation Testing Suite Validates that the validation…, Mutant: Assuming 100% flare destruction efficiency (omitting methane slip).…, Mutant: Acid Gas Removal drops API Table 6-5 0.1% methane slip. Suite must… (+45 more)

### Community 14 - "App.jsx"
Cohesion: 0.10
Nodes (36): fetchCsrfToken(), AdminRoute(), App(), AuditRoute(), AuditTrail, CarbonIntensity, EmissionsMap, ITRoute() (+28 more)

### Community 15 - "Backend (Server)"
Cohesion: 0.03
Nodes (74): `add_indexes.py`, `app.py`, Backend (Server), `background_processor.py`, `benchmark_db.py`, `calculations\base.py`, `calculations\combustion.py`, `calculations\constants.py` (+66 more)

### Community 16 - "test_independent_differential.py"
Cohesion: 0.10
Nodes (44): Battery 1: Midstream & Upstream Process Equipment Test Suite.…, Verifies completions and workovers flowback across all 3 methodologies., Verifies API Eq. 6-3 liquids unloading with tubing geometry and P/T correction., Verifies API Eq. 6-4 blowdown events with compressibility Z-factor., Verifies storage tank flashing and working/breathing losses., Verifies continuous bleed vs intermittent actuation pneumatic devices., TestBlowdownBattery, TestLiquidsUnloadingBattery (+36 more)

### Community 17 - "Frontend (Client)"
Cohesion: 0.03
Nodes (66): `api.js`, `App.jsx`, `components\BulkImportModal.jsx`, `components\CalculationDetails.jsx`, `components\charts\BarChart.jsx`, `components\charts\index.js`, `components\charts\LineChart.jsx`, `components\charts\PieChart.jsx` (+58 more)

### Community 18 - "K/lib.mjs"
Cohesion: 0.06
Nodes (38): EMAIL, OUT, start(), UI, agrInputs, grpIn, grpOut, post (+30 more)

### Community 19 - "sqlite3"
Cohesion: 0.03
Nodes (18): boe(), expected(), Flaring panel ignores 'All Years' (uses current calendar year) and…, flaring-summary unit conversion: 'mmscf' falls into the 'mscf' branch (1000x…, Flaring panel invents a 56/40/4 split for generic 'flaring' rows; stream tCO2e…, Supply-Chain (segment) filter is not applied to the per-source split in…, /granular-intensities: numerator = all facilities, denominator = only rows with…, Preview-Pending toggle only reaches _query_summary; categorical breakdown… (+10 more)

### Community 20 - "Scope1Form.jsx"
Cohesion: 0.05
Nodes (49): CustomDropdown(), ADIPIC_ACID_OPTIONS, AdipicAcidForm(), AGRForm(), TABLE_6_8_BASINS, AsphaltBlowingForm(), AssociatedGasVentingForm(), GAS_VOL_UNITS (+41 more)

### Community 21 - "compute_emissions"
Cohesion: 0.03
Nodes (47): compute_emissions(), Entry point for Scope 1 calculations (routes, bulk, recalculation). Audit…, test_bug025_meter_and_gc_overrides_applied(), Verifies compute_emissions pipeline returns rich result and correct method., TANK FLASHING: GOR method, no control. throughput=1000 bbl, GOR=100 scf/bbl,…, LIQUIDS UNLOADING T3: depth=5000 ft, diameter=2.5 in, pressure=500 psig,…, INDIRECT STEAM: heat=100 MMBtu, EF_co2=56.1 kg/MMBtu, boiler_eff=0.80,…, FLARING T3: Enclosed/ground flare uses higher efficiencies. Default for… (+39 more)

### Community 22 - "log_activity_and_notify"
Cohesion: 0.10
Nodes (41): exempt, Persistent key-value store for application-wide settings (GWP standard, OGMP…, SystemSetting, admin_required(), admin_reset_password(), change_password(), create_user(), delete_user() (+33 more)

### Community 23 - "server/app.py"
Cohesion: 0.08
Nodes (35): DefaultJSONProvider, errorhandler, listens_for, after_request(), before_request(), enforce_session_version(), FiniteJSONProvider, get_csrf_token() (+27 more)

### Community 24 - "resolve_tier"
Cohesion: 0.07
Nodes (33): convert_factor_to_kg_per_unit(), _normalize_efficiency(), _normalize_unit_str(), API Compendium 2021 - Section 5: Combustion and Flaring Implementation of…, Standard fuel-based combustion calculation with API §4.2.1 thermodynamic…, Defensively normalizes efficiency inputs provided as either fractional ratios…, Dual-efficiency flaring model (API 5-3, 5-4) with API §4.2.1 thermodynamic…, API Compendium 2021 - Section 6: Midstream & Process Emissions Implementation… (+25 more)

### Community 25 - "test_tier3_browser_findings.py"
Cohesion: 0.16
Nodes (27): fails(), gas(), _post(), parametrize, Regression tests for the Tier 3 browser test findings…, run(), test_10_combustion_tier3_hhv_only_rejected(), test_11_working_breathing_losses() (+19 more)

### Community 26 - "has_table"
Cohesion: 0.09
Nodes (36): _add(), _bind(), has_table_(), upgrade(), _add(), _bind(), has_table_(), upgrade() (+28 more)

### Community 27 - "useToast"
Cohesion: 0.09
Nodes (34): RFC-4180, api, BatchReviewWizard(), detectAnomalies(), QUICK_REJECTION_REASONS, BulkImportModal(), CalculationDetails(), stripApi() (+26 more)

### Community 28 - "DistributionNonRoutineCalculator"
Cohesion: 0.07
Nodes (25): DistributionNonRoutineCalculator, DistributionPneumaticsCalculator, LNGVentingCalculator, API Compendium 2021 Section 6.7 - LNG Operations Supports: - Table 6-44 Typical…, API Compendium 2021 Section 6.8.1 - Gas-Driven Pneumatic Controllers in…, API Compendium 2021 Section 6.8.2 - Gas Distribution Non-Routine Releases Table…, Unit and Golden Tests for API Compendium 2021 Sections 6.7 & 6.8: LNG…, Table 6-45: Control loops (3.465 tonnes CH4/yr). (+17 more)

### Community 29 - "combustion_methods.py"
Cohesion: 0.14
Nodes (14): ActivityFactorCalculator, CombustionMethodCalculator, _eq(), _frac(), _num(), API Compendium 2021 combustion and waste-gas methods that are not fuel x…, ch4_pj / n2o_pj in tonne per 10^12 J (HHV) as printed; n2o None -> fuel basis…, _unit() (+6 more)

### Community 30 - "sql"
Cohesion: 0.06
Nodes (24): SBTi progress uses the latest year with ANY verified data, incl. the current…, SBTi scope toggle (s1_s2 / s3) compares scope-subset actuals to the all-scope…, SBTi summary with no actual data in the target window reports 100 % reduction…, GET /api/manage/sbti?base_year=Y returns org-wide Verified totals to region-…, POST /api/manage/sbti accepts NaN / Infinity; the trajectory endpoint then 500s…, POST /api/goals has no validation: NaN goal is stored as NULL and then breaks…, Dashboard '% GOAL' badge (year=All, the default) divides the all-years S1+S2…, SBTi pathway label is not tied to the reduction rate: '1.5C' with 0.5 %/yr,… (+16 more)

### Community 31 - "DehydratorCalculator"
Cohesion: 0.17
Nodes (8): AGRCalculator, DehydratorCalculator, Verify Dehydrator stripping gas calculation adds methane volume to still vent…, Verify DehydratorCalculator accurately generates stoichiometric CO2 when gas is…, test_dehydrator_stoichiometric_co2_combustion(), test_dehydrator_stripping_gas_calculation(), API §6.6: Controlled dehydrator must oxidize destroyed methane to…, API Compendium 2021 §6.6: TEG dehydration GRI-GLYCalc parametric methane…

### Community 32 - "Authentication and User-Specific Database Implementation Walkthrough"
Cohesion: 0.04
Nodes (44): 1. User Registration, 2. User Login, 3. User Profile Dropdown, 4. Logout Functionality, ✅ All Tests Passed Successfully, Authentication and User-Specific Database Implementation Walkthrough, Authentication Flow, Backend (+36 more)

### Community 33 - "TestRegressionArchive"
Cohesion: 0.08
Nodes (12): Diff Test: Acid gas removal (amine) CO2 balance and methane slip., Mutant: AGR regenerator emissions calculated with zero methane slip., Bug ID: B9 Description: Top-down SUM over multiple surveys per facility-year…, Bug ID: B12 Description: LiquidsUnloading press_unit ignored (hardcoded psig).…, Bug ID: B13 Description: AGRCalculator CO2 control step function (>0.5 only)…, Bug ID: B14 Description: Case-sensitive units (MWh vs mwh, KWH vs kwh).…, Bug ID: B15 / Client Parity Description: Frontend constants getActiveGwpFactors…, Permanent regression tests for all platform calculation bugs. Each test… (+4 more)

### Community 34 - "ghg_tool/app.py"
Cohesion: 0.07
Nodes (32): add_calc(), display_result(), show_methodology(), calculate_amine(), calculate_combustion(), calculate_compressor(), calculate_dehydrator(), calculate_electricity() (+24 more)

### Community 35 - "Comprehensive Gap Analysis: SolarEPC-Pro"
Cohesion: 0.05
Nodes (40): 10. Module Degradation (Non-linear), 11. String-Level Mismatch, 12. Multi-User / Authentication, 13. Real-Time Monitoring Integration, 14. Error Handling, 15. Unit Tests, 16. Logging, 17. Documentation (+32 more)

### Community 36 - "test_onshore_well_completions_audit.py"
Cohesion: 0.03
Nodes (36): fixture, Comprehensive Regression and Validation Test Suite for Onshore Well…, API Table 6-6: Onshore Oil Well without HF - Vented = 0.0141 t CH4/completion., Tier 1: Multi-event scaling (e.g. 5 completions)., API Table 6-5 Footnote c: Gas CH4 content adjustment (relative to 81.6% base)., API Table 6-5 Footnote c: Gas CO2 estimation based on relative concentrations., Verifies Tier 2 API Engineering calculations using site-specific operational…, API Eq. 6-7: Non-HF completion V_CC = V_Pi * T (daily production rate * vent… (+28 more)

### Community 37 - "75f2d6f4-9958-4818-85e3-afee007ac5ca/implementation_plan.md"
Cohesion: 0.05
Nodes (39): 3. Battery Degradation (`src/hybrid_model.py`), `app.py`, Automated Tests, Goal, Goal, Goal, Goal, Goal (+31 more)

### Community 38 - "Scope1ImportWizard.jsx"
Cohesion: 0.07
Nodes (21): COMP, FIELD_GROUPS, Icon, PROCESS_CATALOGUE, Scope1ImportWizard(), STEPS, FIELD_GROUPS, Icon (+13 more)

### Community 39 - "Solar PV Calculator - Complete Feature Implementation Plan"
Cohesion: 0.05
Nodes (38): Goal Description, Implementation Strategy, Integration Testing, [MODIFY] [app.js](file:///C:/Users/samsung/.gemini/antigravity/scratch/solar-pv-calculator/app.js), [MODIFY] [index.html](file:///C:/Users/samsung/.gemini/antigravity/scratch/solar-pv-calculator/index.html), [MODIFY] [styles.css](file:///C:/Users/samsung/.gemini/antigravity/scratch/solar-pv-calculator/styles.css), [NEW] [battery-storage.js](file:///C:/Users/samsung/.gemini/antigravity/scratch/solar-pv-calculator/battery-storage.js), [NEW] [chart-export.js](file:///C:/Users/samsung/.gemini/antigravity/scratch/solar-pv-calculator/chart-export.js) (+30 more)

### Community 40 - "2. Calculation Inventory by Type"
Cohesion: 0.05
Nodes (38): 1. Calculation Module Overview, 2.10 Component Fugitives, 2.11 Equipment Fugitives, 2.12 Compressor Seal Fugitives, 2.13 Acid Gas Removal (AGR), 2.14 Glycol Dehydrators, 2.15 Indirect Steam / Heat (Scope 1 or 2 boundary), 2.16 Cogeneration Allocation (+30 more)

### Community 41 - "test_audit_rc6_scope1_paths.py"
Cohesion: 0.15
Nodes (21): admin(), _create(), ng_co2e(), fixture, parametrize, RC-6 / RC-4 regressions: Scope 1 create, edit and import paths calculate and…, _scope1_total(), test_bug003_put_fuel_type_changes_factor() (+13 more)

### Community 42 - "CSV Spreadsheet Pro - Enhanced Features Walkthrough"
Cohesion: 0.05
Nodes (37): 1. **Theme Toggle (Light/Dark Mode)** ✅, 2. **Import from URL** ✅, 3. **Excel Export (.xlsx)** ✅, 4. **Row Operations** ✅, 5. **Chart Visualization** ✅, 6. **localStorage Auto-Save** ✅, 7. **Enhanced UI/UX** ✅, Add/Delete Rows (+29 more)

### Community 43 - "4. Formal Specifications for Scope 1 Direct Emissions"
Cohesion: 0.05
Nodes (37): 1. Thermodynamic Reference Conditions and Dimensional Standard, 2.1 Volume Conversions, 2.2 Mass Conversions, 2.3 Energy Conversions, 2. Core Unit Conversions Specification, 3. Global Warming Potentials (GWP) and CO2e Normalization, 4.10 Acid Gas Removal (AGR / Amine Sweetening), 4.11 Glycol Dehydrator (TEG) (+29 more)

### Community 44 - "Master Calculation Register"
Cohesion: 0.05
Nodes (37): CALC-001: Stationary Combustion — Tier 1 / Tier 2 Fuel-Based, CALC-002: Stationary Combustion — Tier 3 Gas Chromatographic Carbon Balance, CALC-003: Flaring — API Compendium Dual-Efficiency Stoichiometric Combustion, CALC-004: Mud Degassing / Well Drilling, CALC-005: Well Completion Flowback, CALC-006: Liquids Unloading, CALC-007: Vessel Blowdown & Equipment Depressurization, CALC-008: Storage Tanks — GOR Flash Gas & Breathing Losses (+29 more)

### Community 45 - "Master Calculation Register"
Cohesion: 0.05
Nodes (37): CALC-001: Stationary Combustion — Tier 1 / Tier 2 Fuel-Based, CALC-002: Stationary Combustion — Tier 3 Gas Chromatographic Carbon Balance, CALC-003: Flaring — API Compendium Dual-Efficiency Stoichiometric Combustion, CALC-004: Mud Degassing / Well Drilling, CALC-005: Well Completion Flowback, CALC-006: Liquids Unloading, CALC-007: Vessel Blowdown & Equipment Depressurization, CALC-008: Storage Tanks — GOR Flash Gas & Breathing Losses (+29 more)

### Community 46 - "LiquidsUnloadingCalculator"
Cohesion: 0.06
Nodes (29): convert_temperature(), Converts gauge or metric pressure to absolute pressure in psia., Converts temperature value across C, F, K, R., Converts temperature value to Kelvin., to_kelvin(), to_psia(), LiquidsUnloadingCalculator, _propagate_vented_results() (+21 more)

### Community 47 - "AUDIT_FINDINGS.md"
Cohesion: 0.06
Nodes (35): Actual, Additional confirmation (BUG-033), Affected Components, AUDIT FINDINGS, BUG-063 — Tier 2 custom factors whose unit is not "kg/<unit>" are misapplied (Manage Data form stores a bare activity unit): tonne factors ×1000 (×10⁶ with kg activity), no volume/mass conversion at all; unknown units such as kg/TJ or kg/GJ are applied 1:1, BUG-100 — Pneumatic controllers calculator cites obsolete 2009 Section 6.10, conflates hourly bleed with actuation volume, and lacks API 2021 Tables 6-14/6-15 and Eq 6-14 malfunction model, BUG-101 — Vessel and pipeline blowdown calculation depressurization formula includes residual atmospheric volume, overestimating vented volume by 1.0 physical vessel volume per event, BUG-102 — Storage tank flashing emissions evaluate to zero when GOR is omitted, lacking API 2021 Table 6-22/6-24 default factors and engineering correlations (VBE, Standing, EUB) (+27 more)

### Community 48 - "TestAllProcessTypesTier3"
Cohesion: 0.05
Nodes (21): _activity_unit(), parametrize, test_all_process_types_matrix.py --------------------------------- Exhaustive…, Activity unit of a generic test row; mud degassing (Table 6-2) is per drilling…, Verify compute_emissions pipeline routes and handles all canonical process…, Verify that every process is mapped to valid segments and combustion/non-…, Every single process type in PROCESS_TYPES must calculate successfully in Tier…, Verify all Scope 2 utility types: Grid Electricity (Location/Market) and… (+13 more)

### Community 49 - "test_associated_gas_venting.py"
Cohesion: 0.06
Nodes (35): calc(), dispatcher(), fixture, API Compendium 2021 Section 6.3.1 - EXHIBIT 6-5: Sample Calculation for Non-…, API Compendium 2021 Section 6.3.1 - EXHIBIT 6-6: Sample Calculation for…, Verify disposition partitioning: Total Gas = GOR * Oil Production = 700 * 5,200…, Test GOR in m3/m3 conversion to scf/bbl., Tier 3: Measured vent rate VR = 2,528 scf/min = 151,680 scfh for 360 hours (15… (+27 more)

### Community 50 - "models.py"
Cohesion: 0.08
Nodes (47): migrate_database(), ActivityLog, BaseYear, CbamProductExport, ComponentInventory, FugitiveSurvey, Goal, MethaneSourceType (+39 more)

### Community 51 - "test_aggregation_reconciliation.py"
Cohesion: 0.08
Nodes (16): Aggregation, Reconciliation, and Rollup Integrity Test Suite.…, Verifies that summing across sources and scopes is strictly conservative and…, Sum(CO2e_i) must equal calculate_co2e(Sum(CO2_i), Sum(CH4_i), Sum(N2O_i)).…, Total GHG = Scope 1 + Scope 2 + Scope 3., Verifies OGMP 2.0 Top-Down vs Bottom-Up reconciliation thresholds., Verifies BOE and Carbon/Methane Intensity calculations., TestIntensityMetrics, TestOGMPSurveyReconciliation (+8 more)

### Community 52 - "ui_format_number"
Cohesion: 0.06
Nodes (18): Tier 1 Natural Gas Combustion: Verify exact digits across DB, API, Table row,…, Flaring calculation with 98% combustion efficiency, methane slip, and carbon…, Hydrogen SMR with CCS: Feedstock + Fuel CO2 minus Capture., Tier 3: Detailed chromatographic fuel gas composition with carbon mass balance., Fugitive Component Leaks: 150 valves with EPA leak factors and 5 decimal UI…, Location-based Grid Electricity: 50,000 kWh at US Average factor., Indirect Steam / District Heat: 1,200 MMBtu with boiler efficiency., Replicates formatNumber(value, decimals) from formatters.js. (+10 more)

### Community 53 - "Detailed Implementation Walkthrough"
Cohesion: 0.06
Nodes (32): 10. `background_processor.py` — Thread-Safe Upload Job Registry, 11. `managedata.py` — Mitigation Record Deletion Protection, 12. `auth.py` — User Role Mutation Whitelist & Hierarchy Check, 1. Carbon Intensity Page (`CarbonIntensity.jsx` & `_query_intensity_stats`), 1. `notifications.py` — Stream Heartbeat Initialization, 1. Scope 1: Tier 1, 2, 3 Calculations, 2. Methane Intensity Page (`MethaneIntensity.jsx` & `_query_intensity_stats`), 2. `scope2.py` — Indirect Steam Custom Thermodynamics (+24 more)

### Community 54 - "antigravity_guide/SKILL.md"
Cohesion: 0.06
Nodes (28): 1. Unified Interface Surfaces, 2. Agent Settings & Permissions, 3. Further Reading, Antigravity 2.0 Reference, Chat Canvas, Global Settings, Left-hand Sidebar, Project-Level Settings (+20 more)

### Community 55 - "k_uilib.mjs"
Cohesion: 0.12
Nodes (15): req, req, req, s, post, dl, post, resp (+7 more)

### Community 56 - "TestBoundaryConditions"
Cohesion: 0.06
Nodes (17): BOUNDARY: Zero flowback gas = zero CH4 from completions., BOUNDARY: Zero tank throughput = zero emissions., BOUNDARY: Zero vessel volume = zero blowdown emissions., BOUNDARY (audit BUG-015 / BUG-112): an all-zero factor is not a factor. A large…, BOUNDARY: 100% CO2 gas in completions → zero CH4 emitted. (ch4_frac=0 →…, BOUNDARY: Negative quantity is physically impossible. Dispatcher raises…, BOUNDARY: Negative mud volume → ValueError., BOUNDARY: NaN quantity is invalid. BaseCalculator.validate_inputs() checks… (+9 more)

### Community 57 - "Reports.jsx"
Cohesion: 0.12
Nodes (22): Reports, Settings, MultiSelectDropdown(), BOUNDARY_OPTIONS, DEFAULT_GWP, getActiveGwpFactors(), GWP_AR4, GWP_AR5 (+14 more)

### Community 58 - "ref_co2e"
Cohesion: 0.07
Nodes (16): PIPELINE STEP 1-7: POST emission → API returns correct computed values.…, PIPELINE STEPS 5-9: Verify stored DB values match the expected calculation.…, TIER 3 COMBUSTION: Gas composition method (carbon mass balance). Formula: -…, TIER 3 COMBUSTION: Pure methane (c1=1.0). Reference: total_C_moles = 1.0…, FLARING T3: Elevated flare, 90% C1, no native CO2. Reference: vol = 500 m3, c1…, FLARING T3: Gas with native CO2 content. Reference: vol = 1000 m3, c1=0.80,…, Independent CO2e using AR5 GWPs., TIER 1 (API Table 6-3): Simplified default based on well count. 10 wells → ch4… (+8 more)

### Community 59 - "TestOATSensitivity"
Cohesion: 0.08
Nodes (16): One-at-a-time sensitivity tests: perturb ONE input, verify mathematical…, Run the standard baseline., OAT: Q → 2Q, EFs unchanged. Mathematical relationship: E_i = Q × EF_i → 2Q ×…, OAT: EF_co2 → 2×EF_co2, quantity/EF_ch4/EF_n2o unchanged. CO2 should double,…, OAT: EF_ch4 → 2×EF_ch4, quantity/EF_co2/EF_n2o unchanged. CH4 should double,…, OAT: EF_n2o → 2×EF_n2o, everything else unchanged. N2O should double, CO2 and…, OAT: Same drilling days, change mud_type: oil_based vs water_based. oil_based…, OAT: 20 devices vs 10 devices (same hours, bleed_rate, CH4). CH4 must be… (+8 more)

### Community 60 - "devDependencies"
Cohesion: 0.07
Nodes (29): autoprefixer, eslint, @eslint/js, eslint-plugin-react-refresh, globals, jsdom, devDependencies, autoprefixer (+21 more)

### Community 61 - "dependencies"
Cohesion: 0.07
Nodes (29): axios, chart.js, class-variance-authority, clsx, formik, framer-motion, jspdf, lucide-react (+21 more)

### Community 62 - "test_audit_rc14_schema.py"
Cohesion: 0.12
Nodes (24): Config, # NOTE: 50 MB covers any realistic single-month CSV upload., LevelUpgradeLog, _cf(), ctx(), _env(), _heads(), fixture (+16 more)

### Community 63 - "session"
Cohesion: 0.11
Nodes (12): crashed, call(), q(), launch(), login(), session(), base, base (+4 more)

### Community 64 - "DashboardEnhanced.jsx"
Cohesion: 0.12
Nodes (23): DashboardEnhanced, SkeletonCard(), calculateForecast(), DashboardEnhanced(), calculateTrend(), formatCompactNumber(), formatDate(), formatNumber() (+15 more)

### Community 65 - "5. CHANGELOG & DRIFT LOG"
Cohesion: 0.07
Nodes (26): 1. ARCHITECTURAL MAP & ENTRY POINTS, [2026-09-14T23:44:00Z] - ARCHITECTURAL KNOWLEDGE GRAPH INITIALIZATION, [2026-09-15T00:01:00Z] - SCOPE 1 EMISSION DETAIL VIEWER REMEDIATION & THEME ALIGNMENT, [2026-09-15T00:52:00Z] - FULL-STACK RESILIENCE & RUNTIME VERIFICATION REMEDIATION, [2026-09-15T01:13:00Z] - FULL-STACK BUG REMEDIATION & UX HARDENING, [2026-09-15T01:36:00Z] - E2E PRODUCT EXPERIENCE & FEATURE POLISH REMEDIATION (DEF-09 TO DEF-12), [2026-09-16T01:10:00Z] - COMPREHENSIVE PRODUCT AUDIT REMEDIATION (DEF-01 TO DEF-08 & FINDINGS 2, 5), [2026-09-16T01:20:00Z] - ADVERSARIAL STRESS-TEST & DETERMINISTIC VERIFICATION AUDIT (CSV UPLOADERS & METROLOGICAL ENGINES) (+18 more)

### Community 66 - "4. Critical Observations"
Cohesion: 0.07
Nodes (26): 1. Repository Structure Overview, 2.1 Active Production Files, 2.2 Legacy / Obsolete Files, 2.3 v2 Files Assessment, 2.4 Test Files Status, 2. File Classification, 3.1 Backend Architecture, 3.2 Frontend Architecture (+18 more)

### Community 67 - "test_deep_injection_matrix.py"
Cohesion: 0.14
Nodes (14): app(), db_session(), dispatcher(), fixture, test_deep_injection_matrix.py ------------------------------ Exhaustive Deep…, Executes the full asynchronous/synchronous file processing pipeline for all 3…, Tier 1 Bulk CSV: Default catalog factors across combustion, venting, and…, Tier 2 Bulk CSV: Uses regional custom emission factors created in DB. (+6 more)

### Community 68 - "test_it_role_security.py"
Cohesion: 0.08
Nodes (26): client(), fixture, IT role cannot register / provision new users (403 Forbidden)., IT role cannot modify user profiles, names, roles, or departments (403…, IT role cannot delete users (403 Forbidden)., IT role cannot view or export audit trail (403 Forbidden)., IT role has zero access to facilities, emissions, scope 2/3, sources, or…, IT role can access region identifiers for UI filtering without error. (+18 more)

### Community 69 - "._run"
Cohesion: 0.09
Nodes (15): Blowdown: vessel volume in m3 vs scf should give same result after the…, Reference result using m3., 5 m3 = 5 * 35.3147 = 176.573 scf Both should give the same result after…, 5 m3 = 5 / 0.158987295 = 31.457... bbl, Completions metered_volume: 1000 m3 vs 35314.67 scf. Reference: ch4 = 1000 *…, 1000 m3 flowback, 85% CH4 = 0.576725 t CH4., 1000 m3 = 35314.67 scf After normalization to m3, same CH4 result., 1000 m3 = 35.31467 Mscf (+7 more)

### Community 70 - "Tasks: [FEATURE NAME]"
Cohesion: 0.07
Nodes (26): Dependencies & Execution Order, Format: `[ID] [P?] [Story] Description`, Implementation for User Story 1, Implementation for User Story 2, Implementation for User Story 3, Implementation Strategy, Incremental Delivery, MVP First (User Story 1 Only) (+18 more)

### Community 71 - "Tasks: [FEATURE NAME]"
Cohesion: 0.07
Nodes (26): Dependencies & Execution Order, Format: `[ID] [P?] [Story] Description`, Implementation for User Story 1, Implementation for User Story 2, Implementation for User Story 3, Implementation Strategy, Incremental Delivery, MVP First (User Story 1 Only) (+18 more)

### Community 72 - "Feature Specification: QA/QC Module (IPCC & ISO 14064 Compliant)"
Cohesion: 0.07
Nodes (24): Content Quality, Feature Readiness, Notes, Requirement Completeness, Specification Quality Checklist: qa-qc-ipcc-iso14064, Complexity Tracking, Constitution Check, Documentation (this feature) (+16 more)

### Community 73 - "sleep"
Cohesion: 0.19
Nodes (11): fi, pv, fillS1(), openS1(), pick(), sleep(), submitS1(), cases (+3 more)

### Community 74 - "🎨 HIGH-TIER 3D CAD RENDERING COMPLETE!"
Cohesion: 0.08
Nodes (25): 1. Photorealistic Materials (PBR), 2. Cinematic Camera Presets, 3. HDR Sky Background, 4. Professional Title & Annotations, 5. Enhanced Hover Information, 6. Modern Modebar, Advanced Lighting, Camera Controls (+17 more)

### Community 75 - "BUG-070 — POST /api/emissions/reject/<id> has no status check: a superuser can flip an admin-Verified record to Rejected (removing it from all totals) and overwrite its approver"
Cohesion: 0.20
Nodes (10): Actual, Affected Components, BUG-070 — POST /api/emissions/reject/<id> has no status check: a superuser can flip an admin-Verified record to Rejected (removing it from all totals) and overwrite its approver, Evidence, Expected, Impact, Location, Recommended Fix (+2 more)

### Community 76 - "test_uncertainty.py"
Cohesion: 0.09
Nodes (25): monte_carlo_simulation(), IPCC 2006 GL Vol.1 §3.4 Approach 2 — Monte Carlo Simulation for GHG Uncertainty…, admin_user(), client(), it_admin_user(), fixture, Test suite for /dashboard/uncertainty endpoint. Covers: auth, RBAC,…, Specifying year= returns that year in the response. (+17 more)

### Community 77 - "make_user"
Cohesion: 0.13
Nodes (45): login(), make_user(), Log in through the real endpoint so session bookkeeping (e.g. session_version)…, uniq(), upload(), parametrize, RC-13 bulk-import integrity regressions (BUG-057/058/081/085/089/111)., _s1() (+37 more)

### Community 78 - "reports.py"
Cohesion: 0.15
Nodes (17): _ascii_cells(), create_pdf_report(), export_emissions(), generate_report(), _pdf_fonts(), route, Generate PDF report based on filters, Prevent formula injection (DDE/CSV injection) in Excel cells including leading… (+9 more)

### Community 79 - "test_qfull_unit_conversions.py"
Cohesion: 0.06
Nodes (22): test_qfull_unit_conversions.py QFULL END-TO-END CALCULATION PIPELINE VALIDATION…, Indirect steam: 100 MMBtu = 29307.1 kWh (1 MMBtu = 293.071 kWh) Both should…, 100 MMBtu → EXPECTED_CO2 tonnes., 100 MMBtu = 100,000,000 BTU Both should give the same CO2…, 100 MMBtu = 100 * 1e6 BTU / 3412.142 BTU/kWh = 29307.1 kWh Formula…, 1 MWh = 1000 kWh → scaling test. 29307.1 kWh = 29.307 MWh → same CO2., Combustion Tier 1: validate that different EF unit representations give the…, Direct: 1000 m3 * 1.9 kg/m3 = 1.9 t CO2. (+14 more)

### Community 80 - "Feature Specification: Batch Approve/Reject Pending Records"
Cohesion: 0.08
Nodes (23): Content Quality, Feature Readiness, Notes, Requirement Completeness, Specification Quality Checklist: batch-approve-reject, Complexity Tracking, Constitution Check, Documentation (this feature) (+15 more)

### Community 81 - "PVGIS Data Analyzer - Walkthrough"
Cohesion: 0.08
Nodes (24): 1. Start the Server, 2. Access the Application, 3. Upload PVGIS Data, 4. View Analysis, Annual Production, Application Launch, Backend Components, Complete Analysis Results (+16 more)

### Community 82 - "Comprehensive GHG Engine & MRV Platform Independent Validation Report"
Cohesion: 0.08
Nodes (24): 10. Appendices, 1. Executive Summary, 2. Standards & Methodology Inventory, 3. Test Methodology & Validation Architecture, 4. Inventory of Tests Executed, 5. Validation Results Matrix, 6. Discrepancy & Bug Catalog, 7. Permanent Regression Suite Audit (+16 more)

### Community 83 - "CCUSVentingCalculator"
Cohesion: 0.12
Nodes (15): CCUSVentingCalculator, CrudeTransportLossesCalculator, API Compendium 2021 Section 6.9 - CCUS & Geological Storage Vented Emissions…, API Compendium 2021 Section 6.10 - Crude Oil Transport Supports: - 6.10.1…, Unit and Golden Tests for API Compendium 2021 Sections 6.9 & 6.10: CCUS,…, Tests for API Compendium 2021 §6.9 CCUS & Geological Storage., Stripper off-gas venting with capture efficiency., Supercritical CO2 storage wellhead blowdown (Equation 6-27). (+7 more)

### Community 84 - "README.md"
Cohesion: 0.08
Nodes (24): 1. Backend Setup (Flask), 2. Frontend Setup (React + Vite), 🏗️ Architecture & Tech Stack, Configure environment variables, Configure environment variables, Create and activate virtual environment (optional but recommended), Greenhouse Gas (GHG) Accounting & Reporting Platform, Install dependencies (+16 more)

### Community 85 - "Proposed Changes"
Cohesion: 0.08
Nodes (23): Authentication and User-Specific Database Implementation, Automated Tests, Backend - Database Architecture, Database Cleanup, Frontend - Authentication UI, Frontend - Login Page Integration, Manual Verification, [MODIFY] All other HTML pages in public folder (+15 more)

### Community 86 - "Dashboard Categorical Overview Fixes - Walkthrough"
Cohesion: 0.08
Nodes (23): 1. Enhanced Categorical Breakdown ([dashboard.js](file:///c:/Users/samsung/Desktop/h/public/dashboard.js#L439-L520)), 2. Mitigation Number Formatting, 3. Updated Subtitle ([dashboard.html](file:///c:/Users/samsung/Desktop/h/public/dashboard.html#L469)), Activity Name Clarification, Added "All Years" Option ([carbon-intensity.js](file:///c:/Users/samsung/Desktop/h/public/carbon-intensity.js#L36-L43)), Advanced "Glassy" PDF Reports ([modern-report.js](file:///c:/Users/samsung/Desktop/h/public/modern-report.js)), Carbon Intensity Year Filter Fix, Categorical Emissions Overview Section (+15 more)

### Community 87 - "Complete CAD/Design View - All 12 Gaps"
Cohesion: 0.08
Nodes (23): 10. Shade Report Integration (#5), 11. Drone Imagery Underlay (#9), 12. ML-Optimized Layout (#12), 1. Layer Toggle Controls, 2. Site Measurements, 3. Sun Path Animation (#11), 4. Dimensions & Annotations (#2), 5. Module-Level Data Overlay (#6) (+15 more)

### Community 88 - "CAD Enhancements: Dimensions & Module Overlay - Complete"
Cohesion: 0.08
Nodes (23): 1. **Dimension Annotations** (Gap #2), 2. **Module Performance Overlay** (Gap #6), A. Shading Analysis 🌑, B. Production Heat Map ⚡, C. Defect Zones ⚠️, CAD Enhancements: Dimensions & Module Overlay - Complete, Comparison: Before vs. After, Dimensions (+15 more)

### Community 89 - "🎨 SolarEPC-Pro UI/UX Enhancement - Complete"
Cohesion: 0.08
Nodes (23): 1. **Animated Gradient Background**, 2. **Glassmorphism Sidebar**, 3. **Interactive Metric Cards**, 4. **Enhanced Buttons**, 5. **Modern Tab System**, 6. **Gradient Text Headers**, 7. **Enhanced Inputs**, 📊 Accessibility (+15 more)

### Community 90 - "custom_factors.py"
Cohesion: 0.14
Nodes (29): _process_row_custom_factors(), CustomFactor, Permits superuser and admin roles for data management operations. NOTE:…, superuser_required(), archive_custom_factor(), _canonical_factor_unit(), _check_plausibility(), create_custom_factor() (+21 more)

### Community 91 - "test_stress_boundary_resilience.py"
Cohesion: 0.11
Nodes (12): boundary_client(), fixture, test_stress_boundary_resilience.py ================================== Pillar 4:…, API endpoints under hostile, oversized, or malformed inputs., API endpoints must cleanly reject NaN and Infinity with 400/422 and 0 crashes., 1 MB giant string payload in text fields must not cause server crash or memory…, Formula injection patterns (=cmd|, @SUM, +1+1) must not be executed., Malformed, empty, or non-dictionary JSON payloads must return 400/422 cleanly. (+4 more)

### Community 92 - "test_production_smoke.py"
Cohesion: 0.08
Nodes (23): fixture, Phase 7.1 — Production Smoke Tests. High-speed (<10 seconds), robust smoke test…, SMOKE-08: Standard scf to m3 conversion factor is accurate., SMOKE-09: Unhandled 404 routes return JSON, not HTML error pages., SMOKE-10: Insecure hard-coded dev accounts (a@a, a) do not exist., SMOKE-01: Health check endpoint responds with 200 and status ok., SMOKE-02: Deep readiness probe confirms database connectivity and WAL…, SMOKE-03: Root API gateway index responds. (+15 more)

### Community 93 - "UI"
Cohesion: 0.12
Nodes (13): shot(), UI, i, ri, yi, cases, routes, list (+5 more)

### Community 94 - "Solar PV Calculator - Advanced Features Implementation Summary"
Cohesion: 0.09
Nodes (22): 1. Chart Export Module, 2. CSV Export Module, 3. System Presets Module, 4. PVGIS API Integration, 5. Financial Calculator Module, 6. Hourly Simulation Engine, 📊 Feature Comparison: Before vs. After, 💡 How to Proceed (+14 more)

### Community 95 - "3. Security, Authorization & RBAC"
Cohesion: 0.09
Nodes (22): 1. Web & Real-Time Communications, 2. Computational & Numerical Logic, 3. Security, Authorization & RBAC, 4. Concurrency & Background Processing, Automated Tests, Comprehensive Defect Remediation Implementation Plan, Manual / System Verification, [MODIFY] [auth.py](file:///c:/Users/samsung/Desktop/H2/new/server/routes/auth.py) (+14 more)

### Community 96 - "TestCalculationMutations"
Cohesion: 0.10
Nodes (11): Diff Test: Flaring dual-efficiency model (elevated and enclosed)., Mutant: Flaring calculation completely drops native CO2 from gas stream., Mutant: CH4 standard density (0.6785 kg/m3) swapped with CO2 density (1.861…, Verifies that mathematical mutations cause tests to fail (100% mutant kill…, Mutant: Flaring unburnt CH4 calculated with (1 + eff) instead of (1 - eff)., Mutant: scf to m3 factor mutated from 0.0283168 to 0.0383168 (+35% error)., Mutant: AR5 GWP for CH4 (28) mutated to SAR (21) or AR4 (25)., Mutant: CO2/CH4 molar ratio 44.01/16.04 (2.7437) inverted to 16.04/44.01… (+3 more)

### Community 98 - "Examples"
Cohesion: 0.09
Nodes (21): Asking for Permissions, Example 10: Searching Pull Requests, Example 11: Searching Commits, Example 12: Searching Code, Example 13: Searching Issues, Example 14: Running (Dispatching) a Workflow, Example 15: Listing, Viewing, or Watching Workflow Runs, Example 1: Creating an Issue (+13 more)

### Community 99 - "TestCombustionTier1"
Cohesion: 0.10
Nodes (14): Test zero quantity combustion., Test large quantity combustion., Test missing factor fields fallback gracefully., Test Suite for Combustion Tier 3 calculations., Test standard Tier 3 calculation with composition., Test pure methane combustion., Test calculation with zero combustion efficiency (complete slip)., Independent CO2e calculation using AR5 GWPs. (+6 more)

### Community 100 - "SolarEPC-Pro v3.0 - Complete Implementation"
Cohesion: 0.10
Nodes (20): 🎉 100% COMPLETE: All 27 Gaps Addressed, 🙏 Acknowledgments, 📈 Business Value, 📚 Complete Implementation Guides (3), 💼 Deployment Options, 📖 Documentation Index, 📊 Final Achievement, 🏆 Final Assessment (+12 more)

### Community 101 - "RTK Commands by Workflow"
Cohesion: 0.10
Nodes (19): Analysis & Debug (70-90% savings), Backend architecture, Build & Compile (80-90% savings), Commands, Files & Search (60-75% savings), Frontend architecture, Git (59-80% savings), GitHub (26-87% savings) (+11 more)

### Community 102 - "get_active_gwp"
Cohesion: 0.05
Nodes (43): get_active_gwp(), Dynamically resolve the active GWP factors dictionary based on standard and…, _compute_emissions_impl(), _has_factor_values(), custom_factor_data(), Map a CustomFactor row to the calculator's factor_data structure., Factor data for a calculation. Raises ValidationError when a required factor is…, resolve_factor() (+35 more)

### Community 103 - "test_audit_remediation.py"
Cohesion: 0.03
Nodes (67): client(), fixture, Defect 5: Verify update_emission merges existing process_type and inputs., Defect 6: Verify bulk import for Scope 2 & 3 blocks it_admin and enforces…, Defect 7: Verify IT admin cannot access QA/QC resolve and users cannot verify…, Defect 8: Verify base year recalculation route enforces role, sets created_by,…, Defect 9: Verify save_cbam_export checks facility access for existing records…, Verify short ton conversion to kg (907.185 kg). (+59 more)

### Community 104 - "test_audit_rc11_sbti.py"
Cohesion: 0.31
Nodes (10): SbtiTarget, fixture, RC-11 SBTi trajectory regressions (BUG-014/019/028/059). Hand values in each…, setup(), test_bug014_current_partial_year_is_not_the_progress_year(), test_bug019_region_restricted_user_uses_region_baseline(), test_bug019_scope_subset_uses_its_own_baseline(), test_bug028_no_data_is_not_on_track() (+2 more)

### Community 105 - "CAD/Design View - Gap Analysis"
Cohesion: 0.11
Nodes (18): Advanced Features (Nice-to-Have), CAD/Design View - Gap Analysis, Comparison: SolarEPC-Pro vs. Aurora Solar CAD, Current State ✅, High Priority (Must-Have for Professional CAD), Identified Gaps (12 Total), Medium Priority (Aurora Solar Features), Phase 1: Professional Essentials (1-2 weeks) (+10 more)

### Community 106 - "IMPLEMENTATION_PLAN.md"
Cohesion: 0.11
Nodes (18): Before starting, Data policy (decided by the user, 2026-09-26), Excluded entries, Fix order, IMPLEMENTATION PLAN — GHG Platform Audit Remediation, PHASE P0 — Prerequisites (do first — other fixes depend on these), PHASE P1 — Critical data-integrity & security defects, PHASE P2 — Critical & high calculation errors (+10 more)

### Community 107 - "SectionMethods.jsx"
Cohesion: 0.06
Nodes (26): EmissionFactorOption(), ACTIVITY, applyChoice(), COMB, currentChoice(), LEGACY(), MEASURED, METHOD_KEYS (+18 more)

### Community 108 - "emission_factors_routes.py"
Cohesion: 0.06
Nodes (45): activity_factor_list(), equipment_factor_list(), get_factor_by_process_category(), get_factor_by_segment(), get_factors_by_segment_and_category(), Emission Factors Database - API Compendium 2021 Complete catalog from Sections…, Returns all emission factors applicable to the given segment. Args: segment…, Returns all emission factors for the given process category. Args:… (+37 more)

### Community 109 - "What Will Be DELETED"
Cohesion: 0.11
Nodes (17): 10. `scripts/` Folder (root level), 1. Old Legacy App Files (root level), 2. Debug / Check / Verify Scripts (root level — one-off dev tools), 3. Test Scripts (root level), 4. Seed / Migration Scripts (root level), 5. PDF References / Extract Text Files (research artifacts, not runtime), 6. Old Databases (not used by new app), 7. Utility/Setup Scripts for Old Stack (+9 more)

### Community 110 - "Performance Optimization Walkthrough"
Cohesion: 0.11
Nodes (17): 1. Database Indices, 2. Specialized Summary Endpoint, 3. Filters Endpoint, 4. Pagination & Year Filtering, 5. Frontend Optimizations, Bottleneck Analysis, Changes Implemented, Data Transfer Reduction (+9 more)

### Community 111 - "🎉 ALL CAD FEATURES COMPLETE - 12/12 IMPLEMENTED!"
Cohesion: 0.11
Nodes (17): 1. Shade Report Generation (#5) ✅, 2. Drone Imagery Underlay (#9) ✅, 3. Roof Module Placement (#4) ✅, 🎉 ALL CAD FEATURES COMPLETE - 12/12 IMPLEMENTED!, CAD Features (12/12) ✅, Commercial Equivalents, Complete Feature List (12/12), Core Features (27/27) ✅ (+9 more)

### Community 112 - "Phase 1 — Testing Inventory"
Cohesion: 0.11
Nodes (17): 1. Backend Test Infrastructure, 2. Backend Test Files Inventory (43 files, 880 tests), 3. Frontend Test Infrastructure, 4. Security Testing, 5. Performance Testing, 6. E2E Testing, 7. Coverage Analysis, 8. Recommended Testing Additions (+9 more)

### Community 113 - "FINAL VALIDATION REPORT"
Cohesion: 0.11
Nodes (17): Calculation Engine: HIGH CONFIDENCE, CI/CD: INCOMPLETE, CRITICAL Findings, Database: ADEQUATE for SQLite, REQUIRES REVIEW for PostgreSQL, Executive Summary, FINAL VALIDATION REPORT, Frontend: INCOMPLETE TESTING COVERAGE, HIGH Findings (+9 more)

### Community 114 - "Tier 3 browser test — every Scope 1 process type (2026-09-28)"
Cohesion: 0.18
Nodes (10): Fixes, Method, Re-run after the fixes (fresh database copy), Remaining issues fixed (follow-up, 2026-09-28), Results before fixes, Table and record, Tier 3 browser test — every Scope 1 process type (2026-09-28), Values shown on the form but not sent (+2 more)

### Community 115 - "audit.py"
Cohesion: 0.27
Nodes (17): audit_access_required(), _build_audit_query(), export_audit_logs(), get_audit_filters(), get_audit_logs(), get_audit_stats(), is_it_role(), route (+9 more)

### Community 116 - "Exploratory browser test — findings and fixes (2026-09-28)"
Cohesion: 0.20
Nodes (9): Audit trail and data integrity, Displays and exports, Exploratory browser test — findings and fixes (2026-09-28), How it was run, Minor, Not changed, Offered but could not be saved, Tests (+1 more)

### Community 117 - "test_audit_rc17_methodology.py"
Cohesion: 0.18
Nodes (12): _ch4(), RC-17 methodology regressions (BUG-100 .. BUG-103), checked against the API…, test_bug100_eq_6_14_monitoring_survey(), test_bug100_table_6_14_high_bleed(), test_bug100_table_6_15_subpart_w_intermittent_is_per_hour(), test_bug101_exhibit_6_25_absolute_pressure(), test_bug101_residual_pressure_counts_only_released_gas(), test_bug102_condensate_table_6_24() (+4 more)

### Community 118 - "L/lib.mjs"
Cohesion: 0.16
Nodes (9): ACCTS, dashboard(), ddOptions(), OUT, dds, i, row, kpi() (+1 more)

### Community 119 - "toasts"
Cohesion: 0.15
Nodes (10): grpOf(), toasts(), save(), i, open(), ORDER, save(), tr (+2 more)

### Community 120 - "4. HTTP & Application Layer Hardening"
Cohesion: 0.12
Nodes (16): 1. Executive Security Summary, 2.1 Password Complexity & Storage, 2.2 Session Management & Defense, 2. Authentication Lifecycle & Session Security, 3.1 Segregation of Duties (SoD) Verification, 3.2 Facility-Level Row-Level Security (RLS) & IDOR Defense, 3.3 Maker-Checker Verification Protocol, 3. Authorization, RBAC & Segregation of Duties (SoD) (+8 more)

### Community 121 - "test_audit_rc10_uncertainty.py"
Cohesion: 0.18
Nodes (16): default_rel_1sigma(), inventory_uncertainty(), Inventory uncertainty (audit RC-10) — IPCC 2006 Vol.1 Ch.3 Approach 1 with EF…, Normative 1-sigma defaults when nothing valid is stored (IPCC Vol.1 Table 3.1 /…, _tier(), _valid(), ctx(), fixture (+8 more)

### Community 122 - "dependencies"
Cohesion: 0.12
Nodes (16): bcryptjs, body-parser, cors, express, express-rate-limit, dependencies, bcryptjs, body-parser (+8 more)

### Community 123 - "Backend Components"
Cohesion: 0.12
Nodes (15): Automated Tests, Backend Components, Data Processing Features, Frontend Components, Manual Verification, [NEW] [package.json](file:///c:/Users/samsung/Desktop/csv/package.json), [NEW] [public/css/styles.css](file:///c:/Users/samsung/Desktop/csv/public/css/styles.css), [NEW] [public/index.html](file:///c:/Users/samsung/Desktop/csv/public/index.html) (+7 more)

### Community 124 - "Database Contents"
Cohesion: 0.12
Nodes (15): Audit Trail (150 Entries), Base Year & Goals, Base Year Recalculation History (3 Records), Comprehensive Test Database Creation, Custom Emission Factors (5 Total), Data Generation Method, Database Contents, Database Files (+7 more)

### Community 125 - "Client Application & Routing"
Cohesion: 0.12
Nodes (15): Architecture & Reimagined UI Layout, Automated Build & Syntax Check, Client Application & Routing, Functional Verification, [MODIFY] [App.jsx](file:///c:/Users/samsung/Desktop/H2/new/client/src/App.jsx), [MODIFY] [Diagnostics.jsx](file:///c:/Users/samsung/Desktop/H2/new/client/src/pages/Diagnostics.jsx), [MODIFY] [QADashboard.jsx](file:///c:/Users/samsung/Desktop/H2/new/client/src/pages/QADashboard.jsx), [MODIFY] [Sidebar.jsx](file:///c:/Users/samsung/Desktop/H2/new/client/src/components/layout/Sidebar.jsx) (+7 more)

### Community 126 - "Implementation: All 27 Gaps ✅"
Cohesion: 0.12
Nodes (15): Achievement:, Advanced Technical ✅, CAD/Design Features (12/12):, 🎨 CAD/Design View - ALL 12 FEATURES COMPLETE! ✅, Code Quality ✅, Core Implementation (27/27):, Data Persistence ✅, 🎉 FINAL SUMMARY: 27 Core + 12 CAD = 39 Features COMPLETE (+7 more)

### Community 127 - "GHGCalculator"
Cohesion: 0.19
Nodes (3): GHGCalculator, ValueError, API Compendium 2021, Section 6.4, Equation 6-3 V (scf/event) = (π/4) ×…

### Community 128 - "test_audit_rc9_dashboard.py"
Cohesion: 0.19
Nodes (14): upstream | midstream | downstream | None (unknown / not set)., segment_category(), batch(), RC-9 / RC-12 dashboard regressions on a controlled dataset. Hand values: AR5…, batch-all returns the summary for every year (the client picks the selected…, rows_for(), test_bug004_040_061_facility_filters_and_source_split(), test_bug005_072_gwp20_uses_active_standard() (+6 more)

### Community 129 - "test_all_bulk_imports.py"
Cohesion: 0.19
Nodes (17): app(), client(), logged_client(), fixture, DEF-04 Verification: Ensure duplicate rows are skipped by default and updated…, Verifies that non-combustion sources (e.g. pneumatics) normalize fuel_k to…, test_bulk_import_custom_factors(), test_bulk_import_duplicate_prevention_and_overwrite() (+9 more)

### Community 130 - "new/.specify/scripts/powershell/common.ps1"
Cohesion: 0.23
Nodes (13): Find-SpecifyRoot(), Format-SpecKitCommand(), Get-CurrentBranch(), Get-FeaturePathsEnv(), Get-InvokeSeparator(), Get-NormalizedPriority(), Get-Python3Command(), Get-RepoRoot() (+5 more)

### Community 131 - ".specify/scripts/powershell/common.ps1"
Cohesion: 0.23
Nodes (13): Find-SpecifyRoot(), Format-SpecKitCommand(), Get-CurrentBranch(), Get-FeaturePathsEnv(), Get-InvokeSeparator(), Get-NormalizedPriority(), Get-Python3Command(), Get-RepoRoot() (+5 more)

### Community 132 - "TestCleanUncertainty"
Cohesion: 0.16
Nodes (9): CLEAN-SLATE VALIDATION: Analytical Uncertainty Propagation Validates Tier 1/2/3…, Independent validation of analytical uncertainty calculations., Even with extreme relative uncertainty (e.g. 150%), lower bound must be clipped…, TestCleanUncertainty, INDEPENDENT REFERENCE MODEL: Analytical Uncertainty Propagation First-…, Gaussian error propagation for product Y = Activity * EF: u_rel(Y) =…, Gaussian propagation for independent sum Z = sum(Y_i): u_abs(Z) =…, ref_propagate_product_uncertainty() (+1 more)

### Community 133 - "BUG-046 — Equity-share allocation ignores effective dates (time-sliced ownership never applied) and POST /api/equity/shares accepts any percentage (500, -50, inf) from any business role"
Cohesion: 0.13
Nodes (15): Actual, Additional confirmation (BUG-004), Additional confirmation (BUG-007), Additional confirmation (BUG-013), Additional confirmation (BUG-033), Affected Components, BUG-046 — Equity-share allocation ignores effective dates (time-sliced ownership never applied) and POST /api/equity/shares accepts any percentage (500, -50, inf) from any business role, Evidence (+7 more)

### Community 134 - "Critical Bugs (Data-Affecting)"
Cohesion: 0.13
Nodes (14): Already Fixed This Session, BUG-1 — `emissions.py` update_emission(): recalculate block always runs, BUG-2 — `emissions.py` import_emissions(): file handle leak, BUG-3 — `dashboard.py` get_categorical_breakdown(): Scope 3 inflates region totals, BUG-4 — `scope2.py` bulk_import_scope2(): units ambiguity in co2e formula, BUG-5 — `dashboard.py` get_uncertainty_analysis(): no facility/activity/division filter, BUG-6 — `emissions.py` add_emission(): goal notification checks Scope 1 only, BUG-7 — `emissions.py` add_emission(): debug print() statements in production (+6 more)

### Community 135 - "CO & Combustion Efficiency Implementation Plan"
Cohesion: 0.13
Nodes (14): CO & Combustion Efficiency Implementation Plan, Emission Sources Management (Exhaustive Inventory), Goal Description, Manage Data Page, Manual Verification, Manual Verification, [MODIFY] [manage-data.html](file:///c:/Users/samsung/Desktop/h/public/manage-data.html), [MODIFY] [manage-data.html](file:///c:/Users/samsung/Desktop/h/public/manage-data.html) (+6 more)

### Community 136 - "Comprehensive Database Architecture, ACID Integrity & Concurrency Audit"
Cohesion: 0.13
Nodes (14): 1. Executive Database Summary, 2. Schema Architecture & Model Inventory, 3.1 Foreign Key Enforcement, 3.2 Cascading Delete Safety, 3. Referential Integrity & Cascading Behavior, 4.1 Atomic Unit of Work Pattern, 4.2 Error Handling & Rollback Verification (Remediated L-12), 4. ACID Compliance & Transactional Atomicity (+6 more)

### Community 137 - "Enterprise Production Readiness, Deployment & Disaster Recovery Audit"
Cohesion: 0.13
Nodes (14): 1. Executive Production Readiness Summary, 2.1 Dockerfile Architecture & Findings, 2.2 Docker Compose Topology, 2. Containerization & Build Pipeline Audit, 3. Environment Hardening & Configuration Audit, 4.1 Python Dependencies (`new/server/requirements.txt`), 4.2 Frontend Dependencies (`new/client/package.json`), 4. Software Dependencies & Vulnerability Audit (+6 more)

### Community 138 - "Calculation Validation Report"
Cohesion: 0.13
Nodes (14): Calculation Validation Matrix, Calculation Validation Report, CONCERN-01 (MEDIUM): N2O Default Factor Inconsistency, CONCERN-02 (LOW): Mobile vs. Stationary Scope Classification, CONCERN-03 (LOW): Cogeneration Allocation Edge Case, Flaring Efficiency — Verified, Golden Dataset Assessment, GWP Values — Independently Verified (+6 more)

### Community 139 - "3. Dimensional Consistency & Physical Equations"
Cohesion: 0.13
Nodes (14): 1.1 Canonical Conversion Constants, 1. Unit Conversion Factor Architecture, 2. Invertibility & Round-Trip Numerical Verification, 3.1 Stationary Combustion (Tier 1/2), 3.2 Flaring Stoichiometric Carbon Mass Balance (D-01), 3.3 Ideal Gas / Real Gas Blowdown Venting, 3.4 Storage Tank Flash Gas (GOR Method), 3.5 Global Warming Potential (GWP) Aggregation (+6 more)

### Community 140 - ".calculate_co2e"
Cohesion: 0.07
Nodes (14): parametrize, BUG-100: 13.5 is the Subpart W intermittent factor in scf/HOUR (API 2021 Table…, Verifies drilling mud degassing calculations against independent reference…, TestMudDegassingBattery, _val(), Diff Test: Liquids unloading wellbore geometry., Diff Test: Storage tank flashing GOR method., Diff Test: Pneumatic devices continuous bleed and intermittent. (+6 more)

### Community 141 - "test_audit.py"
Cohesion: 0.17
Nodes (6): admin_user(), client(), it_admin_user(), fixture, regular_user(), seed_audit_logs()

### Community 142 - "TestPropertyInvariantsHypothesis"
Cohesion: 0.21
Nodes (9): given, settings, GWP AR5 (28) > GWP AR6 (27.9) > GWP AR4 (25) for methane., Hypothesis-driven property invariance tests., E(k * X) == k * E(X) for stationary combustion., E(A + B) == E(A) + E(B) for stationary combustion., A > B ==> E(A) >= E(B)., X >= 0 ==> E(X) >= 0 across all gases. (+1 more)

### Community 143 - "test_audit_rc7_rc8.py"
Cohesion: 0.16
Nodes (14): BUG-023: one percent/fraction decision for the whole analysis…, composition_fractions(), ValueError, Convert one gas analysis to mole fractions, deciding percent vs fraction ONCE.…, parametrize, RC-7 (GWP constants) and RC-8 (gas composition basis) regressions., Hand calc per the audit repro: 1.0 mol% C4 must be 1 %, not 100 %., test_bug013_client_constants_match_server() (+6 more)

### Community 144 - "BUG-091 — Dehydrator throughput entered under the label "MMscf/yr" is saved with unit "MMscf/day" (record activity unit 365× off)"
Cohesion: 0.14
Nodes (14): Actual, Additional confirmation (BUG-072), Additional confirmation (BUG-072), Additional confirmation (BUG-085), Affected Components, BUG-091 — Dehydrator throughput entered under the label "MMscf/yr" is saved with unit "MMscf/day" (record activity unit 365× off), Evidence, Expected (+6 more)

### Community 145 - "make_db"
Cohesion: 0.19
Nodes (11): api_client(), db_path(), get_app(), make_db(), Create audit/db/<name>.db from the pristine snapshot and add audit users (raw…, Import the real Flask app bound to audit/db/<name>.db (one db per process)., c(), fac() (+3 more)

### Community 146 - "Key Improvements"
Cohesion: 0.14
Nodes (13): 1. Fluid Desktop Scaling, 2. Mobile Responsive Sidebar, 3. Integrated Facility Management, 4. Silent UI Experience, 5. Modernized Facility Selector, 6. Modernized Trend Chart, 7. Modernized Source Chart, 8. Modernized Breakdown Table (+5 more)

### Community 147 - "Frontend UI"
Cohesion: 0.14
Nodes (13): Backend API, Database Schema, Frontend UI, Goal Description, Manual Verification, [MODIFY] [emissions-calculator.html](file:///c:/Users/samsung/Desktop/h/public/emissions-calculator.html), [MODIFY] [manage-data.html](file:///c:/Users/samsung/Desktop/h/public/manage-data.html), [MODIFY] [manage-data.html](file:///c:/Users/samsung/Desktop/h/public/manage-data.html) (Script Section / attributes) (+5 more)

### Community 148 - "🎉 Final CAD Implementation Complete"
Cohesion: 0.14
Nodes (13): 1. Setback Compliance (#3) - COMPLETE, 2. DXF Export (#1) - COMPLETE, 💰 Commercial Value, DXF Export, 📦 Files Modified, 🎉 Final CAD Implementation Complete, 📊 Final CAD Status: 9/12 Implemented, Fully Working (9/12) ✅ (+5 more)

### Community 149 - "Proposed Changes"
Cohesion: 0.14
Nodes (13): 1. Glassmorphism Card System, 2. Animated Metrics Cards, 3. Interactive Chart Enhancements, 4. Progressive Disclosure, 5. Micro-interactions, CSS Modules, Design Philosophy: "Energy in Motion", Proposed Changes (+5 more)

### Community 150 - "3. Subsystem Architecture Analysis"
Cohesion: 0.14
Nodes (13): 1. Architectural Reality vs. README Claims, 2. Directory Structure & Lifecycle Classification, 3.1 Frontend Single-Page Application (SPA), 3.2 Backend API Server, 3.3 Database & Storage Layer, 3.4 Authentication, Authorization & Segregation of Duties, 3.5 Calculation Engine Architecture, 3.6 Background Ingestion & Processing (+5 more)

### Community 151 - "Phase 49 — Human Review Required"
Cohesion: 0.14
Nodes (13): HR-01: N2O Default Emission Factor for Flaring, HR-02: Mobile vs. Stationary Combustion Boundary, HR-03: OGMP 2.0 Level Assignment Methodology, HR-04: Scope 3 Category Completeness, HR-05: Uncertainty GWP Interaction, HR-06: Custom Emission Factor Validation Boundary, HR-07: CSRF Protection Architecture, HR-08: Production Database and Backup Procedure (+5 more)

### Community 152 - "Complete Repository Audit & Architecture Baseline"
Cohesion: 0.14
Nodes (13): 1. System Architecture Overview, 2. Active Calculation Paths, 3.1 `new/server/calculations/legacy_engine.py` (Facade & Legacy Fallback), 3.2 Obsolete Scratch Scripts & Archive Files, 3. Inactive, Legacy & Duplicate Calculation Paths, 4. Data Sources & Storage Models, 5. Test Infrastructure Audit, 6.1 Backend Dependencies (`new/server/requirements.txt`) (+5 more)

### Community 153 - "BUG-016 — Alembic migration chain is unusable: `flask db upgrade` fails on both the existing DB and a fresh DB"
Cohesion: 0.14
Nodes (14): Acceptance Criteria, Affected Features, Affected Files, Backend Changes, Browser Verification, BUG-016 — Alembic migration chain is unusable: `flask db upgrade` fails on both the existing DB and a fresh DB, Calculation Changes, Database Changes (+6 more)

### Community 154 - "BUG-011 — Well-completion "Rate × Duration" method divides the Mcf/hr rate by 24 (treats it as Mcf/day): CH4 understated 24×"
Cohesion: 0.14
Nodes (14): Acceptance Criteria, Affected Features, Affected Files, Backend Changes, Browser Verification, BUG-011 — Well-completion "Rate × Duration" method divides the Mcf/hr rate by 24 (treats it as Mcf/day): CH4 understated 24×, Calculation Changes, Database Changes (+6 more)

### Community 155 - "BUG-012 — Well-completion Tier 3 uses `amount` as both the flowback volume and the event count (volume squared), and ignores rate × duration when the method dropdown is left at its default"
Cohesion: 0.14
Nodes (14): Acceptance Criteria, Affected Features, Affected Files, Backend Changes, Browser Verification, BUG-012 — Well-completion Tier 3 uses `amount` as both the flowback volume and the event count (volume squared), and ignores rate × duration when the method dropdown is left at its default, Calculation Changes, Database Changes (+6 more)

### Community 156 - "BUG-023 — Tier 3 combustion/flaring gas composition: each component is converted percent→fraction on its own, so mol% values ≤ 1 (e.g. C4 = 1.0 %, C5 = 0.5 %) become 100 % / 50 %; CO2 inflated 2.7× on the app's own template sample"
Cohesion: 0.14
Nodes (14): Acceptance Criteria, Affected Features, Affected Files, Backend Changes, Browser Verification, BUG-023 — Tier 3 combustion/flaring gas composition: each component is converted percent→fraction on its own, so mol% values ≤ 1 (e.g. C4 = 1.0 %, C5 = 0.5 %) become 100 % / 50 %; CO2 inflated 2.7× on the app's own template sample, Calculation Changes, Database Changes (+6 more)

### Community 157 - "BUG-027 — Tier 1 combustion applies the catalog HHV in the wrong basis when the activity unit is mass or the other phase (diesel/crude per tonne ×3.6, natural gas per tonne ÷40, ethane per scf ×39)"
Cohesion: 0.14
Nodes (14): Acceptance Criteria, Affected Features, Affected Files, Backend Changes, Browser Verification, BUG-027 — Tier 1 combustion applies the catalog HHV in the wrong basis when the activity unit is mass or the other phase (diesel/crude per tonne ×3.6, natural gas per tonne ÷40, ethane per scf ×39), Calculation Changes, Database Changes (+6 more)

### Community 158 - "BUG-047 — Tier 1 fugitive and equipment factors in "per hour" units are multiplied only by the source count (no operating hours): annual CH4 understated 8,760×, and Tier 1 disagrees with Tier 3 for the same factor"
Cohesion: 0.14
Nodes (14): Acceptance Criteria, Affected Features, Affected Files, Backend Changes, Browser Verification, BUG-047 — Tier 1 fugitive and equipment factors in "per hour" units are multiplied only by the source count (no operating hours): annual CH4 understated 8,760×, and Tier 1 disagrees with Tier 3 for the same factor, Calculation Changes, Database Changes (+6 more)

### Community 159 - "BUG-048 — Tier 3 fugitive calculators misread catalog factor units: "CH₄" (Unicode subscript) is not recognised as methane (×0.85 applied), and ComponentFugitiveCalculator treats tonne/hr factors as kg/hr (1000× too low)"
Cohesion: 0.14
Nodes (14): Acceptance Criteria, Affected Features, Affected Files, Backend Changes, Browser Verification, BUG-048 — Tier 3 fugitive calculators misread catalog factor units: "CH₄" (Unicode subscript) is not recognised as methane (×0.85 applied), and ComponentFugitiveCalculator treats tonne/hr factors as kg/hr (1000× too low), Calculation Changes, Database Changes (+6 more)

### Community 160 - "BUG-049 — Generic factor math ignores the 10³ / 10⁶ multiplier in factor denominators: offshore gas fugitives 1,000,000× and refinery fuel-gas fugitives 1,000× overstated"
Cohesion: 0.14
Nodes (14): Acceptance Criteria, Affected Features, Affected Files, Backend Changes, Browser Verification, BUG-049 — Generic factor math ignores the 10³ / 10⁶ multiplier in factor denominators: offshore gas fugitives 1,000,000× and refinery fuel-gas fugitives 1,000× overstated, Calculation Changes, Database Changes (+6 more)

### Community 161 - "BUG-063 — Tier 2 custom factors whose unit is not "kg/<unit>" are misapplied (Manage Data form stores a bare activity unit): tonne factors ×1000 (×10⁶ with kg activity), no volume/mass conversion at all; unknown units such as kg/TJ or kg/GJ are applied 1:1"
Cohesion: 0.14
Nodes (14): Acceptance Criteria, Affected Features, Affected Files, Backend Changes, Browser Verification, BUG-063 — Tier 2 custom factors whose unit is not "kg/<unit>" are misapplied (Manage Data form stores a bare activity unit): tonne factors ×1000 (×10⁶ with kg activity), no volume/mass conversion at all; unknown units such as kg/TJ or kg/GJ are applied 1:1, Calculation Changes, Database Changes (+6 more)

### Community 162 - "BUG-110 — Onshore fugitives "Tier 1: Facility-Level" form: the on-screen preview says 16,644 tCO2e but the saved record is 1.456 tCO2e — the server ignores the selected facility type and duration and books the facility count as a count of valves"
Cohesion: 0.14
Nodes (14): Acceptance Criteria, Affected Features, Affected Files, Backend Changes, Browser Verification, BUG-110 — Onshore fugitives "Tier 1: Facility-Level" form: the on-screen preview says 16,644 tCO2e but the saved record is 1.456 tCO2e — the server ignores the selected facility type and duration and books the facility count as a count of valves, Calculation Changes, Database Changes (+6 more)

### Community 163 - "BUG-090 — Dehydrator form sends "Contactor Pressure" as `dehy_pressure`, but the server reads `dehy_press`: user pressure silently ignored, 800 psig default always used (AGR "routed to flare"/"flash gas recycled" checkboxes also unread)"
Cohesion: 0.14
Nodes (14): Acceptance Criteria, Affected Features, Affected Files, Backend Changes, Browser Verification, BUG-090 — Dehydrator form sends "Contactor Pressure" as `dehy_pressure`, but the server reads `dehy_press`: user pressure silently ignored, 800 psig default always used (AGR "routed to flare"/"flash gas recycled" checkboxes also unread), Calculation Changes, Database Changes (+6 more)

### Community 164 - "BUG-003 — Editing a Scope 1 record's quantity via PUT /api/emissions/<id> does not recalculate emissions (stale `amount` from source_payload wins)"
Cohesion: 0.14
Nodes (14): Acceptance Criteria, Affected Features, Affected Files, Backend Changes, Browser Verification, BUG-003 — Editing a Scope 1 record's quantity via PUT /api/emissions/<id> does not recalculate emissions (stale `amount` from source_payload wins), Calculation Changes, Database Changes (+6 more)

### Community 165 - "BUG-030 — POST /api/emissions/ calculates from `quantity`/`fuel_type` but stores only `amount`/`fuel`: records keep emissions with NULL activity quantity and fuel"
Cohesion: 0.14
Nodes (14): Acceptance Criteria, Affected Features, Affected Files, Backend Changes, Browser Verification, BUG-030 — POST /api/emissions/ calculates from `quantity`/`fuel_type` but stores only `amount`/`fuel`: records keep emissions with NULL activity quantity and fuel, Calculation Changes, Database Changes (+6 more)

### Community 166 - "BUG-037 — Editing a Scope 1 record replaces its propagated 1σ uncertainty with the raw catalog EF half-width (95 %, EF-only); user_uncertainty is stored unpropagated"
Cohesion: 0.14
Nodes (14): Acceptance Criteria, Affected Features, Affected Files, Backend Changes, Browser Verification, BUG-037 — Editing a Scope 1 record replaces its propagated 1σ uncertainty with the raw catalog EF half-width (95 %, EF-only); user_uncertainty is stored unpropagated, Calculation Changes, Database Changes (+6 more)

### Community 167 - "BUG-042 — Recalculating a Tier 2 (custom-factor) Scope 1 record drops the custom factor: emissions become 0 or silently switch to the catalog factor, while factor_source stays "custom""
Cohesion: 0.14
Nodes (14): Acceptance Criteria, Affected Features, Affected Files, Backend Changes, Browser Verification, BUG-042 — Recalculating a Tier 2 (custom-factor) Scope 1 record drops the custom factor: emissions become 0 or silently switch to the catalog factor, while factor_source stays "custom", Calculation Changes, Database Changes (+6 more)

### Community 168 - "BUG-068 — Purchased steam/heat (`indirect_steam`) and CHP allocation (`cogen_allocation`) are accepted as Scope 1 process types and added to Scope 1 totals (Scope 2 counted as Scope 1; CHP double counting)"
Cohesion: 0.14
Nodes (14): Acceptance Criteria, Affected Features, Affected Files, Backend Changes, Browser Verification, BUG-068 — Purchased steam/heat (`indirect_steam`) and CHP allocation (`cogen_allocation`) are accepted as Scope 1 process types and added to Scope 1 totals (Scope 2 counted as Scope 1; CHP double counting), Calculation Changes, Database Changes (+6 more)

### Community 169 - "BUG-024 — Tier 3 flaring/combustion renormalises the gas composition without N2 (and without unspecified components), inflating CH4 and CO2 by 1/(1 − x_inert)"
Cohesion: 0.14
Nodes (14): Acceptance Criteria, Affected Features, Affected Files, Backend Changes, Browser Verification, BUG-024 — Tier 3 flaring/combustion renormalises the gas composition without N2 (and without unspecified components), inflating CH4 and CO2 by 1/(1 − x_inert), Calculation Changes, Database Changes (+6 more)

### Community 170 - "BUG-001 — Bulk upload job API lets any logged-in role (user, it_admin) create/overwrite facilities and custom factors, bypassing RBAC and region scoping"
Cohesion: 0.14
Nodes (14): Acceptance Criteria, Affected Features, Affected Files, Backend Changes, Browser Verification, BUG-001 — Bulk upload job API lets any logged-in role (user, it_admin) create/overwrite facilities and custom factors, bypassing RBAC and region scoping, Calculation Changes, Database Changes (+6 more)

### Community 171 - "BUG-051 — Energy activity units kWh / MJ / Btu with a kg/MMBtu factor are treated as scf of gas (× 1020 Btu/scf): 1000 kWh of natural gas is 3.3× too low, MJ 7.6 % too high"
Cohesion: 0.14
Nodes (14): Acceptance Criteria, Affected Features, Affected Files, Backend Changes, Browser Verification, BUG-051 — Energy activity units kWh / MJ / Btu with a kg/MMBtu factor are treated as scf of gas (× 1020 Btu/scf): 1000 kWh of natural gas is 3.3× too low, MJ 7.6 % too high, Calculation Changes, Database Changes (+6 more)

### Community 172 - "BUG-050 — Negative activity amounts are accepted for process types that are not in the dispatcher (e.g. "loading") and saved as negative emissions"
Cohesion: 0.14
Nodes (14): Acceptance Criteria, Affected Features, Affected Files, Backend Changes, Browser Verification, BUG-050 — Negative activity amounts are accepted for process types that are not in the dispatcher (e.g. "loading") and saved as negative emissions, Calculation Changes, Database Changes (+6 more)

### Community 173 - "BUG-013 — AR5 20-year GWPs are wrong (CH4 82.5 instead of 84, N2O 268 instead of 264); AR6 pairs the fossil CH4 GWP-20 with the non-fossil-weighted GWP-100"
Cohesion: 0.14
Nodes (14): Acceptance Criteria, Affected Features, Affected Files, Backend Changes, Browser Verification, BUG-013 — AR5 20-year GWPs are wrong (CH4 82.5 instead of 84, N2O 268 instead of 264); AR6 pairs the fossil CH4 GWP-20 with the non-fossil-weighted GWP-100, Calculation Changes, Database Changes (+6 more)

### Community 174 - "BUG-005 — GWP-20 conversion in intensity-stats / intensity-trend hard-codes AR5 GWP-100 (28 / 265), so GWP-20 CO2e is wrong whenever the active standard is AR4 or AR6"
Cohesion: 0.14
Nodes (14): Acceptance Criteria, Affected Features, Affected Files, Backend Changes, Browser Verification, BUG-005 — GWP-20 conversion in intensity-stats / intensity-trend hard-codes AR5 GWP-100 (28 / 265), so GWP-20 CO2e is wrong whenever the active standard is AR4 or AR6, Calculation Changes, Database Changes (+6 more)

### Community 175 - "BUG-109 — Scope 1 form saves an entry with no Unit selected: the client silently assumes m³ (10 → 2,641.72 gal stored) while the server calculates from the raw 10 in calc_inputs, so the stored activity and its emissions disagree 264×"
Cohesion: 0.14
Nodes (14): Acceptance Criteria, Affected Features, Affected Files, Backend Changes, Browser Verification, BUG-109 — Scope 1 form saves an entry with no Unit selected: the client silently assumes m³ (10 → 2,641.72 gal stored) while the server calculates from the raw 10 in calc_inputs, so the stored activity and its emissions disagree 264×, Calculation Changes, Database Changes (+6 more)

### Community 176 - "BUG-091 — Dehydrator throughput entered under the label "MMscf/yr" is saved with unit "MMscf/day" (record activity unit 365× off)"
Cohesion: 0.14
Nodes (14): Acceptance Criteria, Affected Features, Affected Files, Backend Changes, Browser Verification, BUG-091 — Dehydrator throughput entered under the label "MMscf/yr" is saved with unit "MMscf/day" (record activity unit 365× off), Calculation Changes, Database Changes (+6 more)

### Community 177 - "BUG-096 — Scope 2 form: switching Source Type to Steam/Heat or CHP leaves the hidden unit at "kWh" — dropdown shows "Select..." but the request sends unit "kWh" (1000 "MMBtu" of steam booked as 3.41 MMBtu)"
Cohesion: 0.14
Nodes (14): Acceptance Criteria, Affected Features, Affected Files, Backend Changes, Browser Verification, BUG-096 — Scope 2 form: switching Source Type to Steam/Heat or CHP leaves the hidden unit at "kWh" — dropdown shows "Select..." but the request sends unit "kWh" (1000 "MMBtu" of steam booked as 3.41 MMBtu), Calculation Changes, Database Changes (+6 more)

### Community 178 - "BUG-097 — CHP allocation form labels Power Output "MWh" but the server uses the number as MMBtu: heat share (and Scope 2 tCO2e) overstated ~2.7× with WRI efficiency method"
Cohesion: 0.14
Nodes (14): Acceptance Criteria, Affected Features, Affected Files, Backend Changes, Browser Verification, BUG-097 — CHP allocation form labels Power Output "MWh" but the server uses the number as MMBtu: heat share (and Scope 2 tCO2e) overstated ~2.7× with WRI efficiency method, Calculation Changes, Database Changes (+6 more)

### Community 179 - "BUG-007 — Manual Scope 1 entry has no plausibility bound or QA flag: 9 test records (1e13 MMBtu gas, 1e15 t coal) make up about 99.99% of the snapshot's Scope 1 total (3.72e12 t Verified, 4.69e12 t Pending)"
Cohesion: 0.14
Nodes (14): Acceptance Criteria, Affected Features, Affected Files, Backend Changes, Browser Verification, BUG-007 — Manual Scope 1 entry has no plausibility bound or QA flag: 9 test records (1e13 MMBtu gas, 1e15 t coal) make up about 99.99% of the snapshot's Scope 1 total (3.72e12 t Verified, 4.69e12 t Pending), Calculation Changes, Database Changes (+6 more)

### Community 180 - "BUG-029 — Manage Data page crashes for every user when any facility has a NULL name; POST /api/facilities accepts facilities with no name"
Cohesion: 0.14
Nodes (14): Acceptance Criteria, Affected Features, Affected Files, Backend Changes, Browser Verification, BUG-029 — Manage Data page crashes for every user when any facility has a NULL name; POST /api/facilities accepts facilities with no name, Calculation Changes, Database Changes (+6 more)

### Community 181 - "BUG-073 — Scope 2 and Scope 3 create accept a missing or non-numeric year: one year-less Scope 2 record makes the main dashboard (summary/batch-all) return 500, and year-less Scope 3 is in the total but missing from by-year"
Cohesion: 0.14
Nodes (14): Acceptance Criteria, Affected Features, Affected Files, Backend Changes, Browser Verification, BUG-073 — Scope 2 and Scope 3 create accept a missing or non-numeric year: one year-less Scope 2 record makes the main dashboard (summary/batch-all) return 500, and year-less Scope 3 is in the total but missing from by-year, Calculation Changes, Database Changes (+6 more)

### Community 182 - "BUG-015 — 43 Tier 1 factors offered in the Scope 1 UI do not exist in the server catalog; records save with HTTP 201 and 0 emissions"
Cohesion: 0.14
Nodes (14): Acceptance Criteria, Affected Features, Affected Files, Backend Changes, Browser Verification, BUG-015 — 43 Tier 1 factors offered in the Scope 1 UI do not exist in the server catalog; records save with HTTP 201 and 0 emissions, Calculation Changes, Database Changes (+6 more)

### Community 183 - "BUG-085 — Scope 2/3 bulk import silently books rows with a blank or non-ISO date to January 2024, and stores a blank Scope 3 category as "Category ""
Cohesion: 0.14
Nodes (14): Acceptance Criteria, Affected Features, Affected Files, Backend Changes, Browser Verification, BUG-085 — Scope 2/3 bulk import silently books rows with a blank or non-ISO date to January 2024, and stores a blank Scope 3 category as "Category ", Calculation Changes, Database Changes (+6 more)

### Community 184 - "BUG-111 — Scope 1 bulk import books a row with a blank Unit as m³ and accepts year 1800, both of which the manual form/API reject"
Cohesion: 0.14
Nodes (14): Acceptance Criteria, Affected Features, Affected Files, Backend Changes, Browser Verification, BUG-111 — Scope 1 bulk import books a row with a blank Unit as m³ and accepts year 1800, both of which the manual form/API reject, Calculation Changes, Database Changes (+6 more)

### Community 185 - "BUG-112 — Custom emission factor with every factor field blank is saved (CO2/CH4/N2O = 0) and Tier 2 records that use it are stored with 0 tCO2e and no warning"
Cohesion: 0.14
Nodes (14): Acceptance Criteria, Affected Features, Affected Files, Backend Changes, Browser Verification, BUG-112 — Custom emission factor with every factor field blank is saved (CO2/CH4/N2O = 0) and Tier 2 records that use it are stored with 0 tCO2e and no warning, Calculation Changes, Database Changes (+6 more)

### Community 186 - "BUG-034 — SBTi target POST accepts NaN / Infinity (range checks pass for non-finite floats); trajectory endpoint then returns 500 or invalid JSON for all users"
Cohesion: 0.14
Nodes (14): Acceptance Criteria, Affected Features, Affected Files, Backend Changes, Browser Verification, BUG-034 — SBTi target POST accepts NaN / Infinity (range checks pass for non-finite floats); trajectory endpoint then returns 500 or invalid JSON for all users, Calculation Changes, Database Changes (+6 more)

### Community 187 - "BUG-039 — Emission goals API ("+ Set Target") has no value validation: negative, year 1, and NaN goals are accepted; a NaN goal for the current year makes the main dashboard batch return 500"
Cohesion: 0.14
Nodes (14): Acceptance Criteria, Affected Features, Affected Files, Backend Changes, Browser Verification, BUG-039 — Emission goals API ("+ Set Target") has no value validation: negative, year 1, and NaN goals are accepted; a NaN goal for the current year makes the main dashboard batch return 500, Calculation Changes, Database Changes (+6 more)

### Community 188 - "BUG-045 — "Add Region" (create facility) form fails with HTTP 500 unless the optional Latitude/Longitude fields are filled"
Cohesion: 0.14
Nodes (14): Acceptance Criteria, Affected Features, Affected Files, Backend Changes, Browser Verification, BUG-045 — "Add Region" (create facility) form fails with HTTP 500 unless the optional Latitude/Longitude fields are filled, Calculation Changes, Database Changes (+6 more)

### Community 189 - "BUG-060 — Scope 2 manual entries and Scope 2 bulk imports by a superuser are auto-Verified, while Scope 1 and Scope 3 require admin approval (inconsistent maker-checker)"
Cohesion: 0.14
Nodes (14): Acceptance Criteria, Affected Features, Affected Files, Backend Changes, Browser Verification, BUG-060 — Scope 2 manual entries and Scope 2 bulk imports by a superuser are auto-Verified, while Scope 1 and Scope 3 require admin approval (inconsistent maker-checker), Calculation Changes, Database Changes (+6 more)

### Community 190 - "BUG-070 — POST /api/emissions/reject/<id> has no status check: a superuser can flip an admin-Verified record to Rejected (removing it from all totals) and overwrite its approver"
Cohesion: 0.14
Nodes (14): Acceptance Criteria, Affected Features, Affected Files, Backend Changes, Browser Verification, BUG-070 — POST /api/emissions/reject/<id> has no status check: a superuser can flip an admin-Verified record to Rejected (removing it from all totals) and overwrite its approver, Calculation Changes, Database Changes (+6 more)

### Community 191 - "BUG-074 — Approve/reject endpoints are not concurrency-safe: two simultaneous approvals of the same record both return 200 (duplicate audit entries; approve+reject race ends in an arbitrary final state)"
Cohesion: 0.14
Nodes (14): Acceptance Criteria, Affected Features, Affected Files, Backend Changes, Browser Verification, BUG-074 — Approve/reject endpoints are not concurrency-safe: two simultaneous approvals of the same record both return 200 (duplicate audit entries; approve+reject race ends in an arbitrary final state), Calculation Changes, Database Changes (+6 more)

### Community 192 - "BUG-093 — Region-restricted superuser can re-region its own facility (PUT /api/facilities/<id>), pushing the facility and all its emissions into another region's scope and out of its own"
Cohesion: 0.14
Nodes (14): Acceptance Criteria, Affected Features, Affected Files, Backend Changes, Browser Verification, BUG-093 — Region-restricted superuser can re-region its own facility (PUT /api/facilities/<id>), pushing the facility and all its emissions into another region's scope and out of its own, Calculation Changes, Database Changes (+6 more)

### Community 193 - "BUG-077 — Dashboard "Export Executive Brief (PDF)" in the default All-Years view reports every year and every Pending record as "FISCAL YEAR 2026" / "Total verified records": PDF total 8.41 T tCO2e vs 3.72 T on the dashboard"
Cohesion: 0.14
Nodes (14): Acceptance Criteria, Affected Features, Affected Files, Backend Changes, Browser Verification, BUG-077 — Dashboard "Export Executive Brief (PDF)" in the default All-Years view reports every year and every Pending record as "FISCAL YEAR 2026" / "Total verified records": PDF total 8.41 T tCO2e vs 3.72 T on the dashboard, Calculation Changes, Database Changes (+6 more)

### Community 194 - "BUG-032 — GET /api/manage/sbti ignores facility/region scoping: region-restricted users can read organisation-wide Verified emission totals for any year"
Cohesion: 0.14
Nodes (14): Acceptance Criteria, Affected Features, Affected Files, Backend Changes, Browser Verification, BUG-032 — GET /api/manage/sbti ignores facility/region scoping: region-restricted users can read organisation-wide Verified emission totals for any year, Calculation Changes, Database Changes (+6 more)

### Community 195 - "BUG-038 — Audit trail (/api/audit/, /api/audit/export) is not facility/region-scoped: a region-restricted superuser reads activity entries for every region's records"
Cohesion: 0.14
Nodes (14): Acceptance Criteria, Affected Features, Affected Files, Backend Changes, Browser Verification, BUG-038 — Audit trail (/api/audit/, /api/audit/export) is not facility/region-scoped: a region-restricted superuser reads activity entries for every region's records, Calculation Changes, Database Changes (+6 more)

### Community 196 - "BUG-046 — Equity-share allocation ignores effective dates (time-sliced ownership never applied) and POST /api/equity/shares accepts any percentage (500, -50, inf) from any business role"
Cohesion: 0.14
Nodes (14): Acceptance Criteria, Affected Features, Affected Files, Backend Changes, Browser Verification, BUG-046 — Equity-share allocation ignores effective dates (time-sliced ownership never applied) and POST /api/equity/shares accepts any percentage (500, -50, inf) from any business role, Calculation Changes, Database Changes (+6 more)

### Community 197 - "BUG-076 — Bulk-upload job status and error CSV have no owner check: any logged-in account (incl. it_admin) can read another user's job rows; absolute server temp path is disclosed"
Cohesion: 0.14
Nodes (14): Acceptance Criteria, Affected Features, Affected Files, Backend Changes, Browser Verification, BUG-076 — Bulk-upload job status and error CSV have no owner check: any logged-in account (incl. it_admin) can read another user's job rows; absolute server temp path is disclosed, Calculation Changes, Database Changes (+6 more)

### Community 198 - "BUG-106 — User Management actions are missing from the Audit Trail: account creation and logout logs are never committed, and user deletion is not logged at all"
Cohesion: 0.14
Nodes (14): Acceptance Criteria, Affected Features, Affected Files, Backend Changes, Browser Verification, BUG-106 — User Management actions are missing from the Audit Trail: account creation and logout logs are never committed, and user deletion is not logged at all, Calculation Changes, Database Changes (+6 more)

### Community 199 - "BUG-087 — Malformed input on create endpoints returns HTTP 500/409 with raw exception and SQL text (≈40 handlers return `str(e)`)"
Cohesion: 0.14
Nodes (14): Acceptance Criteria, Affected Features, Affected Files, Backend Changes, Browser Verification, BUG-087 — Malformed input on create endpoints returns HTTP 500/409 with raw exception and SQL text (≈40 handlers return `str(e)`), Calculation Changes, Database Changes (+6 more)

### Community 200 - "BUG-057 — Bulk upload with "Overwrite Duplicates" enabled inserts every in-file duplicate row as a separate record (double counting)"
Cohesion: 0.14
Nodes (14): Acceptance Criteria, Affected Features, Affected Files, Backend Changes, Browser Verification, BUG-057 — Bulk upload with "Overwrite Duplicates" enabled inserts every in-file duplicate row as a separate record (double counting), Calculation Changes, Database Changes (+6 more)

### Community 201 - "BUG-081 — Scope 2/3 bulk import duplicate key is too coarse: separate meters and sub-categories in the same facility-month are rejected as "duplicates", or with Overwrite they replace a different existing record"
Cohesion: 0.14
Nodes (14): Acceptance Criteria, Affected Features, Affected Files, Backend Changes, Browser Verification, BUG-081 — Scope 2/3 bulk import duplicate key is too coarse: separate meters and sub-categories in the same facility-month are rejected as "duplicates", or with Overwrite they replace a different existing record, Calculation Changes, Database Changes (+6 more)

### Community 202 - "BUG-089 — Scope 3 category is stored as "6" by the UI/API and as "Category 6" by bulk import: cross-channel duplicates are not detected (double counting) and category breakdowns split"
Cohesion: 0.14
Nodes (14): Acceptance Criteria, Affected Features, Affected Files, Backend Changes, Browser Verification, BUG-089 — Scope 3 category is stored as "6" by the UI/API and as "Category 6" by bulk import: cross-channel duplicates are not detected (double counting) and category breakdowns split, Calculation Changes, Database Changes (+6 more)

### Community 203 - "BUG-058 — Bulk-upload overwrite rewrites approved records without an audit trail and leaves them "Pending" but still marked approved"
Cohesion: 0.14
Nodes (14): Acceptance Criteria, Affected Features, Affected Files, Backend Changes, Browser Verification, BUG-058 — Bulk-upload overwrite rewrites approved records without an audit trail and leaves them "Pending" but still marked approved, Calculation Changes, Database Changes (+6 more)

### Community 204 - "BUG-020 — /api/reports/master-annual-report serves full annual GHG report PDFs to any logged-in role (incl. it_admin and out-of-region users) and returns a static, pre-generated file regardless of facility_id"
Cohesion: 0.14
Nodes (14): Acceptance Criteria, Affected Features, Affected Files, Backend Changes, Browser Verification, BUG-020 — /api/reports/master-annual-report serves full annual GHG report PDFs to any logged-in role (incl. it_admin and out-of-region users) and returns a static, pre-generated file regardless of facility_id, Calculation Changes, Database Changes (+6 more)

### Community 205 - "BUG-065 — Custom factor names are not unique, yet bulk import resolves factors by name: the most recently created same-named factor is silently applied"
Cohesion: 0.14
Nodes (14): Acceptance Criteria, Affected Features, Affected Files, Backend Changes, Browser Verification, BUG-065 — Custom factor names are not unique, yet bulk import resolves factors by name: the most recently created same-named factor is silently applied, Calculation Changes, Database Changes (+6 more)

### Community 206 - "BUG-056 — Custom factors used by Tier 2 records can be deleted: the reference check matches `fuel_type == factor name`, but UI records store the factor id, which SQLite then reuses for the next factor"
Cohesion: 0.14
Nodes (14): Acceptance Criteria, Affected Features, Affected Files, Backend Changes, Browser Verification, BUG-056 — Custom factors used by Tier 2 records can be deleted: the reference check matches `fuel_type == factor name`, but UI records store the factor id, which SQLite then reuses for the next factor, Calculation Changes, Database Changes (+6 more)

### Community 207 - "BUG-009 — Deleting a facility that has any OGMP level-upgrade log fails with 500 (FK violation) and leaks raw SQL"
Cohesion: 0.14
Nodes (14): Acceptance Criteria, Affected Features, Affected Files, Backend Changes, Browser Verification, BUG-009 — Deleting a facility that has any OGMP level-upgrade log fails with 500 (FK violation) and leaks raw SQL, Calculation Changes, Database Changes (+6 more)

### Community 208 - "BUG-010 — Deleting a user who created production data, SBTi targets or OGMP level logs fails with 500 (FK cleanup list incomplete)"
Cohesion: 0.14
Nodes (14): Acceptance Criteria, Affected Features, Affected Files, Backend Changes, Browser Verification, BUG-010 — Deleting a user who created production data, SBTi targets or OGMP level logs fails with 500 (FK cleanup list incomplete), Calculation Changes, Database Changes (+6 more)

### Community 209 - "BUG-069 — Deleting a user wipes approved_by/created_by on every record they approved or entered: Verified records lose their maker-checker evidence"
Cohesion: 0.14
Nodes (14): Acceptance Criteria, Affected Features, Affected Files, Backend Changes, Browser Verification, BUG-069 — Deleting a user wipes approved_by/created_by on every record they approved or entered: Verified records lose their maker-checker evidence, Calculation Changes, Database Changes (+6 more)

### Community 210 - "BUG-044 — /granular-intensities (Master Report "Multi-Metric Intensities") divides all-facility emissions by only the facilities with granular MMboe fields, and fabricates NGSI methane (0.05 %) and saleable production (85 %)"
Cohesion: 0.14
Nodes (14): Acceptance Criteria, Affected Features, Affected Files, Backend Changes, Browser Verification, BUG-044 — /granular-intensities (Master Report "Multi-Metric Intensities") divides all-facility emissions by only the facilities with granular MMboe fields, and fabricates NGSI methane (0.05 %) and saleable production (85 %), Calculation Changes, Database Changes (+6 more)

### Community 211 - "BUG-084 — QA/QC Dashboard shows "Zero Anomalies Detected… The inventory is fully verified and audit-compliant" with 149 Pending records and 11 records more than 10^6 × the median; the anomaly queue only lists a stored `qa_flag`, which is never computed for existing data"
Cohesion: 0.14
Nodes (14): Acceptance Criteria, Affected Features, Affected Files, Backend Changes, Browser Verification, BUG-084 — QA/QC Dashboard shows "Zero Anomalies Detected… The inventory is fully verified and audit-compliant" with 149 Pending records and 11 records more than 10^6 × the median; the anomaly queue only lists a stored `qa_flag`, which is never computed for existing data, Calculation Changes, Database Changes (+6 more)

### Community 212 - "BUG-002 — Reports "2025 Master Report (PDF)" button sends facility_id=[object Object]; facility selection ignored"
Cohesion: 0.14
Nodes (14): Acceptance Criteria, Affected Features, Affected Files, Backend Changes, Browser Verification, BUG-002 — Reports "2025 Master Report (PDF)" button sends facility_id=[object Object]; facility selection ignored, Calculation Changes, Database Changes (+6 more)

### Community 213 - "BUG-006 — Reports Excel/PDF exports drop the Division, Field, Method and Search filters shown on screen"
Cohesion: 0.14
Nodes (14): Acceptance Criteria, Affected Features, Affected Files, Backend Changes, Browser Verification, BUG-006 — Reports Excel/PDF exports drop the Division, Field, Method and Search filters shown on screen, Calculation Changes, Database Changes (+6 more)

### Community 214 - "BUG-053 — CAP (air-pollutant) emissions bypass maker-checker: POST /api/cap/emissions stores records as "Verified" by default (client-controlled status) for role user; negative mass/concentration accepted"
Cohesion: 0.14
Nodes (14): Acceptance Criteria, Affected Features, Affected Files, Backend Changes, Browser Verification, BUG-053 — CAP (air-pollutant) emissions bypass maker-checker: POST /api/cap/emissions stores records as "Verified" by default (client-controlled status) for role user; negative mass/concentration accepted, Calculation Changes, Database Changes (+6 more)

### Community 215 - "BUG-113 — Reports "PDF Report" prints every unit and gas name with a missing-glyph box: "tCO■e", "CO■", "CH■", "N■O""
Cohesion: 0.14
Nodes (14): Acceptance Criteria, Affected Features, Affected Files, Backend Changes, Browser Verification, BUG-113 — Reports "PDF Report" prints every unit and gas name with a missing-glyph box: "tCO■e", "CO■", "CH■", "N■O", Calculation Changes, Database Changes (+6 more)

### Community 216 - "BUG-031 — Facility OGMP 2.0 level counts Draft, Pending and Rejected emission records, so a rejected record can raise a facility's level"
Cohesion: 0.14
Nodes (14): Acceptance Criteria, Affected Features, Affected Files, Backend Changes, Browser Verification, BUG-031 — Facility OGMP 2.0 level counts Draft, Pending and Rejected emission records, so a rejected record can raise a facility's level, Calculation Changes, Database Changes (+6 more)

### Community 217 - "BUG-052 — OGMP survey reconciliation status defaults to "Reconciled" whatever the computed variance; a +354 % discrepancy is stored and shown as Reconciled, and a zero bottom-up case is shown as "+0.0 %""
Cohesion: 0.14
Nodes (14): Acceptance Criteria, Affected Features, Affected Files, Backend Changes, Browser Verification, BUG-052 — OGMP survey reconciliation status defaults to "Reconciled" whatever the computed variance; a +354 % discrepancy is stored and shown as Reconciled, and a zero bottom-up case is shown as "+0.0 %", Calculation Changes, Database Changes (+6 more)

### Community 218 - "BUG-075 — Sentinel-5P "Export to OGMP" stores a 1-hour CH4 mass as the survey's "estimated annual tCH4" (default operating_hours = 1): top-down understated 8,760× and reconciliation always flagged"
Cohesion: 0.14
Nodes (14): Acceptance Criteria, Affected Features, Affected Files, Backend Changes, Browser Verification, BUG-075 — Sentinel-5P "Export to OGMP" stores a 1-hour CH4 mass as the survey's "estimated annual tCH4" (default operating_hours = 1): top-down understated 8,760× and reconciliation always flagged, Calculation Changes, Database Changes (+6 more)

### Community 219 - "BUG-040 — Supply Chain filter is not applied to the emissions-by-source split: "Emissions by Source" donut and Detailed Breakdown rows show company-wide values (sources add up to 7× Scope 1)"
Cohesion: 0.14
Nodes (14): Acceptance Criteria, Affected Features, Affected Files, Backend Changes, Browser Verification, BUG-040 — Supply Chain filter is not applied to the emissions-by-source split: "Emissions by Source" donut and Detailed Breakdown rows show company-wide values (sources add up to 7× Scope 1), Calculation Changes, Database Changes (+6 more)

### Community 220 - "BUG-004 — Intensity activity/division filter uses record-level columns that are NULL/inconsistent, so numerator and denominator are filtered differently (Upstream intensity blank, E&P intensity 0.0)"
Cohesion: 0.14
Nodes (14): Acceptance Criteria, Affected Features, Affected Files, Backend Changes, Browser Verification, BUG-004 — Intensity activity/division filter uses record-level columns that are NULL/inconsistent, so numerator and denominator are filtered differently (Upstream intensity blank, E&P intensity 0.0), Calculation Changes, Database Changes (+6 more)

### Community 221 - "BUG-017 — Intensity with year="all" (default view) pairs each facility's emissions from every year with production from other years; KPI mixes periods"
Cohesion: 0.14
Nodes (14): Acceptance Criteria, Affected Features, Affected Files, Backend Changes, Browser Verification, BUG-017 — Intensity with year="all" (default view) pairs each facility's emissions from every year with production from other years; KPI mixes periods, Calculation Changes, Database Changes (+6 more)

### Community 222 - "BUG-026 — Flaring panel treats "All Years" as the current calendar year and ignores the Supply-Chain/Activity/Division/Preview-Pending filters, so it contradicts the dashboard it sits in"
Cohesion: 0.14
Nodes (14): Acceptance Criteria, Affected Features, Affected Files, Backend Changes, Browser Verification, BUG-026 — Flaring panel treats "All Years" as the current calendar year and ignores the Supply-Chain/Activity/Division/Preview-Pending filters, so it contradicts the dashboard it sits in, Calculation Changes, Database Changes (+6 more)

### Community 223 - "BUG-094 — "Net Emissions" KPI subtracts company-wide mitigation whatever the Activity/Division filter (Steel & Iron view: Net = −1,027,393 t) and counts "Planned" projects as achieved reductions"
Cohesion: 0.14
Nodes (14): Acceptance Criteria, Affected Features, Affected Files, Backend Changes, Browser Verification, BUG-094 — "Net Emissions" KPI subtracts company-wide mitigation whatever the Activity/Division filter (Steel & Iron view: Net = −1,027,393 t) and counts "Planned" projects as achieved reductions, Calculation Changes, Database Changes (+6 more)

### Community 224 - "BUG-033 — Decree 21-330 flaring intensity (/flaring-summary) misconverts units: MMscf 1000× too low, scf/kscf 35× too high, UI "m³" gas production 28× too high; compliance verdict flips"
Cohesion: 0.14
Nodes (14): Acceptance Criteria, Affected Features, Affected Files, Backend Changes, Browser Verification, BUG-033 — Decree 21-330 flaring intensity (/flaring-summary) misconverts units: MMscf 1000× too low, scf/kscf 35× too high, UI "m³" gas production 28× too high; compliance verdict flips, Calculation Changes, Database Changes (+6 more)

### Community 225 - "BUG-067 — Maker-checker bypass through edit and delete: a superuser can approve a record they just edited, silently re-date/re-assign Verified records, and a user can hard-delete their own Verified records"
Cohesion: 0.14
Nodes (14): Acceptance Criteria, Affected Features, Affected Files, Backend Changes, Browser Verification, BUG-067 — Maker-checker bypass through edit and delete: a superuser can approve a record they just edited, silently re-date/re-assign Verified records, and a user can hard-delete their own Verified records, Calculation Changes, Database Changes (+6 more)

### Community 226 - "BUG-036 — Flaring panel invents a 56 % / 40 % / 4 % Routine / Non-Routine / Safety split for generic "flaring" records and shows 0 tCO₂e for every stream (and a 2.5 t/kNm³ proxy when CO₂e is 0)"
Cohesion: 0.14
Nodes (14): Acceptance Criteria, Affected Features, Affected Files, Backend Changes, Browser Verification, BUG-036 — Flaring panel invents a 56 % / 40 % / 4 % Routine / Non-Routine / Safety split for generic "flaring" records and shows 0 tCO₂e for every stream (and a 2.5 t/kNm³ proxy when CO₂e is 0), Calculation Changes, Database Changes (+6 more)

### Community 227 - "BUG-054 — "Preview Pending Data" and the pending banner are inconsistent with the rest of the dashboard: the toggle changes only the KPIs (categorical/org breakdown and Scope 3 stay Verified-only), and the banner ignores the Supply Chain, Activity and Division filters and omits Scope 3"
Cohesion: 0.14
Nodes (14): Acceptance Criteria, Affected Features, Affected Files, Backend Changes, Browser Verification, BUG-054 — "Preview Pending Data" and the pending banner are inconsistent with the rest of the dashboard: the toggle changes only the KPIs (categorical/org breakdown and Scope 3 stay Verified-only), and the banner ignores the Supply Chain, Activity and Division filters and omits Scope 3, Calculation Changes, Database Changes (+6 more)

### Community 228 - "BUG-041 — Dashboard "% GOAL" badge in the default All-years view divides the cumulative multi-year Scope 1+2 total by the single current-year goal (and ignores region/facility filters)"
Cohesion: 0.14
Nodes (14): Acceptance Criteria, Affected Features, Affected Files, Backend Changes, Browser Verification, BUG-041 — Dashboard "% GOAL" badge in the default All-years view divides the cumulative multi-year Scope 1+2 total by the single current-year goal (and ignores region/facility filters), Calculation Changes, Database Changes (+6 more)

### Community 229 - "BUG-061 — Dashboard "Emissions by Source" mis-classifies process types: fuel-gas combustion (6.47 M t) shown as "Other", pneumatics/tanks/dehydrators/unloading/completions as "Other" instead of Venting, fugitives merged into "Venting", mobile combustion labelled "Stationary Combustion""
Cohesion: 0.14
Nodes (14): Acceptance Criteria, Affected Features, Affected Files, Backend Changes, Browser Verification, BUG-061 — Dashboard "Emissions by Source" mis-classifies process types: fuel-gas combustion (6.47 M t) shown as "Other", pneumatics/tanks/dehydrators/unloading/completions as "Other" instead of Venting, fugitives merged into "Venting", mobile combustion labelled "Stationary Combustion", Calculation Changes, Database Changes (+6 more)

### Community 230 - "BUG-071 — Dashboard cache is not invalidated after a manual Scope 1 create or a bulk upload: new records are missing from the dashboard for up to 5 minutes (per worker)"
Cohesion: 0.14
Nodes (14): Acceptance Criteria, Affected Features, Affected Files, Backend Changes, Browser Verification, BUG-071 — Dashboard cache is not invalidated after a manual Scope 1 create or a bulk upload: new records are missing from the dashboard for up to 5 minutes (per worker), Calculation Changes, Database Changes (+6 more)

### Community 231 - "BUG-079 — OGMP reconciliation in the default "All years" view compares the AVERAGE of annual top-down surveys with the SUM of multi-year bottom-up CH4, so perfectly reconciled facilities are flagged (−80 %)"
Cohesion: 0.14
Nodes (14): Acceptance Criteria, Affected Features, Affected Files, Backend Changes, Browser Verification, BUG-079 — OGMP reconciliation in the default "All years" view compares the AVERAGE of annual top-down surveys with the SUM of multi-year bottom-up CH4, so perfectly reconciled facilities are flagged (−80 %), Calculation Changes, Database Changes (+6 more)

### Community 232 - "BUG-064 — Categorical Emissions Overview groups facilities by name instead of id: six distinct facilities are merged into one "Updated Facility" card (3.19 T t)"
Cohesion: 0.14
Nodes (14): Acceptance Criteria, Affected Features, Affected Files, Backend Changes, Browser Verification, BUG-064 — Categorical Emissions Overview groups facilities by name instead of id: six distinct facilities are merged into one "Updated Facility" card (3.19 T t), Calculation Changes, Database Changes (+6 more)

### Community 233 - "BUG-072 — Pending-records banner ignores the GWP-20 toggle: it always shows GWP-100 tCO2e while every other dashboard figure switches to GWP-20"
Cohesion: 0.14
Nodes (14): Acceptance Criteria, Affected Features, Affected Files, Backend Changes, Browser Verification, BUG-072 — Pending-records banner ignores the GWP-20 toggle: it always shows GWP-100 tCO2e while every other dashboard figure switches to GWP-20, Calculation Changes, Database Changes (+6 more)

### Community 234 - "BUG-080 — Two contradictory OGMP facility-level algorithms: /intensity-stats reports Level 5 (Gold Standard) where the canonical service (/ogmp-metrics, OGMP export) reports Level 4 for the same facility and year"
Cohesion: 0.14
Nodes (14): Acceptance Criteria, Affected Features, Affected Files, Backend Changes, Browser Verification, BUG-080 — Two contradictory OGMP facility-level algorithms: /intensity-stats reports Level 5 (Gold Standard) where the canonical service (/ogmp-metrics, OGMP export) reports Level 4 for the same facility and year, Calculation Changes, Database Changes (+6 more)

### Community 235 - "BUG-086 — Methane loss-rate segment classification differs between the KPI cards, the trend chart and the server: "Downstream / Processing" counts as Midstream in the trend, and "Upstream / Extraction" is dropped from the Upstream KPI"
Cohesion: 0.14
Nodes (14): Acceptance Criteria, Affected Features, Affected Files, Backend Changes, Browser Verification, BUG-086 — Methane loss-rate segment classification differs between the KPI cards, the trend chart and the server: "Downstream / Processing" counts as Midstream in the trend, and "Upstream / Extraction" is dropped from the Upstream KPI, Calculation Changes, Database Changes (+6 more)

### Community 236 - "BUG-099 — Scope 2 electricity create trusts client-supplied `co2e` / `emission_factor`: 0 kWh can be booked as 12,345 tCO2e, negative Scope 2 (-500 t) is accepted, and any unknown grid region takes the client's factor"
Cohesion: 0.14
Nodes (14): Acceptance Criteria, Affected Features, Affected Files, Backend Changes, Browser Verification, BUG-099 — Scope 2 electricity create trusts client-supplied `co2e` / `emission_factor`: 0 kWh can be booked as 12,345 tCO2e, negative Scope 2 (-500 t) is accepted, and any unknown grid region takes the client's factor, Calculation Changes, Database Changes (+6 more)

### Community 237 - "BUG-088 — Facilities with CH4 emissions but no gas production get methane_loss_rate_pct = 0 and ogmp_target_status "Compliant""
Cohesion: 0.14
Nodes (14): Acceptance Criteria, Affected Features, Affected Files, Backend Changes, Browser Verification, BUG-088 — Facilities with CH4 emissions but no gas production get methane_loss_rate_pct = 0 and ogmp_target_status "Compliant", Calculation Changes, Database Changes (+6 more)

### Community 238 - "BUG-008 — Inventory uncertainty shrinks by √N when the same emissions are split into N records (shared EF uncertainty treated as independent)"
Cohesion: 0.14
Nodes (14): Acceptance Criteria, Affected Features, Affected Files, Backend Changes, Browser Verification, BUG-008 — Inventory uncertainty shrinks by √N when the same emissions are split into N records (shared EF uncertainty treated as independent), Calculation Changes, Database Changes (+6 more)

### Community 239 - "BUG-018 — Uncertainty dashboard applies max(u_CO2, u_CH4, u_N2O) to each record's total CO2e instead of CO2e-weighting the per-gas uncertainties"
Cohesion: 0.14
Nodes (14): Acceptance Criteria, Affected Features, Affected Files, Backend Changes, Browser Verification, BUG-018 — Uncertainty dashboard applies max(u_CO2, u_CH4, u_N2O) to each record's total CO2e instead of CO2e-weighting the per-gas uncertainties, Calculation Changes, Database Changes (+6 more)

### Community 240 - "BUG-025 — Meter (activity-data) and GC (composition) uncertainty inputs are accepted but silently ignored by every calculator"
Cohesion: 0.14
Nodes (14): Acceptance Criteria, Affected Features, Affected Files, Backend Changes, Browser Verification, BUG-025 — Meter (activity-data) and GC (composition) uncertainty inputs are accepted but silently ignored by every calculator, Calculation Changes, Database Changes (+6 more)

### Community 241 - "BUG-043 — Stored uncertainty has no range or unit validation: Scope 2/3 accept percent values, negatives, NaN and 1e6, and the Uncertainty dashboard shows ±3600 %"
Cohesion: 0.14
Nodes (14): Acceptance Criteria, Affected Features, Affected Files, Backend Changes, Browser Verification, BUG-043 — Stored uncertainty has no range or unit validation: Scope 2/3 accept percent values, negatives, NaN and 1e6, and the Uncertainty dashboard shows ±3600 %, Calculation Changes, Database Changes (+6 more)

### Community 242 - "BUG-055 — QA Dashboard "IPCC Tier 1 Uncertainty" reports 1σ as ±%, uses only the CO2 column, and includes Draft and Pending records, so it contradicts the Uncertainty page"
Cohesion: 0.14
Nodes (14): Acceptance Criteria, Affected Features, Affected Files, Backend Changes, Browser Verification, BUG-055 — QA Dashboard "IPCC Tier 1 Uncertainty" reports 1σ as ±%, uses only the CO2 column, and includes Draft and Pending records, so it contradicts the Uncertainty page, Calculation Changes, Database Changes (+6 more)

### Community 243 - "BUG-062 — Uncertainty display inconsistencies: EmissionResult shows the ±1σ (68 %) band as the "Confidence Interval", Scope 2/3 tables use k=1.96 while everything else uses k=2, and the Uncertainty page badge thresholds contradict its legend"
Cohesion: 0.14
Nodes (14): Acceptance Criteria, Affected Features, Affected Files, Backend Changes, Browser Verification, BUG-062 — Uncertainty display inconsistencies: EmissionResult shows the ±1σ (68 %) band as the "Confidence Interval", Scope 2/3 tables use k=1.96 while everything else uses k=2, and the Uncertainty page badge thresholds contradict its legend, Calculation Changes, Database Changes (+6 more)

### Community 244 - "BUG-014 — SBTi progress KPI uses the current, incomplete year (and any future year) as the "current" year, so the dashboard reports ~95-99% reduction and ON TRACK"
Cohesion: 0.14
Nodes (14): Acceptance Criteria, Affected Features, Affected Files, Backend Changes, Browser Verification, BUG-014 — SBTi progress KPI uses the current, incomplete year (and any future year) as the "current" year, so the dashboard reports ~95-99% reduction and ON TRACK, Calculation Changes, Database Changes (+6 more)

### Community 245 - "BUG-019 — SBTi "Scope 1+2 (Operational)" view compares Scope 1+2 actuals to the Scope 1+2+3 baseline and target line (inflated reduction %, false ON TRACK)"
Cohesion: 0.14
Nodes (14): Acceptance Criteria, Affected Features, Affected Files, Backend Changes, Browser Verification, BUG-019 — SBTi "Scope 1+2 (Operational)" view compares Scope 1+2 actuals to the Scope 1+2+3 baseline and target line (inflated reduction %, false ON TRACK), Calculation Changes, Database Changes (+6 more)

### Community 246 - "BUG-028 — SBTi dashboard shows "ON TRACK — Reduction: 100% vs Baseline" when there is no verified data at all in the target window"
Cohesion: 0.14
Nodes (14): Acceptance Criteria, Affected Features, Affected Files, Backend Changes, Browser Verification, BUG-028 — SBTi dashboard shows "ON TRACK — Reduction: 100% vs Baseline" when there is no verified data at all in the target window, Calculation Changes, Database Changes (+6 more)

### Community 247 - "BUG-083 — Activity-data write endpoints accept "NaN" / "1e999" (±Infinity): a Scope 3 record with activity_data=Infinity makes /dashboard/batch-all, /scope3/summary and /api/scope3 emit invalid JSON ("Infinity")"
Cohesion: 0.14
Nodes (14): Acceptance Criteria, Affected Features, Affected Files, Backend Changes, Browser Verification, BUG-083 — Activity-data write endpoints accept "NaN" / "1e999" (±Infinity): a Scope 3 record with activity_data=Infinity makes /dashboard/batch-all, /scope3/summary and /api/scope3 emit invalid JSON ("Infinity"), Calculation Changes, Database Changes (+6 more)

### Community 248 - "BUG-059 — SBTi target labelled "1.5°C" is not tied to its reduction rate (0.5 %/yr accepted and displayed as 1.5°C); arbitrary pathway strings and future base years accepted; main-dashboard banner hard-codes "SBTi 1.5°C Linear Target""
Cohesion: 0.14
Nodes (14): Acceptance Criteria, Affected Features, Affected Files, Backend Changes, Browser Verification, BUG-059 — SBTi target labelled "1.5°C" is not tied to its reduction rate (0.5 %/yr accepted and displayed as 1.5°C); arbitrary pathway strings and future base years accepted; main-dashboard banner hard-codes "SBTi 1.5°C Linear Target", Calculation Changes, Database Changes (+6 more)

### Community 249 - "BUG-092 — Maker-checker outcome is invisible to the maker: reject/approve send no notification, the Scope 1 list shows Rejected/Pending rows exactly like Verified ones, and the reject dialog claims the record is "permanently deleted" although it is kept as Rejected"
Cohesion: 0.14
Nodes (14): Acceptance Criteria, Affected Features, Affected Files, Backend Changes, Browser Verification, BUG-092 — Maker-checker outcome is invisible to the maker: reject/approve send no notification, the Scope 1 list shows Rejected/Pending rows exactly like Verified ones, and the reject dialog claims the record is "permanently deleted" although it is kept as Rejected, Calculation Changes, Database Changes (+6 more)

### Community 250 - "BUG-105 — Manage Data and Reference Data swallow API load errors and show them as empty data ("No production record found", empty factor catalog)"
Cohesion: 0.14
Nodes (14): Acceptance Criteria, Affected Features, Affected Files, Backend Changes, Browser Verification, BUG-105 — Manage Data and Reference Data swallow API load errors and show them as empty data ("No production record found", empty factor catalog), Calculation Changes, Database Changes (+6 more)

### Community 251 - "BUG-107 — CustomDropdown is not keyboard-operable and form inputs have no programmatic labels: Region, Process Type, Emission Factor and Unit cannot be set without a mouse"
Cohesion: 0.14
Nodes (14): Acceptance Criteria, Affected Features, Affected Files, Backend Changes, Browser Verification, BUG-107 — CustomDropdown is not keyboard-operable and form inputs have no programmatic labels: Region, Process Type, Emission Factor and Unit cannot be set without a mouse, Calculation Changes, Database Changes (+6 more)

### Community 252 - "BUG-021 — Reports search keeps the current page number: "Total Records: 42 | Showing: 0" and no pager to recover"
Cohesion: 0.14
Nodes (14): Acceptance Criteria, Affected Features, Affected Files, Backend Changes, Browser Verification, BUG-021 — Reports search keeps the current page number: "Total Records: 42 | Showing: 0" and no pager to recover, Calculation Changes, Database Changes (+6 more)

### Community 253 - "BUG-095 — Scope 1 "Recent Activity": Export CSV exports only the 10 rows of the current page, and the Year/Process filter options are built from that page only"
Cohesion: 0.14
Nodes (14): Acceptance Criteria, Affected Features, Affected Files, Backend Changes, Browser Verification, BUG-095 — Scope 1 "Recent Activity": Export CSV exports only the 10 rows of the current page, and the Year/Process filter options are built from that page only, Calculation Changes, Database Changes (+6 more)

### Community 254 - "BUG-115 — Manage Data forms discard the server's validation message and show a generic "Failed to …" toast (negative production, negative factor, facility 500, etc.)"
Cohesion: 0.14
Nodes (14): Acceptance Criteria, Affected Features, Affected Files, Backend Changes, Browser Verification, BUG-115 — Manage Data forms discard the server's validation message and show a generic "Failed to …" toast (negative production, negative factor, facility 500, etc.), Calculation Changes, Database Changes (+6 more)

### Community 255 - "BUG-022 — Reports "Group By" selector has no effect (getGroupedData is never called)"
Cohesion: 0.14
Nodes (14): Acceptance Criteria, Affected Features, Affected Files, Backend Changes, Browser Verification, BUG-022 — Reports "Group By" selector has no effect (getGroupedData is never called), Calculation Changes, Database Changes (+6 more)

### Community 256 - "BUG-082 — Scope 1 "Live Equation Inspector" states "GWP Standard: IPCC AR6 (CH₄:28, N₂O:265)" — hard-coded, AR5 values mislabelled as AR6, ignores the org GWP setting"
Cohesion: 0.14
Nodes (14): Acceptance Criteria, Affected Features, Affected Files, Backend Changes, Browser Verification, BUG-082 — Scope 1 "Live Equation Inspector" states "GWP Standard: IPCC AR6 (CH₄:28, N₂O:265)" — hard-coded, AR5 values mislabelled as AR6, ignores the org GWP setting, Calculation Changes, Database Changes (+6 more)

### Community 257 - "BUG-098 — Emission Calculation Result panel rounds gas masses to 3 decimals of a tonne: non-zero CH4/N2O shown as "0.00 tonnes""
Cohesion: 0.14
Nodes (14): Acceptance Criteria, Affected Features, Affected Files, Backend Changes, Browser Verification, BUG-098 — Emission Calculation Result panel rounds gas masses to 3 decimals of a tonne: non-zero CH4/N2O shown as "0.00 tonnes", Calculation Changes, Database Changes (+6 more)

### Community 258 - "BUG-114 — Logout does not invalidate the session: a session cookie captured before logout keeps full API access (client-side signed cookie, no server-side revocation)"
Cohesion: 0.14
Nodes (14): Acceptance Criteria, Affected Features, Affected Files, Backend Changes, Browser Verification, BUG-114 — Logout does not invalidate the session: a session cookie captured before logout keeps full API access (client-side signed cookie, no server-side revocation), Calculation Changes, Database Changes (+6 more)

### Community 259 - "BUG-108 — Scope 1 entry form does not reflow at phone width (390 px): Field input, Tier selector and factor picker are clipped off-screen"
Cohesion: 0.14
Nodes (14): Acceptance Criteria, Affected Features, Affected Files, Backend Changes, Browser Verification, BUG-108 — Scope 1 entry form does not reflow at phone width (390 px): Field input, Tier selector and factor picker are clipped off-screen, Calculation Changes, Database Changes (+6 more)

### Community 260 - "BUG-078 — Executive Brief / Master PDF prints hard-coded performance claims ("15.9 % reduction… on track for -30 %", "65.9 % methane reduction", "Lowest annual flaring on record (-38.0 %)", "VISR camera verified" DRE) regardless of the data"
Cohesion: 0.14
Nodes (14): Acceptance Criteria, Affected Features, Affected Files, Backend Changes, Browser Verification, BUG-078 — Executive Brief / Master PDF prints hard-coded performance claims ("15.9 % reduction… on track for -30 %", "65.9 % methane reduction", "Lowest annual flaring on record (-38.0 %)", "VISR camera verified" DRE) regardless of the data, Calculation Changes, Database Changes (+6 more)

### Community 261 - "BUG-066 — AGR form throughput units MMscfd / Mcf/day / m³/yr are ignored by the server (read as MMscf/yr): CO2 365× low, 2.7× high, or 28,317× high"
Cohesion: 0.14
Nodes (14): Acceptance Criteria, Affected Features, Affected Files, Backend Changes, Browser Verification, BUG-066 — AGR form throughput units MMscfd / Mcf/day / m³/yr are ignored by the server (read as MMscf/yr): CO2 365× low, 2.7× high, or 28,317× high, Calculation Changes, Database Changes (+6 more)

### Community 262 - "test_qfull_boundary_sensitivity.py"
Cohesion: 0.17
Nodes (8): MissingFactorError, Raised instead of silently booking 0 tCO2e when no emission factor could be…, test_qfull_boundary_sensitivity.py QFULL END-TO-END CALCULATION PIPELINE…, Verify CO2e responds correctly to GWP changes., CO2e = CO2*1 + CH4*GWP_CH4 + N2O*GWP_N2O If GWP_CH4 increases, totalCo2e…, AR4: CH4=25, AR5: CH4=28 → for CH4-dominant emissions: AR5 totalCo2e > AR4…, For a pure CO2 process, totalCo2e = CO2 × 1.0 regardless of GWP_CH4., TestCO2eSensitivity

### Community 263 - "test_bulk_uploaders.py"
Cohesion: 0.14
Nodes (36): _build_mapping(), _canonical_header(), Header -> field mapping for one import type. Headers are compared without the…, Field name carried by a header: template tags and unit notes are dropped…, csv_rows(), emissions(), parametrize, Bulk uploader checks (POST /api/emissions/upload/start, background_processor).… (+28 more)

### Community 264 - "make_facility"
Cohesion: 0.13
Nodes (26): make_facility(), ctx(), fixture, RC-15 reports / QA regressions (BUG-077, BUG-084, BUG-113)., Year facets and the Scope 1 export read the whole filtered set, not the 10-row…, test_bug077_emissions_list_filters_by_status(), test_bug084_stored_outliers_are_reported(), test_bug095_facets_and_export_cover_all_pages() (+18 more)

### Community 265 - "BUG-069 — Deleting a user wipes approved_by/created_by on every record they approved or entered: Verified records lose their maker-checker evidence"
Cohesion: 0.15
Nodes (13): Actual, Additional confirmation (BUG-047), Additional confirmation (BUG-061), Affected Components, BUG-069 — Deleting a user wipes approved_by/created_by on every record they approved or entered: Verified records lose their maker-checker evidence, Evidence, Expected, Impact (+5 more)

### Community 266 - "BUG-089 — Scope 3 category is stored as "6" by the UI/API and as "Category 6" by bulk import: cross-channel duplicates are not detected (double counting) and category breakdowns split"
Cohesion: 0.15
Nodes (13): Actual, Additional confirmation (BUG-075), Additional confirmation (BUG-075), Affected Components, BUG-089 — Scope 3 category is stored as "6" by the UI/API and as "Category 6" by bulk import: cross-channel duplicates are not detected (double counting) and category breakdowns split, Evidence, Expected, Impact (+5 more)

### Community 267 - "BUG-110 — Onshore fugitives "Tier 1: Facility-Level" form: the on-screen preview says 16,644 tCO2e but the saved record is 1.456 tCO2e — the server ignores the selected facility type and duration and books the facility count as a count of valves"
Cohesion: 0.15
Nodes (13): Actual, Additional confirmation (BUG-029), Additional confirmation (BUG-110), Affected Components, BUG-110 — Onshore fugitives "Tier 1: Facility-Level" form: the on-screen preview says 16,644 tCO2e but the saved record is 1.456 tCO2e — the server ignores the selected facility type and duration and books the facility count as a count of valves, Evidence, Expected, Impact (+5 more)

### Community 268 - "AUDIT MEMORY (living document)"
Cohesion: 0.15
Nodes (12): 0. Conventions and context to respect, 1. CRITICAL security findings, 2. HIGH security findings, 3. Additional security findings (second pass), 4. CALCULATION and LOGIC bugs, 5. Tests and tooling, 6. Decision log, 7. Work log (+4 more)

### Community 269 - "_agentA_common.py"
Cohesion: 0.37
Nodes (3): check(), post_scope1(), Shared helper for Agent A repro scripts (audit harness only; no app source…

### Community 270 - "build_plan.py"
Cohesion: 0.23
Nodes (11): classify(), files_in(), Builds IMPLEMENTATION_PLAN.md from AUDIT_FINDINGS.md + lead-auditor phase/root-…, rc_of(), sec(), section(), squash(), status_line() (+3 more)

### Community 271 - "Frontend Enhancements"
Cohesion: 0.15
Nodes (12): Automated/Browser Testing, Backend Enhancements, Frontend Enhancements, Implementation Plan - Enhance User Profile & Dashboard Integration, Manual Verification, [MODIFY] [dashboard.html](file:///c:/Users/samsung/Desktop/ghg%20old/public/dashboard.html), [MODIFY] [dashboard.js](file:///c:/Users/samsung/Desktop/ghg%20old/public/dashboard.js), [MODIFY] [profile.html](file:///c:/Users/samsung/Desktop/ghg%20old/public/profile.html) (+4 more)

### Community 272 - "Global Responsive Design Optimization"
Cohesion: 0.15
Nodes (12): Dashboard Components, Global Responsive Design Optimization, Layout & TopBar, Manual Verification, [MODIFY] `c:\Users\samsung\Desktop\h\new\client\src\components\layout\Layout.css`, [MODIFY] `c:\Users\samsung\Desktop\h\new\client\src\components\layout\Sidebar.css`, [MODIFY] `c:\Users\samsung\Desktop\h\new\client\src\components\layout\TopBar.css`, [MODIFY] `c:\Users\samsung\Desktop\h\new\client\src\pages\Dashboard.css` (+4 more)

### Community 273 - "GHG Tracker - Major Feature Expansion"
Cohesion: 0.15
Nodes (12): GHG Tracker - Major Feature Expansion, Phase 10: Premium Nature Redesign, Phase 11: Glass Nature Overhaul, Phase 12: Calculator Logic Fix, Phase 13: Custom Factors & Reference Data Enhancement, Phase 1: Planning & Setup, Phase 2: Scope 2 (Electricity) Calculator, Phase 3: Custom Emission Factors (Settings) (+4 more)

### Community 274 - "CAD Enhancement: Sun Path Animation - Complete"
Cohesion: 0.15
Nodes (12): 1. **Time-of-Day Slider** 🌅, 2. **Seasonal Selector** 📅, 3. **Accurate Sun Position Calculator** ☀️, 4. **Position Comparison** ⚠️, CAD Enhancement: Sun Path Animation - Complete, Example Workflow, ✅ Feature Implemented, Future Enhancements (Optional) (+4 more)

### Community 275 - "scripts"
Cohesion: 0.15
Nodes (12): name, private, scripts, build, dev, e2e, lint, preview (+4 more)

### Community 276 - "a11yAndErrors.test.jsx"
Cohesion: 0.26
Nodes (6): ReferenceData, ReferenceData(), OPTS, installLabelLinker(), linkFormLabels(), apiError()

### Community 277 - "BUG-062 — Uncertainty display inconsistencies: EmissionResult shows the ±1σ (68 %) band as the "Confidence Interval", Scope 2/3 tables use k=1.96 while everything else uses k=2, and the Uncertainty page badge thresholds contradict its legend"
Cohesion: 0.20
Nodes (10): Actual, Affected Components, BUG-062 — Uncertainty display inconsistencies: EmissionResult shows the ±1σ (68 %) band as the "Confidence Interval", Scope 2/3 tables use k=1.96 while everything else uses k=2, and the Uncertainty page badge thresholds contradict its legend, Evidence, Expected, Impact, Location, Recommended Fix (+2 more)

### Community 278 - "emissions.py"
Cohesion: 0.04
Nodes (91): dict, plausibility_check(), Return (verdict, message): verdict is "reject", "flag" or None., parse_month(), parse_year(), Reporting year: integer in [1900, current year + 1]., Notification, create_or_update_cap_emission() (+83 more)

### Community 279 - "compute_scope3_co2e"
Cohesion: 0.10
Nodes (13): compute_scope3_co2e(), Authoritatively calculates Scope 3 CO2e in metric tonnes from activity amount…, Verify compute_scope3_co2e distinguishes numerator units from denominator units., test_compute_scope3_co2e_units(), Diff Test: Scope 3 spend EEIO vs physical tonne factor., GHG Protocol Scope 3: Purchased materials (tonne) vs spend-based EEIO ($1000)., parametrize, CLEAN-SLATE VALIDATION: Scope 3 Value Chain Emissions Validates all 15 GHG… (+5 more)

### Community 280 - "extract_val"
Cohesion: 0.21
Nodes (6): extract_val(), Diesel Tier 1: quantity = 500 gal HHV = 138,700 Btu/gal → 500 × 138,700 /…, Liquids Unloading Tier 3 (API Eq. 6-3): well_depth = 5000 ft diameter = 2.441…, Extract the central value from a propagated uncertainty dict or bare float., TestTier1CombustionDiesel, TestTier3LiquidsUnloading

### Community 281 - "Feature Specification: [FEATURE NAME]"
Cohesion: 0.15
Nodes (12): Assumptions, Edge Cases, Feature Specification: [FEATURE NAME], Functional Requirements, Key Entities *(include if feature involves data)*, Measurable Outcomes, Requirements *(mandatory)*, Success Criteria *(mandatory)* (+4 more)

### Community 282 - "Feature Specification: [FEATURE NAME]"
Cohesion: 0.15
Nodes (12): Assumptions, Edge Cases, Feature Specification: [FEATURE NAME], Functional Requirements, Key Entities *(include if feature involves data)*, Measurable Outcomes, Requirements *(mandatory)*, Success Criteria *(mandatory)* (+4 more)

### Community 283 - "BUG-022 — Reports "Group By" selector has no effect (getGroupedData is never called)"
Cohesion: 0.17
Nodes (12): Actual, Additional confirmation (BUG-019), Affected Components, BUG-022 — Reports "Group By" selector has no effect (getGroupedData is never called), Evidence, Expected, Impact, Input (+4 more)

### Community 284 - "BUG-024 — Tier 3 flaring/combustion renormalises the gas composition without N2 (and without unspecified components), inflating CH4 and CO2 by 1/(1 − x_inert)"
Cohesion: 0.17
Nodes (12): Actual, Additional confirmation (BUG-015), Affected Components, BUG-024 — Tier 3 flaring/combustion renormalises the gas composition without N2 (and without unspecified components), inflating CH4 and CO2 by 1/(1 − x_inert), Evidence, Expected, Impact, Input (+4 more)

### Community 285 - "BUG-028 — SBTi dashboard shows "ON TRACK — Reduction: 100% vs Baseline" when there is no verified data at all in the target window"
Cohesion: 0.17
Nodes (12): Actual, Additional confirmation (BUG-015), Affected Components, BUG-028 — SBTi dashboard shows "ON TRACK — Reduction: 100% vs Baseline" when there is no verified data at all in the target window, Evidence, Expected, Impact, Input (+4 more)

### Community 286 - "BUG-037 — Editing a Scope 1 record replaces its propagated 1σ uncertainty with the raw catalog EF half-width (95 %, EF-only); user_uncertainty is stored unpropagated"
Cohesion: 0.17
Nodes (12): Actual, Additional confirmation (BUG-029), Affected Components, BUG-037 — Editing a Scope 1 record replaces its propagated 1σ uncertainty with the raw catalog EF half-width (95 %, EF-only); user_uncertainty is stored unpropagated, Evidence, Expected, Impact, Input (+4 more)

### Community 287 - "BUG-061 — Dashboard "Emissions by Source" mis-classifies process types: fuel-gas combustion (6.47 M t) shown as "Other", pneumatics/tanks/dehydrators/unloading/completions as "Other" instead of Venting, fugitives merged into "Venting", mobile combustion labelled "Stationary Combustion""
Cohesion: 0.17
Nodes (12): Actual, Additional confirmation (BUG-029), Affected Components, BUG-061 — Dashboard "Emissions by Source" mis-classifies process types: fuel-gas combustion (6.47 M t) shown as "Other", pneumatics/tanks/dehydrators/unloading/completions as "Other" instead of Venting, fugitives merged into "Venting", mobile combustion labelled "Stationary Combustion", Evidence, Expected, Impact, Input (+4 more)

### Community 288 - "BUG-071 — Dashboard cache is not invalidated after a manual Scope 1 create or a bulk upload: new records are missing from the dashboard for up to 5 minutes (per worker)"
Cohesion: 0.17
Nodes (12): Actual, Additional confirmation (BUG-029), Affected Components, BUG-071 — Dashboard cache is not invalidated after a manual Scope 1 create or a bulk upload: new records are missing from the dashboard for up to 5 minutes (per worker), Evidence, Expected, Impact, Input (+4 more)

### Community 289 - "BUG-078 — Executive Brief / Master PDF prints hard-coded performance claims ("15.9 % reduction… on track for -30 %", "65.9 % methane reduction", "Lowest annual flaring on record (-38.0 %)", "VISR camera verified" DRE) regardless of the data"
Cohesion: 0.17
Nodes (12): Actual, Additional confirmation (BUG-071), Affected Components, BUG-078 — Executive Brief / Master PDF prints hard-coded performance claims ("15.9 % reduction… on track for -30 %", "65.9 % methane reduction", "Lowest annual flaring on record (-38.0 %)", "VISR camera verified" DRE) regardless of the data, Evidence, Expected, Impact, Input (+4 more)

### Community 290 - "BUG-099 — Scope 2 electricity create trusts client-supplied `co2e` / `emission_factor`: 0 kWh can be booked as 12,345 tCO2e, negative Scope 2 (-500 t) is accepted, and any unknown grid region takes the client's factor"
Cohesion: 0.17
Nodes (12): Actual, Additional confirmation (BUG-099), Affected Components, BUG-099 — Scope 2 electricity create trusts client-supplied `co2e` / `emission_factor`: 0 kWh can be booked as 12,345 tCO2e, negative Scope 2 (-500 t) is accepted, and any unknown grid region takes the client's factor, Evidence, Expected, Impact, Input (+4 more)

### Community 291 - "BUG-106 — User Management actions are missing from the Audit Trail: account creation and logout logs are never committed, and user deletion is not logged at all"
Cohesion: 0.17
Nodes (12): Actual, Additional confirmation (BUG-044), Affected Components, BUG-106 — User Management actions are missing from the Audit Trail: account creation and logout logs are never committed, and user deletion is not logged at all, Evidence, Expected, Impact, Input (+4 more)

### Community 292 - "BUG-109 — Scope 1 form saves an entry with no Unit selected: the client silently assumes m³ (10 → 2,641.72 gal stored) while the server calculates from the raw 10 in calc_inputs, so the stored activity and its emissions disagree 264×"
Cohesion: 0.17
Nodes (12): Actual, Additional confirmation (BUG-109), Affected Components, BUG-109 — Scope 1 form saves an entry with no Unit selected: the client silently assumes m³ (10 → 2,641.72 gal stored) while the server calculates from the raw 10 in calc_inputs, so the stored activity and its emissions disagree 264×, Evidence, Expected, Impact, Input (+4 more)

### Community 293 - "BUG-111 — Scope 1 bulk import books a row with a blank Unit as m³ and accepts year 1800, both of which the manual form/API reject"
Cohesion: 0.17
Nodes (12): Actual, Additional confirmation (BUG-081), Affected Components, BUG-111 — Scope 1 bulk import books a row with a blank Unit as m³ and accepts year 1800, both of which the manual form/API reject, Evidence, Expected, Impact, Input (+4 more)

### Community 294 - "BUG-114 — Logout does not invalidate the session: a session cookie captured before logout keeps full API access (client-side signed cookie, no server-side revocation)"
Cohesion: 0.17
Nodes (12): Actual, Additional confirmation (BUG-114), Affected Components, BUG-114 — Logout does not invalidate the session: a session cookie captured before logout keeps full API access (client-side signed cookie, no server-side revocation), Evidence, Expected, Impact, Input (+4 more)

### Community 295 - "BUG-019 — SBTi "Scope 1+2 (Operational)" view compares Scope 1+2 actuals to the Scope 1+2+3 baseline and target line (inflated reduction %, false ON TRACK)"
Cohesion: 0.17
Nodes (12): Actual, Additional confirmation (BUG-007), Affected Components, BUG-019 — SBTi "Scope 1+2 (Operational)" view compares Scope 1+2 actuals to the Scope 1+2+3 baseline and target line (inflated reduction %, false ON TRACK), Evidence, Expected, Impact, Input (+4 more)

### Community 296 - "test_battery_concurrency_stress_invariants.py"
Cohesion: 0.11
Nodes (12): dispatcher(), fixture, Battery 6: Concurrency, Stress, Determinism & Invariant Test Suite.…, Verifies that engine execution never mutates caller input objects., Verifies smooth numerical scaling from micro-activities to gigascale portfolios., Verifies that CalculationDispatcher is completely re-entrant and thread-safe., Executes 160 simultaneous calculations across 16 worker threads covering…, Verifies that identical mathematical inputs yield bit-for-bit identical outputs. (+4 more)

### Community 297 - "BUG-XXX — Well-completion Tier 3 uses `amount` as both the flowback volume and the event count (volume squared), and ignores rate × duration when the method dropdown is left at its default"
Cohesion: 0.17
Nodes (11): Actual, Affected Components, BUG-XXX — Well-completion Tier 3 uses `amount` as both the flowback volume and the event count (volume squared), and ignores rate × duration when the method dropdown is left at its default, Evidence, Expected, Impact, Input, Location (+3 more)

### Community 298 - "BUG-XXX — Tier 3 flaring/combustion renormalises the gas composition without N2 (and without unspecified components), inflating CH4 and CO2 by 1/(1 − x_inert)"
Cohesion: 0.17
Nodes (11): Actual, Affected Components, BUG-XXX — Tier 3 flaring/combustion renormalises the gas composition without N2 (and without unspecified components), inflating CH4 and CO2 by 1/(1 − x_inert), Evidence, Expected, Impact, Input, Location (+3 more)

### Community 299 - "BUG-XXX — Tier 3 combustion/flaring gas composition: each component is converted percent→fraction on its own, so mol% values ≤ 1 (e.g. C4 = 1.0 %, C5 = 0.5 %) become 100 % / 50 %; CO2 inflated 2.7× on the app's own template sample"
Cohesion: 0.17
Nodes (11): Actual, Affected Components, BUG-XXX — Tier 3 combustion/flaring gas composition: each component is converted percent→fraction on its own, so mol% values ≤ 1 (e.g. C4 = 1.0 %, C5 = 0.5 %) become 100 % / 50 %; CO2 inflated 2.7× on the app's own template sample, Evidence, Expected, Impact, Input, Location (+3 more)

### Community 300 - "BUG-XXX — Well-completion "Rate × Duration" method divides the Mcf/hr rate by 24 (treats it as Mcf/day): CH4 understated 24×"
Cohesion: 0.17
Nodes (11): Actual, Affected Components, BUG-XXX — Well-completion "Rate × Duration" method divides the Mcf/hr rate by 24 (treats it as Mcf/day): CH4 understated 24×, Evidence, Expected, Impact, Input, Location (+3 more)

### Community 301 - "BUG-XXX — Tier 1 fugitive and equipment factors in "per hour" units are multiplied only by the source count (no operating hours): annual CH4 understated 8,760×, and Tier 1 disagrees with Tier 3 for the same factor"
Cohesion: 0.17
Nodes (11): Actual, Affected Components, BUG-XXX — Tier 1 fugitive and equipment factors in "per hour" units are multiplied only by the source count (no operating hours): annual CH4 understated 8,760×, and Tier 1 disagrees with Tier 3 for the same factor, Evidence, Expected, Impact, Input, Location (+3 more)

### Community 302 - "BUG-XXX — Dashboard cache is not invalidated after a manual Scope 1 create or a bulk upload: new records are missing from the dashboard for up to 5 minutes (per worker)"
Cohesion: 0.17
Nodes (11): Actual, Affected Components, BUG-XXX — Dashboard cache is not invalidated after a manual Scope 1 create or a bulk upload: new records are missing from the dashboard for up to 5 minutes (per worker), Evidence, Expected, Impact, Input, Location (+3 more)

### Community 303 - "BUG-XXX — Scope 2/3 bulk import silently books rows with a blank or non-ISO date to January 2024, and stores a blank Scope 3 category as "Category ""
Cohesion: 0.17
Nodes (11): Actual, Affected Components, BUG-XXX — Scope 2/3 bulk import silently books rows with a blank or non-ISO date to January 2024, and stores a blank Scope 3 category as "Category ", Evidence, Expected, Impact, Input, Location (+3 more)

### Community 304 - "BUG-XXX — Scope 2/3 bulk import duplicate key is too coarse: separate meters and sub-categories in the same facility-month are rejected as "duplicates", or with Overwrite they replace a different existing record"
Cohesion: 0.17
Nodes (11): Actual, Affected Components, BUG-XXX — Scope 2/3 bulk import duplicate key is too coarse: separate meters and sub-categories in the same facility-month are rejected as "duplicates", or with Overwrite they replace a different existing record, Evidence, Expected, Impact, Input, Location (+3 more)

### Community 305 - "BUG-XXX — Scope 2 and Scope 3 create accept a missing or non-numeric year: one year-less Scope 2 record makes the main dashboard (summary/batch-all) return 500, and year-less Scope 3 is in the total but missing from by-year"
Cohesion: 0.17
Nodes (11): Actual, Affected Components, BUG-XXX — Scope 2 and Scope 3 create accept a missing or non-numeric year: one year-less Scope 2 record makes the main dashboard (summary/batch-all) return 500, and year-less Scope 3 is in the total but missing from by-year, Evidence, Expected, Impact, Input, Location (+3 more)

### Community 306 - "BUG-XXX — POST /api/emissions/ calculates from `quantity`/`fuel_type` but stores only `amount`/`fuel`: records keep emissions with NULL activity quantity and fuel"
Cohesion: 0.17
Nodes (11): Actual, Affected Components, BUG-XXX — POST /api/emissions/ calculates from `quantity`/`fuel_type` but stores only `amount`/`fuel`: records keep emissions with NULL activity quantity and fuel, Evidence, Expected, Impact, Input, Location (+3 more)

### Community 307 - "BUG-XXX — Editing a Scope 1 record's quantity via PUT /api/emissions/<id> does not recalculate emissions (stale `amount` from source_payload wins)"
Cohesion: 0.17
Nodes (11): Actual, Affected Components, BUG-XXX — Editing a Scope 1 record's quantity via PUT /api/emissions/<id> does not recalculate emissions (stale `amount` from source_payload wins), Evidence, Expected, Impact, Input, Location (+3 more)

### Community 308 - "BUG-XXX — Scope 3 category is stored as "6" by the UI/API and as "Category 6" by bulk import: cross-channel duplicates are not detected (double counting) and category breakdowns split"
Cohesion: 0.17
Nodes (11): Actual, Affected Components, BUG-XXX — Scope 3 category is stored as "6" by the UI/API and as "Category 6" by bulk import: cross-channel duplicates are not detected (double counting) and category breakdowns split, Evidence, Expected, Impact, Input, Location (+3 more)

### Community 309 - "BUG-XXX — Purchased steam/heat (`indirect_steam`) and CHP allocation (`cogen_allocation`) are accepted as Scope 1 process types and added to Scope 1 totals (Scope 2 counted as Scope 1; CHP double counting)"
Cohesion: 0.17
Nodes (11): Actual, Affected Components, BUG-XXX — Purchased steam/heat (`indirect_steam`) and CHP allocation (`cogen_allocation`) are accepted as Scope 1 process types and added to Scope 1 totals (Scope 2 counted as Scope 1; CHP double counting), Evidence, Expected, Impact, Input, Location (+3 more)

### Community 310 - "BUG-XXX — Manual Scope 1 entry has no plausibility bound or QA flag: 9 test records (1e13 MMBtu gas, 1e15 t coal) make up about 99.99% of the snapshot's Scope 1 total (3.72e12 t Verified, 4.69e12 t Pending)"
Cohesion: 0.17
Nodes (11): Actual, Affected Components, BUG-XXX — Manual Scope 1 entry has no plausibility bound or QA flag: 9 test records (1e13 MMBtu gas, 1e15 t coal) make up about 99.99% of the snapshot's Scope 1 total (3.72e12 t Verified, 4.69e12 t Pending), Evidence, Expected, Impact, Input, Location (+3 more)

### Community 311 - "BUG-XXX — 43 Tier 1 factors offered in the Scope 1 UI do not exist in the server catalog; records save with HTTP 201 and 0 emissions"
Cohesion: 0.17
Nodes (11): Actual, Affected Components, BUG-XXX — 43 Tier 1 factors offered in the Scope 1 UI do not exist in the server catalog; records save with HTTP 201 and 0 emissions, Evidence, Expected, Impact, Input, Location (+3 more)

### Community 312 - "BUG-XXX — Tier 1 combustion applies the catalog HHV in the wrong basis when the activity unit is mass or the other phase (diesel/crude per tonne ×3.6, natural gas per tonne ÷40, ethane per scf ×39)"
Cohesion: 0.17
Nodes (11): Actual, Affected Components, BUG-XXX — Tier 1 combustion applies the catalog HHV in the wrong basis when the activity unit is mass or the other phase (diesel/crude per tonne ×3.6, natural gas per tonne ÷40, ethane per scf ×39), Evidence, Expected (t CO2, independent), Impact, Input, Location (+3 more)

### Community 313 - "BUG-XXX — Recalculating a Tier 2 (custom-factor) Scope 1 record drops the custom factor: emissions become 0 or silently switch to the catalog factor, while factor_source stays "custom""
Cohesion: 0.17
Nodes (11): Actual, Affected Components, BUG-XXX — Recalculating a Tier 2 (custom-factor) Scope 1 record drops the custom factor: emissions become 0 or silently switch to the catalog factor, while factor_source stays "custom", Evidence, Expected, Impact, Input, Location (+3 more)

### Community 314 - "BUG-XXX — Custom factors used by Tier 2 records can be deleted: the reference check matches `fuel_type == factor name`, but UI records store the factor id, which SQLite then reuses for the next factor"
Cohesion: 0.17
Nodes (11): Actual, Affected Components, BUG-XXX — Custom factors used by Tier 2 records can be deleted: the reference check matches `fuel_type == factor name`, but UI records store the factor id, which SQLite then reuses for the next factor, Evidence, Expected, Impact, Input, Location (+3 more)

### Community 315 - "BUG-XXX — AR5 20-year GWPs are wrong (CH4 82.5 instead of 84, N2O 268 instead of 264); AR6 pairs the fossil CH4 GWP-20 with the non-fossil-weighted GWP-100"
Cohesion: 0.17
Nodes (11): Actual, Affected Components, BUG-XXX — AR5 20-year GWPs are wrong (CH4 82.5 instead of 84, N2O 268 instead of 264); AR6 pairs the fossil CH4 GWP-20 with the non-fossil-weighted GWP-100, Evidence, Expected, Impact, Input, Location (+3 more)

### Community 316 - "BUG-XXX — GWP-20 conversion in intensity-stats / intensity-trend hard-codes AR5 GWP-100 (28 / 265), so GWP-20 CO2e is wrong whenever the active standard is AR4 or AR6"
Cohesion: 0.17
Nodes (11): Actual, Affected Components, BUG-XXX — GWP-20 conversion in intensity-stats / intensity-trend hard-codes AR5 GWP-100 (28 / 265), so GWP-20 CO2e is wrong whenever the active standard is AR4 or AR6, Evidence, Expected, Impact, Input, Location (+3 more)

### Community 317 - "BUG-XXX — Two contradictory OGMP facility-level algorithms: /intensity-stats reports Level 5 (Gold Standard) where the canonical service (/ogmp-metrics, OGMP export) reports Level 4 for the same facility and year"
Cohesion: 0.17
Nodes (11): Actual, Affected Components, BUG-XXX — Two contradictory OGMP facility-level algorithms: /intensity-stats reports Level 5 (Gold Standard) where the canonical service (/ogmp-metrics, OGMP export) reports Level 4 for the same facility and year, Evidence, Expected, Impact, Input, Location (+3 more)

### Community 318 - "BUG-XXX — OGMP reconciliation in the default "All years" view compares the AVERAGE of annual top-down surveys with the SUM of multi-year bottom-up CH4, so perfectly reconciled facilities are flagged (−80 %)"
Cohesion: 0.17
Nodes (11): Actual, Affected Components, BUG-XXX — OGMP reconciliation in the default "All years" view compares the AVERAGE of annual top-down surveys with the SUM of multi-year bottom-up CH4, so perfectly reconciled facilities are flagged (−80 %), Evidence, Expected, Impact, Input, Location (+3 more)

### Community 319 - "BUG-XXX — Facility OGMP 2.0 level counts Draft, Pending and Rejected emission records, so a rejected record can raise a facility's level"
Cohesion: 0.17
Nodes (11): Actual, Affected Components, BUG-XXX — Facility OGMP 2.0 level counts Draft, Pending and Rejected emission records, so a rejected record can raise a facility's level, Evidence, Expected, Impact, Input, Location (+3 more)

### Community 320 - "BUG-XXX — Pending-records banner ignores the GWP-20 toggle: it always shows GWP-100 tCO2e while every other dashboard figure switches to GWP-20"
Cohesion: 0.17
Nodes (11): Actual, Affected Components, BUG-XXX — Pending-records banner ignores the GWP-20 toggle: it always shows GWP-100 tCO2e while every other dashboard figure switches to GWP-20, Evidence, Expected, Impact, Input, Location (+3 more)

### Community 321 - "BUG-XXX — Sentinel-5P "Export to OGMP" stores a 1-hour CH4 mass as the survey's "estimated annual tCH4" (default operating_hours = 1): top-down understated 8,760× and reconciliation always flagged"
Cohesion: 0.17
Nodes (11): Actual, Affected Components, BUG-XXX — Sentinel-5P "Export to OGMP" stores a 1-hour CH4 mass as the survey's "estimated annual tCH4" (default operating_hours = 1): top-down understated 8,760× and reconciliation always flagged, Evidence, Expected, Impact, Input, Location (+3 more)

### Community 322 - "BUG-XXX — Methane loss-rate segment classification differs between the KPI cards, the trend chart and the server: "Downstream / Processing" counts as Midstream in the trend, and "Upstream / Extraction" is dropped from the Upstream KPI"
Cohesion: 0.17
Nodes (11): Actual, Affected Components, BUG-XXX — Methane loss-rate segment classification differs between the KPI cards, the trend chart and the server: "Downstream / Processing" counts as Midstream in the trend, and "Upstream / Extraction" is dropped from the Upstream KPI, Evidence, Expected, Impact, Input, Location (+3 more)

### Community 323 - "BUG-XXX — OGMP survey reconciliation status defaults to "Reconciled" whatever the computed variance; a +354 % discrepancy is stored and shown as Reconciled, and a zero bottom-up case is shown as "+0.0 %""
Cohesion: 0.17
Nodes (11): Actual, Affected Components, BUG-XXX — OGMP survey reconciliation status defaults to "Reconciled" whatever the computed variance; a +354 % discrepancy is stored and shown as Reconciled, and a zero bottom-up case is shown as "+0.0 %", Evidence, Expected, Impact, Input, Location (+3 more)

### Community 324 - "BUG-XXX — Facilities with CH4 emissions but no gas production get methane_loss_rate_pct = 0 and ogmp_target_status "Compliant""
Cohesion: 0.17
Nodes (11): Actual, Affected Components, BUG-XXX — Facilities with CH4 emissions but no gas production get methane_loss_rate_pct = 0 and ogmp_target_status "Compliant", Evidence, Expected, Impact, Input, Location (+3 more)

### Community 325 - "BUG-XXX — Intensity activity/division filter uses record-level columns that are NULL/inconsistent, so numerator and denominator are filtered differently (Upstream intensity blank, E&P intensity 0.0)"
Cohesion: 0.17
Nodes (11): Actual, Affected Components, BUG-XXX — Intensity activity/division filter uses record-level columns that are NULL/inconsistent, so numerator and denominator are filtered differently (Upstream intensity blank, E&P intensity 0.0), Evidence, Expected, Impact, Input, Location (+3 more)

### Community 326 - "BUG-XXX — Intensity with year="all" (default view) pairs each facility's emissions from every year with production from other years; KPI mixes periods"
Cohesion: 0.17
Nodes (11): Actual, Affected Components, BUG-XXX — Intensity with year="all" (default view) pairs each facility's emissions from every year with production from other years; KPI mixes periods, Evidence, Expected, Impact, Input, Location (+3 more)

### Community 327 - "BUG-XXX — Decree 21-330 flaring intensity (/flaring-summary) misconverts units: MMscf 1000× too low, scf/kscf 35× too high, UI "m³" gas production 28× too high; compliance verdict flips"
Cohesion: 0.17
Nodes (11): Actual, Affected Components, BUG-XXX — Decree 21-330 flaring intensity (/flaring-summary) misconverts units: MMscf 1000× too low, scf/kscf 35× too high, UI "m³" gas production 28× too high; compliance verdict flips, Evidence, Expected, Impact, Input, Location (+3 more)

### Community 328 - "BUG-XXX — /granular-intensities (Master Report "Multi-Metric Intensities") divides all-facility emissions by only the facilities with granular MMboe fields, and fabricates NGSI methane (0.05 %) and saleable production (85 %)"
Cohesion: 0.17
Nodes (11): Actual, Affected Components, BUG-XXX — /granular-intensities (Master Report "Multi-Metric Intensities") divides all-facility emissions by only the facilities with granular MMboe fields, and fabricates NGSI methane (0.05 %) and saleable production (85 %), Evidence, Expected, Impact, Input, Location (+3 more)

### Community 329 - "BUG-XXX — Flaring panel treats "All Years" as the current calendar year and ignores the Supply-Chain/Activity/Division/Preview-Pending filters, so it contradicts the dashboard it sits in"
Cohesion: 0.17
Nodes (11): Actual, Affected Components, BUG-XXX — Flaring panel treats "All Years" as the current calendar year and ignores the Supply-Chain/Activity/Division/Preview-Pending filters, so it contradicts the dashboard it sits in, Evidence, Expected, Impact, Input, Location (+3 more)

### Community 330 - "BUG-XXX — Flaring panel invents a 56 % / 40 % / 4 % Routine / Non-Routine / Safety split for generic "flaring" records and shows 0 tCO₂e for every stream (and a 2.5 t/kNm³ proxy when CO₂e is 0)"
Cohesion: 0.17
Nodes (11): Actual, Affected Components, BUG-XXX — Flaring panel invents a 56 % / 40 % / 4 % Routine / Non-Routine / Safety split for generic "flaring" records and shows 0 tCO₂e for every stream (and a 2.5 t/kNm³ proxy when CO₂e is 0), Evidence, Expected, Impact, Input, Location (+3 more)

### Community 331 - "BUG-XXX — Flaring-summary volume conversion: "mmscf" hits the "mscf" branch (1000× understated), "scf" is read as m³, and the prior-year path uses a different, cruder conversion (YoY +2,732 % for identical volumes)"
Cohesion: 0.17
Nodes (11): Actual, Affected Components, BUG-XXX — Flaring-summary volume conversion: "mmscf" hits the "mscf" branch (1000× understated), "scf" is read as m³, and the prior-year path uses a different, cruder conversion (YoY +2,732 % for identical volumes), Evidence, Expected, Impact, Input, Location (+3 more)

### Community 332 - "BUG-XXX — Supply Chain filter is not applied to the emissions-by-source split: "Emissions by Source" donut and Detailed Breakdown rows show company-wide values (sources add up to 7× Scope 1)"
Cohesion: 0.17
Nodes (11): Actual, Affected Components, BUG-XXX — Supply Chain filter is not applied to the emissions-by-source split: "Emissions by Source" donut and Detailed Breakdown rows show company-wide values (sources add up to 7× Scope 1), Evidence, Expected, Impact, Input, Location (+3 more)

### Community 333 - "BUG-XXX — "Preview Pending Data" and the pending banner are inconsistent with the rest of the dashboard: the toggle changes only the KPIs (categorical/org breakdown and Scope 3 stay Verified-only), and the banner ignores the Supply Chain, Activity and Division filters and omits Scope 3"
Cohesion: 0.17
Nodes (11): Actual, Affected Components, BUG-XXX — "Preview Pending Data" and the pending banner are inconsistent with the rest of the dashboard: the toggle changes only the KPIs (categorical/org breakdown and Scope 3 stay Verified-only), and the banner ignores the Supply Chain, Activity and Division filters and omits Scope 3, Evidence, Expected, Impact, Input, Location (+3 more)

### Community 334 - "BUG-XXX — Dashboard "Emissions by Source" mis-classifies process types: fuel-gas combustion (6.47 M t) shown as "Other", pneumatics/tanks/dehydrators/unloading/completions as "Other" instead of Venting, fugitives merged into "Venting", mobile combustion labelled "Stationary Combustion""
Cohesion: 0.17
Nodes (11): Actual, Affected Components, BUG-XXX — Dashboard "Emissions by Source" mis-classifies process types: fuel-gas combustion (6.47 M t) shown as "Other", pneumatics/tanks/dehydrators/unloading/completions as "Other" instead of Venting, fugitives merged into "Venting", mobile combustion labelled "Stationary Combustion", Evidence, Expected, Impact, Input, Location (+3 more)

### Community 335 - "BUG-XXX — Categorical Emissions Overview groups facilities by name instead of id: six distinct facilities are merged into one "Updated Facility" card (3.19 T t)"
Cohesion: 0.17
Nodes (11): Actual, Affected Components, BUG-XXX — Categorical Emissions Overview groups facilities by name instead of id: six distinct facilities are merged into one "Updated Facility" card (3.19 T t), Evidence, Expected, Impact, Input, Location (+3 more)

### Community 336 - "BUG-XXX — "Net Emissions" KPI subtracts company-wide mitigation whatever the Activity/Division filter (Steel & Iron view: Net = −1,027,393 t) and counts "Planned" projects as achieved reductions"
Cohesion: 0.17
Nodes (11): Actual, Affected Components, BUG-XXX — "Net Emissions" KPI subtracts company-wide mitigation whatever the Activity/Division filter (Steel & Iron view: Net = −1,027,393 t) and counts "Planned" projects as achieved reductions, Evidence, Expected, Impact, Input, Location (+3 more)

### Community 337 - "BUG-XXX — Dashboard "Export Executive Brief (PDF)" in the default All-Years view reports every year and every Pending record as "FISCAL YEAR 2026" / "Total verified records": PDF total 8.41 T tCO2e vs 3.72 T on the dashboard"
Cohesion: 0.17
Nodes (11): Actual, Affected Components, BUG-XXX — Dashboard "Export Executive Brief (PDF)" in the default All-Years view reports every year and every Pending record as "FISCAL YEAR 2026" / "Total verified records": PDF total 8.41 T tCO2e vs 3.72 T on the dashboard, Evidence, Expected, Impact, Input, Location (+3 more)

### Community 338 - "BUG-XXX — Executive Brief / Master PDF prints hard-coded performance claims ("15.9 % reduction… on track for -30 %", "65.9 % methane reduction", "Lowest annual flaring on record (-38.0 %)", "VISR camera verified" DRE) regardless of the data"
Cohesion: 0.17
Nodes (11): Actual, Affected Components, BUG-XXX — Executive Brief / Master PDF prints hard-coded performance claims ("15.9 % reduction… on track for -30 %", "65.9 % methane reduction", "Lowest annual flaring on record (-38.0 %)", "VISR camera verified" DRE) regardless of the data, Evidence, Expected, Impact, Input, Location (+3 more)

### Community 339 - "BUG-XXX — QA/QC Dashboard shows "Zero Anomalies Detected… The inventory is fully verified and audit-compliant" with 149 Pending records and 11 records more than 10^6 × the median; the anomaly queue only lists a stored `qa_flag`, which is never computed for existing data"
Cohesion: 0.17
Nodes (11): Actual, Affected Components, BUG-XXX — QA/QC Dashboard shows "Zero Anomalies Detected… The inventory is fully verified and audit-compliant" with 149 Pending records and 11 records more than 10^6 × the median; the anomaly queue only lists a stored `qa_flag`, which is never computed for existing data, Evidence, Expected, Impact, Input, Location (+3 more)

### Community 340 - "BUG-XXX — Uncertainty dashboard applies max(u_CO2, u_CH4, u_N2O) to each record's total CO2e instead of CO2e-weighting the per-gas uncertainties"
Cohesion: 0.17
Nodes (11): Actual, Affected Components, BUG-XXX — Uncertainty dashboard applies max(u_CO2, u_CH4, u_N2O) to each record's total CO2e instead of CO2e-weighting the per-gas uncertainties, Evidence, Expected, Impact, Input, Location (+3 more)

### Community 341 - "BUG-XXX — Inventory uncertainty shrinks by √N when the same emissions are split into N records (shared EF uncertainty treated as independent)"
Cohesion: 0.17
Nodes (11): Actual, Affected Components, BUG-XXX — Inventory uncertainty shrinks by √N when the same emissions are split into N records (shared EF uncertainty treated as independent), Evidence, Expected, Impact, Input, Location (+3 more)

### Community 342 - "BUG-XXX — Meter (activity-data) and GC (composition) uncertainty inputs are accepted but silently ignored by every calculator"
Cohesion: 0.17
Nodes (11): Actual, Affected Components, BUG-XXX — Meter (activity-data) and GC (composition) uncertainty inputs are accepted but silently ignored by every calculator, Evidence, Expected, Impact, Input, Location (+3 more)

### Community 343 - "BUG-XXX — Editing a Scope 1 record replaces its propagated 1σ uncertainty with the raw catalog EF half-width (95 %, EF-only); user_uncertainty is stored unpropagated"
Cohesion: 0.17
Nodes (11): Actual, Affected Components, BUG-XXX — Editing a Scope 1 record replaces its propagated 1σ uncertainty with the raw catalog EF half-width (95 %, EF-only); user_uncertainty is stored unpropagated, Evidence, Expected, Impact, Input, Location (+3 more)

### Community 344 - "BUG-XXX — QA Dashboard "IPCC Tier 1 Uncertainty" reports 1σ as ±%, uses only the CO2 column, and includes Draft and Pending records, so it contradicts the Uncertainty page"
Cohesion: 0.17
Nodes (11): Actual, Affected Components, BUG-XXX — QA Dashboard "IPCC Tier 1 Uncertainty" reports 1σ as ±%, uses only the CO2 column, and includes Draft and Pending records, so it contradicts the Uncertainty page, Evidence, Expected, Impact, Input, Location (+3 more)

### Community 345 - "BUG-XXX — Stored uncertainty has no range or unit validation: Scope 2/3 accept percent values, negatives, NaN and 1e6, and the Uncertainty dashboard shows ±3600 %"
Cohesion: 0.17
Nodes (11): Actual, Affected Components, BUG-XXX — Stored uncertainty has no range or unit validation: Scope 2/3 accept percent values, negatives, NaN and 1e6, and the Uncertainty dashboard shows ±3600 %, Evidence, Expected, Impact, Input, Location (+3 more)

### Community 346 - "BUG-XXX — Emission goals API ("+ Set Target") has no value validation: negative, year 1, and NaN goals are accepted; a NaN goal for the current year makes the main dashboard batch return 500"
Cohesion: 0.17
Nodes (11): Actual, Affected Components, BUG-XXX — Emission goals API ("+ Set Target") has no value validation: negative, year 1, and NaN goals are accepted; a NaN goal for the current year makes the main dashboard batch return 500, Evidence, Expected, Impact, Input, Location (+3 more)

### Community 347 - "BUG-XXX — Dashboard "% GOAL" badge in the default All-years view divides the cumulative multi-year Scope 1+2 total by the single current-year goal (and ignores region/facility filters)"
Cohesion: 0.17
Nodes (11): Actual, Affected Components, BUG-XXX — Dashboard "% GOAL" badge in the default All-years view divides the cumulative multi-year Scope 1+2 total by the single current-year goal (and ignores region/facility filters), Evidence, Expected, Impact, Input, Location (+3 more)

### Community 348 - "BUG-XXX — GET /api/manage/sbti ignores facility/region scoping: region-restricted users can read organisation-wide Verified emission totals for any year"
Cohesion: 0.17
Nodes (11): Actual, Affected Components, BUG-XXX — GET /api/manage/sbti ignores facility/region scoping: region-restricted users can read organisation-wide Verified emission totals for any year, Evidence, Expected, Impact, Input, Location (+3 more)

### Community 349 - "BUG-XXX — SBTi target POST accepts NaN / Infinity (range checks pass for non-finite floats); trajectory endpoint then returns 500 or invalid JSON for all users"
Cohesion: 0.17
Nodes (11): Actual, Affected Components, BUG-XXX — SBTi target POST accepts NaN / Infinity (range checks pass for non-finite floats); trajectory endpoint then returns 500 or invalid JSON for all users, Evidence, Expected, Impact, Input, Location (+3 more)

### Community 350 - "BUG-XXX — SBTi dashboard shows "ON TRACK — Reduction: 100% vs Baseline" when there is no verified data at all in the target window"
Cohesion: 0.17
Nodes (11): Actual, Affected Components, BUG-XXX — SBTi dashboard shows "ON TRACK — Reduction: 100% vs Baseline" when there is no verified data at all in the target window, Evidence, Expected, Impact, Input, Location (+3 more)

### Community 351 - "BUG-XXX — SBTi progress KPI uses the current, incomplete year (and any future year) as the "current" year, so the dashboard reports ~95-99% reduction and ON TRACK"
Cohesion: 0.17
Nodes (11): Actual, Affected Components, BUG-XXX — SBTi progress KPI uses the current, incomplete year (and any future year) as the "current" year, so the dashboard reports ~95-99% reduction and ON TRACK, Evidence, Expected, Impact, Input, Location (+3 more)

### Community 352 - "BUG-XXX — SBTi target labelled "1.5°C" is not tied to its reduction rate (0.5 %/yr accepted and displayed as 1.5°C); arbitrary pathway strings and future base years accepted; main-dashboard banner hard-codes "SBTi 1.5°C Linear Target""
Cohesion: 0.17
Nodes (11): Actual, Affected Components, BUG-XXX — SBTi target labelled "1.5°C" is not tied to its reduction rate (0.5 %/yr accepted and displayed as 1.5°C); arbitrary pathway strings and future base years accepted; main-dashboard banner hard-codes "SBTi 1.5°C Linear Target", Evidence, Expected, Impact, Input, Location (+3 more)

### Community 353 - "BUG-XXX — SBTi "Scope 1+2 (Operational)" view compares Scope 1+2 actuals to the Scope 1+2+3 baseline and target line (inflated reduction %, false ON TRACK)"
Cohesion: 0.17
Nodes (11): Actual, Affected Components, BUG-XXX — SBTi "Scope 1+2 (Operational)" view compares Scope 1+2 actuals to the Scope 1+2+3 baseline and target line (inflated reduction %, false ON TRACK), Evidence, Expected, Impact, Input, Location (+3 more)

### Community 354 - "BUG-XXX — Audit trail (/api/audit/, /api/audit/export) is not facility/region-scoped: a region-restricted superuser reads activity entries for every region's records"
Cohesion: 0.17
Nodes (11): Actual, Affected Components, BUG-XXX — Audit trail (/api/audit/, /api/audit/export) is not facility/region-scoped: a region-restricted superuser reads activity entries for every region's records, Evidence, Expected, Impact, Input, Location (+3 more)

### Community 355 - "BUG-XXX — Equity-share allocation ignores effective dates (time-sliced ownership never applied) and POST /api/equity/shares accepts any percentage (500, -50, inf) from any business role"
Cohesion: 0.17
Nodes (11): Actual, Affected Components, BUG-XXX — Equity-share allocation ignores effective dates (time-sliced ownership never applied) and POST /api/equity/shares accepts any percentage (500, -50, inf) from any business role, Evidence, Expected, Impact, Input, Location (+3 more)

### Community 356 - "BUG-XXX — /api/reports/master-annual-report serves full annual GHG report PDFs to any logged-in role (incl. it_admin and out-of-region users) and returns a static, pre-generated file regardless of facility_id"
Cohesion: 0.17
Nodes (11): Actual, Affected Components, BUG-XXX — /api/reports/master-annual-report serves full annual GHG report PDFs to any logged-in role (incl. it_admin and out-of-region users) and returns a static, pre-generated file regardless of facility_id, Evidence, Expected, Impact, Input, Location (+3 more)

### Community 357 - "BUG-XXX — Bulk upload job API lets any logged-in role (user, it_admin) create/overwrite facilities and custom factors, bypassing RBAC and region scoping"
Cohesion: 0.17
Nodes (11): Actual, Affected Components, BUG-XXX — Bulk upload job API lets any logged-in role (user, it_admin) create/overwrite facilities and custom factors, bypassing RBAC and region scoping, Evidence, Expected, Impact, Input, Location (+3 more)

### Community 358 - "BUG-XXX — Alembic migration chain is unusable: `flask db upgrade` fails on both the existing DB and a fresh DB"
Cohesion: 0.17
Nodes (11): Actual, Affected Components, BUG-XXX — Alembic migration chain is unusable: `flask db upgrade` fails on both the existing DB and a fresh DB, Evidence, Expected, Impact, Input, Location (+3 more)

### Community 359 - "BUG-XXX — Deleting a user wipes approved_by/created_by on every record they approved or entered: Verified records lose their maker-checker evidence"
Cohesion: 0.17
Nodes (11): Actual, Affected Components, BUG-XXX — Deleting a user wipes approved_by/created_by on every record they approved or entered: Verified records lose their maker-checker evidence, Evidence, Expected, Impact, Input, Location (+3 more)

### Community 360 - "BUG-XXX — Bulk-upload overwrite rewrites approved records without an audit trail and leaves them "Pending" but still marked approved"
Cohesion: 0.17
Nodes (11): Actual, Affected Components, BUG-XXX — Bulk-upload overwrite rewrites approved records without an audit trail and leaves them "Pending" but still marked approved, Evidence, Expected, Impact, Input, Location (+3 more)

### Community 361 - "BUG-XXX — Bulk upload with "Overwrite Duplicates" enabled inserts every in-file duplicate row as a separate record (double counting)"
Cohesion: 0.17
Nodes (11): Actual, Affected Components, BUG-XXX — Bulk upload with "Overwrite Duplicates" enabled inserts every in-file duplicate row as a separate record (double counting), Evidence, Expected, Impact, Input, Location (+3 more)

### Community 362 - "BUG-XXX — Custom factor names are not unique, yet bulk import resolves factors by name: the most recently created same-named factor is silently applied"
Cohesion: 0.17
Nodes (11): Actual, Affected Components, BUG-XXX — Custom factor names are not unique, yet bulk import resolves factors by name: the most recently created same-named factor is silently applied, Evidence, Expected, Impact, Input, Location (+3 more)

### Community 363 - "BUG-XXX — Deleting a facility that has any OGMP level-upgrade log fails with 500 (FK violation) and leaks raw SQL"
Cohesion: 0.17
Nodes (11): Actual, Affected Components, BUG-XXX — Deleting a facility that has any OGMP level-upgrade log fails with 500 (FK violation) and leaks raw SQL, Evidence, Expected, Impact, Input, Location (+3 more)

### Community 364 - "BUG-XXX — Deleting a user who created production data, SBTi targets or OGMP level logs fails with 500 (FK cleanup list incomplete)"
Cohesion: 0.17
Nodes (11): Actual, Affected Components, BUG-XXX — Deleting a user who created production data, SBTi targets or OGMP level logs fails with 500 (FK cleanup list incomplete), Evidence, Expected, Impact, Input, Location (+3 more)

### Community 365 - "BUG-XXX — CustomDropdown is not keyboard-operable and form inputs have no programmatic labels: Region, Process Type, Emission Factor and Unit cannot be set without a mouse"
Cohesion: 0.17
Nodes (11): Actual, Affected Components, BUG-XXX — CustomDropdown is not keyboard-operable and form inputs have no programmatic labels: Region, Process Type, Emission Factor and Unit cannot be set without a mouse, Evidence, Expected, Impact, Input, Location (+3 more)

### Community 366 - "BUG-XXX — AGR form throughput units MMscfd / Mcf/day / m³/yr are ignored by the server (read as MMscf/yr): CO2 365× low, 2.7× high, or 28,317× high"
Cohesion: 0.17
Nodes (11): Actual, Affected Components, BUG-XXX — AGR form throughput units MMscfd / Mcf/day / m³/yr are ignored by the server (read as MMscf/yr): CO2 365× low, 2.7× high, or 28,317× high, Evidence, Expected, Impact, Input, Location (+3 more)

### Community 367 - "BUG-XXX — User Management actions are missing from the Audit Trail: account creation and logout logs are never committed, and user deletion is not logged at all"
Cohesion: 0.17
Nodes (11): Actual, Affected Components, BUG-XXX — User Management actions are missing from the Audit Trail: account creation and logout logs are never committed, and user deletion is not logged at all, Evidence, Expected, Impact, Input, Location (+3 more)

### Community 368 - "BUG-XXX — CHP allocation form labels Power Output "MWh" but the server uses the number as MMBtu: heat share (and Scope 2 tCO2e) overstated ~2.7× with WRI efficiency method"
Cohesion: 0.17
Nodes (11): Actual, Affected Components, BUG-XXX — CHP allocation form labels Power Output "MWh" but the server uses the number as MMBtu: heat share (and Scope 2 tCO2e) overstated ~2.7× with WRI efficiency method, Evidence, Expected, Impact, Input, Location (+3 more)

### Community 369 - "BUG-XXX — Dehydrator form sends "Contactor Pressure" as `dehy_pressure`, but the server reads `dehy_press`: user pressure silently ignored, 800 psig default always used (AGR "routed to flare"/"flash gas recycled" checkboxes also unread)"
Cohesion: 0.17
Nodes (11): Actual, Affected Components, BUG-XXX — Dehydrator form sends "Contactor Pressure" as `dehy_pressure`, but the server reads `dehy_press`: user pressure silently ignored, 800 psig default always used (AGR "routed to flare"/"flash gas recycled" checkboxes also unread), Evidence, Expected, Impact, Input, Location (+3 more)

### Community 370 - "BUG-XXX — Dehydrator throughput entered under the label "MMscf/yr" is saved with unit "MMscf/day" (record activity unit 365× off)"
Cohesion: 0.17
Nodes (11): Actual, Affected Components, BUG-XXX — Dehydrator throughput entered under the label "MMscf/yr" is saved with unit "MMscf/day" (record activity unit 365× off), Evidence, Expected, Impact, Input, Location (+3 more)

### Community 371 - "BUG-XXX — Emission Calculation Result panel rounds gas masses to 3 decimals of a tonne: non-zero CH4/N2O shown as "0.00 tonnes""
Cohesion: 0.17
Nodes (11): Actual, Affected Components, BUG-XXX — Emission Calculation Result panel rounds gas masses to 3 decimals of a tonne: non-zero CH4/N2O shown as "0.00 tonnes", Evidence, Expected, Impact, Input, Location (+3 more)

### Community 372 - "BUG-XXX — Reports Excel/PDF exports drop the Division, Field, Method and Search filters shown on screen"
Cohesion: 0.17
Nodes (11): Actual, Affected Components, BUG-XXX — Reports Excel/PDF exports drop the Division, Field, Method and Search filters shown on screen, Evidence, Expected, Impact, Input, Location (+3 more)

### Community 373 - "BUG-XXX — Reports "Group By" selector has no effect (getGroupedData is never called)"
Cohesion: 0.17
Nodes (11): Actual, Affected Components, BUG-XXX — Reports "Group By" selector has no effect (getGroupedData is never called), Evidence, Expected, Impact, Input, Location (+3 more)

### Community 374 - "BUG-XXX — Scope 1 "Live Equation Inspector" states "GWP Standard: IPCC AR6 (CH₄:28, N₂O:265)" — hard-coded, AR5 values mislabelled as AR6, ignores the org GWP setting"
Cohesion: 0.17
Nodes (11): Actual, Affected Components, BUG-XXX — Scope 1 "Live Equation Inspector" states "GWP Standard: IPCC AR6 (CH₄:28, N₂O:265)" — hard-coded, AR5 values mislabelled as AR6, ignores the org GWP setting, Evidence, Expected, Impact, Input, Location (+3 more)

### Community 375 - "BUG-XXX — Reports "2025 Master Report (PDF)" button sends facility_id=[object Object]; facility selection ignored"
Cohesion: 0.17
Nodes (11): Actual, Affected Components, BUG-XXX — Reports "2025 Master Report (PDF)" button sends facility_id=[object Object]; facility selection ignored, Evidence, Expected, Impact, Input, Location (+3 more)

### Community 376 - "BUG-XXX — Scope 1 "Recent Activity": Export CSV exports only the 10 rows of the current page, and the Year/Process filter options are built from that page only"
Cohesion: 0.17
Nodes (11): Actual, Affected Components, BUG-XXX — Scope 1 "Recent Activity": Export CSV exports only the 10 rows of the current page, and the Year/Process filter options are built from that page only, Evidence, Expected, Impact, Input, Location (+3 more)

### Community 377 - "BUG-XXX — Scope 1 entry form does not reflow at phone width (390 px): Field input, Tier selector and factor picker are clipped off-screen"
Cohesion: 0.17
Nodes (11): Actual, Affected Components, BUG-XXX — Scope 1 entry form does not reflow at phone width (390 px): Field input, Tier selector and factor picker are clipped off-screen, Evidence, Expected, Impact, Input, Location (+3 more)

### Community 378 - "BUG-XXX — Scope 2 form: switching Source Type to Steam/Heat or CHP leaves the hidden unit at "kWh" — dropdown shows "Select..." but the request sends unit "kWh" (1000 "MMBtu" of steam booked as 3.41 MMBtu)"
Cohesion: 0.17
Nodes (11): Actual, Affected Components, BUG-XXX — Scope 2 form: switching Source Type to Steam/Heat or CHP leaves the hidden unit at "kWh" — dropdown shows "Select..." but the request sends unit "kWh" (1000 "MMBtu" of steam booked as 3.41 MMBtu), Evidence, Expected, Impact, Input, Location (+3 more)

### Community 379 - "BUG-XXX — Reports search keeps the current page number: "Total Records: 42 | Showing: 0" and no pager to recover"
Cohesion: 0.17
Nodes (11): Actual, Affected Components, BUG-XXX — Reports search keeps the current page number: "Total Records: 42 | Showing: 0" and no pager to recover, Evidence, Expected, Impact, Input, Location (+3 more)

### Community 380 - "BUG-XXX — Manage Data and Reference Data swallow API load errors and show them as empty data ("No production record found", empty factor catalog)"
Cohesion: 0.17
Nodes (11): Actual, Affected Components, BUG-XXX — Manage Data and Reference Data swallow API load errors and show them as empty data ("No production record found", empty factor catalog), Evidence, Expected, Impact, Input, Location (+3 more)

### Community 381 - "BUG-XXX — Scope 1 bulk import books a row with a blank Unit as m³ and accepts year 1800, both of which the manual form/API reject"
Cohesion: 0.17
Nodes (11): Actual, Affected Components, BUG-XXX — Scope 1 bulk import books a row with a blank Unit as m³ and accepts year 1800, both of which the manual form/API reject, Evidence, Expected, Impact, Input, Location (+3 more)

### Community 382 - "BUG-XXX — Custom emission factor with every factor field blank is saved (CO2/CH4/N2O = 0) and Tier 2 records that use it are stored with 0 tCO2e and no warning"
Cohesion: 0.17
Nodes (11): Actual, Affected Components, BUG-XXX — Custom emission factor with every factor field blank is saved (CO2/CH4/N2O = 0) and Tier 2 records that use it are stored with 0 tCO2e and no warning, Evidence, Expected, Impact, Input, Location (+3 more)

### Community 383 - "BUG-XXX — "Add Region" (create facility) form fails with HTTP 500 unless the optional Latitude/Longitude fields are filled"
Cohesion: 0.17
Nodes (11): Actual, Affected Components, BUG-XXX — "Add Region" (create facility) form fails with HTTP 500 unless the optional Latitude/Longitude fields are filled, Evidence, Expected, Impact, Input, Location (+3 more)

### Community 384 - "BUG-XXX — Onshore fugitives "Tier 1: Facility-Level" form: the on-screen preview says 16,644 tCO2e but the saved record is 1.456 tCO2e — the server ignores the selected facility type and duration and books the facility count as a count of valves"
Cohesion: 0.17
Nodes (11): Actual, Affected Components, BUG-XXX — Onshore fugitives "Tier 1: Facility-Level" form: the on-screen preview says 16,644 tCO2e but the saved record is 1.456 tCO2e — the server ignores the selected facility type and duration and books the facility count as a count of valves, Evidence, Expected, Impact, Input, Location (+3 more)

### Community 385 - "BUG-XXX — Logout does not invalidate the session: a session cookie captured before logout keeps full API access (client-side signed cookie, no server-side revocation)"
Cohesion: 0.17
Nodes (11): Actual, Affected Components, BUG-XXX — Logout does not invalidate the session: a session cookie captured before logout keeps full API access (client-side signed cookie, no server-side revocation), Evidence, Expected, Impact, Input, Location (+3 more)

### Community 386 - "BUG-XXX — Manage Data page crashes for every user when any facility has a NULL name; POST /api/facilities accepts facilities with no name"
Cohesion: 0.17
Nodes (11): Actual, Affected Components, BUG-XXX — Manage Data page crashes for every user when any facility has a NULL name; POST /api/facilities accepts facilities with no name, Evidence, Expected, Impact, Input, Location (+3 more)

### Community 387 - "BUG-XXX — Scope 1 form saves an entry with no Unit selected: the client silently assumes m³ (10 → 2,641.72 gal stored) while the server calculates from the raw 10 in calc_inputs, so the stored activity and its emissions disagree 264×"
Cohesion: 0.17
Nodes (11): Actual, Affected Components, BUG-XXX — Scope 1 form saves an entry with no Unit selected: the client silently assumes m³ (10 → 2,641.72 gal stored) while the server calculates from the raw 10 in calc_inputs, so the stored activity and its emissions disagree 264×, Evidence, Expected, Impact, Input, Location (+3 more)

### Community 388 - "BUG-XXX — Reports "PDF Report" prints every unit and gas name with a missing-glyph box: "tCO■e", "CO■", "CH■", "N■O""
Cohesion: 0.17
Nodes (11): Actual, Affected Components, BUG-XXX — Reports "PDF Report" prints every unit and gas name with a missing-glyph box: "tCO■e", "CO■", "CH■", "N■O", Evidence, Expected, Impact, Input, Location (+3 more)

### Community 389 - "BUG-XXX — Maker-checker outcome is invisible to the maker: reject/approve send no notification, the Scope 1 list shows Rejected/Pending rows exactly like Verified ones, and the reject dialog claims the record is "permanently deleted" although it is kept as Rejected"
Cohesion: 0.17
Nodes (11): Actual, Affected Components, BUG-XXX — Maker-checker outcome is invisible to the maker: reject/approve send no notification, the Scope 1 list shows Rejected/Pending rows exactly like Verified ones, and the reject dialog claims the record is "permanently deleted" although it is kept as Rejected, Evidence, Expected, Impact, Input, Location (+3 more)

### Community 390 - "BUG-XXX — Scope 2 electricity create trusts client-supplied `co2e` / `emission_factor`: 0 kWh can be booked as 12,345 tCO2e, negative Scope 2 (-500 t) is accepted, and any unknown grid region takes the client's factor"
Cohesion: 0.17
Nodes (11): Actual, Affected Components, BUG-XXX — Scope 2 electricity create trusts client-supplied `co2e` / `emission_factor`: 0 kWh can be booked as 12,345 tCO2e, negative Scope 2 (-500 t) is accepted, and any unknown grid region takes the client's factor, Evidence, Expected, Impact, Input, Location (+3 more)

### Community 391 - "BUG-XXX — Manage Data forms discard the server's validation message and show a generic "Failed to …" toast (negative production, negative factor, facility 500, etc.)"
Cohesion: 0.17
Nodes (11): Actual, Affected Components, BUG-XXX — Manage Data forms discard the server's validation message and show a generic "Failed to …" toast (negative production, negative factor, facility 500, etc.), Evidence, Expected, Impact, Input, Location (+3 more)

### Community 392 - "Implementation Plan - Activity Log Dashboard Replica"
Cohesion: 0.17
Nodes (11): Backend, Frontend, Goal, Implementation Plan - Activity Log Dashboard Replica, [MODIFY] [backend/emissions/models.py](file:///c:/Users/samsung/Desktop/cement/backend/emissions/models.py), [MODIFY] [backend/emissions/serializers.py](file:///c:/Users/samsung/Desktop/cement/backend/emissions/serializers.py), [MODIFY] [src/components/emissions/EmissionList.tsx](file:///c:/Users/samsung/Desktop/cement/frontend/src/components/emissions/EmissionList.tsx), [MODIFY] [src/components/emissions/ProtocolCalculator.tsx](file:///c:/Users/samsung/Desktop/cement/frontend/src/components/emissions/ProtocolCalculator.tsx) (+3 more)

### Community 393 - "Modern "Glassy" PDF Report Overhaul"
Cohesion: 0.17
Nodes (11): API Reporting Requirements (2023 Guidance Analysis), Design Aesthetics (Sonatrach "Glassy" Theme), File: `public/modern-report.js`, Goal, Modern "Glassy" PDF Report Overhaul, Proposed Changes, Structure Refined, Technical Implementation (+3 more)

### Community 394 - "Compliance Gap Analysis: API Guidance 2.0 (2023)"
Cohesion: 0.17
Nodes (11): 1. Flaring Intensity Metric, 2. Global Warming Potential (GWP), 3. Organizational Boundaries, 4. Hierarchy & Granularity, 5. Missing Sections (Major Gaps), Compliance Gap Analysis: API Guidance 2.0 (2023), Section 3: GHG Mitigation, Section 5: Scope 3 Emissions (+3 more)

### Community 395 - "Implementation Plan: API Guidance 2.0 Compliance"
Cohesion: 0.17
Nodes (11): 1. Core Calculation & Standards, 2. New Data Modules (Manage Data), 3. Database Schema Updates, 4. Dashboard & Reporting Updates, 5. Execution Order, Flaring Intensity Metrics, Global Warming Potential (GWP) Standardization, Implementation Plan: API Guidance 2.0 Compliance (+3 more)

### Community 396 - "SolarEPC-Pro: Walkthrough & Verification"
Cohesion: 0.17
Nodes (11): Features Implemented, Features Implemented, Features Implemented, Phase 12: Ultimate Optimization & Utility, Phase 13: Advanced Physics & Persistence, Phase 9: 3D Realism & Immersion, Previous Phases (Summary), SolarEPC-Pro: Walkthrough & Verification (+3 more)

### Community 397 - "[Component] Emissions Calculator UI"
Cohesion: 0.17
Nodes (11): Automated Tests, [Component] Emissions Calculator UI, [Component] Emissions Logic, Implementation Plan - Refining Emissions Calculator Table, Manual Verification, [MODIFY] [calculator.css](file:///c:/Users/samsung/Desktop/ghg%20old/public/calculator.css), [MODIFY] [calculator-grid.css](file:///c:/Users/samsung/Desktop/ghg%20old/public/calculator-grid.css), [MODIFY] [emissions-calc.js](file:///c:/Users/samsung/Desktop/ghg%20old/public/emissions-calc.js) (+3 more)

### Community 398 - "Critical Findings (Require Action)"
Cohesion: 0.17
Nodes (11): C1 — `constants.py` misleading dict name (low impact), C2 — `legacy_engine.py:602-606` double division by 1000 in `is_specific` path, C3 — `legacy_engine.py:614` back-calculation of CH4 from total is incorrect, C4 — `scope3.py:162` ambiguous EF units in bulk import, C5 — `combustion.py:38` missing CONVERSIONS key, C6 — Pressure unit ambiguity in LiquidsUnloading (M2 re-classified), Calculation Logic Audit — Full Read-Only Review, Critical Findings (Require Action) (+3 more)

### Community 399 - "Implementation Plan - Cement Industry GHG Emissions Calculator"
Cohesion: 0.17
Nodes (11): Automated Tests, Backend (Django), Frontend (Next.js), Goal Description, Implementation Plan - Cement Industry GHG Emissions Calculator, Manual Verification, [NEW] [backend/](file:///c:/Users/samsung/Desktop/cement/backend), [NEW] [frontend/](file:///c:/Users/samsung/Desktop/cement/frontend) (+3 more)

### Community 400 - "[Server] Calculation Engine Fixes"
Cohesion: 0.17
Nodes (11): Automated Tests, Implementation Plan - API Compendium 2021 Verification Fixes, Manual Verification, [MODIFY] [dispatcher.py](file:///c:/Users/samsung/Desktop/h/new/server/calculations/dispatcher.py), [MODIFY] [emission_factors_api2021.py](file:///c:/Users/samsung/Desktop/h/new/server/emission_factors_api2021.py), [MODIFY] [fugitive.py](file:///c:/Users/samsung/Desktop/h/new/server/calculations/fugitive.py), [MODIFY] [test_compendium_examples.py](file:///c:/Users/samsung/Desktop/h/test_compendium_examples.py), Proposed Changes (+3 more)

### Community 401 - "3. Test Quality & Rigor Audit"
Cohesion: 0.17
Nodes (11): 1. Test Harness Structure & Strategy, 2.1 Backend Pytest Suite Summary, 2.2 Independent Validation Suite Summary (`validation/scripts/run_full_validation_suite.py`), 2.3 Frontend Benchmarks & Parity Suite, 2. Test Execution Inventory & Execution Results, 3.1 Non-Circularity Verification, 3.2 Assertion Rigor & Avoidance of Vacuous Tests, 3.3 Database Isolation & Fixture Hygiene (+3 more)

### Community 402 - "Enterprise Performance, Stress & Latency Benchmark Audit"
Cohesion: 0.17
Nodes (11): 1. Executive Performance Summary, 2. Frontend High-Volume Benchmarks, 3. Backend & API Latency Benchmarks, 4.1 Invalidation Performance, 4.2 Server Memory Stability, 4. Caching & Memory Footprint, Enterprise Performance, Stress & Latency Benchmark Audit, Key Benchmark Highlights: (+3 more)

### Community 403 - "3. Critical Flaws in the Legacy Test Suite"
Cohesion: 0.17
Nodes (11): 1. Executive Summary & Inventory, 2. Framework & Infrastructure Analysis, 3.1 Circular Calculation Tests (Self-Referential Assertions), 3.2 Tests with Weak or Trivial Assertions (Status-Code Only), 3.3 Over-reliance on Mock Logic, 3.4 Suspicious and Potentially Incorrect Expected Values, 3.5 Obsolete and Deprecated Scratch Files, 3. Critical Flaws in the Legacy Test Suite (+3 more)

### Community 405 - "test_emission_calculations.py"
Cohesion: 0.17
Nodes (7): =============================================================================…, Aggregates test results for a final summary table., Fugitive average — uses _generic_calculation with catalog EF. EF: ch4=0.1…, Tier 3 Combustion with gas composition (carbon mass balance): volume = 1000 scf…, SummaryResult, TestTier1FugitiveAverage, TestTier3CombustionGasComposition

### Community 406 - "test_security_hardening.py"
Cohesion: 0.12
Nodes (17): ensure_admin_seeded(), Seeds essential development and admin accounts when SEED_ADMIN=true., client(), fixture, Security hardening regression tests — Phase 1.2. Verifies that: - Hard-coded…, ensure_admin_seeded() must be a no-op when SEED_ADMIN is not set (default:…, SECURITY REGRESSION (CRIT-02): The 'a@a' dev shortcut account must not be auto-…, SECURITY REGRESSION (CRIT-02): The 'a' dev shortcut account (not even a valid… (+9 more)

### Community 407 - "test_audit_bug_fixes.py"
Cohesion: 0.22
Nodes (9): client(), fixture, Verify ComponentFugitiveCalculator handles scalar counts without AttributeError., Verify delete_mitigation returns 400 Bad Request on malformed ID instead of 500…, Verify get_ogmp_surveys handles records with null measured_rate_kg_hr without…, test_component_fugitive_calculator_scalar_counts(), test_delete_mitigation_invalid_id_format(), test_ogmp_survey_null_measured_rate() (+1 more)

### Community 408 - "test_tier2_api_e2e.py"
Cohesion: 0.20
Nodes (11): client(), fixture, End-to-End API and Integration Tests for Tier 2 Custom / Regional / Lab Factor…, End-to-end verification of Tier 2 liquid fuel preset (IANOR NA 8110 Diesel): 1.…, Verifies Mode B: creating a custom factor via /custom-factors/ and using it., End-to-end verification of Tier 2 preset workflow: 1. Authenticate as admin 2.…, test_admin(), test_facility() (+3 more)

### Community 409 - "files"
Cohesion: 0.29
Nodes (6): files, main.js, node_modules/**/*, public/**/*, server.js, users_v2.db

### Community 410 - "Implementation Tasks: QA/QC Module (IPCC & ISO 14064)"
Cohesion: 0.17
Nodes (11): Dependencies & Execution Order, Implementation for User Story 1, Implementation for User Story 2, Implementation for User Story 3, Implementation Tasks: QA/QC Module (IPCC & ISO 14064), Phase 1: Setup (Shared Infrastructure), Phase 2: Foundational (Blocking Prerequisites), Phase 3: User Story 1 - Automated Data Validation (Priority: P1) ⭐ MVP (+3 more)

### Community 411 - "BUG-001 — Bulk upload job API lets any logged-in role (user, it_admin) create/overwrite facilities and custom factors, bypassing RBAC and region scoping"
Cohesion: 0.18
Nodes (11): Actual, Affected Components, BUG-001 — Bulk upload job API lets any logged-in role (user, it_admin) create/overwrite facilities and custom factors, bypassing RBAC and region scoping, Evidence, Expected, Impact, Input, Location (+3 more)

### Community 412 - "BUG-021 — Reports search keeps the current page number: "Total Records: 42 | Showing: 0" and no pager to recover"
Cohesion: 0.18
Nodes (11): Actual, Affected Components, BUG-021 — Reports search keeps the current page number: "Total Records: 42 | Showing: 0" and no pager to recover, Evidence, Expected, Impact, Input, Location (+3 more)

### Community 413 - "BUG-023 — Tier 3 combustion/flaring gas composition: each component is converted percent→fraction on its own, so mol% values ≤ 1 (e.g. C4 = 1.0 %, C5 = 0.5 %) become 100 % / 50 %; CO2 inflated 2.7× on the app's own template sample"
Cohesion: 0.18
Nodes (11): Actual, Affected Components, BUG-023 — Tier 3 combustion/flaring gas composition: each component is converted percent→fraction on its own, so mol% values ≤ 1 (e.g. C4 = 1.0 %, C5 = 0.5 %) become 100 % / 50 %; CO2 inflated 2.7× on the app's own template sample, Evidence, Expected, Impact, Input, Location (+3 more)

### Community 414 - "BUG-025 — Meter (activity-data) and GC (composition) uncertainty inputs are accepted but silently ignored by every calculator"
Cohesion: 0.18
Nodes (11): Actual, Affected Components, BUG-025 — Meter (activity-data) and GC (composition) uncertainty inputs are accepted but silently ignored by every calculator, Evidence, Expected, Impact, Input, Location (+3 more)

### Community 415 - "BUG-026 — Flaring panel treats "All Years" as the current calendar year and ignores the Supply-Chain/Activity/Division/Preview-Pending filters, so it contradicts the dashboard it sits in"
Cohesion: 0.18
Nodes (11): Actual, Affected Components, BUG-026 — Flaring panel treats "All Years" as the current calendar year and ignores the Supply-Chain/Activity/Division/Preview-Pending filters, so it contradicts the dashboard it sits in, Evidence, Expected, Impact, Input, Location (+3 more)

### Community 416 - "BUG-003 — Editing a Scope 1 record's quantity via PUT /api/emissions/<id> does not recalculate emissions (stale `amount` from source_payload wins)"
Cohesion: 0.18
Nodes (11): Actual, Affected Components, BUG-003 — Editing a Scope 1 record's quantity via PUT /api/emissions/<id> does not recalculate emissions (stale `amount` from source_payload wins), Evidence, Expected, Impact, Input, Location (+3 more)

### Community 417 - "BUG-027 — Tier 1 combustion applies the catalog HHV in the wrong basis when the activity unit is mass or the other phase (diesel/crude per tonne ×3.6, natural gas per tonne ÷40, ethane per scf ×39)"
Cohesion: 0.18
Nodes (11): Actual, Affected Components, BUG-027 — Tier 1 combustion applies the catalog HHV in the wrong basis when the activity unit is mass or the other phase (diesel/crude per tonne ×3.6, natural gas per tonne ÷40, ethane per scf ×39), Evidence, Expected (t CO2, independent), Impact, Input, Location (+3 more)

### Community 418 - "BUG-029 — Manage Data page crashes for every user when any facility has a NULL name; POST /api/facilities accepts facilities with no name"
Cohesion: 0.18
Nodes (11): Actual, Affected Components, BUG-029 — Manage Data page crashes for every user when any facility has a NULL name; POST /api/facilities accepts facilities with no name, Evidence, Expected, Impact, Input, Location (+3 more)

### Community 419 - "BUG-030 — POST /api/emissions/ calculates from `quantity`/`fuel_type` but stores only `amount`/`fuel`: records keep emissions with NULL activity quantity and fuel"
Cohesion: 0.18
Nodes (11): Actual, Affected Components, BUG-030 — POST /api/emissions/ calculates from `quantity`/`fuel_type` but stores only `amount`/`fuel`: records keep emissions with NULL activity quantity and fuel, Evidence, Expected, Impact, Input, Location (+3 more)

### Community 420 - "BUG-031 — Facility OGMP 2.0 level counts Draft, Pending and Rejected emission records, so a rejected record can raise a facility's level"
Cohesion: 0.18
Nodes (11): Actual, Affected Components, BUG-031 — Facility OGMP 2.0 level counts Draft, Pending and Rejected emission records, so a rejected record can raise a facility's level, Evidence, Expected, Impact, Input, Location (+3 more)

### Community 421 - "BUG-032 — GET /api/manage/sbti ignores facility/region scoping: region-restricted users can read organisation-wide Verified emission totals for any year"
Cohesion: 0.18
Nodes (11): Actual, Affected Components, BUG-032 — GET /api/manage/sbti ignores facility/region scoping: region-restricted users can read organisation-wide Verified emission totals for any year, Evidence, Expected, Impact, Input, Location (+3 more)

### Community 422 - "BUG-033 — Decree 21-330 flaring intensity (/flaring-summary) misconverts units: MMscf 1000× too low, scf/kscf 35× too high, UI "m³" gas production 28× too high; compliance verdict flips"
Cohesion: 0.18
Nodes (11): Actual, Affected Components, BUG-033 — Decree 21-330 flaring intensity (/flaring-summary) misconverts units: MMscf 1000× too low, scf/kscf 35× too high, UI "m³" gas production 28× too high; compliance verdict flips, Evidence, Expected, Impact, Input, Location (+3 more)

### Community 423 - "BUG-034 — SBTi target POST accepts NaN / Infinity (range checks pass for non-finite floats); trajectory endpoint then returns 500 or invalid JSON for all users"
Cohesion: 0.18
Nodes (11): Actual, Affected Components, BUG-034 — SBTi target POST accepts NaN / Infinity (range checks pass for non-finite floats); trajectory endpoint then returns 500 or invalid JSON for all users, Evidence, Expected, Impact, Input, Location (+3 more)

### Community 424 - "BUG-035 — Flaring-summary volume conversion: "mmscf" hits the "mscf" branch (1000× understated), "scf" is read as m³, and the prior-year path uses a different, cruder conversion (YoY +2,732 % for identical volumes)"
Cohesion: 0.18
Nodes (11): Actual, Affected Components, BUG-035 — Flaring-summary volume conversion: "mmscf" hits the "mscf" branch (1000× understated), "scf" is read as m³, and the prior-year path uses a different, cruder conversion (YoY +2,732 % for identical volumes), Evidence, Expected, Impact, Input, Location (+3 more)

### Community 425 - "BUG-036 — Flaring panel invents a 56 % / 40 % / 4 % Routine / Non-Routine / Safety split for generic "flaring" records and shows 0 tCO₂e for every stream (and a 2.5 t/kNm³ proxy when CO₂e is 0)"
Cohesion: 0.18
Nodes (11): Actual, Affected Components, BUG-036 — Flaring panel invents a 56 % / 40 % / 4 % Routine / Non-Routine / Safety split for generic "flaring" records and shows 0 tCO₂e for every stream (and a 2.5 t/kNm³ proxy when CO₂e is 0), Evidence, Expected, Impact, Input, Location (+3 more)

### Community 426 - "BUG-004 — Intensity activity/division filter uses record-level columns that are NULL/inconsistent, so numerator and denominator are filtered differently (Upstream intensity blank, E&P intensity 0.0)"
Cohesion: 0.18
Nodes (11): Actual, Affected Components, BUG-004 — Intensity activity/division filter uses record-level columns that are NULL/inconsistent, so numerator and denominator are filtered differently (Upstream intensity blank, E&P intensity 0.0), Evidence, Expected, Impact, Input, Location (+3 more)

### Community 427 - "BUG-038 — Audit trail (/api/audit/, /api/audit/export) is not facility/region-scoped: a region-restricted superuser reads activity entries for every region's records"
Cohesion: 0.18
Nodes (11): Actual, Affected Components, BUG-038 — Audit trail (/api/audit/, /api/audit/export) is not facility/region-scoped: a region-restricted superuser reads activity entries for every region's records, Evidence, Expected, Impact, Input, Location (+3 more)

### Community 428 - "BUG-039 — Emission goals API ("+ Set Target") has no value validation: negative, year 1, and NaN goals are accepted; a NaN goal for the current year makes the main dashboard batch return 500"
Cohesion: 0.18
Nodes (11): Actual, Affected Components, BUG-039 — Emission goals API ("+ Set Target") has no value validation: negative, year 1, and NaN goals are accepted; a NaN goal for the current year makes the main dashboard batch return 500, Evidence, Expected, Impact, Input, Location (+3 more)

### Community 429 - "BUG-040 — Supply Chain filter is not applied to the emissions-by-source split: "Emissions by Source" donut and Detailed Breakdown rows show company-wide values (sources add up to 7× Scope 1)"
Cohesion: 0.18
Nodes (11): Actual, Affected Components, BUG-040 — Supply Chain filter is not applied to the emissions-by-source split: "Emissions by Source" donut and Detailed Breakdown rows show company-wide values (sources add up to 7× Scope 1), Evidence, Expected, Impact, Input, Location (+3 more)

### Community 430 - "BUG-041 — Dashboard "% GOAL" badge in the default All-years view divides the cumulative multi-year Scope 1+2 total by the single current-year goal (and ignores region/facility filters)"
Cohesion: 0.18
Nodes (11): Actual, Affected Components, BUG-041 — Dashboard "% GOAL" badge in the default All-years view divides the cumulative multi-year Scope 1+2 total by the single current-year goal (and ignores region/facility filters), Evidence, Expected, Impact, Input, Location (+3 more)

### Community 431 - "BUG-042 — Recalculating a Tier 2 (custom-factor) Scope 1 record drops the custom factor: emissions become 0 or silently switch to the catalog factor, while factor_source stays "custom""
Cohesion: 0.18
Nodes (11): Actual, Affected Components, BUG-042 — Recalculating a Tier 2 (custom-factor) Scope 1 record drops the custom factor: emissions become 0 or silently switch to the catalog factor, while factor_source stays "custom", Evidence, Expected, Impact, Input, Location (+3 more)

### Community 432 - "BUG-043 — Stored uncertainty has no range or unit validation: Scope 2/3 accept percent values, negatives, NaN and 1e6, and the Uncertainty dashboard shows ±3600 %"
Cohesion: 0.18
Nodes (11): Actual, Affected Components, BUG-043 — Stored uncertainty has no range or unit validation: Scope 2/3 accept percent values, negatives, NaN and 1e6, and the Uncertainty dashboard shows ±3600 %, Evidence, Expected, Impact, Input, Location (+3 more)

### Community 433 - "BUG-044 — /granular-intensities (Master Report "Multi-Metric Intensities") divides all-facility emissions by only the facilities with granular MMboe fields, and fabricates NGSI methane (0.05 %) and saleable production (85 %)"
Cohesion: 0.18
Nodes (11): Actual, Affected Components, BUG-044 — /granular-intensities (Master Report "Multi-Metric Intensities") divides all-facility emissions by only the facilities with granular MMboe fields, and fabricates NGSI methane (0.05 %) and saleable production (85 %), Evidence, Expected, Impact, Input, Location (+3 more)

### Community 434 - "BUG-045 — "Add Region" (create facility) form fails with HTTP 500 unless the optional Latitude/Longitude fields are filled"
Cohesion: 0.18
Nodes (11): Actual, Affected Components, BUG-045 — "Add Region" (create facility) form fails with HTTP 500 unless the optional Latitude/Longitude fields are filled, Evidence, Expected, Impact, Input, Location (+3 more)

### Community 435 - "BUG-047 — Tier 1 fugitive and equipment factors in "per hour" units are multiplied only by the source count (no operating hours): annual CH4 understated 8,760×, and Tier 1 disagrees with Tier 3 for the same factor"
Cohesion: 0.18
Nodes (11): Actual, Affected Components, BUG-047 — Tier 1 fugitive and equipment factors in "per hour" units are multiplied only by the source count (no operating hours): annual CH4 understated 8,760×, and Tier 1 disagrees with Tier 3 for the same factor, Evidence, Expected, Impact, Input, Location (+3 more)

### Community 436 - "BUG-005 — GWP-20 conversion in intensity-stats / intensity-trend hard-codes AR5 GWP-100 (28 / 265), so GWP-20 CO2e is wrong whenever the active standard is AR4 or AR6"
Cohesion: 0.18
Nodes (11): Actual, Affected Components, BUG-005 — GWP-20 conversion in intensity-stats / intensity-trend hard-codes AR5 GWP-100 (28 / 265), so GWP-20 CO2e is wrong whenever the active standard is AR4 or AR6, Evidence, Expected, Impact, Input, Location (+3 more)

### Community 437 - "BUG-052 — OGMP survey reconciliation status defaults to "Reconciled" whatever the computed variance; a +354 % discrepancy is stored and shown as Reconciled, and a zero bottom-up case is shown as "+0.0 %""
Cohesion: 0.18
Nodes (11): Actual, Affected Components, BUG-052 — OGMP survey reconciliation status defaults to "Reconciled" whatever the computed variance; a +354 % discrepancy is stored and shown as Reconciled, and a zero bottom-up case is shown as "+0.0 %", Evidence, Expected, Impact, Input, Location (+3 more)

### Community 438 - "BUG-054 — "Preview Pending Data" and the pending banner are inconsistent with the rest of the dashboard: the toggle changes only the KPIs (categorical/org breakdown and Scope 3 stay Verified-only), and the banner ignores the Supply Chain, Activity and Division filters and omits Scope 3"
Cohesion: 0.18
Nodes (11): Actual, Affected Components, BUG-054 — "Preview Pending Data" and the pending banner are inconsistent with the rest of the dashboard: the toggle changes only the KPIs (categorical/org breakdown and Scope 3 stay Verified-only), and the banner ignores the Supply Chain, Activity and Division filters and omits Scope 3, Evidence, Expected, Impact, Input, Location (+3 more)

### Community 439 - "BUG-055 — QA Dashboard "IPCC Tier 1 Uncertainty" reports 1σ as ±%, uses only the CO2 column, and includes Draft and Pending records, so it contradicts the Uncertainty page"
Cohesion: 0.18
Nodes (11): Actual, Affected Components, BUG-055 — QA Dashboard "IPCC Tier 1 Uncertainty" reports 1σ as ±%, uses only the CO2 column, and includes Draft and Pending records, so it contradicts the Uncertainty page, Evidence, Expected, Impact, Input, Location (+3 more)

### Community 440 - "BUG-056 — Custom factors used by Tier 2 records can be deleted: the reference check matches `fuel_type == factor name`, but UI records store the factor id, which SQLite then reuses for the next factor"
Cohesion: 0.18
Nodes (11): Actual, Affected Components, BUG-056 — Custom factors used by Tier 2 records can be deleted: the reference check matches `fuel_type == factor name`, but UI records store the factor id, which SQLite then reuses for the next factor, Evidence, Expected, Impact, Input, Location (+3 more)

### Community 441 - "BUG-057 — Bulk upload with "Overwrite Duplicates" enabled inserts every in-file duplicate row as a separate record (double counting)"
Cohesion: 0.18
Nodes (11): Actual, Affected Components, BUG-057 — Bulk upload with "Overwrite Duplicates" enabled inserts every in-file duplicate row as a separate record (double counting), Evidence, Expected, Impact, Input, Location (+3 more)

### Community 442 - "BUG-058 — Bulk-upload overwrite rewrites approved records without an audit trail and leaves them "Pending" but still marked approved"
Cohesion: 0.18
Nodes (11): Actual, Affected Components, BUG-058 — Bulk-upload overwrite rewrites approved records without an audit trail and leaves them "Pending" but still marked approved, Evidence, Expected, Impact, Input, Location (+3 more)

### Community 443 - "BUG-006 — Reports Excel/PDF exports drop the Division, Field, Method and Search filters shown on screen"
Cohesion: 0.18
Nodes (11): Actual, Affected Components, BUG-006 — Reports Excel/PDF exports drop the Division, Field, Method and Search filters shown on screen, Evidence, Expected, Impact, Input, Location (+3 more)

### Community 444 - "BUG-059 — SBTi target labelled "1.5°C" is not tied to its reduction rate (0.5 %/yr accepted and displayed as 1.5°C); arbitrary pathway strings and future base years accepted; main-dashboard banner hard-codes "SBTi 1.5°C Linear Target""
Cohesion: 0.18
Nodes (11): Actual, Affected Components, BUG-059 — SBTi target labelled "1.5°C" is not tied to its reduction rate (0.5 %/yr accepted and displayed as 1.5°C); arbitrary pathway strings and future base years accepted; main-dashboard banner hard-codes "SBTi 1.5°C Linear Target", Evidence, Expected, Impact, Input, Location (+3 more)

### Community 445 - "BUG-064 — Categorical Emissions Overview groups facilities by name instead of id: six distinct facilities are merged into one "Updated Facility" card (3.19 T t)"
Cohesion: 0.18
Nodes (11): Actual, Affected Components, BUG-064 — Categorical Emissions Overview groups facilities by name instead of id: six distinct facilities are merged into one "Updated Facility" card (3.19 T t), Evidence, Expected, Impact, Input, Location (+3 more)

### Community 446 - "BUG-065 — Custom factor names are not unique, yet bulk import resolves factors by name: the most recently created same-named factor is silently applied"
Cohesion: 0.18
Nodes (11): Actual, Affected Components, BUG-065 — Custom factor names are not unique, yet bulk import resolves factors by name: the most recently created same-named factor is silently applied, Evidence, Expected, Impact, Input, Location (+3 more)

### Community 447 - "BUG-066 — AGR form throughput units MMscfd / Mcf/day / m³/yr are ignored by the server (read as MMscf/yr): CO2 365× low, 2.7× high, or 28,317× high"
Cohesion: 0.18
Nodes (11): Actual, Affected Components, BUG-066 — AGR form throughput units MMscfd / Mcf/day / m³/yr are ignored by the server (read as MMscf/yr): CO2 365× low, 2.7× high, or 28,317× high, Evidence, Expected, Impact, Input, Location (+3 more)

### Community 448 - "BUG-068 — Purchased steam/heat (`indirect_steam`) and CHP allocation (`cogen_allocation`) are accepted as Scope 1 process types and added to Scope 1 totals (Scope 2 counted as Scope 1; CHP double counting)"
Cohesion: 0.18
Nodes (11): Actual, Affected Components, BUG-068 — Purchased steam/heat (`indirect_steam`) and CHP allocation (`cogen_allocation`) are accepted as Scope 1 process types and added to Scope 1 totals (Scope 2 counted as Scope 1; CHP double counting), Evidence, Expected, Impact, Input, Location (+3 more)

### Community 449 - "BUG-007 — Manual Scope 1 entry has no plausibility bound or QA flag: 9 test records (1e13 MMBtu gas, 1e15 t coal) make up about 99.99% of the snapshot's Scope 1 total (3.72e12 t Verified, 4.69e12 t Pending)"
Cohesion: 0.18
Nodes (11): Actual, Affected Components, BUG-007 — Manual Scope 1 entry has no plausibility bound or QA flag: 9 test records (1e13 MMBtu gas, 1e15 t coal) make up about 99.99% of the snapshot's Scope 1 total (3.72e12 t Verified, 4.69e12 t Pending), Evidence, Expected, Impact, Input, Location (+3 more)

### Community 450 - "BUG-072 — Pending-records banner ignores the GWP-20 toggle: it always shows GWP-100 tCO2e while every other dashboard figure switches to GWP-20"
Cohesion: 0.18
Nodes (11): Actual, Affected Components, BUG-072 — Pending-records banner ignores the GWP-20 toggle: it always shows GWP-100 tCO2e while every other dashboard figure switches to GWP-20, Evidence, Expected, Impact, Input, Location (+3 more)

### Community 451 - "BUG-073 — Scope 2 and Scope 3 create accept a missing or non-numeric year: one year-less Scope 2 record makes the main dashboard (summary/batch-all) return 500, and year-less Scope 3 is in the total but missing from by-year"
Cohesion: 0.18
Nodes (11): Actual, Affected Components, BUG-073 — Scope 2 and Scope 3 create accept a missing or non-numeric year: one year-less Scope 2 record makes the main dashboard (summary/batch-all) return 500, and year-less Scope 3 is in the total but missing from by-year, Evidence, Expected, Impact, Input, Location (+3 more)

### Community 452 - "BUG-075 — Sentinel-5P "Export to OGMP" stores a 1-hour CH4 mass as the survey's "estimated annual tCH4" (default operating_hours = 1): top-down understated 8,760× and reconciliation always flagged"
Cohesion: 0.18
Nodes (11): Actual, Affected Components, BUG-075 — Sentinel-5P "Export to OGMP" stores a 1-hour CH4 mass as the survey's "estimated annual tCH4" (default operating_hours = 1): top-down understated 8,760× and reconciliation always flagged, Evidence, Expected, Impact, Input, Location (+3 more)

### Community 453 - "BUG-077 — Dashboard "Export Executive Brief (PDF)" in the default All-Years view reports every year and every Pending record as "FISCAL YEAR 2026" / "Total verified records": PDF total 8.41 T tCO2e vs 3.72 T on the dashboard"
Cohesion: 0.18
Nodes (11): Actual, Affected Components, BUG-077 — Dashboard "Export Executive Brief (PDF)" in the default All-Years view reports every year and every Pending record as "FISCAL YEAR 2026" / "Total verified records": PDF total 8.41 T tCO2e vs 3.72 T on the dashboard, Evidence, Expected, Impact, Input, Location (+3 more)

### Community 454 - "BUG-008 — Inventory uncertainty shrinks by √N when the same emissions are split into N records (shared EF uncertainty treated as independent)"
Cohesion: 0.18
Nodes (11): Actual, Affected Components, BUG-008 — Inventory uncertainty shrinks by √N when the same emissions are split into N records (shared EF uncertainty treated as independent), Evidence, Expected, Impact, Input, Location (+3 more)

### Community 455 - "BUG-079 — OGMP reconciliation in the default "All years" view compares the AVERAGE of annual top-down surveys with the SUM of multi-year bottom-up CH4, so perfectly reconciled facilities are flagged (−80 %)"
Cohesion: 0.18
Nodes (11): Actual, Affected Components, BUG-079 — OGMP reconciliation in the default "All years" view compares the AVERAGE of annual top-down surveys with the SUM of multi-year bottom-up CH4, so perfectly reconciled facilities are flagged (−80 %), Evidence, Expected, Impact, Input, Location (+3 more)

### Community 456 - "BUG-080 — Two contradictory OGMP facility-level algorithms: /intensity-stats reports Level 5 (Gold Standard) where the canonical service (/ogmp-metrics, OGMP export) reports Level 4 for the same facility and year"
Cohesion: 0.18
Nodes (11): Actual, Affected Components, BUG-080 — Two contradictory OGMP facility-level algorithms: /intensity-stats reports Level 5 (Gold Standard) where the canonical service (/ogmp-metrics, OGMP export) reports Level 4 for the same facility and year, Evidence, Expected, Impact, Input, Location (+3 more)

### Community 457 - "BUG-081 — Scope 2/3 bulk import duplicate key is too coarse: separate meters and sub-categories in the same facility-month are rejected as "duplicates", or with Overwrite they replace a different existing record"
Cohesion: 0.18
Nodes (11): Actual, Affected Components, BUG-081 — Scope 2/3 bulk import duplicate key is too coarse: separate meters and sub-categories in the same facility-month are rejected as "duplicates", or with Overwrite they replace a different existing record, Evidence, Expected, Impact, Input, Location (+3 more)

### Community 458 - "BUG-082 — Scope 1 "Live Equation Inspector" states "GWP Standard: IPCC AR6 (CH₄:28, N₂O:265)" — hard-coded, AR5 values mislabelled as AR6, ignores the org GWP setting"
Cohesion: 0.18
Nodes (11): Actual, Affected Components, BUG-082 — Scope 1 "Live Equation Inspector" states "GWP Standard: IPCC AR6 (CH₄:28, N₂O:265)" — hard-coded, AR5 values mislabelled as AR6, ignores the org GWP setting, Evidence, Expected, Impact, Input, Location (+3 more)

### Community 459 - "BUG-084 — QA/QC Dashboard shows "Zero Anomalies Detected… The inventory is fully verified and audit-compliant" with 149 Pending records and 11 records more than 10^6 × the median; the anomaly queue only lists a stored `qa_flag`, which is never computed for existing data"
Cohesion: 0.18
Nodes (11): Actual, Affected Components, BUG-084 — QA/QC Dashboard shows "Zero Anomalies Detected… The inventory is fully verified and audit-compliant" with 149 Pending records and 11 records more than 10^6 × the median; the anomaly queue only lists a stored `qa_flag`, which is never computed for existing data, Evidence, Expected, Impact, Input, Location (+3 more)

### Community 460 - "BUG-085 — Scope 2/3 bulk import silently books rows with a blank or non-ISO date to January 2024, and stores a blank Scope 3 category as "Category ""
Cohesion: 0.18
Nodes (11): Actual, Affected Components, BUG-085 — Scope 2/3 bulk import silently books rows with a blank or non-ISO date to January 2024, and stores a blank Scope 3 category as "Category ", Evidence, Expected, Impact, Input, Location (+3 more)

### Community 461 - "BUG-086 — Methane loss-rate segment classification differs between the KPI cards, the trend chart and the server: "Downstream / Processing" counts as Midstream in the trend, and "Upstream / Extraction" is dropped from the Upstream KPI"
Cohesion: 0.18
Nodes (11): Actual, Affected Components, BUG-086 — Methane loss-rate segment classification differs between the KPI cards, the trend chart and the server: "Downstream / Processing" counts as Midstream in the trend, and "Upstream / Extraction" is dropped from the Upstream KPI, Evidence, Expected, Impact, Input, Location (+3 more)

### Community 462 - "BUG-009 — Deleting a facility that has any OGMP level-upgrade log fails with 500 (FK violation) and leaks raw SQL"
Cohesion: 0.18
Nodes (11): Actual, Affected Components, BUG-009 — Deleting a facility that has any OGMP level-upgrade log fails with 500 (FK violation) and leaks raw SQL, Evidence, Expected, Impact, Input, Location (+3 more)

### Community 463 - "BUG-088 — Facilities with CH4 emissions but no gas production get methane_loss_rate_pct = 0 and ogmp_target_status "Compliant""
Cohesion: 0.18
Nodes (11): Actual, Affected Components, BUG-088 — Facilities with CH4 emissions but no gas production get methane_loss_rate_pct = 0 and ogmp_target_status "Compliant", Evidence, Expected, Impact, Input, Location (+3 more)

### Community 464 - "BUG-090 — Dehydrator form sends "Contactor Pressure" as `dehy_pressure`, but the server reads `dehy_press`: user pressure silently ignored, 800 psig default always used (AGR "routed to flare"/"flash gas recycled" checkboxes also unread)"
Cohesion: 0.18
Nodes (11): Actual, Affected Components, BUG-090 — Dehydrator form sends "Contactor Pressure" as `dehy_pressure`, but the server reads `dehy_press`: user pressure silently ignored, 800 psig default always used (AGR "routed to flare"/"flash gas recycled" checkboxes also unread), Evidence, Expected, Impact, Input, Location (+3 more)

### Community 465 - "BUG-092 — Maker-checker outcome is invisible to the maker: reject/approve send no notification, the Scope 1 list shows Rejected/Pending rows exactly like Verified ones, and the reject dialog claims the record is "permanently deleted" although it is kept as Rejected"
Cohesion: 0.18
Nodes (11): Actual, Affected Components, BUG-092 — Maker-checker outcome is invisible to the maker: reject/approve send no notification, the Scope 1 list shows Rejected/Pending rows exactly like Verified ones, and the reject dialog claims the record is "permanently deleted" although it is kept as Rejected, Evidence, Expected, Impact, Input, Location (+3 more)

### Community 466 - "BUG-094 — "Net Emissions" KPI subtracts company-wide mitigation whatever the Activity/Division filter (Steel & Iron view: Net = −1,027,393 t) and counts "Planned" projects as achieved reductions"
Cohesion: 0.18
Nodes (11): Actual, Affected Components, BUG-094 — "Net Emissions" KPI subtracts company-wide mitigation whatever the Activity/Division filter (Steel & Iron view: Net = −1,027,393 t) and counts "Planned" projects as achieved reductions, Evidence, Expected, Impact, Input, Location (+3 more)

### Community 467 - "BUG-095 — Scope 1 "Recent Activity": Export CSV exports only the 10 rows of the current page, and the Year/Process filter options are built from that page only"
Cohesion: 0.18
Nodes (11): Actual, Affected Components, BUG-095 — Scope 1 "Recent Activity": Export CSV exports only the 10 rows of the current page, and the Year/Process filter options are built from that page only, Evidence, Expected, Impact, Input, Location (+3 more)

### Community 468 - "BUG-096 — Scope 2 form: switching Source Type to Steam/Heat or CHP leaves the hidden unit at "kWh" — dropdown shows "Select..." but the request sends unit "kWh" (1000 "MMBtu" of steam booked as 3.41 MMBtu)"
Cohesion: 0.18
Nodes (11): Actual, Affected Components, BUG-096 — Scope 2 form: switching Source Type to Steam/Heat or CHP leaves the hidden unit at "kWh" — dropdown shows "Select..." but the request sends unit "kWh" (1000 "MMBtu" of steam booked as 3.41 MMBtu), Evidence, Expected, Impact, Input, Location (+3 more)

### Community 469 - "BUG-010 — Deleting a user who created production data, SBTi targets or OGMP level logs fails with 500 (FK cleanup list incomplete)"
Cohesion: 0.18
Nodes (11): Actual, Affected Components, BUG-010 — Deleting a user who created production data, SBTi targets or OGMP level logs fails with 500 (FK cleanup list incomplete), Evidence, Expected, Impact, Input, Location (+3 more)

### Community 470 - "BUG-097 — CHP allocation form labels Power Output "MWh" but the server uses the number as MMBtu: heat share (and Scope 2 tCO2e) overstated ~2.7× with WRI efficiency method"
Cohesion: 0.18
Nodes (11): Actual, Affected Components, BUG-097 — CHP allocation form labels Power Output "MWh" but the server uses the number as MMBtu: heat share (and Scope 2 tCO2e) overstated ~2.7× with WRI efficiency method, Evidence, Expected, Impact, Input, Location (+3 more)

### Community 471 - "BUG-098 — Emission Calculation Result panel rounds gas masses to 3 decimals of a tonne: non-zero CH4/N2O shown as "0.00 tonnes""
Cohesion: 0.18
Nodes (11): Actual, Affected Components, BUG-098 — Emission Calculation Result panel rounds gas masses to 3 decimals of a tonne: non-zero CH4/N2O shown as "0.00 tonnes", Evidence, Expected, Impact, Input, Location (+3 more)

### Community 472 - "BUG-105 — Manage Data and Reference Data swallow API load errors and show them as empty data ("No production record found", empty factor catalog)"
Cohesion: 0.18
Nodes (11): Actual, Affected Components, BUG-105 — Manage Data and Reference Data swallow API load errors and show them as empty data ("No production record found", empty factor catalog), Evidence, Expected, Impact, Input, Location (+3 more)

### Community 473 - "BUG-107 — CustomDropdown is not keyboard-operable and form inputs have no programmatic labels: Region, Process Type, Emission Factor and Unit cannot be set without a mouse"
Cohesion: 0.18
Nodes (11): Actual, Affected Components, BUG-107 — CustomDropdown is not keyboard-operable and form inputs have no programmatic labels: Region, Process Type, Emission Factor and Unit cannot be set without a mouse, Evidence, Expected, Impact, Input, Location (+3 more)

### Community 474 - "BUG-011 — Well-completion "Rate × Duration" method divides the Mcf/hr rate by 24 (treats it as Mcf/day): CH4 understated 24×"
Cohesion: 0.18
Nodes (11): Actual, Affected Components, BUG-011 — Well-completion "Rate × Duration" method divides the Mcf/hr rate by 24 (treats it as Mcf/day): CH4 understated 24×, Evidence, Expected, Impact, Input, Location (+3 more)

### Community 475 - "BUG-108 — Scope 1 entry form does not reflow at phone width (390 px): Field input, Tier selector and factor picker are clipped off-screen"
Cohesion: 0.18
Nodes (11): Actual, Affected Components, BUG-108 — Scope 1 entry form does not reflow at phone width (390 px): Field input, Tier selector and factor picker are clipped off-screen, Evidence, Expected, Impact, Input, Location (+3 more)

### Community 476 - "BUG-112 — Custom emission factor with every factor field blank is saved (CO2/CH4/N2O = 0) and Tier 2 records that use it are stored with 0 tCO2e and no warning"
Cohesion: 0.18
Nodes (11): Actual, Affected Components, BUG-112 — Custom emission factor with every factor field blank is saved (CO2/CH4/N2O = 0) and Tier 2 records that use it are stored with 0 tCO2e and no warning, Evidence, Expected, Impact, Input, Location (+3 more)

### Community 477 - "BUG-113 — Reports "PDF Report" prints every unit and gas name with a missing-glyph box: "tCO■e", "CO■", "CH■", "N■O""
Cohesion: 0.18
Nodes (11): Actual, Affected Components, BUG-113 — Reports "PDF Report" prints every unit and gas name with a missing-glyph box: "tCO■e", "CO■", "CH■", "N■O", Evidence, Expected, Impact, Input, Location (+3 more)

### Community 478 - "BUG-115 — Manage Data forms discard the server's validation message and show a generic "Failed to …" toast (negative production, negative factor, facility 500, etc.)"
Cohesion: 0.18
Nodes (11): Actual, Affected Components, BUG-115 — Manage Data forms discard the server's validation message and show a generic "Failed to …" toast (negative production, negative factor, facility 500, etc.), Evidence, Expected, Impact, Input, Location (+3 more)

### Community 479 - "BUG-012 — Well-completion Tier 3 uses `amount` as both the flowback volume and the event count (volume squared), and ignores rate × duration when the method dropdown is left at its default"
Cohesion: 0.18
Nodes (11): Actual, Affected Components, BUG-012 — Well-completion Tier 3 uses `amount` as both the flowback volume and the event count (volume squared), and ignores rate × duration when the method dropdown is left at its default, Evidence, Expected, Impact, Input, Location (+3 more)

### Community 480 - "BUG-013 — AR5 20-year GWPs are wrong (CH4 82.5 instead of 84, N2O 268 instead of 264); AR6 pairs the fossil CH4 GWP-20 with the non-fossil-weighted GWP-100"
Cohesion: 0.18
Nodes (11): Actual, Affected Components, BUG-013 — AR5 20-year GWPs are wrong (CH4 82.5 instead of 84, N2O 268 instead of 264); AR6 pairs the fossil CH4 GWP-20 with the non-fossil-weighted GWP-100, Evidence, Expected, Impact, Input, Location (+3 more)

### Community 481 - "BUG-014 — SBTi progress KPI uses the current, incomplete year (and any future year) as the "current" year, so the dashboard reports ~95-99% reduction and ON TRACK"
Cohesion: 0.18
Nodes (11): Actual, Affected Components, BUG-014 — SBTi progress KPI uses the current, incomplete year (and any future year) as the "current" year, so the dashboard reports ~95-99% reduction and ON TRACK, Evidence, Expected, Impact, Input, Location (+3 more)

### Community 482 - "BUG-015 — 43 Tier 1 factors offered in the Scope 1 UI do not exist in the server catalog; records save with HTTP 201 and 0 emissions"
Cohesion: 0.18
Nodes (11): Actual, Affected Components, BUG-015 — 43 Tier 1 factors offered in the Scope 1 UI do not exist in the server catalog; records save with HTTP 201 and 0 emissions, Evidence, Expected, Impact, Input, Location (+3 more)

### Community 483 - "BUG-016 — Alembic migration chain is unusable: `flask db upgrade` fails on both the existing DB and a fresh DB"
Cohesion: 0.18
Nodes (11): Actual, Affected Components, BUG-016 — Alembic migration chain is unusable: `flask db upgrade` fails on both the existing DB and a fresh DB, Evidence, Expected, Impact, Input, Location (+3 more)

### Community 484 - "BUG-017 — Intensity with year="all" (default view) pairs each facility's emissions from every year with production from other years; KPI mixes periods"
Cohesion: 0.18
Nodes (11): Actual, Affected Components, BUG-017 — Intensity with year="all" (default view) pairs each facility's emissions from every year with production from other years; KPI mixes periods, Evidence, Expected, Impact, Input, Location (+3 more)

### Community 485 - "BUG-002 — Reports "2025 Master Report (PDF)" button sends facility_id=[object Object]; facility selection ignored"
Cohesion: 0.18
Nodes (11): Actual, Affected Components, BUG-002 — Reports "2025 Master Report (PDF)" button sends facility_id=[object Object]; facility selection ignored, Evidence, Expected, Impact, Input, Location (+3 more)

### Community 486 - "BUG-018 — Uncertainty dashboard applies max(u_CO2, u_CH4, u_N2O) to each record's total CO2e instead of CO2e-weighting the per-gas uncertainties"
Cohesion: 0.18
Nodes (11): Actual, Affected Components, BUG-018 — Uncertainty dashboard applies max(u_CO2, u_CH4, u_N2O) to each record's total CO2e instead of CO2e-weighting the per-gas uncertainties, Evidence, Expected, Impact, Input, Location (+3 more)

### Community 487 - "BUG-020 — /api/reports/master-annual-report serves full annual GHG report PDFs to any logged-in role (incl. it_admin and out-of-region users) and returns a static, pre-generated file regardless of facility_id"
Cohesion: 0.18
Nodes (11): Actual, Affected Components, BUG-020 — /api/reports/master-annual-report serves full annual GHG report PDFs to any logged-in role (incl. it_admin and out-of-region users) and returns a static, pre-generated file regardless of facility_id, Evidence, Expected, Impact, Input, Location (+3 more)

### Community 488 - "BUG-XXX — Generic factor math ignores the 10³ / 10⁶ multiplier in factor denominators: offshore gas fugitives 1,000,000× and refinery fuel-gas fugitives 1,000× overstated"
Cohesion: 0.18
Nodes (10): Actual, Affected Components, BUG-XXX — Generic factor math ignores the 10³ / 10⁶ multiplier in factor denominators: offshore gas fugitives 1,000,000× and refinery fuel-gas fugitives 1,000× overstated, Evidence, Expected, Impact, Location, Recommended Fix (+2 more)

### Community 489 - "BUG-XXX — Energy activity units kWh / MJ / Btu with a kg/MMBtu factor are treated as scf of gas (× 1020 Btu/scf): 1000 kWh of natural gas is 3.3× too low, MJ 7.6 % too high"
Cohesion: 0.18
Nodes (10): Actual, Affected Components, BUG-XXX — Energy activity units kWh / MJ / Btu with a kg/MMBtu factor are treated as scf of gas (× 1020 Btu/scf): 1000 kWh of natural gas is 3.3× too low, MJ 7.6 % too high, Evidence, Expected, Impact, Location, Recommended Fix (+2 more)

### Community 490 - "BUG-XXX — Tier 3 fugitive calculators misread catalog factor units: "CH₄" (Unicode subscript) is not recognised as methane (×0.85 applied), and ComponentFugitiveCalculator treats tonne/hr factors as kg/hr (1000× too low)"
Cohesion: 0.18
Nodes (10): Actual, Affected Components, BUG-XXX — Tier 3 fugitive calculators misread catalog factor units: "CH₄" (Unicode subscript) is not recognised as methane (×0.85 applied), and ComponentFugitiveCalculator treats tonne/hr factors as kg/hr (1000× too low), Evidence, Expected, Impact, Location, Recommended Fix (+2 more)

### Community 491 - "BUG-XXX — Negative activity amounts are accepted for process types that are not in the dispatcher (e.g. "loading") and saved as negative emissions"
Cohesion: 0.18
Nodes (10): Actual, Affected Components, BUG-XXX — Negative activity amounts are accepted for process types that are not in the dispatcher (e.g. "loading") and saved as negative emissions, Evidence, Expected, Impact, Location, Recommended Fix (+2 more)

### Community 492 - "BUG-XXX — Uncertainty display inconsistencies: EmissionResult shows the ±1σ (68 %) band as the "Confidence Interval", Scope 2/3 tables use k=1.96 while everything else uses k=2, and the Uncertainty page badge thresholds contradict its legend"
Cohesion: 0.18
Nodes (10): Actual, Affected Components, BUG-XXX — Uncertainty display inconsistencies: EmissionResult shows the ±1σ (68 %) band as the "Confidence Interval", Scope 2/3 tables use k=1.96 while everything else uses k=2, and the Uncertainty page badge thresholds contradict its legend, Evidence, Expected, Impact, Location, Recommended Fix (+2 more)

### Community 493 - "BUG-XXX — CAP (air-pollutant) emissions bypass maker-checker: POST /api/cap/emissions stores records as "Verified" by default (client-controlled status) for role user; negative mass/concentration accepted"
Cohesion: 0.18
Nodes (10): Actual, Affected Components, BUG-XXX — CAP (air-pollutant) emissions bypass maker-checker: POST /api/cap/emissions stores records as "Verified" by default (client-controlled status) for role user; negative mass/concentration accepted, Evidence, Expected, Impact, Location, Recommended Fix (+2 more)

### Community 494 - "BUG-XXX — Region-restricted superuser can re-region its own facility (PUT /api/facilities/<id>), pushing the facility and all its emissions into another region's scope and out of its own"
Cohesion: 0.18
Nodes (10): Actual, Affected Components, BUG-XXX — Region-restricted superuser can re-region its own facility (PUT /api/facilities/<id>), pushing the facility and all its emissions into another region's scope and out of its own, Evidence, Expected, Impact, Location, Recommended Fix (+2 more)

### Community 495 - "BUG-XXX — Bulk-upload job status and error CSV have no owner check: any logged-in account (incl. it_admin) can read another user's job rows; absolute server temp path is disclosed"
Cohesion: 0.18
Nodes (10): Actual, Affected Components, BUG-XXX — Bulk-upload job status and error CSV have no owner check: any logged-in account (incl. it_admin) can read another user's job rows; absolute server temp path is disclosed, Evidence, Expected, Impact, Location, Recommended Fix (+2 more)

### Community 496 - "BUG-XXX — Maker-checker bypass through edit and delete: a superuser can approve a record they just edited, silently re-date/re-assign Verified records, and a user can hard-delete their own Verified records"
Cohesion: 0.18
Nodes (10): Actual, Affected Components, BUG-XXX — Maker-checker bypass through edit and delete: a superuser can approve a record they just edited, silently re-date/re-assign Verified records, and a user can hard-delete their own Verified records, Evidence, Expected, Impact, Location, Recommended Fix (+2 more)

### Community 497 - "BUG-XXX — Activity-data write endpoints accept "NaN" / "1e999" (±Infinity): a Scope 3 record with activity_data=Infinity makes /dashboard/batch-all, /scope3/summary and /api/scope3 emit invalid JSON ("Infinity")"
Cohesion: 0.18
Nodes (10): Actual, Affected Components, BUG-XXX — Activity-data write endpoints accept "NaN" / "1e999" (±Infinity): a Scope 3 record with activity_data=Infinity makes /dashboard/batch-all, /scope3/summary and /api/scope3 emit invalid JSON ("Infinity"), Evidence, Expected, Impact, Location, Recommended Fix (+2 more)

### Community 498 - "BUG-XXX — Approve/reject endpoints are not concurrency-safe: two simultaneous approvals of the same record both return 200 (duplicate audit entries; approve+reject race ends in an arbitrary final state)"
Cohesion: 0.18
Nodes (10): Actual, Affected Components, BUG-XXX — Approve/reject endpoints are not concurrency-safe: two simultaneous approvals of the same record both return 200 (duplicate audit entries; approve+reject race ends in an arbitrary final state), Evidence, Expected, Impact, Location, Recommended Fix (+2 more)

### Community 499 - "BUG-XXX — POST /api/emissions/reject/<id> has no status check: a superuser can flip an admin-Verified record to Rejected (removing it from all totals) and overwrite its approver"
Cohesion: 0.18
Nodes (10): Actual, Affected Components, BUG-XXX — POST /api/emissions/reject/<id> has no status check: a superuser can flip an admin-Verified record to Rejected (removing it from all totals) and overwrite its approver, Evidence, Expected, Impact, Location, Recommended Fix (+2 more)

### Community 500 - "BUG-XXX — Scope 2 manual entries and Scope 2 bulk imports by a superuser are auto-Verified, while Scope 1 and Scope 3 require admin approval (inconsistent maker-checker)"
Cohesion: 0.18
Nodes (10): Actual, Affected Components, BUG-XXX — Scope 2 manual entries and Scope 2 bulk imports by a superuser are auto-Verified, while Scope 1 and Scope 3 require admin approval (inconsistent maker-checker), Evidence, Expected, Impact, Location, Recommended Fix (+2 more)

### Community 501 - "Expanded Emissions MAP & Refined Data Entry"
Cohesion: 0.18
Nodes (10): 1. Comprehensive Regional Map, 2. Refined Data Entry Flow, 3. Map Integration via Data Entry, 4. Bulk Data Import & Auto-Calculation, Automated Calculations, Bulk Import Modal, Expanded Emissions MAP & Refined Data Entry, Field Reordering (+2 more)

### Community 502 - "Tasks"
Cohesion: 0.18
Nodes (10): Overview, [/] Phase 1: Quick Wins (High Impact, Low Effort), [ ] Phase 2: Real Data Integration, [ ] Phase 3: Financial Analysis, [ ] Phase 4: Advanced Modeling, [ ] Phase 5: Energy Storage, [ ] Phase 6: Advanced Features, [ ] Phase 7: Enhanced UX (+2 more)

### Community 503 - "Proposed Changes"
Cohesion: 0.18
Nodes (10): 1. New Directory Structure (Zero-Public), 2. File Relocations, 3. [MODIFY] [server.js](file:///c:/Users/samsung/Desktop/ghg%20old/server.js), 4. [MODIFY] [seed_script.js](file:///c:/Users/samsung/Desktop/ghg%20old/seed_script.js), 5. [MODIFY] All HTML Files, Automated Tests, Manual Verification, Project Reorganization & Root Entry Plan (+2 more)

### Community 504 - "[Frontend Optimizations]"
Cohesion: 0.18
Nodes (10): Automated Tests, [Frontend Optimizations], Manual Verification, [MODIFY] [notification-logic.js](file:///c:/Users/samsung/Desktop/h/public/notification-logic.js), [MODIFY] [reports-logic.js](file:///c:/Users/samsung/Desktop/h/public/reports-logic.js), [MODIFY] [server.js](file:///c:/Users/samsung/Desktop/h/server.js), Performance Optimization Plan, Proposed Changes (+2 more)

### Community 505 - "Comprehensive System Audit Report"
Cohesion: 0.18
Nodes (10): 1. Calculation Audit (Status: ✅ Verified & Patched), 2. Security Audit (Status: 🔴 Critical Failures), 3. Data Integrity Audit (Status: 🟠 High Risk), 4. Compliance Audit (Status: 🟡 Medium Risk), 5. Code Quality Audit (Status: 🟡 Needs Improvement), 6. IT/Infrastructure Audit (Status: 🟡 Medium Risk), 7. Architecture Review (Status: 🟡 Medium Risk), 8. UI and UX Audit (Status: 🟡 Needs Polish) (+2 more)

### Community 506 - "📸 Photorealistic 3D Rendering Upgrade"
Cohesion: 0.18
Nodes (10): 1. Detailed Module Geometry (3-Layer System), 2. Photorealistic Materials (PBR-like), 3. Professional Color Palette, 4. Cinematic Camera & Environment, 💰 Commercial Value, 🔥 New Visual Features, 📸 Photorealistic 3D Rendering Upgrade, ✅ Professional-Grade Visualization (+2 more)

### Community 507 - "2. Detailed Methodological Analysis by Subsystem"
Cohesion: 0.18
Nodes (10): 1. Master Regulatory Alignment Matrix, 2.1 Flaring & Stoichiometric Partitioning (Decision D-01), 2.2 Indirect Steam Net Efficiency (Decision D-03), 2.3 Top-Down OGMP Survey Reconciliation (Decision D-02), 2.4 Scope 3 Spend vs Physical Activity, 2. Detailed Methodological Analysis by Subsystem, 3.1 Global Warming Potentials, 3.2 Standard Gas Temperature and Pressure (+2 more)

### Community 508 - "test_qaqc_diagnostics.py"
Cohesion: 0.14
Nodes (14): admin_user(), client(), fixture, Test suite for /api/qaqc/dashboard unified diagnostics & QA/QC endpoint.…, Verify that 'all' status excludes rejected records, and 'rejected' status…, Verify that all diagnostic action URLs route to /manage-data and provide sample…, Unauthenticated access must be rejected., Admin user receives unified uncertainty, diagnostics, and anomaly queue data. (+6 more)

### Community 509 - "TestTier1DrillingMud"
Cohesion: 0.18
Nodes (5): Mud Degassing Tier 1 (API Table 6-3 default): wells = 10 wells EF = 0.0524 t…, Water-based mud uses API Onshore EF=0.0458 t CH4/day., Oil-based mud uses API Onshore EF=0.0103 t CH4/day., Tier 2+ scales by X_ch4 / 0.8385., TestTier1DrillingMud

### Community 510 - "BUG-053 — CAP (air-pollutant) emissions bypass maker-checker: POST /api/cap/emissions stores records as "Verified" by default (client-controlled status) for role user; negative mass/concentration accepted"
Cohesion: 0.20
Nodes (10): Actual, Affected Components, BUG-053 — CAP (air-pollutant) emissions bypass maker-checker: POST /api/cap/emissions stores records as "Verified" by default (client-controlled status) for role user; negative mass/concentration accepted, Evidence, Expected, Impact, Location, Recommended Fix (+2 more)

### Community 511 - "Core Principles"
Cohesion: 0.18
Nodes (10): Core Principles, Governance, [PRINCIPLE_1_NAME], [PRINCIPLE_2_NAME], [PRINCIPLE_3_NAME], [PRINCIPLE_4_NAME], [PRINCIPLE_5_NAME], [PROJECT_NAME] Constitution (+2 more)

### Community 512 - "Core Principles"
Cohesion: 0.18
Nodes (10): Core Principles, Governance, [PRINCIPLE_1_NAME], [PRINCIPLE_2_NAME], [PRINCIPLE_3_NAME], [PRINCIPLE_4_NAME], [PRINCIPLE_5_NAME], [PROJECT_NAME] Constitution (+2 more)

### Community 513 - "Core Principles"
Cohesion: 0.18
Nodes (10): Core Principles, Governance, [PRINCIPLE_1_NAME], [PRINCIPLE_2_NAME], [PRINCIPLE_3_NAME], [PRINCIPLE_4_NAME], [PRINCIPLE_5_NAME], [PROJECT_NAME] Constitution (+2 more)

### Community 514 - "Core Principles"
Cohesion: 0.18
Nodes (10): Core Principles, Governance, [PRINCIPLE_1_NAME], [PRINCIPLE_2_NAME], [PRINCIPLE_3_NAME], [PRINCIPLE_4_NAME], [PRINCIPLE_5_NAME], [PROJECT_NAME] Constitution (+2 more)

### Community 515 - "BUG-048 — Tier 3 fugitive calculators misread catalog factor units: "CH₄" (Unicode subscript) is not recognised as methane (×0.85 applied), and ComponentFugitiveCalculator treats tonne/hr factors as kg/hr (1000× too low)"
Cohesion: 0.20
Nodes (10): Actual, Affected Components, BUG-048 — Tier 3 fugitive calculators misread catalog factor units: "CH₄" (Unicode subscript) is not recognised as methane (×0.85 applied), and ComponentFugitiveCalculator treats tonne/hr factors as kg/hr (1000× too low), Evidence, Expected, Impact, Location, Recommended Fix (+2 more)

### Community 516 - "BUG-049 — Generic factor math ignores the 10³ / 10⁶ multiplier in factor denominators: offshore gas fugitives 1,000,000× and refinery fuel-gas fugitives 1,000× overstated"
Cohesion: 0.20
Nodes (10): Actual, Affected Components, BUG-049 — Generic factor math ignores the 10³ / 10⁶ multiplier in factor denominators: offshore gas fugitives 1,000,000× and refinery fuel-gas fugitives 1,000× overstated, Evidence, Expected, Impact, Location, Recommended Fix (+2 more)

### Community 517 - "TestEdgeCases"
Cohesion: 0.20
Nodes (5): Zero quantity should produce zero emissions without crash., Negative quantity must raise ValueError., 1 MMscf = 1,000,000 scf — result should match 1M scf calculation., If GOR=0 and EF=0, result should be zero (no flash gas)., TestEdgeCases

### Community 518 - "BUG-051 — Energy activity units kWh / MJ / Btu with a kg/MMBtu factor are treated as scf of gas (× 1020 Btu/scf): 1000 kWh of natural gas is 3.3× too low, MJ 7.6 % too high"
Cohesion: 0.20
Nodes (10): Actual, Affected Components, BUG-051 — Energy activity units kWh / MJ / Btu with a kg/MMBtu factor are treated as scf of gas (× 1020 Btu/scf): 1000 kWh of natural gas is 3.3× too low, MJ 7.6 % too high, Evidence, Expected, Impact, Location, Recommended Fix (+2 more)

### Community 519 - "TestIntermediateValues"
Cohesion: 0.20
Nodes (6): T3 combustion: CO2 volume = gas_vol * C_moles * eta_c vol=1000 m3,…, Flaring: verify CO2 and CH4 are calculated from DIFFERENT efficiency factors.…, AGR: verify the unit conversion chain: MMscf → scf → diff_co2 → co2_scf →…, Validates intermediate calculation steps (not just final CO2e)., T3 combustion: verify total_carbon_moles intermediate. c1=0.90, c2=0.05,…, TestIntermediateValues

### Community 520 - "BUG-060 — Scope 2 manual entries and Scope 2 bulk imports by a superuser are auto-Verified, while Scope 1 and Scope 3 require admin approval (inconsistent maker-checker)"
Cohesion: 0.20
Nodes (10): Actual, Affected Components, BUG-060 — Scope 2 manual entries and Scope 2 bulk imports by a superuser are auto-Verified, while Scope 1 and Scope 3 require admin approval (inconsistent maker-checker), Evidence, Expected, Impact, Location, Recommended Fix (+2 more)

### Community 521 - "QADashboard.jsx"
Cohesion: 0.16
Nodes (4): Diagnostics, QADashboard, ErrorBoundary, QADashboard()

### Community 522 - "BUG-067 — Maker-checker bypass through edit and delete: a superuser can approve a record they just edited, silently re-date/re-assign Verified records, and a user can hard-delete their own Verified records"
Cohesion: 0.20
Nodes (10): Actual, Affected Components, BUG-067 — Maker-checker bypass through edit and delete: a superuser can approve a record they just edited, silently re-date/re-assign Verified records, and a user can hard-delete their own Verified records, Evidence, Expected, Impact, Location, Recommended Fix (+2 more)

### Community 523 - ".get_token"
Cohesion: 0.28
Nodes (5): Any, Retrieves a valid JWT access token from Copernicus CDSE with caching., Returns tile layer configuration, color ramps, and metadata for Leaflet., Queries Copernicus STAC/OData API for real Sentinel-5P methane data around…, Tests authentication against Copernicus Data Space Ecosystem Keycloak endpoint.…

### Community 524 - "BUG-076 — Bulk-upload job status and error CSV have no owner check: any logged-in account (incl. it_admin) can read another user's job rows; absolute server temp path is disclosed"
Cohesion: 0.20
Nodes (10): Actual, Affected Components, BUG-076 — Bulk-upload job status and error CSV have no owner check: any logged-in account (incl. it_admin) can read another user's job rows; absolute server temp path is disclosed, Evidence, Expected, Impact, Location, Recommended Fix (+2 more)

### Community 525 - "BUG-083 — Activity-data write endpoints accept "NaN" / "1e999" (±Infinity): a Scope 3 record with activity_data=Infinity makes /dashboard/batch-all, /scope3/summary and /api/scope3 emit invalid JSON ("Infinity")"
Cohesion: 0.20
Nodes (10): Actual, Affected Components, BUG-083 — Activity-data write endpoints accept "NaN" / "1e999" (±Infinity): a Scope 3 record with activity_data=Infinity makes /dashboard/batch-all, /scope3/summary and /api/scope3 emit invalid JSON ("Infinity"), Evidence, Expected, Impact, Location, Recommended Fix (+2 more)

### Community 526 - "BUG-093 — Region-restricted superuser can re-region its own facility (PUT /api/facilities/<id>), pushing the facility and all its emissions into another region's scope and out of its own"
Cohesion: 0.20
Nodes (10): Actual, Affected Components, BUG-093 — Region-restricted superuser can re-region its own facility (PUT /api/facilities/<id>), pushing the facility and all its emissions into another region's scope and out of its own, Evidence, Expected, Impact, Location, Recommended Fix (+2 more)

### Community 527 - "BUG-XXX — Tier 2 custom factors whose unit is not "kg/<unit>" are misapplied (Manage Data form stores a bare activity unit): tonne factors ×1000 (×10⁶ with kg activity), no volume/mass conversion at all; unknown units such as kg/TJ or kg/GJ are applied 1:1"
Cohesion: 0.20
Nodes (9): Affected Components, BUG-XXX — Tier 2 custom factors whose unit is not "kg/<unit>" are misapplied (Manage Data form stores a bare activity unit): tonne factors ×1000 (×10⁶ with kg activity), no volume/mass conversion at all; unknown units such as kg/TJ or kg/GJ are applied 1:1, Evidence, Impact, Input / Expected / Actual (t CO2), Location, Recommended Fix, Reproduction (+1 more)

### Community 528 - "BUG-XXX — Malformed input on create endpoints returns HTTP 500/409 with raw exception and SQL text (≈40 handlers return `str(e)`)"
Cohesion: 0.20
Nodes (9): Actual, Affected Components, BUG-XXX — Malformed input on create endpoints returns HTTP 500/409 with raw exception and SQL text (≈40 handlers return `str(e)`), Expected, Impact, Location, Recommended Fix, Reproduction (+1 more)

### Community 529 - "Key Accomplishments"
Cohesion: 0.20
Nodes (9): 1. Backend Infrastructure Upgrades, 2. Modernized Profile Management, 3. Integrated Dashboard Experience, Backend Schema, Key Accomplishments, UI Consistency, Verification Results, Version Control (+1 more)

### Community 530 - "1. Logic Audit & Bug Hunt"
Cohesion: 0.20
Nodes (9): 1. Logic Audit & Bug Hunt, 2. Calculation Verification, 3. Proposed Action Plan, [BUG] Major Unit Inconsistency, [BUG] Methane Intensity Labeling, [BUG] Missing Backend Filters, Carbon Intensity Dashboard - Deep Analysis, Carbon Intensity Dashboard - Deep Analysis (+1 more)

### Community 531 - "Auto-Create Facilities & Sources Walkthrough"
Cohesion: 0.20
Nodes (9): 2. Manage Data > Production Data, 3. Calculations > Emissions Activity Log, Auto-Create Facilities & Sources Walkthrough, Automated Tests, Manual Verification, Navigation Updates, templates, Testing the Logic (+1 more)

### Community 532 - "Walkthrough - Carbon Intensity & Hierarchical Filtering"
Cohesion: 0.20
Nodes (9): 1. Hierarchical Filtering, 2. Flaring Intensity Metric, 3. Data Integrity & Fixes, 4. Manage Data Improvements, 5. API Compliance Modules (Phase 3), 6. Dashboard & Reports (Phase 4), 7. Scope 3 Refactoring (Phase 4.1), 8. Verification & Compliance (Phase 5) (+1 more)

### Community 533 - "Key Changes by Layer"
Cohesion: 0.20
Nodes (9): 1. Frontend State & Concurrency, 2. API & Contract Integrity, 3. Backend Logic & Data Access Layer, 4. OWASP Security Remediations, 5. Runtime Boundaries & Performance, Full-Stack Audit Remediation Walkthrough, Key Changes by Layer, Pytest Test Suite (+1 more)

### Community 534 - "New Capabilities"
Cohesion: 0.20
Nodes (9): 1. Loading Loss Calculator (API Eq 5-1), 2. Tank Flashing Calculator (Vasquez-Beggs), 3. Glycol Dehydrator Calculator, 4. Sentinel-5P Multi-Pollutant Integration, Features:, New Capabilities, Verification, Verification (+1 more)

### Community 535 - "Implementation Plan - GHG Emissions Tool (API Compendium)"
Cohesion: 0.20
Nodes (9): Automated Tests, Goal Description, Implementation Plan - GHG Emissions Tool (API Compendium), Manual Verification, Modules to Implement, Project Structure, Proposed Changes, User Review Required (+1 more)

### Community 536 - "Implementation Plan - 3D Layout Overhaul & Interaction"
Cohesion: 0.20
Nodes (9): 1. Interactive Layout Editor (`app.py`), 2. Unified Rendering Engine (`src/design.py`), 3. Realistic Environment (`src/design.py`), Goal, Implementation Plan - 3D Layout Overhaul & Interaction, Manual Verification, Proposed Changes, User Review Required (+1 more)

### Community 537 - "TestMissingAndEmptyInputs"
Cohesion: 0.25
Nodes (5): parametrize, Verifies rejection of IEEE 754 NaN, +Inf, -Inf., Verifies graceful and explicit validation of missing and empty fields., TestMissingAndEmptyInputs, TestNaNAndInfinityHandling

### Community 538 - "TestTier1Combustion"
Cohesion: 0.20
Nodes (3): Same calculation using m3 input — should produce same result after conversion., Hand-calc for Natural Gas Tier 1: quantity = 10,000 scf HHV = 1,020 Btu/scf →…, TestTier1Combustion

### Community 539 - "TestCatalogFactorIntegrity"
Cohesion: 0.25
Nodes (5): Validates structure and completeness of the API 2021 factor catalog., API Compendium 2021 database must contain all published factors., Every registered segment has non-empty factor sets., Every factor must have unit, category, and valid numerical emissions., TestCatalogFactorIntegrity

### Community 540 - "test_audit_rc3_targets.py"
Cohesion: 0.25
Nodes (7): admin_client(), fixture, parametrize, RC-3 / RC-11 validation of SBTi targets and goals (BUG-034, BUG-039, BUG-059)., test_bug034_059_invalid_sbti_targets_rejected(), test_bug039_dashboard_survives_legacy_nan_goal(), test_bug039_invalid_goals_rejected()

### Community 541 - "User"
Cohesion: 0.03
Nodes (79): User, seed_admin(), admin_user(), app(), client(), login(), fixture, Security and integration tests for GHG Dashboard API. These test the HTTP layer… (+71 more)

### Community 542 - "test_audit_forms_payload.py"
Cohesion: 0.27
Nodes (6): _ch4(), Form / payload contract regressions (BUG-090, BUG-110). Hand values: - BUG-110…, test_bug090_agr_control_is_applied(), test_bug110_facility_level_fugitive_uses_table_7_8(), test_bug110_gas_units_and_composition(), test_bug110_unrecognised_fugitive_request_not_booked_as_valves()

### Community 543 - "BUG-050 — Negative activity amounts are accepted for process types that are not in the dispatcher (e.g. "loading") and saved as negative emissions"
Cohesion: 0.20
Nodes (10): Actual, Affected Components, BUG-050 — Negative activity amounts are accepted for process types that are not in the dispatcher (e.g. "loading") and saved as negative emissions, Evidence, Expected, Impact, Location, Recommended Fix (+2 more)

### Community 544 - "FlaringCalculator"
Cohesion: 0.11
Nodes (13): FlaringCalculator, In flaring, unburnt methane slip is amplified under a 20-year horizon., test_flaring_calculator_basic(), test_flaring_calculator_specific_c1_c10(), test_stationary_combustion_calculator(), Mathematically verifies API Compendium §5.2 flaring carbon mass balance: CH4…, Regression test for N2O flaring default factor harmonization (API Compendium…, test_flaring_n2o_default_consistency() (+5 more)

### Community 545 - "Implementation Tasks: Batch Approve/Reject Pending Records"
Cohesion: 0.20
Nodes (9): Dependencies & Execution Order, Implementation for User Story 1, Implementation for User Story 2, Implementation Tasks: Batch Approve/Reject Pending Records, Phase 1: Setup (Shared Infrastructure), Phase 2: Foundational (Blocking Prerequisites), Phase 3: User Story 1 - Bulk Approving Records (Priority: P1) ⭐ MVP, Phase 4: User Story 2 - Bulk Rejecting Records (Priority: P2) (+1 more)

### Community 546 - "send_email"
Cohesion: 0.31
Nodes (8): is_smtp_configured(), Dispatches outbound email using configured SMTP provider. Gracefully falls back…, Send formatted password reset request email., Check if outbound SMTP configuration is active., Send alert to administrators when new batch uploads require maker-checker…, send_batch_review_alert(), send_email(), send_password_reset_email()

### Community 547 - "test_satellite.py"
Cohesion: 0.18
Nodes (10): Layer configuration returns ESA standard legend steps and unauthenticated…, Crucial policy test: Unconfigured / unauthenticated queries MUST return status…, Tests OAuth2 authentication flow with mock Copernicus Keycloak token endpoint., Verifies the physical 1D box model / mass-divergence plume flux estimation., Tests OAuth2 rejection handling., test_sentinel5p_connection_test_mocked_failure(), test_sentinel5p_connection_test_mocked_success(), test_sentinel5p_flux_calculation() (+2 more)

### Community 548 - "BUG-087 — Malformed input on create endpoints returns HTTP 500/409 with raw exception and SQL text (≈40 handlers return `str(e)`)"
Cohesion: 0.22
Nodes (9): Actual, Affected Components, BUG-087 — Malformed input on create endpoints returns HTTP 500/409 with raw exception and SQL text (≈40 handlers return `str(e)`), Expected, Impact, Location, Recommended Fix, Reproduction (+1 more)

### Community 549 - "Findings and fixes"
Cohesion: 0.18
Nodes (10): Bulk uploader check (2026-09-29), Calculation defects found through the templates (also affect manual entry), File reading and column mapping, Findings and fixes, Follow-up: the remaining gaps (2026-09-29), Results, Scope 1 rows, Scope 2, Scope 3 and Manage Data rows (+2 more)

### Community 550 - "AUDIT SCOPE — GHG Accounting & Reporting Platform"
Cohesion: 0.22
Nodes (8): 0. Audited baseline, 1. Architecture (verified from source), 2. Application areas → workstream ownership, 3. Calculation inventory (module level; per-calculation detail in Appendix A), 4. Initial observations that need explanation (seeded to workstreams), Appendix A — Per-calculation detail, Appendix B — Scope changes during the audit, AUDIT SCOPE — GHG Accounting & Reporting Platform

### Community 551 - "w2_facility.mjs"
Cohesion: 0.22
Nodes (6): lastApi(), actSel, divSel, p, btn, m

### Community 552 - "ISO 14064-1 Uncertainty Implementation"
Cohesion: 0.22
Nodes (9): [Backend] [dashboard.py](file:///c:/Users/samsung/Desktop/h/new/server/routes/dashboard.py), [Backend] [models.py](file:///c:/Users/samsung/Desktop/h/new/server/models.py) & [custom_factors.py](file:///c:/Users/samsung/Desktop/h/new/server/routes/custom_factors.py), [Frontend/Backend] EF Uncertainty Calculation Enhancement, [Frontend] [Dashboard.jsx](file:///c:/Users/samsung/Desktop/h/new/client/src/pages/Dashboard.jsx), [Frontend] [ManageData.jsx](file:///c:/Users/samsung/Desktop/h/new/client/src/pages/ManageData.jsx), [Frontend] [UncertaintyAssessment.jsx](file:///c:/Users/samsung/Desktop/h/new/client/src/pages/UncertaintyAssessment.jsx), ISO 14064-1 Uncertainty Implementation, [MODIFY] [UncertaintyAssessment.jsx](file:///c:/Users/samsung/Desktop/h/new/client/src/pages/UncertaintyAssessment.jsx) (+1 more)

### Community 553 - "PVGIS Data Analyzer - Implementation Tasks"
Cohesion: 0.22
Nodes (8): Backend Development, Daily Breakdown Enhancement, Features Implementation, Frontend Development, ✅ Project Complete!, Project Setup, PVGIS Data Analyzer - Implementation Tasks, Testing & Verification

### Community 554 - "Implementation Plan - Auto-Create Facilities from CSV"
Cohesion: 0.22
Nodes (8): Frontend, Implementation Plan - Auto-Create Facilities from CSV, Manual Verification, [MODIFY] [emissions-calc.js](file:///C:/Users/samsung/Desktop/h/public/emissions-calc.js), [MODIFY] [manage-data.html](file:///C:/Users/samsung/Desktop/h/public/manage-data.html), Proposed Changes, User Review Required, Verification Plan

### Community 555 - "Changes Required"
Cohesion: 0.22
Nodes (8): 1. Rename & Improve Navigation, 2. Enhance Custom Factors Form, 3. Create Reference Data Page, 4. Update Backend (if needed), Changes Required, Custom Factors Enhancement & Reference Data Page, Implementation Order, Overview

### Community 556 - "Changes"
Cohesion: 0.22
Nodes (8): 1. Modernized Login Page, 2. Theme Corrections, 3. OGMP MARS Notifications, 4. Methane Hotspot Explorer, Changes, Overview, Verification Scenarios, Walkthrough: Modernization & OGMP MARS Integration

### Community 557 - "✅ Enhancements Completed"
Cohesion: 0.22
Nodes (8): 1. **Layer Toggle Controls** 🎛️, 2. **Site Measurements** 📏, 3. **Enhanced Info Bar** 📐, 4. **Export Instructions** 💡, CAD View - Quick Wins Implementation, ✅ Enhancements Completed, Impact, Next Steps (Optional)

### Community 558 - "New Features"
Cohesion: 0.22
Nodes (8): 1. ✏️ Interactive Layout Editor, 2. 🏗️ Adaptable Mounting Systems, 3. 🌍 Realistic Environment Textures, 4. 💎 High-Fidelity Details, How to Use, Layout & Rendering Upgrade - Complete, New Features, Overview

### Community 559 - "🌟 Key Features Implemented"
Cohesion: 0.22
Nodes (8): 1. Organizational Boundaries (§4.5.1), 2. Uncertainty Quantification (§4.6.5), 3. Audit Trail & Recalculation (§4.6.6), 4. Verification Workflow (§5.3), Final Compliance Implementation Walkthrough, 🏁 Final Status, 🚀 How to Review, 🌟 Key Features Implemented

### Community 560 - "MCP Servers (`mcp_config.json`)"
Cohesion: 0.22
Nodes (8): 1. Stdio Transport (Local), 2. SSE Transport (Remote), Configuration File (`mcp_config.json`), Configuration Schema, How the Agent Uses MCP, Location, MCP Servers (`mcp_config.json`), Scoping and Scannability

### Community 561 - "Antigravity Customization System Guide"
Cohesion: 0.22
Nodes (9): Advanced Management: JSON Configs, Antigravity Customization System Guide, Customization Discovery and Locations, Customization Types: Quick Reference, Deduplication, Discovery Locations, How Customizations are Applied, Loading Priority and Precedence (+1 more)

### Community 562 - "2. Key WCAG 2.1 Level AA Compliance Findings"
Cohesion: 0.22
Nodes (8): 1. Executive Accessibility Summary, 2.1 Keyboard Operability & Focus Management (WCAG 2.1.1, 2.4.7), 2.2 Form Semantics & Error Handling (WCAG 1.3.1, 3.3.1, 3.3.2), 2.3 Color Contrast & Visual Ergonomics (WCAG 1.4.3, 1.4.11), 2.4 Tables & Complex Data Visualization (WCAG 1.3.1, 1.1.1), 2.5 Screen Reader Live Regions (WCAG 4.1.3), 2. Key WCAG 2.1 Level AA Compliance Findings, Web Accessibility & WCAG 2.1 AA Compliance Audit

### Community 563 - "Cross-Browser Compatibility & Responsive Viewport Audit"
Cohesion: 0.22
Nodes (8): 1. Executive Browser & Viewport Summary, 2. Browser Compatibility Matrix, 3. Web Platform Feature & Polyfill Verification, 4.1 Desktop (1920×1080) & Laptop (1440×900, 1280×800), 4.2 Tablet (768×1024, iPad Portrait / Landscape), 4.3 Mobile Smartphone (375×667, 390×844, 412×915), 4. Responsive Viewport & Device Layout Audit, Cross-Browser Compatibility & Responsive Viewport Audit

### Community 564 - "NumberedCanvas"
Cohesion: 0.28
Nodes (3): NumberedCanvas, Comprehensive Master PDF Report Generator…, Two-pass canvas to dynamically compute and print 'Page X of Y' and running…

### Community 565 - "GHGUser"
Cohesion: 0.31
Nodes (3): HttpUser, GHGUser, task

### Community 566 - "CalculationDispatcher"
Cohesion: 0.03
Nodes (49): CalculationDispatcher, Normalizes a volume value to the specified target unit., Strictly extracts a required float parameter without falling back to defaults., Cleanly parses a percentage (0-100) or fraction (0-1) into a 0.0 - 1.0 ratio., Extracts a percentage or fraction strictly and normalizes to 0.0 - 1.0., Extracts an optional percentage or fraction normalized to 0.0 - 1.0., Executes the calculation for the given process type. - Tier 1 (default /…, Routes a calculation request to the appropriate API 2021 calculator. (+41 more)

### Community 567 - "TestCleanGWPStandards"
Cohesion: 0.25
Nodes (5): Independent validation of GWP constants and standards against IPCC…, IPCC Fourth Assessment Report (2007) GWP values., IPCC Fifth Assessment Report (2013, WG1 Table 8.7) GWP values., IPCC Sixth Assessment Report (2021, WG1 Chapter 7) GWP values., TestCleanGWPStandards

### Community 568 - "BUG-074 — Approve/reject endpoints are not concurrency-safe: two simultaneous approvals of the same record both return 200 (duplicate audit entries; approve+reject race ends in an arbitrary final state)"
Cohesion: 0.20
Nodes (10): Actual, Affected Components, BUG-074 — Approve/reject endpoints are not concurrency-safe: two simultaneous approvals of the same record both return 200 (duplicate audit entries; approve+reject race ends in an arbitrary final state), Evidence, Expected, Impact, Location, Recommended Fix (+2 more)

### Community 569 - "login_required"
Cohesion: 0.05
Nodes (106): MitigationRecord, ReportingMetadata, login_required(), ensure_default_limits(), get_cap_compliance(), get_cap_emissions(), get_regulatory_limits(), route (+98 more)

### Community 570 - "Implementation Plan: [FEATURE]"
Cohesion: 0.22
Nodes (8): Complexity Tracking, Constitution Check, Documentation (this feature), Implementation Plan: [FEATURE], Project Structure, Source Code (repository root), Summary, Technical Context

### Community 571 - "package.json"
Cohesion: 0.22
Nodes (8): author, description, keywords, license, main, name, type, version

### Community 572 - "Implementation Plan: [FEATURE]"
Cohesion: 0.22
Nodes (8): Complexity Tracking, Constitution Check, Documentation (this feature), Implementation Plan: [FEATURE], Project Structure, Source Code (repository root), Summary, Technical Context

### Community 573 - "Existing Entities to Modify"
Cohesion: 0.22
Nodes (8): 1. `Emission` (Scope 1), 2. `Scope2Emission`, 3. `Scope3Emission`, 4. `CustomFactor`, `ActivityLog`, Data Model: QA/QC Module, Existing Entities to Modify, Existing Entities to Utilize

### Community 574 - "TestGWPValidation"
Cohesion: 0.25
Nodes (5): Verify GWP values from AR4, AR5, AR6 produce correct CO2e., AR5 default: CO2=1.0, CH4=28.0, N2O=265.0., AR4: CO2=1.0, CH4=25.0, N2O=298.0., AR6: CO2=1.0, CH4=27.9, N2O=273.0., TestGWPValidation

### Community 575 - "build_master_pdf"
Cohesion: 0.50
Nodes (4): build_master_pdf(), generate_all_15_charts(), Generates all 15 high-resolution (300 DPI) matplotlib charts directly from…, Compiles the complete A4 Portrait publication document.

### Community 576 - "Proposed Changes"
Cohesion: 0.25
Nodes (8): [Debug Support], [General Components], [ManageData.jsx](file:///c:/Users/samsung/Desktop/h/new/client/src/pages/ManageData.jsx), [MODIFY] [BulkImportModal.jsx](file:///c:/Users/samsung/Desktop/h/new/client/src/components/BulkImportModal.jsx), [MODIFY] [BulkImportModal.jsx](file:///c:/Users/samsung/Desktop/h/new/client/src/components/BulkImportModal.jsx), [MODIFY] [emissions.py](file:///c:/Users/samsung/Desktop/h/new/server/routes/emissions.py), [NEW] [BulkImportModal.jsx](file:///c:/Users/samsung/Desktop/h/new/client/src/components/BulkImportModal.jsx), Proposed Changes

### Community 577 - "API Guidance 2.0 Compliance Upgrade"
Cohesion: 0.25
Nodes (7): API Guidance 2.0 Compliance Upgrade, Phase 1: Core Calculation Standards, Phase 2: Database Schema Expansion, Phase 3: "Manage Data" UI Expansion, Phase 4.1: Refactor Scope 3 UI, Phase 4: Dashboard Integration, Phase 5: Verification

### Community 578 - "Implementation Steps"
Cohesion: 0.25
Nodes (7): 1. Create `public/profile-logic.js`, 2. Batch HTML Update, 3. Script Injection, Goal, Implementation Steps, Top-Bar Profile Dropdown Implementation, Verification

### Community 579 - "PVGIS CSV Parsing Support"
Cohesion: 0.25
Nodes (7): CSV Spreadsheet Converter, Manual Verification, [MODIFY] [script.js](file:///C:/Users/samsung/.gemini/antigravity/scratch/csv-spreadsheet-converter/script.js), Proposed Changes, PVGIS CSV Parsing Support, User Review Required, Verification Plan

### Community 580 - "Key Accomplishments"
Cohesion: 0.25
Nodes (7): 1. Data Extraction, 2. Automated Test Suite, 3. Engine Hardening & Bug Fixes, Artifacts Created, Key Accomplishments, Verification Results, Walkthrough - API Compendium 2021 Verification

### Community 581 - "CSV to Spreadsheet Converter"
Cohesion: 0.25
Nodes (7): Advanced Enhancements, Core Features, CSV to Spreadsheet Converter, Enhancement Verification, Project Setup, UI/UX Polish, Verification

### Community 582 - "GHG Tracker - Feature Expansion Walkthrough"
Cohesion: 0.25
Nodes (7): 1. Scope 2 (Electricity) Calculator, 2. Custom Emission Factors, 3. PDF Reports, 4. Reduction Targets & Modern Goal UI, 5. Premium "Glass Nature" Overhaul, GHG Tracker - Feature Expansion Walkthrough, Verification Steps

### Community 583 - "Dashboard Display"
Cohesion: 0.25
Nodes (7): Dashboard Display, Enhanced Profile with Professional Information, [MODIFY] [dashboard.html](file:///c:/Users/samsung/Desktop/ghg%20old/public/dashboard.html), [MODIFY] [dashboard.js](file:///c:/Users/samsung/Desktop/ghg%20old/public/dashboard.js), [MODIFY] [profile.html](file:///c:/Users/samsung/Desktop/ghg%20old/public/profile.html), Profile Page, Proposed Changes

### Community 584 - "Methane Hotspot Explorer Implementation Plan"
Cohesion: 0.25
Nodes (7): 1. New Page: [public/mars-map.html](file:///c:/Users/samsung/Desktop/h/public/mars-map.html), 2. Map Logic: [public/mars-map.js](file:///c:/Users/samsung/Desktop/h/public/mars-map.js), 3. Navigation, Goal, Methane Hotspot Explorer Implementation Plan, Proposed Changes, Verification

### Community 585 - "API Compendium 2021 - List of Exhibits"
Cohesion: 0.25
Nodes (7): API Compendium 2021 - List of Exhibits, Section 3: General Calculation Methodologies, Section 4: Stationary Combustion, Section 5: Flaring and Other Combustion, Section 6: Fugitive and Vented Emissions, Section 7: Wastewater Treatment & SF6, Section 8: Indirect Emissions (Scope 2)

### Community 586 - "Goal Description"
Cohesion: 0.25
Nodes (7): Automated Tests, Calculation Verification Suite, Goal Description, [NEW] [test_api_exhibits.py](file:///c:/Users/samsung/Desktop/h/new/server/tests/test_api_exhibits.py), Open Questions, Proposed Changes, Verification Plan

### Community 587 - "CAD Enhancements Complete: Layer Control & Setbacks"
Cohesion: 0.25
Nodes (7): CAD Enhancements Complete: Layer Control & Setbacks, Current CAD Feature Status, Gap #3: Setback Compliance - IN PROGRESS, Gap #7: Interactive Layer Control - COMPLETE, How to Use, Implementation Time, ✅ Implemented (Gaps #7 & #3)

### Community 588 - "Proposed Changes"
Cohesion: 0.25
Nodes (7): Backend (server.js), Frontend (Management), Frontend (Settings), Manual Verification, Organizational Boundaries Implementation Plan, Proposed Changes, Verification Plan

### Community 589 - "Lifecycle Hooks (`hooks.json`)"
Cohesion: 0.25
Nodes (7): Current Limitations, File Format, Hook Handler Fields, Hook Spec Fields, Lifecycle Hooks (`hooks.json`), Supported Event Types, The Matcher

### Community 590 - "agy-customizations/SKILL.md"
Cohesion: 0.29
Nodes (4): Rule Format, Rule Locations, Rule Merging and Deduplication, Workspace Rules

### Community 591 - "Independent GHG Emissions & MRV Calculation Validation Report"
Cohesion: 0.25
Nodes (7): 1. Zero-Circularity Independent Validation Methodology, 2. GHG Calculation Validation Matrix, 3. Golden Dataset Validation Results, 4. Property-Based Invariant Validation (Hypothesis), 5. Mutation Testing Kill Rate, Independent GHG Emissions & MRV Calculation Validation Report, Non-Circularity Safeguards:

### Community 594 - "env.py"
Cohesion: 0.39
Nodes (7): get_engine(), get_engine_url(), get_metadata(), Run migrations in 'offline' mode. This configures the context with just a URL…, Run migrations in 'online' mode. In this scenario we need to create an Engine…, run_migrations_offline(), run_migrations_online()

### Community 596 - "TestMudVolumeUnits"
Cohesion: 0.25
Nodes (5): Verify drilling mud degassing units: - Tier 1: wells (t CH4 / well) - Tier 2 /…, Reference: 10 wells = 10 * 0.0524 = 0.524 t CH4., Reference: 20 drilling days water-based = 20 * 0.0458 = 0.916 t CH4., Reference: 20 drilling days oil-based = 20 * 0.0103 = 0.206 t CH4., TestMudVolumeUnits

### Community 597 - "BatchAnomalyDetector"
Cohesion: 0.17
Nodes (6): BatchAnomalyDetector, Check a Scope 1 CO2e value against the trailing 12 months strictly prior to the…, Check a Scope 2 CO2e value against the trailing 12 months strictly prior to the…, Check a Scope 3 CO2e value against the trailing 12 months strictly prior to the…, Same checks as AnomalyDetector for a bulk import: the history of a facility and…, Compute Z-score of a value against a list of historical values. Returns…

### Community 598 - "test_audit_rc3_validation.py"
Cohesion: 0.25
Nodes (8): admin_client(), ctx(), fixture, parametrize, RC-3 central input validation regressions (AUDIT_FINDINGS.md)., test_bug083_non_finite_rejected_on_all_write_endpoints(), test_bug083_raw_json_nan_literal_rejected(), test_bug083_reads_stay_valid_json_with_legacy_non_finite_rows()

### Community 599 - "TestCleanStoichiometry"
Cohesion: 0.22
Nodes (5): parametrize, CLEAN-SLATE VALIDATION: Chemical Stoichiometry & Carbon Mass Balance Validates…, Independent validation of combustion stoichiometry., Validates that conservation of mass strictly holds (zero balance error)., TestCleanStoichiometry

### Community 600 - "TestCogenAllocationBattery"
Cohesion: 0.25
Nodes (5): Verifies API §8.3 Cogeneration (CHP) emission allocation., TestCogenAllocationBattery, Differential verification for Scope 2 and Scope 3 calculations., Diff Test: WRI Efficiency CHP allocation., TestDifferentialScope2and3

### Community 601 - "UserManagement.jsx"
Cohesion: 0.32
Nodes (6): UserManagement, Drawer(), getRoleMeta(), ROLE_META, S, UserManagement()

### Community 602 - "Emissions.jsx"
Cohesion: 0.29
Nodes (7): Emissions, STAGE_EMISSION_CALCULATOR, STAGE_FACTOR_CALCULATOR, STAGE_SCOPE1_SUB_SELECTION, STAGE_SCOPE2, STAGE_SCOPE3, STAGE_SCOPE_SELECTION

### Community 603 - "test_clean_emission_factors.py"
Cohesion: 0.14
Nodes (9): CLEAN-SLATE VALIDATION: Emission Factor Integrity & Selection Matrix Validates…, Independent audit of the API Compendium 2021 factor catalog., Verifies that all primary combustion fuels have valid, positive, physical…, Verifies that CO2, CH4, and N2O factors are not mixed up or cross-contaminated., Tests factor selection logic to prevent mis-selection of wrong fuels,…, Natural gas calculation must not select liquid diesel factors., Verifies custom factors take precedence without polluting global catalog., TestCleanEmissionFactorAudit (+1 more)

### Community 604 - "API Compendium 2021 — exhibit and default-factor check (2026-09-27)"
Cohesion: 0.29
Nodes (6): 1. Exhibits run through their process type, 2. Exhibits not runnable (method not in the engine), 3. Default factors x equivalent quantities in different units, 4. Defects found and fixed, 5. Onshore upstream / midstream exhibits added (2026-09-28), API Compendium 2021 — exhibit and default-factor check (2026-09-27)

### Community 605 - "F — Dashboard reconciliation (Agent F)"
Cohesion: 0.29
Nodes (6): Default view (All Years, all filters, GWP-100, Verified), F — Dashboard reconciliation (Agent F), Filter matrix (API `batch-all`, `audit/work/F/filter_matrix.json`), Lead root causes, QA dashboard, Reports / PDF

### Community 606 - "NotificationCenter.jsx"
Cohesion: 0.32
Nodes (6): getTypeConfig(), headerActionBtn, iconBtnStyle, NotifRow(), relativeTime(), TYPE_CONFIG

### Community 607 - "w10_gwp.mjs"
Cohesion: 0.33
Nodes (3): bb, g(), f()

### Community 608 - "w15_import.mjs"
Cohesion: 0.29
Nodes (5): auto, btn, jobs, rows, st

### Community 609 - "Correcting Organizational Hierarchy & Syncing Data"
Cohesion: 0.29
Nodes (6): Automated Tests, Correcting Organizational Hierarchy & Syncing Data, Manual Verification, User Review Required, User Review Required, Verification Plan

### Community 610 - "ReferenceData and Metadata Fixes"
Cohesion: 0.29
Nodes (7): [Backend] [data.py](file:///c:/Users/samsung/Desktop/h/new/server/routes/data.py), [Frontend] [ManageData.jsx](file:///c:/Users/samsung/Desktop/h/new/client/src/pages/ManageData.jsx), [Frontend] [ReferenceData.jsx](file:///c:/Users/samsung/Desktop/h/new/client/src/pages/ReferenceData.jsx), [MODIFY] [data.py](file:///c:/Users/samsung/Desktop/h/new/server/routes/data.py), [MODIFY] [ManageData.jsx](file:///c:/Users/samsung/Desktop/h/new/client/src/pages/ManageData.jsx), [MODIFY] [ReferenceData.jsx](file:///c:/Users/samsung/Desktop/h/new/client/src/pages/ReferenceData.jsx), ReferenceData and Metadata Fixes

### Community 611 - "4135d1c7-8dfd-43ce-af15-f9dd1ab24a49/task.md"
Cohesion: 0.29
Nodes (6): Task: Organize Project Directory (Zero-Public), Task: Prepare for Web Deployment, Task: Restructure Compliance and Login Report, Task:- [/] Restructure Dashboard Navigation, Task: Settings Page Modernization, Task:- [x] Expand Test Data to 9 Years & Diverse Types

### Community 612 - "New Features"
Cohesion: 0.29
Nodes (6): 1. Interactive Profile Menu, 2. Global Consistency, 3. Implementation Details, New Features, Profile Dropdown Implementation, Verification

### Community 613 - "Comprehensive Security, Compliance & IT Audit Report"
Cohesion: 0.29
Nodes (6): 1. Authentication & Session Management (Security & IT), 2. Authorization & Access Control (Security), 3. Data Validation, Injection & Resilience (Technical / InfoSec), 4. Compliance & IT Operations (IT Audit / Compliance), Audit Summary & Verdict, Comprehensive Security, Compliance & IT Audit Report

### Community 614 - "✅ CAD Layer Control Complete - Fixed & Ready"
Cohesion: 0.29
Nodes (6): ✅ CAD Layer Control Complete - Fixed & Ready, CAD Status Summary, File Restoration Complete, Fully Implemented Features, Gap #7: Interactive Layer Control ✅, Next Steps

### Community 615 - "GHG Emissions Calculator Compliance Report"
Cohesion: 0.29
Nodes (6): 1. Organizational Boundaries (§4.5.1), 2. Uncertainty & Verification (Recap), 📊 Compliance Overview, ⚖️ Final Assessment, ✅ Final Enhancements (ISO 14064-1), GHG Emissions Calculator Compliance Report

### Community 616 - "Input/Output Contract"
Cohesion: 0.29
Nodes (7): 1. `PreToolUse` Contract, 2. `PostToolUse` Contract, 3. `PreInvocation` Contract, 4. `PostInvocation` Contract, 5. `Stop` Contract, Common Input Fields, Input/Output Contract

### Community 617 - "Generative UI"
Cohesion: 0.29
Nodes (6): Constraints & Theming, Deciding on Placement (Inline vs. Standalone), Designing Inline Widgets (Cards & Transparency), Generative UI, Sizing Inline Embeds, Workflow

### Community 618 - "devDependencies"
Cohesion: 0.29
Nodes (7): electron, electron-builder, nodemon, devDependencies, electron, electron-builder, nodemon

### Community 621 - "Catalog factor check against the API Compendium 2021 (2026-09-28)"
Cohesion: 0.15
Nodes (12): Algerian National Grid: 0.4979 kg CO2e/kWh (2024, direct combustion), Catalog factor check against the API Compendium 2021 (2026-09-28), Corrected, Follow-up: EPA and IPCC sources (2026-09-29), Follow-up: spend factors and the Algerian grid (2026-09-29), Not verified (outside the Compendium), Removed (no Compendium source), Scope and method (+4 more)

### Community 624 - "TestDataStarvationBattery"
Cohesion: 0.50
Nodes (3): parametrize, Verifies behavior when insufficient historical data is present., TestDataStarvationBattery

### Community 625 - "TestFieldCoercionAndSanitization"
Cohesion: 0.33
Nodes (4): parametrize, Rigorous metrological tests for _clean_float., Mathematically prove that NaN and Infinity are neutralized., TestFieldCoercionAndSanitization

### Community 626 - "test_library_factor_mode.py"
Cohesion: 0.33
Nodes (8): ctx(), post(), fixture, Library factors (the site's factor database: calculated or equipment factors)…, test_combustion_tier2_without_factor_or_site_properties_still_rejected(), test_engineering_tier2_needs_no_library_factor(), test_library_factor_is_activity_times_factor_for_any_process(), test_library_mode_requires_a_library_factor()

### Community 627 - "test_deep_button_audit.py"
Cohesion: 0.48
Nodes (6): audit_buttons_on_current_page(), close_any_modal(), is_forbidden(), Wait for lazy-loaded component to finish mounting and spinners to detach., run(), wait_page_loaded()

### Community 628 - "test_definitions.py"
Cohesion: 0.43
Nodes (5): Export expected results from golden validation cases., get_test_case_by_id(), get_test_cases_by_category(), load_all_test_cases(), Test case accessors for golden validation dataset.

### Community 629 - "Audit Agent Protocol (mandatory for every workstream)"
Cohesion: 0.33
Nodes (5): Audit Agent Protocol (mandatory for every workstream), Final report (your last message), Hard rules, Harness, Reporting — IMMEDIATELY on confirmation, then keep auditing

### Community 630 - "BUG-092.mjs"
Cohesion: 0.33
Nodes (3): fac, row, shows

### Community 632 - "w19_unc.mjs"
Cohesion: 0.40
Nodes (5): f(), dd(), i, setFac(), u

### Community 633 - "[Frontend] Hierarchy Correction"
Cohesion: 0.33
Nodes (6): [Backend] Data Synchronization, [Frontend] Hierarchy Correction, [MODIFY] [BulkImportModal.jsx](file:///c:/Users/samsung/Desktop/h/new/client/src/components/BulkImportModal.jsx), [MODIFY] [ManageData.jsx](file:///c:/Users/samsung/Desktop/h/new/client/src/pages/ManageData.jsx), [NEW] [Sync Hierarchy Script](file:///c:/Users/samsung/Desktop/h/sync_hierarchy.py) [DELETE], Proposed Changes

### Community 634 - "[Calculation Engine Fixes]"
Cohesion: 0.33
Nodes (6): [Calculation Engine Fixes], [MODIFY] [BulkImportModal.css](file:///c:/Users/samsung/Desktop/h/new/client/src/components/BulkImportModal.css), [MODIFY] [emissions.py](file:///c:/Users/samsung/Desktop/h/new/server/routes/emissions.py), [MODIFY] [legacy_engine.py](file:///c:/Users/samsung/Desktop/h/new/server/calculations/legacy_engine.py), [MODIFY] [ManageData.jsx](file:///c:/Users/samsung/Desktop/h/new/client/src/pages/ManageData.jsx), [MODIFY] [managedata.py](file:///c:/Users/samsung/Desktop/h/new/server/routes/managedata.py)

### Community 635 - "Tasks"
Cohesion: 0.33
Nodes (5): Activity Log Dashboard Replica (Completed), Emission Data Page (Completed Initial Version), Tasks, UI/UX Modernization & Functional Enhancement (Completed), WBCSD Protocol Upgrade (Completed)

### Community 636 - "Key Changes"
Cohesion: 0.33
Nodes (5): 1. New Activity Log Table, 2. "New Activity Entry" Form, 3. Backend Enhancements, Key Changes, Walkthrough - Activity Log Dashboard

### Community 637 - "Dashboard and Calculator Fixes"
Cohesion: 0.33
Nodes (5): Dashboard and Calculator Fixes, Implementation, Investigation, Issues to Address, Verification

### Community 638 - "6f3b0214-86d8-4c32-ae7b-51068644ff56/task.md"
Cohesion: 0.33
Nodes (5): Emissions & Dashboard Fixes, Integrating Registration Data with Profile Page, ISO 14064-1 Compliance Features, Notification & Sidebar Polishing, Runtime Error Fixes

### Community 639 - "Comprehensive Software Hardening Walkthrough"
Cohesion: 0.33
Nodes (5): Comprehensive Software Hardening Walkthrough, Conclusion, Phase 2: Data Integrity, Phase 4: Infrastructure & Architecture, Phase 5: UI / UX

### Community 640 - "Walkthrough: Cement GHG Emissions Calculator"
Cohesion: 0.33
Nodes (5): 1. Login & Registration, 2. Modern Dashboard, 3. Backend Logic (WBCSD Compliance), 4. Verification, Walkthrough: Cement GHG Emissions Calculator

### Community 641 - "Verification Walkthrough: Region Hierarchy Refactor"
Cohesion: 0.33
Nodes (5): 1. Restart Server, 2. Verify "Manage Data" Changes, 3. Verify "Emission Calculator" Changes, 4. Verify Data Persistence, Verification Walkthrough: Region Hierarchy Refactor

### Community 642 - "Configuration Schema"
Cohesion: 0.33
Nodes (6): Configuration Schema, JSON Configuration Files, Path Entry Fields, Path Resolution Rules, Pro-Tip: Team Sharing via VCS, Top-Level Fields

### Community 643 - "Plugins"
Cohesion: 0.33
Nodes (6): Directory Structure, How Plugins Work, Manifest (`plugin.json`), Plugins, Registering Plugins, Turning Plugins On and Off

### Community 644 - "Workspace Skills"
Cohesion: 0.33
Nodes (5): Best Practices for Writing Skills, Directory Structure, Frontmatter Fields, Main Instruction File (`SKILL.md`), Workspace Skills

### Community 645 - "Instructions for the Agent"
Cohesion: 0.33
Nodes (5): Instructions for the Agent, Migrate Workflows to Skills, Step 1: Discover Existing Workflows, Step 2: Convert Each Workflow to a Skill (Idempotent Execution), Step 3: Verify and Confirm

### Community 648 - "TestConcurrentBulkIngestionPipeline"
Cohesion: 0.33
Nodes (4): Stress test concurrent polling via get_job_status across 30 parallel threads., Stress tests the background asynchronous file processor under multi-threaded…, Submit and process 8 distinct CSV upload jobs concurrently in parallel…, TestConcurrentBulkIngestionPipeline

### Community 649 - "generate_1k_comprehensive.py"
Cohesion: 0.33
Nodes (3): gas_comp(), Generate a comprehensive 1,000-row Scope 1 test CSV that covers: - All 13…, Return a realistic gas composition that sums to ~100%.

### Community 650 - "TestTier1Flaring"
Cohesion: 0.33
Nodes (3): Flaring Tier 1 (default factor_source → _generic_calculation): Uses API_FACTORS…, Tier 1 flaring falls through to generic EF-based calculation., TestTier1Flaring

### Community 652 - "test_log_handler.py"
Cohesion: 0.33
Nodes (5): Regression test: import_debug.log must not be recreated. Ensures the…, import_debug.log was a 4.1 GB unbounded log file that caused disk exhaustion.…, Verify that the application's rotating log handler is configured with size and…, test_no_import_debug_log_file_exists(), test_trace_log_uses_rotating_handler()

### Community 653 - "TestExhaustiveUnitInvertibility"
Cohesion: 0.47
Nodes (3): parametrize, Tests A -> B -> A round-trip invertibility for every unit category., TestExhaustiveUnitInvertibility

### Community 655 - "test_all_apis_health.py"
Cohesion: 0.47
Nodes (5): get_sample_payload(), Replace route parameter placeholders cleanly without modifying host., Provide realistic sample payloads for POST/PUT endpoints., resolve_rule(), run_api_health_audit()

### Community 656 - "test_master_button_audit.py"
Cohesion: 0.60
Nodes (5): audit_buttons_on_current_page(), close_any_modal(), is_forbidden(), run_master_audit(), wait_page_loaded()

### Community 657 - "scripts"
Cohesion: 0.33
Nodes (6): scripts, build:exe, start, start:electron, start:web, test

### Community 659 - "RTK - Rust Token Killer (Google Antigravity)"
Cohesion: 0.40
Nodes (4): Meta Commands, RTK - Rust Token Killer (Google Antigravity), Rule, Why

### Community 660 - "Agent I — Endpoint inventory (generated from app.url_map + source decorators)"
Cohesion: 0.40
Nodes (4): Agent I — Endpoint inventory (generated from app.url_map + source decorators), Findings mapped to endpoints, Inventory, Timing (admin, snapshot data, in-process)

### Community 661 - "w24_meth.mjs"
Cohesion: 0.40
Nodes (4): all, all2, r, s

### Community 662 - "Investigation Plan: PDF Report Generation Issues"
Cohesion: 0.40
Nodes (4): Checklist, Findings, Goal, Investigation Plan: PDF Report Generation Issues

### Community 663 - "Task: Investigate Report Generation Issue"
Cohesion: 0.40
Nodes (4): Checklist, Findings, Goal, Task: Investigate Report Generation Issue

### Community 664 - "Workspace Cleanup Plan"
Cohesion: 0.40
Nodes (4): Files and Folders to DELETE, Files and Folders to KEEP, User Review Required, Workspace Cleanup Plan

### Community 665 - "Changes Made"
Cohesion: 0.40
Nodes (4): 1. Fixed Acid Gas Removal (AGR) Compliance, 2. Fixed Storage Tank Default Fallback, API Compendium Calculation Logic Fixes, Changes Made

### Community 666 - "Dashboard Summary and CORS Fixes"
Cohesion: 0.40
Nodes (5): [Backend] [app.py](file:///c:/Users/samsung/Desktop/h/new/server/app.py), [Backend] [dashboard.py](file:///c:/Users/samsung/Desktop/h/new/server/routes/dashboard.py), Dashboard Summary and CORS Fixes, [MODIFY] [app.py](file:///c:/Users/samsung/Desktop/h/new/server/app.py), [MODIFY] [dashboard.py](file:///c:/Users/samsung/Desktop/h/new/server/routes/dashboard.py)

### Community 667 - "Unified Emissions Database & Reporting"
Cohesion: 0.40
Nodes (5): [Backend] [emissions.py](file:///c:/Users/samsung/Desktop/h/new/server/routes/emissions.py), [Frontend] [Reports.jsx](file:///c:/Users/samsung/Desktop/h/new/client/src/pages/Reports.jsx), [MODIFY] [emissions.py](file:///c:/Users/samsung/Desktop/h/new/server/routes/emissions.py), [MODIFY] [Reports.jsx](file:///c:/Users/samsung/Desktop/h/new/client/src/pages/Reports.jsx), Unified Emissions Database & Reporting

### Community 668 - "Task: Authentication and Database Restructuring"
Cohesion: 0.40
Nodes (4): Implementation Phase, Planning Phase, Task: Authentication and Database Restructuring, Verification Phase

### Community 669 - "Walkthrough: API Compendium Verification"
Cohesion: 0.40
Nodes (4): 1. Test Framework Generation, 2. Key Exhibit Implementation, 3. Results, Walkthrough: API Compendium Verification

### Community 670 - "Realistic Pitch Deck Complete"
Cohesion: 0.40
Nodes (4): File Location, Preview of the Screenshots Embedded, Realistic Pitch Deck Complete, What Was Done

### Community 671 - "Walkthrough - API GHG Emissions Tool"
Cohesion: 0.40
Nodes (4): Features, How to Run, Project Structure, Walkthrough - API GHG Emissions Tool

### Community 672 - "build_pitch_deck.py"
Cohesion: 0.40
Nodes (4): add_card(), add_header(), Adds standard Startup Algeria header banner with accent bar and title., Creates a modern rounded rectangular card container.

### Community 673 - "Mandatory Human Review & Domain Expert Governance Register"
Cohesion: 0.40
Nodes (4): 1. Principle of Automated Testing Boundaries, 2. Mandatory Human Review Gates Register, 3. Governance Protocol & Audit Sign-Off Requirements, Mandatory Human Review & Domain Expert Governance Register

### Community 681 - "[CHECKLIST TYPE] Checklist: [FEATURE NAME]"
Cohesion: 0.40
Nodes (4): [Category 1], [Category 2], [CHECKLIST TYPE] Checklist: [FEATURE NAME], Notes

### Community 682 - "[CHECKLIST TYPE] Checklist: [FEATURE NAME]"
Cohesion: 0.40
Nodes (4): [Category 1], [Category 2], [CHECKLIST TYPE] Checklist: [FEATURE NAME], Notes

### Community 683 - "Research & Design Decisions: Batch Approve/Reject"
Cohesion: 0.40
Nodes (4): 1. Technical Context Verification, 2. Identified Issues, 3. Decisions, Research & Design Decisions: Batch Approve/Reject

### Community 684 - "Research & Design Decisions: QA/QC Module (IPCC & ISO 14064)"
Cohesion: 0.40
Nodes (4): 1. Technical Context Verification, 2. Identified Issues & Requirements, 3. Decisions, Research & Design Decisions: QA/QC Module (IPCC & ISO 14064)

### Community 685 - "run_full_validation_suite.py"
Cohesion: 0.60
Nodes (4): main(), parse_pytest_summary(), Master Validation Test Runner. ============================= Orchestrates…, run_pytest()

### Community 687 - "BUG-111.mjs"
Cohesion: 0.50
Nodes (3): blank, rows, y1800

### Community 689 - "ef_client.mjs"
Cohesion: 0.50
Nodes (3): API_FACTORS, PROCESS_GROUPS, PROCESS_TYPES

### Community 691 - "Task: Test GHG Platform UI"
Cohesion: 0.50
Nodes (3): Plan, Progress, Task: Test GHG Platform UI

### Community 692 - "Task: Investigate PDF Report Download Issue"
Cohesion: 0.50
Nodes (3): Findings, Plan, Task: Investigate PDF Report Download Issue

### Community 693 - "Task List"
Cohesion: 0.50
Nodes (3): Active Goal: Refactoring Filters to Scrollable Custom Dropdowns, Completed Goals, Task List

### Community 694 - "Task: Implement Specific Emission Factor Calculator"
Cohesion: 0.50
Nodes (3): Objective, Task: Implement Specific Emission Factor Calculator, Todo List

### Community 695 - "Revamped Pitch Deck Plan"
Cohesion: 0.50
Nodes (3): Proposed Strategy, Revamped Pitch Deck Plan, User Review Required

### Community 696 - "Fix NameError in app.py"
Cohesion: 0.50
Nodes (3): Changes, Fix NameError in app.py, Verification

### Community 697 - "fa667970-6544-43ed-9980-019760f9806b/task.md"
Cohesion: 0.50
Nodes (3): Cleanup Task List, Compliance Check Task List, ISO 14064-1 Implementation Task List

### Community 705 - "status.py"
Cohesion: 0.50
Nodes (3): normalize_status(), Canonical Status Vocabulary for GHG Platform. Standardizes statuses across…, Normalize input status string to canonical vocabulary.

### Community 707 - "test_battery_stoichiometry_indirect_energy.py"
Cohesion: 0.11
Nodes (11): parametrize, Battery 2: Stoichiometry & Indirect Energy Allocation Test Suite.…, Verifies API §4.1 stoichiometric carbon mass balance calculations., 1 metric tonne of 100% pure carbon produces exactly 44.01/12.011 = ~3.66414…, TestStoichiometricMassBalanceBattery, _val(), Diff Test: Location-based grid electricity., Diff Test: Indirect steam net efficiency equation. (+3 more)

### Community 711 - "calculations/dispatcher.py"
Cohesion: 0.03
Nodes (92): convert_factor_to_kg_per_unit(), _density_kg_m3(), factor_hhv_unit(), fuel_basis(), hhv_mj_per_unit(), API Compendium 2021 - Section 5: Combustion and Flaring Implementation of…, Heating value in MJ per ONE activity unit, converting the activity into the HHV…, kg of gas per ONE activity unit, through the canonical unit parser (RC-5). -… (+84 more)

### Community 714 - "IndependentUncertaintyModel"
Cohesion: 0.18
Nodes (6): Diff Test: IPCC 2006 SRSS propagation and GUM k=2 95% CI., IndependentUncertaintyModel, Independent Uncertainty Quantification & Propagation Model. Source of Truth:…, IPCC 2006 Eq. 3.1: u_E = sqrt(u_AD^2 + u_EF^2), IPCC 2006 Eq. 3.2 / 3.3: u_total = sqrt(sum((E_i * u_i)^2)) / sum(E_i), Propagates uncertainties per IPCC 2006 Eq 3.1 & GUM §6.2. If input_is_95pct is…

### Community 715 - "build"
Cohesion: 0.22
Nodes (9): build, appId, directories, productName, win, output, asar, icon (+1 more)

### Community 717 - "FIX LOG"
Cohesion: 0.40
Nodes (4): 2026-09-29 - Bulk uploader follow-up, 2026-09-29 - Bulk uploaders, FIX LOG, Remediation run 2 (root-cause-first, branch fix/audit-remediation-rc)

### Community 780 - "build_elm_master_pdf"
Cohesion: 0.50
Nodes (4): build_elm_master_pdf(), generate_elm_15_charts(), Generates all 15 high-resolution (300 DPI) matplotlib charts for El Merk., Compiles the complete A4 Portrait publication document for El Merk.

### Community 785 - "combine_uncertainties_sum"
Cohesion: 0.08
Nodes (17): combine_uncertainties_product(), combine_uncertainties_sum(), Combine relative uncertainties for E = Activity × EF (multiplicative). Standard…, Combine relative uncertainties for E = A + B (additive, independent). Formula:…, Aggregate uncertainty across multiple sources using SRSS Approach 1. Formula:…, srss_inventory(), Finding 8: Verify combine_uncertainties_sum returns non-negative relative…, test_uncertainty_combine_sum_negative_sinks() (+9 more)

### Community 931 - ".test_dashboard_summary_identity_and_compact_formatting"
Cohesion: 0.50
Nodes (3): Replicates formatCompactNumber(value, decimals) from formatters.js., Verify: Dashboard summary aggregate preserves scope1 + scope2 == total and…, ui_format_compact_number()

### Community 940 - "CombustionCalculator"
Cohesion: 0.06
Nodes (27): CombustionCalculator, API Compendium 2021 §4.2 Example 4-1: 10,000 m3 natural gas combustion., Tier 3: Detailed chromatographic gas composition (C1-C10) with carbon mass…, Tier 1: Standard activity × default EF. 1,000 MMBtu natural gas with default…, Sonatrach ISO 6976 Hassi R'Mel sales gas preset: HHV = 1085 Btu/scf. Fuel:…, IANOR NA 8110 Diesel preset: density = 840 kg/m3. Fuel: 10 m3 Diesel. Standard…, Tier 2: Fuel-specific Higher Heating Value (HHV) and regional density. Fuel:…, Verify that carbon mass is strictly conserved in Tier 3 combustion. (+19 more)

## Knowledge Gaps
- **5672 isolated node(s):** `req`, `req`, `req`, `crashed`, `s` (+5667 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **112 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `compute_emissions()` connect `compute_emissions` to `Facility`, `calculate_co2e`, `background_processor.py`, `test_qfull_boundary_sensitivity.py`, `test_browser_exploratory_fixes.py`, `test_bulk_uploaders.py`, `parse_number`, `test_emission_calculations.py`, `emissions.py`, `test_tier3_browser_findings.py`, `User`, `test_audit_forms_payload.py`, `test_onshore_well_completions_audit.py`, `TestAllProcessTypesTier3`, `CalculationDispatcher`, `TestBoundaryConditions`, `ref_co2e`, `TestOATSensitivity`, `._run`, `calculations/dispatcher.py`, `test_qfull_unit_conversions.py`, `TestMudVolumeUnits`, `test_stress_boundary_resilience.py`, `test_clean_emission_factors.py`, `TestCombustionTier1`, `get_active_gwp`, `test_audit_rc10_uncertainty.py`?**
  _High betweenness centrality (0.022) - this node is a cross-community bridge._
- **Why does `User` connect `User` to `Facility`, `test_all_bulk_imports.py`, `extensions.py`, `background_processor.py`, `dashboard.py`, `test_browser_exploratory_fixes.py`, `test_bulk_uploaders.py`, `routes/scope2.py`, `TestIntermediateValues`, `TestConcurrentBulkIngestionPipeline`, `parse_number`, `test_tier_scope_kpi_numerical.py`, `test_audit.py`, `test_security_hardening.py`, `test_audit_bug_fixes.py`, `server/app.py`, `log_activity_and_notify`, `emissions.py`, `test_tier2_api_e2e.py`, `test_onshore_well_completions_audit.py`, `test_associated_gas_venting.py`, `models.py`, `CalculationDispatcher`, `test_audit_rc14_schema.py`, `TestGWPValidation`, `test_deep_injection_matrix.py`, `test_it_role_security.py`, `test_uncertainty.py`, `make_user`, `custom_factors.py`, `test_stress_boundary_resilience.py`, `test_production_smoke.py`, `get_active_gwp`, `test_audit_remediation.py`, `TestFieldCoercionAndSanitization`, `test_qaqc_diagnostics.py`?**
  _High betweenness centrality (0.022) - this node is a cross-community bridge._
- **Why does `sqlite3` connect `sqlite3` to `background_processor.py`, `E/api2.py`, `auditlib.py`, `make_db`, `models.py`, `server/app.py`, `dependencies`, `test_audit_rc14_schema.py`?**
  _High betweenness centrality (0.014) - this node is a cross-community bridge._
- **Are the 59 inferred relationships involving `User` (e.g. with `FiniteJSONProvider` and `ImportTooLarge`) actually correct?**
  _`User` has 59 INFERRED edges - model-reasoned connections that need verification._
- **Are the 6 inferred relationships involving `compute_emissions()` (e.g. with `_process_file_thread()` and `.test_combustion_process_row()`) actually correct?**
  _`compute_emissions()` has 6 INFERRED edges - model-reasoned connections that need verification._
- **Are the 60 inferred relationships involving `Facility` (e.g. with `ImportTooLarge` and `NumberedCanvas`) actually correct?**
  _`Facility` has 60 INFERRED edges - model-reasoned connections that need verification._
- **Are the 54 inferred relationships involving `Emission` (e.g. with `ImportTooLarge` and `AnomalyDetector`) actually correct?**
  _`Emission` has 54 INFERRED edges - model-reasoned connections that need verification._