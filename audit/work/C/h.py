import sys, json
sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/tools")
from auditlib import make_db, api_client, sql, get_app
DB="agentC"
make_db(DB)
c = api_client(DB, "admin")
def fac():
    return sql(DB,"select id,name,region,location from facilities limit 3")
def post(payload):
    r = c.post("/api/emissions/", json=payload)
    j = r.get_json()
    return r.status_code, j
def rec(i):
    return sql(DB,"select id,fuel_type,quantity,unit,co2_emissions,ch4_emissions,n2o_emissions,co2e_total,calc_method,factor_source,uncertainty from emissions where id=?",(i,))
