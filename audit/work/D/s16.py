import sys, json; sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/tools")
from auditlib import api_client
c = api_client("agentD", "admin")
a = c.get("/api/dashboard/flaring-summary?facilityId=all&activity=all&division=all&year=2025").get_json()
b = c.get("/api/dashboard/flaring-summary?facilityId=all&activity=all&division=all&year=2025&gwp_horizon=20").get_json()
print(a == b)
print(json.dumps(a)[:600])
