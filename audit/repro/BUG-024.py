# BUG-024: composition renormalised without N2
import sys; sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/repro")
from _agentA_common import post_scope1, check
row = post_scope1("reproA_024", {"process_type": "flaring", "factor_source": "specific", "fuel": "Natural Gas (Flaring)", "amount": 1000, "unit": "m3", "c1": 90, "n2_mol": 10})
ok = check("ch4 t", 1000 * 0.9 * 0.02 * 0.6785 / 1000, row.get("ch4_emissions"), rel=0.005)
ok &= check("co2 t", 1000 * 0.9 * 0.984 * 1.861 / 1000, row.get("co2_emissions"), rel=0.005)
sys.exit(0 if ok else 1)
