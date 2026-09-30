"""Decree 21-330 flaring intensity: unit normalisation errors in /api/dashboard/flaring-summary."""
import sys; sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/tools")
from auditlib import api_client, make_db
name = "agentE_r3"; make_db(name, overwrite=True)
c = api_client(name, "admin")
fs = lambda: c.get("/api/dashboard/flaring-summary?year=2026&facilityId=13").get_json()
bad = 0
for unit, amt in [("mmscf", 1), ("scf", 1_000_000), ("kscf", 1000)]:   # each = 28,316.8 m3
    v0 = fs()["total_flaring"]["volume_m3"]
    r = c.post("/api/emissions/", json={"process_type": "flaring", "source_type": "Flaring", "facility_id": 13,
               "year": 2026, "month": 3, "amount": amt, "unit": unit, "c1": 90, "fuel": "Natural Gas"})
    assert r.status_code == 201, r.get_json()
    d = fs()["total_flaring"]["volume_m3"] - v0
    ok = abs(d - 28316.8) < 1
    print(f"flared {amt} {unit}: expected +28316.8 m3, actual +{d:.2f} m3", "OK" if ok else "MISMATCH"); bad |= not ok
g0 = fs()["gas_production_m3"]
r = c.post("/api/data/production", json={"facility_id": 13, "year": 2026, "month": 7, "oil_amount": 0,
           "gas_amount": 1_000_000, "oil_unit": "bbl", "gas_unit": "m³"})
assert r.status_code in (200, 201), r.get_json()
d = fs()["gas_production_m3"] - g0
ok = abs(d - 1e6) < 1
print(f"produced 1,000,000 m³ gas: expected +1,000,000 m3 denominator, actual +{d:,.0f}", "OK" if ok else "MISMATCH"); bad |= not ok
f = fs(); print("final flaring_intensity_pct", f["flaring_intensity_pct"], f["compliance_status"])
sys.exit(1 if bad else 0)
