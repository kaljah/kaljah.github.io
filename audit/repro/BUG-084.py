"""QA/QC dashboard reports 'Zero Anomalies … fully verified and audit-compliant' although Pending records exist and
records 10^6× larger than the median are present: anomaly queue only lists stored qa_flag values. Exits 1 while bug exists."""
import sys, sqlite3, statistics; sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/tools")
from auditlib import api_client, db_path
c = api_client("repro_F", "admin")
con = sqlite3.connect(db_path("repro_F"))
q = c.get("/api/qaqc/dashboard?limit=100&offset=0&status=all").get_json()
vals = [r[0] for r in con.execute("select co2e_total from emissions where co2e_total>0")]
med = statistics.median(vals)
outl = con.execute("select count(*) from emissions where co2e_total > ?", (med * 1e6,)).fetchone()[0]
pend = sum(con.execute(f"select count(*) from {t} where status='Pending'").fetchone()[0] for t in ("emissions", "scope2_emissions", "scope3_emissions"))
print(f"QA API total_flagged={q.get('total_flagged_count')} ; independent: Pending records={pend}, records > 1e6 x median ({med:,.2f} t) = {outl}")
sys.exit(1 if q.get("total_flagged_count") == 0 and (outl > 0 or pend > 0) else 0)
