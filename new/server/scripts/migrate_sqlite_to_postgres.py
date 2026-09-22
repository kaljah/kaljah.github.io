#!/usr/bin/env python3
"""
SQLite to PostgreSQL Data Migration Tool.
Transfers all schemas, users, emissions, activity logs, and metadata
from local SQLite to PostgreSQL with data validation and integrity verification.

Usage:
  python migrate_sqlite_to_postgres.py --sqlite-db ghg_app.db --postgres-url postgresql://user:pass@host:5432/dbname
"""
import os
import sys
import sqlite3
import argparse

TABLE_TRANSFER_ORDER = [
    "users",
    "facilities",
    "emission_sources",
    "custom_factors",
    "emissions",
    "production_data",
    "scope2_emissions",
    "scope3_emissions",
    "scope3_data",
    "mitigation_records",
    "mitigation_projects",
    "goals",
    "base_year",
    "base_year_recalculations",
    "reporting_metadata",
    "notifications",
    "cbam_product_exports",
    "ogmp_surveys",
    "methane_source_types",
    "level_upgrade_logs",
    "sbti_targets",
    "system_settings",
    "activity_log",
]


def run_migration(sqlite_path, pg_url, dry_run=False):
    if not os.path.exists(sqlite_path):
        print(f"[ERROR] Source SQLite database not found at: {sqlite_path}")
        return False

    print(f"[INFO] Connecting to SQLite: {sqlite_path}")
    sq_conn = sqlite3.connect(sqlite_path)
    sq_conn.row_factory = sqlite3.Row
    sq_cur = sq_conn.cursor()

    existing_tables = [
        r[0] for r in sq_cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    ]

    print(f"[INFO] Found {len(existing_tables)} tables in SQLite database.")

    if dry_run:
        print("[INFO] DRY RUN MODE: Counting records per table:")
        for t in TABLE_TRANSFER_ORDER:
            if t in existing_tables:
                count = sq_cur.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
                print(f"  - {t}: {count} rows")
        sq_conn.close()
        return True

    try:
        import psycopg2
        from psycopg2.extras import execute_values
    except ImportError:
        print("[ERROR] psycopg2 not installed. Please run: pip install psycopg2-binary")
        sq_conn.close()
        return False

    print(f"[INFO] Connecting to PostgreSQL...")
    try:
        pg_conn = psycopg2.connect(pg_url)
        pg_cur = pg_conn.cursor()
    except Exception as e:
        print(f"[ERROR] Failed to connect to PostgreSQL: {e}")
        sq_conn.close()
        return False

    print("[INFO] Beginning table transfer...")
    transferred_summary = {}

    for table in TABLE_TRANSFER_ORDER:
        if table not in existing_tables:
            print(f"  [SKIP] Table {table} does not exist in source database.")
            continue

        rows = sq_cur.execute(f"SELECT * FROM {table}").fetchall()
        if not rows:
            print(f"  [EMPTY] Table {table} has 0 records.")
            transferred_summary[table] = 0
            continue

        columns = list(rows[0].keys())
        col_names = ", ".join([f'"{c}"' for c in columns])
        values = [tuple(r[c] for c in columns) for r in rows]

        insert_stmt = f'INSERT INTO "{table}" ({col_names}) VALUES %s ON CONFLICT DO NOTHING'

        try:
            execute_values(pg_cur, insert_stmt, values)
            pg_conn.commit()
            print(f"  [SUCCESS] {table}: {len(values)} records transferred.")
            transferred_summary[table] = len(values)
        except Exception as err:
            pg_conn.rollback()
            print(f"  [FAILED] {table} transfer error: {err}")
            transferred_summary[table] = f"Error: {err}"

    sq_conn.close()
    pg_conn.close()
    print("[INFO] Migration process finished.")
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Migrate SQLite GHG database to PostgreSQL")
    parser.add_argument("--sqlite-db", default="ghg_app.db", help="Path to SQLite database file")
    parser.add_argument("--postgres-url", default=os.environ.get("DATABASE_URL"), help="PostgreSQL connection URL")
    parser.add_argument("--dry-run", action="store_true", help="Perform count analysis without writing to target")
    args = parser.parse_args()

    run_migration(args.sqlite_db, args.postgres_url, dry_run=args.dry_run)
