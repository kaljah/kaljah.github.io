"""CAP emissions: any data-entry user writes records directly as Verified (no maker-checker), negative/huge values accepted."""
import sys
sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/tools")
from auditlib import make_db, api_client, sql
DB="repro_BUG053"; make_db(DB, overwrite=True)
u = api_client(DB,"user")
r1 = u.post("/api/cap/emissions", json={"facility_id":1,"year":2025,"source_module":"combustion","pollutant":"NO2","concentration_mg_nm3":150,"flue_gas_volume_nm3":1e6})
r2 = u.post("/api/cap/emissions", json={"facility_id":1,"year":2025,"source_module":"flaring","pollutant":"SO2","mass_tonnes":-5000,"concentration_mg_nm3":-1})
r3 = u.post("/api/cap/emissions", json={"facility_id":1,"year":2025,"source_module":"x","pollutant":"CO","mass_tonnes":1,"status":"Verified"})
rows = sql(DB,"select id,source_module,pollutant,mass_tonnes,concentration_mg_nm3,status,created_by from cap_emissions where id in (?,?,?)",(r1.get_json()["id"],r2.get_json()["id"],r3.get_json()["id"]))
print("role=user responses:", r1.status_code, r2.status_code, r3.status_code)
for r in rows: print(r)
print("expected: role=user records stored as Pending (maker-checker) and negative mass/concentration rejected (400)")
bad = any(r["status"]=="Verified" for r in rows) or r2.status_code==200
print("actual:", [ (r["status"], r["mass_tonnes"]) for r in rows])
sys.exit(1 if bad else 0)
