import sys; sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/tools")
from auditlib import db_path
import sqlite3
con=sqlite3.connect(db_path("agentE"))
def boe(o,ou,g,gu):
    o = o*6.28981077 if (ou or 'bbl').lower() in ('m3','m³') else o
    gu=(gu or 'mscf').lower(); g = g*1000 if gu=='mmscf' else (g*0.0353147 if gu in ('m3','m³') else g)
    return o + g*0.178
bm={}
for fid,y,o,ou,g,gu in con.execute("select facility_id,year,oil_amount,oil_unit,gas_amount,gas_unit from production_data"):
    bm[(fid,y)]=bm.get((fid,y),0)+boe(o or 0,ou,g or 0,gu)
def E(fid,y):
    return con.execute("select coalesce(sum(co2e_total),0) from emissions where status='Verified' and year=? and facility_id=?", (y,fid)).fetchone()[0] + con.execute("select coalesce(sum(co2e),0) from scope2_emissions where status='Verified' and year=? and facility_id=?", (y,fid)).fetchone()[0]
for fid in (2,4,9,10):
    ee=sum(E(fid,y) for (f,y) in bm if f==fid and bm[(f,y)]>0); bb=sum(b for (f,y),b in bm.items() if f==fid and b>0)
    print(fid, "year-matched all-years kg/BOE", ee*1000/bb)
ee=sum(E(f,y) for (f,y),b in bm.items() if b>0); bb=sum(b for b in bm.values() if b>0)
print("corporate year-matched", ee*1000/bb, bb)
