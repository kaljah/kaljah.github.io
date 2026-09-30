import os
from flask_sqlalchemy import SQLAlchemy
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf.csrf import CSRFProtect

db = SQLAlchemy(session_options={"expire_on_commit": False})
csrf = CSRFProtect()


# ── Rate limiting ─────────────────────────────────────────────────────────────
# Global defaults apply to ALL endpoints unless overridden by a per-route
# @limiter.limit(...) decorator.
#
# Default: 200 requests/minute and 2000 requests/hour per signed-in user (per IP address otherwise).
# Override via RATELIMIT_DEFAULT env var (e.g. "100 per minute").
#
# Auth endpoints have stricter per-route limits (e.g. login: 20/15min).
# Calculation-heavy endpoints have their own limits (e.g. 100/min).
#
# Storage: reads RATELIMIT_STORAGE_URI from Flask app.config during init_app().
# Default: memory:// (single process only — safe for dev and single-worker).
# Multi-worker production: set RATELIMIT_STORAGE_URI=redis://host:6379/0
#
def rate_limit_key():
    """Signed-in requests are counted per user (colleagues behind one office address no longer
    share a budget); anonymous requests (sign-in, password reset) per IP address."""
    try:
        from flask import has_request_context, session

        if has_request_context() and session.get("user_id"):
            return f"user:{session['user_id']}"
    except Exception:
        pass
    return get_remote_address()


limiter = Limiter(
    key_func=rate_limit_key,
    default_limits=[
        os.environ.get("RATELIMIT_DEFAULT", "200 per minute"),
        "2000 per hour",
    ],
    # storage_uri is intentionally NOT set here — it is read from
    # app.config["RATELIMIT_STORAGE_URI"] during init_app() call in app.py.
)

