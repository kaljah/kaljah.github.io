"""Scope 2 manual + bulk entries by superuser are auto-Verified (Scope 1/3 require admin approval)."""
import sys
sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/tools")
from auditlib import make_db, api_client, sql
DB="repro_BUG060"; make_db(DB, overwrite=True)
s = api_client(DB,"superuser")
r2 = s.post("/api/scope2", json={"facility_id":1,"year":2025,"month":3,"source_type":"electricity","electricity_kwh":1000000,"grid_region":"Algerian National Grid","amount":1000000,"unit":"kWh"})
r3 = s.post("/api/scope3", json={"facility_id":1,"year":2025,"month":3,"category":"Purchased Goods and Services","activity_data":1000,"unit":"USD","emission_factor":0.5})
r1 = s.post("/api/emissions/", json={"facility_id":1,"year":2025,"month":3,"process_type":"combustion","fuel_type":"Natural Gas","quantity":1000,"unit":"MMBtu"})
rb = s.post("/api/scope2/bulk-import", json={"records":[{"facility_id":1,"year":2025,"month":4,"electricity_kwh":5000,"grid_region":"Algerian National Grid"}]})
print("scope2", r2.status_code, r2.get_data(as_text=True)[:200]); print("scope3", r3.status_code, r3.get_data(as_text=True)[:150]); print("scope1", r1.status_code, r1.get_data(as_text=True)[:150]); print("s2 bulk", rb.status_code, rb.get_data(as_text=True)[:200])
su = sql(DB,"select id from users where email='audit_superuser@audit.local'")[0]["id"]
st2 = sql(DB,"select id,status,approved_by from scope2_emissions where created_by=?",(su,))
st3 = sql(DB,"select id,status from scope3_emissions where created_by=?",(su,))
st1 = sql(DB,"select id,status from emissions where created_by=?",(su,))
print("expected: superuser entries Pending in every scope (maker-checker; Scope 1/3 code: 'only admin role auto-verifies')")
print("actual: scope1", st1, "scope3", st3, "scope2", st2)
sys.exit(1 if any(r["status"]=="Verified" for r in st2) else 0)
