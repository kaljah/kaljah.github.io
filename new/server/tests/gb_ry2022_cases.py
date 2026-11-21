"""Groupement Berkine, HBNS & El Merk GHG inventory, reporting year 2022 (report dated 2023-05-02, API SANGEA, AR4).

Every Scope 1 / Scope 2 source row of the report's Tables 7 / 8 (HBNS) and 14 / 15 (El Merk), written as the
platform's calculation payloads, with the figures the report prints. Shared by
``tests/test_gb_inventory_ry2022.py`` and ``scripts/compare_gb_ry2022.py``.

kind:
  reproduce - every input is printed in the report: the platform should give the printed figure
  implied   - the report does not print the inputs (equipment counts "Multiple", no separator pressure, no BOD5):
              the factor SANGEA used is back-calculated and set beside the platform's factor
  gap       - the platform has no input path for the report's method

Inputs taken as printed: gas volumes in Nm3 at 0 C (Tables 7 / 14), gas compositions in vol fraction rounded to
3 decimals (Tables 6 / 13; the remainder to 100 % entered as N2), HHV in Btu/scf, 98 % flare efficiency
(section 7, item 4), AR4 GWPs (section 3).
"""
from calculations.combustion_methods import EQUIPMENT_FACTORS

GWP = "AR4"

# Table 6 (HBNS, one composition for every fuel and flare stream)
HBNS_GAS = {"c1": 0.684, "c2": 0.172, "c3": 0.101, "c4": 0.023, "c5": 0.005, "c6": 0.002, "c7": 0.001,
            "c8": 0.001, "co2": 0.006, "hhv": 1362.97}
# Table 13 (El Merk). The header names 8 streams over 7 value columns; the CO2 per Nm3 of each flare in Table 15
# matches the columns as: fuel gas (also Flare AP, as section 5.1.2 says), HP, HPLT, LP, NGL, OT1, OT2.
EMK_GAS = {
    "fuel": {"c1": 0.781, "c2": 0.171, "c3": 0.020, "c4": 0.005, "c5": 0.002, "c6": 0.001, "c7": 0.000,
             "c8": 0.000, "co2": 0.014, "hhv": 1167.69},
    "hp": {"c1": 0.752, "c2": 0.167, "c3": 0.038, "c4": 0.012, "c5": 0.004, "c6": 0.004, "c7": 0.002,
           "c8": 0.001, "co2": 0.014, "hhv": 1241.389},
    "hplt": {"c1": 0.777, "c2": 0.176, "c3": 0.019, "c4": 0.004, "c5": 0.002, "c6": 0.001, "c7": 0.001,
             "c8": 0.000, "co2": 0.016, "hhv": 1173.946},
    "lp": {"c1": 0.781, "c2": 0.171, "c3": 0.020, "c4": 0.005, "c5": 0.002, "c6": 0.001, "c7": 0.000,
           "c8": 0.000, "co2": 0.015, "hhv": 1167.021},
    "ngl": {"c1": 0.736, "c2": 0.170, "c3": 0.045, "c4": 0.017, "c5": 0.005, "c6": 0.003, "c7": 0.001,
            "c8": 0.001, "co2": 0.014, "hhv": 1259.711},
    "ot1": {"c1": 0.708, "c2": 0.200, "c3": 0.046, "c4": 0.014, "c5": 0.005, "c6": 0.005, "c7": 0.001,
            "c8": 0.001, "co2": 0.015, "hhv": 1279.908},
    "ot2": {"c1": 0.708, "c2": 0.200, "c3": 0.046, "c4": 0.014, "c5": 0.005, "c6": 0.004, "c7": 0.001,
            "c8": 0.001, "co2": 0.021, "hhv": 1278.036},
}


def gas_inputs(gas):
    """Composition in mol % (the platform's percent basis), remainder to 100 % as N2, HHV in Btu/scf."""
    comp = {k: round(v * 100.0, 4) for k, v in gas.items() if k not in ("hhv", "co2")}
    comp["co2_mol"] = round(gas["co2"] * 100.0, 4)
    comp["n2_mol"] = round(100.0 - sum(comp.values()), 4)
    return {**comp, "composition_basis": "percent", "hhv": gas["hhv"], "hhv_unit": "Btu/scf"}


def _kg_per_mmbtu(key):
    f = EQUIPMENT_FACTORS[key]
    return {"co2": 0, "ch4": f["ch4"] * 1000.0, "n2o": f["n2o"] * 1000.0, "unit": "kg/MMBtu", "type": "gases"}


HEATER = _kg_per_mmbtu("boiler_ng_controlled")      # Table 4-9 low-NOx: CH4 1.0e-3, N2O 2.8e-4 kg/MMBtu
TURBINE = _kg_per_mmbtu("turbine_ng_uncontrolled")  # Table 4-11: CH4 3.9e-3, N2O 1.37e-3 kg/MMBtu


def combustion(volume_nm3, gas, factor):
    return ({"process_type": "combustion", "factor_source": "specific", "amount": volume_nm3, "unit": "Nm3",
             **gas_inputs(gas)}, factor)


def flare(volume_nm3, gas):
    return ({"process_type": "flaring", "factor_source": "specific", "amount": volume_nm3, "unit": "Nm3",
             "destruction_efficiency": 98, "combustion_efficiency": 98, **gas_inputs(gas)}, {})


def diesel_engine(litres, method="equipment"):
    """SANGEA uses the Table 4-11 diesel engine CH4 (TOC x 9 %): the platform's equipment method. The Tier 1 default
    (method="default") takes the stationary Table C-2 CH4 of the fuel row instead (see the test)."""
    if method == "default":
        return ({"process_type": "combustion", "factor_source": "default", "fuel_type": "Diesel (No. 2 Fuel Oil)",
                 "amount": litres, "unit": "l"}, "Diesel (No. 2 Fuel Oil)")
    return ({"process_type": "combustion", "factor_source": "default", "combustion_method": "equipment",
             "equipment_type": "ic_diesel", "amount": litres, "unit": "l"}, {})


# Aviation gasoline has no catalog row: API Compendium 2021 Table 4-5 / EPA Part 98 Table C-1
# (69.25 kg CO2/MMBtu, 0.120 MMBtu/gal); CH4 / N2O are replaced by Table 4-16 through vehicle_type
AVGAS = {"co2": 69.25, "ch4": 0.003, "n2o": 0.0006, "unit": "kg/MMBtu", "hhv": 120000, "type": "liquids"}


def mobile(litres, fuel, vehicle_type):
    fd = AVGAS if fuel == "avgas" else fuel
    return ({"process_type": "mobile", "factor_source": "default", "amount": litres, "unit": "l",
             "vehicle_type": vehicle_type, **({} if fuel == "avgas" else {"fuel_type": fuel})}, fd)


def fire_co2(kg):
    return ({"process_type": "fire_suppression", "factor_source": "default", "agent_type": "co2", "amount": kg,
             "unit": "kg"}, {})


def maint_venting(mmscf, gas):
    """API Compendium Table 6-39 gas-plant non-routine venting per MMscf processed, scaled to the gas CH4 / CO2."""
    return ({"process_type": "non_routine_venting", "factor_source": "default", "activity_key": "proc_non_routine",
             "amount": mmscf, "unit": "MMscf", "ch4_content": gas["c1"] * 100.0, "co2_content": gas["co2"] * 100.0},
            {})


# 1 Sm3 (15 C, as the report's production tables) = 35.3147 scf; HBNS 5,497,258,607 Sm3 = 194,132.66 MMscf, the
# figure Table 7 prints. El Merk's Table 14 prints the same 194,132.66 (copied from HBNS); its venting CH4 (443.89 t)
# is the Table 6-39 factor on El Merk's own gross gas, 3,964,737,224 Sm3 = 140,012 MMscf
SM3_TO_SCF = 35.31466672
HBNS_GAS_MMSCF = 5_497_258_607 * SM3_TO_SCF / 1e6
EMK_GAS_MMSCF = 3_964_737_224 * SM3_TO_SCF / 1e6

# Scope 2 (section 3, Table 4 note 3): IEA 2019 grid factor for Algeria, as implied by Tables 8 / 15
# (57,097.13 t / 136,270 MWh = 0.419 t CO2/MWh; CH4 8.0e-6, N2O 1.0e-6 t/MWh, identical at both sites)
REPORT_GRID = {"co2": 0.4190, "ch4": 8.0e-6, "n2o": 1.005e-6}  # kg per kWh


def P(co2=None, ch4=None, n2o=None, co2e=None):
    return {"co2": co2, "ch4": ch4, "n2o": n2o, "co2e": co2e}


# Tolerances on each printed gas (relative), with the reason where wider than the default
TOL = {"co2": 0.012, "ch4": 0.012, "n2o": 0.02, "co2e": 0.012}
ABS_TOL = 0.005  # t: half the last printed digit of El Merk's 2-decimal small gases


def S(site, module, name, kind, payload=None, printed=None, activity=None, note="", tol=None, skip=()):
    return {"site": site, "module": module, "name": name, "kind": kind, "payload": payload,
            "printed": printed or {}, "activity": activity, "note": note, "tol": {**TOL, **(tol or {})},
            "skip": tuple(skip)}


H, E = "HBNS", "El Merk"
G = EMK_GAS
SOURCES = [
    # ---------------- HBNS, Table 7 activity / Table 8 results ----------------
    S(H, "Stationary Combustion", "Heater 2", "reproduce", combustion(24_359_006.31, HBNS_GAS, HEATER),
      P(70_559.22, 1.237, 0.346, 70_693.33)),
    S(H, "Stationary Combustion", "Heater 3", "reproduce", combustion(23_518_376.81, HBNS_GAS, HEATER),
      P(68_124.22, 1.194, 0.334, 68_253.70)),
    S(H, "Stationary Combustion", "Heater 4", "reproduce", combustion(24_069_698.74, HBNS_GAS, HEATER),
      P(69_721.20, 1.222, 0.342, 69_853.72)),
    S(H, "Stationary Combustion", "Turbine 1", "reproduce", combustion(41_138_229.73, HBNS_GAS, TURBINE),
      P(119_162.55, 8.146, 2.842, 120_213.15)),
    S(H, "Stationary Combustion", "Turbine 2", "reproduce", combustion(38_215_863.77, HBNS_GAS, TURBINE),
      P(110_697.52, 7.567, 2.640, 111_673.48)),
    S(H, "Stationary Combustion", "Turbine 3", "reproduce", combustion(39_804_690.90, HBNS_GAS, TURBINE),
      P(115_299.77, 7.882, 2.750, 116_316.32)),
    S(H, "Stationary Combustion", "SOLAR", "reproduce", combustion(4_043_500.16, HBNS_GAS, TURBINE),
      P(11_712.56, 0.801, 0.279, 11_815.82)),
    S(H, "Stationary Combustion", "GEN 1", "reproduce", combustion(30_946_480.54, HBNS_GAS, TURBINE),
      P(89_640.75, 6.128, 2.138, 90_431.07)),
    S(H, "Stationary Combustion", "GEN 2", "reproduce", combustion(10_792_921.61, HBNS_GAS, TURBINE),
      P(31_263.19, 2.137, 0.746, 31_538.82)),
    S(H, "Stationary Combustion", "Diesel ICE", "reproduce", diesel_engine(399_900.0),
      P(1_073.33, 0.211, 0.009, 1_081.24), tol={"ch4": 0.02},
      note="399.90 m3; CH4 -1.6 %: Table 4-11 diesel engine TOC x 9 % against SANGEA's factor"),
    S(H, "Stationary Combustion", "Flare Purging", "reproduce", combustion(7_127_284.20, HBNS_GAS, HEATER),
      P(20_645.161, 0.362, 0.101, 20_684.40)),
    S(H, "Stationary Combustion", "Blanket Gas", "reproduce", combustion(7_126_100.92, HBNS_GAS, HEATER),
      P(20_641.734, 0.362, 0.101, 20_680.97)),
    S(H, "Stationary Combustion", "Glycol A/B", "reproduce", combustion(7_115_448.63, HBNS_GAS, HEATER),
      P(20_610.878, 0.361, 0.101, 20_650.05)),
    S(H, "Flare", "Flare1 - HP", "reproduce", flare(41_544_753.91, HBNS_GAS), P(117_967.93, 405.761, 1.544, 128_572.19), skip=("n2o", "co2e")),
    S(H, "Flare", "Flare2 - LP", "reproduce", flare(3_627_314.69, HBNS_GAS), P(10_299.90, 35.427, 0.135, 11_225.77), skip=("n2o", "co2e")),
    S(H, "Flare", "Flare3 - AP", "reproduce", flare(2_256_416.09, HBNS_GAS), P(6_407.18, 22.038, 0.084, 6_983.13), skip=("n2o", "co2e")),
    S(H, "Flare", "Flare4 - LT", "reproduce", flare(11_106_481.75, HBNS_GAS), P(31_537.28, 108.475, 0.413, 34_372.20), skip=("n2o", "co2e")),
    S(H, "Flare", "Flare5 - Waterflood", "reproduce", flare(1_859_198.63, HBNS_GAS),
      P(5_279.27, 18.158, 0.069, 5_753.82), skip=("n2o", "co2e")),
    S(H, "Flare", "Flare6 - Glycol VR", "reproduce", flare(3_099_964.67, HBNS_GAS), P(8_802.47, 30.277, 0.115, 9_593.73), skip=("n2o", "co2e")),
    S(H, "Flare", "Field flares (13)", "reproduce", flare(1_111_500.00, HBNS_GAS), P(3_156.15, 10.856, 0.041, 3_439.86), skip=("n2o", "co2e")),
    S(H, "Equipment Leaks", "Leak - Gas Production", "implied", None, P(None, 1.084, None, 27.12),
      note="equipment counts not printed ('Multiple'); Table 8 also prints 13.97 t CO2 in this row, the CO2 of the "
           "CPF gas-processing row, while its CO2e (27.12) is the CH4 alone"),
    S(H, "Equipment Leaks", "Leak - Oil Production", "implied", None, P(12.444, 532.036, None, 13_313.34),
      note="equipment counts not printed"),
    S(H, "Equipment Leaks", "Leak - CPF Gas Processing", "implied", None, P(13.969, 823.437, None, 20_599.89),
      activity=(194_132.66, "MMscf"), note="equipment counts not printed; per MMscf processed"),
    S(H, "Oil & Gas Venting", "Venting - CPF Non-Routine", "reproduce", maint_venting(194_132.66, HBNS_GAS),
      P(12.203, 538.922, None, 13_485.24), tol={"co2": 0.07},
      note="CO2 +6.5 % (0.8 t): Table 6-39 CO2 scaled to the 0.6 % CO2 content differs from SANGEA's CO2 basis"),
    S(H, "Mobile & Transportation", "Aviation", "reproduce", mobile(562_880.0, "avgas", "aviation_gasoline"),
      P(1_238.14, 1.234, 0.129, 1_307.55)),
    S(H, "Mobile & Transportation", "On-Road HD Diesel", "reproduce",
      mobile(19_658.28, "Diesel (No. 2 Fuel Oil)", "hd_diesel_uncontrolled"), P(52.723, 0.003, 0.002, 53.27)),
    S(H, "Mobile & Transportation", "On-Road LD Diesel", "reproduce",
      mobile(113_235.33, "Diesel (No. 2 Fuel Oil)", "lddv_moderate"), P(303.693, 0.008, 0.024, 310.93)),
    S(H, "Mobile & Transportation", "On-Road LD Gasoline", "reproduce",
      mobile(110_665.36, "Motor Gasoline", "ldgv_tier1"), P(261.061, 0.025, 0.053, 277.38),
      tol={"co2": 0.02, "co2e": 0.02},
      note="CO2 -1.7 %: the platform's Table C-1 gasoline (70.22 kg/MMBtu x 0.125 MMBtu/gal = 8.78 kg/gal) "
           "against SANGEA's 8.93 kg/gal"),
    S(H, "Miscellaneous", "Fire Suppressant", "reproduce", fire_co2(619.0), P(0.619, None, None, 0.62)),
    S(H, "Miscellaneous", "STP (aerobic wastewater)", "implied", None, P(11.378, 0.0, 0.024, 18.43),
      activity=(231_696.0, "m3"), note="BOD5 / nitrogen not printed"),
    S(H, "Storage Tank", "Tank - Produced Water", "implied", None, P(None, 63.311, None, 1_582.79),
      activity=(43_355_278.0, "bbl"), note="separator pressure and salt content not printed"),
    S(H, "Indirect (Scope 2)", "Electricity - Imported", "reproduce", ("scope2", 136_270.0),
      P(57_097.13, 1.090, 0.137, 57_165.28), note="Table 7 prints 136,270,00 MWh"),

    # ---------------- El Merk, Table 14 activity / Table 15 results ----------------
    S(E, "Stationary Combustion", "H01 Dehy Regen", "reproduce", combustion(14_749_623.25, G["fuel"], HEATER),
      P(35_528.02, 0.64, 0.18, 35_597.55)),
    S(E, "Stationary Combustion", "H01 NGL Hot Oil Heater", "reproduce", combustion(25_885_862.64, G["fuel"], HEATER),
      P(62_315.67, 1.12, 0.31, 62_437.60)),
    S(E, "Stationary Combustion", "H01 OT1 Hot Oil Heater", "reproduce", combustion(15_539_480.48, G["fuel"], HEATER),
      P(37_443.76, 0.68, 0.19, 37_517.02)),
    S(E, "Stationary Combustion", "IGC1", "reproduce", combustion(32_731_958.47, G["fuel"], TURBINE),
      P(78_536.02, 5.53, 1.93, 79_249.20)),
    S(E, "Stationary Combustion", "IGC2", "reproduce", combustion(34_902_196.84, G["fuel"], TURBINE),
      P(84_297.94, 5.93, 2.07, 85_062.56)),
    S(E, "Stationary Combustion", "IGC3", "reproduce", combustion(36_294_922.21, G["fuel"], TURBINE),
      P(87_337.07, 6.15, 2.15, 88_130.00)),
    S(E, "Stationary Combustion", "RGC1", "reproduce", combustion(46_933_045.60, G["fuel"], TURBINE),
      P(112_471.19, 7.92, 2.76, 113_492.93)),
    S(E, "Stationary Combustion", "RGC2", "reproduce", combustion(32_495_157.78, G["fuel"], TURBINE),
      P(77_822.18, 5.48, 1.91, 78_529.19)),
    S(E, "Stationary Combustion", "Diesel ICE", "reproduce", diesel_engine(1_969_122.0),
      P(5_285.14, 1.04, 0.04, 5_324.07), tol={"ch4": 0.02}),
    S(E, "Flare", "Flare - AP", "reproduce", flare(11_291_502.08, G["fuel"]), P(26_670.68, 125.95, 0.42, 29_944.46), skip=("n2o", "co2e")),
    S(E, "Flare", "Flare - HP", "reproduce", flare(56_782_637.02, G["hp"]), P(145_379.18, 610.03, 2.11, 161_259.10), skip=("n2o", "co2e")),
    S(E, "Flare", "Flare - LP", "reproduce", flare(12_770_729.62, G["lp"]), P(30_164.64, 142.45, 0.47, 33_867.30), skip=("n2o", "co2e")),
    S(E, "Flare", "Flare - NGL", "reproduce", flare(9_578_285.30, G["ngl"]), P(25_071.13, 100.68, 0.36, 27_694.33), skip=("n2o", "co2e")),
    S(E, "Flare", "Flare - OT1", "reproduce", flare(6_983_419.91, G["ot1"]), P(18_637.18, 70.59, 0.26, 20_479.21), skip=("n2o", "co2e")),
    S(E, "Flare", "Flare - OT2", "reproduce", flare(2_948_048.28, G["ot2"]), P(7_845.14, 29.80, 0.11, 8_622.85), skip=("n2o", "co2e")),
    S(E, "Flare", "Flare - PHLT", "reproduce", flare(21_230_769.29, G["hplt"]), P(50_618.00, 234.93, 0.79, 56_726.50), skip=("n2o", "co2e")),
    S(E, "Flare", "Flare-NR - EKT LP", "reproduce", flare(352_420.0, G["lp"]), P(829.57, 3.89, 0.01, 930.78), skip=("n2o", "co2e"),
      tol={"ch4": 0.02}),
    S(E, "Flare", "Flare-NR - EME AP", "reproduce", flare(226_020.0, G["fuel"]), P(531.54, 2.50, 0.01, 596.59), skip=("n2o", "co2e"),
      tol={"ch4": 0.02}),
    S(E, "Flare", "Flare-NR - EMK HP", "reproduce", flare(558_440.0, G["fuel"]), P(1_312.64, 6.17, 0.02, 1_472.95), skip=("n2o", "co2e"),
      tol={"co2": 0.02}, note="its CO2 per Nm3 (2.351 kg) is the fuel-gas composition, not the HP flare stream "
                              "(2.556 kg/Nm3, +8.8 %): SANGEA was given the fuel gas for this well-site flare"),
    S(E, "Flare", "Flare-NR - EMN HPLT", "reproduce", flare(103_900.0, G["hplt"]), P(244.42, 1.15, 0.00, 274.21), skip=("n2o", "co2e"),
      tol={"co2": 0.02}),
    S(E, "Equipment Leaks", "Leak - Gas Production", "implied", None, P(14.45, 289.01, None, 7_239.71),
      note="equipment counts not printed"),
    S(E, "Equipment Leaks", "Leak - Oil Production", "implied", None, P(1.95, 24.17, None, 606.32),
      note="equipment counts not printed"),
    S(E, "Equipment Leaks", "Leak - CPF Gas Processing", "implied", None, P(116.24, 2_494.61, 0.0, 62_481.41),
      activity=(EMK_GAS_MMSCF, "MMscf"), note="equipment counts not printed"),
    S(E, "Oil & Gas Venting", "Non-Routine Venting - CPF", "reproduce", maint_venting(EMK_GAS_MMSCF, G["fuel"]),
      P(22.20, 443.89, None, 11_119.57), tol={"co2": 0.02},
      note="Table 14 prints HBNS's 194,132.66 MMscf; El Merk's own gross gas (140,012 MMscf) is used"),
    S(E, "Mobile & Transportation", "Aviation", "reproduce", mobile(560_902.0, "avgas", "aviation_gasoline"),
      P(1_233.79, 1.23, 0.13, 1_302.95)),
    S(E, "Mobile & Transportation", "On-Road HD Diesel", "reproduce",
      mobile(158_779.0, "Diesel (No. 2 Fuel Oil)", "hd_diesel_uncontrolled"), P(),
      note="Table 15 prints only the on-road total (425.84 t CO2, 430.27 t CO2e)"),
    S(E, "Mobile & Transportation", "On-Road LD Diesel", "reproduce",
      mobile(137_066.0, "Diesel (No. 2 Fuel Oil)", "lddv_moderate"), P(), note="part of the on-road total"),
    S(E, "Mobile & Transportation", "On-Road LD Gasoline", "reproduce",
      mobile(98_340.0, "Motor Gasoline", "ldgv_tier1"), P(), note="part of the on-road total"),
    S(E, "Miscellaneous", "Fire Suppressant CO2", "reproduce", fire_co2(1_219.92), P(1.22, 0.0, 0.0, 1.22)),
    S(E, "Miscellaneous", "STP (aerobic wastewater)", "implied", None, P(8.28, 0.0, None, 9.67),
      activity=(73_952.70, "m3"),
      note="no STP row in Table 15: module total (9.50 t CO2, 10.89 t CO2e) minus the fire suppressant"),
    S(E, "Storage Tank", "Tank - Produced Water", "implied", None, P(None, 11.42, None, 285.47),
      activity=(1_243_186.72 * 6.28981077, "bbl"), note="1,243,186.72 m3; separator pressure not printed"),
    S(E, "Indirect (Scope 2)", "Electricity - Imported", "reproduce", ("scope2", 338_255.0),
      P(141_728.84, 2.71, 0.34, 141_898.00)),
]

# El Merk on-road total (Table 15 prints one row for the three vehicle types)
EMK_ONROAD_PRINTED = P(425.84, 0.02, 0.01, 430.27)

# Tables 9 / 16 (module totals, t CO2e) and site totals
MODULE_TOTALS = {
    H: {"Stationary Combustion": 753_886.06, "Flare": 199_940.70, "Equipment Leaks": 33_940.36,
        "Oil & Gas Venting": 13_485.24, "Mobile & Transportation": 1_949.13, "Storage Tank": 1_582.79,
        "Miscellaneous": 19.05, "Indirect (Scope 2)": 57_165.28},
    E: {"Stationary Combustion": 585_340.12, "Flare": 341_868.29, "Equipment Leaks": 70_327.44,
        "Oil & Gas Venting": 11_119.57, "Mobile & Transportation": 2_356.07, "Storage Tank": 285.47,
        "Miscellaneous": 10.89, "Indirect (Scope 2)": 141_898.00},
}
SITE_TOTALS = {H: {"co2": 991_605.63, "ch4": 2_629.75, "n2o": 15.50, "co2e": 1_061_968.60,
                   "scope1": 1_004_803, "scope2": 57_165},
               E: {"co2": 1_032_493.53, "ch4": 4_629.72, "n2o": 16.68, "co2e": 1_153_205.84,
                   "scope1": 1_011_308, "scope2": 141_898}}

# Tables 5 / 12 / E-4 / E-5: production and intensities
PRODUCTION = {
    H: {"gas_sm3": 5_497_258_607, "gas_boe": 45_620_171, "gas_no_inj_sm3": 808_062_863, "gas_no_inj_boe": 6_705_988,
        "liquids_boe": 26_563_246, "total_boe": 72_183_417, "total_no_inj_boe": 33_269_234,
        "saleable_mmboe": 30.453, "energy_mmbtu": 13_591_542, "co2e_per_boe": 0.0147, "energy_per_boe": 0.1883,
        "flare_mmsm3": 68.146, "flaring_sm3_per_boe": 0.944, "ngsi_pct": 0.141, "hhv": 1362.97},
    E: {"gas_sm3": 3_964_737_224, "gas_boe": 28_104_493, "gas_no_inj_sm3": 380_953_872, "gas_no_inj_boe": 2_712_420,
        "liquids_boe": 32_604_976, "total_boe": 60_709_469, "total_no_inj_boe": 35_317_396,
        "saleable_mmboe": 32.605, "energy_mmbtu": 11_618_572, "co2e_per_boe": 0.0190, "energy_per_boe": 0.1914,
        "flare_mmsm3": 129.556, "flaring_sm3_per_boe": 2.134, "ngsi_pct": 0.176, "hhv": 1167.69},
}

# Tables 11 / 18: equity shares 2022 (%) and CO2e by equity share
EQUITY = {
    H: {"Sonatrach": (44.0, 467_266.18), "Occidental": (21.2, 225_137.34), "Eni": (24.2, 256_996.40),
        "TotalEnergies": (10.6, 112_568.67)},
    E: {"Sonatrach": (46.6, 537_393.92), "Occidental": (22.4, 258_318.11), "Eni": (11.2, 129_159.05),
        "TotalEnergies": (11.2, 129_159.05), "Pertamina": (5.6, 64_579.53), "Talisman": (3.0, 34_596.18)},
}


def run_source(src, gwp_dict):
    """Run one source through the platform: compute_emissions for Scope 1, the Scope 2 grid arithmetic for
    electricity. Returns {co2, ch4, n2o, co2e} in tonnes."""
    payload = src["payload"]
    if payload[0] == "scope2":
        from electricity_factors import grid_factor_kg_co2e_per_kwh
        kwh = payload[1] * 1000.0
        co2e = kwh * grid_factor_kg_co2e_per_kwh(REPORT_GRID, gwp=gwp_dict) / 1000.0
        return {"co2": kwh * REPORT_GRID["co2"] / 1000.0, "ch4": kwh * REPORT_GRID["ch4"] / 1000.0,
                "n2o": kwh * REPORT_GRID["n2o"] / 1000.0, "co2e": co2e}
    from calculations import compute_emissions
    p, factor = payload
    if isinstance(factor, str):
        from emission_factors import API_FACTORS
        factor = dict(API_FACTORS[factor])
    em, _ = compute_emissions(dict(p), dict(factor), gwp_dict=gwp_dict)
    return {"co2": float(em.get("co2") or 0), "ch4": float(em.get("ch4") or 0), "n2o": float(em.get("n2o") or 0),
            "co2e": float(em.get("totalCo2e") or em.get("total_co2e") or 0)}
