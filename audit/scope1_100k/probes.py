"""Minimal reproductions of the audit findings (one or two rows each), through the real import path.

python probes.py [/tmp/probes.db]     -> prints expected vs stored for every probe, writes probes_result.json
Each probe pairs a row with a reference row that describes the same physical activity in a unit the
platform handles correctly; "ratio" is stored / reference (1.0 = correct).
"""
import csv
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from harness import boot, run_csv  # noqa: E402

B = {"date": "2024-03", "facility_name": "In Amenas CPF"}
FT3 = 0.028316846592

PROBES = [
    # id, title, test row, reference row (same physics, handled correctly) or None, expected outcome
    ("P01", "Tier 3 combustion, site HHV + catalog factor, no gas analysis: CO2 must not be 0",
     dict(process_type="combustion", fuel="Natural Gas", quantity="1000", unit="Mscf", factor_type="specific",
          hhv="1020", combustion_efficiency="99.5"),
     dict(process_type="combustion", fuel="Natural Gas", quantity="1000", unit="Mscf", factor_type="default"),
     "ratio 1 (CO2 = 1,020 MMBtu x 53.06 kg = 54.1 t)"),
    ("P02", "Tier 3 combustion of Coke Oven Gas (a gas) with a gas analysis",
     dict(process_type="combustion", fuel="Coke Oven Gas", quantity="1000", unit="Mscf", factor_type="specific",
          hhv="599", combustion_efficiency="99", c1="28", c2="3", n2_mol="5", co2_mol="2"),
     None, "accepted (it is refused: 'heating value tabulated per short_ton')"),
    ("P03", "Tier 3 tank throughput in kbbl",
     dict(process_type="tank_flashing", quantity="5", unit="kbbl", tank_unit="kbbl", factor_type="specific",
          tank_gor="85", tank_ch4_content="65", tank_control_eff="0"),
     dict(process_type="tank_flashing", quantity="5000", unit="bbl", tank_unit="bbl", factor_type="specific",
          tank_gor="85", tank_ch4_content="65", tank_control_eff="0"), "ratio 1"),
    ("P04", "Tier 3 tank throughput given as a MASS (tonne): must be refused",
     dict(process_type="tank_flashing", quantity="5000", unit="tonne", tank_unit="tonne", factor_type="specific",
          tank_gor="85", tank_ch4_content="65", tank_control_eff="0"), None, "refused"),
    ("P05", "Tier 3 pneumatic bleed rate in m³ (superscript) / Sm3 / m3/hr",
     dict(process_type="pneumatic", quantity="25", unit="devices", pneu_count="25", pneu_bleed_rate="0.169901",
          pneu_bleed_unit="m³", pneu_hours="744", pneu_ch4_content="85", factor_type="specific"),
     dict(process_type="pneumatic", quantity="25", unit="devices", pneu_count="25", pneu_bleed_rate="0.169901",
          pneu_bleed_unit="m3", pneu_hours="744", pneu_ch4_content="85", factor_type="specific"), "ratio 1"),
    ("P06", "Tier 3 pneumatic bleed rate in lb/hr (a mass rate): must be refused",
     dict(process_type="pneumatic", quantity="25", unit="devices", pneu_count="25", pneu_bleed_rate="6",
          pneu_bleed_unit="lb/hr", pneu_hours="744", pneu_ch4_content="85", factor_type="specific"), None, "refused"),
    ("P07", "Tier 3 associated-gas vent rate in Mcf/day",
     dict(process_type="associated_gas_venting", vent_rate="24", vent_rate_unit="Mcf/day", venting_duration="100",
          ch4_content="75", co2_content="3", factor_type="specific"),
     dict(process_type="associated_gas_venting", vent_rate="1000", vent_rate_unit="scfh", venting_duration="100",
          ch4_content="75", co2_content="3", factor_type="specific"), "ratio 1 (24 Mcf/day = 1,000 scf/h)"),
    ("P08", "Mass unit 'Mt' (SI: megatonne) for coal",
     dict(process_type="combustion", fuel="Bituminous Coal", quantity="1", unit="Mt", factor_type="default"),
     None, "refused as ambiguous (it is booked as 1 tonne)"),
    ("P09", "Unknown pressure unit (kg/cm2) on a metered gas volume",
     dict(process_type="combustion", fuel="Natural Gas", quantity="1000", unit="m3", factor_type="specific", hhv="1020",
          combustion_efficiency="99.5", c1="90", c2="5", operating_temperature="15.5556", temp_unit="C",
          operating_pressure="10", press_unit="kg/cm2"),
     dict(process_type="combustion", fuel="Natural Gas", quantity="1000", unit="m3", factor_type="specific", hhv="1020",
          combustion_efficiency="99.5", c1="90", c2="5", operating_temperature="15.5556", temp_unit="C",
          operating_pressure="142.233", press_unit="psia"), "refused, or ratio 1 (10 kgf/cm2 = 142.2 psia)"),
    ("P10", "Unknown temperature unit ('deg') on a metered gas volume",
     dict(process_type="combustion", fuel="Natural Gas", quantity="1000", unit="m3", factor_type="specific", hhv="1020",
          combustion_efficiency="99.5", c1="90", c2="5", operating_temperature="60", temp_unit="deg",
          operating_pressure="0", press_unit="psig"), None, "refused"),
    ("P11", "Quantity cell '928 m3' while the unit column says scf",
     dict(process_type="combustion", fuel="Natural Gas", quantity="928 m3", unit="scf", factor_type="default"),
     None, "refused (contradicting units)"),
    ("P12", "unit = bbl but tank_unit = m3 on the same row",
     dict(process_type="tank_flashing", quantity="1000", unit="bbl", tank_unit="m3", factor_type="specific",
          tank_gor="85", tank_ch4_content="65", tank_control_eff="0"), None, "refused (contradicting units)"),
    ("P13", "Per-event unloading factor with unit 'wells': silently switched to the per-well-year factor",
     dict(process_type="unloading", fuel="Liquids Unloading - Non-Plunger (≤10 events/yr)", quantity="10",
          unit="wells", factor_type="default"),
     dict(process_type="unloading", fuel="Liquids Unloading - Non-Plunger (≤10 events/yr)", quantity="10",
          unit="events", factor_type="default"), "refused (the factor is per event)"),
    ("P14", "Tier 3 HHV given with hhv_unit = MJ/m3 (37.99 MJ/m3 = 1,020 Btu/scf)",
     dict(process_type="combustion", fuel="Natural Gas", quantity="1000", unit="Mscf", factor_type="specific",
          hhv="37.99", hhv_unit="MJ/m3", combustion_efficiency="99.5", c1="90", c2="5"),
     dict(process_type="combustion", fuel="Natural Gas", quantity="1000", unit="Mscf", factor_type="specific",
          hhv="1020", combustion_efficiency="99.5", c1="90", c2="5"), "N2O identical to the reference (N2O = energy x factor; it is 37.99/1020 of it: the MJ/m3 unit is ignored)"),
    ("P15", "Tier 2 'catalog factor + site HHV' (offered by the form) through the bulk import",
     dict(process_type="combustion", fuel="Natural Gas", quantity="1000", unit="Mscf", factor_type="custom", hhv="1035"),
     None, "accepted, as on the form (the import requires a saved custom factor)"),
    ("P16", "Thousands separator in a method column (vent_volume '12,345.6')",
     dict(process_type="associated_gas_venting", quantity="12,345.6", unit="scf", vent_volume="12,345.6",
          vent_volume_unit="scf", ch4_content="75", co2_content="3", factor_type="specific"),
     dict(process_type="associated_gas_venting", quantity="12345.6", unit="scf", vent_volume="12345.6",
          vent_volume_unit="scf", ch4_content="75", co2_content="3", factor_type="specific"),
     "ratio 1 (the quantity column accepts the same notation)"),
    ("P17", "Activity table row: unit 'barrels' (spelling accepted elsewhere)",
     dict(process_type="separation", activity_key="sep_dump_valve_crude", quantity="1000", unit="barrels", factor_type="default"),
     dict(process_type="separation", activity_key="sep_dump_valve_crude", quantity="1000", unit="bbl", factor_type="default"),
     "ratio 1"),
    ("P18", "Vented gas volume in Nm3 (accepted by every other gas method)",
     dict(process_type="vented_gas", vent_method="volume", quantity="1000", unit="Nm3", ch4_content="80",
          co2_content="2", factor_type="specific"),
     dict(process_type="vented_gas", vent_method="volume", quantity="1056.95", unit="Sm3", ch4_content="80",
          co2_content="2", factor_type="specific"), "ratio 1 (1 Nm3 = 1.0570 Sm3 at 60 F)"),
]


def main(db_path):
    rows = []
    for pid, _title, test, ref, _exp in PROBES:
        rows.append(dict(B, source_ref=f"{pid}-test", **test))
        if ref:
            rows.append(dict(B, source_ref=f"{pid}-ref", **ref))
    header = sorted({k for r in rows for k in r}, key=lambda k: (k != "source_ref", k))
    fd, path = tempfile.mkstemp(suffix=".csv")
    os.close(fd)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, header)
        w.writeheader()
        w.writerows(rows)
    app = boot(db_path)
    job = run_csv(app, path)
    reasons = {}
    for s in job["skipped"]:
        reasons[rows[s["row"] - 2]["source_ref"]] = s["reason"]
    from models import Emission

    out = []
    with app.app_context():
        recs = {e.data_source_ref: e for e in Emission.query.all()}
        for pid, title, test, ref, exp in PROBES:
            t, r = recs.get(f"{pid}-test"), recs.get(f"{pid}-ref")
            res = {"id": pid, "title": title, "expected": exp,
                   "test": ({"co2_t": t.co2_emissions, "ch4_t": t.ch4_emissions, "n2o_t": t.n2o_emissions,
                             "co2e_t": t.co2e_total, "qty": t.quantity, "unit": t.unit} if t else
                            {"refused": reasons.get(f"{pid}-test")})}
            if ref:
                res["reference"] = ({"co2e_t": r.co2e_total, "co2_t": r.co2_emissions, "ch4_t": r.ch4_emissions,
                                     "n2o_t": r.n2o_emissions} if r else
                                    {"refused": reasons.get(f"{pid}-ref")})
                if t and r and r.co2e_total:
                    res["ratio_co2e"] = t.co2e_total / r.co2e_total
            out.append(res)
            print(json.dumps(res, ensure_ascii=False, default=str))
    json.dump(out, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "results", "probes_result.json"), "w"),
              indent=1, ensure_ascii=False, default=str)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(tempfile.gettempdir(), "scope1_probes.db"))
