"""
Structured Logging Service (Item 4.3)
=====================================
Outputs JSON-formatted logs in production environments or when LOG_FORMAT=json.
Preserves human-readable formatting in development.
"""
import os
import json
import logging
import datetime
from flask import has_request_context, request, g


class JsonFormatter(logging.Formatter):
    """Formats log records as single-line JSON objects."""

    def format(self, record):
        log_entry = {
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Include request context if active
        if has_request_context():
            log_entry["request_id"] = getattr(request, "id", None)
            log_entry["method"] = request.method
            log_entry["path"] = request.path
            log_entry["remote_addr"] = request.remote_addr
            if hasattr(g, "user_id"):
                log_entry["user_id"] = g.user_id

        # Include exception details if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        # Include extra attributes attached to record
        if hasattr(record, "incident_id"):
            log_entry["incident_id"] = record.incident_id
        if hasattr(record, "duration_ms"):
            log_entry["duration_ms"] = record.duration_ms

        return json.dumps(log_entry, default=str)


def setup_logging(app):
    """Configures application logger based on environment."""
    is_prod = app.config.get("IS_PRODUCTION", False)
    log_format = os.environ.get("LOG_FORMAT", "json" if is_prod else "text").lower()

    handler = logging.StreamHandler()
    if log_format == "json":
        handler.setFormatter(JsonFormatter())
    else:
        fmt = "%(asctime)s [%(levelname)s] in %(module)s: %(message)s"
        handler.setFormatter(logging.Formatter(fmt))

    log_level = getattr(logging, os.environ.get("LOG_LEVEL", "INFO").upper(), logging.INFO)
    app.logger.setLevel(log_level)

    # Avoid duplicate handlers
    if not any(isinstance(h, logging.StreamHandler) for h in app.logger.handlers):
        app.logger.addHandler(handler)
    else:
        for h in app.logger.handlers:
            if isinstance(h, logging.StreamHandler) and log_format == "json":
                h.setFormatter(JsonFormatter())
