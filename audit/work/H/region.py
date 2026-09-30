import sys
sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/repro")
from _H_scenario import build, TARGET
from auditlib import api_client
DB = "agentH_region"
build(DB)
a = api_client(DB, "admin"); assert a.post("/api/manage/sbti", json=TARGET).status_code == 201
u = api_client(DB, "user")
d = u.get("/api/dashboard/sbti-trajectory").get_json()
print({k: d[k] for k in ["latest_actual_year","base_year_emissions","current_actual","current_target","reduction_achieved_pct","on_track"]})
print([ (t["year"], t["actual"]) for t in d["trajectory"] if t["actual"] is not None])
print("user manage GET:", u.get("/api/manage/sbti?base_year=2023").get_json())
d = a.get("/api/dashboard/sbti-trajectory?facility_id=4").get_json()
print("admin facility 4 (no data):", {k: d[k] for k in ["latest_actual_year","current_actual","current_target","reduction_achieved_pct","on_track"]})
