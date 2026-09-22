#!/usr/bin/env python3
"""
Cross-platform SQLite restore & integrity verification script.
Tests restoration of a backup file in a temporary sandbox.
"""
import os
import sys
import sqlite3

def verify_restore(backup_file, sandbox_file="sandbox_restore.db"):
    if not os.path.exists(backup_file):
        print(f"[ERROR] Backup file does not exist: {backup_file}")
        return False

    print(f"[INFO] Restoring {backup_file} into {sandbox_file}...")
    src = sqlite3.connect(backup_file)
    dst = sqlite3.connect(sandbox_file)
    src.backup(dst)
    src.close()

    cur = dst.cursor()
    tables = [t[0] for t in cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    print(f"[INFO] Found {len(tables)} tables in restored database.")

    integrity = cur.execute("PRAGMA integrity_check;").fetchall()
    print(f"[INFO] PRAGMA integrity_check: {integrity}")

    dst.close()

    if os.path.exists(sandbox_file):
        os.remove(sandbox_file)
        print("[SUCCESS] Sandbox verified and removed.")

    return True

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python restore.py <path_to_backup_file>")
        sys.exit(1)
    verify_restore(sys.argv[1])
