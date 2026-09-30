# BUG-011: completions rate x duration treats Mcf/hr as Mcf/day (24x under)
import sys; sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/repro")
from _agentA_common import post_scope1, check
row = post_scope1("reproA_011", {"process_type": "completions", "factor_source": "specific", "amount": 339.8016, "unit": "m3",
    "calc_inputs": {"completions": {"calc_method": "rate_duration", "comp_rate": 0.5, "comp_duration": 24, "ch4_content": 80, "amount": 2}}})
exp = 0.5 * 1000 * 24 * 2 * 0.028316846592 * 0.80 * 0.6785 / 1000
sys.exit(0 if check("ch4 t", exp, row.get("ch4_emissions")) else 1)
