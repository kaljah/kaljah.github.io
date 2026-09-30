import sys
sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/tools")
from auditlib import make_db, api_client, sql
DB="agentI_fac"; make_db(DB, overwrite=True)
s = api_client(DB,"superuser")
print("before", sql(DB,"select id,name,region from facilities where id=1"))
r = s.put("/api/facilities/1", json={"region":"South"}); print("superuser West moves fac 1 to South:", r.status_code, r.get_data(as_text=True)[:150])
print("after", sql(DB,"select id,region from facilities where id=1"))
print("superuser can still see fac 1:", 1 in [f["id"] for f in s.get("/api/facilities").get_json()])
r = s.put("/api/facilities/3", json={"region":"West"}); print("superuser pulls Center fac 3 into West:", r.status_code)
r = s.post("/api/facilities", json={"name":"ZZ_EAST","region":"East","latitude":1,"longitude":1}); print("superuser creates facility in East:", r.status_code)
