import sys; sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/tools")
from auditlib import api_client, sql
c = api_client("agentD", "admin")
Y=2025
q="/api/dashboard/batch-all?facilityId=all&activity=all&division=all&year=%d"%Y
p100=c.get(q).get_json()["pending_stats"]; p20=c.get(q+"&gwp_horizon=20").get_json()["pending_stats"]
s1 = sql("agentD","select sum(co2_emissions) co2, sum(ch4_emissions) ch4, sum(n2o_emissions) n2o, sum(co2e_total) e from emissions where status='Pending' and year=?",(Y,))[0]
s2 = sql("agentD","select coalesce(sum(co2e),0) e from scope2_emissions where status='Pending' and year=?",(Y,))[0]
print("banner GWP-100:", p100, " banner GWP-20:", p20)
print("DB pending S1 GWP100 + S2:", s1["e"]+s2["e"])
print("expected GWP-20 pending (S1 co2+ch4*82.5+n2o*268 + S2):", s1["co2"]+s1["ch4"]*82.5+s1["n2o"]*268+s2["e"], " pending CH4 t:", s1["ch4"])
