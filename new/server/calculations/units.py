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
    # Volume (API Compendium 2021 §4.2 / ISO 13443 at 60°F, 14.696 psia)
    "scf_to_m3": 0.028316846592,
    "m3_to_scf": 35.314666721,
    "mscf_to_m3": 28.316846592,
    "m3_to_mscf": 0.035314666721,
    "mcf_to_m3": 28.316846592,
    "m3_to_mcf": 0.035314666721,
    "mmscf_to_m3": 28316.846592,
    "m3_to_mmscf": 3.5314666721e-5,
    "bbl_to_m3": 0.158987295,
    "m3_to_bbl": 6.28981077,
    "gal_to_m3": 0.003785411784,
    "m3_to_gal": 264.172052,
    "liter_to_m3": 0.001,
    "m3_to_liter": 1000.0,
    "l_to_gal": 0.264172052,
    "gal_to_l": 3.785411784,
    "bbl_to_gal": 42.0,
    "mcf_to_scf": 1000.0,
    "scf_to_mcf": 0.001,
    "mscf_to_scf": 1000.0,
    "scf_to_mscf": 0.001,
    "mmscf_to_scf": 1_000_000.0,
    "scf_to_mmscf": 1e-6,
    # Mass (Exact NIST Avoirdupois standards)
    "lb_to_kg": 0.45359237,
    "kg_to_lb": 2.2046226218487757,
    "tonne_to_kg": 1000.0,
    "short_ton_to_kg": 907.18474,
    "long_ton_to_kg": 1016.0469088,
    # Energy (ISO 31-4 / NIST standard BTU and MJ definitions)
    "btu_to_kj": 1.05505585262,
    "mj_to_btu": 947.8171203133172,
    "mmbtu_to_mj": 1055.05585262,
    "mj_to_mmbtu": 0.0009478171203133172,
    "kwh_to_mj": 3.6,
    "mj_to_kwh": 0.2777777777777778,
    "therm_to_mj": 105.4804,
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
    elif u in ["mbarg", "mbar_g"]:
        return max(0.0, (v * 0.0145038) + atmospheric_psia)
    elif u in ["mbar", "mbara"]:
        return max(0.0, v * 0.0145038)
    elif u in ["kpag", "kpa_g"]:
        return max(0.0, (v * 0.145038) + atmospheric_psia)
    elif u in ["kpa", "kpaa"]:
        return max(0.0, v * 0.145038)
    elif u in ["mpag", "mpa_g"]:
        return max(0.0, (v * 145.0377) + atmospheric_psia)
    elif u in ["mpa", "mpaa"]:
        return max(0.0, v * 145.0377)
    elif u in ["pa", "paa"]:
        return max(0.0, v * 0.000145038)
    elif u in ["pag", "pa_g"]:
        return max(0.0, (v * 0.000145038) + atmospheric_psia)
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


VOLUME_UNITS_TO_M3 = {
    "m3": 1.0,
    "m³": 1.0,
    "cubic_meter": 1.0,
    "cubic_meters": 1.0,
    "scf": 0.028316846592,
    "cf": 0.028316846592,
    "ft3": 0.028316846592,
    "mscf": 28.316846592,
    "mcf": 28.316846592,
    "mmscf": 28316.846592,
    "bbl": 0.158987295,
    "barrel": 0.158987295,
    "barrels": 0.158987295,
    "gal": 0.003785411784,
    "gallon": 0.003785411784,
    "gallons": 0.003785411784,
    "l": 0.001,
    "liter": 0.001,
    "liters": 0.001,
}

MASS_UNITS_TO_KG = {
    "kg": 1.0,
    "kgs": 1.0,
    "kilogram": 1.0,
    "kilograms": 1.0,
    "g": 0.001,
    "gram": 0.001,
    "grams": 0.001,
    "tonne": 1000.0,
    "tonnes": 1000.0,
    "metric_ton": 1000.0,
    "metric_tons": 1000.0,
    "mt": 1000.0,
    "t": 1000.0,
    "lb": 0.45359237,
    "lbs": 0.45359237,
    "pound": 0.45359237,
    "pounds": 0.45359237,
    "ton": 907.18474,
    "tons": 907.18474,
    "short_ton": 907.18474,
    "short_tons": 907.18474,
    "us_ton": 907.18474,
    "long_ton": 1016.0469088,
    "long_tons": 1016.0469088,
}

ENERGY_UNITS_TO_MJ = {
    "mj": 1.0,
    "megajoule": 1.0,
    "megajoules": 1.0,
    "kj": 0.001,
    "kilojoule": 0.001,
    "kilojoules": 0.001,
    "gj": 1000.0,
    "gigajoule": 1000.0,
    "gigajoules": 1000.0,
    "btu": 0.00105505585262,
    "btus": 0.00105505585262,
    "mmbtu": 1055.05585262,
    "mm_btu": 1055.05585262,
    "kwh": 3.6,
    "kilowatt_hour": 3.6,
    "mwh": 3600.0,
    "megawatt_hour": 3600.0,
    "therm": 105.4804,
    "therms": 105.4804,
}


def to_celsius(val, unit="c"):
    """Converts temperature value to Celsius."""
    if val is None:
        return STD_TEMP_C
    u = str(unit).strip().lower()
    v = float(val)
    if u in ["c", "celsius", "degc", "°c"]:
        return v
    elif u in ["f", "fahrenheit", "degf", "°f"]:
        return (v - 32.0) * 5.0 / 9.0
    elif u in ["k", "kelvin"]:
        return v - 273.15
    elif u in ["r", "rankine", "degr", "°r"]:
        return (v - 491.67) * 5.0 / 9.0
    return v


def from_psia(psia_val, to_unit="psia", atmospheric_psia=STD_PRESSURE_PSIA):
    """Converts absolute psia pressure to any target unit (gauge or absolute)."""
    if psia_val is None:
        return 0.0
    u = str(to_unit).strip().lower()
    p = float(psia_val)
    if u in ["psia", "psi_a", "psi"]:
        return p
    elif u in ["psig", "psi_g"]:
        return p - atmospheric_psia
    elif u in ["barg", "bar_g"]:
        return (p - atmospheric_psia) / 14.5038
    elif u in ["bar", "bara"]:
        return p / 14.5038
    elif u in ["kpag", "kpa_g"]:
        return (p - atmospheric_psia) / 0.145038
    elif u in ["kpa", "kpaa"]:
        return p / 0.145038
    elif u in ["mpag", "mpa_g"]:
        return (p - atmospheric_psia) / 145.0377
    elif u in ["mpa", "mpaa"]:
        return p / 145.0377
    elif u in ["atm"]:
        return p / STD_PRESSURE_PSIA
    elif u in ["mbar", "mbara"]:
        return p / 0.0145038
    elif u in ["mbarg", "mbar_g"]:
        return (p - atmospheric_psia) / 0.0145038
    elif u in ["pa", "paa"]:
        return p / 0.000145038
    elif u in ["pag", "pa_g"]:
        return (p - atmospheric_psia) / 0.000145038
    return p


def convert_temperature(val, from_unit, to_unit):
    """Converts temperature value across C, F, K, R."""
    k = to_kelvin(val, from_unit)
    u_to = str(to_unit).strip().lower()
    if u_to in ["k", "kelvin"]:
        return k
    elif u_to in ["c", "celsius", "degc", "°c"]:
        return k - 273.15
    elif u_to in ["f", "fahrenheit", "degf", "°f"]:
        return (k - 273.15) * 9.0 / 5.0 + 32.0
    elif u_to in ["r", "rankine", "degr", "°r"]:
        return k * 9.0 / 5.0
    return k


def convert_pressure(val, from_unit, to_unit, atmospheric_psia=STD_PRESSURE_PSIA):
    """Converts pressure value across psia, psig, bar, barg, kpa, kpag, mpa, mpag, atm, pa, mbar."""
    psia = to_psia(val, from_unit, atmospheric_psia=atmospheric_psia)
    return from_psia(psia, to_unit, atmospheric_psia=atmospheric_psia)


DISTANCE_UNITS_TO_M = {
    "m": 1.0,
    "meter": 1.0,
    "meters": 1.0,
    "km": 1000.0,
    "kilometer": 1000.0,
    "kilometers": 1000.0,
    "mile": 1609.344,
    "miles": 1609.344,
    "mi": 1609.344,
    "ft": 0.3048,
    "foot": 0.3048,
    "feet": 0.3048,
    "yd": 0.9144,
    "yard": 0.9144,
    "yards": 0.9144,
    "nmi": 1852.0,
    "nautical_mile": 1852.0,
}

FREIGHT_UNITS_TO_TONNE_KM = {
    "tonne-km": 1.0,
    "t-km": 1.0,
    "tkm": 1.0,
    "tonne_km": 1.0,
    "ton-mile": 1.459972,
    "ton_mile": 1.459972,
    "tonmile": 1.459972,
}

PASSENGER_UNITS_TO_PKM = {
    "passenger-km": 1.0,
    "p-km": 1.0,
    "pkm": 1.0,
    "passenger_km": 1.0,
    "passenger-mile": 1.609344,
    "p-mile": 1.609344,
    "pmile": 1.609344,
    "passenger_mile": 1.609344,
}

TIME_UNITS_TO_HOURS = {
    "hr": 1.0,
    "hrs": 1.0,
    "hour": 1.0,
    "hours": 1.0,
    "h": 1.0,
    "day": 24.0,
    "days": 24.0,
    "d": 24.0,
    "min": 1.0 / 60.0,
    "minute": 1.0 / 60.0,
    "minutes": 1.0 / 60.0,
    "sec": 1.0 / 3600.0,
    "second": 1.0 / 3600.0,
    "seconds": 1.0 / 3600.0,
    "yr": 8760.0,
    "year": 8760.0,
    "years": 8760.0,
}

LIQUID_FLOW_UNITS_TO_M3_HR = {
    "m3/hr": 1.0,
    "m3/h": 1.0,
    "m3_per_hr": 1.0,
    "gph": 0.003785411784,
    "gal/hr": 0.003785411784,
    "lph": 0.001,
    "l/hr": 0.001,
    "liter/hr": 0.001,
    "bph": 0.158987295,
    "bbl/hr": 0.158987295,
    "bpd": 0.158987295 / 24.0,
    "bbl/day": 0.158987295 / 24.0,
}

TEMP_UNITS = {
    "c", "celsius", "degc", "°c",
    "f", "fahrenheit", "degf", "°f",
    "k", "kelvin",
    "r", "rankine", "degr", "°r",
}

PRESS_UNITS = {
    "psia", "psi_a", "psi", "psig", "psi_g",
    "bar", "bara", "barg", "bar_g",
    "kpa", "kpaa", "kpag", "kpa_g",
    "mpa", "mpaa", "mpag", "mpa_g",
    "atm",
    "pa", "paa", "pag", "pa_g",
    "mbar", "mbara", "mbarg", "mbar_g",
}

ALL_DIMENSION_MAPS = [
    VOLUME_UNITS_TO_M3,
    MASS_UNITS_TO_KG,
    ENERGY_UNITS_TO_MJ,
    DISTANCE_UNITS_TO_M,
    FREIGHT_UNITS_TO_TONNE_KM,
    PASSENGER_UNITS_TO_PKM,
    TIME_UNITS_TO_HOURS,
    LIQUID_FLOW_UNITS_TO_M3_HR,
]


def convert(value, from_unit, to_unit):
    """Simple unit conversion wrapper supporting direct keys, dimensional base units, temperatures, and pressures."""
    if value is None:
        return 0.0
    val = float(value)
    u_from = str(from_unit).strip().lower()
    u_to = str(to_unit).strip().lower()
    if u_from == u_to:
        return val

    # Direct / reverse lookup in legacy CONVERSIONS
    key = f"{u_from}_to_{u_to}"
    if key in CONVERSIONS:
        return val * CONVERSIONS[key]

    rev_key = f"{u_to}_to_{u_from}"
    if rev_key in CONVERSIONS:
        return val / CONVERSIONS[rev_key]

    # Temperature conversions
    if u_from in TEMP_UNITS and u_to in TEMP_UNITS:
        return convert_temperature(val, u_from, u_to)

    # Pressure conversions
    if u_from in PRESS_UNITS and u_to in PRESS_UNITS:
        return convert_pressure(val, u_from, u_to)

    # Dimensional base-unit conversions
    for dim_map in ALL_DIMENSION_MAPS:
        if u_from in dim_map and u_to in dim_map:
            val_base = val * dim_map[u_from]
            return val_base / dim_map[u_to]

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


def normalize_efficiency(eff_val, default=0.0):
    """
    Defensively normalizes efficiency inputs provided as either fractional ratios (0.0 - 1.0)
    or percentages (1.0 - 100.0) into a bounded 0.0 - 1.0 float.
    Traps negative numbers and percentages > 1.0 to prevent negative emission inversions.
    """
    if eff_val in [None, "", "-"]:
        return default
    try:
        val = float(str(eff_val).replace("%", "").strip())
    except (ValueError, TypeError):
        return default
    if val < 0.0:
        return 0.0
    if val > 1.0:
        val /= 100.0
    return max(0.0, min(1.0, val))


# Common alias for internal module usage
_normalize_efficiency = normalize_efficiency


def compute_scope3_co2e(
    amt: float, ef: float, ef_unit: str = "", calc_method: str = ""
) -> float:
    """
    Authoritatively calculates Scope 3 CO2e in metric tonnes from activity amount and emission factor.

    Robustly distinguishes numerator GHG mass unit (t vs kg vs g) from denominator activity unit (e.g. tonne, liter, m3).
    - If factor is spend-based / EEIO (e.g. per $1,000 spend, or method containing 'eeio'):
      divide by 1,000,000 (kg -> tonnes and / 1000 spend).
    - If numerator is tonnes CO2e (e.g. 'tCO2e/unit', 'tonne CO2e/bbl', 't/bbl', 'mtCO2e/t'):
      co2e = amt * ef
    - If numerator is kg CO2e (default standard, e.g. 'kg CO2e/liter', 'kg CO2e/tonne', 'kg/unit'):
      co2e = (amt * ef) / 1000.0
    """
    try:
        amt_val = float(amt or 0.0)
        ef_val = float(ef or 0.0)
    except (ValueError, TypeError):
        return 0.0

    if amt_val <= 0.0 or ef_val <= 0.0:
        return 0.0

    unit_str = str(ef_unit or "").lower().strip()
    method_str = str(calc_method or "").lower().strip()

    # 1. EEIO / spend-based per-$1,000 factor check
    is_per_thousand = any(
        k in unit_str for k in ["1000", "1,000", "1k", "$1000", "$1k"]
    ) or (
        "eeio" in method_str
        and not any(t in unit_str for t in ["tonne", "tco2", "mtco2"])
    )
    if is_per_thousand:
        return (amt_val * ef_val) / 1_000_000.0

    # 2. Extract numerator before '/' or ' per '
    num = unit_str.split("/")[0].split(" per ")[0].strip()

    # 3. Check if numerator specifies tonnes CO2e
    # Must NOT be kg, g, or lb
    is_tonne_num = False
    if not any(
        prefix in num for prefix in ["kg", "kilogram", " g", "gram", "lb", "pound"]
    ):
        if any(
            t in num for t in ["tonne", "metric_ton", "tco2", "mtco2", "t/"]
        ) or num.startswith("t ") or num == "t":
            is_tonne_num = True

    if is_tonne_num:
        return amt_val * ef_val
    else:
        # Standard kg CO2e / unit -> tonnes CO2e
        return (amt_val * ef_val) / 1000.0
