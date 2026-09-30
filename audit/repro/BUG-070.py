"""Single reject endpoint accepts already-Verified (and already-Rejected) records."""
import sys
sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/tools")
from auditlib import make_db, api_client, sql
DB="repro_BUG070"; make_db(DB, overwrite=True)
s = api_client(DB,"superuser")
v = sql(DB,"select id,status,approved_by from emissions where status='Verified' and facility_id in (1,2,158,160,168) and co2e_total>0 order by id limit 1")[0]
r = s.post(f"/api/emissions/reject/{v['id']}", json={"reason":"x"})
a = sql(DB,"select status,approved_by,qa_flag from emissions where id=?",(v['id'],))[0]
rb = s.post("/api/emissions/reject/batch", json={"ids":[v['id']], "scope":"1"}).get_json()
print(f"before: {v}")
print(f"expected: 400 'Record is not pending approval' (as /approve does and as /reject/batch filters)")
print(f"actual: {r.status_code}, after={a}; /reject/batch on a non-pending id deleted_count={rb.get('deleted_count')}")
sys.exit(1 if r.status_code==200 else 0)
