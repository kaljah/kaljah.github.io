import sys; sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/tools")
from auditlib import api_client, get_app
c = api_client("ui_k_scratch", "admin")
from calculations.dispatcher import *
import calculations.dispatcher as d
D = [v for k,v in vars(d).items() if isinstance(v,type) and hasattr(v,"_normalize_volume")][0]()
for u in ["m3/yr","m3","MMscf/yr","MMscf","mmscf","Mcf/day"]:
    try: print(u, D._normalize_volume(28316800 if 'm3' in u else 1000, u, "mmscf"))
    except Exception as e: print(u, "ERR", e)
base = {"facility_id":1,"year":2026,"month":9,"process_type":"agr","factor_source":"specific","status":"Draft"}
for thr,unit in [(28316800,"m3/yr"),(1000,"MMscf/yr")]:
    p = dict(base, amount=1, unit="MMscf", calc_inputs={"agr":{"agr_throughput":thr,"agr_unit":unit,"agr_co2_in":5,"agr_co2_out":0.5}})
    r = c.post("/api/emissions", json=p); print(unit, r.status_code, r.get_json().get("emissions"))
