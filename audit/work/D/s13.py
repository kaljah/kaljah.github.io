import sys; sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/tools")
from auditlib import make_db, api_client, sql
DB="agentD_sat"; make_db(DB, overwrite=True)
c = api_client(DB, "admin")
fid=169
bu = sql(DB,"select sum(ch4_emissions) s from emissions where facility_id=? and year=2025 and status='Verified'",(fid,))[0]["s"]
# exactly what MethaneExplorer.handleExportToOgmp sends
r = c.post("/api/satellite/sentinel5p/export-to-ogmp", json={"facility_id":fid,"observation_date":"2025-07-01","ch4_column_ppb":1900,"anomaly_ppb":10,"estimated_emission_rate_kg_hr":100.0,"qa_score":0.8,"notes":"x"})
print(r.status_code, r.get_json())
s = sql(DB,"select measured_rate_kg_hr, operating_hours_year, estimated_annual_tch4, bottom_up_tch4, variance_pct, variance_flag, reconciliation_status, status from ogmp_surveys order by id desc limit 1")[0]
print("stored:", s)
print("bottom-up 2025 tCH4:", bu, " continuous annual equivalent of 100 kg/h:", 100*8760/1000)
om = [f for f in c.get(f"/api/dashboard/ogmp-metrics?year=2025&facilityId={fid}").get_json()["facilities"]][0]
print("ogmp-metrics:", {k:om[k] for k in ("highest_ogmp_level","reconciliation_variance_pct","reconciliation_status")})
