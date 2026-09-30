"""Repro: dashboard per-record uncertainty uses max(u_CO2,u_CH4,u_N2O) instead of CO2e-weighted combination."""
import sys, math; sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/tools")
from auditlib import make_db, api_client
DB = "repro_G_gasmax"
make_db(DB, overwrite=True)
c = api_client(DB, "admin")
r = c.post("/api/emissions/", json={"facility_id": 4, "process_type": "stationary_combustion", "fuel": "Natural Gas",
                                    "unit": "m3", "factor_source": "default", "year": 2043, "month": 1, "quantity": 12000})
assert r.status_code == 201, r.get_json()
e = r.get_json()["emissions"]
GWP = {"ch4": 28, "n2o": 265}  # AR5 (app default)
co2e = {"co2": e["co2"], "ch4": e["ch4"] * GWP["ch4"], "n2o": e["n2o"] * GWP["n2o"]}
E = sum(co2e.values())
# Independent derivation (IPCC 2006 Vol.1 Ch.3, 95% half-widths -> 1 sigma = /2):
# AD +/-10% (Tier 1) common to all gases (fully correlated); EF: CO2 5%, CH4 20%, N2O 20% (catalog Natural Gas).
u_ad = 0.10 / 2; u_ef = {"co2": 0.05 / 2, "ch4": 0.20 / 2, "n2o": 0.20 / 2}
var = (u_ad * E) ** 2 + sum((u_ef[g] * co2e[g]) ** 2 for g in co2e)
exp95 = 2 * math.sqrt(var) / E
d = c.get("/api/dashboard/uncertainty?year=2043").get_json()
print("record CO2e share: CO2 %.4f%%" % (100 * co2e["co2"] / E))
print("expected inventory U95 (CO2e-weighted): +/-%.2f%%" % (100 * exp95))
print("dashboard inventory U95               : %s" % d["inventory_uncertainty_pct"])
sys.exit(1 if abs(d["inventory_uncertainty_decimal"] - exp95) / exp95 > 0.02 else 0)
