import sys, json; sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/tools")
from auditlib import api_client, make_db
name="agentE_flare2"; make_db(name, overwrite=True)
c = api_client(name, "admin")
def fs(): return c.get("/api/dashboard/flaring-summary?year=2026&facilityId=13").get_json()
def ist(): return [x for x in c.get("/api/dashboard/intensity-stats?year=2026&facilityId=13").get_json() if x['facility_id']==13][0]
b=fs(); bi=ist()
r = c.post("/api/data/production", json={"facility_id":13,"year":2026,"month":7,"oil_amount":0,"gas_amount":1000000,"oil_unit":"bbl","gas_unit":"m³"})
print(r.status_code, r.get_json())
a=fs(); ai=ist()
print("flaring-summary gas_production_m3 delta: expected 1,000,000 actual", a["gas_production_m3"]-b["gas_production_m3"])
print("intensity-stats total_gas_m3 delta:", ai["total_gas_m3"]-bi["total_gas_m3"], "boe delta", ai["total_boe"]-bi["total_boe"], "(expected 1e6*0.0353147*0.178 =", 1e6*0.0353147*0.178, ")")
