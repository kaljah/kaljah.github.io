import sys
sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/tools")
from auditlib import make_db, api_client, sql
DB="agentI_mc"; make_db(DB, overwrite=True)
u = api_client(DB,"user"); s = api_client(DB,"superuser")
v = sql(DB,"select id,year,facility_id,quantity,co2e_total,created_by,status from emissions where status='Verified' and facility_id in (1,2,158,160,168) limit 1")[0]; print(v)
r = s.put(f"/api/emissions/{v['id']}", json={"year":2019,"month":7}); print("su edit year:", r.status_code, sql(DB,"select year,month,status,approved_by from emissions where id=?",(v['id'],)))
r = s.put(f"/api/emissions/{v['id']}", json={"facility_id":2}); print("su edit facility:", r.status_code, sql(DB,"select facility_id,status from emissions where id=?",(v['id'],)))
# user creates record, superuser edits quantity, superuser approves own edit
r = u.post("/api/emissions/", json={"facility_id":1,"year":2025,"month":5,"process_type":"combustion","fuel_type":"Natural Gas","quantity":100,"unit":"MMBtu"}); eid=r.get_json().get("id"); print("user create", r.status_code, eid)
r = s.put(f"/api/emissions/{eid}", json={"quantity":999999}); print("su edit qty", r.status_code)
r = s.post(f"/api/emissions/approve/{eid}"); print("su approve own edit:", r.status_code, r.get_json())
print(sql(DB,"select id,quantity,co2e_total,status,created_by,approved_by from emissions where id=?",(eid,)))
# user updates Verified record they created? user deletes own verified record
x = sql(DB,"select id from emissions where id=?",(eid,))
r = u.delete(f"/api/emissions/{eid}"); print("user delete own VERIFIED record:", r.status_code, sql(DB,"select count(*) n from emissions where id=?",(eid,)))
