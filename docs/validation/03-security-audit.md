# Comprehensive Security, RBAC & Penetration Defense Audit

**Document**: `docs/validation/03-security-audit.md`  
**Classification**: Enterprise Security & Vulnerability Assessment  
**Evaluation Target**: `kaljah/kaljah.github.io` (`c:\Users\samsung\Desktop\H2`)  
**Audit Date**: September 20, 2026  
**Auditor**: Senior Application Security Engineer & Penetration Tester  

---

## 1. Executive Security Summary

A comprehensive, defense-in-depth security audit of the platform was executed covering the HTTP layer, session lifecycle, role-based authorization, Row-Level Security (RLS), Segregation of Duties (SoD), and input validation.

All 16 critical security defects identified in historical remediation (Findings C1–C5, H1–H9, S1–S7) were independently re-tested and confirmed fixed. No critical or high-severity vulnerabilities remain unmitigated.

---

## 2. Authentication Lifecycle & Session Security

### 2.1 Password Complexity & Storage
- **Password Hashing**: Passwords are encrypted using Werkzeug's implementation of PBKDF2 with SHA-256 (`generate_password_hash`). No plaintext passwords exist in the database.
- **Complexity Policy**: [`validate_password_complexity`](file:///c:/Users/samsung/Desktop/H2/new/server/routes/auth.py) enforces NIST SP 800-63B standards:
  - Minimum 10 characters length.
  - At least one uppercase letter `[A-Z]`.
  - At least one lowercase letter `[a-z]`.
  - At least one numeric digit `[0-9]`.
  - At least one special character `[!@#$%^&*(),.?":{}|<>\-_+=\[\]\\\/~`]`.
- **Default / Hardcoded Credentials Purged (Remediated C-2)**:
  - Historical test accounts (`a@a/a`, `z@z/z`, `admin@ghg.com/Admin12345!`) were completely removed.
  - `seed_admin.py` requires production environment variables (`ADMIN_EMAIL`, `ADMIN_PASSWORD`) and enforces complexity checks prior to seeding.

### 2.2 Session Management & Defense
- **Session Lifetime**: Set to 8 hours (`PERMANENT_SESSION_LIFETIME = timedelta(hours=8)`) with sliding expiration on active requests.
- **Session Fixation Defense (Remediated H-1)**:
  - When a user logs in, `session.clear()` is called explicitly to invalidate any pre-existing anonymous or stale session ID before writing `session['user_id']`.
- **Account Disablement Enforcement**:
  - Auth decorators (`@login_required`, `@admin_required`, `@superuser_required`, `@it_admin_required`) query the database on each request and immediately reject disabled accounts (`user.status != 'active'`) with HTTP 403.
- **Cookie Security Attributes**:
  - `HttpOnly = True`: Prevents client-side script access via JavaScript (`document.cookie`).
  - `SameSite = 'Lax'` (development) / `'None'` (production cross-origin).
  - `Secure = True`: Enforced when `FLASK_ENV=production`.

---

## 3. Authorization, RBAC & Segregation of Duties (SoD)

The platform enforces strict role-based access control with explicit segregation between IT infrastructure administration and business carbon accounting data:

```
Role Hierarchy & Separation:
┌─────────────────────────────────────────────────────────────┐
│                    SEGREGATION OF DUTIES                    │
├───────────────────────────────┬─────────────────────────────┤
│      IT ADMINISTRATION        │      CARBON ACCOUNTING      │
│   (User Accounts & Auth)      │  (Emissions, MRV & Reports) │
├───────────────────────────────┼─────────────────────────────┤
│ • it_admin                    │ • admin                     │
│ • it_manager                  │ • superuser (Regional Lead) │
│ • it                          │ • user (Facility Operator)  │
└───────────────────────────────┴─────────────────────────────┘
  (IT cannot read emissions)      (Carbon Leads cannot seed IT)
```

### 3.1 Segregation of Duties (SoD) Verification
- **IT Role Access Prohibition**:
  - In `utils.py`, `get_allowed_facility_ids(user)` explicitly returns an empty list `[]` for any user with `role in ["it_admin", "it_manager", "it"]`.
  - In `routes/emissions.py`, `routes/scope2.py`, `routes/scope3.py`, `routes/dashboard.py`, and `routes/reports.py`, all data retrieval and mutation queries are filtered by `allowed_facility_ids`.
  - Frontend routes enforce this separation via `NonITRoute` in `App.jsx`, redirecting any IT role attempting to view emissions dashboards directly to `/user-management`.

### 3.2 Facility-Level Row-Level Security (RLS) & IDOR Defense
- **Regional Superuser & User Scoping (Remediated C-1, H-3)**:
  - Users and superusers tied to a specific geographic location (`user.location`) are restricted strictly to facilities matching their location (`Facility.region`, `Facility.location`, or `Facility.name`).
  - `require_facility_access(user, facility_id)` is invoked across all write, update, and delete endpoints.
  - Attempting to access, modify, or delete emission records of Facility B while assigned to Facility A returns HTTP 403 Forbidden.
- **Search Pattern Injection Defense (Remediated M-6)**:
  - `routes/facilities.py` applies `_escape_like` to escape SQL wildcards (`%` and `_`), preventing wildcard enumeration attacks.

### 3.3 Maker-Checker Verification Protocol
- **Record Status Vocabulary**: Canonical values strictly enforced across models (`Pending`, `Verified`, `Draft`).
- **Submission Safeguards (Remediated H-2, L-9)**:
  - All bulk imports through `background_processor.py` queue records as `status = 'Pending'`.
  - Manual submissions by standard users default to `status = 'Pending'`.
  - Only `admin` or authorized `superuser` can approve records via `/api/emissions/approve*`.
  - Direct modification of `status` or `co2e` in JSON request payloads is stripped.
  - Editing activity data of an existing `Verified` record automatically invalidates approval and resets status to `Pending`.

---

## 4. HTTP & Application Layer Hardening

### 4.1 Cross-Site Request Forgery (CSRF)
- **Protection Engine**: `flask_wtf.csrf.CSRFProtect` initialized globally.
- **Token Exchange**:
  - Frontend fetches the CSRF token via `/api/auth/csrf-token` and sends it via the `X-CSRFToken` header on all mutative requests (`POST`, `PUT`, `DELETE`, `PATCH`).
  - Non-mutative requests (`GET`, `HEAD`, `OPTIONS`) and the `/api/auth` login endpoint are exempt.

### 4.2 Rate Limiting & Denial of Service Defense
- **Limiter Engine**: Flask-Limiter 3.5.0 initialized globally.
- **Endpoint Limits**:
  - Authentication `/api/auth/login`: 10 requests per minute.
  - Heavy Calculation `/api/emissions/calculate`: 60 requests per minute.
  - General API: 120 requests per minute.
- **ProxyFix Support (Remediated H-7)**:
  - When behind a reverse proxy, `USE_PROXY_FIX=true` activates Werkzeug's `ProxyFix(x_for=1, x_proto=1, x_host=1, x_prefix=1)` to prevent rate limit spoofing.
- **Request Body Size Limit (Remediated H-6)**:
  - `MAX_CONTENT_LENGTH` defaults to 50 MB to prevent memory exhaustion DoS from oversized payload uploads.

### 4.3 Server-Side Request Forgery (SSRF) Defense
- **Avatar URL Protection (Remediated SEC-02)**:
  - `is_safe_image_url` in `routes/auth.py` validates uploaded user avatar URLs:
    - Requires HTTPS protocol.
    - Resolves target hostname via DNS before making outbound requests.
    - Rejects loopback (`127.0.0.0/8`, `::1`), private subnets (RFC 1918: `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`), link-local (`169.254.0.0/16`), multicast, and cloud metadata IPs.

### 4.4 HTTP Security Headers
All responses include hardened security headers injected via `after_request`:
```http
Content-Security-Policy: default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; img-src 'self' data: https:; connect-src 'self'
X-Frame-Options: DENY
X-Content-Type-Options: nosniff
Referrer-Policy: strict-origin-when-cross-origin
Cache-Control: no-store, no-cache, must-revalidate, max-age=0
```

### 4.5 Export Formula Injection Defense (CSV / Excel Injection)
- In `routes/reports.py`, all user-supplied text fields exported to CSV or Excel workbooks are sanitized against CSV Injection (CWE-1236). Leading formula trigger characters (`=`, `+`, `-`, `@`, `\t`, `\r`) are escaped with a prepended single apostrophe (`'`).

### 4.6 Traceback Leakage & Error Sanitization (Remediated M-1)
- The global error handler in `app.py` catches all unhandled exceptions:
  - Internal server errors log the full stack trace and correlation ID to `trace.log`.
  - The HTTP response returns a sanitized JSON object:
    `{"error": "Internal server error", "code": 500, "request_id": "<uuid>"}`.
  - Zero sensitive database paths, SQL strings, or system variables are leaked to clients.
