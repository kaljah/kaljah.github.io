"""Part 1.6: Duplicates Audit and Dry-Run Review Script.
Scans the database for duplicate and timestamp-suffixed records across:
1. Custom emission factors (e.g. 'Skikda Light Refinery Gas 2026-1791316242057')
2. Mitigation projects (e.g. 'In Salah Geological Storage Unit 2', 14,250 tCO2e)
3. Emission sources (e.g. repeated 'Gas Lift Compressor Train 4', HP Flare Stack units)
4. Scope 3 emissions (repeated facility, year, month, category, sub_category)

Outputs a comprehensive dry-run report for operator review.
DOES NOT MODIFY OR DELETE ANY DATABASE RECORDS (read-only dry-run).
"""
import os
import re
import json
import sqlite3

def run_duplicates_audit():
    db_path = os.path.join(os.path.dirname(__file__), "..", "ghg_app.db")
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    report_data = {
        "title": "Part 1.6 Duplicates Inventory & Review Dry-Run Report",
        "generated_at": "2026-11-01T12:12:00Z",
        "database_writes_performed": 0,
        "sections": {}
    }

    # 1. Custom Factors
    cur.execute("SELECT id, name, co2_factor, ch4_factor, n2o_factor, unit, source, created_at, status FROM custom_factors")
    factors = [dict(r) for r in cur.fetchall()]
    timestamp_factors = []
    by_base_name = {}
    for f in factors:
        name = f["name"]
        clean_name = re.sub(r"[-_\s]+\d{10,14}$", "", name).strip()
        f["base_name"] = clean_name
        if clean_name != name:
            timestamp_factors.append(f)
        by_base_name.setdefault(clean_name.lower(), []).append(f)

    factor_dupes = {k: v for k, v in by_base_name.items() if len(v) > 1}
    report_data["sections"]["custom_factors"] = {
        "total_records": len(factors),
        "timestamp_suffixed_count": len(timestamp_factors),
        "duplicate_groups_count": len(factor_dupes),
        "duplicate_groups": factor_dupes
    }

    # 2. Mitigation Projects
    cur.execute("SELECT id, name, project_type, year, quantity_tco2e, facility_id, created_at, status FROM mitigation_projects")
    projects = [dict(r) for r in cur.fetchall()]
    timestamp_projects = []
    by_proj_key = {}
    for p in projects:
        name = p["name"]
        clean_name = re.sub(r"[-_\s]+\d{10,14}$", "", name).strip()
        p["base_name"] = clean_name
        if clean_name != name:
            timestamp_projects.append(p)
        key = f"{p['facility_id']}_{p['year']}_{clean_name.lower()}"
        by_proj_key.setdefault(key, []).append(p)

    project_dupes = {k: v for k, v in by_proj_key.items() if len(v) > 1}
    report_data["sections"]["mitigation_projects"] = {
        "total_records": len(projects),
        "timestamp_suffixed_count": len(timestamp_projects),
        "duplicate_groups_count": len(project_dupes),
        "duplicate_groups": project_dupes
    }

    # 3. Emission Sources
    cur.execute("SELECT id, facility_id, name, type, equipment_id, fuel_type, created_at FROM emission_sources")
    sources = [dict(r) for r in cur.fetchall()]
    timestamp_sources = []
    by_eq_id = {}
    by_source_name = {}
    for s in sources:
        name = s["name"]
        clean_name = re.sub(r"[-_\s]+\d{10,14}$", "", name).strip()
        s["base_name"] = clean_name
        if clean_name != name:
            timestamp_sources.append(s)
        if s.get("equipment_id"):
            eq_key = f"{s['facility_id']}_{s['equipment_id'].strip().lower()}"
            by_eq_id.setdefault(eq_key, []).append(s)
        name_key = f"{s['facility_id']}_{clean_name.lower()}"
        by_source_name.setdefault(name_key, []).append(s)

    source_dupes_eq = {k: v for k, v in by_eq_id.items() if len(v) > 1}
    report_data["sections"]["emission_sources"] = {
        "total_records": len(sources),
        "timestamp_suffixed_count": len(timestamp_sources),
        "duplicate_equipment_groups_count": len(source_dupes_eq),
        "duplicate_equipment_groups": source_dupes_eq
    }

    # 4. Scope 3 Emissions
    cur.execute("""
        SELECT facility_id, year, month, category, sub_category, COUNT(*) as cnt, GROUP_CONCAT(id) as ids, SUM(co2e) as total_co2e
        FROM scope3_emissions
        GROUP BY facility_id, year, month, category, sub_category
        HAVING COUNT(*) > 1
    """)
    s3_dupes = [dict(r) for r in cur.fetchall()]
    report_data["sections"]["scope3_emissions"] = {
        "duplicate_groups_count": len(s3_dupes),
        "duplicate_groups": s3_dupes
    }

    report_dir = os.path.join(os.path.dirname(__file__), "..", "reports")
    os.makedirs(report_dir, exist_ok=True)
    out_json = os.path.join(report_dir, "duplicates_cleanup_dryrun.json")
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(report_data, f, indent=2)

    print("============================================================")
    print("PART 1.6 DUPLICATES INVENTORY REPORT (DRY-RUN)")
    print("============================================================")
    print(f"Custom Factors:      {len(factors)} total, {len(timestamp_factors)} timestamped, {len(factor_dupes)} duplicate groups")
    for k, v in factor_dupes.items():
        ids = [item["id"] for item in v]
        print(f"  - '{k}': {len(v)} occurrences (IDs: {ids})")

    print(f"\nMitigation Projects: {len(projects)} total, {len(timestamp_projects)} timestamped, {len(project_dupes)} duplicate groups")
    for k, v in project_dupes.items():
        ids = [item["id"] for item in v]
        print(f"  - '{k}': {len(v)} occurrences (IDs: {ids}, reduction: {v[0]['quantity_tco2e']} t)")

    print(f"\nEmission Sources:    {len(sources)} total, {len(timestamp_sources)} timestamped, {len(source_dupes_eq)} duplicate equipment groups")
    for k, v in source_dupes_eq.items():
        names = [f"#{item['id']} {item['name']}" for item in v]
        print(f"  - Equipment '{k}': {names}")

    print(f"\nScope 3 Emissions:   {len(s3_dupes)} duplicate natural-key groups")
    for d in s3_dupes[:5]:
        print(f"  - Fac {d['facility_id']}, {d['year']}-{d['month']:02d}, {d['category']} ('{d['sub_category']}'): {d['cnt']} rows (IDs: {d['ids']})")
    if len(s3_dupes) > 5:
        print(f"    ... and {len(s3_dupes) - 5} more groups.")

    print(f"\nReport written to: {out_json}")
    print("Database writes performed: 0 (No records deleted or modified).")
    print("============================================================")

if __name__ == "__main__":
    run_duplicates_audit()
