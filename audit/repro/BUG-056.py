"""Agent C repro: a custom factor used by Tier 2 records (UI path) can be deleted; referential check matches only fuel_type == factor name."""
import sys, json
sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/tools")
from auditlib import make_db, api_client, sql
DB = "agentC_bug056"
make_db(DB, overwrite=True)
c = api_client(DB, "admin")
cf = c.post("/api/custom-factors/", json=dict(name="Site flare gas EF", co2_factor=2.0, ch4_factor=0.01, n2o_factor=0, unit="kg/m3")).get_json()["id"]
r = c.post("/api/emissions/", json={"year": 2025, "month": 3, "facility_id": 1, "process_type": "combustion",
                                    "factor_source": "custom", "fuel": str(cf), "fuel_type": str(cf),
                                    "amount": 1000, "quantity": 1000, "unit": "m3", "custom_factor_id": cf})
rid = sql(DB, "select max(id) i from emissions")[0]["i"]
row = sql(DB, "select fuel_type, factor_source, co2e_total, source_payload from emissions where id=?", (rid,))[0]
print("record", rid, "fuel_type=", row["fuel_type"], "factor_source=", row["factor_source"], "co2e=", row["co2e_total"],
      "custom_factor_id in payload=", json.loads(row["source_payload"]).get("custom_factor_id"))
d = c.delete(f"/api/custom-factors/{cf}")
print("DELETE /api/custom-factors/%s ->" % cf, d.status_code, d.get_json())
left = sql(DB, "select count(*) n from custom_factors where id=?", (cf,))[0]["n"]
print("EXPECTED: 409 (factor referenced by record %s)  ACTUAL: %s, factor rows left=%s" % (rid, d.status_code, left))
# SQLite reuses the max rowid: a new factor can take the deleted factor's id, so the record's
# fuel_type / custom_factor_id now point to an unrelated factor.
new_id = c.post("/api/custom-factors/", json=dict(name="Unrelated diesel EF", co2_factor=2.7, unit="kg/liter")).get_json()["id"]
print("next custom factor created gets id", new_id, "(same as deleted id)" if new_id == cf else "")
sys.exit(1 if d.status_code == 200 else 0)
