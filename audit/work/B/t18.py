from bulk import *
DB="agentB_yr"; fresh(DB); c=api_client(DB,"admin")
r=c.post("/api/emissions/", json={"process_type":"combustion","facility_id":1,"year":2099,"month":1,"fuel":"Natural Gas","amount":1000,"unit":"MMBtu"}); print("POST 2099", r.status_code)
r=c.post("/api/emissions/", json={"process_type":"combustion","facility_id":1,"year":1800,"month":1,"fuel":"Natural Gas","amount":1000,"unit":"MMBtu"}); print("POST 1800", r.status_code)
s=upload(c,"Date,Facility,Process,Fuel,Quantity,Unit,Factor Type\n1800-01,ADR,combustion,Natural Gas,1000,MMBtu,default\n9999-01,ADR,combustion,Natural Gas,1000,MMBtu,default\n2030-13,ADR,combustion,Natural Gas,1000,MMBtu,default\n","1")
print("bulk S1", s["status"], s["skipped_count"], [x["reason"][:60] for x in s["skipped_preview"]])
print(sql(DB,"select year,month,status from emissions where id>751"))
s=upload(c,"Date,Facility,Source Type,Consumption,Unit,Grid Region\n1800-01,ADR,electricity,1000,kWh,Algerian National Grid\n2030-13,ADR,electricity,1000,kWh,Algerian National Grid\n","2")
print("bulk S2", s["status"], s["skipped_count"], sql(DB,"select year,month from scope2_emissions where id>37"))
