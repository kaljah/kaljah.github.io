import sys, json; sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/tools")
from auditlib import api_client
c = api_client("dashboard", "admin")
for flt in ({"scope":"all"},{"scope":"all","year":"2025"}):
    r = c.post("/api/reports/generate", json={"filters": flt})
    print(flt, r.status_code, r.content_type, len(r.data))
    try:
        j=r.get_json(); 
        if j: print(list(j.keys())[:10], {k:v for k,v in j.items() if not isinstance(v,list)} )
    except Exception as e: print(e)
r=c.get("/api/reports/export?format=csv&scope=all"); print("export", r.status_code, r.content_type, len(r.data)); open("export_all.bin","wb").write(r.data)
