import sys; sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/tools")
from auditlib import api_client, sql
c = api_client("agentD", "admin")
rows = sql("agentD","""select s.facility_id fid, avg(s.estimated_annual_tch4) td,
 (select sum(ch4_emissions) from emissions e where e.facility_id=s.facility_id and e.status='Verified') bu_all,
 (select sum(ch4_emissions) from emissions e where e.facility_id=s.facility_id and e.status='Verified' and e.year=2026) bu_2026,
 (select count(distinct year) from emissions e where e.facility_id=s.facility_id and e.status='Verified') ny
 from ogmp_surveys s group by s.facility_id having bu_all>0""")
for r in rows[:10]: print(r)
om_all = {f["facility_id"]: f for f in c.get("/api/dashboard/ogmp-metrics?year=all").get_json()["facilities"]}
om_26 = {f["facility_id"]: f for f in c.get("/api/dashboard/ogmp-metrics?year=2026").get_json()["facilities"]}
for r in rows[:10]:
    a=om_all.get(r["fid"]); b=om_26.get(r["fid"])
    print(r["fid"], "all:", a and (a["reconciliation_variance_pct"], a["reconciliation_status"]), "2026:", b and (b["reconciliation_variance_pct"], b["reconciliation_status"]))
