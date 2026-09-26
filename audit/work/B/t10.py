import sys, json; sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/tools")
from auditlib import make_db, api_client, sql
import logging; logging.disable(logging.CRITICAL)
DB="agentB_t10"; make_db(DB, overwrite=True)
c = api_client(DB,"admin")
fid=5; yr=2039
recs=[{"process_type":"flaring","fuel":"Natural Gas (Flaring)","amount":100000,"unit":"scf"},
      {"process_type":"combustion","fuel":"Natural Gas","amount":1000,"unit":"MMBtu"}]
for p in recs:
    r=c.post("/api/emissions/", json={**p,"facility_id":fid,"year":yr,"month":1,"factor_source":"default"}); print(r.status_code, r.get_json().get("emissions"))
print(sql(DB,"select process_type,factor_source,ch4_emissions,co2e_total from emissions where year=?",(yr,)))
j=c.get(f"/api/dashboard/intensity-stats?year={yr}&facilityId={fid}").get_json()
rows=j if isinstance(j,list) else j.get("data", j)
print(json.dumps(rows, default=str)[:3000])
