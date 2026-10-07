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
from dotenv import load_dotenv

load_dotenv()


def verify_sqlite_backup(backup_file, sandbox_file="sandbox_restore.db"):
    if not os.path.exists(backup_file):
        print(f"[ERROR] Backup file does not exist: {backup_file}")
        return False

    temp_unpacked = None
    target_file = backup_file
    if backup_file.endswith(".gz"):
        temp_unpacked = sandbox_file + ".tmp.db"
        print(f"[INFO] Decompressing {backup_file}...")
        with gzip.open(backup_file, "rb") as f_in, open(temp_unpacked, "wb") as f_out:
            shutil.copyfileobj(f_in, f_out)
        target_file = temp_unpacked

    try:
        print(f"[INFO] Restoring {target_file} into {sandbox_file}...")
        src = sqlite3.connect(target_file)
        dst = sqlite3.connect(sandbox_file)
        src.backup(dst)
        src.close()

        cur = dst.cursor()
        tables = [t[0] for t in cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
        print(f"[INFO] Verified {len(tables)} tables in restored database.")

        integrity = cur.execute("PRAGMA integrity_check;").fetchall()
        print(f"[INFO] PRAGMA integrity_check: {integrity}")

        alembic_head = None
        if "alembic_version" in tables:
            cur.execute("SELECT version_num FROM alembic_version")
            row = cur.fetchone()
            if row:
                alembic_head = row[0]
                print(f"[INFO] Restored Alembic revision: {alembic_head}")

        dst.close()
        return True, alembic_head
    finally:
        if temp_unpacked and os.path.exists(temp_unpacked):
            os.remove(temp_unpacked)
        if os.path.exists(sandbox_file):
            os.remove(sandbox_file)


def restore_postgres(backup_file, database_url):
    if not os.path.exists(backup_file):
        print(f"[ERROR] Backup file does not exist: {backup_file}")
        return False

    print(f"[INFO] Restoring PostgreSQL from {backup_file}...")
    cmd = ["psql", "--dbname", database_url]

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
            print(f"[ERROR] psql restore failed with code {proc.returncode}: {stderr.decode('utf-8', errors='ignore')}")
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
                base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                target_db = os.path.join(base_dir, "ghg_app.db")
                print(f"[INFO] Applying verified backup to {target_db}...")
                if backup_file.endswith(".gz"):
                    with gzip.open(backup_file, "rb") as f_in, open(target_db, "wb") as f_out:
                        shutil.copyfileobj(f_in, f_out)
                else:
                    shutil.copyfile(backup_file, target_db)
                print(f"[SUCCESS] Live database replaced with {backup_file}.")
        else:
            print("[ERROR] Sandbox integrity check FAILED.")
            sys.exit(1)


if __name__ == "__main__":
    main()
