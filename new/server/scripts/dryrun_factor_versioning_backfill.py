"""Dry-run audit and backfill plan for Part 2.1: Factor & GWP Versioning.
Analyzes stored records in ghg_app.db and generates a dry-run report
without mutating or deleting any records.
"""
import os
import json
import sqlite3
from datetime import datetime, timezone

def generate_dryrun_report():
    db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "ghg_app.db"))
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        return

    con = sqlite3.connect(db_path)
    cur = con.cursor()

    # Scope 1 emissions
    cur.execute("SELECT count(*), count(factor_version), count(gwp_version) FROM emissions")
    s1_total, s1_fv, s1_gwp = cur.fetchone()

    # Sample Scope 1 records needing backfill
    cur.execute("""
        SELECT id, record_id, process_type, factor_source, factor_version, gwp_version, co2e_total
        FROM emissions
        WHERE factor_version IS NULL OR gwp_version IS NULL
        LIMIT 10
    """)
    s1_samples = [
        {
            "id": r[0],
            "record_id": r[1],
            "process_type": r[2],
            "current_factor_source": r[3],
            "current_factor_version": r[4],
            "current_gwp_version": r[5],
            "co2e_t": r[6],
            "proposed_factor_version": r[3] or "API-2021.1",
            "proposed_gwp_version": "AR5",
        }
        for r in cur.fetchall()
    ]

    # Scope 2 emissions
    cur.execute("SELECT count(*), count(factor_version), count(gwp_version) FROM scope2_emissions")
    s2_total, s2_fv, s2_gwp = cur.fetchone()

    cur.execute("""
        SELECT id, source_type, grid_region, factor_version, gwp_version, co2e
        FROM scope2_emissions
        WHERE factor_version IS NULL OR gwp_version IS NULL
        LIMIT 5
    """)
    s2_samples = [
        {
            "id": r[0],
            "source_type": r[1],
            "grid_region": r[2],
            "current_factor_version": r[3],
            "current_gwp_version": r[4],
            "co2e_t": r[5],
            "proposed_factor_version": "Sonelgaz/IEA-2023.1",
            "proposed_gwp_version": "AR5",
        }
        for r in cur.fetchall()
    ]

    # Scope 3 emissions
    cur.execute("SELECT count(*), count(factor_version), count(gwp_version) FROM scope3_emissions")
    s3_total, s3_fv, s3_gwp = cur.fetchone()

    cur.execute("""
        SELECT id, category, calculation_method, factor_version, gwp_version, co2e
        FROM scope3_emissions
        WHERE factor_version IS NULL OR gwp_version IS NULL
        LIMIT 5
    """)
    s3_samples = [
        {
            "id": r[0],
            "category": r[1],
            "calculation_method": r[2],
            "current_factor_version": r[3],
            "current_gwp_version": r[4],
            "co2e_t": r[5],
            "proposed_factor_version": "API/GHG-Protocol-2023.1",
            "proposed_gwp_version": "AR5",
        }
        for r in cur.fetchall()
    ]

    report = {
        "report_type": "Factor and GWP Versioning Backfill Dry-Run",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "database": db_path,
        "policy": "Never rewrite data automatically. Dry-run report produced for operator review.",
        "records_written": 0,
        "records_mutated": 0,
        "scope1": {
            "total_records": s1_total,
            "records_with_factor_version": s1_fv,
            "records_with_gwp_version": s1_gwp,
            "records_needing_backfill": s1_total - min(s1_fv, s1_gwp),
            "sample_candidates": s1_samples,
        },
        "scope2": {
            "total_records": s2_total,
            "records_with_factor_version": s2_fv,
            "records_with_gwp_version": s2_gwp,
            "records_needing_backfill": s2_total - min(s2_fv, s2_gwp),
            "sample_candidates": s2_samples,
        },
        "scope3": {
            "total_records": s3_total,
            "records_with_factor_version": s3_fv,
            "records_with_gwp_version": s3_gwp,
            "records_needing_backfill": s3_total - min(s3_fv, s3_gwp),
            "sample_candidates": s3_samples,
        },
        "recommendation": "Backfill factor_version and gwp_version on null fields only. All co2e_total values remain 100% frozen."
    }

    out_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "reports"))
    os.makedirs(out_dir, exist_ok=True)
    out_file = os.path.join(out_dir, "factor_versioning_backfill_dryrun.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print(f"Dry-run report saved to {out_file}")

if __name__ == "__main__":
    generate_dryrun_report()
