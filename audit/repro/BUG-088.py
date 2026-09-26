"""BUG-088: CH4>0 with zero gas production reported as 0% loss / Compliant. Exits 1 while bug exists."""
import sys; sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/tools")
from auditlib import make_db, api_client
DB = "agentD_r088"; make_db(DB, overwrite=True)
c = api_client(DB, "admin")
st = c.get("/api/dashboard/intensity-stats?year=2025").get_json()
bad = [(x["facility_id"], x["total_ch4"], x["methane_loss_rate_pct"], x["ogmp_target_status"]) for x in st
       if x["total_ch4"] > 0 and (x["total_gas_m3"] or 0) == 0 and x["ogmp_target_status"] == "Compliant"]
print("expected: no 'Compliant' status without a gas denominator; actual:", bad)
sys.exit(1 if bad else 0)
