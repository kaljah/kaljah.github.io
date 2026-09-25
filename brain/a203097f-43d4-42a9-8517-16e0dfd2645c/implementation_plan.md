# Implementation Plan: Clean-Slate Software Validation, Security & GHG Calculation Audit from Zero

Perform a completely independent, clean-slate validation of the Greenhouse Gas (GHG) Accounting & Reporting Platform from zero, adhering strictly to the user's critical requirement: **DO NOT USE THE OLD TESTS**.

---

## 1. Clean-Slate Validation Architecture

Treat all 47+ existing test files, scripts, and previous QA artifacts as untrusted legacy material. All new tests and expected values will be designed and implemented independently from mathematical, physical, and regulatory principles in a dedicated `validation/` directory structure.

```
validation/
├── reference_model/          # Completely independent math & physics models (no production imports)
│   ├── ref_combustion.py     # Stationary & mobile combustion, thermodynamic normalization
│   ├── ref_flaring.py        # Dual-efficiency flaring model, uncombusted slip, native CO2
│   ├── ref_venting.py        # Tank flashing, pneumatics, blowdown, liquids unloading, well completion
│   ├── ref_midstream.py      # Acid Gas Removal (AGR) and Glycol Dehydration
│   ├── ref_fugitives.py      # Component and equipment fugitive leak screening
│   ├── ref_scope2.py         # Location & Market-based electricity, steam, heating, cooling
│   ├── ref_scope3.py         # All 15 GHG Protocol Scope 3 categories (EEIO, travel, freight, etc.)
│   ├── ref_stoichiometry.py  # Molecular weights, reaction stoichiometry, carbon mass balance
│   ├── ref_gwp.py            # IPCC AR4, AR5, AR6 (100-yr & 20-yr) standards
│   ├── ref_units.py          # Exact physical unit conversion factors & round-trip transformations
│   ├── ref_uncertainty.py    # Analytical Gaussian error propagation & confidence intervals
│   └── ref_intensity.py      # Carbon intensity (kg CO2e/boe) & OGMP 2.0 level scoring
├── golden_data/              # Independently generated golden dataset (documented derivation)
│   ├── golden_cases.json     # Comprehensive dataset (normal, boundary, invalid, multi-tier)
│   └── golden_generator.py   # Independent dataset generator with intermediate & expected values
├── calculation/              # Clean-slate tests for every calculation path
│   ├── test_clean_scope1.py
│   ├── test_clean_scope2.py
│   ├── test_clean_scope3.py
│   ├── test_clean_stoichiometry.py
│   ├── test_clean_emission_factors.py
│   ├── test_clean_gwp.py
│   ├── test_clean_units.py
│   └── test_clean_uncertainty.py
├── property/                 # Property-based tests (Hypothesis)
│   └── test_clean_properties.py # Zero, scaling, additivity, unit invariance, monotonicity
├── mutation/                 # Mutation testing engine
│   └── test_clean_mutations.py  # Formula & coefficient mutations verified killed
├── differential/             # Differential testing engine
│   └── test_clean_differential.py # Production Engine vs Reference Model comparison
├── unit/                     # Unit tests for core utilities, validators, serializers
│   └── test_clean_unit.py
├── api/                      # Clean REST API tests
│   └── test_clean_api.py        # Full endpoint coverage, boundary, invalid, side effects
├── security/                 # Security & RBAC tests
│   └── test_clean_security.py   # Auth, cross-org/region isolation, SQLi, XSS, CSRF, rate limits
├── database/                 # Database schema, foreign keys, cascades, constraints
│   └── test_clean_database.py
├── integration/              # Transactions & concurrency tests
│   └── test_clean_integration.py# Atomicity, rollback, race conditions, duplicate prevention
├── e2e/                      # End-to-end full life-cycle workflows & network failure tests
│   ├── test_clean_e2e.py        # Complete user workflow (auth -> data -> calc -> approval -> report)
│   └── test_clean_network.py    # Backend errors, timeouts, 4xx/5xx resilience
├── performance/              # Performance & load tests
│   └── test_clean_performance.py# Latency percentiles (p50/p95/p99), calculation throughput
└── reports/                  # Generated test evidence & differential analysis output
```

---

## 2. Legacy Test Suite Audit

Inspect existing test suites across `new/server/tests` (47 files, 436 functions), `new/client/tests`, and root test scripts without reusing them as validation evidence.
Create:
- `docs/validation/LEGACY_TEST_AUDIT.md`
  - Document framework, total test count, covered vs unaddressed areas
  - Identify circular assertions, production function imports, weak status-code-only checks, obsolete scripts, and mock logic.

---

## 3. Independent Reference Model & Golden Dataset

Build independent reference models in `validation/reference_model/` using first-principles physics and regulatory equations (API Compendium 2021, GHG Protocol, IPCC AR5/AR6, ISO 14064, ISO 13443):
- **Combustion**: Fuel energy balance, temperature/pressure thermodynamic gas volume normalization ($V_{\text{std}} = V_{\text{meas}} \times \frac{P_{\text{meas}}}{P_{\text{std}}} \times \frac{T_{\text{std}}}{T_{\text{meas}}} \times \frac{1}{Z}$).
- **Flaring**: Dual-efficiency flaring model ($\eta_c$, $\eta_d$, uncombusted slip = $1 - \eta_c$, stoichiometric $\text{CO}_2$ from combusted methane $\times \frac{44.01}{16.043}$ + native $\text{CO}_2$, $\text{N}_2\text{O}$ from flared heat).
- **Venting & Midstream**: Tank flashing, blowdown, pneumatics, liquids unloading, completions, AGR linear removal $(1 - \text{eff})$, dehydrators.
- **Scope 2 & Scope 3**: Location and Market-based electricity, steam/heat/cooling distribution loss, all 15 Scope 3 categories.
- **Stoichiometry & Unit Conversions**: Molecular weights ($MW_{\text{CH}_4}=16.043$, $MW_{\text{CO}_2}=44.01$, etc.), exact NIST avoirdupois and ISO unit conversions.
- **Golden Dataset**: Independent test vectors generated with full derivation records (test_id, inputs, units, methodology, intermediate steps, expected results, tolerances).

---

## 4. Execution of the Clean-Slate Test Suite

Execute the entire clean-slate test suite across all 15 test categories:
1. **Reference & Golden Validation**: Verify golden test cases against reference model.
2. **Calculation Path Verification**: Verify all Scope 1, Scope 2, Scope 3 paths in the production engine.
3. **Property-Based Testing**: Run Hypothesis invariant checks (Zero property, Scaling, Additivity, Unit invariance, Monotonicity).
4. **Mutation Testing**: Apply intentional mutations (+ to -, * to /, factor errors, GWP errors, dropped terms) and verify 100% mutation kill rate.
5. **Differential Testing**: Execute Production Engine vs Reference Model on all cases and record absolute and relative differences with tolerance checks.
6. **Unit & API Testing**: Execute comprehensive unit and API endpoint tests (boundary, invalid, malformed, unauthorized, 401/403/404/422).
7. **Security & Authorization (RBAC/RLS)**: Verify password hashing, session lifecycle, rate limiting, and cross-facility/cross-region access isolation.
8. **Database & Transactions**: Schema constraints, singleton base year constraint, foreign keys, cascades, rollback on mid-operation failure.
9. **Concurrency & Integration**: Simultaneous edits, race conditions, deduplication.
10. **E2E & Network Resilience**: Complete user journey lifecycle, backend degradation/error simulation.
11. **Performance & Load**: Latency measurements (avg, p95, p99), calculation engine stress testing.
12. **Frontend, Accessibility & Responsiveness**: Vite production build verification, component rendering, accessibility ARIA and keyboard audit.

---

## 5. Final Reporting & Verification Matrices

Create `docs/validation/FINAL_VALIDATION_REPORT.md` featuring:
1. **32-Category Final Validation Matrix**:
   - Status (NEWLY TESTED, OLD TESTS ONLY, NOT TESTED, N/A, HUMAN REVIEW, PASS, FAIL, PARTIAL)
   - New tests created, executed, passed, failed, evidence, issues identified.
2. **GHG Calculation Matrix**:
   - Complete breakdown by calculation pathway: Independent Reference, Golden Cases, Property Tests, Mutation Tests, Differential Results.
3. **Defect Classification**:
   - CRITICAL, HIGH, MEDIUM, LOW defect triage.
4. **Production Readiness Summary**:
   - Build health, environment configuration, dependency security, observability, backup/restore evaluation.

---

## User Review Required

> [!IMPORTANT]
> The audit is completely clean-slate and designed from zero. All legacy tests are documented in `LEGACY_TEST_AUDIT.md` but are **not** treated as validation evidence. The new validation suite lives entirely in `validation/` and does not overwrite or destroy legacy project files.

Do you approve proceeding with this clean-slate validation plan?
