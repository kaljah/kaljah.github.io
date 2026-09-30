# BUG-023: per-component percent/fraction detection in Tier 3 composition
import sys; sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/repro")
from _agentA_common import post_scope1, check
row = post_scope1("reproA_023", {"process_type": "combustion", "factor_source": "specific", "fuel": "Natural Gas", "amount": 50000, "unit": "scf",
    "hhv": 1010, "combustion_efficiency": 0.993, "c1": 87.5, "c2": 5.2, "c3": 2.1, "c4": 1.0, "c5": 0.5, "co2_mol": 1.8, "n2_mol": 1.9})
V = 50000 * 0.028316846592
carbon = 0.875 + 2 * 0.052 + 3 * 0.021 + 4 * 0.010 + 5 * 0.005
exp = V * (carbon * 0.993 + 0.018) * 1.861 / 1000
sys.exit(0 if check("co2 t", exp, row.get("co2_emissions"), rel=0.005) else 1)
