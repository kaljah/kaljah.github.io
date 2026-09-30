"""BUG-005: intensity-stats GWP-20 uses hard-coded AR5 GWP-100 base (28/265). Exits 1 while bug exists."""
import sys; sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/tools")
from auditlib import make_db, api_client, sql
DB = "agentD_r005"; make_db(DB, overwrite=True)
c = api_client(DB, "admin")
assert c.put("/api/auth/settings", json={"gwp_standard": "AR4"}).status_code == 200
import calculations.constants as K; K.invalidate_gwp_cache()
Y = 2021
r = sql(DB, "select sum(co2_emissions) co2, sum(ch4_emissions) ch4, sum(n2o_emissions) n2o from emissions where status='Verified' and year=?", (Y,))[0]
expected = r["co2"] + r["ch4"] * 72 + r["n2o"] * 289   # AR4 20-yr, hand math
st = c.get(f"/api/dashboard/intensity-stats?year={Y}").get_json()
actual = sum(x["total_scope1_gwp20"] for x in st)
print(f"expected GWP-20 Scope1 {Y}: {expected:,.2f}\nactual intensity-stats:   {actual:,.2f}\ndiff: {actual-expected:,.2f}")
sys.exit(1 if abs(actual - expected) > 1.0 else 0)
