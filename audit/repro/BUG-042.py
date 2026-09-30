"""Agent C repro: PUT /api/emissions/<id> recalculation drops the record's Tier 2 custom factor."""
import sys
sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/tools")
from auditlib import make_db, api_client, sql
DB = "agentC_bug042"
make_db(DB, overwrite=True)
c = api_client(DB, "admin")
cf = c.post("/api/custom-factors/", json=dict(name="T2 site gas", co2_factor=2.0, ch4_factor=0.01, n2o_factor=0, unit="kg/m3")).get_json()["id"]
# Exactly what Scope1Form sends in Tier 2 "custom_factor" mode: fuel = str(custom factor id)
r = c.post("/api/emissions/", json={"year": 2025, "month": 2, "facility_id": 1, "process_type": "combustion",
                                    "factor_source": "custom", "fuel": str(cf), "fuel_type": str(cf),
                                    "amount": 1000, "quantity": 1000, "unit": "m3", "custom_factor_id": cf})
rid = sql(DB, "select max(id) i from emissions")[0]["i"]
q = "select co2_emissions, ch4_emissions, co2e_total, calc_method, factor_source from emissions where id=?"
before = sql(DB, q, (rid,))[0]
r2 = c.put(f"/api/emissions/{rid}", json={"recalculate": True})
after = sql(DB, q, (rid,))[0]
exp_co2 = 1000 * 2.0 / 1000  # 1000 m3 x 2.0 kg/m3 = 2.0 t CO2 (unchanged factor, unchanged activity)
print("custom factor: 2.0 kg CO2/m3, 0.01 kg CH4/m3; activity 1000 m3")
print("expected after recalc: co2 = %.3f t (same as before)" % exp_co2)
print("before:", before)
print("PUT", r2.status_code, "after:", after)
bad = abs((after["co2_emissions"] or 0) - exp_co2) > 1e-6
sys.exit(1 if bad else 0)
