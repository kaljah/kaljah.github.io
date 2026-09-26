import sys; sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/tools")
from auditlib import api_client
c = api_client("ui_k_scratch", "admin")
base = {"facility_id":1,"year":2026,"month":9,"process_type":"agr","factor_source":"specific","status":"Draft","amount":1,"unit":"MMscf"}
for thr,unit in [(1000,"MMscf/yr"),(1000/365,"MMscf/day"),(1000000/365,"Mcf/day"),(28316846.6,"m3/yr")]:
    p = dict(base, calc_inputs={"agr":{"agr_throughput":thr,"agr_unit":unit,"agr_co2_in":5,"agr_co2_out":0.5}})
    r = c.post("/api/emissions", json=p); e=r.get_json()["emissions"]; print(f"{thr:>14.3f} {unit:10s} (=1000 MMscf/yr) co2={e['co2']:.1f} totalCo2e={e['totalCo2e']:.1f}")
