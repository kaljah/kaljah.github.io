import sys, json
sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/tools")
from auditlib import api_client
c = api_client("agentI_sweep","it_admin")
for p in ["/api/dashboard/flaring-summary?year=2024","/api/dashboard/granular-intensities?year=2024","/api/dashboard/base-year","/api/dashboard/goals/2024","/api/cap/limits","/api/equity/partners","/api/audit/?per_page=3","/api/scope2/emission-factors"]:
    r=c.get(p); print(p, r.status_code, r.get_data(as_text=True)[:600]); print()
