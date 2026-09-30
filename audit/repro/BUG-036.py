"""Flaring panel invents a 56/40/4 split for generic 'flaring' rows; stream tCO2e 0 while total > 0. Exits 1 while bug exists."""
import sys, sqlite3; sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/tools")
from auditlib import api_client, db_path
c = api_client("repro_F", "admin")
con = sqlite3.connect(db_path("repro_F"))
typed = con.execute("select count(*) from emissions where year=2026 and status='Verified' and process_type in ('routine_flaring','non_routine_flaring','safety_flaring')").fetchone()[0]
fd = con.execute("select count(*) from flaring_details where year=2026").fetchone()[0]
f = c.get("/api/dashboard/flaring-summary?year=2026").get_json()
streams = sum(f[k]["tco2e"] for k in ("routine_flaring","non_routine_flaring","safety_flaring"))
print(f"2026 typed-stream rows={typed}, FlaringDetail rows={fd} -> expected routine volume 0 / unclassified")
print(f"API routine={f['routine_flaring']['volume_knm3']} kNm3 ({f['routine_flaring']['percentage']}%), stream tCO2e sum={streams}, total tCO2e={f['total_flaring']['tco2e']}")
bad = (typed == 0 and fd == 0 and f["routine_flaring"]["volume_knm3"] > 0) or abs(streams - f["total_flaring"]["tco2e"]) > 0.01
sys.exit(1 if bad else 0)
