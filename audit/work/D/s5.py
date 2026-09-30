import sys; sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/tools")
from auditlib import make_db, api_client, sql
DB="agentD_ogmp"; make_db(DB, overwrite=True)
fid=169; Y=2025
print(sql(DB,"select status, factor_source, ogmp_level, count(*) n, sum(ch4_emissions) ch4 from emissions where facility_id=? and year=? group by 1,2,3",(fid,Y)))
c = api_client(DB, "admin")
lvl = lambda: [f for f in c.get(f"/api/dashboard/ogmp-metrics?year={Y}&facilityId={fid}").get_json()["facilities"]][0]["highest_ogmp_level"]
print("before", lvl())
sql(DB,"insert into emissions (record_id, year, month, process_type, factor_source, calc_method, ch4_emissions, co2e_total, status, facility_id, ogmp_level) values ('audit-d-rej',?,1,'venting','specific','Blowdown Events',0.001,0.028,'Rejected',?,4)",(Y,fid))
from routes.dashboard import clear_dashboard_cache; clear_dashboard_cache()
print("after adding one REJECTED 0.001 t specific record:", lvl())
