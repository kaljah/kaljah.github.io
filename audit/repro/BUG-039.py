"""POST /api/goals has no validation: NaN goal is stored as NULL and then breaks the main dashboard batch (500)."""
import sys, json, datetime
sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/repro")
from _H_scenario import build
from auditlib import api_client
DB = "agentH_BUG039"
build(DB)
c = api_client(DB, "admin")
cy = datetime.date.today().year
r1 = c.post("/api/goals", data=json.dumps({"year": 1, "target_amount": -5}), content_type="application/json")
r2 = c.post("/api/goals", data=f'{{"year": {cy}, "target_amount": NaN}}', content_type="application/json")
b = c.get("/api/dashboard/batch-all")          # default dashboard view (year=all -> goal of current year)
g = c.get(f"/api/dashboard/goals/{cy}")
print("expected: goal POSTs rejected (400); dashboard batch 200")
print(f"actual  : year=1/-5 t -> {r1.status_code}; NaN -> {r2.status_code}; /dashboard/batch-all -> {b.status_code}; /dashboard/goals/{cy} -> {g.status_code}")
sys.exit(1 if b.status_code != 200 or r1.status_code != 400 else 0)
