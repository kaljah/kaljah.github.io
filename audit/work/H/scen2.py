import sys, json; sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/tools")
from auditlib import api_client, sql
DB="agentH_scen"  # reuse state from scen.py
print(sql(DB,"select id,region from facilities where region='West'")[:10])
for role in ["user","superuser"]:
    c=api_client(DB,role)
    d=c.get("/api/dashboard/sbti-trajectory").get_json(); d.pop("trajectory",None); print(role,{k:d.get(k) for k in ["latest_actual_year","current_actual","reduction_achieved_pct","on_track","base_year_emissions"]})
    print(role,"manage GET 2020",c.get("/api/manage/sbti?base_year=2020").get_json())
    print(role,"manage GET 2023",c.get("/api/manage/sbti?base_year=2023").get_json()["suggested_base_year_emissions"])
    print(role,"goals",c.get("/api/goals").status_code)
a=api_client(DB,"admin")
for body in ['{"base_year":2020,"base_year_emissions":NaN,"target_year":2030,"reduction_rate_pct":4.2}',
             '{"base_year":2020,"base_year_emissions":Infinity,"target_year":2030,"reduction_rate_pct":4.2}',
             '{"base_year":2020,"base_year_emissions":1000,"target_year":2030,"reduction_rate_pct":NaN}',
             '{"base_year":2020,"base_year_emissions":1000,"target_year":2030,"reduction_rate_pct":0.5,"pathway_type":"1.5C"}',
             '{"base_year":2020,"base_year_emissions":1000,"target_year":2030,"reduction_rate_pct":4.2,"pathway_type":"<b>x</b>"}',
             '{"base_year":2020.9,"base_year_emissions":1000,"target_year":2020.5,"reduction_rate_pct":4.2}',
             '{"base_year":"2020","base_year_emissions":"1e3","target_year":null,"reduction_rate_pct":null}']:
    r=a.post("/api/manage/sbti",data=body,content_type="application/json"); print(body[:90], r.status_code, r.get_json())
print(sql(DB,"select * from sbti_targets"))
r=a.get("/api/dashboard/sbti-trajectory"); print(r.status_code, r.get_data(as_text=True)[:400])
for g in [{"year":1,"target_amount":-5},{"year":2025,"target_amount":float('nan')}]:
    r=a.post("/api/goals",data=json.dumps(g),content_type="application/json"); print(g,r.status_code,r.get_json())
