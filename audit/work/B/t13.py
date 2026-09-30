import sys; sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/tools")
from auditlib import api_client
import logging; logging.disable(logging.CRITICAL)
c = api_client("agentB_bulk","admin")
print(c.get("/api/dashboard/summary?year=2038&includePending=true").get_json())
