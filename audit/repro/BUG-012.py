# BUG-012: completions amount used as volume AND events; default method ignores rate x duration
import sys; sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/repro")
from _agentA_common import post_scope1, check
ok = True
r1 = post_scope1("reproA_012", {"process_type": "completions", "factor_source": "specific", "amount": 1000, "unit": "m3", "ch4_content": 80, "comp_method": "metered_volume"})
ok &= check("metered 1000 m3 ch4 t", 1000 * 0.8 * 0.6785 / 1000, r1.get("ch4_emissions"))
r2 = post_scope1("reproA_012", {"process_type": "completions", "factor_source": "specific", "amount": 339.8016, "unit": "m3",
    "calc_inputs": {"completions": {"comp_rate": 0.5, "comp_duration": 24, "ch4_content": 80, "amount": 2}}})
ok &= check("UI default-method ch4 t", 0.5 * 1000 * 24 * 2 * 0.028316846592 * 0.8 * 0.6785 / 1000, r2.get("ch4_emissions"))
sys.exit(0 if ok else 1)
