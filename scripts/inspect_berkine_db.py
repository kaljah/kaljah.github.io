import sqlite3

conn = sqlite3.connect('new/server/ghg_app.db')
conn.row_factory = sqlite3.Row
c = conn.cursor()

c.execute("SELECT * FROM emissions WHERE facility_id IN (37, 38) ORDER BY facility_id, year, process_type")
rows = c.fetchall()
print(f"Total emissions rows for HBNS/ELM: {len(rows)}")
for r in rows:
    print(r['facility_id'], r['year'], r['record_id'], r['process_type'], r['fuel_type'], r['quantity'], r['unit'], r['co2e_total'], r['co2_emissions'], r['ch4_emissions'], r['n2o_emissions'])

c.execute("SELECT * FROM scope2_emissions WHERE facility_id IN (37, 38) ORDER BY facility_id, year")
rows2 = c.fetchall()
print(f"\nTotal scope2 rows for HBNS/ELM: {len(rows2)}")
for r in rows2:
    print(r['facility_id'], r['year'], r['co2e'], r['electricity_kwh'], r['status'])
