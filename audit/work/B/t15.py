from bulk import *
DB="agentB_b3"; fresh(DB); c=api_client(DB,"admin")
csv="""Date,Facility,Category,Sub Category,Activity Data,Emission Factor,EF Unit
2037-03,ADR,6,Air travel,1000,0.2,kg
2037-03,ADR,6,Hotel nights,1000,0.03,kg
2037-03,ADR,1,Steel,1000,1.5,kg
2037-03,ADR,1,Cement,1000,0.9,kg
,ADR,4,Trucking no date,1000,0.1,kg
03/2037,ADR,7,Commute slash date,1000,0.1,kg
2037-04,ADR,,No category,1000,0.1,kg
"""
s=upload(c,csv,"3"); print(json.dumps({k:s[k] for k in ("status","processed","skipped_count","skipped_preview","errors")},default=str)[:2500])
for r in sql(DB,"select id,year,month,category,sub_category,activity_data,co2e,status from scope3_emissions where id>28"): print(r)
