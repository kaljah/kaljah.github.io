"""Idle session timeout (review 2026-10-15).

IT chooses the timeout in User Management (SystemSetting ``session_timeout_minutes``). It was stored and
shown but never applied: the browser signed out after a fixed 10 minutes and the server cookie lived 8 hours,
renewed by every request. The server now ends a session idle for longer than the timeout; the client reads the
same value from /api/auth/me for its warning and sign-out timers.
"""
import json
import time

IDLE_TIMEOUT_CHOICES = (15, 30, 60, 120, 240, 480)
DEFAULT_IDLE_TIMEOUT_MINUTES = 30
_CACHE_SECONDS = 5.0
_cache = {"value": None, "at": 0.0}

# GET requests the client sends on its own (the notification poll): they do not keep a session alive
_BACKGROUND_PREFIXES = ("/api/notifications",)


def _parse(raw):
    try:
        value = json.loads(raw) if isinstance(raw, str) else raw
        value = int(value)
    except (TypeError, ValueError):
        return DEFAULT_IDLE_TIMEOUT_MINUTES
    return value if value in IDLE_TIMEOUT_CHOICES else DEFAULT_IDLE_TIMEOUT_MINUTES


def idle_timeout_minutes():
    """The configured idle timeout in minutes (read at most every few seconds)."""
    now = time.monotonic()
    if _cache["value"] is not None and now - _cache["at"] < _CACHE_SECONDS:
        return _cache["value"]
    from extensions import db
    from models import SystemSetting

    try:
        row = db.session.get(SystemSetting, "session_timeout_minutes")
        value = _parse(row.value) if row is not None and row.value not in (None, "") else DEFAULT_IDLE_TIMEOUT_MINUTES
    except Exception:
        value = DEFAULT_IDLE_TIMEOUT_MINUTES
    _cache.update(value=value, at=now)
    return value


def forget_cached_timeout():
    _cache.update(value=None, at=0.0)


def is_background_request(request):
    return request.method == "GET" and request.path.startswith(_BACKGROUND_PREFIXES)


def check_idle(session, request):
    """End the session when it has been idle too long; otherwise record this request as activity.
    Returns True when the session was ended."""
    now = time.time()
    last = session.get("last_seen")
    try:
        last = float(last) if last is not None else None
    except (TypeError, ValueError):
        last = None
    if last is not None and now - last > idle_timeout_minutes() * 60:
        session.clear()
        return True
    if last is None or not is_background_request(request):
        session["last_seen"] = now
    return False
