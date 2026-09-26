"""BUG-085 repro: Scope 2/3 bulk rows with blank or non-ISO date are silently booked to 2024-01; blank category stored as 'Category '."""
import sys; sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/work/B")
from bulk import *
DB="agentB_rdate"; fresh(DB); c=api_client(DB,"admin")
s3=upload(c,"Date,Facility,Category,Sub Category,Activity Data,Emission Factor,EF Unit\n,ADR,4,no date,1000,0.1,kg\n03/2037,ADR,7,slash date,1000,0.1,kg\n2037-04,ADR,,blank category,1000,0.1,kg\n","3")
s2=upload(c,"Date,Facility,Source Type,Consumption,Unit,Grid Region\n,ADR,electricity,3000,kWh,Algerian National Grid\n","2")
r3=sql(DB,"select year,month,category,sub_category from scope3_emissions where sub_category in ('no date','slash date','blank category')")
r2=sql(DB,"select year,month,electricity_kwh from scope2_emissions where electricity_kwh=3000 and id>37")
print("expected: rows rejected (missing/invalid date, missing category)")
print("scope3 stored:", r3, "skipped", s3["skipped_count"]); print("scope2 stored:", r2, "skipped", s2["skipped_count"])
sys.exit(1 if r3 or r2 else 0)
