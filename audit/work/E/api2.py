import sys, json, urllib.parse; sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/tools")
from auditlib import api_client
import sqlite3
con=sqlite3.connect(r"C:/Users/samsung/Desktop/H2/audit/db/agentE.db")
c = api_client("agentE", "admin")
GAS=0.178
def conv_boe(oil,ou,gas,gu):
    ou=(ou or 'bbl').lower(); gu=(gu or 'mscf').lower()
    o = oil*6.28981077 if ou in ('m3','m³') else oil
    g = gas*1000 if gu=='mmscf' else (gas*0.0353147 if gu in ('m3','m³') else gas)
    return o + g*GAS
def expected(year, act=None, div=None):
    # facility-level (facility.activity) filter on BOTH, year-matched
    fwhere = "1=1"; params=[]
    if act: fwhere += " and f.activity=?"; params.append(act)
    if div: fwhere += " and f.division=?"; params.append(div)
    B=0; E=0
    rows = con.execute(f"select p.facility_id,p.oil_amount,p.oil_unit,p.gas_amount,p.gas_unit from production_data p join facilities f on f.id=p.facility_id where p.year=? and {fwhere}", [year]+params).fetchall()
    fids=set()
    bmap={}
    for fid,o,ou,g,gu in rows:
        bmap[fid]=bmap.get(fid,0)+conv_boe(o or 0,ou,g or 0,gu)
    for fid,b in bmap.items():
        if b<=0: continue
        e1=con.execute("select coalesce(sum(co2e_total),0) from emissions where status='Verified' and year=? and facility_id=?", (year,fid)).fetchone()[0]
        e2=con.execute("select coalesce(sum(co2e),0) from scope2_emissions where status='Verified' and year=? and facility_id=?", (year,fid)).fetchone()[0]
        E+=e1+e2; B+=b
    return (E*1000/B if B else None), B
for act in [None,'Upstream','Activité E&P','Production','Steel & Iron (Acier DRI)']:
    for y in [2025,2022]:
        qs = f"year={y}" + (f"&activity={urllib.parse.quote(act)}" if act else "")
        st = c.get(f"/api/dashboard/intensity-stats?{qs}").get_json()
        E=sum(x["co2_intensity"]*x["total_boe"] for x in st if x["total_boe"]>0); B=sum(x["total_boe"] for x in st if x["total_boe"]>0)
        ex, eb = expected(y, act)
        print(act, y, "API", round(E/B,3) if B else None, "B", round(B), "| expected", ex and round(ex,3), "B", round(eb), "| rows_no_boe_with_emissions", sum(1 for x in st if x['total_boe']==0 and x['total_co2e']>0))
