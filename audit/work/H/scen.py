import sys, json; sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/tools")
from auditlib import make_db, api_client, sql
DB="agentH_scen"
make_db(DB, overwrite=True)
# wipe emissions, insert controlled rows. Facility 1 = West, Facility 3 = Center
for t in ["emissions","scope2_emissions","scope3_emissions","sbti_targets","base_year_recalculations"]:
    sql(DB,f"delete from {t}")
def s1(fid,y,m,v): sql(DB,"insert into emissions(year,month,facility_id,co2e_total,co2_emissions,status) values(?,?,?,?,?,'Verified')",(y,m,fid,v,v))
def s2(fid,y,m,v): sql(DB,"insert into scope2_emissions(year,month,facility_id,co2e,status) values(?,?,?,?,'Verified')",(y,m,fid,v))
def s3(fid,y,m,v): sql(DB,"insert into scope3_emissions(year,month,facility_id,co2e,status) values(?,?,?,?,'Verified')",(y,m,fid,v))
# base 2020: West S1 400, Center S1 300, West S2 100, Center S3 200 -> total 1000; S1+S2 800; West 500
s1(1,2020,6,400); s1(3,2020,6,300); s2(1,2020,6,100); s3(3,2020,6,200)
# 2023: West S1 350, Center S1 300, West S2 100, Center S3 200 -> total 950; S1+S2 750; West 450
s1(1,2023,6,350); s1(3,2023,6,300); s2(1,2023,6,100); s3(3,2023,6,200)
c = api_client(DB,"admin")
r=c.get("/api/manage/sbti?base_year=2020"); print("suggest",r.get_json())
r=c.post("/api/manage/sbti",json={"base_year":2020,"base_year_emissions":1000,"target_year":2030,"reduction_rate_pct":4.2,"pathway_type":"1.5C"}); print(r.status_code,r.get_json())
def show(u,cl=c):
    d=cl.get(u).get_json(); t=d.pop("trajectory",None); print(u, json.dumps({k:d.get(k) for k in ["latest_actual_year","current_actual","current_target","reduction_achieved_pct","on_track","base_year_emissions","target_emissions_final","error"]}))
    return t
t=show("/api/dashboard/sbti-trajectory")
for x in t: print("  ",x["year"],x["sbti_target"],x["actual"])
show("/api/dashboard/sbti-trajectory?scope=s1_s2")
show("/api/dashboard/sbti-trajectory?scope=s3")
show("/api/dashboard/sbti-trajectory?facility_id=1")
show("/api/dashboard/sbti-trajectory?facility_id=4")
# partial current year
s1(1,2026,1,50)
show("/api/dashboard/sbti-trajectory")
