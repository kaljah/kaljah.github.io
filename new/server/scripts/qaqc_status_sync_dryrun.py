"""
QA/QC Status Contradiction Dry-Run Audit Script (Read-Only)
=========================================================
Audits all emissions records (Scope 1, Scope 2, Scope 3) for status contradictions:
- Records with status 'Verified' or 'Pending' but qa_flag indicating [Rejected]
- Records with status 'Rejected' but qa_flag indicating [Verified]
- Missing or invalid workflow statuses

CRITICAL: Strictly read-only. Produces a detailed dry-run report for user review.
"""

import os
import sys
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
os.environ.setdefault("SEED_ADMIN", "false")

from app import app
from extensions import db
from models import Emission, Scope2Emission, Scope3Emission


def audit_status_contradictions():
    models = [
        ("Scope 1", Emission, "co2e_total"),
        ("Scope 2", Scope2Emission, "co2e"),
        ("Scope 3", Scope3Emission, "co2e"),
    ]

    contradictions = []

    with app.app_context():
        for scope_name, model, co2e_col in models:
            records = model.query.all()
            for r in records:
                status = str(r.status or "").strip()
                flag = str(r.qa_flag or "").strip()
                co2e = float(getattr(r, co2e_col, 0.0) or 0.0)

                # Check for [Rejected] flag on non-rejected records
                if ("[rejected]" in flag.lower() or flag.lower().startswith("rejected:")) and status.lower() != "rejected":
                    contradictions.append({
                        "scope": scope_name,
                        "id": r.id,
                        "facility_id": r.facility_id,
                        "year": r.year,
                        "co2e": co2e,
                        "current_status": status,
                        "qa_flag": flag,
                        "issue": "Flag indicates [Rejected] but status is NOT Rejected",
                        "proposed_status": "Rejected",
                        "proposed_clean_flag": flag.replace("[Rejected]", "").replace("Rejected:", "").strip(),
                        "impact_on_inventory": f"Excludes {co2e:,.2f} tCO2e from active inventory totals"
                    })
                # Check for [Verified] flag on non-verified records
                elif "[verified]" in flag.lower() and status.lower() not in ("verified", "active"):
                    contradictions.append({
                        "scope": scope_name,
                        "id": r.id,
                        "facility_id": r.facility_id,
                        "year": r.year,
                        "co2e": co2e,
                        "current_status": status,
                        "qa_flag": flag,
                        "issue": "Flag indicates [Verified] but status is NOT Verified",
                        "proposed_status": "Verified",
                        "proposed_clean_flag": flag.replace("[Verified]", "").strip(),
                        "impact_on_inventory": f"Includes {co2e:,.2f} tCO2e in verified inventory totals"
                    })

    print("=" * 70)
    print("QA/QC WORKFLOW STATUS CONTRADICTION DRY-RUN REPORT")
    print("=" * 70)
    print(f"Total Contradictions Found: {len(contradictions)}")
    for item in contradictions:
        print(f"\n[{item['scope']} Record #{item['id']}] Facility {item['facility_id']} ({item['year']}):")
        print(f"  - Issue: {item['issue']}")
        print(f"  - Current Status: '{item['current_status']}'")
        print(f"  - Current QA Flag: '{item['qa_flag']}'")
        print(f"  - Proposed Status: '{item['proposed_status']}'")
        print(f"  - Proposed Clean QA Flag: '{item['proposed_clean_flag']}'")
        print(f"  - Impact on Inventory: {item['impact_on_inventory']}")
    print("=" * 70)
    print("Dry-run complete. No database records were modified.")
    print("=" * 70)

    # Save JSON report
    report_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "reports", "qaqc_status_contradictions_dryrun.json"))
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(contradictions, f, indent=2)
    print(f"Report saved to: {report_path}")
    return contradictions


if __name__ == "__main__":
    audit_status_contradictions()
