"""Dashboard '% GOAL' badge (year=All, the default) divides the all-years S1+S2 total by the single current-year goal."""
import sys, json, datetime
sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/repro")
from _H_scenario import build
from auditlib import api_client
DB = "agentH_BUG041"
build(DB)
c = api_client(DB, "admin")
cy = datetime.date.today().year
assert c.post("/api/goals", json={"year": cy, "target_amount": 1000}).status_code in (200, 201)
b = c.get("/api/dashboard/batch-all").get_json()           # what DashboardEnhanced requests for year = "all"
# Replicate DashboardEnhanced.jsx lines ~290-305 + 1136-1150 exactly: totals over ALL summary rows (S1+S2)
total = sum((r.get("scope1_total") or 0) + (r.get("scope2_total") or 0) for r in b["summary"])
badge = total / b["goal"]["target_amount"] * 100
cur_year_actual = sum((r.get("scope1_total") or 0) + (r.get("scope2_total") or 0) for r in b["summary"] if int(r["year"]) == cy)
print(f"goal returned: {b['goal']}")
print(f"expected badge (current-year S1+S2 {cur_year_actual} / goal 1000): {cur_year_actual/10:.1f}% GOAL  (or no badge in All-years view)")
print(f"actual badge  (all-years S1+S2 {total} / goal 1000): {badge:.1f}% GOAL")
sys.exit(1 if abs(badge - cur_year_actual/10) > 1e-6 else 0)
