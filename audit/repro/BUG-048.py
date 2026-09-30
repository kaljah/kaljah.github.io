# BUG-048: Tier 3 fugitive unit parsing (CH4 subscript, tonne-as-kg)
import sys; sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/repro")
from _agentA_common import post_scope1, check
ok = True
r = post_scope1("reproA_048", {"process_type": "wellhead_fugitive", "factor_source": "specific", "fuel": "Wellhead - Gas", "amount": 10, "quantity": 10, "unit": "count"})
ok &= check("wellheads ch4 t/yr", 10 * 1.8e-5 * 8760, r.get("ch4_emissions"))
r = post_scope1("reproA_048", {"process_type": "fugitive_component", "factor_source": "specific", "fuel": "Component - Block Valve", "amount": 10, "quantity": 10, "unit": "count"})
ok &= check("valves ch4 t/yr", 10 * 4.36e-6 * 8760, r.get("ch4_emissions"))
sys.exit(0 if ok else 1)
