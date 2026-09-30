"""SBTi pathway label is not tied to the reduction rate: '1.5C' with 0.5 %/yr, arbitrary pathway strings and future base years are accepted."""
import sys
sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/repro")
from _H_scenario import build, TARGET
from auditlib import api_client
DB = "agentH_BUG059"
build(DB)
c = api_client(DB, "admin")
cases = [("1.5C at 0.5%/yr", {**TARGET, "reduction_rate_pct": 0.5}),
         ("pathway 'foo'", {**TARGET, "pathway_type": "foo"}),
         ("base year 2030 (future)", {**TARGET, "base_year": 2030, "target_year": 2031})]
bad = 0
for label, body in cases:
    r = c.post("/api/manage/sbti", json=body)
    print(f"{label}: expected 400, actual {r.status_code}")
    bad += r.status_code != 400
c.post("/api/manage/sbti", json={**TARGET, "reduction_rate_pct": 0.5})
d = c.get("/api/dashboard/sbti-trajectory").get_json()
# 1.5C linear minimum 4.2%/yr -> 2030 target should be <= 1000*(1-0.042*10) = 580 t
print(f"pathway shown '{d['pathway_type']}', target_emissions_final {d['target_emissions_final']} (1.5C-aligned would be <= 580.0)")
sys.exit(1 if bad else 0)
