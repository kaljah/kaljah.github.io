from h import *
r=c.post("/api/custom-factors/",json=dict(name="C_recalc",co2_factor=2.0,ch4_factor=0.01,n2o_factor=0,unit="kg/m3")); cf=r.get_json()["id"]
s,j=post({"year":2025,"month":2,"facility_id":1,"process_type":"combustion","factor_source":"custom","fuel":str(cf),"fuel_type":str(cf),"amount":1000,"quantity":1000,"unit":"m3","custom_factor_id":cf})
rid=sql(DB,"select max(id) i from emissions")[0]["i"]; print("create",s,rec(rid))
# change the factor
print(c.put(f"/api/custom-factors/{cf}",json={"co2_factor":3.0}).status_code)
print("after factor update",rec(rid))
r=c.put(f"/api/emissions/{rid}",json={"recalculate":True}); print("PUT recalc",r.status_code,r.get_json() if r.status_code>=300 else ""); print(rec(rid))
# delete factor: referenced?
r=c.delete(f"/api/custom-factors/{cf}"); print("DELETE cf",r.status_code,r.get_json())
r=c.put(f"/api/emissions/{rid}",json={"recalculate":True,"custom_factor_id":cf}); print("PUT recalc w/ deleted cf",r.status_code); print(rec(rid))
# catalog-name custom
r=c.post("/api/custom-factors/",json=dict(name="C_recalc2",co2_factor=2.0,ch4_factor=0.0,n2o_factor=0,unit="kg/m3")); cf2=r.get_json()["id"]
s,j=post({"year":2025,"month":2,"facility_id":1,"process_type":"combustion","factor_source":"custom","fuel":"Natural Gas","fuel_type":"Natural Gas","amount":1000,"quantity":1000,"unit":"m3","custom_factor_id":cf2})
rid=sql(DB,"select max(id) i from emissions")[0]["i"]; print("create NGname",rec(rid))
r=c.put(f"/api/emissions/{rid}",json={"recalculate":True}); print("PUT",r.status_code, rec(rid))
