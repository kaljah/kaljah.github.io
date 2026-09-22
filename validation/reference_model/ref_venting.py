"""
INDEPENDENT REFERENCE MODEL: Vented Emissions
Pneumatic Devices, Blowdown/Depressuring, Storage Tank Flashing, Liquids Unloading.
First-principles implementation - ZERO production code imports.
Governing equations:
- API Compendium 2021 §5.3, §5.4, §5.6
- US EPA Subpart W (40 CFR §98.233)
"""

import math
from .ref_constants import (
    STD_TEMP_K,
    STD_PRESSURE_PSIA,
    DENSITY_CH4,
    DENSITY_CO2,
    CONV_SCF_TO_M3,
    CONV_BBL_TO_M3,
    resolve_gwp,
)
from .ref_combustion import ref_to_kelvin, ref_to_psia

PNEUMATIC_DEFAULT_RATES_SCF_HR = {
    "high_bleed": 37.3,
    "low_bleed": 1.39,
    "intermittent": 13.5,
    "pump": 13.3,
}


def ref_calculate_pneumatic_devices(
    device_count,
    hours=8760,
    device_type="intermittent",
    vent_rate_scf_hr=None,
    ch4_fraction=0.90,
    co2_fraction=0.0,
    gwp_standard="AR5",
    gwp_horizon="100",
):
    """
    API Compendium §6.10 & EPA Subpart W §98.233(a):
    Pneumatic device vent calculation.
    """
    if device_count is None or float(device_count) <= 0:
        return {"co2": 0.0, "ch4": 0.0, "n2o": 0.0, "co2e": 0.0}

    count = float(device_count)
    hrs = float(hours or 8760.0)
    dt = str(device_type or "intermittent").lower().strip().replace(" ", "_")
    rate = float(vent_rate_scf_hr) if vent_rate_scf_hr is not None else PNEUMATIC_DEFAULT_RATES_SCF_HR.get(dt, 13.5)

    total_scf = count * rate * hrs
    vol_m3 = total_scf * CONV_SCF_TO_M3

    c1 = float(ch4_fraction or 0.90)
    co2_f = float(co2_fraction or 0.0)

    ch4_tonnes = (vol_m3 * c1 * DENSITY_CH4) / 1000.0
    co2_tonnes = (vol_m3 * co2_f * DENSITY_CO2) / 1000.0

    gwp = resolve_gwp(gwp_standard, gwp_horizon)
    co2e = co2_tonnes * gwp["CO2"] + ch4_tonnes * gwp["CH4"]

    return {"co2": co2_tonnes, "ch4": ch4_tonnes, "n2o": 0.0, "co2e": co2e}


def ref_calculate_blowdown(
    vessel_volume_m3,
    initial_press,
    final_press=0.0,
    press_unit="psig",
    temp_c=15.56,
    events=1,
    ch4_fraction=0.90,
    co2_fraction=0.01,
    z_factor=1.0,
    use_absolute_inventory=True,
    gwp_standard="AR5",
    gwp_horizon="100",
):
    """
    API Compendium 2021 Eq. 6-4:
    V_std = V_vessel * (P_abs / P_std) * (T_std / T_meas) * (1 / Z) * events
    If use_absolute_inventory is True, computes full gas inventory expansion from P_abs.
    If False, computes physical vented delta (P_init - P_atm).
    """
    if vessel_volume_m3 is None or float(vessel_volume_m3) <= 0:
        return {"co2": 0.0, "ch4": 0.0, "n2o": 0.0, "co2e": 0.0}

    vol_m3 = float(vessel_volume_m3)
    p_init_psia = ref_to_psia(initial_press, press_unit)
    p_fin_psia = ref_to_psia(final_press, press_unit) if not use_absolute_inventory else 0.0
    delta_p = max(0.0, p_init_psia - p_fin_psia) if not use_absolute_inventory else p_init_psia

    t_k = ref_to_kelvin(temp_c, "c")
    t_factor = STD_TEMP_K / max(1.0, t_k)
    p_factor = delta_p / STD_PRESSURE_PSIA
    z = float(z_factor) if z_factor and float(z_factor) > 0 else 1.0

    vent_m3 = vol_m3 * p_factor * t_factor * (1.0 / z) * float(events or 1)

    c1 = float(ch4_fraction or 0.90)
    co2_f = float(co2_fraction or 0.01)

    ch4_tonnes = (vent_m3 * c1 * DENSITY_CH4) / 1000.0
    co2_tonnes = (vent_m3 * co2_f * DENSITY_CO2) / 1000.0

    gwp = resolve_gwp(gwp_standard, gwp_horizon)
    co2e = co2_tonnes * gwp["CO2"] + ch4_tonnes * gwp["CH4"]

    return {"co2": co2_tonnes, "ch4": ch4_tonnes, "n2o": 0.0, "co2e": co2e}


def ref_calculate_tank_flashing(
    liquid_volume_bbl,
    gor_scf_bbl=None,
    ef_ch4_kg_bbl=None,
    ch4_fraction=0.75,
    co2_fraction=0.02,
    control_eff=0.0,
    gwp_standard="AR5",
    gwp_horizon="100",
):
    if liquid_volume_bbl is None or float(liquid_volume_bbl) <= 0:
        return {"co2": 0.0, "ch4": 0.0, "n2o": 0.0, "co2e": 0.0}

    vol_bbl = float(liquid_volume_bbl)
    ctrl = max(0.0, min(1.0, float(control_eff or 0.0)))
    uncontrolled_multiplier = 1.0 - ctrl

    if ef_ch4_kg_bbl is not None and float(ef_ch4_kg_bbl) > 0:
        ch4_kg = vol_bbl * float(ef_ch4_kg_bbl) * uncontrolled_multiplier
        ch4_tonnes = ch4_kg / 1000.0
        co2_tonnes = 0.0
    else:
        gor = float(gor_scf_bbl or 20.0)
        total_scf = vol_bbl * gor
        vol_m3 = total_scf * CONV_SCF_TO_M3
        c1 = float(ch4_fraction or 0.75)
        co2_f = float(co2_fraction or 0.02)
        ch4_tonnes = (vol_m3 * c1 * DENSITY_CH4 * uncontrolled_multiplier) / 1000.0
        co2_tonnes = (vol_m3 * co2_f * DENSITY_CO2 * uncontrolled_multiplier) / 1000.0

    gwp = resolve_gwp(gwp_standard, gwp_horizon)
    co2e = co2_tonnes * gwp["CO2"] + ch4_tonnes * gwp["CH4"]

    return {"co2": co2_tonnes, "ch4": ch4_tonnes, "n2o": 0.0, "co2e": co2e}
