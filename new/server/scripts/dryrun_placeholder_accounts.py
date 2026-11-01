"""
Dry-Run Audit: Placeholder & Test User Accounts (Item 3.5)
=========================================================
Identifies candidate test and placeholder accounts in the database according to:
- Test emails (@audit.test, @example.test, a@a, a)
- Timestamp-suffixed test accounts (e.g., auditor_1791314711023@sonatrach.dz)
- Benchmark worker accounts (benchmark_10000@sonatrach.dz)
- Accounts with is_test = True

Generates reports/placeholder_accounts_dryrun.json.
DOES NOT MODIFY OR DELETE ANY DATABASE RECORDS.
"""
import os
import sys
import json
import re
import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app import app
from extensions import db
from models import User

def generate_dryrun_report():
    with app.app_context():
        users = User.query.all()
        flagged = []
        production = []
        
        for u in users:
            reasons = []
            email = str(u.email or "").strip().lower()
            name = str(u.fullName or "").strip()
            
            if email in ("a", "a@a", "a@example.test"):
                reasons.append("Single-letter or test domain email")
            if "@audit.test" in email or "@example.test" in email:
                reasons.append("Synthetic test domain (@audit.test / @example.test)")
            if re.search(r"auditor_\d{10,}@", email):
                reasons.append("Timestamp-suffixed E2E test account")
            if "benchmark_" in email or "Benchmark Worker" in name:
                reasons.append("Automated performance benchmark account")
            if "(e2e test)" in name.lower():
                reasons.append("Explicit '(E2E Test)' tag in name")
            if getattr(u, "is_test", False):
                reasons.append("is_test flag already set in database")
                
            entry = {
                "id": u.id,
                "email": u.email,
                "fullName": u.fullName,
                "role": u.role,
                "status": u.status,
                "is_test": bool(getattr(u, "is_test", False)),
                "reasons": reasons,
                "recommended_action": "Mark is_test=True, disable login or remove upon user confirmation" if reasons else "Keep in production",
            }
            
            if reasons:
                flagged.append(entry)
            else:
                production.append(entry)
                
        report = {
            "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "policy": "Zero automated deletion rule (produce dry-run report for user review)",
            "total_accounts": len(users),
            "flagged_placeholder_count": len(flagged),
            "production_account_count": len(production),
            "admin_count_total": sum(1 for u in users if u.role == "admin"),
            "admin_count_flagged": sum(1 for u in flagged if u["role"] == "admin"),
            "admin_count_production": sum(1 for u in production if u["role"] == "admin"),
            "flagged_accounts": flagged,
            "production_accounts": production,
        }
        
        out_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../reports"))
        os.makedirs(out_dir, exist_ok=True)
        report_file = os.path.join(out_dir, "placeholder_accounts_dryrun.json")
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
            
        print(f"Generated dry-run report at {report_file}: {len(flagged)} flagged accounts out of {len(users)} total.")

if __name__ == "__main__":
    generate_dryrun_report()
