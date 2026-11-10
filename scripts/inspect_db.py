import sqlite3

conn = sqlite3.connect('new/server/ghg_app.db')
c = conn.cursor()
c.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [r[0] for r in c.fetchall()]
print("Tables:", tables)

for t in ["facilities", "emissions", "scope2_emissions", "flaring_details", "production_data", "jv_partners", "facility_equity_shares"]:
    if t in tables:
        c.execute(f"SELECT count(*) FROM {t}")
        print(f"{t}: {c.fetchone()[0]} rows")
