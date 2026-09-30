import sys, json; sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/tools")
from auditlib import api_client, sql
import logging; logging.disable(logging.CRITICAL)
F=json.load(open("client_factors.json",encoding="utf8"))
c = api_client("agentB","admin")
zero=[]; ok=[]
for k,v in F.items():
    for proc in v["usage"]:
        if proc not in ("combustion","flaring","venting"): continue
        unit = v["baseUnit"] or "scf"
        p={"process_type":proc,"facility_id":1,"year":2023,"month":1,"fuel":k,"fuel_type":k,"amount":1000000,"quantity":1000000,"unit":unit,"factor_source":"default"}
        r=c.post("/api/emissions/", json=p); j=r.get_json()
        t=j.get("emissions",{}).get("totalCo2e") if r.status_code==201 else None
        (zero if not t else ok).append((proc,k,unit,r.status_code,t,j.get("calculation_method"), j.get("error")))
print("ZERO/FAILED:"); [print(z) for z in zero]
print(len(ok),"ok")
