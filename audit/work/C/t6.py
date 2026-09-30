from h import *
import io, time
c.post("/api/custom-factors/",json=dict(name="C bulk cf",co2_factor=2.0,ch4_factor=0.01,n2o_factor=0,unit="kg/m3"))
fac=sql(DB,"select name from facilities where id=1")[0]["name"]
csv="Facility,Date,Process,Fuel,Factor Type,Quantity,Unit,Equipment\n"
rows=[("combustion","Natural Gas","default",1000,"scf","e1"),
      ("combustion","Natural Gas","specific",1000,"scf","e2"),
      ("flaring","Natural Gas (Flaring)","specific",1000,"m3","e3"),
      ("combustion","C bulk cf","custom",1000,"m3","e4"),
      ("combustion","No Such Custom","custom",1000,"m3","e5"),
      ("combustion","Butane","default",1000,"scf","e6"),
      ("venting","Blowdown - Pipeline","default",2,"event","e7")]
for p,f,t,q,u,e in rows: csv+=f'"{fac}",2025-06,{p},{f},{t},{q},{u},{e}\n'
r=c.post("/api/emissions/upload/start",data={"file":(io.BytesIO(csv.encode()),"c.csv"),"scope":"1"},content_type="multipart/form-data")
print(r.status_code,r.get_json()); jid=r.get_json().get("job_id")
for _ in range(60):
    s=c.get(f"/api/emissions/upload/status/{jid}").get_json()
    if s.get("status")!="processing": break
    time.sleep(0.5)
print({k:s.get(k) for k in ["status","processed","total","skipped","errors"]})
for r in sql(DB,"select id,process_type,fuel_type,equipment_id,co2_emissions,ch4_emissions,co2e_total,calc_method,factor_source,ef_used_co2,uncertainty,source_payload from emissions where year=2025 and month=6 and facility_id=1 order by id"):
    sp=json.loads(r.pop("source_payload")); r["sp_fs"]=sp.get("factor_source"); r["sp_ch4c"]=sp.get("ch4_content"); print(r)
