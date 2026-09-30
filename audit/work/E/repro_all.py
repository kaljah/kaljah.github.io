import sys, sqlite3; sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/tools")
from auditlib import api_client, db_path
c = api_client("agentE_r2", "admin"); con = sqlite3.connect(db_path("agentE_r2"))
def boe(o,ou,g,gu):
    o = o*6.28981077 if (ou or 'bbl').lower() in ('m3','m³') else o
    gu=(gu or 'mscf').lower(); g = g*1000 if gu=='mmscf' else (g*0.0353147 if gu in ('m3','m³') else g)
    return o + g*0.178
def E(fid,y):
    return (con.execute("select coalesce(sum(co2e_total),0) from emissions where status='Verified' and year=? and facility_id=?", (y,fid)).fetchone()[0]
          + con.execute("select coalesce(sum(co2e),0) from scope2_emissions where status='Verified' and year=? and facility_id=?", (y,fid)).fetchone()[0])
st = {x['facility_id']: x for x in c.get("/api/dashboard/intensity-stats").get_json()}
bad = 0
for fid in (2, 9):
    bm = {}
    for y,o,ou,g,gu in con.execute("select year,oil_amount,oil_unit,gas_amount,gas_unit from production_data where facility_id=?", (fid,)):
        bm[y] = bm.get(y,0) + boe(o or 0,ou,g or 0,gu)
    exp = sum(E(fid,y) for y,b in bm.items() if b>0)*1000/sum(b for b in bm.values() if b>0)
    act = st[fid]['co2_intensity']
    ok = abs(act-exp) <= 1e-6*max(1,exp)
    print(f"facility {fid} year=all: expected (year-matched) {exp:.4f} kg/BOE, actual {act:.4f}", "OK" if ok else "MISMATCH")
    bad |= not ok
sys.exit(1 if bad else 0)
