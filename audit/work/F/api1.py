import sys, json; sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/tools")
from auditlib import api_client, sql
c = api_client("dashboard", "admin")
def get(u):
    r=c.get(u); return r.get_json()
b=get("/api/dashboard/batch-all?facilityId=all&activity=all&division=all")
json.dump(b, open("batch_all.json","w"), indent=1)
S=b["summary"]
s1=sum(r["scope1_total"] for r in S); s2=sum(r["scope2_total"] for r in S)
src={k:sum(r[k] for r in S) for k in ("combustion","flaring","venting","other")}
print("scope1",s1,"scope2",s2,"total",s1+s2,"ch4",sum(r["ch4_total"] for r in S))
print("src",src,"sum",sum(src.values()))
cat=b["categorical_breakdown"]; print("cat sum", sum(x["total_emissions"] for x in cat), "cat s3", sum(x["scope3_emissions"] for x in cat))
print("scope3",b["scope3_summary"]); print("mit", sum(m.get("quantity_tco2e",0) or 0 for m in b["mitigation"]), len(b["mitigation"]))
print("pending",b["pending_stats"]); print("years",b["years"])
f=get("/api/dashboard/flaring-summary?facilityId=all&activity=all&division=all"); print(json.dumps(f,indent=1))
