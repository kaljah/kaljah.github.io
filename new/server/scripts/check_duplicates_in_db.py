import sqlite3

con = sqlite3.connect("new/server/ghg_app.db")
cur = con.cursor()

for t in ["custom_factors", "mitigation_projects", "emission_sources", "scope3_emissions"]:
    print(f"\n--- {t} columns ---")
    cols = [c[1] for c in cur.execute(f"PRAGMA table_info({t})").fetchall()]
    print(cols)
    print(f"Total rows: {cur.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0]}")

print("\n--- custom_factors sample ---")
for r in cur.execute("SELECT * FROM custom_factors LIMIT 10").fetchall():
    print(r)

print("\n--- mitigation_projects sample ---")
for r in cur.execute("SELECT * FROM mitigation_projects LIMIT 10").fetchall():
    print(r)
