"""Agent C repro: Manage Data custom factors (unit = bare activity unit, value = kg/unit) are misapplied by the Tier 2 calculation."""
import sys
sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/tools")
from auditlib import make_db, api_client, sql
DB = "agentC_bug063"
make_db(DB, overwrite=True)
c = api_client(DB, "admin")
def mk(**kw):
    return c.post("/api/custom-factors/", json=kw).get_json()["id"]
# ManageData.jsx "Add Custom Factor" form: Unit select = scf | m³ | gal | bbl | kg | tonne ; fields labelled "CO2 Factor (kg/unit)"
cases = [
    # (factor unit, kg CO2 per unit, activity qty, activity unit, expected t CO2 by hand)
    ("tonne", 3170.0, 1, "tonne", 1 * 3170.0 / 1000),                       # 3.17 t
    ("tonne", 3170.0, 1000, "kg", 1.0 * 3170.0 / 1000),                     # 1000 kg = 1 t -> 3.17 t
    ("kg", 3.17, 1, "tonne", 1000 * 3.17 / 1000),                           # 3.17 t
    ("gal", 10.21, 1, "bbl", 42 * 10.21 / 1000),                            # 0.4288 t
    ("scf", 0.0541, 1000, "m3", 1000 * 35.3147 * 0.0541 / 1000),            # 1.9105 t
    ("m³", 1.9, 1000, "scf", 1000 * 0.0283168 * 1.9 / 1000),                # 0.0538 t
]
bad = 0
for fu, ef, q, u, exp in cases:
    cf = mk(name=f"MD {fu}", co2_factor=ef, unit=fu)
    r = c.post("/api/emissions/", json={"year": 2025, "month": 4, "facility_id": 1, "process_type": "combustion",
                                        "factor_source": "custom", "fuel": str(cf), "fuel_type": str(cf),
                                        "amount": q, "quantity": q, "unit": u, "custom_factor_id": cf})
    act = sql(DB, "select co2_emissions from emissions order by id desc limit 1")[0]["co2_emissions"]
    ratio = act / exp
    ok = abs(ratio - 1) < 0.01
    bad += not ok
    print(f"factor {ef} kg/{fu:5s} x {q} {u:5s}: expected {exp:.4f} t, actual {act:.6g} t, ratio {ratio:.4g} {'ok' if ok else 'WRONG'}")
sys.exit(1 if bad else 0)
