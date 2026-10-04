# Security Review — GHG Accounting & Regulatory Reporting Platform

Target: `new/server` (Flask 3 / SQLAlchemy / Flask-WTF / Flask-Limiter) + `new/client` (React 19 / Vite).
Method: full read of the files named in scope, targeted reads of adjacent route modules, and read-only greps
across `new/server` and `new/client/src` for `password secret api_key apikey token AKIA "BEGIN RSA"
"BEGIN PRIVATE" eval( exec( pickle os.system subprocess shell=True render_template_string yaml.load md5 sha1
random.random verify=False`. **No files were created, modified, or deleted in the target; no scanners were run.**
No live credential value appears anywhere in this document.

Two claims were empirically validated in a throwaway in-memory interpreter (no target file written):
the blank-line decorator chain in `routes/custom_factors.py:152-155` still applies `superuser_required` (the
apparent bypass is a **false positive**, both `/api/custom-factors` and `/api/custom-factors/` return 403), and
Werkzeug's default password method is `scrypt:32768:8:1`.

---

## 1. AUTHENTICATION

| Item | Evidence | Verdict |
|---|---|---|
| Hash algorithm | `new/server/models.py:3,37-41` — `generate_password_hash(password)` / `check_password_hash` with **no `method=` argument** → Werkzeug default `scrypt:32768:8:1`, 16-byte salt (verified against the installed `werkzeug.security`). Column is `password_hash = db.Column(db.String(256))` (`models.py:15`) | Good. No `md5`/`sha1`/`random` in any credential path (`generate_*_csv.py` `random.random` hits are synthetic test data only) |
| Password policy | `routes/auth.py:69-91` — ≥10 chars, ≥1 upper, ≥1 lower, ≥1 digit, ≥1 special | Adequate but weak: `Passw0rd!1` passes; no breach-list check, no max length, no re-use prevention |
| Enforcement coverage | Applied in `register` (`auth.py:269`), `change-password` (`:614`), `admin_reset_password` (`:1172`) | Applied on all three write paths |
| Brute force | `routes/auth.py:336-338` — `@csrf.exempt`, `@limiter.limit(os.environ.get("LOGIN_RATE_LIMIT", "20 per 15 minutes"))`, keyed by IP for anonymous callers (`extensions.py:25-35`) | **Weak.** No account lockout, no progressive delay, no CAPTCHA |
| Failed-login tracking | `FAILED_LOGIN` is only ever *read* (`routes/audit.py:228,241`); nothing writes such an `ActivityLog` row — grep for `FAILED_LOGIN\|LOGIN_FAILED\|lockout\|locked_until\|failed_attempts` returns only those two read sites | **Absent.** `security_alerts` on the audit dashboard is permanently 0 |
| Login success only | `routes/auth.py:349-408`, `:384-391` writes `action="LOGIN"` | Silent on failure — no detection signal for credential stuffing |
| Session cookie flags | `config.py:91-99` — `HTTPONLY=True`; `SAMESITE = "None" if _is_production else "Lax"`; `SECURE = _is_production`; `PERMANENT_SESSION_LIFETIME = 8h`; `SESSION_REFRESH_EACH_REQUEST = True` | HttpOnly/Secure correct; **`SameSite=None` in production is the finding** (D1/C1 below). No `SESSION_COOKIE_NAME` is set → Flask default `session` |
| Session lifetime semantics | `SESSION_REFRESH_EACH_REQUEST = True` + `session.permanent = True` at login (`auth.py:354`) | Sliding 8 h with **no absolute cap** — an active session never expires; the `config.py:90` comment "8-hour session lifetime" is inaccurate |
| Session fixation | `auth.py:353` `session.clear()` before `session["user_id"] = user.id` | Correct for a client-side signed cookie (no server session id to rotate) |
| Signing | Flask `SecureCookieSessionInterface`, salt `cookie-session`, HMAC-**SHA1** (`itsdangerous 2.2.0`), signed with `SECRET_KEY` | Integrity depends entirely on `SECRET_KEY` secrecy → see C1 |
| `session_version` revocation | Write sites: `auth.py:356,493,638,643,1065,1177`; check: `app.py:168-185` global `before_request` | Works, but is **only** enforced by the global hook — no decorator re-checks it (`auth.py:138-250`, `routes/audit.py:32-49`, `routes/utils.get_current_user`), so it is a single point of failure for revocation |
| Password reset flow | `auth.py:411-474` — **no token is generated at all**: it fans out in-app `Notification`s to `it_admin`/`it_manager` and emails the requester; the admin then sets a password manually via `auth.py:1152-1202` | No token ⇒ no entropy, expiry or single-use question to get wrong, but also **no self-service reset**, no identity proofing, and the admin must invent and transmit a password. Uniform response mitigates enumeration; timing mitigation is applied (`:467-469`) |
| Reset side effects | `auth.py:1177` bumps `session_version`; response returns only `fullName`/`email`, not the password | Sessions invalidated correctly; no forced change-on-first-login (see H6) |
| Remember-me | No `remember` flag anywhere; `session.permanent` is set unconditionally | Effectively always-on within the 8 h sliding window |
| Logout completeness | `auth.py:484-517` — bump `session_version`, `session.clear()`, `delete_cookie(...)`, commit audit | Complete for the app's own cookie; `delete_cookie` passes no `domain`, so a cookie set on a parent domain would survive (see L4) |
| MFA | grep `mfa\|totp\|MFA\|otp` → no implementation. Only prose in `services/email_service.py:70` ("authorize a reset token") | **Absent.** For a platform holding emissions/production data and issuer-grade reports, this is a gap for admin/superuser/IT roles |

---

## 2. AUTHORIZATION

Scoping primitive: `new/server/utils.py:21-55` `get_allowed_facility_ids` → `None` = all (admin; superuser with
`all/global`), `[]` = none (all IT roles), else facilities whose `region`/`location`/`name` **`ilike` the user's raw
`location` string** applied as a SQL `LIKE` pattern (no `%`-escaping — a `location` containing `%` broadens scope;
`_escape_like` exists only in `routes/emissions.py:36`). `require_facility_access` (`utils.py:58-73`) denies IT roles
first and treats `None` as allow-all. `facility_change_allowed` (`utils.py:105-118`) blocks re-regioning out of scope.

- **IDOR**: the routes read in depth validate before filtering, e.g. `routes/data.py:38-40, 89-90, 228-229, 314-315,
  414-415, 509-510, 556-557, 591-592, 627-628, 698-699, 728-729, 789-790`; `routes/reports.py:364-369, 621-622,
  815-820, 531-536`; `routes/satellite.py:146-170` (incl. a 0.05° spatial-IDOR buffer); `routes/qaqc.py:776, 863`.
  No unscoped-by-omission handler was found in the reviewed set. Residual risk is the `ilike`-pattern scoping above.
- **Role escalation**: `ROLE_RANK` in `auth.py:273` and `auth.py:1026` both map `it_admin` **and** `it_manager` to 4.
  `update_user` (`auth.py:1012-1093`, `@it_admin_required`) lets any rank-4 actor assign **any** role they have the
  rank for, including `it_admin`/`it_manager` peers and `it`. `admin_reset_password` (`auth.py:1152-1202`,
  `@it_access_required`) is **global, with no rank check and no target restriction** — an `it_manager` may reset an
  `admin`'s password and log in as that admin. That is a full privilege-escalation path (H6).
- **`register` (auth.py:253-333)**: requires `it_admin_required`, blocks IT actors from creating `admin`
  (`:281-282`), but an `it_manager` can create `it_manager`/`it` peers — `VALID_ROLES` includes every role and no rank
  comparison is done on the create path.
- **Separation of duties** is otherwise deliberate and code-backed: `it_admin_required` (`:158`) for account
  management, `it_access_required` (`:181`) for list/reset, `superuser_required` (`:227`) for data, and IT roles are
  excluded from facility data (`utils.py:31`, `routes/data.py:21-22`, `routes/reports.py:321`, `:522`, `:560`, `:797`).
- **Server-side vs client-side**: the client guards (`new/client/src/App.jsx:29-73`) hide UI, and the backend repeats
  the checks — **except satellite** (H4 below), so the client hides nothing that is actually allowed.
- **Client-supplied role/owner fields** are not trusted: `created_by` comes from `session` (`routes/data.py:472, 566`),
  and `update_user` only mutates a selected allow-list of fields.
- **Destructive SQL in `delete_user`** (`auth.py:1113-1147`): dynamic identifiers, but taken from `db.metadata` and
  quoted with double quotes; values are bound (`:uid`, `:label`) — not injectable.

---

## 3. CSRF

- **Strategy**: Flask-WTF `CSRFProtect` (`extensions.py:8`, `app.py:126`). The token is *signed with `SECRET_KEY`
  and compared against the token stored in the session*, **not** a true double-submit cookie. The
  `csrf_token` cookie set at `app.py:504-511` (plus the JSON body `csrf_token`, `app.py:503`) is informational —
  **nothing ever compares the cookie to the header**. Tampering with the cookie has no effect; deleting it does not
  break the app. The docstring at `app.py:496-501` ("Issues a CSRF token for the double-submit cookie pattern") and
  `tests/test_security_hardening.py:81-90` both assert a pattern the code does not implement.
- **`/api/csrf-token` is unauthenticated** (`app.py:495`) with `max_age=86400`, `httponly=False`,
  `secure=SESSION_COOKIE_SECURE`, `samesite=SESSION_COOKIE_SAMESITE`. Because the real token lives in the session,
  an anonymous GET mints a valid token for the anonymous session — this also means the endpoint is safe to call
  before login, which is why `new/client/src/api.js:14-23` can.
- **Exemptions**: `@csrf.exempt` on `login` (`auth.py:337`), `forgot-password` (`auth.py:412`), the entire Swagger
  blueprint (`app.py:355`). `logout` (`auth.py:484`) is *not* exempt but also *not* `@login_required`, and it is
  POST — so with a same-site cookie a third-party page cannot force it; with `SameSite=None` it can (forced
  logout/`session_version` bump = user-visible DoS).
- **SSE**: `GET /api/notifications/stream` (`routes/notifications.py:64`) needs only a session cookie and cannot be
  token-protected (EventSource cannot set `X-CSRFToken`) — CSRF by design, mitigated only by `SameSite`. Under
  `SameSite=None` the stream is readable cross-site, and it streams notification **title/message** text
  (`:108-118`), i.e. real data exfiltration rather than just a state change. The response sets
  `Cache-Control: no-cache` itself (`:154-158`), and `app.py:227-229` deliberately skips the no-store header for it.
- **Upload/JSON endpoints**: `POST /api/emissions/upload/start` is `multipart/form-data` and is only protected by the
  same header check (no `@csrf.exempt`), which is correct; JSON bodies are likewise covered because
  `application/json` is not a CORS-simple content type.
- **Client retry-on-400** (`new/client/src/api.js:44-63`): on HTTP 400 whose body contains `csrf`/`token missing`, it
  refetches the token and re-issues the request **once** (`_retry` guard) with `withCredentials` preserved.
  Assessment: **does not meaningfully weaken CSRF**, because the token is still required on the retry and axios
  cannot set the `Cookie` header. It *does* permit one duplicate state-changing POST per token-expiry event, and the
  message-substring match means any future 400 mentioning "token" (e.g. a token-bucket message) silently re-sends
  the payload.
- **`WTF_CSRF_SSL_STRICT = False`** (`config.py:103`): the Referer-based check for HTTPS requests is disabled, so the
  token is the **only** control. Combined with the `kaljah.github.io` origin (§5) the defense-in-depth layer is gone.
- **SameSite/Secure vs production cookie** (`config.py:92-97`): production sets session cookie `SameSite=None;
  Secure` — legal, but it removes the browser-level CSRF barrier entirely. `app.py:508-509` reads the same config for
  the CSRF cookie, so the two cookies are at least consistent.

---

## 4. INJECTION & INPUT

- **SQL injection — none found on a request path.** Raw SQL exists only with internal identifiers or bind params:
  `auth.py:1117, 1127-1133` (metadata-derived, `:uid`/`:label` bound), `app.py:425-441` (fixed DDL),
  `schema_sync.py:68` and `add_columns.py:17` (ORM metadata + `_column_ddl`), `scripts/migrate_sqlite_to_postgres.py:62,92`
  and `benchmark_db.py:25,42` (operator-run scripts/serializers, not request input). `id_guard.py:23-34`
  interpolates only table names from a hard-coded map. Search filters use bound `ilike(f"%{term}%")`, which is
  pattern-injection (a `%`/`_` in `division`/`field`/`method`/`search` widens the match) but not SQLi.
- **Command injection — none**: no `os.system`, no `subprocess` with `shell=True` on a request path (the only
  `subprocess` hit is `tests/test_audit_rc14_schema.py:9-27`).
- **Template injection — none**: no `render_template_string`, no Jinja rendering of request data. PDF text is escaped
  (`routes/reports.py:136-155, 278` `html.escape`).
- **Deserialization — none**: no `pickle`, no `yaml.load`, no `eval(`/`exec(` in app code.
- **Path traversal**: `routes/emissions.py:2558-2563` allow-lists `.csv`/`.xlsx`, then `tempfile.mkstemp(suffix=ext)`
  + `file.save(path)` (`:2591-2593`) — the client filename never touches the path. `upload_errors`
  (`:2643-2656`) serves `get_job_error_csv_path(job_id)` after `_job_visible` (`:2625-2631`), and the path comes from
  the server-side job store (`background_processor.py:279-296`), not the client. `.xls` is rejected explicitly.
- **XXE**: XML surfaces are `openpyxl.load_workbook` (`background_processor.py:584`, `read_only=True, data_only=True`)
  and ReportLab; neither resolves external entities by default, and no `defusedxml`/`lxml` parse of user XML exists.
  Residual risk is the library-default answer, not a code-visible flaw.
- **Zip/xlsx bomb**: **no guard.** `ext == ".xlsx"` is verified only by a 4-byte `PK\x03\x04` check
  (`emissions.py:2596-2607`); `MAX_CONTENT_LENGTH` (50 MB, `config.py:109`) limits the *compressed* body only. A
  ~1 MB xlsx whose sheet XML inflates to gigabytes is passed to openpyxl in a background thread. `MAX_IMPORT_ROWS =
  50_000` (`background_processor.py:465`) is enforced **after** parsing, so it does not bound decompression.
- **Unrestricted file type/size**: type is restricted; size only by the 50 MB body cap; no per-user quota; the
  temp file lands in the OS temp dir (`background_processor.py:16-18`), so a flood also consumes host disk.
- **CSV/formula injection — handled.** `routes/reports.py:43-49` `_safe_excel_value` and `routes/qaqc.py:689-696`
  `_sanitize_csv` both prefix `= - + @ \t \r %` after `lstrip()`. Note the XLSX exports leave *some* user-derived
  strings unpassed through the helper (`routes/reports.py:1204` `s.survey_date`, `:1225` `s.operator_notes` is
  covered — `survey_date` is not), a Low-severity residual.
- **Non-finite JSON** is rejected globally (`app.py:158-164`, `input_validation.py:39-53`) and sanitized on output
  (`app.py:142-150`) — a strong, unusual control.

---

## 5. SECRETS & CONFIG

- **C1 — hard-coded production `SECRET_KEY`.** `docker-compose.yml:13` sets
  `SECRET_KEY=enterprise-ghg-production-secret-change-in-prod` in a service that is built with
  `FLASK_ENV=production` (`:11`). The production guard (`config.py:19-28`) only rejects `None` and the three exact
  strings `dev-secret-key-change-in-prod-please`, `secret`, `changeme`, so this value passes and the documented
  deployment path ships with a world-readable signing key.
- **Committed secrets check**: root `.gitignore` ignores `.env`, `*.env`, `*.db`, and `new/server/ghg_app.db*`.
  `git ls-files` shows **no** tracked `.env` or `.db`; the only tracked binaries are `new/server.rar` (409 KB) and
  `new/server/calculations/calculations.rar` (32 KB), last touched by commit `fbc6ea69`. `new/server/.env` exists on
  disk with exactly one key, `LOGIN_RATE_LIMIT` (no secret value); `new/client/.env` holds only `VITE_API_URL`.
  `.env.example` files hold only `CHANGEME`-style placeholders. **Report only:** `docker-compose.yml:12-13, 24-25`
  (`DATABASE_URL`/`POSTGRES_PASSWORD` inline), and the untracked DB backups listed in §7.
- **CORS** (`app.py:37-44`, `config.py:38-49`): explicit origin list (never `*` — compatible with
  `supports_credentials=True`), `allow_headers` includes `X-CSRFToken`, methods enumerated. Two issues: the default
  list is dev origins (`localhost:5173-5175`, `127.0.0.1:...`, `localhost:3000`) which also applies when
  `FLASK_ENV=production` and `ALLOWED_ORIGINS` is unset, and `https://kaljah.github.io` is **force-appended even if
  the operator removes it** (`config.py:48-49`), i.e. any script able to serve under that Pages origin can send
  credentialed cross-origin requests. `new/server/.env.example:21` shows a *different* list than the default, so the
  documented and effective values diverge.
- **Security headers** (`app.py:213-223`): CSP `default-src 'self'; script-src 'self'; style-src 'self'
  'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; img-src 'self' data:
  https:; connect-src 'self'` — no `'unsafe-inline'` for scripts (good), but `style-src 'unsafe-inline'` and
  `img-src https:` are broad; `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`,
  `Referrer-Policy: strict-origin-when-cross-origin` are set. **Missing: `Strict-Transport-Security`,
  `Permissions-Policy`, `Cross-Origin-Opener-Policy`, `Cross-Origin-Resource-Policy`.**
- **Secrets in logs**: `services/email_service.py:26-29` logs recipient address plus the first 200 chars of the mail
  body at WARNING when SMTP is unset (no credentials in that body today, but the pattern invites future leakage);
  `:49,52` log the recipient. `app.py:239-242` logs method/path/status/duration/request-id only.
- **Copernicus credentials at rest** (`auth.py:685-689`, `save_setting_to_db` `:724-739`): stored as plaintext JSON in
  `SystemSetting` and mirrored in module memory. Masking exists on read (`:828-834`, `:967-971`) and mask-writes are
  refused (`:906`, `:938`), but the values are org-wide and readable by any authenticated user (§6/H5).
- **TLS assumptions**: session cookie `Secure` in production, `ProxyFix` opt-in (`app.py:64-66`), HSTS absent. The
  Postgres DSN is plaintext in compose; no `sslmode` is set for external databases.

---

## 6. RATE LIMITING & DoS

- **Storage** `memory://` (`config.py:116`), default `200 per minute` + `2000 per hour`
  (`extensions.py:38-46`), keyed by `user:{id}` when authenticated else `get_remote_address()`
  (`extensions.py:25-35`). Consequences: counters are **per process** (the shipped `Dockerfile:44` runs
  `gunicorn --workers 4`), reset on restart/deploy, and are disabled outright in tests
  (`tests/conftest.py`). Effective limits are ~4× the configured value, and the login limit becomes a ~4×
  brute-force budget. Redis is only a comment (`extensions.py:23`, `config.py:114-116`).
- **Per-route limits — only 6 exist**: `auth.py:254` register 10/h, `:338` login 20/15 min, `:413` forgot-password
  5/15 min, `:485` logout 60/min, `:592` change-password 5/h, `emissions.py:504` bulk-upload 20/min.
- **Sensitive endpoints with *no* per-route limit** (global default only): `POST /api/emissions/upload/start`
  (each call = temp file + a thread), `POST /api/reports/generate`, `GET /api/reports/export`,
  `GET /api/reports/ogmp-export`, `GET /api/reports/master-annual-report`, `POST /api/satellite/*` (outbound HTTPS),
  `POST /api/data/production/bulk-import`, `GET /api/auth/users`, `PUT /api/auth/settings` (setting `gwp_standard`
  triggers `recalculate_all_emissions_gwp`, `auth.py:924-928` — a full-table UPDATE of every `Emission` row, plus a
  loop over `Scope2Emission.query.all()`, `:764-796`).
- **Unbounded query/report work**: `routes/qaqc.py:114-137` loads **every** non-flagged `Emission` row with no
  `LIMIT` to compute per-process medians, then runs `inventory_uncertainty` four times (`:203`);
  `routes/audit.py:406` loads the entire `ActivityLog` and hashes it per request;
  `routes/reports.py:161-173` sums the whole result set in Python and `:243-257` renders up to `PDF_DETAIL_ROWS = 500`
  detail rows (`:36`), while the OGMP XLSX caps at 1,500 emissions (`:1087-1097`) but runs three aggregate queries
  **per facility** (`:945-968`, `:1260-1273`).
- **Thread-per-upload**: `background_processor.py:500-516` spawns a raw `threading.Thread` per job with no
  concurrency cap, semaphore, or queue; each thread parses a whole workbook and holds up to 50,000 rows
  (`:465`) until a single commit. N concurrent uploads = N unbounded threads plus host temp-disk growth.
- **MAX_CONTENT_LENGTH** 50 MB (`config.py:109`) — 413s are handled by the generic HTTPException branch
  (`app.py:263-273`); note the decompressed-size hole in §4.
- **ReDoS**: the regexes in play are linear — `input_validation.py:14` number matcher, `:146/148` category
  matchers, and `app.py:193` `^[A-Za-z0-9\-]{1,64}$` on the caller-supplied `X-Request-ID`. No nested quantifiers
  over attacker-controlled length were found.
- **SSE worker occupancy**: `routes/notifications.py:86-152` pins a worker thread for up to
  `MAX_STREAM_DURATION = 45 s` per connection with a 2 s DB poll loop and no cap on concurrent streams.

---

## 7. DATA PROTECTION

- **PII/financial data in logs**: `utils.log_activity_and_notify` (`utils.py:210-250`) persists `user_name`,
  `ip_address` (`request.remote_addr`; spoofable if `ProxyFix` is enabled without a trusted proxy), `details`
  (contains emails, e.g. `auth.py:308, 390, 460, 629, 1195`), plus `old_values`/`new_values` JSON verbatim
  (`utils.py:233-234`) — so before/after emission values and production volumes land in `activity_log`.
  Returned to clients by `routes/audit.py:173-214` (scoped: IT roles see security actions only, `:64-65`; regional
  users see their own rows or their facilities', `:66-68`).
- **Stack traces**: the global handler (`app.py:261-300`) logs `traceback.format_exc()` server-side and returns a
  generic `{"error": "Internal server error", "code": 500, "request_id": ...}`; `utils.internal_error`
  (`utils.py:284-296`) does the same. Validation errors echo only the field name (`input_validation.py`,
  `input_validator` handlers `app.py:153-155`). Client also rewrites non-string 500 bodies (`api.js:72-83`).
  Residual: Copernicus failures echo the upstream `error_description`/body (`services/sentinel5p.py:100-116`) and
  `data.py:205` returns `Concurrency conflict: {retry_err}` — DB text in a 409.
- **Audit-log integrity**: there is **no** delete/update route for `ActivityLog` anywhere (all `methods=[...DELETE]`
  routes touch emissions/facilities/users/notifications only). But `GET /api/audit/verify-chain`
  (`routes/audit.py:395-431`) recomputes the SHA-256 chain **from the live rows** with the genesis hash hard-coded
  (`:408`) and no stored per-row hash to compare against, so it returns `"status": "verified"`,
  `"is_tamper_evident": true` unconditionally — a forensic claim that cannot fail (H3). The hashed payload
  (`:413`) also excludes `details`, `old_values`, `new_values`, `metadata_json`, `ip_address` and `facility_id`.
  `notifications.py:235-256` lets a user delete their own security notifications, and `:259-273` deletes all of
  their own — a self-service trail for a user to erase (`utils.py:252-278` also creates those rows).
- **Backups / DB exposure**: tracked in git — `new/server.rar` (409 KB) and
  `new/server/calculations/calculations.rar` (32 KB), i.e. a full server snapshot committed to VCS. Untracked but
  present on disk: `new/server/backups/ghg_app_20260920_172952.db` (**1.91 GB**) and
  `..._173146.db` (**2.34 GB**), `new/server/ghg_app.db` (+`-wal`/`-shm`), `new/server/ghg_app.db.bak_before_scope_deletion`,
  `new/server/database.db`, `new/server/ghg_emissions.db`, `new/instance/ghg_app.db`, `users_v2.db`, plus `audit/db/*.db`.
  These hold `password_hash` (scrypt) and all emissions data; `*.db` is gitignored and no `.db`/`.bak` is tracked, so
  the leak is filesystem/host-level rather than repository-level.
- **Outbound third parties** (`services/sentinel5p.py:19-22, 85-87, 132-197, 287-324`):
  `identity.dataspace.copernicus.eu` (OAuth2 password/client-credentials — org Copernicus username+password or
  client id/secret leaves the system), `catalogue/stac/sh.dataspace.copernicus.eu` (facility lat/lon, date ranges,
  QA threshold, i.e. **the location of the operator's assets**), and SMTP
  (`services/email_service.py:42-47`, STARTTLS, login only if both user and password are set — note `use_tls`
  defaults true but a plaintext connection is used if `SMTP_USE_TLS=false`).
- **Token handling**: Copernicus access tokens are cached **in process memory** keyed by a hash of the credentials
  (`_token_cache`, `sentinel5p.py:47, 191-195`) — acceptable, but the cache is per worker and never invalidated on
  credential rotation, and the credentials themselves are stored plaintext (`auth.py` settings).
- **Readiness probe** (`app.py:538-559`) is unauthenticated and discloses `version` and WAL size.

---

## 8. DEPENDENCY & RUNTIME

- `new/server/requirements.txt`: `Flask==3.0.3`, `Flask-SQLAlchemy==3.1.1`, `Flask-Migrate==4.0.5`,
  `python-dotenv==1.0.1`, `flask-wtf==1.2.1`, `Flask-Limiter==3.5.0`, `python-dateutil==2.8.2`,
  `flask-swagger-ui==4.11.1`; ranges: `Werkzeug>=3.0.6` (installed locally **3.0.3**), `Flask-CORS>=5.0.0`,
  `reportlab>=4.1.0`, `matplotlib>=3.8.0`, `openpyxl>=3.1.3`, `cachetools>=5.3.0`, `requests>=2.31.0`,
  `gunicorn>=21.2.0`, `psycopg2-binary>=2.9.9`. Risk: 8 unpinned/`>=` dependencies (Flask-CORS and openpyxl are
  security-relevant), no lockfile, no `pip-audit`/Dependabot visible in-repo, and the local interpreter already
  violates the Werkzeug floor — the environment is not reproducible from the manifest.
- **Debug mode**: `app.py:562-572` runs `debug=is_debug` from `FLASK_DEBUG` (default false) and binds
  `127.0.0.1`; the interactive debugger is never enabled in the container path.
- **ProxyFix** (`app.py:64-66`): opt-in via `USE_PROXY_FIX=true`, `x_for=1, x_proto=1, x_host=1, x_prefix=1`. Safe
  only behind exactly one trusted proxy; otherwise `X-Forwarded-For` becomes attacker-controlled and audit
  `ip_address` is forgeable.
- **Swagger** (`app.py:340-357`): disabled unless `FLASK_ENV != "production"` or `ENABLE_PUBLIC_SWAGGER=true`. The
  Docker path sets `FLASK_ENV=production` (`Dockerfile:20`, `docker-compose.yml:11`), so production exposure
  requires an explicit opt-in — correct. The `csrf.exempt(swaggerui_blueprint)` call would also exempt any future
  mutation endpoint routed through that prefix.
- **Error handlers**: `404` (`app.py:247-258`), `CSRFError` (`:129-134`, returns `str(e)` from its own handler — a
  Flask-WTF message, not a stack trace), `ValidationError` (`:153-155`), catch-all `Exception` (`:261-300`).
  `internal_error` in `utils.py:284-296` is used consistently for DB-shaped failures.
- **Runtime**: `Dockerfile:14` `python:3.11-slim`; `:44` `gunicorn --workers 4 --timeout 120` in one stage, then a
  **second `FROM python:3.11-slim` at line 46 with no `COPY --from=frontend-builder`** — the effective image never
  contains `static/dist`, so the built SPA is missing (packaging defect; it also orphans the first stage's
  `flask db upgrade` entrypoint at `:44`). `docker-compose.yml:12-13` injects the weak production secret and
  `:24-28` publishes Postgres on the host with `test:test`.
- **Framework versions vs known-bad practice**: Flask 3 / SQLAlchemy 2 / flask-wtf 1.2.1 are current-generation;
  Werkzeug scrypt defaults are used; no `md5`/`sha1` for passwords (the only SHA-1 is Flask's own session HMAC,
  which is library behaviour). The concrete version problems are the unpinned set above and the
  installed-vs-declared Werkzeug mismatch.

---

## 9. FINDINGS TABLE

Confidence: **code-backed** = the flaw is visible in the cited lines; **theoretical** = depends on deployment or
configuration not verifiable from source.

### Critical

| # | Finding | file:line | Exploit | Fix |
|---|---|---|---|---|
| C1 | Production `SECRET_KEY` hard-coded and outside the guard's blacklist | `docker-compose.yml:11,13`; `config.py:19-28,34-36` | Attacker reads the public repo, forges a Flask session cookie (`cookie-session` salt + HMAC-SHA1) with `user_id=<admin>` and the matching `sv`, and is authenticated as that user — and can mint CSRF tokens — without any password. | Remove the literal; require `SECRET_KEY` from the runtime secret store and reject any value matching `(dev|change|secret|test|example)` or shorter than 32 chars. **code-backed** |
| C2 | Postgres published to the host with static credentials | `docker-compose.yml:12,24-28` | Anyone who can reach port 5432 logs in as `test`/`test` and reads/writes the whole GHG database (users, emissions, production, audit log) directly, bypassing the app. | Do not publish 5432; generate credentials from env/secret store; restrict with an internal network. **code-backed** |

### High

| # | Finding | file:line | Exploit | Fix |
|---|---|---|---|---|
| H1 | `memory://` limiter × 4 gunicorn workers | `config.py:116`; `extensions.py:38-46`; `Dockerfile:44` | Login budget is ~80 attempts/15 min/IP instead of 20, and it resets on every restart/redeploy, so credential stuffing against `POST /api/auth/login` is not effectively bounded. | Set `RATELIMIT_STORAGE_URI=redis://…` in production and scale workers behind shared state. **code-backed** |
| H2 | No lockout, no failed-login record | `auth.py:336-408`; `routes/audit.py:228,241` | Nothing throttles a single account beyond the IP limiter and no `FAILED_LOGIN` row is ever written, so a slow password-spray against one account is invisible in the audit UI (`security_alerts` is always 0). | Persist failed attempts per account and implement progressive lockout/backoff; alert on thresholds. **code-backed** |
| H3 | Audit "hash chain" is self-referential and always reports verified | `routes/audit.py:395-431` (`:408, 413-415, 422-431`) | Anyone with DB write access edits an `ActivityLog.details` and `GET /api/audit/verify-chain` still answers `"is_tamper_evident": true` — the assurance claim in the docstring is false. | Persist each block hash (or an HMAC anchored outside the DB) and compare recomputed vs stored, failing on mismatch. **code-backed** |
| H4 | Satellite routes block only `it_admin`; `it_manager`/`it` can query and **write** OGMP survey records | `routes/satellite.py:111, 134, 205, 349` vs `utils.py:31`; `new/client/src/App.jsx:36-42` | An `it_manager` or `it` account — a role with zero facility-data access everywhere else — calls `POST /api/satellite/sentinel5p/export-to-ogmp` and inserts an `OgmpSurvey` into the regulatory ledger, or reads satellite data the client hides from them. | Use a single shared predicate (e.g. `require_facility_access`/`is_it_role`) in all four handlers. **code-backed** |
| H5 | Copernicus credentials stored plaintext and returned to any authenticated user | `auth.py:807-834, 887-921`; `routes/satellite.py:16-62` | Any logged-in user (including `it`/`user`) calls `GET /api/auth/settings` and receives the org-wide `copernicus_username`/`client_id` (secrets masked, identifier not), and the values sit in cleartext in `SystemSetting` for anyone with DB/file access. | Restrict the settings response to admin/superuser, store credentials in a secret manager, and drop the per-user credential fallback. **code-backed** |
| H6 | `it_manager`/`it` can reset **any** user's password, including `admin`, with no rank check and no forced change | `auth.py:1152-1202` (`:1153` `it_access_required`, `:1176-1178`) | A compromised or malicious IT account resets the `admin` password to a value it chooses, logs in as the admin, and takes over business compliance authority (the very boundary `auth.py:1035-1036` tries to enforce on role assignment). | Restrict resets to lower-ranked targets, require the target's old password or a second approver, and flag the new credential as must-change. **code-backed** |
| H7 | Unbounded upload threads plus no decompression-bomb bound | `emissions.py:2591-2622`; `background_processor.py:465, 500-516` | An authenticated uploader starts many concurrent 50 MB xlsx uploads; each spawns a thread that expands an attacker-crafted workbook (highly compressible sheet XML) into memory up to a single 50,000-row commit, exhausting worker memory and host temp disk. | Cap concurrency with a bounded queue/semaphore, validate the inflate ratio and uncompressed size before parsing, stream rows instead of buffering. **code-backed** |
| H8 | `SameSite=None` in production removes the browser CSRF barrier and exposes the un-tokenable SSE stream | `config.py:92-95`; `routes/notifications.py:64-159`; `config.py:103` | A page on any origin sends the victim's session cookie, and can open `EventSource('/api/notifications/stream')` to read notification titles/messages cross-origin; `WTF_CSRF_SSL_STRICT=False` removes the Referer fallback. | Serve the SPA same-site and use `SameSite=Lax`; if cross-site is unavoidable, keep strict referrer checks on and treat SSE as data-bearing. **code-backed** |

### Medium

| # | Finding | file:line | Exploit | Fix |
|---|---|---|---|---|
| M1 | Unbounded work on request: full `Emission` scan for medians, full `ActivityLog` scan + SHA-256 chain, whole-table GWP recalculation on a settings write | `routes/qaqc.py:114-137, 203`; `routes/audit.py:406`; `auth.py:764-796, 924-928` | A few concurrent calls to `/api/qaqc/dashboard` or a `gwp_standard` change pin CPU/DB and stall all workers (no per-route limit on `PUT /api/auth/settings`). | Precompute materialized aggregates/medians, paginate, and move recalculation to an offline job. **code-backed** |
| M2 | Missing security headers: no HSTS, no Permissions-Policy, no COOP/CORP; `style-src 'unsafe-inline'`, `img-src https:` | `app.py:213-223` | A network attacker downgrades the first request (no HSTS) and injection sinks are wider than necessary. | Add HSTS (`max-age=31536000; includeSubDomains`), Permissions-Policy, COOP/CORP; tighten CSP. **code-backed** |
| M3 | `https://kaljah.github.io` force-appended to CORS origins; dev origins are the production default | `config.py:38-49` | If the Pages project is ever attacker-influenced (or simply untrusted), it can issue credentialed cross-origin API requests as any logged-in user, and an unset `ALLOWED_ORIGINS` in production still trusts localhost. | Drop the forced append, make the default empty in production, and fail startup when `ALLOWED_ORIGINS` is unset in production. **code-backed** |
| M4 | `WTF_CSRF_SSL_STRICT=False` | `config.py:103-104` | The token becomes the single CSRF control; any token-cookie confusion or XSS-adjacent leak is immediately exploitable. | Re-enable strict referrer checking for HTTPS deployments. **code-backed** |
| M5 | Unpinned dependencies and a declared/installed Werkzeug mismatch | `requirements.txt` (8 `>=` lines, `Werkzeug>=3.0.6`) | A future resolver pull of a vulnerable `Flask-CORS`/`openpyxl` version ships silently; the current environment already violates the manifest. | Pin exact versions, add a lockfile and an automated CVE scan. **code-backed** |
| M6 | Dockerfile declares a second `FROM` without copying the frontend build | `Dockerfile:38, 44-46, 65, 72` | The deployed image lacks `static/dist`, so either the SPA is missing (functional) or operators silently deploy a stale external build with unknown content; the first stage's DB-upgrade entrypoint is dead code. | Remove the duplicate stage and keep one `CMD` that runs `flask db upgrade` then gunicorn. **code-backed** |
| M7 | CSV/XLSX sanitisation missed on one export field | `routes/reports.py:1204` (`s.survey_date`) vs `:43-49` | A crafted survey date/notes value beginning `=`/`+`/`@` is written unquoted into the OGMP workbook and executes in a reviewer's Excel (DDE). | Pass every user-derived string cell through `_safe_excel_value` and set the workbook's text format. **code-backed** |
| M8 | Admin-set passwords can be reused/weak and must not change on next login | `auth.py:1167-1178`, `:1195` (email text) | An IT admin who resets a password to a value the user already knows (or the admin keeps) retains standing access after handing over, and the audit row is the only trace. | Generate a one-time random credential, force rotation at first login, and never display a password the user chose. **code-backed** |

### Low

| # | Finding | file:line | Exploit | Fix |
|---|---|---|---|---|
| L1 | Plaintext HTTP session / no HSTS for the SMTP-less path; `use_tls` can be disabled | `services/email_service.py:22, 42-47` | `SMTP_USE_TLS=false` in a hostile network exposes SMTP AUTH credentials in transit. | Default `use_tls` from the port (465 ⇒ implicit TLS) and refuse plaintext AUTH. **code-backed** |
| L2 | `verify_audit_chain` loads all logs into memory | `routes/audit.py:406-420` | A large `activity_log` yields slow, memory-hungry responses. | Stream/chunk the chain and cache the head. **code-backed** |
| L3 | Unauthenticated schema-disclosure endpoints | `routes/emissions.py:1025, 1856`; `routes/managedata.py:978-983` (alias of `routes/audit.py:217-220`) | Anonymous callers enumerate process types, units and factor semantics from the import templates. | Put the templates behind `@login_required`. **code-backed** |
| L4 | `delete_cookie` without `domain`; `SESSION_COOKIE_NAME` never set | `auth.py:509-516`; `config.py:91-99` | A cookie issued on a parent domain survives logout, leaving a stale credential in the browser. | Set an explicit cookie name/domain and delete with the same attributes. **code-backed** |
| L5 | Unauthenticated probes leak version and WAL size | `app.py:526-559` | An attacker fingerprints the exact build and DB write activity. | Keep `/health/live` minimal and gate the detailed probe to the orchestrator network. **code-backed** |
| L6 | `ProxyFix` trusts one hop when enabled | `app.py:64-66`; `utils.py:228` | Without a trusted proxy, `X-Forwarded-For` is attacker-controlled and audit `ip_address` is forgeable. | Only enable behind a known proxy and validate the hop count; prefer a proxy-provided identity header. **theoretical** |
| L7 | Formatted error text echoed to clients | `services/sentinel5p.py:100-116`; `routes/data.py:203-205` | Upstream/CDB error strings (occasionally including the submitted username context) reach the browser and logs. | Return fixed messages and log details server-side only. **code-backed** |
| L8 | Repository carries full server snapshots and multi-GB DB copies | tracked `new/server.rar`, `new/server/calculations/calculations.rar`; untracked `new/server/backups/*.db` (1.91 GB + 2.34 GB), `new/server/ghg_app.db*`, `new/instance/ghg_app.db`, `users_v2.db`, `audit/db/*.db` | Anyone with host/repo read access obtains scrypt hashes of every account plus the entire emissions/production history. | Purge the archives from history, move secrets out, add `*.rar`/`*.bak` to `.gitignore`, and store backups encrypted off-host. **code-backed** |
| L9 | Security notification self-deletion | `routes/notifications.py:235-273` | A user erases "Your Password Has Been Reset" and equivalent security notices from their own feed, weakening the in-app trail (the `ActivityLog` row survives). | Make security-type notifications non-deletable by the recipient. **code-backed** |

### Verified as *not* vulnerable (explicitly checked, so a future reviewer does not repeat the work)

- `routes/custom_factors.py:152-155` — the blank line between the two `@custom_factors_bp.route(...)` decorators does
  **not** create an unauthenticated create-factor route; `superuser_required` applies to both paths (validated in a
  scratch interpreter: both return 403). *False positive.*
- `new/client/src/api.js:44-63` retry-on-400 does **not** bypass CSRF (the retry still carries the token, and axios
  cannot set `Cookie`); worst case is one duplicated POST per expiry event.
- `routes/auth.py:1113-1147` `delete_user` dynamic SQL uses metadata-derived identifiers with bound values — not injectable.
- No `pickle`, `yaml.load`, `eval(`/`exec(`, `render_template_string`, `os.system`, `shell=True`, `verify=False`,
  `md5`/`sha1` password hashing, or `random.*` credential generation exists in application code.
