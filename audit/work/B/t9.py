import sys; sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/tools")
from auditlib import make_db, api_client, sql, get_app
import logging; logging.disable(logging.CRITICAL)
DB="agentB_rcache2"; make_db(DB, overwrite=True)
c = api_client(DB,"admin")
app=get_app(DB)
u=app.test_client(); u.post("/api/auth/login", json={"email":"audit_user@audit.local","password":"AuditPass!2026"})
def tot():
    j=c.get("/api/dashboard/summary?year=2024").get_json(); return sum(r["scope1_total"] for r in j)
# user create pending in West facility
fac=sql(DB,"select id from facilities where region='West' or location='West' limit 1")
print(fac)
fid=fac[0]["id"] if fac else 1
r=u.post("/api/emissions/", json={"process_type":"combustion","facility_id":fid,"year":2024,"month":1,"fuel":"Natural Gas","amount":1000,"unit":"MMBtu"}); print(r.status_code, r.get_json().get("id"))
i=r.get_json()["id"]
t0=tot(); r=c.post(f"/api/emissions/approve/{i}", json={"scope":"1"}); print("approve",r.status_code); t1=tot(); print("approve diff", t1-t0)
r=c.delete(f"/api/emissions/{i}"); print("delete", r.status_code); t2=tot(); print("delete diff", t2-t1)
