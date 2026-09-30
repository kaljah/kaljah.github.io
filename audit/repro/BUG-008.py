"""Repro: inventory uncertainty on /api/dashboard/uncertainty depends on how the same activity is split into records
(EF uncertainty treated as independent between records that share one emission factor)."""
import sys, math; sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/tools")
from auditlib import make_db, api_client
DB = "repro_G_granularity"
make_db(DB, overwrite=True)
c = api_client(DB, "admin")
base = {"facility_id": 4, "process_type": "stationary_combustion", "fuel": "Natural Gas", "unit": "m3", "factor_source": "default"}
for m in range(1, 13):
    assert c.post("/api/emissions/", json={**base, "year": 2041, "month": m, "quantity": 1000}).status_code == 201
assert c.post("/api/emissions/", json={**base, "year": 2042, "month": 1, "quantity": 12000}).status_code == 201
a = c.get("/api/dashboard/uncertainty?year=2041").get_json()
b = c.get("/api/dashboard/uncertainty?year=2042").get_json()
print("12 monthly records : total %.4f t  U95 %s" % (a["total_inventory_emissions"], a["inventory_uncertainty_pct"]))
print("1 annual record    : total %.4f t  U95 %s" % (b["total_inventory_emissions"], b["inventory_uncertainty_pct"]))
ratio = b["inventory_uncertainty_decimal"] / a["inventory_uncertainty_decimal"]
print("ratio annual/monthly = %.3f (sqrt(12)=%.3f); expected 1.0 for identical inventories" % (ratio, math.sqrt(12)))
# Independent IPCC Approach 1 expectation for this category: EF +/-5% (95%), AD +/-10% (95%) -> sqrt(5^2+10^2)=11.18%
print("IPCC Approach 1 expected (category-level, shared EF): +/-%.2f%%" % math.hypot(5, 10))
sys.exit(1 if abs(ratio - 1) > 0.01 else 0)
