"""BUG-071 repro: dashboard cache not invalidated after POST /api/emissions/ (flush-before-commit defeats before_commit hook)."""
import sys; sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/tools")
from auditlib import make_db, api_client, sql
import logging; logging.disable(logging.CRITICAL)
DB="agentB_rcache"; make_db(DB, overwrite=True)
c = api_client(DB,"admin")
def tot():
    j=c.get("/api/dashboard/summary?year=2024").get_json(); return sum(r["scope1_total"] for r in j)
before=tot()
c.post("/api/emissions/", json={"process_type":"combustion","facility_id":1,"year":2024,"month":1,"fuel":"Natural Gas","amount":1000,"unit":"MMBtu"})
after=tot()
db_sum=sql(DB,"select sum(co2e_total) s from emissions where year=2024 and status='Verified'")[0]["s"]
print(f"before={before:.4f} after={after:.4f} db={db_sum:.4f} expected after-before=53.1145 actual diff={after-before:.4f}")
sys.exit(1 if abs((after-before)-53.1145)>1e-3 else 0)
