import sqlite3

conn = sqlite3.connect('new/server/ghg_app.db')
conn.row_factory = sqlite3.Row
c = conn.cursor()

print("--- Facilities ---")
c.execute("SELECT id, name, code, boundary_type, equity_share_pct FROM facilities")
facilities = c.fetchall()
for f in facilities:
    print(dict(f))

print("\n--- Emissions summary by facility and year ---")
c.execute("""
    SELECT facility_id, year, count(*), sum(co2e_total), sum(co2_emissions), sum(ch4_emissions), sum(n2o_emissions)
    FROM emissions
    GROUP BY facility_id, year
""")
for r in c.fetchall():
    print(dict(r))

print("\n--- Scope 2 summary by facility and year ---")
c.execute("""
    SELECT facility_id, year, count(*), sum(co2e)
    FROM scope2_emissions
    GROUP BY facility_id, year
""")
for r in c.fetchall():
    print(dict(r))

print("\n--- Emission sources table ---")
c.execute("SELECT count(*) FROM emission_sources")
print("emission_sources count:", c.fetchone()[0])
c.execute("SELECT * FROM emission_sources LIMIT 10")
for r in c.fetchall():
    print(dict(r))
