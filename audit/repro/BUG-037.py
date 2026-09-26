"""Repro: PUT /api/emissions/<id> (recalculate) overwrites the propagated 1-sigma combined uncertainty with the raw
catalog EF uncertainty (a 95% EF-only half-width), and stores user_uncertainty unpropagated."""
import sys, math; sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/tools")
from auditlib import make_db, api_client, sql
DB = "repro_G_put"
make_db(DB, overwrite=True)
c = api_client(DB, "admin")
base = {"facility_id": 4, "process_type": "stationary_combustion", "fuel": "Natural Gas", "unit": "m3",
        "factor_source": "default", "year": 2045, "month": 1, "quantity": 1000}
rid = c.post("/api/emissions/", json=base).get_json()["id"]
q = "select co2e_total, uncertainty, uncertainty_ch4, uncertainty_n2o from emissions where id=?"
before = sql(DB, q, (rid,))[0]; d0 = c.get("/api/dashboard/uncertainty?year=2045").get_json()["inventory_uncertainty_pct"]
assert c.put(f"/api/emissions/{rid}", json={"recalculate": True}).status_code == 200
after = sql(DB, q, (rid,))[0]; d1 = c.get("/api/dashboard/uncertainty?year=2045").get_json()["inventory_uncertainty_pct"]
exp_co2 = math.hypot(0.05 / 2, 0.10 / 2)  # IPCC Eq 3.1, EF 5%, AD 10% (95%) -> 1 sigma
print("expected stored u_CO2 (1 sigma, EF+AD): %.4f" % exp_co2)
print("after POST : %s  dashboard %s" % (before, d0))
print("after PUT  : %s  dashboard %s   (co2e unchanged)" % (after, d1))
rid2 = c.post("/api/emissions/", json={**base, "year": 2046, "user_uncertainty": {"co2": 50}}).get_json()["id"]
u_post = sql(DB, q, (rid2,))[0]["uncertainty"]
c.put(f"/api/emissions/{rid2}", json={"recalculate": True, "user_uncertainty": {"co2": 50}})
u_put = sql(DB, q, (rid2,))[0]["uncertainty"]
print("user_uncertainty co2=50%%: POST stores %.4f, PUT stores %.4f (expected %.4f both)" % (u_post, u_put, math.hypot(0.25, 0.05)))
sys.exit(1 if abs(after["uncertainty"] - exp_co2) > 1e-6 or abs(u_put - u_post) > 1e-6 else 0)
