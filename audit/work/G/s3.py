import sys, json; sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/tools")
from auditlib import api_client, sql
c = api_client("agentG", "admin")
base = {"year":2031,"month":1,"facility_id":4,"process_type":"stationary_combustion","fuel":"Natural Gas","quantity":1000,"unit":"m3","factor_source":"default"}
r = c.post("/api/emissions/", json=base); print(r.status_code, json.dumps(r.get_json())[:1500])
