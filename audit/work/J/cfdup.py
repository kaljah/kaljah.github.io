import sys, io, time; sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/tools")
from auditlib import make_db, api_client, sql
DB = sys.argv[1] if len(sys.argv) > 1 else "agentJ"
make_db(DB, overwrite=True)
sql(DB, "update facilities set name='NONAME-'||id where name is null or name=''")  # sidestep BUG-029
a = api_client(DB, "admin")
ids = []
for co2 in (1.0, 100.0):
    r = a.post("/api/custom-factors", json={"factor_name": "AuditDupGas", "unit": "m3", "co2_factor": co2, "ch4_factor": 0, "n2o_factor": 0})
    print("create", co2, r.status_code, r.get_json())
print(sql(DB, "select id,name,co2_factor,unit from custom_factors where name='AuditDupGas'"))
csv = "date,facility,process,fuel,quantity,unit,factor type,equipment\n2018-03,RNS,combustion,AuditDupGas,1000,m3,custom,CFDUP\n"
r = a.post("/api/emissions/upload/start", data={"file": (io.BytesIO(csv.encode()), "t.csv"), "scope": "1", "global_factor_type": "custom"}, content_type="multipart/form-data")
jid = r.get_json()["job_id"]
for _ in range(150):
    s = a.get(f"/api/emissions/upload/status/{jid}").get_json()
    if s["status"] != "processing": break
    time.sleep(0.2)
print("job", s["status"], s.get("skipped_preview"))
rec = sql(DB, "select ef_used_co2, co2_emissions, co2e_total from emissions where equipment_id='CFDUP'")
print("record:", rec)
sys.exit(1 if len(sql(DB, "select id from custom_factors where name='AuditDupGas'")) > 1 else 0)
