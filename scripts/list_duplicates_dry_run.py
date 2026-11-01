#!/usr/bin/env python3
"""
Duplicate Data Inventory & Dry-Run Report for NeoCarbon GHG/MRV Platform.

Phase 1 Item 1.6:
Scans the database for duplicate records across:
1. Custom Emission Factors (identical names or timestamp suffixes)
2. Mitigation Projects (identical name, facility, year or timestamp suffixes)
3. Operational Emission Sources (repeated equipment names or timestamp suffixes)
4. Scope 3 Emissions (identical repeated activity rows)

WORKING RULE ENFORCEMENT:
- READ-ONLY / DRY-RUN ONLY.
- ZERO AUTOMATIC DELETIONS. NO RECORDS ARE MODIFIED OR DELETED.
- Produces a structured report of candidates for operator review.
"""

import sys
import os
import re
import sqlite3
from collections import defaultdict


def find_db_path():
    candidates = [
        os.path.join(os.path.dirname(__file__), "..", "new", "server", "ghg_app.db"),
        os.path.join(os.path.dirname(__file__), "new", "server", "ghg_app.db"),
        "new/server/ghg_app.db",
        "ghg_app.db",
    ]
    for p in candidates:
        if os.path.exists(p):
            return os.path.abspath(p)
    return None


def strip_timestamp_suffix(name):
    """Strip timestamp/unique suffixes like '-1791316253578' or ' 2026-1791316242057'."""
    if not name:
        return ""
    # Strip epoch timestamp suffixes (10 to 14 digits)
    cleaned = re.sub(r"[-_\s]+(?:202\d[-_])?\d{10,14}$", "", name.strip())
    # Strip trailing 4-digit phase hashes like 'Phase 6780' if generated
    return cleaned.strip()


def run_dry_run_report(db_path):
    print("=" * 80)
    print("  NEOCARBON GHG/MRV PLATFORM — DUPLICATE DATA INVENTORY (DRY-RUN)")
    print("=" * 80)
    print(f"Target Database: {db_path}")
    print("Mode: READ-ONLY (Dry-Run). No data will be deleted.\n")

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    total_dupes_found = 0

    # -------------------------------------------------------------------------
    # 1. CUSTOM EMISSION FACTORS
    # -------------------------------------------------------------------------
    print("=" * 80)
    print("1. CUSTOM EMISSION FACTORS AUDIT")
    print("=" * 80)

    cur.execute("SELECT id, name, facility_id, region, unit, co2_factor, created_at, status FROM custom_factors")
    factors = cur.fetchall()

    factor_groups = defaultdict(list)
    for f in factors:
        base_name = strip_timestamp_suffix(f["name"])
        key = (base_name.lower(), f["facility_id"] or "Global")
        factor_groups[key].append(f)

    factor_dupes = {k: v for k, v in factor_groups.items() if len(v) > 1 or strip_timestamp_suffix(v[0]["name"]) != v[0]["name"]}

    if not factor_dupes:
        print("  ✓ No duplicate or timestamped custom factors found.")
    else:
        print(f"  Found {len(factor_dupes)} groups with timestamp suffixes or multiple copies:\n")
        print(f"  {'ID':<6} | {'Status':<10} | {'Facility':<10} | {'CO2 Factor':<12} | {'Action':<10} | {'Factor Name'}")
        print("  " + "-" * 78)
        for (base_name, fac), rows in factor_dupes.items():
            # sort by id ascending; keep first/oldest
            rows_sorted = sorted(rows, key=lambda r: r["id"])
            for idx, r in enumerate(rows_sorted):
                action = "KEEP" if idx == 0 else "DELETE"
                if action == "DELETE":
                    total_dupes_found += 1
                status = r["status"] or "Approved"
                print(f"  {r['id']:<6} | {status:<10} | {str(fac):<10} | {str(r['co2_factor']):<12} | {action:<10} | {r['name']}")
            print()

    # -------------------------------------------------------------------------
    # 2. MITIGATION PROJECTS
    # -------------------------------------------------------------------------
    print("=" * 80)
    print("2. MITIGATION PROJECTS AUDIT")
    print("=" * 80)

    cur.execute("SELECT id, name, facility_id, year, quantity_tco2e, status, created_at FROM mitigation_projects")
    projects = cur.fetchall()

    proj_groups = defaultdict(list)
    for p in projects:
        base_name = strip_timestamp_suffix(p["name"])
        key = (base_name.lower(), p["facility_id"], p["year"])
        proj_groups[key].append(p)

    proj_dupes = {k: v for k, v in proj_groups.items() if len(v) > 1}

    if not proj_dupes:
        print("  ✓ No duplicate mitigation projects found.")
    else:
        print(f"  Found {len(proj_dupes)} duplicate mitigation project groups:\n")
        print(f"  {'ID':<6} | {'Year':<6} | {'Facility':<10} | {'tCO2e':<12} | {'Action':<10} | {'Project Name'}")
        print("  " + "-" * 78)
        for (base_name, fac, yr), rows in proj_dupes.items():
            rows_sorted = sorted(rows, key=lambda r: r["id"])
            for idx, r in enumerate(rows_sorted):
                action = "KEEP" if idx == 0 else "DELETE"
                if action == "DELETE":
                    total_dupes_found += 1
                print(f"  {r['id']:<6} | {str(yr):<6} | {str(fac):<10} | {str(r['quantity_tco2e']):<12} | {action:<10} | {r['name']}")
            print()

    # -------------------------------------------------------------------------
    # 3. EMISSION SOURCES
    # -------------------------------------------------------------------------
    print("=" * 80)
    print("3. OPERATIONAL EMISSION SOURCES AUDIT")
    print("=" * 80)

    cur.execute("SELECT id, name, facility_id, type, equipment_id, status FROM emission_sources")
    sources = cur.fetchall()

    source_groups = defaultdict(list)
    for s in sources:
        base_name = strip_timestamp_suffix(s["name"])
        key = (base_name.lower(), s["facility_id"])
        source_groups[key].append(s)

    source_dupes = {k: v for k, v in source_groups.items() if len(v) > 1}

    if not source_dupes:
        print("  ✓ No duplicate emission sources found.")
    else:
        print(f"  Found {len(source_dupes)} duplicate emission source groups:\n")
        print(f"  {'ID':<6} | {'Facility':<10} | {'Type':<14} | {'Equip ID':<12} | {'Action':<10} | {'Source Name'}")
        print("  " + "-" * 78)
        for (base_name, fac), rows in source_dupes.items():
            rows_sorted = sorted(rows, key=lambda r: r["id"])
            for idx, r in enumerate(rows_sorted):
                action = "KEEP" if idx == 0 else "DELETE"
                if action == "DELETE":
                    total_dupes_found += 1
                print(f"  {r['id']:<6} | {str(fac):<10} | {str(r['type']):<14} | {str(r['equipment_id']):<12} | {action:<10} | {r['name']}")
            print()

    # -------------------------------------------------------------------------
    # 4. SCOPE 3 EMISSIONS
    # -------------------------------------------------------------------------
    print("=" * 80)
    print("4. SCOPE 3 DUPLICATE EMISSIONS AUDIT")
    print("=" * 80)

    cur.execute("""
        SELECT id, facility_id, year, month, category, sub_category, activity_data, unit, co2e, status
        FROM scope3_emissions
        ORDER BY facility_id, year, month, category, sub_category, id
    """)
    s3_records = cur.fetchall()

    s3_groups = defaultdict(list)
    for s in s3_records:
        key = (s["facility_id"], s["year"], s["month"], s["category"], str(s["sub_category"] or "").strip().lower(), s["activity_data"], s["unit"])
        s3_groups[key].append(s)

    s3_dupes = {k: v for k, v in s3_groups.items() if len(v) > 1}

    if not s3_dupes:
        print("  ✓ No duplicate Scope 3 records found.")
    else:
        print(f"  Found {len(s3_dupes)} groups of identical Scope 3 records:\n")
        print(f"  {'Group Key':<45} | {'Count':<6} | {'Action Summary'}")
        print("  " + "-" * 78)
        for (fac, yr, m, cat, sub_cat, act, u), rows in s3_dupes.items():
            rows_sorted = sorted(rows, key=lambda r: r["id"])
            keep_id = rows_sorted[0]["id"]
            del_ids = [r["id"] for r in rows_sorted[1:]]
            total_dupes_found += len(del_ids)
            label = f"Fac {fac} | {yr}-{m:02d} | {cat} ({sub_cat or 'All'})"
            print(f"  {label:<45} | {len(rows):<6} | Keep ID {keep_id}, Delete IDs {del_ids}")
        print()

    print("=" * 80)
    print("DRY-RUN SUMMARY REPORT")
    print("=" * 80)
    print(f"Total candidate duplicate records identified: {total_dupes_found}")
    print("\n[NOTE]: ZERO RECORDS HAVE BEEN REMOVED.")
    print("This script is non-destructive. To apply any deletions, the user must explicitly approve")
    print("the candidate list above.\n")

    conn.close()


if __name__ == "__main__":
    db_file = sys.argv[1] if len(sys.argv) > 1 else find_db_path()
    if not db_file or not os.path.exists(db_file):
        print(f"Error: Database file not found at '{db_file}'. Provide valid path as argument.")
        sys.exit(1)
    run_dry_run_report(db_file)
