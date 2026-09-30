import sys; sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/tools")
from auditlib import api_client, sql
c = api_client("agentD", "admin")
print(sql("agentD","select year, count(*), count(distinct facility_id) from ogmp_surveys group by year"))
for Y in ("2026",):
    om = {f["facility_id"]: f for f in c.get(f"/api/dashboard/ogmp-metrics?year={Y}").get_json()["facilities"]}
    st = {f["facility_id"]: f for f in c.get(f"/api/dashboard/intensity-stats?year={Y}").get_json()}
    diff=[]
    for fid,f in om.items():
        s = st.get(fid)
        if s and (s["current_ogmp_level"] != f["highest_ogmp_level"] or s["reconciliation_status"]!=f["reconciliation_status"]):
            diff.append((fid, f["highest_ogmp_level"], s["current_ogmp_level"], f["reconciliation_status"], s["reconciliation_status"], s["top_down_tch4"], s["total_ch4"], s["variance_pct"]))
    print(Y, "facilities in both:", len(set(om)&set(st)), "level/status mismatches:", len(diff))
    for d in diff[:8]: print("  ", d)
