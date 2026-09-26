"""Repro: Scope 2/3 POST accept any 'uncertainty' (percent-looking, negative, NaN, 1e6); dashboard has no range guard."""
import sys, json; sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/tools")
from auditlib import make_db, api_client, sql
DB = "repro_G_range"
make_db(DB, overwrite=True)
c = api_client(DB, "admin")
bad = 0
for i, u in enumerate([18, -0.5, "NaN"]):
    y = 2025  # valid year, so a rejection can only come from the uncertainty value
    kwh = 100001 + i  # unique marker to find the stored row
    r = c.post("/api/scope2", json={"facility_id": 4, "year": y, "month": 1, "source_type": "electricity",
                                    "electricity_kwh": kwh, "emission_factor": 0.5, "uncertainty": u})
    body = r.get_data(as_text=True)
    try:
        json.loads(body, parse_constant=lambda s: (_ for _ in ()).throw(ValueError(s)))
        valid_json = True
    except ValueError:
        valid_json = False
    rows = sql(DB, "select uncertainty from scope2_emissions where electricity_kwh=?", (kwh,))
    stored = rows[0]["uncertainty"] if rows else None
    err = (r.get_json(silent=True) or {}).get("error", "")
    print(f"input {u!r:6}: HTTP {r.status_code} (expected 400/422 on uncertainty) error={err!r}, strict-JSON response={valid_json}, stored={stored}")
    bad += not (r.status_code in (400, 422) and "uncertainty" in err and stored is None)
sys.exit(1 if bad else 0)
