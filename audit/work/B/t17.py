import sys, json; sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/tools")
from auditlib import make_db, api_client, sql
import logging; logging.disable(logging.CRITICAL)
DB="agentB_recon"; make_db(DB, overwrite=True); c=api_client(DB,"admin")
for inc in ("false","true"):
    st="('Verified')" if inc=="false" else "('Verified','Pending')"
    j=c.get(f"/api/dashboard/summary?includePending={inc}").get_json()
    api1={r["year"]:r["scope1_total"] for r in j}; api2={r["year"]:r["scope2_total"] for r in j}
    db1={r["year"]:r["s"] for r in sql(DB,f"select year,sum(co2e_total) s from emissions where status in {st} group by year")}
    db2={r["year"]:r["s"] for r in sql(DB,f"select year,sum(co2e) s from scope2_emissions where status in {st} group by year")}
    for y in sorted(set(api1)|set(db1)|set(db2)):
        a1,d1,a2,d2=api1.get(y,0),db1.get(y,0) or 0,api2.get(y,0),db2.get(y,0) or 0
        flag = "" if abs(a1-d1)<=1e-6*max(1,abs(d1)) and abs(a2-d2)<=1e-6*max(1,abs(d2)) else "  <-- MISMATCH"
        print(inc,y,f"S1 api={a1:.4f} db={d1:.4f} S2 api={a2:.4f} db={d2:.4f}{flag}")
    # source split sum vs scope1
    for r in j:
        parts=r["combustion"]+r["flaring"]+r["venting"]+r["other"]
        if abs(parts-r["scope1_total"])>1e-6*max(1,r["scope1_total"]): print("split mismatch",r["year"],parts,r["scope1_total"])
s3=c.get("/api/dashboard/scope3/summary").get_json(); print("s3 api",s3, "db", sql(DB,"select year,sum(co2e) s from scope3_emissions where status='Verified' group by year"))
cb=c.get("/api/dashboard/categorical-breakdown").get_json()
print("categorical S1+S2", sum(x["total_emissions"] for x in cb), "S3", sum(x["scope3_emissions"] for x in cb))
print("db S1+S2 verified", sql(DB,"select (select sum(co2e_total) from emissions where status='Verified')+(select sum(co2e) from scope2_emissions where status='Verified') s"))
print("orphans", sql(DB,"select count(*) n, sum(co2e_total) s from emissions e where status='Verified' and not exists(select 1 from facilities f where f.id=e.facility_id)"))
