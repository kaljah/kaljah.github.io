import sys, json; sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/tools")
from auditlib import api_client, sql
c = api_client("agentG", "admin")
base = {"facility_id":4,"process_type":"stationary_combustion","fuel":"Natural Gas","unit":"m3","factor_source":"default","year":2033,"month":1,"quantity":1000}
for extra in [{}, {"meter_uncertainty_pct":40}, {"meter_uncertainty_pct":1,"gc_uncertainty_pct":30}, {"user_uncertainty":{"co2":50,"ch4":50,"n2o":50}}]:
    r = c.post("/api/emissions/", json={**base, **extra}); j=r.get_json()
    print(extra, r.status_code, j["emissions"]["uncertainty"], j.get("id"))
