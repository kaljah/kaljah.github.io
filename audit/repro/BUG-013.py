"""BUG-013: AR5 GWP-20 applied to CH4 is 82.5 (IPCC AR5 Table 8.7: 84). Exits 1 while bug exists."""
import sys; sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/tools")
from auditlib import make_db, api_client, sql
DB = "agentD_r013"; make_db(DB, overwrite=True)
c = api_client(DB, "admin")
Y = 2026
r = sql(DB, "select sum(co2_emissions) co2, sum(ch4_emissions) ch4, sum(n2o_emissions) n2o from emissions where status='Verified' and year=?", (Y,))[0]
expected = (r["co2"] or 0) + (r["ch4"] or 0) * 84 + (r["n2o"] or 0) * 264   # IPCC AR5 WG1 Table 8.7
b = c.get("/api/dashboard/batch-all?facilityId=all&activity=all&division=all&gwp_horizon=20").get_json()
row = [x for x in b["summary"] if x["year"] == Y][0]
implied = (row["scope1_total_gwp20"] - row["scope1_total_gwp100"]) / row["ch4_total"] + 28
print(f"implied CH4 GWP-20 applied: {implied:.2f} (expected 84)")
print(f"expected GWP-20 Scope1 {Y}: {expected:,.2f}  actual: {row['scope1_total_gwp20']:,.2f}")
sys.exit(1 if abs(row["scope1_total_gwp20"] - expected) > 0.5 else 0)
