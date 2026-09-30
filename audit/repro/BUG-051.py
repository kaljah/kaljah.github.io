# BUG-051: kWh/MJ treated as scf
import sys; sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/repro")
from _agentA_common import post_scope1, check
ok = True
r = post_scope1("reproA_051", {"process_type": "combustion", "factor_source": "default", "fuel": "Natural Gas", "amount": 1000, "quantity": 1000, "unit": "kwh"})
ok &= check("1000 kWh co2 t", 3.412142 * 53.06 / 1000, r.get("co2_emissions"))
r = post_scope1("reproA_051", {"process_type": "combustion", "factor_source": "default", "fuel": "Natural Gas", "amount": 1e6, "quantity": 1e6, "unit": "mj"})
ok &= check("1e6 MJ co2 t", 947.817 * 53.06 / 1000, r.get("co2_emissions"))
sys.exit(0 if ok else 1)
