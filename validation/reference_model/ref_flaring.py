"""
INDEPENDENT REFERENCE MODEL: Flaring Dual-Efficiency Engine
First-principles implementation - ZERO production code imports.
Governing equations:
- API Compendium 2021 §5.2 (Flaring Emissions)
- US EPA AP-42 Chapter 13.5 (Industrial Flares)
- World Bank GGFR (Global Gas Flaring Reduction Partnership Guidelines)
"""

from .ref_constants import (
    DENSITY_CH4,
    DENSITY_CO2,
    CONV_SCF_TO_M3,
    CONV_MSCF_TO_M3,
    CONV_MMSCF_TO_M3,
    resolve_gwp,
)
from .ref_combustion import ref_normalize_gas_volume

FLARE_DEFAULTS = {
    "elevated": {"eta_c": 0.984, "eta_d": 0.980},
    "steam_assisted": {"eta_c": 0.984, "eta_d": 0.980},
    "air_assisted": {"eta_c": 0.984, "eta_d": 0.980},
    "unassisted": {"eta_c": 0.984, "eta_d": 0.980},
    "open": {"eta_c": 0.984, "eta_d": 0.980},
    "enclosed": {"eta_c": 0.996, "eta_d": 0.995},
    "ground": {"eta_c": 0.996, "eta_d": 0.995},
    "pit": {"eta_c": 0.920, "eta_d": 0.950},
    "open_pit": {"eta_c": 0.920, "eta_d": 0.950},
}


def ref_calculate_flaring(
    gas_volume,
    ch4_fraction=0.90,
    flare_type="elevated",
    gas_unit="m3",
    combustion_eff=None,
    destruction_eff=None,
    temp=None,
    temp_unit="C",
    press=None,
    press_unit="psig",
    z_factor=1.0,
    hhv=None,  # MMBtu / m3 or MMBtu / scf
    ef_n2o=None,  # kg N2O / MMBtu
    gwp_standard="AR5",
    gwp_horizon="100",
    gas_composition=None,
):
    """
    Independently calculates dual-efficiency flaring emissions.
    Per API Compendium 2021 §5.2:
    - CO2 is generated from combustion efficiency eta_c
    - Undestroyed methane slip is determined by destruction efficiency eta_d: (1 - eta_d)
    Returns: dict with co2_tonnes, ch4_tonnes, n2o_tonnes, co2e_tonnes
    """
    if gas_volume is None or float(gas_volume) <= 0:
        return {"co2": 0.0, "ch4": 0.0, "n2o": 0.0, "co2e": 0.0}

    raw_vol = float(gas_volume)
    norm_vol = ref_normalize_gas_volume(
        raw_vol, temp=temp, temp_unit=temp_unit, press=press, press_unit=press_unit, z_factor=z_factor
    )

    u = str(gas_unit).strip().lower()
    vol_m3 = norm_vol
    if u in ["scf", "cf", "ft3"]:
        vol_m3 = norm_vol * CONV_SCF_TO_M3
    elif u in ["mscf", "mcf"]:
        vol_m3 = norm_vol * CONV_MSCF_TO_M3
    elif u in ["mmscf"]:
        vol_m3 = norm_vol * CONV_MMSCF_TO_M3

    ft = str(flare_type or "elevated").lower().strip().replace("-", "_").replace(" ", "_")
    defaults = FLARE_DEFAULTS.get(ft, {"eta_c": 0.984, "eta_d": 0.980})
    eta_c = defaults["eta_c"]
    eta_d = defaults["eta_d"]

    if combustion_eff is not None and str(combustion_eff).strip() != "":
        eff = float(str(combustion_eff).replace("%", "").strip())
        if eff > 1.0:
            eff /= 100.0
        eta_c = max(0.0, min(1.0, eff))

    if destruction_eff is not None and str(destruction_eff).strip() != "":
        deff = float(str(destruction_eff).replace("%", "").strip())
        if deff > 1.0:
            deff /= 100.0
        eta_d = max(0.0, min(1.0, deff))

    # Gas composition analysis
    c1 = float(ch4_fraction if ch4_fraction is not None else 0.90)
    c2 = 0.0
    c3 = 0.0
    c4 = 0.0
    c5 = 0.0
    c6 = 0.0
    co2_native_frac = 0.0

    if gas_composition and isinstance(gas_composition, dict):
        c1 = float(gas_composition.get("c1", c1) or 0.0)
        c2 = float(gas_composition.get("c2", 0.0) or 0.0)
        c3 = float(gas_composition.get("c3", 0.0) or 0.0)
        c4 = float(gas_composition.get("c4", 0.0) or (float(gas_composition.get("ic4", 0.0) or 0.0) + float(gas_composition.get("nc4", 0.0) or 0.0)))
        c5 = float(gas_composition.get("c5", 0.0) or (float(gas_composition.get("ic5", 0.0) or 0.0) + float(gas_composition.get("nc5", 0.0) or 0.0)))
        c6 = float(gas_composition.get("c6_plus", 0.0) or gas_composition.get("c6", 0.0) or 0.0)
        co2_native_frac = float(gas_composition.get("co2_comp") or gas_composition.get("co2_mol") or gas_composition.get("co2", 0.0) or 0.0)

    # Hydrocarbon carbon moles per mole of gas
    total_c_moles = c1 * 1.0 + c2 * 2.0 + c3 * 3.0 + c4 * 4.0 + c5 * 5.0 + c6 * 6.0

    # Combusted CO2 from hydrocarbons
    co2_combusted_tonnes = (vol_m3 * total_c_moles * eta_c * DENSITY_CO2) / 1000.0
    # Native CO2 passed through flare
    co2_native_tonnes = (vol_m3 * co2_native_frac * DENSITY_CO2) / 1000.0
    total_co2_tonnes = co2_combusted_tonnes + co2_native_tonnes

    # Undestroyed methane slip per API Compendium 2021 Eq. 5-4: (1 - eta_d)
    ch4_tonnes = (vol_m3 * c1 * (1.0 - eta_d) * DENSITY_CH4) / 1000.0

    # N2O emissions from flaring heat
    n2o_tonnes = 0.0
    if ef_n2o is not None and float(ef_n2o) > 0:
        gas_scf = vol_m3 / CONV_SCF_TO_M3
        heat_val_hhv = float(hhv or 1020.0)  # Btu/scf default
        total_mmbtu = (gas_scf * heat_val_hhv) / 1_000_000.0
        n2o_tonnes = (total_mmbtu * float(ef_n2o)) / 1000.0

    gwp = resolve_gwp(gwp_standard, gwp_horizon)
    co2e_total = (
        total_co2_tonnes * gwp["CO2"]
        + ch4_tonnes * gwp["CH4"]
        + n2o_tonnes * gwp["N2O"]
    )

    return {
        "co2": total_co2_tonnes,
        "ch4": ch4_tonnes,
        "n2o": n2o_tonnes,
        "co2e": co2e_total,
    }
