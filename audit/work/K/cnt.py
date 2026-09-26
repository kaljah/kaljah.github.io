import sys; sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/tools")
from auditlib import api_client
c = api_client("ui_k_scratch", "admin")
for q in ["scope=all", "scope=all&division=Upstream"]:
    r = c.get("/api/emissions/export?format=json&"+q); j=r.get_json()
    n = len(j) if isinstance(j, list) else (len(j.get("data", j.get("emissions", []))) if isinstance(j, dict) else None)
    print(q, r.status_code, n, (list(j.keys())[:5] if isinstance(j, dict) else ""))
