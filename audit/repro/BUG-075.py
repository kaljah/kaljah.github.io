"""BUG-075: S5P export stores 1-hour mass as annual tCH4. Exits 1 while bug exists."""
import sys; sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/tools")
from auditlib import make_db, api_client, sql
DB = "agentD_r075"; make_db(DB, overwrite=True)
c = api_client(DB, "admin")
r = c.post("/api/satellite/sentinel5p/export-to-ogmp", json={"facility_id": 169, "observation_date": "2025-07-01",
     "ch4_column_ppb": 1900, "anomaly_ppb": 10, "estimated_emission_rate_kg_hr": 100.0, "qa_score": 0.8, "notes": "audit"})
s = sql(DB, "select estimated_annual_tch4, reconciliation_status from ogmp_surveys order by id desc limit 1")[0]
exp = 100.0 * 8760 / 1000
print(f"expected annual tCH4 {exp} (rate x 8760 h, as manual surveys); actual {s['estimated_annual_tch4']} ({s['reconciliation_status']})")
sys.exit(1 if abs(s["estimated_annual_tch4"] - exp) > 0.01 else 0)
