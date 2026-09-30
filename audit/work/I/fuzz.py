import sys, json
sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/tools")
from auditlib import make_db, api_client
DB="agentI_fuzz"; make_db(DB, overwrite=True)
a = api_client(DB,"admin")
base = {
 "/api/emissions/": {"facility_id":1,"year":2025,"month":1,"process_type":"combustion","fuel_type":"Natural Gas","quantity":10,"unit":"MMBtu"},
 "/api/scope2": {"facility_id":1,"year":2025,"month":1,"electricity_kwh":1000,"grid_region":"Algerian National Grid"},
 "/api/scope3": {"facility_id":1,"year":2025,"month":1,"category":"Purchased Goods and Services","activity_data":10,"unit":"USD","emission_factor":0.5},
 "/api/data/production": {"facility_id":1,"year":2025,"month":1,"oil_amount":10,"gas_amount":5},
 "/api/goals": {"year":2030,"target_amount":1000},
 "/api/base-years": {"year":2020,"reason":"x"},
 "/api/sources": {"facility_id":1,"name":"S1","type":"combustion"},
 "/api/mitigation": {"facility_id":1,"name":"M","year":2025,"quantity_tco2e":5},
 "/api/data/ogmp-surveys": {"facility_id":1,"year":2025,"source_type":"x","bottom_up_ch4":1,"top_down_ch4":1},
 "/api/data/cbam-exports": {"facility_id":1,"year":2025,"product":"cement","quantity_tonnes":1},
 "/api/facilities": {"name":"FZ","region":"West","latitude":1,"longitude":1},
 "/api/custom-factors": {"name":"CFZ","co2_factor":1,"unit":"scf"},
 "/api/reporting-metadata": {"year":2025},
 "/api/cap/emissions": {"facility_id":1,"year":2025,"source_module":"c","pollutant":"NO2","mass_tonnes":1},
 "/api/equity/shares": {"facility_id":1,"partner_id":1,"equity_share_pct":10},
}
bad_vals = ["abc", -1e308, "1e999", None, [], {}, "NaN", 10**30]
leaks=[]; fives=[]; accepts=[]
for p, body in base.items():
    for k in list(body):
        for v in bad_vals:
            b = dict(body); b[k] = v
            try:
                r = a.post(p, json=b)
            except Exception as e:
                fives.append((p,k,repr(v),"EXC "+type(e).__name__)); continue
            t = r.get_data(as_text=True)
            if r.status_code >= 500: fives.append((p,k,repr(v),r.status_code))
            if any(s in t for s in ["sqlite","SQL","Traceback","could not convert","object has no attribute","NoneType","not supported between","invalid literal"]):
                leaks.append((p,k,repr(v),r.status_code,t[:160]))
            if r.status_code in (200,201) and v in ("NaN","1e999",-1e308,10**30) : accepts.append((p,k,repr(v),r.status_code))
print("== 500s", len(fives)); [print(x) for x in fives]
print("== leaks", len(leaks)); [print(x) for x in leaks]
print("== accepted nonfinite/huge", len(accepts)); [print(x) for x in accepts]
