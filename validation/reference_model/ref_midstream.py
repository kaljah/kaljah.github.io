"""
INDEPENDENT REFERENCE MODEL: Midstream Processes (AGR & Dehydration)
First-principles implementation - ZERO production code imports.
Governing equations:
- API Compendium 2021 §6.5 & Table 6-5 (Acid Gas Removal with Methane Slip)
- API Compendium 2021 §6.6 (Glycol Dehydrators)
- 40 CFR §98.233(d), (e)
"""

from .ref_constants import (
    DENSITY_CO2,
    DENSITY_CH4,
    CONV_SCF_TO_M3,
    CONV_MSCF_TO_M3,
    CONV_MMSCF_TO_M3,
    resolve_gwp,
)
from .ref_combustion import ref_normalize_gas_volume


def ref_calculate_agr(
    feed_gas_volume,
    co2_inlet_fraction,
    co2_outlet_fraction=0.0001,
    ch4_inlet_fraction=0.85,
    ch4_slip_fraction=0.001,  # API Compendium 2021 Table 6-5 default (0.1% of feed methane)
    unit="m3",
    control_eff=0.0,
    temp=None,
    temp_unit="C",
    press=None,
    press_unit="psig",
    z_factor=1.0,
    gwp_standard="AR5",
    gwp_horizon="100",
):
    if feed_gas_volume is None or float(feed_gas_volume) <= 0:
        return {"co2": 0.0, "ch4": 0.0, "n2o": 0.0, "co2e": 0.0}

    raw_vol = float(feed_gas_volume)
    norm_vol = ref_normalize_gas_volume(
        raw_vol, temp=temp, temp_unit=temp_unit, press=press, press_unit=press_unit, z_factor=z_factor
    )

    u = str(unit).strip().lower()
    vol_m3 = norm_vol
    if u in ["scf", "cf", "ft3"]:
        vol_m3 = norm_vol * CONV_SCF_TO_M3
    elif u in ["mscf", "mcf"]:
        vol_m3 = norm_vol * CONV_MSCF_TO_M3
    elif u in ["mmscf"]:
        vol_m3 = norm_vol * CONV_MMSCF_TO_M3

    c_in = max(0.0, float(co2_inlet_fraction or 0.0))
    c_out = max(0.0, float(co2_outlet_fraction or 0.0))
    delta_co2 = max(0.0, c_in - c_out)

    ctrl = max(0.0, min(1.0, float(control_eff or 0.0)))
    co2_vent_m3 = vol_m3 * delta_co2 * (1.0 - ctrl)
    co2_tonnes = (co2_vent_m3 * DENSITY_CO2) / 1000.0

    # Table 6-5 Methane co-absorption slip
    ch4_feed_f = max(0.0, float(ch4_inlet_fraction or 0.85))
    slip_f = max(0.0, float(ch4_slip_fraction or 0.0))
    ch4_slipped_m3 = vol_m3 * ch4_feed_f * slip_f * (1.0 - ctrl)
    ch4_tonnes = (ch4_slipped_m3 * DENSITY_CH4) / 1000.0

    gwp = resolve_gwp(gwp_standard, gwp_horizon)
    co2e = co2_tonnes * gwp["CO2"] + ch4_tonnes * gwp["CH4"]

    return {"co2": co2_tonnes, "ch4": ch4_tonnes, "n2o": 0.0, "co2e": co2e}


def ref_calculate_dehydrator(
    gas_throughput_m3,
    ef_ch4_kg_m3=None,
    ef_ch4_kg_mmscf=None,
    control_eff=0.0,
    gwp_standard="AR5",
    gwp_horizon="100",
):
    if gas_throughput_m3 is None or float(gas_throughput_m3) <= 0:
        return {"co2": 0.0, "ch4": 0.0, "n2o": 0.0, "co2e": 0.0}

    vol_m3 = float(gas_throughput_m3)
    ctrl = max(0.0, min(1.0, float(control_eff or 0.0)))
    uncontrolled = 1.0 - ctrl

    if ef_ch4_kg_m3 is not None:
        ch4_kg = vol_m3 * float(ef_ch4_kg_m3) * uncontrolled
    elif ef_ch4_kg_mmscf is not None:
        mmscf = vol_m3 / CONV_MMSCF_TO_M3
        ch4_kg = mmscf * float(ef_ch4_kg_mmscf) * uncontrolled
    else:
        ch4_kg = vol_m3 * 0.00035 * uncontrolled

    ch4_tonnes = ch4_kg / 1000.0
    gwp = resolve_gwp(gwp_standard, gwp_horizon)
    co2e = ch4_tonnes * gwp["CH4"]

    return {"co2": 0.0, "ch4": ch4_tonnes, "n2o": 0.0, "co2e": co2e}
