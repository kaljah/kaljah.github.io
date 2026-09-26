"""BUG-089 repro: Scope 3 category encoded as '6' by the UI/API but 'Category 6' by bulk import: the same activity is double counted (duplicate check misses) and category breakdowns split."""
import sys; sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/work/B")
from bulk import *
DB="agentB_rs3cat"; fresh(DB); c=api_client(DB,"admin")
# exactly what Scope3Form.jsx sends: category: parseInt(category)
r=c.post("/api/scope3", json={"facility_id":5,"year":2037,"month":3,"category":6,"sub_category":"Air travel","activity_data":1000,"emission_factor":0.2,"unit":"km"})
s=upload(c,"Date,Facility,Category,Sub Category,Activity Data,Emission Factor,EF Unit\n2037-03,ADR,6,Air travel,1000,0.2,kg\n","3")
rows=sql(DB,"select id,category,sub_category,co2e,status from scope3_emissions where year=2037")
print("UI create:", r.status_code, "; bulk skipped:", s["skipped_count"])
print("rows:", rows)
print("expected: 1 record (bulk row flagged as duplicate of the UI row) and one category label; actual:", len(rows), "records, labels", sorted({x['category'] for x in rows}))
sys.exit(1 if len(rows)>1 else 0)
