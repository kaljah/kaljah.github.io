# Legacy Test Suite Audit: Clean-Slate Baseline Review

**Document Version:** 1.0.0  
**Audit Date:** 2026-09-20  
**Author:** Clean-Slate QA & Security Validation Engine  
**Standard:** Clean-Slate Software Validation from Zero  

> [!CRITICAL]
> **DISCLAIMER & FINAL COMMANDMENT:**
> This audit evaluates the legacy test artifacts for informational and gap-identification purposes only.
> **THIS AUDIT DOES NOT TURN OLD TESTS INTO VALIDATION EVIDENCE.**
> All legacy tests, assertions, fixtures, generated scripts, and previous PASS results are classified as **untrusted legacy material**.
> The final validation of the current software is derived entirely from the new clean-slate test suite implemented in `validation/`.

---

## 1. Executive Summary & Inventory

The repository contains legacy test artifacts scattered across multiple directories representing several generations of development, ad-hoc patching, and earlier testing passes.

| Location | Number of Test Files | Test Count / Functions | Test Framework | Primary Intent |
|---|---|---|---|---|
| `new/server/tests/` | 47 | 436 functions | Pytest + Flask Test Client | Unit, API, calculation regression, security |
| `new/server/` (root) | 4 | ~35 functions | Pytest / Custom scripts | CSV upload, calculations, runner |
| `new/` (root scripts) | 8 | ~40 functions | Pytest / Ad-hoc scripts | Button audit, API health, pipeline tests |
| `new/client/tests/` & `src/__tests__/` | 8 | ~25 test suites | Node.js (mjs) / Vitest | UI stress, parsing, visual audits, numerical parity |
| `validation/` (legacy) | 6 | ~30 functions | Pytest | Previous experimental validation artifacts |
| **Total Legacy Inventory** | **73 files** | **~566 tests** | Mixed (Pytest, Node, Python scripts) | Untrusted Legacy Material |

---

## 2. Framework & Infrastructure Analysis

- **Backend Test Framework:** Pytest 9.1.1 using Flask's `test_client()` via `conftest.py`.
- **Database Strategy in Legacy Tests:**
  - `conftest.py` spins up an in-memory SQLite database (`sqlite:///:memory:`) or targets a local temporary test database.
  - Fixtures populate mock facilities, users, and emission factors.
- **Frontend Test Framework:** Vitest / Native Node.js `.mjs` scripts running ad-hoc assertions with Axios or JSDOM.

---

## 3. Critical Flaws in the Legacy Test Suite

A rigorous inspection of the 47 `new/server/tests/` files revealed structural anti-patterns that prevent them from serving as independent validation evidence:

### 3.1 Circular Calculation Tests (Self-Referential Assertions)
- **Files identified:** 30 out of 47 files directly import production logic (`from calculations.dispatcher import CalculationDispatcher`, `from calculations.units import CONVERSIONS`, `from calculations.combustion import CombustionCalculator`).
- **Defect:** Expected values were calculated by running the production code or replicating identical production helper formulas in test fixtures. If a production formula contained a systematic physical error (e.g. stoichiometric flaring factor or thermodynamic gas volume conversion), the test asserted `result == production_algorithm(input)`, creating a circular PASS.

### 3.2 Tests with Weak or Trivial Assertions (Status-Code Only)
- Multiple API tests (e.g. in `test_all_apis_health.py` and parts of `test_api_security.py`) only checked `assert res.status_code == 200` without inspecting the payload body, headers, or verifying database state mutations.
- In particular, several calculation preview endpoints checked that a JSON dict was returned without validating the numerical accuracy of `co2e_total`, `ch4_emissions`, or `qa_flag`.

### 3.3 Over-reliance on Mock Logic
- Legacy scripts such as `services/erp_integration.py` and mock tests inserted canned Scope 3 and Scope 2 records with hardcoded dummy facility IDs (`facility_id = 1`) rather than testing real multi-tenant facility isolation.

### 3.4 Suspicious and Potentially Incorrect Expected Values
- **Flaring N2O Consistency:** Legacy flaring tests used historical kg/MMBtu emission factors with volume multipliers rather than verifying dual-efficiency destruction ($\eta_c$, $\eta_d$) and stoichiometric methane slip against independent thermodynamic references.
- **GWP Horizon Drift:** Tests in `test_gwp_dynamic.py` and `test_battery_gwp_horizons_regulatory.py` tested table lookups but did not independently verify the numerical effect of switching between AR4 (CH4=25), AR5 (CH4=28), and AR6 (CH4=27.9) across compound process streams.
- **Unit Conversions:** Conversions in `test_unit_conversions_exhaustive.py` relied on `CONVERSIONS` dict imported directly from `calculations/units.py`. If a constant in `CONVERSIONS` was misstated, the test would blindly pass.

### 3.5 Obsolete and Deprecated Scratch Files
- In `new/`, scripts like `test_final.py`, `test_final_v2.py`, `test_final_v3.py`, `test_pipeline.py`, and `test_pipeline_robust.py` were one-off scratch scripts written during past debugging sessions. Many are stubs or duplicate logic found in `test_all_bulk_imports.py`.

---

## 4. Coverage Gap Analysis (What the Legacy Suite Missed)

| Category | Legacy Status | Critical Gaps Identified |
|---|---|---|
| **Independent Reference Models** | **ABSENT** | Zero independent physics/math reference engines existed outside production code. |
| **Differential Testing** | **SUPERFICIAL** | `test_independent_differential.py` imported internal helper functions rather than executing against an isolated external reference model. |
| **Property-Based Invariants** | **LIMITED** | Property tests only covered simple arithmetic scaling, omitting true mathematical properties (zero invariance, additivity, dimensional invariance, monotonicity). |
| **Mutation Testing** | **ABSENT** | No automated mutation verification existed to verify that deliberate formula mutations (+ to -, / to *, wrong factor, dropped slip term) are caught and killed. |
| **Cross-Tenant RLS & Regional Isolation** | **PARTIAL** | Region checks were tested only for specific endpoint happy paths; deep cross-organization penetration attempts (e.g. bulk export, report filtering, cascade deletes) were incomplete. |
| **Network & Degradation Resilience** | **ABSENT** | No tests simulated mid-stream network dropped packets, 502/504 gateways, or slow DB lock contention. |
| **Accessibility & WCAG 2.1 AA** | **ABSENT** | No automated ARIA, contrast, focus trapping, or screen-reader semantic verification. |

---

## 5. Conclusion & Transition to Clean-Slate Validation

The legacy test suite is completely decommissioned for the purposes of this audit. The clean-slate validation built in `validation/` will address every gap:
1. Pure first-principles reference models in `validation/reference_model/` with zero production imports.
2. Independently documented golden dataset in `validation/golden_data/`.
3. 100% clean-slate tests spanning calculations, security, RBAC, database integrity, integration, property-based invariants, mutations, differential runs, E2E workflows, and performance.
