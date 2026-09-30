import sys, json; sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/tools")
from auditlib import api_client, sql
c = api_client("agentB","admin")
base={"source_type":"Combustion","facility_id":1,"year":2024,"month":7,"process_type":"Combustion"}
r=c.post("/api/emissions/", json={**base,"fuel":"Natural Gas","amount":1e13,"unit":"MMBtu"}); i=r.get_json()["id"]
print(r.status_code, sql("agentB","select status,qa_flag,co2e_total from emissions where id=?",(i,)))
r=c.post("/api/emissions/", json={**base,"fuel":"Natural Gas","amount":1e300,"unit":"MMBtu"}); print(r.status_code, r.get_json())
