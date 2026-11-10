import sqlite3
from datetime import datetime, timezone

conn = sqlite3.connect("new/server/ghg_app.db")
c = conn.cursor()

now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

# Check or insert custom factors
factors = [
    (101, "HBNS Fuel Gas", 2.896638, 0.00005077, 0.00001421, 0.0, "kg/m3", 37, "HBNS", "Approved"),
    (102, "El Merk Fuel Gas", 2.945717, 0.00005064, 0.00001415, 0.0, "kg/m3", 38, "El Merk", "Approved"),
    (103, "HBNS Flare Gas", 2.839556, 0.009767, 0.000037, 0.0, "kg/m3", 37, "HBNS", "Approved"),
    (104, "El Merk Flare Gas", 2.839556, 0.009767, 0.000037, 0.0, "kg/m3", 38, "El Merk", "Approved"),
]

for fid, name, co2, ch4, n2o, co, unit, fac_id, reg, status in factors:
    c.execute("DELETE FROM custom_factors WHERE id=?", (fid,))
    c.execute('''
        INSERT INTO custom_factors (id, name, co2_factor, ch4_factor, n2o_factor, co_factor, unit, facility_id, region, status, created_at, updated_at, is_archived, is_test)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 0)
    ''', (fid, name, co2, ch4, n2o, co, unit, fac_id, reg, status, now_str, now_str))

conn.commit()
print("Registered custom factors 101, 102, 103, 104 successfully!")
conn.close()
