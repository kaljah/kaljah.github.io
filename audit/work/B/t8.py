import sys, json; sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/tools")
from auditlib import api_client, sql
import logging; logging.disable(logging.CRITICAL)
c = api_client("agentB_s2","admin")
print(c.get("/api/dashboard/summary?year=2030").get_json())
