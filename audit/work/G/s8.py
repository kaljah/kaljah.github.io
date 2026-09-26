import sys, json; sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/tools")
from auditlib import api_client
c = api_client("agentG", "admin")
print(c.get("/api/dashboard/uncertainty?year=2090").get_json())
print(c.get("/api/dashboard/uncertainty?year=2026&facility_id=99999").get_json())
c2 = api_client("agentG", "user")
print(c2.get("/api/dashboard/uncertainty?year=2026").get_json()["inventory_uncertainty_pct"])
