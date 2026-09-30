"""BUG-068 repro: indirect_steam accepted as Scope 1 and summed into scope1_total."""
import sys; sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/tools")
from auditlib import make_db, api_client, sql
import logging; logging.disable(logging.CRITICAL)
DB="agentB_r068"; make_db(DB, overwrite=True)
c = api_client(DB,"admin")
r=c.post("/api/emissions/", json={"process_type":"indirect_steam","facility_id":1,"year":2030,"month":1,"amount":1000,"quantity":1000,"unit":"MMBtu","heat_unit":"mmbtu","boiler_eff":0.8,"fuel":"Natural Gas"})
print("create:", r.status_code)
j=c.get("/api/dashboard/summary?year=2030").get_json()
s1=sum(x["scope1_total"] for x in j); s2=sum(x["scope2_total"] for x in j)
print(f"expected scope1=0 scope2=66.33 (or 4xx on create); actual scope1={s1} scope2={s2}")
sys.exit(1 if r.status_code==201 and s1>0 else 0)
