import sys, io, time, json; sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/tools")
from auditlib import make_db, api_client, sql
make_db("agentJ", overwrite=True)
# work around BUG-029 (NULL facility names crash every bulk upload) in this private copy
sql("agentJ", "update facilities set name='NONAME-'||id where name is null or name=''")
a = api_client("agentJ", "admin")


def run(csv, overwrite, scope="1"):
    r = a.post("/api/emissions/upload/start", data={"file": (io.BytesIO(csv.encode()), "t.csv"), "scope": scope,
               "global_factor_type": "default", "overwrite_duplicates": "true" if overwrite else "false"},
               content_type="multipart/form-data")
    jid = r.get_json()["job_id"]
    for _ in range(150):
        s = a.get(f"/api/emissions/upload/status/{jid}").get_json()
        if s["status"] != "processing":
            return s
        time.sleep(0.2)
    return s


logs0 = sql("agentJ", "select max(id) m from activity_log")[0]["m"]
hdr = "date,facility,process,fuel,quantity,unit,factor type,equipment\n"
print("before id7", sql("agentJ", "select status,approved_by,approved_at,quantity,co2e_total from emissions where id=7"))
s = run(hdr + "2026-09,RNS,pneumatic,Pneumatic Controller - High Bleed,20,devices,default,7\n", True)
print("A job", s["status"], s.get("skipped_preview"), s.get("errors"))
print("after id7", sql("agentJ", "select status,approved_by,approved_at,quantity,co2e_total from emissions where id=7"))
for ov in (True, False):
    n0 = sql("agentJ", "select count(*) n from emissions where year=2019")[0]["n"]
    row = f"2019-05,RNS,mobile,Motor Gasoline,1000,gal,default,DUPTEST{int(ov)}\n"
    s = run(hdr + row + row + row, ov)
    print("B overwrite=", ov, s["status"], [x["reason"][:90] for x in s.get("skipped_preview", [])],
          "inserted:", sql("agentJ", "select count(*) n from emissions where year=2019")[0]["n"] - n0)
print("activity_log rows added by uploads:", sql("agentJ", "select action,entity,details from activity_log where id>?", (logs0,)))
