#!/usr/bin/env python3
"""
Enterprise Database Backup Script for GHG Accounting Platform.

Supports:
- PostgreSQL via pg_dump with gzip compression and connection string parsing.
- SQLite online point-in-time backup via sqlite3.backup().
- Automatic timestamping and retention pruning (keeps last N backups).
"""
import os
import sys
import gzip
import shutil
import sqlite3
import subprocess
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()


def backup_sqlite(db_path, backup_dir):
    os.makedirs(backup_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest_path = os.path.join(backup_dir, f"ghg_sqlite_{timestamp}.db")
    gz_path = f"{dest_path}.gz"

    print(f"[INFO] Backing up SQLite {db_path} to {dest_path}...")
    src = sqlite3.connect(db_path)
    dst = sqlite3.connect(dest_path)
    src.backup(dst)
    src.close()
    dst.close()

    # Compress with gzip
    with open(dest_path, "rb") as f_in, gzip.open(gz_path, "wb") as f_out:
        shutil.copyfileobj(f_in, f_out)
    os.remove(dest_path)

    size_mb = os.path.getsize(gz_path) / (1024 * 1024)
    print(f"[SUCCESS] SQLite compressed backup created: {gz_path} ({size_mb:.2f} MB)")
    return gz_path


def backup_postgres(database_url, backup_dir):
    os.makedirs(backup_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest_path = os.path.join(backup_dir, f"ghg_postgres_{timestamp}.sql.gz")

    print(f"[INFO] Backing up PostgreSQL database to {dest_path}...")
    cmd = ["pg_dump", "--dbname", database_url, "--clean", "--if-exists"]
    
    try:
        with gzip.open(dest_path, "wb") as f_out:
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = proc.communicate()
            if proc.returncode != 0:
                print(f"[ERROR] pg_dump failed with code {proc.returncode}: {stderr.decode('utf-8', errors='ignore')}")
                if os.path.exists(dest_path):
                    os.remove(dest_path)
                return None
            f_out.write(stdout)
    except FileNotFoundError:
        print("[ERROR] pg_dump utility not found in PATH. Please install PostgreSQL client tools.")
        return None

    size_mb = os.path.getsize(dest_path) / (1024 * 1024)
    print(f"[SUCCESS] PostgreSQL backup created: {dest_path} ({size_mb:.2f} MB)")
    return dest_path


def prune_old_backups(backup_dir, retain_count=10):
    """Retains the most recent `retain_count` backups, removing older ones."""
    if not os.path.exists(backup_dir):
        return
    files = [
        os.path.join(backup_dir, f)
        for f in os.listdir(backup_dir)
        if f.endswith((".gz", ".db"))
    ]
    files.sort(key=os.path.getmtime, reverse=True)
    if len(files) > retain_count:
        for f in files[retain_count:]:
            try:
                os.remove(f)
                print(f"[CLEANUP] Pruned old backup: {f}")
            except OSError:
                pass


def main():
    backup_dir = os.environ.get("BACKUP_DIR", "backups")
    retain_count = int(os.environ.get("BACKUP_RETAIN_COUNT", "14"))
    db_type = os.environ.get("DB_TYPE", "sqlite").lower()
    db_url = os.environ.get("DATABASE_URL", "")

    if db_type == "postgres" or db_url.startswith("postgresql://") or db_url.startswith("postgres://"):
        if not db_url:
            print("[ERROR] DATABASE_URL is required for PostgreSQL backups")
            sys.exit(1)
        res = backup_postgres(db_url, backup_dir)
    else:
        # SQLite
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        default_db = os.path.join(base_dir, "ghg_app.db")
        db_path = sys.argv[1] if len(sys.argv) > 1 else default_db
        if not os.path.exists(db_path):
            # Check current working directory
            if os.path.exists("ghg_app.db"):
                db_path = "ghg_app.db"
        res = backup_sqlite(db_path, backup_dir)

    if res:
        prune_old_backups(backup_dir, retain_count=retain_count)
        print("[COMPLETE] Backup procedure finished successfully.")
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
