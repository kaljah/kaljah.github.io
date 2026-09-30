"""Validation errors surface as 500s with raw exception / SQL text in the response."""
import sys
sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/tools")
from auditlib import make_db, api_client
DB="repro_BUG087"; make_db(DB, overwrite=True)
a = api_client(DB,"admin")
cases = [("/api/emissions/", {"facility_id":1,"year":2025,"month":1,"process_type":[],"quantity":10,"unit":"MMBtu"}),
         ("/api/scope2", {"facility_id":"abc","year":2025,"month":1,"electricity_kwh":1000}),
         ("/api/data/production", {"facility_id":1,"year":None,"month":1,"oil_amount":1}),
         ("/api/goals", {"year":"abc","target_amount":1}),
         ("/api/sources", {"facility_id":-1e308,"name":"S"})]
leaks = 0
for p, b in cases:
    r = a.post(p, json=b); t = r.get_data(as_text=True)
    leak = any(s in t for s in ["sqlite3", "[SQL:", "invalid literal", "Python int too large"])
    leaks += leak
    print(f"{p}: HTTP {r.status_code} leak={leak} :: {t[:140]!r}")
print("expected: 400 with a generic validation message; actual:", leaks, "responses leak internals")
sys.exit(1 if leaks else 0)
