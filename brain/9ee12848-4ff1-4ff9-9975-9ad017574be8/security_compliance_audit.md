# Comprehensive Security, Compliance & IT Audit Report

**Date:** 2026-04-23
**Auditor Scope:** Security (AppSec/InfoSec), Compliance, Technical Architecture, IT Operations.
**Status:** READ-ONLY Review (No modifications made)

---

## 1. Authentication & Session Management (Security & IT)

| ID | Severity | File/Location | Category | Description & Impact | Recommendation |
|---|---|---|---|---|---|
| **SEC-01** | 🔴 CRITICAL | `config.py:7` | Cryptography / Auth | **Default Hardcoded SECRET_KEY:** The Flask application uses a default `SECRET_KEY = 'dev-secret-key-change-in-prod-please'`. Flask uses this key to sign session cookies. If deployed to production with this default, an attacker can trivially forge a session cookie to log in as any user (including administrators) and achieve complete account takeover. | Enforce `os.environ.get('SECRET_KEY')` without a fallback, raising a fatal error on startup if missing. |
| **SEC-04** | 🔴 CRITICAL | `audit.py:9`, `audit.py:52` | Broken Access Control | **Unauthenticated Access to System Audit Trails:** The `get_audit_logs()` and `create_audit_log()` routes do **not** check for `session.get('user_id')`. Any anonymous user on the internet can query the entire system activity history, exposing all user emails, IPs, and internal entity IDs. | Add `session.get('user_id')` check to all routes in `audit.py`. Enforce Admin-only access for viewing global audit logs. |
| **SEC-05** | 🔴 CRITICAL | `notifications.py:7` | Broken Access Control | **Information Disclosure via Notifications:** The `get_notifications()` route lacks a strict authentication check. If `user_id` is None, it falls back to returning all global/system notifications to the anonymous requester. | Enforce `session.get('user_id')` check. Return 401 Unauthorized for anonymous requests. |
| **SEC-02** | 🟡 MEDIUM | `auth.py:11-39` | DoS / Rate Limiting | **In-Memory Rate Limiting:** `rate_limit_login` uses a local Python dictionary (`_login_attempts`) keyed by IP address. This causes memory leaks/exhaustion (IP addresses are never cleared unless they log in) and fails entirely in multi-worker environments (e.g., Gunicorn) where memory is not shared. | Use `Flask-Limiter` backed by Redis for distributed, memory-safe rate limiting. |
| **SEC-03** | 🟡 MEDIUM | `auth.py:41` | Policy Enforcement | **Missing Password Strength Validation on Registration:** The `/register` endpoint accepts any password string (e.g., "123"). The `/change-password` endpoint correctly enforces a 10-character minimum, but registration bypasses this. | Extract the password complexity logic into a shared validator and apply it to `/register`. |

---

## 2. Authorization & Access Control (Security)

| ID | Severity | File/Location | Category | Description & Impact | Recommendation |
|---|---|---|---|---|---|
| **SEC-06** | 🔴 CRITICAL | `models.py:20`, All Routes | Privilege Escalation | **Missing Role-Based Access Control (RBAC):** The `User` model defines a `role` field (default='user', can be 'admin'). However, the backend routing only checks `if not user_id:` (meaning *any* authenticated user). Any standard user can hit the `DELETE /api/facilities/<id>` or `DELETE /api/scope2/<id>` endpoints to destroy global system data. | Implement an `@admin_required` decorator that queries the user's role and apply it to destructive actions, master data management, and audit logs. |

---

## 3. Data Validation, Injection & Resilience (Technical / InfoSec)

| ID | Severity | File/Location | Category | Description & Impact | Recommendation |
|---|---|---|---|---|---|
| **SEC-07** | 🟠 HIGH | `managedata.py:58`, `scope3.py:111` | Data Integrity | **Unvalidated Bulk CSV Imports:** The bulk import functions extract floats using `float(rec.get('amount') or 0)`. While this prevents SQLi, a user uploading a maliciously formatted CSV can inject strings causing unhandled `ValueError` 500 crashes, or submit massive numeric values (e.g., 1e99) that distort global reporting metrics indefinitely. | Implement strict schema validation (e.g., Pydantic or Marshmallow) on bulk import payloads to enforce bounds and types. |
| **SEC-08** | 🟡 MEDIUM | `facilities.py`, `auth.py` | Cross-Site Scripting (XSS) | **Lack of Input Sanitization:** Text fields like `boundary_notes`, `description`, and `bio` accept raw user input without server-side HTML stripping. While React (the frontend) generally escapes output natively, any use of `dangerouslySetInnerHTML` on the frontend for these fields would lead to Stored XSS. | Implement a server-side HTML sanitization library (like `bleach`) on all open text inputs before saving to the database. |

---

## 4. Compliance & IT Operations (IT Audit / Compliance)

| ID | Severity | File/Location | Category | Description & Impact | Recommendation |
|---|---|---|---|---|---|
| **CMP-01** | 🟠 HIGH | `auth.py`, `managedata.py` | Non-Repudiation | **Audit Trail Fails Silently:** Throughout the application (e.g., `auth.py:68`, `facilities.py:47`), the `ActivityLog` creation is wrapped in a `try...except Exception as e: print(e)` block. If the database is under load or an attacker intentionally overflows a metadata JSON payload, the audit log will fail to write, but the primary transaction (e.g., Login, Delete Facility) will still succeed. This violates strict non-repudiation compliance standards. | Do not swallow audit exceptions. Use a distributed message queue for resilient logging, or ensure the audit log is part of the same atomic database transaction as the primary action. |
| **CMP-02** | 🟡 MEDIUM | `app.py:15` | Configurations | **Overly Permissive CORS:** CORS allows `http://127.0.0.1:3000` and `http://localhost:5173` globally with `supports_credentials=True`. In production, this must be locked down exclusively to the hosted domain. | Tie the CORS origins list to a strictly validated `os.environ.get('ALLOWED_ORIGINS')` variable. |

---

### Audit Summary & Verdict

The GHG system's calculation math is now highly robust and API 2021 compliant (repaired in previous session). However, the **Security Posture is currently unfit for production**. 

The most alarming risks are **Broken Access Control** (any user can delete any data) and **Unauthenticated Audit/Notification access** (massive data leakage). The hardcoded `SECRET_KEY` is a critical deployment risk.

**Recommended Action:** Halt feature development and dedicate a sprint to implementing an `@admin_required` middleware, securing the `SECRET_KEY`, and locking down the `audit.py` routes before deployment to any public-facing environment.
