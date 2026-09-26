import sys, json; sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/tools")
from auditlib import make_db, api_client, sql
import logging; logging.disable(logging.CRITICAL)
DB="agentB_s2"; make_db(DB, overwrite=True)
c = api_client(DB,"admin")
def s1():
    r=c.get("/api/dashboard/summary?year=2030"); return r.status_code, r.get_json()
print("before", s1())
r=c.post("/api/emissions/", json={"process_type":"indirect_steam","facility_id":1,"year":2030,"month":1,"amount":1000,"quantity":1000,"unit":"MMBtu","heat_unit":"mmbtu","boiler_eff":0.8,"fuel":"Natural Gas"})
print(r.status_code, r.get_json())
r=c.post("/api/emissions/", json={"process_type":"cogen_allocation","facility_id":1,"year":2030,"month":1,"amount":1000,"heat_output":1000,"power_output":100})
print(r.status_code, r.get_json())
print("after", s1())
print(sql(DB,"select id,process_type,co2e_total,status from emissions where year=2030"))
