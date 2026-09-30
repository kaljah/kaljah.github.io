import sys, time
sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/tools")
from auditlib import make_db, api_client
DB="agentI_perf"; make_db(DB, overwrite=True)
a = api_client(DB,"admin")
for p in ["/api/emissions/","/api/emissions/?per_page=100000","/api/emissions/?limit=-1","/api/emissions/export","/api/data/production","/api/dashboard/batch-all","/api/dashboard/batch-all?year=2025","/api/dashboard/intensity-trend","/api/dashboard/uncertainty","/api/qaqc/dashboard","/api/emissions/pending?all=true","/api/audit/?limit=100000","/api/facilities","/api/cap/compliance","/api/equity/allocation","/api/manage/sbti","/api/filters/available"]:
    t=time.time(); r=a.get(p); dt=time.time()-t
    t=time.time(); a.get(p); dt2=time.time()-t
    print(f"{p:45s} {r.status_code} {len(r.data):>9} B  cold {dt:6.2f}s warm {dt2:6.2f}s")
