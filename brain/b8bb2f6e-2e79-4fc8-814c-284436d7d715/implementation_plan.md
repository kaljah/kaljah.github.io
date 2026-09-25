# GHG / MRV Platform — Full Calculation, Logic, Security & Production Validation

Comprehensive Independent Verification & Validation (IV&V) plan for the GHG Accounting, Emissions Analytics, MRV, and Reporting platform (`https://github.com/kaljah/kaljah.github.io`).

## User Review Required

> [!IMPORTANT]
> **Zero Circular Validation Principle**: Production calculation logic is never validated against itself. All validation checks compare production results against an isolated, pure-Python independent reference model (`validation/reference_model/`) derived directly from authoritative international standards (API Compendium 2021, GHG Protocol, IPCC 2006, OGMP 2.0, EPA Subpart W). The reference model has zero imports or dependencies on production code.

> [!WARNING]
> **Strict Sequence: No Premature Formula Changes**: In strict accordance with the master validation rules, NO production calculation formulas will be modified during Phases 1 through 7. Discrepancies will first be documented, classified (CRITICAL / HIGH / MEDIUM / LOW), and verified against authoritative methodology before any fix is applied in Phase 12.

> [!CAUTION]
> **Human Review Gates**: Any scenario involving ambiguous regulatory standards, unverified lab custom factors, or equity-share boundaries will be explicitly flagged into `docs/validation/HUMAN_REVIEW_REQUIRED.md` rather than having assumptions automated silently.

---

## Open Questions

1. **Obsolete Root Scratch & Legacy Scripts**: The repository contains obsolete one-off patch scripts in the root directory (`patch.py`, `patch_ci.py`, `patch_manage_data.py`, `patch_s3.py`, `test_runner.py`) and legacy Node/Electron files (`server.js`, `main.js`, root `package.json`). We recommend formally archiving or isolating these in `temp_old/` or documenting their deprecated status in `docs/validation/repository-audit.md` so they do not contaminate test runners or CI/CD pipelines.
2. **Custom Factors in `custom_factors.csv`**: `custom_factors.csv` contains synthetic benchmark factors (e.g. Custom Gas Factor 0: $\text{CO}_2=144.56$). These will be validated for numerical constraints, non-negativity, and unit conversion, but certified via Human Review Gate **HRG-002** for production facility use.

---

## Proposed Changes & 15-Phase Execution Plan

### Phase 1: Complete Repository Audit
- Conduct an exhaustive audit of all directories: `new/server/`, `new/client/`, `docs/`, `validation/`, root scripts, configs, migrations, and CI workflows.
- Classify every file: **Active**, **Legacy**, **Duplicated**, **Obsolete**, or **Patch**.
- Trace active calculation dispatch paths through `new/server/calculations/dispatcher.py` vs legacy fallbacks in `legacy_engine.py`.
- Finalize and document findings in [repository-audit.md](file:///c:/Users/samsung/Desktop/H2/docs/validation/repository-audit.md).

### Phase 2: Calculation Inventory & Authoritative Methodology Matrix
- Catalog all calculations across 42 process subsystems (Stationary Combustion, Flaring, Mud Degassing, Completions, Liquids Unloading, Blowdown, Tanks, Pneumatics, Fugitives, AGR, Dehydrators, Indirect Steam, CHP Cogeneration, Stoichiometry, Scope 2, Scope 3 Categories 1–15, Uncertainty, Intensity, WEC, OGMP 2.0).
- For every equation, document: ID, file, equation, inputs, units, outputs, methodology standard, factor catalog, GWP horizon, precision rules, and risk rating.
- Update and audit [calculation-inventory.md](file:///c:/Users/samsung/Desktop/H2/docs/validation/calculation-inventory.md) and [methodology-matrix.md](file:///c:/Users/samsung/Desktop/H2/docs/validation/methodology-matrix.md).

### Phase 3: Existing Test Suite Audit
- Audit all 934 tests in `new/server/tests/`: verify coverage, assertions, test isolation (in-memory SQLite session vs dev DB), and eliminate any vacuous or tautological tests.
- Resolve test collection blockers (e.g., `new/server/test_runner.py` legacy import errors when running pytest from root).

### Phase 4: Audit `1k_scope1_comprehensive_test.csv`
- Audit generation script `new/server/generate_1k_comprehensive.py`.
- Analyze all 1,001 rows: verify that it serves as an input pipeline fuzzing / boundary test harness (with deliberate missing-date, missing-facility, and invalid-number error injections) rather than precalculated expected emission truths.
- Document its exact role and boundaries in the audit report.

### Phase 5: Independent Reference Model Verification
- Audit `validation/reference_model/` (12 modules: `combustion_flaring.py`, `vented_processes.py`, `fugitives.py`, `midstream.py`, `scope2.py`, `scope3.py`, `stoichiometry.py`, `uncertainty.py`, `unit_conversions.py`, `aggregation_intensity.py`, `ogmp.py`, `gwp.py`).
- Verify zero imports of production code (`new/server`).
- Verify adherence to API Compendium (2021), GHG Protocol Scope 2 & Scope 3, IPCC (2006), and ISO 13443 standard conditions ($60^\circ\text{F}, 14.696\text{ psia}$).

### Phase 6: Golden Validation Dataset
- Audit `validation/golden_dataset/golden_cases.json` and `dataset_generator.py`.
- Verify coverage across categories A through Q: Normal, Zero, Minimum, Maximum, Small, Large, Decimal, Multiple Units, Multi-Gas, Default/Custom factors, Missing/Invalid inputs, Historical years, and multi-facility cases.

### Phase 7: Differential Testing
- Run automated differential test suite comparing the production engine (`CalculationDispatcher`) against `validation/reference_model/` across all golden test cases and randomized vectors.
- Enforce strict numerical tolerance ($\text{rtol} \le 10^{-5}$ for continuous, exact IEEE-754 for discrete conversions).

### Phase 8: Property-Based Testing
- Execute Hypothesis property invariants in `new/server/tests/test_property_invariants.py`:
  - Zero Invariance: $f(0) = 0$
  - Linearity: $f(k \cdot x) = k \cdot f(x)$ for linear fuel/activity paths
  - Additivity: $f(A + B) = f(A) + f(B)$
  - Monotonicity: $A > B \implies f(A) \ge f(B)$
  - Non-negativity: $f(x) \ge 0$ for all physical inputs $x \ge 0$.

### Phase 9: Mutation Testing
- Execute `validation/mutation/test_calculation_mutations.py` to verify that injected mathematical bugs (inverted operators, wrong GWP, distorted densities, omitted stoichiometry) are 100% detected and killed.

### Phase 10: Integration, API, Database, Concurrency & E2E Testing
- Validate REST APIs: status codes, validation error payloads, transaction rollbacks on failure.
- Validate RBAC and Row-Level Security: ensure users cannot access or alter other facilities/regions, and IT Admin is barred from operational GHG data.
- Validate Maker-Checker workflow: bulk imports default to `Pending`, approval transitions to `Verified`, activity edits recalculate `co2e` and reset to `Pending`.
- Validate Concurrency: thread safety and session rollback protection under simultaneous modifications.
- Validate Reports: PDF, Excel, and CSV export parity with database and dashboard values.

### Phase 11: Security, Performance & Build Testing
- Verify session lifetimes, secure cookies, CSRF protection, rate limiting, and SQL injection / LIKE wildcard escaping.
- Benchmark calculation engine throughput (single calculation, 1k batch, 10k batch).
- Verify multi-stage Docker build and clean dependency installation.

### Phase 12: Verified Software Defect Fixes
- Address any verified software defects or inconsistencies discovered during testing (e.g. frontend fallback alignment `264` vs `268` in `new/client/src/constants.js`, isolating legacy `test_runner.py`).

### Phase 13: Regression Archive
- Add permanent regression test cases in `validation/regression/test_regression_archive.py` with full documentation (Bug ID, Root Cause, Reference Standard, Fix, Test).

### Phase 14: Comprehensive Verification Run
- Execute the complete test suite across all subsystems from a clean test environment to guarantee 100% pass rate.

### Phase 15: Final Deliverables & Governance Gates
- Update [FINAL_VALIDATION_REPORT.md](file:///c:/Users/samsung/Desktop/H2/docs/validation/FINAL_VALIDATION_REPORT.md) with comprehensive component test matrices, defect severity breakdowns, and production-readiness verdict.
- Update [HUMAN_REVIEW_REQUIRED.md](file:///c:/Users/samsung/Desktop/H2/docs/validation/HUMAN_REVIEW_REQUIRED.md) with all governance gates (HRG-001 through HRG-010).

---

## Verification Plan

### Automated Tests
- Full Pytest suite in `new/server`: `pytest -v`
- Reference model differential suite: `pytest tests/test_independent_differential.py`
- Golden dataset suite: `pytest tests/test_golden_dataset_validation.py`
- Property invariant suite: `pytest tests/test_property_invariants.py`
- Mutation testing suite: `pytest validation/mutation/test_calculation_mutations.py`
- Regression archive suite: `pytest validation/regression/test_regression_archive.py`
- Unit conversions exhaustive: `pytest tests/test_unit_conversions_exhaustive.py`
- Security & RBAC suite: `pytest tests/test_api_security.py tests/test_it_role_security.py`
- Performance & stress benchmarks: `pytest tests/test_performance.py tests/test_stress_bulk_pipeline.py`

### Manual Verification
- Review generated reports (PDF, CSV, Excel) for exact visual and numerical parity.
- Review and certify Human Review Gates in `HUMAN_REVIEW_REQUIRED.md`.
