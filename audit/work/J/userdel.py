import sys; sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/tools")
from auditlib import make_db, api_client, sql
make_db("agentJ", overwrite=True)
it=api_client("agentJ","it_admin")
for uid in (1,2,9):
    refs={t:sql("agentJ",f"select count(*) n from {t} where created_by=?",(uid,))[0]["n"] for t in ["production_data","sbti_targets","level_upgrade_logs","cap_emissions","emissions"]}
    r=it.delete(f"/api/auth/users/{uid}")
    print(uid, refs, r.status_code, str(r.get_json())[:300])
    print("  still exists:", sql("agentJ","select count(*) n from users where id=?",(uid,)))
