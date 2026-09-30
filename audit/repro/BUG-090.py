"""BUG-090: dehydrator form key dehy_pressure ignored (server reads dehy_press). Own db repro_bug090."""
import sys; sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/tools")
from auditlib import api_client
c = api_client("repro_bug090", "admin")
dh = {"dehy_throughput": 1000, "dehy_pump_rate": 5, "dehy_hours": 8760, "dehy_ch4_content": 85, "dehy_temp": 100}
def ch4(extra):
    p = {"facility_id": 1, "year": 2026, "month": 9, "process_type": "dehydrator", "factor_source": "specific", "status": "Draft",
         "amount": 1000, "unit": "MMscf/day", "calc_inputs": {"dehydrator": dict(dh, **extra)}}
    return c.post("/api/emissions", json=p).get_json()["emissions"]["ch4"]
a, b = ch4({"dehy_pressure": 200}), ch4({"dehy_pressure": 1000})  # keys exactly as the UI sends them
print(f"UI key dehy_pressure: 200 psig -> {a:.4f} t CH4, 1000 psig -> {b:.4f} t CH4 (expected to differ)")
sys.exit(1 if abs(a - b) < 1e-9 else 0)
