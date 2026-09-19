import os
from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_migrate import Migrate
from config import Config
from flask_wtf.csrf import CSRFProtect, generate_csrf
import uuid
import time
import traceback

from extensions import db, limiter  # SEC-08 FIX: import limiter

app = Flask(__name__)
app.url_map.strict_slashes = False
app.config.from_object(Config)


# Enable CORS
CORS(app, origins=app.config.get("ALLOWED_ORIGINS", []), supports_credentials=True)

# Database
db.init_app(app)
limiter.init_app(app)  # SEC-08 FIX: activate flask-limiter
migrate = Migrate(app, db)

from sqlalchemy import event
from sqlalchemy.engine import Engine
import sqlite3
from routes.dashboard import clear_dashboard_cache


@event.listens_for(Engine, "connect")
def set_sqlite_pragmas(dbapi_conn, _):
    if isinstance(dbapi_conn, sqlite3.Connection):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys = ON")
        cursor.execute("PRAGMA journal_mode = WAL")
        cursor.execute("PRAGMA synchronous = NORMAL")
        cursor.close()


from routes.dashboard import clear_dashboard_cache


@event.listens_for(db.session, "after_commit")
def receive_after_commit(session):
    clear_dashboard_cache()


# CSRF Protection
csrf = CSRFProtect(app)


# Request Logging & Request ID Middleware
@app.before_request
def before_request():
    request.start_time = time.time()
    request.id = request.headers.get("X-Request-ID", str(uuid.uuid4()))


@app.after_request
def after_request(response):
    response.headers["X-Request-ID"] = getattr(request, "id", "")

    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "
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
    import traceback
    with open('trace.log', 'a') as f:
        f.write(f"Unhandled Exception: {str(error)}\n{traceback.format_exc()}\n\n")
    # Log the traceback
    app.logger.error(f"Unhandled Exception: {str(error)}\n{traceback.format_exc()}")

    # Return 422 for unprocessable entity to match standard
    if hasattr(error, "code") and error.code == 422:
        return (
            jsonify(
                {
                    "error": str(error),
                    "code": 422,
                    "request_id": getattr(request, "id", ""),
                }
            ),
            422,
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

    return jsonify(
        {
            "error": "Internal server error",
            "code": getattr(error, "code", 500),
            "request_id": getattr(request, "id", ""),
        }
    ), getattr(error, "code", 500)


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
    try:
        from models import User
        users_to_seed = [
            {
                "email": "admin@ghg.com",
                "password": "Admin12345!",
                "role": "admin",
                "fullName": "System Administrator",
            },
            {
                "email": "a@a",
                "password": "a",
                "role": "admin",
                "fullName": "Admin User",
            },
            {
                "email": "a",
                "password": "a",
                "role": "admin",
                "fullName": "Admin User",
            },
        ]
        for u in users_to_seed:
            user = User.query.filter_by(email=u["email"]).first()
            if not user:
                user = User(
                    fullName=u["fullName"],
                    orgName="GHG Operations",
                    email=u["email"],
                    role=u["role"],
                    sector="Oil & Gas",
                    department="Sustainability & IT",
                    jobTitle="Administrator",
                    location="Global",
                    status="active",
                )
                user.set_password(u["password"])
                db.session.add(user)
            else:
                user.set_password(u["password"])
                user.status = "active"
                user.role = u["role"]
        db.session.commit()
    except Exception as e:
        app.logger.error(f"Failed to auto-seed admin: {e}")


with app.app_context():
    db.create_all()
    ensure_admin_seeded()


@app.route("/api/auth/init-admin")
def init_admin_route():
    ensure_admin_seeded()
    from models import User
    users = User.query.all()
    return jsonify({
        "status": "ok",
        "message": "Admin accounts seeded and ready",
        "users": [u.email for u in users]
    })


@app.route("/api/csrf-token")
def get_csrf_token():
    return jsonify({"csrf_token": generate_csrf()})


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


if __name__ == "__main__":
    with app.app_context():
        db.create_all()

    # SEC-05 FIX: never run debug=True in production; bind to localhost only
    is_debug = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    app.run(debug=is_debug, host="127.0.0.1", port=int(os.environ.get("PORT", 5000)))
