# Phase 1: Automated Sweep Report

> **Execution Date**: November 2026
> **Scope**: Complete static analysis, dependency vulnerability audit, production build, client test suite, backend test suite, and exhaustive API endpoint sweep.

---

## 1. Summary of Automated Tool Executions

| Tool | Target | Result / Status | Key Metrics & Findings |
| :--- | :--- | :---: | :--- |
| **Ruff** | `new/server` | **2,755 errors** | Syntax, imports, code quality violations (raw log in `audit/automated_sweep/ruff.log`). |
| **Flake8** | `new/server` | **22,842 issues** | **6 Critical F821 Undefined Name errors** (`db` undefined in `routes/reports_export.py:124, 172, 226`), 89 F811 redefinitions, 68 F601 duplicate keys. |
| **Bandit** | `new/server` | **15 Medium, 8,041 Low** | CWE-89 SQL injection vectors via string formatting in queries (`routes/auth_users.py`, `id_guard.py`), CWE-20 XML vulnerabilities (`services/cbam_xml.py`). |
| **NPM Audit** | `new/client` | **7 vulnerabilities** | **1 Critical** (`dompurify` XSS template bypass GHSA-cg2g-xh64-v4q7), **3 High** (`zod` DoS, `follow-redirects` credential leak, `undici` DoS/SSRF/TLS bypass). |
| **TypeScript (tsc)** | `new/client` | **0 errors** | `tsc --noEmit` passed cleanly. |
| **ESLint** | `new/client` | **Config Defect** | **Major Blind Spot**: `eslint.config.js` specifies `files: ['**/*.{js,jsx}']`, completely bypassing all 248 `.ts` and `.tsx` application source files in `src/`. |
| **Vite Build** | `new/client` | **Build Passed** | Production bundle generated in 39.30s (779 kB main bundle). |
| **Vitest** | `new/client` | **193 passed (35 files)** | All existing frontend unit tests passed. |
| **Pytest** | `new/server/tests` | **40 FAILURES** | 5,775 passed, 40 failed, 4 skipped, 201 warnings out of 5,819 tests (25m 20s). Contradicts previous claims of 100% passing tests. |
| **API Endpoint Sweep** | All Flask API routes | **HTTP 500 Confirmed** | 1,098 requests across 229 endpoints. `GET /api/reports/export` crashes with 500 (`NameError: name 'db' is not defined`). |

---

## 2. Detailed Findings from Phase 1

### Finding AS-01: Runtime NameError Crashing `GET /api/reports/export`
- **Location**: [`new/server/routes/reports_export.py:124, 172, 226`](file:///c:/Users/samsung/Desktop/H2/new/server/routes/reports_export.py#L124)
- **Severity**: **Critical**
- **Category**: Backend Logic / Unhandled Exception
- **Confidence**: **Confirmed** (Reproduced via API Sweep and static analysis)
- **Description**: `routes/reports_export.py` was refactored out of `routes/reports.py` but failed to import `db` from `extensions`. When filtering by status (which defaults to `"Verified"`), lines 124, 172, and 226 attempt to call `db.func.lower(...)`, throwing an unhandled `NameError: name 'db' is not defined` and returning HTTP 500 to the user.
- **Reproduction**:
  ```python
  client = app.test_client()
  # Log in as admin
  with client.session_transaction() as sess:
      sess['user_id'] = 1
      sess['sv'] = 1
  resp = client.get('/api/reports/export')
  assert resp.status_code == 500
  assert 'NameError' in trace_log or resp.get_json()['error'] == 'Report export failed. Please try again or contact support.'
  ```

### Finding AS-02: Critical DOMPurify XSS Vulnerability in Frontend Dependencies
- **Location**: `new/client/package.json` (`dompurify: 1.4.1` / `<3.4.16`)
- **Severity**: **Critical**
- **Category**: Security / Dependency CVE
- **Confidence**: **Confirmed** (`npm audit` advisory GHSA-cg2g-xh64-v4q7, GHSA-mrv2-3pqr-j5jr)
- **Description**: DOMPurify contains a template expression bypass allowing split template expressions in shadow root content to survive sanitization and execute XSS.

### Finding AS-03: ESLint Configuration Blind Spot Ignoring All TypeScript Code
- **Location**: [`new/client/eslint.config.js:11`](file:///c:/Users/samsung/Desktop/H2/new/client/eslint.config.js#L11)
- **Severity**: **Medium**
- **Category**: Configuration / Static Analysis
- **Confidence**: **Confirmed**
- **Description**: `eslint.config.js` defines `files: ['**/*.{js,jsx}']`. The frontend has been migrated to TypeScript (`.ts` and `.tsx` files count: 248), meaning ESLint scans zero application component files, creating false confidence in linting cleanliness.

### Finding AS-04: String-Interpolated SQL in High-Privilege Endpoints
- **Location**: [`new/server/routes/auth_users.py:195, 200`](file:///c:/Users/samsung/Desktop/H2/new/server/routes/auth_users.py#L195), [`new/server/id_guard.py:27, 33`](file:///c:/Users/samsung/Desktop/H2/new/server/id_guard.py#L27)
- **Severity**: **High**
- **Category**: Security / SQL Injection
- **Confidence**: **Likely** (Identified by Bandit and static analysis)
- **Description**: SQL statements are constructed via Python f-string interpolation (`f'UPDATE "{table.name}" SET "{snapshot}" = :label'`). While table names originate from metadata, interpolating identifiers into raw SQL strings violates secure query design.

### Finding AS-05: Pre-Existing Test Failures in Test Suite
- **Location**: `new/server/tests/`
- **Severity**: **High**
- **Category**: Test Suite / Regression
- **Confidence**: **Confirmed**
- **Description**: The existing test suite contains at least 24 failing tests, proving that recent changes or unremediated defects are present in the active codebase despite previous claims of 100% pass rates.
