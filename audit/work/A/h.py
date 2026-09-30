import sys, json
sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/tools")
from auditlib import make_db, api_client, sql
DB = "agentA"
make_db(DB)
_c = None
def c():
    global _c
    if _c is None:
        _c = api_client(DB, "admin")
    return _c
FAC = None
def fac():
    global FAC
    if FAC is None:
        FAC = sql(DB, "select id from facilities order by id limit 1")[0]["id"]
    return FAC
def post(payload):
    p = {"year": 2025, "month": 1, "facility_id": fac()}
    p.update(payload)
    r = c().post("/api/emissions/", json=p)
    j = r.get_json()
    if r.status_code != 201:
        return r.status_code, j, None
    row = sql(DB, "select co2_emissions,ch4_emissions,n2o_emissions,co2e_total,calc_method,gwp_version,quantity,unit from emissions where id=?", (j["id"],))[0]
    return r.status_code, j, row
def show(label, payload):
    s, j, row = post(payload)
    print("==", label, s)
    if row is None:
        print("  ", j)
    else:
        print("   DB:", row)
    return row
