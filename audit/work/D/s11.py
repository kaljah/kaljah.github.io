import sys, json; sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/tools")
from auditlib import make_db, api_client, sql
DB="agentD_fug"; make_db(DB, overwrite=True)
c = api_client(DB, "admin")
for ptype, fuel, unit in [("fugitive","Fugitive - Valve (Gas/Vapor)","count"), ("fugitive_component","Component - Control Valve","count")]:
    p = {"process_type":ptype,"facility_id":13,"year":2025,"month":1,"quantity":100,"amount":100,"unit":unit,"factor_source":"default","fuel_type":fuel,"fuel":fuel,"activity":"Production","source_type":"Fugitive"}
    r = c.post("/api/emissions/", json=p)
    j = r.get_json(); print(ptype, r.status_code, {k:j.get(k) for k in ("id","message","error")} if isinstance(j,dict) else j)
    rid = j.get("id") or (j.get("emission") or {}).get("id") if isinstance(j,dict) else None
    row = sql(DB,"select id, ch4_emissions, co2e_total, calc_method from emissions order by id desc limit 1")[0]
    print("  stored:", row)
print("expected fugitive valve: 100*0.0045 kg/h*8760 h /1000 =", 100*0.0045*8760/1000, "t/yr (x CH4 fraction if THC)")
print("expected control valve: 100*1.11e-5 t/h*8760 =", 100*1.11e-5*8760)
