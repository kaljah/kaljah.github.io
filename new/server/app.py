import os
from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_migrate import Migrate
from config import Config
from flask_wtf.csrf import CSRFProtect, generate_csrf, CSRFError
import uuid
import time
import traceback
import logging
from logging.handlers import RotatingFileHandler

from extensions import db, limiter, csrf  # SEC-08 FIX: import limiter, csrf

app = Flask(__name__)
app.url_map.strict_slashes = False
app.config.from_object(Config)

# ── Rotating log handler (50 MB max, 3 backups) ────────────────────────────
# Replaces unbounded trace.log writes. All unhandled exceptions and warnings
# route through app.logger which writes to this rotating file.
_log_dir = os.path.dirname(os.path.abspath(__file__))
_log_path = os.path.join(_log_dir, "trace.log")
_rotating_handler = RotatingFileHandler(
    _log_path, maxBytes=50 * 1024 * 1024, backupCount=3, encoding="utf-8"
)
_rotating_handler.setFormatter(
    logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
)
_rotating_handler.setLevel(logging.WARNING)
app.logger.addHandler(_rotating_handler)
app.logger.setLevel(logging.INFO)


# Enable CORS
CORS(
    app,
    origins=app.config.get("ALLOWED_ORIGINS", []),
    supports_credentials=True,
    allow_headers=["Content-Type", "Authorization", "X-CSRFToken", "X-Request-ID", "Accept"],
    methods=["GET", "HEAD", "POST", "OPTIONS", "PUT", "PATCH", "DELETE"],
    expose_headers=["X-Request-ID", "Content-Disposition"],
)

# Database
db.init_app(app)
limiter.init_app(app)  # SEC-08 FIX: activate flask-limiter
migrate = Migrate(app, db)

from sqlalchemy import event
from sqlalchemy.engine import Engine
import sqlite3
from routes.dashboard import clear_dashboard_cache

import re
from werkzeug.exceptions import HTTPException

if os.environ.get("USE_PROXY_FIX", "false").lower() == "true":
    from werkzeug.middleware.proxy_fix import ProxyFix
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

# WAL checkpoint counter — runs PRAGMA wal_checkpoint(TRUNCATE) every 500 commits
# to prevent the SQLite WAL file from growing unboundedly.
_wal_commit_counter = 0
_WAL_CHECKPOINT_INTERVAL = int(os.environ.get("WAL_CHECKPOINT_INTERVAL", "100"))



@event.listens_for(Engine, "connect")
def set_sqlite_pragmas(dbapi_conn, _):
    if isinstance(dbapi_conn, sqlite3.Connection):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys = ON")
        cursor.execute("PRAGMA journal_mode = WAL")
        cursor.execute("PRAGMA synchronous = NORMAL")
        cursor.execute("PRAGMA busy_timeout = 5000")
        try:
            cursor.execute("SELECT description FROM custom_factors LIMIT 1")
        except sqlite3.OperationalError:
            try:
                cursor.execute("ALTER TABLE custom_factors ADD COLUMN description TEXT")
            except Exception:
                pass
        cursor.close()


@event.listens_for(db.session, "before_commit")
def track_modified_entities(session):
    relevant_entities = (
        "Emission",
        "Scope2Emission",
        "Scope3Emission",
        "ProductionData",
        "Facility",
        "CustomFactor",
        "OgmpSurvey",
    )
    has_relevant = False
    for obj in session.new | session.dirty | session.deleted:
        if obj.__class__.__name__ in relevant_entities:
            has_relevant = True
            break
    session.info["has_relevant_changes"] = has_relevant


@event.listens_for(db.session, "after_commit")
def receive_after_commit(session):
    global _wal_commit_counter
    if session.info.get("has_relevant_changes", True):
        clear_dashboard_cache()

    # Periodic WAL checkpoint to truncate the WAL file
    _wal_commit_counter += 1
    if _wal_commit_counter % _WAL_CHECKPOINT_INTERVAL == 0:
        try:
            conn = db.engine.raw_connection()
            if isinstance(conn.connection, sqlite3.Connection):
                conn.connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            conn.close()
        except Exception as _wal_err:
            app.logger.warning(f"WAL checkpoint failed: {_wal_err}")


# CSRF Protection
csrf.init_app(app)


@app.errorhandler(CSRFError)
def handle_csrf_error(e):
    return jsonify({
        "error": "CSRF token missing or invalid. Refresh the page and try again.",
        "code": 400,
    }), 400



# Request Logging & Request ID Middleware
@app.before_request
def before_request():
    request.start_time = time.time()
    req_id = request.headers.get("X-Request-ID", "")
    if not req_id or not re.match(r"^[A-Za-z0-9\-]{1,64}$", req_id):
        req_id = str(uuid.uuid4())
    request.id = req_id


@app.after_request
def after_request(response):
    response.headers["X-Request-ID"] = getattr(request, "id", "")

    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self'; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "img-src 'self' data: https:; "
        "connect-src 'self'"
    )
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

    # Disable caching for API endpoints to prevent stale browser reads.
    # Exception: SSE stream — it sets its own Cache-Control / Connection headers.
    if request.path.startswith("/api") and not request.path.startswith(
        "/api/notifications/stream"
    ):
        response.headers["Cache-Control"] = (
            "no-store, no-cache, must-revalidate, max-age=0"
        )
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"

    # Calculate duration
    if hasattr(request, "start_time"):
        duration = time.time() - request.start_time
        app.logger.info(
            f"{request.method} {request.path} {response.status_code} "
            f"[{duration:.3f}s] [ReqID: {getattr(request, 'id', '')}]"
        )
    return response


# Global JSON Error Handlers
@app.errorhandler(404)
def not_found_error(error):
    return (
        jsonify(
            {
                "error": "Not found",
                "code": 404,
                "request_id": getattr(request, "id", ""),
            }
        ),
        404,
    )


@app.errorhandler(Exception)
def internal_error(error):
    if isinstance(error, HTTPException):
        return (
            jsonify(
                {
                    "error": error.description,
                    "code": error.code,
                    "request_id": getattr(request, "id", ""),
                }
            ),
            error.code,
        )

    # Prevent masking of CSRF errors
    if "CSRF" in str(type(error)):
        return (
            jsonify(
                {
                    "error": str(error),
                    "code": 400,
                    "request_id": getattr(request, "id", ""),
                }
            ),
            400,
        )

    # Route all unhandled exceptions to the rotating logger (no unbounded file write)
    app.logger.error(f"Unhandled Exception: {str(error)}\n{traceback.format_exc()}")

    return (
        jsonify(
            {
                "error": "Internal server error",
                "code": 500,
                "request_id": getattr(request, "id", ""),
            }
        ),
        500,
    )


# Register Blueprints
from routes.auth import auth_bp
from routes.emissions import emissions_bp
from routes.facilities import facilities_bp
from routes.data import data_bp
from routes.reports import reports_bp
from routes.dashboard import dashboard_bp
from routes.custom_factors import custom_factors_bp
from routes.scope2 import scope2_bp
from routes.scope3 import scope3_bp
from routes.managedata import managedata_bp
from routes.emission_factors_routes import factors_bp
from routes.notifications import notifications_bp
from routes.audit import audit_bp
from routes.satellite import satellite_bp
from routes.qaqc import qaqc_bp

app.register_blueprint(auth_bp, url_prefix="/api/auth")
app.register_blueprint(emissions_bp, url_prefix="/api/emissions")
app.register_blueprint(facilities_bp, url_prefix="/api/facilities")
app.register_blueprint(data_bp, url_prefix="/api/data")
app.register_blueprint(reports_bp, url_prefix="/api/reports")
app.register_blueprint(dashboard_bp, url_prefix="/api/dashboard")
app.register_blueprint(custom_factors_bp, url_prefix="/api/custom-factors")
app.register_blueprint(scope2_bp, url_prefix="/api/scope2")
app.register_blueprint(scope3_bp, url_prefix="/api/scope3")
app.register_blueprint(managedata_bp, url_prefix="/api")
app.register_blueprint(factors_bp)
app.register_blueprint(notifications_bp, url_prefix="/api/notifications")
app.register_blueprint(audit_bp, url_prefix="/api/audit")
app.register_blueprint(satellite_bp, url_prefix="/api/satellite")
app.register_blueprint(qaqc_bp, url_prefix="/api/qaqc")

# Swagger UI Configuration (SEC-05 & INFO-01: Disabled in production unless explicitly enabled)
if (
    os.environ.get("FLASK_ENV") != "production"
    or os.environ.get("ENABLE_PUBLIC_SWAGGER", "false").lower() == "true"
):
    try:
        from flask_swagger_ui import get_swaggerui_blueprint

        SWAGGER_URL = "/api/docs"
        API_URL = "/static/swagger.json"

        swaggerui_blueprint = get_swaggerui_blueprint(
            SWAGGER_URL, API_URL, config={"app_name": "GHG Platform API Docs"}
        )
        app.register_blueprint(swaggerui_blueprint, url_prefix=SWAGGER_URL)
        csrf.exempt(swaggerui_blueprint)
    except Exception as e:
        app.logger.warning(f"Could not initialize Swagger UI: {e}")


def ensure_admin_seeded():
    """
    Seeds essential development and admin accounts:
    - Admin: user 'a' / password 'a' (role: admin) and 'a@a'
    - IT Manager: user 'z' / password 'z' (role: it_manager) and 'z@z'
    In production when SEED_ADMIN=true, also configures explicit production credentials.
    """
    _env_name = (
        os.environ.get("FLASK_ENV")
        or os.environ.get("APP_ENV")
        or os.environ.get("ENVIRONMENT")
        or "development"
    ).lower()
    is_production = _env_name in ["production", "prod", "staging"]

    accounts = [
        {
            "email": "a",
            "password": "a",
            "role": "admin",
            "fullName": "Administrator",
            "jobTitle": "Sustainability Lead",
        },
        {
            "email": "a@a",
            "password": "a",
            "role": "admin",
            "fullName": "Administrator",
            "jobTitle": "Sustainability Lead",
        },
        {
            "email": "z",
            "password": "z",
            "role": "it_manager",
            "fullName": "IT Manager",
            "jobTitle": "IT Operations Manager",
        },
        {
            "email": "z@z",
            "password": "z",
            "role": "it_manager",
            "fullName": "IT Manager",
            "jobTitle": "IT Operations Manager",
        },
    ]

    admin_email = os.environ.get("ADMIN_EMAIL", "").strip()
    admin_password = os.environ.get("ADMIN_PASSWORD", "").strip()
    it_admin_email = os.environ.get("IT_ADMIN_EMAIL", "").strip()
    it_admin_password = os.environ.get("IT_ADMIN_PASSWORD", "").strip()

    if admin_email and admin_password:
        accounts.append({
            "email": admin_email,
            "password": admin_password,
            "role": "admin",
            "fullName": os.environ.get("ADMIN_FULL_NAME", "System Administrator"),
            "jobTitle": "Sustainability Lead",
        })
    if it_admin_email and it_admin_password:
        accounts.append({
            "email": it_admin_email,
            "password": it_admin_password,
            "role": "it_admin",
            "fullName": os.environ.get("IT_ADMIN_FULL_NAME", "IT Administrator"),
            "jobTitle": "Systems Administrator",
        })

    try:
        from models import User
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
                    jobTitle=u.get("jobTitle", "Administrator"),
                    location="Global",
                    status="active",
                )
                user.set_password(u["password"])
                db.session.add(user)
                app.logger.info(f"Seeded {u['role']} account: {u['email']}")
            else:
                user.set_password(u["password"])
                user.status = "active"
                user.role = u["role"]
                app.logger.info(f"Updated account: {u['email']}")
        db.session.commit()
    except Exception as e:
        app.logger.error(f"Failed to seed admin accounts: {e}")
        db.session.rollback()


def ensure_database_indexes():
    try:
        from sqlalchemy import text
        queries = [
            "CREATE INDEX IF NOT EXISTS ix_emissions_activity ON emissions(activity);",
            "CREATE INDEX IF NOT EXISTS ix_emissions_division ON emissions(division);",
            "CREATE INDEX IF NOT EXISTS ix_emissions_year ON emissions(year);",
            "CREATE INDEX IF NOT EXISTS ix_emissions_facility_id ON emissions(facility_id);",
            "CREATE INDEX IF NOT EXISTS ix_emissions_status ON emissions(status);",
            "CREATE INDEX IF NOT EXISTS ix_production_data_facility_id ON production_data(facility_id);",
            "CREATE INDEX IF NOT EXISTS ix_production_data_year ON production_data(year);",
            "CREATE INDEX IF NOT EXISTS ix_scope2_emissions_year ON scope2_emissions(year);",
            "CREATE INDEX IF NOT EXISTS ix_scope2_emissions_status ON scope2_emissions(status);",
            "CREATE INDEX IF NOT EXISTS ix_scope3_emissions_year ON scope3_emissions(year);",
            "CREATE INDEX IF NOT EXISTS ix_scope3_emissions_status ON scope3_emissions(status);",
        ]
        with db.engine.connect() as conn:
            for q in queries:
                try:
                    conn.execute(text(q))
                except Exception:
                    pass
            conn.commit()
    except Exception as e:
        app.logger.warning(f"Could not ensure database indexes: {e}")


with app.app_context():
    db.create_all()
    ensure_database_indexes()
    ensure_admin_seeded()


@app.route("/api/auth/init-admin")
def init_admin_route():
    ensure_admin_seeded()
    from models import User
    users = User.query.all()
    return jsonify({
        "status": "ok",
        "message": "Admin and IT Manager accounts seeded successfully",
        "users": [{"email": u.email, "role": u.role, "status": u.status} for u in users]
    })


@app.route("/api/csrf-token")
def get_csrf_token():
    """
    Issues a CSRF token for the double-submit cookie pattern.
    Sets a non-HttpOnly cookie readable by the SPA via document.cookie.
    The client must send the same value as X-CSRFToken header on mutating requests.
    """
    token = generate_csrf()
    resp = jsonify({"csrf_token": token})
    resp.set_cookie(
        "csrf_token",
        token,
        httponly=False,          # Must be False — JavaScript reads this cookie
        secure=app.config.get("SESSION_COOKIE_SECURE", False),
        samesite=app.config.get("SESSION_COOKIE_SAMESITE", "Lax"),
        max_age=86400,
    )
    return resp




@app.route("/")
def index():
    return jsonify({
        "status": "online",
        "service": "GHG Accounting & Reporting Platform API",
        "health": "/api/health"
    })


@app.route("/api/health")
def health_check():
    # SEC-06 FIX: no longer expose DB engine name
    return jsonify({"status": "ok", "version": app.config.get("APP_VERSION", "1.0.0")})


@app.route("/api/health/live")
def health_liveness():
    """Kubernetes / Docker shallow liveness probe."""
    return jsonify({"status": "alive", "version": app.config.get("APP_VERSION", "1.0.0")}), 200


@app.route("/api/health/ready")
def health_readiness():
    """Kubernetes / Docker deep readiness probe verifying DB pool and filesystem readiness."""
    try:
        from sqlalchemy import text
        db.session.execute(text("SELECT 1"))
        wal_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ghg_app.db-wal")
        wal_mb = round(os.path.getsize(wal_path) / (1024 * 1024), 2) if os.path.exists(wal_path) else 0.0
        return jsonify({
            "status": "ready",
            "database": "connected",
            "wal_size_mb": wal_mb,
            "wal_warning": wal_mb > 100.0,
            "version": app.config.get("APP_VERSION", "1.0.0")
        }), 200
    except Exception as e:
        app.logger.error(f"Readiness probe failed: {e}")
        return jsonify({
            "status": "unhealthy",
            "database": "unreachable",
            "error": "Database connectivity check failed"
        }), 503


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        try:
            from routes.auth import load_settings_from_db
            load_settings_from_db()
        except Exception:
            pass

    # SEC-05 FIX: never run debug=True in production; bind to localhost only
    is_debug = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    app.run(debug=is_debug, host="127.0.0.1", port=int(os.environ.get("PORT", 5000)))
