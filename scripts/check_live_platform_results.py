import sqlite3
import json

conn = sqlite3.connect("new/server/ghg_app.db")
c = conn.cursor()

# 1. Total records count in database
total_rec = c.execute("SELECT count(*) FROM emissions WHERE year=2022 AND facility_id IN (37, 38)").fetchone()[0]
print(f"Total 2022 records in database: {total_rec}")

# 2. HBNS breakdown by process
print("\n--- HBNS 2022 BREAKDOWN BY PROCESS ---")
for r in c.execute('''
    SELECT process_type, count(*), sum(quantity), sum(co2_emissions), sum(ch4_emissions), sum(n2o_emissions), sum(co2e_total)
    FROM emissions WHERE year=2022 AND facility_id=37 GROUP BY process_type
''').fetchall():
    print(f"  {r[0]:15} | count: {r[1]:2} | co2: {r[3]:10.2f} | ch4: {r[4]:8.3f} | n2o: {r[5]:8.3f} | total_co2e: {r[6]:12.2f}")

hbns_sum = c.execute("SELECT sum(co2e_total) FROM emissions WHERE year=2022 AND facility_id=37").fetchone()[0]
print(f"  TOTAL HBNS: {hbns_sum:12.2f} t CO2e")

# 3. El Merk breakdown by process
print("\n--- EL MERK 2022 BREAKDOWN BY PROCESS ---")
for r in c.execute('''
    SELECT process_type, count(*), sum(quantity), sum(co2_emissions), sum(ch4_emissions), sum(n2o_emissions), sum(co2e_total)
    FROM emissions WHERE year=2022 AND facility_id=38 GROUP BY process_type
''').fetchall():
    print(f"  {r[0]:15} | count: {r[1]:2} | co2: {r[3]:10.2f} | ch4: {r[4]:8.3f} | n2o: {r[5]:8.3f} | total_co2e: {r[6]:12.2f}")

elm_sum = c.execute("SELECT sum(co2e_total) FROM emissions WHERE year=2022 AND facility_id=38").fetchone()[0]
print(f"  TOTAL EL MERK: {elm_sum:12.2f} t CO2e")
print(f"\nGRAND TOTAL: {hbns_sum + elm_sum:12.2f} t CO2e")

conn.close()
