"""API Compendium 2021 worked examples (Exhibits) run through the engine — the same path as
POST /api/emissions (resolve_factor + compute_emissions). Expected values are the exhibits'
printed results; inputs as the exhibits state them. Exhibit answers were read from
scratch/2021-API-GHG-Compendium.pdf (pdftotext). Exhibit 6-11 is excluded: its text says CO2
comes from the whole-gas factor (2.6 scf/h) but its arithmetic uses 2.1 (the CH4-basis value);
the engine follows the stated method.
"""
import json
import math

import pytest

from calculations.constants import get_active_gwp
from calculations.legacy_engine import compute_emissions
from services.scope1_calc import resolve_factor

CASES = []


def case(ex, title, payload, expect, tol=0.02, note=""):
    CASES.append(pytest.param(payload, expect, tol, id=f"{ex} {title}"))


def ci(process, tier_src, amount, unit, fuel=None, **inputs):
    p = {"process_type": process, "factor_source": tier_src, "amount": amount, "quantity": amount, "unit": unit,
         "calc_inputs": {process: {"amount": amount, "unit": unit, **inputs}}}
    if fuel:
        p["fuel"] = p["fuel_type"] = fuel
        p["calc_inputs"][process]["fuel"] = fuel
    p.update({k: v for k, v in inputs.items() if k in ("hhv", "density", "combustion_efficiency", "location_type", "well_location")})
    return p

# Exhibit cases: inputs as stated in the API Compendium 2021 exhibit, expected = the exhibit's printed result
# (tonnes). Units exactly as the exhibit gives them.

# 4.2 / 4.4 natural gas: 800e6 scf at HHV 1020 Btu/scf = 8.16e11 Btu (Exhibit 4.2); fuel-basis CO2 with
# Table 4-3 NG factor 53.06 kg/MMBtu -> 816,000 MMBtu x 0.05306 = 43,297 t (derived from 4.2's energy)
case("4.2", "Natural gas 800e6 scf, default HHV (Tier 1)",
     ci("combustion", "default", 800e6, "scf", fuel="Natural Gas"),
     {"co2": 816000 * 0.05306}, note="energy input per Exhibit 4.2; CO2 = energy x Table 4-3 factor (derived)")

# 4.4(a): composition known, 100 % oxidation (Eq 4-11). Answer not extractable from the PDF text ->
# derived: 800e6/379.3 lbmol x 1.014 lbmol C/lbmol (CO2 0.8, CH4 95.3, C2 1.7, C3 0.5, C4 0.1) x 44 / 2204.62
case("4.4a", "Natural gas 800e6 scf, known composition (Tier 3)",
     ci("combustion", "specific", 800e6, "scf", fuel="Natural Gas", hhv=1020, combustion_efficiency=100,
        c1=95.3, c2=1.7, c3=0.5, c4=0.1, co2_content=0.8, n2_content=1.6),
     {"co2": 800e6 / 379.3 * 1.014 * 44 / 2204.62}, note="expected derived with Eq 4-11 (exhibit answer not in extracted text)")

# 4.6: 4e6 gal No. 6 residual, Table 4-3 / 3-8 defaults -> CO2 44,984; CH4 1.80; N2O 0.36
case("4.6", "Residual fuel oil No. 6, 4e6 gal (Tier 1)",
     ci("combustion", "default", 4e6, "gal", fuel="Residual Fuel Oil (No. 6)"),
     {"co2": 44984, "ch4": 1.80, "n2o": 0.36})

# 4.13: 275,498 m3 marine diesel -> CO2 742,580
case("4.13", "Marine diesel 275,498 m3 (fuel basis)",
     ci("mobile", "default", 275498, "m3", fuel="Marine Diesel Oil"),
     {"co2": 742580})

# 5.1: flare 20e6 scf; 12 % CO2, 2.1 % N2, 80 % CH4, 4.2 % C2, 1.3 % C3, 0.4 % C4; 98 % combustion
case("5.1", "Gas flare, known volume and composition",
     ci("flaring", "specific", 20e6, "scf", fuel="Natural Gas", hhv=1020, c1=80, c2=4.2, c3=1.3, c4=0.4,
        co2_content=12, n2_content=2.1, combustion_efficiency=98, destruction_efficiency=98),
     {"ch4": 6.1, "co2": 1095})

# 6-1: 85 drilling days, water-based mud, 70 % CH4, 9 % CO2 -> CH4 18.49, CO2 6.54 (factor 0.2605 t/day)
case("6-1", "Mud degassing 85 days, water-based (Tier 2+)",
     {"process_type": "drilling", "factor_source": "tier2_plus", "amount": 85, "unit": "days",
      "calc_inputs": {"drilling": {"amount": 85, "unit": "days", "drilling_days": 85, "mud_type": "water_based",
                                   "tier": "tier2_plus", "ch4_fraction": 0.70, "co2_fraction": 0.09, "well_location": "offshore"}}},
     {"ch4": 18.49, "co2": 6.54}, note="exhibit uses 0.2605 t CH4/day (Table 6-2 value the engine holds as offshore)")

# 6-3: HF gas well; metered to flare 1.48e6 scf over 20 h; 4 h unmetered venting; N2 7,390 scf; 70 % CH4;
# flare 98 % -> vented CH4 1.97, flared CO2 98.7, flared CH4 0.39 -> CH4 total 2.36
case("6-3", "Completion with HF, metered flowback to flare (Tier 3)",
     {"process_type": "completions", "factor_source": "specific", "amount": 1, "unit": "events",
      "calc_inputs": {"completions": {"tier": "tier3", "calc_method": "metered", "comp_volume": 1480000, "volume_unit": "scf",
                                      "comp_injected_n2": 7390, "comp_injected_n2_unit": "scf",
                                      "comp_initial_flowback_hours": 4, "comp_duration": 20,
                                      "comp_ch4_content": 70, "comp_c2plus_content": 30, "comp_disposition": "flared", "comp_flare_eff": 98,
                                      "events": 1}}},
     {"ch4": 1.97 + 0.39, "co2": 98.7})

# 6-6: continuous associated gas venting: GOR 700 scf/bbl, 5,200 bbl/day, 365 d, 70 % CH4, 10 % CO2
case("6-6", "Associated gas venting, GOR balance (Tier 2)",
     {"process_type": "associated_gas_venting", "factor_source": "custom", "amount": 5200, "unit": "bbl/day",
      "calc_inputs": {"associated_gas_venting": {"tier": "tier2", "oil_production": 5200, "oil_unit": "bbl/day",
                                                 "gor": 700, "gor_unit": "scf/bbl", "venting_duration": 365,
                                                 "duration_unit": "days", "period_duration": 365, "ch4_content": 70,
                                                 "co2_content": 10}}},
     {"ch4": 17795, "co2": 6991})

# 6-8: unloading Eq 6-10: 12 events, 10 in, 12,000 ft, 250 psig, SFR 35,000 scf/h, HR 1 h, non-plunger
case("6-8", "Liquids unloading, Eq 6-10 (Tier 3)",
     {"process_type": "unloading", "factor_source": "specific", "amount": 12, "unit": "events",
      "calc_inputs": {"unloading": {"tier": "tier3", "calc_method": "api_equation_6_10", "unload_events": 12,
                                    "unload_diam": 10, "unload_depth": 12000, "unload_press": 250, "sfr": 35000,
                                    "hours_open": 1, "unloading_type": "non_plunger", "unload_type": "non_plunger",
                                    "ch4_content": 80, "co2_content": 3}}},
     {"ch4": 20.39, "co2": 2.10})

# 6-11: 80 low-bleed controllers, API factor (2.6 scf gas/h; 2.1 scf CH4/h at 81.6 %), 70 % CH4, 9 % CO2
case("6-11", "Pneumatic low-bleed controllers x80 (Table 6-14)",
     {"process_type": "pneumatic", "factor_source": "default", "amount": 80, "unit": "devices",
      "pneu_controller_type": "low_bleed",
      "calc_inputs": {"pneumatic": {"amount": 80, "pneu_controller_type": "low_bleed", "pneu_hours": 8760,
                                    "ch4_content": 70, "pneu_co2_content": 9}}},
     {"ch4": 24.2, "co2": 7.0}, note="exhibit text: CO2 from the WHOLE-GAS factor (2.6 scf/h) but its arithmetic uses 2.1 (the CH4-basis value); engine follows the stated method")

# 6-12: monitoring survey: 76 normal all year + 4 normal 0.75 / malfunctioning 0.25; 70 % CH4, 9 % CO2
case("6-12", "Intermittent controllers, monitoring survey (Eq 6-14)",
     {"process_type": "pneumatic", "factor_source": "specific", "amount": 80, "unit": "devices",
      "calc_inputs": {"pneumatic": {"amount": 80, "pneu_monitoring": "true", "pneu_normal_count": 79,
                                    "pneu_normal_fraction": 1.0, "pneu_malfunction_count": 4,
                                    "pneu_malfunction_fraction": 0.25, "ch4_content": 70, "pneu_co2_content": 9}}},
     {"ch4": 5.41, "co2": 1.91})

# 6-13: glycol dehydrator 25 MMscf/d, electric pump, no flash, 82 % CH4 -> 50.2 t CH4 (Table 6-17)
case("6-13", "Glycol dehydrator vent, throughput factor (Table 6-17)",
     {"process_type": "dehydrator", "factor_source": "specific", "amount": 25 * 365, "unit": "MMscf/yr",
      "calc_inputs": {"dehydrator": {"dehy_throughput": 25 * 365, "dehy_ch4_content": 82, "dehy_has_flash": "false"}}},
     {"ch4": 50.2})

# 6-19: tank flashing, GOR chart 47 scf/bbl, 451 bbl/d, 27.4 % CH4 in flash gas -> 40.6
case("6-19", "Tank flashing, GOR 47 scf/bbl (Tier 3)",
     ci("tank_flashing", "specific", 451 * 365, "bbl", tank_gor=47, tank_ch4_content=27.4),
     {"ch4": 40.6})

# 6-20: large tank uncontrolled, Table 6-22: 451 bbl/d x 365 x 0.193 kg/bbl -> 31.8 (not composition-adjusted)
case("6-20", "Tank flashing, Table 6-22 large uncontrolled",
     ci("tank_flashing", "default", 451 * 365, "bbl"),
     {"ch4": 31.8})

# 6-21: produced water 50 bbl/d, salt unknown, 250 psi -> 0.26
case("6-21", "Produced water tank (Table 6-26)",
     ci("tank_flashing", "specific", 50 * 365, "bbl", tank_liquid_type="produced_water"),
     {"ch4": 0.26})

# 6-25: blowdown 83.8 ft3 at 100 psig, 80 F, z 0.9864, 90 % CH4 -> 0.011
case("6-25", "Equipment blowdown, gas law (Eq 6-32)",
     {"process_type": "blowdown", "factor_source": "specific", "amount": 83.8, "unit": "scf",
      "calc_inputs": {"blowdown": {"blowdown_volume": 83.8, "blowdown_unit": "scf", "blowdown_pressure": 100,
                                   "blowdown_events": 1, "ch4_content": 90, "blowdown_temp": 80, "z_factor": 0.9864}}},
     {"ch4": 0.011}, tol=0.03)

# 6-44: hydrogen 13,000e6 scf H2 x 13.41 t/1e6 scf
case("6-44", "Hydrogen plant, simple factor (Table 6-51)",
     {"process_type": "hydrogen_production", "factor_source": "default", "amount": 13000e6, "unit": "scf",
      "calc_inputs": {"hydrogen_production": {"h2_produced_scf": 13000e6}}},
     {"co2": 174300}, tol=0.005)

# 6-45: asphalt 100,000 tons x Table 6-52 (5.61E-3 t CO2/ton, 3.07E-3 t CH4/ton) -> 561 / 307
case("6-45", "Asphalt blowing 100,000 tons (Table 6-52)",
     ci("asphalt_blowing", "default", 100000, "ton", fuel="Asphalt"),
     {"co2": 561, "ch4": 307})

# 7-4: onshore gas equipment (Table 7-10), 8,760 h: 15 wellheads -> 2.36; 4 separators -> 1.55; 1 heater -> 0.40
for n, name, key, exp in ((15, "wellheads", "Wellhead - Gas", 2.36), (4, "separators", "Separator - Gas Production", 1.55),
                          (1, "heater", "Heater - Gas Production", 0.40)):
    case("7-4", f"Onshore gas equipment: {n} {name} (Table 7-10)",
         {"process_type": "fugitive", "factor_source": "custom", "fuel": key, "amount": n, "unit": "count",
          "calc_inputs": {"fugitive": {"fugitive_tier": "tier2", "fugitive_method": "equipment", "equipment_count": n,
                                       "amount": n, "fuel": key, "operating_hours": 8760}}},
         {"ch4": exp})

# 6-42 / 6-43 hydrogen plant, rigorous: feed 85 % CH4, 8 % C2H6, 3 % C4H10, 4 % N2
case("6-42", "Hydrogen plant, feedstock carbon balance (Eq 6-49)",
     {"process_type": "hydrogen_production", "factor_source": "default", "amount": 5e9, "unit": "scf",
      "calc_inputs": {"hydrogen_production": {"feedstock_scf": 5e9, "feed_ch4": 85, "feed_c2h6": 8, "feed_c4h10": 3, "feed_n2": 4}}},
     {"co2": 297100}, tol=0.01)
case("6-43", "Hydrogen plant, H2 stoichiometry (Eq 6-50)",
     {"process_type": "hydrogen_production", "factor_source": "default", "amount": 13e9, "unit": "scf",
      "calc_inputs": {"hydrogen_production": {"h2_produced_scf": 13e9, "feed_ch4": 85, "feed_c2h6": 8, "feed_c4h10": 3, "feed_n2": 4}}},
     {"co2": 177800}, tol=0.01)


CASES = [c for c in CASES if not c.id.startswith("6-11 ")]


@pytest.mark.parametrize("payload,expect,tol", CASES)
def test_exhibit(app, payload, expect, tol):
    with app.app_context():
        p = json.loads(json.dumps(payload))
        em, _ = compute_emissions(p, resolve_factor(p) or {}, gwp_dict=get_active_gwp(standard="AR5"))
        for gas, exp in expect.items():
            assert float(em.get(gas) or 0) == pytest.approx(exp, rel=tol), gas


# every catalog factor gives the same result for equivalent quantities in different units
FT3_PER_M3, L_PER_GAL, KG_PER_TON = 35.3146667, 3.785411784, 907.18474
GAS = {"m3": 1000.0, "scf": 1000.0 * FT3_PER_M3, "Mcf": 1000.0 * FT3_PER_M3 / 1e3, "MMscf": 1000.0 * FT3_PER_M3 / 1e6}
LIQ = {"gal": 1000.0, "bbl": 1000.0 / 42.0, "L": 1000.0 * L_PER_GAL, "m3": 1000.0 * L_PER_GAL / 1000.0}
MASS = {"kg": 1000.0, "tonne": 1.0, "ton": 1000.0 / KG_PER_TON}


@pytest.mark.parametrize("process,fuel,units,gas,expected", [
    ("combustion", "Natural Gas", GAS, "co2", 1000.0 * FT3_PER_M3 * 1020 / 1e6 * 53.06 / 1000),
    ("combustion", "Ethane (Gas)", GAS, "co2", 1000.0 * FT3_PER_M3 * 1768.8 / 1e6 * 59.60 / 1000),
    ("combustion", "Diesel (No. 2 Fuel Oil)", LIQ, "co2", 1000.0 * 138000 / 1e6 * 73.96 / 1000),
    ("combustion", "Residual Fuel Oil (No. 6)", LIQ, "co2", 1000.0 * 150000 / 1e6 * 75.1 / 1000),
    ("asphalt_blowing", "Asphalt", MASS, "ch4", 1000.0 / KG_PER_TON * 3.07 / 1000),
])
def test_equivalent_units_agree(app, process, fuel, units, gas, expected):
    with app.app_context():
        for unit, qty in units.items():
            p = {"process_type": process, "factor_source": "default", "fuel": fuel, "fuel_type": fuel,
                 "amount": qty, "quantity": qty, "unit": unit,
                 "calc_inputs": {process: {"amount": qty, "unit": unit, "fuel": fuel}}}
            em, _ = compute_emissions(p, resolve_factor(p) or {}, gwp_dict=get_active_gwp(standard="AR5"))
            assert float(em[gas]) == pytest.approx(expected, rel=2e-3), unit


@pytest.mark.parametrize("fuel,unit", [("Natural Gas", "gal"), ("Diesel (No. 2 Fuel Oil)", "scf"),
                                       ("Diesel (No. 2 Fuel Oil)", "kg"), ("Ethane (Gas)", "gal")])
def test_wrong_dimension_rejected(app, fuel, unit):
    with app.app_context():
        p = {"process_type": "combustion", "factor_source": "default", "fuel": fuel, "fuel_type": fuel,
             "amount": 1000, "quantity": 1000, "unit": unit,
             "calc_inputs": {"combustion": {"amount": 1000, "unit": unit, "fuel": fuel}}}
        with pytest.raises(Exception):
            compute_emissions(p, resolve_factor(p) or {}, gwp_dict=get_active_gwp(standard="AR5"))
