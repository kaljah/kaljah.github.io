import sys; sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/tools")
from auditlib import make_db, api_client, sql
DB="agentD_survey"; make_db(DB, overwrite=True)
c = api_client(DB, "admin")
# facility 169: 2025 Verified bottom-up 772.46 tCH4
bu = sql(DB,"select sum(ch4_emissions) s from emissions where facility_id=169 and year=2025 and status='Verified'")[0]["s"]
print(sql(DB,"select id,name,activity,segment from facilities where id in (169, 46)"))
r = c.post("/api/data/ogmp-surveys", json={"facility_id":169,"year":2025,"survey_date":"2025-06-01","survey_type":"Aerial","measured_rate_kg_hr":400})
print(r.status_code, r.get_json())
sid = r.get_json().get("id")
print("stored:", sql(DB,"select estimated_annual_tch4, bottom_up_tch4, variance_pct, variance_flag, reconciliation_status from ogmp_surveys where id=?",(sid,)))
g = [s for s in c.get("/api/data/ogmp-surveys?facilityId=169").get_json() if s["id"]==sid][0]
print("GET:", {k:g[k] for k in ("estimated_annual_tch4","bottom_up_tch4","variance_pct","variance_flag","reconciliation_status")})
print("expected variance", (400*8760/1000 - bu)/bu*100)
# zero-bottom-up facility (2024: none)
r = c.post("/api/data/ogmp-surveys", json={"facility_id":169,"year":2022,"survey_date":"2022-06-01","measured_rate_kg_hr":50})
sid2 = r.get_json().get("id"); print(r.status_code)
g = [s for s in c.get("/api/data/ogmp-surveys?facilityId=169").get_json() if s["id"]==sid2][0]
print("stored2:", sql(DB,"select bottom_up_tch4, variance_pct, variance_flag, reconciliation_status from ogmp_surveys where id=?",(sid2,)))
print("GET2:", {k:g[k] for k in ("bottom_up_tch4","variance_pct","variance_flag","reconciliation_status")})
r = c.post("/api/data/ogmp-surveys", json={"facility_id":169,"year":2010,"survey_date":"2010-06-01","measured_rate_kg_hr":50})
sid3 = r.get_json().get("id")
g = [s for s in c.get("/api/data/ogmp-surveys?facilityId=169").get_json() if s["id"]==sid3][0]
print("stored3:", sql(DB,"select bottom_up_tch4, variance_pct, variance_flag, reconciliation_status from ogmp_surveys where id=?",(sid3,)))
print("GET3:", {k:g[k] for k in ("bottom_up_tch4","variance_pct","variance_flag","reconciliation_status")})
