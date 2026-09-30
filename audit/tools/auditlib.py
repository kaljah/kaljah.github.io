"""
Audit harness helpers. NOT application code.

Usage (from any cwd):
    import sys; sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/tools")
    from auditlib import make_db, api_client
    make_db("agentA")                     # copies the pristine snapshot -> audit/db/agentA.db (+ audit users)
    c = api_client("agentA", "admin")     # logged-in Flask test client bound to audit/db/agentA.db
    r = c.get("/api/dashboard/...")

IMPORTANT: api_client() sets DATABASE_URL before importing the Flask app, so only ONE db
name can be used per Python process. Never point anything at new/server/ghg_app.db.

Audit accounts (password for all: AuditPass!2026):
    audit_admin@audit.local      admin      location Global
    audit_superuser@audit.local  superuser  location West
    audit_user@audit.local       user       location West
    audit_itadmin@audit.local    it_admin   location Global
"""
import os
import shutil
import sqlite3
import sys

H2 = r"C:/Users/samsung/Desktop/H2"
SERVER = os.path.join(H2, "new", "server")
DB_DIR = os.path.join(H2, "audit", "db")
SNAPSHOT = os.path.join(DB_DIR, "snapshot_original.db")
PASSWORD = "AuditPass!2026"
ROLES = {
    "admin": ("audit_admin@audit.local", "Global"),
    "superuser": ("audit_superuser@audit.local", "West"),
    "user": ("audit_user@audit.local", "West"),
    "it_admin": ("audit_itadmin@audit.local", "Global"),
}


def db_path(name):
    return os.path.join(DB_DIR, f"{name}.db").replace("\\", "/")


def make_db(name, overwrite=False):
    """Create audit/db/<name>.db from the pristine snapshot and add audit users (raw SQL, werkzeug hash)."""
    path = db_path(name)
    if os.path.exists(path) and not overwrite:
        return path
    for ext in ("", "-wal", "-shm"):
        if os.path.exists(path + ext):
            os.remove(path + ext)
    shutil.copyfile(SNAPSHOT, path)
    from werkzeug.security import generate_password_hash

    con = sqlite3.connect(path)
    for role, (email, loc) in ROLES.items():
        con.execute("DELETE FROM users WHERE email=?", (email,))
        con.execute(
            "INSERT INTO users (fullName, orgName, password_hash, sector, email, role, status, location, department, jobTitle) "
            "VALUES (?,?,?,?,?,?,?,?,?,?)",
            (f"Audit {role}", "Audit Org", generate_password_hash(PASSWORD), "Oil & Gas", email, role, "active", loc, "Audit", "Auditor"),
        )
    con.commit()
    con.close()
    return path


_app = None


def get_app(name):
    """Import the real Flask app bound to audit/db/<name>.db (one db per process)."""
    global _app
    if _app is not None:
        return _app
    make_db(name)
    os.environ["DATABASE_URL"] = "sqlite:///" + db_path(name)
    os.environ.setdefault("FLASK_ENV", "development")
    os.environ["SEED_ADMIN"] = "false"
    if SERVER not in sys.path:
        sys.path.insert(0, SERVER)
    cwd = os.getcwd()
    os.chdir(SERVER)
    try:
        from app import app  # noqa
        from extensions import limiter
    finally:
        os.chdir(cwd)
    app.config["WTF_CSRF_ENABLED"] = False
    app.config["TESTING"] = True
    limiter.enabled = False
    _app = app
    return app


def api_client(name, role="admin"):
    app = get_app(name)
    c = app.test_client()
    email, _ = ROLES[role]
    r = c.post("/api/auth/login", json={"email": email, "password": PASSWORD})
    assert r.status_code == 200, (r.status_code, r.get_data(as_text=True)[:300])
    return c


def sql(name, query, params=()):
    """Read-only-ish direct SQL against an audit db (for DB-level reconciliation)."""
    con = sqlite3.connect(db_path(name))
    con.row_factory = sqlite3.Row
    try:
        rows = [dict(r) for r in con.execute(query, params).fetchall()]
        con.commit()
        return rows
    finally:
        con.close()
