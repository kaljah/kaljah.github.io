"""
Adversarial Unit Conversion and Thermodynamic Conditions Audit
Tests all conversions, inverse symmetry, edge cases, boundaries, and standard conditions.
"""

import sys
import math
from decimal import Decimal

# Add server directory to path
sys.path.insert(0, "new/server")

from calculations.units import (
    CONVERSIONS,
    convert,
    convert_temperature,
    convert_pressure,
    normalize_gas_volume_to_standard,
    to_kelvin,
    to_fahrenheit,
    to_psia,
    calculate_co2e,
    compute_scope3_co2e,
    factor_to_kg_per_activity,
    parse_amount,
    STD_TEMP_K,
    STD_TEMP_F,
    STD_PRESSURE_PSIA,
    MOLAR_VOLUME_M3_PER_KMOL,
    MW_CH4,
    MW_CO2,
)
from calculations.constants import GWP_STANDARDS, get_active_gwp

results = []

def record(test_id, name, passed, detail=""):
    results.append({
        "id": test_id,
        "name": name,
        "passed": passed,
        "detail": detail
    })
    status = "PASS" if passed else "FAIL"
    print(f"[{status}] {test_id}: {name} - {detail}")


# Test 1: Inverse Symmetry of CONVERSIONS
print("\n--- Testing Inverse Symmetry of CONVERSIONS ---")
symmetry_failures = []
for k, v in list(CONVERSIONS.items()):
    if "_to_" in k and isinstance(v, (int, float)) and v > 0:
        u1, u2 = k.split("_to_", 1)
        rev_k = f"{u2}_to_{u1}"
        if rev_k in CONVERSIONS:
            rev_v = CONVERSIONS[rev_k]
            product = v * rev_v
            diff = abs(product - 1.0)
            if diff > 1e-4:  # Allowing slight float representation tolerance
                symmetry_failures.append(f"{k} ({v}) * {rev_k} ({rev_v}) = {product} (diff: {diff})")

if symmetry_failures:
    record("UNIT-01", "Inverse Symmetry in CONVERSIONS table", False, f"Found {len(symmetry_failures)} asymmetry errors: {symmetry_failures[:3]}")
else:
    record("UNIT-01", "Inverse Symmetry in CONVERSIONS table", True, "All directional pairs multiply to ~1.0")


# Test 2: Standard Molar Volume and Gas Densities
print("\n--- Testing Standard Thermodynamic Conditions & Densities ---")
# API Compendium 2021 Eq. 3-4: 379.3 scf/lb-mol = 23.685 m3/kg-mol at 60 F, 14.696 psia
exp_rho_ch4 = 16.04 / 23.685
act_rho_ch4 = CONVERSIONS.get("density_ch4")
diff_ch4 = abs(exp_rho_ch4 - act_rho_ch4) if act_rho_ch4 else 1.0

if diff_ch4 < 1e-5:
    record("UNIT-02", "Methane standard density (API Compendium 60 F, 14.696 psia)", True, f"Density = {act_rho_ch4:.6f} kg/m3")
else:
    record("UNIT-02", "Methane standard density", False, f"Expected {exp_rho_ch4:.6f}, got {act_rho_ch4}")

# Test 3: scf to m3 conversion
# 1 scf = 0.028316846592 m3 (NIST)
scf_to_m3 = CONVERSIONS.get("scf_to_m3")
diff_scf = abs(scf_to_m3 - 0.028316846592)
if diff_scf < 1e-9:
    record("UNIT-03", "NIST exact scf to m3 conversion", True, f"{scf_to_m3}")
else:
    record("UNIT-03", "NIST exact scf to m3 conversion", False, f"Expected 0.028316846592, got {scf_to_m3}")

# Test 4: convert() wrapper round-trips
print("\n--- Testing convert() function roundtrips ---")
roundtrip_tests = [
    (100.0, "kg", "lb"),
    (50.0, "tonne", "short_ton"),
    (1000.0, "m3", "scf"),
    (250.0, "bbl", "gal"),
    (1000.0, "mj", "mmbtu"),
    (500.0, "kwh", "mj"),
    (10.0, "mscf", "mmscf"),
]
roundtrip_fails = []
for val, u1, u2 in roundtrip_tests:
    try:
        conv1 = convert(val, u1, u2)
        conv2 = convert(conv1, u2, u1)
        err = abs(conv2 - val) / val
        if err > 1e-4:
            roundtrip_fails.append(f"{u1} <-> {u2}: original {val}, roundtrip {conv2}, rel_err {err}")
    except Exception as e:
        roundtrip_fails.append(f"{u1} <-> {u2}: raised {e}")

if roundtrip_fails:
    record("UNIT-04", "convert() roundtrip accuracy", False, "; ".join(roundtrip_fails))
else:
    record("UNIT-04", "convert() roundtrip accuracy", True, "All tested pairs roundtrip < 0.01% error")

# Test 5: Temperature & Pressure conversions
print("\n--- Testing Temperature & Pressure Conversions ---")
# 60 F in C
c_from_60f = convert_temperature(60.0, "f", "c")
exp_c = (60.0 - 32.0) * 5.0 / 9.0  # 15.555555...
diff_c = abs(c_from_60f - exp_c)
if diff_c < 1e-5:
    record("UNIT-05", "60 F to C conversion", True, f"Got {c_from_60f:.5f} C")
else:
    record("UNIT-05", "60 F to C conversion", False, f"Expected {exp_c:.5f}, got {c_from_60f:.5f}")

# Absolute zero check
try:
    to_kelvin(-300, "c")
    record("UNIT-06", "Below absolute zero check", False, "Failed to raise ValueError for -300 C")
except ValueError:
    record("UNIT-06", "Below absolute zero check", True, "Correctly rejected -300 C (< 0 K)")

# Test 6: Thermodynamic gas volume normalization (API Compendium §4.2.1)
print("\n--- Testing Thermodynamic Gas Volume Normalization ---")
# V_std = V_meas * (P_meas / 14.696) * (519.67 / T_meas_R) * (1 / Z)
# Test: 1000 m3 at 100 psig (114.696 psia), 100 F (559.67 R), Z = 0.95
p_meas_psig = 100.0
p_meas_psia = 100.0 + 14.696
t_meas_f = 100.0
t_meas_k = (100.0 - 32.0) * 5.0 / 9.0 + 273.15
t_meas_r = 100.0 + 459.67
z = 0.95
vol_act = 1000.0

exp_v_std = vol_act * (p_meas_psia / 14.696) * (519.67 / t_meas_r) * (1.0 / z)
act_v_std = normalize_gas_volume_to_standard(
    volume=vol_act,
    operating_temp=100.0,
    temp_unit="f",
    operating_press=100.0,
    press_unit="psig",
    z_factor=0.95
)
err_norm = abs(act_v_std - exp_v_std) / exp_v_std
if err_norm < 1e-4:
    record("UNIT-07", "Gas Volume Normalization to Standard", True, f"Expected {exp_v_std:.2f}, got {act_v_std:.2f}")
else:
    record("UNIT-07", "Gas Volume Normalization to Standard", False, f"Expected {exp_v_std:.2f}, got {act_v_std:.2f} (err: {err_norm})")

# Test 7: Z-factor edge cases
print("\n--- Testing Z-factor Edge Cases ---")
try:
    normalize_gas_volume_to_standard(100.0, z_factor=0.0)
    record("UNIT-08", "Z-factor zero validation", False, "Allowed z_factor=0.0")
except ValueError:
    record("UNIT-08", "Z-factor zero validation", True, "Rejected z_factor=0.0")

try:
    normalize_gas_volume_to_standard(100.0, z_factor=-0.5)
    record("UNIT-09", "Z-factor negative validation", False, "Allowed negative z_factor")
except ValueError:
    record("UNIT-09", "Z-factor negative validation", True, "Rejected negative z_factor")

# Test 8: Scope 3 co2e calculation edge cases
print("\n--- Testing Scope 3 CO2e calculation ---")
# 100 tonnes activity, factor: 2.5 kg CO2e / tonne -> co2e = 100 * 2.5 / 1000 = 0.25 tonnes
s3_co2e_1 = compute_scope3_co2e(100.0, 2.5, "kg CO2e / tonne")
if abs(s3_co2e_1 - 0.25) < 1e-6:
    record("UNIT-10", "Scope 3 kg CO2e/tonne standard", True, f"{s3_co2e_1} tonnes")
else:
    record("UNIT-10", "Scope 3 kg CO2e/tonne standard", False, f"Expected 0.25, got {s3_co2e_1}")

# Activity in kg, factor in tonne CO2e / tonne
# 50,000 kg activity against 1.5 t CO2e / tonne -> 50 tonnes * 1.5 = 75 tonnes CO2e
s3_co2e_2 = compute_scope3_co2e(50000.0, 1.5, "t CO2e / tonne", activity_unit="kg")
if abs(s3_co2e_2 - 75.0) < 1e-4:
    record("UNIT-11", "Scope 3 kg activity against per-tonne factor", True, f"{s3_co2e_2} tonnes")
else:
    record("UNIT-11", "Scope 3 kg activity against per-tonne factor", False, f"Expected 75.0, got {s3_co2e_2}")

# Per $1,000 spend factor
# $50,000 spend, factor 120.0 kg CO2e / $1,000 -> 50 * 120 / 1000 = 6.0 tonnes CO2e
s3_co2e_3 = compute_scope3_co2e(50000.0, 120.0, "kg CO2e / $1000")
if abs(s3_co2e_3 - 6.0) < 1e-4:
    record("UNIT-12", "Scope 3 per-$1,000 spend factor", True, f"{s3_co2e_3} tonnes")
else:
    record("UNIT-12", "Scope 3 per-$1,000 spend factor", False, f"Expected 6.0, got {s3_co2e_3}")

# Test 9: GWP Standards & Unknown Standard
print("\n--- Testing GWP standards ---")
gwp_ar4 = get_active_gwp(standard="AR4")
gwp_ar5 = get_active_gwp(standard="AR5")
gwp_ar6 = get_active_gwp(standard="AR6")

if gwp_ar4["CH4"] == 25.0 and gwp_ar5["CH4"] == 28.0 and gwp_ar6["CH4"] == 29.8:
    record("UNIT-13", "GWP values for AR4, AR5, AR6 100-yr", True, f"AR4: {gwp_ar4['CH4']}, AR5: {gwp_ar5['CH4']}, AR6: {gwp_ar6['CH4']}")
else:
    record("UNIT-13", "GWP values for AR4, AR5, AR6 100-yr", False, f"Unexpected GWPs: AR4={gwp_ar4}, AR5={gwp_ar5}, AR6={gwp_ar6}")

try:
    get_active_gwp(standard="SAR")
    record("UNIT-14", "GWP SAR (Second Assessment Report)", True, "Supported SAR")
except ValueError as e:
    record("UNIT-14", "GWP SAR (Second Assessment Report)", False, f"SAR not supported in GWP_STANDARDS: {e}")

# Summary
passed = sum(1 for r in results if r["passed"])
failed = sum(1 for r in results if not r["passed"])
print(f"\n==========================================")
print(f"Total Unit Tests: {len(results)} | Passed: {passed} | Failed: {failed}")
print(f"==========================================")
