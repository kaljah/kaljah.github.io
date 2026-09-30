"""BUG-079: year=all OGMP reconciliation compares avg(top-down) vs sum(bottom-up). Exits 1 while bug exists."""
import sys; sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/tools")
from auditlib import make_db, api_client, sql
DB = "agentD_r079"; make_db(DB, overwrite=True)
c = api_client(DB, "admin")
fid = 169
bu = {r["year"]: r["s"] for r in sql(DB, "select year, sum(ch4_emissions) s from emissions where facility_id=? and status='Verified' group by year", (fid,))}
for y, v in bu.items():
    c.post("/api/data/ogmp-surveys", json={"facility_id": fid, "year": y, "survey_date": f"{y}-06-01", "measured_rate_kg_hr": v * 1000 / 8760})
om = c.get(f"/api/dashboard/ogmp-metrics?year=all&facilityId={fid}").get_json()["facilities"][0]
print(f"each year reconciles at 0%; expected all-years variance ~0% Reconciled; actual {om['reconciliation_variance_pct']}% {om['reconciliation_status']}")
v = om["reconciliation_variance_pct"]
sys.exit(1 if v is None or abs(v) > 1 else 0)
