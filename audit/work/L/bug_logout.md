# BUG-XXX — Logout does not invalidate the session: a session cookie captured before logout keeps full API access (client-side signed cookie, no server-side revocation)

**Status:** Confirmed
**Severity:** Medium
**Category:** Security
**Discovered by:** Agent L (Browser)

## Location
- `new/server/routes/auth.py` login (L355 `session["user_id"] = user.id`) and logout (~L485-512: `session.clear()` + expire cookie). Flask's default session is a signed client-side cookie; there is no server-side session store, session id, or per-user token/version that logout could revoke.
- `new/server/config.py:97` `PERMANENT_SESSION_LIFETIME = timedelta(hours=8)`.

## Reproduction
1. On :5190 log in as audit_superuser (Playwright context A); copy the `session` cookie.
2. Click the UI Logout (`#logout-btn-drop` / top-bar logout) → redirected to /login; in context A `GET /api/auth/me` → 401.
3. In a new context B, add the copied pre-logout cookies and call `GET /api/auth/me` and `GET /api/emissions?scope=1&limit=1&offset=0`.
Script: `node audit/repro/BUG-NNN.mjs`.

## Input
Pre-logout `session` + `csrf_token` cookies.

## Expected
After logout the old session is dead everywhere: 401 for any reuse of the cookie.

## Actual
Context B: `/api/auth/me` → **200** `{"authenticated":true,...}` for audit_superuser; `/api/emissions…` → **200**. Logout only removes the cookie from the browser that clicked it.

## Evidence
`audit/work/L/w23_logout.mjs` output:
```
after logout url: http://127.0.0.1:5190/login clicked UI: true
same ctx /me: 401
replayed pre-logout cookie /me: 200 {"authenticated":true,...
replayed cookie data access: 200
```

## Root Cause
Stateless signed-cookie sessions without a revocation list or server-side session id; logout cannot invalidate copies of the cookie.

## Impact
A stolen or shared cookie (shared workstation, proxy logs, XSS, browser sync) stays usable after the user logs out, for the session lifetime; the same applies after an admin deactivates/changes the role only if the per-request user reload does not catch it (not tested here). For an emissions-reporting system with maker-checker roles this undermines the "log out ends access" control expected by ISO 27001-style reviews.

## Affected Components
All authenticated API routes; `POST /api/auth/logout`.

## Recommended Fix
Use a server-side session store (Flask-Session with Redis/DB) or add a per-user `session_version`/random session id stored server-side that is checked on every request and rotated on logout, password change and deactivation.
