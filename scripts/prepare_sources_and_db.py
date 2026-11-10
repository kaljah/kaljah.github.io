import sqlite3
import json
from datetime import datetime

conn = sqlite3.connect("new/server/ghg_app.db")
c = conn.cursor()

# 1. Clean out the 12 old mock 2022 records
c.execute("DELETE FROM emissions WHERE year=2022 AND facility_id IN (37, 38)")
print(f"Deleted old mock 2022 records for facilities 37 & 38. Rows affected: {c.rowcount}")

# 2. Load the 68 sources
with open("scripts/full_reconciled_sources.json", "r", encoding="utf-8") as f:
    sources = json.load(f)

print(f"Loaded {len(sources)} sources from full_reconciled_sources.json")

# Map module to process_type and emission source type
def get_process_info(module, name):
    name_l = name.lower()
    if "combustion" in module.lower():
        if "diesel" in name_l or "edg" in name_l or "fire" in name_l:
            return "combustion", "diesel", "diesel"
        return "combustion", "fuel_gas", "natural_gas"
    elif "flaring" in module.lower():
        return "flaring", "gas", "natural_gas"
    elif "venting" in module.lower():
        return "venting", "gas", "natural_gas"
    elif "fugitive" in module.lower():
        return "fugitive", "gas", "natural_gas"
    elif "mobile" in module.lower():
        if "diesel" in name_l:
            return "mobile", "diesel", "diesel"
        return "mobile", "gasoline", "motor_gasoline"
    elif "waste" in module.lower():
        return "separation", "wastewater", "wastewater"
    elif "fire" in module.lower() or "suppressant" in name_l:
        return "fugitive", "chemical", "hfc"
    return "combustion", "fuel_gas", "natural_gas"

now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

# Register emission sources in emission_sources table
registered_count = 0
for s in sources:
    fac_id = 37 if s["entity"] == "HBNS" else 38
    name = s["source_name"]
    proc_type, fuel_type, sub = get_process_info(s["module"], name)
    
    # Check if already exists
    existing = c.execute("SELECT id FROM emission_sources WHERE facility_id=? AND name=?", (fac_id, name)).fetchone()
    if not existing:
        c.execute('''
            INSERT INTO emission_sources 
            (facility_id, name, type, equipment_id, fuel_type, status, created_at, updated_at, is_test)
            VALUES (?, ?, ?, ?, ?, 'Active', ?, ?, 0)
        ''', (fac_id, name, proc_type, name, fuel_type, now_str, now_str))
        registered_count += 1

conn.commit()
print(f"Registered {registered_count} new equipment sources in emission_sources table.")
total_srcs = c.execute("SELECT count(*) FROM emission_sources WHERE facility_id IN (37, 38)").fetchone()[0]
print(f"Total active sources in database for HBNS & El Merk: {total_srcs}")

conn.close()
