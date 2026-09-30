"""Repro: meter_uncertainty_pct / gc_uncertainty_pct inputs are accepted but never affect propagated uncertainty."""
import sys, math; sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/tools")
from auditlib import make_db, api_client
DB = "repro_G_meter"
make_db(DB, overwrite=True)
c = api_client(DB, "admin")
base = {"facility_id": 4, "process_type": "stationary_combustion", "fuel": "Natural Gas", "unit": "m3",
        "factor_source": "default", "year": 2044, "month": 1, "quantity": 1000}
u0 = c.post("/api/emissions/", json=base).get_json()["emissions"]["uncertainty"]["co2"]
u1 = c.post("/api/emissions/", json={**base, "meter_uncertainty_pct": 40}).get_json()["emissions"]["uncertainty"]["co2"]
u2 = c.post("/api/emissions/", json={**base, "meter_uncertainty_pct": 40, "gc_uncertainty_pct": 30}).get_json()["emissions"]["uncertainty"]["co2"]
# Hand calc (95% inputs -> 1 sigma = /2): EF CO2 5% ; AD overridden by meter 40% ; GC 30%
exp1 = math.hypot(0.05 / 2, 0.40 / 2)
exp2 = math.sqrt((0.05 / 2) ** 2 + (0.40 / 2) ** 2 + (0.30 / 2) ** 2)
print("no override            : stored u_CO2(1s) = %.4f" % u0)
print("meter 40%%              : expected %.4f  actual %.4f" % (exp1, u1))
print("meter 40%% + GC 30%%     : expected %.4f  actual %.4f" % (exp2, u2))
sys.exit(1 if abs(u1 - exp1) > 1e-6 or abs(u2 - exp2) > 1e-6 else 0)
