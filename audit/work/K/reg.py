import sys; sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/tools")
from auditlib import api_client, sql
c = api_client("ui_k_scratch", "it_admin")
import time; em=f"k{int(time.time())}@audit.local"
r = c.post("/api/auth/register", json={"fullName":"K Test","email":em,"password":"Abcdef!2345xyz","role":"user","location":"West","orgName":"A","sector":"x"})
print(r.status_code, r.get_json().get("user",{}).get("id"))
uid = r.get_json()["user"]["id"]
print(sql("ui_k_scratch","select action, record_id, details from activity_log where record_id=? order by id desc limit 3",(str(uid),)))
