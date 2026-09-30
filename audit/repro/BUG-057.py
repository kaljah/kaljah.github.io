import sys, io, time; sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/tools")
from auditlib import make_db, api_client, sql
DB = "agentJ_BUG057"
make_db(DB, overwrite=True)
sql(DB, "update facilities set name='NONAME-'||id where name is null or name=''")  # sidestep BUG-029
a = api_client(DB, "admin")
def run(csv, overwrite):
    r = a.post("/api/emissions/upload/start", data={"file": (io.BytesIO(csv.encode()), "t.csv"), "scope": "1",
               "global_factor_type": "default", "overwrite_duplicates": "true" if overwrite else "false"}, content_type="multipart/form-data")
    jid = r.get_json()["job_id"]
    for _ in range(150):
        s = a.get(f"/api/emissions/upload/status/{jid}").get_json()
        if s["status"] != "processing": return s
        time.sleep(0.2)
hdr = "date,facility,process,fuel,quantity,unit,factor type,equipment\n"
row = "2019-05,RNS,mobile,Motor Gasoline,1000,gal,default,DUPTEST\n"
run(hdr + row + row + row, True)
n = sql(DB, "select count(*) n, sum(co2e_total) t from emissions where year=2019 and equipment_id='DUPTEST'")[0]
print("CSV with the same row 3x, overwrite_duplicates=true")
print("expected: 1 record; actual:", n["n"], "records, total co2e", n["t"])
sys.exit(1 if n["n"] != 1 else 0)
