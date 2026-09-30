import sys, json; sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/tools")
from auditlib import api_client, sql
c = api_client("agentB","admin")
base={"source_type":"Combustion","facility_id":1,"year":2024,"month":7,"process_type":"Combustion","fuel":"Natural Gas","unit":"MMBtu"}
for amt in (-1000, "-1000", "1e400", "nan"):
    r=c.post("/api/emissions/", json={**base,"amount":amt}); j=r.get_json(silent=True)
    print(amt, r.status_code, j if r.status_code!=201 else sql("agentB","select quantity,co2e_total,status from emissions where id=?",(j["id"],)))
r=c.post("/api/emissions/", json={**base,"quantity":-1000}); print("quantity -1000", r.status_code)
