"""SBTi progress uses the latest year with ANY verified data, incl. the current partial year."""
import sys, datetime
sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/repro")
from _H_scenario import build, TARGET
from auditlib import api_client
DB = "agentH_BUG014"
s1, s2, s3 = build(DB)
cy = datetime.date.today().year
s1(1, cy, 1, 50)          # one January record of the current (incomplete) year
c = api_client(DB, "admin")
assert c.post("/api/manage/sbti", json=TARGET).status_code == 201
d = c.get("/api/dashboard/sbti-trajectory").get_json()
# Expected (hand math): last complete reporting year with data = 2023, actual 950 t,
# target 1000*(1-0.042*3) = 874 t -> reduction 5.0 %, on_track False.
exp = (2023, 950.0, 874.0, 5.0, False)
act = (d["latest_actual_year"], d["current_actual"], d["current_target"], d["reduction_achieved_pct"], d["on_track"])
print("expected (year, actual, target, reduction%, on_track):", exp)
print("actual   (year, actual, target, reduction%, on_track):", act)
sys.exit(1 if act != exp else 0)
