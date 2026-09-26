import sys; sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/tools")
from auditlib import api_client
c = api_client("ui_k_scratch", "admin")
j = c.get("/api/emissions/pending?all=true").get_json()
s1 = j.get("scope1", [])
print(len(s1), {k: s1[0].get(k) for k in ["id","process_type","fuel_type","fuel","quantity","amount","unit","co2e_total"]})
print(sum(1 for r in s1 if r.get("quantity") in (None,0) and r.get("amount")), "scope1 rows with amount but no quantity")
s2 = j.get("scope2", []); print([ (r.get("source_type"), r.get("electricity_kwh"), r.get("heat_mmbtu")) for r in s2 if r.get("source_type")!="electricity"][:5])
