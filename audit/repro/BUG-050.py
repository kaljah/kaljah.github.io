# BUG-050: negative amount accepted for non-dispatcher process types
import sys; sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/repro")
from _agentA_common import post_scope1
r = post_scope1("reproA_050", {"process_type": "loading", "factor_source": "default", "fuel": "Loading - Crude Oil (Tank Truck)", "amount": -1000000, "unit": "bbl"})
print("expected HTTP 422; got", r.get("_status", 201), "co2e_total=", r.get("co2e_total"))
sys.exit(0 if r.get("_status") == 422 else 1)
