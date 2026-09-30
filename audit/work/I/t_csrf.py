import sys
sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/tools")
from auditlib import make_db, get_app, api_client, PASSWORD, sql
DB="agentI_csrf"; make_db(DB, overwrite=True)
app = get_app(DB); app.config["WTF_CSRF_ENABLED"]=True; app.config["TESTING"]=False
c = app.test_client()
r = c.post("/api/auth/login", json={"email":"audit_user@audit.local","password":PASSWORD}); print("login (exempt)", r.status_code)
r = c.post("/api/data/production", json={"facility_id":1,"year":2025,"month":12,"oil_amount":1}); print("POST no token", r.status_code, r.get_data(as_text=True)[:80])
tok = c.get("/api/csrf-token").get_json()["csrf_token"]
r = c.post("/api/data/production", json={"facility_id":1,"year":2025,"month":12,"oil_amount":1}, headers={"X-CSRFToken":tok}); print("POST token", r.status_code)
r = c.put("/api/auth/profile", json={"fullName":"x"}); print("PUT no token", r.status_code)
r = c.delete("/api/notifications/all"); print("DELETE no token", r.status_code)
r = c.post("/api/auth/logout"); print("logout no token", r.status_code)
# session invalidation after password reset / deactivation
app.config["WTF_CSRF_ENABLED"]=False
u = api_client(DB,"user"); it = api_client(DB,"it_admin")
uid = sql(DB,"select id from users where email='audit_user@audit.local'")[0]["id"]
r = it.post(f"/api/auth/users/{uid}/reset-password", json={"password":"NewPass!2026xx","new_password":"NewPass!2026xx"}); print("reset", r.status_code, r.get_data(as_text=True)[:120])
print("old session after reset:", u.get("/api/emissions/?limit=1").status_code)
r = u.post("/api/auth/change-password", json={"current_password":PASSWORD,"new_password":"Another!2026xx"}); print("change pw", r.status_code)
