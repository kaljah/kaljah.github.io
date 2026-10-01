"""API Compendium 2021 worked examples (Exhibits) run END TO END through the bulk import path
(the same code path the UI wizard and the HTTP upload use), compared with the exhibit's printed
answer. Inputs are written as a user would enter them; one record per exhibit (annual activity).

python exhibits_e2e.py [db_path]   -> prints a table, writes results/exhibits_e2e.json

Tolerance: 1 % (exhibits print rounded values and use MW 16 / 44 where the platform uses 16.04 / 44.01).
"""
import csv
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from harness import boot, run_csv  # noqa: E402

B = {"date": "2024-12", "facility_name": "In Amenas CPF"}

# (exhibit, description, row, expected tonnes {gas: value}, tolerance)
CASES = [
    ("4.5", "No. 6 residual oil, 4 MMgal, 8.3 lb/gal, 92.3 wt % C (Eq 4-5 carbon balance, Tier 3 fuel analysis)",
     dict(process_type="combustion", fuel="Residual Fuel Oil (No. 6)", factor_type="specific", quantity="4000000",
          unit="gal", carbon_content="92.3", density="8.3", density_unit="lb/gal", hhv="150000", hhv_unit="Btu/gal",
          combustion_efficiency="100"),
     {"co2": 50966.0}, 0.01),
    ("4.6", "No. 6 residual oil, 4 MMgal, default factors (Table 4-3 / 4-5, HHV 6.29 MMBtu/bbl)",
     dict(process_type="combustion", fuel="Residual Fuel Oil (No. 6)", factor_type="default", quantity="4000000",
          unit="gal"),
     {"co2": 44984.0, "ch4": 1.80, "n2o": 0.36}, 0.01),
    ("5.1", "Flare, known flared volume and composition (98 % conversion, 2 % CH4)",
     dict(process_type="flaring", fuel="Natural Gas (Flaring)", quantity="20000000", unit="scf", factor_type="specific",
          c1="80", c2="4.2", c3="1.3", c4="0.4", co2_mol="12", n2_mol="2.1", control_efficiency="98"),
     {"ch4": 6.1, "co2": 1095.0}, 0.01),
    ("5.2", "Flare, known VOC emitted (Eq 5-1 / 5-5)",
     dict(process_type="flaring", factor_type="specific", combustion_method="flare_voc", voc_mass="2.21",
          voc_mass_unit="short_ton", wt_ch4="2.73", wt_c2h6="0.85", wt_c3h8="1.35", wt_c4h10="0.99", wt_c5h12="0.83",
          wt_c6plus="2.16", wt_co2="90.43", combustion_efficiency="98"),
     {"co2": 515.7, "ch4": 1.03, "n2o": 7.76e-4}, 0.01),
    ("6-1", "Offshore water-based mud degassing, 85 days, 70 % CH4 / 9 % CO2",
     dict(process_type="drilling", fuel="Drilling - Mud Degassing (Water Based)", quantity="85", unit="days",
          factor_type="default", mud_type="water_based", well_location="offshore", ch4_fraction="0.70",
          co2_fraction="0.09"),
     {"ch4": 18.49, "co2": 6.54}, 0.01),
    ("6-2", "Oil well test vented 6 h, 4,200 bbl/d, GOR 700, 70 % CH4 / 10 % CO2",
     dict(process_type="well_testing", factor_type="specific", vent_method="gor", gor="700", oil_rate="4200",
          vent_hours="6", ch4_content="70", co2_content="10"),
     {"ch4": 9.84, "co2": 3.87}, 0.01),
    ("6-3", "Completion with HF: 1.48 MMscf metered to flare, 7,390 scf N2, 4 h unmetered vent, 70 % CH4",
     dict(process_type="completions", factor_type="specific", comp_method="metered_volume", quantity="1480000", unit="scf",
          comp_injected_n2="7390", comp_injected_n2_unit="scf", comp_initial_flowback_hours="4", comp_duration="20",
          ch4_content="70", comp_c2plus_content="30", comp_disposition="flared", comp_flare_eff="98"),
     {"ch4": 2.36, "co2": 98.7}, 0.01),
    ("6-5", "Non-continuous associated gas venting: 5,200 bbl/d, GOR 700, 15 days, 70 % CH4 / 10 % CO2",
     dict(process_type="associated_gas_venting", factor_type="custom", oil_production="5200", oil_unit="bbl/day",
          quantity="5200", unit="bbl/day", gor="700", gor_unit="scf/bbl", venting_duration="15", period_duration="15",
          ch4_content="70", co2_content="10"),
     {"ch4": 731.0, "co2": 287.0}, 0.01),
    ("6-6", "Continuous associated gas venting, 365 days",
     dict(process_type="associated_gas_venting", factor_type="custom", oil_production="5200", oil_unit="bbl/day",
          quantity="5200", unit="bbl/day", gor="700", gor_unit="scf/bbl", venting_duration="365", period_duration="365",
          ch4_content="70", co2_content="10"),
     {"ch4": 17795.0, "co2": 6991.0}, 0.01),
    ("6-7", "10 gas-well workovers without HF (3,114 scf/workover), 70 % CH4 / 9 % CO2",
     dict(process_type="workovers", factor_type="specific", vent_method="volume", quantity=str(10 * 3114), unit="scf",
          ch4_content="70", co2_content="9"),
     {"ch4": 0.42, "co2": 0.15}, 0.02),
    ("6-8", "Liquids unloading Eq 6-10: 12 events, 10 in casing, 12,000 ft, 250 psig, HR 1 h, 80 % CH4 / 3 % CO2",
     dict(process_type="unloading", factor_type="specific", quantity="12", unit="events", unloading_type="non_plunger",
          unload_depth="12000", unload_diam="10", unload_press="250", unload_freq="12", sfr="35000", hours_open="1",
          ch4_content="80", co2_content="3", unload_flare_eff="0"),
     {"ch4": 20.39, "co2": 2.10}, 0.01),
    ("6-9", "Primary heavy oil casing gas: 100 bbl/d x 365 d, 70 % CH4 / 9 % CO2 (Table 6-12)",
     dict(process_type="casing_gas", factor_type="default", activity_key="cg_primary_heavy", quantity="36500", unit="bbl",
          ch4_content="70", co2_content="9"),
     {"ch4": 102.7, "co2": 36.3}, 0.01),
    ("6-10", "Low-pressure casing gas migration: 3 wells x 365 d, 70 % CH4 / 9 % CO2",
     dict(process_type="casing_gas", factor_type="default", activity_key="cg_migration", quantity="3", unit="wells",
          activity_days="365", ch4_content="70", co2_content="9"),
     {"ch4": 2.00, "co2": 0.71}, 0.015),
    ("6-11", "80 low-bleed controllers (API study), 8,760 h, 70 % CH4 (exhibit CO2 uses 2.1 scf as whole gas: CH4 only)",
     dict(process_type="pneumatic", factor_type="default", activity_key="prod_pc_low_bleed_api", quantity="80",
          unit="devices", operating_hours="8760", ch4_content="70", co2_content="9"),
     # Table 6-14 prints 2.6 scf gas and 2.1 scf CH4 (2.1 / 0.816 = 2.574): the 1.07 % gap is the table's rounding
     {"ch4": 24.2}, 0.011),
    ("6-12a", "Intermittent controllers, normal: 79 controller-years, 70 % CH4 / 9 % CO2",
     dict(process_type="pneumatic", factor_type="default", activity_key="prod_pc_int_normal_api", quantity="79",
          unit="devices", operating_hours="8760", ch4_content="70", co2_content="9"),
     {"ch4": 0.038 * 79 * 0.70 / 0.816, "co2": 0.038 * 79 * 0.70 / 0.816 / 16 / 0.70 * 0.09 * 44}, 0.015),
    ("6-12b", "Intermittent controllers, malfunctioning: 1 controller-year (sum with 6-12a = 5.41 t CH4 / 1.91 t CO2)",
     dict(process_type="pneumatic", factor_type="default", activity_key="prod_pc_int_malf_api", quantity="1",
          unit="devices", operating_hours="8760", ch4_content="70", co2_content="9"),
     {"ch4": 3.30 * 0.70 / 0.816, "co2": 3.30 * 0.70 / 0.816 / 16 / 0.70 * 0.09 * 44}, 0.015),
    ("6-13", "Glycol dehydrator vent, production, 25 MMscf/d x 365, 82 % CH4 (Table 6-17)",
     dict(process_type="dehydrator", factor_type="default", activity_key="dh_glycol_production",
          quantity=str(25 * 365), unit="MMscf", ch4_content="82"),
     {"ch4": 50.2}, 0.01),
    ("6-14", "Kimray gas-assisted pump, production, 25 MMscf/d x 365, 82 % CH4 / 5 % CO2 (Table 6-18)",
     dict(process_type="dehydrator", factor_type="default", activity_key="dh_kimray_production",
          quantity=str(25 * 365), unit="MMscf", ch4_content="82", co2_content="5"),
     {"ch4": 180.7, "co2": 30.3}, 0.01),
    ("6-15", "Desiccant dehydrator Eq 6-16: 6.40 ft x 1.60 ft, 450 psig, 45 % packed, 52 refills/yr "
             "(record = December: 31/366 of the annual refills)",
     dict(process_type="desiccant_dehydrator", factor_type="specific", vent_method="desiccant", vessel_height_ft="6.40",
          vessel_diameter_ft="1.60", vessel_pressure_psig="450", gas_fraction="45", refills="52",
          ch4_content="90", co2_content="5"),
     {"ch4": 9519 * 0.90 / 379.3 * 16 / 2204.62 * 31 / 366, "co2": 9519 * 0.05 / 379.3 * 44 / 2204.62 * 31 / 366}, 0.01),
    ("6-16", "AGR unit factor, 1 unit x 365 d (Table 6-19)",
     dict(process_type="agr", factor_type="default", activity_key="agr_unit", quantity="1", unit="units",
          activity_days="365"),
     {"ch4": 236.6}, 0.01),
    ("6-17", "Amine unit CO2 material balance Eq 6-18, Tier 3 AGR form fields: 150,000 MMscf at 3 % CO2 -> 2 % CO2",
     dict(process_type="agr", factor_type="specific", quantity="150000", unit="MMscf", agr_co2_in="3", agr_co2_out="2"),
     {"co2": 80506.0, "ch4": 2775.0}, 0.01),
    ("6-17b", "Same, gas-volume method agr_balance with both volumes (150,000 / 148,500 MMscf)",
     dict(process_type="agr", factor_type="specific", vent_method="agr_balance", sour_gas_volume="150000",
          sweet_gas_volume="148500", gas_volume_unit="MMscf", sour_co2_content="3", sweet_co2_content="2"),
     {"co2": 80506.0, "ch4": 2775.0}, 0.01),
    ("6-19", "Crude tank flashing, chart GOR 47 scf/bbl, 451 bbl/d x 365, CH4 unknown (default 27.4 %)",
     dict(process_type="tank_flashing", factor_type="specific", quantity=str(451 * 365), unit="bbl", tank_gor="47"),
     {"ch4": 40.6}, 0.01),
    ("6-20", "Crude tank flashing, Table 6-22 large uncontrolled factor, 451 bbl/d x 365, separator gas 58 % CH4 "
             "(factor NOT adjusted for CH4 content)",
     dict(process_type="tank_flashing", factor_type="specific", quantity=str(451 * 365), unit="bbl",
          tank_method="table_6_22", ch4_content="58"),
     {"ch4": 31.8}, 0.01),
    ("6-22", "CO2 EOR injection pump blowdown, 36.4 m3 at 650 kg/m3, 98.5 wt % CO2",
     dict(process_type="co2_eor", factor_type="specific", vent_method="co2_mass", physical_volume_m3="36.4",
          co2_density="650", co2_wt_pct="98.5", events="1"),
     {"co2": 23.3}, 0.01),
    ("6-25", "Separator blowdown Eq 6-32/6-33: 83.8 ft3 gas space, 100 psig, 80 F, Z 0.9864, 90 % CH4, 1 event",
     dict(process_type="blowdown", factor_type="specific", quantity="83.8", unit="ft3", blowdown_pressure="100",
          blowdown_events="1", blowdown_temp="80", z_factor="0.9864", ch4_content="90"),
     {"ch4": 0.011}, 0.03),
    ("6-26a", "Vessel blowdowns, 5 vessels, 70 % CH4 / 8 % CO2 (Table 6-32), full year",
     dict(process_type="non_routine_venting", factor_type="default", activity_key="gb_bd_vessel", quantity="5",
          unit="vessels", activity_year_fraction="1", ch4_content="70", co2_content="8"),
     {"ch4": 5 * 78 * 0.70 / 0.788 / 379.3 * 16 / 2204.62, "co2": 5 * 99 * 0.08 / 379.3 * 44 / 2204.62}, 0.02),
    ("6-26b", "Compressor blowdowns, 1 compressor, 70 % CH4 / 8 % CO2, full year",
     dict(process_type="non_routine_venting", factor_type="default", activity_key="gb_bd_compressor", quantity="1",
          unit="compressors", activity_year_fraction="1", ch4_content="70", co2_content="8"),
     {"ch4": 3774 * 0.70 / 0.788 / 379.3 * 16 / 2204.62, "co2": 4789 * 0.08 / 379.3 * 44 / 2204.62}, 0.02),
    ("6-35", "Rail splash loading, dedicated, 50,000 bbl, 12 wt % CH4 in TOC (Table 6-47)",
     dict(process_type="loading", factor_type="default", activity_key="load_splash_dedicated", quantity="50000",
          unit="bbl", toc_ch4_wt="12"),
     {"ch4": 0.554}, 0.01),
    ("7-5", "Correlation approach, 100 gas-plant flanges: 95 non-detect, 4 at 7,950 ppmv, 1 pegged at 10,000; "
            "default 56.4 wt % CH4, 8,760 h",
     dict(process_type="fugitive", factor_type="specific", fugitive_method="correlation", component_type="flange",
          corr_zero_count="95", corr_screened_count="4", fugitive_ppm="7950", corr_pegged_10k_count="1",
          operating_hours="8760"),
     {"ch4": 0.47}, 0.02),
]


def run(db_path, cases=CASES):
    rows = []
    for i, (ex, _d, row, _e, _t) in enumerate(cases):
        rows.append(dict(B, source_ref=f"EX-{i:03d}-{ex}", **row))
    header = ["source_ref", "date", "facility_name"] + sorted({k for r in rows for k in r} - {"source_ref", "date", "facility_name"})
    fd, path = tempfile.mkstemp(suffix=".csv")
    os.close(fd)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, header)
        w.writeheader()
        w.writerows(rows)
    app = boot(db_path)
    job = run_csv(app, path)
    reasons = {rows[s["row"] - 2]["source_ref"]: s["reason"] for s in job["skipped"]}
    from models import Emission

    out = []
    with app.app_context():
        recs = {e.data_source_ref: e for e in Emission.query.all()}
        for (ex, desc, row, expect, tol), r in zip(cases, rows):
            e = recs.get(r["source_ref"])
            res = {"exhibit": ex, "description": desc, "expected": expect}
            if e is None:
                res.update(status="REFUSED", reason=reasons.get(r["source_ref"]))
            else:
                got = {"co2": e.co2_emissions, "ch4": e.ch4_emissions, "n2o": e.n2o_emissions, "co2e": e.co2e_total}
                res["got"] = got
                ok = True
                for g, v in expect.items():
                    gg = g.split("_")[0]
                    if abs(got[gg] - v) > tol * abs(v) + 1e-9:
                        ok = False
                res["status"] = "OK" if ok else "DIFF"
            out.append(res)
    return out


if __name__ == "__main__":
    res = run(sys.argv[1] if len(sys.argv) > 1 else os.path.join(tempfile.gettempdir(), "exhibits_e2e.db"))
    for r in res:
        got = r.get("got") or {}
        print(f"{r['exhibit']:>5} {r['status']:7} expected {r['expected']} got "
              f"{ {k: round(v, 4) for k, v in got.items()} if got else r.get('reason')}")
    os.makedirs(os.path.join(os.path.dirname(os.path.abspath(__file__)), "results"), exist_ok=True)
    json.dump(res, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "results", "exhibits_e2e.json"), "w"),
              indent=1, default=str, ensure_ascii=False)
