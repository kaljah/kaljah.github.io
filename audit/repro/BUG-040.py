"""Supply-Chain (segment) filter is not applied to the per-source split in _query_summary, so
Combustion+Flaring+Venting+Other != Scope 1 under a segment filter. Exits 1 while bug exists."""
import sys, sqlite3; sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/tools")
from auditlib import api_client, db_path
c = api_client("repro_F", "admin")
con = sqlite3.connect(db_path("repro_F"))
bad = False
for seg in ("Heavy Industry", "Upstream"):
    S = c.get(f"/api/dashboard/batch-all?facilityId=all&activity=all&division=all&segment={seg}").get_json()["summary"]
    s1 = sum(r["scope1_total"] for r in S)
    src = {k: sum(r[k] for r in S) for k in ("combustion", "flaring", "venting", "other")}
    exp = con.execute("select sum(e.co2e_total) from emissions e join facilities f on f.id=e.facility_id where e.status='Verified' and f.segment=?", (seg,)).fetchone()[0]
    fl_exp = con.execute("select coalesce(sum(e.co2e_total),0) from emissions e join facilities f on f.id=e.facility_id where e.status='Verified' and f.segment=? and lower(e.process_type) like '%flar%'", (seg,)).fetchone()[0]
    print(f"segment={seg}: Scope1 KPI={s1:,.2f} (SQL {exp:,.2f}) | sum of sources={sum(src.values()):,.2f} | flaring shown={src['flaring']:,.2f} expected {fl_exp:,.2f}")
    bad |= abs(sum(src.values()) - s1) > 1
sys.exit(1 if bad else 0)
