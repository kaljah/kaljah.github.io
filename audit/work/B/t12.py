import sys, json, io, time; sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/tools")
from auditlib import make_db, api_client, sql
import logging; logging.disable(logging.CRITICAL)
c = api_client("agentB_bulk","admin")
r=c.post("/api/emissions/bulk-upload", json={"records":[{"date":"2038-01-01","facility":"ADR","process":"combustion","fuel":"Natural Gas","quantity":1000,"unit":"MMBtu"}]})
print("bulk-upload", r.status_code, r.get_data(as_text=True)[:200])
for scope,csv in (("2","Date,Facility,Source Type,Amount,Unit,Region\n2038-01,ADR,electricity,1000,kWh,Algeria\n"),("3","Date,Facility,Category,Activity Data,Unit,Emission Factor\n2038-01,ADR,Purchased Goods,1000,USD,0.5\n")):
    r=c.post("/api/emissions/upload/start", data={"file":(io.BytesIO(csv.encode()),"s.csv"),"scope":scope}, content_type="multipart/form-data")
    jid=r.get_json()["job_id"]
    for _ in range(40):
        s=c.get(f"/api/emissions/upload/status/{jid}").get_json()
        if s["status"]!="processing": break
        time.sleep(0.3)
    print("scope",scope,s["status"],s["errors"])
