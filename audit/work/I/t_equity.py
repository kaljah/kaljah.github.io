import sys
sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/tools")
from auditlib import make_db, api_client, sql
DB="agentI_eq"; make_db(DB, overwrite=True)
a = api_client(DB,"admin")
# time slice: Sonatrach 51% ended 2023-12-31, new 70% from 2024-01-01
sql(DB,"update facility_equity_shares set effective_end_date='2023-12-31' where id=1")
r=a.post("/api/equity/shares", json={"facility_id":169,"partner_id":1,"equity_share_pct":70,"effective_start_date":"2024-01-01"}); print(r.status_code, r.get_json())
yrs = sql(DB,"select year, sum(co2e_total) s from emissions where facility_id=169 and status='Verified' group by year")
print(yrs)
for y in [r['year'] for r in yrs][:3]:
    al = a.get(f"/api/equity/allocation?year={y}&facility_id=169").get_json()
    for f in al:
        tot=sum(p['equity_pct'] for p in f['partners']); son=[p for p in f['partners'] if p['partner_code']=='SH'][0]
        print(y, "total", f['total_co2e'], "sum pct", tot, "Sonatrach pct", son['equity_pct'], "alloc", son['allocated_co2e'])
for v in [500, -50, "nan", "inf", "abc"]:
    try:
        r=a.post("/api/equity/shares", json={"facility_id":169,"partner_id":2,"equity_share_pct":v,"effective_start_date":f"2030-{abs(hash(str(v)))%12+1:02d}-01"}); print(v, r.status_code, r.get_data(as_text=True)[:150])
    except Exception as e: print(v, "EXC", e)
u = api_client(DB,"user")
print("user post equity on own facility 1:", u.post("/api/equity/shares", json={"facility_id":1,"partner_id":2,"equity_share_pct":99}).status_code)
print("user post equity on 169:", u.post("/api/equity/shares", json={"facility_id":169,"partner_id":2,"equity_share_pct":99}).status_code)
