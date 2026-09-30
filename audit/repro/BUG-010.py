import sys; sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/tools")
from auditlib import make_db, api_client, sql
make_db("agentJ_BUG010", overwrite=True)
it = api_client("agentJ_BUG010", "it_admin")
refs = {t: sql("agentJ_BUG010", f"select count(*) n from {t} where created_by=1")[0]["n"] for t in ["production_data", "sbti_targets", "level_upgrade_logs"]}
r = it.delete("/api/auth/users/1")
left = sql("agentJ_BUG010", "select count(*) n from users where id=1")[0]["n"]
print("refs by user 1:", refs)
print("expected: 200 and user removed; actual:", r.status_code, r.get_json(), "user rows left:", left)
sys.exit(1 if r.status_code == 500 else 0)
