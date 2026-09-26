import sys, json; sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/tools")
from auditlib import api_client, sql
c = api_client("agentB","admin")
for fuel in ("Natural Gas","Butane"):
  for unit,amt in (("mmscf",1),("scf",1e6),("MMBtu",1026)):
    r=c.post("/api/emissions/", json={"process_type":"stationary_combustion","facility_id":1,"year":2021,"month":1,"fuel":fuel,"fuel_type":fuel,"amount":amt,"quantity":amt,"unit":unit})
    j=r.get_json(); print(fuel,unit,amt,r.status_code,j.get("emissions",j), j.get("calculation_method"))
