#!/usr/bin/env python3
"""
Cross-platform SQLite online backup script.
Creates a consistent, point-in-time snapshot of the database while it is live.
"""
import os
import sys
import sqlite3
from datetime import datetime

def perform_backup(db_path="ghg_app.db", backup_dir="backups"):
    if not os.path.exists(db_path):
        print(f"[ERROR] Source database does not exist: {db_path}")
        return False

    os.makedirs(backup_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest_path = os.path.join(backup_dir, f"ghg_app_{timestamp}.db")

    print(f"[INFO] Backing up {db_path} to {dest_path}...")
    src = sqlite3.connect(db_path)
    dst = sqlite3.connect(dest_path)
    src.backup(dst)
    src.close()
    dst.close()

    size_mb = os.path.getsize(dest_path) / (1024 * 1024)
    print(f"[SUCCESS] Backup created: {dest_path} ({size_mb:.2f} MB)")
    return dest_path

if __name__ == "__main__":
    db_file = sys.argv[1] if len(sys.argv) > 1 else "ghg_app.db"
    perform_backup(db_file)
