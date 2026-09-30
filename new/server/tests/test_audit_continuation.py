"""
Regression tests for findings from the audit continuation pass (V1-V3 in AUDIT_MEMORY.md).
"""
import datetime

import pytest

from app import app, ensure_admin_seeded
from models import db, User, Facility, Emission


@pytest.fixture
def client():
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False
    with app.test_client() as c:
        with app.app_context():
            yield c


@pytest.fixture
def admin_client(client):
    admin = User.query.filter_by(email="continuation_admin@test.com").first()
    if not admin:
        admin = User(
            email="continuation_admin@test.com",
            fullName="Continuation Admin",
            orgName="AuditCorp",
            sector="Energy",
            role="admin",
            location="Global",
            status="active",
        )
        admin.set_password("ContinuationAdmin123!")
        db.session.add(admin)
        db.session.commit()
    with client.session_transaction() as sess:
        sess["user_id"] = admin.id
    return client


# ── V1: non-object JSON bodies ───────────────────────────────────────────────

@pytest.mark.parametrize("body", ['"just a string"', "[1, 2, 3]", "42", "true"])
@pytest.mark.parametrize("path", ["/api/emissions/", "/api/facilities/", "/api/auth/login"])
def test_non_object_json_body_rejected_with_400(admin_client, path, body):
    resp = admin_client.post(path, data=body, content_type="application/json")
    assert resp.status_code == 400
    assert resp.get_json()["error"] == "JSON body must be an object"


def test_object_json_body_still_reaches_route(client):
    resp = client.post("/api/auth/login", json={"email": "", "password": ""})
    assert resp.status_code == 400
    assert resp.get_json()["error"] == "Email and password required"


# ── V2: hard-coded dev accounts (C2 regression) ─────────────────────────────

def test_seed_admin_never_creates_trivial_accounts(client, monkeypatch):
    monkeypatch.setenv("SEED_ADMIN", "true")
    monkeypatch.setenv("FLASK_ENV", "development")
    for var in ("ADMIN_EMAIL", "ADMIN_PASSWORD", "IT_ADMIN_EMAIL", "IT_ADMIN_PASSWORD"):
        monkeypatch.delenv(var, raising=False)
    ensure_admin_seeded()
    for email in ("a", "a@a", "z", "z@z"):
        assert User.query.filter_by(email=email).first() is None


def test_login_has_no_short_alias_backdoor(client):
    target = User.query.filter_by(email="a@a").first()
    created = False
    if not target:
        target = User(email="a@a", fullName="Alias Target", orgName="X", sector="Energy",
                      role="admin", location="Global", status="active")
        db.session.add(target)
        created = True
    target.set_password("AliasTarget123!")
    db.session.commit()
    try:
        # "a" must not resolve to the "a@a" account.
        resp = client.post("/api/auth/login", json={"email": "a", "password": "AliasTarget123!"})
        assert resp.status_code == 401
    finally:
        if created:
            db.session.delete(target)
            db.session.commit()


# ── V3: emissions pagination ─────────────────────────────────────────────────

@pytest.fixture
def paged_emissions(admin_client):
    fac = Facility.query.filter_by(name="Continuation Paging Facility").first()
    if not fac:
        fac = Facility(name="Continuation Paging Facility", location="Global",
                       boundary_type="Operational Control", segment="Upstream")
        db.session.add(fac)
        db.session.commit()
    Emission.query.filter_by(facility_id=fac.id, year=2091).delete()
    base = datetime.datetime(2091, 1, 1)
    for i in range(7):
        db.session.add(Emission(
            facility_id=fac.id, year=2091, month=1, process_type="combustion",
            fuel_type="Diesel", quantity=1.0, co2e_total=1.0, status="Verified",
            timestamp=base + datetime.timedelta(hours=i),
        ))
    db.session.commit()
    yield fac.id
    Emission.query.filter_by(facility_id=fac.id, year=2091).delete()
    db.session.commit()


def test_offset_not_aligned_to_limit_is_honoured(admin_client, paged_emissions):
    q = f"/api/emissions/?scope=1&year=2091&facility_id={paged_emissions}"
    full = admin_client.get(q + "&limit=50&offset=0").get_json()["data"]
    assert len(full) == 7
    page = admin_client.get(q + "&limit=5&offset=3").get_json()["data"]
    assert [r["id"] for r in page] == [r["id"] for r in full[3:]]


def test_limit_all_goes_through_bounded_path(admin_client, paged_emissions):
    q = f"/api/emissions/?scope=1&year=2091&facility_id={paged_emissions}&limit=all"
    resp = admin_client.get(q)
    assert resp.status_code == 200
    body = resp.get_json()
    assert len(body["data"]) == 7
    assert body["pages"] == 1
