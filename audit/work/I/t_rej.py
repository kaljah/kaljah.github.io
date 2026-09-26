import sys, threading
sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/tools")
from auditlib import make_db, api_client, sql
DB="agentI_rej"; make_db(DB, overwrite=True)
s = api_client(DB,"superuser"); a = api_client(DB,"admin")
v = sql(DB,"select id,status,co2e_total from emissions where status='Verified' and facility_id in (1,2,158,160,168) order by co2e_total desc limit 1")[0]; print(v)
r = s.post(f"/api/emissions/reject/{v['id']}", json={"reason":"x"}); print("reject verified:", r.status_code, r.get_json(), sql(DB,"select status from emissions where id=?",(v['id'],)))
# reject already rejected / approve after reject
r = s.post(f"/api/emissions/reject/{v['id']}"); print("reject again", r.status_code)
# scope param weirdness
r = s.post(f"/api/emissions/approve/1?scope=abc"); print("scope=abc", r.status_code, r.get_json())
# batch approve with bad ids
for body in [{"ids":"1"}, {"ids":[{"a":1}]}, {"ids":[1],"scope":"9"}, {"by_scope":{"1":"5"}}, {"by_scope":[1]}]:
    try: r = a.post("/api/emissions/approve/batch", json=body); print(body, r.status_code, r.get_data(as_text=True)[:120])
    except Exception as e: print(body, "EXC", e)
# pending limit
for q in ["limit=abc","limit=-1","limit=0"]:
    r = a.get("/api/emissions/pending?"+q); print(q, r.status_code, (len(r.get_json().get("scope1",[])) if r.is_json and r.status_code==200 else r.get_data(as_text=True)[:80]))
