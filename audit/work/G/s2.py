import sys, json; sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/tools")
from auditlib import api_client
c = api_client("agentG", "admin")
for y in [2020, 2022, 2026]:
    r = c.get(f"/api/dashboard/uncertainty?year={y}")
    d = r.get_json()
    print(y, r.status_code, d["inventory_uncertainty_pct"], d["inventory_uncertainty_1sigma"], d["total_inventory_emissions"], d["tier_breakdown"])
    for cat in d["categories"]:
        print("   ", cat["category"], round(cat["total_emissions"],2), cat["uncertainty_pct"], cat["level"], [(t["name"], t["uncertainty"]) for t in cat["top_contributors"]])
    r = c.get(f"/api/qaqc/dashboard?year={y}")
    print("  QAQC", r.status_code, r.get_json().get("tier1_uncertainty"))
