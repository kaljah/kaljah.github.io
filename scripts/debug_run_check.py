import sys
import os
import shutil
import json

sys.path.insert(0, os.path.abspath("new/server"))
from app import app
from background_processor import run_file_check

with open("scripts/full_reconciled_sources.json", "r", encoding="utf-8") as f:
    sources = json.load(f)

csv_rows = ["date,year,month,facility_name,process,factor_type,fuel,quantity,unit,equipment"]
for i, s in enumerate(sources):
    ent = s["entity"]
    fac = "HBNS (Hassi Berkine South)" if ent == "HBNS" else "El Merk"
    name = s["source_name"].replace('"', '""')
    fname = f"{ent} - {s['source_name']} EF".replace('"', '""')
    act = float(s["activity_data"] or 0.0)
    csv_rows.append(f'2022-12-31,2022,12,"{fac}",combustion,custom,"{fname}",{act},m3,"{name}"')

csv_text = "\n".join(csv_rows)
with open("berkine_2022_all_68_sources.csv", "w", encoding="utf-8") as f:
    f.write(csv_text)

with app.app_context():
    shutil.copy("berkine_2022_all_68_sources.csv", "test_run_check.csv")
    status = run_file_check(app, "test_run_check.csv", "berkine_2022_all_68_sources.csv", 1, "auto", scope="1", overwrite_duplicates=True, decimal_mark="point")
    print("ERRORS:", status.get("errors"))
    print("SKIPPED:", status.get("skipped_groups"))
    pv = status.get("preview") or {}
    print("TOTAL ROWS:", pv.get("total_rows"))
    print("ESTIMATED OK:", pv.get("estimated_ok"))
