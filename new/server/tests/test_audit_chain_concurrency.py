"""Concurrent writers never fork the audit hash chain on SQLite (development and tests).

PostgreSQL takes an advisory lock before reading the last hash; on SQLite two sessions could read
the same last hash and both chain onto it (a background import writing while a request writes),
which verification then reports as tampering. services/audit_chain.py takes SQLite's write lock first.
"""
import threading

from extensions import db
from models import ActivityLog
from services.audit_chain import verify_chain


def test_parallel_audit_writes_keep_one_chain(app):
    errors = []
    start = threading.Barrier(4)

    def writer(n):
        with app.app_context():
            try:
                start.wait()
                for i in range(15):
                    db.session.add(ActivityLog(action="CONCURRENCY", record_id=f"{n}-{i}", entity="Test",
                                               details=f"writer {n} entry {i}"))
                    db.session.commit()
            except Exception as e:  # pragma: no cover - reported below
                errors.append(repr(e))
            finally:
                db.session.remove()

    threads = [threading.Thread(target=writer, args=(n,)) for n in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=120)

    assert not errors
    with app.app_context():
        total, _head, issues, issue_count = verify_chain(
            ActivityLog.query.order_by(ActivityLog.id).yield_per(500))
        assert total >= 60
        assert issue_count == 0, issues[:5]
