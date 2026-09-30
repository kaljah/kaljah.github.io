import sys
sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/tools")
from auditlib import api_client
c = api_client("agentH_scen5", "admin")
for q in ["year=2023","year=all",""]:
    b=c.get("/api/dashboard/batch-all?"+q).get_json(); print(q, b["summary"], b["scope3_summary"])
