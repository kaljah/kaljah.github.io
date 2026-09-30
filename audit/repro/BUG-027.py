"""Agent C repro: catalog HHV (Btu/gal or Btu/scf) is applied to mass / wrong-phase activity units."""
import sys
sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/tools")
from auditlib import make_db, api_client, sql
DB = "agentC_bug027"
make_db(DB, overwrite=True)
c = api_client(DB, "admin")
# Independent expected values (t CO2):
#  Diesel 1 tonne: density 0.85 kg/L (IPCC/API typical) -> 1176.5 L = 310.8 gal x 0.138 MMBtu/gal x 73.96 kg/MMBtu = 3.172 t
#     (cross-check IPCC 2006: NCV 43.0 TJ/Gg x 74,100 kg/TJ = 3.186 t)
#  Crude oil 1 tonne: IPCC 2006: NCV 42.3 TJ/Gg x 73,300 kg/TJ = 3.101 t
#  Natural gas 1 tonne: pipeline gas ~0.8 kg/m3 -> 1250 m3 = 44,143 scf x 1020 Btu/scf x 53.06 = 2.39 t
#     (cross-check IPCC 2006: NCV 48.0 TJ/Gg x 56,100 kg/TJ = 2.69 t)
#  Ethane 1000 scf (gas): HHV ~1,770 Btu/scf -> 1.77 MMBtu x 59.6 = 0.105 t
#  Propane (Liquid) 1 m3: 264.17 gal x 0.0915 MMBtu/gal x 62.88 = 1.520 t
cases = [
    ("Diesel (No. 2 Fuel Oil)", 1, "tonne", 3.17),
    ("Crude Oil", 1, "tonne", 3.10),
    ("Natural Gas", 1, "tonne", 2.39),
    ("Ethane", 1000, "scf", 0.105),
    ("Propane (Liquid)", 1, "m3", 1.52),
]
bad = 0
for fuel, q, u, exp in cases:
    r = c.post("/api/emissions/", json={"year": 2025, "month": 1, "facility_id": 1, "process_type": "combustion",
                                        "factor_source": "default", "fuel": fuel, "fuel_type": fuel,
                                        "amount": q, "quantity": q, "unit": u})
    act = sql(DB, "select co2_emissions from emissions order by id desc limit 1")[0]["co2_emissions"]
    ratio = act / exp
    flag = "WRONG" if abs(ratio - 1) > 0.25 else "ok"
    bad += flag == "WRONG"
    print(f"{fuel:26s} {q} {u:6s} HTTP {r.status_code}  expected ~{exp:.3f} t CO2  actual {act:.4f} t  ratio {ratio:.2f}  {flag}")
sys.exit(1 if bad else 0)
