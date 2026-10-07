import logging
import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()


class Config:
    # SEC-01: Enforce secure SECRET_KEY across modern environment identifiers
    _env_name = (
        os.environ.get("FLASK_ENV")
        or os.environ.get("APP_ENV")
        or os.environ.get("ENVIRONMENT")
        or "development"
    ).lower()
    # Fail closed: only these names are treated as non-production. Any other value
    # (production, prod, staging, live, ...) enforces the production safety checks below.
    _NON_PRODUCTION_ENVS = {"development", "dev", "local", "testing", "test"}
    _is_production = _env_name not in _NON_PRODUCTION_ENVS
    IS_PRODUCTION = _is_production

    if _is_production:
        SECRET_KEY = os.environ.get("SECRET_KEY")
        if not SECRET_KEY or SECRET_KEY in [
            "dev-secret-key-change-in-prod-please",
            "secret",
            "changeme",
        ]:
            raise ValueError(
                "FATAL: SECRET_KEY is not set or is using the default development key in a production environment."
            )
        prod_db_url = os.environ.get("DATABASE_URL")
        if not prod_db_url:
            raise ValueError(
                "FATAL: DATABASE_URL is not set in a production environment."
            )
        allow_sqlite = (
            os.environ.get("ALLOW_SQLITE_IN_PRODUCTION", "").lower() in ("1", "true")
            or os.environ.get("ALLOW_SQLITE_IN_PROD", "").lower() in ("1", "true")
            or bool(os.environ.get("PYTEST_CURRENT_TEST"))
        )
        if not allow_sqlite and ("sqlite" in prod_db_url.lower() or os.environ.get("DB_TYPE", "").lower() == "sqlite"):
            raise ValueError(
                "FATAL: SQLite is prohibited in production. A production deployment requires PostgreSQL with a valid postgresql:// DATABASE_URL."
            )
    else:
        SECRET_KEY = os.environ.get("SECRET_KEY")
        if not SECRET_KEY:
            SECRET_KEY = "dev-secret-key-change-in-prod-please"
            logging.getLogger(__name__).warning(
                "SECRET_KEY is not set; using the built-in development key. "
                "This is only acceptable for local development and testing."
            )

    _default_origins = (
        "http://localhost:5173,http://localhost:5174,http://localhost:5175,http://localhost:3000,"
        "http://127.0.0.1:5173,http://127.0.0.1:5174,http://127.0.0.1:5175,http://127.0.0.1:3000,"
        "https://kaljah.github.io"
    )
    ALLOWED_ORIGINS = [
        o.strip()
        for o in os.environ.get("ALLOWED_ORIGINS", _default_origins).split(",")
        if o.strip()
    ]
    if _is_production and (not ALLOWED_ORIGINS or "*" in ALLOWED_ORIGINS):
        raise ValueError(
            "FATAL: ALLOWED_ORIGINS must list explicit origins in production "
            "(empty and '*' are not allowed with credentialed requests)."
        )
    # Transitional: the GitHub Pages frontend origin used to be appended unconditionally.
    # Set CORS_STRICT=true once ALLOWED_ORIGINS lists every origin you need.
    _legacy_pages_origin = "https://kaljah.github.io"
    if _legacy_pages_origin not in ALLOWED_ORIGINS:
        if os.environ.get("CORS_STRICT", "").lower() in ("1", "true", "yes"):
            pass
        else:
            ALLOWED_ORIGINS.append(_legacy_pages_origin)
            if _is_production:
                logging.getLogger(__name__).warning(
                    "ALLOWED_ORIGINS does not list %s; it is still added for compatibility. "
                    "Add it explicitly and set CORS_STRICT=true to remove this fallback.",
                    _legacy_pages_origin,
                )

    # Database Configuration
    # Defaults to SQLite, can be overridden by DB_TYPE env var
    DB_TYPE = os.environ.get("DB_TYPE", "sqlite")

    if DB_TYPE == "postgres":
        # Ensure your DATABASE_URL is set in .env
        # Example: postgresql://user:password@localhost:5432/ghg_db
        SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL")
        if not SQLALCHEMY_DATABASE_URI:
            raise ValueError("DB_TYPE is set to postgres but DATABASE_URL is missing!")
    else:
        # Default SQLite
        BASE_DIR = os.path.abspath(os.path.dirname(__file__))
        SQLALCHEMY_DATABASE_URI = os.environ.get(
            "DATABASE_URL"
        ) or "sqlite:///" + os.path.join(BASE_DIR, "ghg_app.db")

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    if "sqlite" in str(SQLALCHEMY_DATABASE_URI).lower():
        if str(SQLALCHEMY_DATABASE_URI).startswith("sqlite:///:memory:"):
            from sqlalchemy.pool import StaticPool
            SQLALCHEMY_ENGINE_OPTIONS = {
                "connect_args": {"check_same_thread": False, "timeout": 30},
                "poolclass": StaticPool,
            }
        else:
            from sqlalchemy.pool import NullPool
            SQLALCHEMY_ENGINE_OPTIONS = {
                "connect_args": {"check_same_thread": False, "timeout": 30},
                "poolclass": NullPool,
            }
    else:
        SQLALCHEMY_ENGINE_OPTIONS = {
            "pool_size": 25,
            "max_overflow": 25,
            "pool_timeout": 60,
        }


    # Session Configuration (8-hour session lifetime)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = os.environ.get(
        "SESSION_COOKIE_SAMESITE",
        "None" if _is_production else "Lax",
    )
    # Only set Secure in production to allow localhost testing
    SESSION_COOKIE_SECURE = _is_production
    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)
    SESSION_REFRESH_EACH_REQUEST = True

    # CSRF Configuration
    # Disable strict referrer checking so GitHub Pages frontend can communicate with Render backend
    WTF_CSRF_SSL_STRICT = False
    WTF_CSRF_TIME_LIMIT = 86400

    # API-03 FIX: Hard limit on all incoming request bodies — prevents large-payload DoS
    # NOTE: 50 MB covers any realistic single-month CSV upload.
    # If you need bulk testing with million-row files, set MAX_CONTENT_LENGTH=1073741824 in .env temporarily.
    MAX_CONTENT_LENGTH = int(os.environ.get("MAX_CONTENT_LENGTH", 50 * 1024 * 1024))  # 50 MB default

    # Rate Limiting Backend
    # Supports Redis in multi-worker production via REDIS_URL or RATELIMIT_STORAGE_URI
    _redis_url = (
        os.environ.get("RATELIMIT_REDIS_URL")
        or os.environ.get("REDIS_URL")
        or os.environ.get("RATELIMIT_STORAGE_URI")
    )
    RATELIMIT_STORAGE_URI = _redis_url if _redis_url else "memory://"
    # With several workers, memory:// gives every worker its own counters, so the effective
    # limit is the setting multiplied by the worker count. Production needs a shared store.
    if (
        _is_production
        and RATELIMIT_STORAGE_URI.startswith("memory://")
        and os.environ.get("ALLOW_MEMORY_LIMITER", "").lower() not in ("1", "true", "yes")
    ):
        raise ValueError(
            "FATAL: production needs a shared rate-limit store. Set REDIS_URL "
            "(or RATELIMIT_STORAGE_URI), or ALLOW_MEMORY_LIMITER=true for a single worker."
        )
    # Expose X-RateLimit-* response headers so clients can self-throttle
    RATELIMIT_HEADERS_ENABLED = True
