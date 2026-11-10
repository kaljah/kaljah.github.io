import sqlite3
import json
from datetime import datetime, timezone

conn = sqlite3.connect("new/server/ghg_app.db")
c = conn.cursor()

now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

with open("scripts/full_reconciled_sources.json", "r", encoding="utf-8") as f:
    sources = json.load(f)

# Define custom factors mapping for all streams
# For each source with non-zero activity, calculate the exact factor if not already standard
custom_factors_list = []

# HBNS Streams:
# 1. HBNS Fuel Gas (combustion): co2=2.896638, ch4=0.00005077, n2o=0.00001421 kg/m3
custom_factors_list.append((101, "HBNS Fuel Gas", 2.896638, 0.00005077, 0.00001421, 0.0, "kg/m3", 37, "HBNS", "Approved"))
# 2. El Merk Fuel Gas (combustion): co2=2.945717, ch4=0.00005064, n2o=0.00001415 kg/m3
custom_factors_list.append((102, "El Merk Fuel Gas", 2.945717, 0.00005064, 0.00001415, 0.0, "kg/m3", 38, "El Merk", "Approved"))
# 3. HBNS Flare Gas: co2=2.839556, ch4=0.009767, n2o=0.000037 kg/m3
custom_factors_list.append((103, "HBNS Flare Gas", 2.839556, 0.009767, 0.000037, 0.0, "kg/m3", 37, "HBNS", "Approved"))
# 4. El Merk Flare Gas: co2=2.839556, ch4=0.009767, n2o=0.000037 kg/m3
custom_factors_list.append((104, "El Merk Flare Gas", 2.839556, 0.009767, 0.000037, 0.0, "kg/m3", 38, "El Merk", "Approved"))
# 5. HBNS CPF Venting: co2=0.015538, ch4=0.686392, n2o=0.0 kg/m3
custom_factors_list.append((105, "HBNS CPF Venting Gas", 0.015538, 0.686392, 0.0, 0.0, "kg/m3", 37, "HBNS", "Approved"))
# 6. El Merk CPF Venting: co2=0.034301, ch4=0.685852, n2o=0.0 kg/m3
custom_factors_list.append((106, "El Merk CPF Venting Gas", 0.034301, 0.685852, 0.0, 0.0, "kg/m3", 38, "El Merk", "Approved"))
# 7. HBNS Produced Water Tank: ch4=0.004289 g/bbl -> 0.000000004289 tonne/bbl -> 0.000004289 kg/bbl
custom_factors_list.append((107, "HBNS Produced Water Tank", 0.0, 0.000004289, 0.0, 0.0, "kg/bbl", 37, "HBNS", "Approved"))
# 8. El Merk Produced Water Tank: ch4=0.004270 g/bbl -> 0.00000427 kg/bbl
custom_factors_list.append((108, "El Merk Produced Water Tank", 0.0, 0.00000427, 0.0, 0.0, "kg/bbl", 38, "El Merk", "Approved"))
# 9. HBNS Diesel (On-Road): co2=2.681966, ch4=0.001487, n2o=0.000293 kg/L
custom_factors_list.append((109, "HBNS Diesel On-Road", 2.681966, 0.001487, 0.000293, 0.0, "kg/L", 37, "HBNS", "Approved"))
# 10. HBNS Gasoline (On-Road): co2=2.358988, ch4=0.004253, n2o=0.000308 kg/L
custom_factors_list.append((110, "HBNS Gasoline On-Road", 2.358988, 0.004253, 0.000308, 0.0, "kg/L", 37, "HBNS", "Approved"))
# 11. HBNS Diesel (Off-Road): co2=2.682086, ch4=0.003571, n2o=0.000374 kg/L
custom_factors_list.append((111, "HBNS Diesel Off-Road", 2.682086, 0.003571, 0.000374, 0.0, "kg/L", 37, "HBNS", "Approved"))
# 12. El Merk Heavy Duty Diesel: co2=2.681967, ch4=0.001486, n2o=0.000290 kg/L
custom_factors_list.append((112, "El Merk Heavy Duty Diesel", 2.681967, 0.001486, 0.000290, 0.0, "kg/L", 38, "El Merk", "Approved"))
# 13. El Merk Light Duty Diesel: co2=2.681993, ch4=0.001488, n2o=0.000292 kg/L
custom_factors_list.append((113, "El Merk Light Duty Diesel", 2.681993, 0.001488, 0.000292, 0.0, "kg/L", 38, "El Merk", "Approved"))
# 14. El Merk Light Duty Gasoline: co2=2.359050, ch4=0.004251, n2o=0.000305 kg/L
custom_factors_list.append((114, "El Merk Light Duty Gasoline", 2.359050, 0.004251, 0.000305, 0.0, "kg/L", 38, "El Merk", "Approved"))
# 15. HBNS Diesel ICE: 399.9 m3 -> 1073.33 t CO2, 0.211 t CH4, 0.009 t N2O
custom_factors_list.append((115, "HBNS Diesel ICE", 2683.996, 0.5276, 0.0225, 0.0, "kg/m3", 37, "HBNS", "Approved"))
# 16. El Merk Diesel ICE: 535.4 m3 -> 1437.17 t CO2, 0.282 t CH4, 0.012 t N2O
custom_factors_list.append((116, "El Merk Diesel ICE", 2684.292, 0.5267, 0.0224, 0.0, "kg/m3", 38, "El Merk", "Approved"))
# 17. HBNS STP: 58197 m3 -> 6.52 t CO2 -> 0.112033 kg/m3
custom_factors_list.append((117, "HBNS STP Wastewater", 0.112033, 0.0, 0.0, 0.0, "kg/m3", 37, "HBNS", "Approved"))
# 18. El Merk STP: 73952.7 m3 -> 8.28 t CO2 -> 0.111963 kg/m3
custom_factors_list.append((118, "El Merk STP Wastewater", 0.111963, 0.0, 0.0, 0.0, "kg/m3", 38, "El Merk", "Approved"))
# 19. HBNS Fire Suppressant: 0.62 kg -> 0.62 t CO2e
custom_factors_list.append((119, "HBNS Fire Suppressant", 1000.0, 0.0, 0.0, 0.0, "kg/kg", 37, "HBNS", "Approved"))
# 20. El Merk Fire Suppressant: 1.22 kg -> 1.22 t CO2e
custom_factors_list.append((120, "El Merk Fire Suppressant", 1000.0, 0.0, 0.0, 0.0, "kg/kg", 38, "El Merk", "Approved"))
# 21. HBNS Gas Leaks: 1 unit -> 13.97 t CO2, 1.084 t CH4
custom_factors_list.append((121, "HBNS Gas Leaks", 13970.0, 1084.0, 0.0, 0.0, "kg/event", 37, "HBNS", "Approved"))
# 22. HBNS Crude Oil Leaks: 1 unit -> 0.02 t CO2
custom_factors_list.append((122, "HBNS Crude Oil Leaks", 20.0, 0.0, 0.0, 0.0, "kg/event", 37, "HBNS", "Approved"))
# 23. El Merk Gas Leaks: 1 unit -> 1.20 t CO2
custom_factors_list.append((123, "El Merk Gas Leaks", 1200.0, 0.0, 0.0, 0.0, "kg/event", 38, "El Merk", "Approved"))
# 24. El Merk Crude Oil Leaks: 1 unit -> 0.02 t CO2
custom_factors_list.append((124, "El Merk Crude Oil Leaks", 20.0, 0.0, 0.0, 0.0, "kg/event", 38, "El Merk", "Approved"))
# 25. HBNS Purchased Electricity: 100,000 kWh -> 55.0 t CO2 -> 0.55 kg/kWh
custom_factors_list.append((125, "HBNS Purchased Electricity", 0.55, 0.00001, 0.0, 0.0, "kg/kWh", 37, "HBNS", "Approved"))

# Insert all
for fid, name, co2, ch4, n2o, co, unit, fac_id, reg, status in custom_factors_list:
    c.execute("DELETE FROM custom_factors WHERE id=?", (fid,))
    c.execute('''
        INSERT INTO custom_factors (id, name, co2_factor, ch4_factor, n2o_factor, co_factor, unit, facility_id, region, status, created_at, updated_at, is_archived, is_test)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 0)
    ''', (fid, name, co2, ch4, n2o, co, unit, fac_id, reg, status, now_str, now_str))

conn.commit()
print(f"Configured {len(custom_factors_list)} custom factors in database!")
conn.close()
