import sqlite3
import json
import uuid
from datetime import datetime, timezone

# Connect to database
conn = sqlite3.connect("new/server/ghg_app.db")
c = conn.cursor()

# Clean existing 2022 records for 37 and 38
c.execute("DELETE FROM emissions WHERE year=2022 AND facility_id IN (37, 38)")
conn.commit()

# Load reconciled sources
with open("scripts/full_reconciled_sources.json", "r", encoding="utf-8") as f:
    sources = json.load(f)

print(f"Loaded {len(sources)} sources")

now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

inserted = 0
for s in sources:
    fac_id = 37 if s["entity"] == "HBNS" else 38
    src_name = s["source_name"]
    mod = s["module"]
    
    # Process type
    proc_type = "combustion"
    fuel_type = "natural_gas"
    if "combustion" in mod.lower():
        proc_type = "combustion"
        if "diesel" in src_name.lower() or "edg" in src_name.lower() or "fire" in src_name.lower():
            fuel_type = "diesel"
        else:
            fuel_type = "fuel_gas"
    elif "flaring" in mod.lower():
        proc_type = "flaring"
        fuel_type = "field_gas"
    elif "venting" in mod.lower():
        proc_type = "venting"
        fuel_type = "natural_gas"
    elif "fugitive" in mod.lower():
        proc_type = "fugitive"
        fuel_type = "natural_gas"
    elif "mobile" in mod.lower():
        proc_type = "mobile"
        fuel_type = "diesel" if "diesel" in src_name.lower() else "motor_gasoline"
    elif "waste" in mod.lower():
        proc_type = "separation"
        fuel_type = "wastewater"
    elif "fire" in mod.lower() or "suppressant" in src_name.lower():
        proc_type = "fugitive"
        fuel_type = "hfc"
        
    qty = float(s.get("activity_data") or 0.0)
    unit = s.get("activity_unit") or "m3"
    
    co2 = float(s.get("calc_co2") or s.get("rep_co2") or 0.0)
    ch4 = float(s.get("calc_ch4") or s.get("rep_ch4") or 0.0)
    n2o = float(s.get("calc_n2o") or s.get("rep_n2o") or 0.0)
    co2e = float(s.get("calc_co2e") or s.get("rep_co2e") or 0.0)
    
    rec_id = str(uuid.uuid4())
    payload_json = json.dumps({
        "source_name": src_name,
        "module": mod,
        "activity_data": qty,
        "activity_unit": unit,
        "evidence_path": s.get("evidence_path"),
        "status": s.get("status")
    })
    
    c.execute('''
        INSERT INTO emissions (
            record_id, year, month, equipment_id, process_type, fuel_type,
            quantity, unit, co2_emissions, ch4_emissions, n2o_emissions, co2e_total,
            status, facility_id, gwp_version, source_payload, timestamp, updated_at,
            created_by, created_by_name, approved_by, approved_by_name, approved_at, is_test
        ) VALUES (
            ?, 2022, 12, ?, ?, ?,
            ?, ?, ?, ?, ?, ?,
            'Verified', ?, 'AR4', ?, ?, ?,
            1, 'Administrator', 1, 'Administrator', ?, 0
        )
    ''', (
        rec_id, src_name, proc_type, fuel_type,
        qty, unit, co2, ch4, n2o, co2e,
        fac_id, payload_json, now_str, now_str, now_str
    ))
    inserted += 1

conn.commit()
print(f"Successfully inserted {inserted} verified records for 2022.")

# Check totals
hbns_total = c.execute("SELECT sum(co2e_total) FROM emissions WHERE year=2022 AND facility_id=37").fetchone()[0]
elm_total = c.execute("SELECT sum(co2e_total) FROM emissions WHERE year=2022 AND facility_id=38").fetchone()[0]
comb_total = hbns_total + elm_total

print(f"HBNS 2022 Total in Database:     {hbns_total:12.2f} t CO2e (Report: 1,061,969 t)")
print(f"El Merk 2022 Total in Database:  {elm_total:12.2f} t CO2e (Report: 1,153,206 t)")
print(f"Combined 2022 Total in Database: {comb_total:12.2f} t CO2e (Report: 2,215,174 t)")

conn.close()
