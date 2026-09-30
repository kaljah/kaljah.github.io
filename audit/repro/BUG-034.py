"""POST /api/manage/sbti accepts NaN / Infinity; the trajectory endpoint then 500s or emits invalid JSON."""
import sys, json
sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/repro")
from _H_scenario import build
from auditlib import api_client
DB = "agentH_BUG034"
build(DB)
c = api_client(DB, "admin")
fail = False
for label, body in [("rate NaN", '{"base_year":2020,"base_year_emissions":1000,"target_year":2030,"reduction_rate_pct":NaN}'),
                    ("baseline Infinity", '{"base_year":2020,"base_year_emissions":Infinity,"target_year":2030,"reduction_rate_pct":4.2}')]:
    r = c.post("/api/manage/sbti", data=body, content_type="application/json")
    t = c.get("/api/dashboard/sbti-trajectory")
    txt = t.get_data(as_text=True)
    try:
        json.loads(txt, parse_constant=lambda k: (_ for _ in ()).throw(ValueError(k))); strict = "valid JSON"
    except Exception as e:
        strict = f"INVALID JSON ({e})"
    print(f"{label}: expected POST 400; actual POST {r.status_code}; trajectory GET {t.status_code} {strict}")
    fail |= r.status_code != 400
sys.exit(1 if fail else 0)
