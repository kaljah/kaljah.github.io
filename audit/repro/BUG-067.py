"""Maker-checker bypass via edit/delete on Scope 1 records."""
import sys
sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/tools")
from auditlib import make_db, api_client, sql
DB="repro_BUG067"; make_db(DB, overwrite=True)
u = api_client(DB,"user"); s = api_client(DB,"superuser")
bad = []
# 1. superuser moves a Verified record to another year: stays Verified, no review
v = sql(DB,"select id,year from emissions where status='Verified' and facility_id in (1,2,158,160,168) limit 1")[0]
s.put(f"/api/emissions/{v['id']}", json={"year":2019})
after = sql(DB,"select year,status from emissions where id=?",(v['id'],))[0]
print(f"1) superuser changes year {v['year']}->2019 on Verified #{v['id']}: expected Pending, actual {after}")
if after["status"]=="Verified": bad.append(1)
# 2. user creates, superuser edits quantity (becomes the maker of the new value), then approves own edit
eid = u.post("/api/emissions/", json={"facility_id":1,"year":2025,"month":5,"process_type":"combustion","fuel_type":"Natural Gas","quantity":100,"unit":"MMBtu"}).get_json()["id"]
s.put(f"/api/emissions/{eid}", json={"quantity":999999})
r = s.post(f"/api/emissions/approve/{eid}")
print(f"2) superuser edits qty then approves own edit: expected 403, actual {r.status_code} {sql(DB,'select quantity,status,approved_by from emissions where id=?',(eid,))}")
if r.status_code==200: bad.append(2)
# 3. user deletes own Verified record
r = u.delete(f"/api/emissions/{eid}")
print(f"3) user deletes own Verified record #{eid}: expected 403 / deletion request pending review, actual {r.status_code}, rows left={sql(DB,'select count(*) n from emissions where id=?',(eid,))[0]['n']}")
if r.status_code==200: bad.append(3)
sys.exit(1 if bad else 0)
