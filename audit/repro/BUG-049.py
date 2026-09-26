# BUG-049: 10^3/10^6 denominator multipliers ignored
import sys; sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/repro")
from _agentA_common import post_scope1, check
ok = True
r = post_scope1("reproA_049", {"process_type": "wellhead_fugitive", "factor_source": "default", "fuel": "Offshore - Gas Production (Facility)", "amount": 5, "quantity": 5, "unit": "mmscf"})
ok &= check("offshore ch4 t", 5 * 0.0104, r.get("ch4_emissions"))
r = post_scope1("reproA_049", {"process_type": "refinery_fugitive", "factor_source": "default", "fuel": "Refinery - Fuel Gas System (50-99k bbl/day)", "amount": 50000, "quantity": 50000, "unit": "bbl"})
ok &= check("refinery ch4 t", 50 * 0.000375, r.get("ch4_emissions"))
sys.exit(0 if ok else 1)
