import sys
sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/tools")
from auditlib import make_db, api_client, sql
DB="repro_BUG020"; make_db(DB, overwrite=True)
bad=False
for role in ["user","it_admin"]:
    c = api_client(DB, role)
    allowed = c.get("/api/facilities").get_json()
    ids = [f["id"] for f in (allowed if isinstance(allowed,list) else allowed.get("facilities",[]))]
    for fid in ("170", None):
        r = c.get("/api/reports/master-annual-report" + (f"?facility_id={fid}" if fid else ""))
        print(f"{role}: allowed facility ids={ids[:10]}.. 170 in scope={170 in ids}; GET master-annual-report facility_id={fid} -> {r.status_code} {r.mimetype} {len(r.data)} bytes")
        if r.status_code == 200 and r.data[:4] == b"%PDF": bad=True
print("expected: 403 for roles without access to facility 170 (El Merk) / consolidated data; actual:", "PDF served" if bad else "denied")
sys.exit(1 if bad else 0)
