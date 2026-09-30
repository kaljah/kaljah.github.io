import sys, io, time; sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/tools")
from auditlib import make_db, api_client, sql
DB = "agentJ_BUG058"
make_db(DB, overwrite=True)
sql(DB, "update facilities set name='NONAME-'||id where name is null or name=''")  # sidestep BUG-029
a = api_client(DB, "admin")
log0 = sql(DB, "select max(id) m from activity_log")[0]["m"]
before = sql(DB, "select status,approved_by,approved_at,quantity,co2e_total from emissions where id=7")[0]
csv = "date,facility,process,fuel,quantity,unit,factor type,equipment\n2026-09,RNS,pneumatic,Pneumatic Controller - High Bleed,20,devices,default,7\n"
r = a.post("/api/emissions/upload/start", data={"file": (io.BytesIO(csv.encode()), "t.csv"), "scope": "1",
           "global_factor_type": "default", "overwrite_duplicates": "true"}, content_type="multipart/form-data")
jid = r.get_json()["job_id"]
for _ in range(150):
    if a.get(f"/api/emissions/upload/status/{jid}").get_json()["status"] != "processing": break
    time.sleep(0.2)
after = sql(DB, "select status,approved_by,approved_at,quantity,co2e_total from emissions where id=7")[0]
logs = sql(DB, "select action,entity,details from activity_log where id>? and action<>'LOGIN'", (log0,))
print("before:", before); print("after: ", after); print("activity_log entries for the upload:", logs)
bad = (after["status"] == "Pending" and after["approved_by"] is not None) or not logs
print("expected: approved_by/approved_at cleared when status reset to Pending, and an ActivityLog entry with old/new values")
sys.exit(1 if bad else 0)
