import sys, json; sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/tools")
from auditlib import api_client, sql
from urllib.parse import urlencode
c = api_client("dashboard", "admin")
def batch(**kw):
    p={"facilityId":"all","activity":"all","division":"all"}; p.update(kw)
    b=c.get("/api/dashboard/batch-all?"+urlencode(p)).get_json()
    S=b["summary"]; yr=kw.get("year")
    rows=[r for r in S if yr in (None,"all") or str(r["year"])==str(yr)]
    s1=sum(r["scope1_total"] for r in rows); s2=sum(r["scope2_total"] for r in rows)
    src=sum(r[k] for r in rows for k in ("combustion","flaring","venting","other"))
    cat=sum(x["total_emissions"] for x in b["categorical_breakdown"])
    return dict(s1=round(s1,2),s2=round(s2,2),kpi=round(s1+s2,2),src_sum=round(src,2),cat=round(cat,2),s3=b["scope3_summary"]["total"],ch4=round(sum(r["ch4_total"] for r in rows),2),pend=b["pending_stats"])
def sq(s,p=()): return sql("dashboard",s,p)
tests=[{},{"activity":"Steel & Iron (Acier DRI)"},{"activity":"Activité E&P"},{"activity":"Production"},{"division":"Metallurgy"},{"division":"DP"},{"segment":"Heavy Industry"},{"segment":"Upstream"},{"year":"2025"},{"year":"2024"},{"facilityId":"1"},{"includePending":"true"},{"gwp_horizon":"20"},{"year":"2025","gwp_horizon":"20"}]
out={}
for t in tests:
    r=batch(**t); out[json.dumps(t,ensure_ascii=False)]=r; print(json.dumps(t,ensure_ascii=False), r)
json.dump(out,open("filter_matrix.json","w"),indent=1,ensure_ascii=False)
