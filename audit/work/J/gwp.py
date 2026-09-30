import sys; sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/tools")
from auditlib import make_db, api_client, sql
make_db("agentJ", overwrite=True)
a=api_client("agentJ","admin")
def tot():
    return {t: sql("agentJ", f"select round(sum({c}),3) s from {t} where status='Verified'")[0]["s"] for t,c in [("emissions","co2e_total"),("scope2_emissions","co2e"),("scope3_emissions","co2e")]}
b=tot(); logs0=sql("agentJ","select count(*) n from activity_log")[0]["n"]
hb0=sql("agentJ","select id,co2e_total,gwp_version,status,approved_by from emissions where id in (682,686)")
print("settings before", a.get("/api/auth/settings").get_json().get("gwp_standard"))
r=a.put("/api/auth/settings", json={"gwp_standard":"AR6"}); print(r.status_code, r.get_json())
print("before",b); print("after ",tot())
print("activity log added:", sql("agentJ","select count(*) n from activity_log")[0]["n"]-logs0, sql("agentJ","select action,entity,details from activity_log order by id desc limit 2"))
print(hb0); print(sql("agentJ","select id,co2e_total,gwp_version,status,approved_by,co2_emissions,ch4_emissions,n2o_emissions from emissions where id in (682,686)"))
print("status dist", sql("agentJ","select status, gwp_version, count(*) n from emissions group by 1,2"))
# switch back
r=a.put("/api/auth/settings", json={"gwp_standard":"AR5"}); print("back", r.status_code, tot())
print(sql("agentJ","select id,co2e_total from emissions where id in (682,686)"))
