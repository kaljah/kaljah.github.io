"""
Error Tracking & Incident Identification Service (Item 4.3)
===========================================================
- Sentry integration hook (auto-enables when SENTRY_DSN is configured)
- Incident ID tagging (X-Incident-ID header and JSON error payload)
- Safe error sanitization (no internal stack traces exposed to client)
"""
import os
import uuid
import logging
from flask import jsonify, request, g

logger = logging.getLogger("error_tracker")
sentry_active = False


def init_error_tracker(app):
    """Initializes Sentry SDK if configured, and registers global incident error handlers."""
    global sentry_active

    sentry_dsn = os.environ.get("SENTRY_DSN")
    if sentry_dsn:
        try:
            import sentry_sdk
            from sentry_sdk.integrations.flask import FlaskIntegration
            from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

            sentry_sdk.init(
                dsn=sentry_dsn,
                integrations=[FlaskIntegration(), SqlalchemyIntegration()],
                traces_sample_rate=float(os.environ.get("SENTRY_TRACES_SAMPLE_RATE", "0.2")),
                environment=os.environ.get("FLASK_ENV", "production"),
                release=app.config.get("APP_VERSION", "1.0.0"),
            )
            sentry_active = True
            app.logger.info("Sentry SDK initialized successfully.")
        except ImportError:
            app.logger.warning("SENTRY_DSN set, but sentry-sdk package is not installed.")
        except Exception as e:
            app.logger.error(f"Failed to initialize Sentry SDK: {e}")

    @app.errorhandler(500)
    def handle_internal_server_error(e):
        return _format_incident_response(e, 500)

    @app.errorhandler(Exception)
    def handle_unhandled_exception(e):
        # Ignore HTTP exceptions handled by Werkzeug (e.g. 404, 400, 401, 403, 422)
        from werkzeug.exceptions import HTTPException
        if isinstance(e, HTTPException):
            return e

        return _format_incident_response(e, 500)


def generate_incident_id():
    """Generates a prefixed incident identifier, e.g. INC-a1b2c3d4e5f6."""
    return f"INC-{uuid.uuid4().hex[:12]}"


def _format_incident_response(exc, status_code=500):
    incident_id = generate_incident_id()
    
    # Log structured error with incident_id
    extra = {"incident_id": incident_id}
    logger.error(
        f"Server Incident {incident_id} on {request.method} {request.path}: {exc}",
        exc_info=exc,
        extra=extra,
    )

    if sentry_active:
        try:
            import sentry_sdk
            with sentry_sdk.push_scope() as scope:
                scope.set_tag("incident_id", incident_id)
                sentry_sdk.capture_exception(exc)
        except Exception:
            pass

    response = jsonify({
        "error": "An internal server error occurred. Please quote the incident ID if contacting support.",
        "incident_id": incident_id,
        "code": status_code,
    })
    response.status_code = status_code
    response.headers["X-Incident-ID"] = incident_id
    return response
