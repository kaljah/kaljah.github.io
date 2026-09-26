import sys, json; sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/tools")
from auditlib import api_client, sql
c = api_client("agentB","admin")
base={"source_type":"Combustion","sub_type":"Stationary","facility_id":1,"year":2024,"month":7,"process_type":"Combustion"}
r=c.post("/api/emissions/", json={**base,"fuel":"Natural Gas","fuel_type":"Natural Gas","amount":1000,"quantity":1000,"unit":"MMBtu"}); i=r.get_json()["id"]
print(sql("agentB","select quantity,co2e_total from emissions where id=?",(i,)))
r=c.put(f"/api/emissions/{i}", json={"quantity":2000}); print(r.status_code, r.get_json())
print("after PUT quantity=2000:", sql("agentB","select quantity,co2e_total from emissions where id=?",(i,)), "expected co2e ~106.23")
