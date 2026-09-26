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
