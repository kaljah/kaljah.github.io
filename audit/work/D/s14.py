import sys; sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/tools")
from auditlib import make_db, api_client, sql
DB="agentD_all"; make_db(DB, overwrite=True)
c = api_client(DB, "admin")
fid=169
bu = {r["year"]: r["s"] for r in sql(DB,"select year, sum(ch4_emissions) s from emissions where facility_id=? and status='Verified' group by year",(fid,))}
print("bottom-up by year:", bu)
for y, v in bu.items():   # one survey per year that exactly matches that year's bottom-up
    c.post("/api/data/ogmp-surveys", json={"facility_id":fid,"year":y,"survey_date":f"{y}-06-01","measured_rate_kg_hr": v*1000/8760})
for Y in [*bu.keys(), "all"]:
    om = c.get(f"/api/dashboard/ogmp-metrics?year={Y}&facilityId={fid}").get_json()["facilities"][0]
    st = [x for x in c.get(f"/api/dashboard/intensity-stats?year={Y}&facilityId={fid}").get_json() if x["facility_id"]==fid][0]
    print(Y, "ogmp-metrics:", om["reconciliation_variance_pct"], om["reconciliation_status"], om["highest_ogmp_level"], "| intensity-stats td/bu:", round(st["top_down_tch4"],2), round(st["total_ch4"],2), st["variance_pct"], st["current_ogmp_level"])
