"""Preview-Pending toggle only reaches _query_summary; categorical breakdown (activity donut, categorical overview,
organizational breakdown), Scope 3, flaring and intensity stay Verified-only. Exits 1 while bug exists."""
import sys, sqlite3; sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/tools")
from auditlib import api_client, db_path
c = api_client("repro_F", "admin")
con = sqlite3.connect(db_path("repro_F"))
b = c.get("/api/dashboard/batch-all?facilityId=all&activity=all&division=all&includePending=true").get_json()
kpi = sum(r["scope1_total"] + r["scope2_total"] for r in b["summary"])
cat = sum(x["total_emissions"] for x in b["categorical_breakdown"])
exp = con.execute("select (select sum(co2e_total) from emissions where status in ('Verified','Pending')) + (select sum(co2e) from scope2_emissions where status in ('Verified','Pending'))").fetchone()[0]
s3 = con.execute("select sum(co2e) from scope3_emissions where status in ('Verified','Pending')").fetchone()[0]
print(f"includePending: Gross KPI={kpi:,.2f} (SQL V+P {exp:,.2f}) | categorical/org-breakdown sum={cat:,.2f} | Scope3={b['scope3_summary']['total']} (SQL V+P {s3})")
sys.exit(1 if abs(cat - kpi) > 1 else 0)
