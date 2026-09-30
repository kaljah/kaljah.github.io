import sys, io, time
sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/tools")
from auditlib import make_db, api_client, sql
make_db("agentI")
def wait(c, jid):
    for _ in range(100):
        s = c.get(f"/api/emissions/upload/status/{jid}").get_json()
        if s.get("status") != "processing": return s
        time.sleep(0.2)
    return s
print(sql("agentI","select id,name,region,location from facilities where region not like 'West' limit 3"))
for role in ["user","it_admin"]:
    c = api_client("agentI", role)
    victim = sql("agentI","select id,name,region from facilities where lower(region)!='west' order by id limit 1")[0]
    csvdata = f"name,location,region,description\n{victim['name']},HACKED_{role},{victim['region']},pwned\nNEWFAC_{role},X,East,created by {role}\n"
    r = c.post("/api/emissions/upload/start", data={"file": (io.BytesIO(csvdata.encode()), "f.csv"), "scope":"facilities", "overwrite_duplicates":"true"}, content_type="multipart/form-data")
    print(role, r.status_code, r.get_json())
    s = wait(c, r.get_json()["job_id"]); print({k:s.get(k) for k in ("status","processed","errors","skipped_count")})
    print(sql("agentI","select id,name,location,region,created_by from facilities where id=? or name=?", (victim['id'], f"NEWFAC_{role}")))
    cf = f"name,co2_factor,ch4_factor,unit\nEVIL_{role},999,1,scf\n"
    r = c.post("/api/emissions/upload/start", data={"file": (io.BytesIO(cf.encode()), "f.csv"), "scope":"custom_factors"}, content_type="multipart/form-data")
    s = wait(c, r.get_json()["job_id"]); print(role, "cf", s.get("status"), s.get("processed"))
    print(sql("agentI","select id,name,co2_factor,created_by from custom_factors where name=?", (f"EVIL_{role}",)))
    # compare direct route
    print(role, "direct POST custom-factors:", c.post("/api/custom-factors", json={"name":"x","co2_factor":1}).status_code,
          "direct facilities import:", c.post("/api/facilities/import", json={"facilities":[{"name":"z"}]}).status_code)
