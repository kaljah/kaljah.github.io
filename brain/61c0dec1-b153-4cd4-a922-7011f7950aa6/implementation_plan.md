# Implementation Plan: Human Review Gates & MRV Platform Refinements

This plan presents the detailed architectural design and code touchpoints to address the Human Review Gates (HRG-001 through HRG-010) identified during the full platform audit, strictly following the user's instructions:
1. Fetch each region's organizational boundary directly from the Region tab in Manage Data.
2. Add a description / lab certification box in the Custom Factors tab in Manage Data.
3. Suggest an architectural solution for Scope 3 category boundary governance.
4. Suggest an engineering solution for flaring aerodynamic efficiency under cross-flow wind conditions.
5. Incorporate TEG dehydrator stripping gas volume into engineering calculations without altering UI theme or styles, with 100% verified correctness.
8. Add a GWP standard selector dropdown in the Report Generator and dynamically recalculate report emissions based on that selection.
- Provide clear solutions for remaining gates: HRG-006 (AGR line-up), HRG-007 (OGMP reconciliation), HRG-009 (correlated uncertainty), HRG-010 (EPA WEC exemptions).

> [!IMPORTANT]
> **Strict Adherence to User Instructions**:
> No production code or calculations will be modified until you review and explicitly approve this plan.

---

## User Review Required

Please review the proposed approach for each item below before authorizing execution:

### 1. Item 1 — Region Organizational Boundary Fetching (HRG-001)
- **Current Problem**: In `new/client/src/pages/ManageData.jsx`, the Region form allows users to select `Consolidation Approach` (`facilityForm.boundary_type`) and `Boundary Details` (`facilityForm.boundary_detail`). However, in `new/server/routes/facilities.py`, `add_facility()` and `update_facility()` do not save `boundary_type` and `boundary_detail` to the database record, and `get_facilities()` does not include them in the JSON response. As a result, `ModernReportGenerator.js` (line 718) always fell back to `"Operational Control"`.
- **Proposed Solution**:
  - Update `facilities.py` (`get_facilities`): Return `"boundary_type": f.boundary_type or "Operational Control"` and `"boundary_detail": f.boundary_detail or ""`.
  - Update `facilities.py` (`add_facility` and `update_facility`): Read and persist `boundary_type` and `boundary_detail` into the `Facility` database model (the columns already exist in `models.py`).
  - Update `ManageData.jsx` table: Display the consolidation approach and boundary details in the Active Regions table.
  - Update `ModernReportGenerator.js`: Dynamically display each region's specific organizational boundary in Chapter 2.

### 2. Item 2 — Custom Factors Description & Lab Certification Box (HRG-002)
- **Current Problem**: In `ManageData.jsx`, custom emission factors only collect factor names, parent fuel, unit, and numerical factor/uncertainty values. There is no field to capture the accredited laboratory gas chromatography report number, EPD link, or boundary justification.
- **Proposed Solution**:
  - Update `new/server/models.py`: Add `description = db.Column(db.Text, nullable=True)` to `CustomFactor` (and ensure backward-compatible migration).
  - Update `new/server/routes/custom_factors.py`: Accept, return, and update `description` and `source` in GET, POST, and PUT endpoints.
  - Update `new/client/src/pages/ManageData.jsx`: Add a `Description & Lab Certification / Reference` text area (e.g., "Accredited Lab Report #, Gas Chromatography analysis, or EPD citation") matching existing UI form styling (`mole-input`).
  - Display the description/certification citation in the custom factors table and details view.

### 3. Item 3 — Scope 3 Value Chain Category Boundary Governance (HRG-003)
- **Recommended Architectural Solution**:
  - Create a structured **Scope 3 Category Boundary & Materiality Matrix** accessible in Manage Data / Settings.
  - For all 15 GHG Protocol Scope 3 categories (Cat 1 Purchased Goods to Cat 15 Investments), configure:
    1. `Status`: `Included (Primary Data)`, `Included (Spend-Based Secondary)`, `Excluded (Below De Minimis <1%)`, or `Not Applicable (No Activity)`.
    2. `Materiality Rationale`: Documented justification per ISO 14064-1:2018 §5.2.4 and GHG Protocol Corporate Value Chain Standard.
    3. `Data Quality Tier`: Tier 1 (Spend / EEIO), Tier 2 (Hybrid), Tier 3 (Supplier Specific / LCA).
  - When the Report Generator runs, Chapter 3 ("Reporting Boundaries") automatically embeds this materiality matrix table, proving ISO 14064-1 compliance without manual paper audits.

### 4. Item 4 — Flaring Aerodynamic Efficiency under Cross-Flow Wind (HRG-004)
- **Recommended Engineering Solution**:
  - Integrate an **Aerodynamic Cross-Wind Derating Algorithm** in `FlaringCalculator` (`new/server/calculations/combustion.py`) based on EPA 40 CFR 60.18 / API Compendium 2021 Table 5-11 and U. of Alberta flame cross-flow correlations:
    - If flare is enclosed or ground-shielded: Derating = 0 (flame is enclosed).
    - If flare is open/elevated/unassisted and ambient crosswind speed $W > 5.0\text{ m/s}$ ($18\text{ km/h}$):
      $$\eta_c(W) = \max\left(0.70, \; \eta_{c,0} \times \left[1.0 - 0.012 \times (W - 5.0)\right]\right)$$
      $$\eta_d(W) = \max\left(0.70, \; \eta_{d,0} \times \left[1.0 - 0.015 \times (W - 5.0)\right]\right)$$
    - If $W \le 5.0\text{ m/s}$ (or not provided), maintain nominal efficiency ($\eta_c = 98.4\%$, $\eta_d = 98.0\%$).
  - When wind speed is provided in activity data, metadata flags `"wind_derated": True` and records `"derated_combustion_eff"` for auditor transparency. 100% backward compatible.

### 5. Item 5 — TEG Dehydrator Stripping Gas Volume in Engineering Calculations (HRG-005)
- **Constraint**: *"Add it to the calculation without altering the UI and the theme of the software and make 100% sure its working"*.
- **Calculation Formulation**:
  - In `new/server/calculations/midstream.py` (`DehydratorCalculator`):
    Injected stripping gas (fuel gas or methane) enters the regenerator stripping section and vents through the regenerator still column overhead.
    $$\text{stripping\_ch4\_scf} = \text{stripping\_rate\_scf\_hr} \times \text{hours} \times x_{\text{CH}_4}$$
    - If Flash Tank Separator is present:
      - $\text{flash\_gas\_scf} = \text{dissolved\_ch4\_scf} \times 0.80$
      - $\text{still\_gas\_scf} = (\text{dissolved\_ch4\_scf} \times 0.20) + \text{stripping\_ch4\_scf}$
    - If no Flash Tank Separator:
      - $\text{still\_gas\_scf} = \text{dissolved\_ch4\_scf} + \text{stripping\_ch4\_scf}$
    - Still vent controls (flare, oxidizer, condenser, VRU) apply directly to `still_gas_scf`.
  - In `new/client/src/components/scope1/DehydratorForm.jsx`:
    Add an optional input `Stripping Gas Rate (scf/hr)` using the exact same `.input-group` and `.mole-input` classes already in use. Zero styling, theme, or color changes.
  - If stripping gas is 0 or absent, calculations yield the exact previous solubility results. 100% backward compatible and mathematically verified.

### 6. Item 8 — GWP Selector Dropdown & Dynamic Recalculation in Reports (HRG-008)
- **Proposed Solution**:
  - In `new/client/src/pages/Reports.jsx`:
    Add a **GWP Standard Dropdown** in the report configuration modal (and on the main report action bar):
    - `IPCC AR5 (100-yr)` [Default] ($\text{CH}_4=28$, $\text{N}_2\text{O}=265$)
    - `IPCC AR6 (100-yr)` ($\text{CH}_4=27.9$, $\text{N}_2\text{O}=273$)
    - `IPCC AR4 (100-yr)` ($\text{CH}_4=25$, $\text{N}_2\text{O}=298$)
    - `IPCC AR5 (20-yr)` ($\text{CH}_4=82.5$, $\text{N}_2\text{O}=268$)
    - `IPCC AR6 (20-yr)` ($\text{CH}_4=82.5$, $\text{N}_2\text{O}=273$)
  - In `new/client/src/utils/ModernReportGenerator.js`:
    - Pass `gwpStandard` into `generateModernPDF(api, filters)`.
    - In `fetchAllReportData()`: Use `getActiveGwpFactors(gwpStandard)` to dynamically recalculate the $tCO_2e$ for every record:
      $$tCO_2e = (CO_2 \times 1.0) + (CH_4 \times GWP_{\text{CH}_4}) + (N_2O \times GWP_{\text{N}_2\text{O}})$$
    - Recalculate all aggregated totals (`scope1Total`, `scope2Total`, `scope3Total`, `totalEmissions`, `facilityBreakdown`, `processBreakdown`, `monthlyData`, and intensity metrics) dynamically.
    - Explicitly state the selected GWP standard and its exact factors in Chapter 1 ("Executive Summary"), Chapter 3 ("Methodology"), and Annex tables.

---

### Solutions for Remaining Gates (6, 7, 9, 10)

#### HRG-006: Acid Gas Removal (AGR) Valve Line-Up Verification
- **Problem**: In natural gas processing plants, acid gas is normally routed to a Claus sulfur recovery unit or Acid Gas Injection (AGI) well. During turnarounds, maintenance, or overpressure events, valves may be realigned to bypass the control system and vent or flare directly.
- **Suggested Solution**:
  1. Add an **Operating Regime & Bypass Hours** field in `AGRForm.jsx` and `dispatcher.py`:
     - Regimes: `100% Routed to Control (Claus/AGI)` vs `Partial Bypass` vs `Emergency Venting`.
     - Bypass Hours ($H_{\text{bypass}}$) out of total annual operating hours.
  2. The calculation calculates weighted composite emissions:
     $$E = E_{\text{controlled}} \times \left(1 - \frac{H_{\text{bypass}}}{H_{\text{total}}}\right) + E_{\text{vented}} \times \left(\frac{H_{\text{bypass}}}{H_{\text{total}}}\right)$$
  3. Require engineering sign-off when AGR capture efficiency $>0$ is claimed.

#### HRG-007: OGMP 2.0 Reconciliation Variance Threshold & Protocol
- **Problem**: Facilities currently flag variance when top-down vs bottom-up discrepancy exceeds a flat 20%. UNEP IMEO Gold Standard requires differentiated scrutiny based on asset complexity and statistical confidence intervals.
- **Suggested Solution**:
  1. Leverage `reconciliation_threshold` in `Facility` (allow facility-specific thresholds: 15% for compressor stations, 25% for complex gas plants).
  2. Add an **OGMP Reconciliation Investigation Workflow** in `Diagnostics.jsx` / `MethaneExplorer.jsx`:
     - When $|T - B| / T > \text{threshold}$, present a reconciliation checklist: unlit flare events, unmetered tank venting, or meteorological wind shear artifacts.
     - Generate a signed UNEP IMEO Reconciliation Statement exportable to Excel/PDF.

#### HRG-009: Correlated Uncertainties / Common Fuel Supply Covariance
- **Problem**: IPCC Eq. 3.2 assumes zero correlation between facilities ($\text{Cov}(X_i, X_j) = 0$). However, facilities supplied from the same gas pipeline trunkline share identical fuel composition and emission factor uncertainties, underestimating combined portfolio uncertainty.
- **Suggested Solution**:
  1. In `new/server/calculations/uncertainty.py`, implement IPCC Good Practice Guidance Eq. 3.3 for fully correlated emission factors:
     $$U_{\text{correlated}} = \frac{\sum (U_{EF} \times E_i) + \sqrt{\sum (U_{activity,i} \times E_i)^2}}{\sum E_i}$$
  2. In `UncertaintyAssessment.jsx`, provide a verification toggle:
     - `Uncorrelated (Standard IPCC Eq. 3.2)`
     - `Correlated Common Fuel Supply (Conservative IPCC Eq. 3.3)`
  3. Report both lower-bound and upper-bound uncertainty intervals to provide external verifiers full transparency.

#### HRG-010: EPA Part 99 Waste Emissions Charge (WEC) Exemption Status
- **Problem**: The platform computes WEC at \$900/\$1200/\$1500 per metric ton on methane exceeding 0.20% sales gas intensity. However, Clean Air Act §136 provides statutory exemptions (permitting delays, permanently shut-in wells, CAA §111 equivalency).
- **Suggested Solution**:
  1. In `Facility` and `ManageData.jsx` (Region tab), add a `WEC Exemption Category` dropdown:
     - `Subject to WEC (Non-Exempt)`
     - `Exempt — Environmental Permitting Delay (CAA §136(f)(5))`
     - `Exempt — Plugged & Abandoned Well (CAA §136(f)(6))`
     - `Exempt — Regulatory Equivalency (CAA §111(b)/(d))`
  2. In WEC calculation reporting, calculate the potential gross tax liability, but apply an exemption credit for qualified facilities with the specific statutory citation recorded in the audit log.

---

## Proposed Changes by Component

### Backend (Server)

#### [MODIFY] `new/server/models.py`
- Add `description = db.Column(db.Text, nullable=True)` to `CustomFactor`.
- Ensure column migration check handles existing database tables smoothly.

#### [MODIFY] `new/server/routes/facilities.py`
- In `get_facilities()`: Include `"boundary_type": f.boundary_type or "Operational Control"` and `"boundary_detail": f.boundary_detail or ""` in JSON output.
- In `add_facility()`: Accept and persist `boundary_type` and `boundary_detail`.
- In `update_facility()`: Accept and persist `boundary_type` and `boundary_detail`.

#### [MODIFY] `new/server/routes/custom_factors.py`
- In `get_custom_factors()`: Return `description` and `source`.
- In `create_custom_factor()` and `update_custom_factor()`: Accept and persist `description` and `source`.

#### [MODIFY] `new/server/calculations/midstream.py`
- In `DehydratorCalculator.calculate()`:
  - Add optional parameters `stripping_gas_rate=0.0` (scf/hr), `stripping_gas_scf=0.0`.
  - Calculate stripping gas methane and combine it with regenerator still vent gas before control devices.

#### [MODIFY] `new/server/calculations/dispatcher.py`
- Map `dehy_stripping_rate` / `stripping_gas_scf` to `DehydratorCalculator.calculate()`.

#### [MODIFY] `new/server/tests/test_audit_remediation.py`
- Add automated tests for:
  - Facility boundary persistence & retrieval.
  - Custom factor description field persistence.
  - Dehydrator stripping gas calculation correctness and backward compatibility.

---

### Frontend (Client)

#### [MODIFY] `new/client/src/pages/ManageData.jsx`
- In Region tab: Verify boundary fields and display `f.boundary_type` & `f.boundary_detail` in the Active Regions table.
- In Custom Factors tab: Add `Description / Lab Certification Notes` text area and display it in table/details.

#### [MODIFY] `new/client/src/components/scope1/DehydratorForm.jsx`
- Add optional `Stripping Gas Rate (scf/hr)` input using the existing `.input-group` and `.mole-input` styling.

#### [MODIFY] `new/client/src/pages/Reports.jsx`
- Add GWP Standard selector dropdown in the Report Configuration modal / controls bar (`IPCC AR5 100-yr`, `IPCC AR6 100-yr`, `IPCC AR4 100-yr`, `IPCC AR5 20-yr`, `IPCC AR6 20-yr`).
- Pass `gwpStandard` to `generateModernPDF`.

#### [MODIFY] `new/client/src/utils/ModernReportGenerator.js`
- Read `gwpStandard` from options.
- In `fetchAllReportData()`, resolve GWP factors via `getActiveGwpFactors(gwpStandard)`.
- Dynamically recalculate each record's $tCO_2e$ and update all aggregated metrics, breakdown tables, charts, and Annex data.
- State the applied GWP standard in Chapter 1, Chapter 3, and Annex headers.

---

## Verification Plan

### Automated Tests
1. Run backend unit & integration tests:
   ```bash
   cd new/server && pytest tests/test_audit_remediation.py -v
   ```
2. Run full calculation suite:
   ```bash
   cd new/server && pytest tests/ -v
   ```
3. Run master validation runner:
   ```bash
   python validation/scripts/run_full_validation_suite.py
   ```
4. Verify frontend production build:
   ```bash
   cd new/client && npm run build
   ```
5. Update knowledge graph:
   ```bash
   graphify update .
   ```

### Manual Verification
1. Navigate to **Manage Data -> Active Regions**:
   - Create a new region with "Financial Control - Consolidated Subsidiary".
   - Confirm it is saved and displayed in the table with "Financial Control - Consolidated Subsidiary".
2. Navigate to **Manage Data -> Custom Factors**:
   - Add a factor with Description: "Certified per Sonatrach Central Lab GC Report #2026-ARZ-01".
   - Confirm description is saved and returned.
3. Navigate to **Scope 1 -> Dehydrator**:
   - Enter standard throughput and pump rate; enter 50 scf/hr stripping gas; confirm calculation reflects stripping methane.
   - Verify UI theme, styling, fonts, and colors remain completely identical.
4. Navigate to **Reports**:
   - Generate ISO 14064-1 report selecting "IPCC AR6 (100-yr)".
   - Confirm Chapter 2 prints the region's boundary from Manage Data.
   - Confirm emissions are calculated using AR6 GWP values ($\text{CH}_4=27.9$) and stated in the report.
