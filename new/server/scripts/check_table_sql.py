import sqlite3

con = sqlite3.connect("new/server/ghg_app.db")
cur = con.cursor()
for t in ['custom_factors', 'mitigation_projects', 'emission_sources', 'scope3_emissions']:
    row = cur.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (t,)).fetchone()
    print(f"=== {t} ===")
    if row:
        print(row[0])
    indexes = cur.execute("SELECT name, sql FROM sqlite_master WHERE type='index' AND tbl_name=?", (t,)).fetchall()
    print("Indexes:")
    for idx_name, idx_sql in indexes:
        print(f"  {idx_name}: {idx_sql}")
