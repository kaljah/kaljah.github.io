"""BUG-072: pending banner totalCo2e identical in GWP-100 and GWP-20. Exits 1 while bug exists."""
import sys; sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/tools")
from auditlib import make_db, api_client, sql
DB = "agentD_r072"; make_db(DB, overwrite=True)
c = api_client(DB, "admin")
Y = 2025
q = f"/api/dashboard/batch-all?facilityId=all&activity=all&division=all&year={Y}"
p20 = c.get(q + "&gwp_horizon=20").get_json()["pending_stats"]["totalCo2e"]
s1 = sql(DB, "select sum(co2_emissions) co2, sum(ch4_emissions) ch4, sum(n2o_emissions) n2o from emissions where status='Pending' and year=?", (Y,))[0]
s2 = sql(DB, "select coalesce(sum(co2e),0) e from scope2_emissions where status='Pending' and year=?", (Y,))[0]["e"]
exp = s1["co2"] + s1["ch4"] * 82.5 + s1["n2o"] * 268 + s2   # app's own active AR5 20-yr factors
print(f"expected GWP-20 pending: {exp:,.1f}   banner (gwp_horizon=20): {p20:,.1f}")
sys.exit(1 if abs(p20 - exp) > 1 else 0)
