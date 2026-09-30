import sys; sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/tools")
from auditlib import make_db, api_client, sql
make_db("agentJ_BUG009", overwrite=True)
a = api_client("agentJ_BUG009", "admin")
n = sql("agentJ_BUG009", "select count(*) n from level_upgrade_logs where facility_id=1")[0]["n"]
r = a.delete("/api/facilities/1")
print("level logs on facility 1:", n)
print("expected: 200 (cascade) or clean 409; actual:", r.status_code, r.get_json())
sys.exit(1 if r.status_code == 500 else 0)
