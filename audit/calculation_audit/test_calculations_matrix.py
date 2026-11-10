"""
Comprehensive Calculation Matrix Audit
Tests all core calculation engines against the independent oracle, boundary values,
and analyzes tautological assertions in test suites.
"""

import sys
import os
import math
from decimal import Decimal

sys.path.insert(0, "new/server")

from calculations.stoichiometry import StoichiometricCalculator
from calculations.combustion import FlaringCalculator, CombustionCalculator
from calculations.indirect import IndirectSteamCalculator, CogenAllocationCalculator
from calculations.units import CONVERSIONS, calculate_co2e
from calculations.dispatcher import CalculationDispatcher
from calculations.constants import GWP_STANDARDS

from independent_oracle import (
    oracle_stoichiometric_co2,
    oracle_flaring_emissions,
    oracle_indirect_steam,
    oracle_co2e,
    DENSITY_CH4_STD,
    DENSITY_CO2_STD,
)

findings = []

def record(f_id, file_line, severity, category, title, expected, actual, repro, confidence):
    findings.append({
        "id": f_id,
        "file_line": file_line,
        "severity": severity,
        "category": category,
        "title": title,
        "expected": expected,
        "actual": actual,
        "repro": repro,
        "confidence": confidence
    })
    print(f"[{severity.upper()}] {f_id}: {title} ({file_line})")


def get_val(res, key):
    if "results" in res and key in res["results"]:
        sub = res["results"][key]
        return sub["value"] if isinstance(sub, dict) else sub
    if key in res:
        sub = res[key]
        return sub["value"] if isinstance(sub, dict) else sub
    return 0.0

# 1. Stoichiometric Calculator vs Oracle
print("\n--- Testing Stoichiometric Calculator vs Oracle ---")
stoich_calc = StoichiometricCalculator()
test_mass_kg = 5000.0
test_carbon = 0.85
test_ox = 0.99

app_res = stoich_calc.calculate(fuel_mass=test_mass_kg, carbon_content=test_carbon, oxidation_factor=test_ox)
app_co2 = get_val(app_res, "co2")

oracle_co2 = float(oracle_stoichiometric_co2(
    Decimal(str(test_mass_kg)),
    Decimal(str(test_carbon)),
    Decimal(str(test_ox))
))

diff = abs(app_co2 - oracle_co2)
rel_err = diff / oracle_co2
print(f"Stoichiometric CO2: App={app_co2:.6f} t, Oracle={oracle_co2:.6f} t, Diff={diff:.2e}, RelErr={rel_err:.2e}")
if rel_err > 1e-4:
    record("CALC-01", "new/server/calculations/stoichiometry.py:78", "Medium", "Calculation Correctness",
           "Stoichiometric calculation discrepancy against API Compendium",
           f"CO2 = {oracle_co2:.6f} t", f"CO2 = {app_co2:.6f} t",
           f"stoich_calc.calculate(5000, 0.85, oxidation_factor=0.99)", "Confirmed")

# Stoichiometric Boundary: Negative mass
try:
    stoich_calc.calculate(fuel_mass=-100.0, carbon_content=0.85)
    record("CALC-02", "new/server/calculations/stoichiometry.py:56", "Medium", "Input Validation",
           "Stoichiometric calculator allows negative fuel mass",
           "Raise ValueError for negative fuel mass", "Calculation proceeded without error",
           "stoich_calc.calculate(-100.0, 0.85)", "Confirmed")
except Exception as e:
    print(f"Negative mass correctly caught: {e}")

# Stoichiometric Boundary: Carbon content > 100%
try:
    stoich_calc.calculate(fuel_mass=100.0, carbon_content=1.5)
    record("CALC-03", "new/server/calculations/stoichiometry.py:66", "Medium", "Input Validation",
           "Stoichiometric calculator allows carbon content > 1.0",
           "Raise ValueError for carbon content > 1.0", "Calculation proceeded without error",
           "stoich_calc.calculate(100.0, 1.5)", "Confirmed")
except Exception as e:
    print(f"Carbon content > 1.0 correctly caught: {e}")


# 2. Flaring Calculator vs Oracle & Unit Conversion
print("\n--- Testing Flaring Calculator vs Oracle ---")
flare_calc = FlaringCalculator()
vol_std_m3 = 10000.0  # 10,000 m3
test_comps = {
    "c1": 0.85,
    "c2": 0.05,
    "c3": 0.03,
    "c4": 0.02,
    "co2": 0.02,
    "n2": 0.03,
}
eta_c = 0.98
eta_d = 0.98

app_flare = flare_calc.calculate(
    gas_volume=vol_std_m3,
    ch4_fraction=0.85,
    flare_type="steam_assisted",
    uncertainties={},
    fuel_unit="m3",
    combustion_efficiency=eta_c,
    destruction_efficiency=eta_d,
    **test_comps
)

app_co2 = get_val(app_flare, "co2")
app_ch4 = get_val(app_flare, "ch4")
app_n2o = get_val(app_flare, "n2o")

oracle_flare = oracle_flaring_emissions(
    vol_std_m3=Decimal(str(vol_std_m3)),
    comp_mol_fractions={k: Decimal(str(v)) for k, v in test_comps.items()},
    eta_combustion=Decimal(str(eta_c)),
    eta_destruction=Decimal(str(eta_d)),
)
oracle_co2 = float(oracle_flare["co2_tonnes"])
oracle_ch4 = float(oracle_flare["ch4_tonnes"])
oracle_n2o = float(oracle_flare["n2o_tonnes"])

print(f"Flaring CO2: App={app_co2:.6f} t, Oracle={oracle_co2:.6f} t, Diff={abs(app_co2 - oracle_co2):.2e}")
print(f"Flaring CH4: App={app_ch4:.6f} t, Oracle={oracle_ch4:.6f} t, Diff={abs(app_ch4 - oracle_ch4):.2e}")
print(f"Flaring N2O: App={app_n2o:.6f} t, Oracle={oracle_n2o:.6f} t, Diff={abs(app_n2o - oracle_n2o):.2e}")

# Flaring N2O HHV Unit Bug
print("\n--- Testing Flaring N2O HHV Unit Handling ---")
# When HHV is entered in btu/m3:
# For natural gas, HHV is ~36,000 to 40,000 kJ/m3 = ~36,000 to 40,000 / 1.055 = ~34,000 to 38,000 Btu/m3
# But lines 623-633 in combustion.py only check: mj/m3, gj/m3, kj/m3, mmbtu/mscf, mmbtu/scf.
# If hhv_u == "btu/m3", it does NOT convert, treating 36,000 as 36,000 Btu/scf (instead of ~1,020 Btu/scf)!
flare_res_btu_m3 = flare_calc.calculate(
    gas_volume=1000.0,
    ch4_fraction=0.95,
    flare_type="steam_assisted",
    uncertainties={},
    fuel_unit="m3",
    hhv=36000.0,
    hhv_unit="btu/m3",
    ef_n2o=0.0001,
    ef_unit="kg/mmbtu",
    c1=0.95,
    co2=0.05
)
n2o_btu_m3 = get_val(flare_res_btu_m3, "n2o")

# If correctly converted: 36,000 Btu/m3 * 1,000 m3 = 36,000,000 Btu = 36 MMBtu.
# With EF 0.0001 kg/MMBtu -> 36 * 0.0001 = 0.0036 kg = 0.0000036 tonnes.
# But with the bug: vol_scf = 1000 * 35.3147 = 35,314.7 scf.
# flared_mmbtu = 35314.7 * 36000 / 1e6 = 1,271.3 MMBtu (35.3x higher)!
# n2o_tonnes = 1271.3 * 0.0001 / 1000 = 0.0001271 tonnes.
exp_n2o_correct = (1000.0 * 36000.0 / 1e6) * 0.0001 / 1000.0
print(f"Flaring N2O with hhv_unit='btu/m3': Got {n2o_btu_m3:.8f} t, Expected {exp_n2o_correct:.8f} t (Ratio: {n2o_btu_m3 / exp_n2o_correct:.2f}x)")

if abs(n2o_btu_m3 - exp_n2o_correct) > 1e-7:
    record(
        "CALC-04",
        "new/server/calculations/combustion.py:623-633",
        "High",
        "Calculation Correctness",
        "Flaring N2O calculation ignores 'btu/m3' HHV unit, causing ~35.3x overestimation",
        f"N2O = {exp_n2o_correct:.8f} tonnes (flared energy 36 MMBtu)",
        f"N2O = {n2o_btu_m3:.8f} tonnes (treated as 36,000 Btu/scf, flared energy 1,271 MMBtu)",
        "flare_calc.calculate(gas_volume=1000, hhv=36000, hhv_unit='btu/m3', ef_n2o=0.0001, ef_unit='kg/mmbtu')",
        "Confirmed"
    )


# 3. Indirect Steam / Heat Net Efficiency Bug
print("\n--- Testing Indirect Steam Net Efficiency Calculation ---")
indirect_calc = IndirectSteamCalculator()

# Test case 1: Normal values (b_eff = 0.80, t_loss = 0.10)
# Correct thermodynamics: net_eff = 0.80 * (1 - 0.10) = 0.72
# App implementation: net_eff = 0.80 - 0.10 = 0.70
# Relative error: 0.70 vs 0.72 -> emissions are (1/0.70) / (1/0.72) = 1.4285 / 1.3888 = ~2.86% overestimated
ind_res = indirect_calc.calculate(
    heat_energy=100.0,  # 100 MMBtu
    heat_unit="mmbtu",
    ef_co2=53.06,       # kg/MMBtu
    boiler_efficiency=0.80,
    transmission_loss=0.10,
    uncertainties={}
)
app_co2_ind = get_val(ind_res, "co2")

# Correct thermodynamic emission: 100 / (0.80 * 0.90) * 53.06 / 1000 = 7.3694 tonnes
exp_co2_mult = float(oracle_indirect_steam(Decimal("100.0"), Decimal("53.06"), Decimal("0.80"), Decimal("0.10"), mode="multiplicative")["co2_tonnes"])
# App subtractive emission: 100 / 0.70 * 53.06 / 1000 = 7.5800 tonnes
exp_co2_sub = float(oracle_indirect_steam(Decimal("100.0"), Decimal("53.06"), Decimal("0.80"), Decimal("0.10"), mode="subtractive")["co2_tonnes"])

print(f"Indirect Steam CO2: App={app_co2_ind:.4f} t, Multiplicative Oracle={exp_co2_mult:.4f} t, Subtractive={exp_co2_sub:.4f} t")

# Test case 2: Transmission loss >= boiler efficiency
# e.g., b_eff = 0.50, t_loss = 0.50
# With subtractive: net_eff = 0.50 - 0.50 = 0.0 -> raises ValueError: Net efficiency must be greater than 0
# But physically, delivering 50% through a 50% loss system has net efficiency 0.50 * 0.50 = 0.25 (25%)!
try:
    indirect_calc.calculate(
        heat_energy=100.0,
        heat_unit="mmbtu",
        ef_co2=53.06,
        boiler_efficiency=0.50,
        transmission_loss=0.50,
        uncertainties={}
    )
    print("b_eff=0.50, t_loss=0.50 did not raise")
except ValueError as e:
    print(f"b_eff=0.50, t_loss=0.50 raised: {e}")
    record(
        "CALC-05",
        "new/server/calculations/indirect.py:95",
        "High",
        "Calculation Correctness",
        "Indirect steam net efficiency uses subtraction (b_eff - t_loss) instead of multiplication (b_eff * (1 - t_loss)), causing systematic bias and false fatal errors",
        "Physical net efficiency = b_eff * (1 - t_loss) = 0.25, CO2 = 21.22 tonnes",
        f"Calculates net_efficiency = 0.50 - 0.50 = 0.0, raises fatal ValueError: '{e}'",
        "indirect_calc.calculate(heat_energy=100, heat_unit='mmbtu', ef_co2=53.06, boiler_efficiency=0.50, transmission_loss=0.50)",
        "Confirmed"
    )


# 4. Cogeneration Allocation Calculator
print("\n--- Testing Cogeneration Allocation Calculator ---")
cogen_calc = CogenAllocationCalculator()
# Total emissions = 1000 tonnes, heat = 500 MMBtu, power = 500 MMBtu
cogen_res = cogen_calc.calculate(
    total_emissions=1000.0,
    heat_output=500.0,
    power_output=500.0,
    method="wri_efficiency",
    heat_efficiency=0.80,
    power_efficiency=0.35,
    uncertainties={}
)
allocated_heat = cogen_res["metadata"]["allocated_heat_tonnes"]
allocated_power = cogen_res["metadata"]["allocated_power_tonnes"]
print(f"Cogen Allocation: Total=1000 t, Heat={allocated_heat:.2f} t, Power={allocated_power:.2f} t")

# Sum of allocations must equal total emissions
sum_alloc = allocated_heat + allocated_power
diff_alloc = abs(sum_alloc - 1000.0)
if diff_alloc > 1e-4:
    record(
        "CALC-06",
        "new/server/calculations/indirect.py:201-202",
        "High",
        "Calculation Correctness",
        "Cogeneration allocation does not conserve total emissions",
        "allocated_heat + allocated_power == total_emissions (1000.0 t)",
        f"Sum of allocations = {sum_alloc:.4f} t",
        "cogen_calc.calculate(1000, 500, 500, method='wri_efficiency', heat_efficiency=0.8, power_efficiency=0.35)",
        "Confirmed"
    )
else:
    print(f"Cogen allocation conservation passed: sum = {sum_alloc:.4f}")

# Cogen allocation with zero outputs
try:
    cogen_zero = cogen_calc.calculate(
        total_emissions=1000.0,
        heat_output=0.0,
        power_output=0.0,
        method="wri_efficiency",
        uncertainties={}
    )
    print(f"Cogen zero outputs handled: {cogen_zero['metadata']}")
except Exception as e:
    record(
        "CALC-07",
        "new/server/calculations/indirect.py:201",
        "Medium",
        "Edge Case",
        "Cogeneration allocation unhandled exception with zero outputs",
        "Return 0 allocated emissions gracefully",
        f"Raised {type(e).__name__}: {e}",
        "cogen_calc.calculate(1000, 0, 0)",
        "Confirmed"
    )


# 5. Tautological Test Inspection
print("\n--- Scanning for Tautological Tests in new/server/tests ---")
tautological_patterns = [
    ("calculate_co2e", "assert calculate_co2e"),
    ("dispatch_calculation", "assert dispatch_calculation"),
]

tautology_matches = []
tests_dir = "new/server/tests"
for root, _, files in os.walk(tests_dir):
    for f in files:
        if f.startswith("test_") and f.endswith(".py"):
            fpath = os.path.join(root, f)
            with open(fpath, "r", encoding="utf-8", errors="ignore") as fh:
                lines = fh.readlines()
            for idx, line in enumerate(lines):
                # Check if an expected value in an assert is calling the calculation function under test
                if "expected" in line.lower() and ("calculate" in line or "dispatch" in line or "to_base" in line):
                    tautology_matches.append((fpath, idx + 1, line.strip()))

print(f"Found {len(tautology_matches)} potential tautological assertion lines in test suite.")
for match in tautology_matches[:5]:
    print(f"  {match[0]}:{match[1]} -> {match[2]}")


# Output summary
print(f"\n==========================================")
print(f"Calculation Matrix Audit Completed: {len(findings)} findings logged")
print(f"==========================================")
