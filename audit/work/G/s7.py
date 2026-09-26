import sys, json; sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/tools")
from auditlib import api_client, sql
c = api_client("agentG", "admin")
for i,u in enumerate([18, -0.5, "NaN", 1e6]):
    r = c.post("/api/scope2", json={"facility_id":4,"year":2034+i,"month":1,"source_type":"electricity","electricity_kwh":100000,"emission_factor":0.5,"uncertainty":u})
    print(u, r.status_code, str(r.get_json())[:200])
    d = c.get(f"/api/dashboard/uncertainty?year={2034+i}&scope=2")
    print("   dash", d.status_code, d.get_data(as_text=True)[:300])
print(sql("agentG","select id,year,co2e,uncertainty,status from scope2_emissions where year between 2034 and 2037"))
r = c.post("/api/scope3", json={"facility_id":4,"year":2038,"month":1,"category":"Category 1","activity_data":1000,"emission_factor":2,"uncertainty":-3})
print("s3", r.status_code, str(r.get_json())[:200])
