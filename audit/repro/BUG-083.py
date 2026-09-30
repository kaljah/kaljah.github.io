"""Write endpoints accept "NaN" / "1e999" (inf) for numeric activity fields; stored as NaN/inf and break reads."""
import sys, math
sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/tools")
from auditlib import make_db, api_client, sql
DB="repro_BUG083"; make_db(DB, overwrite=True)
a = api_client(DB,"admin")
before = a.get("/api/dashboard/summary?year=2025")
res = {
 "scope2 electricity_kwh=NaN": a.post("/api/scope2", json={"facility_id":1,"year":2025,"month":1,"electricity_kwh":"NaN","grid_region":"Algerian National Grid"}),
 "scope3 activity_data=1e999": a.post("/api/scope3", json={"facility_id":1,"year":2025,"month":1,"category":"Purchased Goods and Services","activity_data":"1e999","unit":"USD","emission_factor":0.5}),
 "production oil_amount=NaN": a.post("/api/data/production", json={"facility_id":1,"year":2025,"month":11,"oil_amount":"NaN","gas_amount":5}),
 "custom-factor co2_factor=NaN": a.post("/api/custom-factors", json={"name":"CF_NAN","co2_factor":"NaN","unit":"scf"}),
 "mitigation quantity_tco2e=1e999": a.post("/api/mitigation", json={"facility_id":1,"name":"M_INF","year":2025,"quantity_tco2e":"1e999"}),
}
for k, r in res.items(): print(f"{k}: HTTP {r.status_code}")
print("stored:", sql(DB,"select id,electricity_kwh,co2e from scope2_emissions order by id desc limit 1"),
      sql(DB,"select id,activity_data,co2e from scope3_emissions order by id desc limit 1"),
      sql(DB,"select id,oil_amount from production_data order by id desc limit 1"),
      sql(DB,"select id,co2_factor from custom_factors where name='CF_NAN'"))
after = a.get("/api/dashboard/batch-all?year=2025"); s2 = a.get("/api/dashboard/scope3/summary?year=2025"); cf = a.get("/api/scope3")
def js(r):
    t = r.get_data(as_text=True); return r.status_code, ("NaN" in t or "Infinity" in t)
print(f"batch-all {js(after)}; scope3/summary {js(s2)}; GET /api/scope3 {js(cf)}  (status, body contains NaN/Infinity -> invalid JSON)")
ok = sum(r.status_code in (200,201) for r in res.values())
print(f"expected: 400 for all 5 non-finite inputs; actual: {ok}/5 accepted")
sys.exit(1 if ok else 0)
