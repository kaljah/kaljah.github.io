"""Shared fixtures-as-functions for the audit regression tests (tests/test_audit_rc*.py)."""
import io
import time
import uuid

from extensions import db
from models import Facility, User


def uniq(prefix="t"):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


def make_user(role="user", location="Global", email=None):
    u = User(
        email=email or f"{uniq(role)}@audit.test",
        fullName=f"Audit {role}",
        orgName="Audit Org",
        sector="Oil & Gas",
        role=role,
        status="active",
        location=location,
        department="Audit",
        jobTitle="Auditor",
    )
    u.set_password("AuditPass!2026")
    db.session.add(u)
    db.session.commit()
    return u


def make_facility(name=None, region="West", location=None, **kw):
    f = Facility(name=name or uniq("FAC"), region=region, location=location or region, **kw)
    db.session.add(f)
    db.session.commit()
    return f


def login(client, user):
    """Log in through the real endpoint so session bookkeeping (e.g. session_version) is exercised."""
    r = client.post("/api/auth/login", json={"email": user.email, "password": "AuditPass!2026"})
    assert r.status_code == 200, r.get_data(as_text=True)[:300]
    return r


def upload(client, csv_text, scope, overwrite=True, filename="f.csv", wait=True):
    r = client.post(
        "/api/emissions/upload/start",
        data={"file": (io.BytesIO(csv_text.encode()), filename), "scope": scope,
              "overwrite_duplicates": "true" if overwrite else "false"},
        content_type="multipart/form-data",
    )
    job = (r.get_json() or {}).get("job_id")
    status = None
    if job and wait:
        for _ in range(200):
            status = client.get(f"/api/emissions/upload/status/{job}").get_json()
            if status.get("status") not in ("processing", "queued", "pending"):
                break
            time.sleep(0.1)
    return r, job, status
