import sys; sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/tools")
from auditlib import api_client
c = api_client("ui_k_scratch", "admin")
def post(pt, ci, **kw):
    p = {"facility_id":1,"year":2026,"month":9,"process_type":pt,"factor_source":"specific","status":"Draft","amount":1000,"unit":"MMscf", "calc_inputs":{pt:ci}, **kw}
    r = c.post("/api/emissions", json=p); j=r.get_json(); return r.status_code, j.get("emissions", j)
agr = {"agr_throughput":1000,"agr_unit":"MMscf/yr","agr_co2_in":5,"agr_co2_out":0.5}
print("AGR base          ", post("agr", agr))
print("AGR offgas_to_flare", post("agr", dict(agr, offgas_to_flare=True, flash_gas_recycled=True)))
print("AGR control_type=flare", post("agr", dict(agr, agr_control_type="flare")))
dh = {"dehy_throughput":1000,"dehy_pump_rate":5,"dehy_hours":8760,"dehy_ch4_content":85,"dehy_temp":100}
for pr in [200, 1000]:
    print("DEHY dehy_pressure", pr, post("dehydrator", dict(dh, dehy_pressure=pr)))
    print("DEHY dehy_press   ", pr, post("dehydrator", dict(dh, dehy_press=pr)))
