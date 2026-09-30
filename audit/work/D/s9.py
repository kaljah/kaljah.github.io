import sys; sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/tools")
from auditlib import api_client, sql
c = api_client("agentD", "admin")
for Y in ("2023","2025","2026","all"):
    st = c.get(f"/api/dashboard/intensity-stats?year={Y}&facilityId=all&activity=all&division=all").get_json()
    gas = sum(x["total_gas_m3"] or 0 for x in st)
    ch4_all = sum(x["total_ch4"] for x in st)
    ch4_gasfac = sum(x["total_ch4"] for x in st if (x["total_gas_m3"] or 0)>0)
    nogas = [(x["facility_id"], x["segment"], x["activity"], round(x["total_ch4"],2)) for x in st if (x["total_gas_m3"] or 0)==0 and x["total_ch4"]>0]
    ui = ch4_all*1000/0.6785/gas*100 if gas else None
    ok = ch4_gasfac*1000/0.6785/gas*100 if gas else None
    print(Y, "gas m3", round(gas), "UI loss%", ui, "matched loss%", ok, "nogas CH4 facs", len(nogas), nogas[:4])
