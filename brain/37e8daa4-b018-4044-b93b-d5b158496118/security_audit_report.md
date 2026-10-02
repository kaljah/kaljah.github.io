# Enterprise Security Audit Report: Greenhouse Gas (GHG) Accounting & Reporting Platform

**Date**: October 2, 2026  
**Auditor**: Senior Security Specialist & Code Reviewer  
**Audit Scope**: End-to-End Source Code Security Review (Backend, Frontend, Workers, Database, Deployment)  
**Target Repository**: c:\Users\samsung\Desktop\H2  
**Classification**: CONFIDENTIAL / SECURITY AUDIT  

---

## 1. Executive Summary

A comprehensive, zero-shortcut security assessment was performed across the entire codebase of the enterprise Greenhouse Gas (GHG) Accounting & Reporting Platform. The system is architected as a decoupled web application comprising:
1. **Backend REST API**: Python 3.11 / Flask 3.0 / SQLAlchemy / Alembic / SQLite & PostgreSQL support (
ew/server).
2. **Frontend SPA**: React 18 / Vite 7 / Tailwind CSS / Axios (
ew/client).
3. **Background Job Processor**: Multi-threaded CSV/Excel ingestion pipeline (
ew/server/background_processor.py).
4. **Container & Deployment Configuration**: Dockerfile multi-stage build (Dockerfile).

The audit evaluated all components against the **OWASP Top 10 (2021)**, **CWE/SANS Top 25**, and enterprise cloud security best practices.

### Overall Security Posture
The application exhibits strong baseline defense-in-depth principles:
- **Authentication & Sessions**: Passwords are securely hashed with scrypt/PBKDF2-SHA256, session hijacking is mitigated via cryptographic session tokens with server-side session_version invalidation, and NIST SP 800-63B complexity rules are strictly enforced.
- **SQL & Command Injection**: All dynamic queries leverage SQLAlchemy ORM or parameterized 	ext() constructs. Subprocess executions are restricted strictly to automated schema test suites and do not interface with user input.
- **SSRF Defenses**: External URL handling (avatar uploads and Copernicus CDSE satellite integrations) validates protocol (https://), performs DNS lookups, and actively blocks private, loopback, link-local, and multicast IP ranges.
- **XSS & Frontend State**: No unescaped dangerouslySetInnerHTML is used in the React client. Sensitive tokens are not persisted in localStorage.

However, the audit identified **several high and medium severity vulnerabilities** spanning CSV Formula Injection, authorization inconsistencies (RBAC bypass on secondary endpoints), container configuration degradation, and third-party dependency vulnerabilities.

---

## 2. Vulnerability Severity Matrix

| Vulnerability ID | Vulnerability Title | Severity | OWASP Top 10 | CWE | Status |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **VULN-01** | CSV Formula Injection (DDE) in Bulk Upload Error Export | **HIGH** | A03:2021 - Injection | CWE-1236 | **Confirmed** |
| **VULN-02** | Malformed Multi-Stage Dockerfile Overwrite | **HIGH** | A05:2021 - Security Misconfiguration | CWE-16 | **Confirmed** |
| **VULN-03** | Known Critical/High CVEs in Frontend Dependencies | **HIGH** | A06:2021 - Vulnerable Components | CWE-1395 | **Confirmed** |
| **VULN-04** | Auditor Role RBAC Bypass on Operational Mutation Endpoints | **MEDIUM** | A01:2021 - Broken Access Control | CWE-284 | **Confirmed** |
| **VULN-05** | Inconsistent Formula Injection Sanitization in Emission Export | **MEDIUM** | A03:2021 - Injection | CWE-1236 | **Confirmed** |
| **VULN-06** | Missing Object Ownership Enforcement on Record Deletion | **LOW** | A01:2021 - Broken Access Control | CWE-285 | **Confirmed** |

---

## 3. Deep Technical Findings & Vulnerability Analyses

### [HIGH] VULN-01: CSV Formula Injection (DDE) in Bulk Upload Error Export
- **File**: 
ew/server/background_processor.py (Lines 931–933, 1049–1053)
- **Endpoint**: GET /api/emissions/upload/errors/<job_id>
- **CWE**: CWE-1236 (Improper Neutralization of Formula Elements in a CSV File)
- **OWASP Category**: A03:2021 - Injection

#### Root Cause Analysis
When an uploaded CSV fails ingestion validation, the background processor collects the invalid row values and creates a downloadable error report (errors_<job_id>.csv). While the standard export routes (outes/audit.py, outes/dashboard.py, outes/reports.py) invoke formula sanitization, ackground_processor.py appends raw user-supplied strings directly:
`python
# new/server/background_processor.py:931-933
skipped_list = [; .join(row_errors)]
skipped_list.extend([" if row_dict.get(h) is None else str(row_dict.get(h)) for h in headers])
skipped_rows.append(skipped_list)
...
# new/server/background_processor.py:1049-1052
with open(error_file, w, newline=, encoding=utf-8) as ef:
 writer = csv.writer(ef)
 writer.writerow(error_headers)
 writer.writerows(skipped_rows)
`

#### Exploit Mechanics & Impact
An attacker with operator privileges uploads a CSV file containing malicious spreadsheet formula payloads (e.g. starting with =, +, -, @, \t, \r, or %) inside one of the descriptive or numerical columns, deliberately triggering a validation error (such as an invalid date or negative number). When a compliance officer, auditor, or administrator downloads the error file via /api/emissions/upload/errors/<job_id> and opens it in Microsoft Excel, LibreOffice Calc, or Google Sheets, the formula executes within the user's local context. This can lead to Dynamic Data Exchange (DDE) execution of local commands or silent data exfiltration via hyperlink formulas.

#### Defensive Remediation
Sanitize every cell value written to the error CSV by prepending a single quote (') to any value starting with formula trigger characters:
`python
def sanitize_csv_cell(val):
 if val is None:
 return 
 s = str(val)
 stripped = s.lstrip()
 if stripped and stripped[0] in (=, +, -, @, \t, \r, %):
 return ' + s
 return s

# In background_processor.py:
skipped_list = [; .join(row_errors)]
skipped_list.extend([sanitize_csv_cell(row_dict.get(h)) for h in headers])
skipped_rows.append(skipped_list)
`

---

### [HIGH] VULN-02: Malformed Multi-Stage Dockerfile Overwrites Production Build
- **File**: Dockerfile (Lines 1–73)
- **CWE**: CWE-16 (Configuration)
- **OWASP Category**: A05:2021 - Security Misconfiguration

#### Root Cause Analysis
The project Dockerfile contains two duplicate and conflicting build declarations:
1. Lines 1–44: Stage 1 builds the React client, Stage 2 sets up Python 3.11, copies built frontend assets to /app/static/dist, and binds Gunicorn to port 5000.
2. Lines 46–72: A second, un-named FROM python:3.11-slim statement resets the container image build context entirely. It does NOT copy the compiled frontend assets from Stage 1, alters the exposed port to 10000, and runs as root.

`dockerfile
# Stage 1 & 2 (Lines 1-44)
FROM node:20-alpine AS frontend-builder
...
COPY --from=frontend-builder /app/client/dist /app/static/dist
CMD [sh, -c, ... exec gunicorn --bind 0.0.0.0:5000 ...]

# UN-NAMED STAGE OVERRIDE (Lines 46-72)
FROM python:3.11-slim
WORKDIR /app
COPY new/server/ ./
ENV PORT=10000
EXPOSE 10000
CMD [sh, -c, ... exec gunicorn --bind 0.0.0.0: ...]
`

#### Impact
Docker builds only deliver the final stage. The resulting image produced from this Dockerfile has no compiled frontend assets, causing immediate 404/500 errors when users navigate the web application in production. Furthermore, the application executes as the oot superuser inside the container, violating the principle of least privilege.

#### Defensive Remediation
Consolidate the Dockerfile into a single, clean multi-stage configuration that creates an unprivileged system user (ppuser) and serves both static assets and API endpoints properly.

---

### [HIGH] VULN-03: Known Critical and High Vulnerabilities in Client Dependencies
- **File**: 
ew/client/package.json, 
ew/client/package-lock.json
- **CWE**: CWE-1395 (Dependency on Vulnerable Third-Party Component)
- **OWASP Category**: A06:2021 - Vulnerable and Outdated Components

#### Vulnerability Details
Executing 
pm audit inside 
ew/client reveals 22 vulnerabilities (1 Critical, 13 High, 6 Moderate, 2 Low):
1. **jspdf <= 4.2.0 (Critical / High — GHSA-9vjf-qc39-jprp, GHSA-p5xg-68wr-hm3m)**: PDF Object Injection vulnerability allowing arbitrary JavaScript execution within PDF viewers and AcroForm processing.
2. **dompurify (High — GHSA-76mc-f452-cxcm, GHSA-h8r8-wccr-v5f2)**: Mutation XSS (mXSS) flaws permitting sanitization bypass when processing crafted HTML trees.
3. **eact-router-dom / eact-router (Moderate/High)**: Flaws in state handling and SSR routing resolution.

#### Defensive Remediation
Execute dependency remediation in 
ew/client:
`ash
npm audit fix
npm install jspdf@latest dompurify@latest react-router-dom@latest
`

---

### [MEDIUM] VULN-04: Auditor Role RBAC Bypass on Operational Mutation Endpoints
- **Files**: 
ew/server/routes/data.py and 
ew/server/routes/managedata.py
- **CWE**: CWE-284 (Improper Access Control)
- **OWASP Category**: A01:2021 - Broken Access Control

#### Root Cause Analysis
In the platform's role-based access control (RBAC) model, the uditor role is designated as strictly read-only (designed for external verifiers and compliance reviewers). This constraint is enforced across primary emission routes, facility management, and production deletions:
`python
if user and (user.role in [auditor] or is_it_role(user)):
 return jsonify({error: Read-only or IT administrative role cannot modify operational data.}), 403
`
However, on several secondary operational endpoints, the authorization guard only checked for IT administrative roles and omitted the uditor check:
1. outes/data.py:384 (POST /api/data/ogmp-surveys)
2. outes/data.py:537 (POST /api/data/ogmp/level-upgrade)
3. outes/data.py:673 (POST /api/data/cbam-exports)
4. outes/data.py:781 (DELETE /api/data/cbam-exports/<id>)
5. outes/managedata.py:68 (POST /api/managedata/sources)
6. outes/managedata.py:123 (DELETE /api/managedata/sources/<id>)
7. outes/managedata.py:159 (POST /api/managedata/sources/bulk-import)
8. outes/managedata.py:269 (POST /api/managedata/mitigation)
9. outes/managedata.py:340 (DELETE /api/managedata/mitigation/<id>)
10. outes/managedata.py:579 (POST /api/managedata/mitigation/bulk-import)

#### Impact
An authenticated user possessing the uditor role can send crafted POST and DELETE requests to these endpoints, successfully creating, altering, or deleting emission sources, mitigation projects, OGMP 2.0 survey data, and CBAM trade records. This compromises data integrity and violates regulatory compliance segregation (ISO 14064 / GHG Protocol).

#### Defensive Remediation
Standardize the authorization check across all mutating endpoints in data.py and managedata.py:
`python
if not user or user.role in [auditor, it_admin, it_manager, it]:
 return jsonify({error: Forbidden: Read-only auditor or IT administrative accounts cannot modify operational data.}), 403
`

---

### [MEDIUM] VULN-05: Inconsistent Formula Injection Sanitization in Emission Export
- **File**: 
ew/server/routes/emissions.py (Line 3469–3473)
- **Endpoint**: GET /api/emissions/export
- **CWE**: CWE-1236 (Formula Injection)
- **OWASP Category**: A03:2021 - Injection

#### Root Cause Analysis
In 
ew/server/routes/emissions.py, the Excel export sanitizer is implemented as:
`python
def _safe_excel_value(val):
 if isinstance(val, str) and val and val[0] in (=, -, +, @, \t, \r):
 return ' + val
 return val
`
Unlike the hardened sanitizer in outes/reports.py:43–49 and outes/audit.py:18–25, this function does not call .lstrip() prior to inspecting the first character, and omits %. A cell containing leading whitespace before a formula (e.g.  =1+1) bypasses the al[0] check but will still be evaluated as a formula by Microsoft Excel.

#### Defensive Remediation
Update _safe_excel_value in emissions.py to match the hardened implementation:
`python
def _safe_excel_value(val):
 if isinstance(val, str) and val:
 stripped = val.lstrip()
 if stripped and stripped[0] in (=, -, +, @, \t, \r, %):
 return ' + val
 return val
`

---

### [LOW] VULN-06: Missing Creator Ownership Check on Direct Record Deletion
- **Files**: 
ew/server/routes/managedata.py:121 (DELETE /sources/<id>), 
ew/server/routes/data.py:779 (DELETE /cbam-exports/<id>)
- **CWE**: CWE-285 (Improper Authorization)
- **OWASP Category**: A01:2021 - Broken Access Control

#### Root Cause Analysis
In outes/data.py:delete_ogmp_survey, record deletion checks both facility access and creator ownership:
`python
if user and user.role not in [admin, superuser] and getattr(record, 'created_by', None) and record.created_by != user.id:
 return jsonify({'error': 'Forbidden: You cannot delete survey records created by another user'}), 403
`
However, in delete_source (managedata.py:121) and delete_cbam_export (data.py:779), any operator assigned to the facility can delete any record, regardless of who created it.

#### Defensive Remediation
Incorporate record creator ownership verification or restrict record deletion to users with dmin / superuser roles or the original author.

---

## 4. OWASP Top 10 (2021) Evaluation Matrix

| Category | Finding Summary | Compliance Posture |
| :--- | :--- | :---: |
| **A01: Broken Access Control** | Primary facility scoping and maker-checker segregation are robust. Secondary endpoints lacked uditor role mutation blocks (VULN-04). | **Needs Patching** |
| **A02: Cryptographic Failures** | Strong password hashing (scrypt/PBKDF2), secure cookies (HttpOnly, SameSite), no hardcoded production secrets in repo. | **PASS** |
| **A03: Injection** | SQL/Command injection fully protected. CSV/Excel formula injection discovered in background error generator (VULN-01) and emissions export (VULN-05). | **Needs Patching** |
| **A04: Insecure Design** | Maker-checker dual control, emission factor immutability, boundary locking, and strict IT-vs-business segregation are well designed. | **PASS** |
| **A05: Security Misconfiguration** | Dockerfile multi-stage overwrite breaks frontend bundle (VULN-02). Production environment variables strictly required. | **Needs Patching** |
| **A06: Vulnerable Components** | Outdated npm packages in 
ew/client (jspdf, dompurify) with published CVEs (VULN-03). Backend requirements up to date. | **Needs Patching** |
| **A07: Identification & Auth** | NIST SP 800-63B password rules, server-side session revocation (session_version), rate limiting on login/reset routes. | **PASS** |
| **A08: Software & Data Integrity** | JSON serialization used safely. No untrusted Python pickle/yaml deserialization found. | **PASS** |
| **A09: Logging & Monitoring** | Comprehensive activity logging via log_activity_and_notify tracks IP, user agent, record ID, and action. IT roles blocked from viewing business audit logs. | **PASS** |
| **A10: Server-Side Request Forgery** | Avatar URLs validated against private/loopback/multicast CIDRs. Satellite service connects only to hardcoded Copernicus domains. | **PASS** |

---

## 5. Remediation Plan & Code Patches

### Patch 1: Neutralize CSV Formula Injection in Background Processor
Apply to 
ew/server/background_processor.py:
`python
def _sanitize_csv_cell(val):
 if val is None:
 return 
 s = str(val)
 stripped = s.lstrip()
 if stripped and stripped[0] in (=, +, -, @, \t, \r, %):
 return ' + s
 return s

# Line 931-933:
skipped_list = [; .join(row_errors)]
skipped_list.extend([_sanitize_csv_cell(row_dict.get(h)) for h in headers])
skipped_rows.append(skipped_list)
`

### Patch 2: Harmonize Formula Sanitization in Emissions Export
Apply to 
ew/server/routes/emissions.py:3469:
`python
def _safe_excel_value(val):
 "Prevent formula injection (DDE/CSV injection) in Excel cells including leading whitespace bypasses."
 if isinstance(val, str) and val:
 stripped = val.lstrip()
 if stripped and stripped[0] in (=, -, +, @, \t, \r, %):
 return ' + val
 return val
`

### Patch 3: Enforce Auditor Read-Only Restrictions
Apply to 
ew/server/routes/data.py and 
ew/server/routes/managedata.py:
Replace:
`python
if user and user.role in [it_admin, it_manager, it]:
`
With:
`python
if not user or user.role in [auditor, it_admin, it_manager, it]:
 return jsonify({error: Forbidden: Read-only or IT administrative role cannot modify operational data.}), 403
`

### Patch 4: Consolidate Production Dockerfile
Apply to Dockerfile:
`dockerfile
# Stage 1: Build React Frontend
FROM node:20-alpine AS frontend-builder
WORKDIR /app/client
COPY new/client/package*.json ./
RUN npm ci --prefer-offline --no-audit || npm install
COPY new/client/ ./
RUN npm run build

# Stage 2: Production Python Backend
FROM python:3.11-slim
WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
 PYTHONUNBUFFERED=1 \
 FLASK_ENV=production \
 PORT=5000

RUN apt-get update && apt-get install -y --no-install-recommends \
 build-essential \
 libpq-dev \
 curl \
 && rm -rf /var/lib/apt/lists/*

COPY new/server/requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt gunicorn psycopg2-binary

COPY new/server /app
COPY --from=frontend-builder /app/client/dist /app/static/dist

# Security: Run as unprivileged user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 5000
CMD [sh, -c, FLASK_APP=app.py flask db upgrade && exec gunicorn --bind 0.0.0.0: --workers 4 --timeout 120 app:app]
`

---

## 6. Verification and Hardening Checklist

- [x] Passwords hashed with scrypt / PBKDF2
- [x] Sessions invalidated server-side on logout and credential change (session_version)
- [x] Cookies configured with HttpOnly, SameSite=Lax/Strict, and Secure in production
- [x] Parameterized SQL queries throughout ORM queries and raw text queries
- [x] SSRF blocked on avatar upload via domain resolution and CIDR filtering
- [x] No dangerouslySetInnerHTML or client-side token storage in localStorage
- [x] CSRF protection enforced across all mutating API routes
- [x] Rate limiting active on sensitive authentication endpoints
- [x] Multi-tenant facility isolation enforced (get_allowed_facility_ids)
- [x] IT admin roles segregated from viewing business audit logs
- [ ] **Action Required**: Patch CSV Formula Injection in ackground_processor.py (VULN-01)
- [ ] **Action Required**: Deduplicate and harden Dockerfile (VULN-02)
- [ ] **Action Required**: Run 
pm audit fix for client dependencies (VULN-03)
- [ ] **Action Required**: Add uditor checks to mutating endpoints in data.py & managedata.py (VULN-04)
- [ ] **Action Required**: Align _safe_excel_value in emissions.py (VULN-05)
