# Full-Stack Audit Remediation Walkthrough

We have applied atomic, defensive, non-breaking remediations for all 17 functional bugs, security vulnerabilities (OWASP Top 10), edge cases, and concurrency issues identified during the repository audit.

---

## Key Changes by Layer

### 1. Frontend State & Concurrency
- **`new/client/src/api.js` (`AUD-01`):** Fixed unbounded Axios CSRF retry loop by introducing an explicit `originalConfig._retry = true` sentinel and narrowing token matching to CSRF-specific errors (`csrf`, `csrf token`, `token missing`).
- **`new/client/src/components/BulkImportModal.jsx` (`AUD-02`):** Bound background import polling to a persistent React `useRef` (`pollIntervalRef`) and added a cleanup return hook to cancel intervals on component unmount.
- **`new/client/src/pages/AuditTrail.jsx` (`AUD-03`):** Neutralized custom date filter query races by ensuring both `customStartDate` and `customEndDate` are present before dispatching ISO-formatted date range query parameters.

### 2. API & Contract Integrity
- **`new/server/routes/scope2.py` & `test_calculations_page.py` (`AUD-04`):** Standardized Maker-Checker approval statuses using canonical `PENDING_STATUS_SET`. Revived dead admin in-app notification triggers and resolved the 2 failing tests in `test_calculations_page.py`.
- **`new/server/routes/emissions.py` (`AUD-05`):** Replaced hard-deletion (`q.delete()`) in `POST /api/emissions/reject/batch` with compliant soft-status transitions (`status = 'Rejected'`), updating reviewer metadata and emitting individual `ActivityLog` entries.
- **`new/server/routes/data.py` (`AUD-06`):** Fixed IDOR / BOLA bypass in `save_ogmp_survey` by verifying user authorization against the existing record's facility before mutating or reassigning survey records.

### 3. Backend Logic & Data Access Layer
- **`new/server/routes/dashboard.py` (`AUD-07`):** Eliminated `AttributeError` 500 crash in `get_report_exclusions()` by safely falling back to `getattr(e, 'name', None) or getattr(e, 'reference_id', None) or 'Unspecified Source'`.
- **`new/server/calculations/combustion.py` & `dispatcher.py` (`AUD-08`):** Added volumetric unit normalization (`mscf`, `scf`, `mmscf`) in `FlaringCalculator` and updated `dispatcher.py` to pass normalized unit metadata, preventing volume under-calculations.
- **`new/server/routes/custom_factors.py` (`AUD-09`):** Added referential integrity validation in `DELETE /api/custom-factors/<id>`, blocking deletion with HTTP 409 Conflict if historical or pending records reference the factor.

### 4. OWASP Security Remediations
- **`new/server/routes/facilities.py` (`AUD-10`):** Added strict RBAC check (`user.role in ['admin', 'superuser']`) on `PUT /api/facilities/<id>`, preventing non-admin modification of facility configurations.
- **`new/server/routes/emissions.py`, `scope2.py`, `scope3.py` (`AUD-11`):** Enforced row-level resource ownership checks (`record.created_by == user.id or user.role in ['admin', 'superuser']`), blocked read-only `viewer` / `auditor` accounts from deleting records, and added atomic audit logging on Scope 2/3 deletions.
- **`new/server/routes/auth.py` (`AUD-12`):** Hardened user logout by invoking `session.clear()` and explicitly expiring the session cookie in the HTTP response.
- **`new/server/routes/reports.py` & `routes/audit.py` (`AUD-13`):** Neutralized CSV/Excel formula injection (DDE) bypasses by stripping leading whitespace before inspecting formula trigger characters (`=`, `+`, `-`, `@`, `\t`, `\r`, `%`).

### 5. Runtime Boundaries & Performance
- **`new/server/routes/data.py` (`AUD-14`):** Enforced creator ownership and added atomic `log_activity_and_notify` calls on `DELETE /api/data/ogmp-surveys/<id>`.
- **`new/server/routes/scope2.py` & `routes/scope3.py` (`AUD-15`):** Bounded synchronous bulk import payloads to 2,500 rows maximum to prevent WSGI worker starvation and gateway timeouts.
- **`new/server/config.py` (`AUD-16`):** Modernized production environment detection across `APP_ENV`, `ENVIRONMENT`, and `FLASK_ENV`, disallowing insecure default `SECRET_KEY` fallbacks in production.
- **`new/server/app.py` (`AUD-17`):** Added `PRAGMA busy_timeout = 5000` to SQLite connection initialization to eliminate ephemeral database lock contention under concurrent writes.

---

## Verification Results

### Pytest Test Suite
```
============================= test session starts =============================
platform win32 -- Python 3.12.4, pytest-9.1.1, pluggy-1.6.0
collected 80 items

new/server/tests/test_all_bulk_imports.py ........                       [ 10%]
new/server/tests/test_api_security.py ...............                    [ 28%]
new/server/tests/test_audit.py ........                                  [ 38%]
new/server/tests/test_calculations_page.py ....                          [ 43%]
new/server/tests/test_combustion.py ...                                  [ 47%]
new/server/tests/test_dispatcher.py ............                         [ 62%]
new/server/tests/test_gwp_dynamic.py ...                                 [ 66%]
new/server/tests/test_reports.py ......                                  [ 73%]
new/server/tests/test_satellite.py .....                                 [ 80%]
new/server/tests/test_sbti.py ...                                        [ 83%]
new/server/tests/test_uncertainty.py ...                                 [ 87%]
new/server/tests/test_vented.py ..........                               [100%]

====================== 80 passed, 41 warnings in 12.63s =======================
```
- **Total Tests:** 80
- **Passed:** 80 (100%)
- **Failed:** 0
