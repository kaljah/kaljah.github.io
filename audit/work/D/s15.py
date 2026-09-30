import sys; sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/tools")
from auditlib import api_client
c = api_client("agentD", "admin")
Y = 2025
def kpi(data):   # MethaneIntensity.jsx loadStats (lines ~210-249), exact segment match
    up=[0,0]; mid=[0,0]; tot=[0,0]
    for d in data:
        g = d.get("total_gas_m3") or (d.get("total_gas") or 0)*28.3168; ch4=d.get("total_ch4") or 0
        seg=(d.get("segment") or "").strip().lower(); tot[0]+=g; tot[1]+=ch4
        if seg=="midstream": mid[0]+=g; mid[1]+=ch4
        elif seg=="upstream": up[0]+=g; up[1]+=ch4
    r=lambda a: (a[1]*1000/0.6785)/a[0]*100 if a[0] else 0
    return r(tot), r(up), r(mid), up[0], mid[0]
def trend(data):  # trendChartData (lines ~606-662), substring match
    up=[0,0]; mid=[0,0]; tot=[0,0]
    for d in data:
        g = d.get("total_gas_m3") or (d.get("total_gas") or 0)*28.3168; v=(d.get("total_ch4") or 0)*1000/0.6785
        seg=(d.get("segment") or "").strip().lower(); tot[0]+=g; tot[1]+=v
        if seg=="midstream" or any(s in seg for s in ("midstream","processing","lng","lsh","gnl","gpl")): mid[0]+=g; mid[1]+=v
        elif seg=="upstream" or any(s in seg for s in ("upstream","production","exploration")): up[0]+=g; up[1]+=v
    r=lambda a: a[1]/a[0]*100 if a[0] else 0
    return r(tot), r(up), r(mid), up[0], mid[0]
st = c.get(f"/api/dashboard/intensity-stats?year={Y}&facilityId=all&activity=all&division=all").get_json()
tr = [x for x in c.get("/api/dashboard/intensity-trend?years=2021,2022,2023,2024,2025,2026").get_json() if x["year"]==str(Y)][0]["data"]
print("KPI   (overall, upstream, midstream, upGas, midGas):", kpi(st))
print("TREND (overall, upstream, midstream, upGas, midGas):", trend(tr))
