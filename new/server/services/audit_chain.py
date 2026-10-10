"""Tamper-evident audit log (pilot check 2026-10-09, F12).

Every ActivityLog row is sealed when it is written: ``entry_hash`` is the SHA-256 of the row's content
(including ``details`` and the before/after values) and of ``prev_hash``, the ``entry_hash`` of the row
before it. Changing a sealed row changes its hash; deleting or inserting a row breaks the link of the
next one. ``verify_chain`` recomputes both and reports every break.

Rows are sealed one writer at a time: before the last hash is read, PostgreSQL takes a transaction-scoped
advisory lock and SQLite its write lock (a no-op write), so two writers never chain onto the same row.
On PostgreSQL a trigger (migration d4e8a1b7c2f0) also refuses UPDATE and DELETE on the table, except the
one change the application makes: user deletion clears ``user_id`` (the stored ``user_name`` stays, and
the hash covers the name, not the id).

Removing the newest rows leaves an intact (shorter) chain; that is caught by comparing with a saved
checkpoint (``/api/audit/verify-checkpoint``).
"""
import hashlib
import json
from datetime import datetime

from sqlalchemy import event, text

GENESIS_HASH = "0" * 64
_ADVISORY_LOCK_KEY = 4_141_592_653  # any constant shared by all workers


def _timestamp_text(ts):
    if ts is None:
        return ""
    if isinstance(ts, str):  # SQLite text read without type processing
        ts = datetime.fromisoformat(ts)
    # stored without a time zone (PostgreSQL "timestamp without time zone"): hash the same wall time
    return ts.replace(tzinfo=None).isoformat(timespec="microseconds")


def compute_entry_hash(log, prev_hash):
    """Hash of one entry's content chained to the previous entry's hash."""
    content = [
        prev_hash or GENESIS_HASH,
        _timestamp_text(log.timestamp),
        log.action or "", log.record_id or "", log.user_name or "", log.details or "",
        log.old_values or "",
        log.new_values or "",
        log.ip_address or "",
        log.entity or "",
        log.entity_id or "",
        "" if log.facility_id is None else str(log.facility_id),
        log.metadata_json or "",
    ]
    return hashlib.sha256(json.dumps(content, ensure_ascii=False, separators=(",", ":")).encode("utf-8")).hexdigest()


def _last_hash(session):
    row = session.execute(text("SELECT entry_hash FROM activity_log ORDER BY id DESC LIMIT 1")).first()
    return (row[0] if row and row[0] else GENESIS_HASH)


def seal_new_entries(session, flush_context=None, instances=None):
    """before_flush: chain the ActivityLog rows added in this flush onto the last stored row."""
    from models import ActivityLog, utc_now

    new_logs = [obj for obj in session.new if isinstance(obj, ActivityLog) and not obj.entry_hash]
    if not new_logs:
        return
    bind = session.get_bind()
    if bind.dialect.name == "postgresql":
        session.execute(text("SELECT pg_advisory_xact_lock(:k)"), {"k": _ADVISORY_LOCK_KEY})
    elif bind.dialect.name == "sqlite":
        session.execute(text("UPDATE activity_log SET id = id WHERE 0"))
    prev = _last_hash(session)
    for log in new_logs:  # session.new keeps insertion order, which is the id order of the INSERTs
        if log.timestamp is None:
            log.timestamp = utc_now()
        # sealed with the value as stored: microseconds kept, time zone dropped by the column type
        log.timestamp = log.timestamp.replace(tzinfo=None)
        log.prev_hash = prev
        log.entry_hash = compute_entry_hash(log, prev)
        prev = log.entry_hash


def register(scoped_session):
    if not event.contains(scoped_session, "before_flush", seal_new_entries):
        event.listen(scoped_session, "before_flush", seal_new_entries)


def verify_chain(query, max_issues=50):
    """Walk the log in id order. Returns (total, head_hash, issues, issue_count): issues lists (up to
    max_issues) the rows whose content no longer matches their hash, whose link to the previous row is
    broken, or that are unsealed."""
    issues = []
    total = 0
    expected_prev = GENESIS_HASH
    issue_count = 0
    for log in query:
        total += 1
        found = []
        if not log.entry_hash:
            found.append({"id": log.id, "problem": "unsealed", "detail": "Entry has no hash."})
        else:
            if log.prev_hash != expected_prev:
                found.append({"id": log.id, "problem": "chain_break",
                              "detail": "The entry before this one was deleted, inserted or altered."})
            if compute_entry_hash(log, log.prev_hash) != log.entry_hash:
                found.append({"id": log.id, "problem": "content_changed",
                              "detail": "This entry was changed after it was written."})
        issue_count += len(found)
        issues.extend(found[: max(0, max_issues - len(issues))])
        expected_prev = log.entry_hash or expected_prev
    return total, expected_prev, issues, issue_count


def data_fingerprint(data):
    """SHA-256 of a report's data (records and filters), reproducible from the same data. Printed in the
    exported report and recorded in the audit log, so an auditor can match a document to its log entry."""
    return hashlib.sha256(json.dumps(data, sort_keys=True, default=str, ensure_ascii=False,
                                     separators=(",", ":")).encode("utf-8")).hexdigest()


def record_report_fingerprint(resp, user, kind, filters, record_count, fingerprint):
    """REPORT entry in the audit log carrying the fingerprint printed in an exported document, and the
    X-Audit-SHA256 header of the response. Returns the response."""
    from flask import current_app, request

    from extensions import db
    from utils import log_activity_and_notify

    try:
        log_activity_and_notify(
            action="REPORT", record_id=fingerprint[:16], user=user, request=request, entity="Report",
            details=f"{kind} generated: {record_count} records, filters "
                    f"{json.dumps(filters, sort_keys=True, default=str)}, data fingerprint {fingerprint}",
        )
        db.session.commit()
    except Exception as e:  # the document is still returned; the failure is logged
        db.session.rollback()
        current_app.logger.error(f"Could not record the report fingerprint: {e}")
    resp.headers["X-Audit-SHA256"] = fingerprint
    return resp
