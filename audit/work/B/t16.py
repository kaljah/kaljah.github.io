from bulk import *
DB="agentB_b2"; fresh(DB); c=api_client(DB,"admin")
csv="""Date,Facility,Source Type,Consumption,Unit,Grid Region
2037-03,ADR,electricity,1000,kWh,Algerian National Grid
2037-03,ADR,electricity,2000,kWh,Algerian National Grid
,ADR,electricity,3000,kWh,Algerian National Grid
03/2037,ADR,electricity,4000,kWh,Algerian National Grid
"""
s=upload(c,csv,"2"); print(json.dumps({k:s[k] for k in ("status","processed","skipped_count","errors")},default=str), [x["reason"][:90] for x in s["skipped_preview"]])
for r in sql(DB,"select id,year,month,source_type,electricity_kwh,co2e,status from scope2_emissions where id>37"): print(r)
# across uploads, overwrite: scope3 different subcategory
csv3a="Date,Facility,Category,Sub Category,Activity Data,Emission Factor,EF Unit\n2037-05,ADR,6,Air travel,1000,0.2,kg\n"
csv3b="Date,Facility,Category,Sub Category,Activity Data,Emission Factor,EF Unit\n2037-05,ADR,6,Hotel nights,1000,0.03,kg\n"
upload(c,csv3a,"3"); s=upload(c,csv3b,"3",{"overwrite_duplicates":"true"}); print(s["status"], s["skipped_count"])
for r in sql(DB,"select id,year,month,category,sub_category,co2e,status from scope3_emissions where year=2037"): print(r)
