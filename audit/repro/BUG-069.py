import sys; sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/tools")
from auditlib import make_db, api_client, sql
DB = "agentJ_BUG069"
make_db(DB, overwrite=True)
it = api_client(DB, "it_admin")
q = "select count(*) n from emissions where status='Verified' and approved_by is null"
before_orphans = sql(DB, q)[0]["n"]
approved_by_8 = sql(DB, "select count(*) n from emissions where approved_by=8")[0]["n"]
r = it.delete("/api/auth/users/8")
after_orphans = sql(DB, q)[0]["n"]
print("user 8 approved", approved_by_8, "Verified records; DELETE ->", r.status_code)
print("Verified records with no approver: before", before_orphans, "after", after_orphans)
print("expected: approval evidence preserved (approver id/name retained or delete blocked); actual:", after_orphans - before_orphans, "records lost their approver")
sys.exit(1 if after_orphans > before_orphans else 0)
