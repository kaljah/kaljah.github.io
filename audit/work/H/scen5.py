import sys, json
sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/repro")
from _H_scenario import build, TARGET
from auditlib import api_client
DB = "agentH_scen5"
build(DB)
c = api_client(DB, "admin")
c.post("/api/manage/sbti", json=TARGET)
r = c.post("/api/base-years", json={"year": 2020, "reason": "acquisition", "previous_emissions": 1000, "adjusted_emissions": 1200}); print("recalc", r.status_code)
d = c.get("/api/dashboard/sbti-trajectory").get_json(); print("traj baseline after recalc:", d["base_year_emissions"], d["reduction_achieved_pct"])
print("manage GET:", c.get("/api/manage/sbti").get_json())
print("base-year:", c.get("/api/dashboard/base-year").get_json())
# dashboard consistency for 2023
b = c.get("/api/dashboard/batch-all?year=2023").get_json()
s12 = sum((r.get("scope1_total") or 0)+(r.get("scope2_total") or 0) for r in b["summary"]); s3=b["scope3_summary"]["total"]
row = [t for t in d["trajectory"] if t["year"]=="2023"][0]
print("dashboard 2023 S1+S2", s12, "S3", s3, "| sbti 2023 scope12", row["scope12"], "scope3", row["scope3"])
# pathway/rate mismatch
r = c.post("/api/manage/sbti", json={**TARGET, "pathway_type": "1.5C", "reduction_rate_pct": 0.5}); print("1.5C@0.5%", r.status_code)
r = c.post("/api/manage/sbti", json={**TARGET, "pathway_type": "foo"}); print("pathway foo", r.status_code)
r = c.post("/api/manage/sbti", json={**TARGET, "base_year": 2030, "target_year": 2031}); print("future base 2030", r.status_code)
# snapshot consistency
