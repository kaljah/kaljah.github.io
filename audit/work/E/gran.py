import sys, json; sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/tools")
from auditlib import api_client
c = api_client("agentE", "admin")
for q in ["year=2025","year=2026","year=2025&facilityId=169","year=2025&facilityId=13","year=2026&facilityId=13"]:
    print(q, json.dumps(c.get("/api/dashboard/granular-intensities?"+q).get_json()))
for q in ["year=2025","year=2025&facilityId=169","year=2025&facilityId=13","year=2026&facilityId=13"]:
    st=c.get("/api/dashboard/intensity-stats?"+q).get_json()
    B=sum(x["total_boe"] for x in st if x["total_boe"]>0); E=sum(x["co2_intensity"]*x["total_boe"] for x in st if x["total_boe"]>0)
    print("stats", q, E/B if B else None, B)
