import sys; sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/tools")
from auditlib import make_db, api_client, sql
DB="agentD_gwp"; make_db(DB, overwrite=True)
c = api_client(DB, "admin")
r = c.put("/api/auth/settings", json={"gwp_standard": sys.argv[1]}); print(r.status_code)
import calculations.constants as K; K.invalidate_gwp_cache()
Y=int(sys.argv[2])
rows = sql(DB, "select facility_id, sum(co2_emissions) co2, sum(ch4_emissions) ch4, sum(n2o_emissions) n2o, sum(co2e_total) e from emissions where status='Verified' and year=? group by facility_id", (Y,))
co2=sum(r['co2'] or 0 for r in rows); ch4=sum(r['ch4'] or 0 for r in rows); n2o=sum(r['n2o'] or 0 for r in rows); e=sum(r['e'] or 0 for r in rows)
print("DB co2e(AR6-100)", e, "check", co2+ch4*27.9+n2o*273)
exp20 = co2 + ch4*K.GWP_STANDARDS[sys.argv[1]]["CH4_20"] + n2o*K.GWP_STANDARDS[sys.argv[1]]["N2O_20"]   # app's own AR6 20-yr factors
b = c.get(f"/api/dashboard/batch-all?facilityId=all&activity=all&division=all&gwp_horizon=20").get_json()
summ = [x for x in b["summary"] if x["year"]==Y][0]
st = c.get(f"/api/dashboard/intensity-stats?year={Y}").get_json()
s1_20 = sum(x["total_scope1_gwp20"] for x in st)
print("expected GWP20 S1", exp20)
print("summary scope1_total_gwp20", summ["scope1_total_gwp20"])
print("intensity-stats sum total_scope1_gwp20", s1_20)
