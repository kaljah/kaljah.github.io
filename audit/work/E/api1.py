import sys, json; sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/tools")
from auditlib import api_client
c = api_client("agentE", "admin")
for y in ["all","2021","2022","2023","2024","2025","2026"]:
    r = c.get(f"/api/dashboard/batch-all?year={y}")
    d = r.get_json(); st = d["intensity_stats"]
    E=sum(x["co2_intensity"]*x["total_boe"] for x in st if x["total_boe"]>0); B=sum(x["total_boe"] for x in st if x["total_boe"]>0)
    top = sorted(st, key=lambda x:-x["total_co2e"])[:3]
    print(y, r.status_code, len(st), "weighted kg/boe", E/B if B else None, "B", B, [(t["facility_id"], t["total_co2e"], t["total_boe"], t["co2_intensity"]) for t in top])
