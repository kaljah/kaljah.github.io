import sys, json, io, time; sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/tools")
from auditlib import make_db, api_client, sql
import logging; logging.disable(logging.CRITICAL)
DB="agentB_bulk"; make_db(DB, overwrite=True); import sqlite3 as _s; _c=_s.connect(r"C:/Users/samsung/Desktop/H2/audit/db/agentB_bulk.db"); _c.execute("update facilities set name='NULLNAME_'||id where name is null"); _c.commit(); _c.close()
c = api_client(DB,"admin")
csv="""Date,Facility,Process,Fuel,Quantity,Unit,Factor Type
2038-01,ADR,combustion,Natural Gas,1000,MMBtu,default
2038-02,ADR,flaring,Natural Gas (Flaring),100000,scf,default
2038-03,ADR,mobile,Diesel (No. 2 Fuel Oil),1000,gal,default
2038-04,ADR,routine_flaring,Natural Gas (Flaring),100000,scf,default
2038-05,ADR,indirect_steam,Natural Gas,1000,MMBtu,default
"""
before=c.get("/api/dashboard/summary?year=2038&includePending=true").get_json()
r=c.post("/api/emissions/upload/start", data={"file":(io.BytesIO(csv.encode()),"s1.csv"),"scope":"1"}, content_type="multipart/form-data")
jid=r.get_json()["job_id"]
for _ in range(60):
    s=c.get(f"/api/emissions/upload/status/{jid}").get_json()
    if s["status"]!="processing": break
    time.sleep(0.5)
print(json.dumps(s,default=str)[:1500])
for row in sql(DB,"select id,month,process_type,fuel_type,quantity,unit,factor_source,calc_method,ogmp_level,co2_emissions,ch4_emissions,n2o_emissions,co2e_total,status,qa_flag from emissions where year=2038 order by month"): print(row)
print("summary before", before)
print("summary after (includePending)", c.get("/api/dashboard/summary?year=2038&includePending=true").get_json())
