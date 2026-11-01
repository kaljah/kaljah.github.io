"""Part 1.4: Anomaly detector QA flag dry-run review script.
Scans the database for malformed flags (such as exponential z-scores 2.22e+17 or [BogusStatus])
and outputs a JSON dry-run report without modifying any database records.
"""
import os
import re
import json
import sqlite3

def run_dryrun():
    db_path = os.path.join(os.path.dirname(__file__), "..", "ghg_app.db")
    con = sqlite3.connect(db_path)
    cur = con.cursor()

    malformed = []

    for table in ["emissions", "scope2_emissions", "scope3_emissions"]:
        try:
            cur.execute(f"SELECT id, qa_flag, status FROM {table} WHERE qa_flag IS NOT NULL")
            rows = cur.fetchall()
            for rid, flag, status in rows:
                if not flag:
                    continue
                issue = None
                proposed = flag

                if "BogusStatus" in flag:
                    issue = "legacy_bogus_status_tag"
                    # clean up [BogusStatus] and normalize duplicate tags
                    cleaned = re.sub(r"\[BogusStatus\]\s*", "", flag).strip()
                    cleaned = re.sub(r"(\[Verified\]\s*)+", "[Verified] ", cleaned).strip()
                    proposed = cleaned
                elif "standard deviations" in flag and ("e+" in flag or any(len(part) > 10 and part.isdigit() for part in re.findall(r"\d+", flag))):
                    issue = "astronomical_z_score_formatting"
                    # Format standard deviation nicely capped at 10.0
                    proposed = re.sub(
                        r"is\s+[\d.eE+-]+\s+standard deviations",
                        "is 10.0 standard deviations",
                        flag
                    )

                if issue:
                    malformed.append({
                        "table": table,
                        "id": rid,
                        "current_qa_flag": flag,
                        "status": status,
                        "detected_issue": issue,
                        "proposed_clean_qa_flag": proposed,
                        "action": "PENDING_USER_APPROVAL_NO_CHANGE_MADE"
                    })
        except Exception as e:
            print(f"Error querying {table}: {e}")

    report = {
        "title": "Part 1.4 Anomaly Flag Sanitization Dry-Run Report",
        "timestamp": "2026-11-01T04:54:00Z",
        "records_scanned": "all",
        "malformed_count": len(malformed),
        "malformed_records": malformed,
        "database_writes_performed": 0
    }

    report_dir = os.path.join(os.path.dirname(__file__), "..", "reports")
    os.makedirs(report_dir, exist_ok=True)
    out_path = os.path.join(report_dir, "anomaly_flags_dryrun.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print(f"Report generated: {out_path}")
    print(f"Found {len(malformed)} malformed records:")
    for r in malformed:
        print(f"  [{r['table']} #{r['id']}] Issue: {r['detected_issue']}")
        print(f"    Current:  {r['current_qa_flag']}")
        print(f"    Proposed: {r['proposed_clean_qa_flag']}")

if __name__ == "__main__":
    run_dryrun()
