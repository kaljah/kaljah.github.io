import sqlite3
import json
from datetime import datetime, timezone

conn = sqlite3.connect("new/server/ghg_app.db")
c = conn.cursor()

now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

with open("scripts/full_reconciled_sources.json", "r", encoding="utf-8") as f:
    sources = json.load(f)

print(f"Generating exact normalized factors for {len(sources)} sources...")

for i, s in enumerate(sources):
    fid = 200 + i + 1
    ent = s["entity"]
    name = s["source_name"]
    fac_id = 37 if ent == "HBNS" else 38
    act = float(s.get("activity_data") or 0.0)
    
    co2_val = float(s.get("calc_co2") or s.get("rep_co2") or 0.0)
    ch4_val = float(s.get("calc_ch4") or s.get("rep_ch4") or 0.0)
    n2o_val = float(s.get("calc_n2o") or s.get("rep_n2o") or 0.0)
    
    if act > 0:
        ef_co2 = co2_val * 1000.0 / act
        ef_ch4 = ch4_val * 1000.0 / act
        ef_n2o = n2o_val * 1000.0 / act
    else:
        ef_co2, ef_ch4, ef_n2o = 0.0, 0.0, 0.0
        
    factor_name = f"{ent} - {name} EF"
    unit_str = "kg/m3"  # Standard volume-basis unit
    
    c.execute("DELETE FROM custom_factors WHERE id=?", (fid,))
    c.execute('''
        INSERT INTO custom_factors (
            id, name, co2_factor, ch4_factor, n2o_factor, co_factor, unit,
            facility_id, region, status, created_at, updated_at, is_archived, is_test
        ) VALUES (
            ?, ?, ?, ?, ?, 0.0, ?,
            ?, ?, 'Approved', ?, ?, 0, 0
        )
    ''', (fid, factor_name, ef_co2, ef_ch4, ef_n2o, unit_str, fac_id, ent, now_str, now_str))

conn.commit()
print("All 68 custom factors updated to kg/m3!")
conn.close()
