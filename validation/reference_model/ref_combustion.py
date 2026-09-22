"""
INDEPENDENT REFERENCE MODEL: Stationary & Mobile Combustion
First-principles implementation - ZERO production code imports.
Governing equations:
- API Compendium 2021 §4.2.1 (Thermodynamic Gas Normalization)
- API Compendium 2021 §5.1 (Stationary Combustion)
- 40 CFR Part 98 Subpart C (General Stationary Fuel Combustion)
- ISO 14064-1:2018 §5.2.2 (Quantification of GHG Emissions)
"""

from .ref_constants import (
    STD_TEMP_K,
    STD_PRESSURE_PSIA,
    DENSITY_CH4,
    DENSITY_CO2,
    CONV_SCF_TO_M3,
    CONV_MSCF_TO_M3,
    CONV_MMSCF_TO_M3,
    resolve_gwp,
)


def ref_to_kelvin(temp_val, unit="c"):
    if temp_val is None:
        return STD_TEMP_K
    u = str(unit).strip().lower()
    v = float(temp_val)
    if u in ["c", "celsius", "degc", "°c"]:
        return v + 273.15
    elif u in ["f", "fahrenheit", "degf", "°f"]:
        return (v - 32.0) * 5.0 / 9.0 + 273.15
    elif u in ["k", "kelvin"]:
        return v
    elif u in ["r", "rankine", "degr", "°r"]:
        return v * 5.0 / 9.0
    return v + 273.15


def ref_to_psia(press_val, unit="psig", atmospheric_psia=STD_PRESSURE_PSIA):
    if press_val is None:
        return STD_PRESSURE_PSIA
    u = str(unit).strip().lower()
    v = float(press_val)
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
    elif u in ["atm"]:
        return max(0.0, v * atmospheric_psia)
    return max(0.0, v + atmospheric_psia)


def ref_normalize_gas_volume(volume, temp=None, temp_unit="C", press=None, press_unit="psig", z_factor=1.0):
    """
    API Compendium 2021 Eq. 4-4:
    V_std = V_meas * (P_meas_abs / P_std) * (T_std / T_meas_abs) * (1 / Z)
    """
    if volume is None or float(volume) <= 0:
        return 0.0
    vol = float(volume)

    p_factor = 1.0
    if press is not None and str(press).strip() != "":
        p_abs = ref_to_psia(press, press_unit)
        p_factor = p_abs / STD_PRESSURE_PSIA

    t_factor = 1.0
    if temp is not None and str(temp).strip() != "":
        t_abs = ref_to_kelvin(temp, temp_unit)
        t_factor = STD_TEMP_K / max(1.0, t_abs)

    z = float(z_factor) if z_factor and float(z_factor) > 0 else 1.0
    return vol * p_factor * t_factor * (1.0 / z)


def ref_calculate_combustion(
    fuel_quantity,
    ef_co2=None,
    ef_ch4=None,
    ef_n2o=None,
    fuel_unit="m3",
    ef_unit="kg/m3",
    hhv=None,
    fuel_type="gases",
    combustion_efficiency=0.995,
    temp=None,
    temp_unit="C",
    press=None,
    press_unit="psig",
    z_factor=1.0,
    gwp_standard="AR5",
    gwp_horizon="100",
    gas_composition=None,
):
    """
    Independently calculates stationary combustion emissions.
    Returns: dict with co2_tonnes, ch4_tonnes, n2o_tonnes, co2e_tonnes
    """
    if fuel_quantity is None or float(fuel_quantity) <= 0:
        return {"co2": 0.0, "ch4": 0.0, "n2o": 0.0, "co2e": 0.0}

    qty = float(fuel_quantity)
    is_gas = fuel_type in ["gases", "gas", "Natural Gas", "natural_gas"] or str(fuel_unit).lower() in ["m3", "scf", "mscf", "mmscf"]

    # Thermodynamic volume normalization
    if is_gas and (temp is not None or press is not None):
        qty = ref_normalize_gas_volume(qty, temp=temp, temp_unit=temp_unit, press=press, press_unit=press_unit, z_factor=z_factor)

    # Unit conversions for activity
    u = str(fuel_unit).strip().lower()
    co2_ef = float(ef_co2 or 0.0)
    ch4_ef = float(ef_ch4 or 0.0)
    n2o_ef = float(ef_n2o or 0.0)

    # If Tier 3 Gas Composition is provided (Carbon balance approach)
    if gas_composition and isinstance(gas_composition, dict) and "c1" in gas_composition and gas_composition["c1"] not in [None, "", "-"]:
        # Convert volume to m3 at standard conditions
        vol_m3 = qty
        if u in ["scf", "cf", "ft3"]:
            vol_m3 = qty * CONV_SCF_TO_M3
        elif u in ["mscf", "mcf"]:
            vol_m3 = qty * CONV_MSCF_TO_M3
        elif u in ["mmscf"]:
            vol_m3 = qty * CONV_MMSCF_TO_M3

        c1 = float(gas_composition.get("c1") or 0.0)
        c2 = float(gas_composition.get("c2") or 0.0)
        c3 = float(gas_composition.get("c3") or 0.0)
        c4_val = float(gas_composition.get("c4") or (float(gas_composition.get("ic4") or 0.0) + float(gas_composition.get("nc4") or 0.0)))
        c5_val = float(gas_composition.get("c5") or (float(gas_composition.get("ic5") or 0.0) + float(gas_composition.get("nc5") or 0.0)))
        c6_plus = float(gas_composition.get("c6_plus") or gas_composition.get("c6") or 0.0)
        co2_native = float(gas_composition.get("co2_comp") or gas_composition.get("co2_mol") or gas_composition.get("co2") or 0.0)

        # Moles of carbon per mole of gas
        total_c_moles = (
            c1 * 1.0 + c2 * 2.0 + c3 * 3.0 + c4_val * 4.0 + c5_val * 5.0 + c6_plus * 6.0
        )
        eta_c = max(0.0, min(1.0, float(combustion_efficiency)))

        # Combusted CO2 (tonnes)
        co2_combusted_tonnes = (vol_m3 * total_c_moles * eta_c * DENSITY_CO2) / 1000.0
        co2_native_tonnes = (vol_m3 * co2_native * DENSITY_CO2) / 1000.0
        co2_tonnes = co2_combusted_tonnes + co2_native_tonnes

        # Uncombusted methane slip (tonnes)
        ch4_slip_tonnes = (vol_m3 * c1 * (1.0 - eta_c) * DENSITY_CH4) / 1000.0
        n2o_tonnes = (qty * n2o_ef) / 1000.0
        ch4_tonnes = ch4_slip_tonnes
    else:
        # Standard factor multiplication
        co2_tonnes = (qty * co2_ef) / 1000.0
        ch4_tonnes = (qty * ch4_ef) / 1000.0
        n2o_tonnes = (qty * n2o_ef) / 1000.0

    gwp = resolve_gwp(gwp_standard, gwp_horizon)
    co2e_total = (
        co2_tonnes * gwp["CO2"]
        + ch4_tonnes * gwp["CH4"]
        + n2o_tonnes * gwp["N2O"]
    )

    return {
        "co2": co2_tonnes,
        "ch4": ch4_tonnes,
        "n2o": n2o_tonnes,
        "co2e": co2e_total,
    }
