"""BUG-080: /intensity-stats OGMP level differs from canonical /ogmp-metrics. Exits 1 while bug exists."""
import sys; sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/tools")
from auditlib import make_db, api_client, sql
DB = "agentD_r080"; make_db(DB, overwrite=True)
c = api_client(DB, "admin")
fid, Y = 169, 2021
bu = sql(DB, "select sum(ch4_emissions) s from emissions where facility_id=? and year=? and status='Verified'", (fid, Y))[0]["s"]
c.post("/api/data/ogmp-surveys", json={"facility_id": fid, "year": Y, "survey_date": f"{Y}-06-01", "measured_rate_kg_hr": bu * 1000 / 8760})
a = c.get(f"/api/dashboard/ogmp-metrics?year={Y}&facilityId={fid}").get_json()["facilities"][0]["highest_ogmp_level"]
b = [x for x in c.get(f"/api/dashboard/intensity-stats?year={Y}&facilityId={fid}").get_json() if x["facility_id"] == fid][0]["current_ogmp_level"]
print(f"ogmp-metrics level {a}; intensity-stats level {b} (expected equal)")
sys.exit(1 if a != b else 0)
