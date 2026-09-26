import sys, json; sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/tools")
from auditlib import make_db, api_client, sql
import logging; logging.disable(logging.CRITICAL)
DB="agentB_null"; make_db(DB, overwrite=True)
c = api_client(DB,"admin")
r=c.post("/api/scope2", json={"facility_id":1,"source_type":"electricity","electricity_kwh":1000,"emission_factor":0.5}); print("s2 no year", r.status_code, r.get_json().get("record",{}).get("year"), r.get_json().get("co2e"))
r=c.post("/api/scope3", json={"facility_id":1,"category":"Category 1","activity_data":1000,"emission_factor":0.5}); print("s3 no year", r.status_code, r.get_json())
r=c.post("/api/scope3", json={"facility_id":1,"year":2024,"month":1,"category":"Totally Bogus Category","activity_data":1000,"emission_factor":0.5}); print("s3 bogus cat", r.status_code)
r=c.post("/api/scope2", json={"facility_id":1,"year":"abc","month":13,"source_type":"electricity","electricity_kwh":1000,"emission_factor":0.5}); print("s2 bad year", r.status_code, r.get_data(as_text=True)[:150])
for u in ("/api/dashboard/summary","/api/dashboard/batch-all","/api/dashboard/scope3/summary","/api/dashboard/years","/api/dashboard/categorical-breakdown"):
    r=c.get(u); print(u, r.status_code, r.get_data(as_text=True)[:200].replace("\n"," "))
print(sql(DB,"select id,year,month,co2e,status from scope2_emissions where year is null or typeof(year)!='integer'"))
print(sql(DB,"select id,year,co2e,status,category from scope3_emissions where year is null"))
