import sys, json; sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/tools")
from auditlib import api_client, sql
c = api_client("agentB","admin")
def post(p):
    r=c.post("/api/emissions/", json=p); j=r.get_json(); print(r.status_code, json.dumps(j.get("emissions") if j else j), j.get("calculation_method") if j else None)
    if r.status_code==201:
        print(sql("agentB","select id,process_type,fuel_type,quantity,unit,co2_emissions,ch4_emissions,n2o_emissions,co2e_total,status,factor_source from emissions where id=?",(j["id"],)))
base={"source_type":"Combustion","sub_type":"Stationary","facility_id":1,"year":2024,"month":7}
post({**base,"process_type":"Combustion","fuel_type":"Coal","quantity":1000,"unit":"tonnes"})
post({**base,"process_type":"Combustion","fuel":"Coal","amount":1000,"unit":"tonnes"})
post({**base,"process_type":"Combustion","fuel":"Natural Gas","amount":1000,"unit":"MMBtu"})
post({**base,"process_type":"Combustion","fuel":"Coal","amount":1000,"unit":"tonnes","hhv":24930})
