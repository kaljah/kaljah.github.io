"""Flaring panel ignores 'All Years' (uses current calendar year) and activity/division/segment filters.
Prints expected vs actual; exits 1 while the bug exists. Uses audit db 'repro_F' (copy of snapshot)."""
import sys, sqlite3; sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/tools")
from auditlib import api_client, db_path
c = api_client("repro_F", "admin")
con = sqlite3.connect(db_path("repro_F"))
# Independent: all-years verified flaring CO2e straight from the table (same substring rule the summary uses)
exp_all = con.execute("select sum(co2e_total) from emissions where status='Verified' and lower(process_type) like '%flar%'").fetchone()[0]
f = c.get("/api/dashboard/flaring-summary?facilityId=all&activity=all&division=all").get_json()
b = c.get("/api/dashboard/batch-all?facilityId=all&activity=all&division=all").get_json()
detail_flaring = sum(r["flaring"] for r in b["summary"])
streams = sum(f[k]["tco2e"] for k in ("routine_flaring", "non_routine_flaring", "safety_flaring"))
print(f"All Years: flaring-summary.year={f['year']}  total_tco2e={f['total_flaring']['tco2e']}  streams sum={streams}")
print(f"Detailed Breakdown 'Flaring' (batch summary, all years)={detail_flaring:.2f}  independent SQL={exp_all:.2f}")
# Segment filter: a segment with no flaring must not show flaring
fs = c.get("/api/dashboard/flaring-summary?facilityId=all&activity=all&division=all&segment=Heavy%20Industry&year=2025").get_json()
exp_seg = con.execute("select coalesce(sum(e.co2e_total),0) from emissions e join facilities f on f.id=e.facility_id where e.status='Verified' and e.year=2025 and lower(e.process_type) like '%flar%' and f.segment='Heavy Industry'").fetchone()[0]
print(f"segment=Heavy Industry, 2025: flaring-summary total={fs['total_flaring']['tco2e']} tCO2e, {fs['total_flaring']['volume_knm3']} kNm3; expected (SQL)={exp_seg}")
bad = f["year"] != "all" and abs(f["total_flaring"]["tco2e"] - exp_all) > 1 or abs(fs["total_flaring"]["tco2e"] - exp_seg) > 1
sys.exit(1 if bad else 0)
