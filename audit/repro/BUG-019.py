"""SBTi scope toggle (s1_s2 / s3) compares scope-subset actuals to the all-scope baseline and target."""
import sys
sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/repro")
from _H_scenario import build, TARGET
from auditlib import api_client
DB = "agentH_BUG019"
build(DB)
c = api_client(DB, "admin")
sug = c.get("/api/manage/sbti?base_year=2020").get_json()["suggested_base_year_emissions"]
print("auto-fill baseline for 2020 (S1+S2+S3):", sug)
assert c.post("/api/manage/sbti", json=TARGET).status_code == 201
fail = False
# hand math: S1+S2 baseline 800, 2023 S1+S2 = 750 -> reduction 6.25 %, target 800*(1-0.126)=699.2 -> off track
#            S3 baseline 200, 2023 S3 = 200 -> reduction 0 %, target 174.8 -> off track
for scope, exp in [("s1_s2", (750.0, 699.2, 6.25, False)), ("s3", (200.0, 174.8, 0.0, False))]:
    d = c.get(f"/api/dashboard/sbti-trajectory?scope={scope}").get_json()
    act = (d["current_actual"], d["current_target"], d["reduction_achieved_pct"], d["on_track"])
    print(scope, "expected (actual, target, reduction%, on_track):", exp, " actual:", act)
    fail |= act != exp
sys.exit(1 if fail else 0)
