import sys, json; sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/tools")
from auditlib import api_client, make_db, db_path
name = sys.argv[1] if len(sys.argv)>1 else "agentE_flare"
make_db(name, overwrite=True)
c = api_client(name, "admin")
def fs():
    return c.get("/api/dashboard/flaring-summary?year=2026&facilityId=13").get_json()
b = fs(); print("before", b["total_flaring"], b["gas_production_m3"], b["flaring_intensity_pct"])
tok = c.get("/api/csrf-token").get_json()
res = {}
for unit, amt, exp_m3 in [("mmscf", 1, 28316.8), ("scf", 1_000_000, 28316.8), ("kscf", 1000, 28316.8)]:
    before = fs()["total_flaring"]["volume_m3"]
    r = c.post("/api/emissions/", json={"process_type":"flaring","source_type":"Flaring","facility_id":13,"year":2026,"month":3,
        "amount":amt,"unit":unit,"c1":90,"fuel":"Natural Gas"})
    j = r.get_json()
    after = fs()
    delta = after["total_flaring"]["volume_m3"] - before
    print(unit, r.status_code, (j if r.status_code>=300 else "ok"), "expected +m3", exp_m3, "actual +m3", round(delta,4), "intensity%", after["flaring_intensity_pct"])
    res[unit]=delta
print(json.dumps(fs()))
