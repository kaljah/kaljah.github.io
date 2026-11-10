"""
INDEPENDENT VERIFICATION ORACLE: API COMPENDIUM 2021 & GHG PROTOCOL
===================================================================
Clean-room implementation built from first principles using Python Decimal (50-digit precision).
Strictly adheres to:
- API Compendium of GHG Emissions Methodologies for the Oil and Gas Industry (November 2021)
- GHG Protocol Corporate Accounting and Reporting Standard
- GHG Protocol Scope 2 Guidance (2015) & Scope 3 Standard (2011)
- ISO 14064-1:2018 & ISO/IEC Guide 98-3 (GUM)
- IPCC Assessment Reports AR4, AR5, AR6, and SAR

CRITICAL AUDIT RULE:
ZERO IMPORTS from production source code (`new/server/calculations` or `new/`).
"""

from decimal import Decimal, ROUND_HALF_UP, getcontext
import math
from typing import Dict, Any, Optional, Tuple, List

# 50 decimal digits precision
getcontext().prec = 50

# =============================================================================
# 1. PHYSICAL & CHEMICAL CONSTANTS (API Compendium 2021 Table 3-1, 3-2, 3-3)
# =============================================================================
MW_C = Decimal("12.011")          # Carbon atomic weight (g/mol or kg/kmol)
MW_H = Decimal("1.008")           # Hydrogen atomic weight
MW_O = Decimal("15.9994")         # Oxygen atomic weight
MW_N = Decimal("14.0067")         # Nitrogen atomic weight
MW_S = Decimal("32.065")          # Sulfur atomic weight

MW_CO2 = Decimal("44.01")         # Carbon dioxide molecular weight (kg/kmol)
MW_CH4 = Decimal("16.04")         # Methane molecular weight (kg/kmol)
MW_N2O = Decimal("44.013")        # Nitrous oxide molecular weight (kg/kmol)

# Stoichiometric combustion ratio: CO2 / C
STOICH_RATIO_CO2_C = MW_CO2 / MW_C  # 44.01 / 12.011 = 3.6641412038964282740820914...

# Standard Conditions (API Compendium 2021 §4.2.1: 60 °F and 14.696 psia / 101.325 kPa)
STD_TEMP_F = Decimal("60.0")
STD_TEMP_R = Decimal("519.67")      # 60 + 459.67
STD_TEMP_C = (STD_TEMP_F - Decimal("32.0")) * Decimal("5") / Decimal("9") # 15.555555... °C
STD_TEMP_K = STD_TEMP_C + Decimal("273.15")  # 288.705555... K

STD_PRESSURE_PSIA = Decimal("14.696")
STD_PRESSURE_BAR = Decimal("1.01325")
STD_PRESSURE_KPA = Decimal("101.325")

# Standard Molar Volume (Ideal Gas Law at 60 °F, 14.696 psia)
# 379.3 scf / lb-mol = 23.6853 m3 / kmol
MOLAR_VOL_SCF_LBMOL = Decimal("379.3")
MOLAR_VOL_M3_KMOL = Decimal("23.685")

# Standard Gas Densities at 60 °F, 14.696 psia (kg/m3 = MW / 23.685)
DENSITY_CH4_STD = MW_CH4 / MOLAR_VOL_M3_KMOL    # 16.04 / 23.685 = 0.6772218703821828... kg/m3
DENSITY_CO2_STD = MW_CO2 / MOLAR_VOL_M3_KMOL    # 44.01 / 23.685 = 1.8581380620645978... kg/m3
DENSITY_N2O_STD = MW_N2O / MOLAR_VOL_M3_KMOL    # 44.013 / 23.685 = 1.8582647244880726... kg/m3
DENSITY_AIR_STD = Decimal("28.966") / MOLAR_VOL_M3_KMOL # ~1.22297... kg/m3

# Standard Natural Gas Heating Value (Gross / HHV)
DEFAULT_NG_HHV_BTU_PER_SCF = Decimal("1020.0")  # 1,020 Btu/scf = 1.020 MMBtu/Mscf
DEFAULT_NG_HHV_MJ_PER_M3 = Decimal("38.0")     # ~38.0 MJ/m3

# Barrel of Oil Equivalent (BOE) Energy Basis (API Compendium 2021 §3.1.2)
MMBTU_PER_BOE = Decimal("5.8")                 # 5.80 MMBtu/BOE
SCF_PER_BOE = Decimal("5800000.0") / DEFAULT_NG_HHV_BTU_PER_SCF  # ~5,686.2745 scf/BOE
MSCF_PER_BOE = Decimal("5.8") / Decimal("1.02")  # ~5.68627 Mscf/BOE

# =============================================================================
# 2. EXACT UNIT CONVERSION FACTORS (NIST SP 811 / API Compendium 2021 Ch 3)
# =============================================================================
EXACT_CONVERSIONS = {
    # Mass conversions to kilogram (kg)
    "kg": Decimal("1.0"),
    "tonne": Decimal("1000.0"),
    "t": Decimal("1000.0"),
    "mt": Decimal("1000.0"),
    "metric_ton": Decimal("1000.0"),
    "g": Decimal("0.001"),
    "mg": Decimal("0.000001"),
    "lb": Decimal("0.45359237"),
    "short_ton": Decimal("907.18474"),
    "long_ton": Decimal("1016.0469088"),

    # Volume conversions to standard cubic meters (m3) at 60 °F, 14.696 psia
    "m3": Decimal("1.0"),
    "sm3": Decimal("1.0"),
    "nm3": Decimal("1.0"),  # Note: Normal conditions 0 C are normalized separately
    "ksm3": Decimal("1000.0"),
    "mmsm3": Decimal("1000000.0"),
    "l": Decimal("0.001"),
    "liter": Decimal("0.001"),
    "scf": Decimal("0.028316846592"),
    "cf": Decimal("0.028316846592"),
    "mscf": Decimal("28.316846592"),
    "mcf": Decimal("28.316846592"),
    "mmscf": Decimal("28316.846592"),
    "mmcf": Decimal("28316.846592"),
    "bbl": Decimal("0.158987294928"),
    "barrel": Decimal("0.158987294928"),
    "gal": Decimal("0.003785411784"),
    "gallon": Decimal("0.003785411784"),

    # Energy conversions to Megajoules (MJ)
    "mj": Decimal("1.0"),
    "kj": Decimal("0.001"),
    "gj": Decimal("1000.0"),
    "tj": Decimal("1000000.0"),
    "btu": Decimal("0.00105505585262"),
    "kbtu": Decimal("1.05505585262"),
    "mmbtu": Decimal("1055.05585262"),
    "therm": Decimal("105.505585262"),
    "kwh": Decimal("3.6"),
    "mwh": Decimal("3600.0"),
    "gwh": Decimal("3600000.0"),
}

# =============================================================================
# 3. GLOBAL WARMING POTENTIALS (IPCC AR4, AR5, AR6, SAR)
# =============================================================================
GWP_REGISTRY = {
    # IPCC Second Assessment Report (SAR 1995)
    "SAR": {"CO2": Decimal("1.0"), "CH4": Decimal("21.0"), "N2O": Decimal("310.0")},
    # IPCC Fourth Assessment Report (AR4 2007) - 100 yr
    "AR4": {"CO2": Decimal("1.0"), "CH4": Decimal("25.0"), "N2O": Decimal("298.0")},
    "AR4_20": {"CO2": Decimal("1.0"), "CH4": Decimal("72.0"), "N2O": Decimal("289.0")},
    # IPCC Fifth Assessment Report (AR5 2013) - without climate-carbon feedbacks
    "AR5": {"CO2": Decimal("1.0"), "CH4": Decimal("28.0"), "N2O": Decimal("265.0")},
    "AR5_20": {"CO2": Decimal("1.0"), "CH4": Decimal("84.0"), "N2O": Decimal("264.0")},
    # IPCC Sixth Assessment Report (AR6 2021) - fossil methane
    "AR6": {"CO2": Decimal("1.0"), "CH4": Decimal("29.8"), "N2O": Decimal("273.0")},
    "AR6_20": {"CO2": Decimal("1.0"), "CH4": Decimal("82.5"), "N2O": Decimal("273.0")},
}

def oracle_convert_unit(val: Decimal, from_unit: str, to_unit: str) -> Decimal:
    """Exact dimensional conversion using Decimal factors."""
    u1 = from_unit.strip().lower()
    u2 = to_unit.strip().lower()
    if u1 == u2:
        return val
    if u1 not in EXACT_CONVERSIONS or u2 not in EXACT_CONVERSIONS:
        raise ValueError(f"Unsupported unit conversion: {from_unit} -> {to_unit}")
    # Convert to base SI, then to target
    base_val = val * EXACT_CONVERSIONS[u1]
    return base_val / EXACT_CONVERSIONS[u2]

def oracle_co2e(co2_t: Decimal, ch4_t: Decimal, n2o_t: Decimal, standard: str = "AR5", horizon: str = "100") -> Decimal:
    """CO2 equivalent calculation: sum(Gas_i * GWP_i)."""
    std_key = standard.upper()
    if horizon == "20" and f"{std_key}_20" in GWP_REGISTRY:
        std_key = f"{std_key}_20"
    if std_key not in GWP_REGISTRY:
        raise ValueError(f"Unknown GWP standard: {standard} (horizon: {horizon})")
    g = GWP_REGISTRY[std_key]
    return (co2_t * g["CO2"]) + (ch4_t * g["CH4"]) + (n2o_t * g["N2O"])

# =============================================================================
# 4. SCOPE 1 ORACLE EQUATIONS (API Compendium 2021)
# =============================================================================

def oracle_combustion_tier1(
    fuel_qty: Decimal,
    fuel_unit: str,
    ef_co2_kg: Decimal,
    ef_ch4_kg: Decimal,
    ef_n2o_kg: Decimal,
    ef_unit_basis: str = "m3",
) -> Dict[str, Decimal]:
    """
    API Compendium 2021 Eq. 4-1 / 4-2:
    E = Activity * EF
    Inputs converted to standard matching EF basis, outputs in metric tonnes.
    """
    qty_in_ef_unit = oracle_convert_unit(fuel_qty, fuel_unit, ef_unit_basis)
    co2_tonnes = (qty_in_ef_unit * ef_co2_kg) / Decimal("1000.0")
    ch4_tonnes = (qty_in_ef_unit * ef_ch4_kg) / Decimal("1000.0")
    n2o_tonnes = (qty_in_ef_unit * ef_n2o_kg) / Decimal("1000.0")
    return {
        "co2_tonnes": co2_tonnes,
        "ch4_tonnes": ch4_tonnes,
        "n2o_tonnes": n2o_tonnes,
    }

def oracle_combustion_stoichiometric(
    fuel_mass_kg: Decimal,
    carbon_weight_fraction: Decimal,
    oxidation_fraction: Decimal = Decimal("1.0"),
) -> Decimal:
    """
    API Compendium 2021 Eq. 4-3 / 4-4:
    CO2 (tonnes) = Fuel_Mass (kg) * C_wt_fraction * Oxidation * (44.01 / 12.011) / 1000
    """
    if carbon_weight_fraction < 0 or carbon_weight_fraction > Decimal("1.0"):
        raise ValueError(f"Carbon fraction must be in [0, 1]: got {carbon_weight_fraction}")
    if oxidation_fraction < 0 or oxidation_fraction > Decimal("1.0"):
        raise ValueError(f"Oxidation fraction must be in [0, 1]: got {oxidation_fraction}")
    co2_kg = fuel_mass_kg * carbon_weight_fraction * oxidation_fraction * STOICH_RATIO_CO2_C
    return co2_kg / Decimal("1000.0")

def oracle_flaring_emissions(
    gas_vol_std_m3: Decimal,
    hydrocarbon_mol_fractions: Dict[str, Decimal],  # {"c1": 0.80, "c2": 0.05, ...}
    native_co2_mol_fraction: Decimal = Decimal("0.0"),
    combustion_efficiency: Decimal = Decimal("0.98"),
    destruction_efficiency: Decimal = Decimal("0.98"),
    hhv_btu_per_scf: Decimal = DEFAULT_NG_HHV_BTU_PER_SCF,
    ef_n2o_kg_per_mmbtu: Decimal = Decimal("0.0001"),
) -> Dict[str, Decimal]:
    """
    API Compendium 2021 Eq. 5-4, 5-5, 5-6:
    Hydrocarbon flaring with explicit dual efficiencies (combustion vs destruction).
    - Uncombusted CH4: V_std * y_CH4 * (1 - eta_d) * rho_CH4 / 1000
    - Combusted CO2: V_std * sum(i * y_Ci) * eta_c * rho_CO2 / 1000
    - Native uncombusted CO2: V_std * y_native_CO2 * rho_CO2 / 1000
    - N2O from energy: (V_scf * HHV / 1e6) * EF_N2O / 1000
    """
    c1 = hydrocarbon_mol_fractions.get("c1", Decimal("0.0"))
    
    # 1. Uncombusted CH4
    ch4_tonnes = (gas_vol_std_m3 * c1 * (Decimal("1.0") - destruction_efficiency) * DENSITY_CH4_STD) / Decimal("1000.0")
    
    # 2. Total carbon atoms in hydrocarbon feed
    total_c_moles = Decimal("0.0")
    for k in range(1, 11):
        ck = hydrocarbon_mol_fractions.get(f"c{k}", Decimal("0.0"))
        total_c_moles += ck * Decimal(str(k))
    
    # 3. Combusted CO2
    co2_combusted_tonnes = (gas_vol_std_m3 * total_c_moles * combustion_efficiency * DENSITY_CO2_STD) / Decimal("1000.0")
    
    # 4. Native CO2 (unreacted pass-through)
    co2_native_tonnes = (gas_vol_std_m3 * native_co2_mol_fraction * DENSITY_CO2_STD) / Decimal("1000.0")
    co2_total_tonnes = co2_combusted_tonnes + co2_native_tonnes
    
    # 5. N2O emissions from flared heat
    gas_vol_scf = gas_vol_std_m3 / EXACT_CONVERSIONS["scf"]
    flared_mmbtu = (gas_vol_scf * hhv_btu_per_scf) / Decimal("1000000.0")
    n2o_tonnes = (flared_mmbtu * ef_n2o_kg_per_mmbtu) / Decimal("1000.0")
    
    return {
        "co2_tonnes": co2_total_tonnes,
        "co2_combusted_tonnes": co2_combusted_tonnes,
        "co2_native_tonnes": co2_native_tonnes,
        "ch4_tonnes": ch4_tonnes,
        "n2o_tonnes": n2o_tonnes,
        "flared_mmbtu": flared_mmbtu,
    }

def oracle_pneumatic_emissions(
    device_count: Decimal,
    operating_hours: Decimal,
    ef_vol_scf_per_hr: Decimal,
    ch4_mol_fraction: Decimal,
    co2_mol_fraction: Decimal = Decimal("0.0"),
) -> Dict[str, Decimal]:
    """
    API Compendium 2021 Section 6.2, Table 6-14 / 6-15:
    Whole-gas or methane-basis volumetric pneumatic venting.
    Vol_scf = Count * Hours * EF_scf_hr
    Mass_CH4 (t) = Vol_scf * EXACT_CONVERSIONS["scf"] * y_CH4 * DENSITY_CH4_STD / 1000
    """
    total_vol_scf = device_count * operating_hours * ef_vol_scf_per_hr
    total_vol_m3 = total_vol_scf * EXACT_CONVERSIONS["scf"]
    ch4_tonnes = (total_vol_m3 * ch4_mol_fraction * DENSITY_CH4_STD) / Decimal("1000.0")
    co2_tonnes = (total_vol_m3 * co2_mol_fraction * DENSITY_CO2_STD) / Decimal("1000.0")
    return {
        "vol_m3": total_vol_m3,
        "ch4_tonnes": ch4_tonnes,
        "co2_tonnes": co2_tonnes,
    }

def oracle_storage_tank_flashing(
    oil_throughput_bbl: Decimal,
    flashing_factor_scf_per_bbl: Decimal,
    ch4_mol_fraction: Decimal,
    co2_mol_fraction: Decimal = Decimal("0.0"),
    control_efficiency: Decimal = Decimal("0.0"), # e.g. 0.95 for VRU
) -> Dict[str, Decimal]:
    """
    API Compendium 2021 Section 6.3.1, Eq. 6-12 / 6-13:
    Tank flashing emissions = Throughput * GOR_flash * (1 - Control_Eff)
    """
    flashed_scf = oil_throughput_bbl * flashing_factor_scf_per_bbl * (Decimal("1.0") - control_efficiency)
    flashed_m3 = flashed_scf * EXACT_CONVERSIONS["scf"]
    ch4_tonnes = (flashed_m3 * ch4_mol_fraction * DENSITY_CH4_STD) / Decimal("1000.0")
    co2_tonnes = (flashed_m3 * co2_mol_fraction * DENSITY_CO2_STD) / Decimal("1000.0")
    return {
        "vented_m3": flashed_m3,
        "ch4_tonnes": ch4_tonnes,
        "co2_tonnes": co2_tonnes,
    }

def oracle_acid_gas_removal(
    feed_gas_m3: Decimal,
    co2_feed_fraction: Decimal,
    co2_treated_fraction: Decimal,
    ch4_slip_fraction: Decimal = Decimal("0.0"),
) -> Dict[str, Decimal]:
    """
    API Compendium 2021 Section 6.5, Eq. 6-18:
    CO2 stripped = Feed_Gas * (y_in - y_out) * rho_CO2 / 1000
    """
    delta_co2 = co2_feed_fraction - co2_treated_fraction
    if delta_co2 < 0:
        raise ValueError(f"Treated CO2 fraction ({co2_treated_fraction}) exceeds Feed ({co2_feed_fraction})")
    co2_vented_m3 = feed_gas_m3 * delta_co2
    co2_tonnes = (co2_vented_m3 * DENSITY_CO2_STD) / Decimal("1000.0")
    ch4_tonnes = (feed_gas_m3 * ch4_slip_fraction * DENSITY_CH4_STD) / Decimal("1000.0")
    return {
        "co2_tonnes": co2_tonnes,
        "ch4_tonnes": ch4_tonnes,
    }

def oracle_fugitive_components(
    component_count: Decimal,
    operating_hours: Decimal,
    ef_kg_per_hr_comp: Decimal,
    ch4_weight_fraction: Decimal,
) -> Decimal:
    """
    API Compendium 2021 Section 7.1, Table 7-11:
    CH4 (t) = Count * Hours * EF (kg/hr/comp) * CH4_wt_fraction / 1000
    """
    total_kg = component_count * operating_hours * ef_kg_per_hr_comp * ch4_weight_fraction
    return total_kg / Decimal("1000.0")

# =============================================================================
# 5. SCOPE 2 ORACLE EQUATIONS (GHG Protocol Scope 2 Guidance)
# =============================================================================

def oracle_scope2_electricity(
    consumption_kwh: Decimal,
    ef_kg_co2e_per_kwh: Decimal,
) -> Decimal:
    """
    GHG Protocol Scope 2 Guidance:
    CO2e (tonnes) = Electricity (kWh) * EF (kg CO2e/kWh) / 1000
    """
    return (consumption_kwh * ef_kg_co2e_per_kwh) / Decimal("1000.0")

def oracle_scope2_purchased_steam(
    delivered_heat_mmbtu: Decimal,
    ef_kg_co2e_per_mmbtu: Decimal,
    boiler_efficiency: Decimal = Decimal("0.80"),
    transmission_loss: Decimal = Decimal("0.05"),
    model_mode: str = "multiplicative",
) -> Dict[str, Decimal]:
    """
    API Compendium 2021 Section 8.1.5, Exhibit 8.3:
    Fuel input = Delivered Heat / Net Efficiency
    Thermodynamic standard: Net_Eff = Boiler_Eff * (1 - Loss)
    App defect mode (BUG-06): Net_Eff = Boiler_Eff - Loss
    """
    if model_mode == "multiplicative":
        net_eff = boiler_efficiency * (Decimal("1.0") - transmission_loss)
    elif model_mode == "subtractive":
        net_eff = boiler_efficiency - transmission_loss
    else:
        raise ValueError(f"Unknown mode: {model_mode}")
    
    if net_eff <= 0:
        raise ValueError(f"Net efficiency must be strictly positive: got {net_eff}")
    
    fuel_mmbtu = delivered_heat_mmbtu / net_eff
    co2e_tonnes = (fuel_mmbtu * ef_kg_co2e_per_mmbtu) / Decimal("1000.0")
    return {
        "net_efficiency": net_eff,
        "fuel_mmbtu": fuel_mmbtu,
        "co2e_tonnes": co2e_tonnes,
    }

# =============================================================================
# 6. SCOPE 3 ORACLE EQUATIONS (GHG Protocol Scope 3 Standard)
# =============================================================================

def oracle_scope3_spend_based(
    spend_usd: Decimal,
    ef_kg_co2e_per_usd: Decimal,
) -> Decimal:
    """
    GHG Protocol Scope 3 Cat 1/2 (EEIO):
    CO2e (tonnes) = Spend (USD) * Factor (kg CO2e/USD) / 1000
    """
    return (spend_usd * ef_kg_co2e_per_usd) / Decimal("1000.0")

def oracle_scope3_transport(
    mass_tonne: Decimal,
    distance_km: Decimal,
    ef_kg_co2e_per_tkm: Decimal,
) -> Decimal:
    """
    GHG Protocol Scope 3 Cat 4/9 (GLEC Framework):
    CO2e (tonnes) = Tonnes * Distance (km) * Factor (kg CO2e/t-km) / 1000
    """
    tkm = mass_tonne * distance_km
    return (tkm * ef_kg_co2e_per_tkm) / Decimal("1000.0")

def oracle_scope3_sold_product_use(
    fuel_volume: Decimal,
    fuel_unit: str,
    ef_kg_co2e_per_unit: Decimal,
) -> Decimal:
    """
    GHG Protocol Scope 3 Cat 11 (End-Use Combustion):
    CO2e (tonnes) = Volume Sold * EF / 1000
    """
    return (fuel_volume * ef_kg_co2e_per_unit) / Decimal("1000.0")

# =============================================================================
# 7. DERIVED INTENSITIES & KPIs (OGCI / OGMP / API Section 3)
# =============================================================================

def oracle_carbon_intensity_boe(
    scope1_tco2e: Decimal,
    scope2_tco2e: Decimal,
    production_boe: Decimal,
) -> Decimal:
    """
    OGCI Carbon Intensity Indicator:
    Intensity (kg CO2e/boe) = (Scope 1 + Scope 2) * 1000 / Production (BOE)
    """
    if production_boe <= 0:
        raise ZeroDivisionError("Production BOE must be > 0 for intensity calculation")
    total_kg = (scope1_tco2e + scope2_tco2e) * Decimal("1000.0")
    return total_kg / production_boe

def oracle_flaring_intensity(
    flared_gas_vol_m3: Decimal,
    gross_gas_produced_m3: Decimal,
) -> Decimal:
    """
    Flaring Intensity (%) = (Flared Gas Volume / Gross Gas Produced) * 100%
    """
    if gross_gas_produced_m3 <= 0:
        raise ZeroDivisionError("Gas production must be > 0 for flaring intensity")
    return (flared_gas_vol_m3 / gross_gas_produced_m3) * Decimal("100.0")

def oracle_methane_loss_rate_ngsi(
    total_ch4_emissions_tonnes: Decimal,
    gross_gas_ch4_produced_tonnes: Decimal,
) -> Decimal:
    """
    NGSI / OGCI Methane Loss Rate (%):
    Loss Rate (%) = (Total CH4 Emitted / Gross CH4 Produced) * 100%
    """
    if gross_gas_ch4_produced_tonnes <= 0:
        raise ZeroDivisionError("Produced CH4 mass must be > 0 for methane intensity")
    return (total_ch4_emissions_tonnes / gross_gas_ch4_produced_tonnes) * Decimal("100.0")

# =============================================================================
# 8. GUM UNCERTAINTY PROPAGATION (ISO 14064-1 / Guide 98-3)
# =============================================================================

def oracle_propagate_source_uncertainty(
    activity_rel_1sigma: Decimal,
    ef_rel_1sigma: Decimal,
    coverage_factor_k: Decimal = Decimal("2.0"),
) -> Tuple[Decimal, Decimal]:
    """
    ISO 14064-1 §7.5 / GUM:
    Combined relative standard uncertainty u_c = sqrt(u_A^2 + u_EF^2)
    95% Confidence Interval half-width U_95 = k * u_c
    """
    # Convert to float for sqrt then back to Decimal
    u_c_sq = (activity_rel_1sigma ** Decimal("2")) + (ef_rel_1sigma ** Decimal("2"))
    u_c = Decimal(str(math.sqrt(float(u_c_sq))))
    u_95 = coverage_factor_k * u_c
    return u_c, u_95

def oracle_propagate_inventory_uncertainty(
    source_emissions: List[Decimal],
    source_u95_half_widths: List[Decimal], # in relative fraction (e.g. 0.0566)
) -> Decimal:
    """
    IPCC 2006 Approach 1 RSS Aggregation:
    U_total = sqrt( sum( (E_i * U_i)^2 ) ) / sum(E_i)
    """
    total_e = sum(source_emissions)
    if total_e <= 0:
        return Decimal("0.0")
    sum_sq = Decimal("0.0")
    for e_i, u_i in zip(source_emissions, source_u95_half_widths):
        abs_u = e_i * u_i
        sum_sq += abs_u ** Decimal("2")
    return Decimal(str(math.sqrt(float(sum_sq)))) / total_e
