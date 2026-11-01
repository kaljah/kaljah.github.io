import sqlite3
import json

conn = sqlite3.connect('new/server/ghg_app.db')
c = conn.cursor()

c.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [r[0] for r in c.fetchall() if not r[0].startswith('sqlite_')]

results = {
    "tables_with_none_string": [],
    "facilities": [],
    "mitigation_projects": [],
    "emission_sources": [],
    "custom_factors": [],
    "users": []
}

for t in tables:
    c.execute(f"PRAGMA table_info({t})")
    cols = [r[1] for r in c.fetchall()]
    for col in cols:
        try:
            c.execute(f"SELECT id, {col} FROM {t} WHERE {col} = 'None' OR {col} = 'none'")
            rows = c.fetchall()
            if rows:
                results["tables_with_none_string"].append({
                    "table": t,
                    "column": col,
                    "rows": rows
                })
        except Exception:
            pass

# Facilities / Regions: 'rz', 'RNSaz'
c.execute("SELECT id, name, location, region, is_test FROM facilities WHERE name IN ('rz', 'RNSaz') OR region IN ('rz', 'RNSaz') OR location IN ('rz', 'RNSaz')")
results["facilities"] = [
    {"id": r[0], "name": r[1], "location": r[2], "region": r[3], "is_test": bool(r[4]) if r[4] is not None else False}
    for r in c.fetchall()
]

# Mitigation Projects: name is None, empty, or test
c.execute("SELECT id, facility_id, name, project_type, quantity_tco2e, is_test FROM mitigation_projects WHERE name = 'None' OR name IS NULL OR LOWER(name) = 'none' OR name LIKE '%test%' OR is_test = 1")
results["mitigation_projects"] = [
    {"id": r[0], "facility_id": r[1], "name": r[2], "project_type": r[3], "quantity_tco2e": r[4], "is_test": bool(r[5]) if r[5] is not None else False}
    for r in c.fetchall()
]

# Emission Sources: 'Probe Source'
c.execute("SELECT id, facility_id, name, equipment_id, type, is_test FROM emission_sources WHERE name LIKE '%Probe%' OR name = 'None' OR name IS NULL OR LOWER(name) = 'none' OR is_test = 1")
results["emission_sources"] = [
    {"id": r[0], "facility_id": r[1], "name": r[2], "equipment_id": r[3], "type": r[4], "is_test": bool(r[5]) if r[5] is not None else False}
    for r in c.fetchall()
]

# Custom Factors: 'Combustion' with CO2=CH4=N2O=1
c.execute("SELECT id, name, co2_factor, ch4_factor, n2o_factor, unit, is_test FROM custom_factors WHERE name = 'Combustion' OR (co2_factor = 1.0 AND ch4_factor = 1.0 AND n2o_factor = 1.0) OR is_test = 1")
results["custom_factors"] = [
    {"id": r[0], "name": r[1], "co2_factor": r[2], "ch4_factor": r[3], "n2o_factor": r[4], "unit": r[5], "is_test": bool(r[6]) if r[6] is not None else False}
    for r in c.fetchall()
]

# Users: 'a@a', '@audit.test'
c.execute("SELECT id, email, fullName, role, is_test FROM users WHERE email LIKE '%a@a%' OR email LIKE '%@audit.test%' OR is_test = 1")
results["users"] = [
    {"id": r[0], "email": r[1], "fullName": r[2], "role": r[3], "is_test": bool(r[4]) if r[4] is not None else False}
    for r in c.fetchall()
]

with open("new/server/reports/junk_test_data_dryrun.json", "w", encoding="utf-8") as out:
    json.dump(results, out, indent=2)

print(json.dumps(results, indent=2))
