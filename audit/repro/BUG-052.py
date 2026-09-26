"""BUG-052: survey with +354% variance stored/returned as 'Reconciled'. Exits 1 while bug exists."""
import sys; sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/tools")
from auditlib import make_db, api_client, sql
DB = "agentD_r052"; make_db(DB, overwrite=True)
c = api_client(DB, "admin")
bu = sql(DB, "select sum(ch4_emissions) s from emissions where facility_id=169 and year=2025 and status='Verified'")[0]["s"]
r = c.post("/api/data/ogmp-surveys", json={"facility_id": 169, "year": 2025, "survey_date": "2025-06-01", "measured_rate_kg_hr": 400})
sid = r.get_json()["id"]
g = [s for s in c.get("/api/data/ogmp-surveys?facilityId=169").get_json() if s["id"] == sid][0]
var = (400 * 8760 / 1000 - bu) / bu * 100
print(f"expected variance {var:.2f}% -> status 'Discrepancy Flagged'; actual status {g['reconciliation_status']!r}, variance {g['variance_pct']}")
sys.exit(1 if g["reconciliation_status"] == "Reconciled" else 0)
