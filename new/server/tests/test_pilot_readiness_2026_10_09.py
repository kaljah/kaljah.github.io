"""Pilot readiness check 2026-10-09: regressions for the findings F1-F14 of the pre-pilot bug hunt
(run against a production-mode install on PostgreSQL with four gunicorn workers)."""
import io
import os
import subprocess
import sys

import pytest
from sqlalchemy import text

from background_processor import normalize_number_cell
from extensions import db, limiter
from models import ActivityLog, Emission, User
from services.audit_chain import GENESIS_HASH, compute_entry_hash
from tests.audit_helpers import login, make_facility, make_user, uniq, upload


@pytest.fixture
def ctx(app):
    with app.app_context():
        yield


# ── F11: duplicate detection must match fuels written by an alias ────────────────────────────

def test_f11_reupload_with_fuel_alias_is_a_duplicate_not_a_copy(client, ctx):
    fac = make_facility(region=uniq("PilotRegion"))
    login(client, make_user("admin", "Global"))
    csv = ("date,facility_name,process_type,fuel,quantity,unit,tier,equipment_id\n"
           f"2025-05,{fac.name},combustion,Diesel,10000,liters,1,EQ-2\n")
    _, _, first = upload(client, csv, "1", overwrite=False)
    assert first["status"] == "completed", first
    stored = Emission.query.filter_by(facility_id=fac.id, year=2025, month=5).all()
    assert len(stored) == 1
    assert stored[0].fuel_type != "Diesel"  # saved under the catalog name, the case that slipped through

    _, _, second = upload(client, csv, "1", overwrite=False)
    assert second["status"] == "completed", second
    assert Emission.query.filter_by(facility_id=fac.id, year=2025, month=5).count() == 1
    assert "Duplicate record" in str(second.get("skipped_groups") or second.get("errors"))


def test_f11_reupload_with_fuel_alias_and_overwrite_updates_in_place(client, ctx):
    fac = make_facility(region=uniq("PilotRegion"))
    login(client, make_user("admin", "Global"))
    row = "date,facility_name,process_type,fuel,quantity,unit,tier,equipment_id\n2025-06,{n},combustion,Diesel,{q},liters,1,EQ-2\n"
    upload(client, row.format(n=fac.name, q=10000), "1", overwrite=False)
    _, _, st = upload(client, row.format(n=fac.name, q=12000), "1", overwrite=True)
    assert st["status"] == "completed", st
    rows = Emission.query.filter_by(facility_id=fac.id, year=2025, month=6).all()
    assert len(rows) == 1 and rows[0].quantity == 12000


# ── F6: numbers are read by the decimal format chosen for the file, never guessed ─────────────


@pytest.mark.parametrize("cell, mark, expected", [
    ("1,5", "comma", "1.5"), ("1,000", "comma", "1.000"), ("1.000", "comma", "1000"), ("1 234,5", "comma", "1234.5"),
    ("1.234,5", "comma", "1234.5"), ("-0,25", "comma", "-0.25"), ("12", "comma", "12"),
    ("1.5", "point", "1.5"), ("1,000", "point", "1000"), ("1,234.5", "point", "1234.5"), ("1 234.5", "point", "1234.5"),
    ("0.125", "point", "0.125"), ("12", "point", "12"),
    ("1,5", None, "1,5"), ("1.5", None, "1.5"), ("12,345.6", None, "12,345.6"), ("0.125", None, "0.125"),
    ("14.696", None, "14.696"),
    ("2025-05", "comma", "2025-05"), ("Hassi Messaoud, Nord", "point", "Hassi Messaoud, Nord"), ("5%", "comma", "5%"),
])
def test_f6_number_cells_follow_the_chosen_format(cell, mark, expected):
    assert normalize_number_cell(cell, mark) == expected


@pytest.mark.parametrize("cell, mark", [
    ("1.5", "comma"), ("1,234.5", "comma"), ("1,5", "point"), ("1.234,5", "point"),
    ("1,000", None), ("12,500", None), ("250,000", None),
])
def test_f6_numbers_that_do_not_fit_are_refused_not_guessed(cell, mark):
    out = normalize_number_cell(cell, mark)
    assert out.startswith(cell) and "[" in out  # kept as unreadable text with the reason


def _s1_row(fac, qty, eq="EQ-1"):
    return ("date,facility_name,process_type,fuel,quantity,unit,tier,equipment_id\n"
            f'2025-05,{fac.name},combustion,Natural Gas,"{qty}",MMBtu,1,{eq}\n')


@pytest.mark.parametrize("mark, qty, expected", [("comma", "1,000", 1.0), ("point", "1,000", 1000.0),
                                                 ("comma", "1.000", 1000.0), ("comma", "2 350,5", 2350.5)])
def test_f6_upload_reads_the_quantity_by_the_chosen_format(client, ctx, mark, qty, expected):
    fac = make_facility(region=uniq("PilotRegion"))
    login(client, make_user("admin", "Global"))
    _, _, st = upload(client, _s1_row(fac, qty), "1", decimal_mark=mark)
    assert st["status"] == "completed", st
    rec = Emission.query.filter_by(facility_id=fac.id, year=2025, month=5).one()
    assert rec.quantity == pytest.approx(expected)


def test_f6_upload_without_a_choice_refuses_ambiguous_numbers(client, ctx):
    fac = make_facility(region=uniq("PilotRegion"))
    login(client, make_user("admin", "Global"))
    _, _, st = upload(client, _s1_row(fac, "1,000"), "1")
    assert st["status"] == "completed", st
    assert Emission.query.filter_by(facility_id=fac.id).count() == 0
    assert "ambiguous" in str(st.get("skipped_groups") or st.get("skipped"))


def test_f6_unknown_decimal_mark_is_rejected(client, ctx):
    login(client, make_user("admin", "Global"))
    r = client.post("/api/emissions/upload/check", data={"file": (io.BytesIO(b"a,b\n1,2\n"), "f.csv"),
                                                         "scope": "1", "decimal_mark": "semicolon"},
                    content_type="multipart/form-data")
    assert r.status_code == 400


# ── F12: the audit log is sealed when written and verification reports changes ─────────────────


@pytest.fixture
def sealed_log(ctx):
    """Earlier test modules delete log rows directly (SQLite has no append-only trigger), which breaks
    the shared test database's chain. Re-seal it so each F12 test starts from an intact chain."""
    prev = GENESIS_HASH
    for row in ActivityLog.query.order_by(ActivityLog.id).all():
        row.prev_hash, row.entry_hash = prev, compute_entry_hash(row, prev)
        prev = row.entry_hash
    db.session.commit()


def _logs(n, admin, tag):
    rows = [ActivityLog(action="TEST", record_id=f"{tag}-{i}", user_id=admin.id, user_name="Auditor",
                        entity="Emission", details=f"{tag} entry {i}") for i in range(n)]
    db.session.add_all(rows)
    db.session.commit()
    return [r.id for r in rows]


def _verify(client):
    r = client.get("/api/audit/verify-chain")
    assert r.status_code == 200, r.get_data(as_text=True)
    return r.get_json()


def test_f12_entries_are_sealed_and_linked_when_written(client, ctx, sealed_log):
    admin = make_user("admin", "Global")
    ids = _logs(3, admin, "seal")
    rows = [db.session.get(ActivityLog, i) for i in ids]
    for prev, row in zip(rows, rows[1:]):
        assert row.prev_hash == prev.entry_hash
    for row in rows:
        assert row.entry_hash == compute_entry_hash(row, row.prev_hash)
    first = ActivityLog.query.order_by(ActivityLog.id).first()
    assert first.prev_hash == GENESIS_HASH


def test_f12_edited_details_are_reported(client, ctx, sealed_log):
    admin = make_user("admin", "Global")
    login(client, admin)
    ids = _logs(3, admin, "edit")
    assert _verify(client)["status"] == "verified"
    # an edit made directly in the database (PostgreSQL refuses it; SQLite has no trigger)
    db.session.execute(text("UPDATE activity_log SET details = 'nothing to see' WHERE id = :i"), {"i": ids[1]})
    db.session.commit()
    body = _verify(client)
    assert body["status"] == "tampered" and body["is_intact"] is False
    assert {"id": ids[1], "problem": "content_changed"}.items() <= body["issues"][0].items()
    db.session.execute(text("UPDATE activity_log SET details = 'edit entry 1' WHERE id = :i"), {"i": ids[1]})
    db.session.commit()
    assert _verify(client)["status"] == "verified"


def test_f12_deleted_entry_breaks_the_chain(client, ctx, sealed_log):
    admin = make_user("admin", "Global")
    login(client, admin)
    ids = _logs(3, admin, "del")
    db.session.execute(text("DELETE FROM activity_log WHERE id = :i"), {"i": ids[1]})
    db.session.commit()
    body = _verify(client)
    assert body["status"] == "tampered"
    assert any(i["id"] == ids[2] and i["problem"] == "chain_break" for i in body["issues"])
    # repair for the following tests: re-link the entry after the gap (only a test may do this)
    row = db.session.get(ActivityLog, ids[2])
    row.prev_hash = db.session.get(ActivityLog, ids[0]).entry_hash
    row.entry_hash = compute_entry_hash(row, row.prev_hash)
    db.session.commit()
    nxt = ActivityLog.query.filter(ActivityLog.id > ids[2]).order_by(ActivityLog.id).all()
    prev = row.entry_hash
    for r in nxt:
        r.prev_hash, r.entry_hash = prev, compute_entry_hash(r, prev)
        prev = r.entry_hash
    db.session.commit()
    assert _verify(client)["status"] == "verified"


def test_f12_user_deletion_keeps_the_chain_intact(client, ctx, sealed_log):
    admin = make_user("admin", "Global")
    it_admin = make_user("it_admin", "Global")
    leaver = make_user("user", uniq("PilotRegion"))
    _logs(2, leaver, "leaver")
    login(client, it_admin)
    assert client.delete(f"/api/auth/users/{leaver.id}").status_code == 200
    assert db.session.get(User, leaver.id) is None
    login(client, admin)
    assert _verify(client)["status"] == "verified"


def test_f12_removing_the_newest_entries_is_caught_by_a_saved_checkpoint(client, ctx, sealed_log):
    admin = make_user("admin", "Global")
    login(client, admin)
    ids = _logs(2, admin, "tail")
    saved = _verify(client)
    db.session.execute(text("DELETE FROM activity_log WHERE id = :i"), {"i": ids[-1]})
    db.session.commit()
    now = _verify(client)
    assert now["status"] == "verified"  # a shorter chain is intact on its own...
    check = client.post("/api/audit/verify-checkpoint", json={
        "chain_head_hash": now["chain_head_hash"], "total_records": saved["total_records"],
        "checkpoint_hmac": saved["checkpoint_hmac"]}).get_json()
    assert check["valid"] is False  # ...but no longer matches the checkpoint saved before


# ── F3 / F4: sign-in limits count failures only; per-account lockout ─────────────────────────────


@pytest.fixture
def live_limiter(app):
    prev = limiter.enabled
    limiter.enabled = True
    limiter.reset()
    yield
    limiter.reset()
    limiter.enabled = prev


def _sign_in(client, email, password, ip="10.0.0.1", xff=None):
    headers = {"X-Forwarded-For": xff} if xff else {}
    return client.post("/api/auth/login", json={"email": email, "password": password},
                       environ_base={"REMOTE_ADDR": ip}, headers=headers)


def test_f3_successful_sign_ins_do_not_use_up_the_limit(client, ctx, live_limiter):
    users = [make_user("user", uniq("PilotRegion")) for _ in range(3)]
    codes = [_sign_in(client, users[i % 3].email, "AuditPass!2026").status_code for i in range(30)]
    assert codes == [200] * 30  # one shared address (proxy, Citrix): 30 sign-ins at shift start


def test_f4_account_is_locked_after_ten_failures_from_any_address(client, ctx, live_limiter):
    victim = make_user("user", uniq("PilotRegion"))
    for i in range(10):
        assert _sign_in(client, victim.email, "wrong", ip=f"10.1.0.{i}").status_code == 401
    locked = _sign_in(client, victim.email, "AuditPass!2026", ip="10.1.1.1")
    assert locked.status_code == 429
    assert "failed sign-ins for this account" in locked.get_data(as_text=True)
    other = make_user("user", uniq("PilotRegion"))
    assert _sign_in(client, other.email, "AuditPass!2026", ip="10.1.1.1").status_code == 200


def test_f4_forged_forwarded_for_is_ignored_without_trusted_proxies(client, ctx, live_limiter):
    victim = make_user("user", uniq("PilotRegion"))
    codes = [_sign_in(client, victim.email, "wrong", xff=f"192.0.2.{i}").status_code for i in range(12)]
    assert codes[:10] == [401] * 10 and set(codes[10:]) == {429}


def test_f4_failed_sign_in_is_in_the_audit_log(client, ctx):
    victim = make_user("user", uniq("PilotRegion"))
    _sign_in(client, victim.email, "wrong")
    entry = ActivityLog.query.filter_by(action="FAILED_LOGIN").order_by(ActivityLog.id.desc()).first()
    assert entry is not None and victim.email in entry.details


# ── F9 / F10: restore stops on the first error; backup --output-dir ─────────────────────────────


def test_f9_postgres_restore_stops_at_the_first_error_and_reports_it(tmp_path, monkeypatch):
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "scripts"))
    import restore

    dump = tmp_path / "b.sql"
    dump.write_text("SELECT 1;\n")
    seen = {}

    class FakePsql:
        def __init__(self, cmd, **kw):
            seen["cmd"] = cmd
            self.returncode = 3  # what psql returns when ON_ERROR_STOP stops it

        def communicate(self, input=None):
            return b"", b"ERROR:  relation does not exist"

    monkeypatch.setattr(restore.subprocess, "Popen", FakePsql)
    assert restore.restore_postgres(str(dump), "postgresql://u:p@db/x") is False
    assert "ON_ERROR_STOP=1" in seen["cmd"] and "--single-transaction" in seen["cmd"]


def test_f10_sqlite_backup_writes_to_output_dir(tmp_path):
    import sqlite3

    src = tmp_path / "src.db"
    sqlite3.connect(src).execute("CREATE TABLE t (x INTEGER)").connection.commit()
    out = tmp_path / "out"
    script = os.path.join(os.path.dirname(os.path.dirname(__file__)), "scripts", "backup.py")
    env = {k: v for k, v in os.environ.items() if k not in ("DATABASE_URL", "DB_TYPE", "BACKUP_DIR")}
    p = subprocess.run([sys.executable, script, str(src), "--output-dir", str(out)], env=env,
                       capture_output=True, text=True, timeout=60)
    assert p.returncode == 0, p.stdout + p.stderr
    assert any(f.startswith("ghg_sqlite_") for f in os.listdir(out))


# ── F1 / F2: account seeding ─────────────────────────────────────────────────────────────────────

def test_f1_seed_script_creates_no_it_support_account_unless_configured(ctx, monkeypatch):
    import seed_admin

    monkeypatch.setenv("ADMIN_EMAIL", "seed-admin@pilot.test")
    monkeypatch.setenv("ADMIN_PASSWORD", "Seed!Admin#2026xyz")
    monkeypatch.setenv("IT_ADMIN_EMAIL", "seed-itadmin@pilot.test")
    monkeypatch.setenv("IT_ADMIN_PASSWORD", "Seed!ItAdmin#2026xyz")
    monkeypatch.delenv("IT_EMAIL", raising=False)
    monkeypatch.delenv("IT_PASSWORD", raising=False)
    seed_admin.seed_admin()
    assert User.query.filter_by(email="it@ghg.com").first() is None
    assert User.query.filter_by(role="it").filter(User.email.like("%@ghg.com")).count() == 0

    monkeypatch.setenv("IT_EMAIL", "seed-it@pilot.test")
    monkeypatch.setenv("IT_PASSWORD", "Seed!ItSupport#2026x")
    seed_admin.seed_admin()
    it = User.query.filter_by(email="seed-it@pilot.test").first()
    assert it is not None and it.role == "it" and it.check_password("Seed!ItSupport#2026x")


def test_f2_restart_does_not_re_enable_a_disabled_seeded_account(ctx, monkeypatch):
    from app import ensure_admin_seeded

    admin = make_user("admin", "Global", email="disabled-admin@pilot.test")
    admin.status = "disabled"
    db.session.commit()
    monkeypatch.setenv("SEED_ADMIN", "true")
    monkeypatch.setenv("ADMIN_EMAIL", admin.email)
    monkeypatch.setenv("ADMIN_PASSWORD", "Seed!Admin#2026xyz")
    ensure_admin_seeded()
    db.session.expire_all()
    assert db.session.get(User, admin.id).status == "disabled"


# ── F7: batch decisions explain the records they skip ────────────────────────────────────────────

def test_f7_batch_approve_explains_skipped_records(client, ctx):
    fac = make_facility(region=uniq("PilotRegion"))
    admin = make_user("admin", "Global")
    other = make_user("admin", "Global")
    own = Emission(facility_id=fac.id, year=2025, month=3, process_type="combustion", fuel_type="Natural Gas",
                   quantity=1, unit="MMBtu", co2e_total=0.05, status="Pending", created_by=admin.id)
    theirs = Emission(facility_id=fac.id, year=2025, month=4, process_type="combustion", fuel_type="Natural Gas",
                      quantity=1, unit="MMBtu", co2e_total=0.05, status="Pending", created_by=other.id)
    done = Emission(facility_id=fac.id, year=2025, month=5, process_type="combustion", fuel_type="Natural Gas",
                    quantity=1, unit="MMBtu", co2e_total=0.05, status="Verified", created_by=other.id)
    db.session.add_all([own, theirs, done])
    db.session.commit()
    login(client, admin)
    body = client.post("/api/emissions/approve/batch", json={"scope": "1", "ids": [own.id, theirs.id, done.id, 999999]}).get_json()
    assert body["approved_ids"] == [theirs.id]
    reasons = {s["id"]: s["reason"] for s in body["skipped"]}
    assert "created or last changed" in reasons[own.id]
    assert reasons[done.id] == "Already Verified"
    assert reasons[999999] == "Record not found"
    assert body["skipped_count"] == 3


# ── F13: bad input is a 400 / 404, never a 500 ───────────────────────────────────────────────────

@pytest.mark.parametrize("path, body", [
    ("/api/base-years", None), ("/api/data/cbam-exports", None), ("/api/reports/generate", None),
    ("/api/emissions/approve/batch", {"scope": "1", "ids": [None, "x", 10**20]}),
    ("/api/emissions/reject/batch", {"scope": "1", "ids": [None, "x", 10**20]}),
    ("/api/reporting-metadata", {"facility_id": [1], "year": {"a": 1}}),
    ("/api/sources", {"facility_id": 999999, "name": "x"}),
    ("/api/mitigation", {"facility_id": 999999, "name": "x", "year": 2025}),
    ("/api/data/ogmp/level-upgrade", {"facility_id": 999999, "old_level": 2, "new_level": 3, "year": 2025}),
])
def test_f13_bad_input_is_a_client_error(client, ctx, path, body):
    login(client, make_user("admin", "Global"))
    r = client.post(path, json=body) if body is not None else client.post(path, data="", content_type="text/plain")
    assert r.status_code < 500, (r.status_code, r.get_data()[:200])  # a 4xx, or a default result


def test_f13_reporting_metadata_get_with_a_bad_year_is_a_400(client, ctx):
    login(client, make_user("admin", "Global"))
    assert client.get("/api/reporting-metadata?year=abc").status_code == 400


# ── F14: same-site session cookie, no external sources in the CSP ────────────────────────────────

def test_f14_session_cookie_is_lax_and_csp_has_no_external_sources(client, ctx):
    user = make_user("user", uniq("PilotRegion"))
    r = login(client, user)
    assert "SameSite=Lax" in r.headers.get("Set-Cookie", "")
    csp = client.get("/api/health").headers["Content-Security-Policy"]
    assert "googleapis" not in csp and "gstatic" not in csp and "https:" not in csp


def test_f5_map_config_has_no_tile_server_unless_configured(client, ctx, monkeypatch):
    login(client, make_user("user", uniq("PilotRegion")))
    monkeypatch.delenv("MAP_TILE_URL", raising=False)
    assert client.get("/api/map-config").get_json()["tile_url"] is None
    monkeypatch.setenv("MAP_TILE_URL", "https://tiles.example.internal/{z}/{x}/{y}.png")
    assert client.get("/api/map-config").get_json()["tile_url"].startswith("https://tiles.example.internal/")


@pytest.mark.parametrize("query, status", [
    ("year=abc", 400), ("year=99999", 400), ("month=13", 400), ("facility_id=x", 422), ("facilityId=-1", 422),
    ("activity=%00", 400), ("year=all", 200), ("year=2025", 200), ("facility_id=", 200), ("month=all", 200),
])
def test_f13_malformed_filter_parameters_are_refused_centrally(client, ctx, query, status):
    login(client, make_user("admin", "Global"))
    assert client.get(f"/api/dashboard/summary?{query}").status_code == status


def test_f13_nul_character_in_json_is_refused(client, ctx):
    login(client, make_user("admin", "Global"))
    assert client.post("/api/sources", json={"facility_id": 1, "name": "a\x00b"}).status_code == 400


def test_f13_unknown_scope_in_emission_list_is_a_400(client, ctx):
    login(client, make_user("admin", "Global"))
    assert client.get("/api/emissions/?scope=zz").status_code == 400
