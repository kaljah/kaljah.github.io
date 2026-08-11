from .constants import DEFAULT_GWP, get_active_gwp

# Standard Thermodynamic Conditions (API Compendium 2021 §4.2.1, ISO 13443)
# T_std = 60°F = 15.56°C = 288.71 K = 519.67 °R
# P_std = 14.696 psia = 101.325 kPa = 1.01325 bar = 1.0 atm
STD_TEMP_K = 288.706
STD_TEMP_R = 519.67
STD_TEMP_C = 15.556
STD_TEMP_F = 60.0

STD_PRESSURE_PSIA = 14.696
STD_PRESSURE_KPA = 101.325
STD_PRESSURE_BAR = 1.01325

CONVERSIONS = {
    # Volume
    "scf_to_m3": 0.0283168,
    "m3_to_scf": 35.3147,
    "bbl_to_m3": 0.158987,
    "m3_to_bbl": 6.28981,
    "gal_to_m3": 0.00378541,
    "m3_to_gal": 264.172,
    "liter_to_m3": 0.001,
    "m3_to_liter": 1000.0,
    "l_to_gal": 0.264172,  # 1 liter = 0.264172 US gallons
    "gal_to_l": 3.78541,  # 1 US gallon = 3.78541 liters
    "bbl_to_gal": 42.0,
    "mmscf_to_m3": 28316.8,
    "m3_to_mmscf": 3.53147e-5,
    "mcf_to_scf": 1000.0,
    "scf_to_mcf": 0.001,
    # Mass
    "lb_to_kg": 0.453592,
    "kg_to_lb": 2.20462,
    "tonne_to_kg": 1000.0,
    "short_ton_to_kg": 907.185,
    "long_ton_to_kg": 1016.05,
    # Energy
    "btu_to_kj": 1.05506,
    "mj_to_btu": 947.817,
    "mmbtu_to_mj": 1055.06,
    "mj_to_mmbtu": 0.000947817,
    "kwh_to_mj": 3.6,
    "mj_to_kwh": 0.277778,
    "therm_to_mj": 105.506,
    # Gas Densities (kg/m3 at standard conditions: 60F, 14.696 psia)
    "density_ch4": 0.6785,
    "density_c2h6": 1.282,  # Ethane
    "density_c3h8": 1.882,  # Propane
    "density_c4h10": 2.519,  # n-Butane
    "density_co2": 1.861,
    "density_n2o": 1.860,
    # GWP (GHG Protocol AR5)
    "gwp_ch4": DEFAULT_GWP["CH4"],
    "gwp_n2o": DEFAULT_GWP["N2O"],
    # Global Warming Potentials (Comparison Reference)
    "GWP_AR4": {"ch4": 25, "n2o": 298},
    "GWP_AR5": DEFAULT_GWP,
    "GWP_AR6": {"ch4": 27.9, "n2o": 273},
}


def to_kelvin(val, unit="c"):
    """Converts temperature value to Kelvin."""
    if val is None:
        return STD_TEMP_K
    u = str(unit).strip().lower()
    v = float(val)
    if u in ["c", "celsius", "degc", "°c"]:
        return v + 273.15
    elif u in ["f", "fahrenheit", "degf", "°f"]:
        return (v - 32.0) * 5.0 / 9.0 + 273.15
    elif u in ["r", "rankine", "degr", "°r"]:
        return v * 5.0 / 9.0
    elif u in ["k", "kelvin"]:
        return v
    return v + 273.15


def to_fahrenheit(val, unit="c"):
    """Converts temperature value to Fahrenheit."""
    if val is None:
        return STD_TEMP_F
    u = str(unit).strip().lower()
    v = float(val)
    if u in ["c", "celsius", "degc", "°c"]:
        return (v * 9.0 / 5.0) + 32.0
    elif u in ["f", "fahrenheit", "degf", "°f"]:
        return v
    elif u in ["k", "kelvin"]:
        return (v - 273.15) * 9.0 / 5.0 + 32.0
    elif u in ["r", "rankine", "degr", "°r"]:
        return v - 459.67
    return v


def to_psia(val, unit="psig", atmospheric_psia=STD_PRESSURE_PSIA):
    """Converts gauge or metric pressure to absolute pressure in psia."""
    if val is None:
        return STD_PRESSURE_PSIA
    u = str(unit).strip().lower()
    v = float(val)
    if u in ["psig", "psi_g"]:
        return max(0.0, v + atmospheric_psia)
    elif u in ["psia", "psi_a", "psi"]:
        return max(0.0, v)
    elif u in ["barg", "bar_g"]:
        return max(0.0, (v * 14.5038) + atmospheric_psia)
    elif u in ["bar", "bara"]:
        return max(0.0, v * 14.5038)
    elif u in ["kpag", "kpa_g"]:
        return max(0.0, (v * 0.145038) + atmospheric_psia)
    elif u in ["kpa", "kpaa"]:
        return max(0.0, v * 0.145038)
    elif u in ["atm"]:
        return max(0.0, v * STD_PRESSURE_PSIA)
    return max(0.0, v + atmospheric_psia)


def normalize_gas_volume_to_standard(
    volume,
    operating_temp=None,
    temp_unit="C",
    operating_press=None,
    press_unit="psig",
    z_factor=1.0,
):
    """
    API Compendium 2021 §4.2.1: Converts gas volume measured at actual/operating conditions
    to standard conditions (60°F / 15.56°C, 14.696 psia / 101.325 kPa).

    V_std = V_meas * (P_meas_abs / P_std) * (T_std / T_meas_abs) * (1 / Z)
    """
    if volume is None:
        return 0.0
    vol = float(volume)
    if vol <= 0.0:
        return 0.0

    # Temperature factor
    if operating_temp is not None and str(operating_temp).strip() != "":
        t_meas_k = to_kelvin(operating_temp, temp_unit)
        t_factor = STD_TEMP_K / max(1.0, t_meas_k)
    else:
        t_factor = 1.0

    # Pressure factor
    if operating_press is not None and str(operating_press).strip() != "":
        p_meas_psia = to_psia(operating_press, press_unit)
        p_factor = p_meas_psia / STD_PRESSURE_PSIA
    else:
        p_factor = 1.0

    z = float(z_factor) if z_factor and float(z_factor) > 0 else 1.0

    return vol * p_factor * t_factor * (1.0 / z)


def convert(value, from_unit, to_unit):
    """Simple unit conversion wrapper."""
    if from_unit == to_unit:
        return value
    key = f"{from_unit}_to_{to_unit}"
    if key in CONVERSIONS:
        return value * CONVERSIONS[key]

    # Reverse conversion
    rev_key = f"{to_unit}_to_{from_unit}"
    if rev_key in CONVERSIONS:
        return value / CONVERSIONS[rev_key]

    raise ValueError(f"Unsupported conversion: {from_unit} to {to_unit}")


def calculate_co2e(
    co2=0, ch4=0, n2o=0, gwp_dict=None, gwp_standard=None, horizon="100"
):
    """Calculates CO2e using dynamically resolved GWPs (AR4/AR5/AR6)."""
    gwp = get_active_gwp(standard=gwp_standard, gwp_dict=gwp_dict, horizon=horizon)
    co2_val = float(co2 or 0)
    ch4_val = float(ch4 or 0)
    n2o_val = float(n2o or 0)
    return (
        (co2_val * gwp.get("CO2", 1.0))
        + (ch4_val * gwp.get("CH4", 28.0))
        + (n2o_val * gwp.get("N2O", 265.0))
    )
