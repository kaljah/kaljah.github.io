import sys; sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/tools")
from auditlib import api_client, sql
c = api_client("agentD", "admin")
for Y in ("2025","2026"):
    st = c.get(f"/api/dashboard/intensity-stats?year={Y}").get_json()
    bad=[(x["facility_id"],x["segment"],round(x["total_ch4"],3),x["total_gas_m3"],x["methane_loss_rate_pct"],x["ogmp_target_status"]) for x in st if x["total_ch4"]>0 and x["total_gas_m3"]==0]
    print(Y, len(bad), bad[:6])
    tr = c.get(f"/api/dashboard/intensity-trend").get_json()
