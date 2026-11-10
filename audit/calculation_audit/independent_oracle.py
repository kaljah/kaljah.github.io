"""
Independent Reference Oracle for GHG Emissions Calculations
Conforms strictly to API Compendium (2021) and GHG Protocol Scope 1/2/3 Standards.
Built with Python Decimal for high precision reference calculations.
DO NOT IMPORT FROM new/server/calculations TO AVOID TAUTOLOGICAL ASSERTS.
"""

from decimal import Decimal, ROUND_HALF_UP, getcontext
import math

# Set precision to 50 decimal digits
getcontext().prec = 50

# Physical & Chemical Constants per API Compendium 2021
MW_C = Decimal("12.011")
MW_CO2 = Decimal("44.01")
MW_CH4 = Decimal("16.04")
MW_N2O = Decimal("44.013")
STOICH_RATIO_CO2_C = MW_CO2 / MW_C  # ~3.6641412...

# Standard Thermodynamic Conditions (API Compendium 2021 §4.2.1, ISO 13443)
# 60 °F = 15.55555... °C = 288.705555... K = 519.67 °R
STD_TEMP_F = Decimal("60.0")
STD_TEMP_R = Decimal("519.67")
STD_TEMP_K = (STD_TEMP_F - Decimal("32.0")) * Decimal("5") / Decimal("9") + Decimal("273.15")
STD_PRESSURE_PSIA = Decimal("14.696")
STD_PRESSURE_KPA = Decimal("101.325")

# Molar volume at standard conditions (60 °F, 14.696 psia)
# 379.3 scf / lb-mol = 23.685 m3 / kmol
MOLAR_VOL_SCF_LBMOL = Decimal("379.3")
MOLAR_VOL_M3_KMOL = Decimal("23.685")

# Standard Gas Densities at standard conditions (kg/m3) = MW / 23.685
DENSITY_CH4_STD = MW_CH4 / MOLAR_VOL_M3_KMOL   # 16.04 / 23.685 = 0.6772218...
DENSITY_CO2_STD = MW_CO2 / MOLAR_VOL_M3_KMOL   # 44.01 / 23.685 = 1.8581380...
DENSITY_N2O_STD = MW_N2O / MOLAR_VOL_M3_KMOL   # 44.013 / 23.685 = 1.8582647...

# Standard HHV for Natural gas
NG_HHV_BTU_PER_SCF = Decimal("1020.0")
MMBTU_PER_BOE = Decimal("5.8")

# NIST / API Exact Unit Conversions
CONV = {
    # Mass to kg
    "kg": Decimal("1.0"),
    "tonne": Decimal("1000.0"),
    "t": Decimal("1000.0"),
    "mt": Decimal("1000.0"),
    "metric_ton": Decimal("1000.0"),
    "lb": Decimal("0.45359237"),
    "short_ton": Decimal("907.18474"),
    "long_ton": Decimal("1016.0469088"),
    "g": Decimal("0.001"),

    # Volume to m3 (at 60 °F, 14.696 psia)
    "m3": Decimal("1.0"),
    "sm3": Decimal("1.0"),
    "scf": Decimal("0.028316846592"),
    "mscf": Decimal("28.316846592"),
    "mcf": Decimal("28.316846592"),
    "mmscf": Decimal("28316.846592"),
    "mmcf": Decimal("28316.846592"),
    "bbl": Decimal("0.158987295"),
    "gal": Decimal("0.003785411784"),
    "l": Decimal("0.001"),
    "liter": Decimal("0.001"),

    # Energy to MJ
    "mj": Decimal("1.0"),
    "gj": Decimal("1000.0"),
    "tj": Decimal("1000000.0"),
    "kj": Decimal("0.001"),
    "btu": Decimal("0.00105505585262"),
    "kbtu": Decimal("1.05505585262"),
    "mmbtu": Decimal("1055.05585262"),
    "kwh": Decimal("3.6"),
    "mwh": Decimal("3600.0"),
    "therm": Decimal("105.505585262"),
}

# IPCC Assessment Report Global Warming Potentials
GWP = {
    "AR4": {"CO2": Decimal("1.0"), "CH4": Decimal("25.0"), "N2O": Decimal("298.0")},
    "AR5": {"CO2": Decimal("1.0"), "CH4": Decimal("28.0"), "N2O": Decimal("265.0")},
    "AR6": {"CO2": Decimal("1.0"), "CH4": Decimal("29.8"), "N2O": Decimal("273.0")},  # fossil CH4
    "AR6_NONFOSSIL": {"CO2": Decimal("1.0"), "CH4": Decimal("27.9"), "N2O": Decimal("273.0")},
    "SAR": {"CO2": Decimal("1.0"), "CH4": Decimal("21.0"), "N2O": Decimal("310.0")},  # Second Assessment Report
}


def oracle_stoichiometric_co2(mass_kg: Decimal, carbon_fraction: Decimal, oxidation_factor: Decimal = Decimal("1.0")) -> Decimal:
    """
    API Compendium Eq. 4-3 / 4-4:
    CO2 (tonnes) = Mass (kg) * Carbon_Fraction * Oxidation_Factor * (44.01 / 12.011) / 1000
    """
    if mass_kg < 0 or carbon_fraction < 0 or oxidation_factor < 0:
        raise ValueError("Inputs must be non-negative")
    if carbon_fraction > Decimal("1.0"):
        raise ValueError("Carbon fraction cannot exceed 1.0")
    if oxidation_factor > Decimal("1.0"):
        raise ValueError("Oxidation factor cannot exceed 1.0")
    co2_kg = mass_kg * carbon_fraction * oxidation_factor * STOICH_RATIO_CO2_C
    return co2_kg / Decimal("1000.0")


def oracle_normalize_gas_volume(
    v_meas: Decimal,
    t_meas_k: Decimal = None,
    p_meas_psia: Decimal = None,
    z: Decimal = Decimal("1.0")
) -> Decimal:
    """
    API Compendium §4.2.1:
    V_std = V_meas * (P_meas / P_std) * (T_std / T_meas) * (1 / Z)
    """
    if v_meas <= 0:
        return Decimal("0.0")
    if z <= 0:
        raise ValueError("Compressibility Z must be strictly positive")
    t_factor = (STD_TEMP_K / t_meas_k) if t_meas_k is not None else Decimal("1.0")
    p_factor = (p_meas_psia / STD_PRESSURE_PSIA) if p_meas_psia is not None else Decimal("1.0")
    return v_meas * p_factor * t_factor / z


def oracle_flaring_emissions(
    vol_std_m3: Decimal,
    comp_mol_fractions: dict,  # {"c1": 0.85, "c2": 0.05, ..., "co2": 0.02}
    eta_combustion: Decimal = Decimal("0.98"),
    eta_destruction: Decimal = Decimal("0.98"),
    ef_n2o_kg_per_mmbtu: Decimal = Decimal("0.0001"),
    hhv_btu_per_scf: Decimal = NG_HHV_BTU_PER_SCF
) -> dict:
    """
    API Compendium 2021 Eq. 5-4, 5-5, 5-6:
    Hydrocarbon flaring dual-efficiency calculation.
    """
    c1 = comp_mol_fractions.get("c1", Decimal("0.0"))
    native_co2 = comp_mol_fractions.get("co2", Decimal("0.0"))

    # CH4 uncombusted = V_std * c1 * (1 - eta_d) * density_ch4 / 1000
    ch4_tonnes = (vol_std_m3 * c1 * (Decimal("1.0") - eta_destruction) * DENSITY_CH4_STD) / Decimal("1000.0")

    # Carbon moles per mole of gas
    total_c_moles = Decimal("0.0")
    for k in range(1, 11):
        frac = comp_mol_fractions.get(f"c{k}", Decimal("0.0"))
        total_c_moles += frac * Decimal(str(k))

    # Combusted CO2 volume = V_std * total_c_moles * eta_combustion
    co2_combusted_vol = vol_std_m3 * total_c_moles * eta_combustion
    co2_combusted_tonnes = (co2_combusted_vol * DENSITY_CO2_STD) / Decimal("1000.0")

    # Native uncombusted CO2 = V_std * native_co2 * density_co2 / 1000
    co2_native_tonnes = (vol_std_m3 * native_co2 * DENSITY_CO2_STD) / Decimal("1000.0")
    co2_total_tonnes = co2_combusted_tonnes + co2_native_tonnes

    # N2O from flared energy
    vol_scf = vol_std_m3 / CONV["scf"]
    flared_mmbtu = (vol_scf * hhv_btu_per_scf) / Decimal("1000000.0")
    n2o_tonnes = (flared_mmbtu * ef_n2o_kg_per_mmbtu) / Decimal("1000.0")

    return {
        "co2_tonnes": co2_total_tonnes,
        "ch4_tonnes": ch4_tonnes,
        "n2o_tonnes": n2o_tonnes,
    }


def oracle_indirect_steam(
    heat_energy_mmbtu: Decimal,
    ef_co2_kg_per_mmbtu: Decimal,
    boiler_efficiency: Decimal = Decimal("0.80"),
    transmission_loss: Decimal = Decimal("0.0"),
    ef_ch4_kg_per_mmbtu: Decimal = Decimal("0.0"),
    ef_n2o_kg_per_mmbtu: Decimal = Decimal("0.0"),
    mode: str = "multiplicative"
) -> dict:
    """
    API Compendium Section 8.1.5:
    Steam emissions = (Heat Energy / Net Efficiency) * EF
    Thermodynamic correct: net_efficiency = boiler_efficiency * (1 - transmission_loss)
    If mode == "subtractive": net_efficiency = boiler_efficiency - transmission_loss
    """
    if mode == "multiplicative":
        net_eff = boiler_efficiency * (Decimal("1.0") - transmission_loss)
    elif mode == "subtractive":
        net_eff = boiler_efficiency - transmission_loss
    else:
        raise ValueError(f"Unknown mode: {mode}")

    if net_eff <= 0:
        raise ValueError(f"Net efficiency must be > 0: got {net_eff}")

    fuel_mmbtu = heat_energy_mmbtu / net_eff
    co2_tonnes = (fuel_mmbtu * ef_co2_kg_per_mmbtu) / Decimal("1000.0")
    ch4_tonnes = (fuel_mmbtu * ef_ch4_kg_per_mmbtu) / Decimal("1000.0")
    n2o_tonnes = (fuel_mmbtu * ef_n2o_kg_per_mmbtu) / Decimal("1000.0")

    return {
        "net_efficiency": net_eff,
        "fuel_mmbtu": fuel_mmbtu,
        "co2_tonnes": co2_tonnes,
        "ch4_tonnes": ch4_tonnes,
        "n2o_tonnes": n2o_tonnes,
    }


def oracle_co2e(co2: Decimal, ch4: Decimal, n2o: Decimal, standard: str = "AR5") -> Decimal:
    """
    CO2e = CO2 * GWP_CO2 + CH4 * GWP_CH4 + N2O * GWP_N2O
    """
    if standard not in GWP:
        raise ValueError(f"Unknown standard {standard}")
    g = GWP[standard]
    return co2 * g["CO2"] + ch4 * g["CH4"] + n2o * g["N2O"]
