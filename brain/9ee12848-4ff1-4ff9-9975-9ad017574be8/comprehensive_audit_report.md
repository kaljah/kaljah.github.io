# Comprehensive System Audit Report

**Date:** 2026-04-23
**Scope:** Full Stack (Flask Backend, React Frontend, PostgreSQL/SQLite DB)
**Status:** READ-ONLY Review

This document categorizes all system vulnerabilities, architectural flaws, and compliance gaps as requested.

---

## 1. Calculation Audit (Status: ✅ Verified & Patched)
*Detailed in the previous `calculation_audit.md` artifact.*
*   **Findings:** The legacy engine previously contained "ghost" CH4 calculation errors, unit mismatch errors (psig vs psia), and outdated emission factors.
*   **Resolution:** All calculations now strictly adhere to the **API 2021 Compendium** standards. Custom factors calculate gases independently. GWP values enforce AR5 constants (`CH4=28`, `N2O=265`).

---

## 2. Security Audit (Status: 🔴 Critical Failures)

| ID | Severity | Location | Issue & Impact | Remediation |
|---|---|---|---|---|
| **SEC-01** | 🔴 CRITICAL | `config.py` | **Hardcoded SECRET_KEY:** Defaults to a static string. If deployed, attackers can forge session cookies and achieve full administrator account takeover. | Enforce `os.environ.get('SECRET_KEY')` with a fatal app crash if missing. |
| **SEC-02** | 🔴 CRITICAL | `models.py`, All Routes | **Missing Role-Based Access Control (RBAC):** The system checks *if* a user is logged in, but not *who* they are. Any standard user can delete global facilities or modify custom emission factors. | Implement `@admin_required` decorators for destructive and master-data endpoints. |
| **SEC-03** | 🔴 CRITICAL | `audit.py`, `notifications.py` | **Unauthenticated Endpoints:** `get_audit_logs()` and `get_notifications()` have no authentication checks. Anonymous internet users can dump the entire system activity history (emails, IPs, actions). | Enforce `session.get('user_id')` checks on all routes. |
| **SEC-04** | 🟠 HIGH | `app.py` | **Missing CSRF Protection:** The API relies on cookies (`withCredentials: true`) but lacks a CSRF token mechanism (like Flask-WTF). | Implement `flask_wtf.csrf.CSRFProtect` and require frontend headers. |
| **SEC-05** | 🟡 MEDIUM | `auth.py` | **In-Memory Rate Limiting:** `rate_limit_login` uses a local Python dictionary. This is vulnerable to memory exhaustion (DDoS) and fails completely in multi-worker production deployments (e.g., Gunicorn). | Use `Flask-Limiter` with a Redis backend. |
| **SEC-06** | 🟡 MEDIUM | `auth.py:41` | **No Password Strength on Register:** The `/change-password` route enforces 10 characters, but `/register` allows passwords like "123". | Extract password validation into a shared function. |

---

## 3. Data Integrity Audit (Status: 🟠 High Risk)

| ID | Severity | Location | Issue & Impact | Remediation |
|---|---|---|---|---|
| **INT-01** | 🟠 HIGH | `emissions.py`, `managedata.py` | **Unvalidated Bulk CSV Imports:** The server casts CSV inputs using `float(rec.get('amount'))`. Malformed strings cause unhandled 500 crashes. Missing bounds checking allows users to inject massive values (e.g., `1e99`) distorting global dashboards. | Implement schema validation (e.g., Marshmallow/Pydantic) for all bulk payloads. |
| **INT-02** | 🟠 HIGH | `models.py` | **Missing DB Cascade Deletes:** `Facility` deletions do not cascade to `emissions`. Deleting a facility via the API will leave thousands of orphaned emission records, corrupting dashboard aggregation. | Add `cascade="all, delete-orphan"` to parent-child relationships in SQLAlchemy models. |
| **INT-03** | 🟡 MEDIUM | `emissions.py:258` | **Non-Atomic Transactions:** `db.session.commit()` is called *before* the Audit Log is created. If the audit log fails, the data changes remain. | Move `db.session.commit()` to the very end of the try/except block to ensure atomicity. |

---

## 4. Compliance Audit (Status: 🟡 Medium Risk)

| ID | Severity | Location | Issue & Impact | Remediation |
|---|---|---|---|---|
| **CMP-01** | 🟠 HIGH | `auth.py`, `emissions.py` | **Audit Logs Fail Silently:** Activity log creation is wrapped in `try...except Exception as e: print(e)`. If an attacker overflows the metadata JSON payload, the audit log silently fails to write while the destructive action succeeds. **Violates strict Non-Repudiation standards.** | Do not swallow exceptions in audit trails. If the audit fails, the transaction must rollback. |
| **CMP-02** | 🟢 PASS | `constants.js`, `emissions.py` | **GHG Protocol / API 2021 Alignment:** The core engine, emission categorizations (Scope 1, 2, 3), and UI hierarchy correctly align with GHG Protocol corporate standards. | No action required. |
| **CMP-03** | 🟢 PASS | `models.py` | **TCFD Alignment:** The `ReportingMetadata` model natively supports TCFD (Task Force on Climate-related Financial Disclosures) tracking and Assurance Levels. | No action required. |

---

## 5. Code Quality Audit (Status: 🟡 Needs Improvement)

| ID | Severity | Location | Issue & Impact | Remediation |
|---|---|---|---|---|
| **CQ-01** | 🟡 MEDIUM | Global | **Poor Error Handling:** Extensive use of generic `except Exception:` blocks that merely `print()` to standard out. This hides critical stack traces in production and makes debugging difficult. | Use standard Python `logging` module (`logging.error(..., exc_info=True)`). |
| **CQ-02** | 🟡 MEDIUM | `client/src/` | **Lack of TypeScript / PropTypes:** The React frontend relies entirely on vanilla JS without strict typing, making large refactors brittle and prone to runtime `undefined` errors. | Migrate to TypeScript or enforce `PropTypes` for component props. |

---

## 6. IT/Infrastructure Audit (Status: 🟡 Medium Risk)

| ID | Severity | Location | Issue & Impact | Remediation |
|---|---|---|---|---|
| **INF-01** | 🟠 HIGH | `config.py:11` | **Database Fallback:** The backend silently falls back to local SQLite if `DATABASE_URL` is missing. In production, this can lead to ephemeral data loss if the container restarts. | Fail fast: Raise a fatal error if `DATABASE_URL` is missing in production environments. |
| **INF-02** | 🟡 MEDIUM | `app.py:15` | **Overly Permissive CORS:** CORS allows `http://localhost:3000` globally with `supports_credentials=True`. | Bind `origins` to an `ALLOWED_ORIGINS` environment variable. |

---

## 7. Architecture Review (Status: 🟡 Medium Risk)

| ID | Severity | Location | Issue & Impact | Remediation |
|---|---|---|---|---|
| **ARC-01** | 🟡 MEDIUM | `app.py` | **No API Versioning:** Routes are registered at `/api/emissions` instead of `/api/v1/emissions`. As the software scales and integrates with external client systems, introducing breaking changes will be impossible without versioning. | Prefix all blueprints with `/v1/`. |
| **ARC-02** | 🟢 PASS | `client/src/api.js` | **Centralized Axios Interceptors:** The frontend effectively uses Axios interceptors to globally handle 401 Unauthorized responses and redirect to login. | Keep this pattern. |
| **ARC-03** | 🟡 MEDIUM | `emissions.py:148` | **Inefficient Pagination:** The API pagination pulls `.all()` into memory, sorts the entire dataset in Python, and *then* slices it (`results[start:end]`). For 100,000+ emission records, this will crash the server via Out-Of-Memory (OOM) errors. | Perform pagination and sorting natively in the SQLAlchemy database queries (`.order_by().offset().limit()`). |

---

## 8. UI and UX Audit (Status: 🟡 Needs Polish)

| ID | Severity | Location | Issue & Impact | Remediation |
|---|---|---|---|---|
| **UX-01** | 🟡 MEDIUM | `DashboardEnhanced.jsx` | **Blocking Loading States:** The dashboard uses a full-page `<LoadingSpinner />` when fetching data. For a data-heavy application, this blocks the user from seeing the layout and feels jarring on every filter change. | Implement Skeleton UI loaders (e.g., pulsing grey boxes) for individual dashboard cards instead of a global spinner. |
| **UX-02** | 🟡 MEDIUM | `Dashboard.css`, `index.css` | **Poor Mobile Responsiveness:** The CSS relies heavily on fixed widths (e.g., `width: '180px'`) and CSS grid definitions without sufficient `@media` queries or Tailwind responsive prefixes (`md:`, `lg:`). The dashboard breaks or requires horizontal scrolling on mobile devices. | Refactor CSS to use fluid flex/grid layouts and CSS media queries. |
| **UX-03** | 🟡 MEDIUM | Forms (e.g., `Scope1Form.jsx`) | **Accessibility (a11y) Violations:** Form inputs often lack proper `<label htmlFor="...">` associations and `aria-` attributes. Screen readers cannot properly interpret the forms, violating WCAG compliance. | Audit all forms and ensure every `<input>` has a bound `<label>` and clear error state `aria-invalid` attributes. |
| **UX-04** | 🟢 PASS | `Toast.jsx`, `api.js` | **User Feedback & Error Handling:** The UI correctly catches 401 Unauthorized API responses and redirects to the login page smoothly. Toast notifications provide clear success/error feedback for actions. | Keep this pattern. |

---

### Final Auditor Verdict

The software possesses a fundamentally sound domain model (GHG calculation math, API 2021 Compendium adherence, and TCFD tracking). However, the **Application Security & Data Integrity posture is highly immature**.

The application **MUST NOT** be deployed to any internet-facing or corporate production environment until the Critical Security (RBAC, Unauthenticated Audits, Default Secrets) and High Data Integrity (Pagination OOM, DB Cascades) flaws are remediated. The UI/UX should be polished for mobile accessibility prior to a wider organizational rollout.
