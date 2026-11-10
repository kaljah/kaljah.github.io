"""
SQLite Write Serialization & Lock-Retry Utilities
=================================================
In SQLite WAL mode, concurrent writers or a thread promoting a deferred read
snapshot to a write transaction after another commit can fail immediately with
``SQLITE_BUSY_SNAPSHOT`` ("database is locked") without waiting for
``busy_timeout``.

This module provides:
- Process-wide reentrant write serialization (``sqlite_write_lock``) that activates
  only when the active SQLAlchemy engine uses SQLite (PostgreSQL is untouched).
- Thread-local reentrant acquisition/release helpers for Flask request hooks.
- ``commit_with_retry`` for defense-in-depth handling of transient SQLite locks.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from sqlalchemy.exc import OperationalError

_WRITE_RLOCK = threading.RLock()
_TLS = threading.local()


def is_sqlite_engine(bind_or_session: Any) -> bool:
    """Return True if the given SQLAlchemy Engine/Connection/Session targets SQLite."""
    if bind_or_session is None:
        return True
    try:
        bind = (
            bind_or_session.get_bind()
            if hasattr(bind_or_session, "get_bind")
            else bind_or_session
        )
    except (AttributeError, RuntimeError):
        return False
    dialect = getattr(bind, "dialect", None)
    return str(getattr(dialect, "name", "") or "").lower() == "sqlite"


def _current_depth() -> int:
    return int(getattr(_TLS, "sqlite_lock_depth", 0) or 0)


def acquire_sqlite_write_lock(bind: Any = None) -> bool:
    """Acquire the reentrant SQLite write lock for the current thread if bind is SQLite."""
    if bind is not None and not is_sqlite_engine(bind):
        return False
    _WRITE_RLOCK.acquire()
    _TLS.sqlite_lock_depth = _current_depth() + 1
    return True


def release_sqlite_write_lock() -> bool:
    """Release one level of the current thread's SQLite write lock, if held."""
    depth = _current_depth()
    if depth <= 0:
        return False
    _TLS.sqlite_lock_depth = depth - 1
    try:
        _WRITE_RLOCK.release()
    except RuntimeError:
        _TLS.sqlite_lock_depth = 0
        return False
    return True


def release_all_sqlite_write_locks() -> int:
    """Release every lock level held by the current thread (teardown safety net)."""
    released = 0
    while release_sqlite_write_lock():
        released += 1
    return released


@contextmanager
def sqlite_write_lock(bind: Any = None) -> Iterator[None]:
    """Serialize write transactions on SQLite while leaving PostgreSQL untouched."""
    acquired = acquire_sqlite_write_lock(bind)
    try:
        yield
    finally:
        if acquired:
            release_sqlite_write_lock()


def _is_sqlite_lock_error(exc: BaseException) -> bool:
    msg = str(exc).lower()
    return (
        "database is locked" in msg
        or "database table is locked" in msg
        or "sqlite_busy" in msg
    )


def commit_with_retry(
    session: Any,
    *,
    max_attempts: int = 5,
    initial_delay: float = 0.05,
) -> None:
    """Commit under ``sqlite_write_lock`` with exponential backoff on transient SQLite busy errors."""
    bind = session.get_bind() if hasattr(session, "get_bind") else None
    delay = initial_delay
    for attempt in range(max(1, int(max_attempts))):
        with sqlite_write_lock(bind):
            try:
                session.commit()
                return
            except OperationalError as exc:
                if not _is_sqlite_lock_error(exc) or attempt >= max_attempts - 1:
                    raise
        time.sleep(delay)
        delay = min(delay * 2.0, 0.5)
