import sys; sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/tools")
from auditlib import api_client, db_path
import sqlite3
c = api_client("agentE", "admin"); con=sqlite3.connect(db_path("agentE"))
st = c.get("/api/dashboard/intensity-stats?year=all").get_json()
prod_years = {}
for fid,y in con.execute("select distinct facility_id, year from production_data"): prod_years.setdefault(fid,set()).add(y)
for x in sorted(st, key=lambda x:x['facility_id']):
    fid=x['facility_id']
    if x['total_boe']<=0: continue
    em_years = {y:e for y,e in con.execute("select year, sum(co2e_total) from emissions where status='Verified' and facility_id=? group by year",(fid,))}
    unmatched = {y:e for y,e in em_years.items() if y not in prod_years.get(fid,set())}
    if unmatched:
        print(fid, x['facility_name'], "API int", round(x['co2_intensity'],3), "prod years", sorted(prod_years[fid]), "emission yrs w/o prod", {k:round(v,1) for k,v in unmatched.items()})
