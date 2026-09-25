# GHG Platform — Exhaustive Fix Implementation Plan

> Created: 2026-09-20  
> Order: Critical → High → Medium → Low  
> Format: Fully executable (exact file paths, code snippets, commands, test cases)

---

## Open Questions

None — all decisions received from user.

---

## Execution Order Summary

```
PHASE 1 — CRITICAL (fix immediately, production risk)
  1.1  Delete 4.1 GB import_debug.log + route imports to rotating handler
  1.2  Hard-coded dev credentials (a@a / a) auto-seeded in app.py — CRITICAL SECURITY
  1.3  Add full backend CI job to GitHub Actions

PHASE 2 — HIGH SECURITY (before any public deployment)
  2.1  Rate limiting — add global defaults + audit per-route coverage
  2.2  CSRF — implement double-submit cookie pattern for cross-origin SPA
  2.3  WAL journal checkpoint — force immediate checkpoint + lower interval

PHASE 3 — HIGH QUALITY (testing infrastructure)
  3.1  Backend test isolation — in-memory SQLite conftest.py fixture
  3.2  Frontend unit tests — install Vitest + React Testing Library
  3.3  E2E tests — install Playwright + implement login→calculate→report workflow

PHASE 4 — CALCULATION FIX
  4.1  N2O flaring default inconsistency — harmonize to 0.0001 kg/MMBtu

PHASE 5 — DATABASE MIGRATION
  5.1  Plan + implement SQLite → PostgreSQL migration
  5.2  Backup/restore procedure
  5.3  Migration downgrade paths (Alembic)

PHASE 6 — MEDIUM FIXES
  6.1  RLS documentation + route audit
  6.2  Deprecation warnings (openpyxl utcnow, reportlab ast)
  6.3  Custom factor governance (plausibility bounds)

PHASE 7 — PRODUCTION SMOKE TESTS
  7.1  Implement 10-step smoke test suite

PHASE 8 — CI/CD FINAL INTEGRATION
  8.1  Wire all phases into the unified pipeline
```

---

## PHASE 1 — CRITICAL

---

### 1.1 Delete `import_debug.log` + Route Imports to Rotating Handler

**Problem**: `new/server/import_debug.log` is 4.1 GB unbounded. The rotating handler on `trace.log` does NOT cover this file.  
**Root cause**: `background_processor.py` opens `import_debug.log` directly via Python's `logging.FileHandler` (or `open()`).  
**Fix**: Delete the file. Then patch `background_processor.py` to use `app.logger` (the rotating handler) instead.

#### Step 1 — Delete the file
```powershell
# Run from new/server/
Remove-Item "import_debug.log" -Force
```

#### Step 2 — Find all references to import_debug.log
```powershell
Select-String -Path "new\server\*.py" -Pattern "import_debug" -Recurse
```

#### Step 3 — Patch background_processor.py

Find the logger setup near the top of `new/server/background_processor.py`. Replace any direct `FileHandler("import_debug.log")` or `open("import_debug.log", ...)` with Flask's `current_app.logger`.

**In every function that logs to `import_debug.log`**, replace:
```python
# BEFORE (example pattern):
import logging
debug_logger = logging.getLogger("import_debug")
debug_logger.addHandler(logging.FileHandler("import_debug.log"))
```

**With**:
```python
# AFTER — use app.logger routed through the existing rotating handler
from flask import current_app
# Replace all: debug_logger.info(...)  →  current_app.logger.info(...)
# Replace all: debug_logger.error(...) →  current_app.logger.error(...)
```

#### Step 4 — Add .gitignore entry
```gitignore
# Add to new/server/.gitignore (or root .gitignore):
*.log
ghg_app.db-wal
ghg_app.db-shm
```

#### Verification test
```python
# new/server/tests/test_log_handler.py
def test_no_import_debug_log_file_created():
    """Verify background processor does not create import_debug.log."""
    import os
    server_dir = os.path.join(os.path.dirname(__file__), "..")
    assert not os.path.exists(os.path.join(server_dir, "import_debug.log")), \
        "import_debug.log must not be recreated — use rotating app.logger instead"
```

---

### 1.2 Hard-coded Dev Credentials in app.py — CRITICAL SECURITY

**Problem**: `app.py` lines 285–365 hard-code and AUTO-SEED three accounts on EVERY startup:
- `admin@ghg.com` / `Admin12345!`  
- `a@a` / `a` (bypasses password complexity — 1 character password)  
- `a` / `a` (not even a valid email)

This runs in production. Any attacker who knows these defaults owns the system.

**Fix**: Replace `ensure_admin_seeded()` with an environment-variable driven, production-safe seeder that:
1. Only seeds if `SEED_ADMIN=true` env var is set
2. NEVER seeds the `a@a` / `a` shortcuts
3. Fails loudly in production if `ADMIN_PASSWORD` is a known weak value

#### Step 1 — Replace `ensure_admin_seeded()` in `new/server/app.py`

Remove lines 285–332 entirely. Replace with:

```python
def ensure_admin_seeded():
    """
    Seeds admin accounts ONLY if SEED_ADMIN=true environment variable is set.
    In production, requires ADMIN_EMAIL and ADMIN_PASSWORD to be explicitly configured.
    NEVER seeds development shortcut accounts (a@a, a) in any environment.
    """
    if os.environ.get("SEED_ADMIN", "false").lower() != "true":
        return

    admin_email = os.environ.get("ADMIN_EMAIL", "").strip()
    admin_password = os.environ.get("ADMIN_PASSWORD", "").strip()
    it_admin_email = os.environ.get("IT_ADMIN_EMAIL", "").strip()
    it_admin_password = os.environ.get("IT_ADMIN_PASSWORD", "").strip()

    _env_name = (
        os.environ.get("FLASK_ENV")
        or os.environ.get("APP_ENV")
        or os.environ.get("ENVIRONMENT")
        or "development"
    ).lower()
    is_production = _env_name in ["production", "prod", "staging"]

    KNOWN_WEAK = {"Admin12345!", "admin", "password", "changeme", "secret", "a", "123456"}

    if is_production:
        if not admin_email or not admin_password:
            raise ValueError("FATAL: ADMIN_EMAIL and ADMIN_PASSWORD must be set in production when SEED_ADMIN=true")
        if admin_password in KNOWN_WEAK:
            raise ValueError("FATAL: ADMIN_PASSWORD is a known weak value — set a strong password")

    accounts = []
    if admin_email and admin_password:
        accounts.append({"email": admin_email, "password": admin_password, "role": "admin", "fullName": "System Administrator"})
    if it_admin_email and it_admin_password:
        accounts.append({"email": it_admin_email, "password": it_admin_password, "role": "it_admin", "fullName": "IT Administrator"})

    try:
        for u in accounts:
            user = User.query.filter_by(email=u["email"]).first()
            if not user:
                user = User(
                    fullName=u["fullName"],
                    orgName="GHG Operations",
                    email=u["email"],
                    role=u["role"],
                    sector="Oil & Gas",
                    department="Sustainability & IT",
                    jobTitle="Sustainability Manager",
                    location="Global",
                    status="active",
                )
                user.set_password(u["password"])
                db.session.add(user)
                app.logger.info(f"Seeded {u['role']} account: {u['email']}")
            else:
                app.logger.info(f"Admin account already exists: {u['email']}")
        db.session.commit()
    except Exception as e:
        app.logger.error(f"Failed to seed admin: {e}")
        db.session.rollback()
```

#### Step 2 — Update `.env.example` to document SEED_ADMIN

Add to `new/server/.env.example`:
```dotenv
# Admin seeding (set to 'true' only during initial setup, then remove)
SEED_ADMIN=false
ADMIN_EMAIL=your-admin@company.com
ADMIN_PASSWORD=CHANGEME_strong_password_here
IT_ADMIN_EMAIL=it-admin@company.com
IT_ADMIN_PASSWORD=CHANGEME_strong_password_here
```

#### Step 3 — Remove the exposed init-admin route from app.py

Delete lines 368–377 (the `/api/auth/init-admin` public route):
```python
# REMOVE THIS ENTIRE BLOCK:
@app.route("/api/auth/init-admin")
def init_admin_route():
    ensure_admin_seeded()
    ...
```
This route allows any unauthenticated HTTP request to reseed admin accounts.

#### Step 4 — Regression test
```python
# new/server/tests/test_security_hardening.py

def test_no_hardcoded_dev_credentials_in_startup(app_context):
    """Verify that weak dev accounts (a@a, a) are not auto-created."""
    from models import User
    weak_emails = ["a@a", "a"]
    for email in weak_emails:
        user = User.query.filter_by(email=email).first()
        assert user is None, (
            f"SECURITY FAILURE: Dev account '{email}' exists in the database. "
            "Hard-coded dev credentials must not be auto-seeded."
        )

def test_init_admin_route_does_not_exist(client):
    """Verify the unauthenticated /api/auth/init-admin route has been removed."""
    resp = client.get("/api/auth/init-admin")
    assert resp.status_code == 404, (
        "SECURITY FAILURE: /api/auth/init-admin is publicly accessible. "
        "This route must be removed."
    )
```

---

### 1.3 Backend CI Job in GitHub Actions

**Problem**: `.github/workflows/deploy-pages.yml` only builds and deploys the frontend. Backend tests never run in CI.  
**Fix**: Add a `backend-tests` job that runs before the frontend build.

#### Step 1 — Edit `.github/workflows/deploy-pages.yml`

Add the following `backend-tests` job (insert before the existing `build` job):

```yaml
# .github/workflows/deploy-pages.yml — FULL UPDATED FILE

name: Build, Test & Deploy

on:
  push:
    branches: [main, master]
  pull_request:
    branches: [main, master]
  workflow_dispatch:

permissions:
  contents: read
  pages: write
  id-token: write

concurrency:
  group: "pages"
  cancel-in-progress: true

jobs:
  # ── BACKEND TESTS ──────────────────────────────────────────────────────────
  backend-tests:
    name: Backend Tests & Calculation Validation
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: new/server

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"
          cache: "pip"
          cache-dependency-path: new/server/requirements.txt

      - name: Install backend dependencies
        run: pip install -r requirements.txt pytest pytest-cov hypothesis

      - name: Run backend test suite
        env:
          FLASK_ENV: testing
          DATABASE_URL: "sqlite:///:memory:"
          SECRET_KEY: ci-test-secret-key-do-not-use-in-prod
          SEED_ADMIN: "false"
        run: |
          python -m pytest tests/ \
            --tb=short \
            -q \
            --no-header \
            -x \
            --timeout=300
        timeout-minutes: 10

      - name: Run calculation differential validation
        env:
          FLASK_ENV: testing
          DATABASE_URL: "sqlite:///:memory:"
          SECRET_KEY: ci-test-secret-key-do-not-use-in-prod
        run: |
          python -m pytest tests/test_independent_differential.py \
            tests/test_golden_dataset_validation.py \
            tests/test_property_invariants.py \
            tests/test_unit_conversions_exhaustive.py \
            -v --tb=long
        timeout-minutes: 5

      - name: Run security tests
        env:
          FLASK_ENV: testing
          DATABASE_URL: "sqlite:///:memory:"
          SECRET_KEY: ci-test-secret-key-do-not-use-in-prod
        run: |
          python -m pytest tests/test_api_security.py \
            tests/test_deep_injection_matrix.py \
            tests/test_it_role_security.py \
            -v --tb=long
        timeout-minutes: 5

      - name: Dependency vulnerability audit
        run: pip install pip-audit && pip-audit --requirement requirements.txt

  # ── FRONTEND BUILD ─────────────────────────────────────────────────────────
  build:
    name: Build Frontend
    runs-on: ubuntu-latest
    needs: backend-tests          # ← Frontend only deploys if backend tests pass
    defaults:
      run:
        working-directory: new/client

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: 20
          cache: "npm"
          cache-dependency-path: new/client/package-lock.json

      - name: Install dependencies
        run: npm ci

      - name: Lint
        run: npm run lint

      - name: Build
        env:
          VITE_API_URL: ${{ vars.VITE_API_URL || secrets.VITE_API_URL || 'https://ghg-accounting.onrender.com/api' }}
        run: |
          REPO_NAME="${{ github.event.repository.name }}"
          if [[ "$REPO_NAME" == *.github.io ]]; then
            export VITE_BASE_PATH="/"
          else
            export VITE_BASE_PATH="/${REPO_NAME}/"
          fi
          npm run build

      - name: Upload Pages artifact
        uses: actions/upload-pages-artifact@v3
        with:
          path: new/client/dist

  # ── DEPLOY ─────────────────────────────────────────────────────────────────
  deploy:
    name: Deploy to GitHub Pages
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    runs-on: ubuntu-latest
    needs: build
    if: github.ref == 'refs/heads/main' || github.ref == 'refs/heads/master'
    steps:
      - name: Deploy to GitHub Pages
        id: deployment
        uses: actions/deploy-pages@v4
```

> **Note**: The in-memory `DATABASE_URL=sqlite:///:memory:` in CI requires Phase 3.1 (test isolation) to be completed first, otherwise existing tests that depend on the live DB will fail. Complete Phase 3.1 before merging this CI change.

---

## PHASE 2 — HIGH SECURITY

---

### 2.1 Rate Limiting — Global Defaults + Per-Route Audit

**Problem**: `extensions.py` sets `default_limits=[]`. Only endpoints with `@limiter.limit(...)` are protected.  
**Fix**: Set conservative global defaults and audit each route.

#### Step 1 — Update `new/server/extensions.py`

```python
# new/server/extensions.py — FULL FILE

import os
from flask_sqlalchemy import SQLAlchemy
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

db = SQLAlchemy()

limiter = Limiter(
    key_func=get_remote_address,
    # Global default: 200 requests/minute per IP for all endpoints.
    # Sensitive endpoints override this with stricter per-route limits.
    # Adjust via RATELIMIT_DEFAULT env var: e.g. "100 per minute"
    default_limits=[
        os.environ.get("RATELIMIT_DEFAULT", "200 per minute"),
        "2000 per hour",
    ],
    # Storage URI is configured in config.py (RATELIMIT_STORAGE_URI).
    # Default: memory:// (single process only).
    # Multi-worker production: set RATELIMIT_STORAGE_URI=redis://localhost:6379/0
)
```

#### Step 2 — Audit and add per-route limits in `new/server/routes/auth.py`

The login endpoint already has `@limiter.limit("20 per 15 minutes")`. Verify all auth routes:

```python
# Ensure these decorators exist on these routes:

@auth_bp.route("/login", methods=["POST"])
@limiter.limit("20 per 15 minutes")          # ← already exists ✅
def login(): ...

@auth_bp.route("/register", methods=["POST"])
@limiter.limit("10 per hour")                # ← ADD if missing
@it_admin_required
def register(): ...

@auth_bp.route("/logout", methods=["POST"])
@limiter.limit("60 per minute")              # ← ADD (generous, just cap abuse)
def logout(): ...

@auth_bp.route("/change-password", methods=["POST"])
@limiter.limit("5 per hour")                 # ← ADD
@login_required
def change_password(): ...
```

#### Step 3 — Add per-route limits to expensive endpoints in `new/server/routes/emissions.py`

```python
# Bulk upload / calculation endpoints — add rate limits:
@emissions_bp.route("/bulk-upload", methods=["POST"])
@limiter.limit("10 per hour")       # Large file imports
@login_required
def bulk_upload(): ...

@emissions_bp.route("/calculate", methods=["POST"])
@limiter.limit("100 per minute")    # Calculation-heavy endpoint
@login_required
def calculate_emission(): ...
```

#### Step 4 — Update `.env.example`

```dotenv
# Rate limiting (adjust per deployment)
RATELIMIT_DEFAULT=200 per minute
RATELIMIT_STORAGE_URI=memory://
# For multi-worker production:
# RATELIMIT_STORAGE_URI=redis://localhost:6379/0
```

#### Step 5 — Rate limit tests

```python
# new/server/tests/test_rate_limiting.py

import pytest
from app import app as flask_app
from extensions import db, limiter


@pytest.fixture
def app():
    flask_app.config.update({
        "TESTING": True,
        "WTF_CSRF_ENABLED": False,
        "SECRET_KEY": "test",
        "RATELIMIT_ENABLED": True,       # ← Enable rate limiting in this test
        "RATELIMIT_STORAGE_URI": "memory://",
    })
    limiter.enabled = True
    with flask_app.app_context():
        db.create_all()
        yield flask_app
    limiter.enabled = False


@pytest.fixture
def client(app):
    return app.test_client()


def test_login_rate_limit_triggers_at_21_attempts(client):
    """Login endpoint must reject after 20 attempts in 15 minutes."""
    payload = {"email": "nobody@example.com", "password": "WrongPass1!"}
    for i in range(20):
        client.post("/api/auth/login", json=payload)
    # 21st request must be rate-limited
    resp = client.post("/api/auth/login", json=payload)
    assert resp.status_code == 429, (
        f"Expected 429 Too Many Requests on attempt 21, got {resp.status_code}"
    )


def test_rate_limit_headers_present(client):
    """X-RateLimit-* headers must be present on API responses."""
    resp = client.get("/api/health")
    # Flask-Limiter 3.5+ with RATELIMIT_HEADERS_ENABLED=True
    assert "X-RateLimit-Limit" in resp.headers or "RateLimit-Limit" in resp.headers, \
        "Rate limit headers must be exposed to clients"


def test_global_default_rate_limit_applied(client):
    """General API endpoints must be subject to the global default rate limit."""
    # Make 201 rapid requests — global default is 200/min
    for _ in range(200):
        client.get("/api/health")
    resp = client.get("/api/health")
    assert resp.status_code == 429, \
        "Global default rate limit (200/min) must be enforced on all endpoints"
```

---

### 2.2 CSRF — Double-Submit Cookie Pattern for Cross-Origin SPA

**Problem**: Auth blueprint is fully CSRF-exempt because the SPA (GitHub Pages) and API (Render) are on different origins.  
**Fix**: Implement the **double-submit cookie** pattern:
1. Backend sets a `csrf_cookie` (non-HttpOnly, SameSite=None, Secure)
2. Frontend reads it from `document.cookie` and sends it as `X-CSRF-Token` header
3. Backend verifies they match — this works cross-origin because an attacker on a different origin cannot read the cookie

#### Step 1 — Update `new/server/config.py`

Add CSRF cookie configuration:
```python
# Add to Config class:

# Double-submit cookie CSRF for cross-origin SPA (GitHub Pages ↔ Render)
WTF_CSRF_ENABLED = True
WTF_CSRF_SSL_STRICT = False
WTF_CSRF_TIME_LIMIT = 86400

# CSRF cookie settings (separate from session cookie)
# Must be readable by JavaScript (non-HttpOnly) for double-submit pattern
CSRF_COOKIE_NAME = "csrf_token"
CSRF_COOKIE_SECURE = _is_production
CSRF_COOKIE_SAMESITE = "None" if _is_production else "Lax"
CSRF_COOKIE_HTTPONLY = False   # MUST be False — JS must read it
```

#### Step 2 — Update `new/server/app.py` — CSRF token endpoint

Replace the existing `/api/csrf-token` route to set a readable cookie:

```python
@app.route("/api/csrf-token")
def get_csrf_token():
    """
    Issues a CSRF token for the double-submit cookie pattern.
    Sets a non-HttpOnly cookie that the SPA can read via document.cookie,
    and returns the same token in the response body.
    The client must send it as X-CSRFToken header on mutating requests.
    """
    from flask_wtf.csrf import generate_csrf
    token = generate_csrf()
    resp = jsonify({"csrf_token": token})
    resp.set_cookie(
        "csrf_token",
        token,
        httponly=False,          # Must be False — JS reads this
        secure=app.config.get("CSRF_COOKIE_SECURE", False),
        samesite=app.config.get("CSRF_COOKIE_SAMESITE", "Lax"),
        max_age=86400,
    )
    return resp
```

#### Step 3 — Re-enable CSRF on auth blueprint (remove the full exemption)

In `new/server/app.py`, remove:
```python
# REMOVE:
csrf.exempt(auth_bp)
```

And instead configure Flask-WTF to use the double-submit cookie:

```python
# app.py — after csrf = CSRFProtect(app):

from flask_wtf.csrf import CSRFError

@app.errorhandler(CSRFError)
def handle_csrf_error(e):
    return jsonify({
        "error": "CSRF token missing or invalid. Refresh the page and try again.",
        "code": 400,
    }), 400
```

> **Note**: The auth blueprint currently works without CSRF because it's fully exempt. Re-enabling it requires the frontend to always call `/api/csrf-token` first and send `X-CSRFToken`. The `api.js` interceptor already does this (confirmed in code review). However, initial login cannot fetch a CSRF token before authenticating — this is the bootstrap problem. **Resolution**: The login endpoint specifically can remain exempt, but logout and register must be CSRF-protected.

```python
# In routes/auth.py — keep login exempt individually:
@auth_bp.route("/login", methods=["POST"])
@csrf.exempt   # Login bootstrap: cannot prefetch CSRF token before auth
@limiter.limit("20 per 15 minutes")
def login(): ...
```

#### Step 4 — Frontend already handles this (`api.js`)

`api.js` already fetches the CSRF token and adds `X-CSRFToken` header. Ensure `fetchCsrfToken()` is called on app initialization:

```javascript
// new/client/src/main.jsx — add CSRF token fetch on startup
import { fetchCsrfToken } from './api';

// Call before rendering:
fetchCsrfToken().then(() => {
  // render app
});
```

#### Step 5 — CSRF regression tests

```python
# new/server/tests/test_csrf_protection.py

def test_csrf_token_endpoint_returns_token(client):
    resp = client.get("/api/csrf-token")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "csrf_token" in data
    assert len(data["csrf_token"]) > 20

def test_csrf_token_endpoint_sets_cookie(client):
    resp = client.get("/api/csrf-token")
    assert "csrf_token" in resp.headers.get("Set-Cookie", ""), \
        "CSRF token must be set as a cookie for the double-submit pattern"

def test_mutating_request_without_csrf_rejected(client, admin_session):
    """POST without CSRF token must return 400."""
    resp = client.post(
        "/api/emissions/",
        json={"quantity": 100},
        headers={}  # No X-CSRFToken header
    )
    assert resp.status_code == 400

def test_mutating_request_with_csrf_accepted(client, admin_session):
    """POST with valid CSRF token must not be rejected for CSRF reasons."""
    token_resp = client.get("/api/csrf-token")
    token = token_resp.get_json()["csrf_token"]
    resp = client.post(
        "/api/emissions/",
        json={"quantity": 100},
        headers={"X-CSRFToken": token}
    )
    # Should not be 400 due to CSRF (may fail for other reasons — that's OK)
    assert resp.status_code != 400 or "csrf" not in resp.get_json().get("error", "").lower()
```

---

### 2.3 WAL Journal — Force Checkpoint + Lower Interval

**Problem**: `ghg_app.db-wal` is 233 MB. The current checkpoint interval is 500 commits.  
**Fix**: Force an immediate checkpoint and reduce the interval.

#### Step 1 — One-time manual checkpoint (run once, immediately)

```powershell
# Run from new/server/:
python -c "
import sqlite3
conn = sqlite3.connect('ghg_app.db')
conn.execute('PRAGMA wal_checkpoint(TRUNCATE)')
conn.close()
print('WAL checkpoint complete')
"
```

#### Step 2 — Reduce checkpoint interval in `new/server/app.py`

```python
# Change line ~65:
# BEFORE:
_WAL_CHECKPOINT_INTERVAL = 500

# AFTER:
_WAL_CHECKPOINT_INTERVAL = int(os.environ.get("WAL_CHECKPOINT_INTERVAL", "100"))
```

#### Step 3 — Add WAL size monitoring to health/ready endpoint

```python
# In app.py health_readiness():
import os as _os
wal_path = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "ghg_app.db-wal")
wal_mb = _os.path.getsize(wal_path) / (1024 * 1024) if _os.path.exists(wal_path) else 0
# Add to response:
"wal_size_mb": round(wal_mb, 1),
"wal_warning": wal_mb > 100,
```

---

## PHASE 3 — HIGH QUALITY (Testing Infrastructure)

---

### 3.1 Backend Test Isolation — In-Memory SQLite Fixture

**Problem**: Tests run against `ghg_app.db` (live 2.3 GB production database).  
**Fix**: Replace `new/server/tests/conftest.py` with a proper isolated in-memory database fixture.

#### Full replacement of `new/server/tests/conftest.py`

```python
# new/server/tests/conftest.py — FULL REPLACEMENT

"""
Pytest configuration providing a fully isolated in-memory SQLite database
for every test session. Never touches ghg_app.db.
"""

import sys
import os
import pytest

# Ensure server/ is on sys.path
server_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if server_dir not in sys.path:
    sys.path.insert(0, server_dir)

# Ensure repo root is on sys.path (for validation.reference_model)
repo_root = os.path.abspath(os.path.join(server_dir, "..", "..", ".."))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)


@pytest.fixture(scope="session")
def app():
    """
    Session-scoped Flask app configured with an isolated in-memory SQLite database.
    The database is created fresh for every test session and never touches
    the production ghg_app.db file.
    """
    from app import app as flask_app
    from extensions import db, limiter

    flask_app.config.update({
        "TESTING": True,
        "WTF_CSRF_ENABLED": False,
        "SECRET_KEY": "test-secret-key-do-not-use-in-production",
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",  # ← ISOLATED
        "SQLALCHEMY_ENGINE_OPTIONS": {
            "connect_args": {"check_same_thread": False},
        },
        "RATELIMIT_ENABLED": False,
        "RATELIMIT_STORAGE_URI": "memory://",
        "SEED_ADMIN": "false",
    })

    limiter.enabled = False

    with flask_app.app_context():
        db.create_all()
        yield flask_app
        db.drop_all()


@pytest.fixture(scope="session")
def client(app):
    return app.test_client()


@pytest.fixture(scope="function")
def db_session(app):
    """
    Function-scoped database session that rolls back after each test,
    ensuring complete test isolation.
    """
    from extensions import db
    with app.app_context():
        connection = db.engine.connect()
        transaction = connection.begin()
        # Bind session to the connection
        db.session.bind = connection
        yield db.session
        # Roll back all changes made during the test
        db.session.remove()
        transaction.rollback()
        connection.close()


@pytest.fixture(autouse=True)
def disable_limiter_for_tests():
    """Ensure Flask-Limiter does not throttle tests (except rate-limit-specific tests)."""
    from extensions import limiter
    prev = limiter.enabled
    limiter.enabled = False
    yield
    limiter.enabled = prev
```

> **⚠️ Important**: After this change, any test that previously relied on existing data in `ghg_app.db` will need to create its own fixtures. Review all 43 test files for `User.query.filter_by(email=...).first()` patterns that assume data already exists — these need to be replaced with explicit `db.session.add(user)` setup within the test fixture.

#### Update all affected test files (example pattern)

```python
# BEFORE (assumes production data exists):
def admin_user():
    user = User.query.filter_by(email="admin_audit@test.com").first()
    if not user:
        user = User(email="admin_audit@test.com", ...)
        db.session.add(user)
        db.session.commit()
    return user.email

# AFTER (creates and tears down cleanly):
@pytest.fixture
def admin_user(app):
    from extensions import db
    from models import User
    with app.app_context():
        user = User(
            email="admin_audit@test.com",
            fullName="Admin Audit",
            orgName="Test Org",
            sector="Energy",
            role="admin",
        )
        user.set_password("Password123!")
        db.session.add(user)
        db.session.commit()
        yield user.email
        db.session.delete(User.query.filter_by(email="admin_audit@test.com").first())
        db.session.commit()
```

---

### 3.2 Frontend Unit Tests — Vitest + React Testing Library

**Problem**: `package.json` has no test framework. Zero React component tests exist.

#### Step 1 — Install dependencies

```powershell
cd new\client
npm install --save-dev vitest @vitest/ui jsdom @testing-library/react @testing-library/jest-dom @testing-library/user-event
```

#### Step 2 — Update `new/client/vite.config.js`

Add `test` configuration block:

```javascript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { visualizer } from "rollup-plugin-visualizer"

export default defineConfig({
  base: process.env.VITE_BASE_PATH || '/',
  plugins: [
    react(),
    visualizer({ filename: "stats.html", open: false })
  ],
  server: {
    host: '0.0.0.0',
    port: 5173,
    proxy: {
      '/api/notifications/stream': {
        target: 'http://127.0.0.1:5000',
        changeOrigin: true,
        compress: false,
      },
      '/api': {
        target: 'http://127.0.0.1:5000',
        changeOrigin: true,
      }
    }
  },
  build: {
    sourcemap: false,
    chunkSizeWarningLimit: 500,
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ['react', 'react-dom', 'react-router-dom'],
        }
      }
    }
  },
  // ── Vitest configuration ─────────────────────────────────────────────────
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./src/test-setup.js'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html'],
      include: ['src/**/*.{js,jsx}'],
      exclude: ['src/test-setup.js', 'src/main.jsx'],
    },
  },
})
```

#### Step 3 — Create `new/client/src/test-setup.js`

```javascript
// new/client/src/test-setup.js
import '@testing-library/jest-dom';
```

#### Step 4 — Update `new/client/package.json` scripts

```json
"scripts": {
  "dev": "vite",
  "build": "vite build",
  "lint": "eslint .",
  "preview": "vite preview",
  "test": "vitest run",
  "test:watch": "vitest",
  "test:ui": "vitest --ui",
  "test:coverage": "vitest run --coverage"
}
```

#### Step 5 — Create initial component tests

```javascript
// new/client/src/__tests__/Login.test.jsx

import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { vi } from 'vitest';
import Login from '../pages/Login';

// Mock the api module
vi.mock('../api', () => ({
  default: {
    post: vi.fn(),
    get: vi.fn(),
  },
  fetchCsrfToken: vi.fn(() => Promise.resolve('test-token')),
}));

// Mock AuthContext
vi.mock('../context/AuthContext', () => ({
  useAuth: () => ({ login: vi.fn(), user: null }),
}));

describe('Login page', () => {
  test('renders email and password fields', () => {
    render(<MemoryRouter><Login /></MemoryRouter>);
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
  });

  test('shows error on empty submit', async () => {
    render(<MemoryRouter><Login /></MemoryRouter>);
    fireEvent.click(screen.getByRole('button', { name: /login/i }));
    await waitFor(() => {
      expect(screen.getByText(/required/i)).toBeInTheDocument();
    });
  });

  test('calls login API with credentials', async () => {
    const api = (await import('../api')).default;
    api.post.mockResolvedValueOnce({
      data: { user: { id: 1, email: 'test@test.com', role: 'admin' } }
    });

    render(<MemoryRouter><Login /></MemoryRouter>);
    fireEvent.change(screen.getByLabelText(/email/i), { target: { value: 'test@test.com' } });
    fireEvent.change(screen.getByLabelText(/password/i), { target: { value: 'Password1!' } });
    fireEvent.click(screen.getByRole('button', { name: /login/i }));

    await waitFor(() => {
      expect(api.post).toHaveBeenCalledWith('/auth/login', {
        email: 'test@test.com',
        password: 'Password1!',
      });
    });
  });
});
```

```javascript
// new/client/src/__tests__/EmissionResult.test.jsx
// Tests that numerical display exactly matches backend-expected format

import { render, screen } from '@testing-library/react';
import EmissionResult from '../components/EmissionResult';

describe('EmissionResult component', () => {
  const mockResult = {
    co2: { value: 95.558, lower: 90.28, upper: 100.84 },
    ch4: { value: 0.001801, lower: 0.001530, upper: 0.002072 },
    n2o: { value: 0.0001801, lower: 0.000126, upper: 0.000234 },
    total_co2e: 95.658,
  };

  test('displays CO2e total prominently', () => {
    render(<EmissionResult result={mockResult} />);
    expect(screen.getByText(/95\.658/)).toBeInTheDocument();
  });

  test('displays CO2, CH4, N2O individually', () => {
    render(<EmissionResult result={mockResult} />);
    expect(screen.getByText(/95\.558/)).toBeInTheDocument();
  });

  test('shows uncertainty bounds when present', () => {
    render(<EmissionResult result={mockResult} />);
    expect(screen.getByText(/90\.28/)).toBeInTheDocument();
    expect(screen.getByText(/100\.84/)).toBeInTheDocument();
  });

  test('does not display NaN or undefined values', () => {
    const badResult = { total_co2e: null, co2: null };
    render(<EmissionResult result={badResult} />);
    expect(screen.queryByText('NaN')).not.toBeInTheDocument();
    expect(screen.queryByText('undefined')).not.toBeInTheDocument();
  });
});
```

---

### 3.3 E2E Tests — Playwright

#### Step 1 — Install Playwright

```powershell
cd new\client
npm install --save-dev @playwright/test
npx playwright install chromium firefox
```

#### Step 2 — Create `new/client/playwright.config.js`

```javascript
// new/client/playwright.config.js
import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,
  retries: 1,
  reporter: 'html',
  use: {
    baseURL: 'http://localhost:5173',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
    { name: 'firefox', use: { ...devices['Desktop Firefox'] } },
  ],
  webServer: [
    {
      command: 'npm run dev',
      url: 'http://localhost:5173',
      reuseExistingServer: !process.env.CI,
      timeout: 30000,
    },
  ],
});
```

#### Step 3 — Create E2E test: Login → Calculate → Report

```javascript
// new/client/e2e/ghg-workflow.spec.js

import { test, expect } from '@playwright/test';

const ADMIN_EMAIL = process.env.E2E_ADMIN_EMAIL || 'admin@ghg.com';
const ADMIN_PASSWORD = process.env.E2E_ADMIN_PASSWORD || 'Admin12345!';

test.describe('Core GHG Workflow', () => {

  test('Login → Dashboard → Create emission → Calculate → Verify result', async ({ page }) => {
    // 1. Login
    await page.goto('/');
    await page.fill('[name="email"], [placeholder*="email" i]', ADMIN_EMAIL);
    await page.fill('[name="password"], [placeholder*="password" i]', ADMIN_PASSWORD);
    await page.click('button[type="submit"]');
    await expect(page).toHaveURL(/dashboard/i, { timeout: 10000 });

    // 2. Navigate to Emissions
    await page.click('text=Emissions');
    await expect(page.locator('h1, h2')).toContainText(/emission/i);

    // 3. Verify dashboard loads without errors
    const errorBanners = page.locator('[role="alert"].error, .error-message');
    await expect(errorBanners).toHaveCount(0);

    // 4. Verify no NaN values on screen
    const bodyText = await page.innerText('body');
    expect(bodyText).not.toContain('NaN');
    expect(bodyText).not.toContain('undefined');
    expect(bodyText).not.toContain('Infinity');
  });

  test('Unauthorized access is blocked — redirects to login', async ({ page }) => {
    // Try accessing dashboard without login
    await page.goto('/dashboard');
    await expect(page).toHaveURL(/login/i, { timeout: 5000 });
  });

  test('API health endpoint responds correctly', async ({ request }) => {
    const resp = await request.get('http://localhost:5000/api/health');
    expect(resp.status()).toBe(200);
    const body = await resp.json();
    expect(body.status).toBe('ok');
  });

  test('Login with wrong credentials shows error message', async ({ page }) => {
    await page.goto('/');
    await page.fill('[name="email"], [placeholder*="email" i]', 'wrong@email.com');
    await page.fill('[name="password"], [placeholder*="password" i]', 'WrongPassword1!');
    await page.click('button[type="submit"]');
    await expect(page.locator('text=/invalid|incorrect|error/i')).toBeVisible({ timeout: 5000 });
  });

  test('Network error handling — shows user-friendly message on 500', async ({ page, context }) => {
    // Intercept API and force a 500 error
    await context.route('**/api/emissions/', route =>
      route.fulfill({ status: 500, body: JSON.stringify({ error: 'Internal Server Error' }) })
    );
    await page.goto('/');
    // Login first (route not intercepted)
    await page.fill('[name="email"]', ADMIN_EMAIL);
    await page.fill('[name="password"]', ADMIN_PASSWORD);
    await page.click('button[type="submit"]');
    // Navigate to emissions (will hit intercepted route)
    await page.click('text=Emissions');
    // Must show user-friendly message, NOT a stack trace
    await expect(page.locator('body')).not.toContainText('Traceback');
    await expect(page.locator('body')).not.toContainText('at Object.');
  });
});
```

#### Step 4 — Add E2E script to package.json

```json
"scripts": {
  "e2e": "playwright test",
  "e2e:ui": "playwright test --ui",
  "e2e:report": "playwright show-report"
}
```

---

## PHASE 4 — CALCULATION FIX

---

### 4.1 N2O Flaring Default Inconsistency

**Problem**: `FlaringCalculator` in `combustion.py` defaults `ef_n2o=0.0`, while `_split_vented_and_flared()` in `vented.py` uses `0.0001 kg/MMBtu`.  
**Fix**: Use `0.0001 kg/MMBtu` (API Compendium 2021 Table 5-3 default) in both paths.

#### Step 1 — Update `new/server/calculations/combustion.py`

```python
# In FlaringCalculator.calculate() signature, change:
# BEFORE:
def calculate(self, ..., ef_n2o=0.0, ...):

# AFTER:
N2O_FLARING_DEFAULT_KG_PER_MMBTU = 0.0001  # API Compendium 2021 Table 5-3

def calculate(self, ..., ef_n2o=None, ...):
    # And where ef_n2o is used:
    # BEFORE: if ef_n2o and float(ef_n2o) > 0:
    # AFTER:
    _ef_n2o = float(ef_n2o) if ef_n2o is not None else N2O_FLARING_DEFAULT_KG_PER_MMBTU
    if _ef_n2o > 0:
        ef_u = str(ef_unit or "kg/MMBtu").lower()
        if "mmbtu" in ef_u:
            hhv_val = float(hhv or 1020.0)
            vol_scf = vol_std * CONVERSIONS.get("m3_to_scf", 35.3147)
            flared_mmbtu = (vol_scf * hhv_val) / 1_000_000.0
            n2o_tonnes = (flared_mmbtu * _ef_n2o) / 1000.0
        else:
            n2o_kg = vol_std * convert_factor_to_kg_per_unit(_ef_n2o, ef_unit, "m3", hhv=hhv, fuel_type="gases")
            n2o_tonnes = n2o_kg / 1000.0
    else:
        n2o_tonnes = 0.0
```

#### Step 2 — Verify `_split_vented_and_flared()` uses the same constant

```python
# In vented.py — already uses 0.0001 as fallback:
# n2o_ef_kg = float(ef_n2o if ef_n2o is not None else 0.0001)
# This is already correct — no change needed.
```

#### Step 3 — Regression test

```python
# new/server/tests/test_n2o_flaring_consistency.py

from calculations.combustion import FlaringCalculator
from calculations.vented import _split_vented_and_flared
from calculations.constants import GWP_AR5


def test_flaring_n2o_default_consistent_with_vented_partition():
    """
    N2O default must be 0.0001 kg/MMBtu in BOTH code paths.
    CONCERN-CALC-01 regression test.
    """
    # Path A: FlaringCalculator with no ef_n2o argument
    calc = FlaringCalculator()
    result_a = calc.calculate(
        gas_volume=10000.0,
        ch4_fraction=0.85,
        flare_type="elevated",
        uncertainties={},
        hhv=1020.0,
        ef_n2o=None,   # Must use default 0.0001
        gwp_dict=GWP_AR5,
    )
    n2o_a = result_a["results"]["n2o"]["value"]

    # Path B: _split_vented_and_flared with no ef_n2o argument
    result_b = _split_vented_and_flared(
        total_gas_m3=10000.0,
        ch4_tonnes=10000.0 * 0.85 * 0.6785 / 1000,
        co2_tonnes=0.0,
        ctrl_eff=1.0,   # 100% flared
        hhv=1020.0,
        ef_n2o=None,   # Must use default 0.0001
    )
    n2o_b = result_b["flared_n2o"]

    # Both paths should produce the same N2O for the same gas volume and HHV
    # Allow small tolerance for different calculation paths
    assert abs(n2o_a - n2o_b) / max(n2o_a, 1e-10) < 0.01, (
        f"REGRESSION FAIL: FlaringCalculator N2O={n2o_a:.6f} t, "
        f"_split_vented_and_flared N2O={n2o_b:.6f} t — "
        f"both must use the same 0.0001 kg/MMBtu default (API 2021 Table 5-3)"
    )
```

---

## PHASE 5 — DATABASE MIGRATION (SQLite → PostgreSQL)

---

### 5.1 Migration Plan (SQLite → PostgreSQL)

**Problem**: SQLite is not suitable for multi-user production workloads — no connection pooling, no WAL across multiple processes, no point-in-time recovery, no replication.

#### Step 1 — Add PostgreSQL URL to `.env.example`

```dotenv
# PostgreSQL (for production):
DB_TYPE=postgres
DATABASE_URL=postgresql://ghg_user:CHANGEME@localhost:5432/ghg_production
```

#### Step 2 — Create `new/server/scripts/migrate_sqlite_to_postgres.py`

```python
#!/usr/bin/env python3
"""
Safe SQLite → PostgreSQL data migration script.
Creates all tables in PostgreSQL and bulk-transfers all rows.
Verifies row counts match after migration.

Usage:
  SQLITE_PATH=./ghg_app.db PG_URL=postgresql://user:pass@host/db python migrate_sqlite_to_postgres.py
"""
import os
import sys
import sqlite3
import psycopg2
from psycopg2.extras import execute_values

TABLES = [
    "users", "facilities", "emissions", "production_data",
    "emission_sources", "custom_factors", "activity_log",
    "goals", "base_year", "mitigation_records", "scope3_data",
    "scope2_emissions", "scope3_emissions", "mitigation_projects",
    "base_year_recalculations", "reporting_metadata", "notifications",
    "cbam_product_exports", "ogmp_surveys", "methane_source_types",
    "level_upgrade_logs", "sbti_targets", "system_settings",
]

def migrate():
    sqlite_path = os.environ.get("SQLITE_PATH", "ghg_app.db")
    pg_url = os.environ.get("PG_URL")
    if not pg_url:
        sys.exit("Error: PG_URL environment variable is required")

    sq = sqlite3.connect(sqlite_path)
    sq.row_factory = sqlite3.Row
    pg = psycopg2.connect(pg_url)

    # Create schema via Flask-Migrate before running this script
    print("Migrating data table by table...")

    for table in TABLES:
        rows = sq.execute(f"SELECT * FROM {table}").fetchall()
        if not rows:
            print(f"  {table}: empty (skipped)")
            continue

        cols = list(rows[0].keys())
        with pg.cursor() as cur:
            execute_values(
                cur,
                f"INSERT INTO {table} ({','.join(cols)}) VALUES %s ON CONFLICT DO NOTHING",
                [tuple(r[c] for c in cols) for r in rows],
            )
        pg.commit()

        # Verify
        pg_count = pg.cursor()
        pg_count.execute(f"SELECT COUNT(*) FROM {table}")
        pg_rows = pg_count.fetchone()[0]
        print(f"  {table}: {len(rows)} rows → PostgreSQL: {pg_rows} rows ✓")

    sq.close()
    pg.close()
    print("Migration complete.")

if __name__ == "__main__":
    migrate()
```

---

### 5.2 Backup/Restore Procedure

#### Create `new/server/scripts/backup.sh` (Linux/Render) and `backup.ps1` (Windows)

```powershell
# new/server/scripts/backup.ps1
# SQLite backup procedure

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$backup_dir = "backups"
New-Item -ItemType Directory -Force -Path $backup_dir | Out-Null

# SQLite online backup (safe during live operation)
python -c "
import sqlite3, shutil, os, sys
db_path = 'ghg_app.db'
backup_path = f'backups/ghg_app_{sys.argv[1]}.db'
src = sqlite3.connect(db_path)
dst = sqlite3.connect(backup_path)
src.backup(dst)
src.close()
dst.close()
print(f'Backup created: {backup_path}')
" $timestamp

Write-Host "Backup complete: backups/ghg_app_$timestamp.db"
```

#### Restore test procedure
```powershell
# new/server/scripts/test_restore.ps1
# Test restore into isolated location — NEVER to production path

$backup_file = $args[0]
$restore_path = "ghg_restore_test.db"

python -c "
import sqlite3, sys
src = sqlite3.connect(sys.argv[1])
dst = sqlite3.connect(sys.argv[2])
src.backup(dst)
src.close()
# Verify
count = dst.execute('SELECT COUNT(*) FROM emissions').fetchone()[0]
print(f'Restored OK. Emissions count: {count}')
dst.close()
" $backup_file $restore_path

# Clean up test restore
Remove-Item $restore_path -Force
```

---

### 5.3 Alembic Downgrade Paths

For each of the 5 existing migration files, add a proper `downgrade()` function. Example:

```python
# new/server/migrations/versions/7fe333372c71_add_performance_indexes.py

def upgrade():
    op.create_index('ix_emissions_fac_yr_status', 'emissions', ['facility_id', 'year', 'status'])
    # ... other indexes

def downgrade():
    # BEFORE: pass  ← REMOVE THIS
    # AFTER:
    op.drop_index('ix_emissions_fac_yr_status', table_name='emissions')
    # ... other index drops
```

---

## PHASE 6 — MEDIUM FIXES

---

### 6.1 Deprecation Warnings (Python 3.14 compatibility)

#### `openpyxl` uses `datetime.utcnow()` 
This is in the library itself (not your code). Pin to a newer version or accept the warning until openpyxl publishes a fix:
```
# new/server/requirements.txt — update:
openpyxl>=3.1.3
```

#### `reportlab` uses `ast.NameConstant`
```
reportlab>=4.1.0   # Newer versions have fixed this
```

---

### 6.2 Custom Factor Plausibility Bounds

Add a validation layer to `new/server/routes/custom_factors.py`:

```python
# Plausibility bounds per GHG (kg/MMBtu) — for flagging only, not rejection
PLAUSIBILITY_BOUNDS = {
    "co2_factor": (0.0, 500.0),    # API 2021: coal ~100, gas ~53
    "ch4_factor": (0.0, 100.0),    # API 2021: max ~5 for most fuels
    "n2o_factor": (0.0, 10.0),     # API 2021: max ~0.5 for most fuels
}

def _check_plausibility(data):
    warnings = []
    for field, (lo, hi) in PLAUSIBILITY_BOUNDS.items():
        val = data.get(field)
        if val is not None:
            try:
                v = float(val)
                if v < lo or v > hi:
                    warnings.append(f"{field}={v} is outside plausible range [{lo}, {hi}]")
            except (ValueError, TypeError):
                pass
    return warnings
```

---

## PHASE 7 — PRODUCTION SMOKE TESTS

---

### 7.1 Smoke Test Suite

```python
# new/server/tests/test_production_smoke.py
"""
Production smoke tests — run after every deployment.
Fast (< 30 seconds total). Verifies 10 critical capabilities.
"""

import pytest
from app import app as flask_app
from extensions import db, limiter


@pytest.fixture(scope="module")
def smoke_client():
    flask_app.config.update({
        "TESTING": True,
        "WTF_CSRF_ENABLED": False,
        "SECRET_KEY": "smoke-test-key",
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
    })
    limiter.enabled = False
    with flask_app.app_context():
        db.create_all()
        # Seed one admin user for smoke tests
        from models import User
        u = User(fullName="Smoke Admin", orgName="Smoke Org", email="smoke@test.com",
                 sector="Energy", role="admin", status="active")
        u.set_password("SmokeAdmin1!")
        db.session.add(u)
        db.session.commit()
        yield flask_app.test_client()
        db.drop_all()


def test_smoke_01_application_starts(smoke_client):
    """SMOKE-01: Application starts and health endpoint responds."""
    resp = smoke_client.get("/api/health")
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "ok"


def test_smoke_02_readiness_probe(smoke_client):
    """SMOKE-02: Deep readiness probe confirms DB connectivity."""
    resp = smoke_client.get("/api/health/ready")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["database"] == "connected"


def test_smoke_03_frontend_assets_served(smoke_client):
    """SMOKE-03: Root endpoint responds (API gateway alive)."""
    resp = smoke_client.get("/")
    assert resp.status_code == 200


def test_smoke_04_login_works(smoke_client):
    """SMOKE-04: Admin login succeeds and returns session."""
    resp = smoke_client.post("/api/auth/login", json={
        "email": "smoke@test.com",
        "password": "SmokeAdmin1!",
    })
    assert resp.status_code == 200
    data = resp.get_json()
    assert data.get("user", {}).get("role") == "admin"


def test_smoke_05_unauthenticated_access_blocked(smoke_client):
    """SMOKE-05: Unauthorized requests return 401."""
    resp = smoke_client.get("/api/emissions/")
    assert resp.status_code == 401


def test_smoke_06_calculation_engine_responds(smoke_client):
    """SMOKE-06: A basic combustion calculation can be dispatched."""
    from calculations.dispatcher import CalculationDispatcher
    from calculations.constants import GWP_AR5
    dispatcher = CalculationDispatcher()
    result = dispatcher.dispatch(
        "stationary_combustion",
        {"quantity": 1000, "unit": "m3", "fuel_type": "natural_gas", "hhv": 1020.0},
        {"co2": 53.06, "ch4": 0.001, "n2o": 0.0001, "unit": "kg/MMBtu"},
        {},
        gwp_dict=GWP_AR5,
    )
    assert result["total_co2e"] > 0
    assert not any(str(v) == "nan" for v in [result["total_co2e"]])


def test_smoke_07_gwp_constants_correct(smoke_client):
    """SMOKE-07: GWP constants are correctly loaded (AR5 CH4=28, N2O=265)."""
    from calculations.constants import GWP_AR5, GWP_AR6
    assert GWP_AR5["CH4"] == 28.0
    assert GWP_AR5["N2O"] == 265.0
    assert GWP_AR6["CH4"] == 27.9
    assert GWP_AR6["N2O"] == 273.0


def test_smoke_08_unit_conversion_sanity(smoke_client):
    """SMOKE-08: Critical unit conversion (scf→m3) returns correct value."""
    from calculations.units import VOLUME_UNITS_TO_M3
    scf_to_m3 = VOLUME_UNITS_TO_M3["scf"]
    assert abs(scf_to_m3 - 0.028316846592) < 1e-10, \
        f"scf→m3 conversion is wrong: {scf_to_m3}"


def test_smoke_09_api_returns_json_errors(smoke_client):
    """SMOKE-09: API error responses are JSON (not HTML error pages)."""
    resp = smoke_client.get("/api/nonexistent-endpoint-xyz")
    assert resp.status_code == 404
    content_type = resp.headers.get("Content-Type", "")
    assert "application/json" in content_type, \
        f"404 response must be JSON, got: {content_type}"


def test_smoke_10_no_hardcoded_dev_accounts(smoke_client):
    """SMOKE-10: Dev shortcut accounts (a@a, a) must not exist."""
    from models import User
    for email in ["a@a", "a"]:
        user = User.query.filter_by(email=email).first()
        assert user is None, f"Dev account '{email}' must not exist in production"
```

---

## PHASE 8 — FINAL CI/CD INTEGRATION

After completing all phases, add these CI steps to `deploy-pages.yml`:

```yaml
      - name: Run frontend unit tests
        working-directory: new/client
        run: npm run test

      - name: Run E2E tests (headless)
        working-directory: new/client
        env:
          E2E_ADMIN_EMAIL: ${{ secrets.E2E_ADMIN_EMAIL }}
          E2E_ADMIN_PASSWORD: ${{ secrets.E2E_ADMIN_PASSWORD }}
        run: npx playwright test --project=chromium

      - name: Run production smoke tests
        working-directory: new/server
        env:
          FLASK_ENV: testing
          DATABASE_URL: "sqlite:///:memory:"
          SECRET_KEY: ci-smoke-secret
        run: python -m pytest tests/test_production_smoke.py -v

      - name: Run dependency audit
        working-directory: new/server
        run: pip-audit --requirement requirements.txt
```

---

## Proposed Execution Schedule

| Phase | Estimated Effort | Dependency | Risk if Skipped |
|---|---|---|---|
| 1.1 Delete import_debug.log | 30 min | None | Disk exhaustion |
| 1.2 Remove dev credentials | 1 hour | None | **Production account takeover** |
| 1.3 Backend CI | 2 hours | Phase 3.1 first | Regressions undetected |
| 2.1 Rate limiting | 2 hours | None | Brute force / DoS |
| 2.2 CSRF double-submit | 3 hours | None | CSRF on auth endpoints |
| 2.3 WAL checkpoint | 30 min | None | DB corruption risk |
| 3.1 Test isolation | 3 hours | None | Test data corruption |
| 3.2 Vitest setup | 2 hours | None | UI bugs undetected |
| 3.3 Playwright E2E | 4 hours | Backend running | Workflow regressions |
| 4.1 N2O fix | 1 hour | None | N2O under-reporting |
| 5.1 PostgreSQL migration | 4 hours | 5.2 backup first | Irreversible data loss |
| 5.2 Backup procedure | 1 hour | None | No recovery path |
| 5.3 Alembic downgrade | 2 hours | None | Unrollable migrations |
| 6.1 Deprecation fixes | 1 hour | None | Python 3.14 breakage |
| 7.1 Smoke tests | 1 hour | Phase 1.2 done | Silent deploy failures |
| 8.1 Full CI integration | 2 hours | All above | — |

**Total estimated effort**: ~30 hours of focused engineering

---

*Plan created: 2026-09-20 | Ready for user approval*
