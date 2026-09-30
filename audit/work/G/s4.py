import sys, json; sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/tools")
from auditlib import api_client, sql
c = api_client("agentG", "admin")
base = {"facility_id":4,"process_type":"stationary_combustion","fuel":"Natural Gas","unit":"m3","factor_source":"default"}
# year 2031 already has month 1 record (1000 m3); add months 2..12
for m in range(2,13):
    r = c.post("/api/emissions/", json={**base,"year":2031,"month":m,"quantity":1000}); assert r.status_code==201, r.get_json()
r = c.post("/api/emissions/", json={**base,"year":2032,"month":1,"quantity":12000}); assert r.status_code==201
print(sql("agentG","select year,count(*),status,sum(co2e_total),min(uncertainty),max(uncertainty),max(uncertainty_ch4) from emissions where year in (2031,2032) group by year,status"))
for y in (2031,2032):
    d = c.get(f"/api/dashboard/uncertainty?year={y}").get_json()
    print(y, d["inventory_uncertainty_pct"], d["inventory_uncertainty_1sigma"], d["total_inventory_emissions"])
