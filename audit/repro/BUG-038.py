"""Superuser restricted to West can read audit-log entries about other regions' records."""
import sys
sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/tools")
from auditlib import make_db, api_client, sql
DB="repro_BUG038"; make_db(DB, overwrite=True)
c = api_client(DB, "superuser")
allowed = {f["id"] for f in c.get("/api/facilities").get_json()}
emis_fac = {r["id"]: (r["facility_id"], r["region"]) for r in sql(DB, "select e.id, e.facility_id, f.region from emissions e join facilities f on f.id=e.facility_id")}
logs = c.get("/api/audit/?limit=500&entity=Emission").get_json()["logs"]
leak = []
for l in logs:
    try: eid = int(l["entityId"])
    except Exception: continue
    if eid in emis_fac and emis_fac[eid][0] not in allowed:
        leak.append((l["id"], emis_fac[eid], l["details"][:90]))
exp = c.get("/api/audit/export")
print("superuser (West) allowed facilities:", sorted(allowed))
print("expected: 0 audit entries about facilities outside scope")
print(f"actual: {len(leak)} entries, e.g. {leak[:3]}; /api/audit/export -> {exp.status_code}, {len(exp.data)} bytes")
sys.exit(1 if leak else 0)
