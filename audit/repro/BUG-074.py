"""Concurrent approvals of the same pending record both succeed (check-then-set, no conditional update)."""
import sys, threading
sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/tools")
from auditlib import make_db, api_client, sql
DB="repro_BUG074"; make_db(DB, overwrite=True)
adm = sql(DB,"select id from users where email='audit_admin@audit.local'")[0]["id"]
ids = [r["id"] for r in sql(DB,"select id from emissions where status='Pending' and (created_by is null or created_by!=?) limit 30",(adm,))]
c1, c2 = api_client(DB,"admin"), api_client(DB,"admin")
res = {}
def go(c, i):
    r = c.post(f"/api/emissions/approve/{i}"); res.setdefault(i, []).append(r.status_code)
for i in ids:
    ts = [threading.Thread(target=go, args=(c, i)) for c in (c1, c2)]
    [t.start() for t in ts]; [t.join() for t in ts]
dbl = [i for i in ids if res[i].count(200) == 2]
logs = sql(DB, "select count(*) n from activity_log where details like '%emission approved by%'")[0]["n"]
print(f"expected: exactly one 200 per record, the other 400 'Record is not pending approval' ({len(ids)} approval log rows)")
print(f"actual: {len(dbl)}/{len(ids)} records approved twice (both 200); approval log rows = {logs}")
sys.exit(1 if dbl else 0)
