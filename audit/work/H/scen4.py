import sys, json; sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/tools")
from auditlib import api_client, sql
DB="agentH_scen"
a=api_client(DB,"admin")
print(sql(DB,"select * from goals where year in (1,2025)"))
for y in ["2025","2024"]:
    r=a.get(f"/api/dashboard/batch-all?year={y}"); print(y, r.status_code, r.get_data(as_text=True)[:200])
