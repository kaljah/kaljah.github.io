"""Repro: QA dashboard 'IPCC Tier 1 Uncertainty' shows a 1-sigma value (no k=2), uses only the CO2 column, and includes
Draft/Pending records, so it disagrees with the Uncertainty Assessment page (95%, Verified only) for the same data."""
import sys, math; sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/tools")
from auditlib import make_db, api_client
DB = "repro_G_qaqc"
make_db(DB, overwrite=True)
c = api_client(DB, "admin")
base = {"facility_id": 4, "process_type": "stationary_combustion", "fuel": "Natural Gas", "unit": "m3",
        "factor_source": "default", "year": 2047, "month": 1, "quantity": 12000}
assert c.post("/api/emissions/", json=base).status_code == 201                       # Verified (admin)
assert c.post("/api/emissions/", json={**base, "month": 2, "status": "Draft", "quantity": 120000}).status_code == 201  # Draft
q = c.get("/api/qaqc/dashboard?year=2047").get_json()["tier1_uncertainty"]
d = c.get("/api/dashboard/uncertainty?year=2047").get_json()
exp95 = math.hypot(0.05, 0.10)  # IPCC Eq.3.1 at 95%: EF 5%, AD 10%
print("expected (Verified only, 95%%) : +/-%.2f%% on %.3f t" % (100 * exp95, d["total_inventory_emissions"]))
print("Uncertainty page               : %s on %.3f t" % (d["inventory_uncertainty_pct"], d["total_inventory_emissions"]))
print("QA dashboard card (UI shows ±x%%): +/-%.2f%% on %.3f t (S1 total incl. Draft)" % (100 * q["overall"], q["s1_total_tco2e"]))
ok = abs(q["overall"] - exp95) < 0.002 and abs(q["s1_total_tco2e"] - d["total_inventory_emissions"]) < 1e-6
sys.exit(0 if ok else 1)
