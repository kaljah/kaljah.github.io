# GHG Accounting Software - Phase 2 Verification Test Plan

> **Standards Baseline**: API Compendium 4th Edition (2021), GHG Protocol Corporate Standard, ISO 14064-1
> **Audit Scope**: End-to-End Independent Oracle Verification of Scope 1, Scope 2, and Scope 3 Calculations

---

## 1. Executive Summary & Audit Methodology
This test plan defines the complete coverage matrix and verification specifications for auditing the GHG calculation software.
Following strict non-negotiable rules:
- **Zero Fabricated Numbers**: All expected values derive strictly from API Compendium (2021) tables, equations, and exhibits or step-by-step hand-derived `Decimal` arithmetic.
- **Independent Oracle**: Test assertions compute expected values entirely within the test file using Python `Decimal` and `Fraction`. The application's own conversion or factor modules are NEVER imported to compute expected numbers.
- **No Tautologies**: Exact tight tolerances ($r_{tol} \le 10^{-4}$ for factor lookups, $10^{-5}$ for unit conversions). Tests are never adjusted to hide bugs.
- **Mutation Verification**: A systematic sample of tests will be perturbed (mutated) to prove they detect errors and fail when software deviates.

---

## 2. Comprehensive Coverage Matrix

### Coverage Cell Count Breakdown
| Dimension / Subsystem | Entity Count | Test Matrix Cells | Verification Mechanism |
| :--- | :--- | :--- | :--- |
| **Unit Conversions (Pairwise & Chains)** | 46 pairs, 8 dimension maps | 184 | NIST SP 811 & API Compendium Section 3 exact Decimal ratios |
| **Default Catalog Emission Factors** | 180 API + 105 Activity factors | 285 | 1-to-1 matching against API Compendium 2021 Tables 3-x, 4-x, 5-x, 6-x, 7-x |
| **Scope 1: Tier 1 Process Calculations** | 28 processes across 150 units | 450 | Known-answer tests: quantity x factor x GWP |
| **Scope 1: Tier 2 Custom / HHV / Density** | 28 processes | 112 | Site-measured energy basis and mass-volume cross-conversions |
| **Scope 1: Tier 3 Physical Engineering Models** | 14 specialized process schemas | 45 | Stoichiometric, Vasquez-Beggs, ideal gas blowdown, Method 21 correlations |
| **Scope 2: Grid & Purchased Energy** | 4 source types, 61 grid regions | 244 | eGRID 2022 / IEA emission factor calculations (Location & Market based) |
| **Scope 3: Corporate Value Chain** | 15 categories, 55 activity rows | 110 | EPA EEIO & DEFRA/BEIS spend- and activity-based factor models |
| **TOTAL COVERAGE CELLS** | - | **1145** | - |

---

## 3. Test File Architecture (`tests/test_full_pipeline_audit.py`)

The single verification audit file is organized into 9 formal sections:

### Section A: Reference Oracle & Authoritative Constants
- All physical constants transcribed in `Decimal`:
  - Standard temperature $T_{std} = 288.71\text{ K}$ ($60^\circ\text{F}$)
  - Standard pressure $P_{std} = 101.325\text{ kPa}$ ($14.696\text{ psia}$)
  - Molar volume $V_m = 23.6853\text{ m}^3/\text{kmol}$ ($379.3\text{ scf/lb-mol}$)
  - Standard densities: $\rho_{\text{CH}_4} = 0.67722\text{ kg/m}^3$, $\rho_{\text{CO}_2} = 1.85814\text{ kg/m}^3$
  - Molecular weights: $C = 12.011, H = 1.008, O = 15.999, N = 14.007, S = 32.06$
  - GWP sets: AR4, AR5 (100-yr and 20-yr), AR6

### Section B: Unit Conversion Suite
- Forward conversion: $A \to B$
- Reverse conversion: $B \to A$ ($A \to B \to A = A$)
- Identity conversion: $A \to A = A$
- Path independence: $A \to B \to C == A \to C$
- Compound conversions: Volume $\leftrightarrow$ Mass via density; Volume $\leftrightarrow$ Energy via HHV
- Temperature & Pressure conversions: Gauge to Absolute ($P_{abs} = P_{gauge} + 14.696$)

### Section C: Default Emission Factor Parity
- Verifies all 180 `API_FACTORS` and 105 `ACTIVITY_FACTORS` against API Compendium 2021 tables:
  - Factor numerical value, unit basis, gas species breakdown ($CO_2, CH_4, N_2O$)
  - Fuel and process categorization mapping
  - Uncertainty percentages (95% confidence half-width)

### Section D: Per-Process-Type Known-Answer Tests
- Exhaustive test cases for every process type and tier:
  - Known hand-calculated inputs with step-by-step arithmetic in docstrings/comments
  - Parameterized across all allowed units per process

### Section E: Scenarios, Magnitudes, and End-to-End Workflows
- Dynamic magnitudes: Zero ($0.0$), Tiny ($10^{-6}$), Typical ($10^3$), Large ($10^6$), Very Large ($10^9$)
- Realistic multi-source scenarios:
  - Scenario A: Upstream Onshore Gas Production Facility
  - Scenario B: Midstream Transmission Compressor Station
  - Scenario C: Downstream Refinery / Petrochemical Complex
- Recalculation and edit/delete consistency

### Section F: Metamorphic Invariance Properties
- **Linearity**: $f(k \times x) == k \times f(x)$
- **Unit Invariance**: $1000\text{ scf}$ natural gas combusted must yield the exact same emissions as $28.3168\text{ m}^3$ within conversion tolerance
- **Additivity**: $f(x_1 + x_2) == f(x_1) + f(x_2)$
- **Monotonicity**: $x_1 > x_2 \implies f(x_1) > f(x_2)$
- **Aggregation Integrity**: Corporate total = $\sum \text{Facility totals} = \sum \text{Scope totals}$

### Section G: Pipeline Integrity & Layer Equivalence
- Equivalence across execution layers:
  - Direct Python calculation module $\equiv$ CalculationDispatcher $\equiv$ Flask API endpoint $\equiv$ SQLite persisted record $\equiv$ Dashboard aggregate $\equiv$ CSV/Excel export
- Stored vs Recomputed parity
- Float precision preservation

### Section H: Input Robustness & Error Handling
- Malformed / edge cases:
  - Negative quantities, `None`, empty string, alphanumeric text in numeric fields
  - Comma decimal formatting (`1,234.56` vs `1234,56`)
  - Scientific notation (`1.5e6`)
  - Unsupported units and non-existent fuel types
- Ensures proper HTTP 422 / ValidationError and never a silent wrong calculation

### Section I: Introspection & Coverage Guards
- Introspects live application registry:
  - Asserts that 100% of process types, allowed units, and default factors are present in the test parametrization
  - FAILS immediately if a developer adds a new process type or factor to the software without adding test coverage

---

## 4. Unverified & Excluded Items
| Item | Category | Reason for Unverified / Excluded Status | Audit Action |
| :--- | :--- | :--- | :--- |
| CBAM specific embedded emissions (`cbam_product_exports`) | Scope 3 / Regulatory | EU CBAM regulation uses EU ETS benchmark rules not in API Compendium | Tested for mathematical consistency; labeled `UNVERIFIED_BENCHMARK` |
| SBTI Trajectory Target Equations (`sbti_targets`) | Corporate Reporting | Targets are linear annual reduction trajectories rather than emission physics | Tested for linearity; excluded from API Compendium pass/fail |
