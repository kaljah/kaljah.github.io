"""Region-restricted superuser can move its facility (with its emissions) into another region via PUT /api/facilities/<id>."""
import sys
sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/tools")
from auditlib import make_db, api_client, sql
DB="repro_BUG093"; make_db(DB, overwrite=True)
s = api_client(DB,"superuser")
n = sql(DB,"select count(*) n from emissions where facility_id=1")[0]["n"]
r_create = s.post("/api/facilities", json={"name":"ZZ_SOUTH","region":"South","latitude":1,"longitude":1})
r = s.put("/api/facilities/1", json={"region":"South"})
after = sql(DB,"select region from facilities where id=1")[0]["region"]
print(f"create facility in South as West superuser: {r_create.status_code} (correctly denied)")
print(f"expected: PUT region West->South denied (403) like create; actual: {r.status_code}, facility 1 region now {after!r} with its {n} emission rows")
sys.exit(1 if after == "South" else 0)
