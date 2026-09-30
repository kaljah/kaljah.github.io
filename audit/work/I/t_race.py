import sys, threading
sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/tools")
from auditlib import make_db, api_client, sql
DB="agentI_race"; make_db(DB, overwrite=True)
ids = [r["id"] for r in sql(DB,"select id from emissions where status='Pending' and (created_by is null or created_by!=(select id from users where email='audit_admin@audit.local')) limit 20")]
print(len(ids))
cl = [api_client(DB,"admin") for _ in range(2)] + [api_client(DB,"superuser")]
res = {}
def go(c, i, k):
    r = c.post(f"/api/emissions/approve/{i}"); res.setdefault(i, []).append((k, r.status_code))
def rj(c, i, k):
    r = c.post(f"/api/emissions/reject/{i}"); res.setdefault(i, []).append((k, "rej", r.status_code))
dbl=0
for i in ids:
    ts=[threading.Thread(target=go,args=(cl[0],i,"a1")), threading.Thread(target=go,args=(cl[1],i,"a2")), threading.Thread(target=rj,args=(cl[2],i,"su"))]
    [t.start() for t in ts]; [t.join() for t in ts]
    ok=[x for x in res[i] if x[-1]==200]
    if len(ok)>1: dbl+=1
print("records with >1 successful decision:", dbl, "of", len(ids))
print(list(res.items())[:5])
print(sql(DB,"select status,count(*) n from emissions where id in (%s) group by status"%",".join(map(str,ids))))
