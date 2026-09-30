import sys; sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/tools")
from auditlib import get_app
app = get_app("agentD")
with app.app_context():
    from calculations.dispatcher import *  # noqa
    import calculations.dispatcher as D
    disp = [v for k,v in vars(D).items() if isinstance(v, type) and hasattr(v,'dispatch')][0]()
    from emission_factors_api2021 import ALL_EMISSION_FACTORS as F
    ef = F["Component - Control Valve"]
    print(ef["ch4"], ef["unit"])
    r = disp.dispatch("fugitive_component", {"amount":100, "component_type":"Component - Control Valve","factor_source":"default","unit":"count"}, dict(ef), {})
    ch4 = r["results"]["ch4"]; ch4 = ch4["value"] if isinstance(ch4, dict) and "value" in ch4 else ch4
    print("fugitive_component result:", r["results"]["ch4"] if not isinstance(ch4,(int,float)) else ch4, r.get("method"))
    print("expected t CH4/yr:", 100*1.11e-05*8760)
    r2 = disp.dispatch("wellhead_fugitive", {"amount":100,"factor_source":"default"}, dict(ef), {})
    print("equipment path:", r2["results"]["ch4"])
