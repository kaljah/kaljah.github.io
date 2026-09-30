import sys, json; sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/tools")
from auditlib import api_client, sql
DB="agentH_scen"
a=api_client(DB,"admin")
r=a.get("/api/goals"); print(r.status_code, r.get_data(as_text=True)[:200])
r=a.get("/api/dashboard/goals/2025"); print(r.status_code, r.get_data(as_text=True)[:200])
r=a.get("/api/dashboard/batch?year=2025"); txt=r.get_data(as_text=True); i=txt.find('"goal"'); print(r.status_code, txt[i:i+80])
try: json.loads(txt, parse_constant=lambda c: (_ for _ in ()).throw(ValueError(c))); print("strict ok")
except Exception as e: print("strict JSON parse fails:", e)
# NaN rate target latest
r=a.post("/api/manage/sbti",data='{"base_year":2020,"base_year_emissions":1000,"target_year":2030,"reduction_rate_pct":NaN}',content_type="application/json"); print(r.status_code)
r=a.get("/api/dashboard/sbti-trajectory"); print("traj w/ NULL rate", r.status_code, r.get_data(as_text=True)[:300])
r=a.get("/api/manage/sbti"); print("manage", r.status_code, r.get_data(as_text=True)[:300])
r=a.post("/api/manage/sbti",data='{"base_year":2020,"base_year_emissions":Infinity,"target_year":2030,"reduction_rate_pct":4.2}',content_type="application/json"); print(r.status_code)
r=a.get("/api/dashboard/sbti-trajectory"); print("traj w/ inf", r.status_code, r.get_data(as_text=True)[:300])
