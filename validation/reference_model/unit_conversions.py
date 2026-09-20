"""
Independent Unit Conversion & Thermodynamic Normalization Engine.
Source of Truth: API Compendium 2021 §4.2.1, ISO 13443, NIST SP 811.
Pure mathematical reference implementation - zero production dependencies.
"""
import math

STD_T_K = 288.706      # 60.0 F = 15.556 C
STD_T_F = 60.0
STD_P_PSIA = 14.696    # 101.325 kPa = 1.01325 bar

DENSITY_CH4_STD = 0.6785   # kg/m3 at 60F, 14.696 psia
DENSITY_CO2_STD = 1.8610   # kg/m3 at 60F, 14.696 psia
DENSITY_N2O_STD = 1.8600   # kg/m3 at 60F, 14.696 psia

VOLUME_TO_M3 = {
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
    "bbl": 0.158987294928,
    "barrel": 0.158987294928,
    "barrels": 0.158987294928,
    "gal": 0.003785411784,
    "gallon": 0.003785411784,
    "gallons": 0.003785411784,
    "l": 0.001,
    "liter": 0.001,
    "liters": 0.001,
}

MASS_TO_KG = {
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
    "us_ton": 907.18474,
    "long_ton": 1016.0469088,
}

ENERGY_TO_MJ = {
    "mj": 1.0,
    "megajoule": 1.0,
    "megajoules": 1.0,
    "kj": 0.001,
    "kilojoule": 0.001,
    "gj": 1000.0,
    "gigajoule": 1000.0,
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

DISTANCE_TO_M = {
    "m": 1.0,
    "meter": 1.0,
    "km": 1000.0,
    "kilometer": 1000.0,
    "mile": 1609.344,
    "miles": 1609.344,
    "mi": 1609.344,
    "ft": 0.3048,
    "foot": 0.3048,
    "yd": 0.9144,
    "yard": 0.9144,
    "nmi": 1852.0,
    "in": 0.0254,
    "inch": 0.0254,
    "inches": 0.0254,
    "cm": 0.01,
    "centimeter": 0.01,
    "centimeters": 0.01,
    "mm": 0.001,
    "millimeter": 0.001,
    "millimeters": 0.001,
}

FREIGHT_TO_TONNE_KM = {
    "tonne-km": 1.0,
    "t-km": 1.0,
    "tkm": 1.0,
    "tonne_km": 1.0,
    "ton-mile": 1.459972,
    "ton_mile": 1.459972,
}

PASSENGER_TO_PKM = {
    "passenger-km": 1.0,
    "p-km": 1.0,
    "pkm": 1.0,
    "passenger_km": 1.0,
    "passenger-mile": 1.609344,
    "p-mile": 1.609344,
}

TIME_TO_HOURS = {
    "hr": 1.0,
    "hrs": 1.0,
    "hour": 1.0,
    "hours": 1.0,
    "h": 1.0,
    "day": 24.0,
    "days": 24.0,
    "min": 1.0 / 60.0,
    "minute": 1.0 / 60.0,
    "sec": 1.0 / 3600.0,
    "second": 1.0 / 3600.0,
    "yr": 8760.0,
    "year": 8760.0,
}

LIQUID_FLOW_TO_M3_HR = {
    "m3/hr": 1.0,
    "m3/h": 1.0,
    "gph": 0.003785411784,
    "gal/hr": 0.003785411784,
    "lph": 0.001,
    "l/hr": 0.001,
    "bph": 0.158987294928,
    "bbl/hr": 0.158987294928,
    "bpd": 0.158987294928 / 24.0,
    "bbl/day": 0.158987294928 / 24.0,
}

ALL_DIMENSIONS = [
    VOLUME_TO_M3,
    MASS_TO_KG,
    ENERGY_TO_MJ,
    DISTANCE_TO_M,
    FREIGHT_TO_TONNE_KM,
    PASSENGER_TO_PKM,
    TIME_TO_HOURS,
    LIQUID_FLOW_TO_M3_HR,
]


def to_kelvin(val, unit="c"):
    if val is None:
        return STD_T_K
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
    k = to_kelvin(val, unit)
    return (k - 273.15) * 9.0 / 5.0 + 32.0


def to_psia(val, unit="psig", atmospheric_psia=STD_P_PSIA):
    if val is None:
        return STD_P_PSIA
    u = str(unit).strip().lower()
    v = float(val)
    if u in ["psig", "psi_g"]:
        return max(0.0, v + atmospheric_psia)
    elif u in ["psia", "psi_a", "psi"]:
        return max(0.0, v)
    elif u in ["barg", "bar_g"]:
        return max(0.0, (v * 14.50377377) + atmospheric_psia)
    elif u in ["bar", "bara"]:
        return max(0.0, v * 14.50377377)
    elif u in ["kpag", "kpa_g"]:
        return max(0.0, (v * 0.1450377377) + atmospheric_psia)
    elif u in ["kpa", "kpaa"]:
        return max(0.0, v * 0.1450377377)
    elif u in ["mpag", "mpa_g"]:
        return max(0.0, (v * 145.0377377) + atmospheric_psia)
    elif u in ["mpa", "mpaa"]:
        return max(0.0, v * 145.0377377)
    elif u in ["atm"]:
        return max(0.0, v * STD_P_PSIA)
    elif u in ["pa", "paa"]:
        return max(0.0, v * 0.0001450377377)
    elif u in ["pag", "pa_g"]:
        return max(0.0, (v * 0.0001450377377) + atmospheric_psia)
    elif u in ["mbar", "mbara"]:
        return max(0.0, v * 0.01450377377)
    elif u in ["mbarg", "mbar_g"]:
        return max(0.0, (v * 0.01450377377) + atmospheric_psia)
    return max(0.0, v + atmospheric_psia)


def normalize_to_standard_volume(
    volume,
    operating_temp=None,
    temp_unit="C",
    operating_press=None,
    press_unit="psig",
    z_factor=1.0,
):
    """
    API Compendium 2021 §4.2.1: Converts gas volume at actual conditions to standard volume.
    V_std = V_meas * (P_meas_abs / P_std) * (T_std / T_meas_abs) * (1 / Z)
    """
    if volume is None:
        return 0.0
    vol = float(volume)
    if vol <= 0.0:
        return 0.0

    t_factor = 1.0
    if operating_temp is not None and str(operating_temp).strip() != "":
        t_k = to_kelvin(operating_temp, temp_unit)
        t_factor = STD_T_K / max(1.0, t_k)

    p_factor = 1.0
    if operating_press is not None and str(operating_press).strip() != "":
        p_psia = to_psia(operating_press, press_unit)
        p_factor = p_psia / STD_P_PSIA

    z = float(z_factor) if z_factor and float(z_factor) > 0 else 1.0
    return vol * p_factor * t_factor * (1.0 / z)


class IndependentUnitConverter:
    @staticmethod
    def convert(value, from_unit, to_unit):
        if value is None:
            return 0.0
        val = float(value)
        u_from = str(from_unit).strip().lower()
        u_to = str(to_unit).strip().lower()
        if u_from == u_to:
            return val

        # Temperature conversions
        temp_set = {"c", "celsius", "degc", "°c", "f", "fahrenheit", "degf", "°f", "k", "kelvin", "r", "rankine", "degr", "°r"}
        if u_from in temp_set and u_to in temp_set:
            k = to_kelvin(val, u_from)
            if u_to in ["k", "kelvin"]:
                return k
            elif u_to in ["c", "celsius", "degc", "°c"]:
                return k - 273.15
            elif u_to in ["f", "fahrenheit", "degf", "°f"]:
                return (k - 273.15) * 9.0 / 5.0 + 32.0
            elif u_to in ["r", "rankine", "degr", "°r"]:
                return k * 9.0 / 5.0

        # Pressure conversions
        press_set = {"psia", "psig", "bar", "barg", "kpa", "kpag", "mpa", "mpag", "atm", "pa", "pag", "mbar", "mbarg"}
        if u_from in press_set and u_to in press_set:
            psia = to_psia(val, u_from)
            if u_to in ["psia", "psi"]:
                return psia
            elif u_to in ["psig"]:
                return psia - STD_P_PSIA
            elif u_to in ["bar", "bara"]:
                return psia / 14.50377377
            elif u_to in ["barg"]:
                return (psia - STD_P_PSIA) / 14.50377377
            elif u_to in ["kpa", "kpaa"]:
                return psia / 0.1450377377
            elif u_to in ["kpag"]:
                return (psia - STD_P_PSIA) / 0.1450377377
            elif u_to in ["mpa"]:
                return psia / 145.0377377
            elif u_to in ["mpag"]:
                return (psia - STD_P_PSIA) / 145.0377377
            elif u_to in ["atm"]:
                return psia / STD_P_PSIA
            elif u_to in ["pa"]:
                return psia / 0.0001450377377
            elif u_to in ["pag"]:
                return (psia - STD_P_PSIA) / 0.0001450377377
            elif u_to in ["mbar"]:
                return psia / 0.01450377377
            elif u_to in ["mbarg"]:
                return (psia - STD_P_PSIA) / 0.01450377377

        # Dimensional base-unit conversions
        for dim_map in ALL_DIMENSIONS:
            if u_from in dim_map and u_to in dim_map:
                base_val = val * dim_map[u_from]
                return base_val / dim_map[u_to]

        raise ValueError(f"Independent reference converter: unsupported conversion from '{from_unit}' to '{to_unit}'")
