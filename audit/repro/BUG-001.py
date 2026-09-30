"""BUG-001: /api/emissions/upload/start lets role=user create/overwrite facilities & custom factors."""
import sys, io, time
sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/tools")
from auditlib import make_db, api_client, sql
DB = "repro_BUG001"
make_db(DB, overwrite=True)
c = api_client(DB, "user")
def run(csv, scope):
    r = c.post("/api/emissions/upload/start", data={"file": (io.BytesIO(csv.encode()), "f.csv"), "scope": scope, "overwrite_duplicates": "true"}, content_type="multipart/form-data")
    print(f"  upload scope={scope}: HTTP {r.status_code}")
    jid = (r.get_json() or {}).get("job_id")
    if not jid:  # rejected up front (the fixed behaviour); DB state is still checked below
        return
    for _ in range(100):
        s = c.get(f"/api/emissions/upload/status/{jid}").get_json()
        if s.get("status") != "processing": break
        time.sleep(0.2)
run("name,location\nCimenterie Industrielle de Chlef (GICA),HACKED\n", "facilities")
run("name,co2_factor,unit\nEVIL_CF,999,scf\n", "custom_factors")
loc = sql(DB, "select location from facilities where id=3")[0]["location"]
cf = sql(DB, "select count(*) n from custom_factors where name='EVIL_CF'")[0]["n"]
print("expected: facility 3 location unchanged ('Chlef'), 0 EVIL_CF factors (user role lacks rights)")
print(f"actual:   facility 3 location={loc!r}, EVIL_CF factors={cf}")
sys.exit(1 if (loc == "HACKED" or cf) else 0)
