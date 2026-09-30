"""BUG-066: AGR throughput units other than MMscf/yr are misread by the server. Uses own db copy repro_bug066."""
import sys; sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/tools")
from auditlib import api_client
c = api_client("repro_bug066", "admin")
EXPECTED = 4.5e7 / 379.5 * 44.01 * 0.45359237 / 1000  # t CO2 for 1000 MMscf, 5% -> 0.5% CO2
base = {"facility_id": 1, "year": 2026, "month": 9, "process_type": "agr", "factor_source": "specific", "status": "Draft", "amount": 1, "unit": "MMscf"}
bad = 0
for thr, unit in [(1000, "MMscf/yr"), (1000 / 365, "MMscf/day"), (1e6 / 365, "Mcf/day"), (28316846.6, "m3/yr")]:
    p = dict(base, calc_inputs={"agr": {"agr_throughput": thr, "agr_unit": unit, "agr_co2_in": 5, "agr_co2_out": 0.5}})
    co2 = c.post("/api/emissions", json=p).get_json()["emissions"]["co2"]
    ok = abs(co2 / EXPECTED - 1) < 0.02
    bad += not ok
    print(f"{unit:10s} expected {EXPECTED:,.1f} t  actual {co2:,.1f} t  {'OK' if ok else 'WRONG'}")
sys.exit(1 if bad else 0)
