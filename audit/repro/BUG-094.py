"""Net Emissions KPI: mitigation ignores Activity/Division filters and counts 'Planned' projects. Exits 1 while bug exists."""
import sys, sqlite3; sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/tools")
from auditlib import api_client, db_path
c = api_client("repro_F", "admin")
con = sqlite3.connect(db_path("repro_F"))
bad = False
for act in ("Steel & Iron (Acier DRI)", "all"):
    b = c.get("/api/dashboard/batch-all", query_string={"facilityId": "all", "activity": act, "division": "all"}).get_json()
    gross = sum(r["scope1_total"] + r["scope2_total"] for r in b["summary"])
    mit = sum(m["quantity_tco2e"] for m in b["mitigation"])
    planned = sum(m["quantity_tco2e"] for m in b["mitigation"] if m.get("status") == "Planned")
    q = "select coalesce(sum(p.quantity_tco2e),0) from mitigation_projects p join facilities f on f.id=p.facility_id where p.status<>'Planned'" + ("" if act == "all" else " and f.activity=?")
    exp_mit = con.execute(q, () if act == "all" else (act,)).fetchone()[0]
    print(f"activity={act}: gross={gross:,.2f} mitigation used={mit:,.2f} (incl. Planned {planned:,.2f}) -> Net={gross-mit:,.2f} ; expected mitigation (facility activity, implemented only)={exp_mit:,.2f}")
    bad |= abs(mit - exp_mit) > 0.01
sys.exit(1 if bad else 0)
