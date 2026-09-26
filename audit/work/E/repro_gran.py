"""/granular-intensities: numerator = all facilities, denominator = only rows with total_production_mmboe (others' oil/gas dropped); NGSI methane defaults to 0.05 when gross gas missing."""
import sys, sqlite3; sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/tools")
from auditlib import api_client, db_path
name = "agentE_r4"; c = api_client(name, "admin"); con = sqlite3.connect(db_path(name))
bad = 0
g = c.get("/api/dashboard/granular-intensities?year=2025").get_json()
E = con.execute("select coalesce(sum(co2e_total),0) from emissions where year=2025 and status='Verified'").fetchone()[0] \
  + con.execute("select coalesce(sum(co2e),0) from scope2_emissions where year=2025 and status='Verified'").fetchone()[0]
B = 0.0
for mmboe, oil, ou, gas, gu in con.execute("select total_production_mmboe, oil_amount, oil_unit, gas_amount, gas_unit from production_data where year=2025"):
    if mmboe and mmboe > 0: B += mmboe * 1e6; continue
    oil = (oil or 0) * (6.28981077 if (ou or 'bbl').lower() in ('m3', 'm³') else 1)
    gu = (gu or 'mscf').lower(); gas = (gas or 0) * (1000 if gu == 'mmscf' else 0.0353147 if gu in ('m3', 'm³') else 1)
    B += oil + gas / 5.8          # endpoint's own 5.8 mscf/BOE factor
exp = E * 1000 / B
ok = abs(g["ci_by_total_production_kg_boe"] - exp) < 0.05
print(f"2025 CI total production: expected {exp:.2f} kg/BOE over {B:,.0f} BOE; actual {g['ci_by_total_production_kg_boe']} over {g['total_production_boe']:,.0f} BOE", "OK" if ok else "MISMATCH"); bad |= not ok
g = c.get("/api/dashboard/granular-intensities?year=2026&facilityId=13").get_json()
ok = not (g["gross_gas_sm3"] == 0 and g["methane_intensity_ngsi_wt_pct"] == 0.05)
print(f"2026 fid13 NGSI CH4 wt%: gross gas 0 (gas recorded in mscf), CH4 {g['total_ch4_tonnes']} t -> API returns fabricated {g['methane_intensity_ngsi_wt_pct']}", "OK" if ok else "MISMATCH"); bad |= not ok
sys.exit(1 if bad else 0)
