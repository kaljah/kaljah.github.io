"""Agent C repro: UI (client catalog) factors missing from the server catalog are silently saved with 0 emissions."""
import sys, json, os
sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/tools")
from auditlib import make_db, api_client, sql
DB = "agentC_bug015"
make_db(DB, overwrite=True)
c = api_client(DB, "admin")
# Export the live client catalog (new/client/src/utils/EmissionFactors.js API_FACTORS) via node
import subprocess, shutil, tempfile
tmp = os.path.join(tempfile.mkdtemp(), "ef.mjs")
shutil.copyfile(r"C:/Users/samsung/Desktop/H2/new/client/src/utils/EmissionFactors.js", tmp)
out = subprocess.run(["node", "-e", "import('file:///" + tmp.replace(os.sep, "/") + "').then(m=>process.stdout.write(JSON.stringify(m.API_FACTORS)))"],
                     capture_output=True, text=True, encoding="utf-8", check=True).stdout
CLIENT = json.loads(out)
sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/new/server")
from emission_factors import API_FACTORS
UNIT = {"combustion": "scf", "mobile": "gal", "flaring": "m3", "venting": "event", "pneumatic": "devices",
        "fugitive": "count", "fugitive_pipeline": "km", "tank": "bbl", "drilling": "bbl", "dehydrator": "MMscf",
        "agr": "MMscf", "loading": "bbl", "separation": "m3"}
zero = []
tested = 0
for name, f in CLIENT.items():
    if name in API_FACTORS:
        continue
    if not any(f.get(g) for g in ("co2", "ch4", "n2o")):
        continue  # client factor itself carries no value
    proc = (f.get("usage") or ["combustion"])[0]
    unit = f.get("baseUnit") or UNIT.get(proc, "m3")
    p = {"year": 2025, "month": 1, "facility_id": 1, "process_type": proc, "factor_source": "default",
         "fuel": name, "fuel_type": name, "amount": 1000, "quantity": 1000, "unit": unit}
    r = c.post("/api/emissions/", json=p)
    tested += 1
    row = sql(DB, "select co2e_total, calc_method from emissions order by id desc limit 1")[0]
    if r.status_code in (200, 201) and not row["co2e_total"]:
        zero.append((name, proc, unit, r.status_code, row["co2e_total"], row["calc_method"]))
print(f"client-only factors with non-zero client EF tested: {tested}")
print(f"saved with HTTP 2xx and co2e_total == 0: {len(zero)}")
for z in zero:
    print("  ", z)
print("EXPECTED: non-zero emissions (client EF is non-zero) or a 4xx 'factor not found' error")
sys.exit(1 if zero else 0)
