#!/usr/bin/env python3
"""
Enterprise Database Restore & Verification Script for GHG Accounting Platform.

Supports:
- PostgreSQL restore from .sql.gz or .sql snapshot via psql.
- SQLite sandbox integrity verification & live restore via sqlite3.backup().
- Verification of schema table count and Alembic migration head.
"""
import os
import sys
import gzip
import shutil
import sqlite3
import subprocess
import tempfile
from dotenv import load_dotenv

load_dotenv()


def _unpacked(backup_file, workdir):
    """The backup as a plain SQLite file (a .gz is decompressed into workdir)."""
    if not backup_file.endswith(".gz"):
        return backup_file
    path = os.path.join(workdir, "unpacked.db")
    print(f"[INFO] Decompressing {backup_file}...")
    with gzip.open(backup_file, "rb") as f_in, open(path, "wb") as f_out:
        shutil.copyfileobj(f_in, f_out)
    return path


def verify_sqlite_backup(backup_file, workdir=None):
    """Restore the backup into a scratch database and check it. Returns (ok, alembic_revision).

    Audit 2026-10-14 BUG-0031: a failed integrity check counts as a failure (it was printed and
    ignored), a missing or unreadable file is reported instead of a traceback, and the connections are
    closed whatever happens (the scratch file is in a temporary directory, not the current one)."""
    if not os.path.exists(backup_file):
        print(f"[ERROR] Backup file does not exist: {backup_file}")
        return False, None

    own_dir = workdir is None
    workdir = workdir or tempfile.mkdtemp(prefix="ghg_restore_")
    src = dst = None
    try:
        source = _unpacked(backup_file, workdir)
        sandbox_file = os.path.join(workdir, "sandbox_restore.db")
        print(f"[INFO] Restoring {source} into a scratch database...")
        src = sqlite3.connect(source)
        dst = sqlite3.connect(sandbox_file)
        src.backup(dst)

        cur = dst.cursor()
        tables = [t[0] for t in cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
        print(f"[INFO] Verified {len(tables)} tables in restored database.")

        integrity = cur.execute("PRAGMA integrity_check;").fetchall()
        print(f"[INFO] PRAGMA integrity_check: {integrity}")
        if integrity != [("ok",)]:
            print("[ERROR] The backup failed the SQLite integrity check.")
            return False, None

        alembic_head = None
        if "alembic_version" in tables:
            row = cur.execute("SELECT version_num FROM alembic_version").fetchone()
            if row:
                alembic_head = row[0]
                print(f"[INFO] Restored Alembic revision: {alembic_head}")
        return True, alembic_head
    except sqlite3.DatabaseError as exc:
        print(f"[ERROR] The backup is not a readable SQLite database: {exc}")
        return False, None
    finally:
        for conn in (src, dst):
            if conn is not None:
                conn.close()
        if own_dir:
            shutil.rmtree(workdir, ignore_errors=True)


def sqlite_target():
    """The live SQLite file: DATABASE_URL when it names one, else ghg_app.db next to the server."""
    url = os.environ.get("DATABASE_URL", "")
    if url.startswith("sqlite:///"):
        return url[len("sqlite:///"):]
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ghg_app.db")


def restore_sqlite(backup_file, target_db):
    """Copy the backup into the live database with the SQLite backup API. A plain file copy left the live
    -wal file in place, and SQLite then replayed it over the restored data (BUG-0031). The copy runs
    through a connection to the target, so its WAL is part of the restore, then it is checkpointed."""
    workdir = tempfile.mkdtemp(prefix="ghg_restore_")
    src = dst = None
    try:
        src = sqlite3.connect(_unpacked(backup_file, workdir))
        dst = sqlite3.connect(target_db, timeout=5)
        src.backup(dst)
        dst.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        if dst.execute("PRAGMA integrity_check").fetchall() != [("ok",)]:
            print("[ERROR] The restored database failed the integrity check.")
            return False
        return True
    except sqlite3.OperationalError as exc:
        print(f"[ERROR] Could not write {target_db} ({exc}). Stop the application server and try again.")
        return False
    finally:
        for conn in (src, dst):
            if conn is not None:
                conn.close()
        shutil.rmtree(workdir, ignore_errors=True)


def restore_postgres(backup_file, database_url):
    if not os.path.exists(backup_file):
        print(f"[ERROR] Backup file does not exist: {backup_file}")
        return False

    print(f"[INFO] Restoring PostgreSQL from {backup_file}...")
    # Stop at the first failing statement and roll the whole restore back (pilot check 2026-10-09, F9):
    # without ON_ERROR_STOP psql skips failing statements and exits 0, so a partial restore (once: an
    # empty users table) was reported as a success. In one transaction the database stays as it was.
    cmd = ["psql", "--dbname", database_url, "--quiet", "--set", "ON_ERROR_STOP=1", "--single-transaction"]

    try:
        if backup_file.endswith(".gz"):
            with gzip.open(backup_file, "rb") as f_in:
                proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                stdout, stderr = proc.communicate(input=f_in.read())
        else:
            with open(backup_file, "rb") as f_in:
                proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                stdout, stderr = proc.communicate(input=f_in.read())

        if proc.returncode != 0:
            print(f"[ERROR] psql restore failed with code {proc.returncode}; nothing was changed "
                  f"(the restore runs in one transaction): {stderr.decode('utf-8', errors='ignore').strip()}")
            return False
        print("[SUCCESS] PostgreSQL database restored successfully.")
        return True
    except FileNotFoundError:
        print("[ERROR] psql utility not found in PATH.")
        return False


def main():
    if len(sys.argv) < 2:
        print("Usage: python restore.py <path_to_backup_file> [--apply]")
        sys.exit(1)

    backup_file = sys.argv[1]
    apply_restore = "--apply" in sys.argv
    db_type = os.environ.get("DB_TYPE", "sqlite").lower()
    db_url = os.environ.get("DATABASE_URL", "")

    if db_type == "postgres" or db_url.startswith("postgresql://") or db_url.startswith("postgres://"):
        if not apply_restore:
            print("[INFO] Dry run check for PostgreSQL backup file existence.")
            if os.path.exists(backup_file):
                print(f"[SUCCESS] Backup file {backup_file} verified. Run with --apply to restore to database.")
            else:
                print(f"[ERROR] Backup file not found: {backup_file}")
                sys.exit(1)
        else:
            success = restore_postgres(backup_file, db_url)
            sys.exit(0 if success else 1)
    else:
        # SQLite
        success, head = verify_sqlite_backup(backup_file)
        if success:
            print(f"[SUCCESS] Sandbox integrity check PASSED (Revision: {head}).")
            if apply_restore:
                target_db = sqlite_target()
                print(f"[INFO] Applying verified backup to {target_db}...")
                if not restore_sqlite(backup_file, target_db):
                    sys.exit(1)
                print(f"[SUCCESS] Live database replaced with {backup_file}.")
        else:
            print("[ERROR] Sandbox integrity check FAILED.")
            sys.exit(1)


if __name__ == "__main__":
    main()
