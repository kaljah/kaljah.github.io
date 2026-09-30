import sys, urllib.parse, sqlite3; sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/tools")
from auditlib import api_client, db_path
c = api_client("agentE_r1", "admin")
con = sqlite3.connect(db_path("agentE_r1"))
def boe(o,ou,g,gu):
    o = o*6.28981077 if (ou or 'bbl').lower() in ('m3','m³') else o
    gu=(gu or 'mscf').lower(); g = g*1000 if gu=='mmscf' else (g*0.0353147 if gu in ('m3','m³') else g)
    return o + g*0.178
def expected(y, act):
    bm={}
    for fid,o,ou,g,gu in con.execute("select p.facility_id,p.oil_amount,p.oil_unit,p.gas_amount,p.gas_unit from production_data p join facilities f on f.id=p.facility_id where p.year=? and f.activity=?", (y,act)):
        bm[fid]=bm.get(fid,0)+boe(o or 0,ou,g or 0,gu)
    E=B=0
    for fid,b in bm.items():
        if b<=0: continue
        E+=con.execute("select coalesce(sum(co2e_total),0) from emissions where status='Verified' and year=? and facility_id=?", (y,fid)).fetchone()[0]
        E+=con.execute("select coalesce(sum(co2e),0) from scope2_emissions where status='Verified' and year=? and facility_id=?", (y,fid)).fetchone()[0]
        B+=b
    return E*1000/B if B else None
bad=0
for act,y in [("Upstream",2025),("Activité E&P",2025),("Steel & Iron (Acier DRI)",2022)]:
    st=c.get(f"/api/dashboard/intensity-stats?year={y}&activity={urllib.parse.quote(act)}").get_json()
    B=sum(x["total_boe"] for x in st if x["total_boe"]>0); E=sum(x["co2_intensity"]*x["total_boe"] for x in st if x["total_boe"]>0)
    act_v = E/B if B else None; exp=expected(y,act)
    ok = act_v is not None and abs(act_v-exp)/exp < 1e-3
    print(f"{act} {y}: expected {exp:.3f} kg/BOE, actual {act_v}", "OK" if ok else "MISMATCH")
    bad |= not ok
sys.exit(1 if bad else 0)
