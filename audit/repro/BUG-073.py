"""BUG-073 repro: Scope 2 / Scope 3 POST accepts missing/non-numeric year; one such Scope 2 row makes /api/dashboard/summary and /batch-all return 500 for all users; Scope 3 null-year row is in total but not by_year."""
import sys; sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/tools")
from auditlib import make_db, api_client, sql
import logging; logging.disable(logging.CRITICAL)
DB="agentB_rnull"; make_db(DB, overwrite=True)
c = api_client(DB,"admin")
b0=c.get("/api/dashboard/batch-all").status_code
r=c.post("/api/scope2", json={"facility_id":1,"source_type":"electricity","electricity_kwh":1000,"emission_factor":0.5})
print("scope2 without year ->", r.status_code, "(expected 422)")
s=c.get("/api/dashboard/summary").status_code; b=c.get("/api/dashboard/batch-all").status_code
u=api_client(DB,"user"); su=u.get("/api/dashboard/batch-all").status_code
print(f"batch-all before={b0}; after: summary={s} batch-all={b} (admin), batch-all as West user={su}; expected 200")
r3=c.post("/api/scope3", json={"facility_id":1,"category":"Category 1","activity_data":1000,"emission_factor":0.5})
j=c.get("/api/dashboard/scope3/summary").get_json()
print("scope3 without year ->", r3.status_code, "; scope3 total", j["total"], "sum(by_year)", sum(j["by_year"].values()))
sys.exit(1 if r.status_code==201 or s==500 or b==500 else 0)
