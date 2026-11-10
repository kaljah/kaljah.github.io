"""
Step 7 Regression Tests — Sandbox Reset, Setup, SQLite WAL & Write Serialization,
Login Rate Limiting, Short Session Timeouts, and 5-Concurrent-User Stability
=============================================================================
"""

from __future__ import annotations

import concurrent.futures
import os
import sqlite3
import subprocess
import sys
import time
import uuid
from datetime import timedelta
from pathlib import Path

from app import app
from config import Config
from extensions import db, limiter
from models import Facility, SystemSetting, User

REPO_ROOT = Path(__file__).resolve().parents[3]
SERVER_DIR = REPO_ROOT / "new" / "server"
GIT_BASH = Path(r"C:\Program Files\Git\bin\bash.exe")


def _make_user(role: str, suffix: str) -> tuple[User, str]:
    pw = f"Step7_{suffix}!9"
    u = User(
        email=f"step7_{suffix}_{uuid.uuid4().hex[:6]}@example.org",
        fullName=f"Step7 {suffix}",
        orgName="Demo Operator Co.",
        sector="Oil & Gas",
        role=role,
        location="Global" if role == "admin" else "Sector Alpha",
        status="active",
        tenant_id="default",
    )
    u.set_password(pw)
    db.session.add(u)
    db.session.flush()
    return u, pw


def test_sqlite_wal_busy_timeout_and_write_lock_service():
    """Verify SQLite WAL + busy_timeout pragmas and process-wide write serialization helper."""
    from services.sqlite_lock import is_sqlite_engine, sqlite_write_lock

    with app.app_context():
        assert is_sqlite_engine(db.engine) is True
        raw = db.engine.raw_connection()
        try:
            cur = raw.cursor()
            cur.execute("PRAGMA journal_mode")
            mode = str(cur.fetchone()[0]).lower()
            cur.execute("PRAGMA busy_timeout")
            busy_ms = int(cur.fetchone()[0])
            cur.close()
        finally:
            raw.close()

        assert mode == "wal", f"Expected SQLite WAL mode, got {mode!r}"
        assert busy_ms >= 30000, f"Expected busy_timeout >= 30000ms, got {busy_ms}"

        with sqlite_write_lock(db.engine), sqlite_write_lock(db.engine):  # re-entrant without deadlock
            assert is_sqlite_engine(db.engine) is True


def test_five_concurrent_users_no_database_is_locked_errors():
    """Simulate 5 concurrent users performing logins, facility/emission/scope2/scope3 writes & dashboard reads."""
    prev_limiter = limiter.enabled
    limiter.enabled = False
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False

    users: list[tuple[str, str, int]] = []
    with app.app_context():
        for i in range(5):
            u, pw = _make_user("admin", f"conc{i}")
            fac = Facility(
                name=f"Step7 Conc Facility {i}-{uuid.uuid4().hex[:5]}",
                location="Sector Alpha",
                region="Basin Alpha",
                division="Production",
                activity="EP",
                segment="Upstream",
                tenant_id="default",
            )
            db.session.add(fac)
            db.session.flush()
            users.append((u.email, pw, fac.id))
        db.session.commit()

    def _run_user_workflow(worker_idx: int):
        email, pw, fac_id = users[worker_idx]
        errors: list[str] = []
        statuses: list[int] = []
        with app.test_client() as client:
            r_login = client.post("/api/auth/login", json={"email": email, "password": pw})
            statuses.append(r_login.status_code)
            if r_login.status_code != 200:
                errors.append(f"user {worker_idx} login {r_login.status_code}: {r_login.get_data(as_text=True)}")
                return statuses, errors

            for step in range(4):
                r_s1 = client.post(
                    "/api/emissions",
                    json={
                        "year": 2025,
                        "month": ((worker_idx * 4 + step) % 12) + 1,
                        "facility_id": fac_id,
                        "process_type": "combustion",
                        "fuel": "Natural Gas",
                        "amount": 500 + worker_idx * 25 + step,
                        "unit": "m3",
                        "status": "Verified",
                        "equipment_id": f"S7-EQ-{worker_idx}-{step}-{uuid.uuid4().hex[:4]}",
                        "calc_inputs": {
                            "combustion": {
                                "fuel_gas_volume": 500 + worker_idx * 25 + step,
                                "fuel_type": "Natural Gas",
                            }
                        },
                    },
                )
                statuses.append(r_s1.status_code)
                if r_s1.status_code not in (200, 201):
                    errors.append(f"user {worker_idx} scope1 {r_s1.status_code}: {r_s1.get_data(as_text=True)}")

                r_s2 = client.post(
                    "/api/scope2",
                    json={
                        "year": 2025,
                        "month": ((worker_idx * 4 + step) % 12) + 1,
                        "facility_id": fac_id,
                        "source_type": "electricity",
                        "electricity_kwh": 2000 + worker_idx * 10 + step,
                        "grid_region": "US Average",
                        "status": "Verified",
                    },
                )
                statuses.append(r_s2.status_code)
                if r_s2.status_code not in (200, 201):
                    errors.append(f"user {worker_idx} scope2 {r_s2.status_code}: {r_s2.get_data(as_text=True)}")

                r_s3 = client.post(
                    "/api/scope3",
                    json={
                        "year": 2025,
                        "month": ((worker_idx * 4 + step) % 12) + 1,
                        "facility_id": fac_id,
                        "category": "1",
                        "sub_category": f"Step7 Conc Supply {worker_idx}-{step}",
                        "activity_data": 1000 + step,
                        "unit": "USD",
                        "emission_factor": 0.35,
                        "status": "Verified",
                    },
                )
                statuses.append(r_s3.status_code)
                if r_s3.status_code not in (200, 201):
                    errors.append(f"user {worker_idx} scope3 {r_s3.status_code}: {r_s3.get_data(as_text=True)}")

                r_dash = client.get("/api/dashboard/summary?year=2025")
                statuses.append(r_dash.status_code)
                if r_dash.status_code != 200:
                    errors.append(f"user {worker_idx} dash {r_dash.status_code}: {r_dash.get_data(as_text=True)}")

        return statuses, errors

    try:
        all_errors: list[str] = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
            futs = [pool.submit(_run_user_workflow, i) for i in range(5)]
            for fut in concurrent.futures.as_completed(futs):
                _, errs = fut.result()
                all_errors.extend(errs)
        assert not all_errors, f"5-user concurrency errors (database is locked etc.): {all_errors}"
    finally:
        limiter.enabled = prev_limiter


def test_default_login_rate_limiting_and_short_session_timeouts(monkeypatch):
    """Default rate limit blocks brute force at 6th attempt and session timeout defaults to <= 15 minutes."""
    monkeypatch.delenv("LOGIN_RATE_LIMIT", raising=False)
    monkeypatch.delenv("LOGIN_ACCOUNT_LIMIT", raising=False)
    monkeypatch.delenv("SESSION_LIFETIME_MINUTES", raising=False)

    from services.login_guard import get_login_account_limit, get_login_rate_limit
    from services.session_policy import (
        DEFAULT_IDLE_TIMEOUT_MINUTES,
        forget_cached_timeout,
        idle_timeout_minutes,
    )

    assert Config.PERMANENT_SESSION_LIFETIME <= timedelta(minutes=15), (
        f"Expected short default session lifetime <= 15m, got {Config.PERMANENT_SESSION_LIFETIME}"
    )
    assert DEFAULT_IDLE_TIMEOUT_MINUTES <= 15, (
        f"Expected default idle timeout <= 15m, got {DEFAULT_IDLE_TIMEOUT_MINUTES}"
    )
    assert get_login_account_limit() == "5 per 15 minutes"
    assert int(get_login_rate_limit().split()[0]) <= 15

    # Verify DB fallback when SystemSetting row is absent returns <= 15 and /api/auth/sessions/policy reflects 5/15
    with app.app_context():
        prev_row = db.session.get(SystemSetting, "session_timeout_minutes")
        prev_val = prev_row.value if prev_row else None
        if prev_row is not None:
            db.session.delete(prev_row)
            db.session.commit()
        forget_cached_timeout()
        it_user, _it_pw = _make_user("it_admin", "policy")
        db.session.commit()
        assert idle_timeout_minutes() <= 15

    try:
        # Check sessions/policy output without limiter
        with app.test_client() as c:
            with c.session_transaction() as sess:
                sess["user_id"] = it_user.id
                sess["role"] = it_user.role
                sess["sv"] = int(it_user.session_version or 0)
                sess["last_seen"] = time.time()
            pol = c.get("/api/auth/sessions/policy")
            assert pol.status_code == 200
            pdata = pol.get_json()
            assert pdata["idle_timeout_minutes"] <= 15
            assert pdata["max_failed_logins"] == 5

        # Verify default rate limiter throttles on 6th attempt for one account
        app.config["RATELIMIT_ENABLED"] = True
        prev_enabled = limiter.enabled
        limiter.enabled = True
        try:
            with app.test_client() as c:
                target_email = f"brute_{uuid.uuid4().hex[:8]}@example.org"
                codes = []
                for _ in range(6):
                    resp = c.post(
                        "/api/auth/login",
                        json={"email": target_email, "password": "WrongPassword123!"},
                    )
                    codes.append(resp.status_code)
                assert codes[:5] == [401, 401, 401, 401, 401]
                assert codes[5] == 429, f"Expected HTTP 429 on 6th failed attempt, got {codes}"
        finally:
            limiter.enabled = prev_enabled
    finally:
        with app.app_context():
            if prev_val is not None:
                row = db.session.get(SystemSetting, "session_timeout_minutes")
                if row is None:
                    db.session.add(SystemSetting(key="session_timeout_minutes", value=prev_val))
                else:
                    row.value = prev_val
                db.session.commit()
            forget_cached_timeout()


def test_setup_bat_and_reset_sandbox_scripts_work(tmp_path: Path):
    """Verify new/setup.bat initializes & seeds + prints credentials, and reset_sandbox.sh/.bat restore & clean."""
    reset_sh = REPO_ROOT / "reset_sandbox.sh"
    reset_bat = REPO_ROOT / "reset_sandbox.bat"
    setup_bat = REPO_ROOT / "new" / "setup.bat"

    assert reset_sh.exists(), "reset_sandbox.sh must exist at repository root"
    assert reset_bat.exists(), "reset_sandbox.bat must exist at repository root"
    assert setup_bat.exists(), "new/setup.bat must exist"

    setup_text = setup_bat.read_text(encoding="utf-8", errors="ignore")
    assert "seed_demo.py" in setup_text
    assert "db upgrade" in setup_text

    if GIT_BASH.exists():
        syntax = subprocess.run(
            [str(GIT_BASH), "-n", str(reset_sh)],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            check=False,
        )
        assert syntax.returncode == 0, f"reset_sandbox.sh bash syntax error: {syntax.stderr}"

    # Create isolated template DB + dirty live DB + fake upload/cache artifacts, then run reset_sandbox.bat
    sandbox_server = tmp_path / "sandbox_server"
    db_path = sandbox_server / "ghg_app.db"
    tpl_path = sandbox_server / "instance" / "demo_template.db"
    chart_cache = sandbox_server / "instance" / "chart_cache"
    master_jobs = sandbox_server / "instance" / "master_report_jobs"
    upload_jobs = sandbox_server / "upload_jobs"
    uploads_dir = sandbox_server / "uploads"
    reports_dir = sandbox_server / "reports"

    for d in (chart_cache, master_jobs, upload_jobs, uploads_dir, reports_dir):
        d.mkdir(parents=True, exist_ok=True)

    # Generate a fast valid template DB with seed_demo.py subprocess
    env = os.environ.copy()
    env["PYTHONEXE"] = sys.executable
    env["GHG_DB_PATH"] = str(db_path)
    env["GHG_TEMPLATE_PATH"] = str(tpl_path)
    env["GHG_SANDBOX_SERVER_DIR"] = str(sandbox_server)
    env["GHG_NO_PAUSE"] = "1"

    seed_proc = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "seed_demo.py"),
            "--recreate",
            "--reset-passwords",
            "--db",
            str(db_path),
            "--template",
            str(tpl_path),
        ],
        cwd=str(REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    assert seed_proc.returncode == 0, f"seed_demo failed: {seed_proc.stderr}\n{seed_proc.stdout}"
    assert "DEMO USER CREDENTIALS" in seed_proc.stdout
    assert "demo.admin@example.org" in seed_proc.stdout
    assert tpl_path.exists()

    # Mutate live DB to simulate user modifications + leave caches/uploads behind
    conn = sqlite3.connect(str(db_path))
    conn.execute("DELETE FROM facilities WHERE code = 'FAC-C3'")
    conn.commit()
    conn.close()

    (db_path.parent / "ghg_app.db-wal").write_bytes(b"stale-wal")
    (db_path.parent / "ghg_app.db-shm").write_bytes(b"stale-shm")
    stale_files = [
        chart_cache / "stale_chart.png",
        master_jobs / "stale_job.pdf",
        upload_jobs / "stale_upload.json",
        uploads_dir / "temp.csv",
    ]
    for sf in stale_files:
        sf.write_text("stale", encoding="utf-8")
    preserved_report = reports_dir / "secrets_scan_report.json"
    preserved_report.write_text('{"status":"PASS_CLEAN"}', encoding="utf-8")

    proc = subprocess.run(
        ["cmd", "/c", str(reset_bat)],
        cwd=str(REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    assert proc.returncode == 0, f"reset_sandbox.bat failed: {proc.stderr}\n{proc.stdout}"

    # Caches/uploads and wal/shm cleared; preserved report untouched; deleted facility restored from template!
    for sf in stale_files:
        assert not sf.exists(), f"Stale artifact was not cleared by reset_sandbox.bat: {sf}"
    assert not (db_path.parent / "ghg_app.db-wal").exists()
    assert not (db_path.parent / "ghg_app.db-shm").exists()
    assert preserved_report.exists()

    conn2 = sqlite3.connect(str(db_path))
    row = conn2.execute("SELECT name FROM facilities WHERE code = 'FAC-C3'").fetchone()
    conn2.close()
    assert row is not None and row[0] == "Facility C-3"

    # Also verify setup.bat --db-only --no-pause initializes DB, seeds it, creates template, and prints credentials
    setup_sandbox = tmp_path / "setup_sandbox"
    setup_db = setup_sandbox / "ghg_app.db"
    setup_tpl = setup_sandbox / "instance" / "demo_template.db"
    setup_env = os.environ.copy()
    setup_env["PYTHONEXE"] = sys.executable
    setup_env["GHG_SANDBOX_SERVER_DIR"] = str(setup_sandbox)
    setup_env["GHG_DB_PATH"] = str(setup_db)
    setup_env["GHG_TEMPLATE_PATH"] = str(setup_tpl)
    setup_env["GHG_NO_PAUSE"] = "1"
    setup_proc = subprocess.run(
        ["cmd", "/c", str(setup_bat), "--db-only", "--no-pause"],
        cwd=str(REPO_ROOT),
        env=setup_env,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    assert setup_proc.returncode == 0, f"setup.bat failed: {setup_proc.stderr}\n{setup_proc.stdout}"
    assert "DEMO USER CREDENTIALS" in setup_proc.stdout
    assert "demo.admin@example.org" in setup_proc.stdout
    assert setup_db.exists() and setup_tpl.exists()

    # Also execute reset_sandbox.sh end-to-end when Git Bash is present
    if GIT_BASH.exists():
        (chart_cache / "sh_stale.png").write_text("stale", encoding="utf-8")
        conn3 = sqlite3.connect(str(db_path))
        conn3.execute("DELETE FROM facilities WHERE code = 'FAC-C3'")
        conn3.commit()
        conn3.close()
        sh_env = env.copy()
        sh_env["PYTHONEXE"] = Path(sys.executable).as_posix()
        sh_env["GHG_DB_PATH"] = db_path.as_posix()
        sh_env["GHG_TEMPLATE_PATH"] = tpl_path.as_posix()
        sh_env["GHG_SANDBOX_SERVER_DIR"] = sandbox_server.as_posix()
        sh_proc = subprocess.run(
            [str(GIT_BASH), str(reset_sh.as_posix())],
            cwd=str(REPO_ROOT),
            env=sh_env,
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
        assert sh_proc.returncode == 0, f"reset_sandbox.sh failed: {sh_proc.stderr}\n{sh_proc.stdout}"
        assert not (chart_cache / "sh_stale.png").exists()
        conn4 = sqlite3.connect(str(db_path))
        row4 = conn4.execute("SELECT name FROM facilities WHERE code = 'FAC-C3'").fetchone()
        conn4.close()
        assert row4 is not None and row4[0] == "Facility C-3"


def test_default_idle_timeout_rejects_after_15_minutes_and_commit_retry(tmp_path: Path):
    """Default 15-minute idle policy expires stale sessions (401) and commit_with_retry survives busy errors."""
    from services.session_policy import forget_cached_timeout
    from services.sqlite_lock import commit_with_retry
    from sqlalchemy.exc import OperationalError

    with app.app_context():
        prev_row = db.session.get(SystemSetting, "session_timeout_minutes")
        prev_val = prev_row.value if prev_row else None
        if prev_row is not None:
            db.session.delete(prev_row)
            db.session.commit()
        forget_cached_timeout()
        u, _ = _make_user("admin", "idle15")
        db.session.commit()

    try:
        with app.test_client() as c:
            with c.session_transaction() as sess:
                sess["user_id"] = u.id
                sess["role"] = u.role
                sess["sv"] = int(u.session_version or 0)
                sess["last_seen"] = time.time() - 16 * 60
            resp = c.get("/api/auth/me")
            assert resp.status_code == 401
    finally:
        with app.app_context():
            if prev_val is not None:
                row = db.session.get(SystemSetting, "session_timeout_minutes")
                if row is None:
                    db.session.add(SystemSetting(key="session_timeout_minutes", value=prev_val))
                else:
                    row.value = prev_val
                db.session.commit()
            forget_cached_timeout()

    # Verify commit_with_retry recovers from transient SQLite locked error
    class _FakeSession:
        def __init__(self):
            self.calls = 0

        def get_bind(self):
            return db.engine

        def commit(self):
            self.calls += 1
            if self.calls < 3:
                raise OperationalError("COMMIT", {}, Exception("database is locked"))

    fake = _FakeSession()
    with app.app_context():
        commit_with_retry(fake, max_attempts=4, initial_delay=0.005)
    assert fake.calls == 3
