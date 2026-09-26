"""Shared helper for Agent A repro scripts (audit harness only; no app source edits)."""
import sys
sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/tools")
from auditlib import make_db, api_client, sql


def post_scope1(db, payload):
    make_db(db)
    c = api_client(db, "admin")
    fac = sql(db, "select id from facilities order by id limit 1")[0]["id"]
    p = {"year": 2025, "month": 1, "facility_id": fac}
    p.update(payload)
    r = c.post("/api/emissions/", json=p)
    if r.status_code != 201:
        return {"_status": r.status_code, "_body": r.get_json()}
    return sql(db, "select * from emissions where id=?", (r.get_json()["id"],))[0]


def check(label, expected, actual, rel=0.01):
    ok = actual is not None and abs(actual - expected) <= rel * max(abs(expected), 1e-12)
    print(f"{'OK ' if ok else 'BAD'} {label}: expected={expected:.6g} actual={actual}")
    return ok
