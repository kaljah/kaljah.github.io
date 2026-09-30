"""Categorical breakdown groups by facility NAME, merging distinct facilities. Exits 1 while bug exists."""
import sys, sqlite3; sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/tools")
from auditlib import api_client, db_path
c = api_client("repro_F", "admin")
con = sqlite3.connect(db_path("repro_F"))
ids = [r[0] for r in con.execute("select distinct e.facility_id from emissions e join facilities f on f.id=e.facility_id where e.status='Verified' and f.name='Updated Facility'")]
cat = c.get("/api/dashboard/batch-all?facilityId=all&activity=all&division=all").get_json()["categorical_breakdown"]
cards = [x for x in cat if x["region"] == "Updated Facility"]
print(f"facilities named 'Updated Facility' with Verified emissions: {len(ids)} ids={ids}; categorical cards returned: {len(cards)} -> {[round(x['total_emissions'],2) for x in cards]}")
sys.exit(1 if len(cards) < len(ids) else 0)
