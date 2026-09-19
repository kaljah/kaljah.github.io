import os
from flask_sqlalchemy import SQLAlchemy
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

db = SQLAlchemy()

# ── Rate limiting ─────────────────────────────────────────────────────────────
# Storage URI is configured in config.py (RATELIMIT_STORAGE_URI).
# Default: SQLite on disk → shared across all workers on the same machine.
# Scale-out: set RATELIMIT_STORAGE_URI=redis://localhost:6379/0 in .env
#
# Flask-Limiter reads RATELIMIT_STORAGE_URI from the Flask app config
# automatically when init_app() is called, so we leave storage_uri unset here
# and let the config drive it.  This avoids duplicating the path.
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[],
    # storage_uri is intentionally NOT set here — it is read from
    # app.config["RATELIMIT_STORAGE_URI"] during init_app() call in app.py.
)
