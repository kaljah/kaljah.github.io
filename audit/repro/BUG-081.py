"""BUG-081 repro: Scope 2/3 bulk duplicate key too coarse -> distinct records dropped, or overwritten with overwrite on."""
import sys; sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/work/B")
from bulk import *
DB="agentB_rdup"; fresh(DB); c=api_client(DB,"admin")
s=upload(c,"Date,Facility,Category,Sub Category,Activity Data,Emission Factor,EF Unit\n2037-03,ADR,6,Air travel,1000,0.2,kg\n2037-03,ADR,6,Hotel nights,1000,0.03,kg\n","3")
n3=sql(DB,"select count(*) n, sum(co2e) s from scope3_emissions where year=2037 and month=3")[0]
s=upload(c,"Date,Facility,Source Type,Consumption,Unit,Grid Region\n2037-03,ADR,electricity,1000,kWh,Algerian National Grid\n2037-03,ADR,electricity,2000,kWh,Algerian National Grid\n","2")
n2=sql(DB,"select count(*) n, sum(electricity_kwh) s from scope2_emissions where year=2037 and month=3")[0]
upload(c,"Date,Facility,Category,Sub Category,Activity Data,Emission Factor,EF Unit\n2037-05,ADR,6,Air travel,1000,0.2,kg\n","3")
upload(c,"Date,Facility,Category,Sub Category,Activity Data,Emission Factor,EF Unit\n2037-05,ADR,6,Hotel nights,1000,0.03,kg\n","3",{"overwrite_duplicates":"true"})
n5=sql(DB,"select count(*) n, sum(co2e) s from scope3_emissions where year=2037 and month=5")[0]
print(f"S3 same cat/month two sub-categories: expected 2 rows 0.23 t, actual {n3}")
print(f"S2 two meters same month: expected 2 rows 3000 kWh, actual {n2}")
print(f"S3 2nd upload w/ overwrite, other sub-category: expected 2 rows 0.23 t, actual {n5}")
sys.exit(1 if n3['n']<2 or n2['n']<2 or n5['n']<2 else 0)
