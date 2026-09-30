import h, math
R = {}
def run(label, p, exp):
    row = h.show(label, p)
    print("   EXPECTED:", exp)
    R[label] = row
    return row

D_CH4, D_CO2, SCF = 0.6785, 1.861, 0.028316846592
# Blowdown (UI shape: root amount already m3)
ui = {"blowdown_volume": 100, "blowdown_unit": "m3", "blowdown_pressure": 500, "blowdown_events": 2, "ch4_content": 90}
v = 100 * (500 / 14.696) * 2
run("blowdown T3 100 m3 @500 psig x2, 90% CH4", {"process_type": "blowdown", "factor_source": "specific", "amount": 100, "quantity": 100, "unit": "m3", "calc_inputs": {"blowdown": ui}},
    "ch4 = %.4f t" % (v * 0.9 * D_CH4 / 1000))
ui2 = dict(ui, control_efficiency=98)
run("blowdown T3 flared 98%", {"process_type": "blowdown", "factor_source": "specific", "amount": 100, "quantity": 100, "unit": "m3", "calc_inputs": {"blowdown": ui2}},
    "ch4 = %.4f t (2%% vented + 2%% of flared unburnt), co2 = %.4f t" % (v*0.9*D_CH4/1000*(0.02 + 0.98*0.02), v*0.9*D_CH4/1000*0.98*0.98*44.01/16.04))
# Pneumatic
ui = {"amount": 10, "pneu_bleed_rate": 20, "pneu_bleed_unit": "scf", "pneu_ch4_content": 85, "pneu_hours": 8760}
run("pneumatic T3 10 dev 20 scf/h 8760 h 85%", {"process_type": "pneumatic", "factor_source": "specific", "amount": 10, "quantity": 10, "unit": "devices", "calc_inputs": {"pneumatic": ui}},
    "ch4 = %.4f t" % (10 * 20 * 8760 * SCF * 0.85 * D_CH4 / 1000))
# Tank flashing
ui = {"amount": 10000, "tank_unit": "bbl", "tank_gor": 50, "tank_ch4_content": 60}
run("tank_flashing T3 10000 bbl GOR 50 60%", {"process_type": "tank_flashing", "factor_source": "specific", "amount": 10000, "quantity": 10000, "unit": "bbl", "calc_inputs": {"tank_flashing": ui}},
    "ch4 = %.4f t" % (10000 * 50 * SCF * 0.6 * D_CH4 / 1000))
# Unloading
ui = {"unload_freq": 10, "unload_diam": 2.375, "unload_depth": 8000, "unload_press": 200, "ch4_content": 85}
vt = math.pi / 4 * (2.375 * 0.0254) ** 2 * 8000 * 0.3048 * ((200 + 14.696) / 14.696) * 10
run("unloading T3 8000 ft 2.375 in 200 psig x10", {"process_type": "unloading", "factor_source": "specific", "amount": 10, "quantity": 10, "unit": "events", "calc_inputs": {"unloading": ui}},
    "ch4 = %.5f t (at 60F)" % (vt * 0.85 * D_CH4 / 1000))
# Mud degassing T3
run("drilling T3 100 m3 WBM", {"process_type": "drilling", "factor_source": "specific", "fuel": "Drilling - Mud Degassing (Water Based)", "amount": 100, "quantity": 100, "unit": "m3", "calc_inputs": {"drilling": {"mud_vol": 100, "mud_unit": "m3", "mud_type": "water_based"}}},
    "ch4 = 0.015 t")
# AGR
def agr(cin, cout, label):
    ui = {"agr_throughput": 1000, "agr_unit": "MMscf/yr", "agr_co2_in": cin, "agr_co2_out": cout, "ch4_mole_pct": 85}
    d = (cin/100 - cout/100) / (1 - cout/100)
    run(label, {"process_type": "agr", "factor_source": "specific", "amount": 1000, "quantity": 1000, "unit": "MMscf", "calc_inputs": {"agr": ui}},
        "co2 = %.3f t" % (1e9 * d * SCF * D_CO2 / 1000))
agr(5.0, 0.05, "AGR T3 1000 MMscf, CO2 5.0% -> 0.05%")
agr(0.8, 0.05, "AGR T3 1000 MMscf, CO2 0.8% -> 0.05%")
# Dehydrator
ui = {"dehy_throughput": 100, "dehy_pump_rate": 30, "dehy_pump_unit": "gph", "dehy_hours": 8760, "dehy_ch4_content": 85, "dehy_pressure": 400, "dehy_temp": 100}
r1 = run("dehydrator T3 contactor 400 psig", {"process_type": "dehydrator", "factor_source": "specific", "amount": 100, "quantity": 100, "unit": "MMscf/day", "calc_inputs": {"dehydrator": ui}}, "depends on pressure")
ui2 = dict(ui, dehy_pressure=1200)
r2 = run("dehydrator T3 contactor 1200 psig", {"process_type": "dehydrator", "factor_source": "specific", "amount": 100, "quantity": 100, "unit": "MMscf/day", "calc_inputs": {"dehydrator": ui2}}, "must differ from 400 psig")
ui3 = dict(ui, dehy_control="flare", dehy_eff=98)
run("dehydrator T3 flare 98%", {"process_type": "dehydrator", "factor_source": "specific", "amount": 100, "quantity": 100, "unit": "MMscf/day", "calc_inputs": {"dehydrator": ui3}}, "co2 from combustion > 0")
ui4 = dict(ui, dehy_control="flare")
run("dehydrator T3 flare, no eff entered", {"process_type": "dehydrator", "factor_source": "specific", "amount": 100, "quantity": 100, "unit": "MMscf/day", "calc_inputs": {"dehydrator": ui4}}, "flare default 98% applied")
# Nitric / stoich / chem
run("nitric T3 1000 t, EF 9", {"process_type": "nitric_acid_production", "factor_source": "specific", "fuel": "Nitric Acid - Without NSCR", "amount": 1000, "quantity": 1000, "unit": "tonne"}, "n2o 9 t, co2e 2385")
run("nitric T1 1000 t", {"process_type": "nitric_acid_production", "factor_source": "default", "fuel": "Nitric Acid - Without NSCR", "amount": 1000, "quantity": 1000, "unit": "tonne"}, "n2o 9 t, co2e 2385")
run("stoich T3 1000 kg C 85%", {"process_type": "stoichiometry", "factor_source": "specific", "amount": 1000, "quantity": 1000, "unit": "kg", "carbon_content": 85}, "co2 = %.4f t" % (0.85 * 44.01 / 12.011))
run("chemical T1 Methanol 1000 t", {"process_type": "chemical_production", "factor_source": "default", "fuel": "Methanol", "amount": 1000, "quantity": 1000, "unit": "tonne"}, "co2 670 t, ch4 2.3 t")
run("asphalt T1 1000 ton", {"process_type": "asphalt_blowing", "factor_source": "default", "fuel": "Asphalt", "amount": 1000, "quantity": 1000, "unit": "ton"}, "co2 10.4326 t")
# Tier 1 others
run("flaring T1 NG(Flaring) 1000 scf", {"process_type": "flaring", "factor_source": "default", "fuel": "Natural Gas (Flaring)", "amount": 1000, "quantity": 1000, "unit": "scf"}, "co2 = %.6f t" % (1000 * SCF * 1.92 / 1000))
run("venting T1 NG vent 1000 m3", {"process_type": "venting", "factor_source": "default", "fuel": "Natural Gas (Venting/Blowdown)", "amount": 1000, "quantity": 1000, "unit": "m3"}, "ch4 0.67 t co2 0.054 t")
run("pneumatic T1 high bleed x10", {"process_type": "pneumatic", "factor_source": "default", "fuel": "Pneumatic Controller - High Bleed (>6 scfh)", "amount": 10, "quantity": 10, "unit": "devices"}, "ch4 83.04 t/yr")
run("tank_working T1 10000 bbl", {"process_type": "tank_working", "factor_source": "default", "fuel": "Tank - Working Losses (Oil)", "amount": 10000, "quantity": 10000, "unit": "bbl"}, "ch4 0.5 t")
run("completions T1 gas well x3", {"process_type": "completions", "factor_source": "default", "fuel": "Completion - Gas Well (No Flaring)", "amount": 3, "quantity": 3, "unit": "events"}, "ch4 2.1 t")
run("unloading T1 plunger x10", {"process_type": "unloading", "factor_source": "default", "fuel": "Liquids Unloading - Plunger Lift", "amount": 10, "quantity": 10, "unit": "events"}, "ch4 1.0 t (0.1 t/event)")
run("mobile T1 diesel 1000 gal", {"process_type": "mobile", "factor_source": "default", "fuel": "Diesel (No. 2 Fuel Oil)", "amount": 1000, "quantity": 1000, "unit": "gal"}, "co2 = %.4f t" % (1000 * 0.138 * 73.96 / 1000))
run("combustion T1 diesel 10 bbl", {"process_type": "combustion", "factor_source": "default", "fuel": "Diesel (No. 2 Fuel Oil)", "amount": 10, "quantity": 10, "unit": "bbl"}, "co2 = %.4f t" % (420 * 0.138 * 73.96 / 1000))
run("combustion T1 bit coal 100 tonne", {"process_type": "combustion", "factor_source": "default", "fuel": "Bituminous Coal", "amount": 100, "quantity": 100, "unit": "tonne"}, "co2 = %.3f t" % (100 * 1.1023113 * 24.93 * 93.26 / 1000))
run("cogen T3 1000 t, heat 800, power 200 MMBtu", {"process_type": "cogen_allocation", "factor_source": "specific", "amount": 1000, "quantity": 1000, "unit": "t", "heat_output": 800, "power_output": 200}, "heat share co2 = %.3f t" % (1000 * (800/0.8) / (800/0.8 + 200/0.33)))
run("indirect_steam T3 1000 MMBtu eff 0.8", {"process_type": "indirect_steam", "factor_source": "specific", "fuel": "Natural Gas", "amount": 1000, "quantity": 1000, "unit": "mmbtu", "heat_unit": "mmbtu", "boiler_eff": 0.8}, "co2 = 66.325 t")
