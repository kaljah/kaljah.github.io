import sys, json; sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/tools")
from auditlib import api_client, sql
c = api_client("agentG", "admin")
q="select id,co2e_total,uncertainty,uncertainty_ch4,uncertainty_n2o,status from emissions where id=?"
print(sql("agentG",q,(765,)))
r = c.put("/api/emissions/765", json={"recalculate": True}); print(r.status_code, r.get_json())
print(sql("agentG",q,(765,)))
r = c.put("/api/emissions/766", json={"recalculate": True, "user_uncertainty":{"co2":50}}); print(r.status_code)
print(sql("agentG",q,(766,)))
