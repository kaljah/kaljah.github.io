# Phase 1 — Testing Inventory

> Audit Date: 2026-09-20  
> Platform: GHG/MRV Accounting Platform  
> Repository: `C:\Users\samsung\Desktop\H2`

---

## 1. Backend Test Infrastructure

### Framework
- **Runner**: `pytest` (configured via `new/server/pytest.ini` and root `pytest.ini`)
- **Plugins detected**: `hypothesis` (property-based testing), `pytest-approx` (numeric tolerance)
- **Fixture mechanism**: `conftest.py` in `new/server/tests/` — disables Flask-Limiter for test runs
- **Database**: Uses the live `ghg_app.db` SQLite file (not isolated test DB) — see NOTE below
- **Mock services**: None — tests call production code directly
- **Authentication testing**: Fixtures create test users in the live database and clean up afterward

> **⚠️ NOTE — Test Database Isolation Issue:**  
> Tests run against the live production database (`ghg_app.db`). There is no `TEST_DATABASE_URL` environment variable or in-memory SQLite fixture. Tests that create users/emissions insert and then delete from the production database. This is a risk in production deployment scenarios.

### Test Run Results (2026-09-20)
```
Command:  python -m pytest tests/ --tb=short -q
Result:   880 passed, 0 failed, 13 warnings
Duration: 142.57s (2:22)
Exit code: 0
```

### Test Commands
```bash
# Run full backend suite
cd new/server
python -m pytest tests/

# Run specific test file
python -m pytest tests/test_combustion.py -v

# Run with coverage (not configured — no pytest-cov in requirements)
python -m pytest tests/ --cov=calculations

# Run property-based tests only
python -m pytest tests/test_property_invariants.py -v

# Run differential tests only
python -m pytest tests/test_independent_differential.py -v
```

---

## 2. Backend Test Files Inventory (43 files, 880 tests)

| File | Category | Tests (approx) | Notes |
|---|---|---|---|
| `test_aggregation_reconciliation.py` | Business Logic | ~8 | Rollup, gas balance, intensity |
| `test_all_bulk_imports.py` | Integration | ~25 | CSV/Excel upload scenarios |
| `test_all_process_types_matrix.py` | Calculation | ~30 | All process types via dispatcher |
| `test_api_security.py` | Security | ~25 | Auth, IDOR, input limits |
| `test_audit.py` | Audit | ~15 | Audit log creation, access |
| `test_audit_bug_fixes.py` | Regression | ~8 | Specific audit bug fixes |
| `test_audit_remediation.py` | Audit | ~40 | Comprehensive audit remediation |
| `test_battery_compressor_fugitives_equipment.py` | Calculation | ~12 | Compressor seal, equipment fugitives |
| `test_battery_concurrency_stress_invariants.py` | Concurrency | ~10 | Thread-safety, race conditions |
| `test_battery_gwp_horizons_regulatory.py` | GWP | ~15 | AR4/AR5/AR6, 20/100yr horizons |
| `test_battery_midstream_process_equipment.py` | Calculation | ~20 | AGR, dehydrators |
| `test_battery_statistical_anomaly_detection.py` | Analytics | ~10 | Z-score, IQR anomaly detection |
| `test_battery_stoichiometry_indirect_energy.py` | Calculation | ~15 | Stoichiometry, indirect steam |
| `test_boundary_and_negative.py` | Edge Cases | ~15 | Zero, negative, boundary inputs |
| `test_calculations_page.py` | Integration | ~15 | Calculation workflow via API |
| `test_combustion.py` | Calculation | 3 | Flaring + stationary combustion |
| `test_csv_engine_matrix.py` | Integration | ~30 | CSV parsing matrix |
| `test_deep_injection_matrix.py` | Security | ~35 | SQL injection, XSS, path traversal |
| `test_dispatcher.py` | Calculation | ~15 | Dispatcher routing |
| `test_emission_factor_selection.py` | EF | ~12 | Factor catalog selection |
| `test_golden_dataset_validation.py` | Golden | 25 | 25 authoritative golden cases |
| `test_gwp_dynamic.py` | GWP | ~8 | Dynamic GWP standard resolution |
| `test_independent_differential.py` | Differential | ~30 | Prod vs reference model comparison |
| `test_it_role_security.py` | Security | ~15 | IT role data isolation |
| `test_numerical_invariants.py` | Math | ~40 | Numerical stability, precision |
| `test_operational_defaults.py` | Business | ~10 | Default factor behavior |
| `test_property_invariants.py` | Property | ~15 | Hypothesis: linearity, monotonicity |
| `test_qaqc_diagnostics.py` | QA/QC | ~10 | QA flag generation |
| `test_reports.py` | Reporting | ~15 | PDF, Excel, CSV reports |
| `test_satellite.py` | Integration | ~5 | Satellite data endpoints |
| `test_sbti.py` | Business | ~8 | SBTi target management |
| `test_stress_boundary_resilience.py` | Stress | ~15 | Extreme value handling |
| `test_stress_bulk_pipeline.py` | Stress | ~10 | Large dataset throughput |
| `test_stress_concurrency.py` | Concurrency | ~15 | Multi-thread operation safety |
| `test_stress_memory_leaks.py` | Stress | ~12 | Memory stability |
| `test_stress_volume_analytics.py` | Stress | ~10 | Volume analytics under load |
| `test_tier_scope_kpi_numerical.py` | Calculation | ~35 | Tier/scope KPI accuracy |
| `test_ui_calculation_parity.py` | Parity | ~30 | UI ↔ API numeric consistency |
| `test_uncertainty.py` | Calculation | ~15 | Uncertainty propagation |
| `test_unit_conversions_exhaustive.py` | Conversion | ~60 | All unit round-trips |
| `test_user_profile_update.py` | Auth | ~5 | User profile update |
| `test_vented.py` | Calculation | ~8 | Vented emissions |

---

## 3. Frontend Test Infrastructure

### Current Status: **PARTIAL**

| Component | Status | Notes |
|---|---|---|
| Unit test framework (Vitest/Jest) | ❌ **NOT INSTALLED** | Not in `package.json` |
| Component rendering tests | ❌ **NOT PRESENT** | No `*.test.jsx` files found |
| Browser automation (Playwright/Cypress) | ❌ **NOT INSTALLED** | Not in devDependencies |
| ESLint (static analysis) | ✅ **INSTALLED** | `eslint.config.js` configured |
| Frontend stress tests | ⚠️ **PARTIAL** | 6 Node.js `.mjs` scripts (no browser) |

### Frontend Test Files (`new/client/tests/`)

| File | Type | Description |
|---|---|---|
| `test_ui_audit_visuals.mjs` | State simulation | Audit trail display logic |
| `test_ui_stress_boundary_display.mjs` | Boundary | Extreme value display behavior |
| `test_ui_stress_bulk_parsing.mjs` | Performance | CSV parsing stress test |
| `test_ui_stress_fuzzing_mutations.mjs` | Fuzzing | 1000 rapid filter mutations |
| `test_ui_stress_large_dataset.mjs` | Volume | Large dataset rendering simulation |
| `test_ui_stress_runner.mjs` | Runner | Orchestrates the 5 above tests |

**Note**: These are JavaScript simulations of state-machine logic, not browser-rendered UI tests. They run with `node` directly and exercise JavaScript parsing logic but NOT React rendering, DOM interaction, or actual API calls to a live server.

### Frontend Test Command
```bash
cd new/client
node tests/test_ui_stress_runner.mjs
```

---

## 4. Security Testing

| Category | Tool | Status | Notes |
|---|---|---|---|
| SQL injection | `test_deep_injection_matrix.py` | ✅ PRESENT | 35 injection tests via API |
| XSS | `test_deep_injection_matrix.py` | ✅ PRESENT | Script injection in field values |
| Path traversal | `test_deep_injection_matrix.py` | ✅ PRESENT | Traversal in file paths |
| IDOR | `test_api_security.py` | ✅ PRESENT | Cross-user data access attempts |
| Rate limit testing | — | ❌ NOT PRESENT | Limiter disabled in conftest |
| CSRF bypass testing | — | ❌ NOT PRESENT | CSRF disabled in tests |
| JWT/session testing | `test_api_security.py` | ⚠️ PARTIAL | Session tests but no token manipulation |
| SSRF testing | — | ❌ NOT PRESENT | Avatar URL SSRF code exists but not tested |
| Security header testing | — | ❌ NOT PRESENT | Headers set in `after_request` but not tested |

---

## 5. Performance Testing

| Category | Tool | Status | Notes |
|---|---|---|---|
| Locust load tests | `new/server/locustfile.py` | ⚠️ PRESENT (stub) | Only 4 endpoints, uses `Bearer test` (fake auth) |
| Benchmark DB | `new/server/benchmark_db.py` | ⚠️ PRESENT | Manual benchmark script |
| API response time | `test_performance.py` | ⚠️ PRESENT (657 bytes) | Minimal timing test |
| Stress tests | `test_stress_*.py` (5 files) | ✅ PRESENT | Memory, volume, concurrency stress |

---

## 6. E2E Testing

| Category | Status | Notes |
|---|---|---|
| Playwright | ❌ NOT INSTALLED | Not in devDependencies |
| Cypress | ❌ NOT INSTALLED | Not in devDependencies |
| Selenium | ❌ NOT INSTALLED | No Python selenium dependency |
| Manual E2E | ❌ NOT DOCUMENTED | No E2E test plan documented |
| API integration | ✅ PARTIAL | `test_all_apis_health.py` tests endpoints against live server |

---

## 7. Coverage Analysis

| Coverage Area | Covered? | Depth |
|---|---|---|
| Calculation engine | ✅ | HIGH — 880 tests including differential, property, golden |
| Authentication | ✅ | MEDIUM — login, RBAC, session |
| Authorization (RBAC) | ✅ | MEDIUM — role enforcement, IT isolation |
| API endpoints | ✅ | MEDIUM — core CRUD tested |
| Database models | ⚠️ | LOW — no explicit model constraint tests |
| Migrations | ❌ | NOT TESTED |
| Frontend components | ❌ | NOT TESTED (no framework) |
| E2E workflows | ❌ | NOT TESTED |
| Email | N/A | Not implemented |
| Rate limiting | ❌ | Disabled in tests — not verified |
| CSRF protection | ❌ | Disabled in tests — not verified |
| Production build | ⚠️ | CI builds frontend only |
| Backup/restore | ❌ | NOT TESTED |
| Browser compatibility | ❌ | NOT TESTED |
| Accessibility | ❌ | NOT TESTED |
| Responsive behavior | ❌ | NOT TESTED |

---

## 8. Recommended Testing Additions

### Highest Priority (CRITICAL gaps)

1. **Isolated test database** — Create `conftest.py` with in-memory SQLite or test-specific DB
2. **Rate limit tests** — Test actual rate limit enforcement (not disabled)
3. **CSRF tests** — Test CSRF token behavior
4. **Frontend unit tests** — Install Vitest + React Testing Library
5. **E2E browser tests** — Install Playwright; implement login → calculate → report flow
6. **Migration tests** — Test `flask db upgrade` from clean state
7. **Security header tests** — Verify CSP, X-Frame-Options, etc. in HTTP responses

### Medium Priority

8. **Backup/restore testing** — Test SQLite backup and restore
9. **Load tests** — Run Locust with realistic authentication
10. **Accessibility audit** — Install axe-core or similar
11. **Browser compatibility matrix** — Chromium + Firefox minimum

---

*Document generated: 2026-09-20 | Status: COMPLETE*
