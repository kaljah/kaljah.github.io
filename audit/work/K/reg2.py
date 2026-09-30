import sys, time, sqlite3; sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/tools")
from auditlib import api_client, db_path
c = api_client("ui_k_scratch", "it_admin")
em=f"k{int(time.time())}@audit.local"
r = c.post("/api/auth/register", json={"fullName":"K Test","email":em,"password":"Abcdef!2345xyz","role":"user","location":"West","orgName":"A","sector":"x"})
uid = r.get_json()["user"]["id"]; print("register", r.status_code, uid)
d = c.delete(f"/api/auth/users/{uid}"); print("delete", d.status_code)
lo = c.post("/api/auth/logout"); print("logout", lo.status_code)
con = sqlite3.connect(db_path("ui_k_scratch"))
print("logs for uid/email:", con.execute("select action, details from activity_log where record_id=? or details like ? order by id", (str(uid), f"%{em}%")).fetchall())
print("LOGOUT rows total:", con.execute("select count(*) from activity_log where action='LOGOUT'").fetchone())
