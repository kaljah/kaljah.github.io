"""RC-14 schema governance regressions (BUG-016).

Alembic is the only mechanism that changes the schema. These tests run in subprocesses
because `app` is a module-level singleton bound to one DATABASE_URL per process.
"""
import os
import shutil
import sqlite3
import subprocess
import sys

import pytest

SERVER = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SNAPSHOT = os.path.abspath(os.path.join(SERVER, "..", "..", "audit", "db", "snapshot_original.db"))
PROD_SECRET = "regression-test-secret-key-that-is-long-enough-0123456789abcdef"


def _env(db_path, **extra):
    env = {k: v for k, v in os.environ.items() if k not in ("FLASK_ENV", "APP_ENV", "ENVIRONMENT")}
    env.update(DATABASE_URL="sqlite:///" + db_path.replace("\\", "/"), SEED_ADMIN="false", FLASK_APP="app.py")
    env.update(extra)
    return env


def _run(args, env):
    return subprocess.run([sys.executable, *args], cwd=SERVER, env=env, capture_output=True, text=True, timeout=300)


def _heads():
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    cfg = Config(os.path.join(SERVER, "migrations", "alembic.ini"))
    cfg.set_main_option("script_location", os.path.join(SERVER, "migrations"))
    return set(ScriptDirectory.from_config(cfg).get_heads())


def _version(db_path):
    con = sqlite3.connect(db_path)
    try:
        return {r[0] for r in con.execute("SELECT version_num FROM alembic_version")}
    finally:
        con.close()


def test_flask_db_upgrade_builds_fresh_database_to_head(tmp_path):
    db = str(tmp_path / "fresh.db")
    p = _run(["-m", "flask", "db", "upgrade"], _env(db))
    assert p.returncode == 0, p.stderr[-2000:]
    assert _version(db) == _heads()
    con = sqlite3.connect(db)
    tables = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    con.close()
    assert {"users", "facilities", "emissions", "custom_factors"} <= tables


@pytest.mark.skipif(not os.path.exists(SNAPSHOT), reason="audit snapshot not available")
def test_flask_db_upgrade_brings_existing_snapshot_to_head(tmp_path):
    db = str(tmp_path / "snap.db")
    shutil.copyfile(SNAPSHOT, db)
    p = _run(["-m", "flask", "db", "upgrade"], _env(db))
    assert p.returncode == 0, p.stderr[-2000:]
    assert _version(db) == _heads()


def test_production_refuses_to_start_when_schema_not_at_head(tmp_path):
    db = str(tmp_path / "prod.db")
    env = _env(db, FLASK_ENV="production", SECRET_KEY=PROD_SECRET)
    p = _run(["-c", "import app"], env)
    assert p.returncode != 0
    assert "flask db upgrade" in p.stderr
    # after the documented deploy step the app starts
    assert _run(["-m", "flask", "db", "upgrade"], env).returncode == 0
    assert _run(["-c", "import app"], env).returncode == 0


def test_import_does_not_alter_schema_outside_alembic():
    """No ad-hoc ALTER TABLE / create_all at import time (the old connect hook and ensure_model_columns)."""
    src = open(os.path.join(SERVER, "app.py"), encoding="utf-8").read()
    assert "ALTER TABLE" not in src
    assert "ensure_model_columns" not in src
    assert "db.create_all()" not in src


# ── Behavioural RC-14 regressions (in-process, shared test DB) ─────────────────────

import datetime as _dt

from extensions import db as _db
from models import (ActivityLog, CustomFactor, Emission, Facility, LevelUpgradeLog, ProductionData,
                    SbtiTarget, User)
from tests.audit_helpers import login, make_facility, make_user, uniq


@pytest.fixture
def ctx(app):
    with app.app_context():
        yield


def test_emissions_custom_factor_fk_declared():
    fks = [fk for fk in Emission.__table__.c.custom_factor_id.foreign_keys]
    assert fks and fks[0].column.table.name == "custom_factors"


def test_bug009_delete_facility_with_level_upgrade_log(client, ctx):
    f = make_facility(region="West")
    _db.session.add(LevelUpgradeLog(facility_id=f.id, old_level=3, new_level=4, justification="x"))
    _db.session.commit()
    login(client, make_user("admin", "Global"))
    r = client.delete(f"/api/facilities/{f.id}")
    assert r.status_code == 200, r.get_data(as_text=True)
    assert "sqlite" not in r.get_data(as_text=True).lower()
    assert LevelUpgradeLog.query.filter_by(facility_id=f.id).count() == 0


def test_bug010_069_106_delete_user_with_references_keeps_evidence(client, ctx):
    maker = make_user("admin", "Global")
    f = make_facility(region="West")
    _db.session.add_all([
        ProductionData(facility_id=f.id, year=2024, month=1, created_by=maker.id),
        SbtiTarget(base_year=2020, base_year_emissions=100.0, created_by=maker.id),
        LevelUpgradeLog(facility_id=f.id, old_level=3, new_level=4, created_by=maker.id),
    ])
    e = Emission(facility_id=f.id, year=2024, month=1, process_type="combustion", co2e_total=1.0,
                 status="Verified", created_by=maker.id, approved_by=maker.id)
    _db.session.add(e)
    _db.session.commit()
    eid, mid, memail = e.id, maker.id, maker.email
    login(client, make_user("it_admin", "Global"))
    r = client.delete(f"/api/auth/users/{mid}")
    assert r.status_code == 200, r.get_data(as_text=True)
    _db.session.expire_all()
    assert _db.session.get(User, mid) is None
    row = _db.session.get(Emission, eid)
    assert row.approved_by is None and memail in (row.approved_by_name or "")
    assert memail in (row.created_by_name or "")
    assert ActivityLog.query.filter_by(action="DELETE_USER", record_id=str(mid)).count() == 1


def test_bug106_register_and_logout_are_logged(client, ctx):
    it = make_user("it_admin", "Global")
    login(client, it)
    email = f"{uniq('new')}@audit.test"
    r = client.post("/api/auth/register", json={"fullName": "N U", "orgName": "O", "email": email,
                                                "sector": "Oil & Gas", "password": "Str0ng!Passw0rd", "role": "user"})
    assert r.status_code in (200, 201), r.get_data(as_text=True)
    assert ActivityLog.query.filter(ActivityLog.action == "REGISTER", ActivityLog.details.contains(email)).count() == 1
    client.post("/api/auth/logout")
    assert ActivityLog.query.filter_by(action="LOGOUT", record_id=str(it.id)).count() >= 1


def test_bug114_logout_invalidates_captured_cookie(client, ctx, app):
    u = make_user("admin", "Global")
    login(client, u)
    assert client.get("/api/facilities").status_code == 200
    # capture the cookie, log out, replay it from a second client
    cookie = client.get_cookie(app.config.get("SESSION_COOKIE_NAME", "session"))
    client.post("/api/auth/logout")
    with app.test_client() as attacker:
        attacker.set_cookie(cookie.key, cookie.value)
        assert attacker.get("/api/facilities").status_code == 401


def test_bug114_admin_password_reset_ends_existing_sessions(client, ctx, app):
    u = make_user("user", "West")
    login(client, u)
    assert client.get("/api/facilities").status_code == 200
    with app.test_client() as it_client:
        login(it_client, make_user("it_admin", "Global"))
        r = it_client.post(f"/api/auth/users/{u.id}/reset-password", json={"newPassword": "N3w!Password#2026"})
        assert r.status_code == 200, r.get_data(as_text=True)
    assert client.get("/api/facilities").status_code == 401


# ── Custom factor integrity (BUG-056 / 065 / 112) ─────────────────────────────────

def _cf(client, **kw):
    body = {"name": uniq("CF"), "co2_factor": 1.0, "unit": "kg/scf"}
    body.update(kw)
    return client.post("/api/custom-factors", json=body)


def test_bug112_all_zero_factor_rejected(client, ctx):
    login(client, make_user("admin", "Global"))
    assert _cf(client, co2_factor="", ch4_factor="", n2o_factor="").status_code == 400
    assert _cf(client, co2_factor=0, ch4_factor=0, n2o_factor=0).status_code == 400
    assert _cf(client, co2_factor=0, ch4_factor=0.5).status_code == 201


def test_bug065_duplicate_names_rejected_case_insensitive(client, ctx):
    login(client, make_user("admin", "Global"))
    name = uniq("Dup")
    assert _cf(client, name=name).status_code == 201
    assert _cf(client, name=name.upper()).status_code == 409
    other = _cf(client).get_json()["id"]
    assert client.put(f"/api/custom-factors/{other}", json={"name": name.lower()}).status_code == 409


def test_bug056_referenced_factor_cannot_be_deleted_and_can_be_archived(client, ctx):
    login(client, make_user("admin", "Global"))
    fid = _cf(client).get_json()["id"]
    f = make_facility(region="West")
    _db.session.add(Emission(facility_id=f.id, year=2024, month=1, process_type="combustion",
                             fuel_type=str(fid), custom_factor_id=fid, factor_source="custom", status="Verified"))
    _db.session.commit()
    r = client.delete(f"/api/custom-factors/{fid}")
    assert r.status_code == 409
    assert _db.session.get(CustomFactor, fid) is not None
    # legacy reference by id string in fuel_type only (no FK) is detected too
    fid_legacy = _cf(client).get_json()["id"]
    _db.session.add(Emission(facility_id=f.id, year=2024, month=2, process_type="combustion",
                             fuel_type=str(fid_legacy), factor_source="custom", status="Verified"))
    _db.session.commit()
    assert client.delete(f"/api/custom-factors/{fid_legacy}").status_code == 409
    # archive hides it from new entries but keeps the row and id
    assert client.post(f"/api/custom-factors/{fid}/archive").status_code == 200
    _db.session.expire_all()
    assert _db.session.get(CustomFactor, fid).is_archived
    assert fid not in [x["id"] for x in client.get("/api/custom-factors").get_json()]
    # an unreferenced factor can be deleted (nothing refers to its id)
    fid2 = _cf(client).get_json()["id"]
    assert client.delete(f"/api/custom-factors/{fid2}").status_code == 200
    assert _db.session.get(CustomFactor, fid2) is None
