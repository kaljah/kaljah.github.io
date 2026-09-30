"""SBTi summary with no actual data in the target window reports 100 % reduction and ON TRACK."""
import sys
sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/repro")
from _H_scenario import build
from auditlib import api_client
DB = "agentH_BUG028"
build(DB)
c = api_client(DB, "admin")
# Target with base year 2024: no Verified data exists for 2024..2030 in the scenario
assert c.post("/api/manage/sbti", json={"base_year": 2024, "base_year_emissions": 1000, "target_year": 2030,
                                         "reduction_rate_pct": 4.2, "pathway_type": "1.5C"}).status_code == 201
d = c.get("/api/dashboard/sbti-trajectory").get_json()
act = (d["reduction_achieved_pct"], d["on_track"])
print("expected: reduction% = None/'no data', on_track = None (not evaluable)")
print("actual  : reduction% =", act[0], ", on_track =", act[1], ", current_actual =", d["current_actual"], ", latest_actual_year =", d["latest_actual_year"])
sys.exit(1 if act == (100.0, True) else 0)
