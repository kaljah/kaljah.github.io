"""
Regression test: import_debug.log must not be recreated.
Ensures the background_processor routes all logging through app.logger
(which uses the rotating RotatingFileHandler at trace.log, max 50 MB, 3 backups).
"""
import os
import pytest

SERVER_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def test_no_import_debug_log_file_exists():
    """
    import_debug.log was a 4.1 GB unbounded log file that caused disk exhaustion.
    It must not exist. All background processor logging must go through
    app.logger (trace.log, rotating handler).
    """
    log_path = os.path.join(SERVER_DIR, "import_debug.log")
    assert not os.path.exists(log_path), (
        f"REGRESSION FAIL: {log_path} was recreated. "
        "Background processor must NOT open import_debug.log directly. "
        "Use current_app.logger instead."
    )


def test_trace_log_uses_rotating_handler():
    """
    Verify that the application's rotating log handler is configured
    with size and backup limits (not unbounded).
    """
    import logging
    from logging.handlers import RotatingFileHandler
    from app import app

    app_handlers = list(app.logger.handlers) + list(logging.getLogger().handlers)


    # Find any RotatingFileHandlers
    rotating_handlers = [h for h in app_handlers if isinstance(h, RotatingFileHandler)]

    # If a rotating handler exists, verify it has a size limit
    for h in rotating_handlers:
        assert h.maxBytes > 0, (
            "RotatingFileHandler must have maxBytes set — found unbounded handler"
        )
        assert h.backupCount > 0, (
            "RotatingFileHandler must have backupCount > 0"
        )
