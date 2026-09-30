import sys, json; sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/tools")
from auditlib import api_client
c = api_client("agentH","admin")
for u in ["/api/dashboard/sbti-trajectory","/api/dashboard/sbti-trajectory?scope=s1_s2","/api/manage/sbti","/api/manage/sbti?base_year=2023","/api/dashboard/base-year"]:
    r=c.get(u); d=r.get_json(); print(u, r.status_code)
    if isinstance(d,dict) and 'trajectory' in d:
        t=d.pop('trajectory'); print(json.dumps(d)); [print('  ',x) for x in t]
    else: print(d)
