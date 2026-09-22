"""
INDEPENDENT REFERENCE MODEL: Fundamental Physical Constants & Regulatory Parameters
Clean-slate specification - ZERO production imports.
Authoritative sources:
- API Compendium 2021 §4.2.1, §5.1, §5.2
- ISO 13443 (Natural Gas - Standard Reference Conditions)
- ISO 14064-1:2018 (GHG Quantification and Reporting)
- IPCC AR4 (2007), AR5 (2013), AR6 (2021) Working Group I Reports
- NIST Physical Reference Data (Avoirdupois & SI units)
"""

# Standard Thermodynamic Conditions (ISO 13443 / API Compendium 2021 §4.2.1)
# 60 °F = 15.556 °C = 288.706 K = 519.67 °R
# 14.6959488 psia = 101.325 kPa = 1.01325 bar = 1.0 atm
STD_TEMP_K = 288.706
STD_TEMP_R = 519.67
STD_TEMP_C = 15.555555555555556
STD_TEMP_F = 60.0

STD_PRESSURE_PSIA = 14.6959488
STD_PRESSURE_KPA = 101.325
STD_PRESSURE_BAR = 1.01325
STD_PRESSURE_ATM = 1.0

# Exact Molecular Weights (NIST Atomic Weights, g/mol)
MW_C = 12.011
MW_H = 1.008
MW_O = 15.999
MW_N = 14.0067
MW_S = 32.065

MW_CO2 = MW_C + 2 * MW_O               # 44.009 g/mol
MW_CH4 = MW_C + 4 * MW_H               # 16.043 g/mol
MW_N2O = 2 * MW_N + MW_O               # 44.0124 g/mol
MW_CO = MW_C + MW_O                    # 28.010 g/mol
MW_C2H6 = 2 * MW_C + 6 * MW_H          # 30.070 g/mol
MW_C3H8 = 3 * MW_C + 8 * MW_H          # 44.097 g/mol
MW_nC4H10 = 4 * MW_C + 10 * MW_H       # 58.124 g/mol
MW_iC4H10 = 4 * MW_C + 10 * MW_H       # 58.124 g/mol
MW_nC5H12 = 5 * MW_C + 12 * MW_H       # 72.151 g/mol
MW_iC5H12 = 5 * MW_C + 12 * MW_H       # 72.151 g/mol
MW_C6H14 = 6 * MW_C + 14 * MW_H        # 86.178 g/mol

# Standard Gas Densities at 60°F (15.56°C) and 14.696 psia (101.325 kPa) (kg/m³)
# Derived independently from Ideal Gas Law: rho = (P * MW) / (R_univ * T)
# R_univ = 8.314462618 J/(mol*K) = 8314.462618 Pa*m³/(kmol*K)
# rho = (101325 Pa * MW kg/kmol) / (8314.462618 * 288.706 K)
# Empirical real-gas densities from API Compendium 2021 Table 4-1:
DENSITY_CH4 = 0.6785    # kg/m³
DENSITY_CO2 = 1.8610    # kg/m³
DENSITY_N2O = 1.8600    # kg/m³
DENSITY_C2H6 = 1.2820   # kg/m³
DENSITY_C3H8 = 1.8820   # kg/m³
DENSITY_C4H10 = 2.5190  # kg/m³

# Exact Physical Unit Conversions (NIST Special Publication 811)
CONV_LB_TO_KG = 0.45359237
CONV_KG_TO_LB = 1.0 / 0.45359237
CONV_SHORT_TON_TO_KG = 907.18474
CONV_LONG_TON_TO_KG = 1016.0469088
CONV_METRIC_TONNE_TO_KG = 1000.0

# Volume Conversions
CONV_SCF_TO_M3 = 0.028316846592
CONV_M3_TO_SCF = 1.0 / 0.028316846592
CONV_MSCF_TO_M3 = 28.316846592
CONV_M3_TO_MSCF = 1.0 / 28.316846592
CONV_MMSCF_TO_M3 = 28316.846592
CONV_BBL_TO_M3 = 0.158987294928
CONV_M3_TO_BBL = 1.0 / 0.158987294928
CONV_GAL_TO_M3 = 0.003785411784
CONV_M3_TO_GAL = 1.0 / 0.003785411784
CONV_L_TO_M3 = 0.001
CONV_M3_TO_L = 1000.0

# Energy Conversions (ISO 31-4)
CONV_BTU_TO_J = 1055.05585262
CONV_MMBTU_TO_MJ = 1055.05585262
CONV_MJ_TO_MMBTU = 1.0 / 1055.05585262
CONV_KWH_TO_MJ = 3.6
CONV_MJ_TO_KWH = 1.0 / 3.6
CONV_MWH_TO_MJ = 3600.0
CONV_THERM_TO_MJ = 105.4804
CONV_GJ_TO_MJ = 1000.0

# Global Warming Potential (GWP) Standards
# IPCC AR4 (2007)
GWP_AR4_100 = {"CO2": 1.0, "CH4": 25.0, "N2O": 298.0}
GWP_AR4_20  = {"CO2": 1.0, "CH4": 72.0, "N2O": 289.0}

# IPCC AR5 (2013, WG1 Table 8.7)
GWP_AR5_100 = {"CO2": 1.0, "CH4": 28.0, "N2O": 265.0}
GWP_AR5_20  = {"CO2": 1.0, "CH4": 82.5, "N2O": 268.0}

# IPCC AR6 (2021, WG1 Chapter 7)
GWP_AR6_100 = {"CO2": 1.0, "CH4": 27.9, "N2O": 273.0}
GWP_AR6_20  = {"CO2": 1.0, "CH4": 82.5, "N2O": 273.0}

GWP_REGISTRY = {
    ("AR4", "100"): GWP_AR4_100,
    ("AR4", "20"):  GWP_AR4_20,
    ("AR5", "100"): GWP_AR5_100,
    ("AR5", "20"):  GWP_AR5_20,
    ("AR6", "100"): GWP_AR6_100,
    ("AR6", "20"):  GWP_AR6_20,
}

def resolve_gwp(standard="AR5", horizon="100"):
    std = str(standard or "AR5").strip().upper()
    hor = str(horizon or "100").strip()
    return GWP_REGISTRY.get((std, hor), GWP_AR5_100)
