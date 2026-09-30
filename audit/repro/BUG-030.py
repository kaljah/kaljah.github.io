"""BUG-030 repro: POST with fuel_type/quantity stores NULL quantity/fuel_type."""
import sys; sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/tools")
from auditlib import make_db, api_client, sql
DB="agentB_r030"; make_db(DB, overwrite=True)
c = api_client(DB,"admin")
r=c.post("/api/emissions/", json={"process_type":"Combustion","source_type":"Combustion","facility_id":1,"year":2024,"month":7,"fuel_type":"Coal","quantity":1000,"unit":"tonnes"})
row=sql(DB,"select fuel_type,quantity,co2e_total from emissions where id=?",(r.get_json()["id"],))[0]
print("expected fuel_type=Coal quantity=1000; actual", row)
sys.exit(1 if row["quantity"]!=1000 or row["fuel_type"]!="Coal" else 0)
