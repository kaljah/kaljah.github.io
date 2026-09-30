import sys, json; sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/tools")
from auditlib import api_client, sql
c = api_client("agentD", "admin")
r = c.get("/api/dashboard/batch-all?facilityId=all&activity=all&division=all")
b = r.get_json()
print(r.status_code, b.keys())
s = b["summary"]
print("summary ch4 sum", sum(x.get("ch4_total",0) for x in s))
print(sql("agentD","select sum(ch4_emissions) s from emissions where status='Verified'"))
r20 = c.get("/api/dashboard/batch-all?facilityId=all&activity=all&division=all&gwp_horizon=20").get_json()
for x,y in zip(s, r20["summary"]):
    print(x["year"], x["scope1_total"], y["scope1_total"], x["ch4_total"], y["ch4_total"])
print("pending", b["pending_stats"], r20["pending_stats"])
