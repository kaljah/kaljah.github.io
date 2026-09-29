import math
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


# Volume units that can be read at operating conditions. scf / Mscf / Sm3 / Nm3 are standard by
# definition, and energy or mass quantities have no volume to correct.
ACTUAL_VOLUME_UNITS = {"m3", "m³", "cubic_meters", "cubic_meter", "cf", "ft3", "ft³", "acf", "am3", "actual_m3"}


def is_actual_volume_unit(unit):
    return str(unit or "").strip().lower() in ACTUAL_VOLUME_UNITS


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


# Normal m3 (0 C, 101.325 kPa) in the platform's standard m3 (60 F, 14.696 psia; 1 m3 = 35.3147 scf)
NM3_TO_SM3 = STD_TEMP_K / 273.15

VOLUME_UNITS_TO_M3 = {
    "m3": 1.0,
    "m³": 1.0,
    "sm3": 1.0,
    "sm³": 1.0,
    "nm3": NM3_TO_SM3,
    "nm³": NM3_TO_SM3,
    "ksm3": 1000.0,
    "mmsm3": 1_000_000.0,
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
    "kbbl": 158.987295,
    "mbbl": 158.987295,
    "mmbbl": 158987.295,
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
    "tj": 1_000_000.0,
    "terajoule": 1_000_000.0,
    "kbtu": 1.05505585262,
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


def scope3_ef_kg_per_unit(amount, co2e_tonnes, ef=None):
    """The factor as stored on a Scope 3 record: kg CO2e per activity unit (the unit the tables and
    calculation details read), whatever unit it was entered in (t/unit, g/unit, per $1,000)."""
    try:
        amt = float(amount or 0)
        if amt > 0 and co2e_tonnes is not None:
            return float(co2e_tonnes) * 1000.0 / amt
    except (TypeError, ValueError):
        pass
    return ef


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

    # 3. Check numerator dimension
    is_tonne_num = False
    if not any(
        prefix in num for prefix in ["kg", "kilogram", "lb", "pound"]
    ) and not (num.startswith("g") and not num.startswith("gj")):
        if any(
            t in num for t in ["tonne", "metric_ton", "tco2", "mtco2", "t/"]
        ) or num.startswith("t ") or num == "t":
            is_tonne_num = True

    is_gram_num = (
        num.startswith("g ")
        or num.startswith("gco2")
        or num.startswith("g/")
        or "gram" in num
        or num == "g"
    ) and not num.startswith("gj")

    if is_tonne_num:
        return amt_val * ef_val
    elif is_gram_num:
        # Grams CO2e to tonnes CO2e: divide by 1,000,000
        return (amt_val * ef_val) / 1_000_000.0
    elif num.startswith("lb") or "pound" in num:
        # Pounds CO2e to tonnes CO2e: 0.45359237 kg/lb / 1000 kg/t
        return (amt_val * ef_val * 0.45359237) / 1000.0
    else:
        # Standard kg CO2e / unit -> tonnes CO2e
        return (amt_val * ef_val) / 1000.0


# -- Canonical unit parsing (audit RC-5: BUG-011/027/033/047/048/049/051/063/066) ---------------
# Every place that interprets a unit string goes through these helpers. Matching is on exact
# tokens after normalisation, never on substrings ("mmscf" must not match "mscf", "kg" must not
# match "k"), and an unknown unit raises instead of being passed through 1:1.

import re as _re

_SUBSUP = str.maketrans("₀₁₂₃₄₅₆₇₈₉"
                        "⁰¹²³⁴⁵⁶⁷⁸⁹",
                        "01234567890123456789")

# rate suffixes -> periods per year
_RATE_SUFFIX = {"/d": 365.0, "/day": 365.0, "d": 365.0, "pd": 365.0, "/yr": 1.0, "/year": 1.0, "/y": 1.0,
                "/hr": 8760.0, "/h": 8760.0, "/hour": 8760.0}
_VOLUME_ALIASES = {"mmcf": "mmscf", "kscf": "mscf", "mcfd": "mcf/d", "mmscfd": "mmscf/d", "mscfd": "mscf/d",
                   "m^3": "m3", "cubic metre": "m3", "cubic metres": "m3", "knm3": "ksm3", "kncm": "ksm3",
                   "thousand m3": "ksm3", "million m3": "mmsm3", "mmm3": "mmsm3"}
_GASES = {"ch4": "ch4", "methane": "ch4", "co2": "co2", "n2o": "n2o", "co2e": "co2e", "voc": "voc", "gas": "gas",
          "toc": "toc", "thc": "toc"}
_COUNT_WORDS = {"count", "unit", "units", "source", "sources", "device", "devices", "well", "wells", "separator",
                "separators", "compressor", "compressors", "component", "components", "event", "events", "valve",
                "valves", "connector", "connectors", "each", "ea", "no", "pcs", "controller", "controllers",
                "pump", "pumps", "tank", "tanks", "facility", "facilities", "site", "sites", "wellhead", "wellheads",
                "completion", "completions", "heater", "heaters", "header", "headers", "run", "runs", "leak", "leaks",
                "workover", "workovers", "blowdown", "blowdowns", "vessel", "vessels", "dehydrator", "dehydrators"}


class UnitError(ValueError):
    """A unit string that cannot be interpreted unambiguously."""


def norm_unit(unit):
    """Lower-case, ASCII digits for sub/superscripts, single spaces, aliases applied."""
    u = str(unit or "").translate(_SUBSUP).strip().lower()
    u = u.replace("per ", "/").replace(" / ", "/").replace(" /", "/").replace("/ ", "/")
    u = _re.sub(r"\s+", " ", u)
    return _VOLUME_ALIASES.get(u, u)


GAS_VOLUME_UNITS = {"m3", "m³", "sm3", "sm³", "nm3", "nm³", "ksm3", "mmsm3", "cubic_meter", "cubic_meters",
                    "scf", "cf", "ft3", "mscf", "mcf", "mmscf"}


def gas_volume_m3(quantity, unit):
    """A gas volume in standard m3. A gas-composition (carbon balance) method needs a volume:
    an energy, mass or liquid quantity is refused instead of being read as m3."""
    u = str(unit or "").strip().lower().replace(" ", "")
    if u not in GAS_VOLUME_UNITS:
        raise UnitError(f"The gas composition method needs a gas volume (scf, Mscf, MMscf, m3, Sm3, Nm3), not '{unit}'")
    return float(quantity) * VOLUME_UNITS_TO_M3[u]


def unit_dimension(unit):
    """(dimension, factor_to_base) for a plain unit token; bases: m3, kg, MJ, h, count."""
    u = norm_unit(unit).replace(" ", "_")
    for dim, table in (("volume", VOLUME_UNITS_TO_M3), ("mass", MASS_UNITS_TO_KG),
                       ("energy", ENERGY_UNITS_TO_MJ), ("time", TIME_UNITS_TO_HOURS),
                       ("distance", DISTANCE_UNITS_TO_M)):
        if u in table:
            return dim, table[u]
    if u in _COUNT_WORDS:
        return "count", 1.0
    raise UnitError(f"Unknown unit '{unit}'")


def to_base(value, unit, dimension=None):
    dim, f = unit_dimension(unit)
    if dimension and dim != dimension:
        raise UnitError(f"Unit '{unit}' is a {dim} unit, expected {dimension}")
    return float(value) * f


def parse_volume_rate(unit):
    """BUG-011 / BUG-066: 'MMscf/d', 'Mcf/hr', 'm3/yr', 'MMscfd' -> (m3 per unit, periods per year).

    periods_per_year is None for a plain volume.
    """
    u = norm_unit(unit).replace(" ", "")
    u = _VOLUME_ALIASES.get(u, u)
    if u in VOLUME_UNITS_TO_M3:
        return VOLUME_UNITS_TO_M3[u], None
    for suffix in sorted(_RATE_SUFFIX, key=len, reverse=True):
        if u.endswith(suffix) and u[: -len(suffix)]:
            base = u[: -len(suffix)]
            if base in VOLUME_UNITS_TO_M3:
                return VOLUME_UNITS_TO_M3[base], _RATE_SUFFIX[suffix]
    raise UnitError(f"Unknown volume or volume-rate unit '{unit}'")


def annual_volume_m3(value, unit):
    """Annual volume in m3 from a volume (taken as annual) or a rate unit."""
    f, per_year = parse_volume_rate(unit)
    return float(value) * f * (per_year or 1.0)


_SCALE = _re.compile(r"^(?:10\^?(\d+)|1e(\d+)|(thousand|million|billion))\s*")
_SCALE_WORDS = {"thousand": 1e3, "million": 1e6, "billion": 1e9}


def parse_factor_unit(unit):
    """Parse an emission-factor unit such as 'tonne CH4/hr/source', 'tonne CH4/10^6 scf produced',
    'kg/MMBtu', 'kg/scf'.

    Returns dict(mass_kg, gas, denominators=[(dimension, base_factor_per_unit, token)]) where the
    denominator factor already includes any 10^n scale (BUG-049). Raises UnitError when the
    numerator mass or a denominator cannot be interpreted (BUG-063).
    """
    u = norm_unit(unit)
    if "/" not in u:
        raise UnitError(f"Factor unit '{unit}' has no denominator (expected e.g. kg/scf)")
    parts = [p.strip() for p in u.split("/")]
    num = parts[0].split()
    if not num:
        raise UnitError(f"Factor unit '{unit}' has no numerator")
    mass_tok, gas = num[0], None
    for tok in num[1:]:
        if tok in _GASES:
            gas = _GASES[tok]
    if mass_tok not in MASS_UNITS_TO_KG:
        # compound numerators: "tco2", "kgch4", "tco2e", "mtco2"
        for g in sorted(_GASES, key=len, reverse=True):
            if mass_tok.endswith(g) and mass_tok[: -len(g)] in MASS_UNITS_TO_KG:
                mass_tok, gas = mass_tok[: -len(g)], _GASES[g]
                break
    if mass_tok not in MASS_UNITS_TO_KG:
        raise UnitError(f"Factor unit '{unit}': numerator '{mass_tok}' is not a mass unit")
    dens = []
    for p in parts[1:]:
        scale = 1.0
        m = _SCALE.match(p)
        if m:
            if m.group(1) or m.group(2):
                scale = 10.0 ** int(m.group(1) or m.group(2))
            else:
                scale = _SCALE_WORDS[m.group(3)]
            p = p[m.end():]
        toks = p.split()
        if not toks:
            raise UnitError(f"Factor unit '{unit}' has an empty denominator")
        tok = toks[0]
        if "-" in tok and tok not in ("tonne-km", "passenger-km"):
            # compound denominators such as "well-year" = per well per year
            for sub in tok.split("-"):
                dim, f = unit_dimension(sub)
                dens.append((dim, f, sub))
            continue
        dim, f = unit_dimension(tok)
        dens.append((dim, f * scale, tok))
    return {"mass_kg": MASS_UNITS_TO_KG[mass_tok], "gas": gas, "denominators": dens}


def factor_to_kg_per_activity(factor_value, factor_unit, activity_unit, hours=None, hhv_mj_per_unit=None):
    """kg of pollutant per ONE activity unit (BUG-047/049/051/063).

    - A volume/mass/energy denominator is converted to the activity unit (energy <-> volume/mass
      needs the heating value in MJ per activity unit, else UnitError).
    - A time denominator ('/hr') is multiplied by `hours`, which is required.
    - Count denominators ('/source', '/well') pair with a count activity.
    """
    spec = parse_factor_unit(factor_unit)
    kg = float(factor_value) * spec["mass_kg"]
    a_dim, a_f = unit_dimension(activity_unit)
    matched = False
    for dim, f, tok in spec["denominators"]:
        if dim == "time":
            if hours is None:
                raise UnitError(f"Factor unit '{factor_unit}' is per {tok}: operating hours are required")
            kg *= float(hours) / f  # f = hours in one time unit
            continue
        if matched:
            if dim == "count":
                continue
            raise UnitError(f"Factor unit '{factor_unit}' has more than one activity denominator")
        if dim == a_dim:
            kg *= a_f / f
        elif dim == "energy" and a_dim in ("volume", "mass"):
            if not hhv_mj_per_unit:
                raise UnitError(f"Energy-based factor '{factor_unit}' needs the fuel heating value for '{activity_unit}'")
            kg *= float(hhv_mj_per_unit) / f
        elif dim == "count" and a_dim != "count":
            raise UnitError(f"Factor unit '{factor_unit}' is per {tok} but the activity is in '{activity_unit}'")
        else:
            raise UnitError(f"Factor unit '{factor_unit}' cannot be applied to activity unit '{activity_unit}'")
        matched = True
    if not matched and a_dim != "count":
        raise UnitError(f"Factor unit '{factor_unit}' has no denominator compatible with '{activity_unit}'")
    return kg


def per_source_hour_kg(value, unit):
    """BUG-048: (kg per source per hour, is_ch4) for an equipment / component leak factor.

    'tonne CH4/hr/source' -> (value*1000, True); 'kg TOC/hr/component' -> (value, False);
    'tonnes CH4/yr' -> (value*1000/8760, True). A factor without a time basis raises.
    """
    spec = parse_factor_unit(unit)
    hours = [f for d, f, _ in spec["denominators"] if d == "time"]
    if not hours:
        raise UnitError(f"Leak factor unit '{unit}' has no time basis (expected e.g. kg/hr/source)")
    per = 1.0
    for h in hours:
        per *= h
    return float(value) * spec["mass_kg"] / per, spec["gas"] == "ch4"


# -- Gas composition (audit RC-8: BUG-023 / BUG-024) -------------------------------------
COMPOSITION_KEYS = ("c1", "c2", "c3", "c4", "c5", "c6", "c7", "c8", "c9", "c10", "co2", "n2", "h2s", "other")


def composition_fractions(raw, basis=None):
    """Convert one gas analysis to mole fractions, deciding percent vs fraction ONCE.

    `raw` maps component -> value as entered. The basis is "percent" when requested, or when
    any component exceeds 1 or the analysis sums above 1.5; otherwise "fraction". Every
    component (including CO2, N2, H2S) is scaled the same way, so a 1.0 mol% butane can no
    longer become 100 %. A total above 100 % (+0.5 % rounding) is rejected; an analysis within
    98-102 % is renormalised to 100 %; an incomplete analysis is used as given (the rest is
    unspecified, not redistributed).
    Returns (fractions, info) with info = {"basis", "total", "renormalised"}.
    """
    vals = {}
    for k, v in (raw or {}).items():
        if v in (None, "", "-"):
            continue
        x = float(str(v).replace("%", "").strip())
        if not math.isfinite(x) or x < 0:
            raise ValueError(f"Gas composition '{k}' must be a finite, non-negative number")
        vals[k] = x
    if not vals:
        return {}, {"basis": None, "total": 0.0, "renormalised": False}
    total = sum(vals.values())
    if basis is None:
        basis = "percent" if (max(vals.values()) > 1.0 or total > 1.5) else "fraction"
    scale = 0.01 if basis == "percent" else 1.0
    fr = {k: v * scale for k, v in vals.items()}
    tot = sum(fr.values())
    if tot > 1.005:
        raise ValueError(f"Gas composition sums to {tot * 100:.2f} % (> 100 %)")
    renorm = 0.98 <= tot < 0.99999 or 1.00001 < tot <= 1.005
    if renorm:
        fr = {k: v / tot for k, v in fr.items()}
    return fr, {"basis": basis, "total": tot, "renormalised": renorm}
