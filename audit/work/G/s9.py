import sys, json, math; sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/tools")
from auditlib import api_client, sql
c = api_client("agentG", "admin")
cf = sql("agentG","select id,name,co2_uncertainty,ch4_uncertainty,n2o_uncertainty,uncertainty,unit from custom_factors where co2_uncertainty>0 limit 1")[0]; print(cf)
r = c.post("/api/emissions/", json={"facility_id":4,"process_type":"stationary_combustion","fuel":cf["name"],"custom_factor_id":cf["id"],"factor_source":"custom","unit":cf["unit"],"quantity":1000,"year":2039,"month":1})
j=r.get_json(); print(r.status_code, j.get("emissions",j))
for g in ("co2","ch4","n2o"):
    print(g, "expected", math.hypot(cf[g+"_uncertainty"]/100/2, 0.07/2))
