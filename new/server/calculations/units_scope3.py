"""Scope 3 activity and emission-factor units (moved out of calculations/units.py; re-exported from there)."""
import re as _re

from .units import (CONVERSIONS, FREIGHT_UNITS_TO_TONNE_KM, NG_HHV_BTU_PER_SCF, PASSENGER_UNITS_TO_PKM, UnitError,
                    unit_dimension)


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


_SCOPE3_MASS_TONNES = {
    "": 0.001, "kg": 0.001, "kgs": 0.001, "kilogram": 0.001, "kilograms": 0.001,
    "t": 1.0, "tonne": 1.0, "tonnes": 1.0, "metric ton": 1.0, "metric tons": 1.0, "metric tonne": 1.0,
    "metric tonnes": 1.0, "mt": 1.0,
    "g": 1e-6, "gram": 1e-6, "grams": 1e-6,
    "lb": 0.45359237e-3, "lbs": 0.45359237e-3, "pound": 0.45359237e-3, "pounds": 0.45359237e-3,
    "short ton": 0.90718474, "short tons": 0.90718474, "us ton": 0.90718474, "us tons": 0.90718474,
    "long ton": 1.0160469088, "long tons": 1.0160469088,
}


_SCOPE3_UNIT_ALIASES = {
    "$": "usd", "us$": "usd", "dollar": "usd", "dollars": "usd", "usd": "usd",
    "pkm": "passenger-km", "passenger_km": "passenger-km", "p-km": "passenger-km",
    "tkm": "tonne-km", "t-km": "tonne-km", "tonne_km": "tonne-km", "tonne-km": "tonne-km",
    "ton-km": "tonne-km", "ton_km": "tonne-km", "tonkm": "tonne-km",
    "litre": "l", "litres": "l", "liter": "l", "liters": "l",
    "mmbtu": "mmbtu", "mm-btu": "mmbtu", "million-btu": "mmbtu", "mm_btu": "mmbtu",
    "mscf": "mscf", "mmscf": "mmscf", "mcf": "mcf", "scf": "scf",
}

_GAS_VOLUME_UNITS = {"scf", "mcf", "mscf", "mmscf", "mmcf", "m3", "sm3", "nm3"}
_LIQUID_VOLUME_UNITS = {"bbl", "gal", "gallon", "gallons", "l", "liter", "liters", "litre", "litres", "barrel", "barrels"}
_ENERGY_UNITS = {"mmbtu", "gj", "mj", "kwh", "mwh", "therm", "btu"}


def _scope3_activity_in_factor_unit(activity_unit, den):
    """Activity units per factor denominator unit (1000 for kg against a per-tonne factor). Equal or
    absent units give 1. Units that are both physical convert; anything else that differs is
    refused: an amount in kg against a per-tonne factor was booked 1000x high (bug hunt #30)."""
    def norm(u):
        u = _re.sub(r"\s+", " ", str(u or "").strip().lower())
        return _SCOPE3_UNIT_ALIASES.get(u, u)

    a, d = norm(activity_unit), norm(den)
    if not a or not d or a == d or a in ("unit", "units") or d in ("unit", "units", "item", "items"):
        return 1.0

    a_clean = a.replace(" ", "_")
    d_clean = d.replace(" ", "_")

    # Gas volume to energy conversion via standard Natural Gas HHV (API Compendium §8.1 / 1,020 Btu/scf)
    if a_clean in _GAS_VOLUME_UNITS and d_clean in _ENERGY_UNITS:
        _, m3_factor = unit_dimension(a)
        scf = m3_factor / CONVERSIONS["scf_to_m3"]
        btu = scf * NG_HHV_BTU_PER_SCF
        mj = btu * CONVERSIONS["btu_to_kj"] / 1000.0
        _, d_mj_factor = unit_dimension(d)
        return mj / d_mj_factor

    if d_clean in _GAS_VOLUME_UNITS and a_clean in _ENERGY_UNITS:
        _, d_m3_factor = unit_dimension(d)
        d_scf = d_m3_factor / CONVERSIONS["scf_to_m3"]
        d_btu = d_scf * NG_HHV_BTU_PER_SCF
        d_mj = d_btu * CONVERSIONS["btu_to_kj"] / 1000.0
        _, a_mj_factor = unit_dimension(a)
        return a_mj_factor / d_mj

    # freight and passenger units of the module's own tables (BA-023: they were refused); a bare "ton-mile" stays
    # refused like every bare "ton" (write short_ton-mile or tonne-mile)
    for table in (FREIGHT_UNITS_TO_TONNE_KM, PASSENGER_UNITS_TO_PKM):
        if a_clean in table and d_clean in table:
            if any(u in ("ton-mile", "ton_mile", "tonmile") for u in (a_clean, d_clean)):
                from input_validation import ValidationError
                raise ValidationError(f"'{activity_unit if a_clean in ('ton-mile', 'ton_mile', 'tonmile') else den}': "
                                      "'ton' is ambiguous - use short_ton-mile or tonne-mile", "unit")
            return table[a_clean] / table[d_clean]
    # a plain m3 against a liquid volume is a liquid m3 (1 bbl = 0.158987 m3; BA-023), not a gas volume
    if (a_clean == "m3" and d_clean in _LIQUID_VOLUME_UNITS) or (d_clean == "m3" and a_clean in _LIQUID_VOLUME_UNITS):
        return unit_dimension(a)[1] / unit_dimension(d)[1]

    # Refuse conversion between gas volume and liquid volume
    if (a_clean in _GAS_VOLUME_UNITS and d_clean in _LIQUID_VOLUME_UNITS) or \
       (a_clean in _LIQUID_VOLUME_UNITS and d_clean in _GAS_VOLUME_UNITS):
        from input_validation import ValidationError
        raise ValidationError(f"Activity unit '{activity_unit}' cannot be converted to the factor's unit 'per {den}'",
                              "unit")

    def dim(u):
        parts = u.split("-")
        out = []
        for p in parts:
            dm, f = unit_dimension(p)
            out.append((dm, f))
        return out

    try:
        da, dd = dim(a), dim(d)
    except UnitError as err:
        from input_validation import ValidationError
        raise ValidationError(f"Activity unit '{activity_unit}' cannot be matched to the factor's unit "
                              f"'per {den}': {err}", "unit")
    if len(da) != len(dd) or any(x[0] != y[0] for x, y in zip(da, dd)):
        from input_validation import ValidationError
        raise ValidationError(f"Activity unit '{activity_unit}' cannot be converted to the factor's unit 'per {den}'",
                              "unit")
    scale = 1.0
    for (_, fa), (_, fd) in zip(da, dd):
        scale *= fa / fd
    return scale


def scope3_complete_factor_unit(ef_unit, den_unit):
    """A factor unit with its activity denominator: blank is kg CO2e per unit, and a unit given without "/" or " per "
    keeps its own mass ("tCO2e" -> "tCO2e / den"). It used to be replaced by "kg CO2e / den", reading a factor in
    t CO2e 1000x low (audit 2026-11 F-UPL-03); an unknown mass is then refused by compute_scope3_co2e."""
    u = str(ef_unit or "").strip()
    den = str(den_unit or "unit").strip() or "unit"
    if not u:
        return f"kg CO2e / {den}"
    if "/" in u or " per " in u.lower():
        return u
    return f"{u} / {den}"


def compute_scope3_co2e(
    amt: float, ef: float, ef_unit: str = "", calc_method: str = "", activity_unit: str = ""
) -> float:
    """
    Authoritatively calculates Scope 3 CO2e in metric tonnes from activity amount and emission factor.

    Distinguishes the numerator GHG mass unit (t, kg, g, lb; kg when not given) from the
    denominator activity unit (tonne, liter, $1,000 ...).
    - A per-1,000 denominator ('kg CO2e/$1000', 't CO2e/1000 km') divides the activity by 1,000.
    - Tonnes numerator ('tCO2e/unit', 'tonne CO2e/bbl', 't/bbl'): co2e = amt * ef.
    - kg numerator ('kg CO2e/liter', 'kg/unit'): co2e = amt * ef / 1000.
    `calc_method` is accepted for backward compatibility and does not change the result.
    `activity_unit`, when given with a factor denominator, converts the amount into it (kg against a
    per-tonne factor) or is refused when the two cannot be converted.
    """
    try:
        amt_val = float(amt or 0.0)
        ef_val = float(ef or 0.0)
    except (ValueError, TypeError):
        return 0.0

    if amt_val <= 0.0 or ef_val <= 0.0:
        return 0.0

    unit_str = str(ef_unit or "").lower().strip()

    # 1. Split the unit into numerator (GHG mass) and denominator (activity)
    if "/" in unit_str:
        num, den = (p.strip() for p in unit_str.split("/", 1))
    elif " per " in unit_str:
        num, den = (p.strip() for p in unit_str.split(" per ", 1))
    else:
        num, den = unit_str, ""

    if den in ("ton", "tons"):
        from input_validation import ValidationError
        raise ValidationError(f"Emission factor unit '{ef_unit}': 'ton' is ambiguous - use tonne (metric) or short ton", "factor_unit")

    # 2. A per-1,000 denominator ("kg CO2e/$1000", "t CO2e/1,000 km") scales the activity; it is
    # read from the unit only. The method name says nothing about the factor's basis: an EEIO
    # record stores its factor per USD (audit 2026-09-30: an "EEIO" method read a per-USD factor
    # as per $1,000, 1000x low).
    m_thousand = _re.match(r"^(?:\$|usd)?\s*(?:1,?000(?![0-9])|1k(?![0-9a-z])|thousand\b|k\s*(?:\$|usd(?![a-z])))", den)
    scale = 0.001 if m_thousand else 1.0
    den_unit = den[m_thousand.end():].strip() if m_thousand else den
    if m_thousand and not den_unit:
        den_unit = "usd" if ("$" in den or "usd" in den) else ""
    scale *= _scope3_activity_in_factor_unit(activity_unit, den_unit)

    # 3. Numerator mass in tonnes per unit, by exact token after the gas name is cut off
    # ("kgCO2e" -> "kg", "MT CO2e" -> "mt"). "MT" / "metric ton(s)" / "short ton" used to fall
    # through to kg (1000x / 907x low); a bare "ton" is ambiguous and refused as in the uploads.
    mass = _re.split(r"co2|ch4|n2o|ghg|carbon", num, maxsplit=1)[0].strip().replace("_", " ")
    mass = _re.sub(r"\s+", " ", mass)
    if mass not in _SCOPE3_MASS_TONNES:
        from input_validation import ValidationError
        if mass in ("ton", "tons"):
            raise ValidationError(f"Emission factor unit '{ef_unit}': 'ton' is ambiguous - use tonne (metric) or "
                                  "short ton", "factor_unit")
        raise ValidationError(f"Emission factor unit '{ef_unit}': unknown mass '{mass}' (use kg, t, g or lb CO2e "
                              "per unit)", "factor_unit")
    to_tonnes = _SCOPE3_MASS_TONNES[mass]
    return amt_val * ef_val * scale * to_tonnes
